import json
import logging
import random
import time
import uuid
from collections import Counter
from datetime import timedelta, date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from teamcentral.models import (
    Department,
    Role,
    EmploymentStatus,
    EmployeeType,
    LeaveType,
    LeaveBalance,
    Address,
)
from users.models import Employee

logger = logging.getLogger("data_sync")


ROLE_CODES = {
    "CEO": "Chief Executive Officer",
    "DJGO": "Django Superuser",
    "CFO": "Chief Financial Officer",
    "FMGR": "Finance Manager",
    "AMGR": "Accounts Payable Manager",
    "ASPC": "Accounts Payable Specialist",
    "RMGR": "Accounts Receivable Manager",
    "RSPC": "Accounts Receivable Specialist",
    "ADIR": "Audit Director",
    "AUDT": "Auditor",
    "TDIR": "Tax Director",
    "TAX": "Tax Analyst",
    "RDIR": "Risk Director",
    "RISK": "Risk Analyst",
    "IDIR": "Investment Director",
    "INV": "Investment Analyst",
    "CDIR": "Compliance Director",
    "COFF": "Compliance Officer",
    "TMGR": "Trading Manager",
    "TRAD": "Trader",
    "CFDR": "Corporate Finance Director",
    "CFAN": "Corporate Finance Analyst",
    "YMGR": "Treasury Manager",
    "TRY": "Treasury Analyst",
    "PMGR": "Reporting Manager",
    "RPT": "Reporting Analyst",
    "CMGR": "Credit Manager",
    "CRD": "Credit Analyst",
    "MDIR": "M&A Director",
    "MNA": "M&A Analyst",
    "SYS": "System User",
}

DEPARTMENT_CODES = {
    "FIN": "Finance",
    "AP": "Accounts Payable",
    "AR": "Accounts Receivable",
    "AUD": "Audit",
    "TAX": "Tax",
    "INV": "Investment",
}


