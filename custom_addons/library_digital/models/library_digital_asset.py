from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryDigitalAsset(models.Model):
    _name = 'library.digital.asset'
    _description = 'Library Digital Asset'
    _order = 'title'
    _rec_names_search = ['name', 'title']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    title = fields.Char(required=True)
    asset_type = fields.Selection(
        [
            ('ebook', 'E-Book'),
            ('pdf', 'PDF'),
            ('audiobook', 'Audio Book'),
            ('research', 'Research Document'),
            ('journal', 'Digital Journal'),
        ],
        default='ebook', required=True, index=True,
    )
    author = fields.Char()
    description = fields.Text()
    file_data = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    branch_id = fields.Many2one(
        'library.branch', string='Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    access_mode = fields.Selection(
        [
            ('public', 'Public'),
            ('members', 'Members Only'),
            ('restricted', 'Restricted'),
        ],
        default='members', required=True,
    )
    download_allowed = fields.Boolean(string='Download Allowed', default=True)
    license_limit = fields.Integer(
        default=0,
        help='Maximum concurrent checkouts. 0 means unlimited.',
    )
    expiry_date = fields.Date(string='License Expiry')
    checkout_ids = fields.One2many('library.digital.checkout', 'asset_id', string='Checkouts')
    active_checkout_count = fields.Integer(compute='_compute_active_checkout_count', store=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.digital.asset') or '/'
        return super().create(vals_list)

    @api.constrains('license_limit')
    def _check_license_limit(self):
        for asset in self:
            if asset.license_limit < 0:
                raise ValidationError('License limit cannot be negative.')

    @api.depends('checkout_ids', 'checkout_ids.state')
    def _compute_active_checkout_count(self):
        for asset in self:
            asset.active_checkout_count = len(asset.checkout_ids.filtered(lambda c: c.state == 'active'))

    def _check_usable(self):
        self.ensure_one()
        if not self.active:
            raise ValidationError('This digital asset is archived.')
        if self.expiry_date and self.expiry_date < fields.Date.context_today(self):
            raise ValidationError('The license for "%s" has expired.' % self.title)

    def action_view_checkouts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Checkouts',
            'res_model': 'library.digital.checkout',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }
