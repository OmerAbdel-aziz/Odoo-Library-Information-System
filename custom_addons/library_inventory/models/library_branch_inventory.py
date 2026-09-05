from odoo import fields, models
from odoo.exceptions import ValidationError


class LibraryBranchInventory(models.Model):
    _inherit = 'library.branch'

    processing_location_id = fields.Many2one(
        'stock.location', string='Processing Location', ondelete='set null',
        domain="[('usage', '=', 'internal')]",
    )
    available_location_id = fields.Many2one(
        'stock.location', string='Available Location', ondelete='set null',
        domain="[('usage', '=', 'internal')]",
    )
    hold_shelf_location_id = fields.Many2one(
        'stock.location', string='Hold Shelf Location', ondelete='set null',
        domain="[('usage', '=', 'internal')]",
    )
    repair_location_id = fields.Many2one(
        'stock.location', string='Repair Location', ondelete='set null',
        domain="[('usage', '=', 'internal')]",
    )
    withdrawn_location_id = fields.Many2one(
        'stock.location', string='Withdrawn Location', ondelete='set null',
        domain="[('usage', '=', 'internal')]",
    )

    _LOCATION_SPECS = [
        ('processing_location_id', 'Processing'),
        ('available_location_id', 'Available'),
        ('hold_shelf_location_id', 'Hold Shelf'),
        ('repair_location_id', 'Repair'),
        ('withdrawn_location_id', 'Withdrawn'),
    ]

    def action_setup_stock_locations(self):
        Location = self.env['stock.location']
        for branch in self:
            if not branch.warehouse_id:
                raise ValidationError('Branch "%s" has no warehouse set.' % branch.name)
            parent = branch.warehouse_id.lot_stock_id
            if not parent:
                raise ValidationError('Warehouse of branch "%s" has no stock location.' % branch.name)
            for field_name, suffix in self._LOCATION_SPECS:
                if branch[field_name]:
                    continue
                branch[field_name] = Location.create({
                    'name': '%s %s' % (branch.code or branch.name, suffix),
                    'usage': 'internal',
                    'location_id': parent.id,
                    'company_id': branch.company_id.id,
                })
