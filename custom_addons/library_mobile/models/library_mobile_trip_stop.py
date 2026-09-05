from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMobileTripStop(models.Model):
    _name = 'library.mobile.trip.stop'
    _description = 'Library Mobile Trip Stop Visit'
    _order = 'trip_id, sequence, id'
    _rec_names_search = ['stop_id.name']
    _check_company_auto = True

    trip_id = fields.Many2one('library.mobile.trip', required=True, ondelete='cascade', index=True)
    stop_id = fields.Many2one(
        'library.mobile.stop', string='Stop', required=True,
        ondelete='restrict', index=True, check_company=True,
    )
    sequence = fields.Integer(related='stop_id.sequence', store=True, readonly=True)
    visited = fields.Boolean(default=False, readonly=True)
    visited_at = fields.Datetime(string='Visited At', readonly=True)
    company_id = fields.Many2one(related='trip_id.company_id', store=True, readonly=True)

    def action_visit(self):
        for line in self:
            if line.trip_id.state != 'in_progress':
                raise ValidationError('Stops can only be visited during an ongoing trip.')
            if line.visited:
                raise ValidationError('Stop already visited.')
            line.visited = True
            line.visited_at = fields.Datetime.now()
