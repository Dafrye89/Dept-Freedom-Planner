import csv
from decimal import Decimal, InvalidOperation
from io import BytesIO
import textwrap

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.services.access import get_capabilities, upgrade_message
from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan
from core.services.draft import calculate_from_draft, get_draft
from core.services.schedule import paginate_schedule
from plans.models import DebtItem, DebtPlan
from plans.services import build_plan_view_data, plan_to_engine_payload


def _currency(value) -> str:
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    return f"${amount:,.2f}"


def _debt_type_label(value: str) -> str:
    return dict(DebtItem.DebtType.choices).get(value, "Other Debt")


def _format_payoff_date(value) -> str:
    if value is None:
        return "Needs larger payment"
    return value.strftime("%B %Y")


def _summary_rows(plan: dict) -> list[list[str]]:
    summary = plan["summary"]
    return [
        ["Debt-free date", summary["projected_payoff_date_label"]],
        ["Total debt", _currency(summary["total_debt"])],
        ["Total interest", _currency(summary["total_interest"])],
        ["Total paid", _currency(summary["total_paid"])],
        ["Monthly payment", _currency(summary["monthly_payment"])],
        ["First target", str(summary["first_target"])],
    ]


def _debt_rows_from_context(context: dict) -> list[list[str]]:
    saved_plan = context.get("saved_plan")
    if saved_plan is not None:
        debts = saved_plan.debt_items.all()
        return [
            [
                debt.name,
                debt.lender_name or "-",
                debt.get_debt_type_display(),
                _currency(debt.balance),
                f"{debt.apr:.2f}%",
                _currency(debt.minimum_payment),
            ]
            for debt in debts
        ]

    draft = context.get("draft") or {}
    return [
        [
            debt.get("name", ""),
            debt.get("lender_name", "") or "-",
            _debt_type_label(debt.get("debt_type", "")),
            _currency(debt.get("balance")),
            f"{Decimal(str(debt.get('apr', '0') or '0')):.2f}%",
            _currency(debt.get("minimum_payment")),
        ]
        for debt in draft.get("debts", [])
    ]


def _comparison_rows(comparisons: dict) -> list[list[str]]:
    rows = []
    for comparison in comparisons.values():
        summary = comparison["summary"]
        rows.append(
            [
                comparison["comparison_label"],
                _format_payoff_date(summary["projected_payoff_date"]),
                str(summary["months_to_payoff"]),
                _currency(summary["total_interest"]),
                _currency(summary["extra_payment"]),
            ]
        )
    return rows


def _build_pdf_lines(context: dict) -> list[str]:
    plan = context["plan"]
    saved_plan = context.get("saved_plan")
    draft = context.get("draft") or {}
    comparisons = context.get("comparisons") or {}
    title = saved_plan.title if saved_plan else draft.get("title", "Debt Freedom Roadmap")
    household = saved_plan.household_name if saved_plan else draft.get("household_name", "Debt payoff plan")
    lines = [
        "Debt Freedom Planner",
        title,
        household,
        "",
        "SUMMARY",
    ]
    for label, value in _summary_rows(plan):
        lines.append(f"{label}: {value}")

    lines.extend(["", "DEBTS"])
    for row in _debt_rows_from_context(context):
        lines.append(f"{row[0]} | {row[2]} | {row[3]} at {row[4]} | minimum {row[5]}")
        if row[1] != "-":
            lines.append(f"Lender: {row[1]}")

    if comparisons:
        lines.extend(["", "STRATEGY COMPARISON"])
        for row in _comparison_rows(comparisons):
            lines.append(f"{row[0]} | payoff {row[1]} | {row[2]} months | interest {row[3]} | extra {row[4]}")

    lines.extend(
        [
            "",
            "MONTHLY PAYOFF SCHEDULE",
            "Month       Debt                 Starting      Interest      Payment        Ending       Status",
        ]
    )
    for row in plan["schedule"]:
        lines.append(
            f"{row['month_label'][:11]:<11} {row['debt_name'][:20]:<20} "
            f"{_currency(row['starting_balance']):>11} {_currency(row['interest']):>12} "
            f"{_currency(row['payment']):>12} {_currency(row['ending_balance']):>12} {row['status']}"
        )
    lines.extend(
        [
            "",
            "Debt Freedom Planner is an educational payoff-planning tool and not legal, tax, or financial advice.",
        ]
    )
    return lines


