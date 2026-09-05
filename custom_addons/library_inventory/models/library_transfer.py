from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryTransfer(models.Model):
    _name = 'library.transfer'
    _description = 'Library Inter-Branch Transfer'
    _order = 'create_date desc'
    _rec_names_search = ['name', 'book_copy_id.barcode']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    book_copy_id = fields.Many2one(
        'library.book.copy', string='Copy', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    book_id = fields.Many2one(related='book_copy_id.book_id', store=True, readonly=True)
    source_branch_id = fields.Many2one(
        'library.branch', string='Source Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    dest_branch_id = fields.Many2one(
        'library.branch', string='Destination Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    picking_id = fields.Many2one('stock.picking', string='Stock Transfer', readonly=True, copy=False)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user, readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection(
        [
            ('requested', 'Requested'),
            ('approved', 'Approved'),
            ('prepared', 'Prepared'),
            ('in_transit', 'In Transit'),
            ('received', 'Received'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='requested', required=True, index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(related='source_branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.transfer')
        return super().create(vals_list)

    @api.constrains('source_branch_id', 'dest_branch_id')
    def _check_branches(self):
        for transfer in self:
            if transfer.source_branch_id == transfer.dest_branch_id:
                raise ValidationError('Source and destination branches must be different.')
            if transfer.source_branch_id.company_id != transfer.dest_branch_id.company_id:
                raise ValidationError('Inter-company transfers are not supported.')

    def action_approve(self):
        for transfer in self:
            if transfer.state != 'requested':
                raise ValidationError('Only requested transfers can be approved.')
            if transfer.book_copy_id.state != 'available':
                raise ValidationError('Copy "%s" is not available for transfer.' % (transfer.book_copy_id.barcode or transfer.book_copy_id.name))
            transfer.approved_by = self.env.user
            transfer.state = 'approved'

    def action_prepare(self):
        Picking = self.env['stock.picking']
        for transfer in self:
            if transfer.state != 'approved':
                raise ValidationError('Only approved transfers can be prepared.')
            source = transfer.source_branch_id
            dest = transfer.dest_branch_id
            source.action_setup_stock_locations()
            dest.action_setup_stock_locations()
            copy = transfer.book_copy_id
            copy.action_ensure_lot()
            self.env['stock.quant']._update_available_quantity(
                copy.book_id.product_id,
                source.available_location_id,
                1,
                lot_id=copy.stock_lot_id,
            )
            picking_type = source.warehouse_id.int_type_id
            if not picking_type:
                raise ValidationError('Source warehouse has no internal operation type.')
            transfer.picking_id = Picking.create({
                'picking_type_id': picking_type.id,
                'location_id': source.available_location_id.id,
                'location_dest_id': dest.processing_location_id.id,
                'move_ids': [(0, 0, {
                    'product_id': copy.book_id.product_id.id,
                    'product_uom_qty': 1,
                    'product_uom': copy.book_id.product_id.uom_id.id,
                    'location_id': source.available_location_id.id,
                    'location_dest_id': dest.processing_location_id.id,
                })],
            })
            transfer.picking_id.action_confirm()
            transfer.picking_id.action_assign()
            for line in transfer.picking_id.move_line_ids:
                line.lot_id = copy.stock_lot_id
            copy.action_in_transit()
            transfer.state = 'prepared'

    def action_ship(self):
        for transfer in self:
            if transfer.state != 'prepared':
                raise ValidationError('Only prepared transfers can be shipped.')
            transfer.picking_id.button_validate()
            transfer.state = 'in_transit'

    def action_receive(self):
        for transfer in self:
            if transfer.state != 'in_transit':
                raise ValidationError('Only in-transit transfers can be received.')
            transfer.state = 'received'

    def action_complete(self):
        for transfer in self:
            if transfer.state != 'received':
                raise ValidationError('Only received transfers can be completed.')
            copy = transfer.book_copy_id
            copy.write({
                'branch_id': transfer.dest_branch_id.id,
                'floor_id': False,
                'section_id': False,
                'shelf_id': False,
            })
            copy.action_available()
            transfer.state = 'completed'

    def action_cancel(self):
        for transfer in self:
            if transfer.state in ('completed', 'cancelled'):
                raise ValidationError('Completed or cancelled transfers cannot be cancelled.')
            if transfer.state in ('prepared', 'in_transit') and transfer.picking_id:
                transfer.picking_id.action_cancel()
            if transfer.state in ('prepared', 'in_transit', 'received'):
                transfer.book_copy_id.action_available()
            transfer.state = 'cancelled'
