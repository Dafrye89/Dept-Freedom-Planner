from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

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
