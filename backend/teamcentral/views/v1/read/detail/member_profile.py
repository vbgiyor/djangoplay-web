from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import MemberProfile
from teamcentral.serializers.v1.read import MemberProfileReadSerializerV1


@extend_schema(tags=["Teamcentral: MemberProfile"])
class MemberProfileDetailAPIView(RetrieveAPIView):
    queryset = MemberProfile.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberProfileReadSerializerV1
