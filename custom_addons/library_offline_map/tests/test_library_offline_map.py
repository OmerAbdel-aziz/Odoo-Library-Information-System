import base64
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.addons.library_offline_map.controllers import main as map_controller
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryOfflineMap(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Branch = cls.env['library.branch']
        cls.Floor = cls.env['library.floor']
        cls.Section = cls.env['library.section']
        cls.Shelf = cls.env['library.shelf']
        cls.Settings = cls.env['library.map.settings']

        cls.branch = cls.Branch.create({
            'name': 'Main Library', 'code': 'LIB01',
            'latitude': 30.0444, 'longitude': 31.2357,
        })
        cls.branch2 = cls.Branch.create({
            'name': 'Alex Library', 'code': 'LIB02',
            'latitude': 31.2001, 'longitude': 29.9187,
        })
        cls.floor = cls.Floor.create({'name': 'Ground', 'branch_id': cls.branch.id})
        cls.section = cls.Section.create({'name': 'Fiction', 'floor_id': cls.floor.id})
        cls.shelf = cls.Shelf.create({
            'name': 'Shelf A', 'code': 'A', 'section_id': cls.section.id,
            'map_x': 10.0, 'map_y': 20.0, 'map_width': 15.0, 'map_height': 5.0,
        })

        cls.map_admin = new_test_user(
            cls.env,
            login='map_admin',
            groups='library_base.library_group_map_administrator',
        )
        cls.map_admin.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def test_shelf_bounds_rejected(self):
        with self.assertRaises(ValidationError):
            self.shelf.map_x = 95.0
            self.shelf.map_width = 10.0
            self.shelf.flush_recordset()

    def test_shelf_negative_rejected(self):
        with self.assertRaises(ValidationError):
            self.Shelf.create({
                'name': 'Bad', 'code': 'BAD', 'section_id': self.section.id,
                'map_x': -1.0,
            })

    def test_shelf_placed(self):
        self.assertTrue(self.shelf.map_placed)
        shelf2 = self.Shelf.create({
            'name': 'Shelf B', 'code': 'B', 'section_id': self.section.id,
            'map_width': 0.0, 'map_height': 0.0,
        })
        self.assertFalse(shelf2.map_placed)

    def test_floor_mapped_count(self):
        self.assertEqual(self.floor.shelf_count_mapped, 1)

    def test_plan_size_cap(self):
        with self.assertRaises(ValidationError):
            self.floor.plan_svg = base64.b64encode(b'x' * (3 * 1024 * 1024))

    def test_haversine_math(self):
        dist = self.Branch._haversine_km(30.0444, 31.2357, 31.2001, 29.9187)
        self.assertGreater(dist, 150)
        self.assertLess(dist, 250)

    def test_nearest_branch_order(self):
        nearest = self.Branch.nearest_branch(30.05, 31.24, limit=2)
        self.assertEqual(len(nearest), 2)
        self.assertEqual(nearest[0]['code'], 'LIB01')
        self.assertLess(nearest[0]['distance_km'], nearest[1]['distance_km'])

    def test_pin_data_shape(self):
        pin = self.branch._pin_data()
        for key in ('id', 'name', 'code', 'city', 'phone', 'latitude',
                    'longitude', 'opening_time', 'closing_time', 'manager'):
            self.assertIn(key, pin)

    def test_settings_singleton(self):
        settings = self.Settings._get_settings()
        self.assertTrue(settings)
        self.assertIn('map-server', settings.tiles_url)
        self.assertEqual(self.Settings._get_settings(), settings)

    def test_settings_admin_access(self):
        settings = self.Settings.with_user(self.map_admin).search([])
        self.assertTrue(settings)

    def test_show_on_map_action(self):
        book = self.env['library.book'].create({'name': 'Map Book', 'book_type': 'book'})
        copy = self.env['library.book.copy'].create({
            'book_id': book.id,
            'branch_id': self.branch.id,
            'barcode': 'LIB01-BK-MAP01',
            'floor_id': self.floor.id,
            'section_id': self.section.id,
            'shelf_id': self.shelf.id,
        })
        action = copy.action_show_on_map()
        self.assertEqual(action['tag'], 'library_indoor_map')
        self.assertEqual(action['params']['highlight_shelf_id'], self.shelf.id)
        self.assertEqual(action['params']['floor_id'], self.floor.id)

    def test_floor_map_action(self):
        action = self.floor.action_view_indoor_map()
        self.assertEqual(action['tag'], 'library_indoor_map')
        self.assertEqual(action['params']['floor_id'], self.floor.id)

    def _call_route(self, method, **kwargs):
        fake = MagicMock()
        fake.env = self.env
        fake.not_found.return_value = 'NOT_FOUND'
        endpoint = getattr(map_controller.LibraryMapController(), method)
        endpoint = getattr(endpoint, 'original_endpoint', endpoint)
        with patch.object(map_controller, 'request', fake):
            instance = map_controller.LibraryMapController()
            return endpoint(instance, **kwargs)

    def test_route_indoor_bad_floor(self):
        self.assertIn('error', self._call_route('indoor', floor_id='abc'))
        self.assertIn('error', self._call_route('indoor'))
        self.assertIn('error', self._call_route('indoor', floor_id=999999))

    def test_route_indoor_ok(self):
        data = self._call_route('indoor', floor_id=self.floor.id)
        self.assertEqual(data['floor']['id'], self.floor.id)
        self.assertEqual(len(data['shelves']), 1)
        self.assertEqual(data['shelves'][0]['id'], self.shelf.id)

    def test_route_nearest_validation(self):
        self.assertIn('error', self._call_route('nearest', latitude='x', longitude='y'))
        self.assertIn('error', self._call_route('nearest', latitude=1000, longitude=0))
        self.assertIn('error', self._call_route('nearest', latitude=30.0, longitude=31.0, limit='abc'))
        result = self._call_route('nearest', latitude=30.05, longitude=31.24, limit=5)
        self.assertEqual(result[0]['code'], 'LIB01')

    def test_route_floor_plan_missing(self):
        self.assertEqual(self._call_route('floor_plan', floor_id=999999), 'NOT_FOUND')

    def test_map_admin_writes_coords(self):
        self.shelf.with_user(self.map_admin).write({'map_x': 30.0})
        self.assertEqual(self.shelf.map_x, 30.0)

    def test_regular_user_denied_settings(self):
        user = new_test_user(self.env, login='plain_user', groups='library_base.library_group_user')
        with self.assertRaises(AccessError):
            self.Settings.with_user(user).search([])

    def test_svg_validation(self):
        with self.assertRaises(ValidationError):
            self.floor.plan_svg = base64.b64encode(b'not an svg at all \x00\x01')
        self.floor.plan_svg = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.assertTrue(self.floor.plan_svg)
