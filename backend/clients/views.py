from django_filters import rest_framework as dj_filters
from rest_framework import filters as drf_filters
from rest_framework import permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from .models import Client, ClientOrganization, Organization
from .serializers import (
    ClientCreateSerializer,
    ClientOrganizationCreateSerializer,
    ClientOrganizationReadSerializer,
    ClientSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):

    """Custom pagination class for consistent API responses."""

    page_size = 10  # Default number of items per page
    page_size_query_param = 'page_size'  # Query param to override page size
    max_page_size = 100  # Maximum allowed page size


class ClientFilter(dj_filters.FilterSet):

    """Filter set for Client model with case-insensitive search on related fields."""

    current_country = dj_filters.CharFilter(
        field_name="current_country__name",
        lookup_expr='icontains')
    current_region = dj_filters.CharFilter(
        field_name="current_region__name",
        lookup_expr='icontains')
    current_state = dj_filters.CharFilter(
        field_name="current_state__name",
        lookup_expr='icontains')
    current_industry = dj_filters.CharFilter(
        field_name="current_industry__name",
        lookup_expr='icontains')
    current_organization = dj_filters.CharFilter(
        field_name="current_organization__name",
        lookup_expr='icontains')

    class Meta:
        model = Client
        fields = [
            'current_country',
            'current_region',
            'current_state',
            'current_industry',
            'current_organization']


class ClientViewSet(BulkModelViewSet, viewsets.ModelViewSet):

    """ViewSet for managing Client instances with bulk operations."""

    queryset = Client.objects.all()  # Base queryset for all clients
    serializer_class = ClientSerializer  # Default serializer for responses
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    filter_backends = [
        dj_filters.DjangoFilterBackend,
        drf_filters.OrderingFilter,
        drf_filters.SearchFilter]  # Enable filtering, ordering, and search
    filterset_class = ClientFilter  # Custom filter class
    search_fields = ['email', 'phone', 'name']  # Fields for search queries
    ordering_fields = ['created_at', 'name', 'current_org_joining_day']  # Fields for ordering
    ordering = ['created_at']  # Default ordering
    pagination_class = StandardResultsSetPagination  # Custom pagination

    def create(self, request, *args, **kwargs):
        """Create one or multiple Client instances."""
        is_bulk = isinstance(request.data, list)  # Check if request is for bulk create
        serializer = ClientCreateSerializer(data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update a Client instance with partial updates enabled."""
        partial = kwargs.pop('partial', True)  # Allow partial updates
        instance = self.get_object()
        serializer = ClientCreateSerializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Delete a Client instance."""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClientOrganizationCreateViewSet(viewsets.ModelViewSet):

    """ViewSet for managing ClientOrganization relationships."""

    queryset = ClientOrganization.objects.all()  # Base queryset for client-organization relations
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    pagination_class = StandardResultsSetPagination  # Custom pagination

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['list', 'retrieve']:  # Use read serializer for list/retrieve
            return ClientOrganizationReadSerializer
        return ClientOrganizationCreateSerializer  # Use create serializer for other actions


class OrganizationViewSet(BulkModelViewSet, viewsets.ModelViewSet):

    """ViewSet for managing Organization instances with bulk operations."""

    queryset = Organization.objects.all()  # Base queryset for all organizations
    serializer_class = OrganizationSerializer  # Default serializer for responses
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    filter_backends = [
        dj_filters.DjangoFilterBackend,
        drf_filters.OrderingFilter,
        drf_filters.SearchFilter]  # Enable filtering, ordering, and search
    filterset_fields = ['industry__name', 'headquarter_city__name']  # Fields for filtering
    search_fields = ['name']  # Fields for search queries
    ordering_fields = ['created_at', 'name']  # Fields for ordering
    ordering = ['created_at']  # Default ordering
    pagination_class = StandardResultsSetPagination  # Custom pagination

    def create(self, request, *args, **kwargs):
        """Create one or multiple Organization instances."""
        is_bulk = isinstance(request.data, list)  # Check if request is for bulk create
        serializer = OrganizationCreateSerializer(
            data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update an Organization instance with partial updates enabled."""
        partial = kwargs.pop('partial', True)  # Allow partial updates
        instance = self.get_object()
        serializer = OrganizationCreateSerializer(
            instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
