from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.status import Status
from invoices.serializers.v1.read import StatusReadSerializer


@extend_schema(tags=["Invoices: Status"])
class StatusListAPIView(ListAPIView):

    """
    Read-only list of invoice statuses.
    """

    serializer_class = StatusReadSerializer

    def get_queryset(self):
        return (
            Status.objects
            .filter(is_active=True)
            .order_by("name")
        )