class Command(BaseCommand):
    help = """
    Enterprise Employee Generator

    Features:
    - Auto master-data creation
    - Per-department employee ranges
    - Bulk optimized inserts
    - Optional JSON export
    - Script duration guard
    - Detailed summary report
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--department",
            type=str,
            help="Department code to generate users for (e.g., FIN)"
        )

        parser.add_argument(
            "--all",
            action="store_true",
            help="Generate users for all departments"
        )

        parser.add_argument(
            "--country",
            type=str,
            default="IN",
            help="Country code for Faker locale (default: IN)"
        )

        parser.add_argument(
            "--maxcount",
            type=int,
            default=10,
            help="Maximum number of employees per department (default: 5)"
        )

        parser.add_argument(
            "--mincount",
            type=int,
            default=5,
            help="Minimum employees per department (default: 1)"
        )

        parser.add_argument(
            "--skipjson",
            action="store_true",
            default=True,
            help="Skip JSON generation and directly save to database"
        )

        parser.add_argument(
            "--scriptduration",
            type=int,
            default=172800,
            help="Maximum script runtime in seconds (default: 172800)"
        )

        # New argument for batch size
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for bulk create operations (default: 100)"
        )

        # New argument to limit number of departments processed
        parser.add_argument(
            "--departments-limit",
            type=int,
            default=None,
            help="Limit number of departments to process (default: None)"
        )

    def ensure_master_data(self):
        for rank, (code, title) in enumerate(ROLE_CODES.items()):
            Role.all_objects.get_or_create(code=code, defaults={"title": title, "rank": rank})

        for code, name in DEPARTMENT_CODES.items():
            Department.all_objects.get_or_create(code=code, defaults={"name": name})

        EmploymentStatus.all_objects.get_or_create(code="ACTV", defaults={"name": "Active"})
        EmployeeType.all_objects.get_or_create(code="FT", defaults={"name": "Full-Time"})
        LeaveType.all_objects.get_or_create(code="ANUL", defaults={"name": "Annual Leave", "default_balance": 120})

    def generate_employee(self, dept, roles, status, emp_type, leave_type):
        role = random.choice(roles)
        employee = Employee(
            username=f"user_{uuid.uuid4().hex[:8]}",
            email=f"{uuid.uuid4().hex[:8]}@djangoplay.com",
            password=make_password("default_password_123"),
            department=dept,
            role=role,
            employment_status=status,
            employee_type=emp_type,
            hire_date=timezone.now().date() - timedelta(days=random.randint(30, 1000)),
            approval_limit=Decimal("9999999.99"),
            salary=Decimal(random.randint(50000, 250000)),
            is_active=True,
            is_verified=True,
            employee_code=f"DJP{uuid.uuid4().hex[:10].upper()}",
        )
        return employee

    def handle(self, *args, **options):
        start_time = time.time()
        self.ensure_master_data()
        faker = Faker("en_IN" if options["country"] == "IN" else "en_US")

        maxcount = options["maxcount"]
        mincount = options["mincount"]
        script_limit = options["scriptduration"]
        skipjson = options["skipjson"]
        batch_size = options["batch_size"]
        departments_limit = options["departments_limit"]

        if options["department"] and not options["all"]:
            departments = Department.objects.filter(code=options["department"].upper())
        else:
            departments = Department.objects.all()[:departments_limit] if departments_limit else Department.objects.all()

        roles = list(Role.objects.all())
        status = EmploymentStatus.objects.get(code="ACTV")
        emp_type = EmployeeType.objects.get(code="FT")
        leave_type = LeaveType.objects.first()

        summary = Counter()
        json_output = []

        self.stdout.write(self.style.WARNING("🚀 Starting generation..."))

        for dept in departments:
            dept_count = random.randint(mincount, maxcount)

            self.stdout.write(f"\nDepartment {dept.code} → Generating {dept_count} employees")

            employees_buffer = []
            addresses_buffer = []
            leave_buffer = []

            for _ in range(dept_count):
                if time.time() - start_time > script_limit:
                    self.stdout.write(self.style.ERROR("⏱ Script duration exceeded. Stopping safely."))
                    break

                employee = self.generate_employee(dept, roles, status, emp_type, leave_type)
                employees_buffer.append(employee)

                summary["employees"] += 1
                summary[f"dept_{dept.code}"] += 1
                summary[f"role_{employee.role.code}"] += 1

                json_output.append({
                    "username": employee.username,
                    "department": dept.code,
                    "role": employee.role.code,
                })

            # Bulk insert employees
            with transaction.atomic():
                created = Employee.objects.bulk_create(employees_buffer, batch_size=batch_size)

                for emp in created:
                    addresses_buffer.append(Address(
                        owner=emp,
                        address=faker.street_address(),
                        address_type="CURRENT",
                        country="India",
                        city=faker.city(),
                        state=faker.state(),
                        postal_code=faker.postcode(),
                    ))

                    leave_buffer.append(LeaveBalance(
                        employee=emp,
                        leave_type=leave_type,
                        year=timezone.now().year,
                        balance=Decimal("120"),
                        used=Decimal("0"),
                        reset_date=date(timezone.now().year, 1, 1),
                    ))

                Address.objects.bulk_create(addresses_buffer, batch_size=batch_size)
                LeaveBalance.objects.bulk_create(leave_buffer, batch_size=batch_size)

        if not skipjson:
            output_path = Path("generated_users.json")
            with open(output_path, "w") as f:
                json.dump(json_output, f, indent=4)
            self.stdout.write(self.style.SUCCESS(f"\n📁 JSON exported to {output_path}"))

        elapsed = time.time() - start_time

        # Output summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 GENERATION SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total Employees Created: {summary['employees']}")
        self.stdout.write(f"Execution Time: {elapsed:.2f} seconds\n")

        self.stdout.write("Department Distribution:")
        for key, value in summary.items():
            if key.startswith("dept_"):
                self.stdout.write(f"  {key.replace('dept_', '')}: {value}")

        self.stdout.write("\nRole Distribution:")
        for key, value in summary.items():
            if key.startswith("role_"):
                self.stdout.write(f"  {key.replace('role_', '')}: {value}")

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Completed Successfully"))


# import json
# import logging
# import random
# import time
# from datetime import date, timedelta
# from decimal import Decimal
# from pathlib import Path

# from django.contrib.auth import get_user_model
# from django.core.exceptions import ObjectDoesNotExist, ValidationError
# from django.core.management.base import BaseCommand
# from django.db import transaction
# from django.db.models import Max
# from django.utils import timezone
# from faker import Faker
# from teamcentral.models import Address, Department, EmployeeType, EmploymentStatus, LeaveApplication, LeaveBalance, LeaveType, Role, Team
# from users.models import Employee
# from utilities.utils.data_sync.load_env_and_paths import load_env_paths

# logger = logging.getLogger('data_sync')

# class Command(BaseCommand):
#     help = """
#         Generate and import user-related data (employees, addresses, teams, leave applications, and leave balances)
#         for specified department or all departments in the database to JSON in EMPLOYEES_JSON directory or directly to database.
#         Expected .env keys: EMPLOYEES_JSON
#         Example usage:
#             ./manage.py generate_import_users --department FIN
#             ./manage.py generate_import_users --all --country IN
#             ./manage.py generate_import_users --skipjson
#         JSON files are generated in EMPLOYEES_JSON/{department_code}/{department_code}.json unless --skipjson is provided.
#     """

