import json
import logging
import time
import zlib
from datetime import date, datetime
from decimal import Decimal

from celery import shared_task
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField
from django.db.models.functions import Cast
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
from locations.models import CustomCountry, GlobalRegion
from locations.models.custom_city import CustomCity
from locations.models.custom_region import CustomRegion
from locations.models.custom_subregion import CustomSubRegion
from locations.models.location import Location
from rest_framework import serializers

logger = logging.getLogger('django_redis')

class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

class GlobalRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRegion
        fields = ('id', 'name', 'location_source')

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCountry
        fields = ('id', 'name', 'country_code', 'location_source')

class RegionSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        country_data = redis_conn.hget('countries', instance.country_id)
        return {
            'id': instance.id,
            'name': instance.name,
            'country_id': instance.country_id,
            'country_name': json.loads(country_data)['name'] if country_data else instance.country.name,
            'location_source': instance.location_source
        }

    class Meta:
        model = CustomRegion
        fields = ('id', 'name', 'country_id', 'country_name')

class SubRegionSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        region_data = redis_conn.hget('regions', instance.region_id)
        return {
            'id': instance.id,
            'name': instance.name,
            'region_id': instance.region_id,
            'region_name': json.loads(region_data)['name'] if region_data else instance.region.name,
            'location_source': instance.location_source
        }

    class Meta:
        model = CustomSubRegion
        fields = ('id', 'name', 'region_id', 'region_name')

class CitySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        subregion_data = redis_conn.hget('subregions', instance.subregion_id)
        return {
            'id': instance.id,
            'name': instance.name,
            'subregion_id': instance.subregion_id,
            'subregion_name': json.loads(subregion_data)['name'] if subregion_data else instance.subregion.name,
            'location_source': instance.location_source
        }

    class Meta:
        model = CustomCity
        fields = ('id', 'name', 'subregion_id', 'subregion_name')

class LocationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        city_data = redis_conn.hget('cities', instance.city_id)
        return {
            'id': instance.id,
            'city_id': instance.city_id,
            'city_name': json.loads(zlib.decompress(city_data).decode())['name'] if city_data else instance.city.name,
            'postal_code': instance.postal_code,
            'location_source': instance.location_source
        }

    class Meta:
        model = Location
        fields = ('id', 'city_name', 'city_id', 'postal_code', 'location_source')

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ('id', 'description')

class EntitySerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        industry_data = redis_conn.hget('industries', instance.industry_id)
        redis_conn.hget('addresses', instance.default_address_id) if instance.default_address_id else None
        return {
            'id': instance.id,
            'name': instance.name,
            'slug': instance.slug,
            'entity_type': instance.entity_type,
            'status': instance.status,
            'external_id': instance.external_id,
            'website': instance.website,
            'registration_number': instance.registration_number,
            'entity_size': instance.entity_size,
            'notes': instance.notes,
            'industry_id': instance.industry_id,
            'industry_description': json.loads(industry_data)['description'] if industry_data else instance.industry.description,
            'default_address_id': instance.default_address_id,
        }

    class Meta:
        model = Entity
        fields = ('id', 'name', 'slug', 'entity_type', 'status', 'external_id',
                 'website', 'registration_number', 'entity_size', 'notes',
                 'industry_id', 'industry_description', 'default_address_id')

class AddressSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        city_data = redis_conn.hget('cities', instance.city_id)
        region_data = redis_conn.hget('regions', instance.region_id) if instance.region_id else None
        subregion_data = redis_conn.hget('subregions', instance.subregion_id) if instance.subregion_id else None
        country_data = redis_conn.hget('countries', instance.country_id)
        return {
            'id': instance.id,
            'entity_mapping_id': instance.entity_mapping_id,
            'address_type': instance.address_type,
            'street_address': instance.street_address,
            'city_id': instance.city_id,
            'city_name': json.loads(zlib.decompress(city_data).decode())['name'] if city_data else instance.city.name,
            'postal_code': instance.postal_code,
            'country_id': instance.country_id,
            'country_name': json.loads(country_data)['name'] if country_data else instance.country.name,
            'region_id': instance.region_id,
            'region_name': json.loads(region_data)['name'] if region_data and instance.region_id else instance.region.name if instance.region else None,
            'subregion_id': instance.subregion_id,
            'subregion_name': json.loads(subregion_data)['name'] if subregion_data and instance.subregion_id else instance.subregion.name if instance.subregion else None,
            'is_default': instance.is_default,
        }

    class Meta:
        model = Address
        fields = ('id', 'entity_mapping_id', 'address_type', 'street_address',
                 'city_id', 'city_name', 'postal_code', 'country_id',
                 'country_name', 'region_id', 'region_name', 'subregion_id',
                 'subregion_name', 'is_default')

class ContactSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        country_data = redis_conn.hget('countries', instance.country_id)
        return {
            'id': instance.id,
            'entity_mapping_id': instance.entity_mapping_id,
            'name': instance.name,
            'email': instance.email,
            'phone_number': instance.phone_number,
            'role': instance.role,
            'country_id': instance.country_id,
            'country_name': json.loads(country_data)['name'] if country_data else instance.country.name,
            'is_primary': instance.is_primary,
        }

    class Meta:
        model = Contact
        fields = ('id', 'entity_mapping_id', 'name', 'email', 'phone_number',
                 'role', 'country_id', 'country_name', 'is_primary')

class TaxProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        country_data = redis_conn.hget('countries', instance.country_id)
        region_data = redis_conn.hget('regions', instance.region_id) if instance.region_id else None
        return {
            'id': instance.id,
            'entity_mapping_id': instance.entity_mapping_id,
            'tax_identifier': instance.tax_identifier,
            'tax_identifier_type': instance.tax_identifier_type,
            'is_tax_exempt': instance.is_tax_exempt,
            'tax_exemption_reason': instance.tax_exemption_reason,
            'country_id': instance.country_id,
            'country_name': json.loads(country_data)['name'] if country_data else instance.country.name,
            'region_id': instance.region_id,
            'region_name': json.loads(region_data)['name'] if region_data and instance.region_id else instance.region.name if instance.region else None,
        }

    class Meta:
        model = TaxProfile
        fields = ('id', 'entity_mapping_id', 'tax_identifier', 'tax_identifier_type',
                 'is_tax_exempt', 'tax_exemption_reason', 'country_id',
                 'country_name', 'region_id', 'region_name')

class EntityMappingSerializer(serializers.ModelSerializer):
    entity_uuid_str = serializers.CharField()

    class Meta:
        model = FincoreEntityMapping
        fields = ('id', 'entity_type', 'entity_id', 'content_type', 'entity_uuid_str')

class InvoiceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        issuer_data = redis_conn.hget('entities', instance.issuer_id)
        recipient_data = redis_conn.hget('entities', instance.recipient_id)
        billing_address_data = redis_conn.hget('addresses', instance.billing_address_id)
        billing_country_data = redis_conn.hget('countries', instance.billing_country_id)
        billing_region_data = redis_conn.hget('regions', instance.billing_region_id) if instance.billing_region_id else None
        status_data = redis_conn.hget('statuses', instance.status_id)
        return {
            'id': instance.id,
            'invoice_number': instance.invoice_number,
            'description': instance.description,
            'issuer_id': instance.issuer_id,
            'issuer_name': json.loads(zlib.decompress(issuer_data).decode())['name'] if issuer_data else instance.issuer.name,
            'recipient_id': instance.recipient_id,
            'recipient_name': json.loads(zlib.decompress(recipient_data).decode())['name'] if recipient_data else instance.recipient.name,
            'billing_address_id': instance.billing_address_id,
            'billing_address': json.loads(billing_address_data)['street_address'] if billing_address_data else instance.billing_address.street_address,
            'billing_country_id': instance.billing_country_id,
            'billing_country_name': json.loads(billing_country_data)['name'] if billing_country_data else instance.billing_country.name,
            'billing_region_id': instance.billing_region_id,
            'billing_region_name': json.loads(billing_region_data)['name'] if billing_region_data else instance.billing_region.name if instance.billing_region else None,
            'issue_date': instance.issue_date,
            'due_date': instance.due_date,
            'status_id': instance.status_id,
            'status_name': json.loads(status_data)['name'] if status_data else instance.status.name,
            'payment_terms': instance.payment_terms,
            'currency': instance.currency,
            'base_amount': instance.base_amount,
            'total_amount': instance.total_amount,
            'tax_exemption_status': instance.tax_exemption_status,
            'payment_method': instance.payment_method,
            'payment_reference': instance.payment_reference,
            'issuer_gstin': instance.issuer_gstin,
            'recipient_gstin': instance.recipient_gstin,
            'cgst_rate': instance.cgst_rate,
            'sgst_rate': instance.sgst_rate,
            'igst_rate': instance.igst_rate,
            'cgst_amount': instance.cgst_amount,
            'sgst_amount': instance.sgst_amount,
            'igst_amount': instance.igst_amount,
        }

    class Meta:
        model = Invoice
        fields = ('id', 'invoice_number', 'description', 'issuer_id', 'issuer_name',
                 'recipient_id', 'recipient_name', 'billing_address_id', 'billing_address',
                 'billing_country_id', 'billing_country_name', 'billing_region_id',
                 'billing_region_name', 'issue_date', 'due_date', 'status_id',
                 'status_name', 'payment_terms', 'currency', 'base_amount',
                 'total_amount', 'tax_exemption_status', 'payment_method',
                 'payment_reference', 'issuer_gstin', 'recipient_gstin',
                 'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount',
                 'sgst_amount', 'igst_amount')

class LineItemSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        invoice_data = redis_conn.hget('invoices', instance.invoice_id)
        return {
            'id': instance.id,
            'invoice_id': instance.invoice_id,
            'invoice_number': json.loads(zlib.decompress(invoice_data).decode())['invoice_number'] if invoice_data else instance.invoice.invoice_number,
            'description': instance.description,
            'hsn_sac_code': instance.hsn_sac_code,
            'quantity': instance.quantity,
            'unit_price': instance.unit_price,
            'discount': instance.discount,
            'cgst_rate': instance.cgst_rate,
            'sgst_rate': instance.sgst_rate,
            'igst_rate': instance.igst_rate,
            'cgst_amount': instance.cgst_amount,
            'sgst_amount': instance.sgst_amount,
            'igst_amount': instance.igst_amount,
            'total_amount': instance.total_amount,
        }

    class Meta:
        model = LineItem
        fields = ('id', 'invoice_id', 'invoice_number', 'description',
                 'hsn_sac_code', 'quantity', 'unit_price', 'discount',
                 'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount',
                 'sgst_amount', 'igst_amount', 'total_amount')

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ('id', 'code', 'name', 'description', 'is_active')

class GSTConfigurationSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        region_data = redis_conn.hget('regions', instance.applicable_region_id) if instance.applicable_region_id else None
        return {
            'id': instance.id,
            'description': instance.description or '',
            'cgst_rate': str(instance.cgst_rate) if instance.cgst_rate is not None else None,
            'sgst_rate': str(instance.sgst_rate) if instance.sgst_rate is not None else None,
            'igst_rate': str(instance.igst_rate) if instance.igst_rate is not None else None,
            'rate_type': instance.rate_type or 'STANDARD',
            'applicable_region_id': instance.applicable_region_id,
            'applicable_region_name': (
                json.loads(region_data)['name'] if region_data
                else instance.applicable_region.name if instance.applicable_region
                else None
            ),
            'effective_from': instance.effective_from,
            'effective_to': instance.effective_to,
        }

    class Meta:
        model = GSTConfiguration
        fields = ('id', 'description', 'cgst_rate', 'sgst_rate',
                 'igst_rate', 'rate_type', 'applicable_region_id',
                 'applicable_region_name', 'effective_from', 'effective_to')

class BillingScheduleSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        entity_data = redis_conn.hget('entities', instance.entity_id)
        return {
            'id': instance.id,
            'entity_id': instance.entity_id,
            'entity_name': json.loads(zlib.decompress(entity_data).decode())['name'] if entity_data else instance.entity.name,
            'description': instance.description,
            'frequency': instance.frequency,
            'start_date': instance.start_date,
            'end_date': instance.end_date,
            'next_billing_date': instance.next_billing_date,
            'amount': instance.amount,
            'status': instance.status,
        }

    class Meta:
        model = BillingSchedule
        fields = ('id', 'entity_id', 'entity_name', 'description', 'frequency',
                 'start_date', 'end_date', 'next_billing_date', 'amount', 'status')

class PaymentSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        redis_conn = get_redis_connection('default')
        invoice_data = redis_conn.hget('invoices', instance.invoice_id)
        payment_method_data = redis_conn.hget('payment_methods', instance.payment_method_id)
        return {
            'id': instance.id,
            'invoice_id': instance.invoice_id,
            'invoice_number': json.loads(zlib.decompress(invoice_data).decode())['invoice_number'] if invoice_data else instance.invoice.invoice_number,
            'amount': instance.amount,
            'payment_date': instance.payment_date,
            'payment_method_id': instance.payment_method_id,
            'payment_method_code': json.loads(payment_method_data)['code'] if payment_method_data else instance.payment_method.code,
            'payment_reference': instance.payment_reference,
            'status': instance.status,
        }

    class Meta:
        model = Payment
        fields = ('id', 'invoice_id', 'invoice_number', 'amount',
                 'payment_date', 'payment_method_id', 'payment_method_code',
                 'payment_reference', 'status')

class StatusSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        return {
            'id': instance.id,
            'name': instance.name,
            'code': instance.code,
            'is_default': instance.is_default,
            'is_locked': instance.is_locked,
        }
    class Meta:
        model = Status
        fields = ('id', 'name', 'code', 'is_default', 'is_locked')

