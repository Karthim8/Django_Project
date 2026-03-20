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
    is_club_secretary = models.BooleanField(default=False)

    @property
    def is_super_admin(self):
        return self.user.email == 'karthikeyanspro@gmail.com'

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

class DeveloperProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='developer_profile')
    github_username = models.CharField(max_length=100)
    college_name = models.CharField(max_length=200, blank=True)

    # ── Raw GitHub Data ──────────────────────────────
    total_repos          = models.IntegerField(default=0)
    total_commits        = models.IntegerField(default=0)
    total_stars_received = models.IntegerField(default=0)
    total_prs_merged     = models.IntegerField(default=0)
    languages_used       = models.JSONField(default=dict)
    notable_contributions= models.JSONField(default=list)
    recent_projects      = models.JSONField(default=list)
    commit_streak        = models.IntegerField(default=0)
    account_age_months   = models.IntegerField(default=0)
    commit_map           = models.JSONField(default=dict)  # heatmap data

    # ── AI Scores (0–100) ────────────────────────────
    overall_score        = models.FloatField(default=0)
    consistency_score    = models.FloatField(default=0)
    complexity_score     = models.FloatField(default=0)
    collaboration_score  = models.FloatField(default=0)
    diversity_score      = models.FloatField(default=0)
    documentation_score  = models.FloatField(default=0)
    oss_contribution_score = models.FloatField(default=0)

    # ── Rank Info ────────────────────────────────────
    rank_title           = models.CharField(max_length=50, default='Unranked')
    global_rank          = models.IntegerField(default=0)
    campus_rank          = models.IntegerField(default=0)
    top_strength         = models.CharField(max_length=100, blank=True)
    top_weakness         = models.CharField(max_length=100, blank=True)
    summary              = models.TextField(blank=True)
    badges               = models.JSONField(default=list)

    # ── Anti-Cheat ───────────────────────────────────
    spam_ratio           = models.FloatField(default=0)
    commits_per_day      = models.FloatField(default=0)
    is_suspicious        = models.BooleanField(default=False)
    cheat_flags          = models.JSONField(default=list)

    # ── Status ───────────────────────────────────────
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('fetching',  'Fetching GitHub Data'),
        ('analyzing', 'Analyzing with AI'),
        ('complete',  'Complete'),
        ('failed',    'Failed'),
    ]
    evaluation_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    last_evaluated = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-overall_score']
