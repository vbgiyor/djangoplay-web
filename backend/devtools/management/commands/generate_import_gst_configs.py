import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from invoices.constants import GST_RATE_TYPE_CHOICES, VALID_GST_RATES
from invoices.models.gst_configuration import GSTConfiguration
from invoices.services import validate_gst_configuration
from locations.models.custom_country import CustomCountry

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate and import GST configurations for all Indian states or a specific state to the database.
Example usage: ./manage.py generate_import_gst_configs --all
             or ./manage.py generate_import_gst_configs --code 23
"""

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Generate GST configs for all Indian states')
        parser.add_argument('--code', type=str, help='State code (e.g., 23 for Uttar Pradesh) to generate GST configs for')

    def handle(self, *args, **options):
        # Get user for audit fields
        Employee = get_user_model()
        try:
            user = Employee.objects.get(id=1)
            self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id})"))
            logger.info(f"Using employee: {user.username}")
        except Employee.DoesNotExist:
            error_msg = "Employee with id=1 not found. Please ensure user exists."
            self.stderr.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            return

        generate_all = options['all']
        state_code = options['code']

        if not (generate_all or state_code):
            self.stderr.write(self.style.ERROR("Must provide --all or --code"))
            logger.error("Must provide --all or --code")
            return

        try:
            country = CustomCountry.objects.get(country_code='IN')
        except CustomCountry.DoesNotExist:
            self.stderr.write(self.style.ERROR("Country IN not found"))
            logger.error("Country IN not found")
            return

        if state_code:
            regions = country.regions.filter(code=state_code, is_active=True)
            if not regions.exists():
                self.stderr.write(self.style.ERROR(f"No active region found for state code {state_code}"))
                logger.error(f"No active region found for state code {state_code}")
                return
            regions = list(regions.values('id', 'code', 'name'))
        else:
            regions = list(country.regions.filter(is_active=True).values('id', 'code', 'name'))
            if not regions:
                self.stderr.write(self.style.ERROR("No active regions found for country IN"))
                logger.error("No active regions found for country IN")
                return

        rate_types = [choice[0] for choice in GST_RATE_TYPE_CHOICES]
        effective_from = timezone.now().date()
        effective_to = effective_from + timedelta(days=365)
        gst_configs = []

        for region in regions:
            region_id = region['id']
            region_code = region['code']
            region_name = region['name']
            logger.debug(f"Processing region: {region_name} (ID: {region_id}, Code: {region_code})")

            for rate_type in rate_types:
                rates = [Decimal('0.00')] if rate_type in ['EXEMPT', 'ZERO_RATED'] else VALID_GST_RATES
                for rate in rates:
                    try:
                        if rate_type in ['EXEMPT', 'ZERO_RATED']:
                            cgst_rate = Decimal('0.00')
                            sgst_rate = Decimal('0.00')
                            igst_rate = Decimal('0.00')
                            description = f"{rate_type.title()} GST for {region_name}"
                        else:  # STANDARD rate type
                            if region_name.lower() != 'interstate' and region_id:  # Intra-state
                                cgst_rate = rate if rate in [Decimal('2.50'), Decimal('7.50'), Decimal('9.00'), Decimal('15.00')] else Decimal('9.00')
                                sgst_rate = cgst_rate
                                igst_rate = Decimal('0.00')
                                description = f"Standard GST for {region_name} at CGST {cgst_rate}% + SGST {sgst_rate}%"
                            else:  # Inter-state
                                cgst_rate = Decimal('0.00')
                                sgst_rate = Decimal('0.00')
                                igst_rate = rate if rate in [Decimal('18.00')] else Decimal('18.00')
                                description = f"Standard GST for {region_name} at IGST {igst_rate}%"

                        existing_db_config = GSTConfiguration.objects.filter(
                            rate_type=rate_type,
                            applicable_region_id=region_id,
                            is_active=True,
                            deleted_at__isnull=True
                        ).order_by('-cgst_rate', '-sgst_rate', '-igst_rate').first()
                        if existing_db_config:
                            if (existing_db_config.cgst_rate != cgst_rate or
                                existing_db_config.sgst_rate != sgst_rate or
                                existing_db_config.igst_rate != igst_rate):
                                logger.info(f"Soft deleting existing GST config {existing_db_config.id} due to rate mismatch")
                                existing_db_config.soft_delete(user=user)
                            else:
                                logger.info(f"Found existing GST config: {existing_db_config.description} (ID: {existing_db_config.id})")
                                existing_db_config.description = description
                                existing_db_config.effective_from = effective_from
                                existing_db_config.effective_to = effective_to
                                existing_db_config.updated_by = user
                                existing_db_config.save(user=user, skip_validation=False)
                                gst_configs.append({
                                    'id': existing_db_config.id,
                                    'description': existing_db_config.description,
                                    'rate_type': rate_type,
                                    'cgst_rate': str(existing_db_config.cgst_rate),
                                    'sgst_rate': str(existing_db_config.sgst_rate),
                                    'igst_rate': str(existing_db_config.igst_rate),
                                    'effective_from': effective_from.strftime('%Y-%m-%d'),
                                    'effective_to': effective_to.strftime('%Y-%m-%d'),
                                    'region_id': region_id
                                })
                                continue

                        config = GSTConfiguration(
                            description=description,
                            applicable_region_id=region_id,
                            effective_from=effective_from,
                            effective_to=effective_to,
                            rate_type=rate_type,
                            cgst_rate=cgst_rate,
                            sgst_rate=sgst_rate,
                            igst_rate=igst_rate,
                            created_by=user,
                            updated_by=user,
                            is_active=True,
                            deleted_at=None
                        )
                        validate_gst_configuration(config)
                        config.save(user=user, skip_validation=False)
                        logger.info(f"Saved GST config: {description} (ID: {config.id}, Region ID: {region_id})")
                        gst_configs.append({
                            'id': config.id,
                            'description': description,
                            'rate_type': rate_type,
                            'cgst_rate': str(cgst_rate),
                            'sgst_rate': str(sgst_rate),
                            'igst_rate': str(igst_rate),
                            'effective_from': effective_from.strftime('%Y-%m-%d'),
                            'effective_to': effective_to.strftime('%Y-%m-%d'),
                            'region_id': region_id
                        })
                    except Exception as e:
                        logger.error(f"Failed to create/fetch GST config for {rate_type} in region {region_name}: {str(e)}", exc_info=True)
                        raise

        self.stdout.write(self.style.SUCCESS(f"Generated and imported {len(gst_configs)} GST configs"))
        logger.info(f"Generated and imported {len(gst_configs)} GST configs")



# import logging
# import random
# from decimal import Decimal
# from django.core.management.base import BaseCommand
# from django.utils import timezone
# from datetime import timedelta
# from invoices.models.gst_configuration import GSTConfiguration
# from invoices.services import validate_gst_configuration
# from invoices.constants import GST_RATE_TYPE_CHOICES, VALID_GST_RATES
# from locations.models.custom_country import CustomCountry
# from django.contrib.auth import get_user_model

# logger = logging.getLogger(__name__)

# class Command(BaseCommand):
#     help = """Generate and import GST configurations for all Indian states or a specific state to the database.
# Example usage: ./manage.py generate_import_gst_configs --all
#              or ./manage.py generate_import_gst_configs --code 23
# """

