import argparse
import json
import logging
import random
import string
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from users.constants import ROLE_CODES
from users.models.address import Address
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Sync user data from a JSON file specified in .env (EMP_DATA).

Expected .env keys:
    DATA_DIR, EMP_DATA

Example usage:
    ./manage.py create_employees                     # Loads employees from EMP_DATA
    ./manage.py create_employees --file custom.json  # Loads from custom file

Expected JSON format: list of user objects with nested `address` object
"""

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--file",
            type=str,
            help="Override EMP_DATA path with a custom JSON file",
        )

    def handle(self, *args, **options):
        start_time = time.time()
        self.options = options
        stats = {'created': 0, 'updated': 0, 'skipped': [], 'total': 0}

        self.stdout.write(f"Starting employee sync... ({time.time() - start_time:.2f}s)")
        logger.info("Starting employee sync")

        # Load environment variables and paths
        json_filename = self.options.get('file')
        env_data = load_env_paths(env_var='EMP_DATA', file=json_filename)
        json_filename = env_data.get('EMP_DATA')

        if not json_filename:
            error_msg = f"Failed to load EMP_DATA path ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        User = get_user_model()
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username} (ID: {admin_user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using user: {admin_user.username}")
        except User.DoesNotExist:
            error_msg = f"User with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                EMP_DATA = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON: {e} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            return
        except Exception as e:
            error_msg = f"Failed to read JSON file: {e} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            return

        stats['total'] = len(EMP_DATA)
        full_name_to_username = {}
        created_employees = {}

        for index, user_data in enumerate(EMP_DATA, 1):
            username = user_data.get('username', 'N/A')
            try:
                hire_date = timezone.datetime.strptime(user_data['hire_date'], "%Y-%m-%d").date() if user_data.get('hire_date') and user_data['hire_date'].strip() else None
                termination_date = timezone.datetime.strptime(user_data['termination_date'], "%Y-%m-%d").date() if user_data.get('termination_date') and user_data['termination_date'].strip() else None

                with transaction.atomic():
                    address_data = user_data.get('address')
                    if not address_data:
                        raise ValidationError("Missing address data")

                    address = Address.objects.create(
                        owner=address_data["owner"],  # must be provided or inferred earlier
                        address=address_data.get("address", ""),
                        country=address_data.get("country", ""),
                        state=address_data.get("state", ""),
                        city=address_data.get("city", ""),
                        postal_code=address_data.get("postal_code", ""),
                        address_type=address_data.get("address_type", "CURRENT"),
                        emergency_contact=address_data.get("emergency_contact", ""),
                        created_by=admin_user,
                        updated_by=admin_user,
                    )


                    role = user_data.get('role', 'FIN_MANAGER')
                    if role not in dict(ROLE_CODES).keys():
                        raise ValidationError(f"Invalid role: {role}")

                    password = self.generate_password()
                    is_staff = username == 'django.superuser' or role.upper() in ['CEO', 'CFO', 'DJANGO']
                    is_superuser = is_staff

                    # Clean phone number
                    phone_number = user_data.get('phone_number', '').strip() if user_data.get('phone_number') else None

                    try:
                        user = User.objects.get(username=username)
                        # Update existing user
                        user.email = user_data['email']
                        user.first_name = user_data['first_name']
                        user.last_name = user_data['last_name']
                        user.phone_number = phone_number
                        user.approval_limit = Decimal(str(user_data.get('approval_limit', '0.00')))
                        user.department = user_data.get('department', 'FIN')
                        user.job_title = user_data.get('job_title', '')
                        user.role = role
                        user.hire_date = hire_date
                        user.termination_date = termination_date
                        user.employment_status = user_data.get('employment_status', 'ACTIVE')
                        user.employee_type = user_data.get('employee_type', 'FULL_TIME')
                        user.salary = Decimal(str(user_data.get('salary', '0.00'))) if user_data.get('employee_type') != 'INTERN' else None
                        user.address = address
                        user.address_display = address_data.get('address_display', str(address))
                        user.avatar = user_data.get('avatar', None)
                        user.is_active = True
                        user.is_staff = is_staff
                        user.is_superuser = is_superuser
                        user.set_password(password)
                        user.save(user=admin_user)
                        created = False
                        stats['updated'] += 1
                    except User.DoesNotExist:
                        # Create new user
                        user = User.objects.create_user(
                            username=username,
                            email=user_data['email'],
                            password=password,
                            address=address,
                            created_by=admin_user,
                            first_name=user_data['first_name'],
                            last_name=user_data['last_name'],
                            phone_number=phone_number,
                            approval_limit=Decimal(str(user_data.get('approval_limit', '0.00'))),
                            department=user_data.get('department', 'FIN'),
                            job_title=user_data.get('job_title', ''),
                            role=role,
                            hire_date=hire_date,
                            termination_date=termination_date,
                            employment_status=user_data.get('employment_status', 'ACTIVE'),
                            employee_type=user_data.get('employee_type', 'FULL_TIME'),
                            salary=Decimal(str(user_data.get('salary', '0.00'))) if user_data.get('employee_type') != 'INTERN' else None,
                            address_display=address_data.get('address_display', str(address)),
                            avatar=user_data.get('avatar', None),
                            is_active=True,
                            is_staff=is_staff,
                            is_superuser=is_superuser
                        )
                        created = True
                        stats['created'] += 1

                    created_employees[username] = user
                    full_name_to_username[f"{user.first_name} {user.last_name}".strip()] = username
                    action = "created" if created else "updated"
                    self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} user: {username} ({time.time() - start_time:.2f}s)"))
                    logger.info(f"{action.capitalize()} user: {username}")

            except (KeyError, ValueError, ValidationError) as e:
                stats['skipped'].append({'username': username, 'index': index, 'reason': str(e)})
                warning_msg = f"Skipping user {username} at index {index}: {e} ({time.time() - start_time:.2f}s)"
                self.stderr.write(self.style.WARNING(warning_msg))
                logger.warning(warning_msg)
                continue

        for data in EMP_DATA:
            username = data.get('username', 'N/A')
            user = created_employees.get(username)
            manager_name = data.get('manager')
            if user and manager_name:
                manager_username = full_name_to_username.get(manager_name.strip())
                if manager_username and manager_username in created_employees:
                    try:
                        user.manager = created_employees[manager_username]
                        user.save(user=admin_user)
                        self.stdout.write(self.style.SUCCESS(f"Assigned manager to {user.username}: {manager_username} ({time.time() - start_time:.2f}s)"))
                        logger.info(f"Assigned manager to {user.username}: {manager_username}")
                    except Exception as e:
                        stats['skipped'].append({'username': username, 'index': EMP_DATA.index(data) + 1, 'reason': f"Failed to assign manager {manager_name}: {e}"})
                        warning_msg = f"Failed to assign manager {manager_name} to {username}: {e} ({time.time() - start_time:.2f}s)"
                        self.stderr.write(self.style.WARNING(warning_msg))
                        logger.warning(warning_msg)

        self.stdout.write(self.style.SUCCESS(f"Employee Syncing summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Employees created: {stats['created']}")
        self.stdout.write(f"  - Employees updated: {stats['updated']}")
        self.stdout.write(f"  - Records skipped: {len(stats['skipped'])}")
        logger.info(f"Employee Syncing summary: Total records={stats['total']}, Created={stats['created']}, Updated={stats['updated']}, Skipped={len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - User: {skipped['username']} (Index: {skipped['index']}): {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        self.stdout.write(self.style.SUCCESS(f"Employees Synced in {time.time() - start_time:.2f}s"))
        logger.info(f"Employees Syn�ာced in {time.time() - start_time:.2f}s")

    def generate_password(self) -> str:
        """Generate a secure password with required character classes."""
        characters = string.ascii_letters + string.digits + string.punctuation
        password = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits),
            random.choice(string.punctuation)
        ]
        password += random.choices(characters, k=12)  # Total length 16
        random.shuffle(password)
        return ''.join(password)
