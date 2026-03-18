from django.contrib import admin

from .models import DebtItem, DebtPlan, ScenarioComparison


class DebtItemInline(admin.TabularInline):
    model = DebtItem
    extra = 0


@admin.register(DebtPlan)
class DebtPlanAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "strategy_type",
        "projected_payoff_date",
        "projected_total_interest",
        "is_archived",
    )
    list_filter = ("strategy_type", "is_archived")
    search_fields = ("title", "user__username", "user__email")
    inlines = [DebtItemInline]


@admin.register(DebtItem)
class DebtItemAdmin(admin.ModelAdmin):
    list_display = ("name", "debt_plan", "balance", "apr", "minimum_payment", "custom_order")
    search_fields = ("name", "lender_name", "debt_plan__title")
    list_filter = ("apr",)


@admin.register(ScenarioComparison)
class ScenarioComparisonAdmin(admin.ModelAdmin):
    list_display = ("scenario_name", "debt_plan", "strategy_type", "months_to_payoff", "total_interest")
    list_filter = ("strategy_type",)

# Register your models here.
