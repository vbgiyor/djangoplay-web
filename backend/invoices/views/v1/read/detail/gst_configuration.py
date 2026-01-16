from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from invoices.models.gst_configuration import GSTConfiguration
from invoices.serializers.v1.read import GSTConfigurationReadSerializer


@extend_schema(tags=["Invoices: GST Configuration"])
class GSTConfigurationDetailAPIView(RetrieveAPIView):
    serializer_class = GSTConfigurationReadSerializer

    def get_queryset(self):
        return GSTConfiguration.objects.filter(is_active=True)
