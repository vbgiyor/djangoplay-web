import argparse
import logging
import time
from pathlib import Path

import ijson
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q
from django.utils.text import slugify
from locations.models.custom_city import CustomCity
from locations.models.custom_country import CustomCountry
from locations.models.custom_region import CustomRegion
from locations.models.custom_subregion import CustomSubRegion
from locations.models.location import Location
from locations.models.timezone import Timezone
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.geoservices import get_country_administrative_category

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """📦 Sync cities data from JSON file for a specified country.
    Example usage:
        ./manage.py import_cities --datasource geonames --country NZ --batch-size 60000
        ./manage.py import_cities --datasource geonames --country JP --batch-size 60000
    """

    ALLOWED_FEATURE_CODES = {
        'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLA5', 'PPLC', 'PPLCH', 'PPLF', 'PPLG', 'PPLH', 'PPLL', 'PPLQ', 'PPLR', 'PPLS', 'PPLW', 'PPLX', 'ADM1', 'ADM2', 'ADM3', 'ADM4'
    }

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--datasource",
            type=str,
            required=True,
            help="Data source for location_source field (e.g., 'geonames' or 'GOI')",
        )
        parser.add_argument(
            "--country",
            type=str,
            required=True,
            help="Specify country code or name (e.g., NZ, Japan)"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50000,  # Increased default batch size for better performance
            help="Batch size for processing (default: 50000)"
        )
        parser.add_argument(
            "--input-file",
            type=str,
            help="Override source file path"
        )
        parser.add_argument(
            "--output-file",
            type=str,
            help="Override destination JSON file"
        )

    def safe_strip(self, value):
        """Safely strip a value if it's a string, otherwise return None."""
        return value.strip() if isinstance(value, str) and value.strip() else None

    def safe_float(self, value):
        """Safely convert a value to float, returning None if invalid."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def safe_int(self, value):
        """Safely convert a value to int, returning None if invalid."""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def generate_unique_slug(self, name, existing_slugs):
        """Generate a unique slug for the given name."""
        slug = slugify(name)[:190]  # Leave room for suffixes
        counter = 1
        original_slug = slug
        while slug in existing_slugs:
            slug = f"{original_slug}-{counter}"
            counter += 1
        return slug

    def update_admin_codes(self, country, admin_codes_to_add, user):
        """Update admin_codes in CustomCountry in bulk."""
        admin_codes = country.admin_codes or {
            'admin1_codes': [], 'admin2_codes': [], 'admin3_codes': [], 'admin4_codes': []
        }
        updated = False
        for level, codes in admin_codes_to_add.items():
            key = f"{level}_codes"
            if not isinstance(admin_codes.get(key), list):
                admin_codes[key] = []
            for code in codes:
                if code and code.isdigit() and code not in admin_codes[key]:
                    admin_codes[key].append(code)
                    updated = True
        if updated:
            admin_codes = {k: sorted(v) for k, v in admin_codes.items()}
            country.admin_codes = admin_codes
            country.save(user=user, skip_validation=True)

    def get_similar_region(self, region_name, country_id, admin1_code):
        """Find a region with a similar name using pg_trgm similarity."""
        normalized_region_name = normalize_text(region_name)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, code, similarity(name, %s) AS sim_score
                FROM locations_customregion
                WHERE country_id = %s AND similarity(name, %s) >= 0.5 AND similarity(name, %s) <= 0.9
                ORDER BY sim_score DESC
                LIMIT 1
            """, [normalized_region_name, country_id, normalized_region_name, normalized_region_name])
            result = cursor.fetchone()
            if result:
                return CustomRegion.objects.get(id=result[0])
        return None

    def get_similar_subregion(self, subregion_name, region_id, admin2_code):
        """Find a subregion with a similar name using pg_trgm similarity."""
        normalized_subregion_name = normalize_text(subregion_name)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, code, similarity(name, %s) AS sim_score
                FROM locations_customsubregion
                WHERE region_id = %s AND similarity(name, %s) >= 0.5 AND similarity(name, %s) <= 0.9
                ORDER BY sim_score DESC
                LIMIT 1
            """, [normalized_subregion_name, region_id, normalized_subregion_name, normalized_subregion_name])
            result = cursor.fetchone()
            if result:
                return CustomSubRegion.objects.get(id=result[0])
        return None

    def get_country_code(self, country_input: str) -> str | None:
        """Normalize and validate country input, returning country code."""
        if ' ' in country_input:
            self.stderr.write(self.style.ERROR("Hey Smartpants, why don't you try simple country_code instead of full names. Currently I am out of mood to process names with spaces."))
            return None

        normalized_country = normalize_text(country_input).lower()
        try:
            country = CustomCountry.objects.filter(
                Q(name__iexact=normalized_country) | Q(asciiname__iexact=normalized_country) | Q(country_code__iexact=normalized_country)
            ).first()
            if not country:
                self.stderr.write(self.style.ERROR(f"No country found for input: {country_input}"))
                return None
            self.stdout.write(f"Proceeding with country '{country.name}'")
            return country.country_code
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error validating country: {str(e)}"))
            return None

    def load_subregion_names(self, subregion_file, country_code):
        """Load subregion names from JSON file by admin2_code."""
        subregion_names = {}
        try:
            with open(subregion_file, encoding='utf-8') as f:
                data = ijson.items(f, 'item')
                for record in data:
                    admin2_code = self.safe_strip(record.get('admin2_code'))
                    name = self.safe_strip(record.get('name'))
                    record_country_code = self.safe_strip(record.get('country_code'))
                    if admin2_code and name and record_country_code == country_code:
                        subregion_names[admin2_code] = normalize_text(name)
        except Exception as e:
            logger.warning(f"Failed to load subregion names from {subregion_file}: {str(e)}")
        return subregion_names

    def process_batch(self, batch, input_type, country, country_category, datasource, user, stats, region_cache, subregion_cache, city_cache, timezone_cache, region_slugs, subregion_slugs, city_slugs, admin_codes_to_add, subregion_names):
        # Collect new regions, subregions, cities, locations from the batch
        new_regions = []
        regions_to_update = []
        new_subregions = []
        subregions_to_update = []
        new_cities = []
        cities_to_update = []
        new_locations = []
        locations_to_update = []

        # First, collect and create regions
        potential_regions = {}
        for record_data in batch:
            admin1_code = self.safe_strip(record_data.get('admin1_code'))
            name = self.safe_strip(record_data.get('name'))
            if admin1_code:
                region_key = (country.id, admin1_code or '')
                if region_key not in region_cache:
                    region_name = record_data.get('admin1_name') or f"Region {admin1_code}" if input_type != 'regions' else name
                    normalized_region_name = normalize_text(region_name)
                    potential_regions.setdefault((admin1_code, normalized_region_name), region_name)

        # Create new regions
        for (admin1_code, normalized_region_name), region_name in potential_regions.items():
            region = self.get_similar_region(region_name, country.id, admin1_code)
            if not region:
                slug = self.generate_unique_slug(region_name, region_slugs)
                region = CustomRegion(
                    country_id=country.id,
                    code=admin1_code,
                    name=normalized_region_name,
                    created_by=user,
                    updated_by=user,
                    slug=slug,
                    location_source=datasource
                )
                new_regions.append(region)
                region_slugs.add(slug)
                stats['created_regions'] += 1

        if new_regions:
            CustomRegion.objects.bulk_create(new_regions, ignore_conflicts=True)
            # Refresh cache
            saved_regions = CustomRegion.objects.filter(
                country_id=country.id,
                code__in=[r.code for r in new_regions if r.code]
            ).only('id', 'country_id', 'code', 'name')
            for sr in saved_regions:
                region_cache[(sr.country_id, sr.code or '')] = sr

        # Now, with all regions available, collect subregions
        potential_subregions = {}
        for record_data in batch:
            admin1_code = self.safe_strip(record_data.get('admin1_code'))
            admin2_code = self.safe_strip(record_data.get('admin2_code'))
            region_key = (country.id, admin1_code or '')
            region = region_cache.get(region_key)
            if region and admin2_code:
                subregion_key = (region.id, admin2_code or '')
                if subregion_key not in subregion_cache:
                    subregion_name = subregion_names.get(admin2_code, record_data.get('admin2_name')) or f"{region.name} District {admin2_code or 'Unknown'}"
                    normalized_subregion_name = normalize_text(subregion_name)
                    potential_subregions.setdefault((region.id, admin2_code, normalized_subregion_name), subregion_name)

        # Create new subregions
        for (region_id, admin2_code, normalized_subregion_name), subregion_name in potential_subregions.items():
            subregion = self.get_similar_subregion(subregion_name, region_id, admin2_code)
            if not subregion:
                if country_category in ['unitary_state', 'quasi_federal_state'] and (not admin2_code or admin2_code == admin1_code):
                    region = region_cache.get((country.id, admin1_code))
                    subregion = CustomSubRegion(
                        region_id=region_id,
                        name=region.name,
                        code=admin2_code,
                        created_by=user,
                        updated_by=user,
                        slug=self.generate_unique_slug(region.name, subregion_slugs),
                        location_source=datasource
                    )
                else:
                    slug = self.generate_unique_slug(subregion_name, subregion_slugs)
                    subregion = CustomSubRegion(
                        region_id=region_id,
                        code=admin2_code,
                        name=normalized_subregion_name,
                        created_by=user,
                        updated_by=user,
                        slug=slug,
                        location_source=datasource
                    )
                    subregion_slugs.add(slug)
                new_subregions.append(subregion)
                stats['created_subregions'] += 1

        if new_subregions:
            CustomSubRegion.objects.bulk_create(new_subregions, ignore_conflicts=True)
            # Refresh cache
            saved_subregions = CustomSubRegion.objects.filter(
                region_id__in={s.region_id for s in new_subregions},
                code__in=[s.code for s in new_subregions if s.code]
            ).only('id', 'region_id', 'code', 'name')
            for ss in saved_subregions:
                subregion_cache[(ss.region_id, ss.code or '')] = ss

        # Now process each record with all parents available
        for record_data in batch:
            stats['total_records'] += 1
            try:
                name = self.safe_strip(record_data.get('name'))
                asciiname = self.safe_strip(record_data.get('asciiname'))
                country_code_json = self.safe_strip(record_data.get('country_code'))
                admin1_code = self.safe_strip(record_data.get('admin1_code'))
                admin2_code = self.safe_strip(record_data.get('admin2_code'))
                admin3_code = self.safe_strip(record_data.get('admin3_code'))
                admin4_code = self.safe_strip(record_data.get('admin4_code'))
                latitude = self.safe_float(record_data.get('latitude'))
                longitude = self.safe_float(record_data.get('longitude'))
                timezone_id = self.safe_strip(record_data.get('timezone'))
                feature_code = self.safe_strip(record_data.get('feature_code'))
                geoname_id = self.safe_int(record_data.get('geoname_id'))

                if input_type == 'cities':
                    if not admin2_code:
                        stats['missing_admin2_code'] += 1
                        raise ValidationError(f"Missing admin2_code for city {name or 'unknown'}")
                    if country_code_json != country.country_code:
                        raise ValidationError(f"Invalid country_code: {country_code_json}")
                    if not name or len(name) > 200:
                        raise ValidationError(f"Invalid city name: {name or 'missing'}")
                    if not admin1_code:
                        raise ValidationError(f"Missing admin1_code: {admin1_code}")
                    if admin3_code and not admin3_code.isdigit():
                        stats['invalid_admin_codes'] += 1
                        raise ValidationError(f"Admin3 code must be numeric: {admin3_code}")
                    if admin4_code and not admin4_code.isdigit():
                        stats['invalid_admin_codes'] += 1
                        raise ValidationError(f"Admin4 code must be numeric: {admin4_code}")
                    if not feature_code or feature_code not in self.ALLOWED_FEATURE_CODES:
                        stats['invalid_feature_codes'] += 1
                        raise ValidationError(f"Invalid feature_code: {feature_code}")
                    if latitude is not None and not (-90 <= latitude <= 90):
                        stats['invalid_coordinates'] += 1
                        raise ValidationError(f"Invalid latitude: {latitude}")
                    if longitude is not None and not (-180 <= longitude <= 180):
                        stats['invalid_coordinates'] += 1
                        raise ValidationError(f"Invalid longitude: {longitude}")
                    if latitude is None and longitude is None:
                        stats['missing_coordinates'] += 1
                    if not admin3_code:
                        stats['missing_admin3_code'] += 1
                    if timezone_id and timezone_id not in timezone_cache:
                        stats['invalid_timezones'] += 1
                        timezone_id = None

                # Get region
                region = None
                if admin1_code:
                    region_key = (country.id, admin1_code or '')
                    region = region_cache.get(region_key)
                if region and input_type == 'regions' and normalize_text(region.name) != normalize_text(name):
                    region.name = normalize_text(name)
                    region.asciiname = normalize_text(asciiname) if asciiname else None
                    region.updated_by = user
                    region.location_source = datasource
                    regions_to_update.append(region)
                    stats['updated_regions'] += 1

                # Get subregion
                subregion = None
                if region and admin2_code:
                    subregion_key = (region.id, admin2_code or '')
                    subregion = subregion_cache.get(subregion_key)
                if subregion and input_type == 'subregions' and normalize_text(subregion.name) != normalize_text(name):
                    subregion.name = normalize_text(name)
                    subregion.asciiname = normalize_text(asciiname) if asciiname else None
                    subregion.updated_by = user
                    subregion.location_source = datasource
                    subregions_to_update.append(subregion)
                    stats['updated_subregions'] += 1

                # Create city and location
                if input_type == 'cities' and subregion:
                    city_key = (subregion.id, normalize_text(name).lower())
                    city = city_cache.get(city_key)
                    location = None
                    if city:
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                SELECT id, street_address, latitude, longitude
                                FROM locations_location
                                WHERE city_id = %s AND deleted_at IS NULL
                                LIMIT 1
                            """, [city.id])
                            result = cursor.fetchone()
                            if result:
                                location = Location(id=result[0], street_address=result[1], latitude=result[2], longitude=result[3])
                    if not city:
                        slug = self.generate_unique_slug(name, city_slugs)
                        city = CustomCity(
                            name=normalize_text(name),
                            asciiname=normalize_text(asciiname) if asciiname else None,
                            geoname_id=geoname_id,
                            code=admin3_code,
                            subregion_id=subregion.id,
                            latitude=latitude,
                            longitude=longitude,
                            timezone_id=timezone_cache.get(timezone_id),
                            created_by=user,
                            updated_by=user,
                            slug=slug,
                            location_source=datasource
                        )
                        new_cities.append(city)
                        city_slugs.add(slug)
                        stats['created_cities'] += 1
                    else:
                        stats['duplicate_records'] += 1
                        update_fields = []
                        if city.code != admin3_code:
                            city.code = admin3_code
                            update_fields.append('code')
                        if city.latitude != latitude:
                            city.latitude = latitude
                            update_fields.append('latitude')
                        if city.longitude != longitude:
                            city.longitude = longitude
                            update_fields.append('longitude')
                        if city.timezone_id != timezone_cache.get(timezone_id):
                            city.timezone_id = timezone_cache.get(timezone_id)
                            update_fields.append('timezone_id')
                        if update_fields:
                            city.updated_by = user
                            city.location_source = datasource
                            cities_to_update.append(city)
                            stats['updated_cities'] += 1
                    # Location
                    street_address = normalize_text(name)
                    if city and (latitude is not None or longitude is not None):  # Ensure coordinates are valid
                        if location:
                            if location.street_address != street_address or location.latitude != latitude or location.longitude != longitude:
                                location.street_address = street_address
                                location.latitude = latitude
                                location.longitude = longitude
                                location.updated_by = user
                                locations_to_update.append(location)
                                stats['updated_locations'] += 1
                        else:
                            location = Location(
                                city_id=city.id,
                                street_address=street_address,
                                latitude=latitude,
                                longitude=longitude,
                                created_by=user,
                                updated_by=user,
                                location_source=datasource
                            )
                            new_locations.append(location)
                            stats['created_locations'] += 1

                # Collect admin codes
                if admin1_code:
                    admin_codes_to_add['admin1'].add(admin1_code)
                if admin2_code:
                    admin_codes_to_add['admin2'].add(admin2_code)
                if admin3_code:
                    admin_codes_to_add['admin3'].add(admin3_code)
                if admin4_code:
                    admin_codes_to_add['admin4'].add(admin4_code)

            except (ValueError, ValidationError) as e:
                stats['skipped_records'].append({
                    'name': name or 'unknown',
                    'admin1_code': admin1_code,
                    'admin2_code': admin2_code,
                    'admin3_code': admin3_code,
                    'reason': str(e),
                })
                logger.warning(f"Skipping {input_type} {name or 'unknown'}: {str(e)}")
                continue

        # Bulk operations for updates and new
        if regions_to_update:
            CustomRegion.objects.bulk_update(regions_to_update, ['name', 'asciiname', 'updated_by', 'location_source'])
        if subregions_to_update:
            CustomSubRegion.objects.bulk_update(subregions_to_update, ['name', 'asciiname', 'updated_by', 'location_source'])
        if new_cities:
            CustomCity.objects.bulk_create(new_cities, ignore_conflicts=True)
            # Refresh city cache
            saved_cities = CustomCity.objects.filter(
                subregion_id__in={c.subregion_id for c in new_cities},
                name__in=[c.name for c in new_cities]
            ).only('id', 'subregion_id', 'name')
            city_id_map = {(sc.subregion_id, normalize_text(sc.name).lower()): sc.id for sc in saved_cities}
            for city in saved_cities:
                city_cache[(city.subregion_id, normalize_text(city.name).lower())] = city
            # Update city_id for new locations
            for location in new_locations:
                if location.city_id is None:
                    key = (location.city.subregion_id, normalize_text(location.city.name).lower()) if hasattr(location, 'city') else None
                    location.city_id = city_id_map.get(key)
            new_cities.clear()

        if cities_to_update:
            CustomCity.objects.bulk_update(cities_to_update, ['code', 'latitude', 'longitude', 'timezone_id', 'updated_by', 'location_source'])
        if new_locations:
            # Filter out locations with null city_id
            valid_locations = [loc for loc in new_locations if loc.city_id is not None]
            if valid_locations:
                Location.objects.bulk_create(valid_locations, ignore_conflicts=True)
                stats['created_locations'] = len(valid_locations)
            new_locations.clear()
        if locations_to_update:
            Location.objects.bulk_update(locations_to_update, ['street_address', 'latitude', 'longitude', 'updated_by'])

    def handle(self, *args, **options):
        start_time = time.time()
        batch_size = options['batch_size']
        datasource = normalize_text(options['datasource']).lower()
        country_code = self.get_country_code(options['country'])
        if not country_code:
            return

        # Get country category dynamically
        country_category = get_country_administrative_category(country_code)
        valid_categories = ['unitary_state', 'federal_state', 'quasi_federal_state']
        if country_category not in valid_categories:
            self.stderr.write(self.style.ERROR(f"Invalid or unknown country category '{country_category}' for country code '{country_code}'. Must be one of: {', '.join(valid_categories)}"))
            logger.warning(f"Invalid or unknown country category '{country_category}' for country code '{country_code}'")
            country_category = 'federal_state'

        stats = {
            'created_regions': 0,
            'created_subregions': 0,
            'created_cities': 0,
            'created_locations': 0,
            'updated_regions': 0,
            'updated_subregions': 0,
            'updated_cities': 0,
            'updated_locations': 0,
            'skipped_records': [],
            'missing_coordinates': 0,
            'invalid_coordinates': 0,
            'missing_admin3_code': 0,
            'missing_admin2_code': 0,
            'invalid_timezones': 0,
            'invalid_feature_codes': 0,
            'duplicate_records': 0,
            'total_records': 0,
            'invalid_admin_codes': 0,
        }

        logger.setLevel(logging.WARNING)

        self.stdout.write(f"Starting sync for country code {country_code} with category {country_category}...")
        country = CustomCountry.objects.filter(country_code__iexact=country_code).first()
        if not country:
            self.stderr.write(self.style.ERROR(f"Country with code '{country_code}' not found"))
            logger.error(f"Country with code '{country_code}' not found")
            return

        if country.admin_codes is None:
            country.admin_codes = {
                'admin1_codes': [], 'admin2_codes': [], 'admin3_codes': [], 'admin4_codes': []
            }
            country.save(user=None, skip_validation=True)

        input_types = ['regions', 'subregions', 'cities']

        # Get user for audit fields
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using employee: {user.username}")
        except Employee.DoesNotExist:
            error_msg = f"Employee with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        # Load environment variables
        env_data = {}
        valid_inputs = False
        for input_type in input_types:
            input_env = f"{input_type.upper()}_JSON"
            input_file = options.get('input_file')
            env_data.update(load_env_paths(env_var=input_env, file=input_file, require_exists=False))

            # Construct country-specific JSON file path
            json_filename = str(Path(env_data.get(input_env, '')) / f"{country_code}.json")
            if not Path(json_filename).is_file():
                self.stderr.write(self.style.WARNING(f"No source file {json_filename} exists for {input_type}, skipping"))
                logger.warning(f"No source file {json_filename} exists for {input_type}, skipping")
                continue

            env_data[f"{country_code.upper()}_{input_type.upper()}_JSON"] = json_filename
            valid_inputs = True

        if not valid_inputs:
            elapsed_time = time.time() - start_time
            self.stderr.write(self.style.ERROR("No valid input files found. Sync aborted."))
            logger.error("No valid input files found. Sync aborted.")
            self.stdout.write(self.style.SUCCESS(f"Sync completed in {elapsed_time:.2f}s"))
            return

        # Load subregion names from subregions JSON
        subregion_file = env_data.get(f"{country_code.upper()}_SUBREGIONS_JSON")
        subregion_names = self.load_subregion_names(subregion_file, country_code) if subregion_file else {}

        region_cache = {(r.country_id, r.code or ''): r for r in CustomRegion.objects.filter(country=country).only('id', 'country_id', 'code', 'name')}
        subregion_cache = {(s.region_id, s.code or ''): s for s in CustomSubRegion.objects.filter(region__country=country).only('id', 'region_id', 'code', 'name')}
        city_cache = {(c.subregion_id, normalize_text(c.name).lower()): c for c in CustomCity.objects.filter(subregion__region__country=country).only('id', 'subregion_id', 'name', 'code', 'latitude', 'longitude', 'timezone_id')}
        timezone_cache = {t.timezone_id: t.timezone_id for t in Timezone.objects.all().only('timezone_id')}
        region_slugs = {r.slug for r in region_cache.values()}
        subregion_slugs = {s.slug for s in subregion_cache.values()}
        city_slugs = {c.slug for c in city_cache.values()}
        admin_codes_to_add = {
            'admin1': set(),
            'admin2': set(),
            'admin3': set(),
            'admin4': set(),
        }

        with transaction.atomic():
            for input_type in input_types:
                json_filename = env_data.get(f"{country_code.upper()}_{input_type.upper()}_JSON")
                if not json_filename:
                    continue
                try:
                    with open(json_filename, encoding='utf-8') as f:
                        data = ijson.items(f, 'item')
                        batch = []
                        index = 0
                        for record_data in data:
                            index += 1
                            batch.append(record_data)
                            if len(batch) == batch_size:
                                self.process_batch(batch, input_type, country, country_category, datasource, user, stats, region_cache, subregion_cache, city_cache, timezone_cache, region_slugs, subregion_slugs, city_slugs, admin_codes_to_add, subregion_names)
                                self.stdout.write(f"Processed {index} records for {input_type} ({time.time() - start_time:.2f}s)")
                                batch = []
                        if batch:
                            self.process_batch(batch, input_type, country, country_category, datasource, user, stats, region_cache, subregion_cache, city_cache, timezone_cache, region_slugs, subregion_slugs, city_slugs, admin_codes_to_add, subregion_names)
                            self.stdout.write(f"Processed {index} records for {input_type} ({time.time() - start_time:.2f}s)")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed to read JSON for {input_type}: {e}"))
                    logger.error(f"Failed to read JSON for {input_type}: {e}", exc_info=True)
                    continue

            self.update_admin_codes(country, admin_codes_to_add, user)

            logger.setLevel(logging.INFO)
            elapsed_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"Summary: ({elapsed_time:.2f}s)"))
            self.stdout.write(f"  Total records: {stats['total_records']}")
            self.stdout.write(f"  Regions created: {stats['created_regions']}")
            self.stdout.write(f"  Regions updated: {stats['updated_regions']}")
            self.stdout.write(f"  Subregions created: {stats['created_subregions']}")
            self.stdout.write(f"  Subregions updated: {stats['updated_subregions']}")
            self.stdout.write(f"  Cities created: {stats['created_cities']}")
            self.stdout.write(f"  Cities updated: {stats['updated_cities']}")
            self.stdout.write(f"  Locations created: {stats['created_locations']}")
            self.stdout.write(f"  Locations updated: {stats['updated_locations']}")
            self.stdout.write(f"  Skipped records: {len(stats['skipped_records'])}")
            self.stdout.write(f"  Duplicate records: {stats['duplicate_records']}")
            self.stdout.write(f"  Missing admin2_code: {stats['missing_admin2_code']}")
            self.stdout.write(f"  Missing admin3_code: {stats['missing_admin3_code']}")
            self.stdout.write(f"  Invalid admin codes: {stats['invalid_admin_codes']}")
            self.stdout.write(f"  Missing coordinates: {stats['missing_coordinates']}")
            self.stdout.write(f"  Invalid coordinates: {stats['invalid_coordinates']}")
            self.stdout.write(f"  Invalid timezones: {stats['invalid_timezones']}")
            self.stdout.write(f"  Invalid feature codes: {stats['invalid_feature_codes']}")
            logger.info(
                f"Summary: Total={stats['total_records']}, "
                f"Regions Created={stats['created_regions']}, Regions Updated={stats['updated_regions']}, "
                f"Subregions Created={stats['created_subregions']}, Subregions Updated={stats['updated_subregions']}, "
                f"Cities Created={stats['created_cities']}, Cities Updated={stats['updated_cities']}, "
                f"Locations Created={stats['created_locations']}, Locations Updated={stats['updated_locations']}, "
                f"Skipped={len(stats['skipped_records'])}, Duplicate Records={stats['duplicate_records']}, "
                f"Missing Admin2 Code={stats['missing_admin2_code']}, Missing Admin3 Code={stats['missing_admin3_code']}, "
                f"Invalid Admin Codes={stats['invalid_admin_codes']}, Missing Coordinates={stats['missing_coordinates']}, "
                f"Invalid Coordinates={stats['invalid_coordinates']}, Invalid Timezones={stats['invalid_timezones']}, "
                f"Invalid Feature Codes={stats['invalid_feature_codes']}"
            )
            if stats['skipped_records']:
                for skipped in stats['skipped_records'][:5]:
                    self.stdout.write(
                        f"    - Skipped {input_type}: {skipped['name']} (admin1_code: {skipped['admin1_code']}, admin2_code: {skipped['admin2_code']}, "
                        f"admin3_code: {skipped['admin3_code']}, reason: {skipped['reason']})"
                    )
                if len(stats['skipped_records']) > 5:
                    self.stdout.write(f"    - ... and {len(stats['skipped_records']) - 5} more skipped records")
        self.stdout.write(self.style.SUCCESS(f"Sync completed in {elapsed_time:.2f}s"))
        logger.info(f"Sync completed in {elapsed_time:.2f}s")

