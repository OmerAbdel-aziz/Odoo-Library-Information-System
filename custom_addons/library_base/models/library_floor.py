from odoo import api, fields, models


class LibraryFloor(models.Model):
    _name = 'library.floor'
    _description = 'Library Floor'
    _order = 'branch_id, sequence, name'
    _rec_names_search = ['name', 'code', 'branch_id.name', 'branch_id.code']
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    branch_id = fields.Many2one('library.branch', required=True, ondelete='restrict', index=True, check_company=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    section_ids = fields.One2many('library.section', 'floor_id', string='Sections')
    active = fields.Boolean(default=True)

    _code_branch_unique = models.Constraint('UNIQUE(code, branch_id)', 'The floor code must be unique per branch.')
    _name_branch_unique = models.Constraint('UNIQUE(name, branch_id)', 'The floor name must be unique per branch.')

    @api.depends('name', 'code', 'branch_id')
    def _compute_display_name(self):
        for floor in self:
            label = floor.code and f'[{floor.code}] {floor.name}' or floor.name
            floor.display_name = floor.branch_id and f'{floor.branch_id.display_name} / {label}' or label

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
