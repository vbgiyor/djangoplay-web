from django_filters import rest_framework as dj_filters
from rest_framework import filters as drf_filters
from rest_framework import permissions, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from .models import Client, ClientOrganization, Organization
from .serializers import ClientCreateSerializer, ClientOrganizationCreateSerializer, ClientOrganizationReadSerializer, ClientSerializer, OrganizationCreateSerializer, OrganizationSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ClientFilter(dj_filters.FilterSet):
    current_country = dj_filters.CharFilter(field_name="current_country__name", lookup_expr='icontains')
    current_region = dj_filters.CharFilter(field_name="current_region__name", lookup_expr='icontains')
    current_state = dj_filters.CharFilter(field_name="current_state__name", lookup_expr='icontains')
    current_industry = dj_filters.CharFilter(field_name="current_industry__name", lookup_expr='icontains')
    current_organization = dj_filters.CharFilter(field_name="current_organization__name", lookup_expr='icontains')

    class Meta:
        model = Client
        fields = ['current_country', 'current_region', 'current_state', 'current_industry', 'current_organization']

class ClientViewSet(BulkModelViewSet, viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [dj_filters.DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]
    filterset_class = ClientFilter
    search_fields = ['email', 'phone', 'name']
    ordering_fields = ['created_at', 'name', 'current_org_joining_day']
    ordering = ['created_at']
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        is_bulk = isinstance(request.data, list)
        serializer = ClientCreateSerializer(data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = ClientCreateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ClientOrganizationCreateViewSet(viewsets.ModelViewSet):
    queryset = ClientOrganization.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ClientOrganizationReadSerializer
        return ClientOrganizationCreateSerializer

class OrganizationViewSet(BulkModelViewSet, viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [dj_filters.DjangoFilterBackend, drf_filters.OrderingFilter, drf_filters.SearchFilter]
    filterset_fields = ['industry__name', 'headquarter_city__name']
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
    ordering = ['created_at']
    pagination_class = StandardResultsSetPagination

    def create(self, request, *args, **kwargs):
        is_bulk = isinstance(request.data, list)
        serializer = OrganizationCreateSerializer(data=request.data, many=is_bulk)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = OrganizationCreateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
