import os
import time
import json
from datetime import datetime, timezone, timedelta

from celery import shared_task
'''
from celery import shared_task

👉 This makes a background task

Runs async (in background)
Doesn’t block user request
'''
from github import Github
'''
👉 GitHub API client
Used to fetch:

repos
commits
PRs
'''
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import google.generativeai as genai

from .models import DeveloperProfile

LOW_QUALITY_KEYWORDS = [
    "test", "update", "minor", "wip",
    "temp", "commit", "change", "edit", "misc"
]

def push_update(username, message, progress):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"evaluation_{username}",
        {"type": "evaluation_update",
         "message": message,
         "progress": progress}
    )

def run_anticheat(commits, repos):
    flags = []
    total_commits = 0
    low_quality_count = 0
    commit_times = []

    for commit in commits:
        msg = commit.commit.message.lower().strip()
        total_commits += 1
        commit_times.append(commit.commit.author.date)

        if any(word in msg for word in LOW_QUALITY_KEYWORDS):
            low_quality_count += 1

        if len(msg) < 4:
            low_quality_count += 1

    spam_ratio = low_quality_count / max(total_commits, 1)
    commits_per_day = total_commits / 30

    if spam_ratio > 0.6:
        flags.append("High ratio of low-quality commit messages")

    if commits_per_day > 50:
        flags.append(f"Unusually high commit rate: {commits_per_day:.0f}/day")

    if len(commit_times) >= 20:
        commit_times.sort()
        for i in range(len(commit_times) - 20):
            window = (commit_times[i+19] - commit_times[i]).total_seconds()
            if window < 3600:
                flags.append("Burst commits: 20+ commits within 1 hour")
                break

    for repo in repos:
        if repo.fork: continue
        try:
            commit_count = repo.get_commits().totalCount
            if commit_count > 500 and (repo.size or 0) < 100:
                flags.append(f"Suspicious repo '{repo.name}': {commit_count} commits but very small size")
        except: pass

    is_suspicious = len(flags) > 0
    return {
        "spam_ratio": round(spam_ratio, 2),
        "commits_per_day": round(commits_per_day, 2),
        "is_suspicious": is_suspicious,
        "cheat_flags": flags,
    }

def assign_badges(data):
    badges = []
    nc = data['notable_contributions']
    streak = data['streak']
    languages = data['languages']
    prs = data['prs_merged']
    stars = data['total_stars']

    merged_to_big = any(c['merged'] and c['stars'] >= 100000 for c in nc)
    merged_to_medium = any(c['merged'] and c['stars'] >= 10000 for c in nc)
    if merged_to_big: badges.append("🌍 Open Source Hero")
    elif merged_to_medium: badges.append("⚡ OSS Contributor")
    if len(nc) >= 5: badges.append("🔧 Community Builder")

    if streak >= 365: badges.append("🔥 Year-Long Streak")
    elif streak >= 30: badges.append("⚡ 30-Day Streak")
    elif streak >= 7: badges.append("✅ Weekly Coder")

    if len(languages) >= 5: badges.append("🌐 Polyglot Developer")
    if "Python" in languages and "JavaScript" in languages: badges.append("🐍 Full Stack Capable")

    if stars >= 1000: badges.append("⭐ Star Developer")
    elif stars >= 100: badges.append("💫 Rising Star")

    if prs >= 50: badges.append("🔀 PR Machine")

    return badges

def build_commit_map(repos, github_user):
    commit_map = {}
    since = datetime.now(timezone.utc) - timedelta(days=365)
    for repo in repos:
        if repo.fork: continue
        try:
            commits = repo.get_commits(author=github_user, since=since)
            for commit in commits:
                date_str = commit.commit.author.date.strftime('%Y-%m-%d')
                commit_map[date_str] = commit_map.get(date_str, 0) + 1
        except: pass
    return commit_map

