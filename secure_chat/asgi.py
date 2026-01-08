"""
ASGI config for Secure Chat with WebSocket support
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_chat.settings')

django_asgi_app = get_asgi_application()

# Import after Django setup
from chat.middleware import JWTAuthMiddlewareStack
from chat import routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(routing.websocket_urlpatterns)
        )
    ),
})
