{
    'name': 'Library Offline Map',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Indoor floor maps, branch pins and offline map settings',
    'description': """
Library Offline Map
===================
Indoor floor-plan viewer with shelf coordinates, find-book on map,
branch pins API, offline nearest-branch lookup, and connection
settings for tile/geocode/routing services.

Note: the geographic MapLibre viewer and tile data are deployment
artifacts and ship separately; this module provides the indoor
viewer, data models, JSON APIs, and service settings.
""",
    'depends': ['library_base', 'library_catalog'],
    'data': [
        'security/library_offline_map_security.xml',
        'security/ir.model.access.csv',
        'data/library_map_settings_data.xml',
        'views/library_floor_map_views.xml',
        'views/library_shelf_map_views.xml',
        'views/library_map_settings_views.xml',
        'views/library_offline_map_menus.xml',
        'views/library_book_copy_map_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'library_offline_map/static/src/**/*.js',
            'library_offline_map/static/src/**/*.xml',
            'library_offline_map/static/src/**/*.scss',
        ],
    },
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
