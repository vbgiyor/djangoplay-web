# base/support.py
from rest_framework import serializers

from helpdesk.models import SupportTicket


class BaseSupportSerializer(serializers.ModelSerializer):

    """
    Version-agnostic base serializer for SupportTicket.
    Used by:
      - API v1 read/write serializers
      - Services
      - Admin (later)
    """

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "ticket_number",
            "full_name",
            "email",
            "subject",
            "message",
            "status",
            "severity",
            "user",
            "resolved_at",
            "emails_sent",
            "is_active",
        )
        read_only_fields = (
            "id",
            "ticket_number",
            "resolved_at",
            "emails_sent",
        )
