"""
WebSocket Consumers for Real-time Chat
Handles encrypted message transmission
"""

import json
import base64
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import ChatRoom, RoomMembership, EncryptedMessage, UserPresence


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat rooms
    All messages are encrypted client-side - server only relays
    """
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check authentication
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Check room membership
        is_member = await self.check_membership()
        if not is_member:
            await self.close(code=4003)
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update presence
        await self.update_presence('online')
        
        # Notify room of user joining
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'timestamp': timezone.now().isoformat(),
            }
        )
    
    async def disconnect(self, close_code):
        # Update presence
        await self.update_presence('offline')
        
        # Notify room of user leaving
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'key_exchange':
                await self.handle_key_exchange(data)
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            await self.send_error(str(e))
    
    async def handle_message(self, data):
        """Handle encrypted chat message"""
        # Extract encrypted content (server cannot read this)
        encrypted_content = data.get('encrypted_content')
        sender_public_key = data.get('sender_public_key')
        content_hash = data.get('content_hash')
        message_type = data.get('message_type', 'text')
        
        if not encrypted_content:
            await self.send_error('Missing encrypted content')
            return
        
        # Save encrypted message to database
        message = await self.save_message(
            encrypted_content=encrypted_content,
            sender_public_key=sender_public_key,
            content_hash=content_hash,
            message_type=message_type,
        )
        
        # Broadcast to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message.id),
                'encrypted_content': encrypted_content,
                'sender_public_key': sender_public_key,
                'content_hash': content_hash,
                'message_type': message_type,
                'sender_id': str(self.user.id),
                'sender_username': self.user.username,
                'timestamp': message.timestamp.isoformat(),
            }
        )
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', True)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )
    
    async def handle_read_receipt(self, data):
        """Handle read receipt"""
        message_id = data.get('message_id')
        
        await self.mark_message_read(message_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'message_id': message_id,
                'user_id': str(self.user.id),
                'read_at': timezone.now().isoformat(),
            }
        )
    
    async def handle_key_exchange(self, data):
        """Handle key exchange for E2E encryption"""
        # Forward public key to intended recipient
        recipient_id = data.get('recipient_id')
        public_key = data.get('public_key')
        
        if recipient_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'key_exchange_response',
                    'sender_id': str(self.user.id),
                    'recipient_id': recipient_id,
                    'public_key': public_key,
                }
            )
    
    # Message handlers for group_send
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'encrypted_content': event['encrypted_content'],
            'sender_public_key': event['sender_public_key'],
            'content_hash': event['content_hash'],
            'message_type': event['message_type'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'timestamp': event['timestamp'],
        }))
    
    async def user_join(self, event):
        """Notify when user joins"""
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))
    
    async def user_leave(self, event):
        """Notify when user leaves"""
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator"""
        # Don't send to the user who is typing
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))
    
    async def read_receipt(self, event):
        """Send read receipt"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'read_at': event['read_at'],
        }))
    
    async def key_exchange_response(self, event):
        """Forward key exchange to recipient"""
        if event['recipient_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'key_exchange',
                'sender_id': event['sender_id'],
                'public_key': event['public_key'],
            }))
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))
    
    # Database operations
    
    @database_sync_to_async
    def check_membership(self):
        """Check if user is a member of the room"""
        return RoomMembership.objects.filter(
            user=self.user,
            room_id=self.room_id,
        ).exists()
    
    @database_sync_to_async
    def save_message(self, encrypted_content, sender_public_key, content_hash, message_type):
        """Save encrypted message to database"""
        return EncryptedMessage.objects.create(
            room_id=self.room_id,
            sender=self.user,
            encrypted_content=encrypted_content,
            sender_public_key=sender_public_key or '',
            content_hash=content_hash or '',
            message_type=message_type,
        )
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        """Mark a message as read"""
        from .models import MessageReadReceipt
        
        MessageReadReceipt.objects.get_or_create(
            message_id=message_id,
            user=self.user,
        )
    
    @database_sync_to_async
    def update_presence(self, status):
        """Update user presence"""
        presence, _ = UserPresence.objects.get_or_create(user=self.user)
        room = ChatRoom.objects.filter(id=self.room_id).first() if status == 'online' else None
        presence.update_status(status, room)


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for global presence updates
    """
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        self.presence_group = 'presence_updates'
        
        await self.channel_layer.group_add(
            self.presence_group,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user presence
        await self.set_online()
        
        # Broadcast presence update
        await self.channel_layer.group_send(
            self.presence_group,
            {
                'type': 'presence_update',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'status': 'online',
            }
        )
    
    async def disconnect(self, close_code):
        await self.set_offline()
        
        await self.channel_layer.group_send(
            self.presence_group,
            {
                'type': 'presence_update',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'status': 'offline',
            }
        )
        
        await self.channel_layer.group_discard(
            self.presence_group,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle status updates"""
        try:
            data = json.loads(text_data)
            status = data.get('status', 'online')
            
            if status in ['online', 'away', 'busy']:
                await self.update_status(status)
                
                await self.channel_layer.group_send(
                    self.presence_group,
                    {
                        'type': 'presence_update',
                        'user_id': str(self.user.id),
                        'username': self.user.username,
                        'status': status,
                    }
                )
        except json.JSONDecodeError:
            pass
    
    async def presence_update(self, event):
        """Send presence update to client"""
        await self.send(text_data=json.dumps({
            'type': 'presence',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
        }))
    
    @database_sync_to_async
    def set_online(self):
        presence, _ = UserPresence.objects.get_or_create(user=self.user)
        presence.update_status('online')
    
    @database_sync_to_async
    def set_offline(self):
        presence, _ = UserPresence.objects.get_or_create(user=self.user)
        presence.update_status('offline')
    
    @database_sync_to_async
    def update_status(self, status):
        presence, _ = UserPresence.objects.get_or_create(user=self.user)
        presence.update_status(status)
