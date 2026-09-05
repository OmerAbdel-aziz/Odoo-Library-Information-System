from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibrarySubscription(models.Model):
    _name = 'library.subscription'
    _description = 'Library Subscription'
    _order = 'title'
    _rec_names_search = ['name', 'title', 'supplier_id.name']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    title = fields.Char(required=True)
    supplier_id = fields.Many2one(
        'res.partner', string='Supplier',
        domain="[('supplier_rank', '>', 0)]",
        ondelete='set null', index=True,
    )
    branch_id = fields.Many2one(
        'library.branch', string='Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date()
    frequency = fields.Selection(
        [
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly', required=True,
    )
    cost = fields.Float(digits=(10, 2))
    expected_next_issue = fields.Date(compute='_compute_expected_next_issue', store=True)
    issue_ids = fields.One2many('library.serial.issue', 'subscription_id', string='Issues')
    issue_count = fields.Integer(compute='_compute_issue_count', store=True)
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    _FREQUENCY_DELTAS = {
        'daily': relativedelta(days=1),
        'weekly': relativedelta(weeks=1),
        'monthly': relativedelta(months=1),
        'quarterly': relativedelta(months=3),
        'yearly': relativedelta(years=1),
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.subscription') or '/'
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for subscription in self:
            if subscription.end_date and subscription.start_date and subscription.end_date < subscription.start_date:
                raise ValidationError('Subscription end date must be after start date.')

    @api.depends('issue_ids', 'issue_ids.expected_date', 'issue_ids.state', 'start_date', 'frequency')
    def _compute_expected_next_issue(self):
        for subscription in self:
            if not subscription.issue_ids:
                subscription.expected_next_issue = subscription.start_date
                continue
            pending = subscription.issue_ids.filtered(lambda i: i.state == 'expected' and i.expected_date)
            if pending:
                subscription.expected_next_issue = min(pending.mapped('expected_date'))
                continue
            received = subscription.issue_ids.filtered(lambda i: i.state == 'received' and i.expected_date)
            anchor = max(received.mapped('expected_date')) if received else subscription.start_date
            subscription.expected_next_issue = anchor + self._FREQUENCY_DELTAS[subscription.frequency] if anchor else False

    @api.depends('issue_ids')
    def _compute_issue_count(self):
        for subscription in self:
            subscription.issue_count = len(subscription.issue_ids)

    def action_generate_issues(self, count=6):
        Issue = self.env['library.serial.issue']
        for subscription in self:
            pending = len(subscription.issue_ids.filtered(lambda i: i.state == 'expected'))
            to_create = count - pending
            if to_create <= 0:
                continue
            existing_labels = set(subscription.issue_ids.mapped('label'))
            existing_dates = subscription.issue_ids.mapped('expected_date')
            if existing_dates:
                date = max(existing_dates) + self._FREQUENCY_DELTAS[subscription.frequency]
            else:
                date = subscription.start_date
            created = 0
            attempts = 0
            while created < to_create and attempts < to_create + 100:
                attempts += 1
                if subscription.end_date and date > subscription.end_date:
                    break
                label = date.strftime('%Y-%m')
                if label not in existing_labels:
                    Issue.create({
                        'subscription_id': subscription.id,
                        'label': label,
                        'expected_date': date,
                    })
                    existing_labels.add(label)
                    created += 1
                date = date + self._FREQUENCY_DELTAS[subscription.frequency]

    def action_view_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issues',
            'res_model': 'library.serial.issue',
            'view_mode': 'list,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id},
        }
