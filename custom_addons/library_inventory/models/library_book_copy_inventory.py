from odoo import models


class LibraryBookCopyInventory(models.Model):
    _inherit = 'library.book.copy'

    def action_ensure_lot(self):
        Lot = self.env['stock.lot']
        for copy in self:
            if copy.stock_lot_id:
                continue
            copy.book_id.action_ensure_product()
            copy.stock_lot_id = Lot.create({
                'name': copy.barcode or 'COPY-%d' % copy.id,
                'product_id': copy.book_id.product_id.id,
                'company_id': copy.company_id.id,
            })
