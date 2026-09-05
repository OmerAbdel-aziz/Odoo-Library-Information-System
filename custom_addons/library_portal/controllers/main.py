from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

PAGE_SIZE = 20


class LibraryPortalController(http.Controller):

    def _get_member(self):
        member = request.env['library.member']._get_portal_member(request.env.user)
        if not member:
            return None
        return member

    def _no_member(self):
        member = request.env['library.member']._get_any_member(request.env.user)
        if member:
            return request.render('library_portal.portal_membership_restricted', {
                'page_name': 'library', 'member': member,
            })
        return request.render('library_portal.portal_no_membership', {'page_name': 'library'})

    def _render_error(self, template, member, error, extra=None):
        values = {'page_name': 'library', 'member': member, 'error': error}
        values.update(extra or {})
        return request.render(template, values)

    @http.route('/my/library', type='http', auth='user')
    def dashboard(self):
        member = self._get_member()
        if not member:
            return self._no_member()
        values = member._portal_dashboard()
        branches = request.env['library.branch'].search([])
        values.update({'page_name': 'library', 'branches': branches})
        return request.render('library_portal.portal_library_home', values)

    @http.route('/my/library/books', type='http', auth='user')
    def books(self, q=None, page=1):
        member = self._get_member()
        if not member:
            return self._no_member()
        try:
            page = max(1, int(page or 1))
        except (TypeError, ValueError):
            page = 1
        Book = request.env['library.book']
        total = Book._portal_search_count(query=q)
        books = Book._portal_search(query=q, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
        return request.render('library_portal.portal_library_books', {
            'page_name': 'library_books', 'member': member, 'books': books,
            'q': q or '', 'page': page, 'pages': max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        })

    @http.route('/my/library/books/<int:book_id>', type='http', auth='user')
    def book_detail(self, book_id, error=None):
        member = self._get_member()
        if not member:
            return self._no_member()
        book = request.env['library.book'].browse(book_id)
        if not book.exists():
            return request.not_found()
        return request.render('library_portal.portal_library_book_detail', {
            'page_name': 'library_books', 'member': member, 'book': book,
            'availability': book._portal_availability(), 'error': error,
        })

    @http.route('/my/library/books/<int:book_id>/reserve', type='http', auth='user', methods=['POST'])
    def book_reserve(self, book_id):
        member = self._get_member()
        if not member:
            return self._no_member()
        book = request.env['library.book'].browse(book_id)
        if not book.exists():
            return request.not_found()
        try:
            request.env['library.reservation'].create({
                'member_id': member.id,
                'book_id': book.id,
                'preferred_branch_id': member.branch_id.id,
            })
        except (ValidationError, UserError) as e:
            return self.book_detail(book_id, error=e.args[0])
        return request.redirect('/my/library/reservations')

    @http.route('/my/library/loans', type='http', auth='user')
    def loans(self, error=None):
        member = self._get_member()
        if not member:
            return self._no_member()
        lines = request.env['library.loan.line'].search(
            [('member_id', '=', member.id)], order='due_datetime desc', limit=100)
        return request.render('library_portal.portal_library_loans', {
            'page_name': 'library_loans', 'member': member, 'lines': lines, 'error': error,
        })

    @http.route('/my/library/loans/renew/<int:line_id>', type='http', auth='user', methods=['POST'])
    def loan_renew(self, line_id):
        member = self._get_member()
        if not member:
            return self._no_member()
        line = request.env['library.loan.line'].browse(line_id)
        if not line.exists() or line.member_id != member:
            return request.not_found()
        try:
            line.action_renew()
        except (ValidationError, UserError) as e:
            return self.loans(error=e.args[0])
        return request.redirect('/my/library/loans')

    @http.route('/my/library/fines', type='http', auth='user')
    def fines(self):
        member = self._get_member()
        if not member:
            return self._no_member()
        fines = request.env['library.fine'].search([('member_id', '=', member.id)])
        return request.render('library_portal.portal_library_fines', {
            'page_name': 'library_fines', 'member': member, 'fines': fines,
        })

    @http.route('/my/library/reservations', type='http', auth='user')
    def reservations(self, error=None):
        member = self._get_member()
        if not member:
            return self._no_member()
        reservations = request.env['library.reservation'].search([('member_id', '=', member.id)])
        return request.render('library_portal.portal_library_reservations', {
            'page_name': 'library_reservations', 'member': member,
            'reservations': reservations, 'error': error,
        })

    @http.route('/my/library/reservations/cancel/<int:reservation_id>', type='http', auth='user', methods=['POST'])
    def reservation_cancel(self, reservation_id):
        member = self._get_member()
        if not member:
            return self._no_member()
        reservation = request.env['library.reservation'].browse(reservation_id)
        if not reservation.exists() or reservation.member_id != member:
            return request.not_found()
        try:
            reservation.action_cancel()
        except (ValidationError, UserError) as e:
            return self.reservations(error=e.args[0])
        return request.redirect('/my/library/reservations')

    @http.route('/my/library/events', type='http', auth='user')
    def events(self, error=None):
        member = self._get_member()
        if not member:
            return self._no_member()
        events = request.env['library.event'].search([('state', 'in', ('published', 'ongoing'))])
        return request.render('library_portal.portal_library_events', {
            'page_name': 'library_events', 'member': member, 'events': events, 'error': error,
        })

    @http.route('/my/library/events/register/<int:event_id>', type='http', auth='user', methods=['POST'])
    def event_register(self, event_id):
        member = self._get_member()
        if not member:
            return self._no_member()
        event = request.env['library.event'].browse(event_id)
        if not event.exists() or event.state not in ('published', 'ongoing'):
            return request.not_found()
        try:
            request.env['library.event.registration'].create({
                'event_id': event.id, 'member_id': member.id,
            })
        except (ValidationError, UserError) as e:
            return self.events(error=e.args[0])
        return request.redirect('/my/library/events')

    @http.route('/my/library/requests', type='http', auth='user')
    def purchase_requests(self, error=None):
        member = self._get_member()
        if not member:
            return self._no_member()
        requests = request.env['library.purchase.request'].search([('member_id', '=', member.id)])
        branches = request.env['library.branch'].search([])
        return request.render('library_portal.portal_library_requests', {
            'page_name': 'library_requests', 'member': member,
            'requests': requests, 'branches': branches, 'error': error,
        })

    @http.route('/my/library/requests/create', type='http', auth='user', methods=['POST'])
    def purchase_request_create(self, **post):
        member = self._get_member()
        if not member:
            return self._no_member()
        try:
            quantity = max(1, int(post.get('quantity') or 1))
        except (TypeError, ValueError):
            return self.purchase_requests(error='Invalid quantity.')
        try:
            request.env['library.purchase.request'].create({
                'member_id': member.id,
                'book_name': (post.get('book_name') or '').strip(),
                'author': (post.get('author') or '').strip(),
                'isbn': (post.get('isbn') or '').strip(),
                'reason': (post.get('reason') or '').strip(),
                'quantity': quantity,
                'branch_id': int(post.get('branch_id')) if post.get('branch_id') else member.branch_id.id,
            })
        except (ValidationError, UserError) as e:
            return self.purchase_requests(error=e.args[0])
        return request.redirect('/my/library/requests')
