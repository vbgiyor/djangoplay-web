from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import Address
from teamcentral.serializers.v1.read import AddressReadSerializerV1


@extend_schema(tags=["Teamcentral: Address"])
class AddressHistoryAPIView(BaseHistoryListAPIView):
    queryset = Address.objects.all()
    history_queryset = Address.history.all()
    serializer_class = AddressReadSerializerV1
