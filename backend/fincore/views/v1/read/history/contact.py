from drf_spectacular.utils import extend_schema
from fincore.models import Contact
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.contact import ContactReadSerializerV1
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


@extend_schema(tags=["Finance: Contact"])
class ContactHistoryAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, FincorePermission]
    serializer_class = ContactReadSerializerV1

    def get_queryset(self):
        return Contact.history.filter(id=self.kwargs["pk"])
