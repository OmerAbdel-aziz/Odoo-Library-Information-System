from odoo import fields, models


class LibraryLanguage(models.Model):
    _name = 'library.language'
    _description = 'Library Language'
    _order = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True, index=True)
    code = fields.Char(required=True, index=True, help='ISO 639-1 code')
    active = fields.Boolean(default=True)
