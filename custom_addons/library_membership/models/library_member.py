from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _order = 'member_number'
    _rec_names_search = ['member_number', 'partner_id.name', 'partner_id.email']
    _check_company_auto = True

    member_number = fields.Char(required=True, readonly=True, copy=False, index=True)
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    membership_plan_id = fields.Many2one(
        'library.membership.plan',
        string='Membership Plan',
        index=True,
    )
    registration_date = fields.Date(default=fields.Date.context_today, required=True)
    expiry_date = fields.Date(compute='_compute_expiry_date', store=True)
    branch_id = fields.Many2one(
        'library.branch',
        required=True,
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    member_type = fields.Selection(
        [
            ('adult', 'Adult'),
            ('child', 'Child'),
            ('student', 'Student'),
            ('university_student', 'University Student'),
            ('faculty', 'Faculty'),
            ('employee', 'Employee'),
            ('researcher', 'Researcher'),
            ('vip', 'VIP'),
            ('organization', 'Organization'),
        ],
        default='adult',
        required=True,
    )
    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('suspended', 'Suspended'),
            ('blocked', 'Blocked'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True,
        index=True,
    )
    barcode = fields.Char(index=True, copy=False)
    qr_code = fields.Char(string='QR Code', copy=False)
    max_books = fields.Integer(compute='_compute_max_books', store=True)
    current_loans_count = fields.Integer(default=0)
    outstanding_fines = fields.Float(digits=(10, 2), default=0.0)
    blocked = fields.Boolean(default=False)
    block_reason = fields.Text()
    image_1920 = fields.Image(related='partner_id.image_1920', string='Photo')
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    active = fields.Boolean(default=True)

    _sql_expiry_check = models.Constraint(
        'CHECK(expiry_date IS NULL OR expiry_date >= registration_date)',
        'Expiry date must be after registration date.',
    )

    @api.depends('registration_date', 'membership_plan_id.duration')
    def _compute_expiry_date(self):
        for member in self:
            if member.registration_date and member.membership_plan_id:
                member.expiry_date = member.registration_date + relativedelta(
                    days=member.membership_plan_id.duration
                )
            else:
                member.expiry_date = False

    @api.depends('membership_plan_id.maximum_books')
    def _compute_max_books(self):
        for member in self:
            member.max_books = member.membership_plan_id.maximum_books if member.membership_plan_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('member_number'):
                vals['member_number'] = self.env['ir.sequence'].next_by_code('library.member')
            if not vals.get('barcode'):
                vals['barcode'] = self.env['ir.sequence'].next_by_code('library.member.barcode')
        members = super().create(vals_list)
        for member in members:
            if not member.qr_code:
                member.qr_code = f'LIBMEM:{member.id}'
        return members

    def write(self, vals):
        res = super().write(vals)
        if vals.get('blocked'):
            for member in self:
                if member.status == 'active':
                    member.status = 'blocked'
        return res

    def action_activate(self):
        for member in self:
            if member.status in ('draft', 'suspended', 'blocked'):
                member.write({'blocked': False, 'block_reason': False, 'status': 'active'})

    def action_suspend(self):
        for member in self:
            if member.status == 'active':
                member.status = 'suspended'

    def action_block(self):
        for member in self:
            if member.status in ('active', 'suspended'):
                member.write({'blocked': True, 'status': 'blocked'})

    def action_cancel(self):
        for member in self:
            if member.status not in ('cancelled',):
                member.status = 'cancelled'
                member.active = False

    def action_set_draft(self):
        for member in self:
            if member.status == 'cancelled':
                member.status = 'draft'
                member.active = True

    @api.constrains('blocked', 'status')
    def _check_blocked_status(self):
        for member in self:
            if member.blocked and member.status not in ('blocked', 'cancelled'):
                raise ValidationError('A blocked member must have blocked or cancelled status.')
            if member.status == 'blocked' and not member.blocked:
                raise ValidationError('A member with blocked status must have the blocked flag set.')
