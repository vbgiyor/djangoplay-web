# 📘 **DjangoPlay Email Unsubscribe & System Email Architecture**

### **Full Technical Design & Documentation**

**Version:** 1.0
**Date:** 01-Dec-2025
**Author:** AI Assistant / Shekhar
**Modules:** `CustomAccountAdapter.send_mail`, `PasswordResetService`, `SupportService`, `BugService`, `UnsubscribeView`

---

## 🧩 1. **Background & Original Issues**

The email system needed restructuring due to the following challenges:

| Problem                                                                                         | Description                                     |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Global unsubscribe prevented essential flows like Password Reset                                | User cannot restore access after unsubscribing  |
| Marketing preferences (`preferences` dict) were misunderstood                                   | Boolean False was interpreted incorrectly       |
| Support and bug-report confirmation emails were still delivered to unsubscribed users           | Violated expected unsubscribe behavior          |
| Incorrect UI messages (e.g., "Email is not verified" when clicking same unsubscribe link twice) | Poor UX leading to confusion                    |
| Duplicate signup email validation bug                                                           | Caused incorrect verification message           |
| Messaging and UI redirects inconsistent across flows                                            | Reset password returned generic invalid message |

---

## 🎯 2. **Goal**

Design a clean email framework that:

* Respects both category-based and global unsubscribe rules
* Allows essential system communication
* Avoids accidental lockout
* Provides clear UX
* Enables future expansion without modifying core logic

---

## 🏗 3. **Architectural Approach**

### **The new system categorizes emails into three types**

| Type                      | Examples                              | Unsubscribe Rule                         |
| ------------------------- | ------------------------------------- | ---------------------------------------- |
| **Marketing**             | newsletters, offers, product updates  | Only category-specific preferences block |
| **Normal Product Emails** | onboarding updates, invoice reminders | Block if globally unsubscribed           |
| **System emails**         | Support, Bug to support               | Always allowed                           |
| **Semi-system**           | Password reset, verification/signup   | Block if globally unsubscribed           |

---

## 📍 4. **Central Configurations Introduced**

`utilities/constants/unsubscribe.py`

```python
CATEGORY_BY_PREFIX = {
    "newsletter_weekly": "newsletters",
    "special_offer": "offers",
    "product_update": "updates",
}

SYSTEM_EMAIL_PREFIXES = {
    "request_to_support",   # support mailbox always allowed
}
```

---

## 🧠 5. **Email Delivery Decision Flow**

### 🪢 **Unified Flowchart**

```
START
  |
  |-- Extract current_prefix
  |
  |-- Resolve user from:
  |      context.user / member.employee / ticket.email / param email
  |
  |-- Is prefix in SYSTEM_EMAIL_PREFIXES? ---------- YES ------> Allow Send
  |                                                        |
  NO                                                       v
  |                                                Build and send email
  |
  |-- Is user.is_unsubscribed == True?
  |                | YES
  |                v
  |         Block (stop sending)
  |         Show UI message if web request
  |
  NO
  |
  |-- Is prefix a marketing email?
  |             |
  |             |-- category pref exists? AND pref is False?
  |                               | YES -> Block send
  |
  |-- Special handling: password reset prefix?
  |             |
  |             |-- call send_password_reset_mail()
  |
  |-- Proceed to template rendering
  |
END (send email or suppressed)
```

---

## ⚙ 6. **Final Behavioral State Machine**

```
                                   +-------------------------+
                                   |  USER unsubscribed?     |
                                   +-------------------------+
                                              |
                              +---------------+---------------+
                              |                               |
                            YES                              NO
                              |                               |
       +--------------------------------+           +-----------------------+
       |  Is SYSTEM prefix?            |           |  Normal Email Process |
       +--------------------------------+           +-----------------------+
       |                                |
   +---+---+                        +----+---------+
   | ALLOW |                        | BLOCK EMAIL  |
   +-------+                        +--------------+
```

---

## 🛠 7. **Key Code Changes**

### **Modified**

| File                             | Change                                            |
| -------------------------------- | ------------------------------------------------- |
| `CustomAccountAdapter.send_mail` | Added structured unsubscribe decision flow        |
| `PasswordResetService`           | returns `RESET_STATUS_UNSUBSCRIBED`               |
| `CustomPasswordResetView`        | Shows correct UX for unsubscribed                 |
| `UnsubscribeView`                | Improved second-click handling message            |
| `BugService` & `SupportService`  | Blocks confirmation-to-user email if unsubscribed |
| `CustomSignupView`               | Fixed `email__iexact='email'` bug                 |

---

## 📦 8. **Behavior Verification Scenarios**

| Scenario                                    | Result                                        |
| ------------------------------------------- | --------------------------------------------- |
| User unsubscribes from all email categories | Receives no marketing or system confirmations |
| User clicks reset password                  | Blocked with correct message                  |
| User submits bug report                     | Support gets email; user does not             |
| User submits support ticket                 | Support gets email; user does not             |
| User clicks unsubscribe link twice          | Friendly message shown                        |
| User attempts duplicate signup              | Correct verified email message                |
| User throttled for support/bug              | Consistent UI + Celery flow                   |

---

## 🪄 9. **Design Advantages**

| Benefit                                     | Explanation                    |
| ------------------------------------------- | ------------------------------ |
| Centralized unsubscribe logic               | Single source of truth         |
| No editing adapter for future system emails | Add prefix to dict             |
| No hidden behavior                          | Fully deterministic            |
| Aligned with enterprise email compliance    | (GDPR, CAN-SPAM good practice) |
| Developer friendly                          | Docs & clear flow              |

---

## 🚀 10. Future Enhancements (optional next steps)

* Resubscribe UI
* Manage preferences page with toggles
* Audit logging for unsubscribe activity
* Admin trigger for forced essential emails

---

# 🎉 Conclusion

This redesign transformed a fragmented and inconsistent unsubscribe feature into a **clean, scalable, secure, workflow-oriented architecture** that is easy to understand and extend.

The system is now production-grade and handles:

* UX correctness
* Business logic separation
* Developer clarity
* Email compliance standards

---
