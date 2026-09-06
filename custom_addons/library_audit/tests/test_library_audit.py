from odoo import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryAudit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env['library.audit.rule']
        cls.Log = cls.env['library.audit.log']
        cls.Branch = cls.env['library.branch']

        cls.manager = new_test_user(
            cls.env,
            login='audit_manager',
            groups='library_base.library_group_library_manager',
        )

    def _make_rule(self, model='library.branch', **kwargs):
        model_id = self.env['ir.model'].search([('model', '=', model)], limit=1)
        vals = {'name': 'Test rule', 'model_id': model_id.id}
        vals.update(kwargs)
        return self.Rule.create(vals)

    def _make_branch(self, name='Audit Branch', code=None):
        return self.Branch.create({'name': name, 'code': code or name[:6].upper()})

    def test_create_logged(self):
        self._make_rule()
        branch = self._make_branch()
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
            ('operation', '=', 'create'),
        ])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.user_id, self.env.user)
        self.assertTrue(logs.line_ids)

    def test_write_logged_with_diff(self):
        self._make_rule()
        branch = self._make_branch()
        branch.write({'city': 'Cairo'})
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
            ('operation', '=', 'write'),
        ])
        self.assertEqual(len(logs), 1)
        line = logs.line_ids.filtered(lambda l: l.field_name == 'city')
        self.assertEqual(len(line), 1)
        self.assertFalse(line.old_value)
        self.assertEqual(line.new_value, 'Cairo')

    def test_unchanged_write_not_logged(self):
        self._make_rule()
        branch = self._make_branch()
        branch.write({'city': branch.city})
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
            ('operation', '=', 'write'),
        ])
        self.assertEqual(len(logs), 0)

    def test_unlink_logged(self):
        self._make_rule()
        branch = self._make_branch()
        branch_id = branch.id
        branch.unlink()
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch_id),
            ('operation', '=', 'unlink'),
        ])
        self.assertEqual(len(logs), 1)

    def test_untracked_model_ignored(self):
        self._make_rule(model='library.floor')
        branch = self._make_branch()
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
        ])
        self.assertEqual(len(logs), 0)

    def test_disabled_rule_ignored(self):
        rule = self._make_rule()
        rule.active = False
        branch = self._make_branch()
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
        ])
        self.assertEqual(len(logs), 0)

    def test_field_filter(self):
        city_field = self.env['ir.model.fields'].search([
            ('model', '=', 'library.branch'), ('name', '=', 'city'),
        ], limit=1)
        self._make_rule(field_ids=[Command.set(city_field.ids)])
        branch = self._make_branch()
        branch.write({'city': 'Giza', 'phone': '123'})
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
            ('operation', '=', 'write'),
        ])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.line_ids.mapped('field_name'), ['city'])

    def test_operation_flags(self):
        self._make_rule(track_create=False, track_write=False, track_unlink=False)
        branch = self._make_branch()
        logs = self.Log.search([
            ('model_id.model', '=', 'library.branch'),
            ('res_id', '=', branch.id),
        ])
        self.assertEqual(len(logs), 0)

    def test_manager_reads_logs(self):
        self._make_rule()
        branch = self._make_branch()
        logs = self.Log.with_user(self.manager).search([('res_id', '=', branch.id)])
        self.assertEqual(len(logs), 1)

    def test_no_recursion_on_log_models(self):
        self._make_rule(model='library.audit.log')
        log = self.Log.create({
            'model_id': self.env['ir.model'].search([('model', '=', 'library.branch')], limit=1).id,
            'res_id': 1,
            'operation': 'create',
        })
        logs = self.Log.search([
            ('model_id.model', '=', 'library.audit.log'),
            ('res_id', '=', log.id),
        ])
        self.assertEqual(len(logs), 0)
