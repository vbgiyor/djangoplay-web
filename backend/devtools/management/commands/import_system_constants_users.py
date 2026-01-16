import logging
import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.constants import DEPARTMENT_CODES, EMPLOYEE_TYPE_CODES, EMPLOYMENT_STATUS_CODES, LEAVE_TYPE_CODES, MEMBER_STATUS_CODES, ROLE_CODES
from users.models import Department, EmployeeType, EmploymentStatus, LeaveType, MemberStatus, Role

logger = logging.getLogger(__name__)

class MasterDataCreator:

    """Helper class to manage creation or update of master data records."""

    MODEL_CONFIGS = [
        {
            'model': MemberStatus,
            'constants': MEMBER_STATUS_CODES,
            'code_field': 'code',
            'name_field': 'name',
            'model_name': 'MemberStatus',
        },
        {
            'model': EmploymentStatus,
            'constants': EMPLOYMENT_STATUS_CODES,
            'code_field': 'code',
            'name_field': 'name',
            'model_name': 'EmploymentStatus',
        },
        {
            'model': Role,
            'constants': ROLE_CODES,
            'code_field': 'code',
            'name_field': 'title',
            'model_name': 'Role',
            'extra_defaults': {'rank': 999},
        },
        {
            'model': Department,
            'constants': DEPARTMENT_CODES,
            'code_field': 'code',
            'name_field': 'name',
            'model_name': 'Department',
        },
        {
            'model': EmployeeType,
            'constants': EMPLOYEE_TYPE_CODES,
            'code_field': 'code',
            'name_field': 'name',
            'model_name': 'EmployeeType',
        },
        {
            'model': LeaveType,
            'constants': LEAVE_TYPE_CODES,
            'code_field': 'code',
            'name_field': 'name',
            'model_name': 'LeaveType',
        },

    ]

    def __init__(self, command):
        self.command = command
        self.user = self._get_system_user()
        self.start_time = time.time()

    def _get_system_user(self):
        """Retrieve the system user for audit fields."""
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            logger.info(f"Using employee: {user.username} (ID: {user.id})")
            self.command.stdout.write(self.command.style.SUCCESS(
                f"Using employee: {user.username} (ID: {user.id})"
            ))
            return user
        except Employee.DoesNotExist:
            error_msg = "Employee with id=1 not found. Please ensure a superuser exists."
            logger.error(error_msg)
            self.command.stderr.write(self.command.style.ERROR(error_msg))
            raise ValueError(error_msg)

    def create_or_update_record(self, model, constants, code_field, name_field, model_name, extra_defaults=None):
        """Create or update records for a given model based on constants, respecting model constraints."""
        logger.info(f"Processing {model_name} data creation/update")
        self.command.stdout.write(f"Processing {model_name} data creation/update...")

        created_count = 0
        updated_count = 0
        existing_count = 0
        extra_defaults = extra_defaults or {}

        for code, name in constants.items():
            try:
                defaults = {
                    name_field: name,
                    'created_by': self.user,
                    'updated_by': self.user,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now(),
                    **extra_defaults,
                }
                query = {code_field: code}

                # Check if record exists
                record = model.objects.filter(**query).first()

                if record:
                    # Update existing record if necessary
                    update_needed = False
                    for field, value in defaults.items():
                        current_value = getattr(record, field)
                        if current_value != value:
                            setattr(record, field, value)
                            update_needed = True

                    if update_needed:
                        # Validate model constraints before saving
                        record.clean()
                        record.save()
                        updated_count += 1
                        self.command.stdout.write(self.command.style.SUCCESS(
                            f"Updated {model_name}: {code} - {name}"
                        ))
                        logger.info(f"Updated {model_name}: {code} - {name}")
                    else:
                        existing_count += 1
                        self.command.stdout.write(f"{model_name} unchanged: {code} - {name}")
                        logger.info(f"{model_name} unchanged: {code} - {name}")
                else:
                    # Create new record
                    new_record = model(**query, **defaults)
                    # Validate model constraints before saving
                    new_record.clean()
                    new_record.save()
                    created_count += 1
                    self.command.stdout.write(self.command.style.SUCCESS(
                        f"Created {model_name}: {code} - {name}"
                    ))
                    logger.info(f"Created {model_name}: {code} - {name}")

            except ValidationError as e:
                error_msg = f"Validation error for {model_name} {code}: {str(e)}"
                self.command.stderr.write(self.command.style.ERROR(error_msg))
                logger.error(error_msg, exc_info=True)
                raise
            except Exception as e:
                error_msg = f"Failed to process {model_name} {code}: {str(e)}"
                self.command.stderr.write(self.command.style.ERROR(error_msg))
                logger.error(error_msg, exc_info=True)
                raise

        self._log_summary(model_name, created_count, updated_count, existing_count)

    def _log_summary(self, model_name, created_count, updated_count, existing_count):
        """Log summary for a model's data creation/update."""
        summary = (
            f"{model_name} Processing Summary:\n"
            f"  - Created: {created_count}\n"
            f"  - Updated: {updated_count}\n"
            f"  - Unchanged: {existing_count}"
        )
        self.command.stdout.write(self.command.style.SUCCESS(summary))
        logger.info(
            f"{model_name} Processing Summary: "
            f"Created={created_count}, Updated={updated_count}, Unchanged={existing_count}"
        )

    def run(self):
        """Execute master data creation or update for all configured models."""
        logger.info("Starting master data creation/update from constants")
        self.command.stdout.write(f"Starting master data creation/update... ({time.time() - self.start_time:.2f}s)")

        for config in self.MODEL_CONFIGS:
            try:
                self.create_or_update_record(**config)
            except Exception as e:
                error_msg = f"Error processing {config['model_name']}: {str(e)}"
                self.command.stderr.write(self.command.style.ERROR(error_msg))
                logger.error(error_msg, exc_info=True)
                return

        elapsed_time = time.time() - self.start_time
        self.command.stdout.write(self.command.style.SUCCESS(
            f"Master Data Processing Completed: ({elapsed_time:.2f}s)"
        ))
        logger.info(f"Master Data Processing Completed in {elapsed_time:.2f}s")

class Command(BaseCommand):
    help = """
        Create or update master data records for MemberStatus, EmploymentStatus, Role, Department, and EmployeeType
        based on constants defined in users/constants.py. This command ensures that the database is populated
        with required master data for the application, validating model constraints before saving.

        Requirements:
        - A superuser with ID=1 must exist in the Employee model for audit fields.
        - The constants (MEMBER_STATUS_CODES, EMPLOYMENT_STATUS_CODES, ROLE_CODES, DEPARTMENT_CODES,
          EMPLOYEE_TYPE_CODES) must be defined in users/constants.py.

        Example usage:
        - ./manage.py import_system_constants_users
        - python manage.py import_system_constants_users

        The command will:
        - Retrieve the system user (ID=1) for audit fields.
        - Create or update records for each model based on the corresponding constants.
        - Validate model constraints (e.g., unique fields, required fields) before saving.
        - Log the number of created, updated, and unchanged records for each model.
        - Output a summary of the processing time and results.
    """

    def handle(self, *args, **options):
        """Handle the command execution."""
        creator = MasterDataCreator(self)
        creator.run()
