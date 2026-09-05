from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryMobile(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Unit = cls.env['library.mobile.unit']
        cls.Route = cls.env['library.mobile.route']
        cls.Stop = cls.env['library.mobile.stop']
        cls.Trip = cls.env['library.mobile.trip']
        cls.Branch = cls.env['library.branch']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.unit = cls.Unit.create({
            'title': 'Mobile Library #1',
            'home_branch_id': cls.branch.id,
            'capacity': 2,
        })
        cls.route = cls.Route.create({
            'title': 'Saturday Route',
            'unit_id': cls.unit.id,
            'stop_ids': [(0, 0, {'name': 'School A', 'sequence': 10}),
                         (0, 0, {'name': 'School B', 'sequence': 20})],
        })
        cls.book = cls.Book.create({'name': 'Trip Book', 'book_type': 'book'})
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id, 'branch_id': cls.branch.id, 'barcode': 'LIB01-BK-TRP01',
        })
        cls.copy2 = cls.Copy.create({
            'book_id': cls.book.id, 'branch_id': cls.branch.id, 'barcode': 'LIB01-BK-TRP02',
        })

        cls.circ_user = new_test_user(
            cls.env,
            login='mobile_user',
            groups='library_base.library_group_circulation',
        )
        cls.circ_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_trip(self, copies=None, **kwargs):
        vals = {'route_id': self.route.id}
        vals.update(kwargs)
        trip = self.Trip.create(vals)
        for copy in (copies if copies is not None else [self.copy1]):
            self.env['library.mobile.trip.line'].create({
                'trip_id': trip.id, 'book_copy_id': copy.id,
            })
        return trip

    def test_names_auto_generate(self):
        self.assertTrue(self.unit.name.startswith('MOBUNIT'))
        self.assertTrue(self.route.name.startswith('MOBRTE'))
        trip = self._create_trip()
        self.assertTrue(trip.name.startswith('MOBTRP'))

    def test_negative_capacity_rejected(self):
        with self.assertRaises(ValidationError):
            self.Unit.create({'title': 'Bad', 'home_branch_id': self.branch.id, 'capacity': -1})

    def test_prepare_requires_copies(self):
        trip = self.Trip.create({'route_id': self.route.id})
        with self.assertRaises(ValidationError):
            trip.action_prepare()

    def test_prepare_capacity_enforced(self):
        copy3 = self.Copy.create({
            'book_id': self.book.id, 'branch_id': self.branch.id, 'barcode': 'LIB01-BK-TRP03',
        })
        trip = self._create_trip(copies=[self.copy1, self.copy2, copy3])
        with self.assertRaises(ValidationError):
            trip.action_prepare()

    def test_full_trip_flow(self):
        trip = self._create_trip(copies=[self.copy1, self.copy2])
        trip.action_prepare()
        self.assertEqual(trip.state, 'prepared')
        self.assertEqual(len(trip.stop_line_ids), 2)
        trip.action_start()
        self.assertEqual(trip.state, 'in_progress')
        self.assertEqual(self.copy1.state, 'in_transit')
        with self.assertRaises(ValidationError):
            trip.action_complete()
        for stop_line in trip.stop_line_ids:
            stop_line.action_visit()
        trip.action_complete()
        self.assertEqual(trip.state, 'completed')
        self.assertEqual(self.copy1.state, 'available')
        self.assertEqual(self.copy1.branch_id, self.branch)

    def test_visit_before_start_rejected(self):
        trip = self._create_trip()
        trip.action_prepare()
        with self.assertRaises(ValidationError):
            trip.stop_line_ids[0].action_visit()

    def test_duplicate_load_rejected(self):
        trip = self._create_trip()
        trip.action_prepare()
        trip2 = self._create_trip()
        with self.assertRaises(ValidationError):
            trip2.action_prepare()

    def test_cancel_in_progress_releases_copies(self):
        trip = self._create_trip()
        trip.action_prepare()
        trip.action_start()
        trip.action_cancel()
        self.assertEqual(trip.state, 'cancelled')
        self.assertEqual(self.copy1.state, 'available')

    def test_cancel_completed_rejected(self):
        trip = self._create_trip()
        trip.action_prepare()
        trip.action_start()
        for stop_line in trip.stop_line_ids:
            stop_line.action_visit()
        trip.action_complete()
        with self.assertRaises(ValidationError):
            trip.action_cancel()

    def test_bad_coordinates_rejected(self):
        with self.assertRaises(ValidationError):
            self.Stop.create({'name': 'Bad', 'route_id': self.route.id, 'latitude': 100.0})

    def test_user_can_read_trips(self):
        trip = self._create_trip()
        trips = self.Trip.with_user(self.circ_user).search([])
        self.assertIn(trip, trips)
