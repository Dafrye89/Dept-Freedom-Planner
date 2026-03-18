from django.db import models


class StripeWebhookEvent(models.Model):
    stripe_event_id = models.CharField(max_length=80, unique=True)
    event_type = models.CharField(max_length=80)
    livemode = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]

    def __str__(self):
        return f"{self.event_type} ({self.stripe_event_id})"
