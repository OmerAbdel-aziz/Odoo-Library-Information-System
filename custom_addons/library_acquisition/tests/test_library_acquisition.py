from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryAcquisition(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env['library.purchase.request']
        cls.Branch = cls.env['library.branch']
        cls.Member = cls.env['library.member']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.floor = cls.env['library.floor'].create({'name': 'Ground', 'branch_id': cls.branch.id})
        cls.section = cls.env['library.section'].create({
            'name': 'Fiction', 'floor_id': cls.floor.id,
        })
        cls.shelf = cls.env['library.shelf'].create({
            'name': 'Shelf A', 'code': 'A', 'section_id': cls.section.id,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Test Member'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })
        cls.vendor = cls.env['res.partner'].create({'name': 'Book Supplier', 'is_company': True})

        cls.acq_user = new_test_user(
            cls.env,
            login='acq_user',
            groups='library_base.library_group_acquisition',
        )
        cls.acq_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_request(self, **kwargs):
        vals = {
            'book_name': 'New Acquisition',
            'member_id': self.member.id,
            'branch_id': self.branch.id,
            'shelf_id': self.shelf.id,
            'vendor_id': self.vendor.id,
            'quantity': 2,
            'estimated_cost': 25.0,
        }
        vals.update(kwargs)
        return self.Request.create(vals)

    def _validate_receipt(self, request):
        picking = request.purchase_order_id.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming'
        )
        picking.action_assign()
        lot = self.env['stock.lot'].create({
            'name': 'TEST-LOT-001',
            'product_id': request.product_id.id,
            'company_id': request.company_id.id,
        })
        for line in picking.move_line_ids:
            line.quantity = line.quantity_product_uom
            line.lot_id = lot
        picking.button_validate()
        return picking

    def test_request_auto_generates_name(self):
        request = self._create_request()
        self.assertTrue(request.name)
        self.assertTrue(request.name.startswith('LIBPR'))

    def test_quantity_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self._create_request(quantity=0)

    def test_submit_approve(self):
        request = self._create_request()
        request.action_submit()
        self.assertEqual(request.state, 'submitted')
        request.action_approve()
        self.assertEqual(request.state, 'approved')
        self.assertEqual(request.approved_by, self.env.user)

    def test_approve_requires_submit(self):
        request = self._create_request()
        with self.assertRaises(ValidationError):
            request.action_approve()

    def test_create_po_requires_vendor(self):
        request = self._create_request(vendor_id=False)
        request.action_submit()
        request.action_approve()
        with self.assertRaises(ValidationError):
            request.action_create_po()

    def test_create_po(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        request.action_create_po()
        self.assertEqual(request.state, 'ordered')
        self.assertTrue(request.purchase_order_id)
        self.assertEqual(request.purchase_order_id.state, 'purchase')

    def test_receive_requires_confirmed_po(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        with self.assertRaises(ValidationError):
            request.action_receive()

    def test_full_flow_catalogs_copies(self):
        request = self._create_request(author='Test Author', isbn='9780132350884')
        request.action_submit()
        request.action_approve()
        request.action_create_po()
        self._validate_receipt(request)
        request.action_receive()
        self.assertEqual(request.state, 'received')
        request.action_catalog()
        self.assertEqual(request.state, 'done')
        self.assertTrue(request.book_id)
        self.assertEqual(request.book_id.name, 'New Acquisition')
        self.assertEqual(request.book_id.author_ids.name, 'Test Author')
        self.assertEqual(request.book_id.isbn_13, '9780132350884')
        self.assertEqual(request.book_id.product_id, request.product_id)
        copies = self.Copy.search([('book_id', '=', request.book_id.id)])
        self.assertEqual(len(copies), 2)
        for copy in copies:
            self.assertTrue(copy.barcode)
            self.assertEqual(copy.branch_id, self.branch)
            self.assertEqual(copy.shelf_id, self.shelf)
            self.assertEqual(copy.state, 'available')
            self.assertTrue(copy.stock_lot_id)
            self.assertEqual(copy.acquisition_cost, 12.5)

    def test_catalog_twice_rejected(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        request.action_create_po()
        self._validate_receipt(request)
        request.action_receive()
        request.action_catalog()
        with self.assertRaises(ValidationError):
            request.action_catalog()

    def test_shelf_branch_mismatch_rejected(self):
        other_branch = self.Branch.create({'name': 'Other Library', 'code': 'LIB02'})
        other_floor = self.env['library.floor'].create({'name': 'First', 'branch_id': other_branch.id})
        other_section = self.env['library.section'].create({'name': 'Kids', 'floor_id': other_floor.id})
        other_shelf = self.env['library.shelf'].create({'name': 'Shelf B', 'code': 'B', 'section_id': other_section.id})
        with self.assertRaises(ValidationError):
            self._create_request(shelf_id=other_shelf.id)

    def test_locked_after_ordered(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        request.action_create_po()
        with self.assertRaises(ValidationError):
            request.quantity = 10

    def test_cancel_ordered_rejected(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        request.action_create_po()
        with self.assertRaises(ValidationError):
            request.action_cancel()

    def test_user_can_read_requests(self):
        request = self._create_request()
        requests = self.Request.with_user(self.acq_user).search([])
        self.assertIn(request, requests)
