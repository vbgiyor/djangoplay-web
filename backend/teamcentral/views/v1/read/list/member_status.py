from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import MemberStatus
from teamcentral.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Member Status"])
class MemberStatusListAPIView(BaseListAPIView):
    queryset = MemberStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberStatusReadSerializerV1
