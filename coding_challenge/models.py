from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()   # works with both default AND custom User model

class Problem(models.Model):
    title       = models.CharField(max_length=200)
    description = models.TextField()
    test_cases  = models.JSONField()
    # test_cases format: [{"input": "5", "expected": "10"}, ...]
    language_id = models.IntegerField(default=71)  # 71 = Python 3
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Submission(models.Model):
    STATUS = [
        ("pending",  "Pending"),
        ("accepted", "Accepted"),
        ("partial",  "Partial"),
        ("error",    "Error"),
    ]

    student      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cc_submissions")
    problem      = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    source_code  = models.TextField()
    status       = models.CharField(max_length=20, choices=STATUS, default="pending")
    error_message= models.TextField(blank=True, null=True)
    passed_cases = models.IntegerField(default=0)
    total_cases  = models.IntegerField(default=0)
    score        = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["problem", "-score", "submitted_at"]),
        ]

    def __str__(self):
        return f"{self.student.username} → {self.problem} [{self.status}]"