from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import SignUpRequest
from users.serializers.v1.read import SignUpRequestReadSerializerV1


@extend_schema(tags=["Users: Signup Request"])
class SignUpRequestDetailAPIView(RetrieveAPIView):
    queryset = SignUpRequest.objects.filter(deleted_at__isnull=True)
    serializer_class = SignUpRequestReadSerializerV1
