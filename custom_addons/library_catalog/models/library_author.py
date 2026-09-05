from odoo import fields, models


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = 'Library Author'
    _order = 'name'
    _rec_names_search = ['name']

    name = fields.Char(required=True, translate=True, index=True)
    birth_date = fields.Date()
    death_date = fields.Date()
    country_id = fields.Many2one('res.country', string='Country')
    biography = fields.Text(translate=True)
    image_1920 = fields.Image(string='Image', max_width=1920, max_height=1920)
    website = fields.Char()
    book_ids = fields.Many2many('library.book', 'library_book_author_rel', 'author_id', 'book_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    def _compute_book_count(self):
        for author in self:
            author.book_count = len(author.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Books',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('author_ids', 'in', self.id)],
        }
