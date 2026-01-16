from drf_spectacular.utils import extend_schema
from fincore.models import Contact
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.contact import ContactReadSerializerV1
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated


@extend_schema(tags=["Finance: Contact"])
class ContactDetailAPIView(RetrieveAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactReadSerializerV1
    permission_classes = [IsAuthenticated, FincorePermission]
