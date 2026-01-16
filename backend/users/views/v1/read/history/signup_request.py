from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import SignUpRequest
from users.serializers.v1.read import SignUpRequestReadSerializerV1


@extend_schema(tags=["Users: Signup Request"])
class SignUpRequestHistoryAPIView(BaseHistoryListAPIView):
    queryset = SignUpRequest.objects.all()
    history_queryset = SignUpRequest.history.all()
    serializer_class = SignUpRequestReadSerializerV1
