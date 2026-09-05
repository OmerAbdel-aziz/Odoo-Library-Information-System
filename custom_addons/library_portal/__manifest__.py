{
    'name': 'Library Portal',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Member self-service: catalog, loans, fines, events',
    'description': """
Library Portal
==============
Member self-service portal: catalog search with availability,
reservations, loan viewing and renewal, fines, and event listing
with registration.
""",
    'depends': [
        'library_base', 'library_catalog', 'library_membership',
        'library_circulation', 'library_reservation', 'library_events',
        'library_acquisition', 'portal',
    ],
    'data': [
        'security/library_portal_security.xml',
        'security/ir.model.access.csv',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
