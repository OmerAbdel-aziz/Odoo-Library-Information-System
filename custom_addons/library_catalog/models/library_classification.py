from odoo import fields, models


class LibraryClassificationSystem(models.Model):
    _name = 'library.classification.system'
    _description = 'Library Classification System'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(index=True)
    description = fields.Text(translate=True)
    code_ids = fields.One2many('library.classification.code', 'system_id', string='Classification Codes')


class LibraryClassificationCode(models.Model):
    _name = 'library.classification.code'
    _description = 'Library Classification Code'
    _order = 'code'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(required=True, index=True)
    system_id = fields.Many2one('library.classification.system', required=True, ondelete='restrict', index=True)
    parent_id = fields.Many2one('library.classification.code', string='Parent', index=True, ondelete='restrict')
    child_ids = fields.One2many('library.classification.code', 'parent_id', string='Subcodes')
    description = fields.Text(translate=True)
