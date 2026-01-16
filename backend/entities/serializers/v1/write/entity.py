from entities.serializers.base import BaseEntitySerializer


class EntityWriteSerializerV1(BaseEntitySerializer):

    """
    Write-only Entity serializer (v1).
    Explicit write fields.
    """

    class Meta(BaseEntitySerializer.Meta):
        fields = (
            "name",
            "entity_type",
            "status",
            "external_id",
            "website",
            "registration_number",
            "entity_size",
            "notes",
            "parent",
            "industry",
            "default_address",
        )
