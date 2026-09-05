import base64
import xml.etree.ElementTree as ET

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryFloorMap(models.Model):
    _inherit = 'library.floor'

    plan_svg = fields.Binary(string='Floor Plan (SVG)', attachment=True)
    plan_filename = fields.Char(string='Plan File Name')
    shelf_count_mapped = fields.Integer(string='Mapped Shelves', compute='_compute_shelf_mapped')

    def _compute_shelf_mapped(self):
        groups = self.env['library.shelf']._read_group(
            [('floor_id', 'in', self.ids), ('map_placed', '=', True)],
            ['floor_id'], ['__count'],
        )
        counts = {floor.id: count for floor, count in groups}
        for floor in self:
            floor.shelf_count_mapped = counts.get(floor.id, 0)

    @api.constrains('plan_svg')
    def _check_plan_size(self):
        for floor in self:
            if not floor.plan_svg:
                continue
            if len(floor.plan_svg) > 2 * 1024 * 1024 * 4 // 3:
                raise ValidationError('Floor plan SVG must be smaller than 2MB.')
            try:
                root = ET.fromstring(base64.b64decode(floor.plan_svg))
            except Exception:
                raise ValidationError('Floor plan must be a valid SVG file.')
            if not root.tag.endswith('svg'):
                raise ValidationError('Floor plan must be a valid SVG file.')

    def action_view_indoor_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'library_indoor_map',
            'params': {'floor_id': self.id},
        }
