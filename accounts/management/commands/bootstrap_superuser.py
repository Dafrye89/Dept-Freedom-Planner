from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import CustomUser


class Command(BaseCommand):
    help = "Create or refresh the default local superuser for this project."

    def handle(self, *args, **options):
        username = settings.BOOTSTRAP_SUPERUSER_USERNAME
        password = settings.BOOTSTRAP_SUPERUSER_PASSWORD
        email = settings.BOOTSTRAP_SUPERUSER_EMAIL

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        changed = False
        if user.username != username:
            user.username = username
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if changed:
            user.save()

        user.set_password(password)
        user.save(update_fields=["password"])

        access = user.subscription_access
        if not access.lifetime_override:
            access.lifetime_override = True
            access.save(update_fields=["lifetime_override", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Verified'} superuser '{username}' with founder access."
            )
        )
