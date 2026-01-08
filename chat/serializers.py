"""
Chat Serializers
"""

from rest_framework import serializers
from .models import ChatRoom, EncryptedMessage, RoomMembership


class RoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'description', 'room_type', 'created_at', 'member_count']
    
    def get_member_count(self, obj):
        return obj.memberships.count()


class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_id = serializers.UUIDField(source='sender.id', read_only=True)
    
    class Meta:
        model = EncryptedMessage
        fields = [
            'id', 'encrypted_content', 'sender_public_key',
            'message_type', 'timestamp', 'content_hash',
            'sender_id', 'sender_username', 'is_edited'
        ]


class MembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    public_key = serializers.CharField(source='user.public_key', read_only=True)
    
    class Meta:
        model = RoomMembership
        fields = ['user', 'username', 'role', 'joined_at', 'public_key']
