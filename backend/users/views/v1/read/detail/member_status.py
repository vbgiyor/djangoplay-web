from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from users.models import MemberStatus
from users.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Users: Member Status"])
class MemberStatusDetailAPIView(RetrieveAPIView):
    queryset = MemberStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberStatusReadSerializerV1
