{
    'name': 'Library Membership',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Member management, membership plans, and library cards',
    'description': """
Library Membership
==================
Manages library members, membership plans, registration, expiry,
and printable library cards for the Library Information System.
""",
    'depends': ['library_base'],
    'data': [
        'security/library_membership_security.xml',
        'security/ir.model.access.csv',
        'data/library_member_sequence_data.xml',
        'views/library_membership_plan_views.xml',
        'views/library_member_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
