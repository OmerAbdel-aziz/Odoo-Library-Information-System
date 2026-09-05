from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryReservation(models.Model):
    _name = 'library.reservation'
    _description = 'Library Reservation'
    _order = 'request_date, priority desc, id'
    _rec_names_search = ['name', 'member_id.member_number', 'member_id.partner_id.name', 'book_id.name']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    member_id = fields.Many2one(
        'library.member',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    book_id = fields.Many2one(
        'library.book',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    preferred_branch_id = fields.Many2one(
        'library.branch',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    copy_id = fields.Many2one(
        'library.book.copy',
        ondelete='set null',
        index=True,
        check_company=True,
    )
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    priority = fields.Integer(default=0, index=True)
    queue_position = fields.Integer(readonly=True)
    ready_date = fields.Date()
    expiry_date = fields.Date()
    hold_days = fields.Integer(default=3, help='Number of days to hold a reserved copy')
    state = fields.Selection(
        [
            ('waiting', 'Waiting'),
            ('allocated', 'Allocated'),
            ('ready_for_pickup', 'Ready for Pickup'),
            ('collected', 'Collected'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        default='waiting',
        required=True,
        index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(related='preferred_branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.reservation')
        reservations = super().create(vals_list)
        reservations._update_queue_positions()
        return reservations

    def _update_queue_positions(self):
        for book in self.mapped('book_id'):
            waiting = self.search([
                ('book_id', '=', book.id),
                ('state', '=', 'waiting'),
            ], order='request_date, priority desc, id')
            for i, res in enumerate(waiting, 1):
                res.queue_position = i

    def _compute_is_ready(self):
        now = fields.Date.context_today(self)
        for res in self:
            res.is_ready = (
                res.state == 'ready_for_pickup'
                and res.expiry_date
                and res.expiry_date >= now
            )

    is_ready = fields.Boolean(compute='_compute_is_ready')

    def action_allocate(self):
        for res in self:
            if res.state != 'waiting':
                raise ValidationError('Only waiting reservations can be allocated.')
            book = res.book_id
            available_copy = self.env['library.book.copy'].search([
                ('book_id', '=', book.id),
                ('branch_id', '=', res.preferred_branch_id.id),
                ('state', '=', 'available'),
                ('circulating', '=', True),
            ], limit=1)
            if not available_copy:
                raise ValidationError('No available copy of "%s" at %s.' % (book.name, res.preferred_branch_id.name))
            res.copy_id = available_copy
            available_copy.action_reserved()
            res.ready_date = fields.Date.context_today(self)
            res.expiry_date = fields.Date.context_today(self) + relativedelta(days=res.hold_days)
            res.state = 'allocated'
            res._notify_ready()

    def action_ready_for_pickup(self):
        for res in self:
            if res.state != 'allocated':
                raise ValidationError('Only allocated reservations can be marked ready.')
            res.state = 'ready_for_pickup'

    def action_collect(self):
        for res in self:
            if res.state not in ('allocated', 'ready_for_pickup'):
                raise ValidationError('Only allocated/ready reservations can be collected.')
            if res.copy_id:
                res.copy_id.action_available()
            res.state = 'collected'
            res._update_queue_positions()

    def action_cancel(self):
        for res in self:
            if res.state == 'cancelled':
                continue
            if res.state in ('allocated', 'ready_for_pickup') and res.copy_id:
                res.copy_id.action_available()
            res.state = 'cancelled'
            res._update_queue_positions()

    def action_expire(self):
        expired = self.search([
            ('state', 'in', ('allocated', 'ready_for_pickup')),
            ('expiry_date', '<', fields.Date.context_today(self)),
        ])
        for res in expired:
            if res.copy_id:
                res.copy_id.action_available()
            res.state = 'expired'
            res._update_queue_positions()

    def _notify_ready(self):
        self.ensure_one()
        # Placeholder: pickup notification will be wired in library_notifications (Phase 13).
