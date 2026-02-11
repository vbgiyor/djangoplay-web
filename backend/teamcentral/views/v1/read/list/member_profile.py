from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from utilities.api.generic_views import BaseListAPIView

from teamcentral.models import MemberProfile
from teamcentral.serializers.v1.read import MemberProfileReadSerializerV1


@extend_schema(tags=["Teamcentral: Member"])
class MemberProfileListAPIView(BaseListAPIView):
    queryset = MemberProfile.objects.filter(deleted_at__isnull=True)
    serializer_class = MemberProfileReadSerializerV1
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]
    search_fields = ["email", "member_code"]
