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


def _subscription_price_ids(subscription: dict[str, Any]) -> set[str]:
    items = ((subscription.get("items") or {}).get("data") or [])
    return {((item.get("price") or {}).get("id") or "") for item in items if item}


def _subscription_product_ids(subscription: dict[str, Any]) -> set[str]:
    items = ((subscription.get("items") or {}).get("data") or [])
    return {((item.get("price") or {}).get("product") or "") for item in items if item}


def _subscription_matches_pro_plan(subscription: dict[str, Any]) -> bool:
    price_ids = _subscription_price_ids(subscription)
    product_ids = _subscription_product_ids(subscription)
    if settings.STRIPE_PRO_PRICE_ID and settings.STRIPE_PRO_PRICE_ID in price_ids:
        return True
    if settings.STRIPE_PRO_PRODUCT_ID and settings.STRIPE_PRO_PRODUCT_ID in product_ids:
        return True
    return False


def _extract_customer_details(customer: Any) -> dict[str, Any]:
    if isinstance(customer, dict):
        return customer
    if not customer:
        return {}
    return stripe.Customer.retrieve(customer)


def _find_user_from_customer(customer: dict[str, Any]) -> CustomUser | None:
    metadata = customer.get("metadata") or {}
    user_id = metadata.get("user_id")
    if user_id:
        user = CustomUser.objects.filter(pk=user_id).first()
        if user:
            return user
    email = (customer.get("email") or "").strip().lower()
    if email:
        return CustomUser.objects.filter(email=email).first()
    return None


def _find_access_for_subscription_or_customer(subscription: dict[str, Any]) -> SubscriptionAccess | None:
    access = find_access_for_subscription(subscription)
    if access:
        return access
    customer = _extract_customer_details(subscription.get("customer"))
    user = _find_user_from_customer(customer)
    if not user:
        return None
    access = user.subscription_access
    customer_id = customer.get("id", "")
    if customer_id and access.stripe_customer_id != customer_id:
        access.stripe_customer_id = customer_id
        access.save(update_fields=["stripe_customer_id", "updated_at"])
    return access


def _pick_relevant_subscription(subscriptions: list[dict[str, Any]]) -> dict[str, Any] | None:
    matching = [subscription for subscription in subscriptions if _subscription_matches_pro_plan(subscription)]
    if not matching:
        return None
    active = [subscription for subscription in matching if subscription.get("status") in SubscriptionAccess.ACTIVE_STRIPE_STATUSES]
    pool = active or matching
    return max(pool, key=lambda subscription: int(subscription.get("created") or 0))


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
        subscription_data={"trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS},
        allow_promotion_codes=True,
        success_url=f"{settings.APP_BASE_URL}{reverse('billing:checkout_success')}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.APP_BASE_URL}{reverse('billing:checkout_cancel')}",
    )
    return session["url"]


def sync_checkout_session_for_user(*, user: CustomUser, session_id: str):
    _configure_stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    expected_user_id = str(user.pk)
    session_user_id = str((session.get("metadata") or {}).get("user_id") or session.get("client_reference_id") or "")
    if session_user_id != expected_user_id:
        return None
    return handle_checkout_session_completed(session)


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
        access = _find_access_for_subscription_or_customer(subscription)
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


def reconcile_user_paid_access(user: CustomUser):
    _configure_stripe()
    access = user.subscription_access

    if access.stripe_subscription_id:
        subscription = stripe.Subscription.retrieve(access.stripe_subscription_id)
        if _subscription_matches_pro_plan(subscription):
            return sync_subscription_from_stripe_data(subscription, access=access)

    customer_ids: list[str] = []
    if access.stripe_customer_id:
        customer_ids.append(access.stripe_customer_id)
    else:
        customers = stripe.Customer.list(email=user.email, limit=10)
        for customer in customers.get("data", []):
            matched_user = _find_user_from_customer(customer)
            if matched_user and matched_user.pk == user.pk:
                customer_ids.append(customer.get("id", ""))

    for customer_id in dict.fromkeys(customer_ids):
        if not customer_id:
            continue
        if access.stripe_customer_id != customer_id:
            access.stripe_customer_id = customer_id
            access.save(update_fields=["stripe_customer_id", "updated_at"])
        subscriptions = stripe.Subscription.list(customer=customer_id, status="all", limit=20)
        relevant = _pick_relevant_subscription(subscriptions.get("data", []))
        if relevant:
            return sync_subscription_from_stripe_data(relevant, access=access)

    return access


def reconcile_all_paid_access():
    _configure_stripe()
    synced = 0
    unmatched = 0
    for subscription in stripe.Subscription.list(status="all", limit=100).auto_paging_iter():
        if not _subscription_matches_pro_plan(subscription):
            continue
        access = _find_access_for_subscription_or_customer(subscription)
        if access is None:
            unmatched += 1
            continue
        sync_subscription_from_stripe_data(subscription, access=access)
        synced += 1
    return {"synced": synced, "unmatched": unmatched}
