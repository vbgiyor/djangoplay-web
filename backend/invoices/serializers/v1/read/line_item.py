from rest_framework import serializers

from invoices.models.line_item import LineItem


class LineItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = (
            "id",
            "invoice_id",
            "description",
            "hsn_sac_code",
            "quantity",
            "unit_price",
            "discount",
            "cgst_rate",
            "sgst_rate",
            "igst_rate",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for f in [
            "quantity",
            "unit_price",
            "discount",
            "cgst_rate",
            "sgst_rate",
            "igst_rate",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
        ]:
            if rep.get(f) is not None:
                rep[f] = str(rep[f])
        return rep
