from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter

from core.services.draft import DRAFT_SESSION_KEY


class PlannerAccountAdapter(DefaultAccountAdapter):
    def _planner_redirect(self, request):
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
            return next_url

        draft = request.session.get(DRAFT_SESSION_KEY, {})
        if draft.get("debts"):
            return reverse("core:planner_results")
        return reverse("plans:dashboard")

    def get_login_redirect_url(self, request):
        return self._planner_redirect(request)

    def get_signup_redirect_url(self, request):
        return self._planner_redirect(request)
