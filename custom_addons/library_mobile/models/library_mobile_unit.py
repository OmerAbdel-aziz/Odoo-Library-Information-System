from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMobileUnit(models.Model):
    _name = 'library.mobile.unit'
    _description = 'Library Mobile Unit'
    _order = 'name'
    _rec_names_search = ['name', 'vehicle_number']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    title = fields.Char(string='Unit Title', required=True)
    vehicle_number = fields.Char(string='Vehicle Number')
    capacity = fields.Integer(default=0, help='Maximum copies per trip. 0 means unlimited.')
    home_branch_id = fields.Many2one(
        'library.branch', string='Home Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    driver_id = fields.Many2one('res.users', string='Driver')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related='home_branch_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.mobile.unit') or '/'
        return super().create(vals_list)

    @api.constrains('capacity')
    def _check_capacity(self):
        for unit in self:
            if unit.capacity < 0:
                raise ValidationError('Unit capacity cannot be negative.')