# import argparse
# import logging
# import time
# import ijson
# from django.core.exceptions import ValidationError
# from django.core.management.base import BaseCommand
# from django.db import transaction, connection
# from django.utils.text import slugify
# from django.contrib.auth import get_user_model
# from django.db.models import Q
# from locations.models.custom_country import CustomCountry
# from locations.models.custom_region import CustomRegion
# from locations.models.custom_subregion import CustomSubRegion
# from locations.models.custom_city import CustomCity
# from locations.models.location import Location
# from locations.models.timezone import Timezone
# from utilities.utils.general.normalize_text import normalize_text
# from utilities.utils.data_sync.load_env_and_paths import load_env_paths
# from typing import Optional
# from pathlib import Path
# from utilities.utils.locations.geoservices import get_country_administrative_category

# logger = logging.getLogger(__name__)

# class Command(BaseCommand):
#     help = """📦 Sync cities data from JSON file for a specified country.
#     Example usage:
#         ./manage.py import_cities --datasource geonames --country NZ --batch-size 60000
#         ./manage.py import_cities --datasource geonames --country IN --batch-size 60000
#     """

#     ALLOWED_FEATURE_CODES = {
#         'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLA5', 'PPLC', 'PPLCH', 'PPLF', 'PPLG', 'PPLH', 'PPLL', 'PPLQ', 'PPLR', 'PPLS', 'PPLW', 'PPLX', 'ADM1', 'ADM2', 'ADM3', 'ADM4'
#     }

