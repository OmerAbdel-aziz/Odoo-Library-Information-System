{
    'name': 'Library Circulation',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Loans, returns, renewals, and fine management',
    'description': """
Library Circulation
==================
Manages the complete lending lifecycle: issuing books, tracking due dates,
processing returns, handling renewals, and managing fines.
""",
    'depends': ['library_base', 'library_catalog', 'library_membership'],
    'data': [
        'security/library_circulation_security.xml',
        'security/ir.model.access.csv',
        'data/library_circulation_sequence_data.xml',
        'views/library_loan_views.xml',
        'views/library_fine_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
