from odoo import models


class LibraryBookInventory(models.Model):
    _inherit = 'library.book'

    def action_ensure_product(self):
        Product = self.env['product.product']
        for book in self:
            if book.product_id:
                continue
            book.product_id = Product.create({
                'name': book.name,
                'type': 'consu',
                'is_storable': True,
                'tracking': 'lot',
                'company_id': book.company_id.id,
            })
