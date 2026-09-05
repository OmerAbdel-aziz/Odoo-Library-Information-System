from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryEventRegistration(models.Model):
    _name = 'library.event.registration'
    _description = 'Library Event Registration'
    _order = 'create_date, id'
    _rec_names_search = ['name', 'member_id.member_number']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    event_id = fields.Many2one(
        'library.event', string='Event', required=True,
        ondelete='cascade', index=True, check_company=True,
    )
    member_id = fields.Many2one(
        'library.member', string='Member', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    branch_id = fields.Many2one(related='event_id.branch_id', store=True, readonly=True)
    registration_date = fields.Date(default=fields.Date.context_today, required=True)
    attended = fields.Boolean(default=False)
    state = fields.Selection(
        [
            ('registered', 'Registered'),
            ('attended', 'Attended'),
            ('cancelled', 'Cancelled'),
        ],
        default='registered', required=True, index=True,
    )
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.event.registration') or '/'
        registrations = super().create(vals_list)
        for registration in registrations:
            registration._check_eligible()
        return registrations

    def write(self, vals):
        if 'state' in vals and not self.env.context.get('event_action'):
            raise ValidationError('Use the workflow buttons to change registration status.')
        locked = {'event_id', 'member_id'}
        if locked & set(vals) and any(r.state != 'registered' for r in self):
            raise ValidationError('Only pending registrations can be reassigned.')
        return super().write(vals)

    def _check_eligible(self):
        self.ensure_one()
        event = self.event_id
        if event.state not in ('published', 'ongoing'):
            raise ValidationError('Registrations are only allowed for published events.')
        member = self.member_id
        if member.status != 'active':
            raise ValidationError('Only active members can register for events.')
        if member.blocked:
            raise ValidationError('This member is blocked and cannot register for events.')
        if self.search_count([
            ('event_id', '=', event.id),
            ('member_id', '=', member.id),
            ('state', 'in', ('registered', 'attended')),
            ('id', '!=', self.id),
        ]):
            raise ValidationError('This member is already registered for "%s".' % event.title)
        if event.capacity and event.registration_count > event.capacity:
            raise ValidationError('Event "%s" is fully booked.' % event.title)

    def action_attend(self):
        for registration in self:
            if registration.state != 'registered':
                raise ValidationError('Only pending registrations can be marked attended.')
            registration.with_context(event_action=True).write({'state': 'attended', 'attended': True})

    def action_cancel(self):
        for registration in self:
            if registration.state == 'cancelled':
                continue
            if registration.state == 'attended':
                raise ValidationError('Attended registrations cannot be cancelled.')
            registration.with_context(event_action=True).write({'state': 'cancelled'})
