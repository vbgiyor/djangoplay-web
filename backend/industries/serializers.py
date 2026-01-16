import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from industries.exceptions import InvalidIndustryData
from industries.models import Industry

logger = logging.getLogger(__name__)


class IndustrySerializer(serializers.ModelSerializer):

    """Basic serializer for Industry - used for standard CRUD operations."""

    class Meta:
        model = Industry
        fields = [
            'id', 'code', 'description', 'level', 'sector', 'parent',
            'created_at', 'updated_at', 'created_by', 'updated_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']

    def validate_code(self, value):  # ensure code is present and stripped
        value = (value or "").strip()
        if not value:
            raise InvalidIndustryData("Industry code is required.", code="missing_code", details={"field": "code"})
        return value

    def validate_description(self, value):  # description cannot be empty/whitespace
        if not value or not str(value).strip():
            raise InvalidIndustryData("Description cannot be empty.", code="missing_description", details={"field": "description"})
        return value

    def validate(self, attrs):  # cross-field validation + defensive choice checks
        level = attrs.get('level', getattr(self.instance, 'level', None))
        sector = attrs.get('sector', getattr(self.instance, 'sector', None))

        valid_levels = {c[0] for c in Industry.LEVEL_CHOICES}
        if level and level not in valid_levels:
            raise InvalidIndustryData({"level": f"Invalid level '{level}'. Must be one of {valid_levels}."},
                                      code="invalid_level", details={"field": "level", "value": level})

        valid_sectors = {c[0] for c in Industry.SECTOR_CHOICES}
        if sector and sector not in valid_sectors:
            raise InvalidIndustryData({"sector": f"Invalid sector '{sector}'. Must be one of {valid_sectors}."},
                                      code="invalid_sector", details={"field": "sector", "value": sector})

        return super().validate(attrs)

    def create(self, validated_data):  # populate audit fields via model.save(user=…)
        request = self.context.get('request')
        user = getattr(request, "user", None) if request else None
        try:
            instance = Industry(**validated_data)
            instance.save(user=user)  # model.clean() may raise InvalidIndustryData
            return instance
        except InvalidIndustryData:
            raise

    def update(self, instance, validated_data):  # apply changes + audit on save
        request = self.context.get('request')
        user = getattr(request, "user", None) if request else None
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        try:
            instance.save(user=user)
            return instance
        except InvalidIndustryData:
            raise


class IndustryDetailSerializer(IndustrySerializer):

    """Detailed view serializer - adds parent, children, counts and last update timestamp."""

    parent = serializers.SerializerMethodField()               # nested minimal parent
    children = serializers.SerializerMethodField()             # direct children list
    children_count = serializers.SerializerMethodField()       # count of active children
    last_updated_timestamp = serializers.SerializerMethodField()  # from history or updated_at

    class Meta(IndustrySerializer.Meta):
        fields = IndustrySerializer.Meta.fields + [
            'parent', 'children', 'children_count', 'last_updated_timestamp',
        ]

    @extend_schema_field(serializers.DictField)
    def get_parent(self, obj):  # minimal parent representation (prevents recursion)
        if not obj.parent:
            return None
        p = obj.parent
        return {"id": p.id, "code": p.code, "description": p.description,
                "level": p.level, "sector": p.sector}

    @extend_schema_field(serializers.ListField)
    def get_children(self, obj):  # minimal info for each direct child
        result = []
        for child in obj.children.filter(deleted_at__isnull=True):
            result.append({
                "id": child.id, "code": child.code, "description": child.description,
                "level": child.level, "sector": child.sector,
            })
        return result

    @extend_schema_field(serializers.IntegerField)
    def get_children_count(self, obj):  # count only non-soft-deleted children
        return obj.children.filter(deleted_at__isnull=True).count()

    @extend_schema_field(serializers.DateTimeField)
    def get_last_updated_timestamp(self, obj):  # prefer simple_history date, fallback to updated_at
        latest = obj.history.order_by('-history_date').first()
        return latest.history_date if latest else obj.updated_at
