from odoo import fields, models


class LibraryPublisher(models.Model):
    _name = 'library.publisher'
    _description = 'Library Publisher'
    _order = 'name'
    _rec_names_search = ['name']

    name = fields.Char(required=True, translate=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='set null')
    country_id = fields.Many2one('res.country', string='Country')
    website = fields.Char()
    active = fields.Boolean(default=True)
    book_ids = fields.One2many('library.book', 'publisher_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    def _compute_book_count(self):
        for publisher in self:
            publisher.book_count = len(publisher.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Books',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('publisher_id', '=', self.id)],
        }
