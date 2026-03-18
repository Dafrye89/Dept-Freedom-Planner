from django import forms
from django.forms import formset_factory, inlineformset_factory

from .models import DebtItem, DebtPlan


class DraftPlanDetailsForm(forms.Form):
    title = forms.CharField(max_length=150)
    household_name = forms.CharField(max_length=150, required=False)


class DebtDraftForm(forms.Form):
    name = forms.CharField(max_length=150)
    lender_name = forms.CharField(max_length=150, required=False)
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
    extra_monthly_payment = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class DebtPlanForm(forms.ModelForm):
    class Meta:
        model = DebtPlan
        fields = ["title", "household_name", "strategy_type", "extra_monthly_payment"]


class DebtItemForm(forms.ModelForm):
    class Meta:
        model = DebtItem
        fields = [
            "name",
            "lender_name",
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


DebtItemFormSet = inlineformset_factory(
    DebtPlan,
    DebtItem,
    form=DebtItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
