"""
Authentication Views
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import base64

from .models import SecureUser, SecurityAuditLog, UserSession
from .forms import SecureRegistrationForm, SecureLoginForm
from encryption.e2e_crypto import E2EEncryption
from encryption.key_manager import KeyManager


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


@csrf_protect
@require_http_methods(["GET", "POST"])
def register_view(request):
    """User registration with key generation"""
    if request.user.is_authenticated:
        return redirect('chat:room_list')
    
    if request.method == 'POST':
        form = SecureRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            
            # Generate encryption keys
            key_pair = E2EEncryption.generate_key_pair()
            
            # Encrypt private key with password-derived key
            password = form.cleaned_data['password1']
            key, salt = E2EEncryption.derive_key_from_password(password)
            
            # Use KeyManager to encrypt the private key
            from nacl.secret import SecretBox
            box = SecretBox(key)
            nonce = box.encrypt(key_pair.private_key).nonce
            encrypted_private = box.encrypt(key_pair.private_key, nonce)
            
            # Store encrypted keys
            user.encrypted_private_key = base64.b64encode(
                salt + encrypted_private
            ).decode('utf-8')
            user.public_key = base64.b64encode(key_pair.public_key).decode('utf-8')
            user.keys_generated_at = timezone.now()
            
            user.save()
            
            # Log registration
            SecurityAuditLog.objects.create(
                user=user,
                event_type='login',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'action': 'registration'}
            )
            
            login(request, user)
            messages.success(request, 'Account created successfully! Your encryption keys have been generated.')
            return redirect('chat:room_list')
    else:
        form = SecureRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """Secure login with account lockout protection"""
    if request.user.is_authenticated:
        return redirect('chat:room_list')
    
    if request.method == 'POST':
        form = SecureLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                user = SecureUser.objects.get(username=username)
                
                # Check if account is locked
                if user.check_locked():
                    messages.error(
                        request, 
                        f'Account is locked. Try again after {user.locked_until.strftime("%H:%M")}'
                    )
                    return render(request, 'accounts/login.html', {'form': form})
                
                # Authenticate
                user = authenticate(request, username=username, password=password)
                
                if user is not None:
                    user.reset_failed_logins()
                    login(request, user)
                    
                    # Create session record
                    UserSession.objects.create(
                        user=user,
                        session_key=request.session.session_key or 'unknown',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        expires_at=timezone.now() + timedelta(days=1)
                    )
                    
                    # Log successful login
                    SecurityAuditLog.objects.create(
                        user=user,
                        event_type='login',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    )
                    
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    next_url = request.GET.get('next', 'chat:room_list')
                    return redirect(next_url)
                else:
                    # Record failed attempt
                    user = SecureUser.objects.get(username=username)
                    user.record_failed_login()
                    
                    SecurityAuditLog.objects.create(
                        user=user,
                        event_type='failed_login',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    )
                    
                    messages.error(request, 'Invalid credentials')
                    
            except SecureUser.DoesNotExist:
                messages.error(request, 'Invalid credentials')
    else:
        form = SecureLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    """Secure logout"""
    # Log logout
    SecurityAuditLog.objects.create(
        user=request.user,
        event_type='logout',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    
    # Invalidate session
    UserSession.objects.filter(
        user=request.user,
        session_key=request.session.session_key
    ).update(is_active=False)
    
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """User profile with key information"""
    user = request.user
    
    # Get recent audit logs
    recent_logs = SecurityAuditLog.objects.filter(user=user)[:10]
    
    # Get active sessions
    active_sessions = UserSession.objects.filter(
        user=user, 
        is_active=True,
        expires_at__gt=timezone.now()
    )
    
    context = {
        'user': user,
        'recent_logs': recent_logs,
        'active_sessions': active_sessions,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
@require_http_methods(["POST"])
def terminate_session(request, session_id):
    """Terminate a specific session"""
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
        session.is_active = False
        session.save()
        messages.success(request, 'Session terminated.')
    except UserSession.DoesNotExist:
        messages.error(request, 'Session not found.')
    
    return redirect('accounts:profile')


@login_required
def get_public_key(request):
    """API endpoint to get user's public key"""
    from django.http import JsonResponse
    
    return JsonResponse({
        'public_key': request.user.public_key,
        'key_version': request.user.key_version,
    })
