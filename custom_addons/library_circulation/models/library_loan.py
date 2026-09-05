from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryLoan(models.Model):
    _name = 'library.loan'
    _description = 'Library Loan'
    _order = 'issue_date desc, id desc'
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
    branch_id = fields.Many2one(
        'library.branch',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    loan_line_ids = fields.One2many('library.loan.line', 'loan_id', string='Loan Lines')
    line_count = fields.Integer(compute='_compute_line_count', store=True)
    issue_date = fields.Date()
    due_date = fields.Date()
    return_date = fields.Date()
    issued_by = fields.Many2one('res.users', string='Issued By', index=True)
    returned_by = fields.Many2one('res.users', string='Returned By', index=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('issued', 'Issued'),
            ('returned', 'Returned'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    @api.depends('loan_line_ids')
    def _compute_line_count(self):
        for loan in self:
            loan.line_count = len(loan.loan_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.loan')
        return super().create(vals_list)

    def action_issue(self):
        for loan in self:
            if not loan.loan_line_ids:
                raise ValidationError('Cannot issue a loan without any items.')
            if not loan.issue_date:
                loan.issue_date = fields.Date.context_today(self)
            if not loan.issued_by:
                loan.issued_by = self.env.user

            member = loan.member_id
            if member.status != 'active':
                raise ValidationError('Only active members can borrow books.')
            if member.blocked:
                raise ValidationError('This member is blocked and cannot borrow books.')
            if member.outstanding_fines > (member.membership_plan_id.maximum_fine if member.membership_plan_id else 0):
                raise ValidationError('Member has outstanding fines exceeding the limit.')

            max_books = member.membership_plan_id.maximum_books if member.membership_plan_id else 0
            if max_books and (member.current_loans_count + len(loan.loan_line_ids)) > max_books:
                raise ValidationError('Member would exceed maximum books allowed (%d).' % max_books)

            for line in loan.loan_line_ids:
                copy = line.book_copy_id
                if copy.state != 'available':
                    raise ValidationError('Copy "%s" is not available (current state: %s).' % (copy.barcode or copy.name, copy.state))
                if not copy.circulating:
                    raise ValidationError('Copy "%s" is not a circulating copy.' % (copy.barcode or copy.name))

                plan = member.membership_plan_id
                loan_days = plan.loan_period_days if plan else 14
                line.with_context(loan_line_action=True).write({
                    'issue_datetime': fields.Datetime.now(),
                    'due_datetime': fields.Datetime.now() + relativedelta(days=loan_days),
                })
                copy.action_on_loan()

            loan.loan_line_ids.with_context(loan_line_action=True).write({'state': 'issued'})
            member.current_loans_count += len(loan.loan_line_ids)
            due_datetimes = loan.loan_line_ids.mapped('due_datetime')
            loan.due_date = max(due_datetimes).date() if due_datetimes else False
            loan.state = 'issued'

    def action_return(self):
        for loan in self:
            if loan.state != 'issued':
                raise ValidationError('Only issued loans can be returned.')
            unreturned = loan.loan_line_ids.filtered(lambda l: l.state != 'returned')
            if not unreturned:
                raise ValidationError('All items are already returned.')
            for line in unreturned:
                line._process_return()
            loan.return_date = fields.Date.context_today(self)
            loan.returned_by = self.env.user
            loan.state = 'returned'

    def action_cancel(self):
        for loan in self:
            if loan.state == 'cancelled':
                continue
            if loan.state == 'issued':
                issued_lines = loan.loan_line_ids.filtered(lambda l: l.state == 'issued')
                for line in issued_lines:
                    line.book_copy_id.action_available()
                issued_lines.with_context(loan_line_action=True).write({'state': 'cancelled'})
                loan.member_id.current_loans_count -= len(issued_lines)
            loan.state = 'cancelled'

    def action_view_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Loan Items',
            'res_model': 'library.loan.line',
            'view_mode': 'list,form',
            'domain': [('loan_id', '=', self.id)],
        }
