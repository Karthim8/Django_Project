from django.urls import re_path
from .consumers import ChatConsumer, EvaluationConsumer, LeaderboardConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/$', ChatConsumer.as_asgi()),
    re_path(r'ws/evaluation/(?P<username>[\w-]+)/$', EvaluationConsumer.as_asgi()),
    re_path(r'ws/leaderboard/$', LeaderboardConsumer.as_asgi()),
]