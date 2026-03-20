import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db                import database_sync_to_async
from .views                     import get_leaderboard


class LeaderboardConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.problem_id = self.scope["url_route"]["kwargs"]["problem_id"]
        self.group_name = f"cc_leaderboard_{self.problem_id}"  # cc_ prefix

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Push current state immediately so table isn't empty on load
        data = await database_sync_to_async(get_leaderboard)(int(self.problem_id))
        await self.send(text_data=json.dumps(data))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def leaderboard_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))