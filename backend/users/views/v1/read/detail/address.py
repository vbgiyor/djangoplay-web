from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import Address
from users.serializers.v1.read import AddressReadSerializerV1


@extend_schema(tags=["Users: Address"])
class AddressDetailAPIView(RetrieveAPIView):
    queryset = Address.objects.filter(deleted_at__isnull=True)
    serializer_class = AddressReadSerializerV1
