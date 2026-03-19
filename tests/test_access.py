from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts.models import CustomUser
from accounts.services.access import can_create_plan, get_capabilities


class AccessPolicyTests(TestCase):
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

    def test_anonymous_capabilities(self):
        capabilities = get_capabilities(AnonymousUser())
        self.assertTrue(capabilities.can_calculate)
        self.assertTrue(capabilities.can_compare)
        self.assertFalse(capabilities.can_save_plans)
        self.assertFalse(capabilities.can_view_full_schedule)
        self.assertFalse(capabilities.can_see_admin_link)

    def test_free_user_cannot_save_plans(self):
        user = self.create_user("freeuser", "free@example.com")
        self.assertFalse(can_create_plan(user))

    def test_paid_user_gets_premium_capabilities(self):
        user = self.create_user("paiduser", "paid@example.com", paid=True)
        capabilities = get_capabilities(user)
        self.assertTrue(capabilities.can_export_pdf)
        self.assertTrue(capabilities.can_compare_unlimited)
        self.assertTrue(capabilities.can_view_full_schedule)
        self.assertIsNone(capabilities.max_saved_plans)

    def test_founder_override_gets_admin_link_only_when_superuser(self):
        founder = self.create_user(
            settings.BOOTSTRAP_SUPERUSER_USERNAME,
            "founder@example.com",
            superuser=True,
            override=True,
        )
        capabilities = get_capabilities(founder)
        self.assertTrue(capabilities.is_override)
        self.assertTrue(capabilities.can_see_admin_link)

        staff_user = self.create_user("staffuser", "staff@example.com", superuser=True)
        staff_capabilities = get_capabilities(staff_user)
        self.assertFalse(staff_capabilities.can_see_admin_link)
