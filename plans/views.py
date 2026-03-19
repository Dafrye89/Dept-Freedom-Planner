from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.services.access import get_capabilities, upgrade_message
from core.services.draft import get_draft
from core.services.events import log_event
from core.services.schedule import get_requested_schedule_page, paginate_schedule
from plans.forms import DebtItemFormSet, DebtPlanForm, ScenarioComparisonForm
from plans.models import DebtPlan
from plans.services import (
    create_paid_scenario,
    create_saved_plan_from_draft,
    plan_to_engine_payload,
    refresh_scenarios,
    update_plan_summary,
)
from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan


@login_required
def dashboard(request):
    plans = request.user.debt_plans.filter(is_archived=False).prefetch_related("debt_items")
    return render(
        request,
        "plans/dashboard.html",
        {
            "plans": plans,
        },
    )


@login_required
@require_POST
def save_draft_plan(request):
    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "There is no draft to save yet.")
        return redirect("core:planner_debts")
    capabilities = get_capabilities(request.user)
    if not capabilities.can_save_plans:
        messages.warning(request, upgrade_message("save plans"))
        return redirect("accounts:settings")

    plan = create_saved_plan_from_draft(user=request.user, draft=draft)
    log_event(
        "saved_plan_created",
        user=request.user,
        session_key=request.session.session_key or "",
        metadata={"plan_id": plan.pk},
    )
    messages.success(request, "Your plan was saved.")
    return redirect("plans:detail", pk=plan.pk)


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "scenario_comparisons"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    capabilities = get_capabilities(request.user)
    result = solve_payoff_plan(**plan_to_engine_payload(plan))
    requested_page = get_requested_schedule_page(request.GET.get("schedule_page"))
    if requested_page > 1 and not capabilities.can_view_full_schedule:
        messages.warning(request, upgrade_message("the full monthly schedule"))
        return redirect("accounts:settings")
    schedule_page_obj = paginate_schedule(result["schedule"], requested_page)
    comparisons = create_comparisons(plan_to_engine_payload(plan))
    return render(
        request,
        "plans/detail.html",
        {
            "saved_plan": plan,
            "plan": result,
            "comparisons": comparisons,
            "saved_scenarios": plan.scenario_comparisons.all(),
            "scenario_form": ScenarioComparisonForm(
                initial={
                    "strategy_type": plan.strategy_type,
                    "extra_monthly_payment": plan.extra_monthly_payment,
                }
            ),
            "capabilities": capabilities,
            "schedule_page_obj": schedule_page_obj,
        },
    )


@login_required
def plan_edit(request, pk):
    plan = get_object_or_404(DebtPlan, pk=pk, user=request.user, is_archived=False)
    form = DebtPlanForm(instance=plan, prefix="plan")
    formset = DebtItemFormSet(instance=plan, prefix="debts")

    if request.method == "POST":
        form = DebtPlanForm(request.POST, instance=plan, prefix="plan")
        formset = DebtItemFormSet(request.POST, instance=plan, prefix="debts")
        if form.is_valid() and formset.is_valid():
            plan = form.save()
            formset.instance = plan
            formset.save()
            for index, debt in enumerate(plan.debt_items.filter(), start=1):
                if debt.custom_order != index:
                    debt.custom_order = index
                    debt.save(update_fields=["custom_order"])
            update_plan_summary(plan)
            plan.scenario_comparisons.filter(is_system_generated=False).delete()
            refresh_scenarios(plan)
            messages.success(request, "Your saved plan was updated.")
            return redirect("plans:detail", pk=plan.pk)

    return render(
        request,
        "plans/edit.html",
        {
            "saved_plan": plan,
            "form": form,
            "formset": formset,
        },
    )


@login_required
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(DebtPlan, pk=pk, user=request.user, is_archived=False)
    plan.is_archived = True
    plan.save(update_fields=["is_archived", "updated_at"])
    messages.success(request, "The plan was archived.")
    return redirect("plans:dashboard")


@login_required
@require_POST
def plan_add_scenario(request, pk):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_compare_unlimited:
        messages.warning(request, upgrade_message("custom scenarios"))
        return redirect("accounts:settings")

    plan = get_object_or_404(DebtPlan, pk=pk, user=request.user, is_archived=False)
    form = ScenarioComparisonForm(request.POST)
    if form.is_valid():
        scenario = create_paid_scenario(
            plan=plan,
            scenario_name=form.cleaned_data["scenario_name"],
            strategy_type=form.cleaned_data["strategy_type"],
            extra_monthly_payment=form.cleaned_data["extra_monthly_payment"],
        )
        messages.success(request, f"Scenario '{scenario.scenario_name}' was added.")
    else:
        messages.error(request, "Enter a scenario name, strategy, and extra payment to compare.")
    return redirect("plans:detail", pk=plan.pk)

# Create your views here.
