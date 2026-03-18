from decimal import Decimal

from django import template


register = template.Library()


@register.filter
def currency(value):
    if value in (None, ""):
        return "$0"
    value = Decimal(str(value))
    return f"${value:,.0f}" if value == value.quantize(Decimal("1")) else f"${value:,.2f}"


@register.filter
def percent(value):
    if value in (None, ""):
        return "0.00%"
    return f"{Decimal(str(value)):.2f}%"