#     def add_arguments(self, parser):
#         parser.formatter_class = argparse.RawTextHelpFormatter
#         parser.add_argument(
#             "--datasource",
#             type=str,
#             required=True,
#             help="Data source for location_source field (e.g., 'geonames' or 'GOI')",
#         )
#         parser.add_argument(
#             "--country",
#             type=str,
#             required=True,
#             help="Specify country code or name (e.g., NZ, Japan)"
#         )
#         parser.add_argument(
#             "--batch-size",
#             type=int,
#             default=5000,
#             help="Batch size for processing (default: 5000)"
#         )
#         parser.add_argument(
#             "--input-file",
#             type=str,
#             help="Override source file path"
#         )
#         parser.add_argument(
#             "--output-file",
#             type=str,
#             help="Override destination JSON file"
#         )

#     def safe_strip(self, value):
#         """Safely strip a value if it's a string, otherwise return None."""
#         return value.strip() if isinstance(value, str) and value.strip() else None

#     def safe_float(self, value):
#         """Safely convert a value to float, returning None if invalid."""
#         try:
#             return float(value) if value is not None else None
#         except (ValueError, TypeError):
#             return None

#     def safe_int(self, value):
#         """Safely convert a value to int, returning None if invalid."""
#         try:
#             return int(value) if value is not None else None
#         except (ValueError, TypeError):
#             return None

