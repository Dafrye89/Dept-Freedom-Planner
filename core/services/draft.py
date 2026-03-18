from copy import deepcopy
from decimal import Decimal

from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan


DRAFT_SESSION_KEY = "debt_freedom_planner_draft"


def default_draft() -> dict:
    return {
        "title": "Debt Freedom Roadmap",
        "household_name": "",
        "strategy_type": "snowball",
        "extra_monthly_payment": "0.00",
        "debts": [],
    }


def get_draft(request) -> dict:
    return deepcopy(request.session.get(DRAFT_SESSION_KEY, default_draft()))


def save_draft(request, draft: dict) -> None:
    request.session[DRAFT_SESSION_KEY] = deepcopy(draft)
    request.session.modified = True


def clear_draft(request) -> None:
    request.session.pop(DRAFT_SESSION_KEY, None)
    request.session.modified = True


def calculate_from_draft(draft: dict) -> tuple[dict, dict]:
    payload = {
        "title": draft.get("title") or "Debt Freedom Roadmap",
        "debts": draft.get("debts", []),
        "extra_payment": Decimal(str(draft.get("extra_monthly_payment", "0") or "0")),
        "strategy": draft.get("strategy_type") or "snowball",
    }
    plan = solve_payoff_plan(**payload)
    comparisons = create_comparisons(payload)
    return plan, comparisons
