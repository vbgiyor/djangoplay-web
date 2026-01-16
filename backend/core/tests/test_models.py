import datetime

from django.db import connection
from django.test import TestCase

# Import TimeStampedModel and ActiveManager from core.models
# Import test models from test_models_definitions
from .test_models_definitions import TestModel, TestModelWithoutIsActive


class BaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        # Disable foreign key constraints for SQLite
        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys = OFF;')

        # Create schema for test models only if they don't exist
        with connection.schema_editor() as schema_editor:
            # Check if tables exist to avoid "table already exists" error
            existing_tables = connection.introspection.table_names()
            if 'core_testmodel' not in existing_tables:
                schema_editor.create_model(TestModel)
            if 'core_testmodelwithoutisactive' not in existing_tables:
                schema_editor.create_model(TestModelWithoutIsActive)

        # Re-enable foreign key constraints
        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys = ON;')

        super().setUpClass()

class TimeStampedModelTests(BaseTestCase):
    def setUp(self):
        self.model = TestModel.objects.create(name="Test Instance")

    def test_created_at_auto_set(self):
        """Test that created_at is automatically set on creation."""
        self.assertIsNotNone(self.model.created_at)
        self.assertTrue(isinstance(self.model.created_at, datetime.datetime))

    def test_updated_at_auto_set(self):
        """Test that updated_at is automatically set on creation and updates."""
        original_updated_at = self.model.updated_at
        self.model.name = "Updated Name"
        self.model.save()
        self.assertNotEqual(self.model.updated_at, original_updated_at)

    def test_soft_delete(self):
        """Test that soft_delete sets deleted_at timestamp."""
        self.model.soft_delete()
        self.assertIsNotNone(self.model.deleted_at)
        self.assertTrue(isinstance(self.model.deleted_at, datetime.datetime))

    def test_restore(self):
        """Test that restore clears deleted_at timestamp."""
        self.model.soft_delete()
        self.model.restore()
        self.assertIsNone(self.model.deleted_at)

    def test_soft_delete_does_not_remove_from_db(self):
        """Test that soft_delete keeps the record in the database."""
        self.model.soft_delete()
        self.assertTrue(TestModel.all_objects.filter(id=self.model.id).exists())

class ActiveManagerTests(BaseTestCase):
    def setUp(self):
        # Create test instances
        self.active_instance = TestModel.objects.create(name="Active")
        self.inactive_instance = TestModel.objects.create(name="Inactive", is_active=False)
        self.deleted_instance = TestModel.objects.create(name="Deleted")
        self.deleted_instance.soft_delete()
        self.model_without_is_active = TestModelWithoutIsActive.objects.create(name="No Is Active")
        self.deleted_no_is_active = TestModelWithoutIsActive.objects.create(name="Deleted No Is Active")
        self.deleted_no_is_active.soft_delete()

    def test_active_manager_filters_deleted(self):
        """Test that ActiveManager excludes soft-deleted records."""
        queryset = TestModel.objects.all()
        self.assertIn(self.active_instance, queryset)
        self.assertNotIn(self.deleted_instance, queryset)

    def test_active_manager_filters_inactive(self):
        """Test that ActiveManager excludes inactive records when is_active exists."""
        queryset = TestModel.objects.all()
        self.assertIn(self.active_instance, queryset)
        self.assertNotIn(self.inactive_instance, queryset)

    def test_active_manager_without_is_active(self):
        """Test ActiveManager with model lacking is_active field."""
        queryset = TestModelWithoutIsActive.objects.all()
        self.assertIn(self.model_without_is_active, queryset)
        self.assertNotIn(self.deleted_no_is_active, queryset)

    def test_active_manager_queryset_count(self):
        """Test correct count of active records."""
        self.assertEqual(TestModel.objects.count(), 1)  # Only active_instance should be counted
        self.assertEqual(TestModelWithoutIsActive.objects.count(), 1)  # Only model_without_is_active

    def test_all_objects_including_deleted(self):
        """Test that default manager includes all records."""
        all_objects = TestModel.all_objects.all()  # Use all_objects manager
        self.assertIn(self.active_instance, all_objects)
        self.assertIn(self.inactive_instance, all_objects)
        self.assertIn(self.deleted_instance, all_objects)
