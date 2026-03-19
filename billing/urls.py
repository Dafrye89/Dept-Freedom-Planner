from django.urls import path

from .views import checkout, checkout_cancel, checkout_success, portal, pricing, refresh_access, stripe_webhook

app_name = "billing"

urlpatterns = [
    path("", pricing, name="pricing"),
    path("checkout/", checkout, name="checkout"),
    path("checkout/success/", checkout_success, name="checkout_success"),
    path("checkout/cancel/", checkout_cancel, name="checkout_cancel"),
    path("portal/", portal, name="portal"),
    path("refresh-access/", refresh_access, name="refresh_access"),
    path("webhook/", stripe_webhook, name="stripe_webhook"),
]
