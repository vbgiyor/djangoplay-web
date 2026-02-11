from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import Address
from teamcentral.serializers.v1.read import AddressReadSerializerV1


@extend_schema(tags=["Teamcentral: Address"])
class AddressDetailAPIView(RetrieveAPIView):
    queryset = Address.objects.filter(deleted_at__isnull=True)
    serializer_class = AddressReadSerializerV1
