from dal import autocomplete
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from users.models import Employee


class EmployeeAutocomplete(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Employee.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q)
                | Q(email__icontains=self.q)
                | Q(first_name__icontains=self.q)
                | Q(last_name__icontains=self.q)
                | Q(employee_code__icontains=self.q)
            )

        return qs.order_by("username")
