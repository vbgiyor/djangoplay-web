from drf_spectacular.utils import extend_schema
from fincore.models import TaxProfile
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.tax_profile import TaxProfileReadSerializerV1
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


@extend_schema(tags=["Finance: Tax Profile"])
class TaxProfileHistoryAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, FincorePermission]
    serializer_class = TaxProfileReadSerializerV1

    def get_queryset(self):
        return TaxProfile.history.filter(id=self.kwargs["pk"])