#     def generate_unique_slug(self, name, existing_slugs):
#         """Generate a unique slug for the given name."""
#         slug = slugify(name)[:190]  # Leave room for suffixes
#         counter = 1
#         original_slug = slug
#         while slug in existing_slugs:
#             slug = f"{original_slug}-{counter}"
#             counter += 1
#         return slug

#     def update_admin_codes(self, country, admin_codes_to_add, user):
#         """Update admin_codes in CustomCountry in bulk."""
#         admin_codes = country.admin_codes or {
#             'admin1_codes': [], 'admin2_codes': [], 'admin3_codes': [], 'admin4_codes': []
#         }
#         updated = False
#         for level, codes in admin_codes_to_add.items():
#             key = f"{level}_codes"
#             if not isinstance(admin_codes.get(key), list):
#                 admin_codes[key] = []
#             for code in codes:
#                 if code and code.isdigit() and code not in admin_codes[key]:
#                     admin_codes[key].append(code)
#                     updated = True
#         if updated:
#             admin_codes = {k: sorted(v) for k, v in admin_codes.items()}
#             country.admin_codes = admin_codes
#             country.save(user=user, skip_validation=True)

#     def get_similar_region(self, region_name, country_id, admin1_code):
#         """Find a region with a similar name using pg_trgm similarity."""
#         normalized_region_name = normalize_text(region_name)
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT id, name, code, similarity(name, %s) AS sim_score
#                 FROM locations_customregion
#                 WHERE country_id = %s AND similarity(name, %s) >= 0.5 AND similarity(name, %s) <= 0.9
#                 ORDER BY sim_score DESC
#                 LIMIT 1
#             """, [normalized_region_name, country_id, normalized_region_name, normalized_region_name])
#             result = cursor.fetchone()
#             if result:
#                 return CustomRegion.objects.get(id=result[0])
#         return None

