from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryFine(models.Model):
    _name = 'library.fine'
    _description = 'Library Fine'
    _order = 'create_date desc'
    _rec_names_search = ['name', 'member_id.member_number', 'member_id.partner_id.name']
    _check_company_auto = True

    name = fields.Char(required=True, readonly=True, copy=False, index=True)
    member_id = fields.Many2one(
        'library.member',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    loan_line_id = fields.Many2one(
        'library.loan.line',
        ondelete='set null',
        index=True,
        check_company=True,
    )
    loan_id = fields.Many2one(related='loan_line_id.loan_id', store=True, readonly=True)
    branch_id = fields.Many2one(related='member_id.branch_id', store=True, readonly=True)
    fine_type = fields.Selection(
        [
            ('late_return', 'Late Return'),
            ('lost_book', 'Lost Book'),
            ('damaged_book', 'Damaged Book'),
            ('membership', 'Membership'),
            ('other', 'Other'),
        ],
        required=True,
        index=True,
    )
    amount = fields.Float(digits=(10, 2), required=True)
    paid_amount = fields.Float(digits=(10, 2), default=0.0)
    remaining_amount = fields.Float(compute='_compute_remaining_amount', store=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    due_date = fields.Date()
    payment_date = fields.Date()
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.depends('amount', 'paid_amount')
    def _compute_remaining_amount(self):
        for fine in self:
            fine.remaining_amount = max(0, fine.amount - fine.paid_amount)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.fine')
        fines = super().create(vals_list)
        for fine in fines:
            if fine.state == 'draft':
                fine.state = 'pending'
                fine.member_id.outstanding_fines += fine.amount
        return fines

    def action_pay(self):
        for fine in self:
            if fine.state not in ('pending', 'draft'):
                raise ValidationError('Only pending fines can be marked as paid.')
            if fine.paid_amount < fine.amount:
                raise ValidationError('Full payment required to mark as paid.')
            fine.payment_date = fields.Date.context_today(self)
            fine.state = 'paid'
            fine.member_id.outstanding_fines = max(0, fine.member_id.outstanding_fines - fine.amount)

    def action_cancel(self):
        for fine in self:
            if fine.state == 'cancelled':
                continue
            if fine.state == 'paid':
                raise ValidationError('Cannot cancel a paid fine.')
            fine.state = 'cancelled'
            if fine.remaining_amount > 0:
                fine.member_id.outstanding_fines = max(0, fine.member_id.outstanding_fines - fine.remaining_amount)

    def action_set_draft(self):
        for fine in self:
            if fine.state == 'cancelled':
                fine.state = 'draft'
