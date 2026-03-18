from django.urls import path

from .views import account_settings

app_name = "accounts"

urlpatterns = [
    path("settings/", account_settings, name="settings"),
]

