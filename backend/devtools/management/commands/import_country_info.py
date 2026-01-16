import argparse
import json
import logging
import re
import string
import time
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from locations.models.custom_country import CustomCountry
from locations.models.global_region import GlobalRegion
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Import country data from JSON files specified in .env (COUNTRY_INFO_JSON and PHONE_POSTAL_LENGTH_JSON).
    Expected .env keys: DATA_DIR, COUNTRY_INFO_JSON, PHONE_POSTAL_LENGTH_JSON
    Example usage:
        ./manage.py import_country_info                     # Loads from default JSON files
        ./manage.py import_country_info --country-file custom.json --phone-postal-file postal.json  # Loads from custom JSON files
        ./manage.py import_country_info --datasource geonames
    Imports fields into CustomCountry and links to GlobalRegion.
    """

    BATCH_SIZE_DEFAULT = 1000
    EXPECTED_FIELDS = [
        'ISO', 'Country', 'Capital', 'Population', 'Continent',
        'CurrencyCode', 'CurrencyName', 'Phone', 'Postal Code Regex',
        'Languages', 'geonameid', 'neighbours'
    ]
    FIELD_CONFIG = {
        'country_code': {'json_key': 'ISO', 'max_length': 2, 'db_max_length': 2},
        'name': {'json_key': 'Country', 'max_length': 100, 'db_max_length': 100},
        'asciiname': {'json_key': 'Country', 'max_length': 100, 'db_max_length': 100},
        'country_capital': {'json_key': 'Capital', 'max_length': 100, 'db_max_length': 100},
        'population': {'json_key': 'Population', 'type': int},
        'currency_code': {'json_key': 'CurrencyCode', 'max_length': 3, 'db_max_length': 3},
        'currency_name': {'json_key': 'CurrencyName', 'max_length': 50, 'db_max_length': 50},
        'country_phone_code': {'json_key': 'Phone', 'max_length': 10, 'db_max_length': 10},
        'postal_code_regex': {'json_key': 'Postal Code Regex', 'max_length': 300, 'db_max_length': 300},
        'country_languages': {'json_key': 'Languages', 'max_length': 300, 'db_max_length': 300},
        'geoname_id': {'json_key': 'geonameid', 'type': int},
        'alternatenames': {'json_key': 'alternatenames', 'max_length': 300, 'db_max_length': 300},
        'postal_code_length': {'json_key': 'postal_code_length', 'max_length': 20, 'db_max_length': 20},
        'phone_number_length': {'json_key': 'phone_number_length', 'max_length': 20, 'db_max_length': 20},
        'location_source': {'json_key': 'location_source', 'max_length': 20, 'db_max_length': 20}
    }

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--country-file",
            type=str,
            help="Override COUNTRY_INFO_JSON path with a custom JSON file",
        )
        parser.add_argument(
            "--phone-postal-file",
            type=str,
            help="Override PHONE_POSTAL_LENGTH_JSON path with a custom JSON file",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=self.BATCH_SIZE_DEFAULT,
            help=f"Batch size for bulk operations (default: {self.BATCH_SIZE_DEFAULT})",
        )
        parser.add_argument(
            "--datasource",
            type=str,
            required=True,
            help="Data source for location_source field (e.g., 'geonames' or 'GOI')",
        )

    def clean_string(self, value: Optional[str]) -> Optional[str]:
        """Remove non-printable characters from a string."""
        if value is None:
            return None
        return ''.join(c for c in str(value) if c in string.printable or ord(c) < 0x10000)

    def validate_fields(self, data: Dict, country_name: str, country_code: str) -> Optional[Dict]:
        """Validate and clean fields for a country."""
        cleaned_data = {}
        for field, config in self.FIELD_CONFIG.items():
            if field == 'location_source':
                continue # location_source is set separately
            value = data.get(config['json_key'])
            if 'type' in config and value is not None:
                try:
                    cleaned_data[field] = config['type'](value)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Invalid {field} for {country_name}: {e}")
            else:
                max_length = config.get('db_max_length', config.get('max_length'))
                cleaned_data[field] = self.clean_string(value)[:max_length] if value else None
                if cleaned_data[field] and max_length and len(cleaned_data[field]) > max_length:
                    logger.debug(f"Truncated {field} for {country_name}: {cleaned_data[field]}")
                    cleaned_data[field] = cleaned_data[field][:max_length]

        # Validate continent_code separately
        continent_code = data.get('Continent')
        if continent_code:
            cleaned_data['continent_code'] = self.clean_string(continent_code)[:10]
        else:
            cleaned_data['continent_code'] = None

        # Validate required fields
        required_fields = ['country_code', 'name', 'continent_code']
        missing = [f for f in required_fields if not cleaned_data[f] or cleaned_data[f] == 'N/A']
        if missing:
            raise ValidationError(f"Missing required fields for {country_name}: {', '.join(missing)}")

        # Normalize phone code
        if cleaned_data['country_phone_code']:
            cleaned_data['country_phone_code'] = cleaned_data['country_phone_code'].split(',')[0].strip()[:self.FIELD_CONFIG['country_phone_code']['db_max_length']]
            logger.debug(f"Normalized phone code for {country_name}: {cleaned_data['country_phone_code']}")

        # Validate postal code regex and set has_postal_code
        if cleaned_data['postal_code_regex']:
            try:
                re.compile(cleaned_data['postal_code_regex'])
                logger.debug(f"Valid postal code regex for {country_name}: {cleaned_data['postal_code_regex']}")
                cleaned_data['has_postal_code'] = True
            except re.error as e:
                logger.warning(f"Invalid postal code regex for {country_name}: {e}. Regex: {cleaned_data['postal_code_regex']}")
                cleaned_data['postal_code_regex'] = None
                cleaned_data['has_postal_code'] = False
                logger.info(f"Set postal_code_regex to None and has_postal_code to False for {country_name} due to invalid regex")
        else:
            cleaned_data['has_postal_code'] = False

        return cleaned_data

    def generate_unique_slug(self, name: str, index: int, existing_slugs: set) -> str:
        """Generate a unique slug for a country, ensuring it does not exceed 100 characters."""
        max_length = 100
        slug = slugify(name)
        if not slug:
            slug = f"country-{index}"
        slug = slug[:max_length]
        slug_base = slug[:max_length - 10]
        suffix = 1
        while slug in existing_slugs:
            suffix_str = f"-{suffix}"
            slug = f"{slug_base[:max_length - len(suffix_str)]}{suffix_str}"
            suffix += 1
        return slug

    def process_country(self, data: Dict, index: int, user, caches: Dict, new_countries: List, update_countries: List, country_global_regions: Dict, existing_slugs: set, stats: Dict, datasource: str) -> None:
        """Process a single country record."""
        country_name = data.get('Country', 'N/A')
        country_code = data.get('ISO', 'N/A')
        if country_code in caches['processed_codes']:
            stats['skipped'].append({
                'country_name': country_name,
                'index': index,
                'reason': f"Duplicate country code {country_code}",
                'row_data': data
            })
            logger.warning(f"Skipping duplicate country code {country_code} for {country_name} at index {index}")
            return

        try:
            cleaned_data = self.validate_fields(data, country_name, country_code)
            if cleaned_data is None:
                stats['skipped'].append({
                    'country_name': country_name,
                    'index': index,
                    'reason': "Validation failed",
                    'row_data': data
                })
                logger.warning(f"Skipping {country_name} at index {index} due to validation failure")
                return

            slug = self.generate_unique_slug(cleaned_data['name'], index, existing_slugs)
            existing_slugs.add(slug)

            # Check for global region
            continent_key = cleaned_data['continent_code'].lower()
            global_region = caches['global_region'].get(continent_key)
            if not global_region:
                raise ValidationError(f"Global region code '{cleaned_data['continent_code']}' does not exist for {country_name}")

            country_key = cleaned_data['country_code']
            country = caches['country'].get(country_key)

            # Exclude continent_code from CustomCountry fields
            cleaned_data_for_country = {k: v for k, v in cleaned_data.items() if k != 'continent_code'}
            cleaned_data_for_country['slug'] = slug
            cleaned_data_for_country['location_source'] = datasource # Set the datasource here
            logger.debug(f"Processed data for {country_name}: {cleaned_data_for_country}")

            if country:
                for key, value in cleaned_data_for_country.items():
                    setattr(country, key, value)
                country.updated_by = user
                country.updated_at = timezone.now() # Explicitly set updated_at
                update_countries.append(country)
                stats['updated_countries'] += 1
            else:
                country = CustomCountry(**cleaned_data_for_country, created_by=user, updated_by=user)
                new_countries.append(country)
                stats['created_countries'] += 1

            caches['country'][country_key] = country
            caches['processed_codes'].add(country_key)
            country_global_regions[country_key] = global_region

        except (KeyError, ValueError, ValidationError) as e:
            stats['skipped'].append({
                'country_name': country_name,
                'index': index,
                'reason': str(e),
                'row_data': data
            })
            logger.warning(f"Skipping country {country_name} at index {index}: {e}, row: {data}")

    def handle(self, *args, **options) -> None:
        start_time = time.time()
        batch_size = options['batch_size']
        datasource = options['datasource'] # Get the new datasource argument
        stats = {
            'created_countries': 0,
            'updated_countries': 0,
            'skipped': [],
            'total': 0,
            'invalid_regex_countries': []
        }
        existing_slugs = set(CustomCountry.objects.values_list('slug', flat=True))

        self.stdout.write(f"Starting country data import... ({time.time() - start_time:.2f}s)")
        logger.info("Starting country data import")

        # Load environment paths separately for each file
        country_env_paths = load_env_paths(
            env_var='COUNTRY_INFO_JSON',
            file=options.get('country_file')
        )
        phone_postal_env_paths = load_env_paths(
            env_var='PHONE_POSTAL_LENGTH_JSON',
            file=options.get('phone_postal_file')
        )

        country_json_filename = country_env_paths.get('COUNTRY_INFO_JSON')
        phone_postal_json_filename = phone_postal_env_paths.get('PHONE_POSTAL_LENGTH_JSON')

        if not country_json_filename or not phone_postal_json_filename:
            missing = []
            if not country_json_filename:
                missing.append('COUNTRY_INFO_JSON')
            if not phone_postal_json_filename:
                missing.append('PHONE_POSTAL_LENGTH_JSON')
            self.stderr.write(self.style.ERROR(f"Failed to load paths for {', '.join(missing)} ({time.time() - start_time:.2f}s)"))
            logger.error(f"Failed to load paths for {', '.join(missing)}")
            return

        # Load country JSON file
        try:
            with open(country_json_filename, 'r', encoding='utf-8') as f:
                country_data = json.load(f)
                if not country_data:
                    raise ValueError("No valid data found in the COUNTRY_INFO_JSON file")
                if not all(h in country_data[0] for h in self.EXPECTED_FIELDS):
                    missing = [h for h in self.EXPECTED_FIELDS if h not in country_data[0]]
                    raise ValueError(f"Missing expected fields in COUNTRY_INFO_JSON data: {missing}")
                stats['total'] = len(country_data)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read COUNTRY_INFO_JSON file: {e} ({time.time() - start_time:.2f}s)"))
            logger.error(f"Failed to read COUNTRY_INFO_JSON file: {e}", exc_info=True)
            return

        # Load phone and postal length JSON file
        try:
            with open(phone_postal_json_filename, 'r', encoding='utf-8') as f:
                phone_postal_data = json.load(f)
                if not phone_postal_data:
                    raise ValueError("No valid data found in the PHONE_POSTAL_LENGTH_JSON file")
                phone_postal_map = {
                    item['country_code']: {
                        'postal_code_length': item.get('postal_code_length'),
                        'phone_number_length': item.get('phone_number_length')
                    } for item in phone_postal_data
                }
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read PHONE_POSTAL_LENGTH_JSON file: {e} ({time.time() - start_time:.2f}s)"))
            logger.error(f"Failed to read PHONE_POSTAL_LENGTH_JSON file: {e}", exc_info=True)
            return

        # Merge postal code length and phone number length into country data
        for data in country_data:
            country_code = data.get('ISO')
            if country_code in phone_postal_map:
                data['postal_code_length'] = phone_postal_map[country_code].get('postal_code_length')
                data['phone_number_length'] = phone_postal_map[country_code].get('phone_number_length')
            else:
                data['postal_code_length'] = None
                data['phone_number_length'] = None

        # Get user for audit fields
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using emoloyee: {user.username}")
        except Employee.DoesNotExist:
            error_msg = f"Employee with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        # Initialize caches
        caches = {
            'country': {c.country_code: c for c in CustomCountry.objects.all()},
            'global_region': {r.code.lower(): r for r in GlobalRegion.objects.all()},
            'processed_codes': set()
        }
        new_countries = []
        update_countries = []
        country_global_regions = {}

        # Process countries
        for index, data in enumerate(country_data, 1):
            self.process_country(data, index, user, caches, new_countries, update_countries, country_global_regions, existing_slugs, stats, datasource)
            if index % batch_size == 0:
                self.stdout.write(f"Processed {index} records ({time.time() - start_time:.2f}s)")

            if len(new_countries) >= batch_size or len(update_countries) >= batch_size or index == stats['total']:
                with transaction.atomic():
                    if new_countries:
                        try:
                            CustomCountry.objects.bulk_create(new_countries, batch_size=batch_size)
                            self.stdout.write(f"Created {len(new_countries)} countries ({time.time() - start_time:.2f}s)")
                            new_countries.clear()
                        except Exception as e:
                            logger.error(f"Failed to bulk create countries: {str(e)}")
                            for country in new_countries:
                                logger.error(f"Failed country data: {country.__dict__}")
                            raise
                    if update_countries:
                        CustomCountry.objects.bulk_update(
                            update_countries,
                            list(self.FIELD_CONFIG.keys()) + ['slug', 'updated_by', 'has_postal_code', 'location_source', 'updated_at'],
                            batch_size=batch_size
                        )
                        self.stdout.write(f"Updated {len(update_countries)} countries ({time.time() - start_time:.2f}s)")
                        update_countries.clear()

        # Assign global regions
        with transaction.atomic():
            for country_code, global_region in country_global_regions.items():
                country = caches['country'].get(country_code)
                if country and country.pk:
                    country.global_regions.clear()
                    country.global_regions.add(global_region)
                    self.stdout.write(f"Assigned {global_region.code} to {country.name} ({time.time() - start_time:.2f}s)")

        # Log summary
        self.stdout.write(self.style.SUCCESS(f"Country Data Import Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Countries created: {stats['created_countries']}")
        self.stdout.write(f"  - Countries updated: {stats['updated_countries']}")
        self.stdout.write(f"  - Records skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - Country: {skipped['country_name']} (Index: {skipped['index']}): {skipped['reason']}")
                if 'Invalid postal code regex' in skipped['reason']:
                    stats['invalid_regex_countries'].append(skipped['country_name'])
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        if stats['invalid_regex_countries']:
            self.stdout.write(self.style.WARNING(
                f"  - Countries with invalid postal code regex: {', '.join(stats['invalid_regex_countries'])}"
            ))
            self.stdout.write(self.style.WARNING(
                "Please review the COUNTRY_INFO_JSON file or ensure the source data contains valid regex patterns."
            ))
        logger.info(
            f"Country Data Import Summary: Total={stats['total']}, "
            f"Created={stats['created_countries']}, Updated={stats['updated_countries']}, "
            f"Skipped={len(stats['skipped'])}, Invalid Regex Countries={len(stats['invalid_regex_countries'])}"
        )
        self.stdout.write(self.style.SUCCESS(f"Country Data Imported in {time.time() - start_time:.2f}s"))
