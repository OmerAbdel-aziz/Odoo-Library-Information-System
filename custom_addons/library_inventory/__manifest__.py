{
    'name': 'Library Inventory',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Branch stock locations, copy traceability, inter-branch transfers',
    'description': """
Library Inventory
=================
Branch warehouse locations (Processing, Available, Hold Shelf, Repair,
Withdrawn), book/copy linkage to products and lots, and the
inter-branch transfer workflow.
""",
    'depends': ['library_base', 'library_catalog', 'stock'],
    'data': [
        'security/library_inventory_security.xml',
        'security/ir.model.access.csv',
        'data/library_inventory_sequence_data.xml',
        'views/library_branch_inventory_views.xml',
        'views/library_transfer_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
