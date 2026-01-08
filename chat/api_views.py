"""
Chat API Views
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import ChatRoom, RoomMembership, EncryptedMessage
from .serializers import RoomSerializer, MessageSerializer
from accounts.models import SecureUser


class RoomListAPI(generics.ListAPIView):
    """API to list user's rooms"""
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    
    def get_queryset(self):
        memberships = RoomMembership.objects.filter(
            user=self.request.user
        ).values_list('room_id', flat=True)
        
        return ChatRoom.objects.filter(id__in=memberships)


class MessageListAPI(generics.ListAPIView):
    """API to list room messages"""
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        room_id = self.kwargs['room_id']
        
        # Verify membership
        if not RoomMembership.objects.filter(
            user=self.request.user,
            room_id=room_id
        ).exists():
            return EncryptedMessage.objects.none()
        
        return EncryptedMessage.objects.filter(
            room_id=room_id,
            is_deleted=False
        ).order_by('-timestamp')[:100]


class UserPublicKeyAPI(APIView):
    """API to get a user's public key"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        user = get_object_or_404(SecureUser, id=user_id)
        
        return Response({
            'user_id': str(user.id),
            'username': user.username,
            'public_key': user.public_key,
            'key_version': user.key_version,
        })
