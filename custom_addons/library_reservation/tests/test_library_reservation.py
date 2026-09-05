from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryReservation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Reservation = cls.env['library.reservation']
        cls.Branch = cls.env['library.branch']
        cls.Member = cls.env['library.member']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']
        cls.Plan = cls.env['library.membership.plan']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'maximum_books': 5,
            'loan_period_days': 14,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Test Reserver'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })

        cls.book = cls.Book.create({'name': 'Reserved Book', 'book_type': 'book'})
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.branch.id,
            'barcode': 'LIB01-BK-RES01',
            'state': 'on_loan',
        })

        cls.circ_user = new_test_user(
            cls.env,
            login='resv_user',
            groups='library_base.library_group_circulation',
        )
        cls.circ_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_reservation(self, **kwargs):
        vals = {
            'member_id': self.member.id,
            'book_id': self.book.id,
            'preferred_branch_id': self.branch.id,
        }
        vals.update(kwargs)
        return self.Reservation.create(vals)

    def test_reservation_auto_generates_name(self):
        res = self._create_reservation()
        self.assertTrue(res.name)
        self.assertTrue(res.name.startswith('RESV'))

    def test_reservation_starts_waiting(self):
        res = self._create_reservation()
        self.assertEqual(res.state, 'waiting')

    def test_queue_position(self):
        partner2 = self.env['res.partner'].create({'name': 'Reserver 2'})
        member2 = self.Member.create({
            'partner_id': partner2.id,
            'branch_id': self.branch.id,
            'status': 'active',
        })
        r1 = self._create_reservation()
        r2 = self._create_reservation(member_id=member2.id)
        self.assertEqual(r1.queue_position, 1)
        self.assertEqual(r2.queue_position, 2)

    def test_allocate_no_available_copy(self):
        self.copy1.state = 'on_loan'
        res = self._create_reservation()
        with self.assertRaises(ValidationError):
            res.action_allocate()

    def test_allocate_available_copy(self):
        self.copy1.state = 'available'
        res = self._create_reservation()
        res.action_allocate()
        self.assertEqual(res.state, 'allocated')
        self.assertEqual(res.copy_id, self.copy1)
        self.assertEqual(self.copy1.state, 'reserved')
        self.assertTrue(res.ready_date)
        self.assertTrue(res.expiry_date)

    def test_ready_for_pickup(self):
        self.copy1.state = 'available'
        res = self._create_reservation()
        res.action_allocate()
        res.action_ready_for_pickup()
        self.assertEqual(res.state, 'ready_for_pickup')

    def test_collect(self):
        self.copy1.state = 'available'
        res = self._create_reservation()
        res.action_allocate()
        res.action_collect()
        self.assertEqual(res.state, 'collected')
        self.assertEqual(self.copy1.state, 'available')

    def test_cancel_waiting(self):
        res = self._create_reservation()
        res.action_cancel()
        self.assertEqual(res.state, 'cancelled')

    def test_cancel_allocated_releases_copy(self):
        self.copy1.state = 'available'
        res = self._create_reservation()
        res.action_allocate()
        self.assertEqual(self.copy1.state, 'reserved')
        res.action_cancel()
        self.assertEqual(res.state, 'cancelled')
        self.assertEqual(self.copy1.state, 'available')

    def test_user_can_read_reservations(self):
        res = self._create_reservation()
        reservations = self.Reservation.with_user(self.circ_user).search([])
        self.assertIn(res, reservations)
