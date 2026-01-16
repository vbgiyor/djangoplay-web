from rest_framework import serializers

from invoices.models.payment import Payment


class PaymentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "invoice_id",
            "amount",
            "payment_date",
            "payment_method",
            "payment_reference",
            "status",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep.get("amount") is not None:
            rep["amount"] = str(rep["amount"])
        if rep.get("payment_date"):
            rep["payment_date"] = rep["payment_date"].isoformat()
        return rep
