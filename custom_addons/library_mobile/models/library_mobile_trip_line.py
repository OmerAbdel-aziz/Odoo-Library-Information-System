from odoo import fields, models


class LibraryMobileTripLine(models.Model):
    _name = 'library.mobile.trip.line'
    _description = 'Library Mobile Trip Line'
    _order = 'trip_id, id'
    _rec_names_search = ['book_copy_id.barcode']
    _check_company_auto = True

    trip_id = fields.Many2one('library.mobile.trip', required=True, ondelete='cascade', index=True)
    book_copy_id = fields.Many2one(
        'library.book.copy', string='Copy', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    book_id = fields.Many2one(related='book_copy_id.book_id', store=True, readonly=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('loaded', 'Loaded'),
            ('in_transit', 'In Transit'),
            ('returned', 'Returned'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft', required=True, index=True,
    )
    company_id = fields.Many2one(related='trip_id.company_id', store=True, readonly=True)
