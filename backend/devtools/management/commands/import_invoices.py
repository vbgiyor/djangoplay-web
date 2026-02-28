import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from entities.models.entity import Entity
from invoices.models.billing_schedule import BillingSchedule
from invoices.models.invoice import Invoice
from invoices.models.line_item import LineItem
from invoices.models.payment import Payment
from invoices.models.payment_method import PaymentMethod
from utilities.utils.data_sync.load_env_and_paths import load_env_paths

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Import invoice data for specified entity or all entities in a country from JSON in INVOICES_JSON/{COUNTRY_CODE} directory.
Expected .env keys: DATA_DIR, INVOICES_JSON
Example usage: ./manage.py invimp --entity entity-slug
             or ./manage.py import_invoices --all --country NZ
             or ./manage.py import_invoices --country IN
JSON files are read from INVOICES_JSON/{COUNTRY_CODE}/{entity-slug}.json
"""

    def add_arguments(self, parser):
        parser.add_argument('--entity', type=str, help='Slug of the entity to import invoices for')
        parser.add_argument('--all', action='store_true', help='Import invoices for all entities in the specified country')
        parser.add_argument('--country', type=str, help='Country code (e.g., IN, NZ) to filter entities')

    def import_invoice(self, invoice_data, admin_user):
        """Import a single invoice and its related objects."""
        logger.debug(f"Importing invoice {invoice_data['invoice_number']}")

        with transaction.atomic():
            invoice = Invoice(
                id=invoice_data['id'],
                issuer_id=invoice_data['issuer_id'],
                recipient_id=invoice_data['recipient_id'],
                billing_address_id=invoice_data['billing_address_id'],
                billing_country_id=invoice_data['billing_country_id'],
                billing_region_id=invoice_data['billing_region_id'],
                status_id=invoice_data['status_id'],
                invoice_number=invoice_data['invoice_number'],
                description=invoice_data['description'],
                issue_date=datetime.fromisoformat(invoice_data['issue_date']).date(),
                due_date=datetime.fromisoformat(invoice_data['due_date']).date(),
                payment_terms=invoice_data['payment_terms'],
                currency=invoice_data['currency'],
                base_amount=Decimal(invoice_data['base_amount']),
                total_amount=Decimal(invoice_data['total_amount']),
                cgst_rate=Decimal(invoice_data['cgst_rate']) if invoice_data['cgst_rate'] not in (None, 'None') else None,
                sgst_rate=Decimal(invoice_data['sgst_rate']) if invoice_data['sgst_rate'] not in (None, 'None') else None,
                igst_rate=Decimal(invoice_data['igst_rate']) if invoice_data['igst_rate'] not in (None, 'None') else None,
                cgst_amount=Decimal(invoice_data['cgst_amount']),
                sgst_amount=Decimal(invoice_data['sgst_amount']),
                igst_amount=Decimal(invoice_data['igst_amount']),
                tax_exemption_status=invoice_data['tax_exemption_status'],
                issuer_gstin=invoice_data['issuer_gstin'],
                recipient_gstin=invoice_data['recipient_gstin'],
                created_by=admin_user,
                updated_by=admin_user,
                created_at=datetime.fromisoformat(invoice_data['created_at']),
                updated_at=datetime.fromisoformat(invoice_data['updated_at']),
                is_active=invoice_data['is_active']
            )

            try:
                # Skip total calculation during import since line items come after
                invoice.save(user=admin_user, skip_validation=True)
                logger.info(f"Saved invoice {invoice.invoice_number}")
            except Exception as e:
                logger.error(f"Unexpected error saving invoice {invoice_data['invoice_number']}: {str(e)}", exc_info=True)
                raise

        return invoice

    def import_line_item(self, line_item_data, invoice, admin_user):
        """Import a single line item for an invoice."""
        logger.debug(f"Importing line item {line_item_data['description']} for invoice {invoice.invoice_number}")

        with transaction.atomic():
            line_item = LineItem(
                id=line_item_data['id'],
                invoice=invoice,
                description=line_item_data['description'],
                hsn_sac_code=line_item_data['hsn_sac_code'],
                quantity=Decimal(line_item_data['quantity']),
                unit_price=Decimal(line_item_data['unit_price']),
                discount=Decimal(line_item_data['discount']),
                cgst_rate=Decimal(line_item_data['cgst_rate']) if line_item_data['cgst_rate'] not in (None, 'None') else None,
                sgst_rate=Decimal(line_item_data['sgst_rate']) if line_item_data['sgst_rate'] not in (None, 'None') else None,
                igst_rate=Decimal(line_item_data['igst_rate']) if line_item_data['igst_rate'] not in (None, 'None') else None,
                cgst_amount=Decimal(line_item_data['cgst_amount']),
                sgst_amount=Decimal(line_item_data['sgst_amount']),
                igst_amount=Decimal(line_item_data['igst_amount']),
                total_amount=Decimal(line_item_data['total_amount']),
                created_by=admin_user,
                updated_by=admin_user,
                created_at=datetime.fromisoformat(line_item_data['created_at']) if 'created_at' in line_item_data else timezone.now(),
                updated_at=datetime.fromisoformat(line_item_data['updated_at']) if 'updated_at' in line_item_data else timezone.now(),
                is_active=line_item_data['is_active']
            )

            try:
                line_item.save(user=admin_user, skip_validation=True)
                logger.info(f"Saved line item {line_item.description} for invoice {invoice.invoice_number}")
            except Exception as e:
                logger.error(f"Unexpected error saving line item {line_item_data['description']}: {str(e)}", exc_info=True)
                raise

    def import_billing_schedule(self, billing_schedule_data, admin_user):
        """Import a single billing schedule."""
        logger.debug(f"Importing billing schedule {billing_schedule_data['description']}")

        with transaction.atomic():
            billing_schedule = BillingSchedule(
                id=billing_schedule_data['id'],
                entity_id=billing_schedule_data['entity_id'],
                description=billing_schedule_data['description'],
                start_date=datetime.fromisoformat(billing_schedule_data['start_date']).date(),
                next_billing_date=datetime.fromisoformat(billing_schedule_data['next_billing_date']).date(),
                end_date=datetime.fromisoformat(billing_schedule_data['end_date']).date() if billing_schedule_data['end_date'] else None,
                amount=Decimal(billing_schedule_data['amount']),
                frequency=billing_schedule_data['frequency'],
                status=billing_schedule_data['status'],
                created_by=admin_user,
                updated_by=admin_user,
                created_at=datetime.fromisoformat(billing_schedule_data['created_at']),
                updated_at=datetime.fromisoformat(billing_schedule_data['updated_at']),
                is_active=billing_schedule_data['is_active']
            )

            try:
                billing_schedule.save(user=admin_user, skip_validation=True)
                logger.info(f"Saved billing schedule {billing_schedule.description}")
            except Exception as e:
                logger.error(f"Unexpected error saving billing schedule {billing_schedule_data['description']}: {str(e)}", exc_info=True)
                raise

    def import_payment(self, payment_data, admin_user):
        """Import a single payment."""
        logger.debug(f"Importing payment {payment_data['payment_reference']}")

        with transaction.atomic():
            invoice = Invoice.objects.get(invoice_number=payment_data['invoice.invoice_number'], is_active=True)
            payment_method = PaymentMethod.objects.get(code=payment_data['payment_method_code'], is_active=True)
            payment = Payment(
                id=payment_data['id'],
                invoice=invoice,
                amount=Decimal(payment_data['amount']),
                payment_date=datetime.fromisoformat(payment_data['payment_date']).date(),
                payment_method=payment_method,
                payment_reference=payment_data['payment_reference'],
                status=payment_data['status'],
                created_by=admin_user,
                updated_by=admin_user,
                created_at=datetime.fromisoformat(payment_data['created_at']) if 'created_at' in payment_data else timezone.now(),
                updated_at=datetime.fromisoformat(payment_data['updated_at']) if 'updated_at' in payment_data else timezone.now(),
                is_active=payment_data['is_active']
            )

            try:
                payment.save(user=admin_user, skip_validation=True)
                logger.info(f"Saved payment {payment.payment_reference}")
            except Exception as e:
                logger.error(f"Unexpected error saving payment {payment_data['payment_reference']}: {str(e)}", exc_info=True)
                raise

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
        env_data = load_env_paths(env_var='INVOICES_JSON', require_exists=False)
        invoices_path = env_data.get('INVOICES_JSON')
        if not invoices_path:
            self.stderr.write(self.style.ERROR("INVOICES_JSON not defined in .env"))
            logger.error("INVOICES_JSON not defined")
            return

        country_code = options.get('country')
        entities = Entity.objects.filter(is_active=True)
        if country_code:
            entities = entities.filter(default_address__city__subregion__region__country__country_code=country_code.upper())

        if options['all'] and options['entity']:
            self.stderr.write(self.style.ERROR("Cannot use --all and --entity together"))
            logger.error("Cannot use --all and --entity together")
            return

        if options['entity']:
            entity_slug = options['entity']
            try:
                entities = Entity.objects.filter(slug=entity_slug, is_active=True)
                if country_code:
                    entities = entities.filter(default_address__city__subregion__region__country__country_code=country_code.upper())
            except Entity.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Entity with slug {entity_slug} not found"))
                logger.error(f"Entity with slug {entity_slug} not found")
                return

        if not entities.exists():
            self.stderr.write(self.style.ERROR("No active entities found" + (f" for country {country_code}" if country_code else "")))
            logger.error("No active entities found" + (f" for country {country_code}" if country_code else ""))
            return

        for entity in entities:
            entity_slug = entity.slug
            entity_country_code = entity.default_address.city.subregion.region.country.country_code if entity.default_address and entity.default_address.city else 'UNKNOWN'
            invoices_json = str(Path(invoices_path) / entity_country_code / f"{entity_slug}.json")
            self.stdout.write(f"Importing invoices for entity: {entity.name} ({entity_slug}) in {entity_country_code}")
            logger.info(f"Importing invoices for entity {entity.name} in {entity_country_code}")

            try:
                with open(invoices_json, encoding='utf-8') as f:
                    json_data = json.load(f)
            except FileNotFoundError:
                self.stderr.write(self.style.ERROR(f"JSON file not found: {invoices_json}"))
                logger.error(f"JSON file not found: {invoices_json}")
                continue
            except json.JSONDecodeError as e:
                self.stderr.write(self.style.ERROR(f"Invalid JSON in {invoices_json}: {str(e)}"))
                logger.error(f"Invalid JSON in {invoices_json}: {str(e)}")
                continue

            for invoice_data in json_data.get('invoice', []):
                stats['total'] += 1
                try:
                    invoice = self.import_invoice(invoice_data, admin_user)
                    stats['created'] += 1
                    for line_item_data in json_data.get('line_item', []):
                        if line_item_data['invoice.invoice_number'] == invoice_data['invoice_number']:
                            self.import_line_item(line_item_data, invoice, admin_user)
                    for billing_schedule_data in json_data.get('billing_schedule', []):
                        if billing_schedule_data['description'].startswith(f"Billing Schedule for Invoice {invoice_data['invoice_number']}"):
                            self.import_billing_schedule(billing_schedule_data, admin_user)
                    for payment_data in json_data.get('payment', []):
                        if payment_data['invoice.invoice_number'] == invoice_data['invoice_number']:
                            self.import_payment(payment_data, admin_user)
                    logger.info(f"Successfully imported invoice {invoice_data['invoice_number']} for entity {entity_slug}")
                except Exception as e:
                    error_details = {'invoice': invoice_data['invoice_number'], 'reason': str(e), 'entity': entity_slug}
                    stats['skipped'].append(error_details)
                    logger.error(f"Skipping invoice {invoice_data['invoice_number']} for {entity_slug}: {str(e)}", extra={'details': error_details})

        self.stdout.write(self.style.SUCCESS(f"Import Summary: ({time.time() - start_time:.2f}s)"))
        self.stdout.write(f" - Total invoices: {stats['total']}")
        self.stdout.write(f" - Created: {stats['created']}")
        self.stdout.write(f" - Skipped: {len(stats['skipped'])}")
        if stats['skipped']:
            for skipped in stats['skipped'][:5]:
                self.stdout.write(f" - {skipped['invoice']}: {skipped['reason']}")
            if len(stats['skipped']) > 5:
                self.stdout.write(f" - ... and {len(stats['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Import Completed in {time.time() - start_time:.2f}s"))
        logger.info(f"Import Summary: Total={stats['total']}, Created={stats['created']}, Skipped={len(stats['skipped'])}")
