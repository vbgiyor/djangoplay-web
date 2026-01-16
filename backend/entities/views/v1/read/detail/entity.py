from drf_spectacular.utils import extend_schema
from entities.exceptions import EntityValidationError
from entities.models import Entity
from entities.serializers.v1.read import EntityReadSerializerV1
from rest_framework.generics import RetrieveAPIView


@extend_schema(tags=["Business"])
class EntityDetailAPIView(RetrieveAPIView):
    queryset = Entity.objects.filter(deleted_at__isnull=True, is_active=True)
    serializer_class = EntityReadSerializerV1
    error_class = EntityValidationError
