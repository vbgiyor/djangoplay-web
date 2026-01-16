from drf_spectacular.utils import extend_schema
from fincore.models import Contact
from fincore.permissions import FincorePermission
from fincore.serializers.v1.read.contact import ContactReadSerializerV1
from fincore.serializers.v1.write.contact import ContactWriteSerializerV1
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


@extend_schema(tags=["Finance: Contact"])
class ContactCRUDViewSet(ModelViewSet):

    """
    CRUD ViewSet for Contact.

    Responsibilities:
    - Create / Update / Delete
    - Enforce permissions
    - Orchestrate serializers
    """

    permission_classes = (IsAuthenticated, FincorePermission)
    queryset = Contact.objects.all()

    read_serializer_class = ContactReadSerializerV1
    write_serializer_class = ContactWriteSerializerV1

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return self.write_serializer_class
        return self.read_serializer_class
