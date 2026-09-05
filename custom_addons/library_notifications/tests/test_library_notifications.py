from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryNotifications(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Notification = cls.env['library.notification']
        cls.Branch = cls.env['library.branch']
        cls.Member = cls.env['library.member']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']
        cls.Plan = cls.env['library.membership.plan']
        cls.Loan = cls.env['library.loan']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'maximum_books': 5,
            'loan_period_days': 14,
            'fine_per_day': 1.0,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Notify Me', 'email': 'notify@example.com'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })
        cls.book = cls.Book.create({'name': 'Notify Book', 'book_type': 'book'})
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.branch.id,
            'barcode': 'LIB01-BK-NTF01',
        })

        cls.librarian = new_test_user(
            cls.env,
            login='notif_user',
            groups='library_base.library_group_librarian',
        )
        cls.librarian.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _make_loan(self):
        loan = self.Loan.create({
            'member_id': self.member.id,
            'branch_id': self.branch.id,
            'loan_line_ids': [(0, 0, {'book_copy_id': self.copy1.id})],
        })
        loan.action_issue()
        return loan

    def test_name_auto_generated(self):
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'Test',
            'body': 'Body',
        })
        self.assertTrue(notif.name.startswith('LIBNOTIF'))

    def test_send_inbox(self):
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'Overdue',
            'body': 'Return the book.',
            'channel': 'inbox',
        })
        notif.action_send()
        self.assertEqual(notif.state, 'sent')
        self.assertTrue(notif.sent_date)

    def test_due_soon_generated(self):
        loan = self._make_loan()
        line = loan.loan_line_ids[0]
        line.with_context(loan_line_action=True).write({
            'due_datetime': fields.Datetime.now() + timedelta(days=1),
        })
        self.Notification._generate_loan_notifications()
        pending = self.Notification.search([
            ('member_id', '=', self.member.id),
            ('notification_type', '=', 'due_soon'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_overdue_generated(self):
        loan = self._make_loan()
        line = loan.loan_line_ids[0]
        line.with_context(loan_line_action=True).write({
            'due_datetime': fields.Datetime.now() - timedelta(days=2),
        })
        self.Notification._generate_loan_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'overdue'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_no_duplicate_pending(self):
        loan = self._make_loan()
        line = loan.loan_line_ids[0]
        line.with_context(loan_line_action=True).write({
            'due_datetime': fields.Datetime.now() - timedelta(days=2),
        })
        self.Notification._generate_loan_notifications()
        self.Notification._generate_loan_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'overdue'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_reservation_ready_generated(self):
        book2 = self.Book.create({'name': 'Reserved 2', 'book_type': 'book'})
        copy2 = self.Copy.create({
            'book_id': book2.id, 'branch_id': self.branch.id, 'barcode': 'LIB01-BK-NTF02',
        })
        res = self.env['library.reservation'].create({
            'member_id': self.member.id,
            'book_id': book2.id,
            'preferred_branch_id': self.branch.id,
        })
        res.action_allocate()
        res.action_ready_for_pickup()
        self.Notification._generate_reservation_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'reservation_ready'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_membership_expiring_generated(self):
        self.member.registration_date = fields.Date.context_today(self) - timedelta(days=355)
        self.Notification._generate_membership_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'membership_expiring'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_fine_created_generated(self):
        fine = self.env['library.fine'].create({
            'member_id': self.member.id,
            'fine_type': 'late_return',
            'amount': 5.0,
        })
        self.assertEqual(fine.state, 'pending')
        self.Notification._generate_fine_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'fine_created'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_event_reminder_generated(self):
        event = self.env['library.event'].create({
            'title': 'Story Time',
            'event_type': 'story_session',
            'branch_id': self.branch.id,
            'start_datetime': fields.Datetime.now() + timedelta(days=1),
            'end_datetime': fields.Datetime.now() + timedelta(days=1, hours=2),
        })
        event.action_publish()
        self.env['library.event.registration'].create({
            'event_id': event.id, 'member_id': self.member.id,
        })
        self.Notification._generate_event_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'event_reminder'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_dispatch_cron(self):
        self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
            'channel': 'inbox',
        })
        self.Notification._cron_dispatch_pending()
        sent = self.Notification.search([('state', '=', 'sent')])
        self.assertEqual(len(sent), 1)

    def test_no_repeat_after_send(self):
        loan = self._make_loan()
        line = loan.loan_line_ids[0]
        line.with_context(loan_line_action=True).write({
            'due_datetime': fields.Datetime.now() - timedelta(days=2),
        })
        self.Notification._generate_loan_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'overdue'),
            ('state', '=', 'pending'),
        ])
        pending.action_send()
        self.Notification._generate_loan_notifications()
        self.assertEqual(self.Notification.search_count([
            ('notification_type', '=', 'overdue'),
        ]), 1)

    def test_email_without_address_fails(self):
        self.partner.email = False
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
            'channel': 'email',
        })
        notif.action_send()
        self.assertEqual(notif.state, 'failed')
        self.assertIn('email', notif.failure_reason.lower())

    def test_resend_blocked(self):
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
            'channel': 'inbox',
        })
        notif.action_send()
        self.assertEqual(notif.state, 'sent')
        notif.action_send()
        self.assertEqual(notif.state, 'failed')
        self.assertIn('pending', notif.failure_reason.lower())

    def test_future_scheduled_not_dispatched(self):
        self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
            'channel': 'inbox',
            'scheduled_date': fields.Date.context_today(self) + timedelta(days=5),
        })
        self.Notification._cron_dispatch_pending()
        self.assertEqual(self.Notification.search_count([('state', '=', 'sent')]), 0)

    def test_request_available_generated(self):
        purchase_request = self.env['library.purchase.request'].create({
            'member_id': self.member.id,
            'book_name': 'Requested Title',
            'branch_id': self.branch.id,
            'quantity': 1,
            'state': 'done',
        })
        self.Notification._generate_request_notifications()
        pending = self.Notification.search([
            ('notification_type', '=', 'request_available'),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(pending), 1)

    def test_circulation_can_read(self):
        circ = self.env['res.users'].create({
            'name': 'Circ', 'login': 'notif_circ',
            'group_ids': [Command.set([self.env.ref('library_base.library_group_circulation').id])],
        })
        circ.allowed_branch_ids = [Command.set(self.branch.ids)]
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
        })
        notifs = self.Notification.with_user(circ).search([])
        self.assertIn(notif, notifs)

    def test_user_can_read_notifications(self):
        notif = self.Notification.create({
            'member_id': self.member.id,
            'notification_type': 'overdue',
            'subject': 'X',
            'body': 'Y',
        })
        notifs = self.Notification.with_user(self.librarian).search([])
        self.assertIn(notif, notifs)
