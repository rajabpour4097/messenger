"""
Secure User Model with E2E Encryption Key Storage
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class SecureUser(AbstractUser):
    """
    Custom User model with encryption key storage
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User's encrypted private key (encrypted with password-derived key)
    encrypted_private_key = models.TextField(blank=True)
    
    # User's public key (can be shared)
    public_key = models.CharField(max_length=64, blank=True)
    
    # Key metadata
    key_version = models.PositiveIntegerField(default=1)
    keys_generated_at = models.DateTimeField(null=True, blank=True)
    
    # Security fields
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Two-factor authentication
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    
    # Profile
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    class Meta:
        verbose_name = 'Secure User'
        verbose_name_plural = 'Secure Users'
    
    def __str__(self):
        return self.username
    
    def record_failed_login(self):
        """Record a failed login attempt"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.is_locked = True
            # Lock for 30 minutes
            from datetime import timedelta
            self.locked_until = timezone.now() + timedelta(minutes=30)
        
        self.save()
    
    def reset_failed_logins(self):
        """Reset failed login counter on successful login"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.is_locked = False
        self.locked_until = None
        self.save()
    
    def check_locked(self):
        """Check if account is locked and unlock if time has passed"""
        if self.is_locked and self.locked_until:
            if timezone.now() > self.locked_until:
                self.reset_failed_logins()
                return False
            return True
        return False


class UserSession(models.Model):
    """
    Track user sessions for security
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        SecureUser,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    session_key = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"


class SecurityAuditLog(models.Model):
    """
    Audit log for security events
    """
    
    EVENT_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed_login', 'Failed Login'),
        ('password_change', 'Password Change'),
        ('key_rotation', 'Key Rotation'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        SecureUser,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} at {self.timestamp}"
