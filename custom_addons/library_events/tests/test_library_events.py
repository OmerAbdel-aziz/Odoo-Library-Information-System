from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryEvents(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Event = cls.env['library.event']
        cls.Registration = cls.env['library.event.registration']
        cls.Branch = cls.env['library.branch']
        cls.Member = cls.env['library.member']
        cls.Plan = cls.env['library.membership.plan']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'maximum_books': 5,
            'loan_period_days': 14,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Event Goer'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })

        cls.circ_user = new_test_user(
            cls.env,
            login='events_user',
            groups='library_base.library_group_circulation',
        )
        cls.circ_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_event(self, **kwargs):
        start = fields.Datetime.now() + timedelta(days=7)
        vals = {
            'title': 'Summer Reading Club',
            'event_type': 'book_club',
            'branch_id': self.branch.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=2),
            'capacity': 2,
        }
        vals.update(kwargs)
        return self.Event.create(vals)

    def _create_member(self, name):
        partner = self.env['res.partner'].create({'name': name})
        return self.Member.create({
            'partner_id': partner.id,
            'membership_plan_id': self.plan.id,
            'branch_id': self.branch.id,
            'status': 'active',
        })

    def test_event_auto_generates_name(self):
        event = self._create_event()
        self.assertTrue(event.name)
        self.assertTrue(event.name.startswith('LIBEVT'))

    def test_end_before_start_rejected(self):
        start = fields.Datetime.now() + timedelta(days=7)
        with self.assertRaises(ValidationError):
            self._create_event(start_datetime=start, end_datetime=start - timedelta(hours=1))

    def test_negative_capacity_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_event(capacity=-1)

    def test_publish_start_finish(self):
        event = self._create_event()
        event.action_publish()
        self.assertEqual(event.state, 'published')
        event.action_start()
        self.assertEqual(event.state, 'ongoing')
        event.action_finish()
        self.assertEqual(event.state, 'done')

    def test_register_requires_published(self):
        event = self._create_event()
        with self.assertRaises(ValidationError):
            self.Registration.create({'event_id': event.id, 'member_id': self.member.id})

    def test_register_and_attend(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        self.assertEqual(reg.state, 'registered')
        self.assertEqual(event.registration_count, 1)
        self.assertEqual(event.seats_left, 1)
        reg.action_attend()
        self.assertEqual(reg.state, 'attended')
        self.assertTrue(reg.attended)

    def test_duplicate_registration_rejected(self):
        event = self._create_event()
        event.action_publish()
        self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        with self.assertRaises(ValidationError):
            self.Registration.create({'event_id': event.id, 'member_id': self.member.id})

    def test_capacity_enforced(self):
        event = self._create_event()
        event.action_publish()
        self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        member2 = self._create_member('Goer Two')
        self.Registration.create({'event_id': event.id, 'member_id': member2.id})
        member3 = self._create_member('Goer Three')
        with self.assertRaises(ValidationError):
            self.Registration.create({'event_id': event.id, 'member_id': member3.id})

    def test_blocked_member_rejected(self):
        event = self._create_event()
        event.action_publish()
        self.member.action_block()
        with self.assertRaises(ValidationError):
            self.Registration.create({'event_id': event.id, 'member_id': self.member.id})

    def test_direct_state_write_rejected(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        with self.assertRaises(ValidationError):
            reg.write({'state': 'attended'})

    def test_cancel_event_cancels_registrations(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        event.action_cancel()
        self.assertEqual(event.state, 'cancelled')
        self.assertEqual(reg.state, 'cancelled')

    def test_create_state_forced_registered(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({
            'event_id': event.id, 'member_id': self.member.id, 'state': 'attended',
        })
        self.assertEqual(reg.state, 'registered')
        self.assertFalse(reg.attended)

    def test_reassignment_rechecked(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        draft = self._create_event()
        with self.assertRaises(ValidationError):
            reg.write({'event_id': draft.id})

    def test_event_delete_restricted(self):
        from odoo.exceptions import UserError
        event = self._create_event()
        event.action_publish()
        self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        with self.assertRaises(Exception):
            event.unlink()

    def test_circulation_reads_event(self):
        event = self._create_event()
        events = self.Event.with_user(self.circ_user).search([])
        self.assertIn(event, events)

    def test_user_can_read_registrations(self):
        event = self._create_event()
        event.action_publish()
        reg = self.Registration.create({'event_id': event.id, 'member_id': self.member.id})
        regs = self.Registration.with_user(self.circ_user).search([])
        self.assertIn(reg, regs)
