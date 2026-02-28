import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

import redis
from core.utils.redis_client import redis_client
from django.db import transaction
from django.utils import timezone
from utilities.utils.general.normalize_text import normalize_text

from invoices.constants import DESCRIPTION_MAX_LENGTH, VALID_GST_RATES
from invoices.exceptions import GSTValidationError, InvoiceValidationError

logger = logging.getLogger(__name__)

@transaction.atomic
def fetch_gst_config(region_id: int = None, issue_date=None, rate_type: str = None, exempt_zero_rated: bool = None) -> dict:
    """Fetch GST configuration from Redis or database, with robust default rates."""
    logger.debug(f"Fetching GST config: region_id={region_id}, issue_date={issue_date}, rate_type={rate_type}, exempt_zero_rated={exempt_zero_rated}")
    from locations.models import CustomRegion

    from invoices.models.gst_configuration import GSTConfiguration
    try:
        # Ensure issue_date is a date object
        if issue_date and not isinstance(issue_date, datetime | date):
            logger.warning(f"Invalid issue_date type: {type(issue_date)}. Converting to date.")
            issue_date = timezone.now().date()

        cache_region_id = str(region_id) if region_id is not None else "none"
        cache_key = f"gst_config:{cache_region_id}:{issue_date.strftime('%Y%m%d') if issue_date else 'none'}:{rate_type or 'none'}:{'true' if exempt_zero_rated else 'false'}"
        try:
            cached_config = redis_client.get(cache_key)
            if cached_config:
                logger.debug(f"Cache hit for GST config: {cache_key}")
                return json.loads(cached_config)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for GST config: {str(e)}")

        query = GSTConfiguration.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        )

        # Handle region_id explicitly
        if region_id is not None:
            query = query.filter(applicable_region_id=region_id)
        else:
            query = query.filter(applicable_region_id__isnull=True)

        if issue_date:
            query = query.filter(
                effective_from__lte=issue_date,
                effective_to__gte=issue_date
            )

        if rate_type:
            query = query.filter(rate_type=rate_type)
        elif exempt_zero_rated is True:
            query = query.filter(rate_type__in=['EXEMPT', 'ZERO_RATED'])

        config = query.select_related('applicable_region').first()

        if not config:
            logger.warning(f"No GSTConfiguration found for region={region_id}, rate_type={rate_type}, exempt_zero_rated={exempt_zero_rated}, issue_date={issue_date}")
            # Create a new GSTConfiguration
            from django.contrib.auth import get_user_model

            from invoices.models.gst_configuration import GSTConfiguration
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                logger.error("No superuser found for creating default GST configuration")
                raise GSTValidationError(
                    message="No superuser found for creating default GST configuration",
                    code="no_admin_user",
                    details={"region_id": region_id, "issue_date": str(issue_date)}
                )

            region = CustomRegion.objects.filter(id=region_id, is_active=True).first() if region_id else None
            default_rate_type = rate_type or ('EXEMPT' if exempt_zero_rated else 'STANDARD')
            description = f"{default_rate_type.title()} GST for {'Interstate' if not region else region.name}"

            if rate_type in ['EXEMPT', 'ZERO_RATED'] or exempt_zero_rated:
                cgst_rate = Decimal('0.00')
                sgst_rate = Decimal('0.00')
                igst_rate = Decimal('0.00')
            else:
                if region:
                    cgst_rate = Decimal('9.00')
                    sgst_rate = Decimal('9.00')
                    igst_rate = Decimal('0.00')
                else:
                    cgst_rate = Decimal('0.00')
                    sgst_rate = Decimal('0.00')
                    igst_rate = Decimal('18.00')

            config = GSTConfiguration(
                description=description,
                applicable_region_id=region_id,
                effective_from=issue_date or timezone.now().date(),
                effective_to=(issue_date or timezone.now().date()) + timedelta(days=365),
                rate_type=default_rate_type,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                created_by=admin_user,
                updated_by=admin_user,
                is_active=True
            )
        else:
            # Use config values, converting None to Decimal('0.00')
            cgst_rate = Decimal(str(config.cgst_rate)) if config.cgst_rate is not None else Decimal('0.00')
            sgst_rate = Decimal(str(config.sgst_rate)) if config.sgst_rate is not None else Decimal('0.00')
            igst_rate = Decimal(str(config.igst_rate)) if config.igst_rate is not None else Decimal('0.00')
            default_rate_type = config.rate_type

        config_data = {
            # 'id': str(config.id) if config else None,  # Ensure ID is a string
            'description': config.description if config else description,
            'cgst_rate': str(cgst_rate),
            'sgst_rate': str(sgst_rate),
            'igst_rate': str(igst_rate),
            'rate_type': default_rate_type,
            'region_id': region_id,
            'effective_from': (issue_date or config.effective_from).strftime('%Y-%m-%d') if (issue_date or config.effective_from) else None,
            'effective_to': config.effective_to.strftime('%Y-%m-%d') if config and config.effective_to else (issue_date or timezone.now().date() + timedelta(days=365)).strftime('%Y-%m-%d'),
        }

        try:
            redis_client.setex(cache_key, 3600, json.dumps(config_data))
            logger.info(f"Cached GST config: {cache_key}")
        except redis.RedisError as e:
            logger.warning(f"Failed to cache GST config: {str(e)}")

        logger.info(f"Fetched GST config: {config_data}")
        return config_data
    except Exception as e:
        logger.error(f"Error fetching GST config: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to fetch GST configuration: {str(e)}",
            code="gst_config_fetch_error",
            details={"region_id": region_id, "issue_date": str(issue_date), "rate_type": rate_type}
        )

