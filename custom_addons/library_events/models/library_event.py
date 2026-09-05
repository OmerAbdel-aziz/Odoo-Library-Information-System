from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryEvent(models.Model):
    _name = 'library.event'
    _description = 'Library Event'
    _order = 'start_datetime, id'
    _rec_name = 'title'
    _rec_names_search = ['name', 'title']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    title = fields.Char(required=True)
    event_type = fields.Selection(
        [
            ('book_club', 'Book Club'),
            ('workshop', 'Workshop'),
            ('story_session', 'Children Story Session'),
            ('training', 'Training'),
            ('author_meeting', 'Author Meeting'),
            ('competition', 'Reading Competition'),
        ],
        default='workshop', required=True, index=True,
    )
    branch_id = fields.Many2one(
        'library.branch', string='Branch', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    start_datetime = fields.Datetime(string='Starts At', required=True)
    end_datetime = fields.Datetime(string='Ends At', required=True)
    capacity = fields.Integer(default=0, help='Maximum registrations. 0 means unlimited.')
    description = fields.Text()
    registration_ids = fields.One2many('library.event.registration', 'event_id', string='Registrations')
    registration_count = fields.Integer(compute='_compute_registration_count', store=True)
    seats_left = fields.Integer(compute='_compute_registration_count', store=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('ongoing', 'Ongoing'),
            ('done', 'Done'),
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
                vals['name'] = self.env['ir.sequence'].next_by_code('library.event') or '/'
        return super().create(vals_list)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for event in self:
            if event.start_datetime and event.end_datetime and event.end_datetime <= event.start_datetime:
                raise ValidationError('Event end must be after its start.')

    @api.constrains('capacity')
    def _check_capacity(self):
        for event in self:
            if event.capacity < 0:
                raise ValidationError('Event capacity cannot be negative.')

    @api.depends('registration_ids', 'registration_ids.state', 'capacity')
    def _compute_registration_count(self):
        for event in self:
            confirmed = len(event.registration_ids.filtered(lambda r: r.state in ('registered', 'attended')))
            event.registration_count = confirmed
            event.seats_left = event.capacity - confirmed if event.capacity else False

    def action_publish(self):
        for event in self:
            if event.state != 'draft':
                raise ValidationError('Only draft events can be published.')
            event.state = 'published'

    def action_start(self):
        for event in self:
            if event.state != 'published':
                raise ValidationError('Only published events can start.')
            event.state = 'ongoing'

    def action_finish(self):
        for event in self:
            if event.state != 'ongoing':
                raise ValidationError('Only ongoing events can finish.')
            event.state = 'done'

    def action_cancel(self):
        for event in self:
            if event.state in ('done', 'cancelled'):
                raise ValidationError('Finished or cancelled events cannot be cancelled.')
            event.registration_ids.filtered(
                lambda r: r.state == 'registered'
            ).with_context(event_action=True).write({'state': 'cancelled'})
            event.state = 'cancelled'

    def action_view_registrations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrations',
            'res_model': 'library.event.registration',
            'view_mode': 'list,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id},
        }
