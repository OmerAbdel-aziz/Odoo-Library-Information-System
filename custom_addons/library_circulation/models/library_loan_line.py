from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryLoanLine(models.Model):
    _name = 'library.loan.line'
    _description = 'Library Loan Line'
    _order = 'loan_id, id'
    _rec_names_search = ['book_copy_id.barcode', 'book_copy_id.name']

    loan_id = fields.Many2one('library.loan', required=True, ondelete='cascade', index=True)
    book_copy_id = fields.Many2one(
        'library.book.copy',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    member_id = fields.Many2one(related='loan_id.member_id', store=True, readonly=True)
    branch_id = fields.Many2one(related='loan_id.branch_id', store=True, readonly=True)
    book_id = fields.Many2one(related='book_copy_id.book_id', store=True, readonly=True)
    issue_datetime = fields.Datetime(string='Issued On')
    due_datetime = fields.Datetime(string='Due Date')
    return_datetime = fields.Datetime(string='Returned On')
    renewal_count = fields.Integer(default=0)
    fine_amount = fields.Float(digits=(10, 2), default=0.0)
    condition_on_issue = fields.Selection(
        [
            ('new', 'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('damaged', 'Damaged'),
        ],
        default='good',
    )
    condition_on_return = fields.Selection(
        [
            ('new', 'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('damaged', 'Damaged'),
        ],
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('issued', 'Issued'),
            ('returned', 'Returned'),
            ('overdue', 'Overdue'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    is_overdue = fields.Boolean(compute='_compute_is_overdue', store=True)
    days_overdue = fields.Integer(compute='_compute_is_overdue', store=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)

    @api.depends('due_datetime', 'state', 'return_datetime')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for line in self:
            if line.state == 'issued' and line.due_datetime and not line.return_datetime:
                line.is_overdue = line.due_datetime < now
                delta = now - line.due_datetime
                line.days_overdue = delta.days
            else:
                line.is_overdue = False
                line.days_overdue = 0

    def action_renew(self):
        for line in self:
            if line.state != 'issued':
                raise ValidationError('Only issued items can be renewed.')
            if line.is_overdue:
                raise ValidationError('Cannot renew an overdue item. Please return it first.')
            member = line.member_id
            plan = member.membership_plan_id
            max_renewals = plan.maximum_renewals if plan else 2
            if line.renewal_count >= max_renewals:
                raise ValidationError('Maximum renewals (%d) reached.' % max_renewals)
            loan_days = plan.loan_period_days if plan else 14
            line.due_datetime = fields.Datetime.now() + relativedelta(days=loan_days)
            line.renewal_count += 1

    def _process_return(self):
        self.ensure_one()
        if self.state != 'issued':
            return
        self.return_datetime = fields.Datetime.now()
        self.state = 'returned'

        copy = self.book_copy_id
        if self.condition_on_return == 'damaged':
            copy.condition = 'damaged'
            copy.action_damaged()
        elif self.condition_on_return in ('new', 'good', 'fair', 'poor'):
            copy.condition = self.condition_on_return
            copy.action_available()
        else:
            copy.action_available()

        if self.is_overdue and self.fine_amount <= 0:
            plan = self.member_id.membership_plan_id
            fine_per_day = plan.fine_per_day if plan else 1.0
            self.fine_amount = self.days_overdue * fine_per_day
            if self.fine_amount > 0:
                self.env['library.fine'].create({
                    'member_id': self.member_id.id,
                    'loan_line_id': self.id,
                    'fine_type': 'late_return',
                    'amount': self.fine_amount,
                    'due_date': fields.Date.context_today(self),
                })

        self.member_id.current_loans_count = max(0, self.member_id.current_loans_count - 1)

    @api.constrains('book_copy_id', 'loan_id', 'state')
    def _check_active_loan(self):
        for line in self:
            if line.state == 'issued' and line.book_copy_id:
                domain = [
                    ('book_copy_id', '=', line.book_copy_id.id),
                    ('state', '=', 'issued'),
                    ('id', '!=', line.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        'Copy "%s" already has an active loan.' % (line.book_copy_id.barcode or line.book_copy_id.name)
                    )
