"""
Chat API URLs
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    # JWT Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Room APIs
    path('rooms/', api_views.RoomListAPI.as_view(), name='api_room_list'),
    path('rooms/<uuid:room_id>/messages/', api_views.MessageListAPI.as_view(), name='api_messages'),
    
    # User APIs
    path('users/<uuid:user_id>/public-key/', api_views.UserPublicKeyAPI.as_view(), name='api_public_key'),
]
