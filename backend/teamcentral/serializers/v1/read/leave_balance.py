from teamcentral.serializers.base import BaseLeaveBalanceSerializer


class LeaveBalanceReadSerializerV1(BaseLeaveBalanceSerializer):
    class Meta(BaseLeaveBalanceSerializer.Meta):
        fields = BaseLeaveBalanceSerializer.Meta.fields + (
            "created_at",
            "updated_at",
        )
