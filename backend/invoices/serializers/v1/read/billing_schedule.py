from entities.models import Entity
from rest_framework import serializers

from invoices.models.billing_schedule import BillingSchedule


class EntityMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ("id", "name")
        read_only_fields = fields
        ref_name = "BillingScheduleEntityReadMini"


class BillingScheduleReadSerializer(serializers.ModelSerializer):
    entity = EntityMiniSerializer(read_only=True)

    class Meta:
        model = BillingSchedule
        fields = (
            "id",
            "entity",
            "description",
            "frequency",
            "start_date",
            "end_date",
            "next_billing_date",
            "amount",
            "status",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep.get("amount") is not None:
            rep["amount"] = str(rep["amount"])
        for d in ["start_date", "end_date", "next_billing_date"]:
            if rep.get(d):
                rep[d] = rep[d].isoformat()
        return rep
