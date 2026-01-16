import json
import logging
import zlib
from datetime import date, datetime
from decimal import Decimal

from celery import group
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.core.paginator import Paginator
from django_redis import get_redis_connection
from entities.models.entity import Entity
from fincore.models.address import Address
from fincore.models.contact import Contact
from fincore.models.entity_mapping import FincoreEntityMapping
from fincore.models.tax_profile import TaxProfile
from industries.models.industry import Industry
from invoices.models.billing_schedule import BillingSchedule
from invoices.models.gst_configuration import GSTConfiguration
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion, GlobalRegion, Location

from devtools.tasks import (
    cache_address_batch,
    cache_billing_schedule_batch,
    cache_city_batch,
    cache_contact_batch,
    cache_country_batch,
    cache_entity_batch,
    cache_entity_mapping_batch,
    cache_global_region_batch,
    cache_gst_config_batch,
    cache_industry_batch,
    cache_invoice_batch,
    cache_line_item_batch,
    cache_location_batch,
    cache_payment_batch,
    cache_payment_method_batch,
    cache_region_batch,
    cache_status_batch,
    cache_subregion_batch,
    cache_tax_profile_batch,
)

logger = logging.getLogger('django_redis')

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

class Command(BaseCommand):
    help = 'Cache data in Redis with Celery and incremental updates'

    def handle(self, *args, **kwargs):
        try:
            batch_size = 5000
            logger.debug("Connected to Redis for caching")
            redis_conn = get_redis_connection('default')
            last_cache_run = redis_conn.get('last_cache_run')
            if last_cache_run:
                last_cache_run = datetime.fromisoformat(last_cache_run.decode())
                logger.info(f"Last cache run: {last_cache_run}")
            else:
                logger.info("No previous cache run found. Performing full cache.")
                last_cache_run = None

            data_types = [
                (GlobalRegion.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else GlobalRegion.objects.filter(deleted_at__isnull=True), cache_global_region_batch, 'global_regions'),
                (CustomCountry.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else CustomCountry.objects.filter(deleted_at__isnull=True), cache_country_batch, 'countries'),
                (CustomRegion.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else CustomRegion.objects.filter(deleted_at__isnull=True), cache_region_batch, 'regions'),
                (CustomSubRegion.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else CustomSubRegion.objects.filter(deleted_at__isnull=True), cache_subregion_batch, 'subregions'),
                (CustomCity.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else CustomCity.objects.filter(deleted_at__isnull=True), cache_city_batch, 'cities'),
                (Location.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Location.objects.filter(deleted_at__isnull=True), cache_location_batch, 'locations'),
                (Industry.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Industry.objects.filter(deleted_at__isnull=True), cache_industry_batch, 'industries'),
                (Entity.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Entity.objects.filter(deleted_at__isnull=True), cache_entity_batch, 'entities'),
                (Address.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Address.objects.filter(deleted_at__isnull=True), cache_address_batch, 'addresses'),
                (Contact.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Contact.objects.filter(deleted_at__isnull=True), cache_contact_batch, 'contacts'),
                (TaxProfile.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else TaxProfile.objects.filter(deleted_at__isnull=True), cache_tax_profile_batch, 'tax_profiles'),
                (FincoreEntityMapping.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else FincoreEntityMapping.objects.filter(deleted_at__isnull=True), cache_entity_mapping_batch, 'entity_mappings'),
                (Invoice.all_objects.filter(deleted_at__isnull=True, is_active=True, updated_at__gt=last_cache_run) if last_cache_run else Invoice.all_objects.filter(deleted_at__isnull=True, is_active=True), cache_invoice_batch, 'invoices'),
                (LineItem.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else LineItem.objects.filter(deleted_at__isnull=True), cache_line_item_batch, 'line_items'),
                (PaymentMethod.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else PaymentMethod.objects.filter(deleted_at__isnull=True), cache_payment_method_batch, 'payment_methods'),
                (GSTConfiguration.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else GSTConfiguration.objects.filter(deleted_at__isnull=True), cache_gst_config_batch, 'gst_configs'),
                (BillingSchedule.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else BillingSchedule.objects.filter(deleted_at__isnull=True), cache_billing_schedule_batch, 'billing_schedules'),
                (Payment.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Payment.objects.filter(deleted_at__isnull=True), cache_payment_batch, 'payments'),
                (Status.objects.filter(deleted_at__isnull=True, updated_at__gt=last_cache_run) if last_cache_run else Status.objects.filter(deleted_at__isnull=True), cache_status_batch, 'statuses'),
            ]

            for queryset, task, name in data_types:
                paginator = Paginator(queryset.order_by('id'), batch_size)
                total_items = paginator.count
                logger.debug(f"Total {name}: {total_items}, Pages: {paginator.num_pages}")
                self.stdout.write(self.style.SUCCESS(f"Starting to cache {total_items} {name} in {paginator.num_pages} batches"))

                tasks = [task.s(page_num, batch_size=batch_size) for page_num in paginator.page_range]
                job = group(tasks)
                result = job.apply_async()
                # result.join(timeout=3600)
                result.get(timeout=3600)

                for res in result.results:
                    if res.successful():
                        logger.info(res.get())
                        self.stdout.write(self.style.SUCCESS(res.get(timeout=30)))
                    else:
                        logger.error(f"Task {res.id} failed: {res.get(propagate=False, timeout=30)}")
                        self.stdout.write(self.style.ERROR(f"Task {res.id} failed: {res.get(propagate=False, timeout=30)}"))

            logger.info("Building invoices search list for autocomplete")
            redis_conn = get_redis_connection('default')
            invoice_keys = redis_conn.hkeys('invoices')
            all_invoices = []
            pipe = redis_conn.pipeline(transaction=False)
            for key in invoice_keys:
                pipe.hget('invoices', key)
            datas = pipe.execute()
            for data in datas:
                if data:
                    try:
                        inv_data = json.loads(zlib.decompress(data).decode())
                        inv_id = inv_data.get('id')
                        inv_num = inv_data.get('invoice_number')
                        if inv_id and inv_num:
                            all_invoices.append((inv_id, inv_num))
                    except Exception as e:
                        logger.warning(f"Failed to process invoice data for search list: {str(e)}")
            redis_conn.set('invoices_search_list', json.dumps(all_invoices), ex=172800)  # Expire in 2 days
            logger.info(f"Built invoices search list with {len(all_invoices)} entries")

            cache.set('last_cache_run', datetime.now(), timeout=172800)
            logger.info("Completed Redis cache refresh")
            self.stdout.write(self.style.SUCCESS("Completed Redis cache refresh"))

        except Exception as e:
            logger.error(f'Error caching data: {str(e)}', exc_info=True)
            self.stdout.write(self.style.ERROR(f'Error caching data: {str(e)}'))
            raise
