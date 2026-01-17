import logging

from allauth.account.models import EmailAddress
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import View
from mailer.engine.unsubscribe import UnsubscribeService
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)


class UnsubscribeView(View):
    template_name = TemplateRegistry.UNSUBSCRIBE

    def get(self, request, uidb64=None, token=None):
        context = {
            "email": "",
            "valid_link": False,
            "unsubscribed": False,
            "error": None,
            "show_form": False,
        }

        user, error = (
            UnsubscribeService.validate_unsubscribe_token(uidb64, token)
            if (uidb64 and token)
            else (None, None)
        )

        if not user:
            context["error"] = error or "Invalid unsubscribe link."
            return render(request, self.template_name, context, status=404)

        # --------------------------------------------------
        # Already fully unsubscribed (EXPLICIT conditions)
        # --------------------------------------------------
        # If already unsubscribed → show success, NOT form
        if getattr(user, "is_unsubscribed", False):
            context.update({
                "unsubscribed": True,
                "email": user.email,
            })
            return render(request, self.template_name, context)

        # Otherwise show unsubscribe form
        context.update({
            "email": user.email,
            "valid_link": True,
            "show_form": True,
        })
        return render(request, self.template_name, context)

    def post(self, request, uidb64=None, token=None):
        context = {
            "email": "",
            "valid_link": False,
            "unsubscribed": False,
            "error": None,
            "show_form": False,
        }

        if not (uidb64 and token):
            context["error"] = "Invalid unsubscribe link."
            return render(request, self.template_name, context, status=404)

        user, error = validate_unsubscribe_token(uidb64, token)
        if not user:
            context["error"] = error or "Invalid unsubscribe link."
            return render(request, self.template_name, context, status=404)

        email_to_unsubscribe = user.email

        try:
            selected_prefs = set(request.POST.getlist("preferences"))
            all_keys = ["newsletters", "offers", "updates"]

            user_prefs = user.preferences or dict.fromkeys(all_keys, True)

            # No selection → unsubscribe from all
            if not selected_prefs:
                for key in all_keys:
                    user_prefs[key] = False
            else:
                for key in all_keys:
                    if key in selected_prefs:
                        user_prefs[key] = False

            user.preferences = user_prefs

            EmailAddress.objects.filter(
                user=user,
                email=email_to_unsubscribe,
            ).update(
                primary=False,
                verified=False,
            )

            update_fields = ["preferences"]
            if hasattr(user, "is_unsubscribed"):
                user.is_unsubscribed = True
                user.unsubscribed_at = timezone.now()
                update_fields += ["is_unsubscribed", "unsubscribed_at"]

            user.save(update_fields=update_fields)

            context.update({
                "unsubscribed": True,
                "email": email_to_unsubscribe,
            })

            logger.info("User unsubscribed successfully: %s", email_to_unsubscribe)

        except Exception as e:
            logger.error("Unsubscribe failed for %s: %s", email_to_unsubscribe, e)
            context["error"] = "An error occurred. Please try again or contact support."
            return render(request, self.template_name, context, status=500)

        return render(request, self.template_name, context)
