import argparse
import csv
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.general.normalize_text import normalize_text

logger = logging.getLogger(__name__)

class RawStringEncoder(json.JSONEncoder):

    """Custom JSON encoder to prevent escaping backslashes in specific fields."""

    def encode(self, obj):
        if isinstance(obj, dict) and 'Postal Code Regex' in obj:
            # Replace escaped backslashes with single backslashes for regex
            obj['Postal Code Regex'] = obj['Postal Code Regex'].replace('\\\\', '\\')
        return super().encode(obj)

class Command(BaseCommand):
    help = """Convert a tab-separated GeoNames text files, ISIC CSV file to JSON format.
Supported types: regions, subregions, cities, industries, country, timezones

Example usage:
    ./manage.py generate_json --cities --source geonames --batch-size 60000
    ./manage.py generate_json --regions --source geonames
    ./manage.py generate_json --subregions --source geonames
    ./manage.py generate_json --industries --source isic --batch-size 1000
    ./manage.py generate_json --country --source geonames
    ./manage.py generate_json --timezones --source geonames
"""

    CONFIG = {
        'regions': {
            'source_file_columns': ['code_field', 'name', 'asciiname', 'geoname_id'],
            'json_columns': ['country_code', 'admin1_code', 'admin2_code', 'name', 'asciiname', 'geoname_id'],
            'file_extension': '.txt'
        },
        'subregions': {
            'source_file_columns': ['code_field', 'name', 'asciiname', 'geoname_id'],
            'json_columns': ['country_code', 'admin1_code', 'admin2_code', 'name', 'asciiname', 'geoname_id'],
            'file_extension': '.txt'
        },
        'cities': {
            'source_file_columns': [
                'geoname_id', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude',
                'feature_class', 'feature_code', 'country_code', 'cc2', 'admin1_code',
                'admin2_code', 'admin3_code', 'admin4_code', 'population', 'elevation',
                'dem', 'timezone', 'modification_date'
            ],
            'json_columns': [
                'geoname_id', 'name', 'asciiname', 'alternatenames', 'latitude', 'longitude',
                'country_code', 'admin1_code', 'admin2_code', 'admin3_code', 'admin4_code',
                'population', 'timezone'
            ],
            'valid_feature_class': {'P', 'A'},
            'valid_feature_codes': {
                'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLA5', 'PPLC', 'PPLCH', 'PPLF', 'PPLG',
                'PPLH', 'PPLL', 'PPLQ', 'PPLR', 'PPLS', 'PPLW', 'PPLX', 'ADM1', 'ADM2', 'ADM3', 'ADM4'
            },
            'file_extension': '.txt'
        },
        'industries': {
            'source_file_columns': ['Code', 'Description'],
            'file_extension': '.csv'
        },
        'country': {
            'source_file_columns': [
                'ISO', 'ISO3', 'ISO-Numeric', 'fips', 'Country', 'Capital',
                'Area(in sq km)', 'Population', 'Continent', 'tld',
                'CurrencyCode', 'CurrencyName', 'Phone', 'Postal Code Format',
                'Postal Code Regex', 'Languages', 'geonameid', 'neighbours',
                'EquivalentFipsCode'
            ],
            'file_extension': '.txt'
        },
        'timezones': {
            'source_file_columns': [
                'CountryCode', 'TimeZoneId', 'GMT offset 1. Jan 2025',
                'DST offset 1. Jul 2025', 'rawOffset (independant of DST)'
            ],
            'file_extension': '.txt'
        }
    }

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.RawTextHelpFormatter
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--regions",
            action='store_const',
            const='regions',
            dest='type',
            help="Process regions data"
        )
        group.add_argument(
            "--subregions",
            action='store_const',
            const='subregions',
            dest='type',
            help="Process subregions data"
        )
        group.add_argument(
            "--cities",
            action='store_const',
            const='cities',
            dest='type',
            help="Process cities data"
        )
        group.add_argument(
            "--industries",
            action='store_const',
            const='industries',
            dest='type',
            help="Process ISIC industries data"
        )
        group.add_argument(
            "--country",
            action='store_const',
            const='country',
            dest='type',
            help="Process country data"
        )
        group.add_argument(
            "--timezones",
            action='store_const',
            const='timezones',
            dest='type',
            help="Process timezone data"
        )
        parser.add_argument(
            "--source",
            type=str,
            required=True,
            help="Specify source name (e.g., geonames, isic)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Batch size for processing (default: 5000)"
        )
        parser.add_argument(
            "--input-file",
            type=str,
            help="Override source file path"
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            help="Override destination JSON directory"
        )

    def process_code_field(self, value: str, line_num: int, entry: Dict, input_type: str) -> None:
        """Process code_field for regions and subregions."""
        try:
            code_parts = value.split('.')
            if len(code_parts) < 2:
                raise ValidationError(f"Invalid code_field format: {value}")
            entry['country_code'] = code_parts[0]
            entry['admin1_code'] = code_parts[1]
            if input_type == 'subregions' and len(code_parts) > 2:
                entry['admin2_code'] = code_parts[2]
            else:
                entry['admin2_code'] = None
        except ValueError as e:
            raise ValidationError(f"Invalid code_field format: {e}")

    def validate_entry(self, entry: Dict, input_type: str, line_num: int) -> tuple[Optional[Dict], Optional[Tuple[str, str]]]:
        """Validate entry based on input type."""
        if input_type == 'cities':
            if not entry.get('name'):
                return None, (entry.get('feature_class', 'unknown'), entry.get('feature_code', 'unknown'))
            feature_class = entry.get('feature_class')
            feature_code = entry.get('feature_code')
            if feature_class not in self.CONFIG['cities']['valid_feature_class'] or \
               feature_code not in self.CONFIG['cities']['valid_feature_codes']:
                return None, (feature_class, feature_code)
        return entry, None

    def process_txt_line(self, fields: List[str], columns: List[str], input_type: str, line_num: int) -> tuple[Optional[Dict], Optional[Tuple[str, str]]]:
        """Process a single line from a text file."""
        try:
            entry = {}
            for idx, column in enumerate(columns):
                if idx >= len(fields):
                    value = ''
                else:
                    value = fields[idx].strip() if fields[idx] else ''
                if input_type in ['regions', 'subregions'] and column == 'code_field':
                    self.process_code_field(value, line_num, entry, input_type)
                elif input_type in ['country', 'timezones']:
                    if input_type == 'country' and column in ['Country', 'Capital', 'tld', 'CurrencyName', 'Languages', 'neighbours']:
                        entry[column] = normalize_text(value) if value else ''
                    elif input_type == 'country' and column == 'Postal Code Regex':
                        entry[column] = value
                    elif input_type == 'timezones' and column == 'TimeZoneId':
                        entry[column] = normalize_text(value) if value else ''
                    elif column in ['GMT offset 1. Jan 2025', 'DST offset 1. Jul 2025', 'rawOffset (independant of DST)']:
                        entry[column] = float(value) if value and value.replace('.', '', 1).replace('-', '', 1).isdigit() else None
                    elif column in ['Area(in sq km)', 'Population', 'geonameid']:
                        entry[column] = value if value else ''
                    else:
                        entry[column] = value
                elif column in self.CONFIG[input_type]['json_columns']:
                    if column in ['name', 'asciiname', 'place_name', 'admin1_name', 'admin2_name', 'admin3_name', 'alternatenames']:
                        entry[column] = normalize_text(value) if value else None
                    elif column in ['latitude', 'longitude']:
                        entry[column] = float(value) if value and value.replace('.', '', 1).replace('-', '', 1).isdigit() else None
                    else:
                        entry[column] = value
                elif column in ['feature_class', 'feature_code']:
                    entry[column] = value
            if not entry:
                return None, (None, None)
            return self.validate_entry(entry, input_type, line_num)
        except ValidationError as e:
            logger.warning(f"Line {line_num} skipped: {str(e)}")
            return None, (None, None)

    def process_csv_line(self, row: List[str], line_num: int) -> tuple[Optional[Dict], Optional[str]]:
        """Process a single row from an ISIC CSV file."""
        try:
            if len(row) != 2:
                return None, f"Invalid row: {row}"
            code, description = row
            code = code.strip()
            description = normalize_text(description.strip())
            if not code or not description:
                return None, f"Empty code or description: {row}"
            return {'Code': code, 'Description': description}, None
        except Exception as e:
            return None, f"Error processing row: {str(e)}"

    def _write_batch(self, output_file: str, data_entries: List[Dict], first_entry: bool) -> None:
        """Write a batch of entries to the JSON file as part of a single array."""
        if not data_entries:
            return
        with open(output_file, 'a', encoding='utf-8') as file:
            for i, entry in enumerate(data_entries):
                entry_json = json.dumps(entry, cls=RawStringEncoder, indent=4, ensure_ascii=False)
                if not first_entry or i > 0:
                    file.write(',\n')
                file.write(entry_json)

    def process_industries_csv(self, input_file: str, output_file: str, start_time: float) -> Dict:
        """Process ISIC CSV file and generate a hierarchical JSON file."""
        stats = {'processed': 0, 'skipped': [], 'total': 0}
        self.stdout.write(f"Starting industries conversion... ({time.time() - start_time:.2f}s)")
        logger.info("Starting industries conversion")

        if not os.path.exists(input_file):
            self.stderr.write(self.style.ERROR(f"Input file {input_file} not found"))
            logger.error(f"Input file {input_file} not found")
            return stats

        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        industries = []
        current_section = None
        current_division = None
        current_group = None

        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=',', quotechar='"')
                next(reader, None)  # Skip header
                for index, row in enumerate(reader, 1):
                    stats['total'] += 1
                    entry, skip_reason = self.process_csv_line(row, index)
                    if not entry:
                        stats['skipped'].append({'index': index, 'reason': skip_reason})
                        logger.warning(f"Skipping row {index}: {skip_reason}")
                        continue

                    code = entry['Code']
                    description = entry['Description']
                    try:
                        if len(code) == 1:
                            current_section = {
                                'Section': code,
                                'Description': description,
                                'Divisions': []
                            }
                            current_division = None
                            current_group = None
                            industries.append(current_section)
                            stats['processed'] += 1
                            logger.info(f"Created section: {code}")
                        elif len(code) == 2:
                            current_division = {
                                'Division': code,
                                'Description': description,
                                'Groups': []
                            }
                            current_group = None
                            if current_section:
                                current_section['Divisions'].append(current_division)
                                stats['processed'] += 1
                                logger.info(f"Created division: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Division {code} without section"})
                                logger.warning(f"Skipping division {code}: No section")
                        elif len(code) == 3:
                            current_group = {
                                'Group': code,
                                'Description': description,
                                'Classes': []
                            }
                            if current_division:
                                current_division['Groups'].append(current_group)
                                stats['processed'] += 1
                                logger.info(f"Created group: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Group {code} without division"})
                                logger.warning(f"Skipping group {code}: No division")
                        elif len(code) == 4:
                            class_item = {
                                'Class': code,
                                'Description': description
                            }
                            if current_group:
                                current_group['Classes'].append(class_item)
                                stats['processed'] += 1
                                logger.info(f"Created class: {code}")
                            else:
                                stats['skipped'].append({'index': index, 'reason': f"Class {code} without group"})
                                logger.warning(f"Skipping class {code}: No group")
                        else:
                            stats['skipped'].append({'index': index, 'reason': f"Invalid code length: {code}"})
                            logger.warning(f"Skipping code {code}: Invalid length")
                    except Exception as e:
                        stats['skipped'].append({'index': index, 'reason': f"Error processing code {code}: {str(e)}"})
                        logger.warning(f"Skipping code {code}: {str(e)}")

            if industries:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump({'isic': industries}, f, indent=2, ensure_ascii=False)
                    self.stdout.write(self.style.SUCCESS(f"Generated {output_file} with {stats['processed']} entries ({time.time() - start_time:.2f}s)"))
                    logger.info(f"Generated {output_file} with {stats['processed']} entries")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error writing to {output_file}: {str(e)}"))
                    logger.error(f"Error writing to {output_file}: {str(e)}")
            else:
                self.stderr.write(self.style.WARNING("No data processed, JSON file not generated"))
                logger.warning("No data processed, JSON file not generated")

        except PermissionError:
            self.stderr.write(self.style.ERROR(f"Permission denied: {input_file}"))
            logger.error(f"Permission denied: {input_file}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing {input_file}: {str(e)}"))
            logger.error(f"Error processing {input_file}: {str(e)}")
        return stats

    def process_country_txt(self, input_file: str, output_file: str, start_time: float) -> Dict:
        """Process countryInfo.txt file and generate a JSON file."""
        stats = {'processed': 0, 'skipped': [], 'total': 0}
        self.stdout.write(f"Starting country conversion... ({time.time() - start_time:.2f}s)")
        logger.info("Starting country conversion")

        if not os.path.exists(input_file):
            self.stderr.write(self.style.ERROR(f"Input file {input_file} not found"))
            logger.error(f"Input file {input_file} not found")
            return stats

        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        countries = []
        columns = self.CONFIG['country']['source_file_columns']

        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    if line.strip() and not line.startswith('#'):
                        stats['total'] += 1
                        reader = csv.reader([line], delimiter='\t', quotechar=None)
                        fields = next(reader)
                        if len(fields) >= len(columns):
                            entry, _ = self.process_txt_line(fields, columns, 'country', line_num)
                            if entry:
                                countries.append(entry)
                                stats['processed'] += 1
                            else:
                                stats['skipped'].append({'line': line_num, 'reason': 'Validation failed'})
                        else:
                            stats['skipped'].append({'line': line_num, 'reason': f"Insufficient fields ({len(fields)})"})
                            logger.warning(f"Line {line_num} skipped: Insufficient fields ({len(fields)})")
        except PermissionError:
            self.stderr.write(self.style.ERROR(f"Permission denied: {input_file}"))
            logger.error(f"Permission denied: {input_file}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing {input_file}: {str(e)}"))
            logger.error(f"Error processing {input_file}: {str(e)}")

        if countries:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('[\n')
                    for i, entry in enumerate(countries):
                        entry_json = json.dumps(entry, cls=RawStringEncoder, indent=4, ensure_ascii=False)
                        if i > 0:
                            f.write(',\n')
                        f.write(entry_json)
                    f.write(']\n')
                self.stdout.write(self.style.SUCCESS(f"Generated {output_file} with {stats['processed']} entries ({time.time() - start_time:.2f}s)"))
                logger.info(f"Generated {output_file} with {stats['processed']} entries")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error writing to {output_file}: {str(e)}"))
                logger.error(f"Error writing to {output_file}: {str(e)}")
        else:
            self.stderr.write(self.style.WARNING("No data processed, JSON file not generated"))
            logger.warning("No data processed, JSON file not generated")

        return stats

    def process_timezones_txt(self, input_file: str, output_file: str, start_time: float) -> Dict:
        """Process timeZones.txt file and generate a JSON file."""
        stats = {'processed': 0, 'skipped': [], 'total': 0}
        self.stdout.write(f"Starting timezones conversion... ({time.time() - start_time:.2f}s)")
        logger.info("Starting timezones conversion")

        if not os.path.exists(input_file):
            self.stderr.write(self.style.ERROR(f"Input file {input_file} not found"))
            logger.error(f"Input file {input_file} not found")
            return stats

        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        timezones = []
        columns = self.CONFIG['timezones']['source_file_columns']
        header_row = '\t'.join(columns).lower()

        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#') or line.lower() == header_row:
                        stats['skipped'].append({'line': line_num, 'reason': 'Header or comment line'})
                        logger.debug(f"Skipping line {line_num}: Header or comment")
                        continue
                    stats['total'] += 1
                    reader = csv.reader([line], delimiter='\t', quotechar=None)
                    fields = next(reader)
                    if len(fields) >= len(columns):
                        entry, _ = self.process_txt_line(fields, columns, 'timezones', line_num)
                        if entry:
                            timezones.append(entry)
                            stats['processed'] += 1
                        else:
                            stats['skipped'].append({'line': line_num, 'reason': 'Validation failed'})
                    else:
                        stats['skipped'].append({'line': line_num, 'reason': f"Insufficient fields ({len(fields)})"})
                        logger.warning(f"Line {line_num} skipped: Insufficient fields ({len(fields)})")

            if timezones:
                try:
                    with open(output_file, 'w', encoding='utf-8'):
                        json.dump(timezones, cls=RawStringEncoder, indent=4, ensure_ascii=False)
                    self.stdout.write(self.style.SUCCESS(f"Generated {output_file} with {stats['processed']} entries ({time.time() - start_time:.2f}s)"))
                    logger.info(f"Generated {output_file} with {stats['processed']} entries")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error writing to {output_file}: {str(e)}"))
                    logger.error(f"Error writing to {output_file}: {str(e)}")
            else:
                self.stderr.write(self.style.WARNING("No data processed, JSON file not generated"))
                logger.warning("No data processed, JSON file not generated")

        except PermissionError:
            self.stderr.write(self.style.ERROR(f"Permission denied: {input_file}"))
            logger.error(f"Permission denied: {input_file}")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing {input_file}: {str(e)}"))
            logger.error(f"Error processing {input_file}: {str(e)}")
        return stats

    def process_input_type(self, input_type: str, source: str, batch_size: int, input_file: str, output_dir: str, start_time: float) -> Dict:
        """Process input type and generate JSON files."""
        if input_type == 'industries':
            return self.process_industries_csv(input_file, output_dir, start_time)
        elif input_type == 'country':
            return self.process_country_txt(input_file, output_dir, start_time)
        elif input_type == 'timezones':
            return self.process_timezones_txt(input_file, output_dir, start_time)

        stats = {'processed': 0, 'skipped': [], 'total': 0, 'countries': {}, 'skipped_features': set()}
        self.stdout.write(f"Starting {input_type} conversion... ({time.time() - start_time:.2f}s)")
        logger.info(f"Starting {input_type} conversion")

        if not input_file.endswith(self.CONFIG[input_type]['file_extension']):
            self.stderr.write(self.style.ERROR(f"Input file must be a {self.CONFIG[input_type]['file_extension']} file"))
            logger.error(f"Input file {input_type} is not a {self.CONFIG[input_type]['file_extension']} file")
            return stats

        os.makedirs(output_dir, exist_ok=True)
        country_entries = {}
        columns = self.CONFIG[input_type]['source_file_columns']
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    if not line.strip() or line.startswith('#'):
                        continue
                    stats['total'] += 1
                    reader = csv.reader([line], delimiter='\t', quotechar=None)
                    fields = next(reader)
                    if len(fields) >= len(columns):
                        entry, skipped_feature = self.process_txt_line(fields, columns, input_type, line_num)
                        if entry:
                            country_code = entry.get('country_code')
                            if country_code:
                                if country_code not in country_entries:
                                    country_entries[country_code] = []
                                country_entries[country_code].append(entry)
                                stats['processed'] += 1
                                stats['countries'].setdefault(country_code, {'processed': 0, 'skipped': 0})
                                stats['countries'][country_code]['processed'] += 1
                            else:
                                stats['skipped'].append({'line': line_num, 'reason': 'No country code'})
                                stats['countries'].setdefault('unknown', {'processed': 0, 'skipped': 0})
                                stats['countries']['unknown']['skipped'] += 1
                        else:
                            stats['skipped'].append({'line': line_num, 'reason': 'Validation failed'})
                            stats['countries'].setdefault('unknown', {'processed': 0, 'skipped': 0})
                            stats['countries']['unknown']['skipped'] += 1
                            if skipped_feature and skipped_feature[0] and skipped_feature[1]:
                                stats['skipped_features'].add(skipped_feature)
                    else:
                        stats['skipped'].append({'line': line_num, 'reason': f"Insufficient fields ({len(fields)})"})
                        logger.warning(f"Line {line_num} skipped: Insufficient fields ({len(fields)})")

            self.stdout.write(self.style.NOTICE(f"Processed {stats['processed']} entries, skipped {len(stats['skipped'])} entries"))
            for country_code, country_stats in stats['countries'].items():
                self.stdout.write(self.style.NOTICE(f"Country {country_code}: {country_stats['processed']} processed, {country_stats['skipped']} skipped"))
            if stats['skipped_features']:
                self.stdout.write(self.style.WARNING("Unique skipped feature_class and feature_code combinations:"))
                for feature_class, feature_code in sorted(stats['skipped_features']):
                    self.stdout.write(self.style.WARNING(f"  {feature_class}.{feature_code}"))

            for country_code, entries in country_entries.items():
                output_file = os.path.join(output_dir, f"{country_code}.json")
                try:
                    with open(output_file, 'w', encoding='utf-8') as file:
                        file.write('[\n')
                    first_entry = True
                    for i in range(0, len(entries), batch_size):
                        batch = entries[i:i + batch_size]
                        self._write_batch(output_file, batch, first_entry)
                        first_entry = False
                    with open(output_file, 'a', encoding='utf-8') as file:
                        file.write(']\n')
                    self.stdout.write(self.style.SUCCESS(f"Generated {output_file} with {len(entries)} entries ({time.time() - start_time:.2f}s)"))
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to write {output_file}: {str(e)}"))
                    logger.error(f"Failed to write {output_file}: {str(e)}")
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Input file {input_file} not found"))
            logger.error(f"Input file {input_file} not found")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing {input_file}: {str(e)}"))
            logger.error(f"Error processing {input_file}: {str(e)}")
        return stats

    def handle(self, *args, **options) -> None:
        start_time = time.time()
        source = normalize_text(options['source']).lower()
        input_type = options['type']
        batch_size = options['batch_size']

        env_mapping = {
            'regions': ('REGIONS_TXT', 'REGIONS_JSON'),
            'subregions': ('SUBREGIONS_TXT', 'SUBREGIONS_JSON'),
            'cities': ('CITIES_TXT', 'CITIES_JSON'),
            'industries': ('INDUSTRIES_CSV', 'INDUSTRIES_JSON'),
            'country': ('COUNTRY_INFO_TXT', 'COUNTRY_INFO_JSON'),
            'timezones': ('TIMEZONE_TXT', 'TIMEZONE_JSON')
        }

        input_env, output_env = env_mapping.get(input_type, (None, None))
        if not input_env or not output_env:
            self.stderr.write(self.style.ERROR(f"Invalid input type: {input_type}"))
            logger.error(f"Invalid input type: {input_type}")
            return

        env_data = {}
        env_data.update(load_env_paths(env_var=input_env, file=options.get('input_file'), require_exists=True))
        env_data.update(load_env_paths(env_var=output_env, file=options.get('output_dir'), require_exists=False))
        if not env_data.get(input_env) or not env_data.get(output_env):
            self.stderr.write(self.style.ERROR(f"Failed to load paths for {input_type}"))
            logger.error(f"Failed to load paths for {input_type}")
            return

        self.process_input_type(
            input_type, source, batch_size, env_data[input_env], env_data[output_env], start_time
        )

        self.stdout.write(self.style.SUCCESS(f"Conversion completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Conversion for {input_type} completed in {time.time() - start_time:.2f}s")
