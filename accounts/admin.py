from django.contrib import admin
from .models import UserProfile, PlacementBadge, EmailVerification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'role', 'college', 'batch_year', 'branch')
    list_filter   = ('role', 'batch_year')
    search_fields = ('user__username', 'user__email', 'college')

@admin.register(PlacementBadge)
class PlacementBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'package', 'year')
    list_filter  = ('year', 'company')

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'created_at')
    list_filter  = ('is_verified',)
