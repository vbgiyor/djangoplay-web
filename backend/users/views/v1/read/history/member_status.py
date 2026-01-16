from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import MemberStatus
from users.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Users: Member Status"])
class MemberStatusHistoryAPIView(BaseHistoryListAPIView):
    queryset = MemberStatus.objects.all()
    history_queryset = MemberStatus.history.all()
    serializer_class = MemberStatusReadSerializerV1
