from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.billing_schedule import BillingSchedule
from invoices.serializers.v1.read import BillingScheduleReadSerializer


@extend_schema(tags=["Invoices: Billing Schedule"])
class BillingScheduleHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = BillingScheduleReadSerializer

    def get_queryset(self):
        return (
            BillingSchedule.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
