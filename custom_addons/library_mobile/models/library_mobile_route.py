from odoo import api, fields, models


class LibraryMobileRoute(models.Model):
    _name = 'library.mobile.route'
    _description = 'Library Mobile Route'
    _order = 'name'
    _rec_names_search = ['name', 'title']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    title = fields.Char(string='Route Title', required=True)
    unit_id = fields.Many2one(
        'library.mobile.unit', string='Unit', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    branch_id = fields.Many2one(related='unit_id.home_branch_id', store=True, readonly=True)
    stop_ids = fields.One2many('library.mobile.stop', 'route_id', string='Stops')
    stop_count = fields.Integer(compute='_compute_stop_count', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.mobile.route') or '/'
        return super().create(vals_list)

    @api.depends('stop_ids')
    def _compute_stop_count(self):
        for route in self:
            route.stop_count = len(route.stop_ids)
