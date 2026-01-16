import logging
import socket
import threading

logger = logging.getLogger(__name__)

# Thread-local storage to avoid circular imports
thread_local = threading.local()

def get_machine_ip():
    """
    Get the IP address of the local machine for migration data seeding.
    Not intended for production use. Returns None if IP cannot be determined.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google's DNS
        client_ip = s.getsockname()[0]
        s.close()
        return client_ip
    except Exception:
        return None

def get_current_client_ip(default='N/A'):
    """
    Retrieve the client IP from thread-local storage set by ClientIPMiddleware.
    Returns the default value ('N/A') if no IP is available.
    """
    client_ip = getattr(thread_local, 'client_ip', None)
    return client_ip if client_ip is not None else default
