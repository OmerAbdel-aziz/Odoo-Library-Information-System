from odoo import api, models


class LibraryBookPortal(models.Model):
    _inherit = 'library.book'

    @api.model
    def _portal_search(self, query=None, limit=50, offset=0):
        domain = []
        if query:
            domain = ['|', '|', '|', '|', '|',
                      ('name', 'ilike', query),
                      ('isbn_13', 'ilike', query),
                      ('isbn_10', 'ilike', query),
                      ('author_ids.name', 'ilike', query),
                      ('publisher_id.name', 'ilike', query),
                      ('subject_ids.name', 'ilike', query)]
        return self.search(domain, limit=limit, offset=offset)

    @api.model
    def _portal_search_count(self, query=None):
        domain = []
        if query:
            domain = ['|', '|', '|', '|', '|',
                      ('name', 'ilike', query),
                      ('isbn_13', 'ilike', query),
                      ('isbn_10', 'ilike', query),
                      ('author_ids.name', 'ilike', query),
                      ('publisher_id.name', 'ilike', query),
                      ('subject_ids.name', 'ilike', query)]
        return self.search_count(domain)

    def _portal_availability(self):
        self.ensure_one()
        copies = self.env['library.book.copy'].search([('book_id', '=', self.id)])
        by_branch = {}
        for copy in copies:
            branch = copy.branch_id
            entry = by_branch.setdefault(branch.id, {
                'branch': branch.name,
                'total': 0, 'available': 0, 'on_loan': 0, 'reserved': 0, 'other': 0,
            })
            entry['total'] += 1
            if copy.state == 'available':
                entry['available'] += 1
            elif copy.state == 'on_loan':
                entry['on_loan'] += 1
            elif copy.state == 'reserved':
                entry['reserved'] += 1
            else:
                entry['other'] += 1
        return by_branch
