import csv
import json
from datetime import timedelta
from io import StringIO

from apidocs.models.apirequestlog import APIRequestLog
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import urlencode
from django.views.generic import TemplateView
from policyengine.models import FeatureFlag
from users.services.identity_query_service import IdentityQueryService
from utilities.constants.template_registry import TemplateRegistry

EXCLUDED_PATH_KEYWORDS = [
    "schema",
    "redoc",
    "swagger",
    "apistats",
    "unsubscribe",
]

# =============================================================================
# REUSABLE STATS BUILDER
# =============================================================================
def build_stats_context(logs, is_personal=False):
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    total_calls = logs.count()
    success_cnt = logs.filter(response_status__lt=400).count()
    success_rate = (success_cnt / total_calls * 100) if total_calls else 0

    end_date = now.date()
    start_date = end_date - timedelta(days=6)
    daily_stats = (
        logs.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
        .extra(select={"day": "DATE(timestamp)"})
        .values("day")
        .annotate(calls=Count("id"))
        .order_by("day")
    )

    labels = [stat["day"].strftime("%a") for stat in daily_stats]
    data = [stat["calls"] for stat in daily_stats]

    top_endpoints = (
        logs.exclude(path__icontains="schema")
        .exclude(path__icontains="redoc")
        .exclude(path__icontains="swagger")
        .exclude(path__icontains="apistats")
        .exclude(path__icontains="unsubscribe")
        .exclude(path__icontains="api/dashboard")
    )

    return {
        "is_personal": is_personal,
        "total_calls": total_calls,
        "today_calls": logs.filter(timestamp__date=today).count(),
        "week_calls": logs.filter(timestamp__gte=week_ago).count(),
        "success_rate": success_rate,
        "top_endpoints": top_endpoints,
        "recent_calls": logs.order_by("-timestamp")[:10],
        "daily_labels": json.dumps(labels),
        "daily_data": json.dumps(data),
    }

# =============================================================================
# EXPORT LIMITS
# =============================================================================
MAX_CSV_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# =============================================================================
# SHARED CSV EXPORT LOGIC
# =============================================================================
def handle_csv_export(request, logs, start_date, end_date):
    """
    Generate CSV and either:
    - send via email (validated against identity service), or
    - return direct download response.
    """
    buffer = StringIO()
    writer = csv.writer(buffer)

    writer.writerow([f"API Stats Report ({start_date} to {end_date})"])
    writer.writerow([])
    writer.writerow(["Method", "Path", "Status", "Timestamp", "IP Address"])

    for log in logs.order_by("-timestamp"):
        writer.writerow(
            [
                log.method,
                log.path,
                log.response_status,
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                getattr(log, "client_ip", "N/A"),
            ]
        )

    csv_content = buffer.getvalue()
    buffer.close()

    csv_size = len(csv_content.encode("utf-8"))

    if csv_size > MAX_CSV_SIZE_BYTES:
        messages.error(
            request,
            "The generated report exceeds the 20MB export limit. "
            "Please contact support for assistance.",
            f"Current size: {csv_size / (1024 * 1024):.2f} MB."
        )
        return None


    email_addr = request.POST.get("email", "").strip()
    user = request.user if request.user.is_authenticated else None

    # -------------------------------------------------
    # EMAIL FLOW (IDENTITY-SAFE)
    # -------------------------------------------------
    if email_addr:
        # Logged-in users may only send to their own email
        if user and email_addr.lower() != (user.email or "").lower():
            messages.error(
                request,
                (
                    "The provided email does not match your account email. "
                    "Please use your registered email."
                ),
            )
            return None

        identity = IdentityQueryService.get_by_email(email_addr)
        if not identity:
            messages.error(
                request,
                f"No active account found for email: {email_addr}",
            )
            return None

        email = EmailMessage(
            subject=f"API Stats Report ({start_date} – {end_date})",
            body=(
                "Hi,\n\n"
                f"Your API usage report from {start_date} to {end_date} is attached.\n\n"
                "Best regards,\nDjangoPlay Team"
            ),
            from_email="noreply@djangoplay.com",
            to=[email_addr],
        )
        email.attach(
            f"api_stats_{start_date}_to_{end_date}.csv",
            csv_content,
            "text/csv",
        )
        email.send()

        messages.success(
            request,
            f"Report successfully sent to {email_addr}.",
        )
        return None

    # -------------------------------------------------
    # DIRECT DOWNLOAD
    # -------------------------------------------------
    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="api_stats_{start_date}_to_{end_date}.csv"'
    )
    return response

