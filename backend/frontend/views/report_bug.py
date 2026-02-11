import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from helpdesk.services import BugService

from frontend.forms.report_bug import BugReportForm

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(exclude=True)
class ReportBugView(View):

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(
                request,
                "You must be logged in to submit a bug report.",
                extra_tags="bug_report error",
            )
            return redirect("account_login")

        form = BugReportForm(request.POST, request.FILES)
        form.enforce_logged_in_email(request)

        if not form.is_valid():
            messages.error(
                request,
                f"Invalid form data: {form.errors}",
                extra_tags="bug_report error",
            )
            return redirect(request.META.get("HTTP_REFERER", "/"))

        result = BugService.submit_bug_report(
            request=request,
            form=form,
        )

        if result.status == "limit":
            messages.warning(
                request,
                "You have reported maximum number of issues for today. <br>Take a break and resume tomorrow.",
                extra_tags="bug_report warning",
            )
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if result.status == "success":
            if getattr(request.user, "is_unsubscribed", False):
                messages.warning(
                    request,
                    f"Bug #{result.bug.bug_number} recorded. "
                    "You’ve unsubscribed from emails, so you won’t receive a confirmation email.",
                    extra_tags="bug_report warning",
                )
            else:
                messages.success(
                    request,
                    f"Bug #{result.bug.bug_number} submitted successfully. Thank you!",
                    extra_tags="bug_report success",
                )
            return redirect(request.META.get("HTTP_REFERER", "/"))

        # status == "error"
        messages.error(
            request,
            "Something went wrong while submitting your bug report.",
            extra_tags="bug_report error",
        )
        return redirect(request.META.get("HTTP_REFERER", "/"))