#     def get_similar_subregion(self, subregion_name, region_id, admin2_code):
#         """Find a subregion with a similar name using pg_trgm similarity."""
#         normalized_subregion_name = normalize_text(subregion_name)
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT id, name, code, similarity(name, %s) AS sim_score
#                 FROM locations_customsubregion
#                 WHERE region_id = %s AND similarity(name, %s) >= 0.5 AND similarity(name, %s) <= 0.9
#                 ORDER BY sim_score DESC
#                 LIMIT 1
#             """, [normalized_subregion_name, region_id, normalized_subregion_name, normalized_subregion_name])
#             result = cursor.fetchone()
#             if result:
#                 return CustomSubRegion.objects.get(id=result[0])
#         return None

#     def get_country_code(self, country_input: str) -> Optional[str]:
#         """Normalize and validate country input, returning country code."""
#         if ' ' in country_input:
#             self.stderr.write(self.style.ERROR("Hey Smartpants, why don't you try simple country_code instead of full names. Currently I am out of mood to process names with spaces."))
#             return None

#         normalized_country = normalize_text(country_input).lower()
#         try:
#             country = CustomCountry.objects.filter(
#                 Q(name__iexact=normalized_country) | Q(asciiname__iexact=normalized_country) | Q(country_code__iexact=normalized_country)
#             ).first()
#             if not country:
#                 self.stderr.write(self.style.ERROR(f"No country found for input: {country_input}"))
#                 return None
#             self.stdout.write(f"Proceeding with country '{country.name}'")
#             return country.country_code
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f"Error validating country: {str(e)}"))
#             return None

#     def load_subregion_names(self, subregion_file, country_code):
#         """Load subregion names from JSON file by admin2_code."""
#         subregion_names = {}
#         try:
#             with open(subregion_file, 'r', encoding='utf-8') as f:
#                 data = ijson.items(f, 'item')
#                 for record in data:
#                     admin2_code = self.safe_strip(record.get('admin2_code'))
#                     name = self.safe_strip(record.get('name'))
#                     record_country_code = self.safe_strip(record.get('country_code'))
#                     if admin2_code and name and record_country_code == country_code:
#                         subregion_names[admin2_code] = normalize_text(name)
#         except Exception as e:
#             logger.warning(f"Failed to load subregion names from {subregion_file}: {str(e)}")
#         return subregion_names

#     def handle(self, *args, **options):
#         start_time = time.time()
#         batch_size = options['batch_size']
#         datasource = normalize_text(options['datasource']).lower()
#         country_code = self.get_country_code(options['country'])
#         if not country_code:
#             return

#         # Get country category dynamically
#         country_category = get_country_administrative_category(country_code)
#         valid_categories = ['unitary_state', 'federal_state', 'quasi_federal_state']
#         if country_category not in valid_categories:
#             self.stderr.write(self.style.ERROR(f"Invalid or unknown country category '{country_category}' for country code '{country_code}'. Must be one of: {', '.join(valid_categories)}"))
#             logger.warning(f"Invalid or unknown country category '{country_category}' for country code '{country_code}'")
#             country_category = 'federal_state'

#         stats = {
#             'created_regions': 0,
#             'created_subregions': 0,
#             'created_cities': 0,
#             'created_locations': 0,
#             'updated_regions': 0,
#             'updated_subregions': 0,
#             'updated_cities': 0,
#             'updated_locations': 0,
#             'skipped_records': [],
#             'missing_coordinates': 0,
#             'invalid_coordinates': 0,
#             'missing_admin3_code': 0,
#             'missing_admin2_code': 0,
#             'invalid_timezones': 0,
#             'invalid_feature_codes': 0,
#             'duplicate_records': 0,
#             'total_records': 0,
#             'invalid_admin_codes': 0,
#         }

#         logger.setLevel(logging.WARNING)

#         self.stdout.write(f"Starting sync for country code {country_code} with category {country_category}...")
#         country = CustomCountry.objects.filter(country_code__iexact=country_code).first()
#         if not country:
#             self.stderr.write(self.style.ERROR(f"Country with code '{country_code}' not found"))
#             logger.error(f"Country with code '{country_code}' not found")
#             return

#         if country.admin_codes is None:
#             country.admin_codes = {
#                 'admin1_codes': [], 'admin2_codes': [], 'admin3_codes': [], 'admin4_codes': []
#             }
#             country.save(user=None, skip_validation=True)

#         input_types = ['regions', 'subregions', 'cities']

#         # Get user for audit fields
#         Employee = get_user_model()
#         try:
#             user = Employee.objects.get(id=1)
#             self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}) ({time.time() - start_time:.2f}s)"))
#             logger.info(f"Using employee: {user.username}")
#         except Employee.DoesNotExist:
#             error_msg = f"Employee with id=1 not found. Please ensure user exists. ({time.time() - start_time:.2f}s)"
#             self.stderr.write(self.style.ERROR(error_msg))
#             logger.error(error_msg)
#             return

#         # Load environment variables
#         env_data = {}
#         valid_inputs = False
#         for input_type in input_types:
#             input_env = f"{input_type.upper()}_JSON"
#             input_file = options.get('input_file')
#             env_data.update(load_env_paths(env_var=input_env, file=input_file, require_exists=False))

#             # Construct country-specific JSON file path
#             json_filename = str(Path(env_data.get(input_env, '')) / f"{country_code}.json")
#             if not Path(json_filename).is_file():
#                 self.stderr.write(self.style.WARNING(f"No source file {json_filename} exists for {input_type}, skipping"))
#                 logger.warning(f"No source file {json_filename} exists for {input_type}, skipping")
#                 continue

