"""
Management command: create_superuser

Creates a DjangoPlay superuser employee using plaintext credentials
read directly from ~/.dplay/.secrets.

Safe to run multiple times — exits without error if the superuser
already exists.

Usage:
    python manage.py create_superuser
"""

import logging
from pathlib import Path

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Reference data constants.
# These records must exist before the superuser can be created.
# Run bootstrap management commands first if they are missing.
# ------------------------------------------------------------------
ROLE_CODE              = "DJGO"
EMPLOYMENT_STATUS_CODE = "ACTV"
EMPLOYEE_TYPE_CODE     = "FT"
DEPARTMENT_CODE        = "FIN"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _load_secrets() -> dict:
    """
    Parse ~/.dplay/.secrets into a plain dict.

    Values in this file are always plaintext — the file is the
    source of truth for credentials. encrypt_env.py reads from
    here and writes encrypted values into .env. Never the reverse.
    """
    secrets_path = Path.home() / ".dplay" / ".secrets"

    if not secrets_path.exists():
        raise FileNotFoundError(f"~/.dplay/.secrets not found at {secrets_path}")

    values = {}
    with open(secrets_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


class Command(BaseCommand):
    help = "Create a DjangoPlay superuser employee from ~/.dplay/.secrets credentials."

    def handle(self, *args, **options):
        from teamcentral.models import Department, EmployeeType, EmploymentStatus, Role

        Employee = get_user_model()

        # ── Load credentials ──────────────────────────────────────────
        try:
            secrets = _load_secrets()
        except FileNotFoundError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        username = secrets.get("SUPERUSER_USERNAME", "").strip()
        email    = secrets.get("SUPERUSER_EMAIL", "").strip()
        password = secrets.get("SUPERUSER_PASSWORD", "").strip()

        if not all([username, email, password]):
            self.stderr.write(self.style.ERROR(
                "Missing required keys in ~/.dplay/.secrets: "
                "SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD"
            ))
            return

        # ── Guard: already exists ─────────────────────────────────────
        if Employee.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser "{username}" already exists — skipping.'
            ))
            return

        # ── Bootstrap required reference records ──────────────────────
        try:
            role, _ = Role.all_objects.get_or_create(
                code=ROLE_CODE,
                defaults={"title": "Django Superuser", "rank": 0},
            )
            employment_status, _ = EmploymentStatus.objects.get_or_create(
                code=EMPLOYMENT_STATUS_CODE,
                defaults={"name": "Active"},
            )
            employee_type, _ = EmployeeType.all_objects.get_or_create(
                code=EMPLOYEE_TYPE_CODE,
                defaults={"name": "Full-Time"},
            )
            department, _ = Department.all_objects.get_or_create(
                code=DEPARTMENT_CODE,
                defaults={"name": "Finance"},
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f"Failed to bootstrap reference data: {e}\n"
                "Run bootstrap management commands before creating the superuser."
            ))
            return

        # ── Create superuser ──────────────────────────────────────────
        try:
            with transaction.atomic():
                employee = Employee.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name="Django",
                    last_name="Superuser",
                    created_by=None,
                    department=department,
                    role=role,
                    employment_status=employment_status,
                    employee_type=employee_type,
                    hire_date=timezone.now().date(),
                    is_verified=True,
                )

                EmailAddress.objects.create(
                    user=employee,
                    email=employee.email,
                    verified=True,
                    primary=True,
                )

                employee.created_by = employee
                employee.updated_by = employee
                employee.save()

                self.stdout.write(self.style.SUCCESS(
                    f'Superuser "{employee.username}" created successfully.'
                ))
                logger.info(f"Superuser created: {employee.username}")

        except (IntegrityError, ValidationError) as e:
            self.stderr.write(self.style.ERROR(f"Failed to create superuser: {e}"))
            logger.error(f"Failed to create superuser: {e}", exc_info=True)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Unexpected error: {e}"))
            logger.error(f"Unexpected error creating superuser: {e}", exc_info=True)
