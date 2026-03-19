from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import media_file

admin.site.site_header = "Debt Freedom Planner Control Room"
admin.site.site_title = "Debt Freedom Planner Admin"
admin.site.index_title = "Founder administration"

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/img/branding/favicon.png", permanent=True)),
    path("", include("core.urls")),
    path("account/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("media/<path:path>", media_file, name="media_file"),
    path("plans/", include("plans.urls")),
    path("exports/", include("exports.urls")),
    path("pricing/", include("billing.urls")),
    path("legal/", include("legal.urls")),
    path("control-room/", admin.site.urls),
]
