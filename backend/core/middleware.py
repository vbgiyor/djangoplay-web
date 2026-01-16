import logging
import threading

from apidocs.models.apirequestlog import APIRequestLog
from django.http import HttpRequest, JsonResponse
from django.urls import Resolver404, resolve
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

thread_local = threading.local()

class ClientIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract and store the client IP in thread-local storage
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        thread_local.client_ip = ip
        logger.debug(f"Stored client IP: {thread_local.client_ip}")
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Clear thread-local data on exception to prevent memory leaks
        thread_local.client_ip = None
        logger.error(f"Exception occurred, cleared client IP: {str(exception)}", exc_info=True)
        # Return JSON response for API requests
        if request.path.startswith('/organizations/'):
            return JsonResponse({'error': f'Server error: {str(exception)}'}, status=500)
        return None


class URLResolutionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        try:
            # Resolve the URL path
            resolved = resolve(request.path_info)
            logger.debug(
                f"Resolved URL: {request.path_info} to view {resolved.view_name} "
                f"(func: {resolved.func.__qualname__}, namespace: {resolved.namespace})"
            )
        except Resolver404 as e:
            logger.debug(f"URL resolution failed for {request.path_info}: {str(e)}")
        except Exception as e:
            logger.error(f"Error resolving URL {request.path_info}: {str(e)}", exc_info=True)

        # Check for potential conflicts by scanning all URL patterns
        from django.urls import get_resolver
        resolver = get_resolver()
        conflicting_patterns = []
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'pattern') and pattern.pattern.match(request.path_info):
                conflicting_patterns.append(str(pattern.pattern))

        if len(conflicting_patterns) > 1:
            logger.warning(
                f"Potential URL conflict for {request.path_info}. "
                f"Matched patterns: {', '.join(conflicting_patterns)}"
            )

        response = self.get_response(request)
        return response


class APIRequestLoggingMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            # Log only API calls
            if request.path.startswith('/api/') or request.path.startswith('/console/') and request.method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
                user = getattr(request, 'user', None)

                # If Django auth hasn't authenticated the user (e.g. JWT), try JWT manually
                if not user or not getattr(user, "is_authenticated", False):
                    try:
                        from rest_framework_simplejwt.authentication import JWTAuthentication
                        authenticator = JWTAuthentication()
                        auth_result = authenticator.authenticate(request)
                        if auth_result is not None:
                            user, _ = auth_result
                    except Exception as e:
                        # Don't break the response if auth fails; just log it
                        logger.debug(f"JWT auth in APIRequestLoggingMiddleware failed: {e}")

                APIRequestLog.objects.create(
                    user=user if getattr(user, "is_authenticated", False) else None,
                    path=request.path,
                    method=request.method,
                    response_status=getattr(response, "status_code", 0),
                    client_ip=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
        except Exception as e:
            # Make absolutely sure logging never breaks your API
            logger.error(f"Error logging API request: {e}", exc_info=True)

        return response
