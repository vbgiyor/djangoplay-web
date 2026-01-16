from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from utilities.services.email.resend_verification import (
    resend_verification_for_email,
)


def ResendVerificationView(request):
    email = request.GET.get("email")
    if not email:
        messages.error(request, _("Email address missing."))
        return redirect(reverse("account_login"))

    result = resend_verification_for_email(
        email=email,
        created_by=request.user if request.user.is_authenticated else None,
        client_ip=request.META.get("REMOTE_ADDR"),
    )

    if result.status == "no_user":
        messages.error(request, _("No account found with this email."))

    elif result.status == "already_verified":
        messages.info(request, _("This account is already verified."))

    elif result.status == "rate_limited":
        messages.error(request, _("Too many requests. Try again later."))

    elif result.status == "ok":
        messages.success(
            request,
            _("Verification email sent. Please check your inbox."),
        )

    else:
        messages.error(
            request,
            _("Unable to resend verification email. Please try again later."),
        )

    return redirect(reverse("account_login"))