@shared_task
def evaluate_github_profile(user_id):
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(id=user_id)
        profile = DeveloperProfile.objects.get(user=user)

        social = user.socialaccount_set.get(provider='github')
        if social.socialtoken_set.exists():
            token = social.socialtoken_set.first().token
            g = Github(token)
            github_user = g.get_user()
            username = github_user.login
        else:
            # Fallback for older logins where SOCIALACCOUNT_STORE_TOKENS was False
            g = Github()
            username = social.extra_data.get('login')
            if not username:
                raise Exception("Missing GitHub login in extra_data")
            github_user = g.get_user(username)
    except Exception as e:
        print(f"Task Boot Error: {e}")
        return

    try:
        profile.evaluation_status = 'fetching'
        profile.save()
        push_update(username, "📦 Fetching your repositories...", 10)

        repos = list(github_user.get_repos())
        non_forked = [r for r in repos if not r.fork]

        total_stars = sum(r.stargazers_count for r in non_forked)
        languages = {}
        readme_count = 0

        for repo in non_forked:
            if repo.language:
                languages[repo.language] = languages.get(repo.language, 0) + (repo.size or 0)
            try:
                repo.get_readme()
                readme_count += 1
            except: pass

        push_update(username, "📊 Analyzing commit history...", 25)

        all_commits = []
        recent_commits_count = 0
        prs_merged = 0
        total_commits_count = 0

        for repo in non_forked:
            try:
                time.sleep(0.05) # Safe rate limiting as requested
                paginated_commits = repo.get_commits(author=github_user)
                try: total_commits_count += paginated_commits.totalCount
                except: pass

                commits = list(paginated_commits[:100])
                all_commits.extend(commits)
                for c in commits:
                    days_ago = (datetime.now(timezone.utc) - c.commit.author.date).days
                    if days_ago <= 30:
                        recent_commits_count += 1
            except: pass

        commit_dates = sorted(set(c.commit.author.date.date() for c in all_commits), reverse=True)
        streak = 0
        for i, date in enumerate(commit_dates):
            if i == 0: streak = 1
            else:
                if (commit_dates[i-1] - date).days == 1: streak += 1
                else: break

        push_update(username, "🔍 Running anti-cheat checks...", 40)

        cheat_result = run_anticheat(all_commits, non_forked)
        profile.spam_ratio      = cheat_result['spam_ratio']
        profile.commits_per_day = cheat_result['commits_per_day']
        profile.is_suspicious   = cheat_result['is_suspicious']
        profile.cheat_flags     = cheat_result['cheat_flags']
        profile.save()

        push_update(username, "🌍 Checking OSS contributions...", 55)

        notable_contributions = []
        try:
            query = f"author:{username} is:pr is:merged"
            prs = g.search_issues(query=query)
            
            try:
                prs_merged = prs.totalCount
            except:
                pass
            
            for pr in prs[:30]:  # Limit deep inspection to recent 30 to save rate limits
                try:
                    repo = g.get_repo(pr.repository.full_name)
                    stars = repo.stargazers_count
                    if stars >= 10:
                        notable_contributions.append({"repo": pr.repository.full_name, "stars": stars, "merged": True})
                except Exception:
                    pass
        except Exception:
            pass

        push_update(username, "🗓️ Building activity heatmap...", 65)

        commit_map = build_commit_map(non_forked, github_user)

        recent_repos = sorted(non_forked, key=lambda x: x.pushed_at or x.updated_at or x.created_at, reverse=True)[:5]
        recent_projects = [{"name": r.name, "url": r.html_url, "stars": r.stargazers_count, "description": r.description} for r in recent_repos]

        badge_data = {
            "notable_contributions": notable_contributions,
            "streak": streak,
            "languages": languages,
            "prs_merged": prs_merged,
            "total_stars": total_stars,
        }
        badges = assign_badges(badge_data)

        account_age_months = (datetime.now(timezone.utc) - github_user.created_at).days // 30
        profile.total_repos           = len(repos)
        profile.total_commits         = total_commits_count
        profile.total_stars_received  = total_stars
        profile.languages_used        = languages
        profile.notable_contributions = notable_contributions
        profile.recent_projects       = recent_projects
        profile.total_prs_merged      = prs_merged
        profile.commit_streak         = streak
        profile.account_age_months    = account_age_months
        profile.commit_map            = commit_map
        profile.badges                = badges
        profile.save()

        push_update(username, "🤖 Running AI analysis...", 75)

        profile.evaluation_status = 'analyzing'
        profile.save()

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        prompt = f"""
You are a developer skill evaluator. Score this GitHub profile.

Data:
- Non-forked repos: {len(non_forked)}
- Languages (name: KB): {json.dumps(languages)}
- Recent commits (30 days): {recent_commits_count}
- Commit streak: {streak} days
- README presence: {readme_count}/{len(non_forked)} repos
- Stars received: {total_stars}
- Account age: {account_age_months} months
- OSS contributions: {json.dumps(notable_contributions)}
- Spam ratio: {cheat_result['spam_ratio']} 
  (0=clean, 1=all spam — penalize heavily if above 0.6)
- Suspicious flags: {json.dumps(cheat_result['cheat_flags'])}

Rules:
- Merged PR to 10k+ star repo → massive OSS score boost
- spam_ratio > 0.6 → reduce consistency_score heavily
- Return ONLY valid JSON.
- CRITICAL: NO trailing commas allowed. All property names must be in double quotes.

{{
  "overall_score": 0-100,
  "rank_title": "Beginner/Intermediate/Advanced/Expert",
  "consistency_score": 0-100,
  "complexity_score": 0-100,
  "collaboration_score": 0-100,
  "diversity_score": 0-100,
  "documentation_score": 0-100,
  "oss_contribution_score": 0-100,
  "top_strength": "short phrase",
  "top_weakness": "short phrase",
  "summary": "2 sentences"
}}
"""
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        text = response.text.strip()
        if text.startswith('```json'): text = text[7:]
        elif text.startswith('```'): text = text[3:]
        if text.endswith('```'): text = text[:-3]
        
        try:
            result = json.loads(text.strip())
        except json.JSONDecodeError as err:
            print("AI Output was:", text)
            raise Exception(f"AI returned invalid JSON: {err}")

        profile.overall_score         = result.get('overall_score', 0)
        profile.rank_title            = result.get('rank_title', 'Unranked')
        profile.consistency_score     = result.get('consistency_score', 0)
        profile.complexity_score      = result.get('complexity_score', 0)
        profile.collaboration_score   = result.get('collaboration_score', 0)
        profile.diversity_score       = result.get('diversity_score', 0)
        profile.documentation_score   = result.get('documentation_score', 0)
        profile.oss_contribution_score= result.get('oss_contribution_score', 0)
        profile.top_strength          = result.get('top_strength', '')
        profile.top_weakness          = result.get('top_weakness', '')
        profile.summary               = result.get('summary', '')
        profile.evaluation_status     = 'complete'
        profile.last_evaluated        = datetime.now(timezone.utc)
        profile.save()

        push_update(username, "🏆 Calculating your rank...", 90)

        update_all_ranks()

        push_update(username, "✅ Analysis complete!", 100)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "leaderboard", {"type": "leaderboard_update"}
        )

    except Exception as e:
        profile.evaluation_status = 'failed'
        profile.save()
        push_update(username, f"❌ Error: {str(e)}", -1)
        print("CELERY TASK EXCEPTION:", e)

def update_all_ranks():
    global_profiles = DeveloperProfile.objects.filter(evaluation_status='complete').order_by('-overall_score')
    for i, p in enumerate(global_profiles, start=1):
        p.global_rank = i
        p.save(update_fields=['global_rank'])

    colleges = DeveloperProfile.objects.filter(evaluation_status='complete').values_list('college_name', flat=True).distinct()
    for college in colleges:
        campus_profiles = DeveloperProfile.objects.filter(evaluation_status='complete', college_name=college).order_by('-overall_score')
        for i, p in enumerate(campus_profiles, start=1):
            p.campus_rank = i
            p.save(update_fields=['campus_rank'])
