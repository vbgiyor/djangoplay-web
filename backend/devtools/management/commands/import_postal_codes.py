import argparse
import json
import logging
import os
import time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from locations.exceptions import InvalidLocationData
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, Location
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.locations.geoservices import get_country_administrative_category

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Update postal codes and street addresses for existing locations from JSON file.
Matches records based on unique [name + admin_code1 + admin_code2] or [name + admin_code1] if admin_code2 is None.
Normalizes city names to lowercase for consistent comparison.
Updates existing Location objects or creates new ones if --create-locations is specified.
Skips records if the city or location does not exist or if the combination is not unique.
Sets street_address to normalized city name.
Dynamically determines country category using get_country_administrative_category.
For federal_state, subregion (admin_code2) is mandatory.
For unitary_state or quasi_federal_state, uses region as subregion when admin_code2 is missing, ensuring unique names.
"""

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            "--postal-file",
            type=str,
            help="Override POSTAL_CODES_JSON path with a custom JSON file",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50000,
            help="Number of records to process per batch (default: 5000)",
        )
        parser.add_argument(
            "--country",
            type=str,
            help="Import postal codes for a specific country (e.g., NZ)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Import postal codes for all countries that support postal codes",
        )
        parser.add_argument(
            "--create-locations",
            action="store_true",
            help="Create new Location records if they do not exist",
        )

    def safe_strip(self, value):
        """Safely strip a value if it's a string, otherwise return None."""
        return value.strip() if isinstance(value, str) and value.strip() else None

    def normalize_case(self, text):
        """Normalize text to title case."""
        if not text:
            return None
        return ' '.join(word.capitalize() for word in text.lower().split())

    def process_batch(
        self,
        postal_data,
        country_codes,
        stats,
        city_cache,
        location_cache,
        country_cache,
        create_locations,
        user,
        admin2_map,
        region_cache,
        subregion_cache,
        country_category
    ):
        updated_locations = []
        new_locations = []
        new_cities = []
        new_subregions = []
        skipped_sample = []
        city_temp_cache = {}
        subregion_temp_cache = {}

        valid_categories = ['unitary_state', 'federal_state', 'quasi_federal_state']
        if country_category not in valid_categories:
            logger.warning(f"Invalid country category '{country_category}', defaulting to 'federal_state'")
            country_category = 'federal_state'

        for index, record in enumerate(postal_data, stats['total_records'] + 1):
            try:
                country_code = self.safe_strip(record.get('country_code'))
                if not country_code or country_code not in country_codes:
                    continue

                city_name = self.safe_strip(record.get('place_name'))
                postal_code = self.safe_strip(record.get('postal_code'))
                admin_code1 = self.safe_strip(record.get('admin_code1'))
                admin_code2 = self.safe_strip(record.get('admin_code2'))
                admin_code3 = self.safe_strip(record.get('admin_code3'))
                latitude = record.get('latitude')
                longitude = record.get('longitude')
                admin_name1 = self.safe_strip(record.get('admin_name1'))
                admin_name2 = self.safe_strip(record.get('admin_name2'))

                # Skip if both admin_code1 and admin_code2 are null
                if not admin_code1 and not admin_code2:
                    stats['skipped_records'] += 1
                    if len(skipped_sample) < 100:
                        skipped_sample.append({
                            'place_name': city_name or 'unknown',
                            'index': index,
                            'country_code': country_code or 'unknown',
                            'reason': "Both admin_code1 and admin_code2 are null"
                        })
                    continue

                if not (city_name and postal_code):
                    stats['missing_names'] += 1
                    if len(skipped_sample) < 100:
                        skipped_sample.append({
                            'place_name': city_name or 'unknown',
                            'index': index,
                            'country_code': country_code or 'unknown',
                            'reason': f"Missing required field: city_name={city_name}, postal_code={postal_code}"
                        })
                    stats['skipped_records'] += 1
                    continue

                if create_locations and (
                    latitude is None or longitude is None
                    or not isinstance(latitude, (int, float))
                    or not isinstance(longitude, (int, float))
                ):
                    if len(skipped_sample) < 100:
                        skipped_sample.append({
                            'place_name': city_name,
                            'index': index,
                            'country_code': country_code,
                            'reason': f"Invalid or missing latitude/longitude: lat={latitude}, lon={longitude}"
                        })
                    stats['skipped_records'] += 1
                    logger.warning(
                        f"Skipping record {city_name} at index {index} "
                        f"(country: {country_code}, postal_code: {postal_code}): Invalid lat/lon"
                    )
                    continue

                normalized_city_name = city_name.lower()

                country = country_cache.get(country_code)
                if not country:
                    raise ValidationError(f"Country with code {country_code} not found or does not support postal codes")

                # Handle admin_code2 being null based on country_category
                if not admin_code2 and country_category in ['unitary_state', 'quasi_federal_state']:
                    admin_code2 = admin_code1
                    admin_name2 = admin_name1

                city_key = (country.id, normalized_city_name, admin_code1, admin_code2 or None)
                city_data = city_cache.get(city_key) or city_temp_cache.get(city_key)

                # Handle non-unique city for admin1 with multiple admin2
                if not city_data and not admin_code2:
                    city_key = (country.id, normalized_city_name, admin_code1, None)
                    city_data = city_cache.get(city_key) or city_temp_cache.get(city_key)
                    if city_data and (country.id, admin_code1) in admin2_map:
                        admin2_set = admin2_map[(country.id, admin_code1)]
                        if len(admin2_set - {None}) > 0:
                            if len(skipped_sample) < 100:
                                skipped_sample.append({
                                    'place_name': city_name,
                                    'index': index,
                                    'country_code': country_code,
                                    'reason': f"Non-unique city {normalized_city_name} for admin1={admin_code1} with multiple admin2 codes: {admin2_set}"
                                })
                            stats['skipped_records'] += 1
                            logger.warning(
                                f"Skipping record {city_name} at index {index} "
                                f"(country: {country_code}, postal_code: {postal_code}): Non-unique city for admin1={admin_code1}"
                            )
                            continue

                if not city_data and create_locations:
                    # Skip region creation if admin_code1 is null
                    if not admin_code1:
                        stats['skipped_records'] += 1
                        if len(skipped_sample) < 100:
                            skipped_sample.append({
                                'place_name': city_name,
                                'index': index,
                                'country_code': country_code,
                                'reason': "admin_code1 is null, skipping region creation"
                            })
                        continue

                    # Fetch or create region based on admin_code1
                    region_key = (country.id, admin_code1)
                    region = region_cache.get(region_key)
                    if not region:
                        region = CustomRegion.objects.filter(
                            country_id=country.id,
                            code=admin_code1
                        ).first()
                        if not region:
                            admin_name1 = admin_name1 or f"Region {admin_code1}"
                            region = CustomRegion(
                                country_id=country.id,
                                name=admin_name1,
                                code=admin_code1,
                                created_by=user,
                                updated_by=user
                            )
                            region.save()
                            region_cache[region_key] = region
                            logger.info(f"Created region: {region.name} (code: {region.code}, country_id: {country.id})")
                        else:
                            region_cache[region_key] = region
                            logger.info(f"Reused existing region: {region.name} (code: {region.code}, country_id: {country.id})")

                    # Fetch or create subregion
                    subregion_key = (region.id, admin_code2 or None)
                    subregion = subregion_cache.get(subregion_key) or subregion_temp_cache.get(subregion_key)

                    if not subregion:
                        if country_category == 'federal_state' and admin_code2 and admin_code2 != admin_code1:
                            if not admin_name2:
                                if len(skipped_sample) < 100:
                                    skipped_sample.append({
                                        'place_name': city_name,
                                        'index': index,
                                        'country_code': country_code,
                                        'reason': f"Missing admin_name2 for subregion with admin_code2={admin_code2} in region {admin_code1}"
                                    })
                                stats['skipped_records'] += 1
                                logger.warning(
                                    f"Skipping record {city_name} at index {index} "
                                    f"(country: {country_code}, postal_code: {postal_code}): Missing admin_name2 for subregion"
                                )
                                continue
                            subregion = CustomSubRegion.objects.filter(
                                region_id=region.id,
                                code=admin_code2
                            ).first() or CustomSubRegion.objects.filter(
                                region_id=region.id,
                                name=admin_name2
                            ).first()
                            if subregion:
                                if subregion.code != admin_code2:
                                    subregion.code = admin_code2
                                    subregion.updated_by = user
                                    subregion.save()
                                subregion_cache[subregion_key] = subregion
                                subregion_temp_cache[subregion_key] = subregion
                                logger.info(f"Reused existing subregion: {subregion.name} (code: {subregion.code}, region_id: {region.id})")
                            else:
                                subregion = CustomSubRegion(
                                    region_id=region.id,
                                    name=admin_name2,
                                    code=admin_code2,
                                    created_by=user,
                                    updated_by=user
                                )
                                new_subregions.append(subregion)
                                subregion_temp_cache[subregion_key] = subregion
                                logger.info(f"Created subregion: {subregion.name} (code: {subregion.code}, region_id: {region.id})")
                        elif country_category in ['unitary_state', 'quasi_federal_state']:
                            # Use admin_name2 or admin_code2 or region.name
                            subregion_name = admin_name2 or admin_code2 or region.name
                            subregion = CustomSubRegion.objects.filter(
                                region_id=region.id,
                                code=admin_code2
                            ).first() or CustomSubRegion.objects.filter(
                                region_id=region.id,
                                name=subregion_name
                            ).first()
                            if subregion:
                                if subregion.code != admin_code2:
                                    subregion.code = admin_code2
                                    subregion.updated_by = user
                                    subregion.save()
                                subregion_cache[subregion_key] = subregion
                                subregion_temp_cache[subregion_key] = subregion
                                logger.info(f"Reused existing subregion: {subregion.name} (code: {subregion.code}, region_id: {region.id})")
                            else:
                                subregion = CustomSubRegion(
                                    region_id=region.id,
                                    name=subregion_name,
                                    code=admin_code2,
                                    created_by=user,
                                    updated_by=user
                                )
                                new_subregions.append(subregion)
                                subregion_temp_cache[subregion_key] = subregion
                                logger.info(f"Created subregion: {subregion.name} (code: {subregion.code}, region_id: {region.id})")
                        else:
                            if len(skipped_sample) < 100:
                                skipped_sample.append({
                                    'place_name': city_name,
                                    'index': index,
                                    'country_code': country_code,
                                    'reason': f"Subregion not found for region {region.name}, admin_code2={admin_code2}"
                                })
                            stats['skipped_records'] += 1
                            logger.warning(
                                f"Skipping record {city_name} at index {index} "
                                f"(country: {country_code}, postal_code: {postal_code}): Subregion not found"
                            )
                            continue

                    if subregion:
                        city = CustomCity(
                            name=city_name,
                            subregion=subregion,
                            code=admin_code3 or None,
                            latitude=latitude,
                            longitude=longitude,
                            created_by=user,
                            updated_by=user
                        )
                        new_cities.append(city)
                        city_temp_cache[city_key] = {'city': city, 'admin3_code': admin_code3}
                        stats['created_cities'] = stats.get('created_cities', 0) + 1

                if not city_data and not city_temp_cache.get(city_key):
                    stats['skipped_cities'] += 1
                    if len(skipped_sample) < 100:
                        skipped_sample.append({
                            'place_name': city_name,
                            'index': index,
                            'country_code': country_code,
                            'reason': f"City {normalized_city_name} with admin1={admin_code1}, admin2={admin_code2} not found in database"
                        })
                    stats['skipped_records'] += 1
                    logger.warning(
                        f"Skipping record {city_name} at index {index} "
                        f"(country: {country_code}, postal_code: {postal_code}): City not found"
                    )
                    continue

                city = city_data['city'] if city_data else city_temp_cache.get(city_key, {}).get('city')
                if not city:
                    continue

                postal_code_key = postal_code or ''
                location_key = (city.id if hasattr(city, 'id') else id(city), postal_code_key)
                location = location_cache.get(location_key)

                street_address = self.normalize_case(normalized_city_name)
                if not street_address:
                    raise ValidationError(f"Failed to normalize street_address for city {city_name}")

                if not location and create_locations:
                    if location_key in location_cache:
                        if len(skipped_sample) < 100:
                            skipped_sample.append({
                                'place_name': city_name,
                                'index': index,
                                'country_code': country_code,
                                'reason': f"Location already exists for city_id={city.id if hasattr(city, 'id') else id(city)}, postal_code={postal_code}"
                            })
                        stats['skipped_records'] += 1
                        logger.warning(
                            f"Skipping record {city_name} at index {index} "
                            f"(country: {country_code}, postal_code: {postal_code}): Location already exists"
                        )
                        continue

                    location = Location(
                        city=city,
                        postal_code=postal_code,
                        street_address=street_address,
                        latitude=latitude,
                        longitude=longitude,
                        created_by=user,
                        updated_by=user
                    )
                    new_locations.append(location)
                    location_cache[location_key] = location
                elif location:
                    location.postal_code = postal_code
                    location.street_address = street_address
                    location.latitude = latitude
                    location.longitude = longitude
                    updated_locations.append(location)
                elif not create_locations:
                    if len(skipped_sample) < 100:
                        skipped_sample.append({
                            'place_name': city_name,
                            'index': index,
                            'country_code': country_code,
                            'reason': f"Location with postal_code {postal_code} not found for city {normalized_city_name} (city_id: {city.id if hasattr(city, 'id') else id(city)})"
                        })
                    stats['skipped_records'] += 1
                    logger.warning(
                        f"Skipping record {city_name} at index {index} "
                        f"(country: {country_code}, postal_code: {postal_code}): Location not found"
                    )
                    continue

            except ValidationError as e:
                if len(skipped_sample) < 100:
                    skipped_sample.append({
                        'place_name': city_name or 'unknown',
                        'index': index,
                        'country_code': country_code or 'unknown',
                        'reason': str(e)
                    })
                stats['skipped_records'] += 1
                logger.warning(
                    f"Skipping record {city_name or 'unknown'} at index {index} "
                    f"(country: {country_code or 'unknown'}): {e}"
                )
                continue

        # Bulk create sections
        with transaction.atomic():
            if new_subregions:
                CustomSubRegion.objects.bulk_create(new_subregions, batch_size=1000, ignore_conflicts=True)
                saved_subregions = CustomSubRegion.objects.filter(
                    region_id__in=[s.region_id for s in new_subregions],
                    code__in=[s.code for s in new_subregions if s.code]
                )
                subregion_cache.update({(s.region_id, s.code or None): s for s in saved_subregions})
                new_subregions.clear()

        with transaction.atomic():
            if new_cities:
                rebound_cities = []
                for city in new_cities:
                    region_id = getattr(city.subregion, "region_id", None) or getattr(city.subregion.region, "id", None)
                    sub_code = city.subregion.code or None

                    saved_sub = subregion_cache.get((region_id, sub_code))
                    if not saved_sub:
                        saved_sub = CustomSubRegion.objects.filter(
                            region_id=region_id,
                            code=sub_code
                        ).first()
                    if not saved_sub:
                        subregion_name = city.subregion.name
                        saved_sub = CustomSubRegion.objects.filter(
                            region_id=region_id,
                            name=subregion_name
                        ).first()
                        if saved_sub:
                            subregion_cache[(region_id, sub_code)] = saved_sub
                        else:
                            logger.error(f"Could not resolve subregion for region_id={region_id}, code={sub_code}")
                            continue

                    city.subregion = saved_sub
                    rebound_cities.append(city)

                CustomCity.objects.bulk_create(rebound_cities, batch_size=1000, ignore_conflicts=True)
                saved_cities = CustomCity.objects.filter(
                    name__in=[c.name for c in rebound_cities],
                    subregion__region_id__in={c.subregion.region_id for c in rebound_cities}
                ).select_related('subregion__region')
                for city in saved_cities:
                    city_key = (
                        city.subregion.region.country_id,
                        city.name.lower(),
                        city.subregion.region.code,
                        city.subregion.code or None
                    )
                    city_cache[city_key] = {'city': city, 'admin3_code': city.code}
                stats['created_cities'] += len(saved_cities)
                new_cities.clear()

        with transaction.atomic():
            if new_locations:
                for location in new_locations:
                    city_key = (
                        location.city.subregion.region.country_id,
                        location.city.name.lower(),
                        location.city.subregion.region.code,
                        location.city.subregion.code or None
                    )
                    saved_city = city_cache.get(city_key, {}).get('city')
                    if saved_city:
                        location.city = saved_city
                valid_locations = [loc for loc in new_locations if loc.city.id is not None]
                if valid_locations:
                    Location.objects.bulk_create(valid_locations, batch_size=1000, ignore_conflicts=True)
                    stats['created_locations'] += len(valid_locations)
                new_locations.clear()

        return updated_locations, new_locations, skipped_sample

    def handle(self, *args, **options):
        start_time = time.time()
        batch_size = options.get('batch_size', 5000)
        country_code = options.get('country')
        import_all = options.get('all')
        create_locations = options.get('create_locations')
        stats = {
            'updated_locations': 0,
            'created_locations': 0,
            'created_cities': 0,
            'skipped_records': 0,
            'skipped_cities': 0,
            'missing_names': 0,
            'total_records': 0,
        }

        self.stdout.write(f"Starting postal codes update... ({time.time() - start_time:.2f}s)")
        if create_locations:
            logger.warning("Running script with create locations enabled")
        if not logger.isEnabledFor(logging.DEBUG):
            logger.setLevel(logging.INFO)

        if country_code and import_all:
            self.stderr.write(self.style.ERROR("Cannot use --country and --all together."))
            return

        env_start = time.time()
        env_data = load_env_paths(env_var='POSTAL_CODES_JSON', file=options.get('postal_file'))
        postal_base_path = env_data.get('POSTAL_CODES_JSON')
        self.stdout.write(f"Environment paths loaded in {time.time() - env_start:.2f}s")
        if not postal_base_path:
            self.stderr.write(self.style.ERROR(f"Failed to load POSTAL_CODES_JSON path ({time.time() - start_time:.2f}s)"))
            return

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

        # Load countries
        country_start = time.time()
        country_cache = {}
        countries_to_process = []
        if import_all:
            countries_to_process = list(CustomCountry.objects.filter(has_postal_code=True).only('id', 'country_code'))
        elif country_code:
            country = CustomCountry.objects.filter(country_code=country_code.upper(), has_postal_code=True).only('id', 'country_code').first()
            if not country:
                self.stderr.write(self.style.ERROR(f"Country with code '{country_code}' not found or does not support postal codes. ({time.time() - start_time:.2f}s)"))
                return
            countries_to_process = [country]
        else:
            self.stderr.write(self.style.ERROR("Must specify either --country or --all."))
            return
        country_cache = {c.country_code: c for c in countries_to_process}
        country_codes = list(country_cache.keys())
        self.stdout.write(f"Countries loaded in {time.time() - country_start:.2f}s")

        # Load caches
        cache_start = time.time()
        city_cache = {
            (c.subregion.region.country_id, c.name.lower(), c.subregion.region.code, c.subregion.code or None): {
                'city': c,
                'admin3_code': getattr(c, 'code', None)
            } for c in CustomCity.objects.filter(
                subregion__region__country_id__in=[c.id for c in countries_to_process],
                subregion__is_active=True,
                subregion__region__is_active=True
            ).select_related('subregion__region').only(
                'id', 'name', 'code', 'subregion__code', 'subregion__region__code', 'subregion__region__country_id'
            )
        }

        admin2_map = {}
        for key in city_cache:
            country_id, _, admin1, admin2 = key
            if (country_id, admin1) not in admin2_map:
                admin2_map[(country_id, admin1)] = set()
            if admin2:
                admin2_map[(country_id, admin1)].add(admin2)

        location_cache = {
            (loc.city_id, loc.postal_code or ''): loc for loc in Location.objects.filter(
                city__subregion__region__country_id__in=[c.id for c in countries_to_process],
                deleted_at__isnull=True
            ).only('id', 'city_id', 'postal_code', 'street_address', 'latitude', 'longitude')
        }

        region_cache = {
            (r.country_id, r.code): r for r in CustomRegion.objects.filter(
                country_id__in=[c.id for c in countries_to_process]
            ).only('id', 'country_id', 'code', 'name')
        }

        subregion_cache = {
            (s.region_id, s.code or None): s for s in CustomSubRegion.objects.filter(
                region__country_id__in=[c.id for c in countries_to_process]
            ).only('id', 'region_id', 'code', 'name')
        }

        self.stdout.write(f"Caches loaded in {time.time() - cache_start:.2f}s")

        for country in countries_to_process:
            sample_cities = [(k[1], k[2], k[3]) for k in list(city_cache.keys())[:10] if k[0] == country.id]
            self.stdout.write(f"Sample cities for {country.country_code}: {sample_cities}")

        updated_locations = []
        new_locations = []
        all_skipped_samples = []
        for country in countries_to_process:
            country_code = country.country_code
            try:
                country_category = get_country_administrative_category(country_code)
            except InvalidLocationData as e:
                self.stderr.write(self.style.ERROR(f"Error retrieving country category for {country_code}: {e}"))
                logger.error(f"Error retrieving country category for {country_code}: {e}")
                continue

            orig_create = create_locations
            if country_category == 'quasi_federal_state':
                create_locations = True
                if orig_create:
                    logger.warning("Creation of new locations, cities, and subregions disabled for quasi_federal_state countries.")

            postal_filename = os.path.join(postal_base_path, f"{country_code}.json") if not options.get('postal_file') else options.get('postal_file')

            if not os.path.exists(postal_filename):
                self.stderr.write(self.style.ERROR(f"Postal codes file not found: {postal_filename} ({time.time() - start_time:.2f}s)"))
                continue

            try:
                json_start = time.time()
                with open(postal_filename, encoding='utf-8') as f:
                    if os.path.getsize(postal_filename) == 0:
                        self.stderr.write(self.style.ERROR(f"JSON file {postal_filename} is empty ({time.time() - start_time:.2f}s)"))
                        continue
                    postal_data = json.load(f)
                    stats['total_records'] += len(postal_data)
                self.stdout.write(f"JSON loaded in {time.time() - json_start:.2f}s")

                for i in range(0, len(postal_data), batch_size):
                    batch_start = time.time()
                    batch = postal_data[i:i + batch_size]
                    self.stdout.write(f"Processing batch of {len(batch)} records (Total: {i + len(batch)}, {time.time() - start_time:.2f}s)")
                    batch_updated, batch_new, skipped_sample = self.process_batch(
                        batch, country_codes, stats, city_cache, location_cache, country_cache, create_locations, user, admin2_map, region_cache, subregion_cache, country_category
                    )
                    updated_locations.extend(batch_updated)
                    new_locations.extend(batch_new)
                    all_skipped_samples.extend(skipped_sample)

                    if updated_locations:
                        with transaction.atomic():
                            Location.objects.bulk_update(
                                [loc for loc in updated_locations if loc.pk],
                                ['postal_code', 'street_address', 'latitude', 'longitude'],
                                batch_size=batch_size
                            )
                            self.stdout.write(f"Updated {len(updated_locations)} locations in batch ({time.time() - start_time:.2f}s)")
                            stats['updated_locations'] += len(updated_locations)
                            updated_locations.clear()

                    self.stdout.write(f"Batch processed in {time.time() - batch_start:.2f}s")

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to process postal codes JSON file: {e} ({time.time() - start_time:.2f}s)"))
                logger.error(f"Failed to process postal codes JSON file: {e}", exc_info=True)
                continue

        self.stdout.write(self.style.SUCCESS(f"Postal Codes Update Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total records: {stats['total_records']}")
        self.stdout.write(f"  - Locations updated: {stats['updated_locations']}")
        self.stdout.write(f"  - Locations created: {stats['created_locations']}")
        self.stdout.write(f"  - Cities created: {stats['created_cities']}")
        self.stdout.write(f"  - Cities skipped: {stats['skipped_cities']}")
        self.stdout.write(f"  - Records skipped: {stats['skipped_records']}")
        self.stdout.write(f"  - Missing names/codes: {stats['missing_names']}")
        if all_skipped_samples:
            for skipped in all_skipped_samples[:5]:
                self.stdout.write(f"    - Place: {skipped['place_name']} (Index: {skipped['index']}, country: {skipped['country_code']}, reason: {skipped['reason']})")
            if len(all_skipped_samples) > 5:
                self.stdout.write(f"    - ... and {len(all_skipped_samples) - 5} more skipped records")
        self.stdout.write(self.style.SUCCESS(f"Postal Codes Updated in {time.time() - start_time:.2f}s"))
        logger.info(
            f"Summary: Total={stats['total_records']}, "
            f"Locations Updated={stats['updated_locations']}, Locations Created={stats['created_locations']}, "
            f"Cities Created={stats['created_cities']}, Cities Skipped={stats['skipped_cities']}, "
            f"Records Skipped={stats['skipped_records']}, Missing Names/Codes={stats['missing_names']}"
        )
