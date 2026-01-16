from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import PasswordResetRequest
from users.serializers.v1.read import PasswordResetRequestReadSerializerV1


@extend_schema(exclude=True)
class PasswordResetRequestDetailAPIView(RetrieveAPIView):
    queryset = PasswordResetRequest.objects.filter(deleted_at__isnull=True)
    serializer_class = PasswordResetRequestReadSerializerV1
