"""
Email unsubscribe policy configuration.

=====================================================
| Email type              | Controlled by                | When is_unsubscribed=True |
| ----------------------- | ---------------------------- | --------------------------|
| Marketing               | preferences dict             | Block per-category         |
| Normal product emails   | global unsubscribe           | Block                      |
| Password reset          | global unsubscribe           | Block                      |
| Verification / Signup   | global unsubscribe           | Block                      |
| Support Ticket Emails   | SYSTEM_EMAIL_PREFIXES        | Always allowed             |
| Future new system email | add suffix in set below      | Done                       |
=====================================================

CATEGORY_BY_PREFIX maps marketing emails to preference keys.
SYSTEM_EMAIL_PREFIXES lists transactional emails that must always be sent
(even when the user is globally unsubscribed), e.g., support or critical system notices.

To add a new system-type email: include its template suffix in SYSTEM_EMAIL_PREFIXES.
To add a new marketing category: extend CATEGORY_BY_PREFIX.
"""

# Marketing / promotional category mapping
CATEGORY_BY_PREFIX = {
    "newsletter_weekly": "newsletters",
    "special_offer": "offers",
    "product_update": "updates",
}

# Support & ticket emails ALWAYS allowed even when is_unsubscribed=True
SYSTEM_EMAIL_PREFIXES = {
    "request_to_support",        # to support team for requesting re-subscribe
}
