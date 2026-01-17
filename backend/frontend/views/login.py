import logging

from allauth.account.views import LoginView as AllauthLoginView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils.safestring import mark_safe
from users.services.unified_login import UnifiedLoginService
from utilities.constants.template_registry import TemplateRegistry
from mailer.engine.verification_guard import handle_unverified_email

logger = logging.getLogger(__name__)


# ===================================================================
# WEB LOGIN VIEW
# ===================================================================
class ConsoleLoginView(AllauthLoginView):

    """
    Console login (UI login form).
    Uses Allauth's authentication pipeline but adds UnifiedLoginService
    *after* user is authenticated.
    """

    template_name = TemplateRegistry.CONSOLE_LOGIN_FORM

    def post(self, request, *args, **kwargs):
        """
        Allauth's LoginForm expects a field named `login`.
        Your UI uses `email`, so map it before validation.
        """
        request.POST._mutable = True

        # Map email -> login so Allauth can validate it
        if "email" in request.POST and "login" not in request.POST:
            request.POST["login"] = request.POST["email"]

        request.POST._mutable = False

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # TODO: MFA to be implemented later here
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return reverse("console_dashboard")

    def form_invalid(self, form):
        """
        Ensures we show meaningful errors for:
        - Non-existent user
        - Invalid username/email characters
        - Empty login field
        - Wrong password
        """
        if getattr(form, "_unified_login_error_handled", False):
            return super().form_invalid(form)

        login_input = (form.cleaned_data.get("login") or form.data.get("login") or "").strip()
        User = get_user_model()

        user_exists = User.objects.filter(
            Q(email__iexact=login_input) | Q(username__iexact=login_input),
            deleted_at__isnull=True,
            is_active=True,
        ).exists()

        if not user_exists:
            messages.error(
                self.request,
                mark_safe(
                    "No account found with this email or username.<br>"
                    "Please use correct username/email or create a new account."
                )
            )
            return super().form_invalid(form)

        user_obj = User.objects.filter(
            Q(email__iexact=login_input) | Q(username__iexact=login_input)
        ).first()

        if user_obj:
            validation = UnifiedLoginService.validate_user(user_obj)
            if validation.reason == "EMAIL_NOT_VERIFIED":
                return handle_unverified_email(
                    request=self.request,
                    email=user_obj.email,
                    context="login",
                )
            return super().form_invalid(form)

        messages.error(
            self.request,
            "Incorrect password. Please try again."
        )

        return super().form_invalid(form)

