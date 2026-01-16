import logging
import re


class SanitizeQueryParamsFilter(logging.Filter):

    """
    A logging filter that redacts sensitive fields (e.g., password, token)
    in query parameters before they are logged.
    """

    def filter(self, record):
        """
        Redacts 'password' and 'token' from query parameters in logs.
        """
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = re.sub(r'(\bpassword\b|\btoken\b)=[^&]+', r'\1=REDACTED', record.msg)
        return True

def add_sanitization_filter_to_logger(logger=None):
    """
    Add the SanitizeQueryParamsFilter to the provided logger instance.
    If no logger is provided, it adds to the default logger.
    """
    if logger is None:
        logger = logging.getLogger()

    logger.addFilter(SanitizeQueryParamsFilter())
