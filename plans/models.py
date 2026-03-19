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
    checkins_active = models.BooleanField(default=False)
    checkin_anchor_date = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class DebtItem(models.Model):
    class DebtType(models.TextChoices):
        CREDIT_CARD = "credit_card", "Credit Card"
        VEHICLE = "vehicle", "Vehicle"
        MORTGAGE = "mortgage", "Mortgage"
        BANK_LOAN = "bank_loan", "Bank Loan"
        PAYDAY_LOAN = "payday_loan", "Payday Loan"
        PERSONAL_LOAN = "personal_loan", "Personal Loan"
        STUDENT_LOAN = "student_loan", "Student Loan"
        OTHER = "other_debt", "Other Debt"

    debt_plan = models.ForeignKey(DebtPlan, on_delete=models.CASCADE, related_name="debt_items")
    name = models.CharField(max_length=150)
    lender_name = models.CharField(max_length=150, blank=True)
    debt_type = models.CharField(max_length=32, choices=DebtType.choices, default=DebtType.OTHER)
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


class BadgeAward(models.Model):
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="badge_awards")
    debt_plan = models.ForeignKey(DebtPlan, on_delete=models.CASCADE, related_name="badge_awards")
    debt_item = models.ForeignKey(DebtItem, on_delete=models.CASCADE, related_name="badge_awards")
    badge_key = models.CharField(max_length=64)
    badge_name = models.CharField(max_length=120)
    badge_image = models.CharField(max_length=255)
    debt_type = models.CharField(max_length=32)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        constraints = [
            models.UniqueConstraint(fields=["debt_item", "badge_key"], name="unique_badge_award_per_debt"),
        ]

    def __str__(self):
        return f"{self.badge_name} for {self.debt_item.name}"


class MonthlyCheckIn(models.Model):
    class Status(models.TextChoices):
        EXPECTED = "expected", "Made payments as planned"
        SKIPPED_EXTRA = "skipped_extra", "Skipped extra payment"
        CUSTOM = "custom", "Adjusted extra payment"

    debt_plan = models.ForeignKey(DebtPlan, on_delete=models.CASCADE, related_name="monthly_checkins")
    month_index = models.PositiveIntegerField()
    month_date = models.DateField()
    status = models.CharField(max_length=32, choices=Status.choices)
    extra_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["month_index"]
        constraints = [
            models.UniqueConstraint(fields=["debt_plan", "month_index"], name="unique_monthly_checkin_per_plan_month"),
        ]

    def __str__(self):
        return f"{self.debt_plan.title} month {self.month_index}"


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
