from datetime import date
from decimal import Decimal

from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan
from calculator.services.payoff_engine import add_months, round_currency

from .models import BadgeAward, DebtItem, DebtPlan, MonthlyCheckIn, ScenarioComparison


BADGE_CONFIG = {
    DebtItem.DebtType.CREDIT_CARD: {
        "badge_key": "credit_card",
        "badge_name": "Credit Card Slayer",
        "badge_image": "img/branding/badges/credit_card_slayer.png",
    },
    DebtItem.DebtType.VEHICLE: {
        "badge_key": "vehicle",
        "badge_name": "Vehicle Paid Off",
        "badge_image": "img/branding/badges/Vehical_Paid_off.png",
    },
    DebtItem.DebtType.MORTGAGE: {
        "badge_key": "mortgage",
        "badge_name": "Mortgage Crusher",
        "badge_image": "img/branding/badges/morgage_crusher.png",
    },
    DebtItem.DebtType.BANK_LOAN: {
        "badge_key": "bank_loan",
        "badge_name": "Bank Loan Eliminator",
        "badge_image": "img/branding/badges/band_Loan_eliminator.png",
    },
    DebtItem.DebtType.PAYDAY_LOAN: {
        "badge_key": "payday_loan",
        "badge_name": "Payday Loan Escaped",
        "badge_image": "img/branding/badges/Payday_Loan_Escaped.png",
    },
    DebtItem.DebtType.PERSONAL_LOAN: {
        "badge_key": "personal_loan",
        "badge_name": "Financial Discipline",
        "badge_image": "img/branding/badges/financial_disipline.png",
    },
    DebtItem.DebtType.STUDENT_LOAN: {
        "badge_key": "student_loan",
        "badge_name": "Student Loan Conqueror",
        "badge_image": "img/branding/badges/student_loan_conqueror.png",
    },
    DebtItem.DebtType.OTHER: {
        "badge_key": "other_debt",
        "badge_name": "Debt Conqueror",
        "badge_image": "img/branding/badges/debt_conqueror.png",
    },
}


def draft_to_plan_payload(draft: dict) -> dict:
    return {
        "title": draft.get("title") or "Debt Freedom Roadmap",
        "debts": draft.get("debts", []),
        "extra_payment": Decimal(str(draft.get("extra_monthly_payment", "0") or "0")),
        "strategy": draft.get("strategy_type") or "snowball",
    }


def plan_to_engine_payload(plan: DebtPlan) -> dict:
    debts = [
        {
            "id": f"plan-debt-{debt.pk}",
            "name": debt.name,
            "lender_name": debt.lender_name,
            "debt_type": debt.debt_type,
            "balance": debt.balance,
            "apr": debt.apr,
            "minimum_payment": debt.minimum_payment,
            "due_day": debt.due_day,
            "notes": debt.notes,
            "custom_order": debt.custom_order,
        }
        for debt in plan.debt_items.all()
    ]
    extra_overrides = {
        checkin.month_index: checkin.extra_payment_amount
        for checkin in plan.monthly_checkins.all()
    }
    actual_snapshot_month_index = max(extra_overrides.keys(), default=0)
    return {
        "title": plan.title,
        "debts": debts,
        "extra_payment": plan.extra_monthly_payment,
        "monthly_extra_payments": extra_overrides,
        "actual_snapshot_month_index": actual_snapshot_month_index,
        "start_date": plan.checkin_anchor_date or plan.created_at.date(),
        "strategy": plan.strategy_type,
    }


def plan_to_draft(plan: DebtPlan) -> dict:
    return {
        "title": plan.title,
        "household_name": plan.household_name,
        "strategy_type": plan.strategy_type,
        "extra_monthly_payment": str(plan.extra_monthly_payment),
        "debts": [
            {
                "name": debt.name,
                "lender_name": debt.lender_name,
                "debt_type": debt.debt_type,
                "balance": str(debt.balance),
                "apr": str(debt.apr),
                "minimum_payment": str(debt.minimum_payment),
                "due_day": debt.due_day or "",
                "notes": debt.notes,
                "custom_order": debt.custom_order,
            }
            for debt in plan.debt_items.all()
        ],
    }


