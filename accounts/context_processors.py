from django.conf import settings

from accounts.services.access import get_capabilities, plan_limit_message


def app_access(request):
    capabilities = get_capabilities(request.user)
    profile = getattr(getattr(request, "user", None), "profile", None)
    avatar_url = ""
    if profile:
        if getattr(profile, "avatar", None):
            try:
                avatar_url = profile.avatar.url
            except ValueError:
                avatar_url = ""
        if not avatar_url:
            avatar_url = profile.google_avatar_url
    branding_logo_path = "img/branding/logo-pro.png" if capabilities.is_paid else "img/branding/logo-light.png"
    return {
        "capabilities": capabilities,
        "show_admin_link": capabilities.can_see_admin_link,
        "google_login_enabled": settings.GOOGLE_LOGIN_ENABLED,
        "plan_limit_message": plan_limit_message(request.user),
        "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
        "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
        "branding_logo_path": branding_logo_path,
        "header_avatar_url": avatar_url,
        "show_pricing_link": not capabilities.is_paid,
    }
