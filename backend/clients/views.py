from django_filters import rest_framework as dj_filters
from rest_framework import filters as drf_filters
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from .models import Client
from .serializers import ClientSerializer


class ClientFilter(dj_filters.FilterSet):
    current_country = dj_filters.CharFilter(field_name="current_country", lookup_expr='icontains')
    current_region = dj_filters.CharFilter(field_name="current_region", lookup_expr='icontains')

    class Meta:
        model = Client
        fields = ['current_country', 'current_region']


class ClientViewSet(BulkModelViewSet, viewsets.ModelViewSet):

    """
    A viewset for viewing, creating, updating, and deleting Client instances.
    Supports filtering, ordering, pagination, and bulk operations.
    """

    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [dj_filters.DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]
    filterset_class = ClientFilter
    search_fields = ['email', 'phone', 'name']
    ordering_fields = ['created_at', 'name', 'current_org_joining_day']
    ordering = ['created_at']  # Default ordering

    def create(self, request, *args, **kwargs):
        """Create a new Client or multiple Clients (bulk)."""
        is_bulk = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update an existing Client or multiple Clients (bulk)."""
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a Client instance."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
