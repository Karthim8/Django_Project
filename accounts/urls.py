from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.custom_signup, name='custom_signup'),
    path('verify/', views.verify_email, name='verify_email'),
]