# =============================================================================
# SHARED DATE PARSER
# =============================================================================
from datetime import datetime

from django.utils import timezone


def parse_date_range_from_request(request):
    """
    Extracts start_date and end_date from POST.
    Defaults to today's date if not provided or invalid.
    Returns (start_date, end_date)
    """
    today = timezone.localdate()

    raw_start = request.POST.get("start_date")
    raw_end = request.POST.get("end_date")

    try:
        start_date = datetime.strptime(raw_start, "%Y-%m-%d").date() if raw_start else today
    except (ValueError, TypeError):
        start_date = today

    try:
        end_date = datetime.strptime(raw_end, "%Y-%m-%d").date() if raw_end else today
    except (ValueError, TypeError):
        end_date = today

    return start_date, end_date


# =============================================================================
# PUBLIC VIEW – NO LOGIN
# =============================================================================
class PublicAPIStatsView(TemplateView):
    template_name = TemplateRegistry.APIDOCS_STATS_PUBLIC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = APIRequestLog.objects.all()
        context.update(build_stats_context(logs, is_personal=False))
        return context

    def post(self, request, *args, **kwargs):
        if "export_csv" not in request.POST:
            return self.get(request, *args, **kwargs)

        try:
            csv_flag = FeatureFlag.objects.get(key="apidocs_stats_csv")
            if not (csv_flag.enabled_globally or csv_flag.users.exists()):
                messages.error(request, "CSV export is not enabled.")
                return self.get(request, *args, **kwargs)
        except FeatureFlag.DoesNotExist:
            messages.error(request, "CSV export is disabled.")
            return self.get(request, *args, **kwargs)

        try:
            start_date, end_date = parse_date_range_from_request(request)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return self.get(request, *args, **kwargs)

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return self.get(request, *args, **kwargs)

        logs = APIRequestLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )

        response = handle_csv_export(request, logs, start_date, end_date)
        return response or self.get(request, *args, **kwargs)


# =============================================================================
# PERSONAL VIEW – LOGIN + FLAG
# =============================================================================
class PersonalAPIStatsView(LoginRequiredMixin, TemplateView):
    login_url = "/accounts/login/"
    redirect_field_name = "next"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = f"{self.login_url}?{urlencode({'next': request.get_full_path()})}"
            return redirect(login_url)
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return [TemplateRegistry.APIDOCS_STATS_PERSONAL]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = APIRequestLog.objects.filter(user=self.request.user)
        context.update(build_stats_context(logs, is_personal=True))
        return context

    def post(self, request, *args, **kwargs):
        if "export_csv" not in request.POST:
            return self.get(request, *args, **kwargs)

        try:
            csv_flag = FeatureFlag.objects.get(key="apidocs_stats_csv")
            if not csv_flag.is_enabled_for(request.user):
                messages.error(request, "CSV export is not enabled for your account.")
                return self.get(request, *args, **kwargs)
        except FeatureFlag.DoesNotExist:
            messages.error(request, "CSV export is disabled.")
            return self.get(request, *args, **kwargs)

        try:
            start_date, end_date = parse_date_range_from_request(request)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return self.get(request, *args, **kwargs)

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return self.get(request, *args, **kwargs)

        logs = APIRequestLog.objects.filter(
            user=request.user,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )

        response = handle_csv_export(request, logs, start_date, end_date)
        return response or self.get(request, *args, **kwargs)
