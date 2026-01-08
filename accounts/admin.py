from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import SecureUser, UserSession, SecurityAuditLog


@admin.register(SecureUser)
class SecureUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_locked', 'two_factor_enabled', 'date_joined')
    list_filter = ('is_locked', 'two_factor_enabled', 'is_staff')
    search_fields = ('username', 'email')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Security', {
            'fields': ('is_locked', 'locked_until', 'failed_login_attempts', 'two_factor_enabled')
        }),
        ('Encryption', {
            'fields': ('public_key', 'key_version', 'keys_generated_at')
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'created_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'ip_address')


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'event_type', 'ip_address', 'user_agent', 'details', 'timestamp')
