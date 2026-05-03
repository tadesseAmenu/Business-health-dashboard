from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import json

class BusinessDashboard(models.TransientModel):
    _name = "business.dashboard"
    _description = "Business Health Dashboard"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
        help="Company used to compute and present dashboard values.",
    )

    date_from = fields.Date(
        string="From Date",
        required=True,
        default=lambda self: date.today().replace(day=1),
        help="Start date used to compute KPI values.",
    )
    date_to = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.context_today,
        help="End date used to compute KPI values.",
    )

    # KPIs
    total_revenue = fields.Monetary(
        string="Total Revenue",
        compute="_compute_kpis",
        currency_field='currency_id',
        help="Sum of all revenue entries in the selected period.",
    )
    total_expenses = fields.Monetary(
        string="Total Expenses",
        compute="_compute_kpis",
        currency_field='currency_id',
        help="Sum of all expense entries in the selected period.",
    )
    net_profit = fields.Monetary(
        string="Net Profit",
        compute="_compute_kpis",
        currency_field='currency_id',
        help="Revenue minus expenses for the selected period.",
    )
    profit_margin = fields.Float(
        string="Profit Margin (%)",
        compute="_compute_kpis",
        help="Net profit divided by revenue, shown as a percentage.",
    )
    expense_ratio = fields.Float(
        string="Expense Ratio (%)",
        compute="_compute_kpis",
        help="Expenses divided by revenue, shown as a percentage.",
    )
    cash_balance = fields.Monetary(
        string="Cash Balance",
        compute="_compute_kpis",
        currency_field='currency_id',
        help="Opening balance plus net profit for the selected period.",
    )
    opening_balance = fields.Monetary(
        string="Opening Balance",
        compute="_compute_kpis",
        currency_field='currency_id',
        help="Configured starting balance used in cash computation.",
    )
    rev_exp_chart_data = fields.Text(
        string="Revenue vs Expense Chart Data",
        compute="_compute_chart_data",
        help="Serialized chart payload used by embedded revenue versus expense widget.",
    )
    profit_trend_chart_data = fields.Text(
        string="Profit Trend Chart Data",
        compute="_compute_chart_data",
        help="Serialized chart payload used by embedded net profit trend widget.",
    )

    # Alerts
    alert_message = fields.Text(
        string="Alerts",
        compute="_compute_alerts",
        help="Automated warnings based on configured thresholds.",
    )

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        help="Currency used to display dashboard KPIs.",
    )

    def _get_config_float(self, key, default_value):
        """Read float configuration values safely with fallback defaults."""
        value = self.env['ir.config_parameter'].sudo().get_param(key, default_value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default_value)

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_kpis(self):
        """Compute KPI values for the selected date range."""
        for dashboard in self:
            # Revenue
            rev_data = self.env['business.revenue'].read_group(
                [
                    ('date', '>=', dashboard.date_from),
                    ('date', '<=', dashboard.date_to),
                    ('company_id', '=', dashboard.company_id.id),
                ],
                ['amount:sum'],
                []
            )
            if rev_data:
                rev_row = rev_data[0]
                dashboard.total_revenue = rev_row.get('amount_sum', rev_row.get('amount', 0.0)) or 0.0
            else:
                dashboard.total_revenue = 0.0

            # Expenses
            exp_data = self.env['expense.tracker.entry'].read_group(
                [
                    ('date', '>=', dashboard.date_from),
                    ('date', '<=', dashboard.date_to),
                    ('company_id', '=', dashboard.company_id.id),
                ],
                ['amount:sum'],
                []
            )
            if exp_data:
                exp_row = exp_data[0]
                dashboard.total_expenses = exp_row.get('amount_sum', exp_row.get('amount', 0.0)) or 0.0
            else:
                dashboard.total_expenses = 0.0

            dashboard.net_profit = dashboard.total_revenue - dashboard.total_expenses

            if dashboard.total_revenue:
                dashboard.profit_margin = (dashboard.net_profit / dashboard.total_revenue) * 100
                dashboard.expense_ratio = (dashboard.total_expenses / dashboard.total_revenue) * 100
            else:
                dashboard.profit_margin = 0.0
                dashboard.expense_ratio = 0.0

            # Cash balance with configurable starting balance
            starting_balance = dashboard._get_config_float('business_dashboard.starting_balance', 0.0)
            dashboard.opening_balance = starting_balance
            dashboard.cash_balance = starting_balance + dashboard.net_profit

    @api.depends('date_from', 'date_to', 'cash_balance', 'expense_ratio', 'total_revenue', 'net_profit', 'profit_margin')
    def _compute_alerts(self):
        """Build alert messages from current thresholds and KPI values."""
        for dashboard in self:
            alerts = []
            cash_threshold = dashboard._get_config_float('business_dashboard.cash_alert_threshold', 1000.0)
            if dashboard.cash_balance < cash_threshold:
                currency = dashboard.currency_id or self.env.company.currency_id
                formatted_threshold = f"{cash_threshold:.2f} {currency.symbol}"
                alerts.append(_("⚠️ Cash balance is below %s. Review expenses or increase revenue.") % formatted_threshold)
            
            expense_threshold = dashboard._get_config_float('business_dashboard.expense_ratio_alert_threshold', 70.0)
            if dashboard.expense_ratio > expense_threshold:
                alerts.append(_("⚠️ Expense ratio is above %s%%. Consider cutting costs.") % expense_threshold)

            revenue_threshold = dashboard._get_config_float('business_dashboard.revenue_alert_threshold', 1000.0)
            if dashboard.total_revenue < revenue_threshold:
                currency = dashboard.currency_id or self.env.company.currency_id
                formatted_threshold = f"{revenue_threshold:.2f} {currency.symbol}"
                alerts.append(_("⚠️ Total revenue is below %s. Consider boosting sales activity.") % formatted_threshold)

            if not alerts:
                alerts.append(_("✅ No alerts. Business health looks good!"))
            
            dashboard.alert_message = "\n".join(alerts)

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_chart_data(self):
        """Prepare serialized chart data payloads for embedded JS widgets."""
        for dashboard in self:
            if not dashboard.date_from or not dashboard.date_to:
                empty_payload = json.dumps({'type': 'bar', 'labels': [], 'series': []})
                dashboard.rev_exp_chart_data = empty_payload
                dashboard.profit_trend_chart_data = empty_payload
                continue

            rev_domain = [
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('company_id', '=', dashboard.company_id.id),
            ]
            exp_domain = [
                ('date', '>=', dashboard.date_from),
                ('date', '<=', dashboard.date_to),
                ('company_id', '=', dashboard.company_id.id),
            ]

            rev_groups = self.env['business.revenue'].read_group(
                rev_domain,
                ['amount:sum'],
                ['month_label'],
                lazy=False,
            )
            exp_groups = self.env['expense.tracker.entry'].read_group(
                exp_domain,
                ['amount:sum'],
                ['month_label'],
                lazy=False,
            )

            revenue_by_month = {
                group.get('month_label'): group.get('amount_sum', group.get('amount', 0.0)) or 0.0
                for group in rev_groups
                if group.get('month_label')
            }
            expense_by_month = {
                group.get('month_label'): group.get('amount_sum', group.get('amount', 0.0)) or 0.0
                for group in exp_groups
                if group.get('month_label')
            }

            labels = sorted(set(revenue_by_month) | set(expense_by_month))
            revenue_values = [revenue_by_month.get(label, 0.0) for label in labels]
            expense_values = [expense_by_month.get(label, 0.0) for label in labels]
            profit_values = [revenue_by_month.get(label, 0.0) - expense_by_month.get(label, 0.0) for label in labels]

            dashboard.rev_exp_chart_data = json.dumps({
                'type': 'bar',
                'labels': labels,
                'series': [
                    {'label': 'Revenue', 'color': '#1f77d0', 'values': revenue_values},
                    {'label': 'Expenses', 'color': '#7c3aed', 'values': expense_values},
                ],
            })
            dashboard.profit_trend_chart_data = json.dumps({
                'type': 'line',
                'labels': labels,
                'series': [
                    {'label': 'Net Profit', 'color': '#166534', 'values': profit_values},
                ],
            })

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        """Ensure selected start date is not after end date."""
        for dashboard in self:
            if dashboard.date_from and dashboard.date_to and dashboard.date_from > dashboard.date_to:
                raise ValidationError('Start date must be before or equal to end date.')

    def action_refresh(self):
        """Reload the current dashboard view."""
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_print_dashboard(self):
        """Generate a printable PDF summary of the dashboard values."""
        self.ensure_one()
        return self.env.ref('business_health_dashboard.action_report_business_dashboard').report_action(self)

    def action_view_revenue_graph(self):
        """Open revenue graph for the current period"""
        action = self.env.ref('business_health_dashboard.action_business_revenue').read()[0]
        action['view_mode'] = 'graph'
        action['views'] = [(self.env.ref('business_health_dashboard.view_business_revenue_graph').id, 'graph')]
        action['domain'] = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        return action

    def action_view_expense_graph(self):
        """Open expense graph for the current period"""
        action = self.env.ref('business_health_dashboard.action_expense_tracker_entry').read()[0]
        action['view_mode'] = 'graph'
        action['views'] = [(self.env.ref('business_health_dashboard.view_expense_tracker_entry_graph').id, 'graph')]
        action['domain'] = [('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        return action