from django.urls import re_path
from .consumers import ChatConsumer, RoomConsumer, EvaluationConsumer, LeaderboardConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conv_id>\d+)/$', ChatConsumer.as_asgi()),
    re_path(r'ws/room/(?P<room_id>\d+)/$', RoomConsumer.as_asgi()),
    re_path(r'ws/evaluation/(?P<username>[\w-]+)/$', EvaluationConsumer.as_asgi()),
    re_path(r'ws/leaderboard/$', LeaderboardConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]