from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ExpenseTrackerEntry(models.Model):
    _name = "expense.tracker.entry"
    _description = "Expense Entry"
    _order = "date desc, id desc"

    name = fields.Char(string="Title", required=True, help="Short description of the expense.")
    amount = fields.Monetary(
        string="Amount",
        required=True,
        help="Expense amount. It must be positive.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency used for this expense.",
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        help="Date when this expense happened.",
    )
    category = fields.Selection([
        ('food', 'Food'),
        ('transport', 'Transport'),
        ('housing', 'Housing'),
        ('utilities', 'Utilities'),
        ('health', 'Health'),
        ('education', 'Education'),
        ('other', 'Other'),
    ], required=True, default='other', help="Category used for analysis and reporting.")
    note = fields.Text(help="Optional notes for this expense.")
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True,
        help="Company this expense belongs to.",
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        required=True,
        index=True,
        help="Owner of this expense entry.",
    )

    # Computed fields (for grouping and display)
    month_label = fields.Char(
        compute='_compute_month_label',
        store=True,
        help="Month label in YYYY-MM format for grouping.",
    )
    monthly_total = fields.Monetary(
        compute='_compute_monthly_total',
        currency_field='currency_id',
        help="Total expenses for the same company and month.",
    )

    _sql_constraints = [
        ('amount_non_negative', 'CHECK(amount >= 0)', 'Amount must be positive.'),
    ]

    @api.depends('date')
    def _compute_month_label(self):
        """Compute month label for search and grouping."""
        for rec in self:
            rec.month_label = rec.date.strftime('%Y-%m') if rec.date else False

    @api.depends('date', 'company_id')
    def _compute_monthly_total(self):
        """Compute monthly totals in one grouped query over the recordset range."""
        if not self:
            return

        min_date = min(rec.date for rec in self if rec.date)
        max_date = max(rec.date for rec in self if rec.date)
        domain = [
            ('company_id', 'in', self.mapped('company_id').ids),
            ('date', '>=', min_date),
            ('date', '<=', max_date),
        ]
        groups = self.env['expense.tracker.entry'].read_group(
            domain,
            ['amount:sum'],
            ['company_id', 'date:year', 'date:month'],
            lazy=False,
        )
        totals = {}
        for g in groups:
            company_id = g['company_id'][0]
            year = g['date:year']
            month = g['date:month']
            totals[(company_id, year, month)] = g.get('amount_sum', g.get('amount', 0.0)) or 0.0

        for rec in self:
            if rec.date and rec.company_id:
                key = (rec.company_id.id, rec.date.year, rec.date.month)
                rec.monthly_total = totals.get(key, 0.0)
            else:
                rec.monthly_total = 0.0

    @api.constrains('amount')
    def _check_amount_positive(self):
        """Provide user-friendly validation for negative values."""
        for rec in self:
            if rec.amount < 0:
                raise ValidationError('Amount must be positive.')