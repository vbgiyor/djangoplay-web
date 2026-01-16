from fincore.serializers.base.contact import BaseContactSerializer


class ContactWriteSerializerV1(BaseContactSerializer):

    """
    Write serializer for Contact.

    Purpose:
    - Create / update input contract
    - All validation inherited from BaseContactSerializer
    """

    class Meta(BaseContactSerializer.Meta):
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
            "deleted_by",
        )
