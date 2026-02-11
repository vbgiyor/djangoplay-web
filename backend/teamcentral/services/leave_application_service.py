import logging

from django.db import transaction

from teamcentral.models import LeaveApplication

logger = logging.getLogger(__name__)


class LeaveApplicationService:

    @staticmethod
    @transaction.atomic
    def create_application(*, data: dict, created_by):
        application = LeaveApplication(**data, created_by=created_by)
        application.save(user=created_by)
        logger.info("Leave application created id=%s", application.id)
        return application
