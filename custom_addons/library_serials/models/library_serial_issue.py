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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.serial.issue') or '/'
        return super().create(vals_list)

    def action_receive(self):
        for issue in self:
            if issue.state not in ('expected', 'claimed'):
                raise ValidationError('Only expected or claimed issues can be received.')
            issue.received_date = fields.Date.context_today(self)
            issue.state = 'received'

    def action_mark_missing(self):
        for issue in self:
            if issue.state != 'expected':
                raise ValidationError('Only expected issues can be marked missing.')
            issue.state = 'missing'

    def action_claim(self):
        for issue in self:
            if issue.state != 'missing':
                raise ValidationError('Only missing issues can be claimed.')
            issue.state = 'claimed'
