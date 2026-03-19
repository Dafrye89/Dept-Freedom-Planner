from stripe._error import SignatureVerificationError, StripeError

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.services.access import get_capabilities
from billing.services import (
    construct_stripe_event,
    create_checkout_session,
    create_portal_session,
    get_publishable_key,
    is_stripe_configured,
    process_stripe_event,
    sync_checkout_session_for_user,
)


def pricing(request):
    return render(
        request,
        "billing/pricing.html",
        {
            "capabilities": get_capabilities(request.user),
            "stripe_enabled": is_stripe_configured(),
            "stripe_publishable_key": get_publishable_key(),
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
        },
    )


@login_required
@require_POST
def checkout(request):
    capabilities = get_capabilities(request.user)
    if capabilities.is_override:
        messages.info(request, "Founder access already includes every paid feature.")
        return redirect("plans:dashboard")
    if capabilities.is_paid:
        messages.info(request, "Your account already has paid access.")
        return redirect("accounts:settings")
    if not is_stripe_configured():
        messages.error(request, "Stripe is not configured yet.")
        return redirect("billing:pricing")

    try:
        checkout_url = create_checkout_session(user=request.user)
    except StripeError:
        messages.error(request, "Stripe could not start checkout right now. Please try again.")
        return redirect("billing:pricing")
    return redirect(checkout_url)


@login_required
@require_POST
def portal(request):
    if not is_stripe_configured():
        messages.error(request, "Stripe is not configured yet.")
        return redirect("accounts:settings")
    try:
        portal_url = create_portal_session(user=request.user)
    except StripeError:
        messages.error(request, "Stripe could not open the billing portal right now.")
        return redirect("accounts:settings")
    return redirect(portal_url)


@login_required
def checkout_success(request):
    session_id = request.GET.get("session_id", "").strip()
    if session_id and is_stripe_configured():
        try:
            access = sync_checkout_session_for_user(user=request.user, session_id=session_id)
        except StripeError:
            access = None
        if access and access.tier == access.Tier.PAID:
            messages.success(request, "Your Pro access is active now.")
        else:
            messages.info(request, "Stripe checkout completed. We are still confirming your Pro access.")
    else:
        messages.success(request, "Stripe checkout completed.")
    return redirect("plans:dashboard")


@login_required
def checkout_cancel(request):
    messages.warning(request, "Stripe checkout was canceled. You can restart it any time from pricing.")
    return redirect("billing:pricing")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not is_stripe_configured():
        return HttpResponse(status=204)

    signature = request.headers.get("Stripe-Signature", "")
    if not signature:
        return HttpResponseBadRequest("Missing Stripe-Signature header.")
    try:
        event = construct_stripe_event(payload=request.body, signature=signature)
    except ValueError:
        return HttpResponseBadRequest("Invalid payload.")
    except SignatureVerificationError:
        return HttpResponseBadRequest("Invalid signature.")
    except RuntimeError:
        return HttpResponse(status=204)

    process_stripe_event(event)
    return HttpResponse(status=200)
