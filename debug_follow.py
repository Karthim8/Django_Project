import sys
import os
import django

sys.stdout = open('debug_follow_output_py.txt', 'w', encoding='utf-8')
sys.stderr = sys.stdout

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from django.contrib.auth.models import User
from appname.models import Follow

# Delete old test users and follows
User.objects.filter(username__in=['test_u1', 'test_u2']).delete()

u1 = User.objects.create_user(username='test_u1', password='pw')
u2 = User.objects.create_user(username='test_u2', password='pw')

print(f"Initial: u2 pending requests count: {Follow.objects.filter(following=u2, status='pending').count()}")

# test u1 sending follow request to u2
Follow.objects.get_or_create(follower=u1, following=u2, status='pending')

# check pending requests for u2
pr = Follow.objects.filter(following=u2, status='pending')
print(f"After ORM follow: u2 pending requests count: {pr.count()}")

# try with test client
from django.test import Client
c = Client()
c.login(username='test_u1', password='pw')
response = c.post('/connect/follow/', {'action': 'request', 'user_id': u2.id})
print("HTTP Response status from follow_action:", response.status_code)

pr_after_http = Follow.objects.filter(following=u2, status='pending')
print(f"After HTTP follow: u2 pending requests count: {pr_after_http.count()}")
