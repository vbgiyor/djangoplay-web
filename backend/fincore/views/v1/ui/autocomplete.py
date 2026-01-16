from dal import autocomplete
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from fincore.models import Address, Contact, TaxProfile


@extend_schema(exclude=True)
class FincoreAutocompleteView(autocomplete.Select2QuerySetView):

    """
    Unified autocomplete endpoint for fincore entities.
    """

    model = None
    def get_search_fields(self):
        return ()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.model.objects.none()

        qs = self.model.objects.all()

        if self.q:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": self.q})
            qs = qs.filter(query)

        return qs[:10]


class ContactAutocompleteView(FincoreAutocompleteView):
    model = Contact
    def get_search_fields(self):
        return ("name", "email", "phone_number")


class AddressAutocompleteView(FincoreAutocompleteView):
    model = Address
    def get_search_fields(self):
        return ("street_address", "postal_code", "city__name")


class TaxProfileAutocompleteView(FincoreAutocompleteView):
    model = TaxProfile
    def get_search_fields(self):
        return ("tax_identifier",)
