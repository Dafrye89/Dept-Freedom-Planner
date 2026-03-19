from django.conf import settings
from django.shortcuts import render


def privacy(request):
    return render(
        request,
        "legal/privacy.html",
        {
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
            "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
        },
    )


def terms(request):
    return render(
        request,
        "legal/terms.html",
        {
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
            "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
        },
    )


def disclaimer(request):
    return render(
        request,
        "legal/disclaimer.html",
        {
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
            "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
        },
    )

# Create your views here.
