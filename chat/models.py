"""
Chat Models - Secure Chat Room System
All messages are stored encrypted (E2EE)
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatRoom(models.Model):
    """
    Represents a secure chat room
    Room keys are encrypted and stored per-user
    """
    
    ROOM_TYPES = (
        ('public', 'Public Room'),
        ('private', 'Private Room'),
        ('direct', 'Direct Message'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='private')
    
    # Encrypted room key (encrypted with server master key)
    encrypted_room_key = models.TextField()
    key_version = models.PositiveIntegerField(default=1)
    key_id = models.CharField(max_length=64, unique=True)
    
    # Room metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_rooms'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Security settings
    max_members = models.PositiveIntegerField(default=100)
    message_retention_days = models.PositiveIntegerField(default=30)  # 0 = forever
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
    
    def __str__(self):
        return f"{self.name} ({self.room_type})"


class RoomMembership(models.Model):
    """
    User membership in a chat room
    Contains user-specific encrypted room key
    """
    
    ROLES = (
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_memberships'
    )
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    
    # User-specific encrypted room key (encrypted with user's public key)
    encrypted_room_key_for_user = models.TextField()
    
    role = models.CharField(max_length=20, choices=ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(default=timezone.now)
    is_muted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'room')
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class EncryptedMessage(models.Model):
    """
    End-to-End encrypted message
    Server cannot read message content
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
    
    # Encrypted content (ciphertext + nonce combined)
    encrypted_content = models.TextField()
    
    # Sender's public key for this message (for verification)
    sender_public_key = models.CharField(max_length=64)
    
    # Message metadata (not encrypted)
    message_type = models.CharField(max_length=20, default='text')  # text, image, file
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # For message integrity
    content_hash = models.CharField(max_length=64)  # SHA3-256 of plaintext
    
    # Editing/deletion
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['room', 'timestamp']),
            models.Index(fields=['sender', 'timestamp']),
        ]
    
    def __str__(self):
        sender_name = self.sender.username if self.sender else 'Deleted User'
        return f"Message by {sender_name} at {self.timestamp}"
    
    def soft_delete(self):
        """Soft delete the message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.encrypted_content = ''  # Clear encrypted content
        self.save()


class MessageReadReceipt(models.Model):
    """
    Track message read status
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        EncryptedMessage,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')


class UserPresence(models.Model):
    """
    Track user online status
    """
    
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('away', 'Away'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='presence'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(default=timezone.now)
    current_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"{self.user.username}: {self.status}"
    
    def update_status(self, status: str, room=None):
        self.status = status
        self.last_seen = timezone.now()
        self.current_room = room
        self.save()
