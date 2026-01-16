import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from users.models import Employee, Member
from utilities.commons.helpers import employee_state_by_email
from utilities.constants.template_registry import TemplateRegistry
from utilities.services.email.support import SupportService
from mailer.engine.unverified_guard import handle_unverified_email

from frontend.forms.support import SupportForm

logger = logging.getLogger(__name__)


def support_view(request):
    if request.method == "POST":
        form = SupportForm(request.POST, request.FILES)
        form.enforce_logged_in_email(request)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            full_name = form.cleaned_data["name"]
            # keep original behaviour for email variable (no forced lowercasing here)
            email = form.cleaned_data["email"]
            message = form.cleaned_data["message"]
            files = request.FILES.getlist("files")

            # -------------------------
            # Minimal generic pre-check
            # -------------------------

            state, emp = employee_state_by_email(email)
            if state == "inactive":
                if request.user.is_authenticated and getattr(request.user, "pk", None) == getattr(emp, "pk", None):
                    messages.error(
                        request,
                        _(
                            "Your account is inactive or has been removed. "
                            "Support requests cannot be submitted while the account is inactive. "
                            "Please contact an administrator to restore your account."
                        ),
                        extra_tags="support_request error",
                    )
                else:
                    messages.error(
                        request,
                        _(
                            "We cannot accept support requests for this email because the associated account is inactive or has been removed."
                        ),
                        extra_tags="support_request error",
                    )
                logger.warning("Blocked support submit — inactive employee: %s", email)
                return redirect(reverse("console_dashboard") if request.user.is_authenticated else reverse("account_login"))

            # ------------------------------------------------------------------
            # state == "unverified" via shared utility
            # ------------------------------------------------------------------
            response = handle_unverified_email(
                request=request,
                email=email,
                context="support",
            )
            if response:
                logger.info("Blocked support submit — unverified employee: %s", email)
                return response

            # state == "ok" or "not_found" or "error" -> proceed to submit (we allow not_found)
            if state == "error":
                logger.warning("employee_state_by_email returned error for %s; proceeding with submission", email)

            # -------------------------
            # Proceed with original flow (SupportService does throttling/limit)
            # -------------------------
            result = SupportService.submit_support_request(
                request=request,
                subject=subject,
                full_name=full_name,
                email=email,
                message=message,
                files=files,
            )

            # NOTE: treat not_registered as allowed — show success message (use ticket if service created one)
            if result.status == "not_registered":
                ticket_num = None
                try:
                    ticket_num = getattr(result, "ticket", None) and result.ticket.ticket_number
                except Exception:
                    ticket_num = None

                # If the service returns a ticket, show the ticket-based success message.
                # Otherwise show a generic allowed-success message. We still rely on result.status == "limit"
                # to indicate throttling if the service sets it.
                if ticket_num:
                    messages.success(
                        request,
                        _(
                            "Your support ticket #{} has been submitted. "
                            "We'll get back to you soon!"
                        ).format(ticket_num),
                        extra_tags="support_request success",
                    )
                else:
                    messages.success(
                        request,
                        _(
                            "Your support request has been submitted. We'll get back to you soon!"
                        ),
                        extra_tags="support_request success",
                    )

            elif result.status == "success":
                # ------------------------------------------------------------------
                # Determine unsubscribed state for both logged-in and anonymous users
                # ------------------------------------------------------------------
                is_unsubscribed = False

                if request.user.is_authenticated:
                    is_unsubscribed = getattr(request.user, "is_unsubscribed", False)
                else:
                    try:
                        emp = Employee.objects.filter(email__iexact=email).first()
                        if emp:
                            is_unsubscribed = getattr(emp, "is_unsubscribed", False)
                        else:
                            mem = Member.objects.filter(email__iexact=email).first()
                            if mem and mem.employee:
                                is_unsubscribed = getattr(mem.employee, "is_unsubscribed", False)
                            elif mem:
                                is_unsubscribed = getattr(mem, "is_unsubscribed", False)
                    except Exception:
                        pass

                # ------------------------------------------------------------------
                # Show appropriate success message (only if NOT throttled)
                # ------------------------------------------------------------------
                if is_unsubscribed:
                    messages.warning(
                        request,
                        _(
                            "Your support ticket #{} has been submitted. "
                            "You’ve unsubscribed from emails, so you won’t receive a confirmation email."
                        ).format(result.ticket.ticket_number),
                        extra_tags="support_request warning",
                    )
                else:
                    messages.success(
                        request,
                        _(
                            "Your support ticket #{} has been submitted. "
                            "We'll get back to you soon!"
                        ).format(result.ticket.ticket_number),
                        extra_tags="support_request success",
                    )

            elif result.status == "limit":
                # ------------------------------------------------------------------
                # IMPORTANT: respect throttling — no success message when limit reached
                # ------------------------------------------------------------------
                messages.warning(
                    request,
                    _(
                        "You’ve reached the maximum number of support requests.<br>Our team will contact you soon."
                    ),
                    extra_tags="support_request warning",
                )

            else:  # "error"
                messages.error(
                    request,
                    _(
                        "Something went wrong while creating your support ticket. "
                        "Please try again later."
                    ),
                    extra_tags="support_request error",
                )

            if request.user.is_authenticated:
                return redirect(reverse("console_dashboard"))
            else:
                return redirect(reverse("account_login"))

        else:
            messages.error(
                request,
                _("Please correct the errors below."),
                extra_tags="support_request error",
            )
            if request.user.is_authenticated:
                return redirect(reverse("console_dashboard"))
            else:
                return redirect(reverse("account_login"))

    form = SupportForm()
    form.enforce_logged_in_email(request)
    return render(request, TemplateRegistry.SUPPORT_REQUEST_FORM, {"form": form})
