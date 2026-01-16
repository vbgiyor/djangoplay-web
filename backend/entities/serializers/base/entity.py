import logging
import re

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text

from entities.constants import ENTITY_STATUS_CHOICES, ENTITY_TYPE_CHOICES
from entities.exceptions import (
    EntityValidationError,
    InactiveEntityError,
)
from entities.models import Entity

logger = logging.getLogger(__name__)


class BaseEntitySerializer(serializers.ModelSerializer):

    """
    Canonical, version-agnostic Entity serializer.
    ALL validation + persistence rules live here.
    """

    class Meta:
        model = Entity
        fields = (
            "id",
            "name",
            "slug",
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
        read_only_fields = ("id", "slug")

    # -------------------------------------------------
    # Field normalization
    # -------------------------------------------------
    def validate_name(self, value):
        if not value or not value.strip():
            raise EntityValidationError("Entity name cannot be empty.", code="missing_name")
        return normalize_text(value)

    def validate_website(self, value):
        if value and not re.match(r"^https?://", value):
            value = f"https://{value}"
        return normalize_text(value) if value else value

    def validate_registration_number(self, value):
        return normalize_text(value) if value else value

    def validate_entity_size(self, value):
        return normalize_text(value) if value else value

    def validate_notes(self, value):
        return normalize_text(value) if value else value

    def validate_entity_type(self, value):
        if value not in dict(ENTITY_TYPE_CHOICES):
            raise EntityValidationError(
                f"Invalid entity type: {value}.",
                code="invalid_entity_type",
                details={"field": "entity_type", "value": value},
            )
        return value

    def validate_status(self, value):
        if value not in dict(ENTITY_STATUS_CHOICES):
            raise EntityValidationError(
                f"Invalid status: {value}.",
                code="invalid_status",
                details={"field": "status", "value": value},
            )
        return value

    # -------------------------------------------------
    # Cross-field validation (mirrors model.clean)
    # -------------------------------------------------
    def validate(self, attrs):
        instance = self.instance

        if instance and instance.deleted_at:
            raise InactiveEntityError(details={"object": "Entity", "id": instance.id})

        entity_type = attrs.get("entity_type", getattr(instance, "entity_type", None))
        industry = attrs.get("industry", getattr(instance, "industry", None))

        if entity_type in ("BUSINESS", "GOVERNMENT", "NONPROFIT", "PARTNERSHIP") and not industry:
            raise EntityValidationError(
                "Industry is required for this entity type.",
                code="invalid_industry",
                details={"field": "industry"},
            )

        return super().validate(attrs)

    # -------------------------------------------------
    # Persistence hooks
    # -------------------------------------------------
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        if not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])

        instance = Entity(**validated_data)
        instance.save(user=user)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        if "name" in validated_data and not validated_data.get("slug"):
            validated_data["slug"] = slugify(validated_data["name"])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save(user=user)
        return instance
