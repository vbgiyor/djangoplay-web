import logging

from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from users.services.common import CommonService
from users.services.signup_token_manager import SignupTokenManagerService

logger = logging.getLogger(__name__)


class UnifiedEmailVerifyView(View):

    """
    Email verification endpoint with strict token ownership enforcement.
    """

    def get(self, request: HttpRequest):
        token = request.GET.get("token", "").strip()
        result = SignupTokenManagerService.validate_token(token)

        # EARLY idempotent success — ONLY for the token owner
        if (
            request.user.is_authenticated
            and result.user
            and request.user.pk == result.user.pk
            and result.reason == "consumed"
        ):
            messages.info(
                request,
                _("This account has already been verified."),
                extra_tags="account_verify info",
            )
            return redirect(reverse("console_dashboard"))

        # =========================================================
        # CASE 1: TOKEN NEVER EXISTED / MALFORMED
        # =========================================================
        if result.user is None:
            messages.error(
                request,
                _("This verification link is invalid or has expired."),
                extra_tags="account_verify error",
            )
            return redirect(reverse("account_login"))

        token_owner = result.user

        # =========================================================
        # CASE 2: DIFFERENT LOGGED-IN USER
        # =========================================================
        if (
            request.user.is_authenticated
            and request.user.pk != token_owner.pk
        ):
            messages.error(
                request,
                _("This verification link does not belong to your account."),
                extra_tags="account_verify error",
            )
            return redirect(reverse("console_dashboard"))

        # =========================================================
        # CASE 3: TOKEN CONSUMED
        # =========================================================
        if result.reason == "consumed":
            if token_owner.is_verified:
                messages.info(
                    request,
                    _("This account has already been verified."),
                    extra_tags="account_verify info",
                )
            else:
                messages.error(
                    request,
                    _("This verification link is no longer valid or expired."),
                    extra_tags="account_verify error",
                )

            return redirect(
                reverse("console_dashboard")
                if request.user.is_authenticated
                else reverse("account_login")
            )


        # =========================================================
        # CASE 4: TOKEN EXPIRED
        # =========================================================
        if result.reason == "expired":
            messages.error(
                request,
                _("This verification link has expired. Please request a new one."),
                extra_tags="account_verify error",
            )
            return redirect(reverse("account_login"))

        # =========================================================
        # CASE 5: VALID TOKEN → ACTIVATE
        # =========================================================
        SignupTokenManagerService.consume_and_activate(
            result.signup_request
        )

        messages.success(
            request,
            _("Your email address has been verified successfully."),
            extra_tags="account_verify success",
        )

        # =========================================================
        # AUDIT LOG
        # =========================================================
        try:
            CommonService.log_user_activity(
                user=token_owner,
                action="VERIFY_EMAIL",
                client_ip=getattr(request, "client_ip", None),
            )
        except Exception:
            logger.exception("Failed to log VERIFY_EMAIL activity")

        return redirect(
            reverse("console_dashboard")
            if request.user.is_authenticated
            else reverse("account_login")
        )