#     def add_arguments(self, parser):
        # parser.add_argument('--department', type=str, help='Department code to generate users for (e.g., FIN)')
        # parser.add_argument('--all', action='store_true', help='Generate users for all departments')
        # parser.add_argument('--country', type=str, default='IN', help='Country code for data generation (e.g., IN) (default: IN)')
        # parser.add_argument('--maxcount', type=int, default=5, help='Maximum number of employees per department (default: 5)')
        # parser.add_argument('--mincount', type=int, default=1, help='Minimum number of employees per department if maxcount=2')
        # parser.add_argument('--skipjson', action='store_true', help='Skip generating JSON and directly save to database', default=True)
        # parser.add_argument('--scriptduration', type=int, default=172800, help='Maximum script duration in seconds (default: 172800)')

#     def generate_username(self, first_name, last_name):
#         """Generate a unique username based on first and last name."""
#         return f"{first_name.lower()}.{last_name.lower()}{random.randint(100, 999)}"

#     def generate_phone_number(self, country_phone_code):
#         """Generate a phone number with the country code."""
#         return f"{country_phone_code}{random.randint(9000000000, 9999999999)}"

#     def generate_postal_code(self, country_code):
#         """Generate a postal code based on country code."""
#         if country_code == 'IN':
#             return f"{random.randint(100000, 999999)}"
#         return f"{random.randint(10000, 99999)}"  # Generic fallback for other countries

#     def get_manager_for_role(self, role, department, employees):
#         """Determine the appropriate manager for an employee based on their role."""
#         # Define role-to-manager mapping based on ROLE_CODES
#         role_manager_map = {
#             'ASPC': 'AMGR',  # Accounts Payable Specialist -> Accounts Payable Manager
#             'RSPC': 'RMGR',  # Accounts Receivable Specialist -> Accounts Receivable Manager
#             'AUDT': 'ADIR',  # Auditor -> Audit Director
#             'TAX': 'TDIR',   # Tax Analyst -> Tax Director
#             'RISK': 'RDIR',  # Risk Analyst -> Risk Director
#             'INV': 'IDIR',   # Investment Analyst -> Investment Director
#             'COFF': 'CDIR',  # Compliance Officer -> Compliance Director
#             'TRAD': 'TMGR',  # Trader -> Trading Manager
#             'CFAN': 'CFDR',  # Corporate Finance Analyst -> Corporate Finance Director
#             'TRY': 'YMGR',   # Treasury Analyst -> Treasury Manager
#             'RPT': 'PMGR',   # Reporting Analyst -> Reporting Manager
#             'CRD': 'CMGR',   # Credit Analyst -> Credit Manager
#             'MNA': 'MDIR',   # M&A Analyst -> M&A Director
#             # Directors and managers report to CFO or DJGO
#             'FMGR': ['CFO', 'DJGO'],
#             'AMGR': ['CFO', 'DJGO'],
#             'RMGR': ['CFO', 'DJGO'],
#             'ADIR': ['CFO', 'DJGO'],
#             'TDIR': ['CFO', 'DJGO'],
#             'RDIR': ['CFO', 'DJGO'],
#             'IDIR': ['CFO', 'DJGO'],
#             'CDIR': ['CFO', 'DJGO'],
#             'TMGR': ['CFO', 'DJGO'],
#             'CFDR': ['CFO', 'DJGO'],
#             'YMGR': ['CFO', 'DJGO'],
#             'PMGR': ['CFO', 'DJGO'],
#             'CMGR': ['CFO', 'DJGO'],
#             'MDIR': ['CFO', 'DJGO'],
#             # CFO and DJGO report to CEO
#             'CFO': 'CEO',
#             'DJGO': 'CEO',
#             # SYS reports to DJGO
#             'SYS': 'DJGO',
#             # CEO and SSO have no manager
#             'CEO': None,
#             'SSO': None
#         }

