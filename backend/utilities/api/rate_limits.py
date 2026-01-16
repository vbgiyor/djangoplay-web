from core.middleware import thread_local
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class CustomThrottle(SimpleRateThrottle):
    scope = 'custom'
    rate = '50/hour'

    def get_cache_key(self, request, view):
        ident = request.META.get('REMOTE_ADDR')
        return f"throttle_{self.scope}_{ident}"


class CustomSearchThrottle(SimpleRateThrottle):
    scope = 'custom_search'
    rate = '100/hour'

    def get_cache_key(self, request, view):
        ident = request.META.get('REMOTE_ADDR')
        return f"throttle_{self.scope}_{ident}"


class TokenThrottle(UserRateThrottle):
    rate = '50/hour'

class BugReportThrottle(SimpleRateThrottle):
    scope = "bug_report"
    rate = "20/day"

    def get_cache_key(self, request, view):
        """
        DRF still requires a cache key, but the actual limit is enforced
        via BugService.can_submit_bug().
        """
        user = getattr(request, "user", None)
        employee = getattr(user, "employee", None) if user and user.is_authenticated else None
        email = request.data.get("email")
        ip = getattr(thread_local, "client_ip", None)
        ident = f"{employee.id if employee else ''}_{email}_{ip}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


# ----------------------------------------------------------------------
#  Generic decorator that works with *any* DRF-style throttle class
# ----------------------------------------------------------------------
def throttle(throttle_cls):
    """
    Decorator for plain Django views.
    It instantiates ``throttle_cls`` and calls ``allow_request``.
    If the request is throttled a 429 JsonResponse is returned.
    """
    def decorator(view_func):
        from functools import wraps
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # DRF throttles expect ``request`` and ``view`` attributes
            throttle = throttle_cls()
            throttle.request = request
            # ``history`` is filled by ``allow_request`` – we just give it a dummy
            throttle.history = None

            if not throttle.allow_request(request, view_func):
                wait = throttle.wait()
                msg = (
                    f"Too many bug reports. Try again in {int(wait)} seconds."
                    if wait else
                    "Rate limit exceeded."
                )
                return JsonResponse({'error': msg}, status=429)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
