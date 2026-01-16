from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import PasswordResetRequest
from users.serializers.v1.read import PasswordResetRequestReadSerializerV1


@extend_schema(exclude=True)
class PasswordResetRequestHistoryAPIView(BaseHistoryListAPIView):
    queryset = PasswordResetRequest.objects.all()
    history_queryset = PasswordResetRequest.history.all()
    serializer_class = PasswordResetRequestReadSerializerV1
