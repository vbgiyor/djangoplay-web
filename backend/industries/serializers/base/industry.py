import logging

from rest_framework import serializers

from industries.exceptions import InvalidIndustryData
from industries.models import Industry

logger = logging.getLogger(__name__)


class BaseIndustrySerializer(serializers.ModelSerializer):

    """
    Canonical, version-agnostic Industry serializer.
    Contains ALL validation logic.
    """

    class Meta:
        model = Industry
        fields = (
            "id",
            "code",
            "description",
            "level",
            "sector",
            "parent",
        )
        read_only_fields = ("id",)

    # ------------------------------
    # Field-level validation
    # ------------------------------
    def validate_code(self, value):
        value = (value or "").strip()
        if not value:
            raise InvalidIndustryData(
                "Industry code is required.",
                code="missing_code",
                details={"field": "code"},
            )
        return value

    def validate_description(self, value):
        if not value or not str(value).strip():
            raise InvalidIndustryData(
                "Description cannot be empty.",
                code="missing_description",
                details={"field": "description"},
            )
        return value

    # ------------------------------
    # Cross-field validation
    # ------------------------------
    def validate(self, attrs):
        level = attrs.get("level", getattr(self.instance, "level", None))
        sector = attrs.get("sector", getattr(self.instance, "sector", None))

        valid_levels = {c[0] for c in Industry.LEVEL_CHOICES}
        if level and level not in valid_levels:
            raise InvalidIndustryData(
                {"level": f"Invalid level '{level}'. Must be one of {valid_levels}."},
                code="invalid_level",
                details={"field": "level", "value": level},
            )

        valid_sectors = {c[0] for c in Industry.SECTOR_CHOICES}
        if sector and sector not in valid_sectors:
            raise InvalidIndustryData(
                {"sector": f"Invalid sector '{sector}'. Must be one of {valid_sectors}."},
                code="invalid_sector",
                details={"field": "sector", "value": sector},
            )

        return super().validate(attrs)

    # ------------------------------
    # Persistence hooks
    # ------------------------------
    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        instance = Industry(**validated_data)
        instance.save(user=user)
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save(user=user)
        return instance
