from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from users.models import MemberStatus
from users.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Users: Member Status"])
class MemberStatusListAPIView(BaseListAPIView):
    queryset = MemberStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberStatusReadSerializerV1
