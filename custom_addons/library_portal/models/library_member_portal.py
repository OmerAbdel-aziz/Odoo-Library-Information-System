from odoo import api, fields, models


class LibraryMemberPortal(models.Model):
    _inherit = 'library.member'

    @api.model
    def _get_portal_member(self, user):
        return self.search([
            ('partner_id', '=', user.partner_id.id),
            ('active', '=', True),
        ], limit=1)

    def _portal_dashboard(self):
        self.ensure_one()
        LoanLine = self.env['library.loan.line']
        Fine = self.env['library.fine']
        Reservation = self.env['library.reservation']
        active_lines = LoanLine.search([('member_id', '=', self.id), ('state', '=', 'issued')])
        overdue_lines = LoanLine.search([('member_id', '=', self.id), ('is_overdue', '=', True)])
        open_fines = Fine.search([('member_id', '=', self.id), ('state', '=', 'pending')])
        open_reservations = Reservation.search([
            ('member_id', '=', self.id),
            ('state', 'in', ('waiting', 'allocated', 'ready_for_pickup')),
        ])
        return {
            'member': self,
            'active_loans': active_lines,
            'overdue_loans': overdue_lines,
            'open_fines': open_fines,
            'fines_total': sum(open_fines.mapped('remaining_amount')),
            'reservations': open_reservations,
        }
