from odoo import api, fields, models


class LibraryAuditRule(models.Model):
    _name = 'library.audit.rule'
    _description = 'Library Audit Rule'
    _order = 'model_id'

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade',
        domain="[('model', '=like', 'library.%')]",
    )
    field_ids = fields.Many2many(
        'ir.model.fields', string='Tracked Fields',
        domain="[('model_id', '=', model_id)]",
        help='Empty means all stored fields except binaries and relations.',
    )
    track_create = fields.Boolean(default=True)
    track_write = fields.Boolean(default=True)
    track_unlink = fields.Boolean(default=True)
    active = fields.Boolean(default=True)

    _WRAPPED_MODELS = ('library.audit.log', 'library.audit.log.line', 'library.audit.rule')

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            rules = self.sudo().search([('active', '=', True)])
        except Exception:
            return
        for rule in rules:
            if rule.model_id.model not in self._WRAPPED_MODELS:
                self._ensure_wrapped(rule.model_id.model)

    @api.model
    def _ensure_wrapped(self, model_name):
        model = self.env.get(model_name)
        if model is None:
            return
        cls = type(model)
        if getattr(cls, '__audit_wrapped__', False):
            return
        for operation in ('create', 'write', 'unlink'):
            original = getattr(cls, operation, None)
            if original is None:
                continue
            setattr(cls, operation, self._make_wrapper(operation, original))
        cls.__audit_wrapped__ = True

    @api.model
    def _make_wrapper(self, operation, original):
        def _wrapper_create(self, vals_list):
            records = original(self, vals_list)
            try:
                self.env['library.audit.log']._log_records(records, 'create')
            except Exception:
                pass
            return records

        def _wrapper_write(self, vals):
            old_values = {}
            if self:
                try:
                    old_values = self.env['library.audit.log']._snapshot(self, vals)
                except Exception:
                    old_values = {}
            result = original(self, vals)
            if self:
                try:
                    self.env['library.audit.log']._log_write(self, vals, old_values)
                except Exception:
                    pass
            return result

        def _wrapper_unlink(self):
            try:
                self.env['library.audit.log']._log_unlink(self)
            except Exception:
                pass
            return original(self)

        return {'create': _wrapper_create, 'write': _wrapper_write, 'unlink': _wrapper_unlink}[operation]

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        for rule in rules:
            if rule.active and rule.model_id.model not in self._WRAPPED_MODELS:
                self._ensure_wrapped(rule.model_id.model)
        return rules

    def write(self, vals):
        res = super().write(vals)
        for rule in self:
            if rule.active and rule.model_id.model not in self._WRAPPED_MODELS:
                self._ensure_wrapped(rule.model_id.model)
        return res
