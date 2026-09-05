import base64

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryShelfMap(models.Model):
    _inherit = 'library.shelf'

    map_x = fields.Float(string='Map X (%)', digits=(5, 2), default=0.0)
    map_y = fields.Float(string='Map Y (%)', digits=(5, 2), default=0.0)
    map_width = fields.Float(string='Map Width (%)', digits=(5, 2), default=10.0)
    map_height = fields.Float(string='Map Height (%)', digits=(5, 2), default=5.0)
    map_placed = fields.Boolean(compute='_compute_map_placed', store=True)

    @api.depends('map_x', 'map_y', 'map_width', 'map_height')
    def _compute_map_placed(self):
        for shelf in self:
            shelf.map_placed = bool(shelf.map_width > 0 and shelf.map_height > 0)

    @api.constrains('map_x', 'map_y', 'map_width', 'map_height')
    def _check_map_bounds(self):
        for shelf in self:
            for fname in ('map_x', 'map_y', 'map_width', 'map_height'):
                value = shelf[fname]
                if value < 0 or value > 100:
                    raise ValidationError('Shelf map coordinates must be between 0 and 100.')
            if shelf.map_x + shelf.map_width > 100 or shelf.map_y + shelf.map_height > 100:
                raise ValidationError('Shelf map rectangle must fit inside the floor plan.')
