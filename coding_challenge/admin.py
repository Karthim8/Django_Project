from django.contrib import admin
from .models import Problem, Submission

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display  = ["title", "language_id", "created_at"]
    list_filter   = ["language_id"]

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display  = ["student", "problem", "status", "score", "passed_cases", "total_cases", "submitted_at"]
    list_filter   = ["status", "problem"]
    readonly_fields = ["submitted_at"]