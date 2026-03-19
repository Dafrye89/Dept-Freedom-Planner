from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from billing.models import StripeWebhookEvent
from billing.services import create_checkout_session
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

    def test_signup_with_planner_next_redirects_back_to_planner(self):
        response = self.client.post(
            f"{reverse('account_signup')}?next={reverse('core:planner_start')}",
            {
                "email": "signup-flow@example.com",
                "username": "signupflow",
                "password1": "Freedom_12345",
                "password2": "Freedom_12345",
                "next": reverse("core:planner_start"),
            },
        )

        self.assertRedirects(response, reverse("core:planner_start"), fetch_redirect_response=False)

    def test_login_and_password_reset_pages_load(self):
        self.assertEqual(self.client.get(reverse("account_login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("account_reset_password")).status_code, 200)

    def test_homepage_is_marketing_for_anonymous_users(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-shell="marketing"')
        self.assertContains(response, "Debt Freedom Planner helps you build a solid, step-by-step roadmap to eliminate your balances and earn your way back to breathing room.")

    def test_anonymous_planner_routes_redirect_to_signup(self):
        for route_name in [
            "core:planner_start",
            "core:planner_debts",
            "core:planner_strategy",
            "core:planner_results",
        ]:
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("account_signup"), response["Location"])

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

    def test_free_user_cannot_save_plan_and_is_sent_to_settings(self):
        user = self.create_user("freeuser", "free-save@example.com")
        self.client.force_login(user)
        self.set_draft(sample_draft("Blocked Plan"))

        response = self.client.post(reverse("plans:save_draft"), follow=True)

        self.assertEqual(DebtPlan.objects.filter(user=user, is_archived=False).count(), 0)
        self.assertRedirects(response, reverse("accounts:settings"))
        self.assertContains(response, "If you want to use save plans, you will need to upgrade to the Pro plan.")

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

        self.assertRedirects(response, reverse("accounts:settings"), fetch_redirect_response=False)

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

        self.assertRedirects(response, reverse("accounts:settings"), fetch_redirect_response=False)
        self.assertFalse(ScenarioComparison.objects.filter(debt_plan=plan, scenario_name="Blocked").exists())

    def test_free_user_cannot_access_second_schedule_page(self):
        user = self.create_user("schedulefree", "schedulefree@example.com")
        self.client.force_login(user)
        self.set_draft(sample_draft())

        response = self.client.get(reverse("core:planner_results"), {"schedule_page": 2})

        self.assertRedirects(response, reverse("accounts:settings"), fetch_redirect_response=False)

    @patch("billing.views.create_checkout_session", return_value="https://checkout.stripe.com/pay/cs_test_123")
    def test_logged_in_free_user_can_start_stripe_checkout(self, mocked_checkout):
        user = self.create_user("stripefree", "stripefree@example.com")
        self.client.force_login(user)

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
            STRIPE_PUBLISHABLE_KEY="pk_test_123",
        ):
            response = self.client.post(reverse("billing:checkout"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://checkout.stripe.com/pay/cs_test_123")
        mocked_checkout.assert_called_once_with(user=user)

    @patch("billing.services.stripe.checkout.Session.create", return_value={"url": "https://checkout.stripe.com/pay/cs_trial_123"})
    @patch("billing.services.stripe.Customer.create", return_value={"id": "cus_trial_123"})
    def test_checkout_session_uses_trial_period_days(self, mocked_customer_create, mocked_session_create):
        user = self.create_user("trialuser", "trial@example.com")

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
            STRIPE_TRIAL_PERIOD_DAYS=30,
        ):
            checkout_url = create_checkout_session(user=user)

        self.assertEqual(checkout_url, "https://checkout.stripe.com/pay/cs_trial_123")
        self.assertEqual(mocked_session_create.call_args.kwargs["subscription_data"]["trial_period_days"], 30)
        mocked_customer_create.assert_called_once()

    @patch("billing.views.create_portal_session", return_value="https://billing.stripe.com/session/test_123")
    def test_paid_user_can_open_stripe_portal(self, mocked_portal):
        user = self.create_user("stripepaid", "stripepaid@example.com", paid=True)
        user.subscription_access.stripe_customer_id = "cus_123"
        user.subscription_access.save(update_fields=["stripe_customer_id", "updated_at"])
        self.client.force_login(user)

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
        ):
            response = self.client.post(reverse("billing:portal"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://billing.stripe.com/session/test_123")
        mocked_portal.assert_called_once_with(user=user)

    @patch("billing.views.reconcile_user_paid_access")
    def test_refresh_access_promotes_paid_user_from_stripe(self, mocked_reconcile):
        user = self.create_user("refreshuser", "refresh@example.com")
        self.client.force_login(user)

        def reconcile_and_activate(target_user):
            access = target_user.subscription_access
            access.sync_stripe_subscription(
                customer_id="cus_refresh_123",
                subscription_id="sub_refresh_123",
                price_id="price_test_123",
                status="active",
                current_period_end=1775000000,
                notes="manual refresh",
            )
            return access

        mocked_reconcile.side_effect = reconcile_and_activate

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
        ):
            response = self.client.post(reverse("billing:refresh_access"))

        user.refresh_from_db()
        self.assertRedirects(response, reverse("accounts:settings"), fetch_redirect_response=False)
        self.assertEqual(user.subscription_access.tier, user.subscription_access.Tier.PAID)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Your Pro access has been refreshed." in str(message) for message in messages))
        mocked_reconcile.assert_called_once_with(user)

    @patch(
        "billing.services.stripe.Subscription.retrieve",
        return_value={
            "id": "sub_success_123",
            "customer": "cus_success_123",
            "status": "trialing",
            "cancel_at_period_end": False,
            "current_period_end": 1775000000,
            "items": {"data": [{"price": {"id": "price_test_123"}}]},
        },
    )
    @patch(
        "billing.services.stripe.checkout.Session.retrieve",
        return_value={
            "id": "cs_success_123",
            "customer": "cus_success_123",
            "subscription": "sub_success_123",
            "client_reference_id": "1",
            "metadata": {"user_id": "1"},
        },
    )
    def test_checkout_success_activates_paid_access_immediately(self, mocked_session_retrieve, mocked_subscription_retrieve):
        user = self.create_user("successuser", "success@example.com")
        self.client.force_login(user)

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
        ):
            mocked_session_retrieve.return_value["client_reference_id"] = str(user.pk)
            mocked_session_retrieve.return_value["metadata"]["user_id"] = str(user.pk)
            response = self.client.get(reverse("billing:checkout_success"), {"session_id": "cs_success_123"})

        user.refresh_from_db()
        self.assertRedirects(response, reverse("plans:dashboard"), fetch_redirect_response=False)
        self.assertEqual(user.subscription_access.tier, user.subscription_access.Tier.PAID)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Your Pro access is active now." in str(message) for message in messages))
        mocked_session_retrieve.assert_called_once_with("cs_success_123")
        mocked_subscription_retrieve.assert_called_once_with("sub_success_123")

    @patch(
        "billing.services.stripe.checkout.Session.retrieve",
        return_value={
            "id": "cs_wrong_user_123",
            "customer": "cus_wrong_123",
            "subscription": "sub_wrong_123",
            "client_reference_id": "9999",
            "metadata": {"user_id": "9999"},
        },
    )
    def test_checkout_success_does_not_sync_other_users_session(self, mocked_session_retrieve):
        user = self.create_user("wrongsession", "wrongsession@example.com")
        self.client.force_login(user)

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
        ):
            response = self.client.get(reverse("billing:checkout_success"), {"session_id": "cs_wrong_user_123"})

        user.refresh_from_db()
        self.assertRedirects(response, reverse("plans:dashboard"), fetch_redirect_response=False)
        self.assertEqual(user.subscription_access.tier, user.subscription_access.Tier.FREE)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("still confirming your Pro access" in str(message) for message in messages))
        mocked_session_retrieve.assert_called_once_with("cs_wrong_user_123")

    @patch("billing.management.commands.reconcile_stripe_access.reconcile_user_paid_access")
    def test_reconcile_stripe_access_command_updates_single_user(self, mocked_reconcile):
        user = self.create_user("commanduser", "command@example.com")

        def reconcile_and_activate(target_user):
            access = target_user.subscription_access
            access.sync_stripe_subscription(
                customer_id="cus_command_123",
                subscription_id="sub_command_123",
                price_id="price_test_123",
                status="active",
                current_period_end=1775000000,
                notes="command sync",
            )
            return access

        mocked_reconcile.side_effect = reconcile_and_activate
        out = StringIO()

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
        ):
            call_command("reconcile_stripe_access", "--username", user.username, stdout=out)

        user.refresh_from_db()
        self.assertEqual(user.subscription_access.tier, user.subscription_access.Tier.PAID)
        self.assertIn("User 'commanduser' reconciled. Tier: paid. Stripe status: active.", out.getvalue())
        mocked_reconcile.assert_called_once()

    @patch(
        "billing.services.stripe.Subscription.retrieve",
        return_value={
            "id": "sub_123",
            "customer": "cus_123",
            "status": "trialing",
            "cancel_at_period_end": False,
            "current_period_end": 1775000000,
            "items": {"data": [{"price": {"id": "price_test_123"}}]},
        },
    )
    @patch(
        "billing.views.construct_stripe_event",
        return_value={
            "id": "evt_checkout_123",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_123",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "client_reference_id": "1",
                    "metadata": {"user_id": "1"},
                }
            },
        },
    )
    def test_checkout_completed_webhook_activates_paid_access(self, mocked_construct_event, mocked_subscription_retrieve):
        user = self.create_user("webhookuser", "webhook@example.com")

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
            STRIPE_WEBHOOK_SECRET="whsec_test_123",
        ):
            event = mocked_construct_event.return_value
            event["data"]["object"]["client_reference_id"] = str(user.pk)
            event["data"]["object"]["metadata"]["user_id"] = str(user.pk)

            response = self.client.post(
                reverse("billing:stripe_webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_test_123",
            )

        user.refresh_from_db()
        access = user.subscription_access
        self.assertEqual(response.status_code, 200)
        self.assertEqual(access.tier, access.Tier.PAID)
        self.assertEqual(access.stripe_customer_id, "cus_123")
        self.assertEqual(access.stripe_subscription_id, "sub_123")
        self.assertEqual(access.stripe_status, "trialing")
        self.assertTrue(StripeWebhookEvent.objects.filter(stripe_event_id="evt_checkout_123").exists())
        mocked_construct_event.assert_called_once()
        mocked_subscription_retrieve.assert_called_once_with("sub_123")

    @patch(
        "billing.views.construct_stripe_event",
        return_value={
            "id": "evt_subscription_deleted_123",
            "type": "customer.subscription.deleted",
            "livemode": False,
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "canceled",
                    "cancel_at_period_end": False,
                    "current_period_end": 1775000000,
                    "items": {"data": [{"price": {"id": "price_test_123"}}]},
                }
            },
        },
    )
    def test_subscription_deleted_webhook_downgrades_paid_access(self, mocked_construct_event):
        user = self.create_user("downgradeuser", "downgrade@example.com", paid=True)
        user.subscription_access.sync_stripe_subscription(
            customer_id="cus_123",
            subscription_id="sub_123",
            price_id="price_test_123",
            status="active",
            current_period_end=1775000000,
            notes="setup",
        )

        with self.settings(
            STRIPE_SECRET_KEY="sk_test_123",
            STRIPE_PRO_PRICE_ID="price_test_123",
            STRIPE_WEBHOOK_SECRET="whsec_test_123",
        ):
            response = self.client.post(
                reverse("billing:stripe_webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig_test_123",
            )

        user.refresh_from_db()
        access = user.subscription_access
        self.assertEqual(response.status_code, 200)
        self.assertEqual(access.tier, access.Tier.FREE)
        self.assertEqual(access.stripe_status, "canceled")

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