#             env_data[f"{country_code.upper()}_{input_type.upper()}_JSON"] = json_filename
#             valid_inputs = True

#         if not valid_inputs:
#             elapsed_time = time.time() - start_time
#             self.stderr.write(self.style.ERROR("No valid input files found. Sync aborted."))
#             logger.error("No valid input files found. Sync aborted.")
#             self.stdout.write(self.style.SUCCESS(f"Sync completed in {elapsed_time:.2f}s"))
#             return

#         # Load subregion names from subregions JSON
#         subregion_file = env_data.get(f"{country_code.upper()}_SUBREGIONS_JSON")
#         subregion_names = self.load_subregion_names(subregion_file, country_code) if subregion_file else {}

#         region_cache = {(r.country_id, r.code or ''): r for r in CustomRegion.objects.filter(country=country).only('id', 'country_id', 'code', 'name')}
#         subregion_cache = {(s.region_id, s.code or ''): s for s in CustomSubRegion.objects.filter(region__country=country).only('id', 'region_id', 'code', 'name')}
#         city_cache = {(c.subregion_id, normalize_text(c.name).lower()): c for c in CustomCity.objects.filter(subregion__region__country=country).only('id', 'subregion_id', 'name', 'code', 'latitude', 'longitude', 'timezone_id')}
#         timezone_cache = {t.timezone_id: t.timezone_id for t in Timezone.objects.all().only('timezone_id')}
#         region_slugs = {r.slug for r in region_cache.values()}
#         subregion_slugs = {s.slug for s in subregion_cache.values()}
#         city_slugs = {c.slug for c in city_cache.values()}
#         admin_codes_to_add = {
#             'admin1': set(),
#             'admin2': set(),
#             'admin3': set(),
#             'admin4': set(),
#         }

#         new_regions = []
#         new_subregions = []
#         new_cities = []
#         new_locations = []
#         regions_to_update = []
#         subregions_to_update = []
#         cities_to_update = []
#         locations_to_update = []

#         with transaction.atomic():
#             for input_type in input_types:
#                 json_filename = env_data.get(f"{country_code.upper()}_{input_type.upper()}_JSON")
#                 if not json_filename:
#                     continue
#                 try:
#                     with open(json_filename, 'r', encoding='utf-8') as f:
#                         data = ijson.items(f, 'item')
#                         for index, record_data in enumerate(data, 1):
#                             stats['total_records'] += 1
#                             try:
#                                 name = self.safe_strip(record_data.get('name'))
#                                 asciiname = self.safe_strip(record_data.get('asciiname'))
#                                 country_code_json = self.safe_strip(record_data.get('country_code'))
#                                 admin1_code = self.safe_strip(record_data.get('admin1_code'))
#                                 admin2_code = self.safe_strip(record_data.get('admin2_code'))
#                                 admin3_code = self.safe_strip(record_data.get('admin3_code'))
#                                 admin4_code = self.safe_strip(record_data.get('admin4_code'))
#                                 latitude = self.safe_float(record_data.get('latitude'))
#                                 longitude = self.safe_float(record_data.get('longitude'))
#                                 timezone_id = self.safe_strip(record_data.get('timezone'))
#                                 feature_code = self.safe_strip(record_data.get('feature_code'))
#                                 geoname_id = self.safe_int(record_data.get('geoname_id'))

#                                 if input_type == 'cities':
#                                     if not admin2_code:
#                                         stats['missing_admin2_code'] += 1
#                                         raise ValidationError(f"Missing admin2_code for city {name or 'unknown'}")
#                                     if country_code_json != country_code:
#                                         raise ValidationError(f"Invalid country_code: {country_code_json}")
#                                     if not name or len(name) > 200:
#                                         raise ValidationError(f"Invalid city name: {name or 'missing'}")
#                                     if not admin1_code:
#                                         raise ValidationError(f"Missing admin1_code: {admin1_code}")
#                                     if admin3_code and not admin3_code.isdigit():
#                                         stats['invalid_admin_codes'] += 1
#                                         raise ValidationError(f"Admin3 code must be numeric: {admin3_code}")
#                                     if admin4_code and not admin4_code.isdigit():
#                                         stats['invalid_admin_codes'] += 1
#                                         raise ValidationError(f"Admin4 code must be numeric: {admin4_code}")
#                                     if not feature_code or feature_code not in self.ALLOWED_FEATURE_CODES:
#                                         stats['invalid_feature_codes'] += 1
#                                         raise ValidationError(f"Invalid feature_code: {feature_code}")
#                                     if latitude is not None and not (-90 <= latitude <= 90):
#                                         stats['invalid_coordinates'] += 1
#                                         raise ValidationError(f"Invalid latitude: {latitude}")
#                                     if longitude is not None and not (-180 <= longitude <= 180):
#                                         stats['invalid_coordinates'] += 1
#                                         raise ValidationError(f"Invalid longitude: {longitude}")
#                                     if latitude is None and longitude is None:
#                                         stats['missing_coordinates'] += 1
#                                     if not admin3_code:
#                                         stats['missing_admin3_code'] += 1
#                                     if timezone_id and timezone_id not in timezone_cache:
#                                         stats['invalid_timezones'] += 1
#                                         timezone_id = None

#                                 # Get or create region
#                                 if input_type in ['regions', 'subregions', 'cities']:
#                                     region_key = (country.id, admin1_code or '')
#                                     region = region_cache.get(region_key)
#                                     if not region and admin1_code:
#                                         region_name = record_data.get('admin1_name') or f"Region {admin1_code}" if input_type != 'regions' else name
#                                         region = self.get_similar_region(region_name, country.id, admin1_code)
#                                         if not region:
#                                             region, _ = CustomRegion.objects.get_or_create(
#                                                 country_id=country.id,
#                                                 code=admin1_code,
#                                                 defaults={
#                                                     'name': normalize_text(region_name),
#                                                     'created_by': user,
#                                                     'updated_by': user,
#                                                     'slug': self.generate_unique_slug(region_name, region_slugs),
#                                                     'location_source': datasource
#                                                 }
#                                             )
#                                             stats['created_regions'] += 1
#                                             new_regions.append(region)
#                                         region_cache[region_key] = region
#                                         region_slugs.add(region.slug)
#                                     elif region and input_type == 'regions' and region.name != name:
#                                         region.name = normalize_text(name)
#                                         region.asciiname = normalize_text(asciiname) if asciiname else None
#                                         region.updated_by = user
#                                         region.location_source = datasource
#                                         regions_to_update.append(region)
#                                         stats['updated_regions'] += 1

#                                 # Get or create subregion
#                                 if input_type in ['subregions', 'cities'] and region:
#                                     subregion_key = (region.id, admin2_code or '')
#                                     subregion = subregion_cache.get(subregion_key)
#                                     if not subregion and (admin2_code or country_category in ['unitary_state', 'quasi_federal_state']):
#                                         subregion_name = subregion_names.get(admin2_code, record_data.get('admin2_name')) or f"{region.name} District {admin2_code or 'Unknown'}"
#                                         normalized_subregion_name = normalize_text(subregion_name).lower()

