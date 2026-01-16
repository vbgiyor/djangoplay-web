from drf_spectacular.utils import extend_schema
from utilities.api.generic_viewsets import BaseViewSet

from users.models import SignUpRequest
from users.serializers.v1.read import SignUpRequestReadSerializerV1
from users.serializers.v1.write import SignUpRequestWriteSerializerV1


@extend_schema(tags=["Users: Signup Request"])
class SignUpRequestViewSet(BaseViewSet):
    queryset = SignUpRequest.objects.filter(deleted_at__isnull=True)

    read_serializer_class = SignUpRequestReadSerializerV1
    write_serializer_class = SignUpRequestWriteSerializerV1
