from rest_framework import serializers

from users.models.support import SupportTicket


class BaseSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "employee",
            "subject",
            "ticket_number",
            "status",
            "is_active",
        )
        read_only_fields = ("id",)
