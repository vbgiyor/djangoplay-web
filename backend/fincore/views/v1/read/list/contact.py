from drf_spectacular.utils import extend_schema
from fincore.models import Contact
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.contact import ContactReadSerializerV1
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated


@extend_schema(tags=["Finance: Contact"])
class ContactListAPIView(ListAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactReadSerializerV1
    permission_classes = [IsAuthenticated, FincorePermission]
