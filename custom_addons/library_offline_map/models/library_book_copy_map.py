from odoo import models


class LibraryBookCopyMap(models.Model):
    _inherit = 'library.book.copy'

    def action_show_on_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'library_indoor_map',
            'params': {
                'floor_id': self.floor_id.id if self.floor_id else False,
                'highlight_shelf_id': self.shelf_id.id if self.shelf_id else False,
            },
        }
