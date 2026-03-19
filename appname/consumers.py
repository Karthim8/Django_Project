from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = "global_chat"

        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)

        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'chat_message',
                'message': data['message']
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))

class EvaluationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.room_name = f"evaluation_{self.username}"

        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def evaluation_update(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'progress': event['progress']
        }))

class LeaderboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "leaderboard"
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def leaderboard_update(self, event):
        from accounts.models import DeveloperProfile
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def get_leaderboard():
            profiles = DeveloperProfile.objects.filter(evaluation_status='complete').order_by('global_rank')[:50]
            return [{
                'global_rank': p.global_rank,
                'username': p.github_username,
                'overall_score': p.overall_score,
                'rank_title': p.rank_title,
                'badges': p.badges
            } for p in profiles]
            
        leaderboard = await get_leaderboard()
        await self.send(text_data=json.dumps({
            'leaderboard': leaderboard
        }))