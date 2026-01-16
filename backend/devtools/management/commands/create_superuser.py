import logging
import os
from pathlib import Path

import environ
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone
from paystream.security.crypto import decrypt_value
from users.models import Department, EmployeeType, EmploymentStatus, Role

logger = logging.getLogger(__name__)

# Constants for superuser creation
ROLE_CODES = {
    'DJGO': 'Django Superuser',  # System superuser with full access
}

EMPLOYMENT_STATUS_CODES = {
    'ACTV': 'Active',  # Currently employed and active
}

EMPLOYEE_TYPE_CODES = {
    'FT': 'Full-Time',  # Full-time system employee
}

DEPARTMENT_CODES = {
    'DIR': 'Board of Directors',  # Department for leadership
}

class Command(BaseCommand):
    help = 'Creates a superuser employee using environment variables or provided arguments.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Superuser username')
        parser.add_argument('--email', type=str, help='Superuser email')
        parser.add_argument('--password', type=str, help='Superuser password')
        parser.add_argument('--first_name', type=str, help='Superuser first name')
        parser.add_argument('--last_name', type=str, help='Superuser last name')

    def handle(self, *args, **options):
        Employee = get_user_model()

        env = environ.Env()
        env_path = Path(__file__).resolve().parent.parent / '.env'
        environ.Env.read_env(env_path, override=True)

        # Get encryption key from env
        encryption_key = env('ENCRYPTION_KEY')
        if not encryption_key:
            self.stderr.write(self.style.ERROR('ENCRYPTION_KEY must be set in .env'))
            return
        key_bytes = encryption_key.encode('utf-8')

        # Get values (command-line args take precedence; else from env, which are encrypted)
        encrypted_username = options.get('username') or os.getenv('SUPERUSER_USERNAME')
        encrypted_email = options.get('email') or os.getenv('SUPERUSER_EMAIL')
        encrypted_password = options.get('password') or os.getenv('SUPERUSER_PASSWORD')
        first_name = options.get('first_name') or os.getenv('SUPERUSER_FIRST_NAME', 'Django')
        last_name = options.get('last_name') or os.getenv('SUPERUSER_LAST_NAME', 'Superuser')

        # Validate required fields
        if not all([encrypted_username, encrypted_email, encrypted_password]):
            error_msg = 'Missing required fields: SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD'
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        # Decrypt values
        try:
            username = decrypt_value(encrypted_username, key_bytes)
            email = decrypt_value(encrypted_email, key_bytes)
            password = decrypt_value(encrypted_password, key_bytes)
        except ValueError as e:
            error_msg = f'Decryption failed: {e}'
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        # Check if employee exists
        if Employee.objects.filter(username=username).exists():
            warning_msg = f'Employee "{username}" already exists.'
            self.stdout.write(self.style.WARNING(warning_msg))
            logger.warning(warning_msg)
            return

        try:
            with transaction.atomic():
                # Create required records
                role, _ = Role.all_objects.get_or_create(
                    code='DJGO',
                    defaults={'title': ROLE_CODES['DJGO'], 'rank': 0}
                )
                logger.info(f"Role 'DJGO' ensured: {role}")

                employment_status, _ = EmploymentStatus.objects.get_or_create(
                    code='ACTV',
                    defaults={'name': EMPLOYMENT_STATUS_CODES['ACTV']}
                )
                logger.info(f"EmploymentStatus 'ACTV' ensured: {employment_status}")

                employee_type, _ = EmployeeType.all_objects.get_or_create(
                    code='FT',
                    defaults={'name': EMPLOYEE_TYPE_CODES['FT']}
                )
                logger.info(f"EmployeeType 'FT' ensured: {employee_type}")

                department, _ = Department.all_objects.get_or_create(
                    code='DIR',
                    defaults={'name': DEPARTMENT_CODES['DIR']}
                )
                logger.info(f"Department 'DIR' ensured: {department}")

                # Create superuser
                employee = Employee.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    created_by=None,
                    department=department,
                    role=role,
                    employment_status=employment_status,
                    employee_type=employee_type,
                    hire_date=timezone.now().date(),
                    is_verified=True  # Set for allauth compatibility
                )

                # Create and verify EmailAddress for allauth
                try:
                    EmailAddress.objects.create(
                        user=employee,
                        email=employee.email,
                        verified=True,
                        primary=True
                    )
                    logger.info("Created and verified an EmailAddress for the superuser.")
                except Exception as e:
                    logger.error(f"Failed to create EmailAddress for superuser: {e}")
                    raise

                # Set created_by and updated_by
                employee.created_by = employee
                employee.updated_by = employee
                employee.save()

                success_msg = f'Employee "{employee.username}" created successfully.'
                self.stdout.write(self.style.SUCCESS(success_msg))
                logger.info(success_msg)

        except (IntegrityError, ValidationError) as e:
            error_msg = f'Failed to create superuser: {e}'
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
        except Exception as e:
            error_msg = f'Unexpected error: {e}'
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
