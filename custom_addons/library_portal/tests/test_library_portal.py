from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('at_install', '-post_install')
class TestLibraryPortal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Portal Member'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal_member',
            'partner_id': cls.partner.id,
            'group_ids': [Command.set([cls.env.ref('base.group_portal').id])],
        })
        cls.other_partner = cls.env['res.partner'].create({'name': 'Other Member'})
        cls.other_member = cls.Member.create({
            'partner_id': cls.other_partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })
        cls.book = cls.Book.create({'name': 'Portal Book', 'book_type': 'book'})
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.branch.id,
            'barcode': 'LIB01-BK-PRT01',
        })

    def test_get_portal_member(self):
        member = self.Member._get_portal_member(self.portal_user)
        self.assertEqual(member, self.member)

    def test_no_member_for_stranger(self):
        stranger = self.env['res.users'].create({
            'name': 'Stranger',
            'login': 'portal_stranger',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })
        self.assertFalse(self.Member._get_portal_member(stranger))

    def test_portal_sees_own_member_only(self):
        members = self.Member.with_user(self.portal_user).search([])
        self.assertEqual(members, self.member)

    def test_portal_reads_catalog(self):
        books = self.Book.with_user(self.portal_user).search([])
        self.assertIn(self.book, books)
        copies = self.Copy.with_user(self.portal_user).search([])
        self.assertIn(self.copy1, copies)

    def test_portal_search(self):
        books = self.Book._portal_search(query='Portal')
        self.assertIn(self.book, books)
        books = self.Book._portal_search(query='Nonexistent XYZ')
        self.assertNotIn(self.book, books)

    def test_portal_availability(self):
        availability = self.book._portal_availability()
        entry = list(availability.values())[0]
        self.assertEqual(entry['total'], 1)
        self.assertEqual(entry['available'], 1)
        self.assertEqual(entry['on_loan'], 0)

    def test_portal_dashboard(self):
        data = self.member._portal_dashboard()
        self.assertEqual(data['member'], self.member)
        self.assertEqual(len(data['active_loans']), 0)
        self.assertEqual(data['fines_total'], 0)

    def test_portal_loan_isolation(self):
        loan = self.Loan.create({
            'member_id': self.other_member.id,
            'branch_id': self.branch.id,
            'loan_line_ids': [(0, 0, {'book_copy_id': self.copy1.id})],
        })
        loan.action_issue()
        lines = self.env['library.loan.line'].with_user(self.portal_user).search([])
        self.assertNotIn(loan.loan_line_ids[0], lines)
        fines = self.env['library.fine'].with_user(self.portal_user).search([])
        self.assertEqual(len(fines), 0)

    def test_portal_can_reserve(self):
        reservation = self.env['library.reservation'].with_user(self.portal_user).create({
            'member_id': self.member.id,
            'book_id': self.book.id,
            'preferred_branch_id': self.branch.id,
        })
        self.assertEqual(reservation.state, 'waiting')

    def test_blocked_member_no_portal_access(self):
        self.member.action_block()
        self.assertFalse(self.Member._get_portal_member(self.portal_user))
        self.assertTrue(self.Member._get_any_member(self.portal_user))

    def test_portal_event_visibility(self):
        event = self.env['library.event'].create({
            'title': 'Draft Event',
            'event_type': 'workshop',
            'branch_id': self.branch.id,
            'start_datetime': '2026-10-01 10:00:00',
            'end_datetime': '2026-10-01 12:00:00',
        })
        events = self.env['library.event'].with_user(self.portal_user).search([])
        self.assertNotIn(event, events)
        event.action_publish()
        events = self.env['library.event'].with_user(self.portal_user).search([])
        self.assertIn(event, events)

    def test_portal_purchase_request(self):
        request = self.env['library.purchase.request'].with_user(self.portal_user).create({
            'member_id': self.member.id,
            'book_name': 'Portal Requested Book',
            'branch_id': self.branch.id,
            'quantity': 1,
        })
        self.assertEqual(request.state, 'draft')
        other = self.env['library.purchase.request'].search([('member_id', '=', self.other_member.id)])
        own = self.env['library.purchase.request'].with_user(self.portal_user).search([])
        self.assertIn(request, own)
        for rec in other:
            self.assertNotIn(rec, own)

    def test_portal_search_pagination(self):
        books = self.Book._portal_search(query='Portal', limit=1, offset=0)
        self.assertLessEqual(len(books), 1)
        count = self.Book._portal_search_count(query='Portal')
        self.assertGreaterEqual(count, 1)

    def test_portal_can_renew(self):
        loan = self.Loan.create({
            'member_id': self.member.id,
            'branch_id': self.branch.id,
            'loan_line_ids': [(0, 0, {'book_copy_id': self.copy1.id})],
        })
        loan.action_issue()
        line = loan.loan_line_ids[0].with_user(self.portal_user)
        line.action_renew()
        self.assertEqual(line.renewal_count, 1)
