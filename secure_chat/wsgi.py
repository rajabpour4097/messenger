"""WSGI config for Secure Chat"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'secure_chat.settings')

application = get_wsgi_application()
