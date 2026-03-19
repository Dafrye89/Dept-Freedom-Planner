from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from billing.services import is_stripe_configured, reconcile_all_paid_access, reconcile_user_paid_access


class Command(BaseCommand):
    help = "Reconcile paid access from live Stripe subscriptions."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Reconcile one user by username.")
        parser.add_argument("--email", help="Reconcile one user by email.")
        parser.add_argument(
            "--all",
            action="store_true",
            help="Reconcile every matching Stripe subscription against local users.",
        )

    def handle(self, *args, **options):
        if not is_stripe_configured():
            raise CommandError("Stripe is not configured.")

        User = get_user_model()
        username = options.get("username")
        email = options.get("email")
        reconcile_all = options.get("all")

        if reconcile_all:
            result = reconcile_all_paid_access()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reconciled {result['synced']} Stripe subscriptions. Unmatched subscriptions: {result['unmatched']}."
                )
            )
            return

        if username:
            user = User.objects.filter(username=username.lower().strip()).first()
            if not user:
                raise CommandError(f"No user found with username '{username}'.")
        elif email:
            user = User.objects.filter(email=email.lower().strip()).first()
            if not user:
                raise CommandError(f"No user found with email '{email}'.")
        else:
            raise CommandError("Pass --all, --username, or --email.")

        access = reconcile_user_paid_access(user)
        self.stdout.write(
            self.style.SUCCESS(
                f"User '{user.username}' reconciled. Tier: {access.tier}. Stripe status: {access.stripe_status or 'unknown'}."
            )
        )
