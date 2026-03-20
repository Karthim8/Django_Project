from django.shortcuts import render, redirect
import urllib.request
import json
import boto3
import uuid
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Resource, Tag, Conversation, Message, StudyRoom, RoomMembership


def index(request):
    return render(request, "index.html")

@login_required
def chat_view(request):
    # Fetch user's conversations and pre-compute other_user for each
    convs_qs = Conversation.objects.filter(
        Q(user_a=request.user) | Q(user_b=request.user)
    ).order_by('-updated_at').select_related('user_a', 'user_b').prefetch_related('messages')

    # Attach other_user attribute so the template can use {{ conv.other }}
    conversations = []
    for conv in convs_qs:
        conv.other = conv.user_b if conv.user_a == request.user else conv.user_a
        conversations.append(conv)

    # Study rooms this user is a member of
    my_rooms = StudyRoom.objects.filter(
        memberships__user=request.user, is_active=True
    ).distinct()

    return render(request, "chat.html", {
        "conversations": conversations,
        "my_rooms": my_rooms,
    })

@login_required
def rooms_view(request):
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name')
            subject = request.POST.get('subject')
            desc = request.POST.get('description', '')
            pw = request.POST.get('password', '')
            
            if name and subject:
                room = StudyRoom.objects.create(
                    name=name,
                    subject=subject,
                    description=desc,
                    password_hash=pw, # in prod, actually hash it
                    host=request.user
                )
                RoomMembership.objects.create(room=room, user=request.user)
                return redirect('rooms')
        elif action == 'join':
            room_id = request.POST.get('room_id')
            pw = request.POST.get('password', '')
            try:
                room = StudyRoom.objects.get(id=room_id)
                if room.password_hash and room.password_hash != pw:
                    messages.error(request, "Incorrect password.")
                else:
                    RoomMembership.objects.get_or_create(room=room, user=request.user)
                    messages.success(request, f"Joined {room.name}!")
            except StudyRoom.DoesNotExist:
                pass
            return redirect('rooms')

    all_rooms = StudyRoom.objects.filter(is_active=True).order_by('-created_at')
    my_room_ids = list(RoomMembership.objects.filter(user=request.user).values_list('room_id', flat=True))
    
    return render(request, "rooms.html", {
        "all_rooms": all_rooms,
        "my_room_ids": my_room_ids
    })

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
    if request.method == "POST" and request.user.is_authenticated:
        uploaded_file = request.FILES.get('resource_file')
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        semester = request.POST.get('semester')
        
        if uploaded_file and title and subject:
            ext = uploaded_file.name.split('.')[-1]
            s3_key = f"resources/{uuid.uuid4().hex}.{ext}"
            
            from botocore.client import Config
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
            )
            
            try:
                s3_client.upload_fileobj(
                    uploaded_file,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={'ContentType': uploaded_file.content_type}
                )
                
                # Construct the S3 URL
                file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
                
                sem_val = None
                if semester and "Year" in semester:
                    # Extracts number from "1st Year", "2nd Year" if they match semester logical names (or just keep 1-4 for now)
                    # The models expecting choices 1-8. Let's map "1st Year" -> 1 (or 1st sem)
                    digits = [int(s) for s in semester if s.isdigit()]
                    if digits: sem_val = digits[0]
                elif semester and semester.isdigit():
                    sem_val = int(semester)
                
                resource = Resource.objects.create(
                    title=title,
                    file_url=file_url,
                    subject=subject,
                    semester=sem_val,
                    uploader=request.user
                )

                messages.success(request, "Resource uploaded successfully to AWS S3!")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Failed to upload to S3: {e}")
        else:
            messages.error(request, "File, title, and subject are required.")
            
        return redirect('resources')

    resources_list = list(Resource.objects.all().order_by('-upload_date'))
    
    # Generate presigned URLs for each resource
    from botocore.client import Config
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
    )
    bucket_url_prefix = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/"
    
    for res in resources_list:
        if res.file_url and res.file_url.startswith(bucket_url_prefix):
            try:
                s3_key = res.file_url[len(bucket_url_prefix):]
                res.presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=3600 # 1 hour
                )
            except Exception:
                res.presigned_url = res.file_url
        else:
            res.presigned_url = res.file_url
            
    return render(request, "resources.html", {"resources": resources_list})

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
