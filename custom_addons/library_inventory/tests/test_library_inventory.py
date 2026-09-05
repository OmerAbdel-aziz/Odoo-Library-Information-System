from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryInventory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Transfer = cls.env['library.transfer']
        cls.Branch = cls.env['library.branch']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']

        cls.source = cls.Branch.create({'name': 'Source Library', 'code': 'LIB01'})
        cls.dest = cls.Branch.create({'name': 'Dest Library', 'code': 'LIB02'})
        cls.source.warehouse_id = cls.env['stock.warehouse'].create({
            'name': 'Source WH', 'code': 'SRC',
        })
        cls.dest.warehouse_id = cls.env['stock.warehouse'].create({
            'name': 'Dest WH', 'code': 'DST',
        })

        cls.book = cls.Book.create({'name': 'Transfer Book', 'book_type': 'book'})
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.source.id,
            'barcode': 'LIB01-BK-TRF01',
        })

        cls.inv_user = new_test_user(
            cls.env,
            login='inv_user',
            groups='library_base.library_group_inventory',
        )
        cls.inv_user.allowed_branch_ids = [Command.set((cls.source + cls.dest).ids)]

    def _create_transfer(self, **kwargs):
        vals = {
            'book_copy_id': self.copy1.id,
            'source_branch_id': self.source.id,
            'dest_branch_id': self.dest.id,
        }
        vals.update(kwargs)
        return self.Transfer.create(vals)

    def test_transfer_auto_generates_name(self):
        transfer = self._create_transfer()
        self.assertTrue(transfer.name)
        self.assertTrue(transfer.name.startswith('LIBTRF'))

    def test_same_branch_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_transfer(dest_branch_id=self.source.id)

    def test_setup_locations(self):
        self.source.action_setup_stock_locations()
        for field in ('processing_location_id', 'available_location_id',
                      'hold_shelf_location_id', 'repair_location_id', 'withdrawn_location_id'):
            self.assertTrue(self.source[field], field)

    def test_setup_requires_warehouse(self):
        branch = self.Branch.create({'name': 'No Warehouse', 'code': 'LIB99'})
        with self.assertRaises(ValidationError):
            branch.action_setup_stock_locations()

    def test_ensure_product(self):
        self.assertFalse(self.book.product_id)
        self.book.action_ensure_product()
        self.assertTrue(self.book.product_id)
        self.assertEqual(self.book.product_id.tracking, 'lot')

    def test_ensure_lot(self):
        self.assertFalse(self.copy1.stock_lot_id)
        self.copy1.action_ensure_lot()
        self.assertTrue(self.copy1.stock_lot_id)
        self.assertEqual(self.copy1.stock_lot_id.product_id, self.book.product_id)

    def test_approve_requires_available_copy(self):
        self.copy1.action_on_loan()
        transfer = self._create_transfer()
        with self.assertRaises(ValidationError):
            transfer.action_approve()

    def test_full_workflow(self):
        transfer = self._create_transfer()
        transfer.action_approve()
        self.assertEqual(transfer.state, 'approved')
        transfer.action_prepare()
        self.assertEqual(transfer.state, 'prepared')
        self.assertTrue(transfer.picking_id)
        self.assertEqual(self.copy1.state, 'in_transit')
        transfer.action_ship()
        self.assertEqual(transfer.state, 'in_transit')
        transfer.action_receive()
        self.assertEqual(transfer.state, 'received')
        transfer.action_complete()
        self.assertEqual(transfer.state, 'completed')
        self.assertEqual(self.copy1.branch_id, self.dest)
        self.assertEqual(self.copy1.state, 'available')
        self.assertFalse(self.copy1.shelf_id)

    def test_cancel_prepared_releases_copy(self):
        transfer = self._create_transfer()
        transfer.action_approve()
        transfer.action_prepare()
        self.assertEqual(self.copy1.state, 'in_transit')
        transfer.action_cancel()
        self.assertEqual(transfer.state, 'cancelled')
        self.assertEqual(self.copy1.state, 'available')

    def test_cancel_completed_rejected(self):
        transfer = self._create_transfer()
        transfer.action_approve()
        transfer.action_prepare()
        transfer.action_ship()
        transfer.action_receive()
        transfer.action_complete()
        with self.assertRaises(ValidationError):
            transfer.action_cancel()

    def test_user_can_read_transfers(self):
        transfer = self._create_transfer()
        transfers = self.Transfer.with_user(self.inv_user).search([])
        self.assertIn(transfer, transfers)
