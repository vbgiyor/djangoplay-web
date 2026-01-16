import logging

from allauth.account.views import PasswordResetView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from users.services.common import CommonService
from users.services.password_reset import PasswordResetService
from utilities.constants.login import (
    RESET_STATUS_INVALID,
    RESET_STATUS_LIMIT,
    RESET_STATUS_NOT_FOUND,
    RESET_STATUS_SUCCESS,
    RESET_STATUS_UNSUBSCRIBED,
)
from utilities.constants.template_registry import TemplateRegistry

from frontend.forms.password_reset import CustomResetPasswordForm, CustomResetPasswordKeyForm

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class CustomPasswordResetView(PasswordResetView):

    """
    Custom reset view that:

      * Uses CustomResetPasswordForm (identifier: email/username).
      * Calls PasswordResetService (sync lookup + throttle + Celery).
      * Returns a simple status via query params:
          ?status=success   -> email queued
          ?status=notfound  -> user not found
          ?status=limit     -> throttle hit
          ?status=invalid   -> form/format errors, with &msg=...
      * Keeps user on Reset tab except for success.
    """

    template_name = TemplateRegistry.PASSWORD_RESET_TAB
    form_class = CustomResetPasswordForm
    success_url = reverse_lazy("account_login")

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        Hit directly → open login page with Reset tab active.
        """
        login_url = reverse("account_login")
        return redirect(f"{login_url}?reset=1")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        """
        Called ONLY when identifier passed basic validation
        (format ok as email or username).

        We still need to:
          - Resolve user
          - Apply throttle
          - Queue Celery task
          Then redirect with appropriate status.
        """
        identifier = form.cleaned_data["identifier"].strip()
        identifier_type = form.cleaned_data.get("identifier_type")

        login_url = reverse("account_login")

        result = PasswordResetService.send_reset_link(
            identifier=identifier,
            identifier_type=identifier_type,
            request=self.request,
        )

        # Handle Unsubscribed
        if result.status == RESET_STATUS_UNSUBSCRIBED:
            messages.error(
                self.request,
                "You've unsubscribed from all emails. Contact support to re-enable password reset emails.",
                extra_tags="password_reset unsubscribe",
            )
            # Stay on Reset tab, but DO NOT mark as invalid & no generic msg
            return redirect(
                f"{login_url}?reset=1&status={RESET_STATUS_UNSUBSCRIBED}"
            )

        # Email queued (Celery task scheduled)
        elif result.status == RESET_STATUS_SUCCESS:
            # Go back to Sign In tab – no `reset=1`
            return redirect(f"{login_url}?status={RESET_STATUS_SUCCESS}")

        # No such user → stay on Reset tab
        elif result.status == RESET_STATUS_NOT_FOUND:
            messages.warning(
                self.request,
                "",
                extra_tags="password_reset notfound",
            )
            return redirect(
                f"{login_url}?reset=1&status={RESET_STATUS_NOT_FOUND}"
            )

        # Throttled → stay on Reset tab
        elif result.status == RESET_STATUS_LIMIT:
            # messages.error(
            #     self.request,
            #     "You have reached the password reset email limit. "
            #     "Please try again later.",
            #     extra_tags="password_reset limit",
            # )
            return redirect(f"{login_url}?reset=1&status={RESET_STATUS_LIMIT}")


        # Fallback safety (shouldn’t normally happen)
        return redirect(
            f"{login_url}?reset=1&status={RESET_STATUS_INVALID}"
            "&msg=Something went wrong. Please try again."
        )


    def form_invalid(self, form):
        """
        Called when identifier is empty or fails our validators
        (e.g. weird characters, invalid email format).
        We keep user on Reset tab with a warning.
        """
        error_message = None

        # Field-specific error
        if "identifier" in form.errors:
            error_message = form.errors["identifier"][0]
        # Non-field error (e.g. form-level validation)
        elif form.non_field_errors():
            error_message = form.non_field_errors()[0]

        msg = error_message or "Invalid email or username format."

        login_url = reverse("account_login")
        # URL-encode short message via query param; JS already opens Reset tab on ?reset=1
        return redirect(
            f"{login_url}?reset=1"
            f"&status={RESET_STATUS_INVALID}"
            f"&msg={msg}"
        )

    def get_success_response(self):
        # allauth default; kept for compatibility
        return redirect(self.get_success_url())


from django.views.generic import FormView
from users.services.password_reset_token_manager import (
    PasswordResetTokenManagerService,
)


class CustomPasswordResetConfirmView(FormView):
    template_name = TemplateRegistry.PASSWORD_RESET_FORM
    form_class = CustomResetPasswordKeyForm

    def dispatch(self, request, *args, **kwargs):
        # self.request.session.flush()
        self.request.session.pop("_password_reset_token", None)

        self.token = kwargs.get("token")
        self.reset_request = None
        self.reset_user = None

        reset_req, status = PasswordResetTokenManagerService.validate_token(self.token)

        if status != "ok":
            logger.warning(
                "Password reset token invalid: token=%s status=%s",
                self.token,
                status,
            )

            messages.warning(
                request,
                "The password reset link is invalid or has expired. Please request a new one.",
                extra_tags="password_reset invalid",
            )

            # Prefer where the user came from
            referer = request.META.get("HTTP_REFERER")

            if referer:
                return redirect(referer)

            # Fallbacks
            if request.user.is_authenticated:
                return redirect("console_dashboard")

            return redirect("account_login")

        # ✅ Token valid
        self.reset_request = reset_req
        self.reset_user = reset_req.user

        return super().dispatch(request, *args, **kwargs)


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.reset_user
        return kwargs

    def form_valid(self, form):
        user = form.save()

        # 🔒 Consume this token AND invalidate all others
        PasswordResetTokenManagerService.consume(self.reset_request)

        if getattr(settings, "ACCOUNT_LOGIN_ON_PASSWORD_RESET", False):
            auth_login(
                self.request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            messages.success(self.request, "Your password has been reset successfully.")
            redirect_url = reverse("console_dashboard")
        else:
            messages.success(
                self.request,
                "Your password has been reset. Please log in with your new password.",
            )
            redirect_url = reverse("account_login")


        # =========================================================
        # AUDIT LOG
        # =========================================================
        try:
            CommonService.log_user_activity(
                user=self.reset_user,
                action="RESET_PASSWORD",
                client_ip=getattr(self.reset_request, "client_ip", None),
            )
        except Exception:
            logger.exception("Failed to log RESET_PASSWORD activity")

        # Audit log (best effort)
        # try:
        #     UserActivityLog = apps.get_model("users", "UserActivityLog")
        #     client_ip = (
        #         self.request.META.get("REMOTE_ADDR")
        #         or self.request.META.get("HTTP_X_FORWARDED_FOR")
        #     )
        #     if client_ip and "," in client_ip:
        #         client_ip = client_ip.split(",")[0].strip()

        #     UserActivityLog.objects.create(
        #         user=user,
        #         action="RESET_PASSWORD",
        #         client_ip=client_ip,
        #         created_at=timezone.now(),
        #     )
        # except Exception:
        #     logger.exception("Failed to log RESET_PASSWORD activity")

        return redirect(redirect_url)
