from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class CapabilitySet:
    tier_label: str
    is_authenticated: bool
    is_free: bool
    is_paid: bool
    is_override: bool
    can_calculate: bool
    can_compare: bool
    can_compare_unlimited: bool
    can_save_plans: bool
    can_print: bool
    can_export_pdf: bool
    can_view_full_schedule: bool
    max_saved_plans: int | None
    can_see_admin_link: bool


def _get_access(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "subscription_access", None)


def is_override_user(user) -> bool:
    access = _get_access(user)
    return bool(
        getattr(user, "is_authenticated", False)
        and user.username.lower() == settings.BOOTSTRAP_SUPERUSER_USERNAME.lower()
        and access
        and access.lifetime_override
    )


def is_paid_user(user) -> bool:
    access = _get_access(user)
    return bool(access and access.tier == access.Tier.PAID)


def get_capabilities(user) -> CapabilitySet:
    if not getattr(user, "is_authenticated", False):
        return CapabilitySet(
            tier_label="Anonymous",
            is_authenticated=False,
            is_free=False,
            is_paid=False,
            is_override=False,
            can_calculate=True,
            can_compare=True,
            can_compare_unlimited=False,
            can_save_plans=False,
            can_print=False,
            can_export_pdf=False,
            can_view_full_schedule=False,
            max_saved_plans=0,
            can_see_admin_link=False,
        )

    override = is_override_user(user)
    paid = is_paid_user(user)
    if override or paid:
        return CapabilitySet(
            tier_label="Founder Access" if override else "Paid",
            is_authenticated=True,
            is_free=False,
            is_paid=True,
            is_override=override,
            can_calculate=True,
            can_compare=True,
            can_compare_unlimited=True,
            can_save_plans=True,
            can_print=True,
            can_export_pdf=True,
            can_view_full_schedule=True,
            max_saved_plans=None,
            can_see_admin_link=override and user.is_superuser,
        )

    return CapabilitySet(
        tier_label="Free",
        is_authenticated=True,
        is_free=True,
        is_paid=False,
        is_override=False,
        can_calculate=True,
        can_compare=True,
        can_compare_unlimited=False,
        can_save_plans=False,
        can_print=True,
        can_export_pdf=False,
        can_view_full_schedule=False,
        max_saved_plans=0,
        can_see_admin_link=False,
    )


def can_create_plan(user) -> bool:
    capabilities = get_capabilities(user)
    if not capabilities.can_save_plans:
        return False
    if capabilities.max_saved_plans is None:
        return True

    from plans.models import DebtPlan

    return DebtPlan.objects.filter(user=user, is_archived=False).count() < capabilities.max_saved_plans


def plan_limit_message(user) -> str:
    capabilities = get_capabilities(user)
    if not capabilities.is_authenticated:
        return "Create an account to build and view your debt payoff plan."
    if not capabilities.can_save_plans:
        return "If you want to save plans, you will need to upgrade to the Pro plan."
    return "Your account includes unlimited saved plans."


def upgrade_message(feature_name: str) -> str:
    return f"If you want to use {feature_name}, you will need to upgrade to the Pro plan."
