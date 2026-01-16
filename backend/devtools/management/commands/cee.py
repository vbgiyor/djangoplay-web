import argparse
import json
import logging
import os
import random
import string
import time
import uuid
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker
from locations.models.custom_country import CustomCountry
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.locations.postal_code_validations import get_country_postal_regex

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate data for specified models and countries, saving to JSON files in EMPLOYEES_JSON/<country_code>_<model>.json.
    Example usage:
        ./manage.py cee --employee --country IN --count 10
        ./manage.py cee --employee --role --count 10
        ./manage.py cee --custom employee,role,department --country NZ --count 10
        ./manage.py cee --custom employee,role,department --countries IN,CN,KR --count 10
        ./manage.py cee --custom employee,role,department --all --count 10
    Generates JSON data for specified models with country-specific details using Faker.
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--country", type=str, help="Country code (e.g., IN)")
        group.add_argument("--all", action="store_true", help="Generate for all countries")
        group.add_argument("--countries", type=str, help="Comma-separated country codes (e.g., IN,CN,KR)")

        parser.add_argument("--employee", action="store_true", help="Generate employee data")
        parser.add_argument("--address", action="store_true", help="Generate address data")
        parser.add_argument("--department", action="store_true", help="Generate department data")
        parser.add_argument("--employment_status", action="store_true", help="Generate employment status data")
        parser.add_argument("--employee_type", action="store_true", help="Generate employee type data")
        parser.add_argument("--leave_application", action="store_true", help="Generate leave application data")
        parser.add_argument("--leave_balance", action="store_true", help="Generate leave balance data")
        parser.add_argument("--leave_type", action="store_true", help="Generate leave type data")
        parser.add_argument("--role", action="store_true", help="Generate role data")
        parser.add_argument("--team", action="store_true", help="Generate team data")
        parser.add_argument("--custom", type=str, help="Comma-separated models (e.g., employee,role,department)")

        parser.add_argument("--count", type=int, default=5, help="Number of records per model (default: 50)")
        parser.add_argument("--emp-json", type=str, help="Override EMPLOYEES_JSON path (used with --country)")

    def generate_phone_number(self, country_phone_code: str, phone_length: int = 10) -> str:
        digits = ''.join(random.choices(string.digits, k=phone_length))
        return f"{country_phone_code}{digits}"

    def generate_username(self, first_name: str, last_name: str) -> str:
        base = f"{first_name.lower()}.{last_name.lower()}"
        username = slugify(base, allow_unicode=True)
        return username or f"user-{uuid.uuid4().hex[:8]}"

    def generate_postal_code(self, country_code: str) -> str:
        regex = get_country_postal_regex(country_code)
        if not regex:
            return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        if regex == r"^\d{3}-\d{4}$":  # Japan
            return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        elif regex == r"^\d{5}$":  # South Korea
            return f"{random.randint(10000, 99999)}"
        return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"

    def generate_employee_code(self):
        code_suffix = str(uuid.uuid4()).replace('-', '')[:12].upper()
        return f"DJP{code_suffix}"

    def generate_role_code(self, title: str):
        return title.upper().replace(" ", "_")[:20]

    def generate_department_code(self):
        return ''.join(random.choices(string.ascii_uppercase, k=4))

    def generate_leave_type_code(self, name: str):
        return name.upper().replace(" ", "_")[:20]

    def generate_employee(self, country_data: dict, faker: Faker, departments: list, roles: list, employee_types: list, employment_statuses: list) -> dict:
        first_name = faker.first_name()
        last_name = faker.last_name()
        department = random.choice(departments) if departments else {"code": "FIN", "name": "Finance"}
        role = random.choice(roles) if roles else {"code": "ANLYST", "title": "Analyst", "rank": 10}
        employee_type = random.choice(employee_types) if employee_types else {"code": "FULL_TIME", "name": "Full-Time"}
        employment_status = random.choice(employment_statuses) if employment_statuses else {"code": "ACTIVE", "name": "Active"}
        city = faker.city()

        return {
            "employee_code": self.generate_employee_code(),
            "username": self.generate_username(first_name, last_name),
            "email": f"{first_name.lower()}.{last_name.lower()}@djangoplay.com",
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": self.generate_phone_number(country_data["country_phone_code"]),
            "department": department["code"],
            "role": role["code"],
            "team": None,
            "job_title": role["title"],
            "address": None,
            "approval_limit": round(random.uniform(100000, 99999999.99), 2),
            "manager": None,
            "avatar": None,
            "hire_date": "2020-01-01",
            "termination_date": None,
            "employment_status": employment_status["code"],
            "employee_type": employee_type["code"],
            "salary": round(random.uniform(50000, 250000), 2),
            "date_of_birth": faker.date_of_birth(minimum_age=18, maximum_age=65).strftime("%Y-%m-%d"),
            "national_id": f"{random.randint(10000, 99999)}-{random.randint(1000, 9999)}",
            "emergency_contact_name": f"{faker.first_name()} {faker.last_name()}",
            "emergency_contact_phone": self.generate_phone_number(country_data["country_phone_code"]),
            "probation_end_date": None,
            "contract_end_date": None,
            "gender": random.choice(["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"]),
            "marital_status": random.choice(["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "PREFER_NOT_TO_SAY"]),
            "bank_details": {"account": f"{random.randint(10000000, 99999999)}", "bank": faker.company()},
            "notes": "",
            "address_display": f"{city}, {country_data['name']}",
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None,
            "is_active": True
        }

    def generate_address(self, country_data: dict, faker: Faker) -> dict:
        city = faker.city()
        street = f"{random.randint(1, 999)} {faker.street_name()}"

        return {
            "address": street,
            "country": country_data["name"],
            "state": city,
            "city": city,
            "postal_code": self.generate_postal_code(country_data["country_code"]),
            "address_type": "CURRENT",  # or "PERMANENT" based on your test intent
            "emergency_contact": (
                f"{faker.first_name()} {faker.last_name()} "
                f"{self.generate_phone_number(country_data['country_phone_code'])}"
            ),
        }


    def generate_department(self, faker: Faker) -> dict:
        name = faker.company_suffix()
        return {
            "code": self.generate_department_code(),
            "name": f"{name} Department",
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def generate_employment_status(self, faker: Faker) -> dict:
        status = random.choice(["Active", "On Leave", "Terminated"])
        return {
            "code": status.upper().replace(" ", "_"),
            "name": status,
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def generate_employee_type(self, faker: Faker) -> dict:
        type_name = random.choice(["Full-Time", "Part-Time", "Contractor"])
        return {
            "code": type_name.upper().replace("-", "_"),
            "name": type_name,
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def generate_leave_type(self, faker: Faker) -> dict:
        name = random.choice(["Annual Leave", "Sick Leave", "Maternity Leave", "Personal Leave"])
        return {
            "code": self.generate_leave_type_code(name),
            "name": name,
            "default_balance": round(random.uniform(40, 200), 2),
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def generate_leave_balance(self, employee: dict, leave_type: dict, faker: Faker) -> dict:
        year = timezone.now().year
        return {
            "employee": employee["employee_code"],
            "leave_type": leave_type["code"],
            "year": year,
            "balance": leave_type["default_balance"],
            "used": round(random.uniform(0, leave_type["default_balance"] / 2), 2),
            "reset_date": f"{year}-01-01",
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None,
            "is_active": True
        }

    def generate_leave_application(self, employee: dict, leave_type: dict, faker: Faker) -> dict:
        start_date = faker.date_this_year()
        end_date = start_date + timedelta(days=random.randint(1, 10))
        return {
            "employee": employee["employee_code"],
            "leave_type": leave_type["code"],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d") if random.choice([True, False]) else None,
            "hours": round(random.uniform(8, 40), 2) if random.choice([True, False]) else None,
            "status": random.choice(["PENDING", "APPROVED", "REJECTED", "CANCELLED"]),
            "approver": None,
            "reason": faker.sentence(),
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None,
            "is_active": True
        }

    def generate_role(self, faker: Faker) -> dict:
        title = random.choice(["Analyst", "Manager", "Director", "Officer"])
        return {
            "code": self.generate_role_code(title),
            "title": title,
            "rank": random.randint(1, 20),
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def generate_team(self, department: dict, employee: dict, faker: Faker) -> dict:
        return {
            "name": f"{faker.word().capitalize()} Team",
            "department": department["code"],
            "leader": employee["employee_code"] if employee else None,
            "description": faker.sentence(),
            "is_active": True,
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "created_by": None,
            "updated_by": None,
            "deleted_at": None,
            "deleted_by": None
        }

    def handle(self, *args, **options):
        start_time = time.time()
        env_data = load_env_paths(env_var="EMPLOYEES_JSON", file=options.get("emp_json"))
        employees_base_path = env_data.get("EMPLOYEES_JSON")
        if not employees_base_path:
            self.stderr.write(self.style.ERROR(f"Failed to load EMPLOYEES_JSON path ({time.time() - start_time:.2f}s)"))
            return

        locale_map = {"JP": "ja_JP", "US": "en_US", "GB": "en_GB", "KR": "ko_KR", "IN": "en_IN"}
        models_to_generate = []
        if options["custom"]:
            models_to_generate = [m.strip() for m in options["custom"].split(",")]
        else:
            for model in ["employee", "address", "department", "employment_status", "employee_type",
                          "leave_application", "leave_balance", "leave_type", "role", "team"]:
                if options.get(model):
                    models_to_generate.append(model)

        if not models_to_generate:
            self.stderr.write(self.style.ERROR(f"No models specified for generation ({time.time() - start_time:.2f}s)"))
            return

        if options["all"]:
            countries = CustomCountry.objects.all()
            if not countries:
                self.stderr.write(self.style.ERROR(f"No countries found ({time.time() - start_time:.2f}s)"))
                return
        elif options["countries"]:
            country_codes = [code.strip().upper() for code in options["countries"].split(",")]
            countries = CustomCountry.objects.filter(country_code__in=country_codes)
            invalid_codes = set(country_codes) - {country.country_code for country in countries}
            if invalid_codes:
                self.stderr.write(self.style.ERROR(f"Invalid country codes: {', '.join(invalid_codes)} ({time.time() - start_time:.2f}s)"))
                return
        else:
            country_code = options["country"].upper()
            try:
                countries = [CustomCountry.objects.get(country_code=country_code)]
            except CustomCountry.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Country code {country_code} not found ({time.time() - start_time:.2f}s)"))
                return

        for country in countries:
            country_code = country.country_code
            locale = locale_map.get(country_code, "en_US")
            faker = Faker(locale)
            global_region = country.global_regions.first()
            if not global_region:
                self.stderr.write(self.style.ERROR(f"No global region for {country_code} ({time.time() - start_time:.2f}s)"))
                continue

            country_data = {
                "name": country.name,
                "country_code": country_code,
                "country_phone_code": country.country_phone_code,
                "region": global_region.name,
                "postal_code_regex": country.postal_code_regex,
            }

            # Generate data for each model
            data = {model: [] for model in models_to_generate}
            if "department" in models_to_generate:
                for _ in range(options["count"]):
                    data["department"].append(self.generate_department(faker))
            if "employment_status" in models_to_generate:
                for _ in range(min(options["count"], 5)):  # Limit to common statuses
                    data["employment_status"].append(self.generate_employment_status(faker))
            if "employee_type" in models_to_generate:
                for _ in range(min(options["count"], 3)):  # Limit to common types
                    data["employee_type"].append(self.generate_employee_type(faker))
            if "role" in models_to_generate:
                for _ in range(options["count"]):
                    data["role"].append(self.generate_role(faker))
            if "leave_type" in models_to_generate:
                for _ in range(min(options["count"], 5)):  # Limit to common leave types
                    data["leave_type"].append(self.generate_leave_type(faker))
            if "address" in models_to_generate:
                for _ in range(options["count"]):
                    data["address"].append(self.generate_address(country_data, faker))
            if "employee" in models_to_generate:
                for _ in range(options["count"]):
                    data["employee"].append(self.generate_employee(
                        country_data, faker, data.get("department", []),
                        data.get("role", []), data.get("employee_type", []),
                        data.get("employment_status", [])))
            if "team" in models_to_generate:
                for _ in range(options["count"]):
                    employee = random.choice(data.get("employee", [])) if data.get("employee") else None
                    department = random.choice(data.get("department", [])) if data.get("department") else {"code": "FIN", "name": "Finance"}
                    data["team"].append(self.generate_team(department, employee, faker))
            if "leave_balance" in models_to_generate and "employee" in data and "leave_type" in data:
                for employee in data["employee"]:
                    for leave_type in data["leave_type"]:
                        data["leave_balance"].append(self.generate_leave_balance(employee, leave_type, faker))
            if "leave_application" in models_to_generate and "employee" in data and "leave_type" in data:
                for employee in data["employee"]:
                    for leave_type in data["leave_type"]:
                        data["leave_application"].append(self.generate_leave_application(employee, leave_type, faker))

            # Save to JSON
            for model, records in data.items():
                if not records:
                    continue
                emp_json_file = os.path.join(employees_base_path, f"{country_code}_{model}.json")
                if options["country"] and options.get("emp_json"):
                    emp_json_file = options["emp_json"].replace(".json", f"_{model}.json")
                emp_json_path = Path(emp_json_file)
                emp_json_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(emp_json_path, 'w', encoding='utf-8') as f:
                        json.dump(records, f, indent=2, ensure_ascii=False)
                    self.stdout.write(self.style.SUCCESS(f"Generated {len(records)} {model} records for {country_code} and saved to {emp_json_path} ({time.time() - start_time:.2f}s)"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to write {model} to {emp_json_path}: {e} ({time.time() - start_time:.2f}s)"))
                    logger.error(f"Failed to write {model} to {emp_json_path}: {e}", exc_info=True)
