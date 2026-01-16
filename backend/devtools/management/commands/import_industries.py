import argparse
import json
import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from industries.models.industry import Industry
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Import ISIC Rev. 5 Industry data from a JSON file (INDUSTRIES_JSON) into the database.
If the JSON file is not present, it will exit with an error message.

Expected .env keys:
    DATA_DIR, INDUSTRIES_JSON

Example usage:
    ./manage.py import_industries                     # Imports from INDUSTRIES_JSON
    ./manage.py import_industries --file custom.json  # Imports from a custom JSON file
"""

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--file",
            type=str,
            help="Override INDUSTRIES_JSON path with a custom JSON file",
        )

    def handle(self, *args, **options):
        self.options = options
        start_time = time.time()
        stats = {'created': 0, 'updated': 0, 'skipped': [], 'total': 0}

        self.stdout.write(f"Starting industry import... ({time.time() - start_time:.2f}s)")
        logger.info("Starting industry import")

        # Load INDUSTRIES_JSON path
        json_filename = self.options.get('file')
        env_data = load_env_paths(env_var='INDUSTRIES_JSON', file=json_filename, require_exists=bool(json_filename))
        json_filename = env_data.get('INDUSTRIES_JSON')
        if not json_filename:
            error_msg = f"Failed to load INDUSTRIES_JSON path from environment ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        self.stdout.write(f"Checking JSON file: {json_filename} ({time.time() - start_time:.2f}s)")
        logger.info(f"Checking JSON file: {json_filename}")

        # Check if JSON file exists
        if not Path(json_filename).is_file():
            error_msg = f"JSON file {json_filename} not found. Please ensure the file exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
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

        # Load JSON file
        try:
            self.stdout.write(f"Loading JSON file: {json_filename} ({time.time() - start_time:.2f}s)")
            logger.info(f"Loading JSON file: {json_filename}")
            with open(json_filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            industries = data.get('isic', [])
            if not industries:
                error_msg = f"No 'isic' key found in JSON file {json_filename} or it is empty ({time.time() - start_time:.2f}s)"
                self.stderr.write(self.style.ERROR(error_msg))
                logger.error(error_msg)
                return
            stats['total'] = sum(len(section['Divisions']) + sum(len(division['Groups']) + sum(len(group['Classes']) for group in division['Groups']) for division in section['Divisions']) for section in industries)
            self.stdout.write(f"Found {stats['total']} industry records to import ({time.time() - start_time:.2f}s)")
            logger.info(f"Found {stats['total']} industry records to import")
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON file {json_filename}: {e} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            return
        except Exception as e:
            error_msg = f"Failed to read JSON file {json_filename}: {e} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            return

        sector_map = {
            "A": "PRIMARY",
            "B": "PRIMARY",
            "C": "SECONDARY",
            "D": "TERTIARY",
            "E": "TERTIARY",
            "F": "TERTIARY",
            "G": "TERTIARY",
            "H": "TERTIARY",
            "I": "TERTIARY",
            "J": "TERTIARY",
            "K": "TERTIARY",
            "L": "TERTIARY",
            "M": "TERTIARY",
            "N": "TERTIARY",
            "O": "TERTIARY",
            "P": "TERTIARY",
            "Q": "TERTIARY",
            "R": "TERTIARY",
            "S": "TERTIARY",
            "T": "TERTIARY",
            "U": "TERTIARY",
        }

        with transaction.atomic():
            for section in industries:
                try:
                    section_obj, created = Industry.objects.get_or_create(
                        code=section["Section"],
                        defaults={
                            "description": section["Description"],
                            "level": "SECTION",
                            "sector": sector_map.get(section["Section"], "TERTIARY"),
                            "created_by": user,
                            "updated_by": user,
                        }
                    )
                    action = 'created' if created else 'updated'
                    stats[action] += 1
                    self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} Section: {section['Section']} ({time.time() - start_time:.2f}s)"))
                    logger.info(f"{action.capitalize()} Section: {section['Section']}")

                    for division in section["Divisions"]:
                        try:
                            division_obj, created = Industry.objects.get_or_create(
                                code=division["Division"],
                                defaults={
                                    "description": division["Description"],
                                    "level": "DIVISION",
                                    "sector": sector_map.get(section["Section"], "TERTIARY"),
                                    "parent": section_obj,
                                    "created_by": user,
                                    "updated_by": user,
                                }
                            )
                            action = 'created' if created else 'updated'
                            stats[action] += 1
                            self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} Division: {division['Division']} ({time.time() - start_time:.2f}s)"))
                            logger.info(f"{action.capitalize()} Division: {division['Division']}")

                            for group in division["Groups"]:
                                try:
                                    group_obj, created = Industry.objects.get_or_create(
                                        code=group["Group"],
                                        defaults={
                                            "description": group["Description"],
                                            "level": "GROUP",
                                            "sector": sector_map.get(section["Section"], "TERTIARY"),
                                            "parent": division_obj,
                                            "created_by": user,
                                            "updated_by": user,
                                        }
                                    )
                                    action = 'created' if created else 'updated'
                                    stats[action] += 1
                                    self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} Group: {group['Group']} ({time.time() - start_time:.2f}s)"))
                                    logger.info(f"{action.capitalize()} Group: {group['Group']}")

                                    for cls in group["Classes"]:
                                        try:
                                            class_obj, created = Industry.objects.get_or_create(
                                                code=cls["Class"],
                                                defaults={
                                                    "description": cls["Description"],
                                                    "level": "CLASS",
                                                    "sector": sector_map.get(section["Section"], "TERTIARY"),
                                                    "parent": group_obj,
                                                    "created_by": user,
                                                    "updated_by": user,
                                                }
                                            )
                                            action = 'created' if created else 'updated'
                                            stats[action] += 1
                                            self.stdout.write(self.style.SUCCESS(f"{action.capitalize()} Class: {cls['Class']} ({time.time() - start_time:.2f}s)"))
                                            logger.info(f"{action.capitalize()} Class: {cls['Class']}")
                                        except ValidationError as e:
                                            stats['skipped'].append({'code': cls["Class"], 'reason': str(e)})
                                            warning_msg = f"Skipping class {cls['Class']}: {e} ({time.time() - start_time:.2f}s)"
                                            self.stderr.write(self.style.WARNING(warning_msg))
                                            logger.warning(warning_msg)
                                            continue
                                except ValidationError as e:
                                    stats['skipped'].append({'code': group["Group"], 'reason': str(e)})
                                    warning_msg = f"Skipping group {group['Group']}: {e} ({time.time() - start_time:.2f}s)"
                                    self.stderr.write(self.style.WARNING(warning_msg))
                                    logger.warning(warning_msg)
                                    continue
                        except ValidationError as e:
                            stats['skipped'].append({'code': division["Division"], 'reason': str(e)})
                            warning_msg = f"Skipping division {division['Division']}: {e} ({time.time() - start_time:.2f}s)"
                            self.stderr.write(self.style.WARNING(warning_msg))
                            logger.warning(warning_msg)
                            continue
                except ValidationError as e:
                    stats['skipped'].append({'code': section["Section"], 'reason': str(e)})
                    warning_msg = f"Skipping section {section['Section']}: {e} ({time.time() - start_time:.2f}s)"
                    self.stderr.write(self.style.WARNING(warning_msg))
                    logger.warning(warning_msg)
                    continue

        self.stdout.write(self.style.SUCCESS(f"Industry Import summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Created: {stats['created']}")
        self.stdout.write(f"  - Updated: {stats['updated']}")
        self.stdout.write(f"  - Skipped: {len(stats['skipped'])}")
        logger.info(f"Industry Import summary: Total records={stats['total']}, Created={stats['created']}, Updated={stats['updated']}, Skipped={len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - Code: {skipped['code']}): {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        self.stdout.write(self.style.SUCCESS(f"Industries Imported in {time.time() - start_time:.2f}s"))
        logger.info(f"Industries Imported in {time.time() - start_time:.2f}s")
