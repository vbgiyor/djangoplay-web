# Shared base logic

def get_user_role(user):
    """Retrieve the user's role code."""
    role = getattr(user, 'role', None)
    return role.code if role else None

def get_user_department(user):
    """Retrieve the user's department code."""
    department = getattr(user, 'department', None)
    return department.code if department else None

def is_user_active(user):
    """Check if the user has an active employment status."""
    return hasattr(user, 'employment_status') and user.employment_status.code == 'ACTV'
