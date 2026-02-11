from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as translate
from mailer.flows.resend_verification import (
    resend_verification_for_email_task,
)


def ResendVerificationView(request):
    email = request.GET.get("email")
    if not email:
        messages.error(request, _("Email address missing."))
        return redirect(reverse("account_login"))

    result = resend_verification_for_email_task(
        email=email,
        created_by=request.user if request.user.is_authenticated else None,
        client_ip=request.META.get("REMOTE_ADDR"),
    )

    if result.status == "no_user":
        messages.error(request, translate("No account found with this email."))

    elif result.status == "already_verified":
        messages.info(request, translate("This account is already verified."))

    elif result.status == "rate_limited":
        messages.error(request, translate("Too many requests. Try again later."))

    elif result.status == "ok":
        messages.success(
            request,
            translate("Verification email sent. Please check your inbox."),
        )

    else:
        messages.error(
            request,
            translate("Unable to resend verification email. Please try again later."),
        )

    return redirect(reverse("account_login"))
