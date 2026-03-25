import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from django.test import Client

c = Client()
try:
    response = c.post('/accounts/signup/', {
        'name': 'Karthik Test',
        'email': 'karthiktest@example.com',
        'password': 'password123'
    })
    print("Response Status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
