"""Constants for the entities app."""

ENTITY_TYPE_CHOICES = [
    ('INDIVIDUAL', 'Individual'),
    ('BUSINESS', 'Business'),
    ('GOVERNMENT', 'Government'),
    ('NONPROFIT', 'Nonprofit'),
    ('PARTNERSHIP', 'Partnership'),
    ('SOLE_PROPRIETORSHIP', 'Sole Proprietorship'),
    ('OTHER', 'Other'),
]

ENTITY_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('ACTIVE', 'Active'),
    ('INACTIVE', 'Inactive'),
    ('SUSPENDED', 'Suspended'),
    ('ON_HOLD', 'On Hold'),
]
