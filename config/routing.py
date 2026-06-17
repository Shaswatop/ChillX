from django.urls import re_path
from home.consumers import MultiplayerConsumer

websocket_urlpatterns = [
    re_path(r'ws/multiplayer/(?P<room_code>\w+)/$', MultiplayerConsumer.as_asgi()),
]