#         manager_role_code = role_manager_map.get(role.code)
#         if not manager_role_code:
#             return None

#         # Handle cases where manager_role_code is a list (e.g., directors)
#         if isinstance(manager_role_code, list):
#             for code in manager_role_code:
#                 manager = Employee.objects.filter(department=department, role__code=code, is_active=True).first()
#                 if manager:
#                     return manager
#             return None

#         # Handle single manager role code
#         return Employee.objects.filter(department=department, role__code=manager_role_code, is_active=True).first()

#     def generate_employee(self, country_data: dict, faker: Faker, index: int, department, roles, employment_statuses, employee_types, employees):
#         """Generate a single employee record."""
#         first_name = faker.first_name()
#         last_name = faker.last_name()
#         city = faker.city()
#         # Select the specific role passed (for prioritized creation)
#         role = roles[0] if roles else random.choice(list(Role.objects.filter(is_active=True)))
#         employment_status = random.choice(list(employment_statuses))
#         employee_type = random.choice(list(employee_types))
#         # Get manager based on role and department
#         manager = self.get_manager_for_role(role, department, employees)

#         return {
#             "username": self.generate_username(first_name, last_name),
#             "email": f"{first_name.lower()}.{last_name.lower()}@djangoplay.com",
#             "first_name": first_name,
#             "last_name": last_name,
#             "phone_number": self.generate_phone_number(country_data["country_phone_code"]),
#             "country": country_data["name"],
#             "region": country_data["region"],
#             "manager": manager,
#             "approval_limit": Decimal(str(round(random.uniform(100000, 99999999.99), 2))),
#             "department": department,
#             "job_title": role.title,
#             "role": role,
#             "hire_date": (timezone.now().date() - timedelta(days=random.randint(30, 1000))).isoformat(),
#             "termination_date": None,
#             "employment_status": employment_status,
#             "employee_type": employee_type,
#             "salary": Decimal(str(round(random.uniform(50000, 250000), 2))),
#             "address_display": f"{country_data['name']}, {country_data['region']}, {city}",
#             "avatar": None,
#             "address": {
#                 "address": f"{random.randint(1, 999)} {faker.street_name()}, {city}",
#                 "country": country_data["name"],
#                 "state": city,
#                 "city": city,
#                 "postal_code": self.generate_postal_code(country_data["country_code"]),
#                 "address_type": "CURRENT",  # or "PERMANENT"
#                 "emergency_contact": (
#                     f"{faker.first_name()} {faker.last_name()} "
#                     f"{country_data['country_phone_code']} "
#                     f"{random.randint(9000000000, 9999999999)}"
#                 ),
#             }

#         }

#     def save_employee(self, employee_data, admin_user, country_data, counters, faker):
#         """Save an employee and their address to the database."""
#         address_data = employee_data.pop('address')
#         address = Address(
#             id=counters["address"] + 1,
#             owner=address_data["owner"],
#             address=address_data["address"],
#             country=address_data["country"],
#             state=address_data["state"],
#             city=address_data["city"],
#             postal_code=address_data["postal_code"],
#             address_type=address_data.get("address_type", "CURRENT"),
#             emergency_contact=address_data["emergency_contact"],
#             created_by=admin_user,
#             updated_by=admin_user,
#             created_at=timezone.now(),
#             updated_at=timezone.now(),
#             is_active=True,
#         )

