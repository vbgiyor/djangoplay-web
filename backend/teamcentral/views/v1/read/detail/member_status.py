from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveAPIView

from teamcentral.models import MemberStatus
from teamcentral.serializers.v1.read import MemberStatusReadSerializerV1


@extend_schema(tags=["Teamcentral: Member Status"])
class MemberStatusDetailAPIView(RetrieveAPIView):
    queryset = MemberStatus.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberStatusReadSerializerV1
