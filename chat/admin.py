from django.contrib import admin
from .models import ChatRoom, RoomMembership, EncryptedMessage, UserPresence


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'created_by', 'created_at', 'is_active')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'key_id', 'created_at', 'updated_at')


@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'room__name')


@admin.register(EncryptedMessage)
class EncryptedMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'message_type', 'timestamp', 'is_deleted')
    list_filter = ('message_type', 'is_deleted', 'timestamp')
    search_fields = ('sender__username', 'room__name')
    readonly_fields = ('id', 'encrypted_content', 'content_hash', 'timestamp')


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'last_seen', 'current_room')
    list_filter = ('status',)
    search_fields = ('user__username',)
