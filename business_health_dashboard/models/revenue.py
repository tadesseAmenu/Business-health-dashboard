from odoo import api, fields, models
from odoo.exceptions import ValidationError

class BusinessRevenue(models.Model):
    _name = "business.revenue"
    _description = "Revenue Entry"
    _order = "date desc"

    name = fields.Char(string="Revenue Source", required=True, help="Source or title of this revenue item.")
    amount = fields.Monetary(
        string="Amount",
        required=True,
        help="Revenue amount. It must be positive.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency used for this revenue.",
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        help="Date when this revenue was recognized.",
    )
    category = fields.Selection([
        ('sales', 'Sales'),
        ('services', 'Services'),
        ('other', 'Other'),
    ], required=True, default='other', help="Category used for reporting.")
    note = fields.Text(help="Optional details for this revenue entry.")
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
        help="Company this revenue belongs to.",
    )
    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        required=True,
        index=True,
        help="Owner of this revenue entry.",
    )
    month_label = fields.Char(
        compute='_compute_month_label',
        store=True,
        help="Month label in YYYY-MM format for grouping.",
    )

    _sql_constraints = [
        ('amount_non_negative', 'CHECK(amount >= 0)', 'Amount must be positive.'),
    ]

    @api.depends('date')
    def _compute_month_label(self):
        """Compute month label for grouping and search defaults."""
        for record in self:
            record.month_label = record.date.strftime('%Y-%m') if record.date else False

    @api.constrains('amount')
    def _check_amount_positive(self):
        """Provide user-friendly validation for negative values."""
        for record in self:
            if record.amount < 0:
                raise ValidationError('Amount must be positive.')