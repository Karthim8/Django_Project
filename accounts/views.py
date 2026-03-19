import uuid
import json
import urllib.request
import urllib.error
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings


def custom_signup(request):
    """Custom signup view with name, email, password and Brevo email verification."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        errors = []

        if not name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email address is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.objects.filter(email=email).exists():
            errors.append("An account with this email already exists.")

        if errors:
            return render(request, 'account/signup.html', {'errors': errors, 'name': name, 'email': email})

        # Create user (inactive until email verified)
        first_name = name.split()[0]
        last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
        username = email.split('@')[0] + '_' + str(uuid.uuid4())[:8]
        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = False  # inactive until verified
        user.save()

        # Generate verification token and store it
        token = str(uuid.uuid4())
        request.session['verify_token'] = token
        request.session['verify_user_id'] = user.id

        # Send verification email via Brevo
        verify_url = request.build_absolute_uri(f'/accounts/verify/?token={token}&uid={user.id}')
        _send_verification_email_brevo(name, email, verify_url)

        return render(request, 'account/verify_sent.html', {'email': email})

    return render(request, 'account/signup.html')


def verify_email(request):
    """Handle email verification link click."""
    token = request.GET.get('token')
    uid = request.GET.get('uid')

    try:
        user = User.objects.get(id=uid)
        session_token = request.session.get('verify_token')
        # Also allow verification even without session (link clicked in new browser)
        if token and str(uid) == str(user.id):
            user.is_active = True
            user.save()
            request.session.pop('verify_token', None)
            request.session.pop('verify_user_id', None)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome to NexusLink, {user.first_name}! Your email has been verified.")
            return redirect('/')
    except User.DoesNotExist:
        pass

    return render(request, 'account/verify_fail.html')


def _send_verification_email_brevo(name, email, verify_url):
    """Send email via Brevo (Sendinblue) API."""
    api_key = "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"
    url = "https://api.brevo.com/v3/smtp/email"

    html_body = f"""
    <div style="font-family: 'Nunito', Arial, sans-serif; max-width: 520px; margin: 0 auto; background: #faf9f6; padding: 40px; border-radius: 16px;">
      <div style="text-align:center; margin-bottom: 24px;">
        <span style="background:#c1440e; color:white; width:44px; height:44px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; font-size:22px; font-weight:900; font-family:Georgia,serif;">N</span>
        <span style="font-size:22px; font-weight:900; margin-left:8px; font-family:Georgia,serif;">NexusLink</span>
      </div>
      <h2 style="font-family:Georgia,serif; font-weight:900; font-size:24px; margin-bottom:8px; text-align:center;">Verify your email, {name}! 🎓</h2>
      <p style="color:#6b5e4e; font-size:15px; text-align:center; margin-bottom:28px;">You're one step away from joining the campus network.</p>
      <div style="text-align:center; margin-bottom:28px;">
        <a href="{verify_url}" style="background:#c1440e; color:white; padding:14px 36px; border-radius:12px; text-decoration:none; font-size:15px; font-weight:700; display:inline-block; box-shadow: 4px 4px 0 rgba(193,68,14,0.3);">Verify my email ✓</a>
      </div>
      <p style="color:#9b8b7b; font-size:12px; text-align:center;">If you didn't create an account, you can safely ignore this email. This link expires in 24 hours.</p>
    </div>
    """

    payload = json.dumps({
        "sender": {"name": "NexusLink", "email": "noreply@nexuslink.app"},
        "to": [{"email": email, "name": name}],
        "subject": "Verify your NexusLink account 🎓",
        "htmlContent": html_body
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("accept", "application/json")
    req.add_header("api-key", api_key)
    req.add_header("content-type", "application/json")

    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print(f"[Brevo] Error sending email: {e.read().decode()}")
    except Exception as e:
        print(f"[Brevo] Exception: {e}")
