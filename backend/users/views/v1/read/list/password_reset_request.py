from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import PasswordResetRequest
from users.serializers.v1.read import PasswordResetRequestReadSerializerV1


@extend_schema(exclude=True)
class PasswordResetRequestListAPIView(BaseListAPIView):
    queryset = PasswordResetRequest.objects.filter(deleted_at__isnull=True)
    serializer_class = PasswordResetRequestReadSerializerV1