#         try:
#             address.clean()
#             address.save()
#             counters['address'] += 1
#         except ValidationError as e:
#             logger.error(f"Failed to save address for employee {employee_data['username']}: {str(e)}")
#             raise  # Re-raise to skip employee creation if address fails

#         employee_manager = Employee.objects
#         try:
#             with transaction.atomic():
#                 employee = employee_manager.create_user(
#                     username=employee_data['username'],
#                     first_name=employee_data['first_name'],
#                     last_name=employee_data['last_name'],
#                     email=employee_data['email'],
#                     password='default_password_123',  # Default password
#                     address=address,
#                     created_by=admin_user,
#                     department=employee_data['department'],
#                     role=employee_data['role'],
#                     employment_status=employee_data['employment_status'],
#                     employee_type=employee_data['employee_type'],
#                     hire_date=employee_data['hire_date'],
#                     approval_limit=employee_data['approval_limit'],
#                     phone_number=employee_data['phone_number'],
#                     job_title=employee_data['job_title'],
#                     salary=employee_data['salary'],
#                     date_of_birth=faker.date_of_birth(minimum_age=20, maximum_age=60),
#                     national_id=f"{random.randint(10000, 99999)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
#                     emergency_contact_name=faker.first_name() + " " + faker.last_name(),
#                     emergency_contact_phone=self.generate_phone_number(country_data['country_phone_code']),
#                     gender=random.choice(['MALE', 'FEMALE', 'PREFER_NOT_TO_SAY']),
#                     marital_status=random.choice(['SINGLE', 'MARRIED', 'PREFER_NOT_TO_SAY']),
#                     manager=employee_data['manager'],
#                     is_active=True,  # Ensure login capability
#                     is_verified=True,  # Ensure email verification
#                     sso_provider='EMAIL'
#                 )
#                 counters['employee'] += 1
#                 employee_data['employee_code'] = employee.employee_code
#                 employee_data['address_id'] = address.id
#                 employee_data['manager_id'] = employee.manager.id if employee.manager else None
#                 return employee, address, employee_data, address_data
#         except ValidationError as e:
#             logger.error(f"Failed to save employee {employee_data['username']}: {str(e)}")
#             # Delete the address to avoid orphaned records
#             address.delete()
#             raise

#     def generate_team(self, department, admin_user, counters, employees):
#         """Generate a single team for a department with a leader."""
#         # Only create a team if there are employees
#         if not employees:
#             logger.warning(f"No employees available to create team for department {department.code}")
#             return None, None
#         leader = random.choice(list(employees))
#         team_data = {
#             'id': counters['team'] + 1,
#             'name': f"{department.name} Team",  # Consistent name, e.g., "Investment Team"
#             'department': department,
#             'leader': leader,
#             'description': f"Team for {department.name} department",
#             'is_active': True,
#             'created_by': admin_user,
#             'updated_by': admin_user,
#             'created_at': timezone.now().isoformat(),
#             'updated_at': timezone.now().isoformat()
#         }
#         # Check if team already exists for the department
#         team = Team.objects.filter(department=department, name=f"{department.name} Team").first()
#         if not team:
#             team = Team(**team_data)
#             try:
#                 team.clean()
#                 team.save()
#                 counters['team'] += 1
#                 logger.debug(f"Generated team {team.id} for department {department.code}")
#             except ValidationError as e:
#                 logger.error(f"Failed to generate team for department {department.code}: {str(e)}")
#                 raise
#         # Assign all employees to the team
#         for emp in employees:
#             try:
#                 emp.team = team
#                 emp.save()
#             except ValidationError as e:
#                 logger.error(f"Failed to assign employee {emp.employee_code} to team {team.name}: {str(e)}")
#                 continue
#         return team, team_data

