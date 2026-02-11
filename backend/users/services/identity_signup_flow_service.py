import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email, user_field
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import transaction
from django.utils import timezone

from users.exceptions import EmployeeValidationError
from users.models import Employee
from users.services.identity_verification_token_service import (
    SignupTokenManagerService,
)

if TYPE_CHECKING:
    from users.models import SignUpRequest

logger = logging.getLogger(__name__)
UserModel = get_user_model()

# ---------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------
@dataclass
class SignupSaveResult:
    user: Optional[AbstractBaseUser] = None
    signup_request: Optional["SignUpRequest"] = None


# ---------------------------------------------------------------------
# Identity Signup Service
# ---------------------------------------------------------------------
class SignupFlowService:

    """
    Identity-only signup orchestration.

    HARD RULES:
    - No teamcentral imports
    - No HR policy decisions
    - No lifecycle semantics
    - Enforces identity invariants only
    """

    # ------------------------------------------------------------------
    # Identity invariants
    # ------------------------------------------------------------------
    @staticmethod
    def _assert_identity_not_exists(email: str) -> None:
        """
        Identity invariant:
        One email == one identity.
        """
        if Employee.objects.filter(email=email).exists():
            raise EmployeeValidationError(
                {"email": "An account already exists with this email address."},
                code="duplicate_employee_code",
            )

    # ------------------------------------------------------------------
    # MANUAL SIGNUP (email/password)
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def handle_manual_signup(
        *,
        data: dict,
        request,
        hr_defaults: dict,
    ) -> SignupSaveResult:
        """
        Creates the identity (Employee).

        HR meaning is injected via hr_defaults but NOT owned here.
        """
        email = data["email"].strip().lower()

        # Enforce identity invariant
        SignupFlowService._assert_identity_not_exists(email)

        # Create identity shell (Employee IS the identity aggregate)
        user = UserModel(
            email=email,
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_active=True,
            is_verified=False,
            sso_provider="EMAIL",

            # --- Injected HR fields (identity does not own meaning) ---
            department=hr_defaults["department"],
            role=hr_defaults["role"],
            employment_status=hr_defaults["employment_status"],
            employee_type=hr_defaults["employee_type"],
            hire_date=timezone.now().date(),
        )

        user.set_password(data["password"])
        user.save()

        from policyengine.components.ssopolicies import setup_role_based_group

        # Assign default role-based permissions
        default_role_code = hr_defaults["role"].code
        default_group = setup_role_based_group(default_role_code)
        user.groups.add(default_group)

        if not user.groups.exists():
            logger.warning(
                "Employee %s created without groups – assigning default role group",
                user.email,
            )

        # EmailAddress record (single source of truth)
        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": False, "primary": True},
        )

        # Verification token
        signup_request, _ = SignupTokenManagerService.create_for_user(
            user=user,
            request=request,
        )

        logger.info("Identity created for %s", user.email)
        return SignupSaveResult(
            user=user,
            signup_request=signup_request,
        )

    # ------------------------------------------------------------------
    # ALLAUTH SIGNUP (email / social)
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def handle_allauth_signup(request, user, form, commit=True) -> SignupSaveResult:
        """
        Identity enrichment for django-allauth flows.
        """
        data = form.cleaned_data
        email = data.get("email", "").lower()

        # Identity invariant (allauth may call save twice)
        if not user.pk:
            SignupFlowService._assert_identity_not_exists(email)

        # Identity-only fields
        user_email(user, email)
        user_field(user, "first_name", data.get("first_name", ""))
        user_field(user, "last_name", data.get("last_name", ""))
        user.sso_provider = user.sso_provider or "EMAIL"
        user.is_active = True

        # DB constraint safety
        if not getattr(user, "hire_date", None):
            user.hire_date = timezone.now().date()

        if commit:
            user.save()

        EmailAddress.objects.update_or_create(
            user=user,
            email=user.email,
            defaults={"verified": user.is_verified, "primary": True},
        )

        # Token for unverified identities
        if not user.is_verified:
            SignupTokenManagerService.create_for_user(
                user=user,
                request=request,
            )

        logger.info("Allauth identity saved for %s", user.email)
        return SignupSaveResult(user=user)

    # ------------------------------------------------------------------
    # EMAIL CONFIRMATION (identity-only)
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def handle_email_confirmation(email_address) -> None:
        """
        Called by CustomAccountAdapter.confirm_email.

        Identity responsibility ONLY:
        - mark verified
        """
        try:
            user = UserModel.objects.get(email=email_address.email)
        except UserModel.DoesNotExist:
            logger.info(
                "Email confirmation ignored: no identity found for %s",
                email_address.email,
            )
            return

        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            logger.info("Identity verified for %s", user.email)
