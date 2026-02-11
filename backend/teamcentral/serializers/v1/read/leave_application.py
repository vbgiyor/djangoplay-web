from teamcentral.serializers.base import BaseLeaveApplicationSerializer


class LeaveApplicationReadSerializerV1(BaseLeaveApplicationSerializer):
    class Meta(BaseLeaveApplicationSerializer.Meta):
        fields = BaseLeaveApplicationSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
