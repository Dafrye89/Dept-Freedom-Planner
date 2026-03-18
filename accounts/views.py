from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileSettingsForm, UserSettingsForm
from .services.access import get_capabilities
from billing.services import is_stripe_configured


@login_required
def account_settings(request):
    user_form = UserSettingsForm(instance=request.user, prefix="user")
    profile_form = ProfileSettingsForm(instance=request.user.profile, prefix="profile")

    if request.method == "POST":
        user_form = UserSettingsForm(request.POST, instance=request.user, prefix="user")
        profile_form = ProfileSettingsForm(request.POST, instance=request.user.profile, prefix="profile")
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
        },
    )

# Create your views here.
