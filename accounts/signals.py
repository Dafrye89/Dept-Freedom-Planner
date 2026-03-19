from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from allauth.socialaccount.models import SocialAccount

from .models import CustomUser, Profile, SubscriptionAccess


@receiver(post_save, sender=CustomUser)
def ensure_profile_and_access(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            display_name=instance.username or instance.email.split("@")[0],
        )
        SubscriptionAccess.objects.create(
            user=instance,
            lifetime_override=instance.username.lower() == settings.BOOTSTRAP_SUPERUSER_USERNAME.lower(),
        )


@receiver(post_save, sender=SocialAccount)
def sync_google_avatar(sender, instance, **kwargs):
    if instance.provider != "google":
        return
    picture = (instance.extra_data or {}).get("picture", "").strip()
    name = (instance.extra_data or {}).get("name", "").strip()
    profile = instance.user.profile
    updated_fields = []
    if picture and profile.google_avatar_url != picture:
        profile.google_avatar_url = picture
        updated_fields.append("google_avatar_url")
    if name and not profile.display_name:
        profile.display_name = name
        updated_fields.append("display_name")
    if updated_fields:
        updated_fields.append("updated_at")
        profile.save(update_fields=updated_fields)
