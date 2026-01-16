import json
import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from core.utils.redis_client import redis_client
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.phone_number_validations import validate_phone_number

from users.models.employee import Employee
from users.models.leave_application import LeaveApplication
from users.models.leave_balance import LeaveBalance
from users.models.leave_type import LeaveType
from users.models.password_reset_request import PasswordResetRequest
from users.models.team import Team

from ..exceptions import EmployeeValidationError, LeaveValidationError, TeamValidationError

logger = logging.getLogger(__name__)

class EmployeeService:

    """Service layer for Employee, Team, LeaveType, LeaveBalance, and LeaveApplication operations."""

    @staticmethod
    def validate_employee_data(data, instance=None):
        """Validate employee data."""
        errors = {}
        if not data.get('email'):
            errors['email'] = "Email is required."
        if not data.get('username'):
            errors['username'] = "Username is required."
        if data.get('hire_date') and data.get('hire_date') > timezone.now().date():
            errors['hire_date'] = "Hire date cannot be in the future."
        if data.get('termination_date') and data.get('hire_date') and data.get('termination_date') < data.get('hire_date'):
            errors['termination_date'] = "Termination date cannot be before hire date."
        if data.get('salary') and data.get('employee_type') and data.get('employee_type').code == 'INTERN' and data.get('salary') > 0:
            errors['salary'] = "Interns cannot have a salary."
        if data.get('manager') and instance and data.get('manager') == instance:
            errors['manager'] = "Employee cannot be their own manager."
        if data.get('national_id') and not RegexValidator(r'^[A-Z0-9\-]{5,50}$')(data.get('national_id')):
            errors['national_id'] = "Invalid national ID format."
        if data.get('phone_number') and not validate_phone_number(data.get('phone_number')):
            errors['phone_number'] = "Invalid phone number format."
        if data.get('emergency_contact_phone') and not validate_phone_number(data.get('emergency_contact_phone')):
            errors['emergency_contact_phone'] = "Invalid emergency contact phone format."
        if errors:
            logger.error(f"Validation failed for employee data {data.get('email', 'unknown')}: {errors}")
            raise EmployeeValidationError(errors, code="invalid_fields")
        return normalize_text(data.get('first_name', '')), normalize_text(data.get('last_name', '')), normalize_text(data.get('email', ''))

    @staticmethod
    @transaction.atomic
    def create_employee(data, created_by):
        """Create a new employee."""
        logger.info(f"Creating employee: email={data.get('email')}, created_by={created_by}")
        first_name, last_name, email = EmployeeService.validate_employee_data(data)
        try:
            employee = Employee.objects.create_user(
                username=data.get('username'),
                email=email,
                password=data.get('password'),  # None for SSO users
                first_name=first_name,
                last_name=last_name,
                department=data.get('department'),
                role=data.get('role'),
                team=data.get('team', None),
                phone_number=data.get('phone_number', ''),
                job_title=data.get('job_title', ''),
                address=data.get('address', None),
                approval_limit=data.get('approval_limit', 0.00),
                manager=data.get('manager', None),
                hire_date=data.get('hire_date', None),
                employment_status=data.get('employment_status'),
                employee_type=data.get('employee_type'),
                salary=data.get('salary', None),
                date_of_birth=data.get('date_of_birth', None),
                national_id=data.get('national_id', ''),
                emergency_contact_name=data.get('emergency_contact_name', ''),
                emergency_contact_phone=data.get('emergency_contact_phone', ''),
                probation_end_date=data.get('probation_end_date', None),
                contract_end_date=data.get('contract_end_date', None),
                gender=data.get('gender', ''),
                marital_status=data.get('marital_status', ''),
                bank_details=data.get('bank_details', None),
                notes=data.get('notes', ''),
                sso_id=data.get('sso_id', ''),
                sso_provider=data.get('sso_provider', 'EMAIL'),  # Matches Employee model default
                is_active=data.get('is_active', True),
                is_verified=data.get('is_verified', False),  # Default False for verification
                is_superuser=data.get('is_superuser', False),
                created_by=created_by,
                updated_by=created_by
            )
            logger.info(f"Employee created: {employee.employee_code}")
            return employee
        except Exception as e:
            logger.error(f"Failed to create employee for {email}: {str(e)}")
            raise EmployeeValidationError(
                f"Failed to create employee: {str(e)}",
                code="employee_creation_failed",
                details={"error": str(e)}
            )

    @staticmethod
    @transaction.atomic
    def update_employee(employee, data, updated_by):
        """Update an existing employee."""
        logger.info(f"Updating employee: {employee.employee_code}, updated_by={updated_by}")
        first_name, last_name, email = EmployeeService.validate_employee_data(data, employee)
        for field, value in data.items():
            if field in ['first_name', 'last_name', 'email']:
                value = locals()[field]
            setattr(employee, field, value)
        employee.updated_by = updated_by
        employee.updated_at = timezone.now()
        employee.address_display = str(employee.address) if employee.address else 'No address'
        try:
            employee.save(user=updated_by)
            logger.info(f"Employee updated: {employee.employee_code}")
            return employee
        except Exception as e:
            logger.error(f"Failed to update employee {employee.employee_code}: {str(e)}")
            raise EmployeeValidationError(
                f"Failed to update employee: {str(e)}",
                code="employee_update_failed",
                details={"error": str(e)}
            )

    @staticmethod
    def validate_team_data(data, instance=None):
        """Validate team data."""
        errors = {}
        if not data.get('name'):
            errors['name'] = "Name is required."
        if not data.get('department'):
            errors['department'] = "Department is required."
        if data.get('leader') and data.get('department') and data.get('leader').department != data.get('department'):
            errors['leader'] = "Leader must be in the same department."
        if data.get('name') and data.get('department') and Team.objects.filter(
            name=data.get('name'), department=data.get('department'), deleted_at__isnull=True
        ).exclude(pk=instance.pk if instance else None).exists():
            errors['name'] = "Team name already exists in this department."
        if errors:
            raise TeamValidationError(errors, code="invalid_fields")
        return normalize_text(data.get('name', ''))

    @staticmethod
    @transaction.atomic
    def create_team(data, created_by):
        """Create a new team."""
        logger.info(f"Creating team: name={data.get('name')}, created_by={created_by}")
        name = EmployeeService.validate_team_data(data)
        try:
            team = Team(
                name=name,
                department=data.get('department'),
                leader=data.get('leader'),
                description=data.get('description', ''),
                created_by=created_by
            )
            team.save(user=created_by)
            redis_client.setex(f"team:{team.id}:data", 24 * 3600, json.dumps({
                'name': team.name,
                'department': team.department.code
            }))
            logger.info(f"Team created: {team.name}")
            return team
        except Exception as e:
            logger.error(f"Failed to create team: {str(e)}")
            raise TeamValidationError(
                f"Failed to create team: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    @transaction.atomic
    def update_team(team, data, updated_by):
        """Update an existing team."""
        logger.info(f"Updating team: {team.name}, updated_by={updated_by}")
        name = EmployeeService.validate_team_data(data, team)
        for field, value in data.items():
            if field == 'name':
                value = name
            setattr(team, field, value)
        team.updated_by = updated_by
        team.updated_at = timezone.now()
        try:
            team.save(user=updated_by)
            redis_client.setex(f"team:{team.id}:data", 24 * 3600, json.dumps({
                'name': team.name,
                'department': team.department.code
            }))
            logger.info(f"Team updated: {team.name}")
            return team
        except Exception as e:
            logger.error(f"Failed to update team {team.name}: {str(e)}")
            raise TeamValidationError(
                f"Failed to update team: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    def validate_leave_type_data(data, instance=None):
        """Validate leave type data."""
        errors = {}
        if not data.get('code'):
            errors['code'] = "Code is required."
        if not data.get('name'):
            errors['name'] = "Name is required."
        if data.get('default_balance') and data.get('default_balance') < 0:
            errors['default_balance'] = "Default balance cannot be negative."
        if data.get('code') and LeaveType.objects.filter(code=data.get('code'), deleted_at__isnull=True).exclude(pk=instance.pk if instance else None).exists():
            errors['code'] = "Leave type code already exists."
        if errors:
            raise LeaveValidationError(errors, code="invalid_leave_type")
        return normalize_text(data.get('name', ''))

    @staticmethod
    @transaction.atomic
    def create_leave_type(data, created_by):
        """Create a new leave type."""
        logger.info(f"Creating leave type: code={data.get('code')}, created_by={created_by}")
        name = EmployeeService.validate_leave_type_data(data)
        try:
            leave_type = LeaveType(
                code=data.get('code'),
                name=name,
                default_balance=data.get('default_balance', 0.00),
                created_by=created_by
            )
            leave_type.save(user=created_by)
            logger.info(f"LeaveType created: {leave_type.code}")
            return leave_type
        except Exception as e:
            logger.error(f"Failed to create leave type: {str(e)}")
            raise LeaveValidationError(
                f"Failed to create leave type: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    def validate_leave_balance_data(data, instance=None):
        """Validate leave balance data."""
        errors = {}
        if not data.get('employee'):
            errors['employee'] = "Employee is required."
        if not data.get('leave_type'):
            errors['leave_type'] = "Leave type is required."
        if not data.get('year'):
            errors['year'] = "Year is required."
        if data.get('year') and data.get('year') > timezone.now().year + 1:
            errors['year'] = "Year cannot be more than one year in the future."
        if data.get('balance') and data.get('balance') < 0:
            errors['balance'] = "Balance cannot be negative."
        if data.get('used') and data.get('used') < 0:
            errors['used'] = "Used cannot be negative."
        if data.get('balance') and data.get('used') and data.get('balance') < data.get('used'):
            errors['balance'] = "Used cannot exceed balance."
        if data.get('reset_date') and data.get('year') and data.get('reset_date').year != data.get('year'):
            errors['reset_date'] = "Reset date must be in the same year."
        if data.get('employee') and data.get('leave_type') and data.get('year') and LeaveBalance.objects.filter(
            employee=data.get('employee'), leave_type=data.get('leave_type'), year=data.get('year'), deleted_at__isnull=True
        ).exclude(pk=instance.pk if instance else None).exists():
            errors['unique'] = "Leave balance already exists for this employee, leave type, and year."
        if errors:
            raise LeaveValidationError(errors, code="invalid_leave_balance")
        return data

    @staticmethod
    @transaction.atomic
    def allocate_leave_balance(employee, leave_type, year, balance, reset_date, created_by):
        """Allocate leave balance for an employee."""
        logger.info(f"Allocating leave balance: employee={employee.employee_code}, leave_type={leave_type.code}, year={year}")
        cache_key = f"leave:balance:{employee.id}:{leave_type.id}:{year}"
        cached_balance = redis_client.get(cache_key)
        if cached_balance:
            cached_data = json.loads(cached_balance)
            if cached_data['balance'] == str(balance) and cached_data['reset_date'] == str(reset_date):
                logger.info(f"Leave balance already allocated: {cache_key}")
                return LeaveBalance.objects.get(employee=employee, leave_type=leave_type, year=year)

        data = {
            'employee': employee,
            'leave_type': leave_type,
            'year': year,
            'balance': balance,
            'used': 0.00,
            'reset_date': reset_date
        }
        EmployeeService.validate_leave_balance_data(data)
        try:
            leave_balance = LeaveBalance(
                employee=employee,
                leave_type=leave_type,
                year=year,
                balance=balance,
                used=0.00,
                reset_date=reset_date,
                created_by=created_by
            )
            leave_balance.save(user=created_by)
            redis_client.setex(cache_key, 365 * 24 * 3600, json.dumps({
                'balance': str(leave_balance.balance),
                'used': str(leave_balance.used),
                'reset_date': str(leave_balance.reset_date)
            }))
            logger.info(f"Leave balance allocated: {leave_balance}")
            return leave_balance
        except Exception as e:
            logger.error(f"Failed to allocate leave balance: {str(e)}")
            raise LeaveValidationError(
                f"Failed to allocate leave balance: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    @shared_task
    def allocate_yearly_leave_balances():
        """Celery task to allocate leave balances yearly."""
        logger.info("Starting yearly leave balance allocation")
        current_year = timezone.now().year
        employees = Employee.objects.filter(employment_status__code='ACTIVE', deleted_at__isnull=True)
        leave_types = LeaveType.objects.filter(deleted_at__isnull=True)
        for employee in employees:
            for leave_type in leave_types:
                reset_date = leave_type.reset_date or timezone.datetime(current_year, 1, 1).date()
                EmployeeService.allocate_leave_balance(
                    employee=employee,
                    leave_type=leave_type,
                    year=current_year,
                    balance=leave_type.default_balance,
                    reset_date=reset_date,
                    created_by=None
                )
        logger.info("Yearly leave balance allocation completed")

    @staticmethod
    def validate_leave_application_data(data, instance=None):
        """Validate leave application data."""
        errors = {}
        if not data.get('employee'):
            errors['employee'] = "Employee is required."
        if not data.get('leave_type'):
            errors['leave_type'] = "Leave type is required."
        if not data.get('start_date'):
            errors['start_date'] = "Start date is required."
        if data.get('end_date') and data.get('start_date') and data.get('end_date') < data.get('start_date'):
            errors['end_date'] = "End date must be after start date."
        if data.get('hours') and data.get('hours') <= 0:
            errors['hours'] = "Hours must be positive."
        if data.get('hours') and data.get('end_date'):
            errors['hours'] = "Cannot specify both hours and end date."
        if data.get('approver') and not data.get('approver').is_active_employee:
            errors['approver'] = "Approver must be an active employee."
        if data.get('employee') and data.get('leave_type') and data.get('start_date'):
            cache_key = f"leave:balance:{data.get('employee').id}:{data.get('leave_type').id}:{data.get('start_date').year}"
            cached_balance = redis_client.get(cache_key)
            if cached_balance:
                balance_data = json.loads(cached_balance)
                available = Decimal(balance_data['balance']) - Decimal(balance_data['used'])
                hours = data.get('hours') or (data.get('end_date') - data.get('start_date')).days * 8
                if available < hours:
                    errors['balance'] = "Insufficient leave balance."
            else:
                balance = LeaveBalance.objects.filter(
                    employee=data.get('employee'),
                    leave_type=data.get('leave_type'),
                    year=data.get('start_date').year,
                    deleted_at__isnull=True
                ).first()
                if balance and balance.balance - balance.used < (data.get('hours') or (data.get('end_date') - data.get('start_date')).days * 8):
                    errors['balance'] = "Insufficient leave balance."
        if errors:
            raise LeaveValidationError(errors, code="invalid_leave_application")
        return data

    @staticmethod
    @transaction.atomic
    def create_leave_application(data, created_by):
        """Create a new leave application."""
        logger.info(f"Creating leave application: employee={data.get('employee').employee_code}")
        data = EmployeeService.validate_leave_application_data(data)
        try:
            leave_application = LeaveApplication(
                employee=data.get('employee'),
                leave_type=data.get('leave_type'),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                hours=data.get('hours'),
                status=data.get('status', 'PENDING'),
                approver=data.get('approver'),
                reason=data.get('reason', ''),
                created_by=created_by
            )
            leave_application.save(user=created_by)
            logger.info(f"Leave application created: {leave_application}")
            return leave_application
        except Exception as e:
            logger.error(f"Failed to create leave application: {str(e)}")
            raise LeaveValidationError(
                f"Failed to create leave application: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    @transaction.atomic
    def approve_leave_application(application, approver):
        """Approve a leave application and update balance."""
        logger.info(f"Approving leave application: {application}, approver={approver.employee_code}")
        if application.status != 'PENDING':
            raise LeaveValidationError(
                "Only pending applications can be approved.",
                code="invalid_leave_application",
                details={"application_id": application.pk}
            )
        cache_key = f"leave:balance:{application.employee.id}:{application.leave_type.id}:{application.start_date.year}"
        cached_balance = redis_client.get(cache_key)
        hours = application.hours or (application.end_date - application.start_date).days * 8
        if cached_balance:
            balance_data = json.loads(cached_balance)
            available = Decimal(balance_data['balance']) - Decimal(balance_data['used'])
            if available < hours:
                raise LeaveValidationError(
                    "Insufficient leave balance.",
                    code="insufficient_balance",
                    details={"application_id": application.pk}
                )
        balance = LeaveBalance.objects.filter(
            employee=application.employee,
            leave_type=application.leave_type,
            year=application.start_date.year,
            deleted_at__isnull=True
        ).first()
        if balance and balance.balance - balance.used < hours:
            raise LeaveValidationError(
                "Insufficient leave balance.",
                code="insufficient_balance",
                details={"application_id": application.pk}
            )
        try:
            balance.used += Decimal(hours)
            balance.save(user=approver)
            application.status = 'APPROVED'
            application.approver = approver
            application.save(user=approver)
            redis_client.setex(cache_key, 365 * 24 * 3600, json.dumps({
                'balance': str(balance.balance),
                'used': str(balance.used),
                'reset_date': str(balance.reset_date)
            }))
            logger.info(f"Leave application approved: {application}")
            return application
        except Exception as e:
            logger.error(f"Failed to approve leave application {application}: {str(e)}")
            raise LeaveValidationError(
                f"Failed to approve leave application: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    def is_duplicate_email(email, exclude_pk=None):
        """Check if email already exists."""
        return Employee.objects.filter(email__iexact=email, deleted_at__isnull=True).exclude(pk=exclude_pk).exists()

    @staticmethod
    def is_duplicate_employee_code(employee_code, exclude_pk=None):
        """Check if employee code already exists."""
        return Employee.objects.filter(employee_code__iexact=employee_code, deleted_at__isnull=True).exclude(pk=exclude_pk).exists()

    @staticmethod
    def is_duplicate_balance(employee, leave_type, year, exclude_pk=None):
        """Check if leave balance already exists for employee, leave type, and year."""
        return LeaveBalance.objects.filter(
            employee=employee, leave_type=leave_type, year=year, deleted_at__isnull=True
        ).exclude(pk=exclude_pk).exists()

    @staticmethod
    def has_sufficient_balance(employee, leave_type, start_date, end_date):
        """Check if employee has sufficient leave balance."""
        year = start_date.year
        balance = LeaveBalance.objects.filter(
            employee=employee, leave_type=leave_type, year=year, deleted_at__isnull=True
        ).first()
        if not balance:
            return False
        hours = (end_date - start_date).days * 8
        return balance.balance - balance.used >= Decimal(hours)

    @staticmethod
    def validate_password_reset_data(data, instance=None):
        """Validate password reset request data."""
        errors = {}
        if not data.get('user'):
            errors['user'] = "User is required."
        if data.get('expires_at') and data.get('expires_at') < timezone.now():
            errors['expires_at'] = "Expiration time cannot be in the past."
        if data.get('used') and data.get('expires_at') and data.get('expires_at') < timezone.now():
            errors['used'] = "Cannot use expired token."
        if errors:
            raise EmployeeValidationError(errors, code="invalid_password_reset")
        return data

    @staticmethod
    @transaction.atomic
    def create_password_reset_request(user, created_by):
        """Create a new password reset request for an Employee."""
        logger.info(f"Creating password reset request: user={user.email}, created_by={created_by}")
        data = {
            'user': user,
            'expires_at': timezone.now() + timedelta(hours=24),
            'used': False
        }
        EmployeeService.validate_password_reset_data(data)
        try:
            reset_request = PasswordResetRequest(
                user=user,
                expires_at=data['expires_at'],
                used=data['used'],
                created_by=created_by
            )
            reset_request.save(user=created_by)
            from users.services.member import MemberService
            MemberService.send_password_reset_email_to_employee(user, reset_request.token)
            logger.info(f"Password reset request created: {reset_request}")
            return reset_request
        except Exception as e:
            logger.error(f"Failed to create password reset request: {str(e)}")
            raise EmployeeValidationError(
                f"Failed to create password reset request: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )
