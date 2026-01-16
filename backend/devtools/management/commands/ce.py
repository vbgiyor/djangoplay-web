import argparse
import json
import logging
import os
import random
import string
import time
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker
from locations.models.custom_country import CustomCountry
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.locations.postal_code_validations import get_country_postal_regex

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate employee data dynamically for specified countries and save to EMPLOYEES_JSON/<country_code>.json.
    Example usage:
        ./manage.py ce --country KR --count 1000
        ./manage.py ce --all --count 1000
        ./manage.py ce --countries IN,JP,KR,GB --count 1000
    Use quotes for --countries if commas cause shell issues, e.g., --countries "IN,JP,KR,GB".
    Generates JSON employee data with country-specific names, addresses, phone numbers, etc.
    Uses Faker for realistic data generation and CustomCountry for country-specific details.
    """

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        # Create a mutually exclusive group for country selection
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--country",
            type=str,
            help="Country code (e.g., KR for South Korea)",
        )
        group.add_argument(
            "--all",
            action="store_true",
            help="Generate JSON for all countries in CustomCountry",
        )
        group.add_argument(
            "--countries",
            type=str,
            help="Comma-separated country codes (e.g., IN,JP,KR,GB). Use quotes if needed: 'IN,JP,KR,GB'",
            # Alternative: Use space-separated input with:
            # type=str, nargs='*', help="Space-separated country codes (e.g., IN JP KR GB)"
        )
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of employees to generate per country (default: 1000)",
        )
        parser.add_argument(
            "--emp-json",
            type=str,
            help="Override EMPLOYEES_JSON path for output JSON file (used only with --country)",
        )

    def generate_phone_number(self, country_phone_code: str, phone_length: int = 10) -> str:
        """Generate a random phone number with the country code."""
        digits = ''.join(random.choices(string.digits, k=phone_length))
        return f"{country_phone_code} {digits[:4]}{digits[4:7]}{digits[7:]}"

    def generate_username(self, first_name: str, last_name: str) -> str:
        """Generate a unique username based on first and last name."""
        base = f"{first_name.lower()}.{last_name.lower()}"
        username = slugify(base, allow_unicode=True)  # Allow Unicode characters
        if not username:  # Fallback if slugify returns empty string
            username = f"user-{uuid.uuid4().hex[:8]}"  # Generate a fallback username
        return username

    def generate_postal_code(self, country_code: str) -> str:
        """Generate a postal code matching the country's regex or a fallback format."""
        try:
            regex = get_country_postal_regex(country_code)
            if not regex:
                return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            # Simplified: Generate for common formats
            if regex == r"^\d{3}-\d{4}$":  # Japan (e.g., 123-4567)
                return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            elif regex == r"^\d{5}$":  # South Korea (e.g., 12345)
                return f"{random.randint(10000, 99999)}"
            return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"  # Fallback
        except Exception as e:
            logger.warning(f"Failed to generate postal code for {country_code}: {e}")
            return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"

    def generate_employee(self, country_data: dict, faker: Faker, index: int) -> dict:
        """Generate a single employee record."""
        first_name = faker.first_name()
        last_name = faker.last_name()
        city = faker.city()
        department = random.choice(["FIN", "RISK", "COM", "TRY", "AP", "TRD", "AUD", "CRD", "CORP", "MNA", "INV", "TAX", "RPT", "AR"])
        job_title = {
            "FIN": "CFO", "RISK": "Risk Analyst", "COM": "Com Officer", "TRY": "Try Manager",
            "AP": "Ap Manager", "TRD": "Trader", "AUD": "Auditor", "CRD": "Crd Manager",
            "CORP": "Corp Analyst", "MNA": "Mna Analyst", "INV": "Inv Director", "TAX": "Tax Director",
            "RPT": "Rpt Analyst", "AR": "Ar Specialist"
        }.get(department, "Employee")
        role = job_title.upper().replace(" ", "_")

        return {
            "username": self.generate_username(first_name, last_name),
            "email": f"{first_name.lower()}.{last_name.lower()}@djangoplay.com",
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": self.generate_phone_number(country_data["country_phone_code"]),
            "country": country_data["name"],
            "region": country_data["region"],
            "manager": None,  # Simplified: can be extended to assign managers
            "approval_limit": round(random.uniform(100000, 99999999.99), 2),
            "department": department,
            "job_title": job_title,
            "role": role,
            "hire_date": "2020-01-01",
            "termination_date": "",
            "employment_status": "ACTIVE",
            "employee_type": "FULL_TIME",
            "salary": round(random.uniform(50000, 250000), 2),
            "address_display": f"{country_data['name']}, {country_data['region']}",
            "avatar": None,
            "address": {
                "address": f"{random.randint(1, 999)} {faker.street_name()}, {city}",
                "country": country_data["name"],
                "state": city,  # using city as state for simplicity
                "city": city,
                "postal_code": self.generate_postal_code(country_data["country_code"]),
                "address_type": "CURRENT",  # or "PERMANENT" if required by scenario
                "emergency_contact": (
                    f"{faker.first_name()} {faker.last_name()} "
                    f"{country_data['country_phone_code']} "
                    f"{random.randint(9000000000, 9999999999)}"
                ),
            }

        }

    def handle(self, *args, **options):
        start_time = time.time()

        # Load EMPLOYEES_JSON path
        env_start = time.time()
        env_data = load_env_paths(env_var="EMPLOYEES_JSON", file=options.get("emp_json"))
        employees_base_path = env_data.get("EMPLOYEES_JSON")
        self.stdout.write(f"Environment paths loaded in {time.time() - env_start:.2f}s")

        if not employees_base_path:
            self.stderr.write(self.style.ERROR(f"Failed to load EMPLOYEES_JSON path ({time.time() - start_time:.2f}s)"))
            return

        # Initialize Faker locale map
        locale_map = {"JP": "ja_JP", "US": "en_US", "GB": "en_GB", "KR": "ko_KR", "IN": "en_IN"}

        # Process countries based on arguments
        if options["all"]:
            countries = CustomCountry.objects.all()
            if not countries:
                self.stderr.write(self.style.ERROR(f"No countries found in CustomCountry ({time.time() - start_time:.2f}s)"))
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
                self.stderr.write(self.style.ERROR(f"Country code {country_code} not found in CustomCountry ({time.time() - start_time:.2f}s)"))
                return

        # Process each country
        for country in countries:
            country_code = country.country_code
            locale = locale_map.get(country_code, "en_US")  # Fallback to en_US
            faker = Faker(locale)

            # Fetch region data
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

            # Generate employees
            employees = []
            for i in range(options["count"]):
                employee = self.generate_employee(country_data, faker, i)
                employees.append(employee)

            # Construct output path
            emp_json_file = os.path.join(employees_base_path, f"{country_code}.json")
            if options["country"] and options.get("emp_json"):
                emp_json_file = options["emp_json"]

            # Ensure output directory exists
            emp_json_path = Path(emp_json_file)
            emp_json_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to JSON
            try:
                with open(emp_json_path, 'w', encoding='utf-8') as f:
                    json.dump(employees, f, indent=2, ensure_ascii=False)
                self.stdout.write(self.style.SUCCESS(f"Generated {options['count']} employees for {country_code} and saved to {emp_json_path} ({time.time() - start_time:.2f}s)"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to write to {emp_json_path}: {e} ({time.time() - start_time:.2f}s)"))
                logger.error(f"Failed to write to {emp_json_path}: {e}", exc_info=True)

# import argparse
# import json
# import os
# import random
# import string
# import time
# import uuid
# from pathlib import Path
# from faker import Faker
# from django.core.management.base import BaseCommand
# from django.utils.text import slugify
# from locations.models.custom_country import CustomCountry
# from locations.models.global_region import GlobalRegion
# from utilities.utils.data_sync.load_env_and_paths import load_env_paths
# import logging

# logger = logging.getLogger(__name__)

# class Command(BaseCommand):
#     help = """Generate employee data dynamically for a specified country and save to EMPLOYEES_JSON/<country_code>.json.
#     Example usage:
#         ./manage.py ce --country KR --count 1000
#     Generates JSON employee data with country-specific names, addresses, phone numbers, etc.
#     Uses Faker for realistic data generation and CustomCountry for country-specific details.
#     """

#     def add_arguments(self, parser: argparse.ArgumentParser) -> None:
#         parser.add_argument(
#             "--country",
#             type=str,
#             required=True,
#             help="Country code (e.g., KR for South Korea)",
#         )
#         parser.add_argument(
#             "--count",
#             type=int,
#             default=1000,
#             help="Number of employees to generate (default: 1000)",
#         )
#         parser.add_argument(
#             "--emp-json",
#             type=str,
#             help="Override EMPLOYEES_JSON path for output JSON file",
#         )

#     def generate_phone_number(self, country_phone_code: str, phone_length: int = 10) -> str:
#         """Generate a random phone number with the country code."""
#         digits = ''.join(random.choices(string.digits, k=phone_length))
#         return f"{country_phone_code} {digits[:4]}{digits[4:7]}{digits[7:]}"

#     def generate_username(self, first_name: str, last_name: str) -> str:
#         """Generate a unique username based on first and last name."""
#         base = f"{first_name.lower()}.{last_name.lower()}"
#         username = slugify(base, allow_unicode=True)  # Allow Unicode characters
#         if not username:  # Fallback if slugify returns empty string
#             username = f"user-{uuid.uuid4().hex[:8]}"  # Generate a fallback username
#         return username

#     def generate_postal_code(self, postal_code_regex: str) -> str:
#         """Generate a postal code matching the country's regex or a fallback format."""
#         if not postal_code_regex:
#             return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
#         # Simplified: Generate a 7-digit postal code for Japan (e.g., 123-4567)
#         if postal_code_regex == r"^\d{3}-\d{4}$":  # Japan's postal code format
#             return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
#         # Simplified: Generate a 5-digit postal code for South Korea (e.g., 12345)
#         elif postal_code_regex == r"^\d{5}$":  # South Korea's postal code format
#             return f"{random.randint(10000, 99999)}"
#         return f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"  # Fallback

#     def generate_employee(self, country_data: dict, faker: Faker, index: int) -> dict:
#         """Generate a single employee record."""
#         first_name = faker.first_name()
#         last_name = faker.last_name()
#         city = faker.city()
#         department = random.choice(["FIN", "RISK", "COM", "TRY", "AP", "TRD", "AUD", "CRD", "CORP", "MNA", "INV", "TAX", "RPT", "AR"])
#         job_title = {
#             "FIN": "CFO", "RISK": "Risk Analyst", "COM": "Com Officer", "TRY": "Try Manager",
#             "AP": "Ap Manager", "TRD": "Trader", "AUD": "Auditor", "CRD": "Crd Manager",
#             "CORP": "Corp Analyst", "MNA": "Mna Analyst", "INV": "Inv Director", "TAX": "Tax Director",
#             "RPT": "Rpt Analyst", "AR": "Ar Specialist"
#         }.get(department, "Employee")
#         role = job_title.upper().replace(" ", "_")

#         return {
#             "username": self.generate_username(first_name, last_name),
#             "email": f"{first_name.lower()}.{last_name.lower()}@djangoplay.com",
#             "first_name": first_name,
#             "last_name": last_name,
#             "phone_number": self.generate_phone_number(country_data["country_phone_code"]),
#             "country": country_data["name"],
#             "region": country_data["region"],
#             "manager": None,  # Simplified: can be extended to assign managers
#             "approval_limit": round(random.uniform(100000, 99999999.99), 2),
#             "department": department,
#             "job_title": job_title,
#             "role": role,
#             "hire_date": "2020-01-01",
#             "termination_date": "",
#             "employment_status": "ACTIVE",
#             "employee_type": "FULL_TIME",
#             "salary": round(random.uniform(50000, 250000), 2),
#             "address_display": f"{country_data['name']}, {country_data['region']}",
#             "avatar": None,
#             "address": {
#                 "current_address": f"{random.randint(1, 999)} {faker.street_name()}, {city}",
#                 "permanent_address": f"{random.randint(1, 999)} {faker.street_name()}, {city}",
#                 "country": country_data["name"],
#                 "state": city,  # Use city as state for simplicity; can be enhanced
#                 "city": city,
#                 "postal_code": self.generate_postal_code(country_data.get("postal_code_regex", "")),
#                 "address_type": "Home",
#                 "emergency_contact": f"{faker.first_name()} {faker.last_name()} {country_data['country_phone_code']} {random.randint(9000000000, 9999999999)}"
#             }
#         }

#     def handle(self, *args, **options):
#         start_time = time.time()
#         country_code = options["country"].upper()
#         count = options["count"]

#         # Load EMPLOYEES_JSON path
#         env_start = time.time()
#         env_data = load_env_paths(env_var="EMPLOYEES_JSON", file=options.get("emp_json"))
#         employees_base_path = env_data.get("EMPLOYEES_JSON")
#         self.stdout.write(f"Environment paths loaded in {time.time() - env_start:.2f}s")

#         if not employees_base_path:
#             self.stderr.write(self.style.ERROR(f"Failed to load EMPLOYEES_JSON path ({time.time() - start_time:.2f}s)"))
#             return

#         # Construct country-specific JSON filename
#         emp_json_file = os.path.join(employees_base_path, f"{country_code}.json") if not options.get("emp_json") else options.get("emp_json")

#         # Initialize Faker with country-specific locale
#         locale_map = {"JP": "ja_JP", "US": "en_US", "GB": "en_GB", "KR": "ko_KR", "IN": "en_IN"}
#         locale = locale_map.get(country_code, "en_US")  # Fallback to en_US
#         faker = Faker(locale)

#         # Fetch country and region data
#         try:
#             country = CustomCountry.objects.get(country_code=country_code)
#             global_region = country.global_regions.first()  # Use .first() to get one region
#             if not global_region:
#                 self.stderr.write(self.style.ERROR(f"No global region associated with country {country_code} ({time.time() - start_time:.2f}s)"))
#                 return
#             country_data = {
#                 "name": country.name,
#                 "country_phone_code": country.country_phone_code,
#                 "region": global_region.name,
#                 "postal_code_regex": country.postal_code_regex,
#             }
#         except CustomCountry.DoesNotExist:
#             self.stderr.write(self.style.ERROR(f"Country code {country_code} not found in CustomCountry ({time.time() - start_time:.2f}s)"))
#             return
#         except GlobalRegion.DoesNotExist:
#             self.stderr.write(self.style.ERROR(f"Global region for {country_code} not found ({time.time() - start_time:.2f}s)"))
#             return

#         # Generate employees
#         employees = []
#         for i in range(count):
#             employee = self.generate_employee(country_data, faker, i)
#             employees.append(employee)

#         # Ensure output directory exists
#         emp_json_path = Path(emp_json_file)
#         emp_json_path.parent.mkdir(parents=True, exist_ok=True)

#         # Save to <country_code>.json
#         try:
#             with open(emp_json_path, 'w', encoding='utf-8') as f:
#                 json.dump(employees, f, indent=2, ensure_ascii=False)
#             self.stdout.write(self.style.SUCCESS(f"Generated {count} employees for {country_code} and saved to {emp_json_path} ({time.time() - start_time:.2f}s)"))
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f"Failed to write to {emp_json_path}: {e} ({time.time() - start_time:.2f}s)"))
#             logger.error(f"Failed to write to {emp_json_path}: {e}", exc_info=True)
#             return
