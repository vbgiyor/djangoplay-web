from enum import StrEnum


class IssueLabelSlug(StrEnum):

    """
    Canonical Issue label slugs.

    These values are the source of truth across the integration layer.
    """

    BUG_INTERNAL = "bug-internal"
    BUG_PUBLIC = "bug-public"


class IssueLabelMeta(StrEnum):

    """
    Canonical Issue label display metadata.
    """

    BUG_INTERNAL_NAME = "🐞 INTERNAL"
    BUG_PUBLIC_NAME = "🐞 PUBLIC"
