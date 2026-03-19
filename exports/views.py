import base64
import csv
from pathlib import Path
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from io import BytesIO

from accounts.services.access import get_capabilities, upgrade_message
from core.services.draft import calculate_from_draft, get_draft
from plans.models import DebtPlan
from plans.services import build_plan_view_data, plan_to_engine_payload
from core.services.schedule import paginate_schedule
from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan

PDF_STYLES = """
body {
  font-family: Helvetica, Arial, sans-serif;
  color: #122340;
  margin: 0;
  padding: 24px;
  font-size: 12px;
}
main {
  display: block;
}
.panel, .summary-card {
  border: 1px solid #d8e1f2;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 18px;
}
.brand-card {
  background: #132d72;
  color: #ffffff;
}
.brand-card__row {
  display: table;
  width: 100%;
}
.brand-card__logo,
.brand-copy {
  display: table-cell;
  vertical-align: middle;
}
.brand-card__logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  padding-right: 12px;
}
.eyebrow {
  display: block;
  text-transform: uppercase;
  font-size: 10px;
  font-weight: 700;
  margin-bottom: 6px;
}
.summary-grid {
  width: 100%;
}
.summary-card {
  display: inline-block;
  width: 46%;
  margin-right: 2%;
  vertical-align: top;
}
.summary-card strong {
  display: block;
  font-size: 20px;
  margin-top: 6px;
}
.muted {
  color: #53657f;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border-bottom: 1px solid #d8e1f2;
  padding: 8px 6px;
  text-align: left;
  vertical-align: top;
}
th {
  text-transform: uppercase;
  font-size: 10px;
  color: #53657f;
}
"""


def _render_pdf_response(request, template_name, context, filename):
    capabilities = context.get("capabilities")
    logo_name = "logo-pro.png" if getattr(capabilities, "is_paid", False) else "logo-light.png"
    logo_bytes = Path(settings.BASE_DIR / "static" / "img" / "branding" / logo_name).read_bytes()
    pdf_context = {
        **context,
        "pdf_mode": True,
        "pdf_styles": PDF_STYLES,
        "branding_logo_data_uri": f"data:image/png;base64,{base64.b64encode(logo_bytes).decode('ascii')}",
    }
    html = render_to_string(template_name, pdf_context, request=request)
    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    except OSError:
        from xhtml2pdf import pisa

        result = BytesIO()
        pdf_status = pisa.CreatePDF(src=html, dest=result)
        if pdf_status.err:
            raise
        pdf_bytes = result.getvalue()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def draft_print(request):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_print:
        messages.warning(request, "Print view is available after you create a free account.")
        return redirect("account_login")
    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "There is no active draft to print.")
        return redirect("core:planner_debts")
    plan, comparisons = calculate_from_draft(draft)
    return render(
        request,
        "exports/printable_plan.html",
        {
            "draft": draft,
            "plan": plan,
            "comparisons": comparisons,
            "print_mode": True,
            "schedule_page_obj": paginate_schedule(plan["schedule"], 1),
            "capabilities": capabilities,
        },
    )


@login_required
def plan_print(request, pk):
    plan_obj = get_object_or_404(DebtPlan.objects.prefetch_related("debt_items"), pk=pk, user=request.user, is_archived=False)
    capabilities = get_capabilities(request.user)
    plan = solve_payoff_plan(**plan_to_engine_payload(plan_obj))
    comparisons = create_comparisons(plan_to_engine_payload(plan_obj))
    return render(
        request,
        "exports/printable_plan.html",
        {
            "saved_plan": plan_obj,
            "plan": plan,
            "comparisons": comparisons,
            "print_mode": True,
            "schedule_page_obj": paginate_schedule(plan["schedule"], 1),
            "capabilities": capabilities,
        },
    )


@login_required
def plan_pdf(request, pk):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_export_pdf:
        messages.warning(request, upgrade_message("PDF export"))
        return redirect("accounts:settings")

    plan_obj = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "monthly_checkins"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    plan_data = build_plan_view_data(plan_obj)
    plan = plan_data["result"]
    comparisons = plan_data["comparisons"]
    full_schedule_page = paginate_schedule(plan["schedule"], 1, page_size=max(len(plan["schedule"]), 18))
    try:
        return _render_pdf_response(
            request,
            "exports/printable_plan.html",
            {
                "saved_plan": plan_obj,
                "plan": plan,
                "comparisons": comparisons,
                "print_mode": True,
                "schedule_page_obj": full_schedule_page,
                "full_schedule_export": True,
                "capabilities": capabilities,
            },
            f"debt-freedom-plan-{plan_obj.pk}.pdf",
        )
    except OSError:
        messages.error(
            request,
            "PDF export is temporarily unavailable on this machine because the PDF rendering libraries are missing.",
        )
        return redirect("exports:plan_print", pk=plan_obj.pk)


@login_required
def plan_csv(request, pk):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_export_pdf:
        messages.warning(request, upgrade_message("CSV export"))
        return redirect("accounts:settings")
    plan_obj = get_object_or_404(
        DebtPlan.objects.prefetch_related("debt_items", "monthly_checkins"),
        pk=pk,
        user=request.user,
        is_archived=False,
    )
    plan_data = build_plan_view_data(plan_obj)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="debt-freedom-plan-{plan_obj.pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Month", "Debt", "Starting Balance", "Interest", "Payment", "Ending Balance", "Status"])
    for row in plan_data["result"]["schedule"]:
        writer.writerow(
            [
                row["month_label"],
                row["debt_name"],
                row["starting_balance"],
                row["interest"],
                row["payment"],
                row["ending_balance"],
                row["status"],
            ]
        )
    return response

# Create your views here.
