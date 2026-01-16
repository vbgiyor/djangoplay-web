from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from invoices.models.billing_schedule import BillingSchedule
from invoices.serializers.v1.read import BillingScheduleReadSerializer


@extend_schema(tags=["Invoices: Billing Schedule"])
class BillingScheduleDetailAPIView(RetrieveAPIView):
    serializer_class = BillingScheduleReadSerializer

    def get_queryset(self):
        return BillingSchedule.objects.filter(is_active=True)
