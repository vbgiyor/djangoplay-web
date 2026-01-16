import logging

from django.db import transaction
from django.utils import timezone
from utilities.utils.general.normalize_text import normalize_text

from users.models.address import Address
from users.models.user_activity_log import UserActivityLog

from ..exceptions import AddressValidationError

logger = logging.getLogger(__name__)

class CommonService:

    """Service layer for Address and UserActivityLog operations."""

    @staticmethod
    def validate_address_data(data, instance=None):
        """Validate address data."""
        errors = {}
        if not data.get('address'):
            errors['address'] = "Address is required."
        if data.get('postal_code') and not data.get('postal_code').strip():
            errors['postal_code'] = "Postal code cannot be empty if provided."
        if errors:
            raise AddressValidationError(errors, code="invalid_address")
        return normalize_text(data.get('address', '')), normalize_text(data.get('city', ''))

    @staticmethod
    @transaction.atomic
    def create_address(data, created_by):
        """Create a new address."""
        logger.info(f"Creating address: city={data.get('city')}, created_by={created_by}")
        address_text, city = CommonService.validate_address_data(data)
        try:
            owner = data.get("owner")

            # Inclusive fallback: infer owner from created_by if possible
            if owner is None:
                if hasattr(created_by, "addresses"):
                    owner = created_by
                else:
                    raise AddressValidationError(
                        "Owner must be provided to create an address.",
                        code="missing_owner",
                    )
            # 🔐 enforce single active address
            Address.all_objects.filter(
                owner=owner,
                is_active=True,
            ).update(is_active=False)

            address = Address(
                owner=owner,
                address=address_text,
                country=data.get('country', ''),
                state=data.get('state', ''),
                city=city,
                postal_code=data.get('postal_code', ''),
                address_type=data.get('address_type'),
                emergency_contact=data.get('emergency_contact', ''),
                created_by=created_by,
            )
            address.save(user=created_by)
            logger.info(f"Address created: {address}")
            return address
        except Exception as e:
            logger.error(f"Failed to create address: {str(e)}")
            raise AddressValidationError(
                f"Failed to create address: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    @transaction.atomic
    def update_address(address, data, updated_by):
        """Mutates existing row; admin uses versioned replace"""
        logger.info(f"Updating address: id={address.id}, updated_by={updated_by}")
        address_text, city = CommonService.validate_address_data(data)
        address.address = address_text
        address.city = city
        address.country = data.get('country', address.country)
        address.state = data.get('state', address.state)
        address.postal_code = data.get('postal_code', address.postal_code)
        address.address_type = data.get('address_type', address.address_type)
        address.emergency_contact = data.get('emergency_contact', address.emergency_contact)
        address.updated_by = updated_by
        address.updated_at = timezone.now()
        try:
            address.save(user=updated_by)
            logger.info(f"Address updated: {address}")
            return address
        except Exception as e:
            logger.error(f"Failed to update address {address.id}: {str(e)}")
            raise AddressValidationError(
                f"Failed to update address: {str(e)}",
                code="save_error",
                details={"error": str(e)}
            )

    @staticmethod
    @transaction.atomic
    def log_user_activity(user, action, client_ip=None):
        """Log user activity."""
        logger.info(f"Logging activity: user={user.get_full_name}, action={action}")
        if action not in dict(UserActivityLog.ACTION_CHOICES).keys():
            raise ValueError(f"Invalid action: {action}")
        try:
            activity = UserActivityLog(
                user=user,
                action=action,
                client_ip=client_ip,
                created_at=timezone.now()
            )
            activity.save()
            logger.info(f"Activity logged: {activity}")
            return activity
        except Exception as e:
            logger.error(f"Failed to log activity for user {user.get_full_name}: {str(e)}")
            raise ValueError(f"Failed to log activity: {str(e)}")


    @staticmethod
    def is_duplicate_address(user, address_type, exclude_pk=None):
        """Check if address type already exists for user."""
        return Address.objects.filter(
            owner=user,
            address_type=address_type,
            is_active=True,
        ).exclude(pk=exclude_pk).exists()


