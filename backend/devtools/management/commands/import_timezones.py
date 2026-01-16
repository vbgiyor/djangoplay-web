import argparse
import json
import logging
import time
from typing import Dict

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models.timezone import Timezone
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Sync timezone data from a JSON file specified in .env (TIMEZONE_JSON).
    Expected .env keys: DATA_DIR, TIMEZONE_JSON
    Example usage:
        ./manage.py import_timezones                     # Loads from TIMEZONE_JSON
        ./manage.py import_timezones --file custom.json  # Loads from custom file
    Imports fields: country_code, timezone_id, gmt_offset_jan, dst_offset_jul, raw_offset
    """

    EXPECTED_FIELDS = ['country_code', 'timezone_id', 'gmt_offset_jan', 'dst_offset_jul', 'raw_offset']
    FIELD_CONFIG = {
        'country_code': {'source': 'CountryCode', 'max_length': 2},
        'timezone_id': {'source': 'TimeZoneId', 'max_length': 100},
        'display_name': {'source': 'TimeZoneId', 'max_length': 100},
        'gmt_offset_jan': {'source': 'GMT offset 1. Jan 2025', 'type': float},
        'dst_offset_jul': {'source': 'DST offset 1. Jul 2025', 'type': float},
        'raw_offset': {'source': 'rawOffset (independant of DST)', 'type': float},
    }

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--file",
            type=str,
            help="Override TIMEZONE_JSON path with a custom JSON file",
        )

    def validate_fields(self, data: Dict, timezone_id: str) -> Dict:
        """Validate and clean fields for a timezone."""
        cleaned_data = {}
        for field, config in self.FIELD_CONFIG.items():
            value = data.get(config.get('source', field))
            if 'type' in config and value is not None:
                try:
                    cleaned_data[field] = config['type'](value)
                except (ValueError, TypeError) as e:
                    raise ValidationError(f"Invalid {field}: {e}")
            else:
                cleaned_data[field] = value[:config['max_length']] if value and 'max_length' in config else value

        missing = [f for f in ['country_code', 'timezone_id', 'gmt_offset_jan', 'dst_offset_jul', 'raw_offset'] if cleaned_data[f] is None]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
        if not cleaned_data['timezone_id']:
            raise ValidationError("Display name (derived from timezone_id) is required")

        return cleaned_data

    def process_timezone(self, data: Dict, index: int, user, stats: Dict) -> None:
        """Process a single timezone record."""
        timezone_id = data.get('TimeZoneId', 'N/A')
        try:
            cleaned_data = self.validate_fields(data, timezone_id)
            with transaction.atomic():
                try:
                    timezone = Timezone.objects.get(timezone_id=cleaned_data['timezone_id'])
                    for key, value in cleaned_data.items():
                        setattr(timezone, key, value)
                    timezone.updated_by = user
                    timezone.save()
                    stats['updated'] += 1
                    action = "updated"
                except Timezone.DoesNotExist:
                    timezone = Timezone.objects.create(**cleaned_data, created_by=user, updated_by=user)
                    stats['created'] += 1
                    action = "created"
                logger.info(f"{action.capitalize()} timezone: {timezone_id}")
                self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} timezone: {timezone_id} ({time.time() - stats['start_time']:.2f}s)"))
        except (KeyError, ValueError, ValidationError) as e:
            stats['skipped'].append({'timezone_id': timezone_id, 'index': index, 'reason': str(e)})
            logger.warning(f"Skipping timezone {timezone_id} at index {index}: {e}")

    def handle(self, *args, **options) -> None:
        stats = {'created': 0, 'updated': 0, 'skipped': [], 'total': 0, 'start_time': time.time()}
        self.stdout.write(f"Starting timezone sync... ({time.time() - stats['start_time']:.2f}s)")
        logger.info("Starting timezone sync")
        start_time = time.time()

        # Load JSON file
        json_filename = load_env_paths(env_var='TIMEZONE_JSON', file=options.get('file')).get('TIMEZONE_JSON')
        if not json_filename:
            self.stderr.write(self.style.ERROR(f"Failed to load TIMEZONE_JSON path ({time.time() - stats['start_time']:.2f}s)"))
            logger.error("Failed to load TIMEZONE_JSON path")
            return

        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                timezone_data = json.load(f)
                if not timezone_data:
                    raise ValueError("No valid timezone data found in JSON file")
                stats['total'] = len(timezone_data)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read JSON file: {e} ({time.time() - stats['start_time']:.2f}s)"))
            logger.error(f"Failed to read JSON file: {e}", exc_info=True)
            return

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

        # Process timezones
        for index, data in enumerate(timezone_data, 1):
            self.process_timezone(data, index, user, stats)

        # Log summary
        self.stdout.write(self.style.SUCCESS(f"Timezone Syncing summary: ({time.time() - stats['start_time']:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Timezones created: {stats['created']}")
        self.stdout.write(f"  - Timezones updated: {stats['updated']}")
        self.stdout.write(f"  - Records skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - Timezone: {skipped['timezone_id']} (Index: {skipped['index']}): {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        logger.info(
            f"Timezone Syncing summary: Total={stats['total']}, Created={stats['created']}, "
            f"Updated={stats['updated']}, Skipped={len(stats['skipped'])}"
        )
        self.stdout.write(self.style.SUCCESS(f"Timezones Synced in {time.time() - stats['start_time']:.2f}s"))