def update_plan_summary(plan: DebtPlan) -> dict:
    result = solve_payoff_plan(**plan_to_engine_payload(plan))
    summary = result["summary"]
    plan.total_balance_snapshot = summary["total_debt"]
    plan.projected_payoff_date = summary["projected_payoff_date"]
    plan.projected_months_to_payoff = summary["months_to_payoff"]
    plan.projected_total_interest = summary["total_interest"]
    plan.projected_total_paid = summary["total_paid"]
    plan.save(
        update_fields=[
            "total_balance_snapshot",
            "projected_payoff_date",
            "projected_months_to_payoff",
            "projected_total_interest",
            "projected_total_paid",
            "updated_at",
        ]
    )
    return result


def get_badge_config(debt_type: str) -> dict:
    return BADGE_CONFIG.get(debt_type, BADGE_CONFIG[DebtItem.DebtType.OTHER])


def sync_plan_badges(plan: DebtPlan, result: dict) -> list[BadgeAward]:
    snapshot = result.get("current_snapshot") or {}
    paid_off_ids = set(snapshot.get("paid_off_debt_ids", []))
    if not paid_off_ids:
        return []
    debt_lookup = {f"plan-debt-{debt.pk}": debt for debt in plan.debt_items.all()}
    awarded = []
    for debt_id in paid_off_ids:
        debt = debt_lookup.get(debt_id)
        if debt is None:
            continue
        config = get_badge_config(debt.debt_type)
        badge_award, created = BadgeAward.objects.get_or_create(
            debt_item=debt,
            badge_key=config["badge_key"],
            defaults={
                "user": plan.user,
                "debt_plan": plan,
                "badge_name": config["badge_name"],
                "badge_image": config["badge_image"],
                "debt_type": debt.debt_type,
            },
        )
        if created:
            awarded.append(badge_award)
    return awarded


def get_plan_badges(plan: DebtPlan):
    return plan.badge_awards.all()


def get_due_checkin(plan: DebtPlan, today: date | None = None) -> dict | None:
    if not plan.checkins_active or not plan.checkin_anchor_date:
        return None
    today = today or date.today()
    anchor_month = date(plan.checkin_anchor_date.year, plan.checkin_anchor_date.month, 1)
    current_month = date(today.year, today.month, 1)
    month_diff = (current_month.year - anchor_month.year) * 12 + (current_month.month - anchor_month.month)
    if month_diff < 0:
        return None
    due_through = month_diff + 1
    answered = set(plan.monthly_checkins.values_list("month_index", flat=True))
    for month_index in range(1, due_through + 1):
        if month_index in answered:
            continue
        month_date = add_months(anchor_month, month_index - 1)
        return {
            "month_index": month_index,
            "month_label": month_date.strftime("%B %Y"),
            "month_date": month_date,
            "default_extra_payment": plan.extra_monthly_payment,
        }
    return None


def save_monthly_checkin(*, plan: DebtPlan, month_index: int, status: str, custom_extra_payment=None) -> MonthlyCheckIn:
    anchor_month = date(plan.checkin_anchor_date.year, plan.checkin_anchor_date.month, 1)
    month_date = add_months(anchor_month, month_index - 1)
    extra_payment_amount = plan.extra_monthly_payment
    if status == MonthlyCheckIn.Status.SKIPPED_EXTRA:
        extra_payment_amount = Decimal("0.00")
    elif status == MonthlyCheckIn.Status.CUSTOM:
        extra_payment_amount = round_currency(Decimal(str(custom_extra_payment or "0")))
    checkin, _created = MonthlyCheckIn.objects.update_or_create(
        debt_plan=plan,
        month_index=month_index,
        defaults={
            "month_date": month_date,
            "status": status,
            "extra_payment_amount": extra_payment_amount,
        },
    )
    return checkin


def save_plan_pace_update(*, plan: DebtPlan, extra_monthly_payment) -> dict:
    plan.extra_monthly_payment = Decimal(str(extra_monthly_payment))
    plan.save(update_fields=["extra_monthly_payment", "updated_at"])
    result = update_plan_summary(plan)
    refresh_scenarios(plan)
    return result


