from odoo import api, fields, models


class LibrarySubject(models.Model):
    _name = 'library.subject'
    _description = 'Library Subject'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(index=True)
    description = fields.Text(translate=True)
    parent_ids = fields.Many2many('library.subject', 'library_subject_parent_rel', 'child_id', 'parent_id', string='Parents')
    child_ids = fields.Many2many('library.subject', 'library_subject_parent_rel', 'parent_id', 'child_id', string='Children')
    book_ids = fields.Many2many('library.book', 'library_book_subject_rel', 'subject_id', 'book_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    def _compute_book_count(self):
        for subject in self:
            subject.book_count = len(subject.book_ids)

    def action_view_books(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Books',
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('subject_ids', 'in', self.id)],
        }
