from odoo import fields, models


class LibrarySeries(models.Model):
    _name = 'library.series'
    _description = 'Library Series'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(index=True)
    description = fields.Text(translate=True)
    book_ids = fields.One2many('library.book', 'series_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    def _compute_book_count(self):
        for series in self:
            series.book_count = len(series.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Books',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('series_id', '=', self.id)],
        }
