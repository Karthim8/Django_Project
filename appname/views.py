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
from .models import Resource, Tag, Conversation, Message, StudyRoom, RoomMembership, Follow, Announcement


def index(request):
    return render(request, "index.html")

@login_required
def chat_view(request):
    # Get IDs of users who have an accepted follow relationship with current user
    following_ids = Follow.objects.filter(follower=request.user, status='accepted').values_list('following_id', flat=True)
    follower_ids = Follow.objects.filter(following=request.user, status='accepted').values_list('follower_id', flat=True)
    connected_user_ids = set(list(following_ids) + list(follower_ids))

    # Fetch user's conversations and pre-compute other_user for each
    convs_qs = Conversation.objects.filter(
        (Q(user_a=request.user) & Q(user_b_id__in=connected_user_ids)) | 
        (Q(user_b=request.user) & Q(user_a_id__in=connected_user_ids))
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

@login_required
def connect_view(request):
    # Fetch all users except self
    users_qs = User.objects.exclude(id=request.user.id).select_related('profile').prefetch_related('placements')
    
    # Get current user's following list to show "Requested" or "Followed"
    following_status = {f.following_id: f.status for f in Follow.objects.filter(follower=request.user)}
    
    # Attach status to each user object for easy template access
    users = []
    for u in users_qs:
        u.f_status = following_status.get(u.id) # None, 'pending', or 'accepted'
        users.append(u)
    
    # Get pending requests for the current user (notification sidebar)
    pending_requests = Follow.objects.filter(following=request.user, status='pending').select_related('follower__profile')

    # Get network stats
    following_count = Follow.objects.filter(follower=request.user, status='accepted').count()
    followers_count = Follow.objects.filter(following=request.user, status='accepted').count()

    return render(request, "connect.html", {
        "users": users,
        "pending_requests": pending_requests,
        "following_count": following_count,
        "followers_count": followers_count,
    })

@login_required
def follow_action(request):
    if request.method == "POST":
        action = request.POST.get('action') # 'request', 'accept', 'decline'
        user_id = request.POST.get('user_id')
        
        if action == 'request':
            target_user = User.objects.get(id=user_id)
            
            # Use update_or_create to avoid IntegrityError if a rejected follow already exists
            follow_obj, created = Follow.objects.get_or_create(
                follower=request.user, 
                following=target_user,
                defaults={'status': 'pending'}
            )
            
            if not created and follow_obj.status in ['rejected', 'decline']:
                follow_obj.status = 'pending'
                follow_obj.save()

            if follow_obj.status == 'pending':
                # Broadcast real-time notification
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"notify_{target_user.id}",
                        {
                            "type": "notification_update",
                            "category": "follow",
                            "count_update": 1
                        }
                    )
                except Exception as e:
                    print(f"WebSocket notification failed: {e}")

                messages.success(request, f"Follow request sent to {target_user.username}!")
            else:
                messages.info(request, f"You are already connected with {target_user.username}.")
            
        elif action == 'accept':
            follow_req = Follow.objects.get(follower_id=user_id, following=request.user, status='pending')
            follow_req.status = 'accepted'
            follow_req.save()
            
            # Autocreate conversation if it doesn't exist
            # We ensure user_a has smaller ID for consistency
            u1_id, u2_id = (min(request.user.id, int(user_id)), max(request.user.id, int(user_id)))
            u1, u2 = User.objects.get(id=u1_id), User.objects.get(id=u2_id)
            Conversation.objects.get_or_create(user_a=u1, user_b=u2)
            
            messages.success(request, f"You are now connected with {follow_req.follower.username}!")
            
        elif action == 'decline':
            Follow.objects.filter(follower_id=user_id, following=request.user, status='pending').delete()
            messages.info(request, "Follow request declined.")
            
    return redirect('connect')
def get_github_stats(user):
    github_repos = []
    github_repo_count = 0
    github_error = None
    profile = getattr(user, 'profile', None)
    if profile and profile.github:
        username = profile.github.strip()
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
                github_error = str(e)
    return github_repos, github_repo_count, github_error

@login_required
def user_profile_view(request, user_id):
    target_user = User.objects.get(id=user_id)
    if target_user == request.user:
        return redirect('profile')

    is_connected = Follow.objects.filter(
        (Q(follower=request.user, following=target_user) | Q(follower=target_user, following=request.user)),
        status='accepted'
    ).exists()
    
    github_repos, github_repo_count, github_error = get_github_stats(target_user)

    return render(request, "profile.html", {
        "profile_user": target_user,
        "is_connected": is_connected,
        "is_own_profile": False,
        "github_repos": github_repos,
        "github_repo_count": github_repo_count,
        "github_error": github_error
    })

def profile_view(request):
    # This might be for the current user's profile
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

    github_repos, github_repo_count, github_error = get_github_stats(request.user)

    return render(request, "profile.html", {
        "profile_user": request.user,
        "is_own_profile": True,
        "github_repos": github_repos,
        "github_repo_count": github_repo_count,
        "github_error": github_error
    })

