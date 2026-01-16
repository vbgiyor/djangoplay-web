from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import SignUpRequest
from users.serializers.v1.read import SignUpRequestReadSerializerV1


@extend_schema(tags=["Users: Signup Request"])
class SignUpRequestListAPIView(BaseListAPIView):
    queryset = SignUpRequest.objects.filter(deleted_at__isnull=True)
    serializer_class = SignUpRequestReadSerializerV1
