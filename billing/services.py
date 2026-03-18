from __future__ import annotations

from typing import Any

import stripe
from django.conf import settings
from django.urls import reverse

from accounts.models import CustomUser, SubscriptionAccess
from billing.models import StripeWebhookEvent


SUBSCRIPTION_SYNC_EVENT_TYPES = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}


def is_stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PRO_PRICE_ID)


def get_publishable_key() -> str:
    return settings.STRIPE_PUBLISHABLE_KEY


def _configure_stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe secret key is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def ensure_stripe_customer(user: CustomUser) -> str:
    _configure_stripe()
    access = user.subscription_access
    if access.stripe_customer_id:
        return access.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.get_full_name() or user.profile.display_name or user.username,
        metadata={"user_id": str(user.pk), "username": user.username},
    )
    access.stripe_customer_id = customer["id"]
    access.save(update_fields=["stripe_customer_id", "updated_at"])
    return access.stripe_customer_id


def create_checkout_session(*, user: CustomUser) -> str:
    _configure_stripe()
    customer_id = ensure_stripe_customer(user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(user.pk),
        metadata={"user_id": str(user.pk)},
        line_items=[{"price": settings.STRIPE_PRO_PRICE_ID, "quantity": 1}],
        allow_promotion_codes=True,
        success_url=f"{settings.APP_BASE_URL}{reverse('billing:checkout_success')}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.APP_BASE_URL}{reverse('billing:checkout_cancel')}",
    )
    return session["url"]


def create_portal_session(*, user: CustomUser) -> str:
    _configure_stripe()
    access = user.subscription_access
    customer_id = access.stripe_customer_id or ensure_stripe_customer(user)
    kwargs: dict[str, Any] = {
        "customer": customer_id,
        "return_url": f"{settings.APP_BASE_URL}{reverse('accounts:settings')}",
    }
    if settings.STRIPE_PORTAL_CONFIGURATION_ID:
        kwargs["configuration"] = settings.STRIPE_PORTAL_CONFIGURATION_ID
    session = stripe.billing_portal.Session.create(**kwargs)
    return session["url"]


def construct_stripe_event(*, payload: bytes, signature: str):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Stripe webhook secret is not configured.")
    return stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.STRIPE_WEBHOOK_SECRET)


def sync_subscription_from_stripe_data(subscription: dict[str, Any], *, access: SubscriptionAccess | None = None):
    if access is None:
        access = find_access_for_subscription(subscription)
    if access is None:
        return None

    subscription_item = ((subscription.get("items") or {}).get("data") or [{}])[0]
    price_data = subscription_item.get("price") or {}
    access.sync_stripe_subscription(
        customer_id=subscription.get("customer", "") or access.stripe_customer_id,
        subscription_id=subscription.get("id", ""),
        price_id=price_data.get("id", ""),
        status=subscription.get("status", ""),
        cancel_at_period_end=subscription.get("cancel_at_period_end", False),
        current_period_end=subscription.get("current_period_end"),
        notes=f"Stripe subscription sync: {subscription.get('status', 'unknown')}",
    )
    return access


def find_access_for_subscription(subscription: dict[str, Any]) -> SubscriptionAccess | None:
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    if subscription_id:
        match = SubscriptionAccess.objects.filter(stripe_subscription_id=subscription_id).first()
        if match:
            return match
    if customer_id:
        return SubscriptionAccess.objects.filter(stripe_customer_id=customer_id).first()
    return None


def handle_checkout_session_completed(session: dict[str, Any]):
    user_id = (session.get("metadata") or {}).get("user_id") or session.get("client_reference_id")
    if not user_id:
        return None
    user = CustomUser.objects.filter(pk=user_id).first()
    if not user:
        return None
    access = user.subscription_access
    access.stripe_customer_id = session.get("customer", "") or access.stripe_customer_id
    access.stripe_subscription_id = session.get("subscription", "") or access.stripe_subscription_id
    access.save(update_fields=["stripe_customer_id", "stripe_subscription_id", "updated_at"])
    if access.stripe_subscription_id:
        _configure_stripe()
        subscription = stripe.Subscription.retrieve(access.stripe_subscription_id)
        return sync_subscription_from_stripe_data(subscription, access=access)
    return access


def handle_invoice_event(invoice: dict[str, Any]):
    subscription_id = invoice.get("subscription")
    customer_id = invoice.get("customer")
    access = None
    if subscription_id:
        access = SubscriptionAccess.objects.filter(stripe_subscription_id=subscription_id).first()
    if access is None and customer_id:
        access = SubscriptionAccess.objects.filter(stripe_customer_id=customer_id).first()
    if access is None:
        return None
    if subscription_id:
        _configure_stripe()
        subscription = stripe.Subscription.retrieve(subscription_id)
        return sync_subscription_from_stripe_data(subscription, access=access)
    return access


def process_stripe_event(event: dict[str, Any]) -> bool:
    event_id = event.get("id")
    if not event_id:
        return False
    if StripeWebhookEvent.objects.filter(stripe_event_id=event_id).exists():
        return False

    event_type = event.get("type", "")
    object_data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        handle_checkout_session_completed(object_data)
    elif event_type.startswith("customer.subscription."):
        sync_subscription_from_stripe_data(object_data)
    elif event_type.startswith("invoice."):
        handle_invoice_event(object_data)

    StripeWebhookEvent.objects.create(
        stripe_event_id=event_id,
        event_type=event_type,
        livemode=bool(event.get("livemode")),
        payload=event,
    )
    return True
