import logging

from django.db import transaction

from teamcentral.models import LeaveBalance

logger = logging.getLogger(__name__)


class LeavePolicyService:

    @staticmethod
    @transaction.atomic
    def allocate_leave_balance(*, employee, leave_type, year, balance, created_by):
        existing = LeaveBalance.objects.filter(
            employee=employee,
            leave_type=leave_type,
            year=year,
            deleted_at__isnull=True,
        ).first()

        if existing:
            return existing

        lb = LeaveBalance(
            employee=employee,
            leave_type=leave_type,
            year=year,
            balance=balance,
            used=0,
            created_by=created_by,
        )
        lb.save(user=created_by)
        logger.info("Leave balance allocated emp=%s", employee.employee_code)
        return lb
