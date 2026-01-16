from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from invoices.models.gst_configuration import GSTConfiguration
from invoices.serializers.v1.read import GSTConfigurationReadSerializer
from invoices.serializers.v1.write import GSTConfigurationWriteSerializer


@extend_schema(tags=["Invoices: GST Configuration"])
class GSTConfigurationViewSet(ModelViewSet):
    queryset = (
        GSTConfiguration.objects
        .select_related("applicable_region")
        .filter(is_active=True)
        .order_by("-effective_from")
    )

    read_serializer_class = GSTConfigurationReadSerializer
    write_serializer_class = GSTConfigurationWriteSerializer

    def get_serializer_class(self):
        return (
            self.write_serializer_class
            if self.action in ("create", "update", "partial_update")
            else self.read_serializer_class
        )
