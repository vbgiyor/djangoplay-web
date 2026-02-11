import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from helpdesk.services.support_ticket_service import SupportService
from users.contracts.identity import get_identity_snapshot
from users.services.identity_query_service import IdentityQueryService
from utilities.commons.helpers import employee_state_by_email
from utilities.constants.template_registry import TemplateRegistry

from frontend.forms.support import SupportForm

logger = logging.getLogger(__name__)


def support_view(request):
    if request.method == "POST":
        origin = request.POST.get("from") or request.GET.get("from", "login")
        form = SupportForm(request.POST, request.FILES)
        form.enforce_logged_in_email(request)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            full_name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            message = form.cleaned_data["message"]
            files = request.FILES.getlist("files")

            # -------------------------------------------------
            # Identity state check (shared utility)
            # -------------------------------------------------
            state, identity = employee_state_by_email(email)

            if state == "inactive":
                if request.user.is_authenticated and request.user.email == email:
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
                            "We cannot accept support requests for this email because "
                            "the associated account is inactive or has been removed."
                        ),
                        extra_tags="support_request error",
                    )

                logger.warning("Blocked support submit — inactive identity: %s", email)
                return redirect(
                    reverse("console_dashboard")
                    if request.user.is_authenticated
                    else reverse("account_login")
                )

            # -------------------------------------------------
            # Optional unverified handling (kept commented intentionally)
            # -------------------------------------------------
            # from mailer.engine.verification_guard import handle_unverified_email

            # if not request.user.is_authenticated:
            #     response = handle_unverified_email(
            #         request=request,
            #         email=email,
            #         context="support",
            #     )
            #     if response:
            #         logger.info(
            #             "Blocked support submit — unverified identity: %s",
            #             email,
            #         )
            #         return response

            if state == "error":
                logger.warning(
                    "employee_state_by_email returned error for %s; proceeding",
                    email,
                )

            # -------------------------------------------------
            # Submit support request (service owns throttling)
            # -------------------------------------------------
            result = SupportService.submit_support_request(
                request=request,
                subject=subject,
                full_name=full_name,
                email=email,
                message=message,
                files=files,
            )

            # -------------------------------------------------
            # Result handling
            # -------------------------------------------------
            if result.status == "not_registered":
                ticket_num = getattr(getattr(result, "ticket", None), "ticket_number", None)

                messages.success(
                    request,
                    _(
                        "Your support request has been submitted."
                        if not ticket_num
                        else "Your support ticket #{} has been submitted. We'll get back to you soon!"
                    ).format(ticket_num) if ticket_num else _(
                        "Your support request has been submitted. We'll get back to you soon!"
                    ),
                    extra_tags="support_request success",
                )

            elif result.status == "success":
                is_unsubscribed = False

                if request.user.is_authenticated:
                    is_unsubscribed = getattr(request.user, "is_unsubscribed", False)
                else:
                    identity = IdentityQueryService.get_by_email(email)
                    if identity:
                        snapshot = get_identity_snapshot(identity.id)
                        is_unsubscribed = snapshot.get("is_unsubscribed", False)

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
                messages.warning(
                    request,
                    _(
                        "You’ve reached the maximum number of support requests.<br>"
                        "Our team will contact you soon."
                    ),
                    extra_tags="support_request warning",
                )

            else:
                messages.error(
                    request,
                    _(
                        "Something went wrong while creating your support ticket. "
                        "Please try again later."
                    ),
                    extra_tags="support_request error",
                )

            # return redirect(
            #     reverse("console_dashboard")
            #     if request.user.is_authenticated
            #     else reverse("account_login")
            # )
            return redirect(
                resolve_support_redirect(origin, request.user.is_authenticated)
            )


        messages.error(
            request,
            _("Please correct the errors below."),
            extra_tags="support_request error",
        )

        # return redirect(
        #     reverse("console_dashboard")
        #     if request.user.is_authenticated
        #     else reverse("account_login")
        # )

        return redirect(
            resolve_support_redirect(origin, request.user.is_authenticated)
        )

    form = SupportForm()
    form.enforce_logged_in_email(request)
    return render(
        request,
        TemplateRegistry.SUPPORT_REQUEST_FORM,
        {"form": form},
    )

def resolve_support_redirect(origin, is_authenticated):
    """
    Determines where to redirect after support submission
    """
    # Standard site login
    if origin == "login":
        return reverse("account_login")

    # API login page (generic api_login.html)
    if origin == "api":
        return reverse("frontend:api_login")

    if origin == "dashboard":
        return reverse("console_dashboard")

    if origin == "redoc":
        if is_authenticated:
            return reverse("apidocs:redoc")
        return reverse("frontend:api_login") + "?from=redoc"

    if origin == "swagger":
        if is_authenticated:
            return reverse("apidocs:swagger-ui")
        return reverse("frontend:api_login") + "?from=swagger"

    # Safe fallback
    return reverse("account_login")

