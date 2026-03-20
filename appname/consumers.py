from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """Real-time DM consumer for a specific conversation."""

    async def connect(self):
        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.room_group_name = f"chat_{self.conv_id}"
        user = self.scope['user']

        # Verify user is part of this conversation
        if not user.is_authenticated:
            await self.close()
            return

        allowed = await self.user_in_conversation(user, self.conv_id)
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 1. Mark as read
        await self.mark_messages_as_read(user, self.conv_id)

        # 2. Send history
        history = await self.get_chat_history(self.conv_id)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('message', '').strip()
        if not content:
            return
        user = self.scope['user']
        msg = await self.save_message(user, self.conv_id, content)
        # Broadcast to conversation group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': content,
                'sender': user.get_full_name() or user.username,
                'sender_id': user.id,
                'initials': (user.first_name[:1] + user.last_name[:1]).upper() or user.username[:2].upper(),
                'timestamp': msg.timestamp.strftime('%I:%M %p'),
            }
        )

        # Broadcast notification to recipient
        recipient = await self.get_recipient(user, self.conv_id)
        if recipient:
            recipient_group = f"notify_{recipient.id}"
            await self.channel_layer.group_send(
                recipient_group,
                {
                    'type': 'notification_update',
                    'category': 'message',
                    'count_update': 1
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def user_in_conversation(self, user, conv_id):
        from .models import Conversation
        return Conversation.objects.filter(
            id=conv_id
        ).filter(
            __import__('django.db.models', fromlist=['Q']).Q(user_a=user) |
            __import__('django.db.models', fromlist=['Q']).Q(user_b=user)
        ).exists()

    @database_sync_to_async
    def get_chat_history(self, conv_id):
        from .models import Message
        msgs = Message.objects.filter(conversation_id=conv_id).order_by('timestamp')[:50]
        return [{
            'message': m.content,
            'sender': m.sender.get_full_name() or m.sender.username,
            'sender_id': m.sender.id,
            'initials': (m.sender.first_name[:1] + m.sender.last_name[:1]).upper() or m.sender.username[:2].upper(),
            'timestamp': m.timestamp.strftime('%I:%M %p'),
        } for m in msgs]

    @database_sync_to_async
    def mark_messages_as_read(self, user, conv_id):
        from .models import Message
        Message.objects.filter(conversation_id=conv_id).exclude(sender=user).update(is_read=True)

    @database_sync_to_async
    def get_recipient(self, user, conv_id):
        from .models import Conversation
        conv = Conversation.objects.get(id=conv_id)
        return conv.user_b if conv.user_a == user else conv.user_a

    @database_sync_to_async
    def save_message(self, user, conv_id, content):
        from .models import Conversation, Message
        conv = Conversation.objects.get(id=conv_id)
        msg = Message.objects.create(conversation=conv, sender=user, content=content)
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        return msg


class RoomConsumer(AsyncWebsocketConsumer):
    """Real-time chat consumer for a study room."""

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"
        user = self.scope['user']

        if not user.is_authenticated:
            await self.close()
            return

        # Auto-join membership if not already present
        await self.ensure_membership(user, self.room_id)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Send room history
        history = await self.get_room_history(self.room_id)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get('message', '').strip()
        if not content:
            return
        user = self.scope['user']
        msg = await self.save_room_message(user, self.room_id, content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'room_message',
                'message': content,
                'sender': user.get_full_name() or user.username,
                'sender_id': user.id,
                'initials': (user.first_name[:1] + user.last_name[:1]).upper() or user.username[:2].upper(),
                'timestamp': msg.timestamp.strftime('%I:%M %p'),
            }
        )

    async def room_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def ensure_membership(self, user, room_id):
        from .models import StudyRoom, RoomMembership
        try:
            room = StudyRoom.objects.get(id=room_id)
            RoomMembership.objects.get_or_create(room=room, user=user)
        except StudyRoom.DoesNotExist:
            pass

    @database_sync_to_async
    def get_room_history(self, room_id):
        from .models import RoomMessage
        msgs = RoomMessage.objects.filter(room_id=room_id).order_by('timestamp')[:50]
        return [{
            'message': m.content,
            'sender': m.sender.get_full_name() or m.sender.username,
            'sender_id': m.sender.id,
            'initials': (m.sender.first_name[:1] + m.sender.last_name[:1]).upper() or m.sender.username[:2].upper(),
            'timestamp': m.timestamp.strftime('%I:%M %p'),
        } for m in msgs]

    @database_sync_to_async
    def save_room_message(self, user, room_id, content):
        from .models import StudyRoom, RoomMessage
        room = StudyRoom.objects.get(id=room_id)
        return RoomMessage.objects.create(room=room, sender=user, content=content)


class EvaluationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.room_name = f"evaluation_{self.username}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def evaluation_update(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'progress': event['progress']
        }))


class LeaderboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "leaderboard"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def leaderboard_update(self, event):
        from accounts.models import DeveloperProfile
        from asgiref.sync import sync_to_async

        @sync_to_async
        def get_leaderboard():
            profiles = DeveloperProfile.objects.filter(evaluation_status='complete').order_by('global_rank')[:50]
            return [{'global_rank': p.global_rank, 'username': p.github_username,
                     'overall_score': p.overall_score, 'rank_title': p.rank_title, 'badges': p.badges}
                    for p in profiles]

        leaderboard = await get_leaderboard()
        await self.send(text_data=json.dumps({'leaderboard': leaderboard}))

class NotificationConsumer(AsyncWebsocketConsumer):
    """Global notification consumer for real-time badges (DMs, Follow Requests)."""

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return

        self.user_id = user.id
        self.group_name = f"notify_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_update(self, event):
        # Forward to WebSocket
        await self.send(text_data=json.dumps(event))