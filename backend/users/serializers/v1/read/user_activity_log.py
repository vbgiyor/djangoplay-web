from users.serializers.base import BaseUserActivityLogSerializer


class UserActivityLogReadSerializerV1(BaseUserActivityLogSerializer):
    class Meta(BaseUserActivityLogSerializer.Meta):
        fields = BaseUserActivityLogSerializer.Meta.fields
