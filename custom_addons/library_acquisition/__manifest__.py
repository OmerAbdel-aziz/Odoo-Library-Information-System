{
    'name': 'Library Acquisition',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Purchase requests, vendor orders, receiving and cataloging',
    'description': """
Library Acquisition
===================
Librarian/member purchase requests, approval, vendor purchase orders,
receiving, cataloging, copy generation with barcodes and shelf assignment.
""",
    'depends': ['library_base', 'library_catalog', 'purchase'],
    'data': [
        'security/library_acquisition_security.xml',
        'security/ir.model.access.csv',
        'data/library_acquisition_sequence_data.xml',
        'views/library_purchase_request_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
