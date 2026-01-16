from users.constants import ROLE_CODES

# Define permission roles based on ROLE_CODES
PERMISSION_ROLES = {
    'read': {role[0] for role in ROLE_CODES.items()},  # All roles can read
    'write': {'CEO', 'DJGO', 'CFO'},
    'delete': {'CEO', 'DJGO'},
}
