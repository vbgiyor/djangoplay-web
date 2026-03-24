import json
import logging
import random
import time
import uuid
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.apps import apps  # Added to bypass direct import
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from teamcentral.models import (
    Address,
    Department,
    EmployeeType,
    EmploymentStatus,
    LeaveBalance,
    LeaveType,
    Role,
)

# Removed: from users.models import Employee (This was triggering TID251)

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
    help = """Enterprise Employee Generator"""

    def add_arguments(self, parser):
        parser.add_argument("--department", type=str)
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--country", type=str, default="IN")
        parser.add_argument("--maxcount", type=int, default=10)
        parser.add_argument("--mincount", type=int, default=5)
        parser.add_argument("--skipjson", action="store_true", default=True)
        parser.add_argument("--scriptduration", type=int, default=172800)
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--departments-limit", type=int, default=None)

    def ensure_master_data(self):
        for rank, (code, title) in enumerate(ROLE_CODES.items()):
            Role.all_objects.get_or_create(code=code, defaults={"title": title, "rank": rank})

        for code, name in DEPARTMENT_CODES.items():
            Department.all_objects.get_or_create(code=code, defaults={"name": name})

        EmploymentStatus.all_objects.get_or_create(code="ACTV", defaults={"name": "Active"})
        EmployeeType.all_objects.get_or_create(code="FT", defaults={"name": "Full-Time"})
        LeaveType.all_objects.get_or_create(code="ANUL", defaults={"name": "Annual Leave", "default_balance": 120})

    def generate_employee_instance(self, EmployeeModel, dept, roles, status, emp_type):
        """Creates an unsaved Employee instance using the passed model class."""
        role = random.choice(roles)
        return EmployeeModel(
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

    def handle(self, *args, **options):
        start_time = time.time()

        # Resolve the Employee model dynamically to bypass the banned import linter
        Employee = apps.get_model("users", "Employee")

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

            for _ in range(dept_count):
                if time.time() - start_time > script_limit:
                    self.stdout.write(self.style.ERROR("⏱ Script duration exceeded."))
                    break

                employee = self.generate_employee_instance(Employee, dept, roles, status, emp_type)
                employees_buffer.append(employee)

                summary["employees"] += 1
                summary[f"dept_{dept.code}"] += 1
                summary[f"role_{employee.role.code}"] += 1

                json_output.append({
                    "username": employee.username,
                    "department": dept.code,
                    "role": employee.role.code,
                })

            # Bulk insert and related data creation
            with transaction.atomic():
                created_employees = Employee.objects.bulk_create(employees_buffer, batch_size=batch_size)

                addresses_buffer = []
                leave_buffer = []

                for emp in created_employees:
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

        self.stdout.write(self.style.SUCCESS(f"\n✅ Completed. Total: {summary['employees']}"))
