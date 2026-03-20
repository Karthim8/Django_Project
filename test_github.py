# import time
# from github import Github

# # Initialize using your exact database token
# TOKEN = "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"
# g = Github(TOKEN)

# # 1. Grab Authentication Profile
# github_user = g.get_user()
# print(f"Logged in automatically as: {github_user.login}")

# # 2. Get Repositories
# all_repos = list(github_user.get_repos())
# non_forked = [r for r in all_repos if not r.fork]
# print(f"\nTotal Repositories Found: {len(all_repos)}")
# print(f"Original Non-Forked Repos to Scan: {len(non_forked)}")

# # 3. Compute Stars
# total_stars = sum(r.stargazers_count for r in non_forked)
# print(f"Total Stars Accumulated: {total_stars}")

# # 4. Count Commits across Repos
# total_commits = 0
# print("\nScanning repos for accurate commit counts...")
# for repo in non_forked:
#     try:
#         # Pacing to protect GitHub Rate Limits
#         time.sleep(0.05) 
        
#         # Pull actual header count dynamically
#         commits = repo.get_commits(author=github_user)
#         total_commits += commits.totalCount
#         print(f" - {repo.name}: {commits.totalCount} commits")
#     except Exception as e:
#         # Ignore empty repositories
#         pass

# print(f"\nTRUE TOTAL COMMITS IN GITHUB: {total_commits}")

# # 5. Extract Pull Requests / Contributions
# prs_merged = 0
# print("\nScanning Recent Noteworthy Events...")
# for event in github_user.get_events()[:100]:
#     if event.type == "PullRequestEvent":
#         try:
#             full_repo = g.get_repo(event.repo.name)
#             stars = full_repo.stargazers_count
#             merged = event.payload.get('pull_request', {}).get('merged', False)
            
#             if merged:
#                 prs_merged += 1
#                 if stars >= 10:
#                     print(f"🌟 Notable Contribution: '{event.repo.name}' (Stars: {stars})")
#         except:
#             pass

# print(f"\nTOTAL UPSTREAM PRS MERGED RECENTLY: {prs_merged}")


# from github import Github, Auth

# auth = Auth.Token("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")
# g = Github(auth=auth)

# github_user = g.get_user()

# query = f"author:{github_user.login} is:pr is:merged"

# prs = g.search_issues(query=query)

# prs_merged = 0

# print("\nScanning ALL merged PRs (global search)...")

# for pr in prs:
#     try:
#         repo = g.get_repo(pr.repository.full_name)
#         stars = repo.stargazers_count
        
#         prs_merged += 1
        
#         if stars >= 10:
#             print(f"🌟 Notable Contribution: {pr.repository.full_name} (Stars: {stars})")
#     except:
#         pass

# print(f"\nTOTAL MERGED PRs: {prs_merged}")



import time
from github import Github, Auth

# ⚠️ IMPORTANT: Use environment variable instead of hardcoding
# TOKEN = "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"
TOKEN = "gho_6nAUk25ypXlxwwXroygGfDlCLnv2IGC3TIufn"
# ✅ Modern authentication (no deprecation warning)
auth = Auth.Token(TOKEN)
g = Github(auth=auth)

# 1. Get User
github_user = g.get_user()
print(f"Logged in automatically as: {github_user.login}")

# 2. Get Repositories
all_repos = list(github_user.get_repos())
non_forked = [r for r in all_repos if not r.fork]

print(f"\nTotal Repositories Found: {len(all_repos)}")
print(f"Original Non-Forked Repos to Scan: {len(non_forked)}")

# 3. Total Stars
total_stars = sum(r.stargazers_count for r in non_forked)
print(f"Total Stars Accumulated: {total_stars}")

# 4. Total Commits
total_commits = 0
print("\nScanning repos for accurate commit counts...")

for repo in non_forked:
    try:
        time.sleep(0.05)  # prevent rate limit
        
        commits = repo.get_commits(author=github_user)
        count = commits.totalCount
        
        total_commits += count
        print(f" - {repo.name}: {count} commits")
        
    except Exception:
        pass

print(f"\nTRUE TOTAL COMMITS IN GITHUB: {total_commits}")

# ---------------------------------------------------
# 5. PR ANALYSIS (GLOBAL SEARCH - CORRECT WAY)
# ---------------------------------------------------

print("\nScanning ALL merged PRs (global search)...")

query = f"author:{github_user.login} is:pr is:merged"
prs = g.search_issues(query=query)

total_prs = 0
notable_prs = 0

for pr in prs:
    try:
        repo = g.get_repo(pr.repository.full_name)
        stars = repo.stargazers_count
        
        total_prs += 1
        
        # Highlight strong contributions
        if stars >= 10:
            notable_prs += 1
            print(f"🌟 Notable Contribution: {pr.repository.full_name} (⭐ {stars})")
    
    except Exception:
        pass

print(f"\nTOTAL MERGED PRs (GLOBAL): {total_prs}")
print(f"NOTABLE PRs (⭐ >=10): {notable_prs}")

# ---------------------------------------------------
# 6. OPTIONAL: RECENT ACTIVITY (for UI / timeline)
# ---------------------------------------------------

recent_prs = 0
print("\nScanning Recent Activity (last 100 events)...")

for event in github_user.get_events()[:100]:
    if event.type == "PullRequestEvent":
        merged = event.payload.get('pull_request', {}).get('merged', False)
        
        if merged:
            recent_prs += 1

print(f"RECENT MERGED PRs (last 100 events): {recent_prs}")