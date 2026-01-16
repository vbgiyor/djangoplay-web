import argparse
import json
import logging
import time
from typing import Dict, List

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from locations.models.global_region import GlobalRegion
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Import global region data from JSON file specified in .env (GLOBAL_REGION_JSON).
    Expected .env key: DATA_DIR, GLOBAL_REGION_JSON
    Example usage:
        ./manage.py import_global_regions --datasource geonames # Loads from default JSON file with location_source='geonames'
        ./manage.py import_global_regions --region-file custom.json --datasource GOI # Loads from custom JSON file
    Imports fields into GlobalRegion with location_source.
    """

    BATCH_SIZE_DEFAULT = 1000
    EXPECTED_FIELDS = ['code', 'name', 'geonameid', 'slug']
    EXPECTED_FIELDS = ['code', 'name', 'asciiname', 'geonameId']
    FIELD_CONFIG = {
        'code': {'json_key': 'code', 'max_length': 2, 'db_max_length': 2},
        'name': {'json_key': 'name', 'max_length': 100, 'db_max_length': 100},
        'asciiname': {'json_key': 'asciiname', 'max_length': 100, 'db_max_length': 100},
        'geoname_id': {'json_key': 'geonameId', 'type': int},
        'slug': {'json_key': 'slug', 'max_length': 100, 'db_max_length': 100},
        'location_source': {'json_key': 'location_source', 'max_length': 20, 'db_max_length': 20}
    }

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--region-file",
            type=str,
            help="Override GLOBAL_REGION_JSON path with a custom JSON file",
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

    def process_region(self, data: Dict, index: int, user, caches: Dict, new_regions: List, update_regions: List, existing_slugs: set, stats: Dict, datasource: str) -> None:
        """Process a single global region record."""
        region_name = data.get('name', 'N/A')
        region_code = data.get('code', 'N/A')
        if not region_code:
            stats['skipped'].append({
                'region_name': region_name,
                'index': index,
                'reason': "Missing region code",
                'row_data': data
            })
            logger.warning(f"Skipping region {region_name} at index {index}: Missing region code")
            return

        try:
            # Prepare cleaned data
            cleaned_data = {
                'code': region_code,
                'name': data.get('name'),
                'geoname_id': data.get('geonameid'),
                'location_source': datasource,
            }

            slug = self.generate_unique_slug(cleaned_data['name'], index, existing_slugs)
            existing_slugs.add(slug)
            cleaned_data['slug'] = slug

            region = caches['global_region'].get(region_code)

            if region:
                for key, value in cleaned_data.items():
                    setattr(region, key, value)
                region.updated_by = user
                region.updated_at = timezone.now()
                update_regions.append(region)
                stats['updated_global_regions'] += 1
            else:
                region = GlobalRegion(**cleaned_data, created_by=user, updated_by=user)
                new_regions.append(region)
                stats['created_global_regions'] += 1

            caches['global_region'][region_code] = region

        except (KeyError, ValueError, ValidationError) as e:
            stats['skipped'].append({
                'region_name': region_name,
                'index': index,
                'reason': str(e),
                'row_data': data
            })
            logger.warning(f"Skipping region {region_name} at index {index}: {e}, row: {data}")

    def generate_unique_slug(self, name: str, index: int, existing_slugs: set) -> str:
        """Generate a unique slug for a region."""
        max_length = 100
        slug = slugify(name)
        if not slug:
            slug = f"region-{index}"
        slug = slug[:max_length]
        slug_base = slug[:max_length - 10]
        suffix = 1
        while slug in existing_slugs:
            suffix_str = f"-{suffix}"
            slug = f"{slug_base[:max_length - len(suffix_str)]}{suffix_str}"
            suffix += 1
        return slug

    def handle(self, *args, **options) -> None:
        start_time = time.time()
        batch_size = options['batch_size']
        datasource = options['datasource']
        stats = {
            'created_global_regions': 0,
            'updated_global_regions': 0,
            'skipped': [],
            'total': 0
        }
        existing_slugs = set(GlobalRegion.objects.values_list('slug', flat=True))

        self.stdout.write(f"Starting global region data import with datasource: {datasource}... ({time.time() - start_time:.2f}s)")
        logger.info(f"Starting global region data import with datasource: {datasource}")


        # Load JSON file
        json_filename = load_env_paths(env_var='GLOBAL_REGIONS_SYNC', file=options.get('file')).get('GLOBAL_REGIONS_SYNC')
        if not json_filename:
            self.stderr.write(self.style.ERROR(f"Failed to load GLOBAL_REGIONS_SYNC path ({time.time() - start_time:.2f}s)"))
            logger.error("Failed to load GLOBAL_REGIONS_SYNC path")
            return

        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                region_data = json.load(f)
                if not region_data:
                    raise ValueError("No valid data found in the JSON file")
                if not all(h in region_data[0] for h in self.EXPECTED_FIELDS):
                    missing = [h for h in self.EXPECTED_FIELDS if h not in region_data[0]]
                    raise ValueError(f"Missing expected fields in JSON data: {missing}")
                stats['total'] = len(region_data)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read JSON file: {e} ({time.time() - start_time:.2f}s)"))
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

        # Initialize caches
        caches = {
            'global_region': {r.code: r for r in GlobalRegion.objects.all()}
        }
        new_regions = []
        update_regions = []

        # Process regions
        for index, data in enumerate(region_data, 1):
            self.process_region(data, index, user, caches, new_regions, update_regions, existing_slugs, stats, datasource)

        # Bulk create and update
        with transaction.atomic():
            if new_regions:
                try:
                    GlobalRegion.objects.bulk_create(new_regions, batch_size=batch_size)
                    self.stdout.write(f"Created {len(new_regions)} global regions ({time.time() - start_time:.2f}s)")
                except Exception as e:
                    logger.error(f"Failed to bulk create global regions: {str(e)}")
                    for region in new_regions:
                        logger.error(f"Failed region data: {region.__dict__}")
                    raise

            if update_regions:
                fields_to_update = ['name', 'asciiname', 'geoname_id', 'slug', 'updated_by', 'location_source', 'updated_at']
                GlobalRegion.objects.bulk_update(
                    update_regions,
                    fields_to_update,
                    batch_size=batch_size
                )
                self.stdout.write(f"Updated {len(update_regions)} global regions ({time.time() - start_time:.2f}s)")

        # Log summary
        self.stdout.write(self.style.SUCCESS(f"Global Region Data Import Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Global regions created: {stats['created_global_regions']}")
        self.stdout.write(f"  - Global regions updated: {stats['updated_global_regions']}")
        self.stdout.write(f"  - Records skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - Region: {skipped['region_name']} (Index: {skipped['index']}): {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        logger.info(
            f"Global Region Data Import Summary: Total={stats['total']}, "
            f"Created={stats['created_global_regions']}, Updated={stats['updated_global_regions']}, "
            f"Skipped={len(stats['skipped'])}"
        )
        self.stdout.write(self.style.SUCCESS(f"Global Region Data Imported in {time.time() - start_time:.2f}s"))
