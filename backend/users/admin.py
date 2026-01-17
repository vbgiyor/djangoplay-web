import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import TabularInline, display
from django.db import transaction
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from locations.utils.location_filters import *
from utilities.admin.admin_filters import *
from mailer.flows.member_notifications import send_manual_verification_email_task
from mailer.throttling.throttle import check_and_increment_email_limit
from mailer.engine.unsubscribe import UnsubscribeService

from users.forms.common import AddressForm, UserActivityLogForm
from users.forms.employee import *
from users.forms.member import *
from users.models import *
from users.models.address import Address
from users.models.password_reset_request import PasswordResetRequest
from users.models.signup_request import SignUpRequest
from users.models.user_activity_log import UserActivityLog
from users.utils.helpers import user_is_verified_employee

logger = logging.getLogger(__name__)

class LeaveBalanceInline(TabularInline):
    model = LeaveBalance
    extra = 0
    fields = ('leave_type', 'balance', 'year')
    readonly_fields = ('balance', 'year')
    autocomplete_fields = ['leave_type']
    can_delete = True
    show_change_link = True
    fk_name = 'employee'

class LeaveApplicationInline(TabularInline):
    model = LeaveApplication
    extra = 0
    fields = ('leave_type', 'start_date', 'end_date', 'status')
    readonly_fields = ('start_date', 'end_date', 'status')
    autocomplete_fields = ['leave_type']
    can_delete = True
    show_change_link = True
    fk_name = 'employee'


