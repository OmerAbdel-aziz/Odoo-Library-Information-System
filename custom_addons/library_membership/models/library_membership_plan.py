from odoo import fields, models


class LibraryMembershipPlan(models.Model):
    _name = 'library.membership.plan'
    _description = 'Library Membership Plan'
    _order = 'name'
    _rec_names_search = ['name']

    name = fields.Char(required=True, translate=True, index=True)
    duration = fields.Integer(required=True, default=365, help='Duration in days')
    membership_fee = fields.Float(digits=(10, 2))
    maximum_books = fields.Integer(required=True, default=5)
    loan_period_days = fields.Integer(required=True, default=14)
    maximum_renewals = fields.Integer(required=True, default=2)
    reservation_limit = fields.Integer(required=True, default=3)
    fine_per_day = fields.Float(digits=(10, 2), default=1.0)
    maximum_fine = fields.Float(digits=(10, 2), default=100.0)
    grace_period_days = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    member_ids = fields.One2many('library.member', 'membership_plan_id', string='Members')
    member_count = fields.Integer(compute='_compute_member_count')

    def _compute_member_count(self):
        for plan in self:
            plan.member_count = len(plan.member_ids)

    def action_view_members(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Members',
            'res_model': 'library.member',
            'view_mode': 'list,form',
            'domain': [('membership_plan_id', '=', self.id)],
        }
