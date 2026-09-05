from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryNotification(models.Model):
    _name = 'library.notification'
    _description = 'Library Notification'
    _order = 'create_date desc'
    _rec_names_search = ['name', 'member_id.member_number']
    _check_company_auto = True
    _inherit = ['mail.thread']

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    member_id = fields.Many2one(
        'library.member', string='Member', required=True,
        ondelete='cascade', index=True, check_company=True,
    )
    branch_id = fields.Many2one(related='member_id.branch_id', store=True, readonly=True)
    notification_type = fields.Selection(
        [
            ('due_soon', 'Book Due Soon'),
            ('overdue', 'Book Overdue'),
            ('reservation_ready', 'Reservation Ready'),
            ('reservation_expiring', 'Reservation Expiring'),
            ('membership_expiring', 'Membership Expiring'),
            ('fine_created', 'Fine Created'),
            ('event_reminder', 'Event Reminder'),
        ],
        required=True, index=True,
    )
    subject = fields.Char(required=True)
    body = fields.Text(required=True)
    channel = fields.Selection(
        [('inbox', 'Inbox'), ('email', 'Email'), ('both', 'Both')],
        default='both', required=True,
    )
    reference = fields.Reference(
        selection=[
            ('library.loan.line', 'Loan Item'),
            ('library.reservation', 'Reservation'),
            ('library.member', 'Member'),
            ('library.fine', 'Fine'),
            ('library.event', 'Event'),
        ],
        string='Related Record',
    )
    state = fields.Selection(
        [('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')],
        default='pending', required=True, index=True,
    )
    scheduled_date = fields.Date(default=fields.Date.context_today)
    sent_date = fields.Datetime(readonly=True)
    failure_reason = fields.Text(readonly=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.notification') or '/'
        return super().create(vals_list)

    @classmethod
    def _queue(cls, env, member, notification_type, subject, body, reference=None, channel='both'):
        existing = env['library.notification'].search_count([
            ('member_id', '=', member.id),
            ('notification_type', '=', notification_type),
            ('state', '=', 'pending'),
            ('reference', '=', '%s,%s' % (reference._name, reference.id) if reference else False),
        ])
        if existing:
            return env['library.notification']
        return env['library.notification'].create({
            'member_id': member.id,
            'notification_type': notification_type,
            'subject': subject,
            'body': body,
            'reference': '%s,%s' % (reference._name, reference.id) if reference else False,
            'channel': channel,
        })

    def action_send(self):
        for notification in self:
            if notification.state != 'pending':
                raise ValidationError('Only pending notifications can be sent.')
            partner = notification.member_id.partner_id
            try:
                if notification.channel in ('inbox', 'both'):
                    notification.message_post(
                        body=notification.body,
                        partner_ids=partner.ids,
                        subject=notification.subject,
                    )
                if notification.channel in ('email', 'both') and partner.email:
                    template = self.env.ref(
                        'library_notifications.mail_template_notification', raise_if_not_found=False)
                    if template:
                        template.send_mail(notification.id, force_send=True)
                notification.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
            except Exception as e:
                notification.write({'state': 'failed', 'failure_reason': str(e)[:500]})

    @api.model
    def _cron_dispatch_pending(self):
        pending = self.search([('state', '=', 'pending')])
        pending.action_send()

    @api.model
    def _cron_generate(self):
        self._generate_loan_notifications()
        self._generate_reservation_notifications()
        self._generate_membership_notifications()
        self._generate_fine_notifications()
        self._generate_event_notifications()

    @api.model
    def _generate_loan_notifications(self):
        today = fields.Date.context_today(self)
        soon = self.env['library.loan.line'].search([
            ('state', '=', 'issued'),
            ('due_datetime', '>=', fields.Datetime.now()),
            ('due_datetime', '<', fields.Datetime.now() + timedelta(days=3)),
        ])
        for line in soon:
            due = fields.Datetime.context_timestamp(self, line.due_datetime).date()
            if (due - today).days <= 3:
                self._queue(
                    self.env, line.member_id, 'due_soon',
                    'Book due soon: %s' % line.book_copy_id.name,
                    'Please return "%s" by %s.' % (line.book_copy_id.name, line.due_datetime),
                    reference=line,
                )
        overdue = self.env['library.loan.line'].search([
            ('state', '=', 'issued'), ('is_overdue', '=', True),
        ])
        for line in overdue:
            self._queue(
                self.env, line.member_id, 'overdue',
                'Book overdue: %s' % line.book_copy_id.name,
                '"%s" is %d day(s) overdue. Fines may apply.' % (
                    line.book_copy_id.name, line.days_overdue),
                reference=line,
            )

    @api.model
    def _generate_reservation_notifications(self):
        today = fields.Date.context_today(self)
        ready = self.env['library.reservation'].search([('state', '=', 'ready_for_pickup')])
        for res in ready:
            self._queue(
                self.env, res.member_id, 'reservation_ready',
                'Reservation ready: %s' % res.book_id.name,
                '"%s" is ready for pickup at %s until %s.' % (
                    res.book_id.name, res.preferred_branch_id.name, res.expiry_date),
                reference=res,
            )
            if res.expiry_date and (res.expiry_date - today).days <= 1:
                self._queue(
                    self.env, res.member_id, 'reservation_expiring',
                    'Reservation expiring: %s' % res.book_id.name,
                    'Your hold on "%s" expires on %s.' % (res.book_id.name, res.expiry_date),
                    reference=res,
                )

    @api.model
    def _generate_membership_notifications(self):
        today = fields.Date.context_today(self)
        members = self.env['library.member'].search([
            ('status', '=', 'active'),
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', today + timedelta(days=14)),
        ])
        for member in members:
            self._queue(
                self.env, member, 'membership_expiring',
                'Membership expiring soon',
                'Your membership (%s) expires on %s. Please renew.' % (
                    member.member_number, member.expiry_date),
                reference=member,
            )

    @api.model
    def _generate_fine_notifications(self):
        fines = self.env['library.fine'].search([('state', '=', 'pending')])
        for fine in fines:
            self._queue(
                self.env, fine.member_id, 'fine_created',
                'New library fine: %s' % fine.name,
                'A fine of %s (%s) was recorded on your account.' % (
                    fine.amount, fine.fine_type),
                reference=fine,
            )

    @api.model
    def _generate_event_notifications(self):
        today = fields.Date.context_today(self)
        events = self.env['library.event'].search([
            ('state', '=', 'published'),
            ('start_datetime', '>=', fields.Datetime.now()),
            ('start_datetime', '<', fields.Datetime.now() + timedelta(days=2)),
        ])
        for event in events:
            registrations = self.env['library.event.registration'].search([
                ('event_id', '=', event.id), ('state', '=', 'registered'),
            ])
            for reg in registrations:
                self._queue(
                    self.env, reg.member_id, 'event_reminder',
                    'Upcoming event: %s' % event.title,
                    '"%s" starts on %s at %s.' % (
                        event.title, event.start_datetime, event.branch_id.name),
                    reference=event,
                )
