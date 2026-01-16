from fincore.constants import CONTACT_ROLE_CHOICES
from fincore.exceptions import ContactValidationError, InactiveFincoreError
from fincore.models import Contact, FincoreEntityMapping
from rest_framework import serializers
from utilities.utils.general.normalize_text import normalize_text


class BaseContactSerializer(serializers.ModelSerializer):
    entity_mapping = serializers.PrimaryKeyRelatedField(
        queryset=FincoreEntityMapping.objects.all()
    )
    role = serializers.ChoiceField(choices=CONTACT_ROLE_CHOICES)

    class Meta:
        model = Contact
        fields = "__all__"

    def validate(self, data):
        if data.get("deleted_at"):
            raise InactiveFincoreError(details={"object": "Contact"})

        if not data.get("email") and not data.get("phone_number"):
            raise ContactValidationError(
                "Email or phone number required.",
                code="missing_contact_info",
            )

        if data.get("name"):
            data["name"] = normalize_text(data["name"])
        if data.get("email"):
            data["email"] = normalize_text(data["email"])

        return data
