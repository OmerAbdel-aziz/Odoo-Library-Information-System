from odoo import fields, models


class LibraryWeekday(models.Model):
    _name = 'library.weekday'
    _description = 'Library Working Day'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        [
            ('mon', 'Monday'),
            ('tue', 'Tuesday'),
            ('wed', 'Wednesday'),
            ('thu', 'Thursday'),
            ('fri', 'Friday'),
            ('sat', 'Saturday'),
            ('sun', 'Sunday'),
        ],
        required=True,
    )
    sequence = fields.Integer(default=10)

    _code_unique = models.Constraint('UNIQUE(code)', 'The working day code must be unique.')
