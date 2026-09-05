from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryDigitalCheckout(models.Model):
    _name = 'library.digital.checkout'
    _description = 'Library Digital Checkout'
    _order = 'checkout_date desc, id desc'
    _rec_names_search = ['name', 'member_id.member_number', 'asset_id.title']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    member_id = fields.Many2one(
        'library.member', string='Member', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    asset_id = fields.Many2one(
        'library.digital.asset', string='Asset', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    branch_id = fields.Many2one(related='asset_id.branch_id', store=True, readonly=True)
    checkout_date = fields.Date(default=fields.Date.context_today, required=True)
    due_date = fields.Date(required=True)
    return_date = fields.Date()
    download_count = fields.Integer(default=0, readonly=True)
    state = fields.Selection(
        [
            ('active', 'Active'),
            ('returned', 'Returned'),
            ('expired', 'Expired'),
        ],
        default='active', required=True, index=True,
    )
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.digital.checkout') or '/'
            if not vals.get('due_date'):
                member = self.env['library.member'].browse(vals.get('member_id'))
                plan = member.membership_plan_id if member else False
                loan_days = plan.loan_period_days if plan else 14
                vals['due_date'] = fields.Date.context_today(self) + relativedelta(days=loan_days)
        checkouts = super().create(vals_list)
        for checkout in checkouts:
            checkout._check_eligible()
        return checkouts

    def write(self, vals):
        if not self.env.context.get('digital_checkout_action'):
            if 'state' in vals:
                raise ValidationError('Use the workflow buttons to change checkout status.')
            locked = {'member_id', 'asset_id', 'due_date', 'checkout_date'}
            if locked & set(vals) and any(c.state != 'active' for c in self):
                raise ValidationError('Only active checkouts can be modified.')
            if ({'member_id', 'asset_id'} & set(vals)) and any(c.state == 'active' for c in self):
                raise ValidationError('Member and asset cannot be changed on an active checkout.')
        return super().write(vals)

    def _check_eligible(self):
        self.ensure_one()
        member = self.member_id
        if member.status != 'active':
            raise ValidationError('Only active members can check out digital assets.')
        if member.blocked:
            raise ValidationError('This member is blocked and cannot check out digital assets.')
        asset = self.asset_id
        asset._check_usable()
        if asset.access_mode == 'restricted' and member.membership_plan_id not in asset.allowed_plan_ids:
            raise ValidationError('"%s" is restricted to specific membership plans.' % asset.title)
        if self.search_count([
            ('member_id', '=', member.id),
            ('asset_id', '=', asset.id),
            ('state', '=', 'active'),
            ('id', '!=', self.id),
        ]):
            raise ValidationError('This member already has an active checkout of "%s".' % asset.title)
        active_count = self.search_count([
            ('asset_id', '=', asset.id),
            ('state', '=', 'active'),
        ])
        if asset.license_limit and active_count > asset.license_limit:
            raise ValidationError('License limit reached for "%s".' % asset.title)

    def action_download(self):
        for checkout in self:
            if checkout.state != 'active':
                raise ValidationError('Only active checkouts can be downloaded.')
            checkout.asset_id._check_usable()
            if not checkout.asset_id.download_allowed:
                raise ValidationError('Downloading is not allowed for "%s".' % checkout.asset_id.title)
            checkout.with_context(digital_checkout_action=True).download_count += 1

    def action_return(self):
        for checkout in self:
            if checkout.state != 'active':
                raise ValidationError('Only active checkouts can be returned.')
            checkout.with_context(digital_checkout_action=True).write({
                'return_date': fields.Date.context_today(self),
                'state': 'returned',
            })

    @api.model
    def _cron_expire_checkouts(self):
        expired = self.search([
            ('state', '=', 'active'),
            ('due_date', '<', fields.Date.context_today(self)),
        ])
        expired.with_context(digital_checkout_action=True).write({'state': 'expired'})
