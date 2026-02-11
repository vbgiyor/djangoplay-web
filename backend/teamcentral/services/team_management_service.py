import logging

from django.db import transaction
from users.exceptions import TeamValidationError
from utilities.utils.general.normalize_text import normalize_text

from teamcentral.models import Team

logger = logging.getLogger(__name__)


class TeamManagementService:

    @staticmethod
    def validate_team_payload(data, *, instance=None):
        if not data.get("name"):
            raise TeamValidationError("Team name required")

        return normalize_text(data["name"])

    @staticmethod
    @transaction.atomic
    def create_team(*, data: dict, created_by):
        name = TeamManagementService.validate_team_payload(data)

        team = Team(
            name=name,
            department=data["department"],
            leader=data.get("leader"),
            created_by=created_by,
        )
        team.save(user=created_by)

        logger.info("Team created name=%s", name)
        return team
