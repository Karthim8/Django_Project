from django.shortcuts import render

def index(request):
    return render(request, "index.html")

def chat_view(request):
    return render(request, "chat.html")

def rooms_view(request):
    return render(request, "rooms.html")

def connect_view(request):
    return render(request, "connect.html")

def profile_view(request):
    return render(request, "profile.html")

def resources_view(request):
    return render(request, "resources.html")
