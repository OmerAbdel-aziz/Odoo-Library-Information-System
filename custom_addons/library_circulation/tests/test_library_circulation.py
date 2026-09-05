from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryCirculation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Loan = cls.env['library.loan']
        cls.LoanLine = cls.env['library.loan.line']
        cls.Fine = cls.env['library.fine']
        cls.Branch = cls.env['library.branch']
        cls.Plan = cls.env['library.membership.plan']
        cls.Member = cls.env['library.member']
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']

        cls.branch = cls.Branch.create({
            'name': 'Main Library',
            'code': 'LIB01',
        })

        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'membership_fee': 50.0,
            'maximum_books': 3,
            'loan_period_days': 7,
            'maximum_renewals': 2,
            'fine_per_day': 1.0,
            'maximum_fine': 100.0,
        })

        cls.partner = cls.env['res.partner'].create({'name': 'Test Borrower'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })

        cls.book = cls.Book.create({
            'name': 'Test Book',
            'book_type': 'book',
        })
        cls.copy1 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.branch.id,
            'barcode': 'LIB01-BK-TEST01',
            'state': 'available',
        })
        cls.copy2 = cls.Copy.create({
            'book_id': cls.book.id,
            'branch_id': cls.branch.id,
            'barcode': 'LIB01-BK-TEST02',
            'state': 'available',
        })

        cls.circ_user = new_test_user(
            cls.env,
            login='circ_user',
            groups='library_base.library_group_circulation',
        )
        cls.circ_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_loan(self, **kwargs):
        vals = {
            'member_id': self.member.id,
            'branch_id': self.branch.id,
            'loan_line_ids': [(0, 0, {
                'book_copy_id': self.copy1.id,
                'condition_on_issue': 'good',
            })],
        }
        vals.update(kwargs)
        return self.Loan.create(vals)

    def test_loan_auto_generates_name(self):
        loan = self._create_loan()
        self.assertTrue(loan.name)
        self.assertTrue(loan.name.startswith('LOAN'))

    def test_issue_loan(self):
        loan = self._create_loan()
        self.assertEqual(loan.state, 'draft')
        loan.action_issue()
        self.assertEqual(loan.state, 'issued')
        self.assertTrue(loan.issue_date)
        self.assertEqual(loan.issued_by, self.env.user)
        self.assertEqual(self.copy1.state, 'on_loan')
        self.assertEqual(self.member.current_loans_count, 1)

    def test_issue_requires_items(self):
        loan = self.Loan.create({
            'member_id': self.member.id,
            'branch_id': self.branch.id,
        })
        with self.assertRaises(ValidationError):
            loan.action_issue()

    def test_issue_rejects_inactive_member(self):
        self.member.action_suspend()
        loan = self._create_loan()
        with self.assertRaises(ValidationError):
            loan.action_issue()

    def test_issue_rejects_blocked_member(self):
        self.member.action_block()
        loan = self._create_loan()
        with self.assertRaises(ValidationError):
            loan.action_issue()

    def test_issue_rejects_unavailable_copy(self):
        self.copy1.action_on_loan()
        self.copy1.state = 'on_loan'
        self.member.current_loans_count = 1
        loan = self._create_loan()
        with self.assertRaises(ValidationError):
            loan.action_issue()

    def test_issue_rejects_over_limit(self):
        for i in range(3):
            c = self.Copy.create({
                'book_id': self.book.id,
                'branch_id': self.branch.id,
                'barcode': f'LIB01-BK-OVER{i:03d}',
                'state': 'available',
            })
            loan = self.Loan.create({
                'member_id': self.member.id,
                'branch_id': self.branch.id,
                'loan_line_ids': [(0, 0, {'book_copy_id': c.id, 'condition_on_issue': 'good'})],
            })
            loan.action_issue()
        loan4 = self._create_loan()
        with self.assertRaises(ValidationError):
            loan4.action_issue()

    def test_return_loan(self):
        loan = self._create_loan()
        loan.action_issue()
        loan.action_return()
        self.assertEqual(loan.state, 'returned')
        self.assertTrue(loan.return_date)
        self.assertEqual(loan.returned_by, self.env.user)
        self.assertEqual(self.copy1.state, 'available')
        self.assertEqual(self.member.current_loans_count, 0)

    def test_return_sets_condition(self):
        self.copy1.write({'state': 'available'})
        loan = self._create_loan()
        loan.action_issue()
        line = loan.loan_line_ids[0]
        line.condition_on_return = 'damaged'
        loan.action_return()
        self.assertEqual(self.copy1.condition, 'damaged')
        self.assertEqual(self.copy1.state, 'damaged')

    def test_renew_loan(self):
        loan = self._create_loan()
        loan.action_issue()
        line = loan.loan_line_ids[0]
        line.due_datetime = fields.Datetime.now() + relativedelta(days=2)
        old_due = line.due_datetime
        line.action_renew()
        self.assertEqual(line.renewal_count, 1)
        self.assertGreater(line.due_datetime, old_due)

    def test_renew_rejects_overdue(self):
        loan = self._create_loan()
        loan.action_issue()
        line = loan.loan_line_ids[0]
        line.due_datetime = fields.Datetime.now() - relativedelta(days=1)
        with self.assertRaises(ValidationError):
            line.action_renew()

    def test_renew_rejects_max_renewals(self):
        loan = self._create_loan()
        loan.action_issue()
        line = loan.loan_line_ids[0]
        line.action_renew()
        line.action_renew()
        with self.assertRaises(ValidationError):
            line.action_renew()

    def test_cancel_issued_loan(self):
        loan = self._create_loan()
        loan.action_issue()
        loan.action_cancel()
        self.assertEqual(loan.state, 'cancelled')
        self.assertEqual(self.copy1.state, 'available')
        self.assertEqual(self.member.current_loans_count, 0)

    def test_fine_auto_generates_name(self):
        fine = self.Fine.create({
            'member_id': self.member.id,
            'fine_type': 'late_return',
            'amount': 5.0,
        })
        self.assertTrue(fine.name)
        self.assertTrue(fine.name.startswith('FINE'))

    def test_fine_payment(self):
        fine = self.Fine.create({
            'member_id': self.member.id,
            'fine_type': 'late_return',
            'amount': 10.0,
        })
        self.assertEqual(fine.state, 'pending')
        self.assertEqual(self.member.outstanding_fines, 10.0)
        fine.paid_amount = 10.0
        fine.action_pay()
        self.assertEqual(fine.state, 'paid')
        self.assertEqual(self.member.outstanding_fines, 0.0)

    def test_fine_cancel(self):
        fine = self.Fine.create({
            'member_id': self.member.id,
            'fine_type': 'late_return',
            'amount': 10.0,
        })
        self.member.outstanding_fines = 10.0
        fine.action_cancel()
        self.assertEqual(fine.state, 'cancelled')
        self.assertEqual(self.member.outstanding_fines, 0.0)

    def test_user_can_read_loans(self):
        loan = self._create_loan()
        loans = self.Loan.with_user(self.circ_user).search([])
        self.assertIn(loan, loans)

    def test_cannot_issue_non_circulating_copy(self):
        self.copy1.circulating = False
        loan = self._create_loan()
        with self.assertRaises(ValidationError):
            loan.action_issue()
