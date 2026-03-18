from django.urls import path

from .views import (
    home,
    planner_debts,
    planner_results,
    planner_start,
    planner_strategy,
    strategy_preview,
)

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("planner/start/", planner_start, name="planner_start"),
    path("planner/debts/", planner_debts, name="planner_debts"),
    path("planner/strategy/", planner_strategy, name="planner_strategy"),
    path("planner/preview/", strategy_preview, name="strategy_preview"),
    path("planner/results/", planner_results, name="planner_results"),
]
