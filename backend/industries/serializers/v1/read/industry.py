from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from industries.serializers.base import BaseIndustrySerializer


class IndustryReadSerializerV1(BaseIndustrySerializer):

    """
    Read-only Industry serializer (v1).
    Adds timestamps + hierarchy metadata.
    """

    parent = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    last_updated_timestamp = serializers.SerializerMethodField()

    class Meta(BaseIndustrySerializer.Meta):
        fields = BaseIndustrySerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "parent",
            "children",
            "children_count",
            "last_updated_timestamp",
        )

    @extend_schema_field(serializers.DictField)
    def get_parent(self, obj):
        if not obj.parent:
            return None
        p = obj.parent
        return {
            "id": p.id,
            "code": p.code,
            "description": p.description,
            "level": p.level,
            "sector": p.sector,
        }

    @extend_schema_field(serializers.ListField)
    def get_children(self, obj):
        return [
            {
                "id": c.id,
                "code": c.code,
                "description": c.description,
                "level": c.level,
                "sector": c.sector,
            }
            for c in obj.children.filter(deleted_at__isnull=True)
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_children_count(self, obj):
        return obj.children.filter(deleted_at__isnull=True).count()

    @extend_schema_field(serializers.DateTimeField)
    def get_last_updated_timestamp(self, obj):
        latest = obj.history.order_by("-history_date").first()
        return latest.history_date if latest else obj.updated_at