@AdminIconDecorator.register_with_icon(Employee)
class EmployeeAdmin(BaseAdmin):
    form = EmployeeForm
    list_display = ("full_name", "email", "username", "employee_code",  "department_display", "role_display", "employment_status_display", "employee_type_display", "manager_display", "hire_date", "is_active_employee_display")
    search_fields = ("employee_code", "username", "email", "first_name", "last_name", "phone_number", "national_id")
    list_per_page = 50
    select_related_fields = ['employment_status', 'department', 'role', 'employee_type', 'manager', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('employment_status', queryset=EmploymentStatus.objects.filter(is_active=True)),
        Prefetch('team', queryset=Team.all_objects.filter(is_active=True)),
        Prefetch('department', queryset=Department.all_objects.filter(is_active=True)),
        Prefetch('role', queryset=Role.all_objects.filter(is_active=True)),
        Prefetch('employee_type', queryset=EmployeeType.all_objects.filter(is_active=True)),
    ]
    actions = ["soft_delete", "restore"]
    readonly_fields = ("employee_code", "address_display", "unsubscribed_at", "deleted_at", "deleted_by", "created_at", "created_by", "updated_at", "updated_by")
    base_fieldsets_config = [
        (None, {
            'fields': (
                'first_name', 'last_name', 'username', 'email', 'sso_id', 'sso_provider',
                'phone_number', 'department', 'role', 'team', 'employment_status',
                'employee_type', 'manager', 'address', 'is_active', 'is_verified'
            )
        }),
        (_('Details'), {
            'fields': (
                'job_title', 'approval_limit', 'avatar', 'hire_date', 'termination_date',
                'salary', 'date_of_birth', 'national_id', 'emergency_contact_name',
                'emergency_contact_phone', 'probation_end_date', 'contract_end_date',
                'gender', 'marital_status', 'bank_details', 'notes', 'preferences'
            )
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None): return []
    # def get_search_results(self, request, queryset, search_term):
    #     queryset, use_distinct = super().get_search_results(request, queryset, search_term)
    #     if "employee__search" in request.GET: queryset = queryset.filter(employee_code__icontains=search_term)
    #     return queryset, use_distinct

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        if search_term:
            queryset = queryset.filter(
                Q(email__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )

        return queryset, use_distinct
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .only(
                "employee_code",
                "username",
                "email",
                "first_name",
                "last_name",
                "phone_number",
                "job_title",
                "hire_date",
                "is_active",
                "deleted_at",
                "department__name",
                "role__code",
                "employment_status__code",
                "employee_type__code",
                "manager__employee_code",
                "created_by",
                "updated_by",
                "deleted_by",
            )
        )
    def get_list_filter(self, request):
        base = [IsActiveFilter, changelist_filter("department"), changelist_filter("role"), changelist_filter("employment_status"), changelist_filter("employee_type")]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=Employee))
        return base

    @display(description="Full Name")
    def full_name(self, obj): return obj.get_full_name
    @display(description="Department")
    def department_display(self, obj):
        if obj.department_id:
            try:
                return format_html('<a href="{}">{}</a>', reverse("admin:users_department_change", args=[obj.department.pk]), obj.department)
            except:
                return str(obj.department)
        return "-"
    @display(description="Role")
    def role_display(self, obj):
        if obj.role_id:
            try:
                return format_html('<a href="{}">{}</a>', reverse("admin:users_role_change", args=[obj.role.pk]), obj.role.code)
            except:
                return getattr(obj.role, "code", str(obj.role))
        return "-"
    @display(description="Employment Status")
    def employment_status_display(self, obj):
        if obj.employment_status_id:
            try:
                return format_html('<a href="{}">{}</a>', reverse("admin:users_employmentstatus_change", args=[obj.employment_status.pk]), obj.employment_status.code)
            except:
                return getattr(obj.employment_status, "code", str(obj.employment_status))
        return "-"
    @display(description="Employee Type")
    def employee_type_display(self, obj):
        if obj.employee_type_id:
            try:
                return format_html('<a href="{}">{}</a>', reverse("admin:users_employeetype_change", args=[obj.employee_type.pk]), obj.employee_type.code)
            except:
                return getattr(obj.employee_type, "code", str(obj.employee_type))
        return "-"
    @display(description="Manager")
    def manager_display(self, obj):
        if obj.manager_id:
            try:
                return format_html('<a href="{}">{}</a>', reverse("admin:users_employee_change", args=[obj.manager.pk]), obj.manager.employee_code)
            except:
                return getattr(obj.manager, "employee_code", str(obj.manager))
        return "-"
    @display(description="Is Active Employee", boolean=True)
    def is_active_employee_display(self, obj): return obj.is_active_employee

    def save_model(self, request, obj, form, change):
        """
        Admin save hook to reconcile email subscription state
        based on preferences JSON.
        """
        super().save_model(request, obj, form, change)

        # Only act if preferences were changed
        if not change or "preferences" not in form.changed_data:
            return

        prefs = obj.preferences or {}

        # If ALL known preferences are True → resubscribe
        if prefs and all(prefs.get(k) is True for k in prefs.keys()):
            UnsubscribeService.resubscribe_user(obj)