#     def add_arguments(self, parser):
#         parser.add_argument('--all', action='store_true', help='Generate GST configs for all Indian states')
#         parser.add_argument('--code', type=str, help='State code (e.g., 23 for Uttar Pradesh) to generate GST configs for')

#     def handle(self, *args, **options):
#         # Get user for audit fields
#         Employee = get_user_model()
#         try:
#             user = Employee.objects.get(id=1)
#             self.stdout.write(self.style.SUCCESS(f"Using employee: {user.username} (ID: {user.id}))"))
#             logger.info(f"Using employee: {user.username}")
#         except Employee.DoesNotExist:
#             error_msg = f"Employee with id=1 not found. Please ensure user exists.)"
#             self.stderr.write(self.style.ERROR(error_msg))
#             logger.error(error_msg)
#             return

#         generate_all = options['all']
#         state_code = options['code']

#         if not (generate_all or state_code):
#             self.stderr.write(self.style.ERROR("Must provide --all or --code"))
#             logger.error("Must provide --all or --code")
#             return

#         try:
#             country = CustomCountry.objects.get(country_code='IN')
#         except CustomCountry.DoesNotExist:
#             self.stderr.write(self.style.ERROR("Country IN not found"))
#             logger.error("Country IN not found")
#             return

#         if state_code:
#             regions = country.regions.filter(code=state_code, is_active=True)
#             if not regions.exists():
#                 self.stderr.write(self.style.ERROR(f"No active region found for state code {state_code}"))
#                 logger.error(f"No active region found for state code {state_code}")
#                 return
#             regions = list(regions.values('id', 'code', 'name'))
#         else:
#             regions = list(country.regions.filter(is_active=True).values('id', 'code', 'name'))
#             if not regions:
#                 self.stderr.write(self.style.WARNING("No active regions found for country IN, using default codes"))
#                 logger.warning("No active regions found for country IN, using default codes")
#                 regions = [{'id': None, 'code': str(i).zfill(2), 'name': f"State {i:02d}"} for i in range(1, 38)]

#         regions.append({'id': None, 'code': None, 'name': 'Interstate'})
#         rate_types = [choice[0] for choice in GST_RATE_TYPE_CHOICES]
#         effective_from = timezone.now().date()
#         effective_to = effective_from + timedelta(days=365)
#         gst_configs = []

