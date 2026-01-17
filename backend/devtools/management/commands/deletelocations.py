import logging
import time

from core.utils.redis_client import redis_client
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, Location

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Permanently deletes all cities, locations, regions, and subregions for the specified country code from the database.'

    def add_arguments(self, parser):
        parser.add_argument('--country', type=str, required=True, help='ISO-3166 2-letter country code (e.g., NZ)')
        parser.add_argument('--batch-size', type=int, default=1000, help='Number of records to delete in each batch')

    def handle(self, *args, **options):
        start_time = time.time()
        country_code = options['country'].upper()
        batch_size = options['batch_size']

        # Get admin user for audit fields
        User = get_user_model()
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username} (ID: {admin_user.id}) ({time.time() - start_time:.2f}s)"))
            logger.info(f"Using user: {admin_user.username} ({time.time() - start_time:.2f}s)")
        except User.DoesNotExist:
            error_msg = f"User with id=1 not found. Please ensure admin user exists. ({time.time() - start_time:.2f}s)"
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        if batch_size <= 0:
            self.stdout.write(self.style.ERROR(f"Batch size must be a positive integer. ({time.time() - start_time:.2f}s)"))
            logger.error(f"Invalid batch size: {batch_size} ({time.time() - start_time:.2f}s)")
            return

        try:
            with transaction.atomic():
                # Step 1: Find the country with the specified code
                try:
                    country = CustomCountry.objects.get(country_code=country_code)
                    self.stdout.write(self.style.SUCCESS(f"Found country: {country.name} (ID: {country.pk}) ({time.time() - start_time:.2f}s)"))
                    logger.info(f"Found country for deletion: {country.name} (ID: {country.pk}, Code: {country_code}) ({time.time() - start_time:.2f}s)")
                except CustomCountry.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Country with code '{country_code}' not found. ({time.time() - start_time:.2f}s)"))
                    logger.error(f"Country with code '{country_code}' not found. ({time.time() - start_time:.2f}s)")
                    return

                # Step 2: Delete all locations for cities in the country
                location_count = 0
                location_ids = Location.objects.filter(city__subregion__region__country=country).values_list('id', flat=True)
                total_locations = len(location_ids)
                for i in range(0, total_locations, batch_size):
                    batch_ids = location_ids[i:i + batch_size]
                    batch_count = Location.objects.filter(id__in=batch_ids).delete()[0]
                    location_count += batch_count
                    logger.info(f"Permanently deleted {batch_count} Location records in batch {i//batch_size + 1} for {country_code}. ({time.time() - start_time:.2f}s)")
                self.stdout.write(self.style.SUCCESS(f"Permanently deleted {location_count} locations. ({time.time() - start_time:.2f}s)"))

                # Step 3: Delete all cities in the country
                city_count = 0
                city_ids = CustomCity.objects.filter(subregion__region__country=country).values_list('id', flat=True)
                total_cities = len(city_ids)
                for i in range(0, total_cities, batch_size):
                    batch_ids = city_ids[i:i + batch_size]
                    batch_count = CustomCity.objects.filter(id__in=batch_ids).delete()[0]
                    city_count += batch_count
                    logger.info(f"Permanently deleted {batch_count} CustomCity records in batch {i//batch_size + 1} for {country_code}. ({time.time() - start_time:.2f}s)")
                self.stdout.write(self.style.SUCCESS(f"Permanently deleted {city_count} cities. ({time.time() - start_time:.2f}s)"))

                # Step 4: Delete all subregions in the country
                subregion_count = 0
                subregion_ids = CustomSubRegion.objects.filter(region__country=country).values_list('id', flat=True)
                total_subregions = len(subregion_ids)
                for i in range(0, total_subregions, batch_size):
                    batch_ids = subregion_ids[i:i + batch_size]
                    batch_count = CustomSubRegion.objects.filter(id__in=batch_ids).delete()[0]
                    subregion_count += batch_count
                    logger.info(f"Permanently deleted {batch_count} CustomSubRegion records in batch {i//batch_size + 1} for {country_code}. ({time.time() - start_time:.2f}s)")
                self.stdout.write(self.style.SUCCESS(f"Permanently deleted {subregion_count} subregions. ({time.time() - start_time:.2f}s)"))

                # Step 5: Delete all regions in the country
                region_count = 0
                region_ids = CustomRegion.objects.filter(country=country).values_list('id', flat=True)
                total_regions = len(region_ids)
                for i in range(0, total_regions, batch_size):
                    batch_ids = region_ids[i:i + batch_size]
                    batch_count = CustomRegion.objects.filter(id__in=batch_ids).delete()[0]
                    region_count += batch_count
                    logger.info(f"Permanently deleted {batch_count} CustomRegion records in batch {i//batch_size + 1} for {country_code}. ({time.time() - start_time:.2f}s)")
                self.stdout.write(self.style.SUCCESS(f"Permanently deleted {region_count} regions. ({time.time() - start_time:.2f}s)"))

                # Step 6: Clear relevant Redis cache keys
                redis = redis_client.get_client()
                cache_keys = [
                    "location:*:*",
                    "city:*:*",
                    "subregion:*:*",
                    "region:*:*",
                ]
                for pattern in cache_keys:
                    try:
                        keys = redis.keys(pattern)
                        if keys:
                            redis.delete(*keys)
                            logger.info(f"Cleared {len(keys)} cache keys matching pattern: {pattern} ({time.time() - start_time:.2f}s)")
                    except Exception as e:
                        logger.warning(f"Failed to clear cache keys for pattern {pattern}: {str(e)} ({time.time() - start_time:.2f}s)")

                self.stdout.write(self.style.SUCCESS(f"Successfully deleted all records for country code {country_code}. ({time.time() - start_time:.2f}s)"))

        except Exception as e:
            logger.error(f"Error during hard deletion for country code {country_code}: {str(e)} ({time.time() - start_time:.2f}s)", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Failed to delete records for {country_code}: {str(e)} ({time.time() - start_time:.2f}s)"))
            raise
