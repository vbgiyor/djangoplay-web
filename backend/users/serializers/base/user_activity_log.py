from rest_framework import serializers

from users.models.user_activity_log import UserActivityLog


class BaseUserActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityLog
        fields = (
            "id",
            "user",
            "action",
            "client_ip",
            "created_at",
        )
        read_only_fields = fields