#         for region in regions:
#             region_id = region['id']
#             region_code = region['code'] if region['code'] else str(random.randint(1, 37)).zfill(2)
#             region_name = region['name'] if region['name'] else f"State {region_code}"
#             logger.debug(f"Processing region: {region_name} (ID: {region_id}, Code: {region_code})")

#             for rate_type in rate_types:
#                 rates = [Decimal('0.00')] if rate_type in ['EXEMPT', 'ZERO_RATED'] else ([Decimal('18.00')] if region_id is None else VALID_GST_RATES)
#                 for rate in rates:
#                     try:
#                         if rate_type in ['EXEMPT', 'ZERO_RATED']:
#                             cgst_rate = Decimal('0.00')
#                             sgst_rate = Decimal('0.00')
#                             igst_rate = Decimal('0.00')
#                             description = f"{rate_type.title()} GST for {region_name}"
#                         else:  # STANDARD rate type
#                             if region_id:  # Intra-state
#                                 cgst_rate = rate if rate in [Decimal('2.50'), Decimal('7.50'), Decimal('9.00'), Decimal('15.00')] else Decimal('9.00')
#                                 sgst_rate = cgst_rate
#                                 igst_rate = Decimal('0.00')
#                                 description = f"Standard GST for {region_name} at CGST {cgst_rate}% + SGST {sgst_rate}%"
#                             else:  # Inter-state
#                                 cgst_rate = Decimal('0.00')
#                                 sgst_rate = Decimal('0.00')
#                                 igst_rate = rate
#                                 description = f"Standard GST for {region_name} at IGST {igst_rate}%"

#                         existing_db_config = GSTConfiguration.objects.filter(
#                             applicable_region_id=region_id,
#                             rate_type=rate_type,
#                             effective_from__lte=effective_to,
#                             effective_to__gte=effective_from,
#                             is_active=True,
#                             deleted_at__isnull=True
#                         ).order_by('-cgst_rate', '-sgst_rate', '-igst_rate').first()
#                         if existing_db_config:
#                             if (existing_db_config.cgst_rate != cgst_rate or
#                                 existing_db_config.sgst_rate != sgst_rate or
#                                 existing_db_config.igst_rate != igst_rate):
#                                 logger.info(f"Soft deleting existing GST config {existing_db_config.id} due to rate mismatch")
#                                 existing_db_config.soft_delete(user=user)
#                             else:
#                                 logger.info(f"Found existing GST config: {existing_db_config.description} (ID: {existing_db_config.id})")
#                                 existing_db_config.description = description
#                                 existing_db_config.effective_from = effective_from
#                                 existing_db_config.effective_to = effective_to
#                                 existing_db_config.updated_by = user
#                                 existing_db_config.save(user=user, skip_validation=not region_id)
#                                 gst_configs.append({
#                                     'id': existing_db_config.id,
#                                     'description': existing_db_config.description,
#                                     'rate_type': rate_type,
#                                     'cgst_rate': str(existing_db_config.cgst_rate),
#                                     'sgst_rate': str(existing_db_config.sgst_rate),
#                                     'igst_rate': str(existing_db_config.igst_rate),
#                                     'effective_from': effective_from.strftime('%Y-%m-%d'),
#                                     'effective_to': effective_to.strftime('%Y-%m-%d'),
#                                     'region_id': region_id
#                                 })
#                                 continue

#                         config = GSTConfiguration(
#                             description=description,
#                             applicable_region_id=region_id,
#                             effective_from=effective_from,
#                             effective_to=effective_to,
#                             rate_type=rate_type,
#                             cgst_rate=cgst_rate,
#                             sgst_rate=sgst_rate,
#                             igst_rate=igst_rate,
#                             created_by=user,
#                             updated_by=user,
#                             is_active=True,
#                             deleted_at=None
#                         )
#                         validate_gst_configuration(config)
#                         config.save(user=user, skip_validation=not region_id)
#                         logger.info(f"Saved GST config: {description} (ID: {config.id}, Region ID: {region_id if region_id else 'None'})")
#                         gst_configs.append({
#                             'id': config.id,
#                             'description': description,
#                             'rate_type': rate_type,
#                             'cgst_rate': str(cgst_rate),
#                             'sgst_rate': str(sgst_rate),
#                             'igst_rate': str(igst_rate),
#                             'effective_from': effective_from.strftime('%Y-%m-%d'),
#                             'effective_to': effective_to.strftime('%Y-%m-%d'),
#                             'region_id': region_id
#                         })
#                     except Exception as e:
#                         logger.error(f"Failed to create/fetch GST config for {rate_type} in region {region_name}: {str(e)}", exc_info=True)
#                         raise

#         self.stdout.write(self.style.SUCCESS(f"Generated and imported {len(gst_configs)} GST configs"))
#         logger.info(f"Generated and imported {len(gst_configs)} GST configs")
