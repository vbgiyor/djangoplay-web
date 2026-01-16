from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from users.models import Member
from users.serializers.v1.read import MemberReadSerializerV1


@extend_schema(tags=["Users: Member"])
class MemberHistoryAPIView(BaseHistoryListAPIView):
    queryset = Member.objects.all()
    history_queryset = Member.history.all()
    serializer_class = MemberReadSerializerV1
