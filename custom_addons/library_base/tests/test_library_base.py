from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')
class TestLibraryBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Branch = cls.env['library.branch']
        cls.Floor = cls.env['library.floor']
        cls.Section = cls.env['library.section']
        cls.Shelf = cls.env['library.shelf']
        cls.library_user = new_test_user(
            cls.env,
            login='library_base_user',
            groups='library_base.library_group_librarian',
        )
        cls.branch_manager = new_test_user(
            cls.env,
            login='library_base_branch_manager',
            groups='library_base.library_group_branch_manager',
        )
        cls.library_manager = new_test_user(
            cls.env,
            login='library_base_library_manager',
            groups='library_base.library_group_library_manager',
        )
        cls.branch_a = cls.Branch.create({
            'name': 'Main Library',
            'code': 'lib01',
            'city': 'Cairo',
            'manager_id': cls.branch_manager.id,
            'opening_time': 8.0,
            'closing_time': 18.0,
        })
        cls.branch_b = cls.Branch.create({
            'name': 'Nasr City Library',
            'code': 'ncr',
            'city': 'Cairo',
            'opening_time': 9.0,
            'closing_time': 17.0,
        })
        cls.floor_a = cls.Floor.create({
            'name': 'Ground Floor',
            'code': 'gf',
            'branch_id': cls.branch_a.id,
        })
        cls.section_a = cls.Section.create({
            'name': 'Computer Science',
            'code': 'cs',
            'floor_id': cls.floor_a.id,
        })
        cls.shelf_a = cls.Shelf.create({
            'name': 'Shelf CS-04',
            'code': 'cs-04',
            'section_id': cls.section_a.id,
        })
        cls.library_user.allowed_branch_ids = [Command.set(cls.branch_a.ids)]
        cls.branch_manager.allowed_branch_ids = [Command.set(cls.branch_a.ids)]

    def test_location_hierarchy_and_code_normalization(self):
        self.assertEqual(self.branch_a.code, 'LIB01')
        self.assertEqual(self.floor_a.code, 'GF')
        self.assertEqual(self.section_a.code, 'CS')
        self.assertEqual(self.shelf_a.code, 'CS-04')
        self.assertEqual(self.section_a.branch_id, self.branch_a)
        self.assertEqual(self.shelf_a.floor_id, self.floor_a)
        self.assertEqual(self.shelf_a.branch_id, self.branch_a)
        self.assertEqual(self.branch_a.floor_count, 1)
        self.assertEqual(self.branch_a.section_count, 1)
        self.assertEqual(self.branch_a.shelf_count, 1)

    def test_branch_constraints(self):
        with self.assertRaises(ValidationError):
            self.Branch.create({
                'name': 'Bad Latitude',
                'code': 'badlat',
                'latitude': 120,
            })
        with self.assertRaises(ValidationError):
            self.Branch.create({
                'name': 'Bad Hours',
                'code': 'badhours',
                'opening_time': 18.0,
                'closing_time': 9.0,
            })

    def test_user_sees_only_assigned_branches(self):
        branches = self.Branch.with_user(self.library_user).search([])
        self.assertIn(self.branch_a, branches)
        self.assertNotIn(self.branch_b, branches)

        shelves = self.Shelf.with_user(self.library_user).search([])
        self.assertIn(self.shelf_a, shelves)

    def test_library_manager_sees_all_branches(self):
        branches = self.Branch.with_user(self.library_manager).search([])
        self.assertIn(self.branch_a, branches)
        self.assertIn(self.branch_b, branches)

    def test_branch_manager_can_create_location_only_in_allowed_branch(self):
        floor = self.Floor.with_user(self.branch_manager).create({
            'name': 'First Floor',
            'code': '1f',
            'branch_id': self.branch_a.id,
        })
        self.assertEqual(floor.branch_id, self.branch_a)

        with mute_logger('odoo.addons.base.models.ir_rule'):
            with self.assertRaises(AccessError):
                self.Floor.with_user(self.branch_manager).create({
                    'name': 'Restricted Floor',
                    'code': 'rf',
                    'branch_id': self.branch_b.id,
                })

    def test_library_user_cannot_modify_branch(self):
        with mute_logger('odoo.addons.base.models.ir_model'):
            with self.assertRaises(AccessError):
                self.branch_a.with_user(self.library_user).write({'name': 'Changed'})