@transaction.atomic
def entity_from_gstin(gstin: str, issue_date=None) -> dict:
    """
    Retrieve entity and tax profile data for a given GSTIN.

    Args:
        gstin (str): The GSTIN to query.
        issue_date (date, optional): The date to check for active status.

    Returns:
        dict: Contains entity ID, GSTIN, tax profile ID, billing region, and country IDs.

    Raises:
        GSTValidationError: If the GSTIN is invalid or no active entity is found.

    """
    from entities.models import Entity
    from fincore.models import TaxProfile
    try:
        if not isinstance(gstin, str):
            raise GSTValidationError(
                message="GSTIN must be a string.",
                code="invalid_gstin",
                details={"field": "gstin"}
            )

        cache_key = f"gstin:{gstin}"
        try:
            cached_entity = redis_client.get(cache_key)
            if cached_entity:
                return json.loads(cached_entity)
        except redis.RedisError as e:
            logger.warning(f"Redis cache miss for GSTIN {gstin}: {str(e)}")

        # Query TaxProfile for GSTIN
        tax_profile = TaxProfile.objects.filter(
            tax_identifier_type='GSTIN',
            tax_identifier=gstin,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('entity_mapping').first()
        if not tax_profile or not tax_profile.entity_mapping:
            raise GSTValidationError(
                message="No active entity mapping found with the provided GSTIN.",
                code="invalid_gstin",
                details={"gstin": gstin}
            )

        # Fetch Entity using entity_mapping
        entity_mapping = tax_profile.entity_mapping
        if entity_mapping.entity_type != 'entities.Entity':
            raise GSTValidationError(
                message="Entity mapping does not correspond to an Entity.",
                code="invalid_entity_type",
                details={"entity_type": entity_mapping.entity_type, "gstin": gstin}
            )

        entity = Entity.objects.filter(
            id=entity_mapping.entity_id,
            is_active=True,
            deleted_at__isnull=True
        ).first()
        if not entity:
            raise GSTValidationError(
                message="No active entity found for the provided GSTIN.",
                code="inactive_entity",
                details={"gstin": gstin, "entity_id": entity_mapping.entity_id}
            )

        entity_data = {
            'id': entity.id,
            'gstin': gstin,
            'tax_profile_id': tax_profile.id,
            'billing_region_id': tax_profile.region_id,
            'billing_country_id': tax_profile.country_id
        }

        try:
            redis_client.setex(cache_key, 3600, json.dumps(entity_data))
        except redis.RedisError as e:
            logger.warning(f"Failed to cache entity data: {str(e)}")

        logger.info(f"Fetched entity for GSTIN {gstin}: Entity ID {entity.id}")
        return entity_data
    except Exception as e:
        logger.error(f"Failed to fetch entity for GSTIN {gstin}: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to fetch entity: {str(e)}",
            code="gstin_fetch_error",
            details={"error": str(e)}
        )

@transaction.atomic
def is_interstate_transaction(buyer_gstin: str = None, seller_gstin: str = None, billing_region_id: int = None, billing_country_id: int = None, issuer=None, recipient=None, issue_date=None) -> bool:
    """
    Determine if the transaction is interstate based on GSTIN, region, or entity data.

    Args:
        buyer_gstin (str, optional): GSTIN of the buyer.
        seller_gstin (str, optional): GSTIN of the seller.
        billing_region_id (int, optional): ID of the billing region.
        billing_country_id (int, optional): ID of the billing country.
        issuer (Entity, optional): Issuer entity object.
        recipient (Entity, optional): Recipient entity object.
        issue_date (date, optional): Date of the transaction.

    Returns:
        bool: True if the transaction is interstate, False otherwise.

    Raises:
        GSTValidationError: If validation fails or required data is missing/invalid.

    """
    logger.debug(f"Checking if transaction is interstate: buyer_gstin={buyer_gstin}, seller_gstin={seller_gstin}, billing_region_id={billing_region_id}, billing_country_id={billing_country_id}, issuer={issuer}, recipient={recipient}")
    try:
        from entities.models import Entity  # Local import to avoid circular dependency
        from locations.models import CustomCountry, CustomRegion
        from utilities.utils.entities.entity_validations import validate_gstin

        from invoices.models.invoice import Invoice

        # Validate issue_date
        if issue_date and not isinstance(issue_date, datetime | date):
            raise GSTValidationError(
                message="Issue date must be a valid date object.",
                code="invalid_issue_date",
                details={"issue_date": str(issue_date)}
            )
        issue_date = issue_date.date() if isinstance(issue_date, datetime) else issue_date or timezone.now().date()

        # Validate billing_country_id
        if not billing_country_id:
            raise GSTValidationError(
                message="Billing country ID is required to determine transaction type.",
                code="missing_billing_country",
                details={"field": "billing_country_id"}
            )

        country = CustomCountry.objects.filter(id=billing_country_id, is_active=True).first()
        if not country:
            raise GSTValidationError(
                message="Billing country must be active.",
                code="invalid_billing_country",
                details={"field": "billing_country_id", "value": billing_country_id}
            )

        if country.country_code.upper() != 'IN':
            logger.debug("Non-India transaction, returning False for interstate check")
            return False

        # Use provided issuer and recipient if available, otherwise fetch from GSTIN
        if buyer_gstin and not recipient:
            recipient_data = entity_from_gstin(buyer_gstin, issue_date)
            recipient = Entity.objects.filter(id=recipient_data['id'], is_active=True, deleted_at__isnull=True).first()
            if not recipient:
                raise GSTValidationError(
                    message="No active recipient entity found for provided GSTIN.",
                    code="inactive_recipient",
                    details={"buyer_gstin": buyer_gstin}
                )
        if seller_gstin and not issuer:
            issuer_data = entity_from_gstin(seller_gstin, issue_date)
            issuer = Entity.objects.filter(id=issuer_data['id'], is_active=True, deleted_at__isnull=True).first()
            if not issuer:
                raise GSTValidationError(
                    message="No active issuer entity found for provided GSTIN.",
                    code="inactive_issuer",
                    details={"seller_gstin": seller_gstin}
                )

        # Case 1: Billing region provided (prioritize for Indian transactions)
        if billing_region_id:
            region = CustomRegion.objects.filter(id=billing_region_id, is_active=True).first()
            if not region:
                raise GSTValidationError(
                    message="Billing region must be active.",
                    code="invalid_billing_region",
                    details={"field": "billing_region_id", "value": billing_region_id}
                )
            if region.country.country_code.upper() == 'IN':
                logger.debug(f"Billing region {billing_region_id} provided, marking this as intrastate for Indian transaction")
                return False  # Prioritize billing region, assume intrastate

        # Case 2: Both GSTINs provided
        if buyer_gstin and seller_gstin:
            validate_gstin(buyer_gstin)
            validate_gstin(seller_gstin)
            if issuer and recipient:
                # Validate GSTINs against entity default addresses
                if issuer.default_address and issuer.default_address.city and issuer.default_address.city.subregion and issuer.default_address.city.subregion.region:
                    issuer_state_code = issuer.default_address.city.subregion.region.code
                    if seller_gstin[:2] != issuer_state_code:
                        raise GSTValidationError(
                            message="Seller GSTIN state code does not match issuer's default address state.",
                            code="seller_gstin_address_mismatch",
                            details={"seller_gstin": seller_gstin, "issuer_state": issuer_state_code}
                        )
                if recipient.default_address and recipient.default_address.city and recipient.default_address.city.subregion and recipient.default_address.city.subregion.region:
                    recipient_state_code = recipient.default_address.city.subregion.region.code
                    if buyer_gstin[:2] != recipient_state_code:
                        raise GSTValidationError(
                            message="Buyer GSTIN state code does not match recipient's default address state.",
                            code="buyer_gstin_address_mismatch",
                            details={"buyer_gstin": buyer_gstin, "recipient_state": recipient_state_code}
                        )
            logger.debug(f"Checking GSTIN states: buyer={buyer_gstin[:2]}, seller={seller_gstin[:2]}")
            return buyer_gstin[:2] != seller_gstin[:2]

        # Case 3: Seller GSTIN and no billing region
        if seller_gstin:
            validate_gstin(seller_gstin)
            if issuer and issuer.default_address and issuer.default_address.city and issuer.default_address.city.subregion and issuer.default_address.city.subregion.region:
                issuer_state_code = issuer.default_address.city.subregion.region.code
                if seller_gstin[:2] != issuer_state_code:
                    raise GSTValidationError(
                        message="Seller GSTIN state code does not match issuer's default address state.",
                        code="seller_gstin_address_mismatch",
                        details={"seller_gstin": seller_gstin, "issuer_state": issuer_state_code}
                    )
            logger.warning("Only seller GSTIN provided without billing region, defaulting to interstate")
            return True

        # Case 4: Fallback to invoice lookup if entities or GSTINs are insufficient
        if not (buyer_gstin or seller_gstin or issuer or recipient):
            invoice = Invoice.objects.filter(
                issuer_gstin=seller_gstin,
                recipient_gstin=buyer_gstin,
                billing_country_id=billing_country_id,
                billing_region_id=billing_region_id,
                is_active=True,
                deleted_at__isnull=True
            ).select_related('issuer', 'recipient').first()
            if invoice and invoice.issuer_gstin and invoice.recipient_gstin:
                validate_gstin(invoice.issuer_gstin)
                validate_gstin(invoice.recipient_gstin)
                logger.debug(f"Fallback to invoice GSTINs: issuer={invoice.issuer_gstin[:2]}, recipient={invoice.recipient_gstin[:2]}")
                return invoice.issuer_gstin[:2] != invoice.recipient_gstin[:2]

        raise GSTValidationError(
            message="Insufficient data to determine transaction type. Provide GSTINs or entities.",
            code="missing_data",
            details={"buyer_gstin": buyer_gstin, "seller_gstin": seller_gstin, "billing_region_id": billing_region_id}
        )

    except GSTValidationError as e:
        logger.error(f"GST validation failed: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Failed to determine interstate transaction: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to determine interstate transaction: {str(e)}",
            code="interstate_check_error",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_gst_rates(cgst_rate, sgst_rate, igst_rate, region_id, country_id, issue_date, tax_exemption_status, hsn_sac_code=None):
    """Validate GST rates for a given transaction."""
    logger.debug(f"Validating GST rates: cgst={cgst_rate}, sgst={sgst_rate}, igst={igst_rate}, region={region_id}, country={country_id}, exemption={tax_exemption_status}")
    try:
        from decimal import Decimal

        from locations.models import CustomCountry

        # Convert inputs to Decimal for consistent comparison
        cgst_rate = Decimal(str(cgst_rate)) if cgst_rate is not None else Decimal('0.00')
        sgst_rate = Decimal(str(sgst_rate)) if sgst_rate is not None else Decimal('0.00')
        igst_rate = Decimal(str(igst_rate)) if igst_rate is not None else Decimal('0.00')

        # Return True for non-Indian transactions, bypassing GST validation
        if country_id:
            country = CustomCountry.objects.filter(id=country_id, is_active=True).first()
            if not country or country.country_code.upper() != 'IN':
                logger.debug(f"Skipping GST rate validation for non-India country: {country.country_code if country else 'Unknown'}")
                return True

        # Validate rates based on exemption status
        if tax_exemption_status in ['EXEMPT', 'ZERO_RATED']:
            if cgst_rate != Decimal('0.00') or sgst_rate != Decimal('0.00') or igst_rate != Decimal('0.00'):
                raise GSTValidationError(
                    message=f"GST rates must be zero for {tax_exemption_status} status.",
                    code="invalid_exemption_rates",
                    details={"tax_exemption_status": tax_exemption_status}
                )
        else:
            # Validate standard rates
            valid_rates = [Decimal(str(r)) for r in VALID_GST_RATES]
            if cgst_rate != Decimal('0.00') and cgst_rate not in valid_rates:
                raise GSTValidationError(
                    message=f"CGST rate {cgst_rate} is not valid.",
                    code="invalid_gst_rate",
                    details={"field": "cgst_rate", "value": str(cgst_rate)}
                )
            if sgst_rate != Decimal('0.00') and sgst_rate not in valid_rates:
                raise GSTValidationError(
                    message=f"SGST rate {sgst_rate} is not valid.",
                    code="invalid_gst_rate",
                    details={"field": "sgst_rate", "value": str(sgst_rate)}
                )
            if igst_rate != Decimal('0.00') and igst_rate not in valid_rates:
                raise GSTValidationError(
                    message=f"IGST rate {igst_rate} is not valid.",
                    code="invalid_gst_rate",
                    details={"field": "igst_rate", "value": str(igst_rate)}
                )
            # Ensure correct rate combination
            if region_id:
                if igst_rate != Decimal('0.00') and (cgst_rate != Decimal('0.00') or sgst_rate != Decimal('0.00')):
                    raise GSTValidationError(
                        message="Intra-state transaction cannot have IGST with CGST/SGST.",
                        code="invalid_gst_rate_combination",
                        details={"region_id": region_id}
                    )
                if not igst_rate and (cgst_rate != sgst_rate):  # Allow both CGST and SGST to be zero
                    raise GSTValidationError(
                        message="Intra-state transaction must have matching CGST and SGST rates.",
                        code="invalid_gst_rate_combination",
                        details={"region_id": region_id}
                    )
            else:
                if cgst_rate != Decimal('0.00') or sgst_rate != Decimal('0.00'):
                    raise GSTValidationError(
                        message="Inter-state transaction cannot have CGST/SGST.",
                        code="invalid_gst_rate_combination",
                        details={"region_id": None}
                    )
                if igst_rate == Decimal('0.00'):
                    raise GSTValidationError(
                        message="Inter-state transaction must have IGST.",
                        code="invalid_gst_rate_combination",
                        details={"region_id": None}
                    )
        logger.info(f"Validated GST rates for region={region_id}, exemption={tax_exemption_status}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate GST rates: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to validate GST rates: {str(e)}",
            code="gst_validation_error",
            details={"error": str(e)}
        )

@transaction.atomic
def validate_gst_configuration(config, exclude_pk: int = None) -> bool:
    """Validate a GSTConfiguration instance."""
    from locations.models import CustomRegion

    from invoices.models.gst_configuration import GSTConfiguration

    logger.debug(f"Validating GSTConfiguration: {config.description}, exclude_pk={exclude_pk}")

    try:
        if not isinstance(config, GSTConfiguration):
            raise GSTValidationError(
                message="Invalid GST configuration object.",
                code="invalid_gst_config",
                details={"config_id": getattr(config, 'id', None)}
            )

        config.description = normalize_text(config.description)
        if not config.description or len(config.description) > DESCRIPTION_MAX_LENGTH:
            raise GSTValidationError(
                message=f"Description must be non-empty and not exceed {DESCRIPTION_MAX_LENGTH} characters.",
                code="invalid_description",
                details={"field": "description", "value": config.description or 'None'}
            )

        if not config.effective_from:
            raise GSTValidationError(
                message="Effective start date is required.",
                code="invalid_effective_dates",
                details={"field": "effective_from"}
            )
        if config.effective_to and config.effective_to < config.effective_from:
            raise GSTValidationError(
                message="Effective end date cannot be before effective start date.",
                code="invalid_effective_dates",
                details={"field": "effective_to", "effective_from": config.effective_from, "effective_to": config.effective_to}
            )

        if config.applicable_region:
            cache_key_region = f"region:{config.applicable_region.id}"
            try:
                cached_region = redis_client.get(cache_key_region)
                region = json.loads(cached_region) if cached_region else None
            except redis.RedisError as e:
                logger.warning(f"Redis cache miss for region {config.applicable_region.id}: {str(e)}")
                raise InvoiceValidationError(
                    message="Failed to access cache for region lookup.",
                    code="redis_connection_error",
                    details={"error": str(e)}
                )
            if not region:
                try:
                    region_obj = CustomRegion.objects.get(id=config.applicable_region.id, is_active=True)
                    region = {'id': region_obj.id, 'country_id': region_obj.country_id, 'country_code': region_obj.country.country_code}
                    try:
                        redis_client.setex(cache_key_region, 3600, json.dumps(region))
                    except redis.RedisError as e:
                        logger.warning(f"Failed to cache region: {str(e)}")
                except CustomRegion.DoesNotExist:
                    raise GSTValidationError(
                        message="Invalid or inactive region.",
                        code="inactive_region",
                        details={"field": "applicable_region", "region_id": config.applicable_region.id}
                    )
            if region['country_code'].upper() != 'IN':
                raise GSTValidationError(
                    message="GST configurations are only applicable for India.",
                    code="invalid_billing_region",
                    details={"field": "applicable_region", "country_code": region['country_code']}
                )

        current_date = timezone.now().date()
        query = GSTConfiguration.objects.filter(
            applicable_region=config.applicable_region,
            rate_type=config.rate_type,
            cgst_rate=config.cgst_rate,
            sgst_rate=config.sgst_rate,
            igst_rate=config.igst_rate,
            effective_from__lte=config.effective_to or current_date,
            effective_to__gte=config.effective_from,
            is_active=True,
            deleted_at__isnull=True
        ).exclude(pk=exclude_pk)
        if query.exists():
            raise GSTValidationError(
                message="A GST configuration with this region, rate type, rates, and overlapping effective date range already exists.",
                code="duplicate_gst_config",
                details={
                    "fields": ["applicable_region", "rate_type", "cgst_rate", "sgst_rate", "igst_rate", "effective_from", "effective_to"]
                }
            )

        if config.rate_type == 'STANDARD':
            if not any([config.cgst_rate, config.sgst_rate, config.igst_rate]):
                raise GSTValidationError(
                    message="At least one GST rate (CGST, SGST, or IGST) must be non-zero for STANDARD rate type.",
                    code="invalid_gst_rates",
                    details={"rate_type": config.rate_type}
                )
        elif config.rate_type in ['EXEMPT', 'ZERO_RATED']:
            if any([config.cgst_rate, config.sgst_rate, config.igst_rate]):
                raise GSTValidationError(
                    message=f"GST rates must be zero for {config.rate_type} rate type.",
                    code="invalid_exemption_rates",
                    details={"rate_type": config.rate_type}
                )

        logger.info(f"Validated GSTConfiguration: {config.description}")
        return True
    except Exception as e:
        logger.error(f"Failed to validate GSTConfiguration {config.description}: {str(e)}", exc_info=True)
        raise GSTValidationError(
            message=f"Failed to validate GST configuration: {str(e)}",
            code="gst_config_validation_error",
            details={"error": str(e)}
        )
