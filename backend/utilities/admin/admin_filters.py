"""
Custom Django admin filters for the locations app.
These filters are designed to handle hierarchical location data (GlobalRegion -> Country -> Region -> SubRegion -> City -> Location)
and common status filters like active/inactive (soft delete).

Usage in admin.py:
- Import: from .filters import *
- Assign to list_filter in ModelAdmin classes, e.g., list_filter = (IsActiveFilter, CountryFilter, RegionFilter)
- For conditional filters, override get_list_filter in ModelAdmin.

Filters are reusable across models via dynamic queryset methods.
"""

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from teamcentral.models import Department, EmployeeType, EmploymentStatus, LeaveType, MemberStatus, Role


class IsActiveFilter(admin.SimpleListFilter):

    """
    Filter for active/inactive status (handles soft deletes via deleted_at).
    Choices: All, Active, Inactive.
    """

    title = _('Status')
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('all', _('All')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deleted_at__isnull=True, is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(Q(deleted_at__isnull=False) | Q(is_active=False))
        return queryset

class GlobalRegionFilter(admin.SimpleListFilter):

    """Used by CustomCountry (M2M) – can be reused on any model that adds the same M2M."""

    title = _('Global Region')
    parameter_name = 'global_region'

    def lookups(self, request, model_admin):
        from locations.models import GlobalRegion
        return [
            (gr.id, gr.name)
            for gr in GlobalRegion.objects.filter(
                deleted_at__isnull=True, is_active=True
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(global_regions__id=self.value())
        return queryset

class GlobalRegionNameFilter(admin.SimpleListFilter):
    title = _('Global Region Name')
    parameter_name = 'name'

    def lookups(self, request, model_admin):
        from locations.models import GlobalRegion
        regions = GlobalRegion.objects.filter(
            deleted_at__isnull=True,
            is_active=True
        ).order_by('name')
        return [(region.name, region.name) for region in regions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(name__exact=self.value())
        return queryset

class CountryFilter(admin.SimpleListFilter):

    """
    Filter for CustomCountry (used in RegionAdmin, SubRegionAdmin, CityAdmin, LocationAdmin, TimezoneAdmin).
    - For direct FK (e.g., CustomRegion.country): filters by country_id.
    - For indirect (e.g., CustomSubRegion.region__country): filters by region__country_id.
    - For M2M (e.g., CustomCountry.global_regions): not applicable here.
    Shows active countries only.
    """

    title = _('Country')
    parameter_name = 'country'

    def lookups(self, request, model_admin):
        from locations.models import CustomCountry
        return [(c.id, c.name) for c in CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')]

    def queryset(self, request, queryset):
        from locations.models import CustomCountry, Timezone
        if self.value():
            model = queryset.model
            if hasattr(model, 'country'):  # Direct FK: CustomRegion
                return queryset.filter(country_id=self.value())
            elif hasattr(model, 'region'):  # Indirect via region: CustomSubRegion
                return queryset.filter(region__country_id=self.value())
            elif hasattr(model, 'subregion'):  # Indirect via subregion->region->country: CustomCity
                return queryset.filter(subregion__region__country_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city->subregion->region->country: Location
                return queryset.filter(city__subregion__region__country_id=self.value())
            elif model == Timezone:  # For Timezone.country_code (exact match)
                return queryset.filter(country_code__exact=CustomCountry.objects.get(id=self.value()).country_code)
        return queryset

class RegionFilter(admin.SimpleListFilter):

    """
    Filter for CustomRegion (used in SubRegionAdmin, CityAdmin, LocationAdmin).
    - For direct FK (e.g., CustomSubRegion.region): filters by region_id.
    - For indirect (e.g., CustomCity.subregion__region): filters by subregion__region_id.
    Shows active regions only, dynamically scoped by country if provided in request.GET.
    """

    title = _('Region/State')
    parameter_name = 'region'

    def lookups(self, request, model_admin):
        from locations.models import CustomRegion
        regions = CustomRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to country if provided (e.g., via CountryFilter)
        country_id = request.GET.get('country')
        if country_id:
            regions = regions.filter(country_id=country_id)
        return [(r.id, r.name) for r in regions]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if hasattr(model, 'region'):  # Direct FK: CustomSubRegion
                return queryset.filter(region_id=self.value())
            elif hasattr(model, 'subregion'):  # Indirect via subregion: CustomCity
                return queryset.filter(subregion__region_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city->subregion->region: Location
                return queryset.filter(city__subregion__region_id=self.value())
        return queryset


class SubRegionFilter(admin.SimpleListFilter):

    """
    Filter for CustomSubRegion (used in CityAdmin, LocationAdmin).
    - For direct FK (e.g., CustomCity.subregion): filters by subregion_id.
    - For indirect (e.g., Location.city__subregion): filters by city__subregion_id.
    Shows active subregions only, dynamically scoped by region (and country) if provided.
    """

    title = _('Subregion/District')
    parameter_name = 'subregion'

    def lookups(self, request, model_admin):
        from locations.models import CustomSubRegion
        subregions = CustomSubRegion.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to region if provided
        region_id = request.GET.get('region')
        if region_id:
            subregions = subregions.filter(region_id=region_id)
        # Further scope to country if no region but country provided
        elif request.GET.get('country'):
            country_id = request.GET.get('country')
            subregions = subregions.filter(region__country_id=country_id)
        return [(sr.id, sr.name) for sr in subregions]

    def queryset(self, request, queryset):
        if self.value():
            model = queryset.model
            if hasattr(model, 'subregion'):  # Direct FK: CustomCity
                return queryset.filter(subregion_id=self.value())
            elif hasattr(model, 'city'):  # Indirect via city: Location
                return queryset.filter(city__subregion_id=self.value())
        return queryset


class CityFilter(admin.SimpleListFilter):

    """
    Filter for CustomCity (used in Locations app).
    Filters by city_id directly.
    Shows active cities only, dynamically scoped by subregion (and higher levels) if provided.
    """

    title = _('City')
    parameter_name = 'city'

    def lookups(self, request, model_admin):
        from locations.models import CustomCity
        cities = CustomCity.objects.filter(deleted_at__isnull=True, is_active=True).order_by('name')
        # Scope to subregion if provided
        subregion_id = request.GET.get('subregion')
        if subregion_id:
            cities = cities.filter(subregion_id=subregion_id)
        # Further scope to region if no subregion but region provided
        elif request.GET.get('region'):
            region_id = request.GET.get('region')
            cities = cities.filter(subregion__region_id=region_id)
        # Further scope to country if no region/subregion but country provided
        elif request.GET.get('country'):
            country_id = request.GET.get('country')
            cities = cities.filter(subregion__region__country_id=country_id)
        return [(c.id, c.name) for c in cities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(city_id=self.value())
        return queryset


class TimezoneFilter(admin.SimpleListFilter):

    """
    Filter for Timezone (used in CityAdmin).
    Filters by timezone_id directly.
    Shows active timezones only, optionally scoped by country if provided.
    """

    title = _('Timezone')
    parameter_name = 'timezone'

    def lookups(self, request, model_admin):
        from locations.models import CustomCountry, Timezone
        timezones = Timezone.objects.filter(deleted_at__isnull=True, is_active=True).order_by('display_name')
        # Scope to country if provided
        country_id = request.GET.get('country')
        if country_id:
            country_code = CustomCountry.objects.get(id=country_id).country_code
            timezones = timezones.filter(country_code=country_code)
        return [(tz.timezone_id, tz.display_name) for tz in timezones]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(timezone_id=self.value())
        return queryset


class LocationSourceFilter(admin.SimpleListFilter):

    """
    Filter for location_source (common across models: GlobalRegion, CustomCountry, etc.).
    Shows distinct active sources.
    """

    title = _('Location Source')
    parameter_name = 'location_source'

    def lookups(self, request, model_admin):
        model = model_admin.model
        sources = model.objects.filter(deleted_at__isnull=True, is_active=True).values_list('location_source', flat=True).distinct().exclude(location_source__isnull=True).exclude(location_source__exact='')
        return [(s, s) for s in sorted(sources)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(location_source__exact=self.value())
        return queryset


class CurrencyCodeFilter(admin.SimpleListFilter):

    """
    Filter for currency_code (specific to CustomCountryAdmin).
    Shows distinct active currency codes.
    """

    title = _('Currency Code')
    parameter_name = 'currency_code'

    def lookups(self, request, model_admin):
        from locations.models import CustomCountry
        currencies = CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).values_list('currency_code', flat=True).distinct().exclude(currency_code__isnull=True).exclude(currency_code__exact='')
        return [(c, c) for c in sorted(currencies)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(currency_code__exact=self.value())
        return queryset


class CountryCodeFilter(admin.SimpleListFilter):

    """
    Filter for country_code (used in TimezoneAdmin for country_code field).
    Shows active countries' codes.
    """

    title = _('Country Code')
    parameter_name = 'country_code'

    def lookups(self, request, model_admin):
        from locations.models import CustomCountry
        return [(c.country_code, c.country_code) for c in CustomCountry.objects.filter(deleted_at__isnull=True, is_active=True).exclude(country_code__isnull=True).order_by('country_code')]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country_code__exact=self.value())
        return queryset

class GMTOffsetFilter(admin.SimpleListFilter):

    """
    Filter for GMT Offset (January) in TimezoneAdmin.
    Allows filtering by distinct gmt_offset_jan values.
    """

    title = _('GMT Offset (Jan)')
    parameter_name = 'gmt_offset_jan'

    def lookups(self, request, model_admin):
        offsets = (
            model_admin.model.objects
            .filter(deleted_at__isnull=True)
            .values_list('gmt_offset_jan', flat=True)
            .distinct()
            .order_by('gmt_offset_jan')
        )
        return [(str(o), f"{o:+.2f}") for o in offsets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(gmt_offset_jan=self.value())
        return queryset


class DSTOffsetFilter(admin.SimpleListFilter):

    """
    Filter for DST Offset (July) in TimezoneAdmin.
    Allows filtering by distinct dst_offset_jul values.
    """

    title = _('DST Offset (Jul)')
    parameter_name = 'dst_offset_jul'

    def lookups(self, request, model_admin):
        offsets = (
            model_admin.model.objects
            .filter(deleted_at__isnull=True)
            .values_list('dst_offset_jul', flat=True)
            .distinct()
            .order_by('dst_offset_jul')
        )
        return [(str(o), f"{o:+.2f}") for o in offsets]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(dst_offset_jul=self.value())
        return queryset


class AddressTypeFilter(admin.SimpleListFilter):
    title = _('Address Type')
    parameter_name = 'addr_type'

    def lookups(self, request, model_admin):
        from teamcentral.models import Address
        addr_type = (Address.objects
                     .exclude(address_type__exact='')
                     .values_list('address_type', flat=True)
                     .distinct()
                     .order_by('address_type'))
        return [(c, c) for c in addr_type if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(address_type__iexact=self.value())
        return queryset


class AddressCountryFilter(admin.SimpleListFilter):
    title = _('Country')
    parameter_name = 'addr_country'

    def lookups(self, request, model_admin):
        from teamcentral.models import Address
        countries = (Address.objects
                     .exclude(country__exact='')
                     .values_list('country', flat=True)
                     .distinct()
                     .order_by('country'))
        return [(c, c) for c in countries if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(country__iexact=self.value())
        return queryset


class AddressStateFilter(admin.SimpleListFilter):
    title = _('State')
    parameter_name = 'addr_state'

    def lookups(self, request, model_admin):
        from teamcentral.models import Address
        qs = Address.objects.exclude(state__exact='')

        # Auto-scope by selected country
        country = request.GET.get('addr_country')
        if country:
            qs = qs.filter(country__iexact=country)

        states = (qs.values_list('state', flat=True)
                  .distinct()
                  .order_by('state'))
        return [(s, s) for s in states if s]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(state__iexact=self.value())
        return queryset


class AddressCityFilter(admin.SimpleListFilter):
    title = _('City')
    parameter_name = 'addr_city'

    def lookups(self, request, model_admin):
        from teamcentral.models import Address
        qs = Address.objects.exclude(city__exact='')

        # Auto-scope by country + state
        country = request.GET.get('addr_country')
        state = request.GET.get('addr_state')

        if country:
            qs = qs.filter(country__iexact=country)
        if state:
            qs = qs.filter(state__iexact=state)

        cities = (qs.values_list('city', flat=True)
                  .distinct()
                  .order_by('city'))
        return [(c, c) for c in cities if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(city__iexact=self.value())
        return queryset


class DepartmentFilter(admin.SimpleListFilter):
    title = _('Code')
    parameter_name = 'dept_code'

    def lookups(self, request, model_admin):
        # from teamcentral.models import Department
        from teamcentral.models import Department
        qs = Department.objects.exclude(code__exact='')

        # Auto-scope by country + state
        code = request.GET.get('dept_code')

        if code:
            qs = qs.filter(code__iexact=code)

        codes = (qs.values_list('code', flat=True)
                  .distinct()
                  .order_by('code'))
        return [(c, c) for c in codes if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(code__iexact=self.value())
        return queryset

class GenericCodeNameFilter(admin.SimpleListFilter):

    """
    Works for any model that has:
        - code
        - name OR title
        - is_active + deleted_at
    Just subclass and set the four class variables.
    """

    title = _("Code")
    parameter_name = "code_filter"
    model = None          # ← must be set
    field_name = None     # ← e.g. "role", "department", "employee_type"
    display_field = "name"  # ← "title" for Role, "name" for others

    def lookups(self, request, model_admin):
        if not self.model:
            return []
        qs = self.model.objects.filter(
            deleted_at__isnull=True,
            is_active=True
        ).only("id", "code", self.display_field).order_by("code")

        return [
            (obj.id, f"{obj.code} - {getattr(obj, self.display_field) or ''}".strip())
            for obj in qs
            if obj.code
        ]

    def queryset(self, request, queryset):
        if self.value():
            lookup = "id"
            return queryset.filter(**{lookup: self.value()})
        return queryset


# -------------------------------------------------------------------
# One-liner filters using the base class above
# -------------------------------------------------------------------
class RoleFilter(GenericCodeNameFilter):
    title = _("Role")
    parameter_name = "role"
    model = Role
    field_name = "role"
    display_field = "title"


class DepartmentFilter(GenericCodeNameFilter):
    title = _("Department")
    parameter_name = "department"
    model = Department
    field_name = "department"
    display_field = "name"


class EmployeeTypeFilter(GenericCodeNameFilter):
    title = _("Employee Type")
    parameter_name = "employee_type"
    model = EmployeeType
    field_name = "employee_type"
    display_field = "name"


class EmploymentStatusFilter(GenericCodeNameFilter):
    title = _("Employment Status")
    parameter_name = "employment_status"
    model = EmploymentStatus
    field_name = "employment_status"
    display_field = "name"


class MemberStatusFilter(GenericCodeNameFilter):
    title = _("Member Status")
    parameter_name = "member_status"
    model = MemberStatus
    field_name = "member_status"
    display_field = "name"


class LeaveTypeFilter(GenericCodeNameFilter):
    title = _("Leave Type")
    parameter_name = "leave_type"
    model = LeaveType
    field_name = "leave_type"
    display_field = "name"


class BugStatusFilter(admin.SimpleListFilter):
    title = _("Bug Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        from helpdesk.models import BugStatus
        return [(k, v.label) for k, v in BugStatus.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

class BugSeverityFilter(admin.SimpleListFilter):
    title = _("Severity")
    parameter_name = "severity"

    def lookups(self, request, model_admin):
        from helpdesk.models import Severity
        return [(k, v.label) for k, v in Severity.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(severity=self.value())
        return queryset

class BugReporterFilter(admin.SimpleListFilter):
    title = _("Reporter")
    parameter_name = "reporter"

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.select_related("reporter").values_list(
            "reporter_id", "reporter__email"
        ).distinct()
        return [(pk, email) for pk, email in qs if pk]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(reporter_id=self.value())
        return queryset

class HasExternalIssueURLFilter(admin.SimpleListFilter):
    title = _("External Issue URL")
    parameter_name = "has_external_issue"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Has URL")),
            ("no", _("No URL")),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(external_issue_url__isnull=True).exclude(external_issue_url="")
        if self.value() == "no":
            return queryset.filter(
                Q(external_issue_url__isnull=True) | Q(external_issue_url="")
            )
        return queryset

class SupportStatusFilter(admin.SimpleListFilter):
    title = _("Support Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        from helpdesk.models import SupportStatus
        return [(k, v.label) for k, v in SupportStatus.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

class SupportPriorityFilter(admin.SimpleListFilter):
    title = _("Priority")
    parameter_name = "priority"

    def lookups(self, request, model_admin):
        from helpdesk.models import Priority
        return [(k, v.label) for k, v in Priority.choices]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())
        return queryset


class SupportCreatedByFilter(admin.SimpleListFilter):
    title = _("Created By")
    parameter_name = "created_by"

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.select_related("created_by").values_list(
            "created_by_id", "created_by__email"
        ).distinct()
        return [(pk, email) for pk, email in qs if pk]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(created_by_id=self.value())
        return queryset


class FileTypeFilter(admin.SimpleListFilter):
    title = _("File Type")
    parameter_name = "file"

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.values_list(
            "file", flat=True
        ).distinct().exclude(file__isnull=True).exclude(file="")
        return [(t, t.upper()) for t in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(file=self.value())
        return queryset


class FileCategoryFilter(admin.SimpleListFilter):

    """
    Logical file grouping filter for FileUpload.
    Derived from file extension.
    """

    title = _("File Category")
    parameter_name = "file_category"

    IMAGE_EXT = ("jpg", "jpeg", "png", "gif")
    VIDEO_EXT = ("mp4",)
    DOCUMENT_EXT = ("pdf", "txt", "log")
    ARCHIVE_EXT = ("zip",)

    def lookups(self, request, model_admin):
        return (
            ("image", _("Image")),
            ("video", _("Video")),
            ("document", _("Document")),
            ("archive", _("Archive")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        def build_q(exts):
            q = Q()
            for ext in exts:
                q |= Q(file__iendswith=f".{ext}")
            return q

        if value == "image":
            return queryset.filter(build_q(self.IMAGE_EXT))
        if value == "video":
            return queryset.filter(build_q(self.VIDEO_EXT))
        if value == "document":
            return queryset.filter(build_q(self.DOCUMENT_EXT))
        if value == "archive":
            return queryset.filter(build_q(self.ARCHIVE_EXT))

        return queryset


class HasAttachmentsFilter(admin.SimpleListFilter):

    """
    Filters models that use GenericRelation(FileUpload)
    """

    title = _("Attachments")
    parameter_name = "has_attachments"

    def lookups(self, request, model_admin):
        return (
            ("yes", _("Has Attachments")),
            ("no", _("No Attachments")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == "yes":
            return queryset.filter(attachments__isnull=False).distinct()
        if value == "no":
            return queryset.filter(attachments__isnull=True)
        return queryset


class TicketTypeFilter(admin.SimpleListFilter):

    """
    Filter FileUpload by linked object type (GenericForeignKey).
    """

    title = _("Ticket Type")
    parameter_name = "ticket_type"

    def lookups(self, request, model_admin):
        return (
            ("bug", _("Bug")),
            ("support", _("Support")),
            ("other", _("Other")),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        from helpdesk.models import BugReport, SupportTicket
        bug_ct = ContentType.objects.get_for_model(BugReport)
        support_ct = ContentType.objects.get_for_model(SupportTicket)

        if value == "bug":
            return queryset.filter(content_type=bug_ct)

        if value == "support":
            return queryset.filter(content_type=support_ct)

        if value == "other":
            return queryset.exclude(
                content_type__in=[bug_ct, support_ct]
            )

        return queryset


def changelist_filter(field_name=None, *, model=None):
    """
    Universal list filter that works for:

      • FK on the admin model:
          changelist_filter("role")            → filters by role_id
          changelist_filter("manager")         → filters by manager_id

      • Self-model filter (by pk):
          changelist_filter(model=EmploymentStatus)  → filters by pk

      • Non-FK fields (status, type, etc.):
          changelist_filter("status")          → filters by status field
                                                (choices or distinct values)
    """
    if field_name is None and model is None:
        raise ValueError("Either field_name or model must be provided")

    class UniversalFilter(admin.SimpleListFilter):
        # Clean parameter name for query string
        parameter_name = field_name or model._meta.model_name

        def __init__(self, request, params, model_cls, model_admin):
            """
            model_cls = admin model (e.g., Employee)
            model     = explicit model passed to factory (for self-filter)
            """
            self.model_cls = model_cls
            self.model_admin = model_admin

            # Determine mode: "fk", "field", or "pk"
            if field_name:
                try:
                    field = model_cls._meta.get_field(field_name)
                except FieldDoesNotExist:
                    raise FieldDoesNotExist(
                        f"{model_cls.__name__} has no field named '{field_name}'"
                    )

                self.field = field

                # Is this a ForeignKey / OneToOne?
                if getattr(field, "remote_field", None) is not None:
                    self.mode = "fk"
                    self.related_model = field.remote_field.model
                else:
                    self.mode = "field"
                    self.related_model = None

                self.title = _(field.verbose_name).title()
            else:
                # Self-filter by primary key of the given model
                self.field = None
                self.mode = "pk"
                self.related_model = model or model_cls
                self.title = _(self.related_model._meta.verbose_name_plural).title()

            super().__init__(request, params, model_cls, model_admin)

        # ---------- Lookups ----------

        def _fk_lookups(self):
            """
            Build lookups for FK fields, respecting deleted_at/is_active if present.
            """
            qs = self.related_model._default_manager.all()

            # Make `deleted_at` / `is_active` filtering safe & generic
            if "deleted_at" in [f.name for f in self.related_model._meta.fields]:
                qs = qs.filter(deleted_at__isnull=True)
            if "is_active" in [f.name for f in self.related_model._meta.fields]:
                qs = qs.filter(is_active=True)

            return [(obj.pk, str(obj)) for obj in qs.order_by("pk")]

        def _pk_lookups(self):
            """
            Self-filter by pk of the admin model.
            """
            qs = self.model_cls._default_manager.all()
            return [(obj.pk, str(obj)) for obj in qs.order_by("pk")]

        def _field_lookups(self, request):
            """
            Lookups for non-FK fields:

            - If the field has choices → use those.
            - Else → use distinct values from the admin queryset.
            """
            # 1) Choices-based fields
            if getattr(self.field, "choices", None):
                # self.field.choices is already iterable of (value, label)
                return [(value, str(label)) for value, label in self.field.choices]

            # 2) Fallback: distinct values from queryset
            qs = self.model_admin.get_queryset(request)

            values = (
                qs.values_list(field_name, flat=True)
                .order_by(field_name)
                .distinct()
            )

            # Skip NULLs
            values = [v for v in values if v is not None]

            return [(v, str(v)) for v in values]

        def lookups(self, request, model_admin):
            if self.mode == "fk":
                return self._fk_lookups()
            elif self.mode == "pk":
                return self._pk_lookups()
            else:  # "field"
                return self._field_lookups(request)

        # ---------- Filtering ----------

        def queryset(self, request, queryset):
            value = self.value()
            if value in (None, ""):
                return queryset

            if self.mode == "fk":
                # Filtering via ForeignKey → use {field_name}_id
                return queryset.filter(**{f"{field_name}_id": value})

            if self.mode == "pk":
                # Self-filter by primary key
                return queryset.filter(pk=value)

            # mode == "field" → normal field filter
            # Cast the string value from the URL into proper Python type
            prepared_value = self.field.get_prep_value(value)
            return queryset.filter(**{field_name: prepared_value})

    return UniversalFilter

# ===================================================================
# 4. Export everything
# ===================================================================

# __all__ = [
#     'IsActiveFilter',
#     'changelist_filter',
#     # 'GlobalRegionFilter',
#     # 'CountryFilter',
#     # 'RegionFilter',
#     # 'SubRegionFilter',
#     # 'CityFilter',

#     # 'RoleFilter',
#     # 'DepartmentFilter',
#     # 'EmployeeTypeFilter',
#     # 'EmploymentStatusFilter',
#     # 'MemberStatusFilter',
#     # 'LeaveTypeFilter',
#     # 'GenericCodeNameFilter',
# ]

__all__ = [
    'IsActiveFilter',
    'CountryFilter',
    'AddressCountryFilter',
    'AddressStateFilter',
    'AddressCityFilter',
    'changelist_filter',
    'FileTypeFilter',
    'SupportStatusFilter',
    'SupportPriorityFilter',
    'HasExternalIssueURLFilter',
    'BugReporterFilter',
    'BugSeverityFilter',
    'BugStatusFilter'
]
