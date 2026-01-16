import logging

logger = logging.getLogger(__name__)


class BaseFilterMixin:

    """
    Base helper for filter mixins.
    Provides standardized error raising using `error_class`.
    """

    error_class = None  # inherited from view

    def raise_invalid(self, field: str, value, message: str = None):
        """
        Raise a standardized invalid-field error.
        """
        msg = message or f"Invalid value for {field}: {value}"
        raise self.error_class(
            msg,
            code="invalid_fields",
            details={"field": field, "value": value},
        )
