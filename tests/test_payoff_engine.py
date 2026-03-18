from decimal import Decimal

from django.test import SimpleTestCase

from calculator.services.payoff_engine import create_comparisons, solve_payoff_plan


class PayoffEngineTests(SimpleTestCase):
    def test_snowball_orders_by_smallest_balance(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Large Loan", "balance": "5000", "apr": "10", "minimum_payment": "120"},
                {"name": "Small Card", "balance": "800", "apr": "15", "minimum_payment": "50"},
            ],
            extra_payment=Decimal("100"),
            strategy="snowball",
        )

        self.assertEqual(result["summary"]["first_target"], "Small Card")
        self.assertEqual(result["debts"][0]["focus_rank"], 2)
        self.assertEqual(result["debts"][1]["focus_rank"], 1)

    def test_avalanche_orders_by_highest_apr(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Low APR", "balance": "1000", "apr": "6", "minimum_payment": "50"},
                {"name": "High APR", "balance": "2000", "apr": "22", "minimum_payment": "60"},
            ],
            extra_payment=Decimal("75"),
            strategy="avalanche",
        )

        self.assertEqual(result["summary"]["first_target"], "High APR")

    def test_custom_order_uses_custom_rank(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Debt A", "balance": "1000", "apr": "10", "minimum_payment": "50", "custom_order": 2},
                {"name": "Debt B", "balance": "1000", "apr": "10", "minimum_payment": "50", "custom_order": 1},
            ],
            extra_payment=Decimal("50"),
            strategy="custom",
        )

        self.assertEqual(result["summary"]["first_target"], "Debt B")

    def test_overpayment_rolls_into_next_debt_same_month(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Debt A", "balance": "50", "apr": "0", "minimum_payment": "50"},
                {"name": "Debt B", "balance": "100", "apr": "0", "minimum_payment": "10"},
            ],
            extra_payment=Decimal("100"),
            strategy="snowball",
        )

        month_one_rows = [row for row in result["schedule"] if row["month_index"] == 1]
        debt_b_row = next(row for row in month_one_rows if row["debt_name"] == "Debt B")
        self.assertGreater(debt_b_row["payment"], Decimal("10.00"))
        self.assertEqual(result["summary"]["months_to_payoff"], 1)

    def test_zero_interest_debt_has_zero_total_interest(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Zero APR Loan", "balance": "1200", "apr": "0", "minimum_payment": "100"},
            ],
            extra_payment=Decimal("0"),
            strategy="snowball",
        )

        self.assertEqual(result["summary"]["months_to_payoff"], 12)
        self.assertEqual(result["summary"]["total_interest"], Decimal("0.00"))

    def test_exact_final_payoff_month_is_reported(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Single Loan", "balance": "300", "apr": "0", "minimum_payment": "100"},
            ],
            extra_payment=Decimal("0"),
            strategy="snowball",
        )

        self.assertEqual(result["summary"]["months_to_payoff"], 3)
        self.assertEqual(result["debts"][0]["paid_off_month"], 3)

    def test_stalled_plan_is_detected(self):
        result = solve_payoff_plan(
            debts=[
                {"name": "Bad Loan", "balance": "1000", "apr": "60", "minimum_payment": "10"},
            ],
            extra_payment=Decimal("0"),
            strategy="snowball",
        )

        self.assertEqual(result["status"], "stalled")
        self.assertIsNone(result["summary"]["projected_payoff_date"])

    def test_comparisons_include_accelerated_label(self):
        comparisons = create_comparisons(
            {
                "debts": [
                    {"name": "Loan", "balance": "1000", "apr": "8", "minimum_payment": "50"},
                ],
                "extra_payment": Decimal("100"),
                "strategy": "snowball",
            }
        )

        self.assertEqual(comparisons["accelerated"]["comparison_label"], "Add $150 more")
