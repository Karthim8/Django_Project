from django.urls import re_path
from .consumers  import LeaderboardConsumer

# Named cc_websocket_urlpatterns so asgi.py can merge it cleanly
cc_websocket_urlpatterns = [
    re_path(r"^ws/cc/leaderboard/(?P<problem_id>\d+)/$", LeaderboardConsumer.as_asgi()),
]