from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMobileTrip(models.Model):
    _name = 'library.mobile.trip'
    _description = 'Library Mobile Trip'
    _order = 'trip_date desc, id desc'
    _rec_names_search = ['name']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    route_id = fields.Many2one(
        'library.mobile.route', string='Route', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    unit_id = fields.Many2one(related='route_id.unit_id', store=True, readonly=True)
    branch_id = fields.Many2one(
        'library.branch', string='Branch',
        ondelete='restrict', index=True, check_company=True, readonly=True,
    )
    trip_date = fields.Date(default=fields.Date.context_today, required=True)
    driver_id = fields.Many2one('res.users', string='Driver')
    line_ids = fields.One2many('library.mobile.trip.line', 'trip_id', string='Carried Copies', copy=False)
    stop_line_ids = fields.One2many('library.mobile.trip.stop', 'trip_id', string='Stop Visits', copy=False)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('prepared', 'Prepared'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft', required=True, index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.mobile.trip') or '/'
            if not vals.get('branch_id') and vals.get('route_id'):
                route = self.env['library.mobile.route'].browse(vals['route_id'])
                if route.branch_id:
                    vals['branch_id'] = route.branch_id.id
        trips = super().create(vals_list)
        for trip in trips:
            if not trip.branch_id and trip.route_id:
                trip.branch_id = trip.route_id.branch_id
        return trips

    def write(self, vals):
        if {'route_id', 'line_ids'} & set(vals) and any(t.state != 'draft' for t in self):
            raise ValidationError('Route and carried copies cannot be changed after preparation.')
        res = super().write(vals)
        if 'route_id' in vals:
            for trip in self:
                if trip.state == 'draft' and trip.route_id:
                    trip.branch_id = trip.route_id.branch_id
        return res

    def unlink(self):
        if any(t.state not in ('draft', 'cancelled', 'completed') for t in self):
            raise ValidationError('Only draft, cancelled or completed trips can be deleted.')
        return super().unlink()

    def _check_capacity(self):
        self.ensure_one()
        capacity = self.unit_id.capacity
        if capacity and len(self.line_ids) > capacity:
            raise ValidationError('Trip exceeds unit capacity (%d copies).' % capacity)

    def action_prepare(self):
        TripStop = self.env['library.mobile.trip.stop']
        for trip in self:
            if trip.state != 'draft':
                raise ValidationError('Only draft trips can be prepared.')
            if not trip.line_ids:
                raise ValidationError('Select at least one copy to carry.')
            if not trip.route_id.stop_ids:
                raise ValidationError('Route has no stops to visit.')
            trip._check_capacity()
            seen = set()
            for line in trip.line_ids:
                copy = line.book_copy_id
                if copy.id in seen:
                    raise ValidationError('Copy "%s" is listed twice on this trip.' % (copy.barcode or copy.name))
                seen.add(copy.id)
                if copy.branch_id != trip.branch_id:
                    raise ValidationError('Copy "%s" is not at the home branch.' % (copy.barcode or copy.name))
                if copy.state != 'available':
                    raise ValidationError('Copy "%s" is not available.' % (copy.barcode or copy.name))
                if self.env['library.mobile.trip.line'].search_count([
                    ('book_copy_id', '=', copy.id),
                    ('state', 'in', ('loaded', 'in_transit')),
                    ('id', '!=', line.id),
                ]):
                    raise ValidationError('Copy "%s" is already loaded on another trip.' % (copy.barcode or copy.name))
            for stop in trip.route_id.stop_ids.sorted('sequence'):
                TripStop.create({'trip_id': trip.id, 'stop_id': stop.id})
            trip.line_ids.write({'state': 'loaded'})
            trip.state = 'prepared'

    def action_start(self):
        for trip in self:
            if trip.state != 'prepared':
                raise ValidationError('Only prepared trips can start.')
            trip.line_ids.book_copy_id.action_in_transit()
            trip.line_ids.write({'state': 'in_transit'})
            trip.state = 'in_progress'

    def _release_copies(self):
        for copy in self.line_ids.book_copy_id:
            if copy.state == 'in_transit':
                copy.action_available()

    def action_complete(self):
        for trip in self:
            if trip.state != 'in_progress':
                raise ValidationError('Only trips in progress can be completed.')
            unvisited = trip.stop_line_ids.filtered(lambda s: not s.visited)
            if unvisited:
                raise ValidationError('All stops must be visited before completing.')
            trip._release_copies()
            trip.line_ids.write({'state': 'returned'})
            trip.state = 'completed'

    def action_cancel(self):
        for trip in self:
            if trip.state in ('completed', 'cancelled'):
                raise ValidationError('Completed or cancelled trips cannot be cancelled.')
            if trip.state == 'in_progress':
                trip._release_copies()
            trip.line_ids.write({'state': 'cancelled'})
            trip.state = 'cancelled'
