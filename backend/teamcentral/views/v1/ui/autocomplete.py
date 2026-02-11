from dal import autocomplete
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated

from teamcentral.models import (
    Address,
    Department,
    LeaveType,
    MemberProfile,
    Role,
    Team,
)


class BaseAutocompleteView(autocomplete.Select2QuerySetView):
    permission_classes = [IsAuthenticated]
    model = None
    search_fields = ()

    def get_queryset(self):
        qs = self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True,
        )

        if self.q and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": self.q})
            qs = qs.filter(query)

        return qs


class AddressAutocomplete(BaseAutocompleteView):
    model = Address
    search_fields = ("address", "city", "state", "country")

    def get_queryset(self):
        return super().get_queryset().order_by("city")


class DepartmentAutocomplete(BaseAutocompleteView):
    model = Department
    search_fields = ("name", "code")

    def get_queryset(self):
        return super().get_queryset().order_by("name")


class TeamAutocomplete(BaseAutocompleteView):
    model = Team
    search_fields = ("name",)

    def get_queryset(self):
        return super().get_queryset().order_by("name")


class RoleAutocomplete(BaseAutocompleteView):
    model = Role
    search_fields = ("title", "code")

    def get_queryset(self):
        return super().get_queryset().order_by("rank")


class MemberProfileAutocomplete(BaseAutocompleteView):
    model = MemberProfile
    search_fields = ("email", "member_code", "first_name", "last_name")

    def get_queryset(self):
        return super().get_queryset().order_by("email")


class LeaveTypeAutocomplete(BaseAutocompleteView):
    model = LeaveType
    search_fields = ("name", "code")

    def get_queryset(self):
        return super().get_queryset().order_by("name")
