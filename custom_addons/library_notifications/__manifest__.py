{
    'name': 'Library Notifications',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Due/overdue alerts, reservation and membership reminders',
    'description': """
Library Notifications
=====================
Generates and dispatches member notifications: books due soon and
overdue, reservations ready and expiring, memberships expiring,
new fines, and event reminders — via inbox and email.
""",
    'depends': [
        'library_base', 'library_membership', 'library_circulation',
        'library_reservation', 'library_events', 'mail',
    ],
    'data': [
        'security/library_notifications_security.xml',
        'security/ir.model.access.csv',
        'data/library_notifications_sequence_data.xml',
        'data/library_notifications_cron_data.xml',
        'views/library_notification_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
