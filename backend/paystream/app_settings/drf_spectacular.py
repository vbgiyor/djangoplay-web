SPECTACULAR_SETTINGS = {
    "TITLE": "DjangoPlay APIs",
    "DESCRIPTION": "Unlock the power of the DjangoPlay platform with our APIs for seamless business automation. Integrate and manage users, invoices, and locations effortlessly using our comprehensive OpenAPI specification.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SERVE_PERMISSIONS": [],
    "CONTACT": {
    },
    "OAS_VERSION": "3.0.3",
    "SERVERS": [
        {"url": "https://localhost:9999", "description": "Local Development Server"},
    ],
    "SWAGGER_UI_TEMPLATE": "drf_spectacular/swagger.html",
    "SWAGGER_UI_SETTINGS": {
        "url": "/api/docs/schema/",
        "docExpansion": "none",
        "displayRequestDuration": True,
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "layout": "BaseLayout",
    },
    "REDOOC_UI_SETTINGS": {
        "hideDownloadButton": True,
        "auth": {
            "enabled": True,
            "default": "jwtAuth",
        },
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_SPLIT_RESPONSE": True,
    "PREPROCESSING_HOOKS": [
        "drf_spectacular.hooks.preprocess_exclude_path_format",
        "apidocs.hooks.exclude_docs_views",
    ],
    "POSTPROCESSING_HOOKS": [
        "apidocs.hooks.remove_none_auth",
        "apidocs.hooks.beautify_operation_ids",
    ],
    "COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Authenticate using a JWT token obtained from /api/v1/auth/token/. Tokens expire after 2 hours. Example: 'Bearer <token>'.",
            },
            # Optional: Remove BasicAuth for JWT-only
            # "BasicAuth": {
            #     "type": "http",
            #     "scheme": "basic",
            #     "description": "Authenticate using username and password (less preferred).",
            # },
        }
    },
    "SECURITY": [{"jwtAuth": []}],
#  TODO
# Hook to override schema info
# Hooks are only necessary if:
#     - You want to dynamically change schema content (e.g., inject build number from CI/CD, hide internal endpoints, rename tags programmatically).
#     - Or Spectacular ignores/mis-generates something and you want to patch it centrally.
}

# Custom preprocessing hook to clean up schema
def customize_schema(openapi_info):
    # Ensure only title and description are shown
    openapi_info["info"] = {
        "title": SPECTACULAR_SETTINGS["TITLE"],
        "description": SPECTACULAR_SETTINGS["DESCRIPTION"],
    }
    return openapi_info
