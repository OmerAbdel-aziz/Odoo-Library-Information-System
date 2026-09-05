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
    due_date = fields.Date()
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
        checkouts = super().create(vals_list)
        for checkout in checkouts:
            checkout._check_eligible()
            if not checkout.due_date:
                checkout.due_date = fields.Date.context_today(self) + relativedelta(days=14)
        return checkouts

    def _check_eligible(self):
        self.ensure_one()
        member = self.member_id
        if member.status != 'active':
            raise ValidationError('Only active members can check out digital assets.')
        if member.blocked:
            raise ValidationError('This member is blocked and cannot check out digital assets.')
        asset = self.asset_id
        asset._check_usable()
        if self.search_count([
            ('member_id', '=', member.id),
            ('asset_id', '=', asset.id),
            ('state', '=', 'active'),
            ('id', '!=', self.id),
        ]):
            raise ValidationError('This member already has an active checkout of "%s".' % asset.title)
        if asset.license_limit and asset.active_checkout_count > asset.license_limit:
            raise ValidationError('License limit reached for "%s".' % asset.title)

    def action_download(self):
        for checkout in self:
            if checkout.state != 'active':
                raise ValidationError('Only active checkouts can be downloaded.')
            checkout.asset_id._check_usable()
            if not checkout.asset_id.download_allowed:
                raise ValidationError('Downloading is not allowed for "%s".' % checkout.asset_id.title)
            checkout.download_count += 1

    def action_return(self):
        for checkout in self:
            if checkout.state != 'active':
                raise ValidationError('Only active checkouts can be returned.')
            checkout.return_date = fields.Date.context_today(self)
            checkout.state = 'returned'

    @api.model
    def _cron_expire_checkouts(self):
        expired = self.search([
            ('state', '=', 'active'),
            ('due_date', '<', fields.Date.context_today(self)),
        ])
        expired.write({'state': 'expired'})
