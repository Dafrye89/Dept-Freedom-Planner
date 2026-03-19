from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils._os import safe_join
from django.views.decorators.http import require_GET

from .forms import ProfileSettingsForm, UserSettingsForm
from .services.access import get_capabilities
from billing.services import is_stripe_configured
from plans.services import aggregate_dashboard_progress


@login_required
def account_settings(request):
    user_form = UserSettingsForm(instance=request.user, prefix="user")
    profile_form = ProfileSettingsForm(instance=request.user.profile, prefix="profile")
    saved_plans = list(
        request.user.debt_plans.filter(is_archived=False).prefetch_related("debt_items", "monthly_checkins", "badge_awards")
    )

    if request.method == "POST":
        user_form = UserSettingsForm(request.POST, instance=request.user, prefix="user")
        profile_form = ProfileSettingsForm(request.POST, request.FILES, instance=request.user.profile, prefix="profile")
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your account settings were updated.")
            return redirect("accounts:settings")

    return render(
        request,
        "account/settings.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "capabilities": get_capabilities(request.user),
            "stripe_enabled": is_stripe_configured(),
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
            "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
            "badge_awards": request.user.badge_awards.select_related("debt_plan", "debt_item"),
            "profile_progress": aggregate_dashboard_progress(saved_plans),
        },
    )


@require_GET
def media_file(request, path):
    try:
        full_path = Path(safe_join(settings.MEDIA_ROOT, path))
    except ValueError as exc:
        raise Http404("File not found") from exc
    if not full_path.exists() or not full_path.is_file():
        raise Http404("File not found")
    return FileResponse(full_path.open("rb"))

# Create your views here.
