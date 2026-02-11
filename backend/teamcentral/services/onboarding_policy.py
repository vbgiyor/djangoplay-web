
import logging

from django.core.exceptions import ValidationError

from teamcentral.models import (
    Department,
    EmployeeType,
    EmploymentStatus,
    MemberStatus,
    Role,
)

logger = logging.getLogger(__name__)


class OnboardingPolicy:

    """
    Central HR onboarding policy.

    This class owns:
    - Default department
    - Default role
    - Default employment status
    - Default employee type
    - Default member status

    Identity layer MUST NOT import this.
    """

    @staticmethod
    def default_employee_defaults() -> dict:
        try:
            return {
                "department": Department.objects.get(code="SSO"),
                "role": Role.objects.get(code="SSO"),
                "employment_status": EmploymentStatus.objects.get(code="PEND"),
                "employee_type": EmployeeType.objects.get(code="SSO"),
            }
        except Exception as exc:
            logger.error("Employee onboarding defaults missing: %s", exc)
            raise ValidationError(
                "Employee onboarding configuration is incomplete. "
                "Please contact an administrator."
            )

    @staticmethod
    def default_member_status() -> MemberStatus:
        try:
            return MemberStatus.objects.get(code="PEND")
        except Exception as exc:
            logger.error("Member onboarding status missing: %s", exc)
            raise ValidationError(
                "Member onboarding configuration is incomplete. "
                "Please contact an administrator."
            )
