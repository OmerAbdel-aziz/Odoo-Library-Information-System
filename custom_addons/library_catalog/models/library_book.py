from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'name'
    _rec_names_search = ['name', 'isbn_13', 'isbn_10', 'classification_code_id.code']

    name = fields.Char(required=True, translate=True, index=True)
    subtitle = fields.Char(translate=True)
    isbn_10 = fields.Char(string='ISBN-10', index=True)
    isbn_13 = fields.Char(string='ISBN-13', index=True)
    edition = fields.Char(translate=True)
    publication_year = fields.Integer()
    author_ids = fields.Many2many(
        'library.author',
        'library_book_author_rel',
        'book_id',
        'author_id',
        string='Authors',
    )
    publisher_id = fields.Many2one('library.publisher', string='Publisher', index=True)
    language_id = fields.Many2one('library.language', string='Language', index=True)
    category_ids = fields.Many2many(
        'library.category',
        'library_book_category_rel',
        'book_id',
        'category_id',
        string='Categories',
    )
    subject_ids = fields.Many2many(
        'library.subject',
        'library_book_subject_rel',
        'book_id',
        'subject_id',
        string='Subjects',
    )
    classification_id = fields.Many2one('library.classification.system', string='Classification System', index=True)
    classification_code_id = fields.Many2one('library.classification.code', string='Classification Code', index=True)
    description = fields.Text(translate=True)
    page_count = fields.Integer()
    cover_image = fields.Image(string='Cover Image', max_width=1920, max_height=1920)
    book_type = fields.Selection(
        [
            ('book', 'Book'),
            ('reference_book', 'Reference Book'),
            ('journal', 'Journal'),
            ('magazine', 'Magazine'),
            ('thesis', 'Thesis'),
            ('research_paper', 'Research Paper'),
            ('audio_book', 'Audio Book'),
            ('e_book', 'E-Book'),
            ('other', 'Other'),
        ],
        default='book',
        required=True,
        index=True,
    )
    series_id = fields.Many2one('library.series', string='Series', index=True)
    product_id = fields.Many2one(
        'product.product',
        string='Related Product',
        ondelete='set null',
        help='Product template linked to this book for stock integration.',
    )
    copy_ids = fields.One2many('library.book.copy', 'book_id', string='Copies')
    copy_count = fields.Integer(compute='_compute_copy_count')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    @api.depends('copy_ids')
    def _compute_copy_count(self):
        for book in self:
            book.copy_count = len(book.copy_ids)

    @api.depends('name', 'author_ids')
    def _compute_display_name(self):
        for book in self:
            authors = ', '.join(book.author_ids.mapped('name'))
            book.display_name = f'{book.name} ({authors})' if authors else book.name

    @api.constrains('isbn_10')
    def _check_isbn_10(self):
        for book in self:
            if book.isbn_10:
                cleaned = book.isbn_10.replace('-', '').replace(' ', '')
                if len(cleaned) != 10 or not cleaned[:-1].isdigit() or cleaned[-1] not in '0123456789Xx':
                    raise ValidationError('Invalid ISBN-10 format.')

    @api.constrains('isbn_13')
    def _check_isbn_13(self):
        for book in self:
            if book.isbn_13:
                cleaned = book.isbn_13.replace('-', '').replace(' ', '')
                if len(cleaned) != 13 or not cleaned.isdigit():
                    raise ValidationError('Invalid ISBN-13 format.')

    def action_view_copies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Copies',
            'res_model': 'library.book.copy',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }
