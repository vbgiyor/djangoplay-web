from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseHistoryListAPIView

from teamcentral.models import MemberProfile
from teamcentral.serializers.v1.read import MemberProfileReadSerializerV1


@extend_schema(tags=["Teamcentral: Member"])
class MemberProfileHistoryAPIView(BaseHistoryListAPIView):
    queryset = MemberProfile.objects.all()
    history_queryset = MemberProfile.history.all()
    serializer_class = MemberProfileReadSerializerV1
