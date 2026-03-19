from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [('student', 'Student'), ('senior', 'Senior'), ('alumni', 'Alumni')]

    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    bio          = models.TextField(blank=True)
    college      = models.CharField(max_length=200, blank=True)
    branch       = models.CharField(max_length=100, blank=True)
    batch_year   = models.PositiveSmallIntegerField(null=True, blank=True)
    semester     = models.PositiveSmallIntegerField(null=True, blank=True)
    avatar_url   = models.URLField(blank=True)
    github       = models.CharField(max_length=100, blank=True)
    codeforces   = models.CharField(max_length=100, blank=True)
    linkedin     = models.URLField(blank=True)
    skills       = models.JSONField(default=list, blank=True)   # ["Python","Django",...]
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"


class PlacementBadge(models.Model):
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='placements')
    company  = models.CharField(max_length=150)
    role     = models.CharField(max_length=150)
    package  = models.CharField(max_length=50, blank=True)   # e.g. "24 LPA"
    year     = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.user.username} → {self.company}"


class EmailVerification(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verifications')
    token      = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Verification({self.user.email} - {'✓' if self.is_verified else '✗'})"
