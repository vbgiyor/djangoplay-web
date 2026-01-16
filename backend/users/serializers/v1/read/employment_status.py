from users.serializers.base import BaseEmploymentStatusSerializer


class EmploymentStatusReadSerializerV1(BaseEmploymentStatusSerializer):
    class Meta(BaseEmploymentStatusSerializer.Meta):
        fields = BaseEmploymentStatusSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
