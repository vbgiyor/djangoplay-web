from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from invoices.models.gst_configuration import GSTConfiguration
from invoices.serializers.v1.read import GSTConfigurationReadSerializer


@extend_schema(tags=["Invoices: GST Configuration"])
class GSTConfigurationHistoryAPIView(BaseHistoryListAPIView):
    serializer_class = GSTConfigurationReadSerializer

    def get_queryset(self):
        return (
            GSTConfiguration.history
            .filter(id=self.kwargs["pk"])
            .order_by("-history_date")
        )
