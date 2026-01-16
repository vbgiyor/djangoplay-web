from django.core.exceptions import ValidationError
from fincore.constants import TAX_IDENTIFIER_TYPE_CHOICES
from fincore.exceptions import InactiveFincoreError, TaxProfileValidationError
from fincore.models import FincoreEntityMapping, TaxProfile
from rest_framework import serializers
from utilities.utils.entities.entity_validations import is_valid_indian_pan, validate_gstin
from utilities.utils.general.normalize_text import normalize_text


class BaseTaxProfileSerializer(serializers.ModelSerializer):
    entity_mapping = serializers.PrimaryKeyRelatedField(
        queryset=FincoreEntityMapping.objects.all()
    )
    tax_identifier_type = serializers.ChoiceField(choices=TAX_IDENTIFIER_TYPE_CHOICES)

    class Meta:
        model = TaxProfile
        fields = "__all__"

    def validate(self, data):
        if data.get("deleted_at"):
            raise InactiveFincoreError(details={"object": "TaxProfile"})

        tax_id = data.get("tax_identifier")
        tax_type = data.get("tax_identifier_type")

        if tax_type == "GSTIN" and tax_id:
            try:
                validate_gstin(tax_id)
            except ValidationError as exc:
                raise TaxProfileValidationError(str(exc), code="invalid_gstin")

        if tax_type == "PAN" and tax_id and not is_valid_indian_pan(tax_id):
            raise TaxProfileValidationError("Invalid PAN", code="invalid_pan")

        if data.get("tax_identifier"):
            data["tax_identifier"] = normalize_text(data["tax_identifier"])

        return data
