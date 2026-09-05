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
                vals['name'] = self.env['ir.sequence'].next_by_code('library.transfer') or '/'
        return super().create(vals_list)

    @api.constrains('source_branch_id', 'dest_branch_id')
    def _check_branches(self):
        for transfer in self:
            if transfer.source_branch_id == transfer.dest_branch_id:
                raise ValidationError('Source and destination branches must be different.')
            if transfer.source_branch_id.company_id != transfer.dest_branch_id.company_id:
                raise ValidationError('Inter-company transfers are not supported.')

    def _check_copy_ready(self):
        self.ensure_one()
        copy = self.book_copy_id
        if copy.branch_id != self.source_branch_id:
            raise ValidationError('Copy "%s" is not at the source branch.' % (copy.barcode or copy.name))
        if copy.state != 'available':
            raise ValidationError('Copy "%s" is not available for transfer.' % (copy.barcode or copy.name))
        if self.search_count([
            ('book_copy_id', '=', copy.id),
            ('state', 'not in', ('completed', 'cancelled')),
            ('id', '!=', self.id),
        ]):
            raise ValidationError('Copy "%s" already has an open transfer.' % (copy.barcode or copy.name))

    def _lot_available_qty(self, product, lot, location):
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('lot_id', '=', lot.id),
            ('location_id', '=', location.id),
        ])
        return sum(quants.mapped('quantity'))

    def _move_lot(self, product, lot, source_location, dest_location, picking_type):
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'company_id': source_location.company_id.id,
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        if not picking.move_line_ids:
            raise ValidationError('No stock move lines generated for the transfer.')
        for line in picking.move_line_ids:
            line.lot_id = lot
            line.quantity = 1
        picking.button_validate()
        if picking.state != 'done':
            raise ValidationError('Stock transfer could not be completed.')
        return picking

    def action_approve(self):
        for transfer in self:
            if transfer.state != 'requested':
                raise ValidationError('Only requested transfers can be approved.')
            transfer._check_copy_ready()
            transfer.approved_by = self.env.user
            transfer.state = 'approved'

    def action_prepare(self):
        for transfer in self:
            if transfer.state != 'approved':
                raise ValidationError('Only approved transfers can be prepared.')
            transfer._check_copy_ready()
            source = transfer.source_branch_id
            dest = transfer.dest_branch_id
            source.action_setup_stock_locations()
            dest.action_setup_stock_locations()
            copy = transfer.book_copy_id
            copy.action_ensure_lot()
            product = copy.book_id.product_id
            if self._lot_available_qty(product, copy.stock_lot_id, source.available_location_id) < 1:
                self.env['stock.quant']._update_available_quantity(
                    product,
                    source.available_location_id,
                    1,
                    lot_id=copy.stock_lot_id,
                )
            picking_type = source.warehouse_id.int_type_id
            if not picking_type:
                raise ValidationError('Source warehouse has no internal operation type.')
            transfer.picking_id = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': source.available_location_id.id,
                'location_dest_id': dest.processing_location_id.id,
                'company_id': transfer.company_id.id,
                'move_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'location_id': source.available_location_id.id,
                    'location_dest_id': dest.processing_location_id.id,
                })],
            })
            transfer.picking_id.action_confirm()
            transfer.picking_id.action_assign()
            if not transfer.picking_id.move_line_ids:
                raise ValidationError('No stock move lines generated for the transfer.')
            for line in transfer.picking_id.move_line_ids:
                line.lot_id = copy.stock_lot_id
                line.quantity = 1
            copy.action_in_transit()
            transfer.state = 'prepared'

    def action_ship(self):
        for transfer in self:
            if transfer.state != 'prepared':
                raise ValidationError('Only prepared transfers can be shipped.')
            if not transfer.picking_id:
                raise ValidationError('Transfer has no stock picking to ship.')
            transfer.picking_id.button_validate()
            if transfer.picking_id.state != 'done':
                raise ValidationError('Stock transfer could not be validated.')
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
            dest = transfer.dest_branch_id
            picking_type = dest.warehouse_id.int_type_id
            if not picking_type:
                raise ValidationError('Destination warehouse has no internal operation type.')
            self._move_lot(
                copy.book_id.product_id, copy.stock_lot_id,
                dest.processing_location_id, dest.available_location_id,
                picking_type,
            )
            copy.write({
                'branch_id': dest.id,
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
            if transfer.state == 'prepared' and transfer.picking_id:
                transfer.picking_id.action_cancel()
            if transfer.state in ('in_transit', 'received') and transfer.picking_id:
                source = transfer.source_branch_id
                dest = transfer.dest_branch_id
                picking_type = dest.warehouse_id.int_type_id
                if picking_type:
                    self._move_lot(
                        transfer.book_copy_id.book_id.product_id,
                        transfer.book_copy_id.stock_lot_id,
                        dest.processing_location_id, source.available_location_id,
                        picking_type,
                    )
            if transfer.state in ('prepared', 'in_transit', 'received'):
                transfer.book_copy_id.action_available()
            transfer.state = 'cancelled'
