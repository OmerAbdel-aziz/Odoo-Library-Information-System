from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')
class TestLibraryMembership(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Plan = cls.env['library.membership.plan']
        cls.Member = cls.env['library.member']
        cls.Branch = cls.env['library.branch']

        cls.branch = cls.Branch.create({
            'name': 'Main Library',
            'code': 'LIB01',
        })

        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'membership_fee': 50.0,
            'maximum_books': 5,
            'loan_period_days': 14,
            'maximum_renewals': 2,
            'reservation_limit': 3,
            'fine_per_day': 1.0,
            'maximum_fine': 100.0,
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Member',
            'email': 'test@example.com',
        })

        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'member_type': 'adult',
        })

        cls.library_user = new_test_user(
            cls.env,
            login='membership_user',
            groups='library_base.library_group_user',
        )
        cls.library_user.allowed_branch_ids = [Command.set(cls.branch.ids)]
        cls.library_manager = new_test_user(
            cls.env,
            login='membership_manager',
            groups='library_base.library_group_library_manager',
        )

    def test_member_auto_generates_number(self):
        self.assertTrue(self.member.member_number)
        self.assertTrue(self.member.member_number.startswith('MEM'))

    def test_member_auto_generates_barcode(self):
        self.assertTrue(self.member.barcode)
        self.assertTrue(self.member.barcode.startswith('LM'))

    def test_expiry_date_computed(self):
        expected = self.member.registration_date + relativedelta(days=self.plan.duration)
        self.assertEqual(self.member.expiry_date, expected)

    def test_max_books_computed_from_plan(self):
        self.assertEqual(self.member.max_books, 5)

    def test_status_transitions(self):
        self.assertEqual(self.member.status, 'draft')
        self.member.action_activate()
        self.assertEqual(self.member.status, 'active')
        self.member.action_suspend()
        self.assertEqual(self.member.status, 'suspended')
        self.member.action_activate()
        self.assertEqual(self.member.status, 'active')
        self.member.action_block()
        self.assertEqual(self.member.status, 'blocked')
        self.assertEqual(self.member.blocked, True)
        self.member.action_activate()
        self.assertEqual(self.member.status, 'active')
        self.assertEqual(self.member.blocked, False)

    def test_cancel_and_set_draft(self):
        self.member.action_activate()
        self.member.action_cancel()
        self.assertEqual(self.member.status, 'cancelled')
        self.assertFalse(self.member.active)
        self.member.action_set_draft()
        self.assertEqual(self.member.status, 'draft')
        self.assertTrue(self.member.active)

    def test_member_initial_status_is_draft(self):
        member = self.Member.create({
            'partner_id': self.env['res.partner'].create({'name': 'New'}).id,
            'branch_id': self.branch.id,
        })
        self.assertEqual(member.status, 'draft')

    def test_block_sets_status(self):
        self.member.action_activate()
        self.member.action_block()
        self.assertEqual(self.member.status, 'blocked')
        self.assertTrue(self.member.blocked)

    def test_user_can_read_members(self):
        members = self.Member.with_user(self.library_user).search([])
        self.assertIn(self.member, members)

    def test_manager_sees_all_members(self):
        members = self.Member.with_user(self.library_manager).search([])
        self.assertIn(self.member, members)

    def test_blocked_status_requires_blocked_flag(self):
        with self.assertRaises(ValidationError):
            self.member.write({'status': 'blocked', 'blocked': False})

    def test_blocked_flag_requires_blocked_status(self):
        self.member.action_activate()
        with self.assertRaises(ValidationError):
            self.member.write({'blocked': True, 'status': 'active'})

    def test_member_auto_generates_qr_code(self):
        self.assertTrue(self.member.qr_code)
        self.assertTrue(self.member.qr_code.startswith('LIBMEM:'))