@AdminIconDecorator.register_with_icon(Team)
class TeamAdmin(BaseAdmin):
    form = TeamForm
    list_display = ('name', 'department_display', 'leader_display', 'is_active')
    list_filter = ('is_active', 'department__code')
    search_fields = ('name', 'description')
    list_per_page = 50
    select_related_fields = ['department', 'leader', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('department', queryset=Department.all_objects.filter(is_active=True)),
        Prefetch('leader', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    actions = ['soft_delete', 'restore']
    autocomplete_fields = ['department', 'leader']
    ordering = ('-id',)

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'department', 'leader', 'description', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'name', 'description', 'department__code', 'leader__employee_code',
            'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description='Department')
    def department_display(self, obj):
        if obj.department:
            url = reverse('admin:users_department_change', args=[obj.department.pk])
            return format_html('<a href="{}">{}</a>', url, obj.department.code)
        return '-'

    @display(description='Leader')
    def leader_display(self, obj):
        if obj.leader:
            url = reverse('admin:users_employee_change', args=[obj.leader.pk])
            return format_html('<a href="{}">{}</a>', url, obj.leader.employee_code)
        return '-'

    def get_list_filter(self, request):
        base_filters = [
            IsActiveFilter,
            changelist_filter("department"),    # FK field
            changelist_filter("leader"),        # FK to Employee
        ]
        return base_filters

@AdminIconDecorator.register_with_icon(LeaveType)
class LeaveTypeAdmin(BaseAdmin):
    form = LeaveTypeForm
    list_display = ('name', 'code', 'default_balance', 'is_active')
    search_fields = ('name', 'code')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('name', 'code', 'default_balance', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'name', 'code', 'default_balance', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=LeaveType))
        return base_filters

@AdminIconDecorator.register_with_icon(LeaveBalance)
class LeaveBalanceAdmin(BaseAdmin):
    form = LeaveBalanceForm
    list_display = ('employee_display', 'leave_type_display', 'balance', 'year', 'is_active')
    list_filter = ('leave_type__name', 'year')
    search_fields = ('employee__employee_code', 'leave_type__name')
    list_per_page = 50
    select_related_fields = ['employee', 'leave_type', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('employee', queryset=Employee.all_objects.filter(is_active=True)),
        Prefetch('leave_type', queryset=LeaveType.all_objects.filter(is_active=True)),
    ]
    actions = ['soft_delete', 'restore']
    autocomplete_fields = ['employee', 'leave_type']
    ordering = ('-year',)

    base_fieldsets_config = [
        (None, {
            'fields': ('employee', 'leave_type', 'balance', 'year', 'used', 'reset_date', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'employee__search' in request.GET:
            queryset = queryset.filter(employee__employee_code__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'employee__employee_code', 'leave_type__name', 'balance', 'year',
            'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description='Employee')
    def employee_display(self, obj):
        if obj.employee:
            url = reverse('admin:users_employee_change', args=[obj.employee.pk])
            return format_html('<a href="{}">{}</a>', url, obj.employee.username)
        return '-'

    @display(description='Leave Type')
    def leave_type_display(self, obj):
        if obj.leave_type:
            url = reverse('admin:users_leavetype_change', args=[obj.leave_type.pk])
            return format_html('<a href="{}">{}</a>', url, obj.leave_type.name)
        return '-'

    def get_list_filter(self, request):
        base_filters = [
            IsActiveFilter,
            changelist_filter("leave_type"),
            changelist_filter("employee"),
        ]
        return base_filters

@AdminIconDecorator.register_with_icon(LeaveApplication)
class LeaveApplicationAdmin(BaseAdmin):
    form = LeaveApplicationForm
    list_display = ('employee_display', 'leave_type_display', 'start_date', 'end_date', 'status_display', 'approver', 'is_active')
    list_filter = ('leave_type__name', 'status')
    search_fields = ('employee__employee_code', 'leave_type__name', 'reason')
    list_per_page = 50
    select_related_fields = ['employee', 'leave_type', 'approver', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('employee', queryset=Employee.all_objects.filter(is_active=True)),
        Prefetch('leave_type', queryset=LeaveType.all_objects.filter(is_active=True)),
        Prefetch('approver', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    actions = ['soft_delete', 'restore']
    autocomplete_fields = ['employee', 'leave_type', 'approver']
    ordering = ('-start_date',)

    base_fieldsets_config = [
        (None, {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'hours', 'reason', 'status', 'approver', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'employee__search' in request.GET:
            queryset = queryset.filter(employee__employee_code__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'employee__employee_code', 'leave_type__name', 'start_date', 'end_date',
            'status', 'approver__employee_code', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description='Employee')
    def employee_display(self, obj):
        if obj.employee:
            url = reverse('admin:users_employee_change', args=[obj.employee.pk])
            return format_html('<a href="{}">{}</a>', url, obj.employee.employee_code)
        return '-'

    @display(description='Leave Type')
    def leave_type_display(self, obj):
        if obj.leave_type:
            url = reverse('admin:users_leavetype_change', args=[obj.leave_type.pk])
            return format_html('<a href="{}">{}</a>', url, obj.leave_type.name)
        return '-'

    @display(description='Status')
    def status_display(self, obj):
        return obj.status

    def get_list_filter(self, request):
        base_filters = [
            IsActiveFilter,
            changelist_filter("leave_type"),
            changelist_filter("employee"),
            changelist_filter("approver"),
            'status',
        ]
        return base_filters


@AdminIconDecorator.register_with_icon(MemberStatus)
class MemberStatusAdmin(BaseAdmin):
    form = MemberStatusForm
    list_display = ('code', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'name', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=MemberStatus))
        return base_filters

@AdminIconDecorator.register_with_icon(Member)
class MemberAdmin(BaseAdmin):
    icon = 'fas fa-user-friends'
    form = MemberForm
    list_display = ('member_code', 'email', 'first_name', 'last_name', 'employee_display', 'status_display')
    # list_filter = ('status__code', CountryFilterMixin.CountryAdminFilter)
    search_fields = ('member_code', 'email', 'first_name', 'last_name')
    list_per_page = 50
    select_related_fields = ['status', 'employee', 'address', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('status', queryset=MemberStatus.all_objects.filter(is_active=True)),
        Prefetch('employee', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    actions = ['soft_delete', 'restore']
    autocomplete_fields = ['status', 'employee', 'address']

    base_fieldsets_config = [
        (None, {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'employee', 'status', 'address', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'member__search' in request.GET:
            queryset = queryset.filter(member_code__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'member_code', 'email', 'first_name', 'last_name', 'employee__employee_code',
            'status__code', 'address', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description='Active', boolean=True)
    def active_status(self, obj):
        return obj.deleted_at is None

    @display(description='Employee')
    def employee_display(self, obj):
        if obj.employee:
            url = reverse('admin:users_employee_change', args=[obj.employee.pk])
            return format_html('<a href="{}">{}</a>', url, obj.employee.employee_code)
        return '-'

    @display(description='Status')
    def status_display(self, obj):
        if obj.status:
            url = reverse('admin:users_memberstatus_change', args=[obj.status.pk])
            return format_html('<a href="{}">{}</a>', url, obj.status.code)
        return '-'

    def get_list_filter(self, request):
        base_filters = [
            IsActiveFilter,
            changelist_filter("status"),
        ]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=Member))
        return base_filters

@AdminIconDecorator.register_with_icon(SignUpRequest)
class SignUpRequestAdmin(BaseAdmin):
    form = SignUpRequestForm
    list_display = ("token", "user_display", "sso_provider", "sso_id", "expires_at", "active_status", "created_at")
    search_fields = ("token", "sso_id", "user__email", "user__username")
    list_per_page = 50
    select_related_fields = ["user", "created_by", "updated_by", "deleted_by"]
    prefetch_related_fields = [
        Prefetch('user', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    actions = ["soft_delete", "restore"]
    readonly_fields = ("token", "created_at", "created_by", "updated_at", "updated_by", "deleted_at", "deleted_by")

    base_fieldsets_config = [
        (None, {
            "fields": (
                "user",
                "email", "first_name", "last_name", "username",
                "sso_provider", "sso_id",
                "expires_at", "is_active",
            )
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if "signup__search" in request.GET:
            queryset = queryset.filter(token__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            "token", "user__email", "user__username", "sso_provider", "sso_id",
            "expires_at", "deleted_at", "created_by", "updated_by", "deleted_by"
        )

    def get_fieldsets(self, request, obj=None):
        """
        - ADD: hide email / first_name / last_name / username
        - EDIT: show them (read-only, via form)
        """
        fieldsets = super().get_fieldsets(request, obj)

        if obj is None:  # ADD form
            cleaned = []
            for name, opts in fieldsets:
                fields = list(opts.get("fields", ()))
                filtered = tuple(
                    f for f in fields
                    if f not in ("email", "first_name", "last_name", "username")
                )
                new_opts = dict(opts, fields=filtered)
                cleaned.append((name, new_opts))
            return cleaned

        return fieldsets

    def get_list_filter(self, request):
        base = [IsActiveFilter]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=SignUpRequest))
        return base

    # ---------- Display helpers ----------
    @display(description="Active", boolean=True)
    def active_status(self, obj):
        return obj.deleted_at is None

    @display(description="User")
    def user_display(self, obj):
        if not obj.user_id:
            return "-"
        try:
            url = reverse("admin:users_employee_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email or str(obj.user))
        except Exception:
            logger.debug("Reverse for user admin failed for user_id=%s", obj.user_id)
            return getattr(obj.user, "email", str(obj.user))

    @display(description="SSO")
    def sso_display(self, obj):
        return f"{obj.sso_provider} / {obj.sso_id or '-'}" if obj.sso_provider else "-"

    # ---------- Email triggering ----------
    def save_model(self, request, obj, form, change):
        """
        - Save with audit fields.
        - On create: send verification email to the Member.
        - On update: if expires_at changed, attempt to send again,
            but throttle using a global limit.
        """
        # Capture old expires_at before saving (for change case)
        old_expires_at = None
        if change and obj.pk:
            try:
                old = SignUpRequest.all_objects.get(pk=obj.pk)
                old_expires_at = old.expires_at
            except SignUpRequest.DoesNotExist:
                old_expires_at = None

        # Save with audit user
        obj.save(user=request.user)

        employee = obj.user
        member = (
            Member.objects
            .filter(employee=employee, deleted_at__isnull=True)
            .order_by("-id")
            .first()
        )

        if not member:
            logger.warning(
                "SignUpRequestAdmin.save_model: No Member found for SignUpRequest(pk=%s, user_id=%s); "
                "no email sent.",
                obj.pk,
                employee.pk if employee else None,
            )
            return

        max_limit = int(getattr(settings, 'SIGNUP_REQUEST_MAX_PER_USER', 2))

        # Decide logically whether we *want* to send
        send_email = False
        if not change:
            send_email = True        # new request
        else:
            if old_expires_at != obj.expires_at:
                send_email = True    # only if expiry changed

        if send_email and not employee.is_verified:
            # Throttle per flow + user
            allowed = check_and_increment_email_limit(
                flow="signup_request_admin",
                max_total=max_limit,
                user_id=employee.pk,
                email=employee.email,
                ttl_seconds=24 * 60 * 60    #  Set None for no expiry → lifetime cap for this flow+user
            )

            if not allowed:
                messages.warning(
                    request,
                    f"Maximum {max_limit} signup verification emails have already "
                    "been sent for this user from admin."
                )
                logger.info(
                    "SignUpRequestAdmin.save_model: email not sent, throttle limit reached "
                    "for user_id=%s flow=signup_request_admin",
                    employee.pk,
                )
                return

            try:
                # Synchronous call (same behavior as manual signup)
                send_manual_verification_email_task(
                    member.id,
                    employee.username,
                    employee.first_name,
                    employee.last_name,
                )
                logger.info(
                    "SignUpRequestAdmin.save_model: Sent manual verification email "
                    "for %s (signup_request_pk=%s).",
                    member.email,
                    obj.pk,
                )
                messages.success(request, "Verification email has been sent.")
            except Exception:
                logger.exception(
                    "SignUpRequestAdmin.save_model: Failed to send manual verification email "
                    "for signup_request_pk=%s.",
                    obj.pk,
                )
                messages.error(request, "Failed to send verification email. See logs for details.")


@AdminIconDecorator.register_with_icon(PasswordResetRequest)
class PasswordResetRequestAdmin(BaseAdmin):
    form = PasswordResetRequestForm
    list_display = ('username', 'token_display', 'expires_at', 'used', 'is_active')
    list_filter = ()
    search_fields = ('user__email',)
    list_per_page = 50
    select_related_fields = ['user', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = [
        Prefetch('user', queryset=Employee.all_objects.filter(is_active=True)),
    ]
    ordering = ('-created_at',)

    base_fieldsets_config = [
        (None, {
            'fields': ('user', 'expires_at', 'used', 'token')
        }),
    ]

    def get_readonly_fields(self, request, obj=None):
        # Always show expires_at as calculated value (read-only)
        return ('expires_at', 'token',) + tuple(super().get_readonly_fields(request, obj))

    def get_fieldsets(self, request, obj=None):
        # Let BaseAdmin inject audit fieldset first
        fieldsets = super().get_fieldsets(request, obj)

        if obj is None:
            # On ADD form → hide some fields
            new_fieldsets = []
            for title, opts in fieldsets:
                fields = list(opts.get('fields', []))
                if 'expires_at' in fields:
                    fields.remove('expires_at')
                if 'is_active' in fields:
                    fields.remove('is_active')
                if 'used' in fields:
                    fields.remove('used')
                if 'token' in fields:
                    fields.remove('token')
                new_fieldsets.append((title, {**opts, 'fields': fields}))
            return new_fieldsets

        # On EDIT: remove is_active but KEEP metadata
        new_fieldsets = []
        for title, opts in fieldsets:
            fields = list(opts.get('fields', []))
            if 'is_active' in fields:
                fields.remove('is_active')
            new_fieldsets.append((title, {**opts, 'fields': fields}))

        return new_fieldsets

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if 'user__search' in request.GET:
            queryset = queryset.filter(user__email__icontains=search_term)
        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'user__email', 'expires_at', 'used', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    @display(description="User")
    def username(self, obj):
        return obj.user.get_full_name

    @display(description="Token")
    def token_display(self, obj):
        return obj.token

    @display(description="Expires At")
    def expires_at(self, obj):
        if not obj or not obj.expires_at:
            return "-"
        return obj.expires_at.strftime("%Y-%m-%d %H:%M:%S")


    def get_list_filter(self, request):
        base_filters = [
            # changelist_filter("user"),
            ('used'),
            IsActiveFilter,
        ]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter('user'))
        return base_filters


@AdminIconDecorator.register_with_icon(Address)
class AddressAdmin(BaseAdmin):
    form = AddressForm

    list_display = (
        "owner",
        "address",
        "address_type",
        "is_active"
    )

    search_fields = (
        "owner__email",
        "address",
        "city",
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("owner")
        return ro


    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        new_fieldsets = []
        for title, opts in fieldsets:
            fields = list(opts.get("fields", []))

            if obj is None:
                # ADD form → show search field only
                if "email" in fields:
                    fields.remove("email")
            else:
                # EDIT form → show read-only email only
                if "user" in fields:
                    fields.remove("user")

            new_fieldsets.append((title, {**opts, "fields": fields}))

        return new_fieldsets


    base_fieldsets_config = [
        (
            None,
            {
                "fields": (
                    "email",          # EDIT only (read-only)
                    "user",           # ADD only (Select2 search)
                    "address_type",
                    "address",
                    "country",
                    "state",
                    "city",
                    "postal_code",
                    "emergency_contact",
                    "is_active"
                )
            },
        )
    ]

    def save_model(self, request, obj, form, change):
        """
        Address Activation Rules

        ADD:
        - A newly created address is always set as active.
        - Any existing active address for the same owner is automatically
        deactivated BEFORE the new address is saved.

        EDIT:
        - If is_active=True:
            - This address is promoted to be the owner's sole active address.
            - Any other active address for the same owner is deactivated
            BEFORE saving to satisfy the database constraint.
        - If is_active=False:
            - The address is simply updated.
            - No other addresses are affected.

        Invariant:
        - At all times, an owner can have at most ONE active address.
        - Zero or more inactive addresses are allowed.
        """
        owner = obj.owner if change else form.cleaned_data.get("user")
        if not owner:
            raise ValidationError("Address must have an owner.")

        with transaction.atomic():

            # ----------------------------
            # ADD: always active
            # ----------------------------
            if not change:
                obj.owner = owner
                obj.is_active = True

                # Deactivate existing BEFORE insert
                Address.all_objects.filter(
                    owner=owner,
                    is_active=True,
                ).update(is_active=False)

                super().save_model(request, obj, form, change)
                return

            # ----------------------------
            # EDIT
            # ----------------------------
            if obj.is_active:
                # Admin wants this to be active → deactivate others FIRST
                Address.all_objects.filter(
                    owner=owner,
                    is_active=True,
                ).exclude(pk=obj.pk).update(is_active=False)

            # Now safe to save (0 or 1 active row exists)
            super().save_model(request, obj, form, change)


    @admin.display(boolean=True, description="Active")
    def is_active_display(self, obj):
        return obj.is_active

    def get_list_filter(self, request):
        base = [AddressCountryFilter, AddressStateFilter, AddressCityFilter, IsActiveFilter]
        if user_is_verified_employee(request):
            base.insert(0, AddressTypeFilter)
        return base


@AdminIconDecorator.register_with_icon(UserActivityLog)
class UserActivityLogAdmin(BaseAdmin):
    form = UserActivityLogForm
    list_display = ('user_display', 'action', 'client_ip', 'event_timestamp')
    list_filter = ('action',)
    search_fields = ('user__email', 'action')
    list_per_page = 50
    select_related_fields = ['user']
    readonly_fields = ('user', 'action', 'event_timestamp')
    ordering = ('-created_at',)

    base_fieldsets_config = [
        (None, {
            'fields': ('user', 'action')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'user__email', 'action', 'created_at'
        )

    @admin.display(description='User')
    def user_display(self, obj):
        if obj.user:
            url = reverse('admin:users_employee_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'

    @admin.display(description='Event Timestamp')
    def event_timestamp(self, obj):
        return obj.created_at

    def get_list_display(self, request):
        # Override to ensure 'event_timestamp' is included, bypassing audit field exclusion
        return ('user_display', 'action', 'client_ip', 'event_timestamp')

    def get_fieldsets(self, request, obj=None):
        # Ensure 'event_timestamp' is always included, even if audit fields are restricted
        fieldsets = list(self.base_fieldsets_config)
        if self.user_can_see_audit(request):
            audit_fields = self.get_audit_fields(obj)
            fieldsets.append((_('Metadata'), {
                'fields': audit_fields
            }))
        return fieldsets

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@AdminIconDecorator.register_with_icon(Department)
class DepartmentAdmin(BaseAdmin):
    list_display = ('code', 'name', 'get_is_active')
    search_fields = ('code', 'name')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'name', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=Department))
        return base_filters


@AdminIconDecorator.register_with_icon(Role)
class RoleAdmin(BaseAdmin):
    list_display = ('code', 'title', 'rank', 'is_active')
    search_fields = ('code', 'title')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']
    ordering = ('rank',)

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'title', 'rank', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'title', 'rank', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=Role))
        return base_filters

@AdminIconDecorator.register_with_icon(EmployeeType)
class EmployeeTypeAdmin(BaseAdmin):
    list_display = ('code', 'name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'name', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=EmployeeType))
        return base_filters

@AdminIconDecorator.register_with_icon(EmploymentStatus)
class EmploymentStatusAdmin(BaseAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')
    list_per_page = 50
    select_related_fields = ['created_by', 'updated_by', 'deleted_by']
    actions = ['soft_delete', 'restore']

    base_fieldsets_config = [
        (None, {
            'fields': ('code', 'name', 'is_active')
        }),
    ]

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_queryset(self, request):
        return super().get_queryset(request).only(
            'code', 'name', 'is_active', 'created_by', 'updated_by', 'deleted_by'
        )

    def get_list_filter(self, request):
        base_filters = [IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter(model=EmploymentStatus))
        return base_filters

@AdminIconDecorator.register_with_icon(SupportTicket)
class SupportTicketAdmin(BaseAdmin):
    form = SupportTicketForm
    list_display = ('ticket_number', 'subject', 'is_bug_report', 'status_display', 'email','file_count', 'created_at')
    search_fields = ('ticket_number', 'subject', 'full_name', 'email')
    list_per_page = 50
    select_related_fields = ['employee', 'created_by', 'updated_by', 'deleted_by']
    prefetch_related_fields = ['file_uploads']
    actions = ['soft_delete', 'restore']
    autocomplete_fields = ['employee']
    base_fieldsets_config = [
        (None, {
            'fields': ('subject', 'email', 'message', 'status', 'resolved_at', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by')
        }),
    ]
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('file_uploads')

    def get_fieldset_conditions(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.status in (SupportStatus.RESOLVED, SupportStatus.CLOSED):
            ro += ["full_name", "email", "is_bug_report"]
            # optionally:
            # ro += ["subject", "message"]
        return ro

    def get_admin_url(self):
        from django.urls import reverse
        return reverse('admin:users_supportticket_change', args=[self.pk])

    @display(description='Status')
    def status_display(self, obj):
        return SupportStatus[obj.status].label if obj.status else '-'

    @admin.display(description='Attachments')
    def file_count(self, obj):
        from django.contrib.contenttypes.models import ContentType
        if not obj.pk:
            return '-'
        count = obj.file_uploads.count()
        if count:
            # Get ContentType dynamically
            ct = ContentType.objects.get_for_model(obj)
            url = (
                reverse('admin:users_fileupload_changelist')
                + f'?content_type_id={ct.id}&object_id={obj.pk}'
            )
            return format_html('<a href="{}"><b>{}</b></a>', url, count)
        return '-'

    def get_list_filter(self, request):
        base_filters = [changelist_filter("is_bug_report"), IsActiveFilter]
        if user_is_verified_employee(request):
            base_filters.insert(0, changelist_filter("employee"),)
        return base_filters


@AdminIconDecorator.register_with_icon(FileUpload)
class FileUploadAdmin(BaseAdmin):
    list_display = ('original_name_link', 'content_object', 'size_display', 'uploaded_at', 'created_by_display')
    list_filter = ('uploaded_at', 'is_active')
    search_fields = ('original_name', 'file')
    readonly_fields = ('original_name_link', 'size', 'uploaded_at', 'created_by', 'updated_by', 'content_object')
    list_per_page = 50
    ordering = ('-uploaded_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description='File Name')
    def original_name_link(self, obj):
        if obj.file and obj.file.url:
            return format_html(
                '<a href="{}" target="_blank"><i class="fas fa-download"></i> {}</a>',
                obj.file.url,
                obj.original_name
            )
        return obj.original_name

    @display(description='Size')
    def size_display(self, obj):
        if obj.size:
            return f"{obj.size / 1024:.1f} KB"
        return '-'

    @display(description='Linked To')
    def content_object(self, obj):
        if not obj.content_object:
            return '-'
        app_label = obj.content_type.app_label
        model_name = obj.content_type.model
        object_id = obj.object_id
        url = reverse(f'admin:{app_label}_{model_name}_change', args=[object_id])
        return format_html('<a href="{}">{}</a>', url, str(obj.content_object))

    @display(description='Created By')
    def created_by_display(self, obj):
        if obj.created_by:
            url = reverse('admin:users_employee_change', args=[obj.created_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.employee_code or obj.created_by.email)
        return '-'
