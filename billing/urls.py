from django.urls import path

from .views import pricing

app_name = "billing"

urlpatterns = [
    path("", pricing, name="pricing"),
]
