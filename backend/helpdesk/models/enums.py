from django.db import models


class Severity(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class SupportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class BugStatus(models.TextChoices):
    NEW = "NEW", "New"
    TRIAGED = "TRIAGED", "Triaged"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    FIXED = "FIXED", "Fixed"
    VERIFIED = "VERIFIED", "Verified"
    CLOSED = "CLOSED", "Closed"
