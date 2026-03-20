from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.services.access import get_capabilities, upgrade_message
from billing.services import is_stripe_configured
from core.services.draft import get_draft
from core.services.events import log_event
from core.services.schedule import get_requested_schedule_page, paginate_schedule
from plans.forms import DebtItemFormSet, DebtPlanForm, MonthlyCheckInForm, PlanPaceUpdateForm, ScenarioComparisonForm
from plans.models import DebtPlan, MonthlyCheckIn
from plans.services import (
    aggregate_dashboard_progress,
    build_plan_view_data,
    create_paid_scenario,
    create_saved_plan_from_draft,
    get_due_checkin,
    plan_to_engine_payload,
    refresh_scenarios,
    save_monthly_checkin,
    save_plan_pace_update,
    sync_plan_badges,
    update_plan_summary,
)
from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan


@login_required
def dashboard(request):
    plans = list(
        request.user.debt_plans.filter(is_archived=False).prefetch_related("debt_items", "monthly_checkins", "badge_awards")
    )
    plan_cards = []
    for plan in plans:
        plan_data = build_plan_view_data(plan)
        plan_cards.append(
            {
                "saved_plan": plan,
                "progress": plan_data["progress"],
                "due_checkin": plan_data["due_checkin"],
                "badges": plan_data["badges"][:4],
                "new_badges": plan_data["new_badges"],
            }
        )
    due_checkins = [card for card in plan_cards if card["due_checkin"]]
    return render(
        request,
        "plans/dashboard.html",
        {
            "plans": plans,
            "plan_cards": plan_cards,
            "dashboard_progress": aggregate_dashboard_progress(plans),
            "due_checkins": due_checkins,
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
        DebtPlan.objects.prefetch_related("debt_items", "scenario_comparisons", "monthly_checkins", "badge_awards"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    capabilities = get_capabilities(request.user)
    plan_data = build_plan_view_data(plan)
    result = plan_data["result"]
    requested_page = get_requested_schedule_page(request.GET.get("schedule_page"))
    if requested_page > 1 and not capabilities.can_view_full_schedule:
        messages.warning(request, upgrade_message("the full monthly schedule"))
        return redirect("accounts:settings")
    schedule_page_obj = paginate_schedule(result["schedule"], requested_page)
    return render(
        request,
        "plans/detail.html",
        {
            "saved_plan": plan,
            "plan": result,
            "comparisons": plan_data["comparisons"],
            "saved_scenarios": plan.scenario_comparisons.all(),
            "scenario_form": ScenarioComparisonForm(
                initial={
                    "strategy_type": plan.strategy_type,
                    "extra_monthly_payment": plan.extra_monthly_payment,
                }
            ),
            "pace_form": PlanPaceUpdateForm(initial_extra_payment=plan.extra_monthly_payment),
            "monthly_checkin_form": MonthlyCheckInForm(),
            "capabilities": capabilities,
            "schedule_page_obj": schedule_page_obj,
            "due_checkin": plan_data["due_checkin"],
            "badges": plan_data["badges"],
            "new_badges": plan_data["new_badges"],
            "progress": plan_data["progress"],
            "stripe_enabled": is_stripe_configured(),
            "stripe_pro_monthly_price": settings.STRIPE_PRO_MONTHLY_PRICE,
            "stripe_trial_period_days": settings.STRIPE_TRIAL_PERIOD_DAYS,
        },
    )


@login_required
def plan_edit(request, pk):
    plan = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "monthly_checkins"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
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
            result = update_plan_summary(plan)
            plan.scenario_comparisons.filter(is_system_generated=False).delete()
            refresh_scenarios(plan)
            sync_plan_badges(plan, result)
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


@login_required
@require_POST
def plan_update_pace(request, pk):
    plan = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "monthly_checkins"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    form = PlanPaceUpdateForm(request.POST, initial_extra_payment=plan.extra_monthly_payment)
    if form.is_valid():
        save_plan_pace_update(plan=plan, extra_monthly_payment=form.cleaned_data["extra_monthly_payment"])
        messages.success(request, "The extra monthly payment was updated.")
    else:
        messages.error(request, "Choose a preset amount or enter a custom extra payment.")
    return redirect("plans:detail", pk=plan.pk)


@login_required
@require_POST
def plan_submit_checkin(request, pk):
    plan = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "monthly_checkins", "badge_awards"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    due_checkin = get_due_checkin(plan)
    if due_checkin is None:
        messages.info(request, "There is no monthly check-in due for this plan right now.")
        return redirect("plans:detail", pk=plan.pk)
    form = MonthlyCheckInForm(request.POST)
    if form.is_valid():
        save_monthly_checkin(
            plan=plan,
            month_index=due_checkin["month_index"],
            status=form.cleaned_data["status"],
            custom_extra_payment=form.cleaned_data.get("extra_monthly_payment"),
        )
        result = update_plan_summary(plan)
        refresh_scenarios(plan)
        new_badges = sync_plan_badges(plan, result)
        if new_badges:
            messages.success(request, f"You unlocked {len(new_badges)} new badge{'s' if len(new_badges) != 1 else ''}.")
        else:
            messages.success(request, "Your monthly check-in was saved.")
    else:
        messages.error(request, "Answer the monthly check-in before continuing.")
    return redirect("plans:detail", pk=plan.pk)


@login_required
@require_POST
def plan_toggle_checkins(request, pk):
    plan = get_object_or_404(DebtPlan, pk=pk, user=request.user, is_archived=False)
    plan.checkins_active = not plan.checkins_active
    if not plan.checkin_anchor_date:
        plan.checkin_anchor_date = plan.created_at.date()
    plan.save(update_fields=["checkins_active", "checkin_anchor_date", "updated_at"])
    messages.success(
        request,
        "Monthly check-ins are active for this plan." if plan.checkins_active else "Monthly check-ins are paused for this plan.",
    )
    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("plans:detail", pk=plan.pk)

# Create your views here.
