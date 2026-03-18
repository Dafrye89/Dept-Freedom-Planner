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
    timezone = models.CharField(max_length=64, default="America/Chicago")
    marketing_opt_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user}"


class SubscriptionAccess(models.Model):
    class Tier(models.TextChoices):
        FREE = "free", "Free"
        PAID = "paid", "Paid"

    user = models.OneToOneField("accounts.CustomUser", on_delete=models.CASCADE, related_name="subscription_access")
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)
    paid_activated_at = models.DateTimeField(null=True, blank=True)
    paid_notes = models.TextField(blank=True)
    lifetime_override = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def activate_paid(self, notes=""):
        self.tier = self.Tier.PAID
        self.paid_activated_at = timezone.now()
        if notes:
            self.paid_notes = notes
        self.save(update_fields=["tier", "paid_activated_at", "paid_notes", "updated_at"])

    def __str__(self):
        return f"{self.user} ({self.get_tier_display()})"

# Create your models here.
