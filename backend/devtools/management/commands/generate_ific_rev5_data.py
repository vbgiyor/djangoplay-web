import argparse
import csv
import json
import logging
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate JSON file from ISIC Rev 4 CSV data specified in .env (ISIC_REV5_SOURCE).

Expected .env keys:
    DATA_DIR, ISIC_REV5_SOURCE, ISIC_REV5_JSON

Example usage:
    ./manage.py generate_ific_REV5_data                     # Loads ISIC data from ISIC_REV5_SOURCE and saves to ISIC_REV5_JSON
    ./manage.py generate_ific_REV5_data --file custom.csv   # Uses custom CSV file
"""

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--file",
            type=str,
            help="Override ISIC_REV5_SOURCE path with a custom CSV file",
        )

    def handle(self, *args, **options):
        start_time = time.time()
        self.options = options
        stats = {'created': 0, 'skipped': [], 'total': 0}

        self.stdout.write(f"Starting ISIC JSON generation... ({time.time() - start_time:.2f}s)")
        logger.info("Starting ISIC JSON generation")

        # Load environment variables
        json_filename = self.options.get('file')
        env_data = load_env_paths(env_var='ISIC_REV5_SOURCE', file=json_filename, require_exists=True)
        isic_source = env_data.get('ISIC_REV5_SOURCE')
        env_data = load_env_paths(env_var='ISIC_REV5_JSON', require_exists=False)
        isic_json = env_data.get('ISIC_REV5_JSON')

        if not isic_source or not isic_json:
            error_msg = f"Failed to load ISIC_REV5_SOURCE or ISIC_REV5_JSON path ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        self.stdout.write(f"ISIC Source Path: {isic_source}")
        self.stdout.write(f"ISIC JSON Path: {isic_json}")

        # Get admin user for audit purposes
        user_start = time.time()
        Employee = get_user_model()
        try:
            global admin_user
            admin_user = Employee.objects.get(id=1)
        except Employee.DoesNotExist:
            error_msg = f"User with id=1 not found. Proceeding without user. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.WARNING(error_msg))
            logger.warning(error_msg)
            admin_user = None
            return
        self.stdout.write(f"Admin user loaded in {time.time() - user_start:.2f}s")

        # Initialize the hierarchical structure
        industries = []
        current_section = None
        current_division = None
        current_group = None

        # Read CSV and build JSON structure
        try:
            with open(isic_source, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=',', quotechar='"')
                next(reader, None)  # Skip header row ("Code","Description")

                for index, row in enumerate(reader, 1):
                    stats['total'] += 1
                    if not row or len(row) != 2:
                        stats['skipped'].append({'index': index, 'reason': f"Invalid row: {row}"})
                        warning_msg = f"Skipping invalid row at index {index}: {row} ({time.time() - start_time:.2f}s)"
                        self.stderr.write(self.style.WARNING(warning_msg))
                        logger.warning(warning_msg)
                        continue

                    code, description = row
                    code = code.strip()
                    description = description.strip()

                    if not code or not description:
                        stats['skipped'].append({'index': index, 'reason': f"Empty code or description: {row}"})
                        warning_msg = f"Skipping empty code or description at index {index}: {row} ({time.time() - start_time:.2f}s)"
                        self.stderr.write(self.style.WARNING(warning_msg))
                        logger.warning(warning_msg)
                        continue

                    try:
                        # Determine level based on code length
                        if len(code) == 1:  # Section
                            current_section = {
                                'Section': code,
                                'Description': description,
                                'Divisions': []
                            }
                            current_division = None
                            current_group = None
                            industries.append(current_section)
                            stats['created'] += 1
                            self.stdout.write(self.style.SUCCESS(f"Created section: {code} ({time.time() - start_time:.2f}s)"))
                            logger.info(f"Created section: {code}")
                        elif len(code) == 2:  # Division
                            current_division = {
                                'Division': code,
                                'Description': description,
                                'Groups': []
                            }
                            current_group = None
                            if current_section:
                                current_section['Divisions'].append(current_division)
                                stats['created'] += 1
                                self.stdout.write(self.style.SUCCESS(f"Created division: {code} ({time.time() - start_time:.2f}s)"))
                                logger.info(f"Created division: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Division {code} found without a section"})
                                warning_msg = f"Skipping division {code} at index {index}: No parent section ({time.time() - start_time:.2f}s)"
                                self.stderr.write(self.style.WARNING(warning_msg))
                                logger.warning(warning_msg)
                        elif len(code) == 3:  # Group
                            current_group = {
                                'Group': code,
                                'Description': description,
                                'Classes': []
                            }
                            if current_division:
                                current_division['Groups'].append(current_group)
                                stats['created'] += 1
                                self.stdout.write(self.style.SUCCESS(f"Created group: {code} ({time.time() - start_time:.2f}s)"))
                                logger.info(f"Created group: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Group {code} found without a division"})
                                warning_msg = f"Skipping group {code} at index {index}: No parent division ({time.time() - start_time:.2f}s)"
                                self.stderr.write(self.style.WARNING(warning_msg))
                                logger.warning(warning_msg)
                        elif len(code) == 4:  # Class
                            class_item = {
                                'Class': code,
                                'Description': description
                            }
                            if current_group:
                                current_group['Classes'].append(class_item)
                                stats['created'] += 1
                                self.stdout.write(self.style.SUCCESS(f"Created class: {code} ({time.time() - start_time:.2f}s)"))
                                logger.info(f"Created class: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Class {code} found without a group"})
                                warning_msg = f"Skipping class {code} at index {index}: No parent group ({time.time() - start_time:.2f}s)"
                                self.stderr.write(self.style.WARNING(warning_msg))
                                logger.warning(warning_msg)
                        else:
                            stats['skipped'].append({'index': index, 'reason': f"Invalid code length for {code}"})
                            warning_msg = f"Skipping code {code} at index {index}: Invalid code length ({time.time() - start_time:.2f}s)"
                            self.stderr.write(self.style.WARNING(warning_msg))
                            logger.warning(warning_msg)

                    except Exception as e:
                        stats['skipped'].append({'index': index, 'reason': f"Error processing code {code}: {str(e)}"})
                        warning_msg = f"Skipping code {code} at index {index}: {str(e)} ({time.time() - start_time:.2f}s)"
                        self.stderr.write(self.style.WARNING(warning_msg))
                        logger.warning(warning_msg, exc_info=True)

            # Ensure output directory exists
            Path(isic_json).parent.mkdir(parents=True, exist_ok=True)

            # Write to JSON file
            with open(isic_json, 'w', encoding='utf-8') as f:
                json.dump({'isic_REV5': industries}, f, indent=2, ensure_ascii=False)

            self.stdout.write(self.style.SUCCESS(f"Successfully generated JSON at {isic_json} ({time.time() - start_time:.2f}s)"))
            logger.info(f"Successfully generated JSON at {isic_json}")

        except FileNotFoundError:
            error_msg = f"Source file {isic_source} not found ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return
        except PermissionError:
            error_msg = f"Permission denied accessing {isic_source} or writing to {isic_json} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return
        except Exception as e:
            error_msg = f"Error processing file: {str(e)} ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            return

        # Output summary
        self.stdout.write(self.style.SUCCESS(f"ISIC JSON Generation Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total']}")
        self.stdout.write(f"  - Records created: {stats['created']}")
        self.stdout.write(f"  - Records skipped: {len(stats['skipped'])}")
        logger.info(f"ISIC JSON Generation Summary: Total records={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - Index: {skipped['index']}: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        self.stdout.write(self.style.SUCCESS(f"ISIC JSON Generated in {time.time() - start_time:.2f}s"))
        logger.info(f"ISIC JSON Generated in {time.time() - start_time:.2f}s")
