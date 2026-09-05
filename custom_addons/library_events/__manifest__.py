{
    'name': 'Library Events',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Library programs, sessions and member registrations',
    'description': """
Library Events
==============
Book clubs, workshops, story sessions, trainings, author meetings
and reading competitions with capacity control and attendance.
""",
    'depends': ['library_base', 'library_membership'],
    'data': [
        'security/library_events_security.xml',
        'security/ir.model.access.csv',
        'data/library_events_sequence_data.xml',
        'views/library_event_views.xml',
        'views/library_event_registration_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
