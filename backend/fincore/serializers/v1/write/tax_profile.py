from fincore.serializers.base.tax_profile import BaseTaxProfileSerializer


class TaxProfileWriteSerializerV1(BaseTaxProfileSerializer):

    """
    Write serializer for TaxProfile.

    Purpose:
    - Create / update input contract
    - Validation and compliance rules live in base serializer
    """

    class Meta(BaseTaxProfileSerializer.Meta):
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
            "deleted_by",
        )
