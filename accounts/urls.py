from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.custom_signup, name='custom_signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
]
