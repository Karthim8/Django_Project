from django.shortcuts import render

# Create your views here.
import json
from django.shortcuts               import render, get_object_or_404
from django.http                    import JsonResponse
from django.views.decorators.http   import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf   import csrf_exempt
from channels.layers                import get_channel_layer
from asgiref.sync                   import async_to_sync
from .models                        import Problem, Submission
from .judge0                        import judge_submission

channel_layer = get_channel_layer()


def get_leaderboard(problem_id: int) -> list:
    """Best submission per student — highest score, then earliest time."""
    from django.db.models import Max

    best_scores = (
        Submission.objects
        .filter(problem_id=problem_id)
        .values("student_id")
        .annotate(best=Max("score"))
    )

    rows = []
    for entry in best_scores:
        sub = (
            Submission.objects
            .filter(problem_id=problem_id, student_id=entry["student_id"], score=entry["best"])
            .order_by("submitted_at")
            .select_related("student")
            .first()
        )
        if sub:
            rows.append({
                "username":     sub.student.username,
                "score":        sub.score,
                "passed":       sub.passed_cases,
                "total":        sub.total_cases,
                "status":       sub.status,
                "submitted_at": sub.submitted_at.strftime("%H:%M:%S"),
            })

    rows.sort(key=lambda r: (-r["score"], r["submitted_at"]))
    return rows


def problem_list(request):
    problems = Problem.objects.all().order_by("-created_at")
    return render(request, "coding_challenge/problem_list.html", {"problems": problems})


def problem_detail(request, problem_id: int):
    problem = get_object_or_404(Problem, pk=problem_id)
    return render(request, "coding_challenge/problem_detail.html", {"problem": problem})


@csrf_exempt
@login_required
@require_POST
def submit_code(request, problem_id: int):
    problem = get_object_or_404(Problem, pk=problem_id)
    data    = json.loads(request.body)

    source_code = data.get("source_code", "").strip()
    if not source_code:
        return JsonResponse({"error": "Empty submission"}, status=400)

    # Save → judge → broadcast
    sub = Submission.objects.create(
        student=request.user,
        problem=problem,
        source_code=source_code,
    )
    language_id = data.get("language_id") or problem.language_id
    sub = judge_submission(sub, language_id)

    async_to_sync(channel_layer.group_send)(
        f"cc_leaderboard_{problem_id}",          # cc_ prefix avoids collision
        {
            "type": "leaderboard.update",
            "data": get_leaderboard(problem_id),
        },
    )

    return JsonResponse({
        "status": sub.status,
        "score":  sub.score,
        "passed": sub.passed_cases,
        "total":  sub.total_cases,
    })