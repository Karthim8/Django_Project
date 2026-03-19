from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat_view, name='chat'),
    path('rooms/', views.rooms_view, name='rooms'),
    path('connect/', views.connect_view, name='connect'),
    path('profile/', views.profile_view, name='profile'),
    path('resources/', views.resources_view, name='resources'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
]