def resources_view(request):
    from botocore.client import Config
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
    )

    if request.method == "POST" and request.user.is_authenticated:
        uploaded_file = request.FILES.get('resource_file')
        title = request.POST.get('title')
        subject = request.POST.get('subject')
        semester = request.POST.get('semester')
        
        if uploaded_file and title and subject:
            ext = uploaded_file.name.split('.')[-1]
            s3_key = f"resources/{uuid.uuid4().hex}.{ext}"
            
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
                    digits = [int(s) for s in semester if s.isdigit()]
                    if digits: sem_val = digits[0]
                elif semester and semester.isdigit():
                    sem_val = int(semester)
                
                Resource.objects.create(
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

    # Sync with S3: Check for files in bucket that aren't in DB
    try:
        response = s3_client.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix='resources/')
        if 'Contents' in response:
            # Find a system user to act as uploader for synced files
            system_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            
            if system_user:
                for obj in response['Contents']:
                    s3_key = obj['Key']
                    if not s3_key or s3_key == 'resources/': continue
                    
                    # Check if this exact file exists in DB
                    file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
                    if not Resource.objects.filter(file_url=file_url).exists():
                        # Auto-create resource entry
                        filename = s3_key.split('/')[-1]
                        Resource.objects.create(
                            title=filename,
                            file_url=file_url,
                            subject="Uncategorized",
                            uploader=system_user,
                            description="Automatically synced from S3 storage."
                        )
    except Exception as e:
        print(f"S3 Sync Error: {e}")

    # Re-fetch the list after sync
    resources_list = list(Resource.objects.all().order_by('-upload_date'))
    bucket_url_prefix = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/"
    
    for res in resources_list:
        if res.file_url and res.file_url.startswith(bucket_url_prefix):
            try:
                s3_key = res.file_url[len(bucket_url_prefix):]
                filename = s3_key.split('/')[-1]
                res.presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 
                        'Key': s3_key,
                        'ResponseContentDisposition': f'attachment; filename="{filename}"'
                    },
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

    github_connected = request.user.socialaccount_set.filter(provider='github').exists()

    return render(request, "ranking_dashboard.html", {
        "profile": profile,
        "github_connected": github_connected
    })

# ──────────────────────────────────────────────
#  Announcements & Roles
# ──────────────────────────────────────────────
from accounts.models import UserProfile, DeveloperProfile

def announcements_view(request):
    is_authorized = False
    if request.user.is_authenticated:
        if request.user.email == settings.ADMIN_EMAIL or (hasattr(request.user, 'profile') and request.user.profile.is_club_secretary):
            is_authorized = True
    
    announcements = Announcement.objects.all().order_by('-is_pinned', '-created_at')
    return render(request, "announcements.html", {
        "announcements": announcements,
        "is_authorized": is_authorized,
        "is_super_admin": request.user.is_authenticated and request.user.email == settings.ADMIN_EMAIL
    })

@login_required
def create_announcement(request):
    is_super_admin = request.user.email == settings.ADMIN_EMAIL
    is_secretary = hasattr(request.user, 'profile') and request.user.profile.is_club_secretary
    
    if not (is_super_admin or is_secretary):
        messages.error(request, "You are not authorized to post announcements.")
        return redirect('announcements')

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        event_date = request.POST.get('event_date')
        image_file = request.FILES.get('image')
        is_pinned = request.POST.get('is_pinned') == 'on'
        event_type = request.POST.get('event_type', 'general')

        image_url = ""
        if image_file:
            from botocore.client import Config
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
            )
            ext = image_file.name.split('.')[-1]
            s3_key = f"announcements/{uuid.uuid4().hex}.{ext}"
            try:
                s3_client.upload_fileobj(image_file, settings.AWS_STORAGE_BUCKET_NAME, s3_key, ExtraArgs={'ContentType': image_file.content_type})
                image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            except Exception as e:
                messages.error(request, f"Image upload failed: {e}")

        Announcement.objects.create(
            title=title,
            description=description,
            image_url=image_url,
            event_type=event_type,
            event_date=event_date if event_date else None,
            author=request.user,
            is_pinned=is_pinned
        )
        messages.success(request, "Announcement posted successfully!")
    return redirect('announcements')

@login_required
def delete_announcement(request, pk):
    from django.shortcuts import get_object_or_404
    announcement = get_object_or_404(Announcement, pk=pk)
    is_super_admin = request.user.email == settings.ADMIN_EMAIL
    
    if announcement.author == request.user or is_super_admin:
        announcement.delete()
        messages.success(request, "Announcement deleted.")
    else:
        messages.error(request, "Not authorized.")
    return redirect('announcements')

@login_required
def manage_roles_view(request):
    if request.user.email != settings.ADMIN_EMAIL:
        messages.error(request, "Access denied.")
        return redirect('index')
    
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        action = request.POST.get('action') 
        target_user = User.objects.get(id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        
        if action == 'promote':
            profile.is_club_secretary = True
            messages.success(request, f"{target_user.username} promoted to Club Secretary.")
        else:
            profile.is_club_secretary = False
            messages.info(request, f"{target_user.username} demoted.")
        profile.save()
        return redirect('manage_roles')

    users = User.objects.all().select_related('profile').exclude(email=settings.ADMIN_EMAIL).order_by('username')
    return render(request, "manage_roles.html", {"users": users})
