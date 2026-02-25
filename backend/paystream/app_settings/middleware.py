from django.conf import settings

MIDDLEWARE = [
    # --- Request context (must be FIRST) ---
    "core.middleware.request_id.RequestIDMiddleware",
    "core.middleware.client_ip.ClientIPMiddleware",
    "audit.middleware.api_audit.APIAuditMiddleware",

    # --- django-hosts subdomain config ---
    "django_hosts.middleware.HostsRequestMiddleware",

    # --- Security & HTTP ---
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    # --- Auth & user context ---
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",

    # --- UI & clickjacking ---
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # --- History / auditing ---
    "simple_history.middleware.HistoryRequestMiddleware",

    # --- Template Error Guard ---
    "core.middleware.template_syntax.TemplateSyntaxErrorLoggingMiddleware",

    # --- API request persistence (near the end) ---
    "core.middleware.api_request_logging.APIRequestLoggingMiddleware",

    # --- django-hosts subdomain config ---
    "django_hosts.middleware.HostsResponseMiddleware",
]

if settings.DEBUG:
    MIDDLEWARE += [
        "core.middleware.url_resolution_debug.URLResolutionLoggingMiddleware",
    ]
