from dal import autocomplete
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from helpdesk.models import BugReport, SupportTicket


class BaseAutocompleteView(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]
    model = None

    def get_queryset(self):
        return self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

class BugReportAutocomplete(BaseAutocompleteView):
    model = BugReport

    def get_queryset(self):
        qs = super().get_queryset()

        if self.q:
            qs = qs.filter(
                Q(ticket_number__icontains=self.q)
                | Q(title__icontains=self.q)
                | Q(description__icontains=self.q)
            )

        return qs.order_by("-created_at")



class SupportTicketAutocomplete(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SupportTicket.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

        if self.q:
            qs = qs.filter(
                Q(ticket_number__icontains=self.q)
                | Q(subject__icontains=self.q)
                | Q(email__icontains=self.q)
            )

        return qs.order_by("-created_at")
