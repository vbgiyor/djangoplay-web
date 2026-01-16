"""
Bootstrap secrets decryption for Django & Celery.
Ensures that encrypted .env values are decrypted BEFORE Django loads settings.
"""

from paystream.app_settings.common import load_all_decrypted_values


def bootstrap_secrets():
    """
    Ensures secrets are decrypted and placed into os.environ
    PRIOR to Django configuration loading.
    """
    try:
        load_all_decrypted_values()
    except Exception as e:
        raise RuntimeError(f"Failed to bootstrap secrets: {e}")
