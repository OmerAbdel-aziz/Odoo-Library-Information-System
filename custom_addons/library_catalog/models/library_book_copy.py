from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryBookCopy(models.Model):
    _name = 'library.book.copy'
    _description = 'Library Book Copy'
    _order = 'branch_id, book_id, copy_number'
    _rec_names_search = ['name', 'barcode', 'book_id.name']
    _check_company_auto = True

    _VALID_TRANSITIONS = {
        'available': ['reserved', 'on_loan', 'in_transit', 'processing', 'repair', 'damaged', 'lost', 'missing', 'withdrawn', 'reference_only'],
        'reserved': ['available', 'on_loan'],
        'on_loan': ['available', 'damaged', 'lost', 'missing'],
        'in_transit': ['available', 'processing'],
        'processing': ['available', 'repair', 'damaged'],
        'repair': ['available', 'damaged'],
        'damaged': ['repair', 'withdrawn'],
        'lost': [],
        'missing': [],
        'withdrawn': [],
        'reference_only': ['available', 'withdrawn'],
    }

    name = fields.Char(compute='_compute_name', store=True)
    book_id = fields.Many2one('library.book', required=True, ondelete='restrict', index=True, check_company=True)
    copy_number = fields.Integer(string='Copy #')
    barcode = fields.Char(string='Barcode', index=True, copy=False)
    qr_code = fields.Char(string='QR Code', copy=False)
    branch_id = fields.Many2one('library.branch', required=True, ondelete='restrict', index=True, check_company=True)
    floor_id = fields.Many2one('library.floor', ondelete='set null', index=True, check_company=True)
    section_id = fields.Many2one('library.section', ondelete='set null', index=True, check_company=True)
    shelf_id = fields.Many2one('library.shelf', ondelete='set null', index=True, check_company=True)
    acquisition_date = fields.Date()
    acquisition_cost = fields.Float(digits=(10, 2))
    condition = fields.Selection(
        [
            ('new', 'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('damaged', 'Damaged'),
        ],
        default='new',
        required=True,
    )
    state = fields.Selection(
        [
            ('available', 'Available'),
            ('reserved', 'Reserved'),
            ('on_loan', 'On Loan'),
            ('in_transit', 'In Transit'),
            ('processing', 'Processing'),
            ('repair', 'Under Repair'),
            ('damaged', 'Damaged'),
            ('lost', 'Lost'),
            ('missing', 'Missing'),
            ('withdrawn', 'Withdrawn'),
            ('reference_only', 'Reference Only'),
        ],
        default='available',
        required=True,
        index=True,
    )
    stock_lot_id = fields.Many2one(
        'stock.lot',
        string='Stock Lot',
        ondelete='set null',
        help='Stock lot for traceability.',
    )
    reference_only = fields.Boolean(default=False)
    circulating = fields.Boolean(default=True)
    last_inventory_date = fields.Date()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.depends('book_id', 'copy_number')
    def _compute_name(self):
        for copy in self:
            name = copy.book_id.name or ''
            if copy.copy_number:
                name = f'{name} (#{copy.copy_number})'
            copy.name = name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                branch = self.env['library.branch'].browse(vals.get('branch_id'))
                branch_code = branch.code if branch else 'XX'
                seq = self.env['ir.sequence'].next_by_code('library.book.copy')
                vals['barcode'] = f'{branch_code}-BK-{seq}' if seq else False
        return super().create(vals_list)

    @api.constrains('barcode')
    def _check_barcode_unique(self):
        for copy in self:
            if copy.barcode and self.search_count([('barcode', '=', copy.barcode), ('id', '!=', copy.id)]):
                raise ValidationError('The copy barcode must be unique.')

    def _check_state_transition(self, new_state):
        for copy in self:
            allowed = self._VALID_TRANSITIONS.get(copy.state, [])
            if new_state not in allowed:
                raise ValidationError(
                    f'Cannot transition copy "{copy.barcode or copy.name}" from "{copy.state}" to "{new_state}".'
                )

    def action_available(self):
        self._check_state_transition('available')
        self.write({'state': 'available'})

    def action_reserved(self):
        self._check_state_transition('reserved')
        self.write({'state': 'reserved'})

    def action_on_loan(self):
        self._check_state_transition('on_loan')
        self.write({'state': 'on_loan'})

    def action_in_transit(self):
        self._check_state_transition('in_transit')
        self.write({'state': 'in_transit'})

    def action_processing(self):
        self._check_state_transition('processing')
        self.write({'state': 'processing'})

    def action_repair(self):
        self._check_state_transition('repair')
        self.write({'state': 'repair'})

    def action_damaged(self):
        self._check_state_transition('damaged')
        self.write({'state': 'damaged'})

    def action_lost(self):
        self._check_state_transition('lost')
        self.write({'state': 'lost'})

    def action_missing(self):
        self._check_state_transition('missing')
        self.write({'state': 'missing'})

    def action_withdrawn(self):
        self._check_state_transition('withdrawn')
        self.write({'state': 'withdrawn'})
