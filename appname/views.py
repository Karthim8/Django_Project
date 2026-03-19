from django.shortcuts import render
import urllib.request
import json

def index(request):
    return render(request, "index.html")

def chat_view(request):
    return render(request, "chat.html")


def rooms_view(request):
    return render(request, "rooms.html")

def connect_view(request):
    return render(request, "connect.html")

def profile_view(request):
    if request.method == "POST" and request.user.is_authenticated:
        full_name = request.POST.get("full_name")
        if full_name:
            parts = full_name.strip().split(" ", 1)
            request.user.first_name = parts[0]
            if len(parts) > 1:
                request.user.last_name = parts[1]
            else:
                request.user.last_name = ""
            request.user.save()
            
        from accounts.models import UserProfile, PlacementBadge
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.college = request.POST.get('college', profile.college)
        profile.branch = request.POST.get('branch', profile.branch)
        batch_year = request.POST.get('batch_year')
        if batch_year and batch_year.isdigit():
            profile.batch_year = int(batch_year)
        profile.github = request.POST.get('github', profile.github)
        profile.codeforces = request.POST.get('codeforces', profile.codeforces)
        profile.bio = request.POST.get('bio', profile.bio)
        
        skills_input = request.POST.get('skills')
        if skills_input is not None:
            profile.skills = [s.strip() for s in skills_input.split(',') if s.strip()]
        profile.save()
            
        company = request.POST.get('company')
        role = request.POST.get('role')
        if company or role:
            badge = request.user.placements.first()
            if not badge:
                badge = PlacementBadge(user=request.user, year=profile.batch_year if profile.batch_year else 2026)
            badge.company = company or badge.company
            badge.role = role or badge.role
            badge.save()

    github_repos = []
    github_repo_count = 0
    github_error = None
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.github:
            username = profile.github.strip()
            # Clean up url if pasted directly
            if 'github.com/' in username:
                username = username.split('github.com/')[-1].strip('/')
            if username:
                try:
                    import ssl
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    url = f"https://api.github.com/users/{username}/repos?per_page=100"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        data = json.loads(response.read().decode())
                        if isinstance(data, list):
                            github_repo_count = len(data)
                            sorted_repos = sorted(data, key=lambda r: r.get('stargazers_count', 0), reverse=True)
                            github_repos = sorted_repos[:4]
                        else:
                            github_error = data.get('message', 'Unknown API Response')
                except Exception as e:
                    print(f"GitHub API Error for {username}: {e}")
                    github_error = str(e)

    return render(request, "profile.html", {
        "github_repos": github_repos,
        "github_repo_count": github_repo_count,
        "github_error": github_error
    })

def resources_view(request):
    return render(request, "resources.html")

def dashboard_view(request):
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('account_login')
    
    from accounts.models import DeveloperProfile
    try:
        profile = request.user.developer_profile
    except DeveloperProfile.DoesNotExist:
        profile = None

    return render(request, "ranking_dashboard.html", {"profile": profile})
