import logging

from entities.models import Entity
from fincore.models import Address
from locations.models import CustomCountry, CustomRegion
from rest_framework import serializers

from invoices.models.invoice import Invoice
from invoices.models.status import Status

logger = logging.getLogger(__name__)


# -------------------------
# Small nested read helpers
# -------------------------

class EntityReadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ("id", "name")
        read_only_fields = fields
        ref_name = "InvoiceEntityReadMini"


class AddressReadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "street_address", "postal_code")
        read_only_fields = fields
        ref_name = "InvoiceAddressReadMini"


class CountryReadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCountry
        fields = ("id", "name", "country_code")
        read_only_fields = fields
        ref_name = "InvoiceCountryReadMini"


class RegionReadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomRegion
        fields = ("id", "name", "code")
        read_only_fields = fields
        ref_name = "InvoiceRegionReadMini"


class StatusReadMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = ("id", "name", "code", "is_locked")
        read_only_fields = fields
        ref_name = "InvoiceStatusReadMini"


# -------------------------
# Base read serializer
# -------------------------

class InvoiceReadSerializer(serializers.ModelSerializer):
    issuer = EntityReadMiniSerializer(read_only=True)
    recipient = EntityReadMiniSerializer(read_only=True)
    billing_address = AddressReadMiniSerializer(read_only=True)
    billing_country = CountryReadMiniSerializer(read_only=True)
    billing_region = RegionReadMiniSerializer(read_only=True, allow_null=True)
    status = StatusReadMiniSerializer(read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "description",
            "issuer",
            "recipient",
            "billing_address",
            "billing_country",
            "billing_region",
            "issue_date",
            "due_date",
            "status",
            "payment_terms",
            "currency",
            "base_amount",
            "cgst_rate",
            "sgst_rate",
            "igst_rate",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "total_amount",
            "tax_exemption_status",
            "payment_method",
            "payment_reference",
            "issuer_gstin",
            "recipient_gstin",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for f in [
            "base_amount",
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
        for d in ["issue_date", "due_date"]:
            if rep.get(d):
                rep[d] = rep[d]
        return rep


# -------------------------
# Context-specific wrappers
# -------------------------

class InvoiceListSerializer(InvoiceReadSerializer):

    """Optimized for list views (safe for caching)."""

    pass


class InvoiceDetailSerializer(InvoiceReadSerializer):

    """Full invoice detail view."""

    pass


class InvoiceHistorySerializer(serializers.ModelSerializer):

    """
    Serializer for historical invoice records
    (simple_history compatible).
    """

    class Meta:
        model = Invoice.history.model
        fields = "__all__"
        read_only_fields = ()
