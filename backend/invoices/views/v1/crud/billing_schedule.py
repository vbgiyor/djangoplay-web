from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.billing_schedule import BillingSchedule
from invoices.serializers.v1.read import BillingScheduleReadSerializer
from invoices.serializers.v1.write import BillingScheduleWriteSerializer


@extend_schema(tags=["Invoices: Billing Schedule"])
class BillingScheduleViewSet(ModelViewSet):
    queryset = (
        BillingSchedule.objects
        .select_related("entity")
        .filter(is_active=True)
        .order_by("-start_date")
    )

    read_serializer_class = BillingScheduleReadSerializer
    write_serializer_class = BillingScheduleWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