#                                         # Handle subregion based on country_category
#                                         if country_category == 'federal_state' and (not admin2_code or admin2_code == admin1_code or not subregion_name):
#                                             stats['skipped_records'].append({
#                                                 'name': name or 'unknown',
#                                                 'index': index,
#                                                 'admin1_code': admin1_code,
#                                                 'admin2_code': admin2_code,
#                                                 'admin3_code': admin3_code,
#                                                 'reason': f"Missing or invalid admin2_code or subregion name for federal_state: admin2_code={admin2_code}, subregion_name={subregion_name}"
#                                             })
#                                             logger.warning(f"Skipping {input_type} {name or 'unknown'} at index {index}: Missing or invalid admin2_code or subregion name for federal_state")
#                                             continue
#                                         elif country_category in ['unitary_state', 'quasi_federal_state'] and (not admin2_code or admin2_code == admin1_code):
#                                             # Use region details for subregion
#                                             subregion = CustomSubRegion.objects.filter(
#                                                 region_id=region.id,
#                                                 name=region.name
#                                             ).first()
#                                             if subregion:
#                                                 if subregion.code != admin2_code:
#                                                     subregion.code = admin2_code
#                                                     subregion.updated_by = user
#                                                     subregion.save()
#                                                     subregions_to_update.append(subregion)
#                                                     stats['updated_subregions'] += 1
#                                             else:
#                                                 subregion = CustomSubRegion(
#                                                     region_id=region.id,
#                                                     name=region.name,
#                                                     code=admin2_code,
#                                                     created_by=user,
#                                                     updated_by=user,
#                                                     slug=self.generate_unique_slug(region.name, subregion_slugs),
#                                                     location_source=datasource
#                                                 )
#                                                 new_subregions.append(subregion)
#                                                 stats['created_subregions'] += 1
#                                                 logger.debug(f"Created new subregion using region name: {region.name} (Code: {admin2_code})")
#                                         else:
#                                             # Normal subregion creation for valid admin2_code
#                                             subregion = CustomSubRegion.objects.filter(
#                                                 region_id=region.id,
#                                                 name__iexact=normalized_subregion_name
#                                             ).first()
#                                             if not subregion:
#                                                 subregion = self.get_similar_subregion(subregion_name, region.id, admin2_code)
#                                             if not subregion:
#                                                 try:
#                                                     subregion, created = CustomSubRegion.objects.get_or_create(
#                                                         region_id=region.id,
#                                                         code=admin2_code,
#                                                         defaults={
#                                                             'name': normalize_text(subregion_name),
#                                                             'created_by': user,
#                                                             'updated_by': user,
#                                                             'slug': self.generate_unique_slug(subregion_name, subregion_slugs),
#                                                             'location_source': datasource
#                                                         }
#                                                     )
#                                                     if created:
#                                                         stats['created_subregions'] += 1
#                                                         new_subregions.append(subregion)
#                                                         logger.debug(f"Created new subregion: {subregion_name} (ID: {subregion.id}, Code: {admin2_code})")
#                                                         if subregion_name.startswith(f"{region.name} District"):
#                                                             logger.warning(f"Created fallback subregion name: {subregion_name} for admin2_code {admin2_code}")
#                                                     else:
#                                                         logger.debug(f"Found existing subregion: {subregion_name} (ID: {subregion.id})")
#                                                 except Exception as e:
#                                                     stats['skipped_records'].append({
#                                                         'name': subregion_name,
#                                                         'index': index,
#                                                         'admin1_code': admin1_code,
#                                                         'admin2_code': admin2_code,
#                                                         'admin3_code': admin3_code,
#                                                         'reason': f"Failed to create subregion: {str(e)}"
#                                                     })
#                                                     logger.warning(f"Skipping subregion {subregion_name} due to error: {str(e)}")
#                                                     continue
#                                         subregion_cache[subregion_key] = subregion
#                                         subregion_slugs.add(subregion.slug)
#                                     elif subregion and input_type == 'subregions' and normalize_text(subregion.name) != normalize_text(name):
#                                         subregion.name = normalize_text(name)
#                                         subregion.asciiname = normalize_text(asciiname) if asciiname else None
#                                         subregion.updated_by = user
#                                         subregion.location_source = datasource
#                                         subregions_to_update.append(subregion)
#                                         stats['updated_subregions'] += 1

#                                 # Get or create city and location
#                                 if input_type == 'cities' and subregion:
#                                     city_key = (subregion.id, normalize_text(name).lower())
#                                     city = city_cache.get(city_key)
#                                     location = None
#                                     if city:
#                                         location = Location.objects.filter(city_id=city.id, deleted_at__isnull=True).first()
#                                     if not city:
#                                         city = CustomCity(
#                                             name=normalize_text(name),
#                                             asciiname=normalize_text(asciiname) if asciiname else None,
#                                             geoname_id=geoname_id,
#                                             code=admin3_code,
#                                             subregion_id=subregion.id,
#                                             latitude=latitude,
#                                             longitude=longitude,
#                                             timezone_id=timezone_cache.get(timezone_id),
#                                             created_by=user,
#                                             updated_by=user,
#                                             slug=self.generate_unique_slug(name, city_slugs),
#                                             location_source=datasource
#                                         )
#                                         city_slugs.add(city.slug)
#                                         new_cities.append(city)
#                                         city_cache[city_key] = city
#                                         stats['created_cities'] += 1
#                                     else:
#                                         stats['duplicate_records'] += 1
#                                         update_fields = []
#                                         if city.code != admin3_code:
#                                             city.code = admin3_code
#                                             update_fields.append('code')
#                                         if city.latitude != latitude:
#                                             city.latitude = latitude
#                                             update_fields.append('latitude')
#                                         if city.longitude != longitude:
#                                             city.longitude = longitude
#                                             update_fields.append('longitude')
#                                         if city.timezone_id != timezone_cache.get(timezone_id):
#                                             city.timezone_id = timezone_cache.get(timezone_id)
#                                             update_fields.append('timezone_id')
#                                         if update_fields and city.pk:
#                                             city.updated_by = user
#                                             city.location_source = datasource
#                                             update_fields.extend(['updated_by', 'location_source'])
#                                             cities_to_update.append(city)
#                                             stats['updated_cities'] += 1
#                                         # Update or create location
#                                         if location:
#                                             if location.street_address != normalize_text(name) or location.latitude != latitude or location.longitude != longitude:
#                                                 location.street_address = normalize_text(name)
#                                                 location.latitude = latitude
#                                                 location.longitude = longitude
#                                                 location.updated_by = user
#                                                 locations_to_update.append(location)
#                                                 stats['updated_locations'] += 1
#                                         else:
#                                             location = Location(
#                                                 city=city,
#                                                 street_address=normalize_text(name),
#                                                 latitude=latitude,
#                                                 longitude=longitude,
#                                                 created_by=user,
#                                                 updated_by=user
#                                             )
#                                             new_locations.append(location)
#                                             stats['created_locations'] += 1

#                                 # Collect admin codes
#                                 if admin1_code:
#                                     admin_codes_to_add['admin1'].add(admin1_code)
#                                 if admin2_code:
#                                     admin_codes_to_add['admin2'].add(admin2_code)
#                                 if admin3_code:
#                                     admin_codes_to_add['admin3'].add(admin3_code)
#                                 if admin4_code:
#                                     admin_codes_to_add['admin4'].add(admin4_code)

