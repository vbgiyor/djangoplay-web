from users.constants import DEPARTMENT_CODES

PERMISSION_DEPARTMENTS = {
    'read': {dept[0] for dept in DEPARTMENT_CODES.items()},
    'write': {'FIN', 'SSO'},
}
