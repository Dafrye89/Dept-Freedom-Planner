from django.conf import settings

from accounts.services.access import get_capabilities, plan_limit_message


def app_access(request):
    capabilities = get_capabilities(request.user)
    return {
        "capabilities": capabilities,
        "show_admin_link": capabilities.can_see_admin_link,
        "google_login_enabled": settings.GOOGLE_LOGIN_ENABLED,
        "plan_limit_message": plan_limit_message(request.user),
        "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
        "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
    }
