from django.contrib import admin
from .models import (
    Follow, Conversation, Message,
    StudyRoom, RoomMembership, RoomMessage, PinnedMessage,
    Tag, Resource,
)

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display  = ('follower', 'following', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('follower__username', 'following__username')

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('user_a', 'user_b', 'created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation', 'timestamp', 'is_read')

@admin.register(StudyRoom)
class StudyRoomAdmin(admin.ModelAdmin):
    list_display  = ('name', 'subject', 'host', 'max_members', 'is_active', 'created_at')
    list_filter   = ('subject', 'is_active')
    search_fields = ('name', 'host__username')

@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'joined_at')

@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'timestamp')

@admin.register(PinnedMessage)
class PinnedMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'pinned_by', 'pinned_at')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display  = ('title', 'subject', 'uploader', 'downloads', 'upload_date')
    list_filter   = ('subject', 'semester')
    search_fields = ('title', 'uploader__username')
