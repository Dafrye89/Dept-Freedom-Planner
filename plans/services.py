from decimal import Decimal

from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan

from .models import DebtItem, DebtPlan, ScenarioComparison


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
            "balance": debt.balance,
            "apr": debt.apr,
            "minimum_payment": debt.minimum_payment,
            "due_day": debt.due_day,
            "notes": debt.notes,
            "custom_order": debt.custom_order,
        }
        for debt in plan.debt_items.all()
    ]
    return {
        "title": plan.title,
        "debts": debts,
        "extra_payment": plan.extra_monthly_payment,
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
    )
    debts = draft.get("debts", [])
    for index, debt in enumerate(debts, start=1):
        DebtItem.objects.create(
            debt_plan=plan,
            name=debt["name"],
            lender_name=debt.get("lender_name", ""),
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
