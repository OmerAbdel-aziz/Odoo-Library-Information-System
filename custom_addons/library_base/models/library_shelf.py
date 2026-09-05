from odoo import api, fields, models


class LibraryShelf(models.Model):
    _name = 'library.shelf'
    _description = 'Library Shelf'
    _order = 'branch_id, floor_id, section_id, sequence, name'
    _rec_names_search = ['name', 'code', 'section_id.name', 'floor_id.name', 'branch_id.name', 'branch_id.code']
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    section_id = fields.Many2one('library.section', required=True, ondelete='restrict', index=True, check_company=True)
    floor_id = fields.Many2one(related='section_id.floor_id', store=True, readonly=True)
    branch_id = fields.Many2one(related='section_id.branch_id', store=True, readonly=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    _code_section_unique = models.Constraint('UNIQUE(code, section_id)', 'The shelf code must be unique per section.')
    _name_section_unique = models.Constraint('UNIQUE(name, section_id)', 'The shelf name must be unique per section.')

    @api.depends('name', 'code', 'section_id')
    def _compute_display_name(self):
        for shelf in self:
            label = shelf.code and f'[{shelf.code}] {shelf.name}' or shelf.name
            shelf.display_name = shelf.section_id and f'{shelf.section_id.display_name} / {label}' or label

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
