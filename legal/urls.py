from django.urls import path

from .views import disclaimer, privacy, terms

app_name = "legal"

urlpatterns = [
    path("privacy/", privacy, name="privacy"),
    path("terms/", terms, name="terms"),
    path("disclaimer/", disclaimer, name="disclaimer"),
]
