import logging

from core.admin_mixins import AdminIconDecorator, BaseAdmin
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import display
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mailer.flows.member.verification import send_manual_verification_email_task
from mailer.throttling.throttle import check_and_increment_email_limit
from teamcentral.models import MemberProfile
from utilities.admin.admin_filters import IsActiveFilter, changelist_filter

from users.forms import SignUpRequestForm
from users.models import Employee
from users.models.signup_request import SignUpRequest
from users.utils.helpers import user_is_verified_employee

logger = logging.getLogger(__name__)


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
            MemberProfile.objects
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


    def get_list_filter(self, request):
        base = [IsActiveFilter]
        if user_is_verified_employee(request):
            base.insert(0, changelist_filter(model=SignUpRequest))
        return base
