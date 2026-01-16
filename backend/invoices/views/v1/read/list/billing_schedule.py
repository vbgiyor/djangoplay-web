from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.billing_schedule import BillingSchedule
from invoices.serializers.v1.read import BillingScheduleReadSerializer


@extend_schema(tags=["Invoices: Billing Schedule"])
class BillingScheduleListAPIView(ListAPIView):
    serializer_class = BillingScheduleReadSerializer

    def get_queryset(self):
        return (
            BillingSchedule.objects
            .select_related("entity")
            .filter(is_active=True)
            .order_by("-start_date")
        )
