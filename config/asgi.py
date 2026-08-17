import os

# Must be set BEFORE importing Django apps/modules — config.routing imports
# home.consumers, which imports models that read AUTH_USER_MODEL at import
# time. Daphne boots the ASGI app directly (no manage.py), so this has to
# come first or the app crashes with ImproperlyConfigured.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application

# Calling get_asgi_application() runs django.setup() — the app registry must
# be ready before config.routing (which imports home.consumers → models) is
# imported below. Import order matters here.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from config.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
