from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryBranch(models.Model):
    _name = 'library.branch'
    _description = 'Library Branch'
    _order = 'code, name'
    _rec_names_search = ['name', 'code', 'city']
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    manager_id = fields.Many2one(
        'res.users',
        string='Branch Manager',
        domain="[('share', '=', False)]",
        check_company=True,
    )
    phone = fields.Char()
    email = fields.Char()
    street = fields.Char()
    city = fields.Char(index=True)
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    opening_time = fields.Float(string='Opening Time')
    closing_time = fields.Float(string='Closing Time')
    working_day_ids = fields.Many2many(
        'library.weekday',
        'library_branch_weekday_rel',
        'branch_id',
        'weekday_id',
        string='Working Days',
    )
    floor_ids = fields.One2many('library.floor', 'branch_id', string='Floors')
    floor_count = fields.Integer(compute='_compute_location_counts')
    section_count = fields.Integer(compute='_compute_location_counts')
    shelf_count = fields.Integer(compute='_compute_location_counts')
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint('UNIQUE(code)', 'The branch code must be unique.')
    _opening_time_range = models.Constraint('CHECK(opening_time >= 0 AND opening_time <= 24)', 'Opening time must be between 0 and 24.')
    _closing_time_range = models.Constraint('CHECK(closing_time >= 0 AND closing_time <= 24)', 'Closing time must be between 0 and 24.')

    @api.depends('floor_ids', 'floor_ids.section_ids', 'floor_ids.section_ids.shelf_ids')
    def _compute_location_counts(self):
        Section = self.env['library.section']
        Shelf = self.env['library.shelf']
        for branch in self:
            branch.floor_count = len(branch.floor_ids)
            branch.section_count = Section.search_count([('branch_id', '=', branch.id)])
            branch.shelf_count = Shelf.search_count([('branch_id', '=', branch.id)])

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for branch in self:
            branch.display_name = branch.code and f'[{branch.code}] {branch.name}' or branch.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].strip().upper()
        return super().write(vals)

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for branch in self:
            if branch.latitude and not -90 <= branch.latitude <= 90:
                raise ValidationError('Latitude must be between -90 and 90.')
            if branch.longitude and not -180 <= branch.longitude <= 180:
                raise ValidationError('Longitude must be between -180 and 180.')

    @api.constrains('opening_time', 'closing_time')
    def _check_working_hours(self):
        for branch in self:
            if branch.opening_time and branch.closing_time and branch.opening_time >= branch.closing_time:
                raise ValidationError('Closing time must be later than opening time.')

    def action_view_floors(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Floors',
            'res_model': 'library.floor',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
            'context': {'default_branch_id': self.id},
        }

    def action_view_sections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sections',
            'res_model': 'library.section',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
        }

    def action_view_shelves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shelves',
            'res_model': 'library.shelf',
            'view_mode': 'list,form',
            'domain': [('branch_id', '=', self.id)],
        }