# ===================================================================
# API LOGIN (Swagger / Redoc) — FORM-BASED FLOW
# ===================================================================
class ApiLoginView(AllauthLoginView):

    """
    API Console login (Swagger / ReDoc).
    Two-step flow:
        STEP 1 → User enters email, we verify access, show password screen
        STEP 2 → User enters password, Allauth handles authentication
    UnifiedLoginService is applied after authentication.
    """

    template_name = TemplateRegistry.API_LOGIN_FORM

    # --------------------------------------------------------------
    # Console type detection
    # --------------------------------------------------------------
    def get_console_type_from_request(self):
        """
        Determine console type from URL name OR ?from= param.
        This is used ONLY on GET, before login.
        """
        if self.request.resolver_match:
            url_name = self.request.resolver_match.url_name
            if url_name == "redoc_console":
                return "redoc"
            if url_name == "api_console":
                return "api"

        return self.request.GET.get("from", "api")

    def get_console_type(self):
        """
        After the login process begins, console type MUST COME FROM SESSION.
        This ensures redirect correctness even during password POST and allauth redirects.
        """
        return self.request.session.get("login_from", "api")

    # --------------------------------------------------------------
    # Redirect helpers
    # --------------------------------------------------------------
    def get_permission_codename(self):
        console = self.get_console_type()
        return "apidocs.view_redoc" if console == "redoc" else "apidocs.view_swagger"

    def get_redirect_url(self):
        console = self.get_console_type()
        return reverse("apidocs:redoc") if console == "redoc" else reverse("apidocs:swagger-ui")

    def get_success_url(self):
        """
        Ensures correct redirect after successful authentication.
        """
        console = self.get_console_type()
        next_url = self.request.POST.get("next") or self.request.GET.get("next")

        if next_url and next_url.startswith("/"):
            return next_url

        return reverse("apidocs:redoc") if console == "redoc" else reverse("apidocs:swagger-ui")

    # --------------------------------------------------------------
    # Authentication success hook (Allauth)
    # --------------------------------------------------------------
    def form_valid(self, form):
        user = form.user

        # Strict unified validation
        validation = UnifiedLoginService.validate_user(user)
        if not validation.ok:
            if validation.reason == "EMAIL_NOT_VERIFIED":
                return handle_unverified_email(
                    request=self.request,
                    email=user.email,
                    context="login",
                )

            messages.error(
                self.request,
                UnifiedLoginService.map_reason_to_message(validation.reason)
            )
            return self.form_invalid(form)
        # TODO: MFA extension goes here

        return super().form_valid(form)

    # --------------------------------------------------------------
    # GET = Always show Step 1 → email entry screen
    # --------------------------------------------------------------
    def get(self, request, *args, **kwargs):
        console = self.get_console_type_from_request()

        # Persist console type for entire login lifecycle
        request.session["login_from"] = console

        return render(
            request,
            self.template_name,
            {
                "email": "",
                "u": "false",
                "from": console,
                "show_password": False,
                "console_title": "Redoc OpenAPI Specs" if console == "redoc" else "Interactive API Console",
                "submit_button_text": "Launch Redoc Specs" if console == "redoc" else "Launch API Console",
                "next": self.get_redirect_url(),
            },
        )

    # --------------------------------------------------------------
    # POST dispatcher: Step 1 or Step 2
    # --------------------------------------------------------------
    def post(self, request, *args, **kwargs):
        console = self.get_console_type()
        User = get_user_model()

        # STEP 2 → Password present → Delegate to Allauth LoginView
        if "password" in request.POST:
            logger.info("ApiLoginView: STEP 2 (password entry) → Allauth handles authentication")
            return super().post(request, *args, **kwargs)

        # STEP 1 → Only email entered → Determine if user exists + has permission
        login_input = (request.POST.get("email") or request.POST.get("login") or "").strip().lower()

        if not login_input:
            messages.error(request, "Email or Username is required.")
            return self.get(request, *args, **kwargs)

        user = User.objects.filter(
            Q(email__iexact=login_input) | Q(username__iexact=login_input),
            is_active=True
        ).first()

        if not user:
            messages.error(request, "No account found with this email or username.")
            return self.get(request, *args, **kwargs)

        # Permission check for API console access (STEP 1)
        if not (user.is_superuser or user.has_perm(self.get_permission_codename())):
            return self.handle_permission_denied()

        # If allowed, show password screen (STEP 2)
        messages.success(request, "You're authorized. Please enter your password.")

        return render(
            request,
            self.template_name,
            {
                "email": login_input,
                "show_password": True,
                "next": self.get_redirect_url(),
                "from": console,
                "u": "false",
                "console_title": "Redoc OpenAPI Specs" if console == "redoc" else "Interactive API Console",
                "submit_button_text": "Launch Redoc Specs" if console == "redoc" else "Launch API Console",
            },
        )

    # --------------------------------------------------------------
    # Permission denied screen
    # --------------------------------------------------------------
    def handle_permission_denied(self):
        console = self.get_console_type()

        return render(
            self.request,
            TemplateRegistry.ACCOUNT_403,
            {
                "error_message": (
                    "You don't have access to view the ReDoc API Console."
                    if console == "redoc"
                    else "You don't have access to view the Swagger API Console."
                ),
                "from": console,
            },
            status=403,
        )
