import logging

from django.shortcuts import redirect, render
from django.urls import reverse
from rest_framework.views import exception_handler
from utilities.constants.template_registry import TemplateRegistry

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# Extract parent /console/<app>/<model>/ URL
# -------------------------------------------------------------
def get_console_parent_url(path: str):
    """
    Extract /console/<app>/<model>/ from ANY console admin path.
    Works for add, change, list, etc.
    """
    path = path.rstrip("/")
    parts = path.split("/")  # ['', 'console', 'app', 'model', ...]

    if len(parts) >= 4 and parts[1] == "console":
        return f"/console/{parts[2]}/{parts[3]}/"

    return None


# -------------------------------------------------------------
# Global 403 handler
# -------------------------------------------------------------
def custom_403(request, exception=None):
    logger.warning(f"403 Forbidden: {request.path} – User: {request.user}")

    path_lower = request.path.lower()
    from_param = request.GET.get("from", "")

    # Auto-detect source if no ?from=
    if not from_param:
        if "redoc" in path_lower:
            from_param = "redoc"
        elif "swagger" in path_lower or "api" in path_lower:
            from_param = "api"
        else:
            from_param = "dashboard"

    # Redirect ReDoc/Swagger
    if "redoc" in path_lower or "swagger" in path_lower:
        return redirect("/api/v1/accounts/api-login/?u=false&from=redoc")

    # 1. Try HTTP referrer
    back_url = request.META.get("HTTP_REFERER")
    if not back_url or request.get_host() not in (back_url or ""):
        back_url = None

    # 2. Console: /console/<app>/<model>/
    parent = get_console_parent_url(request.path)
    if parent:
        back_url = parent

    # 3. Django Admin → redirect to console equivalent
    if request.path.startswith("/admin/"):
        parts = request.path.rstrip("/").split("/")
        # ['', 'admin', 'app', 'model']
        if len(parts) >= 4:
            app_label, model_name = parts[2], parts[3]
            if app_label == "users":
                back_url = reverse('console_dashboard')
            else:
                back_url = f"/console/{app_label}/{model_name}/"

    # DEFAULT fallback
    if not back_url:
        back_url = reverse("console_dashboard")

    back_url = request.META.get("HTTP_REFERER", "/")
    return render(
        request,
        "errors/403.html",
        {
            "back_url": back_url,
        },
        status=403,
    )


# -------------------------------------------------------------
# Global 401 (API auth) handler
# -------------------------------------------------------------
def custom_401(exc, context):
    response = exception_handler(exc, context)

    if response is None or response.status_code != 401:
        return response

    request = context.get("request")

    # Detect where user is
    from_param = "api"
    if request:
        path = request.path.lower()
        if "redoc" in path:
            from_param = "redoc"
        elif "swagger" in path or "api" in path:
            from_param = "api"
        elif "dashboard" in path:
            from_param = "dashboard"

    # Detect if token existed (expired session)
    had_token = (
        bool(localStorage_get(request, "access_token"))
        or request.headers.get("Authorization", "").startswith("Bearer ")
        or request.COOKIES.get("access_token")
    )

    # Remove stale cookies
    for cookie in ("access_token", "refresh_token"):
        if request.COOKIES.get(cookie):
            response.delete_cookie(cookie)

    context = {
        "from": from_param,
        "request": request,
        "was_logged_in": had_token,
        "title": "Session Expired" if had_token else "Login Required",
        "icon": "clock" if had_token else "lock",
        "message": "Your session has expired." if had_token else "You need to log in to access this resource.",
        "subtitle": (
            "For security, sessions last 2 hours. Please log in again."
            if had_token else "Please enter your credentials."
        ),
        "button_text": "Log In Again" if had_token else "Log In",
        "modal_title": "Log In Again" if had_token else "Log In to Continue",
    }

    request = context.get("request")

    return render(
        request,
        "errors/401.html",
        {
            "title": "Session Expired",
            "icon": "clock",
            "message": "Your session has expired.",
            "subtitle": "Please log in again.",
            "button_text": "Log In Again",
            "modal_title": "Log In Again",
        },
        status=401,
    )


# -------------------------------------------------------------
# Global 404 handler
# -------------------------------------------------------------

def custom_404(request, exception=None, app_label=None, app_display_name=None):
    logger.warning(f"404 Not Found: {request.path} – User: {request.user}")

    back_url = reverse("console_dashboard")

    referer = request.META.get("HTTP_REFERER")
    if referer and request.get_host() in referer:
        back_url = referer

    if request.path.startswith("/admin/"):
        back_url = reverse("console_dashboard")

    if not back_url:
        back_url = reverse("console_dashboard")

    back_url = request.META.get("HTTP_REFERER", "/")

    return render(
        request,
        "errors/404.html",
        {
            "back_url": back_url,
            "app_display_name": app_display_name,
        },
        status=404,
    )


# -------------------------------------------------------------
# Global 500 handler
# -------------------------------------------------------------
def custom_500(request):
    return render(
        request,
        "errors/error.html",
        {
            "title": "Server Error",
            "error_image": "elements/images/error-pages/500.jpg",
            "back_url": "/",
        },
        status=500,
    )

# -------------------------------------------------------------
# Read localStorage fallback via cookies or GET
# -------------------------------------------------------------
def localStorage_get(request, key):
    return request.COOKIES.get(key) or request.GET.get(key)
