from decimal import Decimal


def get_safe_decimal(value):
    """
    Safely converts a value to a Decimal, returning Decimal('0.00') for None.
    """
    if value is None:
        return Decimal('0.00')
    try:
        return Decimal(value)
    except (TypeError, ValueError):
        return Decimal('0.00')
