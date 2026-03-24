from django.db.models.signals import post_save
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added
from django.contrib.auth.models import User
from .models import DeveloperProfile
from .tasks import evaluate_github_profile
'''

📦 Real Example
@receiver(social_account_added)
def trigger_github_evaluation(request, sociallogin, **kwargs):

👉 Means:

WHEN:
    social_account_added happens

THEN:
    run trigger_github_evaluation()


'''



@receiver(social_account_added)
def trigger_github_evaluation(request, sociallogin, **kwargs):
    if sociallogin.account.provider == 'github':
        user = sociallogin.user
        profile, created = DeveloperProfile.objects.get_or_create(
            user=user,
            defaults={'github_username': sociallogin.account.extra_data.get('login', '')}
        )
            # If user reconnects/updates or creates for first time, fire task
        profile.evaluation_status = 'pending'
        profile.save()
        evaluate_github_profile.delay(user.id)

from allauth.account.signals import user_logged_in

@receiver(user_logged_in)
def trigger_github_evaluation_on_login(request, user, **kwargs):
    if user.socialaccount_set.filter(provider='github').exists():
        social_account = user.socialaccount_set.get(provider='github')
        profile, created = DeveloperProfile.objects.get_or_create(
            user=user,
            defaults={'github_username': social_account.extra_data.get('login', '')}
        )
        if profile.evaluation_status not in ['fetching', 'analyzing']:
            profile.evaluation_status = 'pending'
            profile.save()
            evaluate_github_profile.delay(user.id)
