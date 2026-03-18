from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileSettingsForm, UserSettingsForm


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
        },
    )

# Create your views here.
