{
    'name': 'Library Digital',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'E-books, audio, research documents and licensed checkouts',
    'description': """
Library Digital
===============
Digital assets (e-books, PDFs, audio books, research documents,
journals) with access permissions, download control, license
limits and expiry, plus member checkouts.
""",
    'depends': ['library_base', 'library_membership'],
    'data': [
        'security/library_digital_security.xml',
        'security/ir.model.access.csv',
        'data/library_digital_sequence_data.xml',
        'views/library_digital_asset_views.xml',
        'views/library_digital_checkout_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
