from django.urls import path
from .views import problem_list, problem_detail, submit_code

app_name = "coding_challenge"

urlpatterns = [
    path("", problem_list, name="problem_list"),
    path("<int:problem_id>/",        problem_detail, name="problem_detail"),
    path("<int:problem_id>/submit/", submit_code,    name="submit_code"),
]
# Final URLs will be:
# GET  /contest/1/         → problem page
# POST /contest/1/submit/  → judge + broadcast