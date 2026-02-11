# frontend/views/manual_verify_email.py
import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from users.services.identity_signup_flow_service import SignupFlowService

logger = logging.getLogger(__name__)


class ManualVerifyEmailView(View):

    def post(self, request):
        data = {
            "email": request.POST.get("email"),
            "username": request.POST.get("username"),
            "password": request.POST.get("password"),
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "department": request.POST.get("department"),
        }

        try:
            employee, member, status = SignupFlowService.handle_manual_signup(
                data=data,
                request=request,
            )
        except Exception:
            logger.exception("Manual signup failed")
            messages.error(request, "Signup failed. Please try again.")
            return redirect(reverse("account_login"))

        messages.info(
            request,
            "Signup successful. Check your email to verify your account.",
        )
        return redirect(reverse("account_login") + "?email_sent=true")