@shared_task
def cache_global_region_batch(page_num, batch_size=1000):
    """Cache a batch of global regions in Redis."""
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = GlobalRegion.objects.filter(deleted_at__isnull=True).only(
            'id', 'name', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = GlobalRegionSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    cache_key = f"global_region:{item['name'].lower()}"
                    pipe.hset('global_regions', cache_key, zlib.compress(json.dumps(item, cls=CustomJSONEncoder).encode()))
                pipe.set(f'global_regions_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} global regions in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} global regions cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching global regions in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_country_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = CustomCountry.objects.filter(deleted_at__isnull=True).only(
            'id', 'name', 'country_code', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = CountrySerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('countries', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'countries_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} countries in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} countries cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching countries in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_region_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = CustomRegion.objects.filter(deleted_at__isnull=True).select_related('country').only(
            'id', 'name', 'country_id', 'country__name', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = RegionSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('regions', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'regions_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} regions in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} regions cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching regions in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_subregion_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = CustomSubRegion.objects.filter(deleted_at__isnull=True).select_related('region').only(
            'id', 'name', 'region_id', 'region__name', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = SubRegionSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('subregions', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'subregions_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} subregions in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} subregions cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching subregions in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_city_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        logger.debug(f"Starting cache_city_batch for page {page_num} with batch_size {batch_size}")
        items = CustomCity.objects.filter(deleted_at__isnull=True).select_related('subregion').only(
            'id', 'name', 'subregion_id', 'subregion__name', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = CitySerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    compressed_data = zlib.compress(json.dumps(item, cls=CustomJSONEncoder).encode())
                    pipe.hset('cities', item['id'], compressed_data)
                pipe.set(f'cities_page_{page_num}', zlib.compress(json.dumps(chunk, cls=CustomJSONEncoder).encode()), ex=172800)
                pipe.execute()
                logger.debug(f"Cached chunk {i//chunk_size + 1} of {len(data)//chunk_size + 1} for cities page {page_num}")
        logger.info(f"Successfully cached {len(data)} cities in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} cities cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching cities in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_location_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Location.objects.filter(deleted_at__isnull=True).select_related('city').only(
            'id', 'city_id', 'city__name', 'postal_code', 'location_source'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = LocationSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('locations', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'locations_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} locations in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} locations cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching locations in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_industry_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Industry.objects.filter(deleted_at__isnull=True).only(
            'id', 'description'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = IndustrySerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('industries', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'industries_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} industries in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} industries cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching industries in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_entity_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Entity.objects.filter(deleted_at__isnull=True).select_related('industry').prefetch_related('default_address').only(
            'id', 'name', 'slug', 'entity_type', 'status', 'external_id',
            'website', 'registration_number', 'entity_size', 'notes',
            'industry_id', 'industry__description', 'default_address_id'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = EntitySerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('entities', item['id'], zlib.compress(json.dumps(item, cls=CustomJSONEncoder).encode()))
                pipe.set(f'entities_page_{page_num}', zlib.compress(json.dumps(chunk, cls=CustomJSONEncoder).encode()), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} entities in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} entities cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching entities in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_address_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Address.objects.filter(deleted_at__isnull=True).select_related('city', 'country').prefetch_related('region', 'subregion').only(
            'id', 'entity_mapping_id', 'address_type', 'street_address', 'postal_code', 'is_default',
            'city_id', 'city__name', 'country_id', 'country__name',
            'region_id', 'region__name', 'subregion_id', 'subregion__name'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = AddressSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('addresses', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'addresses_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} addresses in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} addresses cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching addresses in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_contact_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Contact.objects.filter(deleted_at__isnull=True).select_related('country').only(
            'id', 'entity_mapping_id', 'name', 'email', 'phone_number',
            'role', 'country_id', 'country__name', 'is_primary'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = ContactSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('contacts', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'contacts_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} contacts in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} contacts cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching contacts in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_tax_profile_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = TaxProfile.objects.filter(deleted_at__isnull=True).select_related('country').prefetch_related('region').only(
            'id', 'entity_mapping_id', 'tax_identifier', 'tax_identifier_type',
            'is_tax_exempt', 'tax_exemption_reason', 'country_id',
            'country__name', 'region_id', 'region__name'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = TaxProfileSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('tax_profiles', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'tax_profiles_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} tax profiles in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} tax profiles cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching tax profiles in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_entity_mapping_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = FincoreEntityMapping.objects.filter(deleted_at__isnull=True).annotate(
            entity_uuid_str=Cast('entity_uuid', output_field=CharField())
        ).only(
            'id', 'entity_type', 'entity_id', 'content_type', 'entity_uuid'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = EntityMappingSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('entity_mappings', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'entity_mappings_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} entity mappings in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} entity mappings cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching entity mappings in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_invoice_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Invoice.all_objects.filter(
            deleted_at__isnull=True, is_active=True
        ).select_related('issuer', 'recipient', 'billing_address', 'billing_country', 'billing_region', 'status').only(
            'id', 'invoice_number', 'description', 'issuer_id', 'issuer__name',
            'recipient_id', 'recipient__name', 'billing_address_id', 'billing_address__street_address',
            'billing_country_id', 'billing_country__name', 'billing_region_id', 'billing_region__name',
            'issue_date', 'due_date', 'status_id', 'status__name', 'payment_terms',
            'currency', 'base_amount', 'total_amount', 'tax_exemption_status',
            'issuer_gstin', 'recipient_gstin',
            'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount', 'sgst_amount', 'igst_amount'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = InvoiceSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('invoices', item['id'], zlib.compress(json.dumps(item, cls=CustomJSONEncoder).encode()))
                pipe.set(f'invoices_page_{page_num}', zlib.compress(json.dumps(chunk, cls=CustomJSONEncoder).encode()), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} invoices in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} invoices cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching invoices in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_line_item_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = LineItem.objects.filter(deleted_at__isnull=True).select_related('invoice').only(
            'id', 'invoice_id', 'invoice__invoice_number', 'description', 'hsn_sac_code',
            'quantity', 'unit_price', 'discount', 'cgst_rate', 'sgst_rate', 'igst_rate',
            'cgst_amount', 'sgst_amount', 'igst_amount', 'total_amount'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = LineItemSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('line_items', item['id'], zlib.compress(json.dumps(item, cls=CustomJSONEncoder).encode()))
                pipe.set(f'line_items_page_{page_num}', zlib.compress(json.dumps(chunk, cls=CustomJSONEncoder).encode()), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} line items in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} line items cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching line items in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_payment_method_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = PaymentMethod.objects.filter(deleted_at__isnull=True).only(
            'id', 'code', 'name', 'description', 'is_active'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = PaymentMethodSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('payment_methods', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'payment_methods_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} payment methods in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} payment methods cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching payment methods in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_gst_config_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = GSTConfiguration.objects.filter(deleted_at__isnull=True).select_related('applicable_region').only(
            'id', 'description', 'cgst_rate', 'sgst_rate', 'igst_rate',
            'rate_type', 'applicable_region_id', 'applicable_region__name',
            'effective_from', 'effective_to'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = GSTConfigurationSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('gst_configs', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'gst_configs_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} GST configurations in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} GST configurations cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching GST configurations in batch {page_num}: {str(e)}", exc_info=True)
        raise


@shared_task
def cache_billing_schedule_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = BillingSchedule.objects.filter(deleted_at__isnull=True).select_related('entity').only(
            'id', 'entity_id', 'entity__name', 'description', 'frequency',
            'start_date', 'end_date', 'next_billing_date', 'amount', 'status'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = BillingScheduleSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('billing_schedules', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'billing_schedules_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} billing schedules in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} billing schedules cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching billing schedules in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_payment_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Payment.objects.filter(deleted_at__isnull=True).select_related('invoice', 'payment_method').only(
            'id', 'invoice_id', 'invoice__invoice_number', 'amount',
            'payment_date', 'payment_method', 'payment_method__code',
            'payment_reference', 'status'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = PaymentSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('payments', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'payments_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} payments in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} payments cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching payments in batch {page_num}: {str(e)}", exc_info=True)
        raise

@shared_task
def cache_status_batch(page_num, batch_size=1000):
    try:
        start_time = time.time()
        redis_conn = get_redis_connection('default')
        items = Status.objects.filter(deleted_at__isnull=True).only(
            'id', 'name', 'code', 'is_default', 'is_locked'
        ).order_by('id')[(page_num - 1) * batch_size: page_num * batch_size]
        serializer = StatusSerializer(items, many=True)
        data = serializer.data

        with redis_conn.pipeline() as pipe:
            chunk_size = 500
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                for item in chunk:
                    pipe.hset('statuses', item['id'], json.dumps(item, cls=CustomJSONEncoder))
                pipe.set(f'statuses_page_{page_num}', json.dumps(chunk, cls=CustomJSONEncoder), ex=172800)
                pipe.execute()
        logger.info(f"Successfully cached {len(data)} statuses in batch {page_num} in {time.time() - start_time:.2f} seconds")
        return f"Batch {page_num}: {len(data)} statuses cached in {time.time() - start_time:.2f} seconds"
    except Exception as e:
        logger.error(f"Error caching statuses in batch {page_num}: {str(e)}", exc_info=True)
        raise
