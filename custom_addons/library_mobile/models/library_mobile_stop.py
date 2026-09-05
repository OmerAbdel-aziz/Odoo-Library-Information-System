from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMobileStop(models.Model):
    _name = 'library.mobile.stop'
    _description = 'Library Mobile Stop'
    _order = 'route_id, sequence, id'
    _rec_names_search = ['name']
    _check_company_auto = True

    name = fields.Char(required=True)
    route_id = fields.Many2one(
        'library.mobile.route', string='Route', required=True,
        ondelete='cascade', index=True, check_company=True,
    )
    sequence = fields.Integer(default=10)
    address = fields.Char()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    partner_id = fields.Many2one('res.partner', string='Partner (e.g. School)', ondelete='set null')
    company_id = fields.Many2one(related='route_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for stop in self:
            if stop.latitude != 0.0 and not -90 <= stop.latitude <= 90:
                raise ValidationError('Latitude must be between -90 and 90.')
            if stop.longitude != 0.0 and not -180 <= stop.longitude <= 180:
                raise ValidationError('Longitude must be between -180 and 180.')
