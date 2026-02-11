from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import MemberStatus
from teamcentral.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Member Status"])
class MemberStatusHistoryAPIView(BaseHistoryListAPIView):
    queryset = MemberStatus.objects.all()
    history_queryset = MemberStatus.history.all()
    serializer_class = MemberStatusReadSerializerV1
