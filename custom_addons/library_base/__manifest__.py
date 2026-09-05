{
    'name': 'Library Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'sequence': 210,
    'summary': 'Foundation for multi-branch library management',
    'description': """
Library Management Foundation
=============================

Base module for the Library Information System. It defines the branch and
physical location hierarchy shared by catalog, circulation, inventory, maps,
portal, and reporting modules.
""",
    'depends': ['base'],
    'data': [
        'security/library_base_security.xml',
        'security/ir.model.access.csv',
        'data/library_weekday_data.xml',
        'views/library_base_menus.xml',
        'views/library_branch_views.xml',
        'views/library_floor_views.xml',
        'views/library_section_views.xml',
        'views/library_shelf_views.xml',
        'views/library_weekday_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
