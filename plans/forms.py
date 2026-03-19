from django import forms
from django.forms import formset_factory, inlineformset_factory

from .models import DebtItem, DebtPlan


EXTRA_PAYMENT_PRESETS = [
    ("", "Choose amount"),
    ("0.00", "$0"),
    ("50.00", "$50"),
    ("100.00", "$100"),
    ("200.00", "$200"),
    ("500.00", "$500"),
    ("custom", "Custom"),
]

DEBT_TYPE_CHOICES = [("", "Choose debt type"), *DebtItem.DebtType.choices]


def preset_choice_for_value(value) -> str:
    normalized = f"{value:.2f}" if hasattr(value, "quantize") else str(value or "").strip()
    preset_values = {choice for choice, _label in EXTRA_PAYMENT_PRESETS if choice and choice != "custom"}
    return normalized if normalized in preset_values else "custom"


class ExtraPaymentPresetMixin:
    extra_payment_preset = forms.ChoiceField(choices=EXTRA_PAYMENT_PRESETS, required=True)
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    def __init__(self, *args, initial_extra_payment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if "extra_payment_preset" not in self.fields or "extra_monthly_payment" not in self.fields:
            return
        initial_value = initial_extra_payment
        if initial_value is None:
            initial_value = self.initial.get("extra_monthly_payment")
        if initial_value is None and "extra_monthly_payment" in self.fields:
            initial_value = self.fields["extra_monthly_payment"].initial
        initial_value = initial_value or 0
        self.fields["extra_payment_preset"].initial = preset_choice_for_value(initial_value)
        self.fields["extra_monthly_payment"].initial = initial_value

    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get("extra_payment_preset")
        amount = cleaned_data.get("extra_monthly_payment")
        if not preset:
            self.add_error("extra_payment_preset", "Choose an extra monthly payment amount.")
            return cleaned_data
        if preset == "custom":
            if amount is None:
                self.add_error("extra_monthly_payment", "Enter the custom extra monthly payment amount.")
                return cleaned_data
            cleaned_data["extra_monthly_payment"] = amount
            return cleaned_data
        cleaned_data["extra_monthly_payment"] = preset
        return cleaned_data


class DraftPlanDetailsForm(forms.Form):
    title = forms.CharField(max_length=150)
    household_name = forms.CharField(max_length=150, required=False)


class DebtDraftForm(forms.Form):
    name = forms.CharField(max_length=150)
    lender_name = forms.CharField(max_length=150, required=False)
    debt_type = forms.ChoiceField(choices=DEBT_TYPE_CHOICES)
    balance = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    apr = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0)
    minimum_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    due_day = forms.IntegerField(min_value=1, max_value=31, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    custom_order = forms.IntegerField(min_value=1, required=False)


DebtDraftFormSet = formset_factory(
    DebtDraftForm,
    extra=0,
    can_delete=True,
    validate_min=True,
    min_num=1,
    max_num=10,
    validate_max=True,
)


class StrategySelectionForm(forms.Form):
    strategy_type = forms.ChoiceField(choices=DebtPlan.Strategy.choices)
    extra_payment_preset = forms.ChoiceField(choices=EXTRA_PAYMENT_PRESETS, required=True)
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        initial_extra_payment = kwargs.get("initial", {}).get("extra_monthly_payment", 0)
        super().__init__(*args, **kwargs)
        self.fields["extra_payment_preset"].initial = preset_choice_for_value(initial_extra_payment)

    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get("extra_payment_preset")
        amount = cleaned_data.get("extra_monthly_payment")
        if not preset:
            self.add_error("extra_payment_preset", "Choose an extra monthly payment amount.")
            return cleaned_data
        if preset == "custom":
            if amount is None:
                self.add_error("extra_monthly_payment", "Enter the custom extra monthly payment amount.")
                return cleaned_data
            cleaned_data["extra_monthly_payment"] = amount
            return cleaned_data
        cleaned_data["extra_monthly_payment"] = preset
        return cleaned_data


class DebtPlanForm(ExtraPaymentPresetMixin, forms.ModelForm):
    extra_payment_preset = forms.ChoiceField(choices=EXTRA_PAYMENT_PRESETS, required=True)
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    class Meta:
        model = DebtPlan
        fields = ["title", "household_name", "strategy_type", "extra_monthly_payment"]

    def __init__(self, *args, **kwargs):
        initial_extra_payment = None
        if kwargs.get("instance") is not None:
            initial_extra_payment = kwargs["instance"].extra_monthly_payment
        super().__init__(*args, initial_extra_payment=initial_extra_payment, **kwargs)


class DebtItemForm(forms.ModelForm):
    debt_type = forms.ChoiceField(choices=DEBT_TYPE_CHOICES)

    class Meta:
        model = DebtItem
        fields = [
            "name",
            "lender_name",
            "debt_type",
            "balance",
            "apr",
            "minimum_payment",
            "due_day",
            "notes",
            "custom_order",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ScenarioComparisonForm(forms.Form):
    scenario_name = forms.CharField(max_length=120)
    strategy_type = forms.ChoiceField(choices=DebtPlan.Strategy.choices)
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class PlanPaceUpdateForm(ExtraPaymentPresetMixin, forms.Form):
    extra_payment_preset = forms.ChoiceField(choices=EXTRA_PAYMENT_PRESETS, required=True)
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)


class MonthlyCheckInForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ("expected", "Yes, I made the plan as expected"),
            ("skipped_extra", "No, skip my extra payment for this month"),
            ("custom", "No, use a different extra payment amount"),
        ]
    )
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("status") == "custom" and cleaned_data.get("extra_monthly_payment") is None:
            self.add_error("extra_monthly_payment", "Enter the extra payment amount for this month.")
        return cleaned_data


DebtItemFormSet = inlineformset_factory(
    DebtPlan,
    DebtItem,
    form=DebtItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
