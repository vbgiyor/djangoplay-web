from users.serializers.base import BaseEmploymentStatusSerializer


class EmploymentStatusWriteSerializerV1(BaseEmploymentStatusSerializer):
    class Meta(BaseEmploymentStatusSerializer.Meta):
        fields = (
            "code",
            "name",
            "is_active",
        )