def build_plan_view_data(plan: DebtPlan) -> dict:
    result = solve_payoff_plan(**plan_to_engine_payload(plan))
    new_badges = sync_plan_badges(plan, result)
    return {
        "result": result,
        "comparisons": create_comparisons(plan_to_engine_payload(plan)),
        "due_checkin": get_due_checkin(plan),
        "badges": get_plan_badges(plan),
        "new_badges": new_badges,
        "progress": result.get("current_snapshot") or {},
    }


def aggregate_dashboard_progress(plans: list[DebtPlan]) -> dict:
    total_debt = Decimal("0.00")
    remaining = Decimal("0.00")
    total_debts = 0
    debts_cleared = 0
    for plan in plans:
        result = solve_payoff_plan(**plan_to_engine_payload(plan))
        progress = result.get("current_snapshot") or {}
        total_debt += Decimal(str(plan.total_balance_snapshot or 0))
        remaining += Decimal(str(progress.get("remaining_balance") or 0))
        total_debts += int(progress.get("total_debts") or 0)
        debts_cleared += int(progress.get("debts_cleared") or 0)
    total_paid_off = round_currency(total_debt - remaining)
    return {
        "total_debt": round_currency(total_debt),
        "remaining_balance": round_currency(remaining),
        "total_paid_off": total_paid_off,
        "total_debts": total_debts,
        "debts_cleared": debts_cleared,
        "progress_percent": round_currency((total_paid_off / total_debt) * Decimal("100")) if total_debt > 0 else Decimal("0.00"),
    }


def refresh_scenarios(plan: DebtPlan) -> dict:
    comparisons = create_comparisons(plan_to_engine_payload(plan))
    plan.scenario_comparisons.filter(is_system_generated=True).delete()
    for comparison in comparisons.values():
        summary = comparison["summary"]
        ScenarioComparison.objects.create(
            debt_plan=plan,
            scenario_name=comparison["comparison_label"],
            strategy_type=comparison["strategy"],
            extra_monthly_payment=summary["extra_payment"],
            payoff_date=summary["projected_payoff_date"],
            months_to_payoff=summary["months_to_payoff"],
            total_interest=summary["total_interest"],
            total_paid=summary["total_paid"],
            is_system_generated=True,
        )
    return comparisons


def create_paid_scenario(*, plan: DebtPlan, scenario_name: str, strategy_type: str, extra_monthly_payment) -> ScenarioComparison:
    result = solve_payoff_plan(
        **{
            **plan_to_engine_payload(plan),
            "strategy": strategy_type,
            "extra_payment": extra_monthly_payment,
        }
    )
    summary = result["summary"]
    return ScenarioComparison.objects.create(
        debt_plan=plan,
        scenario_name=scenario_name,
        strategy_type=strategy_type,
        extra_monthly_payment=extra_monthly_payment,
        payoff_date=summary["projected_payoff_date"],
        months_to_payoff=summary["months_to_payoff"],
        total_interest=summary["total_interest"],
        total_paid=summary["total_paid"],
        is_system_generated=False,
    )


def create_saved_plan_from_draft(*, user, draft: dict) -> DebtPlan:
    plan = DebtPlan.objects.create(
        user=user,
        title=draft.get("title") or "Debt Freedom Roadmap",
        household_name=draft.get("household_name") or "",
        strategy_type=draft.get("strategy_type") or DebtPlan.Strategy.SNOWBALL,
        extra_monthly_payment=Decimal(str(draft.get("extra_monthly_payment", "0") or "0")),
        checkin_anchor_date=date.today(),
    )
    debts = draft.get("debts", [])
    for index, debt in enumerate(debts, start=1):
        DebtItem.objects.create(
            debt_plan=plan,
            name=debt["name"],
            lender_name=debt.get("lender_name", ""),
            debt_type=debt.get("debt_type") or DebtItem.DebtType.OTHER,
            balance=Decimal(str(debt["balance"])),
            apr=Decimal(str(debt["apr"])),
            minimum_payment=Decimal(str(debt["minimum_payment"])),
            due_day=debt.get("due_day") or None,
            notes=debt.get("notes", ""),
            custom_order=int(debt.get("custom_order") or index),
        )
    update_plan_summary(plan)
    refresh_scenarios(plan)
    return plan
