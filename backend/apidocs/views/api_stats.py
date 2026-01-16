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
from users.models.employee import Employee
from utilities.constants.template_registry import TemplateRegistry

EXCLUDED_PATH_KEYWORDS = ["schema", "redoc", "swagger", "apistats", "unsubscribe" ]

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
        .extra(select={'day': "DATE(timestamp)"})
        .values('day')
        .annotate(calls=Count('id'))
        .order_by('day')
    )

    labels = [stat['day'].strftime("%a") for stat in daily_stats]
    data = [stat['calls'] for stat in daily_stats]
    top_endpoints = (
        logs.exclude(path__icontains="schema")
            .exclude(path__icontains="redoc")
            .exclude(path__icontains="swagger")
            .exclude(path__icontains="apistats")
            .exclude(path__icontains="api/dashboard")
        )

    return {
        'is_personal': is_personal,
        'total_calls': total_calls,
        'today_calls': logs.filter(timestamp__date=today).count(),
        'week_calls': logs.filter(timestamp__gte=week_ago).count(),
        'success_rate': success_rate,
        # 'top_endpoints': logs.values('path').annotate(count=Count('path')).order_by('-count')[:10],
        'top_endpoints': top_endpoints,
        'recent_calls': logs.order_by('-timestamp')[:10],
        'daily_labels': json.dumps(labels),
        'daily_data': json.dumps(data),
    }


# =============================================================================
# SHARED CSV EXPORT LOGIC (UPDATED)
# =============================================================================
def handle_csv_export(request, logs, start_date, end_date):
    """Generate CSV and send/download. Returns HttpResponse or None."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([f"API Stats Report ({start_date} to {end_date})"])
    writer.writerow([])
    writer.writerow(['Method', 'Path', 'Status', 'Timestamp', 'IP Address'])
    for log in logs.order_by('-timestamp'):
        writer.writerow([
            log.method,
            log.path,
            log.response_status,
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            getattr(log, 'client_ip', 'N/A')
        ])
    csv_content = buffer.getvalue()
    buffer.close()

    email_addr = request.POST.get('email', '').strip()
    user = request.user if request.user.is_authenticated else None

    # === EMAIL VALIDATION FOR LOGGED-IN USERS ===
    if email_addr:
        if user and email_addr.lower() != user.email.lower():
            messages.error(
                request,
                f"The provided email <strong>{email_addr}</strong> does not match your account. "
                f"Please use your registered email: <strong>{user.email}</strong>."
            )
            return None

        try:
            recipient = Employee.objects.get(email__iexact=email_addr)
            full_name = recipient.get_full_name if hasattr(recipient, 'get_full_name') else recipient.username
            email = EmailMessage(
                subject=f"API Stats Report ({start_date} – {end_date})",
                body=(
                    f"Hi {full_name},\n\n"
                    f"Your API usage report from {start_date} to {end_date} is attached.\n\n"
                    f"Best regards,\nDjangoPlay Team"
                ),
                from_email="noreply@djangoplay.com",
                to=[recipient.email],
            )
            email.attach(
                f"api_stats_{start_date}_to_{end_date}.csv",
                csv_content,
                "text/csv"
            )
            email.send()
            messages.success(
                request,
                f"Report successfully sent to <strong>{recipient.email}</strong>."
            )
        except Employee.DoesNotExist:
            messages.error(request, f"No user found with email: <strong>{email_addr}</strong>")
    else:
        # No email → download directly
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="api_stats_{start_date}_to_{end_date}.csv"'
        )
        return response

    return None  # Stay on page with message

# =============================================================================
# PUBLIC VIEW – NO LOGIN
# =============================================================================
class PublicAPIStatsView(TemplateView):
    template_name = TemplateRegistry.APIDOCS_STATS_PUBLIC

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Show ALL logged API calls, not just is_public_api=True
        logs = APIRequestLog.objects.all()
        # logs = APIRequestLog.objects.filter(is_public_api=True)
        context.update(build_stats_context(logs, is_personal=False))
        return context

    def post(self, request, *args, **kwargs):
        if 'export_csv' not in request.POST:
            return self.get(request, *args, **kwargs)

        # Public: allow export if flag is enabled globally or for anonymous
        try:
            csv_flag = FeatureFlag.objects.get(key='apidocs_stats_csv')
            if not (csv_flag.enabled_globally or csv_flag.users.exists()):
                messages.error(request, "CSV export is not enabled.")
                return self.get(request, *args, **kwargs)
        except FeatureFlag.DoesNotExist:
            messages.error(request, "CSV export is disabled.")
            return self.get(request, *args, **kwargs)

        # Parse dates
        try:
            start_date = timezone.datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return self.get(request, *args, **kwargs)

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return self.get(request, *args, **kwargs)

        logs = APIRequestLog.objects.filter(
            # For CSV to include everything, remove is_public_api
            # is_public_api=True,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        )

        response = handle_csv_export(request, logs, start_date, end_date)
        return response or self.get(request, *args, **kwargs)


# =============================================================================
# PERSONAL VIEW – LOGIN + FLAG
# =============================================================================
class PersonalAPIStatsView(LoginRequiredMixin, TemplateView):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = f"{self.login_url}?{urlencode({'next': request.get_full_path()})}"
            return redirect(login_url)
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        # Let the registry decide between personal vs public
        return [TemplateRegistry.get_api_stats_template(self.request.user)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_personal = (
            TemplateRegistry.get_api_stats_template(user) == TemplateRegistry.APIDOCS_STATS_PERSONAL
        )

        logs = APIRequestLog.objects.all()
        if is_personal:
            logs = logs.filter(user=user)
        else:
            # logs = logs.filter(is_public_api=True)
            # Non-personal: show everything as well
            # (if you want to show only public ones here, you can re-add is_public_api=True)
            pass

        context.update(build_stats_context(logs, is_personal=is_personal))
        return context

    def post(self, request, *args, **kwargs):
        if 'export_csv' not in request.POST:
            return self.get(request, *args, **kwargs)

        user = request.user

        # Check CSV flag for personal user
        try:
            csv_flag = FeatureFlag.objects.get(key='apidocs_stats_csv')
            if not csv_flag.is_enabled_for(user):
                messages.error(request, "CSV export is not enabled for your account.")
                return self.get(request, *args, **kwargs)
        except FeatureFlag.DoesNotExist:
            messages.error(request, "CSV export is disabled.")
            return self.get(request, *args, **kwargs)

        # Parse dates
        try:
            start_date = timezone.datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
            end_date = timezone.datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return self.get(request, *args, **kwargs)

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return self.get(request, *args, **kwargs)

        # Build same queryset as GET
        logs = APIRequestLog.objects.all()
        if TemplateRegistry.get_api_stats_template(user) == TemplateRegistry.APIDOCS_STATS_PERSONAL:
            logs = logs.filter(user=user)
        else:
            # logs = logs.filter(is_public_api=True)
            # Non-personal: show everything as well
            # (if you want to show only public ones here, you can re-add is_public_api=True)
            pass

        logs = logs.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)

        response = handle_csv_export(request, logs, start_date, end_date)
        return response or self.get(request, *args, **kwargs)
