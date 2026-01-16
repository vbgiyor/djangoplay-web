from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from invoices.models.gst_configuration import GSTConfiguration
from invoices.serializers.v1.read import GSTConfigurationReadSerializer


@extend_schema(tags=["Invoices: GST Configuration"])
class GSTConfigurationListAPIView(ListAPIView):
    serializer_class = GSTConfigurationReadSerializer

    def get_queryset(self):
        return (
            GSTConfiguration.objects
            .select_related("applicable_region")
            .filter(is_active=True)
            .order_by("-effective_from")
        )
