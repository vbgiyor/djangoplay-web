from django.core.exceptions import ValidationError
from fincore.constants import ADDRESS_TYPE_CHOICES
from fincore.exceptions import AddressValidationError, InactiveFincoreError
from fincore.models import Address, FincoreEntityMapping
from locations.models import CustomCity, CustomCountry, CustomRegion, CustomSubRegion
from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text
from utilities.utils.locations.postal_code_validations import validate_postal_code


class BaseAddressSerializer(serializers.ModelSerializer):
    entity_mapping = serializers.PrimaryKeyRelatedField(
        queryset=FincoreEntityMapping.objects.all()
    )
    address_type = serializers.ChoiceField(choices=ADDRESS_TYPE_CHOICES)
    city = serializers.PrimaryKeyRelatedField(queryset=CustomCity.objects.filter(deleted_at__isnull=True))
    country = serializers.PrimaryKeyRelatedField(queryset=CustomCountry.objects.filter(deleted_at__isnull=True))
    region = serializers.PrimaryKeyRelatedField(
        queryset=CustomRegion.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
    )
    subregion = serializers.PrimaryKeyRelatedField(
        queryset=CustomSubRegion.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Address
        fields = "__all__"

    def validate(self, data):
        if data.get("deleted_at"):
            raise InactiveFincoreError(details={"object": "Address"})

        if data.get("address_type") == "HEADQUARTERS" and not data.get("street_address"):
            raise AddressValidationError(
                "Street address required for HEADQUARTERS.",
                code="missing_street_address",
            )

        if data.get("postal_code"):
            try:
                validate_postal_code(data["postal_code"], data["country"].country_code)
            except ValidationError as exc:
                raise AddressValidationError(str(exc), code="invalid_postal_code")

        if data.get("street_address"):
            data["street_address"] = normalize_text(data["street_address"])

        return data
