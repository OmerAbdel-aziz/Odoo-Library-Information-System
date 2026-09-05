{
    'name': 'Library Mobile',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Bookmobile units, routes, stops and trips',
    'description': """
Library Mobile
==============
Mobile library units with scheduled routes and stops. Trips carry
book copies out to stops and reconcile them back at the home branch.
""",
    'depends': ['library_base', 'library_catalog', 'library_circulation'],
    'data': [
        'security/library_mobile_security.xml',
        'security/ir.model.access.csv',
        'data/library_mobile_sequence_data.xml',
        'views/library_mobile_unit_views.xml',
        'views/library_mobile_route_views.xml',
        'views/library_mobile_trip_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
