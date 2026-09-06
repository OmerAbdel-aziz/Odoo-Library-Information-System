from odoo import api, fields, models


class LibraryAuditLog(models.Model):
    _name = 'library.audit.log'
    _description = 'Library Audit Log'
    _order = 'timestamp desc, id desc'

    model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade', readonly=True,
    )
    res_id = fields.Integer(string='Record ID', readonly=True)
    res_name = fields.Char(string='Record', readonly=True)
    operation = fields.Selection(
        [('create', 'Create'), ('write', 'Write'), ('unlink', 'Delete')],
        required=True, readonly=True, index=True,
    )
    user_id = fields.Many2one(
        'res.users', string='User', required=True, readonly=True,
        default=lambda self: self.env.user,
    )
    timestamp = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    line_ids = fields.One2many('library.audit.log.line', 'log_id', string='Changes', readonly=True)

    @api.model
    def _active_rules(self, model_name):
        return self.env['library.audit.rule'].sudo().search([
            ('model_id.model', '=', model_name),
            ('active', '=', True),
        ])

    @api.model
    def _tracked_fields(self, rules, record):
        names = set()
        for rule in rules:
            if rule.field_ids:
                names.update(rule.field_ids.mapped('name'))
            else:
                names.update(
                    fname for fname, field in record._fields.items()
                    if field.store and field.type not in ('binary', 'one2many', 'many2many')
                )
        return [fname for fname in names if fname in record._fields]

    @api.model
    def _format_value(self, record, fname):
        field = record._fields[fname]
        value = record[fname]
        if not value and field.type != 'boolean':
            return False
        if field.type == 'many2one':
            return '%s' % value.display_name
        if field.type == 'selection' and field.selection:
            return dict(field.selection).get(value, value) or False
        if field.type in ('one2many', 'many2many'):
            return '%d record(s)' % len(value)
        if field.type == 'binary':
            return '[binary data]'
        if field.type == 'datetime':
            return fields.Datetime.to_string(value) if value else False
        if field.type == 'date':
            return fields.Date.to_string(value) if value else False
        text = '%s' % value
        return text[:500]

    @api.model
    def _snapshot(self, records, vals):
        tracked = self._tracked_fields(self._active_rules(records._name), records)
        snapshot = {}
        for record in records:
            snapshot[record.id] = {
                fname: self._format_value(record, fname)
                for fname in tracked if fname in vals
            }
        return snapshot

    @api.model
    def _log_records(self, records, operation):
        if not records or records._name in ('library.audit.log', 'library.audit.log.line', 'library.audit.rule'):
            return
        rules = self._active_rules(records._name)
        if not rules:
            return
        if operation == 'create' and not any(r.track_create for r in rules):
            return
        for record in records:
            tracked = self._tracked_fields(rules, record)
            changes = {}
            for fname in tracked:
                new = self._format_value(record, fname)
                if new not in (False, '', '0'):
                    changes[fname] = (False, new)
            self._create_log(record, operation, changes)

    @api.model
    def _log_write(self, records, vals, old_values):
        if records._name in ('library.audit.log', 'library.audit.log.line', 'library.audit.rule'):
            return
        rules = self._active_rules(records._name)
        if not rules or not any(r.track_write for r in rules):
            return
        for record in records:
            old = old_values.get(record.id, {})
            changes = {}
            for fname in old:
                new = self._format_value(record, fname)
                if new != old[fname]:
                    changes[fname] = (old[fname], new)
            if changes:
                self._create_log(record, 'write', changes)

    @api.model
    def _log_unlink(self, records):
        if not records:
            return
        if records._name in ('library.audit.log', 'library.audit.log.line', 'library.audit.rule'):
            return
        rules = self._active_rules(records._name)
        if not rules or not any(r.track_unlink for r in rules):
            return
        for record in records:
            self._create_log(record, 'unlink', {})

    @api.model
    def _create_log(self, record, operation, changes):
        model = self.env['ir.model'].sudo().search([('model', '=', record._name)], limit=1)
        log = self.sudo().create({
            'model_id': model.id,
            'res_id': record.id,
            'res_name': (record.display_name or '')[:200],
            'operation': operation,
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
        })
        lines = []
        for fname, (old, new) in changes.items():
            field = record._fields[fname]
            lines.append({
                'log_id': log.id,
                'field_name': fname,
                'field_label': field.string,
                'old_value': old,
                'new_value': new,
            })
        if lines:
            self.sudo().env['library.audit.log.line'].create(lines)
        return log


class LibraryAuditLogLine(models.Model):
    _name = 'library.audit.log.line'
    _description = 'Library Audit Log Line'
    _order = 'id'

    log_id = fields.Many2one('library.audit.log', ondelete='cascade', readonly=True)
    field_name = fields.Char(readonly=True)
    field_label = fields.Char(string='Field', readonly=True)
    old_value = fields.Text(string='Old Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)
