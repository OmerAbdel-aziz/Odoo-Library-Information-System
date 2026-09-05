from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('at_install', '-post_install')
class TestLibraryCatalog(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Book = cls.env['library.book']
        cls.Copy = cls.env['library.book.copy']
        cls.Author = cls.env['library.author']
        cls.Publisher = cls.env['library.publisher']
        cls.Subject = cls.env['library.subject']
        cls.Category = cls.env['library.category']
        cls.Language = cls.env['library.language']
        cls.ClassSystem = cls.env['library.classification.system']
        cls.ClassCode = cls.env['library.classification.code']
        cls.Series = cls.env['library.series']
        cls.Branch = cls.env['library.branch']

        cls.branch = cls.Branch.create({
            'name': 'Main Library',
            'code': 'LIB01',
        })
        cls.floor = cls.env['library.floor'].create({
            'name': 'Ground Floor',
            'code': 'GF',
            'branch_id': cls.branch.id,
        })
        cls.section = cls.env['library.section'].create({
            'name': 'Computer Science',
            'code': 'CS',
            'floor_id': cls.floor.id,
        })
        cls.shelf = cls.env['library.shelf'].create({
            'name': 'Shelf CS-01',
            'code': 'CS-01',
            'section_id': cls.section.id,
        })

        cls.author = cls.Author.create({'name': 'Robert C. Martin'})
        cls.publisher = cls.Publisher.create({'name': 'Prentice Hall'})
        cls.language = cls.Language.create({'name': 'English', 'code': 'en'})
        cls.subject = cls.Subject.create({'name': 'Software Engineering', 'code': 'SE'})
        cls.category = cls.Category.create({'name': 'Computers', 'code': 'COMP'})
        cls.series = cls.Series.create({'name': 'Professional Series', 'code': 'PS'})

        cls.class_system = cls.ClassSystem.create({
            'name': 'Dewey Decimal',
            'code': 'DDC',
        })
        cls.class_code = cls.ClassCode.create({
            'name': 'Computer Science',
            'code': '000',
            'system_id': cls.class_system.id,
        })

        cls.book = cls.Book.create({
            'name': 'Clean Code',
            'isbn_13': '9780132350884',
            'book_type': 'book',
            'author_ids': [Command.set(cls.author.ids)],
            'publisher_id': cls.publisher.id,
            'language_id': cls.language.id,
            'subject_ids': [Command.set(cls.subject.ids)],
            'category_ids': [Command.set(cls.category.ids)],
            'classification_id': cls.class_system.id,
            'classification_code_id': cls.class_code.id,
            'series_id': cls.series.id,
        })

        cls.cataloger = new_test_user(
            cls.env,
            login='cataloger',
            groups='library_base.library_group_cataloger',
        )
        cls.library_user = new_test_user(
            cls.env,
            login='catalog_user',
            groups='library_base.library_group_user',
        )
        cls.library_user.allowed_branch_ids = [(6, 0, cls.branch.ids)]

    def test_book_display_name_with_authors(self):
        self.assertIn('Clean Code', self.book.display_name)
        self.assertIn('Robert C. Martin', self.book.display_name)

    def test_isbn_10_validation(self):
        with self.assertRaises(ValidationError):
            self.Book.create({
                'name': 'Bad ISBN',
                'isbn_10': '123456789',  # too short
            })

    def test_isbn_13_validation(self):
        with self.assertRaises(ValidationError):
            self.Book.create({
                'name': 'Bad ISBN-13',
                'isbn_13': '123456789012',  # too short
            })

    def test_valid_isbn_10(self):
        book = self.Book.create({
            'name': 'Valid ISBN-10',
            'isbn_10': '0-13-235088-2',
        })
        self.assertEqual(book.isbn_10, '0-13-235088-2')

    def test_valid_isbn_10_with_x(self):
        book = self.Book.create({
            'name': 'Valid ISBN-10 with X',
            'isbn_10': '0-8044-2957-X',
        })
        self.assertEqual(book.isbn_10, '0-8044-2957-X')

    def test_invalid_isbn_10_check_character(self):
        with self.assertRaises(ValidationError):
            self.Book.create({
                'name': 'Bad ISBN-10 Check',
                'isbn_10': '013235088Z',
            })

    def test_valid_isbn_13(self):
        book = self.Book.create({
            'name': 'Valid ISBN-13',
            'isbn_13': '978-0-13-235088-4',
        })
        self.assertEqual(book.isbn_13, '978-0-13-235088-4')

    def test_copy_auto_generates_barcode(self):
        copy = self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
        })
        self.assertTrue(copy.barcode)
        self.assertTrue(copy.barcode.startswith('LIB01-BK-'))

    def test_copy_barcode_unique(self):
        self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
            'barcode': 'UNIQUE-TEST-001',
        })
        with self.assertRaises(ValidationError):
            self.Copy.create({
                'book_id': self.book.id,
                'branch_id': self.branch.id,
                'barcode': 'UNIQUE-TEST-001',
            })

    def test_copy_state_workflow(self):
        copy = self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
        })
        self.assertEqual(copy.state, 'available')
        copy.action_on_loan()
        self.assertEqual(copy.state, 'on_loan')
        copy.action_available()
        self.assertEqual(copy.state, 'available')
        copy.action_lost()
        self.assertEqual(copy.state, 'lost')

    def test_copy_invalid_state_transition_rejected(self):
        copy = self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
        })
        copy.action_lost()
        with self.assertRaises(ValidationError):
            copy.action_available()
        with self.assertRaises(ValidationError):
            copy.action_on_loan()

    def test_copy_name_computation(self):
        copy = self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
            'copy_number': 1,
        })
        self.assertIn('Clean Code', copy.name)
        self.assertIn('#1', copy.name)

    def test_book_copy_count(self):
        self.assertEqual(self.book.copy_count, 0)
        self.Copy.create({
            'book_id': self.book.id,
            'branch_id': self.branch.id,
        })
        self.book.invalidate_recordset(['copy_count'])
        self.assertEqual(self.book.copy_count, 1)

    def test_classification_hierarchy(self):
        sub_code = self.ClassCode.create({
            'name': 'Algorithms',
            'code': '001',
            'system_id': self.class_system.id,
            'parent_id': self.class_code.id,
        })
        self.assertEqual(sub_code.parent_id, self.class_code)
        self.assertIn(sub_code, self.class_code.child_ids)

    def test_category_hierarchy(self):
        sub_cat = self.Category.create({
            'name': 'Programming',
            'code': 'PROG',
            'parent_id': self.category.id,
        })
        self.assertEqual(sub_cat.parent_id, self.category)
        self.assertIn(sub_cat, self.category.child_ids)

    def test_user_can_read_books(self):
        books = self.Book.with_user(self.library_user).search([])
        self.assertIn(self.book, books)

    def test_cataloger_can_crud_books(self):
        book = self.Book.with_user(self.cataloger).create({
            'name': 'New Book',
            'book_type': 'book',
        })
        self.assertTrue(book.id)
        book.with_user(self.cataloger).write({'name': 'Updated Book'})
        self.assertEqual(book.name, 'Updated Book')
