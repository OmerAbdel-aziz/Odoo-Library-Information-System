from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryPurchaseRequest(models.Model):
    _name = 'library.purchase.request'
    _description = 'Library Purchase Request'
    _order = 'request_date desc, id desc'
    _rec_names_search = ['name', 'book_name', 'member_id.member_number']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    member_id = fields.Many2one(
        'library.member', string='Requested For (Member)',
        ondelete='set null', index=True, check_company=True,
    )
    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, readonly=True,
    )
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    book_name = fields.Char(string='Book Title', required=True)
    author = fields.Char()
    isbn = fields.Char(string='ISBN')
    reason = fields.Text()
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    quantity = fields.Integer(default=1)
    estimated_cost = fields.Float(digits=(10, 2))
    branch_id = fields.Many2one(
        'library.branch', string='Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    shelf_id = fields.Many2one(
        'library.shelf', string='Shelf Assignment',
        ondelete='set null', index=True, check_company=True,
    )
    vendor_id = fields.Many2one(
        'res.partner', string='Vendor',
        domain="[('is_company', '=', True)]",
        ondelete='set null', index=True,
    )
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Purchase Order',
        ondelete='set null', readonly=True, copy=False,
    )
    book_id = fields.Many2one(
        'library.book', string='Cataloged Book',
        ondelete='set null', readonly=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('ordered', 'Ordered'),
            ('received', 'Received'),
            ('done', 'Cataloged'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft', required=True, index=True,
    )
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.purchase.request') or '/'
        return super().create(vals_list)

    @api.constrains('quantity')
    def _check_quantity(self):
        for request in self:
            if request.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise ValidationError('Only draft requests can be submitted.')
            if not request.book_name:
                raise ValidationError('Book title is required.')
            request.state = 'submitted'

    def action_approve(self):
        for request in self:
            if request.state != 'submitted':
                raise ValidationError('Only submitted requests can be approved.')
            request.approved_by = self.env.user
            request.state = 'approved'

    def action_create_po(self):
        PurchaseOrder = self.env['purchase.order']
        for request in self:
            if request.state != 'approved':
                raise ValidationError('Only approved requests can be ordered.')
            if not request.vendor_id:
                raise ValidationError('A vendor is required to create a purchase order.')
            if request.purchase_order_id:
                raise ValidationError('A purchase order already exists for this request.')
            product = self.env['product.product'].create({
                'name': request.book_name,
                'type': 'consu',
                'is_storable': True,
                'purchase_ok': True,
                'company_id': request.company_id.id,
            })
            po = PurchaseOrder.create({
                'partner_id': request.vendor_id.id,
                'company_id': request.company_id.id,
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'product_qty': request.quantity,
                    'price_unit': request.estimated_cost or 0.0,
                })],
            })
            po.button_confirm()
            request.purchase_order_id = po
            request.state = 'ordered'

    def action_receive(self):
        for request in self:
            if request.state != 'ordered':
                raise ValidationError('Only ordered requests can be received.')
            po = request.purchase_order_id
            if not po or po.state not in ('purchase', 'done'):
                raise ValidationError('Purchase order is not confirmed yet.')
            request.state = 'received'

    def action_catalog(self):
        Book = self.env['library.book']
        Copy = self.env['library.book.copy']
        for request in self:
            if request.state != 'received':
                raise ValidationError('Only received requests can be cataloged.')
            if request.book_id:
                raise ValidationError('This request has already been cataloged.')
            shelf = request.shelf_id
            book = Book.create({
                'name': request.book_name,
                'book_type': 'book',
                'company_id': request.company_id.id,
            })
            for _i in range(request.quantity):
                Copy.create({
                    'book_id': book.id,
                    'branch_id': request.branch_id.id,
                    'floor_id': shelf.floor_id.id if shelf and shelf.floor_id else False,
                    'section_id': shelf.section_id.id if shelf and shelf.section_id else False,
                    'shelf_id': shelf.id if shelf else False,
                })
            request.book_id = book
            request.state = 'done'

    def action_cancel(self):
        for request in self:
            if request.state not in ('draft', 'submitted', 'approved'):
                raise ValidationError('Only draft, submitted or approved requests can be cancelled.')
            request.state = 'cancelled'
