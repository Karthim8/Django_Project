from django.db import models
from django.contrib.auth.models import User


# ──────────────────────────────────────────────
#  Social Graph
# ──────────────────────────────────────────────
class Follow(models.Model):
    STATUS_CHOICES = [('pending','Pending'),('accepted','Accepted'),('rejected','Rejected')]
    follower   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.username} → {self.following.username} [{self.status}]"


# ──────────────────────────────────────────────
#  Private DMs
# ──────────────────────────────────────────────
class Conversation(models.Model):
    """A DM thread between exactly two users."""
    user_a     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_a')
    user_b     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_b')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user_a', 'user_b')

    def other_user(self, me):
        return self.user_b if self.user_a == me else self.user_a

    def __str__(self):
        return f"DM({self.user_a.username} ↔ {self.user_b.username})"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content      = models.TextField()
    file_url     = models.URLField(blank=True)
    is_read      = models.BooleanField(default=False)
    timestamp    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.timestamp:%H:%M}] {self.sender.username}: {self.content[:40]}"


# ──────────────────────────────────────────────
#  Study Server Rooms
# ──────────────────────────────────────────────
class StudyRoom(models.Model):
    name          = models.CharField(max_length=150)
    subject       = models.CharField(max_length=100)
    description   = models.TextField(blank=True)
    host          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    password_hash = models.CharField(max_length=128, blank=True)  # empty = open room
    max_members   = models.PositiveSmallIntegerField(default=20)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Room: {self.name} ({self.subject})"


class RoomMembership(models.Model):
    room      = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name='memberships')
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.room.name}"


class RoomMessage(models.Model):
    room      = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name='room_messages')
    sender    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_messages_sent')
    content   = models.TextField()
    file_url  = models.URLField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.room.name}] {self.sender.username}: {self.content[:40]}"


class PinnedMessage(models.Model):
    room      = models.OneToOneField(StudyRoom, on_delete=models.CASCADE, related_name='pinned')
    message   = models.ForeignKey(RoomMessage, on_delete=models.CASCADE)
    pinned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    pinned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pinned in {self.room.name}"


# ──────────────────────────────────────────────
#  Resources
# ──────────────────────────────────────────────
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Resource(models.Model):
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 9)]

    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file_url    = models.URLField()
    subject     = models.CharField(max_length=100)
    semester    = models.PositiveSmallIntegerField(choices=SEMESTER_CHOICES, null=True, blank=True)
    uploader    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resources')
    tags        = models.ManyToManyField(Tag, blank=True, related_name='resources')
    downloads   = models.PositiveIntegerField(default=0)
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.title} — {self.subject}"


# ──────────────────────────────────────────────
#  Announcements
# ──────────────────────────────────────────────
class Announcement(models.Model):
    EVENT_TYPE_CHOICES = [
        ('general',   'General'),
        ('hackathon', 'Hackathon'),
        ('workshop',  'Workshop'),
        ('seminar',   'Seminar'),
        ('placement', 'Placement Drive'),
    ]

    title       = models.CharField(max_length=200)
    description = models.TextField()
    image_url   = models.URLField(blank=True)
    event_type  = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='general')
    event_date  = models.DateTimeField(null=True, blank=True)
    author      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    is_pinned   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title
