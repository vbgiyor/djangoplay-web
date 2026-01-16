# from django.core.exceptions import ValidationError
# from locations.models.custom_country import CustomCountry


# def validate_currency(value):
#     """Validate currency against active CustomCountry currency codes."""
#     if value:
#         valid_currencies = CustomCountry.objects.filter(
#             is_active=True, deleted_at__isnull=True
#         ).values_list('currency_code', flat=True).distinct()
#         if value not in valid_currencies:
#             raise ValidationError(
#                 f"Currency must be one of {list(valid_currencies)}.",
#                 code="invalid_currency"
#             )

# @staticmethod
# def get_currency_choices():
#     """Return currency choices from active CustomCountry currency codes."""
#     return [(code, code) for code in CustomCountry.objects.filter(
#         is_active=True, deleted_at__isnull=True
#     ).values_list('currency_code', flat=True).distinct() if code]
