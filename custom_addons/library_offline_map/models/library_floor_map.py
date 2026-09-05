from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryFloorMap(models.Model):
    _inherit = 'library.floor'

    plan_svg = fields.Binary(string='Floor Plan (SVG)', attachment=True)
    plan_filename = fields.Char(string='Plan File Name')
    shelf_count_mapped = fields.Integer(string='Mapped Shelves', compute='_compute_shelf_mapped')

    def _compute_shelf_mapped(self):
        Shelf = self.env['library.shelf']
        for floor in self:
            floor.shelf_count_mapped = Shelf.search_count([
                ('floor_id', '=', floor.id),
                ('map_placed', '=', True),
            ])

    @api.constrains('plan_svg')
    def _check_plan_size(self):
        for floor in self:
            if floor.plan_svg and len(floor.plan_svg) > 2 * 1024 * 1024 * 4 // 3:
                raise ValidationError('Floor plan SVG must be smaller than 2MB.')

    def action_view_indoor_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'library_indoor_map',
            'params': {'floor_id': self.id},
        }
