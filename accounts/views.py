import uuid
import json
import random
import urllib.request
import urllib.error
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings
import os


def custom_signup(request):
    """Custom signup view with name, email, password and Brevo email verification."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip() #removes spaces
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
        try:
            first_name = name.split()[0]
            last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            username = email.split('@')[0] + '_' + str(uuid.uuid4())[:8]
            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = False  # inactive until verified
            user.save()
        except Exception as e:
            print(f"Error creating user: {e}")
            errors.append("An error occurred while creating your account. Please try again.")
            return render(request, 'account/signup.html', {'errors': errors, 'name': name, 'email': email})

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        request.session['verify_email'] = email
        request.session['verify_user_id'] = user.id

        # Store OTP in Upstash Redis (valid for 5 mins / 300s)
        try:
            upstash_url = os.getenv('UPSTASH_REST_URL')
            upstash_token = os.getenv('UPSTASH_REST_TOKEN')
            # URL encode the email to handle special characters safely
            import urllib.parse
            safe_email = urllib.parse.quote(email)
            set_url = f"{upstash_url}/set/otp:{safe_email}/{otp}/EX/300"
            
            req = urllib.request.Request(set_url, headers={"Authorization": f"Bearer {upstash_token}"})
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[Upstash] Error setting OTP: {e}")
            # If Redis fails, we delete the created user so they can try again
            user.delete()
            errors.append("We're currently experiencing issues sending verification codes. Please try again later.")
            return render(request, 'account/signup.html', {'errors': errors, 'name': name, 'email': email})

        # Send OTP email via Brevo
        _send_verification_email_brevo(name, email, otp)

        return render(request, 'account/verify_sent.html', {'email': email})

    return render(request, 'account/signup.html')


def verify_otp(request):
    """Handle OTP submission."""
    if request.method == 'POST':
        submitted_otp = request.POST.get('otp', '').strip()
        email = request.session.get('verify_email')
        uid = request.session.get('verify_user_id')

        if not email or not uid:
            return redirect('custom_signup')

        # Check OTP in Upstash Redis
        upstash_url = os.getenv('UPSTASH_REST_URL')
        upstash_token = os.getenv('UPSTASH_REST_TOKEN')
        import urllib.parse
        safe_email = urllib.parse.quote(email)
        get_url = f"{upstash_url}/get/otp:{safe_email}"
        
        try:
            req = urllib.request.Request(get_url, headers={"Authorization": f"Bearer {upstash_token}"})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            stored_otp = data.get("result")
        except Exception as e:
            print(f"[Upstash] Error getting OTP: {e}")
            stored_otp = None

        if stored_otp and str(stored_otp) == str(submitted_otp):
            try:
                user = User.objects.get(id=uid)
                user.is_active = True
                user.save()
                
                # Cleanup Upstash
                try:
                    del_url = f"{upstash_url}/del/otp:{safe_email}"
                    del_req = urllib.request.Request(del_url, headers={"Authorization": f"Bearer {upstash_token}"})
                    urllib.request.urlopen(del_req, timeout=5)
                except Exception as e:
                    print(f"[Upstash] Error deleting OTP: {e}")
                    pass # Non-critical if deletion fails, it expires in 5m anyway

                request.session.pop('verify_email', None)
                request.session.pop('verify_user_id', None)

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"Welcome to NexusLink, {user.first_name}!")
                return redirect('/')
            except User.DoesNotExist:
                return render(request, 'account/verify_sent.html', {'email': email, 'error': "User not found."})
        else:
            return render(request, 'account/verify_sent.html', {'email': email, 'error': "Invalid or expired OTP."})

    # For GET request
    email = request.session.get('verify_email')
    if not email:
        return redirect('custom_signup')
    return render(request, 'account/verify_sent.html', {'email': email})


def _send_verification_email_brevo(name, email, otp):
    """Send email via Brevo (Sendinblue) API."""
    api_key = os.getenv('BREVO_API_KEY', '')
    url = "https://api.brevo.com/v3/smtp/email"

    html_body = f"""
    <div style="font-family: 'Nunito', Arial, sans-serif; max-width: 520px; margin: 0 auto; background: #faf9f6; padding: 40px; border-radius: 16px;">
      <div style="text-align:center; margin-bottom: 24px;">
        <span style="background:#c1440e; color:white; width:44px; height:44px; display:inline-flex; align-items:center; justify-content:center; border-radius:12px; font-size:22px; font-weight:900; font-family:Georgia,serif;">N</span>
        <span style="font-size:22px; font-weight:900; margin-left:8px; font-family:Georgia,serif;">NexusLink</span>
      </div>
      <h2 style="font-family:Georgia,serif; font-weight:900; font-size:24px; margin-bottom:8px; text-align:center;">Your Verification Code</h2>
      <p style="color:#6b5e4e; font-size:15px; text-align:center; margin-bottom:28px;">Use the following 6-digit code to verify your email, {name}:</p>
      <div style="text-align:center; margin-bottom:28px;">
        <div style="background:white; border:2px dashed #c1440e; color:#c1440e; padding:18px 36px; border-radius:12px; font-size:32px; font-weight:900; letter-spacing:8px; display:inline-block;">{otp}</div>
      </div>
      <p style="color:#9b8b7b; font-size:12px; text-align:center;">This code expires in 5 minutes. If you didn't create an account, you can safely ignore this email.</p>
    </div>
    """

    payload = json.dumps({
        "sender": {"name": getattr(settings, 'BREVO_SENDER_NAME', 'NexusLink'), "email": getattr(settings, 'BREVO_SENDER_EMAIL', '')},
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
