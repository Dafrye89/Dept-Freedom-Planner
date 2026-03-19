from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.lower().strip()
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username or self.email


class Profile(models.Model):
    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    google_avatar_url = models.URLField(blank=True)
    timezone = models.CharField(max_length=64, default="America/Chicago")
    marketing_opt_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user}"


class SubscriptionAccess(models.Model):
    ACTIVE_STRIPE_STATUSES = {"active", "trialing", "past_due"}

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        PAID = "paid", "Paid"

    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="subscription_access")
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)
    paid_activated_at = models.DateTimeField(null=True, blank=True)
    paid_notes = models.TextField(blank=True)
    lifetime_override = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=64, blank=True)
    stripe_subscription_id = models.CharField(max_length=64, blank=True)
    stripe_price_id = models.CharField(max_length=64, blank=True)
    stripe_status = models.CharField(max_length=32, blank=True)
    stripe_cancel_at_period_end = models.BooleanField(default=False)
    stripe_current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def activate_paid(self, notes=""):
        self.tier = self.Tier.PAID
        self.paid_activated_at = timezone.now()
        if notes:
            self.paid_notes = notes
        self.save(update_fields=["tier", "paid_activated_at", "paid_notes", "updated_at"])

    def deactivate_paid(self, notes=""):
        self.tier = self.Tier.FREE
        if notes:
            self.paid_notes = notes
        self.save(update_fields=["tier", "paid_notes", "updated_at"])

    def sync_stripe_subscription(
        self,
        *,
        customer_id="",
        subscription_id="",
        price_id="",
        status="",
        cancel_at_period_end=False,
        current_period_end=None,
        notes="",
    ):
        self.stripe_customer_id = customer_id or self.stripe_customer_id
        self.stripe_subscription_id = subscription_id or ""
        self.stripe_price_id = price_id or ""
        self.stripe_status = status or ""
        self.stripe_cancel_at_period_end = bool(cancel_at_period_end)
        self.stripe_current_period_end = self._normalize_timestamp(current_period_end)
        if notes:
            self.paid_notes = notes

        if self.stripe_status in self.ACTIVE_STRIPE_STATUSES:
            self.tier = self.Tier.PAID
            if not self.paid_activated_at:
                self.paid_activated_at = timezone.now()
        elif not self.lifetime_override:
            self.tier = self.Tier.FREE

        self.save(
            update_fields=[
                "stripe_customer_id",
                "stripe_subscription_id",
                "stripe_price_id",
                "stripe_status",
                "stripe_cancel_at_period_end",
                "stripe_current_period_end",
                "tier",
                "paid_activated_at",
                "paid_notes",
                "updated_at",
            ]
        )

    @staticmethod
    def _normalize_timestamp(value):
        if not value:
            return None
        if isinstance(value, datetime):
            if timezone.is_aware(value):
                return value
            return timezone.make_aware(value)
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)

    def __str__(self):
        return f"{self.user} ({self.get_tier_display()})"

# Create your models here.
