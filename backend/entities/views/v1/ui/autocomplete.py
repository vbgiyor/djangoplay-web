import logging

from dal import autocomplete
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from entities.exceptions import EntityValidationError
from entities.models import Entity
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from utilities.api.rate_limits import CustomSearchThrottle, CustomThrottle

logger = logging.getLogger(__name__)

class BaseAutocompleteView(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomSearchThrottle]
    error_class = EntityValidationError

    def get_queryset(self):
        return self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

@extend_schema(tags=["Entities"])
class EntityAutocompleteAPIView(BaseAutocompleteView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CustomThrottle]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        qs = Entity.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(slug__icontains=query)
            )

        qs = qs.order_by("slug")[:10]

        return Response(
            [
                {
                    "id": e.id,
                    "label": e.name,
                    "value": e.name,
                }
                for e in qs
            ]
        )
