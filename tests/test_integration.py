from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from core.services.draft import DRAFT_SESSION_KEY
from plans.models import DebtPlan, ScenarioComparison
from plans.services import create_saved_plan_from_draft


def sample_draft(title="Debt Freedom Roadmap"):
    return {
        "title": title,
        "household_name": "Test Household",
        "strategy_type": "snowball",
        "extra_monthly_payment": "150.00",
        "debts": [
            {
                "name": "Card One",
                "lender_name": "Liberty Bank",
                "balance": "1200.00",
                "apr": "18.00",
                "minimum_payment": "55.00",
                "due_day": 5,
                "notes": "",
                "custom_order": 1,
            },
            {
                "name": "Car Note",
                "lender_name": "Main Street Credit",
                "balance": "4200.00",
                "apr": "7.50",
                "minimum_payment": "180.00",
                "due_day": 18,
                "notes": "",
                "custom_order": 2,
            },
        ],
    }


class IntegrationTests(TestCase):
    def create_user(self, username, email, *, paid=False, superuser=False, override=False):
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password="Freedom_12345",
            is_staff=superuser,
            is_superuser=superuser,
        )
        access = user.subscription_access
        if paid:
            access.activate_paid("test")
        if override:
            access.lifetime_override = True
            access.save(update_fields=["lifetime_override", "updated_at"])
        return user

    def set_draft(self, draft):
        session = self.client.session
        session[DRAFT_SESSION_KEY] = draft
        session.save()

    def test_signup_redirects_back_to_results_when_draft_exists(self):
        self.set_draft(sample_draft())
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "signup-flow@example.com",
                "username": "signupflow",
                "password1": "Freedom_12345",
                "password2": "Freedom_12345",
            },
        )

        self.assertRedirects(response, reverse("core:planner_results"), fetch_redirect_response=False)

    def test_login_and_password_reset_pages_load(self):
        self.assertEqual(self.client.get(reverse("account_login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("account_reset_password")).status_code, 200)

    def test_homepage_is_marketing_for_anonymous_users(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-shell="marketing"')
        self.assertContains(response, "Build your debt-free roadmap with confidence.")

    def test_homepage_redirects_authenticated_users_to_dashboard(self):
        user = self.create_user("dashboarduser", "dashboard@example.com")
        self.client.force_login(user)

        response = self.client.get(reverse("core:home"))

        self.assertRedirects(response, reverse("plans:dashboard"), fetch_redirect_response=False)

    def test_pricing_uses_marketing_shell_and_dashboard_uses_app_shell(self):
        user = self.create_user("shelluser", "shell@example.com")
        self.client.force_login(user)

        pricing_response = self.client.get(reverse("billing:pricing"))
        dashboard_response = self.client.get(reverse("plans:dashboard"))

        self.assertContains(pricing_response, 'data-shell="marketing"')
        self.assertContains(dashboard_response, 'data-shell="app"')

    def test_free_user_can_save_first_plan_and_hits_limit_on_second(self):
        user = self.create_user("freeuser", "free-save@example.com")
        self.client.force_login(user)
        self.set_draft(sample_draft("First Plan"))

        first_response = self.client.post(reverse("plans:save_draft"))
        self.assertEqual(DebtPlan.objects.filter(user=user, is_archived=False).count(), 1)
        self.assertRedirects(
            first_response,
            reverse("plans:detail", args=[DebtPlan.objects.get(user=user).pk]),
            fetch_redirect_response=False,
        )

        self.set_draft(sample_draft("Second Plan"))
        second_response = self.client.post(reverse("plans:save_draft"))
        self.assertRedirects(second_response, reverse("billing:pricing"), fetch_redirect_response=False)
        self.assertEqual(DebtPlan.objects.filter(user=user, is_archived=False).count(), 1)

    def test_free_user_can_open_print_view(self):
        user = self.create_user("printfree", "print@example.com")
        self.client.force_login(user)
        self.set_draft(sample_draft())

        response = self.client.get(reverse("exports:draft_print"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Debt payoff plan")

    def test_free_user_cannot_export_pdf(self):
        user = self.create_user("freepdf", "freepdf@example.com")
        plan = create_saved_plan_from_draft(user=user, draft=sample_draft())
        self.client.force_login(user)

        response = self.client.get(reverse("exports:plan_pdf", args=[plan.pk]))

        self.assertRedirects(response, reverse("billing:pricing"), fetch_redirect_response=False)

    def test_paid_user_can_export_pdf(self):
        user = self.create_user("paidpdf", "paidpdf@example.com", paid=True)
        plan = create_saved_plan_from_draft(user=user, draft=sample_draft())
        self.client.force_login(user)

        response = self.client.get(reverse("exports:plan_pdf", args=[plan.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_paid_user_can_add_custom_scenario(self):
        user = self.create_user("paiduser", "paidscenario@example.com", paid=True)
        plan = create_saved_plan_from_draft(user=user, draft=sample_draft())
        self.client.force_login(user)

        response = self.client.post(
            reverse("plans:add_scenario", args=[plan.pk]),
            {
                "scenario_name": "Bigger Push",
                "strategy_type": "avalanche",
                "extra_monthly_payment": "300.00",
            },
        )

        self.assertRedirects(response, reverse("plans:detail", args=[plan.pk]), fetch_redirect_response=False)
        self.assertTrue(
            ScenarioComparison.objects.filter(
                debt_plan=plan,
                scenario_name="Bigger Push",
                is_system_generated=False,
            ).exists()
        )

    def test_free_user_cannot_add_custom_scenario(self):
        user = self.create_user("freeuser2", "free2@example.com")
        plan = create_saved_plan_from_draft(user=user, draft=sample_draft())
        self.client.force_login(user)

        response = self.client.post(
            reverse("plans:add_scenario", args=[plan.pk]),
            {
                "scenario_name": "Blocked",
                "strategy_type": "snowball",
                "extra_monthly_payment": "300.00",
            },
        )

        self.assertRedirects(response, reverse("billing:pricing"), fetch_redirect_response=False)
        self.assertFalse(ScenarioComparison.objects.filter(debt_plan=plan, scenario_name="Blocked").exists())

    def test_bootstrap_superuser_command_creates_founder(self):
        call_command("bootstrap_superuser")
        founder = CustomUser.objects.get(username=settings.BOOTSTRAP_SUPERUSER_USERNAME)

        self.assertTrue(founder.is_superuser)
        self.assertTrue(founder.subscription_access.lifetime_override)

    def test_admin_link_visible_only_for_founder(self):
        founder = self.create_user(
            settings.BOOTSTRAP_SUPERUSER_USERNAME,
            "founder-ui@example.com",
            superuser=True,
            override=True,
        )
        other_staff = self.create_user("staffuser", "staff-ui@example.com", superuser=True)

        self.client.force_login(founder)
        founder_response = self.client.get(reverse("plans:dashboard"))
        self.assertContains(founder_response, "Admin")

        self.client.force_login(other_staff)
        staff_response = self.client.get(reverse("plans:dashboard"))
        self.assertNotContains(staff_response, "Admin")
