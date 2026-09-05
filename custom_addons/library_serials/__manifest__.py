{
    'name': 'Library Serials',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Periodical subscriptions and issue tracking',
    'description': """
Library Serials
===============
Magazine/journal subscriptions with suppliers, expected issue
generation from frequency, receipt tracking, and claiming of
missing issues.
""",
    'depends': ['library_base'],
    'data': [
        'security/library_serials_security.xml',
        'security/ir.model.access.csv',
        'data/library_serials_sequence_data.xml',
        'views/library_subscription_views.xml',
        'views/library_serial_issue_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
