import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, PlacementBadge, EmailVerification

users_data = [
    {
        'first_name': 'Anjali', 'last_name': 'Kumar',
        'email': 'anjali@example.com', 'username': 'anjali_kumar',
        'role': 'senior', 'company': 'Google', 'job_role': 'Software Engineer',
    },
    {
        'first_name': 'Mohammed', 'last_name': 'Saleem',
        'email': 'saleem@example.com', 'username': 'mohammed_saleem',
        'role': 'senior', 'company': 'Amazon', 'job_role': 'Software Engineer',
    },
    {
        'first_name': 'Priya', 'last_name': 'Venkat',
        'email': 'priya@example.com', 'username': 'priya_venkat',
        'role': 'student', 'company': None, 'job_role': None,
    },
]

for data in users_data:
    user, created = User.objects.get_or_create(
        username=data['username'],
        defaults={
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
        }
    )
    if created:
        user.set_password('nexus123')
        user.save()
        print(f"[CREATED] {user.get_full_name()} | {user.email}")
    else:
        print(f"[EXISTS]  {user.get_full_name()} | {user.email}")

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = data['role']
    profile.save()
    print(f"         role = {data['role']}")

    if data['company']:
        badge, b_created = PlacementBadge.objects.get_or_create(
            user=user, company=data['company'],
            defaults={'role': data['job_role'], 'year': 2024}
        )
        if b_created:
            print(f"         badge -> {data['company']}")

    ev, ev_created = EmailVerification.objects.get_or_create(
        user=user,
        defaults={'token': f"test_token_{user.username}", 'is_verified': True}
    )
    ev.is_verified = True
    ev.save()
    print(f"         email verified = True")

print("\nAll done!")
