from fincore.models import TaxProfile
from rest_framework import serializers


class TaxProfileReadSerializerV1(serializers.ModelSerializer):

    """
    Read-only serializer for TaxProfile.

    Purpose:
    - Stable API response contract
    - Explicit output shape for compliance data
    """

    class Meta:
        model = TaxProfile
        fields = (
            "id",
            "entity_mapping",
            "tax_identifier",
            "tax_identifier_type",
            "is_tax_exempt",
            "tax_exemption_reason",
            "tax_exemption_document",
            "country",
            "region",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = fields
