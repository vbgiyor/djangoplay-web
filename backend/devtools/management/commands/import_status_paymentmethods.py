import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone
from invoices.constants import INVOICE_STATUS_CODES, PAYMENT_METHOD_CODES
from invoices.exceptions import InvoiceValidationError
from invoices.models.payment_method import PaymentMethod
from invoices.models.status import Status
from invoices.services.status import cache_status, validate_status

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Create or update Status and PaymentMethod data in the database.
Example usage:
  - ./manage.py import_status_paymentmethods.py --status
  - ./manage.py import_status_paymentmethods.py --payment_methods
  - ./manage.py import_status_paymentmethods.py [--all]
"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            action='store_true',
            help='Process only invoice status data.'
        )
        parser.add_argument(
            '--payment_methods',
            action='store_true',
            help='Process only payment method data.'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process both status and payment method data (default).'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        User = get_user_model()
        try:
            admin_user = User.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using user: {admin_user.username}"))
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR("User with id=1 not found"))
            logger.error("User with id=1 not found")
            return

        # Determine what to process based on arguments
        process_status = options['status'] or options['all'] or not (options['status'] or options['payment_methods'])
        process_payment_methods = options['payment_methods'] or options['all'] or not (options['status'] or options['payment_methods'])

        stats = {
            'status': {'created': 0, 'updated': 0, 'skipped': []},
            'payment_method': {'created': 0, 'updated': 0, 'skipped': []}
        }

        with transaction.atomic():
            if process_status:
                self.stdout.write(self.style.SUCCESS("Processing status data..."))
                logger.info("Processing status data")
                set(Status.objects.filter(is_active=True, deleted_at__isnull=True).values_list('code', flat=True))
                set(Status.objects.filter(is_active=True, deleted_at__isnull=True).values_list('name', flat=True))
                status_id = Status.objects.count() + 1 if Status.objects.exists() else 1

                for code, name in INVOICE_STATUS_CODES.items():
                    try:
                        existing_status = Status.objects.filter(
                            models.Q(code__iexact=code) | models.Q(name__iexact=name),
                            is_active=True,
                            deleted_at__isnull=True
                        ).first()
                        if existing_status:
                            updated = False
                            if existing_status.name != name or existing_status.is_default != (code == 'DRAFT') or existing_status.is_locked != (code in ['PAID', 'CANCELLED']):
                                existing_status.name = name
                                existing_status.is_default = (code == 'DRAFT')
                                existing_status.is_locked = (code in ['PAID', 'CANCELLED'])
                                updated = True
                            try:
                                existing_status.updated_by = admin_user
                                validate_status(existing_status, exclude_pk=existing_status.id)
                                existing_status.save(user=admin_user)
                                cache_status(existing_status)
                                if updated:
                                    stats['status']['updated'] += 1
                                    logger.info(f"Updated Status {code} (ID: {existing_status.id})")
                                    self.stdout.write(self.style.SUCCESS(f"Updated Status {code} (ID: {existing_status.id})"))
                                else:
                                    stats['status']['skipped'].append({
                                        'code': code,
                                        'reason': 'No changes detected'
                                    })
                                    logger.info(f"Skipped unchanged Status {code}")
                                    self.stdout.write(self.style.WARNING(f"Skipped unchanged Status {code}"))
                            except InvoiceValidationError as e:
                                stats['status']['skipped'].append({
                                    'code': code,
                                    'reason': str(e)
                                })
                                logger.warning(f"Failed to update Status {code}: {str(e)}")
                                self.stdout.write(self.style.WARNING(f"Failed to update Status {code}: {str(e)}"))
                            continue

                        temp_status = Status(
                            id=status_id,
                            code=code,
                            name=name,
                            is_active=True,
                            is_default=(code == 'DRAFT'),
                            is_locked=(code in ['PAID', 'CANCELLED']),
                            created_by=admin_user,
                            updated_by=admin_user,
                            created_at=timezone.now(),
                            updated_at=timezone.now()
                        )

                        validate_status(temp_status)
                        temp_status.save(user=admin_user)
                        cache_status(temp_status)
                        stats['status']['created'] += 1
                        logger.info(f"Created Status {code} (ID: {status_id})")
                        self.stdout.write(self.style.SUCCESS(f"Created Status {code} (ID: {status_id})"))
                        status_id += 1

                    except InvoiceValidationError as e:
                        stats['status']['skipped'].append({
                            'code': code,
                            'reason': str(e)
                        })
                        logger.warning(f"Failed to create/update Status {code}: {str(e)}")
                        self.stdout.write(self.style.WARNING(f"Failed to create/update Status {code}: {str(e)}"))
                        continue
                    except Exception as e:
                        stats['status']['skipped'].append({
                            'code': code,
                            'reason': str(e)
                        })
                        logger.error(f"Failed to create/update Status {code}: {str(e)}", exc_info=True)
                        self.stdout.write(self.style.ERROR(f"Failed to create/update Status {code}: {str(e)}"))
                        continue

            if process_payment_methods:
                self.stdout.write(self.style.SUCCESS("Processing payment method data..."))
                logger.info("Processing payment method data")
                payment_method_id = PaymentMethod.objects.count() + 1 if PaymentMethod.objects.exists() else 1

                for code, name in PAYMENT_METHOD_CODES.items():
                    try:
                        existing_method = PaymentMethod.objects.filter(
                            code=code,
                            is_active=True,
                            deleted_at__isnull=True
                        ).first()

                        if existing_method:
                            updated = False
                            if existing_method.name != name or existing_method.description != f"{name} payment method":
                                existing_method.name = name
                                existing_method.description = f"{name} payment method"
                                updated = True
                            if updated:
                                existing_method.updated_by = admin_user
                                existing_method.save(user=admin_user)
                                stats['payment_method']['updated'] += 1
                                logger.info(f"Updated PaymentMethod {code} (ID: {existing_method.id})")
                                self.stdout.write(self.style.SUCCESS(f"Updated PaymentMethod {code} (ID: {existing_method.id})"))
                            else:
                                stats['payment_method']['skipped'].append({
                                    'code': code,
                                    'reason': 'No changes detected'
                                })
                                logger.info(f"Skipped unchanged PaymentMethod {code}")
                                self.stdout.write(self.style.WARNING(f"Skipped unchanged PaymentMethod {code}"))
                            continue

                        temp_method = PaymentMethod(
                            id=payment_method_id,
                            code=code,
                            name=name,
                            description=f"{name} payment method",
                            is_active=True,
                            created_by=admin_user,
                            updated_by=admin_user,
                            created_at=timezone.now(),
                            updated_at=timezone.now()
                        )

                        temp_method.clean()
                        temp_method.save(user=admin_user)
                        stats['payment_method']['created'] += 1
                        logger.info(f"Created PaymentMethod {code} (ID: {payment_method_id})")
                        self.stdout.write(self.style.SUCCESS(f"Created PaymentMethod {code} (ID: {payment_method_id})"))
                        payment_method_id += 1

                    except InvoiceValidationError as e:
                        stats['payment_method']['skipped'].append({
                            'code': code,
                            'reason': str(e)
                        })
                        logger.warning(f"Failed to create/update PaymentMethod {code}: {str(e)}")
                        self.stdout.write(self.style.WARNING(f"Failed to create/update PaymentMethod {code}: {str(e)}"))
                        continue
                    except Exception as e:
                        stats['payment_method']['skipped'].append({
                            'code': code,
                            'reason': str(e)
                        })
                        logger.error(f"Failed to create/update PaymentMethod {code}: {str(e)}", exc_info=True)
                        self.stdout.write(self.style.ERROR(f"Failed to create/update PaymentMethod {code}: {str(e)}"))
                        continue

        total_created = sum(stats[model]['created'] for model in stats)
        total_updated = sum(stats[model]['updated'] for model in stats)
        total_skipped = sum(len(stats[model]['skipped']) for model in stats)

        self.stdout.write(self.style.SUCCESS(f"Import Summary: ({(timezone.now() - start_time).total_seconds():.2f}s)"))
        for model in stats:
            self.stdout.write(f"  - {model.replace('_', ' ').title()}:")
            self.stdout.write(f"    - Created: {stats[model]['created']}")
            self.stdout.write(f"    - Updated: {stats[model]['updated']}")
            self.stdout.write(f"    - Skipped: {len(stats[model]['skipped'])}")
            if stats[model]['skipped']:
                for skipped in stats[model]['skipped'][:5]:
                    self.stdout.write(f"      - {skipped.get('code', 'Unknown')}: {skipped['reason']}")
                if len(stats[model]['skipped']) > 5:
                    self.stdout.write(f"      - ... and {len(stats[model]['skipped']) - 5} more skipped")
        self.stdout.write(self.style.SUCCESS(f"Total Created: {total_created}, Total Updated: {total_updated}, Total Skipped: {total_skipped}"))
        self.stdout.write(self.style.SUCCESS(f"Processing completed in {(timezone.now() - start_time).total_seconds():.2f}s"))
        logger.info(f"Import Summary: Total Created={total_created}, Total Updated={total_updated}, Total Skipped={total_skipped}")
