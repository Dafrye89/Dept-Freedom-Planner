from django import forms

from .models import CustomUser, Profile


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["username", "email", "first_name", "last_name"]


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "timezone", "marketing_opt_in"]

