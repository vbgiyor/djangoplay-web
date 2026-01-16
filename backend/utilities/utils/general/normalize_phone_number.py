# def normalize_phone_number(self, phone_number):
#     """Normalize phone number by removing spaces and ensuring +64 prefix."""
#     if not phone_number:
#         return phone_number
#     # Remove spaces and other characters
#     phone_number = ''.join(filter(str.isdigit, phone_number))
#     # Ensure +64 prefix
#     if phone_number.startswith('64'):
#         phone_number = '+' + phone_number
#     elif phone_number.startswith('0'):
#         phone_number = '+64' + phone_number[1:]
#     return phone_number
