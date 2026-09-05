from odoo import api, fields, models


class LibrarySection(models.Model):
    _name = 'library.section'
    _description = 'Library Section'
    _order = 'branch_id, floor_id, sequence, name'
    _rec_names_search = ['name', 'code', 'floor_id.name', 'branch_id.name', 'branch_id.code']
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    section_type = fields.Selection(
        [
            ('general', 'General'),
            ('reading', 'Reading Area'),
            ('kids', 'Kids Area'),
            ('reference', 'Reference Area'),
            ('store', 'Store'),
        ],
        default='general',
        required=True,
    )
    floor_id = fields.Many2one('library.floor', required=True, ondelete='restrict', index=True, check_company=True)
    branch_id = fields.Many2one(related='floor_id.branch_id', store=True, readonly=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    shelf_ids = fields.One2many('library.shelf', 'section_id', string='Shelves')
    active = fields.Boolean(default=True)

    _code_floor_unique = models.Constraint('UNIQUE(code, floor_id)', 'The section code must be unique per floor.')
    _name_floor_unique = models.Constraint('UNIQUE(name, floor_id)', 'The section name must be unique per floor.')

    @api.depends('name', 'code', 'floor_id')
    def _compute_display_name(self):
        for section in self:
            label = section.code and f'[{section.code}] {section.name}' or section.name
            section.display_name = section.floor_id and f'{section.floor_id.display_name} / {label}' or label

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
