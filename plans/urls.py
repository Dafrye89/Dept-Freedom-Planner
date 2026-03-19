from django.urls import path

from .views import (
    dashboard,
    plan_add_scenario,
    plan_delete,
    plan_detail,
    plan_edit,
    plan_submit_checkin,
    plan_toggle_checkins,
    plan_update_pace,
    save_draft_plan,
)

app_name = "plans"

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("save-draft/", save_draft_plan, name="save_draft"),
    path("<int:pk>/", plan_detail, name="detail"),
    path("<int:pk>/scenario/add/", plan_add_scenario, name="add_scenario"),
    path("<int:pk>/pace/update/", plan_update_pace, name="update_pace"),
    path("<int:pk>/checkin/submit/", plan_submit_checkin, name="submit_checkin"),
    path("<int:pk>/checkin/toggle/", plan_toggle_checkins, name="toggle_checkins"),
    path("<int:pk>/edit/", plan_edit, name="edit"),
    path("<int:pk>/delete/", plan_delete, name="delete"),
]