#     def generate_leave_balance(self, employee, leave_type, admin_user, counters):
#         """Generate a leave balance for an employee."""
#         year = timezone.now().year
#         leave_balance_data = {
#             'id': counters['leave_balance'] + 1,
#             'employee_id': employee.id,
#             'leave_type_id': leave_type.id,
#             'year': year,
#             'balance': Decimal(str(round(random.uniform(40, 120), 2))),
#             'used': Decimal(str(round(random.uniform(0, 40), 2))),
#             'reset_date': date(year, 1, 1).isoformat(),
#             'created_by_id': admin_user.id,
#             'updated_by_id': admin_user.id,
#             'created_at': timezone.now().isoformat(),
#             'updated_at': timezone.now().isoformat(),
#             'is_active': True
#         }
#         leave_balance = LeaveBalance(
#             id=leave_balance_data['id'],
#             employee=employee,
#             leave_type=leave_type,
#             year=year,
#             balance=leave_balance_data['balance'],
#             used=leave_balance_data['used'],
#             reset_date=date(year, 1, 1),
#             created_by=admin_user,
#             updated_by=admin_user,
#             created_at=timezone.now(),
#             updated_at=timezone.now(),
#             is_active=True
#         )
#         try:
#             leave_balance.clean()
#             leave_balance.save()
#             counters['leave_balance'] += 1
#             logger.debug(f"Generated leave balance {leave_balance.id} for employee {employee.employee_code}")
#             return leave_balance, leave_balance_data
#         except ValidationError as e:
#             logger.error(f"Failed to generate leave balance for employee {employee.employee_code}: {str(e)}")
#             raise

#     def generate_leave_application(self, employee, leave_type, admin_user, counters):
#         """Generate a leave application for an employee."""
#         start_date = timezone.now().date() + timedelta(days=random.randint(1, 30))
#         # Check if manager is an active employee
#         approver = employee.manager if employee.manager and employee.manager.is_active_employee else None
#         leave_application_data = {
#             'id': counters['leave_application'] + 1,
#             'employee_id': employee.id,
#             'leave_type_id': leave_type.id,
#             'start_date': start_date.isoformat(),
#             'end_date': (start_date + timedelta(days=random.randint(1, 5))).isoformat(),
#             'hours': Decimal(str(round(random.uniform(8, 40), 2))),
#             'status': random.choice(['PENDING', 'APPROVED', 'REJECTED']),
#             'approver_id': approver.id if approver else None,
#             'reason': f"Leave request for {leave_type.name}",
#             'created_by_id': admin_user.id,
#             'updated_by_id': admin_user.id,
#             'created_at': timezone.now().isoformat(),
#             'updated_at': timezone.now().isoformat(),
#             'is_active': True
#         }
#         leave_application = LeaveApplication(
#             id=leave_application_data['id'],
#             employee=employee,
#             leave_type=leave_type,
#             start_date=start_date,
#             end_date=date.fromisoformat(leave_application_data['end_date']),
#             hours=leave_application_data['hours'],
#             status=leave_application_data['status'],
#             approver=approver,
#             reason=leave_application_data['reason'],
#             created_by=admin_user,
#             updated_by=admin_user,
#             created_at=timezone.now(),
#             updated_at=timezone.now(),
#             is_active=True
#         )
#         try:
#             leave_application.clean()
#             leave_application.save()
#             counters['leave_application'] += 1
#             logger.debug(f"Generated leave application {leave_application.id} for employee {employee.employee_code}")
#             return leave_application, leave_application_data
#         except ValidationError as e:
#             logger.error(f"Failed to generate leave application for employee {employee.employee_code}: {str(e)}")
#             raise

#     def handle(self, *args, **options):
#         start_time = time.time()
#         User = get_user_model()
#         try:
#             admin_user = User.objects.get(id=1)
#             self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username}"))
#             logger.info(f"Using user: {admin_user.username}")
#         except User.DoesNotExist:
#             self.stderr.write(self.style.ERROR("User with id=1 not found"))
#             logger.error("User with id=1 not found")
#             return

#         stats = {'created': 0, 'skipped': [], 'total': 0}
#         counters = {
#             'employee': Employee.objects.aggregate(Max('id'))['id__max'] or 0,
#             'address': Address.objects.aggregate(Max('id'))['id__max'] or 0,
#             'team': Team.objects.aggregate(Max('id'))['id__max'] or 0,
#             'leave_balance': LeaveBalance.objects.aggregate(Max('id'))['id__max'] or 0,
#             'leave_application': LeaveApplication.objects.aggregate(Max('id'))['id__max'] or 0
#         }

