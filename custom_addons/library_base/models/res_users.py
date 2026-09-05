from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_branch_ids = fields.Many2many(
        'library.branch',
        'library_branch_res_users_rel',
        'user_id',
        'branch_id',
        string='Allowed Library Branches',
        help='Library branches this user can access. Library managers and administrators can access all branches in their allowed companies.',
    )
