from django.db import models


class DebtPlan(models.Model):
    class Strategy(models.TextChoices):
        SNOWBALL = "snowball", "Snowball"
        AVALANCHE = "avalanche", "Avalanche"
        CUSTOM = "custom", "Custom"

    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="debt_plans")
    title = models.CharField(max_length=150)
    household_name = models.CharField(max_length=150, blank=True)
    strategy_type = models.CharField(max_length=20, choices=Strategy.choices, default=Strategy.SNOWBALL)
    extra_monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_balance_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    projected_payoff_date = models.DateField(null=True, blank=True)
    projected_months_to_payoff = models.PositiveIntegerField(default=0)
    projected_total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    projected_total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class DebtItem(models.Model):
    debt_plan = models.ForeignKey(DebtPlan, on_delete=models.CASCADE, related_name="debt_items")
    name = models.CharField(max_length=150)
    lender_name = models.CharField(max_length=150, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    apr = models.DecimalField(max_digits=6, decimal_places=2)
    minimum_payment = models.DecimalField(max_digits=10, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    custom_order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["custom_order", "created_at"]

    def __str__(self):
        return self.name


class ScenarioComparison(models.Model):
    debt_plan = models.ForeignKey(DebtPlan, on_delete=models.CASCADE, related_name="scenario_comparisons")
    scenario_name = models.CharField(max_length=120)
    strategy_type = models.CharField(max_length=20, choices=DebtPlan.Strategy.choices)
    extra_monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payoff_date = models.DateField(null=True, blank=True)
    months_to_payoff = models.PositiveIntegerField(default=0)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_system_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.scenario_name

# Create your models here.
