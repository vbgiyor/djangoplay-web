import json
import logging
import random
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from entities.models.entity import Entity
from fincore.models.tax_profile import TaxProfile
from invoices.constants import BILLING_FREQUENCY_CHOICES, BILLING_STATUS_CODES, PAYMENT_TERMS_CHOICES
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
from invoices.models.gst_configuration import GSTConfiguration
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status
from invoices.services import (
    calculate_line_item_total,
    calculate_total_amount,
    entity_from_gstin,
    fetch_gst_config,
    generate_invoice_number,
    is_interstate_transaction,
    validate_billing_schedule,
    validate_gst_configuration,
    validate_gst_rates,
    validate_hsn_sac_code,
    validate_invoice,
    validate_line_item,
    validate_payment_amount,
    validate_payment_reference,
)
from locations.models.custom_country import CustomCountry
from utilities.utils.data_sync.load_env_and_paths import load_env_paths
from utilities.utils.entities.entity_validations import validate_gstin

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate invoice data for specified entity or all entities in a country to JSON in INVOICES_JSON/{COUNTRY_CODE} directory.
Expected .env keys: DATA_DIR, INVOICES_JSON
Example usage: ./manage.py generate_invoices --entity entity-slug
             or ./manage.py generate_invoices --all --country IN
             or ./manage.py generate_invoices --country IN
