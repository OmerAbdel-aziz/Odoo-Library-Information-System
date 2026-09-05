{
    'name': 'Library Reservation',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Book reservation hold queue and pickup management',
    'description': """
Library Reservation
===================
Manages the book reservation hold queue, copy allocation,
pickup notifications, and reservation expiry.
""",
    'depends': ['library_base', 'library_catalog', 'library_membership'],
    'data': [
        'security/library_reservation_security.xml',
        'security/ir.model.access.csv',
        'data/library_reservation_sequence_data.xml',
        'views/library_reservation_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
