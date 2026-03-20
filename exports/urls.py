from django.urls import path

from .views import draft_csv, draft_pdf, draft_print, plan_csv, plan_pdf, plan_print

app_name = "exports"

urlpatterns = [
    path("draft/print/", draft_print, name="draft_print"),
    path("draft/pdf/", draft_pdf, name="draft_pdf"),
    path("draft/csv/", draft_csv, name="draft_csv"),
    path("plans/<int:pk>/print/", plan_print, name="plan_print"),
    path("plans/<int:pk>/pdf/", plan_pdf, name="plan_pdf"),
    path("plans/<int:pk>/csv/", plan_csv, name="plan_csv"),
]
