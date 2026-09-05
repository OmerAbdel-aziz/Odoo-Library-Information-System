from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibrarySerialIssue(models.Model):
    _name = 'library.serial.issue'
    _description = 'Library Serial Issue'
    _order = 'expected_date, id'
    _rec_names_search = ['name', 'label', 'subscription_id.title']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    subscription_id = fields.Many2one(
        'library.subscription', string='Subscription', required=True,
        ondelete='cascade', index=True, check_company=True,
    )
    branch_id = fields.Many2one(related='subscription_id.branch_id', store=True, readonly=True)
    label = fields.Char(required=True, help='Issue label, e.g. 2026-09.')
    expected_date = fields.Date(required=True)
    received_date = fields.Date()
    state = fields.Selection(
        [
            ('expected', 'Expected'),
            ('received', 'Received'),
            ('missing', 'Missing'),
            ('claimed', 'Claimed'),
        ],
        default='expected', required=True, index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    _unique_per_date = models.Constraint(
        'UNIQUE(subscription_id, expected_date)',
        'An issue already exists for this subscription and date.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.serial.issue') or '/'
        return super().create(vals_list)

    def write(self, vals):
        if ('state' in vals or 'received_date' in vals) and not self.env.context.get('serial_issue_action'):
            raise ValidationError('Use the workflow buttons to change issue status.')
        locked = {'subscription_id', 'expected_date', 'label'}
        if locked & set(vals) and any(issue.state != 'expected' for issue in self):
            raise ValidationError('Only expected issues can be edited.')
        return super().write(vals)

    @api.constrains('expected_date', 'subscription_id')
    def _check_expected_date(self):
        for issue in self:
            subscription = issue.subscription_id
            if issue.expected_date and subscription.start_date and issue.expected_date < subscription.start_date:
                raise ValidationError('Issue date cannot be before the subscription start date.')
            if issue.expected_date and subscription.end_date and issue.expected_date > subscription.end_date:
                raise ValidationError('Issue date cannot be after the subscription end date.')

    def _transition(self, state, **kwargs):
        self.with_context(serial_issue_action=True).write(dict(kwargs, state=state))

    def action_receive(self):
        for issue in self:
            if issue.state not in ('expected', 'claimed'):
                raise ValidationError('Only expected or claimed issues can be received.')
            issue._transition('received', received_date=fields.Date.context_today(self))

    def action_mark_missing(self):
        for issue in self:
            if issue.state != 'expected':
                raise ValidationError('Only expected issues can be marked missing.')
            issue._transition('missing')

    def action_claim(self):
        for issue in self:
            if issue.state != 'missing':
                raise ValidationError('Only missing issues can be claimed.')
            issue._transition('claimed')
