import argparse
import json
import logging
import time
from typing import Dict

from core.utils.redis_client import RedisClient
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as dj_timezone
from locations.models import CustomCity, CustomCountry, Timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Update timezone for cities with null or empty timezone values based on country.
    Example usage:
        ./manage.py update_locations_timezones --country NZ  # Update cities for India
        ./manage.py update_locations_timezones --all        # Update cities for all countries
    Only cities with null/empty timezone will be updated.
    """

    BATCH_SIZE_DEFAULT = 10000
    CACHE_TIMEOUT = 3600  # Cache timeout in seconds (1 hour)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.RawTextHelpFormatter
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--country",
            type=str,
            help="ISO 3166-1 alpha-2 country code to update cities (e.g., 'IN' for India)",
        )
        group.add_argument(
            "--all",
            action="store_true",
            help="Update timezones for all cities across all countries",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=self.BATCH_SIZE_DEFAULT,
            help=f"Batch size for bulk operations (default: {self.BATCH_SIZE_DEFAULT})",
        )

    def get_country_timezone_map(self, redis_client: RedisClient) -> Dict[str, str]:
        """Create a mapping of country codes to their primary timezone ID, using Redis cache."""
        cache_key = 'timezone_map'
        cached_map = redis_client.get(cache_key)
        if cached_map:
            logger.debug("Retrieved timezone map from Redis cache")
            return json.loads(cached_map)

        timezone_map = {}
        timezones = Timezone.objects.filter(is_active=True).values('country_code', 'timezone_id', 'raw_offset')
        for tz in timezones:
            if tz['country_code']:
                # Prioritize timezones with non-zero offset or most common for the country
                if tz['country_code'] not in timezone_map or tz['raw_offset'] != 0:
                    timezone_map[tz['country_code']] = tz['timezone_id']

        try:
            redis_client.set(cache_key, json.dumps(timezone_map), ex=self.CACHE_TIMEOUT)
            logger.debug(f"Cached timezone map in Redis with key {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache timezone map: {str(e)}")

        return timezone_map

    def get_timezone_cache(self, timezone_ids: list, redis_client: RedisClient) -> Dict[str, Timezone]:
        """Cache timezone objects in Redis and return a dictionary of timezone_id to Timezone objects."""
        cache_key_prefix = 'timezone:'
        timezone_cache = {}
        missing_ids = []

        # Check Redis for cached timezones
        for tz_id in timezone_ids:
            cache_key = f"{cache_key_prefix}{tz_id}"
            cached_tz = redis_client.get(cache_key)
            if cached_tz:
                tz_data = json.loads(cached_tz)
                timezone_cache[tz_id] = Timezone(timezone_id=tz_data['timezone_id'])
                logger.debug(f"Retrieved timezone {tz_id} from Redis cache")
            else:
                missing_ids.append(tz_id)

        # Fetch missing timezones from database
        if missing_ids:
            db_timezones = Timezone.objects.filter(timezone_id__in=missing_ids).only('timezone_id')
            for tz in db_timezones:
                timezone_cache[tz.timezone_id] = tz
                try:
                    tz_data = {'timezone_id': tz.timezone_id}
                    redis_client.set(f"{cache_key_prefix}{tz.timezone_id}", json.dumps(tz_data), ex=self.CACHE_TIMEOUT)
                    logger.debug(f"Cached timezone {tz.timezone_id} in Redis")
                except Exception as e:
                    logger.warning(f"Failed to cache timezone {tz.timezone_id}: {str(e)}")

        return timezone_cache

    def process_batch(self, cities, timezone_map: Dict[str, str], user, stats: Dict, timezone_cache: Dict) -> None:
        """Process a batch of cities to update their timezones."""
        update_cities = []
        for city in cities:
            try:
                country_code = city['subregion__region__country__country_code']
                if not country_code or country_code not in timezone_map:
                    stats['skipped'].append({
                        'city_id': city['id'],
                        'city': city['name'],
                        'country': city['country_name'],
                        'reason': f"No timezone found for country code {country_code}"
                    })
                    logger.warning(f"Skipping city {city['id']} (city: {city['name']}, country: {city['country_name']}): No timezone for country code {country_code}")
                    continue

                timezone_id = timezone_map[country_code]
                timezone = timezone_cache.get(timezone_id)
                if not timezone:
                    stats['skipped'].append({
                        'city_id': city['id'],
                        'city': city['name'],
                        'country': city['country_name'],
                        'reason': f"Timezone {timezone_id} not found"
                    })
                    logger.warning(f"Skipping city {city['id']} (city: {city['name']}, country: {city['country_name']}): Timezone {timezone_id} not found")
                    continue

                update_cities.append(
                    CustomCity(
                        id=city['id'],
                        timezone=timezone,
                        updated_by=user,
                        updated_at=dj_timezone.now()
                    )
                )
                stats['updated_cities'] += 1
                logger.debug(f"Queued timezone update for city ID {city['id']} (city: {city['name']}) to {timezone_id}")

            except Exception as e:
                stats['skipped'].append({
                    'city_id': city['id'],
                    'city': city['name'],
                    'country': city['country_name'],
                    'reason': str(e)
                })
                logger.warning(f"Skipping city {city['id']}: {str(e)}")

        if update_cities:
            try:
                with transaction.atomic():
                    CustomCity.objects.bulk_update(
                        update_cities,
                        ['timezone', 'updated_by', 'updated_at'],
                        batch_size=self.BATCH_SIZE_DEFAULT
                    )
                logger.info(f"Updated {len(update_cities)} cities in batch")
            except Exception as e:
                logger.error(f"Failed to bulk update cities: {str(e)}", exc_info=True)
                stats['errors'].append(str(e))

    def handle(self, *args, **options) -> None:
        start_time = time.time()
        batch_size = options['batch_size']
        country_code = options.get('country')
        update_all = options.get('all')
        stats = {
            'updated_cities': 0,
            'skipped': [],
            'errors': [],
            'total': 0
        }

        print(f"Selected: {update_all}")

        redis_client = RedisClient.get_client()

        self.stdout.write(f"Starting city timezone update... ({time.time() - start_time:.2f}s)")
        logger.info("Starting city timezone update")

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

        # Get country-timezone mapping
        tz_start = time.time()
        timezone_map = self.get_country_timezone_map(redis_client)
        if not timezone_map:
            self.stderr.write(self.style.ERROR(f"No active timezones found in database ({time.time() - start_time:.2f}s)"))
            logger.error("No active timezones found in database")
            return
        self.stdout.write(f"Timezone map loaded in {time.time() - tz_start:.2f}s")

        # Cache timezone objects
        timezone_cache = self.get_timezone_cache(list(timezone_map.values()), redis_client)

        # # Build country filter
        # country_start = time.time()
        # countries_cache_key = 'countries_to_process'
        # cached_countries = redis_client.get(countries_cache_key)
        # if cached_countries:
        #     countries_to_process = json.loads(cached_countries)
        #     logger.debug("Retrieved countries from Redis cache")
        #     # In the handle method, after building countries_to_process
        #     logger.info(f"Countries to process: {[c['country_code'] for c in countries_to_process]}")
        #     self.stdout.write(f"Countries to process: {[c['country_code'] for c in countries_to_process]}")
        # else:
        #     countries_to_process = []
        #     if update_all:
        #         countries_to_process = list(CustomCountry.objects.filter(
        #             country_code__in=timezone_map.keys(),
        #             regions__subregions__cities__timezone__isnull=True
        #         ).distinct().values('id', 'country_code'))
        #     elif country_code:
        #         try:
        #             country = CustomCountry.objects.filter(country_code=country_code.upper()).values('id', 'country_code').first()
        #             if not country:
        #                 self.stderr.write(self.style.ERROR(f"Country with code {country_code} not found ({time.time() - start_time:.2f}s)"))
        #                 logger.error(f"Country with code {country_code} not found")
        #                 return
        #             countries_to_process = [country]
        #         except CustomCountry.DoesNotExist:
        #             self.stderr.write(self.style.ERROR(f"Country with code {country_code} not found ({time.time() - start_time:.2f}s)"))
        #             logger.error(f"Country with code {country_code} not found")
        #             return
        #     try:
        #         redis_client.set(countries_cache_key, json.dumps(countries_to_process), ex=self.CACHE_TIMEOUT)
        #         logger.debug(f"Cached countries list in Redis with key {countries_cache_key}")
        #     except Exception as e:
        #         logger.warning(f"Failed to cache countries list: {str(e)}")
        # self.stdout.write(f"Countries loaded in {time.time() - country_start:.2f}s")

        # Build country filter
        country_start = time.time()
        countries_cache_key = f'countries_to_process_{country_code if country_code else "all"}'
        cached_countries = redis_client.get(countries_cache_key)
        if cached_countries:
            countries_to_process = json.loads(cached_countries)
            logger.debug("Retrieved countries from Redis cache")
        else:
            countries_to_process = []
            if update_all:
                countries_to_process = list(CustomCountry.objects.filter(
                    country_code__in=timezone_map.keys(),
                    regions__subregions__cities__timezone__isnull=True
                ).distinct().values('id', 'country_code'))
            elif country_code:
                country = CustomCountry.objects.filter(country_code=country_code.upper()).values('id', 'country_code').first()
                if not country:
                    self.stderr.write(self.style.ERROR(f"Country with code {country_code} not found ({time.time() - start_time:.2f}s)"))
                    logger.error(f"Country with code {country_code} not found")
                    return
                countries_to_process = [country]
            try:
                redis_client.set(countries_cache_key, json.dumps(countries_to_process), ex=self.CACHE_TIMEOUT)
                logger.debug(f"Cached countries list in Redis with key {countries_cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache countries list: {str(e)}")
        logger.info(f"Countries to process: {[c['country_code'] for c in countries_to_process]}")
        self.stdout.write(f"Countries to process: {[c['country_code'] for c in countries_to_process]}")
        self.stdout.write(f"Countries loaded in {time.time() - country_start:.2f}s")

        # Build city query using values() to fetch only needed fields
        cities_query = CustomCity.objects.filter(
            timezone__isnull=True,
            subregion__region__country_id__in=[c['id'] for c in countries_to_process],
            subregion__is_active=True,
            subregion__region__is_active=True
        ).values(
            'id',
            'name',
            'subregion__region__country__country_code',
            'subregion__region__country__name'
        )


        stats['total'] = cities_query.count()
        if stats['total'] == 0:
            self.stdout.write(self.style.WARNING(f"No cities found to update ({time.time() - start_time:.2f}s)"))
            logger.info("No cities found to update")
            return

        # Process cities in batches
        cities = cities_query.iterator(chunk_size=batch_size)
        batch = []
        for index, city in enumerate(cities, 1):
            batch.append(city)
            if len(batch) >= batch_size or index == stats['total']:
                batch_start = time.time()
                self.process_batch(batch, timezone_map, user, stats, timezone_cache)
                self.stdout.write(f"Processed {index} cities ({time.time() - start_time:.2f}s)")
                batch.clear()
                self.stdout.write(f"Batch processed in {time.time() - batch_start:.2f}s")

        # Log summary
        self.stdout.write(self.style.SUCCESS(f"City Timezone Update Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f"  - Total cities: {stats['total']}")
        self.stdout.write(f"  - Cities updated: {stats['updated_cities']}")
        self.stdout.write(f"  - Cities skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f"    - City ID: {skipped['city_id']} (City: {skipped['city']}, Country: {skipped['country']}): {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f"    - ... and {len(stats['skipped']) - 5} more skipped records")
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"  - Errors encountered: {len(stats['errors'])}"))
            for error in stats['errors'][:5]:
                self.stdout.write(f"    - Error: {error}")
            if len(stats['errors']) > 5:
                self.stdout.write(f"    - ... and {len(stats['errors']) - 5} more errors")
        logger.info(
            f"City Timezone Update Summary: Total={stats['total']}, "
            f"Updated={stats['updated_cities']}, Skipped={len(stats['skipped'])}, "
            f"Errors={len(stats['errors'])}"
        )
        self.stdout.write(self.style.SUCCESS(f"City Timezone Update Completed in {time.time() - start_time:.2f}s"))
