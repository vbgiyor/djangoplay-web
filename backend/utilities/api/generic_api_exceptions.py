# Generic fallback error for API Exceptions

class GenericAPIError(Exception):

    """Generic fallback exception used by Base API Views when app-level exception is not provided."""

    def __init__(self, message, code="error", details=None):
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self):
        return {
            "error": {
                "message": self.message,
                "code": self.code,
                "details": self.details,
            }
        }
