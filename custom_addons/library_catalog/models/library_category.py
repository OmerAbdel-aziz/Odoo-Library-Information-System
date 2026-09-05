from odoo import api, fields, models


class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Library Category'
    _order = 'name'
    _rec_names_search = ['name', 'code']
    _parent_store = True

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(index=True)
    parent_id = fields.Many2one('library.category', string='Parent Category', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('library.category', 'parent_id', string='Subcategories')
    book_ids = fields.Many2many('library.book', 'library_book_category_rel', 'category_id', 'book_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    def _compute_book_count(self):
        for category in self:
            category.book_count = len(category.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Books',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('category_ids', 'in', self.id)],
        }
