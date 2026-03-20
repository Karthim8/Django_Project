from .models import Message, Follow
from django.db.models import Q

def notifications_count(request):
    if not request.user.is_authenticated:
        return {}
    
    # 1. Unread DMs
    # Messages in any conversation the user is part of, sender is NOT user, and is_read is False
    unread_messages = Message.objects.filter(
        (Q(conversation__user_a=request.user) | Q(conversation__user_b=request.user)),
        is_read=False
    ).exclude(sender=request.user).count()

    # 2. Pending follow requests
    pending_follows = Follow.objects.filter(
        following=request.user,
        status='pending'
    ).count()

    return {
        'unread_messages_count': unread_messages,
        'pending_follow_count': pending_follows,
        'total_notifications': unread_messages + pending_follows
    }
