from contextvars import ContextVar
from types import SimpleNamespace

# Canonical request-scoped context variables
client_ip: ContextVar[str | None] = ContextVar("client_ip", default=None)
request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# ------------------------------------------------------------------
# COMPATIBILITY SHIM (TEMPORARY)
# ------------------------------------------------------------------
# This mimics the old `thread_local.client_ip` access pattern
# so legacy code keeps working without refactor today.
#
# THIS WILL BE REMOVED IN PHASE 2.
# ------------------------------------------------------------------

class _ThreadLocalCompat(SimpleNamespace):
    @property
    def client_ip(self):
        return client_ip.get()

    @client_ip.setter
    def client_ip(self, value):
        client_ip.set(value)

thread_local = _ThreadLocalCompat()
