import builtins
import json
import logging
import random
import time
from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from entities.models.entity import Entity
from fincore.models.tax_profile import TaxProfile
from industries.models import Industry
from invoices.constants import (
    BILLING_FREQUENCY_CHOICES,
    BILLING_STATUS_CODES,
    DESCRIPTION_MAX_LENGTH,
    GST_RATE_TYPE_CHOICES,
    PAYMENT_TERMS_CHOICES,
)
from invoices.exceptions import GSTValidationError, InvoiceValidationError
from invoices.models.billing_schedule import BillingSchedule
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

logger = logging.getLogger('data_sync')

class Command(BaseCommand):
    help = """Generate and imports invoice data for specified entity or all entities in a country to JSON in INVOICES_JSON/{COUNTRY_CODE} directory or directly to database.
Expected .env keys: DATA_DIR, INVOICES_JSON
Example usage: ./manage.py generate_import_invoices --entity entity-slug
             or ./manage.py generate_import_invoices --all --country IN
             or ./manage.py generate_import_invoices --country IN
JSON files are generated in INVOICES_JSON/{COUNTRY_CODE}/{entity-slug}.json unless --skipjson is provided
"""

    def add_arguments(self, parser):
        parser.add_argument('--entity', type=str, help='Slug of the entity to generate invoices for')
        parser.add_argument('--all', action='store_true', help='Generate invoices for all entities in the specified country')
        parser.add_argument('--country', type=str, help='Country code (e.g., IN) to filter entities')
        parser.add_argument('--maxcount', type=int, default=5, help='Maximum number of invoices per status (default: 5)')
        parser.add_argument('--mincount', type=int, default=1, help='Minimum number of invoices per status if --maxcount=2')
        parser.add_argument('--schedules', type=int, default=2, help='Number of billing schedules per invoice')
        parser.add_argument('--skipjson', action='store_true', help='Skip generating JSON and directly save to database')
        parser.add_argument('--scriptduration', type=int, default=172800, help='Maximum script duration in seconds (default: 172800)')
        parser.add_argument('--fixed', action='store_true', help='Generate exactly one invoice per active status with default settings')

    def fetch_line_items_json(self):
        """Load invoice_line_items.json and return the data."""
        env_data = load_env_paths(env_var='LINE_ITEM_JSON', require_exists=False)
        line_item_json_path = env_data.get('LINE_ITEM_JSON')
        if not line_item_json_path:
            logger.error("LINE_ITEM_JSON not defined in .env")
            raise ValidationError("LINE_ITEM_JSON not defined in .env")
        file_path = str(Path(line_item_json_path))
        try:
            with open(file_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading invoice_line_items.json from {file_path}: {str(e)}")
            raise ValidationError(f"Error reading invoice_line_items.json: {str(e)}")

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
                if entity_data and entity_data['id'] == entity.id:
                    logger.info(f"Using existing GSTIN {tax_profile.tax_identifier} for entity {entity.slug}")
                    return tax_profile.tax_identifier
                logger.warning(f"Tax profile GSTIN {tax_profile.tax_identifier} already used by another entity or no entity found")
            except (ValidationError, GSTValidationError) as e:
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
            except (ValidationError, GSTValidationError):
                continue
        raise ValidationError(f"Could not generate unique GSTIN for entity {entity.slug} after {max_attempts} attempts")

    def generate_payment(self, invoice, status, counters, admin_user, total_data):
        """Generate payment data for the given invoice with at least 3 payments for PAID, PARTIALLY_PAID, and CANCELLED statuses."""
        payment_data = []
        logger.debug(f"Attempting payments for invoice {invoice.id}, status {status.code}, total {total_data['total']}")

        if status.code not in ['PAID', 'PARTIALLY_PAID', 'CANCELLED']:
            logger.debug(f"Skipping payment for invoice {invoice.id}: Status {status.code} not PAID, PARTIALLY_PAID, or CANCELLED")
            return payment_data

        if total_data['total'] <= 0:
            logger.warning(f"Skipping payment for invoice {invoice.id}: Non-positive total {total_data['total']}")
            return payment_data

        payment_methods = PaymentMethod.objects.filter(is_active=True)
        if not payment_methods.exists():
            logger.error(f"No active payment methods for invoice {invoice.id}")
            raise ValidationError(f"No active payment methods found for invoice {invoice.id}")

        invoice_number = invoice.invoice_number
        last_14_digits = invoice_number[-14:] if len(invoice_number) >= 14 else invoice_number
        num_payments = 3  # Generate exactly 3 payments

        total_payment_amount = Decimal(str(total_data['total'])).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        if status.code != 'PAID':
            total_payment_amount = (total_payment_amount * Decimal(str(random.uniform(0.3, 0.9)))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        if status.code == 'PAID':
            base_amount = (total_payment_amount / 3).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            payment_amounts = [base_amount] * 3
            total_payment_sum = sum(payment_amounts)
            if total_payment_sum != total_payment_amount:
                payment_amounts[-1] = (total_payment_amount - 2 * base_amount).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        else:
            weights = [random.uniform(0.2, 0.5) for _ in range(2)]
            weights.append(1 - sum(weights))
            payment_amounts = []
            remaining_amount = total_payment_amount
            for i, w in enumerate(weights[:2]):
                amount = (total_payment_amount * Decimal(str(w))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                payment_amounts.append(amount)
                remaining_amount -= amount
            payment_amounts.append(remaining_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN))

        for i in range(num_payments):
            counters['payment'] += 1
            payment_method = random.choice(list(payment_methods))
            payment_amount = payment_amounts[i]

            if payment_amount <= 0:
                logger.warning(f"Skipping payment {counters['payment']} for invoice {invoice.id}: Non-positive amount {payment_amount}")
                continue

            if payment_method.code == 'UPI':
                reference_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
                payment_reference = f"UPI{reference_chars}{random.randint(1000, 9999)}"
            else:
                payment_reference = f"PAY-/{last_14_digits}/{random.randint(1000, 9999)}"
            payment_reference = payment_reference[:50]

            payment = Payment(
                id=counters['payment'],
                invoice=invoice,
                payment_method=payment_method,
                amount=payment_amount,
                payment_reference=payment_reference,
                payment_date=invoice.issue_date + timedelta(days=random.randint(0, 30)),
                status='PENDING' if status.code != 'CANCELLED' else 'FAILED',
                created_by=admin_user,
                updated_by=admin_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                is_active=status.code != 'CANCELLED'
            )

            try:
                validate_payment_amount(payment_amount, invoice, payment.id)
                validate_payment_reference(payment_reference, payment_method.code, invoice, payment.id)
                payment.save()
                payment_data.append({
                    'id': payment.id,
                    'invoice_id': invoice.id,
                    'payment_method_id': payment_method.id,
                    'amount': str(payment.amount),
                    'payment_reference': payment.payment_reference,
                    'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
                    'created_by_id': payment.created_by_id,
                    'updated_by_id': payment.updated_by_id,
                    'is_active': payment.is_active
                })
                logger.debug(f"Generated payment {payment.id} for invoice {invoice.id}")
            except (InvoiceValidationError, GSTValidationError) as e:
                logger.error(f"Failed to validate or save payment {counters['payment']} for invoice {invoice.id}: {str(e)}")
                raise

        return payment_data

    def generate_billing_schedule(self, invoice, entity, counters, admin_user, num_schedules=1):
        """Generate billing schedule data for the given invoice, inactive for CANCELLED status."""
        billing_schedule_data = []
        if invoice.status.code == 'DRAFT':
            logger.debug(f"Skipping billing schedule generation for invoice {invoice.invoice_number} with status {invoice.status.code}")
            return billing_schedule_data

        for _ in range(num_schedules):
            counters['billing_schedule'] += 1
            issue_date = invoice.issue_date if isinstance(invoice.issue_date, date) else invoice.issue_date.date()
            next_billing_date = issue_date + timedelta(days=random.randint(1, 30))
            start_date = issue_date
            status = random.choice(list(BILLING_STATUS_CODES.keys()))
            end_date = next_billing_date + timedelta(days=random.randint(1, 90)) if status == 'COMPLETED' else None
            amount = max(invoice.total_amount.quantize(Decimal('0.01')), Decimal('0.01'))

            billing_schedule = BillingSchedule(
                id=counters['billing_schedule'],
                entity=entity,
                description=f"Billing Schedule {counters['billing_schedule']} for Invoice {invoice.invoice_number}",
                start_date=start_date,
                next_billing_date=next_billing_date,
                end_date=end_date,
                amount=amount,
                frequency=random.choice([freq[0] for freq in BILLING_FREQUENCY_CHOICES]),
                status=status,
                created_by=admin_user,
                updated_by=admin_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                is_active=invoice.status.code != 'CANCELLED'
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
                logger.error(f"Failed to save billing schedule {counters['billing_schedule']} for invoice {invoice.invoice_number}: {str(e)}")
                raise
        return billing_schedule_data

    def generate_line_item(self, invoice, counters, admin_user, max_line_items=5, line_item_json=None):
        """Generate line items for the invoice using invoice_line_items.json."""
        line_item_data = []
        used_hsn_sac_codes = set()

        if not line_item_json or not line_item_json.get('isic'):
            logger.error(f"Invalid JSON for invoice {invoice.invoice_number}: JSON is missing or lacks 'isic' key")
            raise ValidationError("Invalid or missing JSON")

        try:
            industry = Industry.objects.filter(entities=invoice.issuer, is_active=True).first()
            industry_code = industry.code if industry else None
            logger.debug(f"Industry code for entity {invoice.issuer.slug}: {industry_code}")
        except AttributeError as e:
            logger.error(f"Invalid issuer for invoice {invoice.invoice_number}: {str(e)}")
            raise ValidationError(f"Invalid issuer: {str(e)}")

        line_item_choices = []
        if industry_code:
            logger.debug(f"Searching for line items for industry code: {industry_code}")
            for section in line_item_json['isic']:
                section_code = section.get("Section", "Unknown")
                for division in section.get("Divisions", []):
                    division_code = division.get("Division", "Unknown")
                    for group in division.get("Groups", []):
                        group_code = group.get("Group", "Unknown")
                        for class_data in group.get("Classes", []):
                            class_code = class_data.get("Class")
                            if class_code == industry_code:
                                line_items = class_data.get("line_items", {})
                                if line_items:
                                    line_item_choices = list(line_items.values())
                                    logger.debug(f"Found {len(line_item_choices)} line items for industry {industry_code} in section {section_code}, division {division_code}, group {group_code}, class {class_code}")
                                else:
                                    logger.warning(f"No line items found in JSON for industry {industry_code} in class {class_code}")
                                break
                            if line_item_choices:
                                break
                        if line_item_choices:
                            break
                    if line_item_choices:
                        break

        if not line_item_choices and line_item_json.get('isic'):
            logger.warning(f"No line items found for industry {industry_code or 'None'} in invoice {invoice.invoice_number}. Attempting generic JSON fallback.")
            for section in line_item_json['isic']:
                for division in section.get("Divisions", []):
                    for group in division.get("Groups", []):
                        for class_data in group.get("Classes", []):
                            line_items = class_data.get("line_items", {})
                            if line_items:
                                line_item_choices.extend(list(line_items.values()))
            logger.debug(f"Generic JSON fallback found {len(line_item_choices)} line items: {line_item_choices[:5]}...")

        if not line_item_choices:
            logger.warning(f"No line items found in JSON for invoice {invoice.invoice_number}. Using default fallback values.")
            logger.debug(f"Available class codes in JSON: {[c['Class'] for s in line_item_json['isic'] for d in s.get('Divisions', []) for g in d.get('Groups', []) for c in g.get('Classes', [])]}")
            line_item_choices = ["General service item", "Consulting service", "Product delivery", "Maintenance service", "Support service"]

        for description in random.sample(line_item_choices, min(max_line_items, len(line_item_choices))):
            counters['line_item'] += 1
            description = description[:DESCRIPTION_MAX_LENGTH]

            for _ in range(50):
                code_type = random.choice(['HSN', 'SAC'])
                code_number = ''.join(random.choices('0123456789', k=4))
                hsn_sac_code = f"{code_type} {code_number}"
                if hsn_sac_code not in used_hsn_sac_codes:
                    try:
                        validate_hsn_sac_code(hsn_sac_code)
                        used_hsn_sac_codes.add(hsn_sac_code)
                        break
                    except GSTValidationError:
                        continue
                else:
                    logger.warning(f"HSN/SAC code {hsn_sac_code} already used for invoice {invoice.invoice_number}")
            else:
                logger.error(f"Failed to generate unique HSN/SAC code for invoice {invoice.invoice_number} after 50 attempts")
                raise ValidationError("Could not generate unique HSN/SAC code")

            line_item = LineItem(
                id=counters['line_item'],
                invoice=invoice,
                description=description,
                hsn_sac_code=hsn_sac_code,
                quantity=random.randint(1, 10),
                unit_price=Decimal(str(round(random.uniform(10, 100), 2))),
                discount=Decimal(str(round(random.uniform(0, 10), 2))),
                cgst_rate=invoice.cgst_rate,
                sgst_rate=invoice.sgst_rate,
                igst_rate=invoice.igst_rate,
                created_by=admin_user,
                updated_by=admin_user,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                is_active=True
            )

            try:
                validate_line_item(line_item)
                total_data = calculate_line_item_total(line_item)
                line_item.cgst_amount = total_data['cgst_amount']
                line_item.sgst_amount = total_data['sgst_amount']
                line_item.igst_amount = total_data['igst_amount']
                line_item.total_amount = total_data['total']
                line_item.save()
                line_item_data.append({
                    'id': line_item.id,
                    'invoice.invoice_number': invoice.invoice_number,
                    'description': description,
                    'hsn_sac_code': hsn_sac_code,
                    'cgst_amount': str(line_item.cgst_amount),
                    'sgst_amount': str(line_item.sgst_amount),
                    'igst_amount': str(line_item.igst_amount),
                    'total_amount': str(line_item.total_amount),
                    'created_by_id': line_item.created_by_id,
                    'updated_by_id': line_item.updated_by_id,
                    'is_active': line_item.is_active,
                    'quantity': str(line_item.quantity),
                    'unit_price': str(line_item.unit_price),
                    'discount': str(line_item.discount),
                    'cgst_rate': str(line_item.cgst_rate) if line_item.cgst_rate is not None else None,
                    'sgst_rate': str(line_item.sgst_rate) if line_item.sgst_rate is not None else None,
                    'igst_rate': str(line_item.igst_rate) if line_item.igst_rate is not None else None,
                })
                logger.debug(f"Generated line item {line_item.id} for invoice {invoice.invoice_number}: {description}")
            except Exception as e:
                logger.error(f"Failed to save line item {counters['line_item']} for invoice {invoice.invoice_number}: {str(e)}")
                raise

        if not line_item_data:
            logger.error(f"No line items generated for invoice {invoice.invoice_number}")
            raise ValidationError("No line items generated")

        return line_item_data

    def generate_invoice(self, entity, status, counters, admin_user, line_item_json, recipient=None, num_schedules=1):
        logger.debug(f"Generating invoice for entity {entity.slug}, status {status.code}, recipient {recipient.slug if recipient else 'None'}")
        if 'id' in locals() or 'id' in globals():
            logger.error(f"Variable 'id' is defined in scope: {locals().get('id', globals().get('id'))}")

        # Validate entity and recipient as Entity instances
        if not isinstance(entity, Entity):
            logger.error(f"Invalid issuer entity for invoice generation: {entity} is not an Entity instance")
            raise ValidationError("Invalid issuer entity: Must be an Entity instance")
        if recipient and not isinstance(recipient, Entity):
            logger.error(f"Invalid recipient entity for invoice generation: {recipient} is not an Entity instance")
            raise ValidationError("Invalid recipient entity: Must be an Entity instance")

        # Validate status
        if not isinstance(status, Status):
            logger.error(f"Invalid status object for entity {entity.slug}: {status}")
            raise ValidationError(f"Invalid status object: {status}")

        # Validate entity and recipient activity
        if not entity.is_active:
            logger.error(f"Entity {entity.slug} is not active")
            raise ValidationError(f"Entity {entity.slug} is not active")
        if recipient and not recipient.is_active:
            logger.error(f"Recipient {recipient.slug} is not active")
            raise ValidationError(f"Recipient {recipient.slug} is not active")

        # Validate entity and recipient addresses
        if not entity.default_address or not entity.default_address.city or not entity.default_address.city.subregion.region:
            logger.error(f"Invalid address configuration for entity {entity.slug}")
            raise ValidationError(f"Entity {entity.slug} has invalid address configuration")
        if recipient and (not recipient.default_address or not recipient.default_address.city or not recipient.default_address.city.subregion.region):
            logger.error(f"Invalid address configuration for recipient {recipient.slug}")
            raise ValidationError(f"Recipient {recipient.slug} has invalid address configuration")

        # Determine if transaction is in India
        effective_from = timezone.now().date() - timedelta(days=random.randint(0, 365))
        effective_to = effective_from + timedelta(days=random.randint(0, 365))
        billing_region = entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
        billing_country = entity.default_address.city.subregion.region.country if billing_region else None
        is_india_transaction = (
            recipient.default_address.city.subregion.region.country.country_code.upper() == 'IN'
            if recipient and recipient.default_address and recipient.default_address.city
            else False
        )
        tax_exemption_status = random.choices(['NONE', 'EXEMPT', 'ZERO_RATED'], weights=[0.8, 0.1, 0.1], k=1)[0] if is_india_transaction else 'NONE'

        # Generate GSTINs
        issuer_gstin = self.generate_gstin(billing_region, entity) if is_india_transaction else None
        recipient_gstin = self.generate_gstin(billing_region, recipient) if is_india_transaction and recipient else None

        # Validate and select billing address
        if recipient:
            recipient_mapping = recipient.get_entity_mapping()
            if not recipient.default_address or recipient.default_address.entity_mapping != recipient_mapping:
                logger.warning(f"Default billing address {recipient.default_address} does not match recipient {recipient.slug} entity mapping")
                # Fallback to a valid address for the recipient
                billing_address = recipient.addresses.filter(
                    entity_mapping=recipient_mapping,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()
                if not billing_address:
                    logger.error(f"No valid billing address found for recipient {recipient.slug}")
                    raise InvoiceValidationError(
                        message="No valid billing address found for recipient entity.",
                        code="invalid_billing_address",
                        details={"entity_id": recipient.id}
                    )
            else:
                billing_address = recipient.default_address
        else:
            billing_address = entity.default_address

        # Set billing country and region based on billing address
        billing_country = (
            billing_address.city.subregion.region.country
            if billing_address and billing_address.city and billing_address.city.subregion
            else entity.default_address.city.subregion.region.country if entity.default_address and entity.default_address.city else None
        )
        billing_region = (
            billing_address.city.subregion.region
            if billing_address and billing_address.city and billing_address.city.subregion
            else entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
        )

        # Fetch GST configuration
        rate_type = random.choice([choice[0] for choice in GST_RATE_TYPE_CHOICES])
        gst_config = fetch_gst_config(
            region_id=billing_region.id if billing_region else None,
            issue_date=effective_from,
            rate_type=rate_type,
            exempt_zero_rated=rate_type in ['EXEMPT', 'ZERO_RATED']
        )
        gst_config_id = None
        if gst_config.get('id') == builtins.id:
            logger.error(f"gst_config_id is set to built-in id function: {gst_config.get('id')}")
            raise ValidationError("Invalid gst_config_id")

        # Assign GSTINs for India transactions
        if is_india_transaction:
            entity_mapping = entity.get_entity_mapping()
            tax_profile = TaxProfile.objects.filter(
                entity_mapping_id=entity_mapping.id,
                tax_identifier_type='GSTIN',
                is_active=True
            ).first()
            issuer_gstin = tax_profile.tax_identifier if tax_profile else self.generate_gstin(billing_region, entity)

            if recipient:
                recipient_mapping = recipient.get_entity_mapping()
                recipient_tax_profile = TaxProfile.objects.filter(
                    entity_mapping_id=recipient_mapping.id,
                    tax_identifier_type='GSTIN',
                    is_active=True
                ).first()
                recipient_gstin = recipient_tax_profile.tax_identifier if recipient_tax_profile else self.generate_gstin(billing_region, recipient)

        # Determine if transaction is interstate
        is_interstate = is_interstate_transaction(
            buyer_gstin=recipient_gstin,
            seller_gstin=issuer_gstin,
            billing_region_id=billing_region.id if billing_region else None,
            billing_country_id=billing_country.id if billing_country else None,
            issuer=entity,
            recipient=recipient,
            issue_date=effective_from
        )

        # Assign GST rates
        if is_india_transaction:
            if tax_exemption_status in ['EXEMPT', 'ZERO_RATED']:
                cgst_rate = Decimal('0.00')
                sgst_rate = Decimal('0.00')
                igst_rate = Decimal('0.00')
            else:
                if is_interstate:
                    cgst_rate = Decimal('0.00')
                    sgst_rate = Decimal('0.00')
                    igst_rate = Decimal(gst_config['igst_rate']).quantize(Decimal('0.01')) if gst_config['igst_rate'] else Decimal('0.00')
                else:
                    cgst_rate = Decimal(gst_config['cgst_rate']).quantize(Decimal('0.01')) if gst_config['cgst_rate'] else Decimal('0.00')
                    sgst_rate = Decimal(gst_config['sgst_rate']).quantize(Decimal('0.01')) if gst_config['sgst_rate'] else Decimal('0.00')
                    igst_rate = Decimal('0.00')
        else:
            cgst_rate = Decimal('0.00')
            sgst_rate = Decimal('0.00')
            igst_rate = Decimal('0.00')

        # Validate GST rates
        try:
            validate_gst_rates(
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                region_id=billing_region.id if billing_region else None,
                country_id=billing_country.id,
                issue_date=effective_from,
                tax_exemption_status=tax_exemption_status
            )
        except GSTValidationError as e:
            logger.error(f"GST rate validation failed for entity {entity.slug}: {str(e)}")
            raise

        # Create invoice object
        invoice = Invoice(
            id=counters['invoice'],
            issuer=entity,
            recipient=recipient,
            billing_address=billing_address,
            billing_country=billing_country,
            billing_region=billing_region,
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

        # Wrap in a transaction to ensure atomicity
        with transaction.atomic():
            # Generate and save line items
            line_item_data = self.generate_line_item(invoice, counters, admin_user, max_line_items=5, line_item_json=line_item_json)
            if not line_item_data:
                logger.error(f"No line items generated for invoice {invoice.invoice_number}")
                raise ValidationError(f"No line items generated for invoice {invoice.invoice_number}")

            # Save invoice initially without totals to assign ID
            try:
                invoice.base_amount = Decimal('0.00')
                invoice.total_amount = Decimal('0.00')
                invoice.cgst_amount = Decimal('0.00')
                invoice.sgst_amount = Decimal('0.00')
                invoice.igst_amount = Decimal('0.00')
                invoice.save(user=admin_user, skip_validation=True)
                logger.debug(f"Initially saved invoice {invoice.invoice_number} for entity {entity.slug}")
            except (InvoiceValidationError, GSTValidationError) as e:
                logger.error(f"Failed to initially save invoice {invoice.invoice_number} for {entity.slug}: {str(e)}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error initially saving invoice {invoice.invoice_number} for {entity.slug}: {str(e)}", exc_info=True)
                raise

            # Verify line items
            try:
                for item_data in line_item_data:
                    line_item = LineItem.objects.get(id=item_data['id'], invoice=invoice, is_active=True)
                    logger.debug(f"Verified LineItem {line_item.id} for invoice {invoice.invoice_number}")
            except LineItem.DoesNotExist as e:
                logger.error(f"Line item not found or not associated with invoice {invoice.invoice_number}: {str(e)}")
                raise ValidationError(f"Line item not found for invoice {invoice.invoice_number}")

            # Calculate and update invoice totals
            try:
                invoice.refresh_from_db()
                total_data = calculate_total_amount(invoice)
                logger.debug(f"Calculated total for invoice {invoice.invoice_number}: {total_data}")
                invoice.base_amount = total_data.get('base', Decimal('0.00')).quantize(Decimal('0.01'))
                invoice.total_amount = total_data.get('total', Decimal('0.00')).quantize(Decimal('0.01'))
                invoice.cgst_amount = total_data.get('cgst', Decimal('0.00')).quantize(Decimal('0.01'))
                invoice.sgst_amount = total_data.get('sgst', Decimal('0.00')).quantize(Decimal('0.01'))
                invoice.igst_amount = total_data.get('igst', Decimal('0.00')).quantize(Decimal('0.01'))
                invoice.save(user=admin_user, skip_validation=True)  # Explicitly skip validation
                logger.debug(f"Updated invoice {invoice.invoice_number} with totals")
            except Exception as e:
                logger.error(f"Failed to calculate total for invoice {invoice.invoice_number}: {str(e)}")
                raise ValidationError(f"Failed to calculate invoice total: {str(e)}")

        # Generate payments and billing schedules
        payment_data = self.generate_payment(invoice, status, counters, admin_user, total_data)
        billing_schedule_data = self.generate_billing_schedule(invoice, entity, counters, admin_user, num_schedules=num_schedules)

        # Prepare invoice data for JSON
        invoice_data = {
            'id': invoice.id,
            'issuer_id': invoice.issuer_id,
            'recipient_id': invoice.recipient_id,
            'billing_address_id': invoice.billing_address_id,
            'billing_country_id': invoice.billing_country_id,
            'billing_region_id': invoice.billing_region.id if invoice.billing_region else None,
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
            'gst_config_id': str(gst_config_id) if gst_config_id else None
        }
        gst_config_entry = None
        if is_india_transaction:
            gst_config_entry = {
                'id': str(gst_config.get('id')) if gst_config.get('id') else None,
                'description': gst_config.get('description', f"{rate_type.title()} GST for {'Interstate' if not billing_region else billing_region.name}"),
                'rate_type': gst_config.get('rate_type', rate_type),
                'cgst_rate': str(cgst_rate),
                'sgst_rate': str(sgst_rate),
                'igst_rate': str(igst_rate),
                'applicable_region_id': gst_config.get('region_id'),
                'effective_from': effective_from.isoformat() if effective_from else gst_config.get('effective_from'),
                'effective_to': effective_to.isoformat() if effective_to else gst_config.get('effective_to'),
            }

        return {
            'invoice': invoice_data,
            'line_item': line_item_data,
            'billing_schedule': billing_schedule_data,
            'payment': payment_data,
            'gst_config': gst_config_entry
        }

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

        script_duration = options['scriptduration']
        num_schedules = options['schedules']
        skip_json = options['skipjson']
        fixed_mode = options['fixed']

        env_data = load_env_paths(env_var='INVOICES_JSON', require_exists=False)
        invoices_path = env_data.get('INVOICES_JSON')
        if not invoices_path and not skip_json:
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

        entity_slug = options.get('entity')
        if entity_slug and not options['all']:
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
        else:
            entities = Entity.objects.filter(is_active=True)
            if country_code:
                entities = entities.filter(default_address__city__subregion__region__country__country_code=country_code.upper())
            if not entities:
                self.stderr.write(self.style.ERROR("No active entities found" + (f" for country {country_code}" if country_code else "")))
                logger.error("No active entities found" + (f" for country {country_code}" if country_code else ""))
                return

        all_statuses = Status.objects.filter(is_active=True)
        if not all_statuses.exists():
            self.stderr.write(self.style.ERROR("No active statuses found"))
            logger.error("No active statuses found")
            return

        num_invoices_per_status = 1 if fixed_mode else (options['maxcount'] if options['maxcount'] != 2 else random.randint(options['mincount'], options['maxcount']))

        json_data = {
            'invoice': [],
            'line_item': [],
            'billing_schedule': [],
            'payment': [],
            'gst_config': []
        } if not skip_json else None

        unique_gst_configs = set() if not skip_json else None

        try:
            self.line_item_json = self.fetch_line_items_json()
            logger.info("Successfully loaded invoice_line_items.json")
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to load invoice_line_items.json: {str(e)}"))
            logger.error(f"Failed to load invoice_line_items.json: {str(e)}")
            return

        for entity in entities:
            entity_slug = entity.slug
            entity_country_code = entity.default_address.city.subregion.region.country.country_code if entity.default_address and entity.default_address.city else 'UNKNOWN'
            invoices_json = str(Path(invoices_path) / entity_country_code / f"{entity_slug}.json") if not skip_json else None
            self.stdout.write(f"Generating invoices for entity: {entity.name} ({entity_slug}) in {entity_country_code}")
            logger.info(f"Generating invoices for entity {entity.name} in {entity_country_code}")

            same_country_entities = Entity.objects.filter(
                default_address__city__subregion__region__country__country_code=entity_country_code,
                is_active=True
            ).exclude(id=entity.id)

            for status in all_statuses:
                logger.debug(f"Processing status {status.code} for entity {entity_slug}")
                invoice_count = 0
                max_invoices = num_invoices_per_status if not fixed_mode else 1

                while invoice_count < max_invoices:
                    if time.time() - start_time > script_duration:
                        self.stderr.write(self.style.WARNING(f"Invoice generation timeout reached after {script_duration} seconds"))
                        logger.warning(f"Invoice generation timeout reached after {script_duration} seconds")
                        if json_data and invoices_json:
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
                                self.stdout.write(f" - {skipped.get('invoice', skipped.get('entity'))}: {skipped['reason']}")
                            if len(stats['skipped']) > 5:
                                self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
                        self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
                        logger.info(f"Generation and Import Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
                        return

                    # recipient = random.choice(list(same_country_entities)) if same_country_entities.exists() and (fixed_mode or random.choice([True, False])) else None
                    # if fixed_mode and not recipient:
                    #     recipient = random.choice(list(same_country_entities)) if same_country_entities.exists() else None
                    #     if not recipient:
                    #         error_details = {'invoice': f"Invoice {counters['invoice']}", 'reason': 'No valid recipient found for fixed mode', 'entity': entity_slug}
                    #         stats['skipped'].append(error_details)
                    #         logger.error(f"Skipping invoice generation {counters['invoice']} for {entity_slug}: {error_details['reason']}", extra={'details': error_details})
                    #         continue

                    recipient = random.choice(list(same_country_entities)) if same_country_entities.exists() else None
                    if not recipient:
                        error_details = {'invoice': f"Invoice {counters['invoice']}", 'reason': 'No valid recipient found', 'entity': entity_slug}
                        stats['skipped'].append(error_details)
                        logger.error(f"Skipping invoice generation {counters['invoice']} for {entity_slug}: {error_details['reason']}", extra={'details': error_details})
                        continue

                    stats['total'] += 1
                    counters['invoice'] += 1
                    try:
                        invoice_data = self.generate_invoice(
                            entity, status, counters, admin_user, line_item_json=self.line_item_json, recipient=recipient,
                            num_schedules=num_schedules
                        )
                        if not skip_json:
                            json_data['invoice'].append(invoice_data['invoice'])
                            json_data['line_item'].extend(invoice_data['line_item'])
                            json_data['billing_schedule'].extend(invoice_data['billing_schedule'])
                            json_data['payment'].extend(invoice_data['payment'])
                            if invoice_data['gst_config']:
                                gst_config_tuple = (
                                    invoice_data['gst_config'].get('id'),
                                    invoice_data['gst_config']['rate_type'],
                                    invoice_data['gst_config']['applicable_region_id'],
                                    invoice_data['gst_config']['effective_from'],
                                    invoice_data['gst_config']['effective_to'],
                                    invoice_data['gst_config']['cgst_rate'],
                                    invoice_data['gst_config']['sgst_rate'],
                                    invoice_data['gst_config']['igst_rate']
                                )
                                if gst_config_tuple not in unique_gst_configs:
                                    unique_gst_configs.add(gst_config_tuple)
                                    json_data['gst_config'].append(invoice_data['gst_config'])
                        stats['created'] += 1
                        logger.info(f"Successfully generated invoice {invoice_data['invoice']['invoice_number']} for entity {entity_slug}")
                    except Exception as e:
                        error_details = {'invoice': f"Invoice {counters['invoice']}", 'reason': str(e), 'entity': entity_slug}
                        stats['skipped'].append(error_details)
                        logger.error(f"Skipping invoice generation {counters['invoice']} for {entity_slug}: {str(e)}", extra={'details': error_details})
                    invoice_count += 1

            if not skip_json and invoices_json:
                try:
                    Path(invoices_json).parent.mkdir(parents=True, exist_ok=True)
                    with open(invoices_json, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=4, ensure_ascii=False)
                    self.stdout.write(self.style.SUCCESS(f"Generated JSON at {invoices_json}"))
                    logger.info(f"Generated JSON at {invoices_json}")
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}"))
                    logger.error(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}")

        self.line_item_json = None
        logger.info("Cleared invoice_line_items.json from memory")

        self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f" - Total invoices: {stats['total']}")
        self.stdout.write(f" - Created: {stats['created']}")
        self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f" - {skipped.get('invoice', skipped.get('entity'))}: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Generation and Import Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")

# import json
# import logging
# import time
# import random
# import builtins
# from pathlib import Path
# from django.core.management.base import BaseCommand
# from django.core.exceptions import ValidationError, ObjectDoesNotExist
# from django.db import transaction, models
# from django.utils import timezone
# from datetime import date, timedelta
# from decimal import Decimal, ROUND_DOWN
# from django.db.models import Max, Q
# from entities.models.entity import Entity
# from industries.models import Industry
# from invoices.models.invoice import Invoice
# from invoices.models.line_item import LineItem
# from invoices.models.billing_schedule import BillingSchedule
# from invoices.models.payment import Payment
# from invoices.models.status import Status
# from invoices.models.payment_method import PaymentMethod
# from utilities.utils.entities.entity_validations import validate_gstin
# from invoices.services import (
#     validate_billing_schedule, validate_hsn_sac_code, validate_line_item, calculate_line_item_total,
#     fetch_gst_config, is_interstate_transaction, entity_from_gstin,
#     validate_payment_amount, validate_payment_reference, validate_invoice, calculate_total_amount,
#     validate_gst_rates, generate_invoice_number
# )
# from fincore.models.tax_profile import TaxProfile
# from locations.models.custom_country import CustomCountry
# from utilities.utils.data_sync.load_env_and_paths import load_env_paths
# from django.contrib.auth import get_user_model
# from invoices.exceptions import InvoiceValidationError, GSTValidationError

# from invoices.constants import (
#     BILLING_FREQUENCY_CHOICES,
#     BILLING_STATUS_CODES,
#     PAYMENT_TERMS_CHOICES,
#     DESCRIPTION_MAX_LENGTH,
#     GST_RATE_TYPE_CHOICES
# )

# logger = logging.getLogger(__name__)

# class Command(BaseCommand):
#     help = """Generate and imports invoice data for specified entity or all entities in a country to JSON in INVOICES_JSON/{COUNTRY_CODE} directory.
# Expected .env keys: DATA_DIR, INVOICES_JSON
# Example usage: ./manage.py generate_import_invoices --entity entity-slug
#              or ./manage.py generate_import_invoices --all --country IN
#              or ./manage.py generate_import_invoices --country IN
# JSON files are generated in INVOICES_JSON/{COUNTRY_CODE}/{entity-slug}.json
# """

#     def add_arguments(self, parser):
#         parser.add_argument('--entity', type=str, help='Slug of the entity to generate invoices for')
#         parser.add_argument('--all', action='store_true', help='Generate invoices for all entities in the specified country')
#         parser.add_argument('--country', type=str, help='Country code (e.g., IN) to filter entities')
#         parser.add_argument('--count', type=int, default=5, help='Number of invoices per status (default: 2)')
#         parser.add_argument('--min', type=int, default=1, help='Minimum number of invoices per status if --count=2')
#         parser.add_argument('--max', type=int, default=5, help='Maximum number of invoices per status if --count=2')
#         parser.add_argument('--schedules', type=int, default=2, help='Number of billing schedules per invoice')

#     def fetch_line_items_json(self):
#         """Load invoice_line_items.json and return the data."""
#         env_data = load_env_paths(env_var='LINE_ITEM_JSON', require_exists=False)
#         line_item_json_path = env_data.get('LINE_ITEM_JSON')
#         if not line_item_json_path:
#             logger.error("LINE_ITEM_JSON not defined in .env")
#             raise ValidationError("LINE_ITEM_JSON not defined in .env")
#         file_path = str(Path(line_item_json_path))
#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 return json.load(f)
#         except Exception as e:
#             logger.error(f"Error reading invoice_line_items.json from {file_path}: {str(e)}")
#             raise ValidationError(f"Error reading invoice_line_items.json: {str(e)}")

#     def generate_gstin(self, region, entity):
#         """Generate a valid GSTIN for the given region and ensure it matches entity's tax profile and address state."""
#         if not region or not hasattr(region, 'code'):
#             state_code = str(random.randint(1, 37)).zfill(2)
#         else:
#             state_code = entity.default_address.city.subregion.region.code.zfill(2) if entity.default_address and entity.default_address.city else str(random.randint(1, 37)).zfill(2)

#         entity_region = entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
#         if entity_region and entity_region.code != state_code:
#             logger.warning(f"Region code {state_code} does not match entity {entity.slug} default address region {entity_region.code}")
#             state_code = entity_region.code.zfill(2)

#         entity_mapping = entity.get_entity_mapping()
#         tax_profile = TaxProfile.objects.filter(
#             entity_mapping_id=entity_mapping.id,
#             tax_identifier_type='GSTIN',
#             tax_identifier__startswith=state_code,
#             is_active=True
#         ).first()
#         if tax_profile:
#             try:
#                 validate_gstin(tax_profile.tax_identifier)
#                 entity_data = entity_from_gstin(tax_profile.tax_identifier)
#                 if entity_data and entity_data['id'] == entity.id:
#                     logger.info(f"Using existing GSTIN {tax_profile.tax_identifier} for entity {entity.slug}")
#                     return tax_profile.tax_identifier
#                 logger.warning(f"Tax profile GSTIN {tax_profile.tax_identifier} already used by another entity or no entity found")
#             except (ValidationError, GSTValidationError) as e:
#                 logger.warning(f"Invalid GSTIN in tax profile for entity {entity.slug}: {tax_profile.tax_identifier}, error: {str(e)}")

#         max_attempts = 50
#         for attempt in range(max_attempts):
#             if attempt == 25:
#                 logger.warning(f"Reached 50% of max_attempts ({max_attempts}) for GSTIN generation for entity {entity.slug}")
#             pan = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5)) + ''.join(random.choices('0123456789', k=4)) + random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
#             entity_code = random.choice(['1', '2', '3', '4', '5', '6'])
#             check_digit = random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
#             gstin = f"{state_code}{pan}{entity_code}Z{check_digit}"
#             try:
#                 validate_gstin(gstin)
#                 entity_data = entity_from_gstin(gstin)
#                 if entity_data is None or entity_data['id'] is None:
#                     logger.info(f"Generated unique GSTIN {gstin} for entity {entity.slug}")
#                     return gstin
#             except (ValidationError, GSTValidationError):
#                 continue
#         raise ValidationError(f"Could not generate unique GSTIN for entity {entity.slug} after {max_attempts} attempts")

#     def generate_payment(self, invoice, status, counters, admin_user, total_data):
#         """Generate payment data for the given invoice with at least 3 payments for PAID, PARTIALLY_PAID, and CANCELLED statuses."""
#         payment_data = []
#         logger.debug(f"Attempting payments for invoice {invoice.id}, status {status.code}, total {total_data['total']}")

#         if status.code not in ['PAID', 'PARTIALLY_PAID', 'CANCELLED']:
#             logger.debug(f"Skipping payment for invoice {invoice.id}: Status {status.code} not PAID, PARTIALLY_PAID, or CANCELLED")
#             return payment_data

#         if total_data['total'] <= 0:
#             logger.warning(f"Skipping payment for invoice {invoice.id}: Non-positive total {total_data['total']}")
#             return payment_data

#         payment_methods = PaymentMethod.objects.filter(is_active=True)
#         if not payment_methods.exists():
#             logger.error(f"No active payment methods for invoice {invoice.id}")
#             raise ValidationError(f"No active payment methods found for invoice {invoice.id}")

#         invoice_number = invoice.invoice_number
#         last_14_digits = invoice_number[-14:] if len(invoice_number) >= 14 else invoice_number
#         num_payments = 3  # Generate exactly 3 payments

#         # Ensure total_payment_amount is a Decimal quantized to 2 decimal places
#         total_payment_amount = Decimal(str(total_data['total'])).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
#         if status.code != 'PAID':
#             total_payment_amount = (total_payment_amount * Decimal(str(random.uniform(0.3, 0.9)))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

#         # Distribute total_payment_amount across 3 payments
#         if status.code == 'PAID':
#             # Divide equally, ensuring each payment is quantized
#             base_amount = (total_payment_amount / 3).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
#             payment_amounts = [base_amount] * 3
#             # Adjust the last payment to ensure the sum matches total_payment_amount
#             total_payment_sum = sum(payment_amounts)
#             if total_payment_sum != total_payment_amount:
#                 payment_amounts[-1] = (total_payment_amount - 2 * base_amount).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
#         else:
#             # For PARTIALLY_PAID and CANCELLED, create variable amounts
#             weights = [random.uniform(0.2, 0.5) for _ in range(2)]
#             weights.append(1 - sum(weights))
#             payment_amounts = []
#             remaining_amount = total_payment_amount
#             for i, w in enumerate(weights[:2]):
#                 amount = (total_payment_amount * Decimal(str(w))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
#                 payment_amounts.append(amount)
#                 remaining_amount -= amount
#             # Last payment takes the remaining amount to avoid precision issues
#             payment_amounts.append(remaining_amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN))

#         for i in range(num_payments):
#             counters['payment'] += 1
#             payment_method = random.choice(list(payment_methods))
#             payment_amount = payment_amounts[i]

#             if payment_amount <= 0:
#                 logger.warning(f"Skipping payment {counters['payment']} for invoice {invoice.id}: Non-positive amount {payment_amount}")
#                 continue

#             # Generate UPI-compliant payment reference if payment method is UPI
#             if payment_method.code == 'UPI':
#                 reference_chars = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))
#                 payment_reference = f"UPI{reference_chars}{random.randint(1000, 9999)}"
#             else:
#                 payment_reference = f"PAY-/{last_14_digits}/{random.randint(1000, 9999)}"
#             payment_reference = payment_reference[:50]

#             payment = Payment(
#                 id=counters['payment'],
#                 invoice=invoice,
#                 payment_method=payment_method,
#                 amount=payment_amount,
#                 payment_reference=payment_reference,
#                 payment_date=invoice.issue_date + timedelta(days=random.randint(0, 30)),
#                 status='COMPLETED' if status.code != 'CANCELLED' else 'CANCELLED',
#                 created_by=admin_user,
#                 updated_by=admin_user,
#                 created_at=timezone.now(),
#                 updated_at=timezone.now(),
#                 is_active=status.code != 'CANCELLED'
#             )

#             try:
#                 validate_payment_amount(payment_amount, invoice, payment.id)
#                 validate_payment_reference(payment_reference, payment_method.code, invoice, payment.id)
#                 payment.save()
#                 payment_data.append({
#                     'id': payment.id,
#                     'invoice_id': invoice.id,
#                     'payment_method_id': payment_method.id,
#                     'amount': str(payment.amount),
#                     'payment_reference': payment.payment_reference,
#                     'payment_date': payment.payment_date.strftime('%Y-%m-%d'),
#                     'created_by_id': payment.created_by_id,
#                     'updated_by_id': payment.updated_by_id,
#                     'is_active': payment.is_active
#                 })
#                 logger.debug(f"Generated payment {payment.id} for invoice {invoice.id}")
#             except (InvoiceValidationError, GSTValidationError) as e:
#                 logger.error(f"Failed to validate or save payment {counters['payment']} for invoice {invoice.id}: {str(e)}")
#                 raise

#         return payment_data

#     def generate_billing_schedule(self, invoice, entity, counters, admin_user, num_schedules=1):
#         """Generate billing schedule data for the given invoice, inactive for CANCELLED status."""
#         billing_schedule_data = []
#         # Skip billing schedules for DRAFT invoices
#         if invoice.status.code == 'DRAFT':
#             logger.debug(f"Skipping billing schedule generation for invoice {invoice.invoice_number} with status {invoice.status.code}")
#             return billing_schedule_data

#         for _ in range(num_schedules):
#             counters['billing_schedule'] += 1
#             issue_date = invoice.issue_date if isinstance(invoice.issue_date, date) else invoice.issue_date.date()
#             next_billing_date = issue_date + timedelta(days=random.randint(1, 30))
#             start_date = issue_date
#             status = random.choice(list(BILLING_STATUS_CODES.keys()))
#             end_date = next_billing_date + timedelta(days=random.randint(1, 90)) if status == 'COMPLETED' else None
#             amount = max(invoice.total_amount.quantize(Decimal('0.01')), Decimal('0.01'))

#             billing_schedule = BillingSchedule(
#                 id=counters['billing_schedule'],
#                 entity=entity,
#                 description=f"Billing Schedule {counters['billing_schedule']} for Invoice {invoice.invoice_number}",
#                 start_date=start_date,
#                 next_billing_date=next_billing_date,
#                 end_date=end_date,
#                 amount=amount,
#                 frequency=random.choice([freq[0] for freq in BILLING_FREQUENCY_CHOICES]),
#                 status=status,
#                 created_by=admin_user,
#                 updated_by=admin_user,
#                 created_at=timezone.now(),
#                 updated_at=timezone.now(),
#                 is_active=invoice.status.code != 'CANCELLED'
#             )
#             try:
#                 validate_billing_schedule(billing_schedule)
#                 billing_schedule.save(user=admin_user)
#                 billing_schedule_data.append({
#                     'id': billing_schedule.id,
#                     'entity_id': billing_schedule.entity_id,
#                     'description': billing_schedule.description,
#                     'start_date': billing_schedule.start_date.isoformat(),
#                     'next_billing_date': billing_schedule.next_billing_date.isoformat(),
#                     'end_date': billing_schedule.end_date.isoformat() if billing_schedule.end_date else None,
#                     'amount': str(billing_schedule.amount),
#                     'frequency': billing_schedule.frequency,
#                     'status': billing_schedule.status,
#                     'created_at': billing_schedule.created_at.isoformat(),
#                     'updated_at': billing_schedule.updated_at.isoformat(),
#                     'created_by_id': billing_schedule.created_by_id,
#                     'updated_by_id': billing_schedule.updated_by_id,
#                     'is_active': billing_schedule.is_active
#                 })
#             except Exception as e:
#                 logger.error(f"Failed to save billing schedule {counters['billing_schedule']} for invoice {invoice.invoice_number}: {str(e)}")
#                 raise
#         return billing_schedule_data

#     def generate_line_item(self, invoice, counters, admin_user, max_line_items=5, line_item_json=None):
#         """Generate line items for the invoice using invoice_line_items.json."""
#         line_item_data = []
#         used_hsn_sac_codes = set()

#         # Validate JSON
#         if not line_item_json or not line_item_json.get('isic'):
#             logger.error(f"Invalid JSON for invoice {invoice.invoice_number}: JSON is missing or lacks 'isic' key")
#             raise ValidationError("Invalid or missing JSON")

#         # Get industry code
#         try:
#             industry = Industry.objects.filter(entities=invoice.issuer, is_active=True).first()
#             industry_code = industry.code if industry else None
#             logger.debug(f"Industry code for entity {invoice.issuer.slug}: {industry_code}")
#         except AttributeError as e:
#             logger.error(f"Invalid issuer for invoice {invoice.invoice_number}: {str(e)}")
#             raise ValidationError(f"Invalid issuer: {str(e)}")

#         # Find line items
#         line_item_choices = []
#         if industry_code:
#             logger.debug(f"Searching for line items for industry code: {industry_code}")
#             for section in line_item_json['isic']:
#                 section_code = section.get("Section", "Unknown")
#                 for division in section.get("Divisions", []):
#                     division_code = division.get("Division", "Unknown")
#                     for group in division.get("Groups", []):
#                         group_code = group.get("Group", "Unknown")
#                         for class_data in group.get("Classes", []):
#                             class_code = class_data.get("Class")
#                             if class_code == industry_code:
#                                 line_items = class_data.get("line_items", {})
#                                 if line_items:
#                                     line_item_choices = list(line_items.values())
#                                     logger.debug(f"Found {len(line_item_choices)} line items for industry {industry_code} in section {section_code}, division {division_code}, group {group_code}, class {class_code}")
#                                 else:
#                                     logger.warning(f"No line items found in JSON for industry {industry_code} in class {class_code}")
#                                 break
#                             if line_item_choices:
#                                 break
#                         if line_item_choices:
#                             break
#                     if line_item_choices:
#                         break

#         # If no specific line items found, try a generic fallback from JSON
#         if not line_item_choices and line_item_json.get('isic'):
#             logger.warning(f"No line items found for industry {industry_code or 'None'} in invoice {invoice.invoice_number}. Attempting generic JSON fallback.")
#             for section in line_item_json['isic']:
#                 for division in section.get("Divisions", []):
#                     for group in division.get("Groups", []):
#                         for class_data in group.get("Classes", []):
#                             line_items = class_data.get("line_items", {})
#                             if line_items:
#                                 line_item_choices.extend(list(line_items.values()))
#             logger.debug(f"Generic JSON fallback found {len(line_item_choices)} line items: {line_item_choices[:5]}...")

#         # Final fallback to default values if JSON fallback also fails
#         if not line_item_choices:
#             logger.warning(f"No line items found in JSON for invoice {invoice.invoice_number}. Using default fallback values.")
#             logger.debug(f"Available class codes in JSON: {[c['Class'] for s in line_item_json['isic'] for d in s.get('Divisions', []) for g in d.get('Groups', []) for c in g.get('Classes', [])]}")
#             line_item_choices = ["General service item", "Consulting service", "Product delivery", "Maintenance service", "Support service"]

#         # Create line items
#         for description in random.sample(line_item_choices, min(max_line_items, len(line_item_choices))):
#             counters['line_item'] += 1

#             # Truncate description if needed
#             description = description[:DESCRIPTION_MAX_LENGTH]

#             # Generate HSN/SAC code
#             for _ in range(50):
#                 code_type = random.choice(['HSN', 'SAC'])
#                 code_number = ''.join(random.choices('0123456789', k=4))
#                 hsn_sac_code = f"{code_type} {code_number}"
#                 if hsn_sac_code not in used_hsn_sac_codes:
#                     try:
#                         validate_hsn_sac_code(hsn_sac_code)
#                         used_hsn_sac_codes.add(hsn_sac_code)
#                         break
#                     except GSTValidationError:
#                         continue
#                 else:
#                     logger.warning(f"HSN/SAC code {hsn_sac_code} already used for invoice {invoice.invoice_number}")
#             else:
#                 logger.error(f"Failed to generate unique HSN/SAC code for invoice {invoice.invoice_number} after 50 attempts")
#                 raise ValidationError("Could not generate unique HSN/SAC code")

#             # Create line item
#             line_item = LineItem(
#                 id=counters['line_item'],
#                 invoice=invoice,
#                 description=description,
#                 hsn_sac_code=hsn_sac_code,
#                 quantity=random.randint(1, 10),
#                 unit_price=Decimal(str(round(random.uniform(10, 100), 2))),
#                 discount=Decimal(str(round(random.uniform(0, 10), 2))),
#                 cgst_rate=invoice.cgst_rate,
#                 sgst_rate=invoice.sgst_rate,
#                 igst_rate=invoice.igst_rate,
#                 created_by=admin_user,
#                 updated_by=admin_user,
#                 created_at=timezone.now(),
#                 updated_at=timezone.now(),
#                 is_active=True
#             )

#             try:
#                 validate_line_item(line_item)
#                 total_data = calculate_line_item_total(line_item)
#                 line_item.cgst_amount = total_data['cgst_amount']
#                 line_item.sgst_amount = total_data['sgst_amount']
#                 line_item.igst_amount = total_data['igst_amount']
#                 line_item.total_amount = total_data['total']
#                 line_item.save()
#                 line_item_data.append({
#                     'id': line_item.id,
#                     'invoice.invoice_number': invoice.invoice_number,
#                     'description': description,
#                     'hsn_sac_code': hsn_sac_code,
#                     'cgst_amount': str(line_item.cgst_amount),
#                     'sgst_amount': str(line_item.sgst_amount),
#                     'igst_amount': str(line_item.igst_amount),
#                     'total_amount': str(line_item.total_amount),
#                     'created_by_id': line_item.created_by_id,
#                     'updated_by_id': line_item.updated_by_id,
#                     'is_active': line_item.is_active,
#                     'quantity': str(line_item.quantity),
#                     'unit_price': str(line_item.unit_price),
#                     'discount': str(line_item.discount),
#                     'cgst_rate': str(line_item.cgst_rate) if line_item.cgst_rate is not None else None,
#                     'sgst_rate': str(line_item.sgst_rate) if line_item.sgst_rate is not None else None,
#                     'igst_rate': str(line_item.igst_rate) if line_item.igst_rate is not None else None,
#                 })
#                 logger.debug(f"Generated line item {line_item.id} for invoice {invoice.invoice_number}: {description}")
#             except Exception as e:
#                 logger.error(f"Failed to save line item {counters['line_item']} for invoice {invoice.invoice_number}: {str(e)}")
#                 raise

#         if not line_item_data:
#             logger.error(f"No line items generated for invoice {invoice.invoice_number}")
#             raise ValidationError("No line items generated")

#         return line_item_data

#     def generate_invoice(self, entity, status, counters, admin_user, line_item_json, recipient=None, num_schedules=1):
#         logger.debug(f"Generating invoice for entity {entity.slug}, status {status.code}, recipient {recipient.slug if recipient else 'None'}")
#         if 'id' in locals() or 'id' in globals():
#             logger.error(f"Variable 'id' is defined in scope: {locals().get('id', globals().get('id'))}")

#         # Validate entity and recipient as Entity instances
#         if not isinstance(entity, Entity):
#             logger.error(f"Invalid issuer entity for invoice generation: {entity} is not an Entity instance")
#             raise ValidationError(f"Invalid issuer entity: Must be an Entity instance")
#         if recipient and not isinstance(recipient, Entity):
#             logger.error(f"Invalid recipient entity for invoice generation: {recipient} is not an Entity instance")
#             raise ValidationError(f"Invalid recipient entity: Must be an Entity instance")

#         # Validate status
#         if not isinstance(status, Status):
#             logger.error(f"Invalid status object for entity {entity.slug}: {status}")
#             raise ValidationError(f"Invalid status object: {status}")

#         # Validate entity and recipient activity
#         if not entity.is_active:
#             logger.error(f"Entity {entity.slug} is not active")
#             raise ValidationError(f"Entity {entity.slug} is not active")
#         if recipient and not recipient.is_active:
#             logger.error(f"Recipient {recipient.slug} is not active")
#             raise ValidationError(f"Recipient {recipient.slug} is not active")

#         # Validate entity and recipient addresses
#         if not entity.default_address or not entity.default_address.city or not entity.default_address.city.subregion.region:
#             logger.error(f"Invalid address configuration for entity {entity.slug}")
#             raise ValidationError(f"Entity {entity.slug} has invalid address configuration")
#         if recipient and (not recipient.default_address or not recipient.default_address.city or not recipient.default_address.city.subregion.region):
#             logger.error(f"Invalid address configuration for recipient {recipient.slug}")
#             raise ValidationError(f"Recipient {recipient.slug} has invalid address configuration")

#         # Determine if transaction is in India
#         effective_from = timezone.now().date() - timedelta(days=random.randint(0, 365))
#         effective_to = effective_from + timedelta(days=random.randint(0, 365))
#         billing_region = entity.default_address.city.subregion.region if entity.default_address and entity.default_address.city else None
#         issuer_gstin = self.generate_gstin(billing_region, entity)
#         recipient_gstin = self.generate_gstin(billing_region, recipient) if recipient else None
#         billing_country = entity.default_address.city.subregion.region.country if billing_region else None
#         is_india_transaction = recipient.default_address.city.subregion.region.country.country_code.upper() == 'IN' if recipient and recipient.default_address and recipient.default_address.city else False
#         tax_exemption_status = random.choices(['NONE', 'EXEMPT', 'ZERO_RATED'], weights=[0.8, 0.1, 0.1], k=1)[0] if is_india_transaction else 'NONE'
#         cgst_rate = None
#         sgst_rate = None
#         igst_rate = None
#         gst_config_id = None

#         # Fetch GST configuration from database
#         rate_type = random.choice([choice[0] for choice in GST_RATE_TYPE_CHOICES])
#         gst_config = fetch_gst_config(
#             region_id=billing_region.id if billing_region else None,
#             issue_date=effective_from,
#             rate_type=rate_type,
#             exempt_zero_rated=rate_type in ['EXEMPT', 'ZERO_RATED']
#         )
#         if gst_config_id is builtins.id:
#             logger.error(f"gst_config_id is set to built-in id function: {gst_config_id}")

#         if is_india_transaction:
#             entity_mapping = entity.get_entity_mapping()
#             tax_profile = TaxProfile.objects.filter(
#                 entity_mapping_id=entity_mapping.id,
#                 tax_identifier_type='GSTIN',
#                 is_active=True
#             ).first()
#             issuer_gstin = tax_profile.tax_identifier if tax_profile else self.generate_gstin(billing_region, entity)

#             if recipient:
#                 recipient_mapping = recipient.get_entity_mapping()
#                 recipient_tax_profile = TaxProfile.objects.filter(
#                     entity_mapping_id=recipient_mapping.id,
#                     tax_identifier_type='GSTIN',
#                     is_active=True
#                 ).first()
#                 recipient_gstin = recipient_tax_profile.tax_identifier if recipient_tax_profile else self.generate_gstin(billing_region, recipient)

#         is_interstate = is_interstate_transaction(
#             buyer_gstin=recipient_gstin,
#             seller_gstin=issuer_gstin,
#             billing_region_id=billing_region.id if billing_region else None,
#             billing_country_id=billing_country.id if billing_country else None,
#             issuer=entity,
#             recipient=recipient,
#             issue_date=effective_from
#         )

#         # Assign GST rates based on configuration and transaction type
#         if is_india_transaction:
#             if tax_exemption_status in ['EXEMPT', 'ZERO_RATED']:
#                 cgst_rate = Decimal('0.00')
#                 sgst_rate = Decimal('0.00')
#                 igst_rate = Decimal('0.00')
#             else:
#                 if is_interstate:
#                     cgst_rate = Decimal('0.00')
#                     sgst_rate = Decimal('0.00')
#                     igst_rate = Decimal(gst_config['igst_rate']).quantize(Decimal('0.01')) if gst_config['igst_rate'] else Decimal('0.00')
#                 else:
#                     cgst_rate = Decimal(gst_config['cgst_rate']).quantize(Decimal('0.01')) if gst_config['cgst_rate'] else Decimal('0.00')
#                     sgst_rate = Decimal(gst_config['sgst_rate']).quantize(Decimal('0.01')) if gst_config['sgst_rate'] else Decimal('0.00')
#                     igst_rate = Decimal('0.00')
#         else:
#             cgst_rate = Decimal('0.00')
#             sgst_rate = Decimal('0.00')
#             igst_rate = Decimal('0.00')

#         # Validate GST rates
#         try:
#             validate_gst_rates(
#                 cgst_rate=cgst_rate,
#                 sgst_rate=sgst_rate,
#                 igst_rate=igst_rate,
#                 region_id=billing_region.id if billing_region else None,
#                 country_id=billing_country.id,
#                 issue_date=effective_from,
#                 tax_exemption_status=tax_exemption_status
#             )
#         except GSTValidationError as e:
#             logger.error(f"GST rate validation failed for entity {entity.slug}: {str(e)}")
#             raise

#         # Create invoice object (but don't save yet)
#         invoice = Invoice(
#             id=counters['invoice'],
#             issuer=entity,
#             recipient=recipient,
#             billing_address=recipient.default_address,
#             billing_country=recipient.default_address.city.subregion.region.country,
#             billing_region=recipient.default_address.city.subregion.region,
#             invoice_number=generate_invoice_number(),
#             description=f"Invoice {counters['invoice']} for {entity.name}",
#             issue_date=timezone.now().date() - timedelta(days=random.randint(0, 30)),
#             due_date=timezone.now().date() + timedelta(days=random.randint(15, 45)),
#             status=status,
#             payment_terms=random.choice([pt[0] for pt in PAYMENT_TERMS_CHOICES]),
#             currency='INR' if entity.default_address.city.subregion.region.country.country_code == 'IN' else 'USD',
#             base_amount=Decimal('0.00'),
#             total_amount=Decimal('0.00'),
#             cgst_rate=cgst_rate,
#             sgst_rate=sgst_rate,
#             igst_rate=igst_rate,
#             issuer_gstin=issuer_gstin,
#             recipient_gstin=recipient_gstin,
#             tax_exemption_status=tax_exemption_status,
#             created_by=admin_user,
#             updated_by=admin_user,
#             created_at=timezone.now(),
#             updated_at=timezone.now(),
#             is_active=True
#         )

#         # Validate invoice before proceeding
#         try:
#             validate_invoice(invoice)
#         except (InvoiceValidationError, GSTValidationError) as e:
#             logger.error(f"Failed to validate invoice {invoice.invoice_number} for {entity.slug}: {str(e)}")
#             raise

#         # Wrap in a transaction to ensure atomicity
#         with transaction.atomic():
#             # Generate and save line items
#             line_item_data = self.generate_line_item(invoice, counters, admin_user, max_line_items=5, line_item_json=line_item_json)
#             if not line_item_data:
#                 logger.error(f"No line items generated for invoice {invoice.invoice_number}")
#                 raise ValidationError(f"No line items generated for invoice {invoice.invoice_number}")

#             # Save invoice initially without totals to assign ID
#             try:
#                 invoice.base_amount = Decimal('0.00')  # Set temporary values
#                 invoice.total_amount = Decimal('0.00')
#                 invoice.cgst_amount = Decimal('0.00')
#                 invoice.sgst_amount = Decimal('0.00')
#                 invoice.igst_amount = Decimal('0.00')
#                 invoice.save(user=admin_user, skip_validation=True)  # Skip validation to avoid total checks
#                 logger.debug(f"Initially saved invoice {invoice.invoice_number} for entity {entity.slug}")
#             except (InvoiceValidationError, GSTValidationError) as e:
#                 logger.error(f"Failed to initially save invoice {invoice.invoice_number} for {entity.slug}: {str(e)}")
#                 raise
#             except Exception as e:
#                 logger.error(f"Unexpected error initially saving invoice {invoice.invoice_number} for {entity.slug}: {str(e)}", exc_info=True)
#                 raise

#             # Verify line items
#             try:
#                 for item_data in line_item_data:
#                     line_item = LineItem.objects.get(id=item_data['id'], invoice=invoice, is_active=True)
#                     logger.debug(f"Verified LineItem {line_item.id} for invoice {invoice.invoice_number}")
#             except LineItem.DoesNotExist as e:
#                 logger.error(f"Line item not found or not associated with invoice {invoice.invoice_number}: {str(e)}")
#                 raise ValidationError(f"Line item not found for invoice {invoice.invoice_number}")

#             # Calculate and update invoice totals
#             try:
#                 invoice.refresh_from_db()
#                 total_data = calculate_total_amount(invoice)
#                 logger.debug(f"Calculated total for invoice {invoice.invoice_number}: {total_data}")
#                 invoice.base_amount = total_data.get('base', Decimal('0.00')).quantize(Decimal('0.01'))
#                 invoice.total_amount = total_data.get('total', Decimal('0.00')).quantize(Decimal('0.01'))
#                 invoice.cgst_amount = total_data.get('cgst', Decimal('0.00')).quantize(Decimal('0.01'))
#                 invoice.sgst_amount = total_data.get('sgst', Decimal('0.00')).quantize(Decimal('0.01'))
#                 invoice.igst_amount = total_data.get('igst', Decimal('0.00')).quantize(Decimal('0.01'))
#                 invoice.save(user=admin_user)
#                 logger.debug(f"Updated invoice {invoice.invoice_number} with totals")
#             except Exception as e:
#                 logger.error(f"Failed to calculate total for invoice {invoice.invoice_number}: {str(e)}")
#                 raise ValidationError(f"Failed to calculate invoice total: {str(e)}")


#         # Generate payments
#         payment_data = self.generate_payment(invoice, status, counters, admin_user, total_data)

#         # Generate billing schedules
#         billing_schedule_data = self.generate_billing_schedule(invoice, entity, counters, admin_user, num_schedules=num_schedules)

#         invoice_data = {
#             'id': invoice.id,
#             'issuer_id': invoice.issuer_id,
#             'recipient_id': invoice.recipient_id,
#             'billing_address_id': invoice.billing_address_id,
#             'billing_country_id': invoice.billing_country_id,
#             'billing_region_id': invoice.billing_region.id if invoice.billing_region else None,
#             'status_id': invoice.status_id,
#             'invoice_number': invoice.invoice_number,
#             'description': invoice.description,
#             'issue_date': invoice.issue_date.isoformat(),
#             'due_date': invoice.due_date.isoformat(),
#             'payment_terms': invoice.payment_terms,
#             'currency': invoice.currency,
#             'has_gst_required_fields': invoice.has_gst_required_fields,
#             'tax_exemption_status': invoice.tax_exemption_status,
#             'issuer_gstin': invoice.issuer_gstin,
#             'recipient_gstin': invoice.recipient_gstin,
#             'cgst_rate': str(invoice.cgst_rate) if invoice.cgst_rate is not None else None,
#             'sgst_rate': str(invoice.sgst_rate) if invoice.sgst_rate is not None else None,
#             'igst_rate': str(invoice.igst_rate) if invoice.igst_rate is not None else None,
#             'base_amount': str(invoice.base_amount),
#             'cgst_amount': str(invoice.cgst_amount),
#             'sgst_amount': str(invoice.sgst_amount),
#             'igst_amount': str(invoice.igst_amount),
#             'total_amount': str(invoice.total_amount),
#             'created_at': invoice.created_at.isoformat(),
#             'updated_at': invoice.updated_at.isoformat(),
#             'created_by_id': invoice.created_by_id,
#             'updated_by_id': invoice.updated_by_id,
#             'is_active': invoice.is_active,
#             'gst_config_id': str(gst_config_id) if gst_config_id else None
#         }
#         # Construct gst_config dictionary
#         gst_config_entry = None
#         if is_india_transaction:
#             gst_config_entry = {
#                 'id': str(gst_config.get('id')) if gst_config.get('id') else None,
#                 'description': gst_config.get('description', f"{rate_type.title()} GST for {'Interstate' if not billing_region else billing_region.name}"),
#                 'rate_type': gst_config.get('rate_type', rate_type),
#                 'cgst_rate': str(cgst_rate),
#                 'sgst_rate': str(sgst_rate),
#                 'igst_rate': str(igst_rate),
#                 'applicable_region_id': gst_config.get('region_id'),
#                 'effective_from': effective_from.isoformat() if effective_from else gst_config.get('effective_from'),
#                 'effective_to': effective_to.isoformat() if effective_to else gst_config.get('effective_to'),
#             }

#         return {
#             'invoice': invoice_data,
#             'line_item': line_item_data,
#             'billing_schedule': billing_schedule_data,
#             'payment': payment_data,
#             'gst_config': gst_config_entry
#         }

#     def handle(self, *args, **options):
#         start_time = time.time()
#         User = get_user_model()
#         try:
#             admin_user = User.objects.get(id=1)
#             self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username}"))
#         except User.DoesNotExist:
#             self.stderr.write(self.style.ERROR("User with id=1 not found"))
#             logger.error("User with id=1 not found")
#             return

#         stats = {'created': 0, 'skipped': [], 'total': 0}
#         counters = {
#             'invoice': Invoice.objects.aggregate(Max('id'))['id__max'] or 0,
#             'line_item': LineItem.objects.aggregate(Max('id'))['id__max'] or 0,
#             'billing_schedule': BillingSchedule.objects.aggregate(Max('id'))['id__max'] or 0,
#             'payment': Payment.objects.aggregate(Max('id'))['id__max'] or 0
#         }

#         env_data = load_env_paths(env_var='INVOICES_JSON', require_exists=False)
#         invoices_path = env_data.get('INVOICES_JSON')
#         if not invoices_path:
#             self.stderr.write(self.style.ERROR("INVOICES_JSON not defined in .env"))
#             logger.error("INVOICES_JSON not defined")
#             return

#         country_code = options.get('country')
#         if country_code:
#             try:
#                 CustomCountry.objects.get(country_code=country_code.upper())
#             except ObjectDoesNotExist:
#                 self.stderr.write(self.style.ERROR(f"Country with code {country_code} not found"))
#                 logger.error(f"Country with code {country_code} not found")
#                 return

#         entity_slug = options.get('entity')
#         if entity_slug and not options['all']:
#             try:
#                 entity = Entity.objects.get(slug=entity_slug, is_active=True)
#                 if country_code and entity.default_address.city.subregion.region.country.country_code != country_code.upper():
#                     self.stderr.write(self.style.ERROR(f"Entity {entity_slug} does not belong to country {country_code}"))
#                     logger.error(f"Entity {entity_slug} does not belong to country {country_code}")
#                     return
#                 entities = [entity]
#             except ObjectDoesNotExist:
#                 self.stderr.write(self.style.ERROR(f"Entity with slug {entity_slug} not found"))
#                 logger.error(f"Entity with slug {entity_slug} not found")
#                 return
#         else:
#             entities = Entity.objects.filter(is_active=True)
#             if country_code:
#                 entities = entities.filter(default_address__city__subregion__region__country__country_code=country_code.upper())
#             if not entities:
#                 self.stderr.write(self.style.ERROR(f"No active entities found" + (f" for country {country_code}" if country_code else "")))
#                 logger.error(f"No active entities found" + (f" for country {country_code}" if country_code else ""))
#                 return

#         all_statuses = Status.objects.filter(is_active=True)
#         if not all_statuses.exists():
#             self.stderr.write(self.style.ERROR("No active statuses found"))
#             logger.error("No active statuses found")
#             return

#         num_invoices_per_status = options['count'] if options['count'] != 2 else random.randint(options['min'], options['max'])
#         max_duration = 172800
#         unique_gst_configs = set()
#         num_schedules = options['schedules']
#         json_data = {
#             'invoice': [],
#             'line_item': [],
#             'billing_schedule': [],
#             'payment': [],
#             'gst_config': []
#         }

#         # Load line items JSON once
#         try:
#             self.line_item_json = self.fetch_line_items_json()
#             logger.info("Successfully loaded invoice_line_items.json")
#         except Exception as e:
#             self.stderr.write(self.style.ERROR(f"Failed to load invoice_line_items.json: {str(e)}"))
#             logger.error(f"Failed to load invoice_line_items.json: {str(e)}")
#             return

#         for entity in entities:
#             entity_slug = entity.slug
#             entity_country_code = entity.default_address.city.subregion.region.country.country_code if entity.default_address and entity.default_address.city else 'UNKNOWN'
#             invoices_json = str(Path(invoices_path) / entity_country_code / f"{entity_slug}.json")
#             self.stdout.write(f"Generating invoices for entity: {entity.name} ({entity_slug}) in {entity_country_code}")
#             logger.info(f"Generating {num_invoices_per_status} invoice(s) per status for entity {entity.name} in {entity_country_code}")

#             same_country_entities = Entity.objects.filter(
#                 default_address__city__subregion__region__country__country_code=entity_country_code,
#                 is_active=True
#             ).exclude(id=entity.id)
#             recipient = random.choice(list(same_country_entities)) if same_country_entities.exists() else None
#             logger.debug(f"Selected recipient: {recipient.slug if recipient else 'None'} for entity {entity_slug}")

#             for status in all_statuses:
#                 logger.debug(f"Processing status {status.code} for entity {entity_slug}")
#                 for _ in range(num_invoices_per_status):
#                     if time.time() - start_time > max_duration:
#                         self.stderr.write(self.style.ERROR(f"Generation timed out after {max_duration} seconds"))
#                         logger.error(f"Generation timed out after {max_duration} seconds")
#                         return
#                     stats['total'] += 1
#                     counters['invoice'] += 1
#                     try:
#                         invoice_data = self.generate_invoice(
#                             entity, status, counters, admin_user, line_item_json=self.line_item_json, recipient=recipient,
#                             num_schedules=num_schedules
#                         )
#                         json_data['invoice'].append(invoice_data['invoice'])
#                         json_data['line_item'].extend(invoice_data['line_item'])
#                         json_data['billing_schedule'].extend(invoice_data['billing_schedule'])
#                         json_data['payment'].extend(invoice_data['payment'])
#                         if invoice_data['gst_config']:
#                             gst_config_tuple = (
#                                 invoice_data['gst_config'].get('id'),
#                                 invoice_data['gst_config']['rate_type'],
#                                 invoice_data['gst_config']['applicable_region_id'],
#                                 invoice_data['gst_config']['effective_from'],
#                                 invoice_data['gst_config']['effective_to'],
#                                 invoice_data['gst_config']['cgst_rate'],
#                                 invoice_data['gst_config']['sgst_rate'],
#                                 invoice_data['gst_config']['igst_rate']
#                             )
#                             if gst_config_tuple not in unique_gst_configs:
#                                 unique_gst_configs.add(gst_config_tuple)
#                                 json_data['gst_config'].append(invoice_data['gst_config'])
#                             stats['created'] += 1
#                             logger.info(f"Successfully generated invoice {invoice_data['invoice']['invoice_number']} for entity {entity_slug}")
#                         else:
#                             stats['created'] += 1
#                             logger.info(f"Successfully generated invoice {invoice_data['invoice']['invoice_number']} for entity {entity_slug} (no GST config)")
#                     except Exception as e:
#                         error_details = {'invoice': f"Invoice {counters['invoice']}", 'reason': str(e), 'entity': entity_slug}
#                         stats['skipped'].append(error_details)
#                         logger.error(f"Skipping invoice generation {counters['invoice']} for {entity_slug}: {str(e)}", extra={'details': error_details})

#             try:
#                 Path(invoices_json).parent.mkdir(parents=True, exist_ok=True)
#                 with open(invoices_json, 'w', encoding='utf-8') as f:
#                     json.dump(json_data, f, indent=4, ensure_ascii=False)
#                 self.stdout.write(self.style.SUCCESS(f"Generated JSON at {invoices_json}"))
#                 logger.info(f"Generated JSON at {invoices_json}")
#             except Exception as e:
#                 self.stderr.write(self.style.ERROR(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}"))
#                 logger.error(f"Error writing JSON for {entity_slug} in {entity_country_code}: {str(e)}")

#         # Clear line item JSON from memory
#         self.line_item_json = None
#         logger.info("Cleared invoice_line_items.json from memory")

#         self.stdout.write(self.style.SUCCESS(f"Generation Summary: ({time.time() - start_time:.2f}s)"))
#         self.stdout.write(f" - Total invoices: {stats['total']}")
#         self.stdout.write(f" - Created: {stats['created']}")
#         self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
#         if stats['skipped']:
#             for skipped in stats['skipped'][:5]:
#                 self.stdout.write(f" - {skipped.get('invoice', skipped.get('entity'))}: {skipped['reason']}")
#             if len(stats['skipped']) > 5:
#                 self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
#         self.stdout.write(self.style.SUCCESS(f"Generation Completed in {time.time() - start_time:.2f}s"))
#         logger.info(f"Generation and Import Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
