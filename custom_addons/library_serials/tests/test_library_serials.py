from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibrarySerials(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Subscription = cls.env['library.subscription']
        cls.Issue = cls.env['library.serial.issue']
        cls.Branch = cls.env['library.branch']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.supplier = cls.env['res.partner'].create({'name': 'Magazine Co'})

        cls.librarian = new_test_user(
            cls.env,
            login='serials_user',
            groups='library_base.library_group_librarian',
        )
        cls.librarian.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_subscription(self, **kwargs):
        vals = {
            'title': 'Science Weekly',
            'supplier_id': self.supplier.id,
            'branch_id': self.branch.id,
            'frequency': 'monthly',
            'cost': 120.0,
        }
        vals.update(kwargs)
        return self.Subscription.create(vals)

    def test_subscription_auto_generates_name(self):
        sub = self._create_subscription()
        self.assertTrue(sub.name)
        self.assertTrue(sub.name.startswith('LIBSUB'))

    def test_end_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_subscription(start_date='2026-06-01', end_date='2026-01-01')

    def test_generate_issues(self):
        sub = self._create_subscription(start_date='2026-01-01')
        sub.action_generate_issues(count=3)
        self.assertEqual(sub.issue_count, 3)
        labels = sorted(sub.issue_ids.mapped('label'))
        self.assertEqual(labels, ['2026-01', '2026-02', '2026-03'])

    def test_generate_issues_idempotent(self):
        sub = self._create_subscription(start_date='2026-01-01')
        sub.action_generate_issues(count=3)
        sub.action_generate_issues(count=3)
        self.assertEqual(sub.issue_count, 3)

    def test_generate_respects_end_date(self):
        sub = self._create_subscription(start_date='2026-01-01', end_date='2026-02-15')
        sub.action_generate_issues(count=6)
        self.assertEqual(sub.issue_count, 2)

    def test_issue_flow(self):
        sub = self._create_subscription(start_date='2026-01-01')
        sub.action_generate_issues(count=1)
        issue = sub.issue_ids[0]
        self.assertEqual(issue.state, 'expected')
        issue.action_mark_missing()
        self.assertEqual(issue.state, 'missing')
        issue.action_claim()
        self.assertEqual(issue.state, 'claimed')
        issue.action_receive()
        self.assertEqual(issue.state, 'received')
        self.assertTrue(issue.received_date)

    def test_receive_direct(self):
        sub = self._create_subscription(start_date='2026-01-01')
        sub.action_generate_issues(count=1)
        issue = sub.issue_ids[0]
        issue.action_receive()
        self.assertEqual(issue.state, 'received')

    def test_invalid_transitions_rejected(self):
        sub = self._create_subscription(start_date='2026-01-01')
        sub.action_generate_issues(count=1)
        issue = sub.issue_ids[0]
        with self.assertRaises(ValidationError):
            issue.action_claim()
        issue.action_mark_missing()
        with self.assertRaises(ValidationError):
            issue.action_mark_missing()
        issue.action_claim()
        with self.assertRaises(ValidationError):
            issue.action_mark_missing()
        issue.action_receive()
        with self.assertRaises(ValidationError):
            issue.action_receive()

    def test_expected_next_issue_advances(self):
        sub = self._create_subscription(start_date='2026-01-01')
        first_expected = sub.expected_next_issue
        self.assertTrue(first_expected)
        sub.action_generate_issues(count=1)
        sub.issue_ids[0].action_receive()
        self.assertGreater(sub.expected_next_issue, first_expected)

    def test_user_can_read_subscriptions(self):
        sub = self._create_subscription()
        subs = self.Subscription.with_user(self.librarian).search([])
        self.assertIn(sub, subs)
