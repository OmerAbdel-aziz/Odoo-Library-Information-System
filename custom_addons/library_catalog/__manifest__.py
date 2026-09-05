{
    'name': 'Library Catalog',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Book catalog, authors, publishers, and classification',
    'description': """
Library Catalog
===============
Manages the bibliographic records (books), physical copies, authors,
publishers, subjects, categories, classification systems, and series
for the Library Information System.
""",
    'depends': ['library_base', 'product'],
    'data': [
        'security/library_catalog_security.xml',
        'security/ir.model.access.csv',
        'data/library_book_sequence_data.xml',
        'views/library_author_views.xml',
        'views/library_publisher_views.xml',
        'views/library_subject_views.xml',
        'views/library_category_views.xml',
        'views/library_language_views.xml',
        'views/library_classification_views.xml',
        'views/library_series_views.xml',
        'views/library_book_views.xml',
        'views/library_book_copy_views.xml',
    ],
    'installable': True,
    'author': 'Odoo LIS Contributors',
    'license': 'LGPL-3',
}
