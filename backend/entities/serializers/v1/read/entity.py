from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from entities.serializers.base import BaseEntitySerializer


class EntityReadSerializerV1(BaseEntitySerializer):

    """
    Read-only Entity serializer (v1).
    Adds timestamps and hierarchy info.
    """

    children = serializers.SerializerMethodField()

    class Meta(BaseEntitySerializer.Meta):
        fields = BaseEntitySerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
            "deleted_by",
            "children",
        )

    @extend_schema_field(serializers.ListField)
    def get_children(self, obj):
        return [
            {
                "id": c.id,
                "name": c.name,
                "entity_type": c.entity_type,
                "status": c.status,
            }
            for c in obj.children.filter(deleted_at__isnull=True, is_active=True)
        ]
