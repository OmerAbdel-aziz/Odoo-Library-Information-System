from odoo import api, models


class LibraryBookPortal(models.Model):
    _inherit = 'library.book'

    @api.model
    def _portal_search(self, query=None, limit=50):
        domain = []
        if query:
            domain = ['|', '|', ('name', 'ilike', query),
                      ('isbn_13', 'ilike', query),
                      ('author_ids.name', 'ilike', query)]
        return self.search(domain, limit=limit)

    def _portal_availability(self):
        self.ensure_one()
        copies = self.env['library.book.copy'].search([('book_id', '=', self.id)])
        by_branch = {}
        for copy in copies:
            branch = copy.branch_id.name or '-'
            entry = by_branch.setdefault(branch, {'total': 0, 'available': 0})
            entry['total'] += 1
            if copy.state == 'available':
                entry['available'] += 1
        return by_branch
