from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryDigital(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env['library.digital.asset']
        cls.Checkout = cls.env['library.digital.checkout']
        cls.Branch = cls.env['library.branch']
        cls.Member = cls.env['library.member']
        cls.Plan = cls.env['library.membership.plan']

        cls.branch = cls.Branch.create({'name': 'Main Library', 'code': 'LIB01'})
        cls.plan = cls.Plan.create({
            'name': 'Standard',
            'duration': 365,
            'maximum_books': 5,
            'loan_period_days': 14,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Digital Reader'})
        cls.member = cls.Member.create({
            'partner_id': cls.partner.id,
            'membership_plan_id': cls.plan.id,
            'branch_id': cls.branch.id,
            'status': 'active',
        })

        cls.circ_user = new_test_user(
            cls.env,
            login='digital_user',
            groups='library_base.library_group_circulation',
        )
        cls.circ_user.allowed_branch_ids = [Command.set(cls.branch.ids)]

    def _create_asset(self, **kwargs):
        vals = {
            'title': 'Sample E-Book',
            'asset_type': 'ebook',
            'branch_id': self.branch.id,
            'license_limit': 2,
        }
        vals.update(kwargs)
        return self.Asset.create(vals)

    def _create_member(self, name):
        partner = self.env['res.partner'].create({'name': name})
        return self.Member.create({
            'partner_id': partner.id,
            'membership_plan_id': self.plan.id,
            'branch_id': self.branch.id,
            'status': 'active',
        })

    def test_asset_auto_generates_name(self):
        asset = self._create_asset()
        self.assertTrue(asset.name)
        self.assertTrue(asset.name.startswith('LIBDIG'))

    def test_negative_license_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_asset(license_limit=-1)

    def test_checkout_auto_due_date(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        self.assertEqual(checkout.state, 'active')
        self.assertEqual(checkout.due_date, fields.Date.context_today(self) + timedelta(days=14))

    def test_due_date_follows_plan(self):
        self.plan.loan_period_days = 30
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        self.assertEqual(checkout.due_date, fields.Date.context_today(self) + timedelta(days=30))

    def test_restricted_asset_plan_enforced(self):
        other_plan = self.env['library.membership.plan'].create({
            'name': 'Premium', 'duration': 365, 'maximum_books': 10, 'loan_period_days': 21,
        })
        asset = self._create_asset(access_mode='restricted')
        asset.allowed_plan_ids = [Command.set(other_plan.ids)]
        with self.assertRaises(ValidationError):
            self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        asset.allowed_plan_ids = [Command.set(self.plan.ids)]
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        self.assertEqual(checkout.state, 'active')

    def test_reactivation_blocked(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        checkout.action_return()
        with self.assertRaises(ValidationError):
            checkout.write({'state': 'active'})

    def test_member_asset_change_blocked(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        member2 = self._create_member('Reader Two')
        with self.assertRaises(ValidationError):
            checkout.write({'member_id': member2.id})

    def test_circulation_reads_asset(self):
        asset = self._create_asset()
        assets = self.Asset.with_user(self.circ_user).search([])
        self.assertIn(asset, assets)

    def test_duplicate_active_rejected(self):
        asset = self._create_asset()
        self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        with self.assertRaises(ValidationError):
            self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})

    def test_license_limit_enforced(self):
        asset = self._create_asset(license_limit=1)
        self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        member2 = self._create_member('Reader Two')
        with self.assertRaises(ValidationError):
            self.Checkout.create({'member_id': member2.id, 'asset_id': asset.id})

    def test_return_frees_license(self):
        asset = self._create_asset(license_limit=1)
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        checkout.action_return()
        self.assertEqual(checkout.state, 'returned')
        member2 = self._create_member('Reader Two')
        checkout2 = self.Checkout.create({'member_id': member2.id, 'asset_id': asset.id})
        self.assertEqual(checkout2.state, 'active')

    def test_blocked_member_rejected(self):
        asset = self._create_asset()
        self.member.action_block()
        with self.assertRaises(ValidationError):
            self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})

    def test_expired_license_rejected(self):
        asset = self._create_asset(expiry_date=fields.Date.context_today(self) - timedelta(days=1))
        with self.assertRaises(ValidationError):
            self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})

    def test_download_permission(self):
        asset = self._create_asset(download_allowed=False)
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        with self.assertRaises(ValidationError):
            checkout.action_download()
        asset.download_allowed = True
        checkout.action_download()
        self.assertEqual(checkout.download_count, 1)

    def test_download_after_return_rejected(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        checkout.action_return()
        with self.assertRaises(ValidationError):
            checkout.action_download()

    def test_cron_expires_overdue(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        checkout.due_date = fields.Date.context_today(self) - timedelta(days=1)
        self.Checkout._cron_expire_checkouts()
        self.assertEqual(checkout.state, 'expired')

    def test_user_can_read_checkouts(self):
        asset = self._create_asset()
        checkout = self.Checkout.create({'member_id': self.member.id, 'asset_id': asset.id})
        checkouts = self.Checkout.with_user(self.circ_user).search([])
        self.assertIn(checkout, checkouts)
