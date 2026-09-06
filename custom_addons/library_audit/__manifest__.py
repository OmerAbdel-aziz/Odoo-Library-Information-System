{
    'name': 'Library Audit',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Rule-based audit trail for critical library records',
    'description': """
Library Audit
=============
Audit rules select models, operations and fields to track. Creates,
writes and deletions are logged with user, timestamp, and old/new
values per field.
""",
    'depends': ['library_base', 'mail'],
    'data': [
        'security/library_audit_security.xml',
        'security/ir.model.access.csv',
        'views/library_audit_rule_views.xml',
        'views/library_audit_log_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
