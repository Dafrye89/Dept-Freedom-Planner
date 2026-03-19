from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


MAX_MONTHS = 600
EPSILON = Decimal("0.005")


def round_currency(value: Decimal | float | int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def month_label(value: date) -> str:
    return value.strftime("%b %Y")


def add_months(base: date, months_to_add: int) -> date:
    year = base.year + ((base.month - 1 + months_to_add) // 12)
    month = ((base.month - 1 + months_to_add) % 12) + 1
    return date(year, month, 1)


@dataclass
class DebtState:
    id: str
    name: str
    lender: str
    debt_type: str
    balance: Decimal
    apr: Decimal
    minimum_payment: Decimal
    due_day: str
    notes: str
    custom_rank: int
    current_balance: Decimal
    paid_off_month: int | None = None
    total_interest: Decimal = Decimal("0.00")
    total_paid: Decimal = Decimal("0.00")


def normalize_debt(raw: dict, index: int) -> DebtState:
    balance = round_currency(max(Decimal(str(raw.get("balance", 0))), Decimal("0")))
    minimum_payment = round_currency(max(Decimal(str(raw.get("minimum_payment", raw.get("minimumPayment", 0)))), Decimal("0")))
    apr = round_currency(max(Decimal(str(raw.get("apr", 0))), Decimal("0")))
    return DebtState(
        id=str(raw.get("id") or f"debt-{index + 1}"),
        name=(raw.get("name") or f"Debt {index + 1}").strip(),
        lender=(raw.get("lender") or raw.get("lender_name") or "").strip(),
        debt_type=(raw.get("debt_type") or raw.get("debtType") or "other_debt").strip(),
        balance=balance,
        apr=apr,
        minimum_payment=minimum_payment,
        due_day=str(raw.get("due_day") or raw.get("dueDay") or ""),
        notes=(raw.get("notes") or "").strip(),
        custom_rank=int(raw.get("custom_rank") or raw.get("custom_order") or raw.get("customRank") or index + 1),
        current_balance=balance,
    )


def strategy_label(strategy: str) -> str:
    return {
        "snowball": "Snowball",
        "avalanche": "Avalanche",
        "custom": "Custom",
    }.get(strategy, "Snowball")


def debt_type_label(debt_type: str) -> str:
    return {
        "credit_card": "Credit Card",
        "vehicle": "Vehicle",
        "mortgage": "Mortgage",
        "bank_loan": "Bank Loan",
        "payday_loan": "Payday Loan",
        "personal_loan": "Personal Loan",
        "student_loan": "Student Loan",
        "other_debt": "Other Debt",
    }.get(debt_type, "Other Debt")


def sort_debts(active_debts: list[DebtState], strategy: str) -> list[DebtState]:
    if strategy == "avalanche":
        return sorted(active_debts, key=lambda debt: (-debt.apr, debt.balance, debt.name))
    if strategy == "custom":
        return sorted(active_debts, key=lambda debt: (debt.custom_rank, debt.name))
    return sorted(active_debts, key=lambda debt: (debt.balance, -debt.apr, debt.name))


def build_current_snapshot(debt_states: list[DebtState], *, month_index: int, month_date: date, total_debt: Decimal) -> dict:
    remaining_balance = round_currency(sum(debt.current_balance for debt in debt_states))
    total_paid_off = round_currency(total_debt - remaining_balance)
    debts_cleared = sum(1 for debt in debt_states if debt.current_balance <= EPSILON)
    total_debts = len(debt_states)
    snapshot_debts = [
        {
            "id": debt.id,
            "name": debt.name,
            "debt_type": debt.debt_type,
            "debt_type_label": debt_type_label(debt.debt_type),
            "remaining_balance": round_currency(max(debt.current_balance, Decimal("0"))),
            "paid_off": debt.current_balance <= EPSILON,
        }
        for debt in debt_states
    ]
    return {
        "month_index": month_index,
        "month_label": month_label(month_date),
        "remaining_balance": remaining_balance,
        "total_paid_off": total_paid_off,
        "debts_cleared": debts_cleared,
        "total_debts": total_debts,
        "progress_percent": round_currency((total_paid_off / total_debt) * Decimal("100")) if total_debt > 0 else Decimal("100.00"),
        "paid_off_debt_ids": [debt["id"] for debt in snapshot_debts if debt["paid_off"]],
        "debts": snapshot_debts,
    }


def solve_payoff_plan(
    *,
    debts: list[dict],
    extra_payment: Decimal | float | int = 0,
    monthly_extra_payments: dict[int, Decimal | float | int] | None = None,
    actual_snapshot_month_index: int = 0,
    strategy: str = "snowball",
    start_date: date | None = None,
    title: str = "Debt Freedom Plan",
) -> dict:
    normalized = []
    for index, debt in enumerate(debts):
        normalized_debt = normalize_debt(debt, index)
        if normalized_debt.balance > 0 and normalized_debt.minimum_payment > 0:
            normalized.append(normalized_debt)
    extra = round_currency(max(Decimal(str(extra_payment)), Decimal("0")))
    monthly_override_map = {
        int(month_index): round_currency(max(Decimal(str(value)), Decimal("0")))
        for month_index, value in (monthly_extra_payments or {}).items()
        if int(month_index) > 0
    }
    simulation_start = date((start_date or date.today()).year, (start_date or date.today()).month, 1)

    if not normalized:
        return {
            "title": title,
            "strategy": strategy,
            "strategy_label": strategy_label(strategy),
            "summary": {
                "total_debt": Decimal("0.00"),
                "months_to_payoff": 0,
                "total_interest": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "total_minimums": Decimal("0.00"),
                "extra_payment": extra,
                "monthly_payment": extra,
                "projected_payoff_date_label": month_label(simulation_start),
                "projected_payoff_date": simulation_start,
                "payoff_order": [],
                "first_target": None,
                "fastest_win_months": 0,
            },
            "debts": [],
            "monthly_totals": [],
            "schedule": [],
            "current_snapshot": build_current_snapshot([], month_index=0, month_date=simulation_start, total_debt=Decimal("0.00")),
            "status": "empty",
        }

    debt_state = normalized
    base_order = sort_debts(debt_state, strategy)
    focus_rank_map = {debt.id: rank for rank, debt in enumerate(base_order, start=1)}
    total_debt = round_currency(sum(debt.balance for debt in normalized))
    schedule: list[dict] = []
    payoff_order: list[dict] = []
    monthly_totals: list[dict] = []
    total_interest = Decimal("0.00")
    total_paid = Decimal("0.00")
    stalled_months = 0
    current_snapshot = build_current_snapshot(
        debt_state,
        month_index=0,
        month_date=simulation_start,
        total_debt=total_debt,
    )

    for month_index in range(MAX_MONTHS):
        active = [debt for debt in debt_state if debt.current_balance > EPSILON]
        if not active:
            break

        current_order = sort_debts(active, strategy)
        month_date = add_months(simulation_start, month_index)
        month_rows: list[dict] = []
        applied_extra_payment = monthly_override_map.get(month_index + 1, extra)
        extra_remaining = applied_extra_payment
        month_interest = Decimal("0.00")
        month_paid = Decimal("0.00")
        total_starting_balance = round_currency(sum(debt.current_balance for debt in active))

        for debt in current_order:
            starting_balance = round_currency(debt.current_balance)
            interest = round_currency(starting_balance * (debt.apr / Decimal("100") / Decimal("12")))
            balance_after_interest = round_currency(starting_balance + interest)
            minimum_payment = round_currency(min(balance_after_interest, debt.minimum_payment))
            debt.current_balance = round_currency(balance_after_interest - minimum_payment)
            debt.total_interest = round_currency(debt.total_interest + interest)
            debt.total_paid = round_currency(debt.total_paid + minimum_payment)
            total_interest = round_currency(total_interest + interest)
            total_paid = round_currency(total_paid + minimum_payment)
            month_interest = round_currency(month_interest + interest)
            month_paid = round_currency(month_paid + minimum_payment)

            month_rows.append(
                {
                    "month_index": month_index + 1,
                    "month_label": month_label(month_date),
                    "debt_id": debt.id,
                    "debt_name": debt.name,
                    "strategy": strategy,
                    "debt_type": debt.debt_type,
                    "debt_type_label": debt_type_label(debt.debt_type),
                    "starting_balance": starting_balance,
                    "interest": interest,
                    "payment": minimum_payment,
                    "ending_balance": round_currency(max(debt.current_balance, Decimal("0"))),
                    "status": "Paid off" if debt.current_balance <= EPSILON else "Active",
                }
            )

        while extra_remaining > EPSILON:
            targets = sort_debts([debt for debt in debt_state if debt.current_balance > EPSILON], strategy)
            if not targets:
                break
            target = targets[0]
            applied_extra = round_currency(min(target.current_balance, extra_remaining))
            if applied_extra <= EPSILON:
                break

            target.current_balance = round_currency(target.current_balance - applied_extra)
            target.total_paid = round_currency(target.total_paid + applied_extra)
            total_paid = round_currency(total_paid + applied_extra)
            month_paid = round_currency(month_paid + applied_extra)
            extra_remaining = round_currency(extra_remaining - applied_extra)

            target_row = next((row for row in month_rows if row["debt_id"] == target.id), None)
            if target_row:
                target_row["payment"] = round_currency(target_row["payment"] + applied_extra)
                target_row["ending_balance"] = round_currency(max(target.current_balance, Decimal("0")))
                target_row["status"] = "Paid off" if target.current_balance <= EPSILON else "Active"

        for debt in debt_state:
            if debt.current_balance <= EPSILON:
                debt.current_balance = Decimal("0.00")
                if debt.paid_off_month is None:
                    debt.paid_off_month = month_index + 1
                    payoff_order.append(
                        {
                            "debt_id": debt.id,
                            "debt_name": debt.name,
                            "month_index": debt.paid_off_month,
                        }
                    )

        total_ending_balance = round_currency(sum(debt.current_balance for debt in debt_state))
        monthly_totals.append(
            {
                "month_index": month_index + 1,
                "month_label": month_label(month_date),
                "total_starting_balance": total_starting_balance,
                "total_ending_balance": total_ending_balance,
                "interest": month_interest,
                "payment": month_paid,
                "extra_payment": applied_extra_payment,
            }
        )
        schedule.extend(month_rows)
        if actual_snapshot_month_index == month_index + 1:
            current_snapshot = build_current_snapshot(
                debt_state,
                month_index=month_index + 1,
                month_date=month_date,
                total_debt=total_debt,
            )

        if total_ending_balance >= total_starting_balance - EPSILON:
            stalled_months += 1
        else:
            stalled_months = 0

        if stalled_months >= 3:
            return {
                "title": title,
                "strategy": strategy,
                "strategy_label": strategy_label(strategy),
                "summary": {
                    "total_debt": total_debt,
                    "months_to_payoff": month_index + 1,
                    "total_interest": total_interest,
                    "total_paid": total_paid,
                    "total_minimums": round_currency(sum(debt.minimum_payment for debt in normalized)),
                    "extra_payment": extra,
                    "monthly_payment": round_currency(sum(debt.minimum_payment for debt in normalized) + extra),
                    "projected_payoff_date_label": "Plan needs a larger payment",
                    "projected_payoff_date": None,
                    "payoff_order": payoff_order,
                    "first_target": base_order[0].name if base_order else None,
                    "fastest_win_months": payoff_order[0]["month_index"] if payoff_order else 0,
                },
                "debts": debt_state,
                "monthly_totals": monthly_totals,
                "schedule": schedule,
                "current_snapshot": current_snapshot,
                "status": "stalled",
            }

    months_to_payoff = len(monthly_totals)
    payoff_date = add_months(simulation_start, months_to_payoff - 1) if months_to_payoff else simulation_start

    return {
        "title": title,
        "strategy": strategy,
        "strategy_label": strategy_label(strategy),
        "summary": {
            "total_debt": total_debt,
            "months_to_payoff": months_to_payoff,
            "total_interest": total_interest,
            "total_paid": total_paid,
            "total_minimums": round_currency(sum(debt.minimum_payment for debt in normalized)),
            "extra_payment": extra,
            "monthly_payment": round_currency(sum(debt.minimum_payment for debt in normalized) + extra),
            "projected_payoff_date_label": month_label(payoff_date),
            "projected_payoff_date": payoff_date,
            "payoff_order": payoff_order,
            "first_target": base_order[0].name if base_order else None,
            "fastest_win_months": payoff_order[0]["month_index"] if payoff_order else 0,
        },
        "debts": [
            {
                "id": debt.id,
                "name": debt.name,
                "lender": debt.lender,
                "debt_type": debt.debt_type,
                "debt_type_label": debt_type_label(debt.debt_type),
                "balance": debt.balance,
                "apr": debt.apr,
                "minimum_payment": debt.minimum_payment,
                "due_day": debt.due_day,
                "notes": debt.notes,
                "custom_rank": debt.custom_rank,
                "current_balance": debt.current_balance,
                "paid_off_month": debt.paid_off_month,
                "projected_payoff_month_label": (
                    month_label(add_months(simulation_start, debt.paid_off_month - 1))
                    if debt.paid_off_month
                    else "Still active"
                ),
                "total_interest": debt.total_interest,
                "total_paid": debt.total_paid,
                "focus_rank": focus_rank_map.get(debt.id, debt.custom_rank),
                "progress": round_currency(((debt.balance - debt.current_balance) / debt.balance) * Decimal("100"))
                if debt.balance > 0
                else Decimal("100.00"),
            }
            for debt in debt_state
        ],
        "monthly_totals": monthly_totals,
        "schedule": schedule,
        "current_snapshot": current_snapshot,
        "status": "complete",
    }


def create_comparisons(plan_input: dict) -> dict:
    snowball = solve_payoff_plan(**{**plan_input, "strategy": "snowball"})
    snowball["comparison_label"] = "Snowball"
    avalanche = solve_payoff_plan(**{**plan_input, "strategy": "avalanche"})
    avalanche["comparison_label"] = "Avalanche"
    custom = solve_payoff_plan(**{**plan_input, "strategy": "custom"})
    custom["comparison_label"] = "Custom order"
    accelerated = solve_payoff_plan(
        **{
            **plan_input,
            "extra_payment": round_currency(Decimal(str(plan_input.get("extra_payment", 0))) + Decimal("150")),
        }
    )
    accelerated["comparison_label"] = "Add $150 more"
    return {
        "snowball": snowball,
        "avalanche": avalanche,
        "custom": custom,
        "accelerated": accelerated,
    }