#         script_duration = options['scriptduration']
#         skip_json = options['skipjson']
#         department_code = options.get('department')
#         country_code = options['country'].upper()
#         num_employees_per_dept = random.randint(options['mincount'], options['maxcount']) if options['maxcount'] != 2 else options['maxcount']

#         # Initialize Faker with country-specific locale
#         faker = Faker('en_IN' if country_code == 'IN' else 'en_US')
#         country_data = {
#             'name': 'India' if country_code == 'IN' else 'United States',
#             'region': random.choice(['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu']) if country_code == 'IN' else 'California',
#             'country_code': country_code,
#             'country_phone_code': '+91' if country_code == 'IN' else '+1'
#         }

#         env_data = load_env_paths(env_var='EMPLOYEES_JSON', require_exists=False)
#         employees_path = env_data.get('EMPLOYEES_JSON')
#         if not employees_path and not skip_json:
#             self.stderr.write(self.style.ERROR("EMPLOYEES_JSON not defined in .env"))
#             logger.error("EMPLOYEES_JSON not defined")
#             return

#         if department_code and not options['all']:
#             try:
#                 department = Department.objects.get(code=department_code.upper(), is_active=True)
#                 departments = [department]
#             except ObjectDoesNotExist:
#                 self.stderr.write(self.style.ERROR(f"Department with code {department_code} not found"))
#                 logger.error(f"Department with code {department_code} not found")
#                 return
#         else:
#             departments = Department.objects.filter(is_active=True)
#             if not departments:
#                 self.stderr.write(self.style.ERROR("No active departments found"))
#                 logger.error("No active departments found")
#                 return

#         roles = Role.objects.filter(is_active=True)
#         employment_statuses = EmploymentStatus.objects.filter(is_active=True)
#         employee_types = EmployeeType.objects.filter(is_active=True)
#         leave_types = LeaveType.objects.filter(is_active=True)

#         if not all([roles, employment_statuses, employee_types, leave_types]):
#             self.stderr.write(self.style.ERROR("Required master data (Roles, EmploymentStatus, EmployeeType, or LeaveType) missing"))
#             logger.error("Required master data missing")
#             return

#         json_data = {
#             'employee': [],
#             'address': [],
#             'team': [],
#             'leave_balance': [],
#             'leave_application': []
#         } if not skip_json else None

#         # Define role priority order to ensure managers are created first
#         role_priority = [
#             'CEO', 'CFO', 'DJGO',  # Top-level roles
#             'FMGR', 'AMGR', 'RMGR', 'ADIR', 'TDIR', 'RDIR', 'IDIR', 'CDIR', 'TMGR', 'CFDR', 'YMGR', 'PMGR', 'CMGR', 'MDIR',  # Directors and managers
#             'ASPC', 'RSPC', 'AUDT', 'TAX', 'RISK', 'INV', 'COFF', 'TRAD', 'CFAN', 'TRY', 'RPT', 'CRD', 'MNA',  # Team members
#             'SYS', 'SSO'  # System and social users
#         ]

#         for department in departments:
#             department_code = department.code
#             employees_json = str(Path(employees_path) / department_code / f"{department_code}.json") if not skip_json else None
#             self.stdout.write(f"Generating user data for department: {department.name} ({department_code}) in {country_data['name']}")
#             logger.info(f"Generating user data for department {department.name} ({department_code}) in {country_data['name']}")

#             employee_count = 0
#             department_employees = []
#             # Create employees in role priority order to ensure managers exist
#             for role_code in role_priority:
#                 role = roles.filter(code=role_code).first()
#                 if not role:
#                     continue
#                 # Create at least one employee per role if within maxcount
#                 if employee_count < num_employees_per_dept:
#                     stats['total'] += 1
#                     try:
#                         with transaction.atomic():
#                             # Generate and save employee
#                             employee_data = self.generate_employee(
#                                 country_data, faker, employee_count, department, [role], employment_statuses, employee_types, department_employees
#                             )
#                             employee, address, employee_data, address_data = self.save_employee(employee_data, admin_user, country_data, counters, faker)
#                             department_employees.append(employee)
#                             if not skip_json:
#                                 json_data['employee'].append(employee_data)
#                                 json_data['address'].append(address_data)

