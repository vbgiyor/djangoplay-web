from fincore.models import Contact
from rest_framework import serializers


class ContactReadSerializerV1(serializers.ModelSerializer):

    """
    Read-only serializer for Contact.

    Purpose:
    - Stable API response contract
    - No validation or mutation logic
    - Used by read APIs and CRUD responses
    """

    class Meta:
        model = Contact
        fields = (
            "id",
            "entity_mapping",
            "name",
            "email",
            "phone_number",
            "role",
            "country",
            "is_primary",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = fields
