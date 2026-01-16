from users.serializers.base import BaseLeaveTypeSerializer


class LeaveTypeReadSerializerV1(BaseLeaveTypeSerializer):
    class Meta(BaseLeaveTypeSerializer.Meta):
        fields = BaseLeaveTypeSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