#                             # Generate leave balance and application
#                             leave_type = random.choice(list(leave_types))
#                             leave_balance, leave_balance_data = self.generate_leave_balance(employee, leave_type, admin_user, counters)
#                             leave_application, leave_application_data = self.generate_leave_application(employee, leave_type, admin_user, counters)
#                             if not skip_json:
#                                 json_data['leave_balance'].append(leave_balance_data)
#                                 json_data['leave_application'].append(leave_application_data)

#                             stats['created'] += 1
#                             logger.info(f"Successfully generated employee {employee.employee_code} for department {department_code}")
#                             employee_count += 1
#                     except Exception as e:
#                         error_details = {'employee': f"Employee {counters['employee'] + 1}", 'reason': str(e), 'department': department_code}
#                         stats['skipped'].append(error_details)
#                         logger.error(f"Skipping employee generation for {department_code}: {str(e)}", extra={'details': error_details})

#             # Generate team after all employees are created
#             if department_employees:
#                 try:
#                     team, team_data = self.generate_team(department, admin_user, counters, department_employees)
#                     if not skip_json:
#                         json_data['team'].append(team_data)
#                 except Exception as e:
#                     error_details = {'team': f"Team for {department_code}", 'reason': str(e), 'department': department_code}
#                     stats['skipped'].append(error_details)
#                     logger.error(f"Skipping team generation for {department_code}: {str(e)}", extra={'details': error_details})

#             if not skip_json and employees_json:
#                 try:
#                     Path(employees_json).parent.mkdir(parents=True, exist_ok=True)
#                     with open(employees_json, 'w', encoding='utf-8') as f:
#                         json.dump(json_data, f, indent=4, ensure_ascii=False)
#                     self.stdout.write(self.style.SUCCESS(f"Generated JSON at {employees_json}"))
#                     logger.info(f"Generated JSON at {employees_json}")
#                 except Exception as e:
#                     self.stderr.write(self.style.ERROR(f"Error writing JSON for {department_code}: {str(e)}"))
#                     logger.error(f"Error writing JSON for {department_code}: {str(e)}")

#             if time.time() - start_time > script_duration:
#                 self.stderr.write(self.style.WARNING(f"User data generation timeout reached after {script_duration} seconds"))
#                 logger.warning(f"User data generation timeout reached after {script_duration} seconds")
#                 if json_data and employees_json:
#                     try:
#                         Path(employees_json).parent.mkdir(parents=True, exist_ok=True)
#                         with open(employees_json, 'w', encoding='utf-8') as f:
#                             json.dump(json_data, f, indent=4, ensure_ascii=False)
#                         self.stdout.write(self.style.SUCCESS(f"Generated JSON at {employees_json}"))
#                         logger.info(f"Generated JSON at {employees_json}")
#                     except Exception as e:
#                         self.stderr.write(self.style.ERROR(f"Error writing JSON for {department_code}: {str(e)}"))
#                         logger.error(f"Error writing JSON for {department_code}: {str(e)}")
#                 self._print_summary(stats, start_time)
#                 return

#         self._print_summary(stats, start_time)

#     def _print_summary(self, stats, start_time):
#         """Print the generation summary."""
#         elapsed_time = time.time() - start_time
#         self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({elapsed_time:.2f}s)"))
#         self.stdout.write(f" - Total attempted: {stats['total']}")
#         self.stdout.write(f" - Created: {stats['created']}")
#         self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
#         if stats['skipped']:
#             for skipped in stats['skipped'][:5]:
#                 self.stdout.write(f" - {skipped.get('employee', skipped.get('department', skipped.get('team')))}: {skipped['reason']}")
#             if len(stats['skipped']) > 5:
#                 self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
#         self.stdout.write(self.style.SUCCESS(f"Generation Completed in {elapsed_time:.2f}s"))
#         logger.info(f"Generation Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
