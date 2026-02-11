import logging
import smtplib
import socket

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from users.adapters.context.email import EmailContextProvider
from users.adapters.context.password_reset import PasswordResetContextProvider
from users.adapters.context.support import SupportContextProvider
from utilities.constants.template_registry import TemplateRegistry as T

from mailer.engine.inline_images import InlineImageService
from mailer.engine.templates import TemplateResolver
from mailer.engine.unsubscribe import UnsubscribeService

logger = logging.getLogger(__name__)


class EmailEngine:

    """
    ============================================================================
    CENTRAL EMAIL ENGINE FOR ADAPTERS
    ----------------------------------------------------------------------------
    This module provides the full DRY email orchestration used by:

        • CustomAccountAdapter.send_mail
        • Celery tasks calling send_email_via_adapter
        • Any future unified mail system (mobile, SPA, etc.)

    It intentionally contains NO business logic for:
        - password reset
        - signup flow
        - onboarding
        - bug/support throttles

    All business logic must stay in services.

    This class focuses ONLY on:
        - default context injection
        - unsubscribe enforcement
        - template resolution
        - inline image attachment
        - building & sending emails

    ============================================================================
    """

    # ------------------------------------------------------------------
    # Shared default context injector (from your old adapter)
    # ------------------------------------------------------------------
    @staticmethod
    def inject_defaults(context: dict) -> dict:
        """
        Adds site_name, expiry days, etc.
        Mirrors the helpful defaults you originally injected in the adapter.
        """
        expiry_map = getattr(settings, "LINK_EXPIRY_DAYS", {})

        defaults = {
            "verification_expiry_days": expiry_map.get("email_verification", 7),
            "password_reset_expiry_days": expiry_map.get("password_reset", 2),
            "unsubscribe_expiry_days": expiry_map.get("unsubscribe", 30),
            "site_name": getattr(settings, "SITE_NAME", None)
            or getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        }

        for key, value in defaults.items():
            if not context.get(key):
                context[key] = value


        return context

    # ------------------------------------------------------------------
    # Resolve Employee from context (same logic you had, preserved DRY)
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_user(email: str, context: dict):
        """
        Attempt to resolve an Employee instance based on various hints
        (member, employee, ticket, context['email'], fallback).
        """
        user = context.get("user")

        if not user:
            # Member → Employee
            member = context.get("member")
            if member and hasattr(member, "employee"):
                user = member.employee

        if not user and context.get("employee"):
            user = context["employee"]

        return user

    # # ------------------------------------------------------------------
    # # Build unsubscribe URL using service abstraction
    # # ------------------------------------------------------------------
    # @staticmethod
    # def attach_unsubscribe_url(context: dict, user):
    #     if "unsubscribe_url" in context:
    #         return  # already set by the caller

    #     if not user:
    #         context["unsubscribe_url"] = "#"
    #         return

    #     url = UnsubscribeService.build_unsubscribe_url(user)
    #     context["unsubscribe_url"] = url


    # ------------------------------------------------------------------
    # Main send entrypoint
    # ------------------------------------------------------------------
    @staticmethod
    def send(prefix: str, email: str, context: dict, request=None, user=None):
        """
        MAIN SEND METHOD
        ----------------
        • prefix → template prefix (e.g., "account_signup")
        • context → template context
        • email → target recipient

        Responsibilities:
            - resolve user
            - enforce unsubscribe rules
            - attach unsubscribe URL
            - template rendering (subject + txt + html)
            - inline images (logo and optional signature/icons)
            - send email safely
        """
        email = email.lower().strip()

        # Explicit user always wins
        explicit_user = user
        if explicit_user and "user" not in context:
            context["user"] = explicit_user

        # Normalize prefix once for engine logic
        normalized_prefix = TemplateResolver(prefix).prefix

        # Skip redstar globally (your existing behavior)
        if email == "redstar@djangoplay.com":
            logger.info("EmailEngine.send: skipping redstar email for prefix=%s", prefix)
            return None

        # Resolve user from context
        if not explicit_user:
            explicit_user = EmailEngine.resolve_user(email, context)
            if explicit_user and "user" not in context:
                context["user"] = explicit_user

        # Inject defaults
        context = EmailEngine.inject_defaults(context)

        # Inject canonical email context
        for k, v in EmailContextProvider.get().items():
            context.setdefault(k, v)

        # ------------------------------------------------------------------
        # Invariant enforcement: password reset emails must have reset_url
        # ------------------------------------------------------------------
        if prefix == T.PASSWORD_RESET_EMAIL:
            if not context.get("reset_url"):
                logger.critical(
                    "INVARIANT VIOLATION: reset_url missing for PASSWORD_RESET_EMAIL. "
                    "user=%s context_keys=%s",
                    getattr(user, "pk", None),
                    sorted(context.keys()),
                )
                raise RuntimeError(
                    "reset_url must be present in context for PASSWORD_RESET_EMAIL"
                )

        if normalized_prefix == T.PASSWORD_RESET_EMAIL and user:
            PasswordResetContextProvider.inject_password_reset_context(user=user, context=context)

        # ------------------------------------------------------------------
        # Enforce unsubscribe URL using service abstraction
        # ------------------------------------------------------------------
        effective_user = context.get("user")

        if not UnsubscribeService.is_allowed(effective_user, normalized_prefix):
            logger.info(
                "EmailEngine.send: blocked by unsubscribe policy "
                "(user=%s prefix=%s)",
                getattr(effective_user, "pk", None),
                normalized_prefix,
            )
            return None

        if (effective_user and "unsubscribe_url" not in context):
            context["unsubscribe_url"] = UnsubscribeService.build_unsubscribe_url(effective_user)

        # Support context (phone, github, linkedin, etc.)
        context.update(SupportContextProvider.get())

        # Template rendering
        try:
            resolver = TemplateResolver(normalized_prefix)
            # subject = resolver.render("_subject.txt", context).strip()
            subject = resolver.render("_subject.txt", context).strip()
            assert subject and subject != "Password Reset", subject
            text_body = resolver.render(".txt", context)
            html_body = resolver.render(".html", context)
        except Exception as e:
            logger.error("EmailEngine.send: template resolution failed for %s: %s", prefix, e)
            raise

        # Build the message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            to=[email],
        )
        msg.attach_alternative(html_body, "text/html")

        # Inline logo (always)
        InlineImageService.attach_logo(msg)

        # Signature images only for specific prefixes
        SIGNATURE_PREFIXES = {
            "account_signup",
        }
        if prefix in SIGNATURE_PREFIXES:
            InlineImageService.attach_signature_image(msg)
            InlineImageService.attach_contact_icons(msg)

        # Send email
        try:
            msg.send()
            logger.info("EmailEngine.send: delivered → %s (prefix=%s)", email, prefix)
            return msg
        except (socket.gaierror, smtplib.SMTPException, OSError) as e:
            logger.warning(
                "EmailEngine.send: network/SMTP failure sending to %s (prefix=%s): %s",
                email,
                prefix,
                e,
            )
            if request and hasattr(request, "_messages"):
                messages.error(
                    request,
                    "We could not send the email due to network or email service issues.",
                )
            return None
        except Exception as e:
            logger.exception("EmailEngine.send: unexpected error sending to %s: %s", email, e)
            raise
