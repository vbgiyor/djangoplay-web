"""
Audit infrastructure app.

This package defines the audit subsystem.
Public API is intentionally NOT imported here to avoid
Django app registry initialization issues.

Consumers should import from explicit submodules, e.g.:

    from audit.services import AuditRecorder
    from audit.contracts import AuditActor, AuditTarget
"""
