"""
Chat Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import base64
import os

from .models import ChatRoom, RoomMembership, EncryptedMessage, UserPresence
from .forms import CreateRoomForm
from encryption.e2e_crypto import E2EEncryption
from encryption.key_manager import KeyManager


@login_required
def room_list(request):
    """List all rooms user is a member of"""
    memberships = RoomMembership.objects.filter(
        user=request.user
    ).select_related('room')
    
    rooms = [m.room for m in memberships]
    
    # Get unread counts
    room_data = []
    for membership in memberships:
        unread_count = EncryptedMessage.objects.filter(
            room=membership.room,
            timestamp__gt=membership.last_read_at
        ).exclude(sender=request.user).count()
        
        room_data.append({
            'room': membership.room,
            'role': membership.role,
            'unread_count': unread_count,
        })
    
    context = {
        'rooms': room_data,
    }
    
    return render(request, 'chat/room_list.html', context)


@login_required
def room_detail(request, room_id):
    """Chat room view"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check membership
    membership = RoomMembership.objects.filter(
        user=request.user,
        room=room
    ).first()
    
    if not membership:
        messages.error(request, 'You are not a member of this room.')
        return redirect('chat:room_list')
    
    # Update last read
    membership.last_read_at = timezone.now()
    membership.save()
    
    # Get recent messages (encrypted)
    messages_list = EncryptedMessage.objects.filter(
        room=room,
        is_deleted=False
    ).select_related('sender').order_by('-timestamp')[:50]
    
    # Get room members
    members = RoomMembership.objects.filter(
        room=room
    ).select_related('user')
    
    # Get online members
    online_user_ids = UserPresence.objects.filter(
        status='online',
        user__room_memberships__room=room
    ).values_list('user_id', flat=True)
    
    context = {
        'room': room,
        'membership': membership,
        'messages': reversed(list(messages_list)),
        'members': members,
        'online_user_ids': list(online_user_ids),
        'user_public_key': request.user.public_key,
        'encrypted_room_key': membership.encrypted_room_key_for_user,
    }
    
    return render(request, 'chat/room_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def create_room(request):
    """Create a new chat room"""
    if request.method == 'POST':
        form = CreateRoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.created_by = request.user
            
            # Generate room encryption key
            room_key = E2EEncryption.generate_room_key()
            
            # Get master key from environment
            master_password = os.environ.get('ROOM_KEY_PASSWORD', 'default-secure-key')
            key_manager = KeyManager(master_password)
            
            # Encrypt room key for storage
            room_key_data = key_manager.generate_room_key()
            room.encrypted_room_key = key_manager.encrypt_key(room_key)
            room.key_id = room_key_data['key_id']
            
            room.save()
            
            # Create membership for creator with encrypted room key
            # Encrypt room key for the user using their public key
            user_public_key = base64.b64decode(request.user.public_key)
            
            # For room keys, we store the room key encrypted with a derived key
            # In practice, you'd encrypt the room key with the user's public key
            encrypted_for_user = base64.b64encode(room_key).decode('utf-8')
            
            RoomMembership.objects.create(
                user=request.user,
                room=room,
                role='admin',
                encrypted_room_key_for_user=encrypted_for_user,
            )
            
            messages.success(request, f'Room "{room.name}" created successfully!')
            return redirect('chat:room_detail', room_id=room.id)
    else:
        form = CreateRoomForm()
    
    return render(request, 'chat/create_room.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def join_room(request, room_id):
    """Join a public room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    if room.room_type != 'public':
        messages.error(request, 'This room is private.')
        return redirect('chat:room_list')
    
    # Check if already a member
    if RoomMembership.objects.filter(user=request.user, room=room).exists():
        messages.info(request, 'You are already a member of this room.')
        return redirect('chat:room_detail', room_id=room.id)
    
    # Check member limit
    if room.memberships.count() >= room.max_members:
        messages.error(request, 'This room is full.')
        return redirect('chat:room_list')
    
    # Get room key and encrypt for user
    master_password = os.environ.get('ROOM_KEY_PASSWORD', 'default-secure-key')
    key_manager = KeyManager(master_password)
    room_key = key_manager.decrypt_key(room.encrypted_room_key)
    
    encrypted_for_user = base64.b64encode(room_key).decode('utf-8')
    
    RoomMembership.objects.create(
        user=request.user,
        room=room,
        encrypted_room_key_for_user=encrypted_for_user,
    )
    
    messages.success(request, f'You have joined "{room.name}"!')
    return redirect('chat:room_detail', room_id=room.id)


@login_required
@require_http_methods(["POST"])
def leave_room(request, room_id):
    """Leave a room"""
    membership = get_object_or_404(
        RoomMembership,
        user=request.user,
        room_id=room_id
    )
    
    room_name = membership.room.name
    membership.delete()
    
    messages.success(request, f'You have left "{room_name}".')
    return redirect('chat:room_list')


@login_required
def public_rooms(request):
    """List public rooms available to join"""
    # Get rooms user is not a member of
    member_room_ids = RoomMembership.objects.filter(
        user=request.user
    ).values_list('room_id', flat=True)
    
    public_rooms = ChatRoom.objects.filter(
        room_type='public',
        is_active=True
    ).exclude(id__in=member_room_ids)
    
    return render(request, 'chat/public_rooms.html', {'rooms': public_rooms})


@login_required
def room_members(request, room_id):
    """Get room members (API)"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check membership
    if not RoomMembership.objects.filter(user=request.user, room=room).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    
    members = RoomMembership.objects.filter(room=room).select_related('user')
    
    data = [{
        'id': str(m.user.id),
        'username': m.user.username,
        'role': m.role,
        'public_key': m.user.public_key,
        'joined_at': m.joined_at.isoformat(),
    } for m in members]
    
    return JsonResponse({'members': data})
