import logging

from django.db import transaction
from django.utils import timezone
from users.exceptions import AddressValidationError
from utilities.utils.general.normalize_text import normalize_text

from teamcentral.models import Address

logger = logging.getLogger(__name__)


class AddressManagementService:

    """
    Handles creation and mutation of Address records.

    Rules:
    - Exactly ONE active address per owner
    - Historical addresses are preserved (soft-deactivated)
    """

    @staticmethod
    def validate_address_data(data):
        errors = {}

        if not data.get("address"):
            errors["address"] = "Address is required."

        if data.get("postal_code") is not None and not str(data["postal_code"]).strip():
            errors["postal_code"] = "Postal code cannot be empty."

        if errors:
            raise AddressValidationError(errors, code="invalid_address")

        return (
            normalize_text(data.get("address", "")),
            normalize_text(data.get("city", "")),
        )

    @staticmethod
    @transaction.atomic
    def create_address(*, data: dict, created_by):
        address_text, city = AddressManagementService.validate_address_data(data)

        owner = data.get("owner")
        if not owner:
            raise AddressValidationError(
                "Owner must be provided.",
                code="missing_owner",
            )

        # Enforce single active address
        Address.all_objects.filter(
            owner=owner,
            is_active=True,
        ).update(is_active=False)

        address = Address(
            owner=owner,
            address=address_text,
            city=city,
            country=data.get("country", ""),
            state=data.get("state", ""),
            postal_code=data.get("postal_code", ""),
            address_type=data.get("address_type"),
            emergency_contact=data.get("emergency_contact", ""),
            created_by=created_by,
        )
        address.save(user=created_by)

        logger.info("Address created id=%s owner=%s", address.id, owner)
        return address

    @staticmethod
    @transaction.atomic
    def update_address(*, address: Address, data: dict, updated_by):
        address_text, city = AddressManagementService.validate_address_data(data)

        address.address = address_text
        address.city = city
        address.country = data.get("country", address.country)
        address.state = data.get("state", address.state)
        address.postal_code = data.get("postal_code", address.postal_code)
        address.address_type = data.get("address_type", address.address_type)
        address.emergency_contact = data.get(
            "emergency_contact", address.emergency_contact
        )
        address.updated_by = updated_by
        address.updated_at = timezone.now()

        address.save(user=updated_by)
        logger.info("Address updated id=%s", address.id)
        return address
