# Check if user is verified employee

def user_is_verified_employee(request):
    """Return True only if logged-in user is a verified Employee."""
    return (
        request.user.is_authenticated
        and hasattr(request.user, 'is_verified')
        and request.user.is_verified
    )