JSON files are generated in INVOICES_JSON/{COUNTRY_CODE}/{entity-slug}.json
"""

    def add_arguments(self, parser):
        parser.add_argument('--entity', type=str, help='Slug of the entity to generate invoices for')
        parser.add_argument('--all', action='store_true', help='Generate invoices for all entities in the specified country')
        parser.add_argument('--country', type=str, help='Country code (e.g., IN) to filter entities')
        parser.add_argument('--count', type=int, default=2, help='Number of invoices per status (default: 2)')
        parser.add_argument('--min', type=int, default=1, help='Minimum number of invoices per status if --count=2')
        parser.add_argument('--max', type=int, default=5, help='Maximum number of invoices per status if --count=2')

    def generate_gstin(self, region, entity):
        """Generate a valid GSTIN for the given region and ensure it matches entity's tax profile and address state."""
        if not region or not hasattr(region, 'code'):
            state_code = str(random.randint(1, 37)).zfill(2)
        else:
            state_code = entity.default_address.city.subregion.region.code.zfill(2) if entity.default_address and entity.default_address.city else str(random.randint(1, 37)).zfill(2)

        entity_region = entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
        if entity_region and entity_region.code != state_code:
            logger.warning(f"Region code {state_code} does not match entity {entity.slug} default address region {entity_region.code}")
            state_code = entity_region.code.zfill(2)

        entity_mapping = entity.get_entity_mapping()
        tax_profile = TaxProfile.objects.filter(
            entity_mapping_id=entity_mapping.id,
            tax_identifier_type='GSTIN',
            tax_identifier__startswith=state_code,
            is_active=True
        ).first()
        if tax_profile:
            try:
                validate_gstin(tax_profile.tax_identifier)
                entity_data = entity_from_gstin(tax_profile.tax_identifier)
                if entity_data['id'] == entity.id:
                    logger.info(f"Using existing GSTIN {tax_profile.tax_identifier} for entity {entity.slug}")
                    return tax_profile.tax_identifier
                logger.warning(f"Tax profile GSTIN {tax_profile.tax_identifier} already used by another entity")
            except ValidationError as e:
                logger.warning(f"Invalid GSTIN in tax profile for entity {entity.slug}: {tax_profile.tax_identifier}, error: {str(e)}")

        max_attempts = 50
        for attempt in range(max_attempts):
            if attempt == 25:
                logger.warning(f"Reached 50% of max_attempts ({max_attempts}) for GSTIN generation for entity {entity.slug}")
            pan = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5)) + ''.join(random.choices('0123456789', k=4)) + random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            entity_code = random.choice(['1', '2', '3', '4', '5', '6'])
            check_digit = random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            gstin = f"{state_code}{pan}{entity_code}Z{check_digit}"
            try:
                validate_gstin(gstin)
                entity_data = entity_from_gstin(gstin)
                if entity_data is None or entity_data['id'] is None:
                    logger.info(f"Generated unique GSTIN {gstin} for entity {entity.slug}")
                    return gstin
            except ValidationError:
                continue
        raise ValidationError(f"Could not generate unique GSTIN for entity {entity.slug} after {max_attempts} attempts")

    def generate_gst_configs(self, admin_user, billing_region, effective_from, effective_to, billing_country_id):
        """Generate or fetch GST configurations for the given region and dates."""
        gst_configs = {}
        rate_types = ['STANDARD', 'EXEMPT', 'ZERO_RATED']
        for rate_type in rate_types:
            try:
                logger.debug(f"Attempting GST config for {rate_type}, region: {billing_region.id if billing_region else 'Interstate'}")
                f"gst_config:{billing_region.id if billing_region else 'interstate'}:{effective_from.strftime('%Y%m%d')}:{rate_type}:{rate_type in ['EXEMPT', 'ZERO_RATED']}"
                existing_config_data = fetch_gst_config(
                    region_id=billing_region.id if billing_region else None,
                    issue_date=effective_from,
                    rate_type=rate_type,
                    exempt_zero_rated=rate_type in ['EXEMPT', 'ZERO_RATED']
                )
                # Ensure existing_config_data is a dictionary
                if not isinstance(existing_config_data, dict):
                    logger.error(f"fetch_gst_config returned non-dict: {existing_config_data}")
                    raise ValueError(f"fetch_gst_config returned invalid data: {existing_config_data}")

                existing_db_config = GSTConfiguration.objects.filter(
                    applicable_region=billing_region,
                    rate_type=rate_type,
                    cgst_rate=Decimal(existing_config_data['cgst_rate']),
                    sgst_rate=Decimal(existing_config_data['sgst_rate']),
                    igst_rate=Decimal(existing_config_data['igst_rate']),
                    effective_from__lte=effective_to,
                    effective_to__gte=effective_from,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()
                if existing_db_config:
                    logger.info(f"Found existing GST config: {existing_db_config.description} (ID: {existing_db_config.id})")
                    gst_configs[f"{rate_type}_{billing_region.id if billing_region else 'interstate'}_9.0"] = existing_db_config
                    continue
                if rate_type in ['EXEMPT', 'ZERO_RATED']:
                    description = f"{rate_type.title()} GST for {billing_region.name if billing_region else 'Interstate'}"
                    cgst_rate = Decimal('0.00')
                    sgst_rate = Decimal('0.00')
                    igst_rate = Decimal('0.00')
                else:
                    description = f"Standard GST for {billing_region.name if billing_region else 'Interstate'}"
                    if billing_region:
                        description += " at CGST 9.0% + SGST 9.0%"
                        cgst_rate = Decimal('9.00')
                        sgst_rate = Decimal('9.00')
                        igst_rate = Decimal('0.00')
                    else:
                        description += " at IGST 18.0%"
                        cgst_rate = Decimal('0.00')
                        sgst_rate = Decimal('0.00')
                        igst_rate = Decimal('18.00')
                config = GSTConfiguration(
                    description=description,
                    applicable_region=billing_region,
                    effective_from=effective_from,
                    effective_to=effective_to,
                    rate_type=rate_type,
                    cgst_rate=cgst_rate,
                    sgst_rate=sgst_rate,
                    igst_rate=igst_rate,
                    created_by=admin_user,
                    updated_by=admin_user,
                    is_active=True,
                    deleted_at=None
                )
                validate_gst_configuration(config)
                config.save(user=admin_user)
                logger.info(f"Saved GST config: {description} (ID: {config.id}, Region ID: {billing_region.id if billing_region else 'None'})")
                gst_configs[f"{rate_type}_{billing_region.id if billing_region else 'interstate'}_9.0"] = config
            except Exception as e:
                logger.error(f"Failed to create/fetch GST config for {rate_type}: {str(e)}", exc_info=True)
                raise
        logger.debug(f"Generated GST configs: {len(gst_configs)} configs")
        return gst_configs

    @transaction.atomic
    def generate_invoice(self, entity, status, counters, admin_user, recipient=None):
        logger.debug(f"Generating invoice for entity {entity.slug}, status {status.code}, recipient {recipient.slug if recipient else 'None'}")

        # Validate status
        if not isinstance(status, Status):
            logger.error(f"Invalid status object for entity {entity.slug}: {status}")
            raise ValidationError(f"Invalid status object: {status}")

        # Validate recipient
        if not recipient:
            logger.error(f"No valid recipient found for entity {entity.slug}")
            raise ValidationError(f"No valid recipient found for entity {entity.slug}")

        # Validate entity and recipient addresses
        if not entity.default_address or not entity.default_address.city or not entity.default_address.city.subregion.region:
            logger.error(f"Invalid address configuration for entity {entity.slug}")
            raise ValidationError(f"Entity {entity.slug} has invalid address configuration")
        if not recipient.default_address or not recipient.default_address.city or not recipient.default_address.city.subregion.region:
            logger.error(f"Invalid address configuration for recipient {recipient.slug}")
            raise ValidationError(f"Recipient {recipient.slug} has invalid address configuration")

        # Determine if transaction is in India
        is_india_transaction = recipient.default_address.city.subregion.region.country.country_code.upper() == 'IN'
        tax_exemption_status = random.choices(['NONE', 'EXEMPT', 'ZERO_RATED'], weights=[0.8, 0.1, 0.1], k=1)[0]
        issuer_gstin = None
        recipient_gstin = None
        cgst_rate = None
        sgst_rate = None
        igst_rate = None
        gst_config_id = None

        # Generate GST configurations
        effective_from = timezone.now().date()
        effective_to = effective_from + timedelta(days=365)
        billing_region = entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
        billing_country_id = entity.default_address.city.subregion.region.country.id if entity.default_address and entity.default_address.city else None

        if is_india_transaction:
            # Fetch GSTINs
            issuer_gstin = entity.get_tax_profiles().filter(tax_identifier_type='GSTIN').first()
            recipient_gstin = recipient.get_tax_profiles().filter(tax_identifier_type='GSTIN').first()
            issuer_gstin = issuer_gstin.tax_identifier if issuer_gstin else None
            recipient_gstin = recipient_gstin.tax_identifier if recipient_gstin else None

            # Generate GST configurations
            try:
                gst_configs = self.generate_gst_configs(
                    admin_user=admin_user,
                    billing_region=billing_region,
                    effective_from=effective_from,
                    effective_to=effective_to,
                    billing_country_id=billing_country_id
                )
            except Exception as e:
                logger.error(f"Failed to generate GST configs for entity {entity.slug}: {str(e)}")
                raise ValidationError(f"Failed to generate GST configs: {str(e)}")

            # Select appropriate GST configuration based on tax_exemption_status
            config_key = f"{tax_exemption_status if tax_exemption_status in ['EXEMPT', 'ZERO_RATED'] else 'STANDARD'}_{billing_region.id if billing_region else 'interstate'}_9.0"
            gst_config = gst_configs.get(config_key)
            if not gst_config:
                logger.error(f"No GST configuration found for key {config_key}")
                raise ValidationError(f"No GST configuration found for {tax_exemption_status}")

            gst_config_id = gst_config.id
            is_interstate = is_interstate_transaction(
                seller_gstin=issuer_gstin,
                buyer_gstin=recipient_gstin,
                billing_region_id=billing_region.id if billing_region else None,
                billing_country_id=billing_country_id,
                issuer=entity,
                recipient=recipient,
                issue_date=effective_from
            )

            # Assign GST rates based on configuration and transaction type
            if tax_exemption_status in ['EXEMPT', 'ZERO_RATED']:
                cgst_rate = Decimal('0.00')
                sgst_rate = Decimal('0.00')
                igst_rate = Decimal('0.00')
            else:
                if is_interstate:
                    cgst_rate = Decimal('0.00')
                    sgst_rate = Decimal('0.00')
                    igst_rate = Decimal(gst_config.igst_rate).quantize(Decimal('0.01'))
                else:
                    cgst_rate = Decimal(gst_config.cgst_rate).quantize(Decimal('0.01'))
                    sgst_rate = Decimal(gst_config.sgst_rate).quantize(Decimal('0.01'))
                    igst_rate = Decimal('0.00')

            # Validate GST rates
            try:
                validate_gst_rates(
                    cgst_rate=cgst_rate,
                    sgst_rate=sgst_rate,
                    igst_rate=igst_rate,
                    region_id=billing_region.id if billing_region else None,
                    country_id=billing_country_id,
                    issue_date=effective_from,
                    tax_exemption_status=tax_exemption_status
                )
            except GSTValidationError as e:
                logger.error(f"GST rate validation failed for entity {entity.slug}: {str(e)}")
                raise

        # Create invoice object (but don't save yet)
        invoice = Invoice(
            id=counters['invoice'],
            issuer=entity,
            recipient=recipient,
            billing_address=recipient.default_address,
            billing_country=recipient.default_address.city.subregion.region.country,
            billing_region=recipient.default_address.city.subregion.region,
            invoice_number=generate_invoice_number(),
            description=f"Invoice {counters['invoice']} for {entity.name}",
            issue_date=timezone.now().date() - timedelta(days=random.randint(0, 30)),
            due_date=timezone.now().date() + timedelta(days=random.randint(15, 45)),
            status=status,
            payment_terms=random.choice([pt[0] for pt in PAYMENT_TERMS_CHOICES]),
            currency='INR' if entity.default_address.city.subregion.region.country.country_code == 'IN' else 'USD',
            base_amount=Decimal('0.00'),
            total_amount=Decimal('0.00'),
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate,
            issuer_gstin=issuer_gstin,
            recipient_gstin=recipient_gstin,
            tax_exemption_status=tax_exemption_status,
            created_by=admin_user,
            updated_by=admin_user,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            is_active=True
        )

        # Validate invoice before proceeding
        try:
            validate_invoice(invoice)
        except (InvoiceValidationError, GSTValidationError) as e:
            logger.error(f"Failed to validate invoice {invoice.invoice_number} for {entity.slug}: {str(e)}")
            raise

        # Generate and save line items
        line_item_data = self.generate_line_item(invoice, counters, admin_user)
        if not line_item_data:
            logger.error(f"No line items generated for invoice {invoice.invoice_number}")
            raise ValidationError(f"No line items generated for invoice {invoice.invoice_number}")

        # Save invoice before calculating totals to ensure line items are committed
        try:
            invoice.save(user=admin_user)
            logger.debug(f"Saved invoice {invoice.invoice_number} for entity {entity.slug}")
        except (InvoiceValidationError, GSTValidationError) as e:
            logger.error(f"Failed to save invoice {invoice.invoice_number} for {entity.slug}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving invoice {invoice.invoice_number} for {entity.slug}: {str(e)}", exc_info=True)
            raise

        # Calculate invoice totals after line items and invoice are saved
        try:
            invoice.refresh_from_db()  # Ensure invoice reflects saved line items
            total_data = calculate_total_amount(invoice)
            logger.debug(f"Calculated total for invoice {invoice.invoice_number}: {total_data}")
            invoice.base_amount = total_data.get('base', Decimal('0.00'))
            invoice.total_amount = total_data['total']
            invoice.cgst_amount = total_data.get('cgst', Decimal('0.00'))
            invoice.sgst_amount = total_data.get('sgst', Decimal('0.00'))
            invoice.igst_amount = total_data.get('igst', Decimal('0.00'))
            # Save invoice again with updated totals
            invoice.save(user=admin_user)
        except Exception as e:
            logger.error(f"Failed to calculate total for invoice {invoice.invoice_number}: {str(e)}")
            raise ValidationError(f"Failed to calculate invoice total: {str(e)}")

        # Generate payments (if applicable)
        payment_data = []
        if status.code in ['PAID', 'PARTIALLY_PAID']:
            payment_methods = PaymentMethod.objects.filter(is_active=True)
            payment_method = random.choice(list(payment_methods)) if payment_methods.exists() else None
            invoice_number = invoice['invoice_number']
            last_14_digits = invoice_number[-14:]
            if not payment_method:
                logger.warning(f"No active payment method found for invoice {invoice.id}")
            elif total_data['total'] <= 0:
                logger.warning(f"Skipping payment generation for invoice {invoice.id} due to zero or negative total amount: {total_data['total']}")
            else:
                counters['payment'] += 1
                payment_amount = total_data['total'] if status.code == 'PAID' else total_data['total'] * Decimal(str(random.uniform(0.1, 0.9)))
                payment_amount = payment_amount.quantize(Decimal('0.01'))
                if payment_amount <= 0:
                    logger.warning(f"Skipping payment generation for invoice {invoice.id} due to non-positive payment amount: {payment_amount}")
                else:
                    # Generate UPI-compliant payment reference if payment method is UPI
                    if payment_method.code == 'UPI':
                        reference_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
                        payment_reference = f"UPI{reference_chars}{random.randint(1000, 9999)}"
                    else:
                        payment_reference = f"PAY-/{last_14_digits}"
                    payment_reference = payment_reference[:50]

                    payment = Payment(
                        id=counters['payment'],
                        invoice=invoice,
                        amount=payment_amount,
                        payment_date=timezone.now().date(),
                        payment_method=payment_method,
                        payment_reference=payment_reference,
                        status='COMPLETED',
                        created_by=admin_user,
                        updated_by=admin_user,
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                        is_active=True
                    )

                    try:
                        validate_payment_amount(payment_amount, invoice, payment.id)
                        validate_payment_reference(payment_reference, payment_method.code, invoice, payment.id)
                        payment.save(user=admin_user)
                        logger.debug(f"Saved Payment {payment.id} for invoice {invoice.id}")
                        payment_data.append({
                            'id': payment.id,
                            'invoice.invoice_number': invoice.invoice_number,
                            'amount': str(payment_amount),
                            'payment_date': str(payment.payment_date),
                            'payment_method_code': payment_method.code,
                            'payment_reference': payment_reference,
                            'status': payment.status,
                            'created_by_id': payment.created_by_id,
                            'updated_by_id': payment.updated_by_id,
                            'is_active': payment.is_active
                        })
                    except (InvoiceValidationError, GSTValidationError) as e:
                        logger.error(f"Failed to validate or save payment for invoice {invoice.id}: {str(e)}")
                        raise
                    except Exception as e:
                        logger.error(f"Failed to generate payment for invoice {invoice.id}: {str(e)}")
                        raise ValidationError(f"Failed to save payment: {str(e)}")

        billing_schedule_data = []
        if random.choice([True, False]):
            counters['billing_schedule'] += 1
            issue_date = invoice.issue_date if isinstance(invoice.issue_date, date) else invoice.issue_date.date()
            next_billing_date = issue_date + timedelta(days=random.randint(1, 30))
            start_date = issue_date
            status = random.choice(list(BILLING_STATUS_CODES.keys()))
            end_date = next_billing_date + timedelta(days=random.randint(1, 90)) if status == 'COMPLETED' else None
            billing_schedule = BillingSchedule(
                id=counters['billing_schedule'],
                entity=entity,
                description=f"Billing Schedule for Invoice {invoice.invoice_number}",
                start_date=start_date,
                next_billing_date=next_billing_date,
                end_date=end_date,
                amount=max(invoice.total_amount.quantize(Decimal('0.01')), Decimal('0.01')),
                frequency=random.choice([freq[0] for freq in BILLING_FREQUENCY_CHOICES]),
                status=status,
                created_by=admin_user,
                updated_by=admin_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                is_active=True
            )
            try:
                validate_billing_schedule(billing_schedule)
                billing_schedule.save(user=admin_user)
                billing_schedule_data.append({
                    'id': billing_schedule.id,
                    'entity_id': billing_schedule.entity_id,
                    'description': billing_schedule.description,
                    'start_date': billing_schedule.start_date.isoformat(),
                    'next_billing_date': billing_schedule.next_billing_date.isoformat(),
                    'end_date': billing_schedule.end_date.isoformat() if billing_schedule.end_date else None,
                    'amount': str(billing_schedule.amount),
                    'frequency': billing_schedule.frequency,
                    'status': billing_schedule.status,
                    'created_at': billing_schedule.created_at.isoformat(),
                    'updated_at': billing_schedule.updated_at.isoformat(),
                    'created_by_id': billing_schedule.created_by_id,
                    'updated_by_id': billing_schedule.updated_by_id,
                    'is_active': billing_schedule.is_active
                })
            except Exception as e:
                logger.error(f"Failed to generate billing schedule for invoice {invoice.invoice_number}: {str(e)}")
                raise

        invoice_data = {
            'id': invoice.id,
            'issuer_id': invoice.issuer_id,
            'recipient_id': invoice.recipient_id,
            'billing_address_id': invoice.billing_address_id,
            'billing_country_id': invoice.billing_country_id,
            'billing_region_id': invoice.billing_region_id if invoice.billing_region else None,
            'status_id': invoice.status_id,
            'invoice_number': invoice.invoice_number,
            'description': invoice.description,
            'issue_date': invoice.issue_date.isoformat(),
            'due_date': invoice.due_date.isoformat(),
            'payment_terms': invoice.payment_terms,
            'currency': invoice.currency,
            'has_gst_required_fields': invoice.has_gst_required_fields,
            'tax_exemption_status': invoice.tax_exemption_status,
            'issuer_gstin': invoice.issuer_gstin,
            'recipient_gstin': invoice.recipient_gstin,
            'cgst_rate': str(invoice.cgst_rate) if invoice.cgst_rate is not None else None,
            'sgst_rate': str(invoice.sgst_rate) if invoice.sgst_rate is not None else None,
            'igst_rate': str(invoice.igst_rate) if invoice.igst_rate is not None else None,
            'base_amount': str(invoice.base_amount),
            'cgst_amount': str(invoice.cgst_amount),
            'sgst_amount': str(invoice.sgst_amount),
            'igst_amount': str(invoice.igst_amount),
            'total_amount': str(invoice.total_amount),
            'created_at': invoice.created_at.isoformat(),
            'updated_at': invoice.updated_at.isoformat(),
            'created_by_id': invoice.created_by_id,
            'updated_by_id': invoice.updated_by_id,
            'is_active': invoice.is_active,
            'gst_config_id': gst_config_id  # Add GST configuration ID
        }
        return {
            'invoice': invoice_data,
            'line_item': line_item_data,
            'billing_schedule': billing_schedule_data,
            'payment': payment_data,
            'gst_config': {
                'id': gst_config.id,
                'description': gst_config.description,
                'rate_type': gst_config.rate_type,
                'cgst_rate': str(gst_config.cgst_rate),
                'sgst_rate': str(gst_config.sgst_rate),
                'igst_rate': str(gst_config.igst_rate),
                'applicable_region_id': gst_config.applicable_region_id,
                'effective_from': gst_config.effective_from.isoformat(),
                'effective_to': gst_config.effective_to.isoformat() if gst_config.effective_to else None,
                'is_active': gst_config.is_active
            } if is_india_transaction and gst_config else None
        }

    def generate_line_item(self, invoice, counters, admin_user):
        line_item_data = []
        num_line_items = random.randint(1, 5)
        used_hsn_sac_codes = set()

        for _i in range(num_line_items):
            counters['line_item'] += 1
            description = f"Service/Product {counters['line_item']}-{random.randint(1000, 9999)}"
            max_attempts = 50
            hsn_sac_code = None
            for attempt in range(max_attempts):
                code_type = random.choice(['HSN', 'SAC'])
                num_digits = 4  # Use 4 digits to ensure total length (3 + 1 + 4) <= 8
                code_number = ''.join(random.choices('0123456789', k=num_digits))
                hsn_sac_code = f"{code_type} {code_number}"  # e.g., 'HSN 1234' or 'SAC 5678'
                if hsn_sac_code not in used_hsn_sac_codes:
                    try:
                        validate_hsn_sac_code(hsn_sac_code)  # Uses HSN_SAC_CODE_REGEX
                        used_hsn_sac_codes.add(hsn_sac_code)
                        logger.debug(f"Generated valid HSN/SAC code: {hsn_sac_code}")
                        break
                    except GSTValidationError as e:
                        logger.debug(f"HSN/SAC code {hsn_sac_code} failed validation: {str(e)}")
                        continue
                if attempt == max_attempts - 1:
                    logger.error(f"Could not generate valid HSN/SAC code after {max_attempts} attempts for invoice {invoice.invoice_number}")
                    raise ValidationError(f"Could not generate valid HSN/SAC code after {max_attempts} attempts")

            quantity = random.randint(1, 10)
            unit_price = Decimal(str(round(random.uniform(10, 100), 2)))
            discount = Decimal(str(round(random.uniform(0, 10), 2)))
            cgst_rate = invoice.cgst_rate
            sgst_rate = invoice.sgst_rate
            igst_rate = invoice.igst_rate

            try:
                validate_hsn_sac_code(hsn_sac_code)
            except ValidationError as e:
                logger.error(f"Invalid HSN/SAC code {hsn_sac_code} for line item {counters['line_item']}: {str(e)}")
                raise

            line_item = LineItem(
                id=counters['line_item'],
                invoice=invoice,
                description=description,
                hsn_sac_code=hsn_sac_code,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                created_by=admin_user,
                updated_by=admin_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                is_active=True
            )

            try:
                logger.debug(f"Validating line item {line_item.id} for invoice {invoice.id}")
                validate_line_item(line_item)
                total_data = calculate_line_item_total(line_item)
                logger.debug(f"LineItem total for invoice {invoice.id}: {total_data}")
                line_item.cgst_amount = total_data['cgst_amount']
                line_item.sgst_amount = total_data['sgst_amount']
                line_item.igst_amount = total_data['igst_amount']
                line_item.total_amount = total_data['total']
                line_item.save()
                logger.debug(f"Saved LineItem {line_item.id} for invoice {invoice.id}")
                if line_item.invoice != invoice:
                    logger.error(f"LineItem {line_item.id} saved but not associated with invoice {invoice.id}")
                    raise ValidationError(f"LineItem {line_item.id} not associated with invoice {invoice.id}")
                line_item_data.append({
                    'id': line_item.id,
                    'invoice.invoice_number': invoice.invoice_number,
                    'description': line_item.description,
                    'hsn_sac_code': line_item.hsn_sac_code,
                    'cgst_amount': str(line_item.cgst_amount),
                    'sgst_amount': str(line_item.sgst_amount),
                    'igst_amount': str(line_item.igst_amount),
                    'total_amount': str(line_item.total_amount),
                    'created_by_id': line_item.created_by_id,
                    'updated_by_id': line_item.updated_by_id,
                    'is_active': line_item.is_active,
                    'quantity': str(quantity),
                    'unit_price': str(unit_price),
                    'discount': str(discount),
                    'cgst_rate': str(cgst_rate) if cgst_rate is not None else None,
                    'sgst_rate': str(sgst_rate) if sgst_rate is not None else None,
                    'igst_rate': str(igst_rate) if igst_rate is not None else None,
                })
            except (InvoiceValidationError, GSTValidationError) as e:
                logger.error(f"Failed to validate or save line item {counters['line_item']} for invoice {invoice.id}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in generating line item {counters['line_item']} for invoice {invoice.id}: {str(e)}", exc_info=True)
                raise ValidationError(f"Unexpected error generating line item: {str(e)}")

        if not line_item_data:
            logger.error(f"No line items generated for invoice {invoice.id}")
            raise ValidationError(f"No line items generated for invoice {invoice.id}")

        logger.debug(f"Generated {len(line_item_data)} line items for invoice {invoice.id}")
        return line_item_data

    def handle(self, *args, **options):
        start_time = time.time()
        User = get_user_model()
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username}"))
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR("User with id=1 not found"))
            logger.error("User with id=1 not found")
            return

        stats = {'created': 0, 'skipped': [], 'total': 0}
        counters = {
            'invoice': Invoice.objects.aggregate(Max('id'))['id__max'] or 0,
            'line_item': LineItem.objects.aggregate(Max('id'))['id__max'] or 0,
            'billing_schedule': BillingSchedule.objects.aggregate(Max('id'))['id__max'] or 0,
            'payment': Payment.objects.aggregate(Max('id'))['id__max'] or 0
        }

        env_data = load_env_paths(env_var='INVOICES_JSON', require_exists=False)
        invoices_path = env_data.get('INVOICES_JSON')
        if not invoices_path:
            self.stderr.write(self.style.ERROR("INVOICES_JSON not defined in .env"))
            logger.error("INVOICES_JSON not defined")
            return

        country_code = options.get('country')
        if country_code:
            try:
                CustomCountry.objects.get(country_code=country_code.upper())
            except ObjectDoesNotExist:
                self.stderr.write(self.style.ERROR(f"Country with code {country_code} not found"))
                logger.error(f"Country with code {country_code} not found")
                return

        entities = Entity.objects.filter(is_active=True)
        if country_code:
            entities = entities.filter(default_address__city__subregion__region__country__country_code=country_code.upper())

        if options['all']:
            pass
        else:
            entity_slug = options.get('entity')
            if not entity_slug:
                self.stderr.write(self.style.ERROR("Must provide --entity or --all"))
                logger.error("Must provide --entity or --all")
                return
            try:
                entity = Entity.objects.get(slug=entity_slug, is_active=True)
                if country_code and entity.default_address.city.subregion.region.country.country_code != country_code.upper():
                    self.stderr.write(self.style.ERROR(f"Entity {entity_slug} does not belong to country {country_code}"))
                    logger.error(f"Entity {entity_slug} does not belong to country {country_code}")
                    return
                entities = [entity]
            except ObjectDoesNotExist:
                self.stderr.write(self.style.ERROR(f"Entity with slug {entity_slug} not found"))
                logger.error(f"Entity with slug {entity_slug} not found")
                return

        if not entities:
            self.stderr.write(self.style.ERROR("No active entities found" + (f" for country {country_code}" if country_code else "")))
            logger.error("No active entities found" + (f" for country {country_code}" if country_code else ""))
            return

        all_statuses = Status.objects.filter(is_active=True)
        if not all_statuses.exists():
            self.stderr.write(self.style.ERROR("No active statuses found"))
            logger.error("No active statuses found")
            return

        num_invoices_per_status = options['count'] if options['count'] != 1 else random.randint(options['min'], options['max'])
        max_duration = 300
        json_data = {
            'invoice': [],
            'line_item': [],
            'billing_schedule': [],
            'payment': [],
            'gst_config': []  # Add gst_config to JSON output
        }

        for entity in entities:
            entity_slug = entity.slug
            entity_country_code = entity.default_address.city.subregion.region.country.country_code if entity.default_address and entity.default_address.city else 'UNKNOWN'
            invoices_json = str(Path(invoices_path) / entity_country_code / f"{entity_slug}.json")
            self.stdout.write(f"Generating invoices for entity: {entity.name} ({entity_slug}) in {entity_country_code}")
            logger.info(f"Generating {num_invoices_per_status} invoice(s) per status for entity {entity.name} in {entity_country_code}")

            same_country_entities = Entity.objects.filter(
                default_address__city__subregion__region__country__country_code=entity_country_code,
                is_active=True
            ).exclude(id=entity.id)
            recipient = random.choice(list(same_country_entities)) if same_country_entities.exists() else None
            logger.debug(f"Selected recipient: {recipient.slug if recipient else 'None'} for entity {entity_slug}")

            for status in all_statuses:
                logger.debug(f"Processing status {status.code} for entity {entity_slug}")
                for _ in range(num_invoices_per_status):
                    if time.time() - start_time > max_duration:
                        self.stderr.write(self.style.ERROR(f"Generation timed out after {max_duration} seconds"))
                        logger.error(f"Generation timed out after {max_duration} seconds")
                        return
                    stats['total'] += 1
                    counters['invoice'] += 1
                    try:
                        invoice_data = self.generate_invoice(
                            entity, status, counters, admin_user, recipient=recipient
                        )
                        json_data['invoice'].append(invoice_data['invoice'])
                        json_data['line_item'].extend(invoice_data['line_item'])
                        json_data['billing_schedule'].extend(invoice_data['billing_schedule'])
                        json_data['payment'].extend(invoice_data['payment'])
                        if invoice_data['gst_config']:
                            json_data['gst_config'].append(invoice_data['gst_config'])
                        stats['created'] += 1
                        logger.info(f"Successfully generated invoice {invoice_data['invoice']['invoice_number']} for entity {entity_slug}")
                    except Exception as e:
                        error_details = {'invoice': f"Invoice {counters['invoice']}", 'reason': str(e), 'entity': entity_slug}
                        stats['skipped'].append(error_details)
                        logger.error(f"Skipping invoice generation {counters['invoice']} for {entity_slug}: {str(e)}", extra={'details': error_details})

            try:
                Path(invoices_json).parent.mkdir(parents=True, exist_ok=True)
                with open(invoices_json, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                self.stdout.write(self.style.SUCCESS(f"Generated JSON at {invoices_json}"))
                logger.info(f"Generated JSON at {invoices_json}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}"))
                logger.error(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}")

        self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f" - Total invoices: {stats['total']}")
        self.stdout.write(f" - Created: {stats['created']}")
        self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f" - {skipped['invoice']}: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Generation Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
