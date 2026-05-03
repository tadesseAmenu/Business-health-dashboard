from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestBusinessHealthDashboard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.revenue_model = self.env["business.revenue"]
        self.expense_model = self.env["expense.tracker.entry"]
        self.dashboard_model = self.env["business.dashboard"]

    def test_kpi_computation(self):
        self.revenue_model.create(
            {
                "name": "Sales",
                "amount": 1000.0,
                "date": "2099-03-10",
                "category": "sales",
            }
        )
        self.expense_model.create(
            {
                "name": "Rent",
                "amount": 300.0,
                "date": "2099-03-12",
                "category": "housing",
            }
        )

        dashboard = self.dashboard_model.create(
            {
                "date_from": "2099-03-01",
                "date_to": "2099-03-31",
            }
        )

        self.assertEqual(dashboard.total_revenue, 1000.0)
        self.assertEqual(dashboard.total_expenses, 300.0)
        self.assertEqual(dashboard.net_profit, 700.0)

    def test_positive_amount_constraints(self):
        with self.assertRaises(Exception):
            self.revenue_model.create(
                {
                    "name": "Invalid Revenue",
                    "amount": -5.0,
                    "date": "2026-03-12",
                    "category": "other",
                }
            )

        with self.assertRaises(Exception):
            self.expense_model.create(
                {
                    "name": "Invalid Expense",
                    "amount": -10.0,
                    "date": "2026-03-12",
                    "category": "other",
                }
            )

    def test_dashboard_date_validation(self):
        with self.assertRaises(ValidationError):
            self.dashboard_model.create(
                {
                    "date_from": "2026-03-31",
                    "date_to": "2026-03-01",
                }
            )