#                                 if index % batch_size == 0:
#                                     self.stdout.write(f"Processed {index} records for {input_type} ({time.time() - start_time:.2f}s)")
#                                     if new_regions:
#                                         CustomRegion.objects.bulk_create(new_regions, batch_size=batch_size, ignore_conflicts=True)
#                                         new_regions.clear()
#                                     if new_subregions:
#                                         CustomSubRegion.objects.bulk_create(new_subregions, batch_size=batch_size, ignore_conflicts=True)
#                                         new_subregions.clear()
#                                     if new_cities:
#                                         CustomCity.objects.bulk_create(new_cities, batch_size=batch_size, ignore_conflicts=True)
#                                         saved_cities = CustomCity.objects.filter(
#                                             subregion_id__in=[c.subregion_id for c in new_cities],
#                                             name__in=[c.name for c in new_cities]
#                                         ).only('id', 'subregion_id', 'name', 'code', 'latitude', 'longitude', 'timezone_id')
#                                         for city in saved_cities:
#                                             city_cache[(city.subregion_id, normalize_text(city.name).lower())] = city
#                                             # Update city_id for new locations
#                                             for location in new_locations:
#                                                 if location.city.name == city.name and location.city.subregion_id == city.subregion_id:
#                                                     location.city_id = city.id
#                                         new_cities.clear()
#                                     if cities_to_update:
#                                         CustomCity.objects.bulk_update(
#                                             cities_to_update,
#                                             ['code', 'latitude', 'longitude', 'timezone_id', 'updated_by', 'location_source'],
#                                             batch_size=batch_size
#                                         )
#                                         cities_to_update.clear()
#                                     if new_locations:
#                                         Location.objects.bulk_create(new_locations, batch_size=batch_size, ignore_conflicts=True)
#                                         new_locations.clear()
#                                     if locations_to_update:
#                                         Location.objects.bulk_update(
#                                             locations_to_update,
#                                             ['street_address', 'latitude', 'longitude', 'updated_by'],
#                                             batch_size=batch_size
#                                         )
#                                         locations_to_update.clear()
#                             except (ValueError, ValidationError) as e:
#                                 stats['skipped_records'].append({
#                                     'name': name or 'unknown',
#                                     'index': index,
#                                     'admin1_code': admin1_code,
#                                     'admin2_code': admin2_code,
#                                     'admin3_code': admin3_code,
#                                     'reason': str(e),
#                                 })
#                                 logger.warning(f"Skipping {input_type} {name or 'unknown'} at index {index}: {str(e)}")
#                                 continue
#                 except Exception as e:
#                     self.stderr.write(self.style.ERROR(f"Failed to read JSON for {input_type}: {e}"))
#                     logger.error(f"Failed to read JSON for {input_type}: {e}", exc_info=True)
#                     continue

#             # Final bulk operations
#             if new_regions:
#                 CustomRegion.objects.bulk_create(new_regions, batch_size=batch_size, ignore_conflicts=True)
#                 new_regions.clear()
#             if new_subregions:
#                 CustomSubRegion.objects.bulk_create(new_subregions, batch_size=batch_size, ignore_conflicts=True)
#                 new_subregions.clear()
#             if new_cities:
#                 CustomCity.objects.bulk_create(new_cities, batch_size=batch_size, ignore_conflicts=True)
#                 saved_cities = CustomCity.objects.filter(
#                     subregion_id__in=[c.subregion_id for c in new_cities],
#                     name__in=[c.name for c in new_cities]
#                 ).only('id', 'subregion_id', 'name', 'code', 'latitude', 'longitude', 'timezone_id')
#                 for city in saved_cities:
#                     city_cache[(city.subregion_id, normalize_text(city.name).lower())] = city
#                     # Update city_id for new locations
#                     for location in new_locations:
#                         if location.city.name == city.name and location.city.subregion_id == city.subregion_id:
#                             location.city_id = city.id
#                 new_cities.clear()
#             if cities_to_update:
#                 CustomCity.objects.bulk_update(
#                     cities_to_update,
#                     ['code', 'latitude', 'longitude', 'timezone_id', 'updated_by', 'location_source'],
#                     batch_size=batch_size
#                 )
#                 cities_to_update.clear()
#             if new_locations:
#                 Location.objects.bulk_create(new_locations, batch_size=batch_size, ignore_conflicts=True)
#                 new_locations.clear()
#             if locations_to_update:
#                 Location.objects.bulk_update(
#                     locations_to_update,
#                     ['street_address', 'latitude', 'longitude', 'updated_by'],
#                     batch_size=batch_size
#                 )
#                 locations_to_update.clear()
#             self.update_admin_codes(country, admin_codes_to_add, user)

#             logger.setLevel(logging.INFO)
#             elapsed_time = time.time() - start_time
#             self.stdout.write(self.style.SUCCESS(f"Summary for {input_type}: ({elapsed_time:.2f}s)"))
#             self.stdout.write(f"  Total records: {stats['total_records']}")
#             self.stdout.write(f"  Regions created: {stats['created_regions']}")
#             self.stdout.write(f"  Regions updated: {stats['updated_regions']}")
#             self.stdout.write(f"  Subregions created: {stats['created_subregions']}")
#             self.stdout.write(f"  Subregions updated: {stats['updated_subregions']}")
#             self.stdout.write(f"  Cities created: {stats['created_cities']}")
#             self.stdout.write(f"  Cities updated: {stats['updated_cities']}")
#             self.stdout.write(f"  Locations created: {stats['created_locations']}")
#             self.stdout.write(f"  Locations updated: {stats['updated_locations']}")
#             self.stdout.write(f"  Skipped records: {len(stats['skipped_records'])}")
#             self.stdout.write(f"  Duplicate records: {stats['duplicate_records']}")
#             self.stdout.write(f"  Missing admin2_code: {stats['missing_admin2_code']}")
#             self.stdout.write(f"  Missing admin3_code: {stats['missing_admin3_code']}")
#             self.stdout.write(f"  Invalid admin codes: {stats['invalid_admin_codes']}")
#             self.stdout.write(f"  Missing coordinates: {stats['missing_coordinates']}")
#             self.stdout.write(f"  Invalid coordinates: {stats['invalid_coordinates']}")
#             self.stdout.write(f"  Invalid timezones: {stats['invalid_timezones']}")
#             self.stdout.write(f"  Invalid feature codes: {stats['invalid_feature_codes']}")
#             logger.info(
#                 f"Summary for {input_type}: Total={stats['total_records']}, "
#                 f"Regions Created={stats['created_regions']}, Regions Updated={stats['updated_regions']}, "
#                 f"Subregions Created={stats['created_subregions']}, Subregions Updated={stats['updated_subregions']}, "
#                 f"Cities Created={stats['created_cities']}, Cities Updated={stats['updated_cities']}, "
#                 f"Locations Created={stats['created_locations']}, Locations Updated={stats['updated_locations']}, "
#                 f"Skipped={len(stats['skipped_records'])}, Duplicate Records={stats['duplicate_records']}, "
#                 f"Missing Admin2 Code={stats['missing_admin2_code']}, Missing Admin3 Code={stats['missing_admin3_code']}, "
#                 f"Invalid Admin Codes={stats['invalid_admin_codes']}, Missing Coordinates={stats['missing_coordinates']}, "
#                 f"Invalid Coordinates={stats['invalid_coordinates']}, Invalid Timezones={stats['invalid_timezones']}, "
#                 f"Invalid Feature Codes={stats['invalid_feature_codes']}"
#             )
#             if stats['skipped_records']:
#                 for skipped in stats['skipped_records'][:5]:
#                     self.stdout.write(
#                         f"    - Skipped {input_type}: {skipped['name']} (Index: {skipped['index']}, "
#                         f"admin1_code: {skipped['admin1_code']}, admin2_code: {skipped['admin2_code']}, "
#                         f"admin3_code: {skipped['admin3_code']}, reason: {skipped['reason']})"
#                     )
#                 if len(stats['skipped_records']) > 5:
#                     self.stdout.write(f"    - ... and {len(stats['skipped_records']) - 5} more skipped records")
#         self.stdout.write(self.style.SUCCESS(f"Sync completed in {elapsed_time:.2f}s"))
#         logger.info(f"Sync completed in {elapsed_time:.2f}s")
