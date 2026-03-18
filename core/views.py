from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.services.access import can_create_plan
from core.services.draft import calculate_from_draft, clear_draft, default_draft, get_draft, save_draft
from core.services.events import log_event
from plans.forms import DebtDraftFormSet, DraftPlanDetailsForm, StrategySelectionForm


SAMPLE_DRAFT = {
    "title": "Debt Freedom Roadmap",
    "household_name": "The Freedom Household",
    "strategy_type": "snowball",
    "extra_monthly_payment": "350.00",
    "debts": [
        {
            "name": "Freedom Card",
            "lender_name": "Liberty Bank",
            "balance": "2480.00",
            "apr": "24.99",
            "minimum_payment": "95.00",
            "due_day": 12,
            "notes": "Used for groceries and unexpected repairs.",
            "custom_order": 1,
        },
        {
            "name": "General Store Card",
            "lender_name": "General Market",
            "balance": "3100.00",
            "apr": "19.50",
            "minimum_payment": "90.00",
            "due_day": 18,
            "notes": "",
            "custom_order": 2,
        },
        {
            "name": "Truck Loan",
            "lender_name": "Roadway Credit",
            "balance": "11700.00",
            "apr": "7.20",
            "minimum_payment": "315.00",
            "due_day": 4,
            "notes": "",
            "custom_order": 3,
        },
    ],
}


@require_GET
def home(request):
    if request.user.is_authenticated:
        return redirect("plans:dashboard")
    sample_plan, sample_comparisons = calculate_from_draft(SAMPLE_DRAFT)
    return render(
        request,
        "core/home.html",
        {
            "sample_plan": sample_plan,
            "sample_comparisons": sample_comparisons,
        },
    )


@require_http_methods(["GET", "POST"])
def planner_start(request):
    clear_draft(request)
    save_draft(request, default_draft())
    log_event("planner_started", user=request.user, session_key=request.session.session_key or "")
    return redirect("core:planner_debts")


@require_http_methods(["GET", "POST"])
def planner_debts(request):
    draft = get_draft(request)
    initial_debts = draft.get("debts") or [{}]

    details_form = DraftPlanDetailsForm(
        prefix="details",
        initial={
            "title": draft.get("title") or "Debt Freedom Roadmap",
            "household_name": draft.get("household_name") or "",
        },
    )
    debt_formset = DebtDraftFormSet(prefix="debts", initial=initial_debts)

    if request.method == "POST":
        details_form = DraftPlanDetailsForm(request.POST, prefix="details")
        debt_formset = DebtDraftFormSet(request.POST, prefix="debts")
        for form in debt_formset.forms:
            field_names = ["name", "balance", "apr", "minimum_payment", "lender_name", "due_day", "notes", "custom_order"]
            has_any_value = any(request.POST.get(form.add_prefix(field), "").strip() for field in field_names)
            if not has_any_value:
                form.empty_permitted = True
        if details_form.is_valid() and debt_formset.is_valid():
            cleaned_debts = []
            for index, form in enumerate(debt_formset.forms, start=1):
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                cleaned_debts.append(
                    {
                        "name": form.cleaned_data["name"],
                        "lender_name": form.cleaned_data.get("lender_name", ""),
                        "balance": str(form.cleaned_data["balance"]),
                        "apr": str(form.cleaned_data["apr"]),
                        "minimum_payment": str(form.cleaned_data["minimum_payment"]),
                        "due_day": form.cleaned_data.get("due_day") or "",
                        "notes": form.cleaned_data.get("notes", ""),
                        "custom_order": form.cleaned_data.get("custom_order") or index,
                    }
                )

            if not cleaned_debts:
                messages.error(request, "Add at least one debt before continuing.")
            else:
                draft.update(details_form.cleaned_data)
                draft["debts"] = cleaned_debts
                save_draft(request, draft)
                log_event(
                    "planner_debts_saved",
                    user=request.user,
                    session_key=request.session.session_key or "",
                    metadata={"debt_count": len(cleaned_debts)},
                )
                return redirect("core:planner_strategy")

    return render(
        request,
        "core/planner_debts.html",
        {
            "details_form": details_form,
            "debt_formset": debt_formset,
        },
    )


@require_http_methods(["GET", "POST"])
def planner_strategy(request):
    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "Start by entering your debts.")
        return redirect("core:planner_debts")

    strategy_form = StrategySelectionForm(
        prefix="strategy",
        initial={
            "strategy_type": draft.get("strategy_type") or "snowball",
            "extra_monthly_payment": draft.get("extra_monthly_payment") or "0.00",
        },
    )

    preview_plan, preview_comparisons = calculate_from_draft(draft)

    if request.method == "POST":
        strategy_form = StrategySelectionForm(request.POST, prefix="strategy")
        if strategy_form.is_valid():
            draft["strategy_type"] = strategy_form.cleaned_data["strategy_type"]
            draft["extra_monthly_payment"] = str(strategy_form.cleaned_data["extra_monthly_payment"])
            save_draft(request, draft)
            log_event(
                "planner_strategy_saved",
                user=request.user,
                session_key=request.session.session_key or "",
                metadata={
                    "strategy": draft["strategy_type"],
                    "extra_monthly_payment": draft["extra_monthly_payment"],
                },
            )
            return redirect("core:planner_results")

        preview_draft = draft | {
            "strategy_type": request.POST.get("strategy-strategy_type", draft.get("strategy_type")),
            "extra_monthly_payment": request.POST.get(
                "strategy-extra_monthly_payment",
                draft.get("extra_monthly_payment"),
            ),
        }
        preview_plan, preview_comparisons = calculate_from_draft(preview_draft)

    return render(
        request,
        "core/planner_strategy.html",
        {
            "strategy_form": strategy_form,
            "preview_plan": preview_plan,
            "preview_comparisons": preview_comparisons,
        },
    )


@require_POST
def strategy_preview(request):
    draft = get_draft(request)
    preview_draft = draft | {
        "strategy_type": request.POST.get("strategy-strategy_type", draft.get("strategy_type")),
        "extra_monthly_payment": request.POST.get(
            "strategy-extra_monthly_payment",
            draft.get("extra_monthly_payment"),
        ),
    }
    preview_plan, preview_comparisons = calculate_from_draft(preview_draft)
    return render(
        request,
        "partials/strategy_preview.html",
        {
            "preview_plan": preview_plan,
            "preview_comparisons": preview_comparisons,
        },
    )


@require_GET
def planner_results(request):
    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "Start by entering your debts.")
        return redirect("core:planner_debts")

    plan, comparisons = calculate_from_draft(draft)
    return render(
        request,
        "core/planner_results.html",
        {
            "draft": draft,
            "plan": plan,
            "comparisons": comparisons,
            "can_save_current_plan": can_create_plan(request.user) if request.user.is_authenticated else False,
        },
    )

# Create your views here.
