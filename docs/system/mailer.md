# Mailer

The **mailer** app is a workflow-driven email engine.

---

## Responsibilities

* Transactional email delivery
* Signup, verification, reset, and support flows
* Inline images and templating
* Unsubscribe enforcement
* Flow-level throttling

---

## Architecture

```
Service Action
   │
   ▼
Mailer Flow
   │
   ▼
Verification Guards
   │
   ▼
Template Engine
   │
   ▼
Email Adapter
   │
   ▼
SMTP / Provider
```