def _build_simple_pdf_bytes(lines: list[str]) -> bytes:
    max_lines_per_page = 56
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped = textwrap.wrap(line, width=96, replace_whitespace=False, drop_whitespace=False) or [""]
        wrapped_lines.extend(wrapped)
    pages = [wrapped_lines[index : index + max_lines_per_page] for index in range(0, len(wrapped_lines), max_lines_per_page)] or [[]]

    def escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects: list[bytes | None] = [None, None, None, b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"]
    page_refs = []
    for page_lines in pages:
        stream_lines = ["BT", "/F1 10 Tf", "50 748 Td", "13 TL"]
        for index, line in enumerate(page_lines):
            operator = "Tj" if index == 0 else "T*"
            if index == 0:
                stream_lines.append(f"({escape_pdf_text(line)}) {operator}")
            else:
                stream_lines.append(f"{operator} ({escape_pdf_text(line)}) Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
        content_id = len(objects)
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        page_id = len(objects)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode(
                "latin-1"
            )
        )
        page_refs.append(f"{page_id} 0 R")

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>".encode("latin-1")

    pdf = BytesIO()
    pdf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id in range(1, len(objects)):
        offsets.append(pdf.tell())
        pdf.write(f"{object_id} 0 obj\n".encode("latin-1"))
        pdf.write(objects[object_id] or b"")
        pdf.write(b"\nendobj\n")
    xref_offset = pdf.tell()
    pdf.write(f"xref\n0 {len(objects)}\n".encode("latin-1"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.write(
        f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    )
    return pdf.getvalue()


def _build_pdf_response(context, filename):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        response = HttpResponse(_build_simple_pdf_bytes(_build_pdf_lines(context)), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def build_table(data, column_widths, header_background=colors.HexColor("#132d72")):
        table = Table(data, colWidths=column_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_background),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#122340")),
                    ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#d8e1f2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ]
            )
        )
        return table

    capabilities = context.get("capabilities")
    logo_name = "logo-pro.png" if getattr(capabilities, "is_paid", False) else "logo-light.png"
    logo_path = settings.BASE_DIR / "static" / "img" / "branding" / logo_name
    plan = context["plan"]
    saved_plan = context.get("saved_plan")
    draft = context.get("draft") or {}
    comparisons = context.get("comparisons") or {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=saved_plan.title if saved_plan else draft.get("title", "Debt Freedom Planner"),
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PlannerTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=colors.HexColor("#132d72"),
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "PlannerSubtitle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#53657f"),
        spaceAfter=12,
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.HexColor("#132d72"),
        spaceBefore=10,
        spaceAfter=8,
    )
    footer_style = ParagraphStyle(
        "PlannerFooter",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#53657f"),
        spaceBefore=10,
    )

    story = []
    if logo_path.exists():
        story.append(Image(str(logo_path), width=1.0 * inch, height=1.0 * inch))
        story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Debt Freedom Planner", subtitle_style))
    story.append(Paragraph(saved_plan.title if saved_plan else draft.get("title", "Debt Freedom Roadmap"), title_style))
    story.append(
        Paragraph(
            saved_plan.household_name if saved_plan else draft.get("household_name", "Debt payoff plan"),
            subtitle_style,
        )
    )

    summary_table = build_table(
        [["Summary", "Value"], *_summary_rows(plan)],
        [2.3 * inch, 4.6 * inch],
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Accounts included in this plan", section_title))
    debt_rows = _debt_rows_from_context(context)
    story.append(
        build_table(
            [["Debt", "Lender", "Type", "Balance", "APR", "Minimum"], *debt_rows],
            [1.55 * inch, 1.35 * inch, 1.15 * inch, 1.0 * inch, 0.7 * inch, 1.0 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    if comparisons:
        story.append(Paragraph("Strategy comparison", section_title))
        story.append(
            build_table(
                [["Strategy", "Payoff date", "Months", "Interest", "Extra payment"], *_comparison_rows(comparisons)],
                [1.8 * inch, 1.3 * inch, 0.8 * inch, 1.1 * inch, 1.2 * inch],
            )
        )
        story.append(Spacer(1, 0.18 * inch))

    story.append(PageBreak())
    story.append(Paragraph("Full monthly payoff schedule", section_title))
    schedule_rows = plan["schedule"]
    header = ["Month", "Debt", "Starting", "Interest", "Payment", "Ending", "Status"]
    chunk_size = 30
    for index in range(0, len(schedule_rows), chunk_size):
        chunk = schedule_rows[index : index + chunk_size]
        story.append(
            build_table(
                [
                    header,
                    *[
                        [
                            row["month_label"],
                            row["debt_name"],
                            _currency(row["starting_balance"]),
                            _currency(row["interest"]),
                            _currency(row["payment"]),
                            _currency(row["ending_balance"]),
                            row["status"],
                        ]
                        for row in chunk
                    ],
                ],
                [0.9 * inch, 1.45 * inch, 0.95 * inch, 0.75 * inch, 0.9 * inch, 0.95 * inch, 0.9 * inch],
            )
        )
        if index + chunk_size < len(schedule_rows):
            story.append(Spacer(1, 0.12 * inch))
    story.append(
        Paragraph(
            "Debt Freedom Planner is an educational payoff-planning tool and not legal, tax, or financial advice.",
            footer_style,
        )
    )
    doc.build(story)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
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
def draft_pdf(request):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_export_pdf:
        messages.warning(request, upgrade_message("PDF export"))
        return redirect("accounts:settings")

    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "There is no active draft to export yet.")
        return redirect("core:planner_debts")

    plan, comparisons = calculate_from_draft(draft)
    return _build_pdf_response(
        {
            "draft": draft,
            "plan": plan,
            "comparisons": comparisons,
            "capabilities": capabilities,
        },
        "debt-freedom-draft-plan.pdf",
    )


@login_required
def draft_csv(request):
    capabilities = get_capabilities(request.user)
    if not capabilities.can_export_pdf:
        messages.warning(request, upgrade_message("CSV export"))
        return redirect("accounts:settings")

    draft = get_draft(request)
    if not draft.get("debts"):
        messages.warning(request, "There is no active draft to export yet.")
        return redirect("core:planner_debts")

    plan, _comparisons = calculate_from_draft(draft)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="debt-freedom-draft-plan.csv"'
    writer = csv.writer(response)
    writer.writerow(["Month", "Debt", "Starting Balance", "Interest", "Payment", "Ending Balance", "Status"])
    for row in plan["schedule"]:
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
    return _build_pdf_response(
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
