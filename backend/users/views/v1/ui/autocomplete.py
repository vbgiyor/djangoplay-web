from dal import autocomplete
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from users.models import (
    Address,
    Department,
    Employee,
    LeaveType,
    Member,
    Role,
    SupportTicket,
    Team,
)


class BaseAutocompleteView(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )


class EmployeeAutocomplete(BaseAutocompleteView):
    model = Employee

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q)
                | Q(email__icontains=self.q)
                | Q(first_name__icontains=self.q)
                | Q(last_name__icontains=self.q)
            )
        return qs.order_by("username")


class MemberAutocomplete(BaseAutocompleteView):
    model = Member

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(email__icontains=self.q)
        return qs.order_by("email")


class DepartmentAutocomplete(BaseAutocompleteView):
    model = Department

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs.order_by("name")


class TeamAutocomplete(BaseAutocompleteView):
    model = Team

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(name__icontains=self.q)
        return qs.order_by("name")


class RoleAutocomplete(BaseAutocompleteView):
    model = Role

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(title__icontains=self.q)
        return qs.order_by("rank")


class AddressAutocomplete(BaseAutocompleteView):
    model = Address

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(city__icontains=self.q)
                | Q(state__icontains=self.q)
                | Q(country__icontains=self.q)
            )
        return qs.order_by("city")


class LeaveTypeAutocomplete(BaseAutocompleteView):
    model = LeaveType

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(name__icontains=self.q)
                | Q(code__icontains=self.q)
            )
        return qs.order_by("name")


class SupportAutocomplete(BaseAutocompleteView):
    model = SupportTicket

    def get_queryset(self):
        qs = super().get_queryset()
        if self.q:
            qs = qs.filter(
                Q(ticket_number__icontains=self.q)
                | Q(subject__icontains=self.q)
                | Q(email__icontains=self.q)
            )
        return qs.order_by("-created_at")
