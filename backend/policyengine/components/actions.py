ACTION_PERMISSIONS = {
    'create': {'DJGO', 'CEO', 'CFO'},
    'update': {'DJGO', 'CEO', 'CFO'},
    'partial_update': {'DJGO', 'CEO', 'CFO'},
    'destroy': {'DJGO', 'CEO', 'CFO'},
    'soft_delete': {'DJGO', 'CEO', 'CFO'},
    'list': {'DJGO', 'CEO', 'CFO'}
}

MODEL_ROLE_PERMISSIONS = {
    # ---------------- USERS ----------------
    "employee": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["ADMIN", "HR"],
        "update": ["ADMIN", "HR"],
        "destroy": ["ADMIN"],
    },
    "member": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "supportticket": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
        "create": ["EMPLOYEE"],
        "update": ["EMPLOYEE"],
        "destroy": ["ADMIN"],
    },
    "leavetype": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "leaveapplication": {
        "list": ["ADMIN", "HR", "EMPLOYEE"],
        "retrieve": ["ADMIN", "HR", "EMPLOYEE"],
        "create": ["EMPLOYEE"],
        "update": ["EMPLOYEE"],
        "destroy": ["EMPLOYEE"],
    },
    "leavebalance": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["HR"],
        "update": ["HR"],
        "destroy": ["HR"],
    },
    "useractivitylog": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
    },
    "signuprequest": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": [],
        "update": [],
        "destroy": ["ADMIN"],
    },
    "passwordresetrequest": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": [],
        "update": [],
        "destroy": [],
    },
    "department": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "team": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "role": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },

    # ---------------- LOCATIONS ----------------
    "customregion": {
        "list": ["DJGO", "CEO", "SSO"],
        "retrieve": ["DJGO", "CEO", "SSO"],
        "create": ["DJGO", "CEO", "SSO"],
        "update": ["DJGO", "CEO", "SSO"],
        "destroy": ["DJGO", "CEO", "SSO"],
    },
    "customsubregion": {
        "list": ["ADMIN", "HR"],
        "retrieve": ["ADMIN", "HR"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "customcountry": {
        "list": ["DJGO", "CEO", "SSO"],
        "retrieve": ["DJGO", "CEO", "SSO"],
        "view_detailed_country": ["DJGO", "CEO"], # Only Django Superuser and CEO can view
        "view_detailed_globalregion": ["DJGO", "CEO"],
    },
    "customcity": {
        "list": ["ADMIN", "HR", "EMPLOYEE"],
        "retrieve": ["ADMIN", "HR", "EMPLOYEE"],
    },
    "globalregion": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
    },
    "location": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
    },
    "timezone": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
    },

    # ---------------- FINANCE ----------------
    "payment": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["CFO"],
        "update": ["CFO"],
        "destroy": ["ADMIN"],
    },
    "invoice": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["CFO"],
        "update": ["CFO"],
        "destroy": ["ADMIN"],
    },
    "line_item": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
    },
    "billing_schedule": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["CFO"],
        "update": ["CFO"],
        "destroy": ["CFO"],
    },
    "gst_configuration": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "payment_method": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },

    # ---------------- ENTITY ----------------
    "entity": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },
    "entity_mapping": {
        "list": ["ADMIN"],
        "retrieve": ["ADMIN"],
        "create": ["ADMIN"],
        "update": ["ADMIN"],
        "destroy": ["ADMIN"],
    },

    # ---------------- CONTACT ----------------
    "contact": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
        "create": ["EMPLOYEE"],
        "update": ["EMPLOYEE"],
        "destroy": ["ADMIN"],
    },
    "address": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
        "create": ["EMPLOYEE"],
        "update": ["EMPLOYEE"],
        "destroy": ["ADMIN"],
    },

    # ---------------- MISC ----------------
    "industry": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
    },
    "status": {
        "list": ["ADMIN", "EMPLOYEE"],
        "retrieve": ["ADMIN", "EMPLOYEE"],
    },
    "tax_profile": {
        "list": ["ADMIN", "CFO"],
        "retrieve": ["ADMIN", "CFO"],
        "create": ["CFO"],
        "update": ["CFO"],
        "destroy": ["CFO"],
    },

    # Example of denying everything
    "emailconfirmation": {
        "list": [],
        "retrieve": [],
        "create": [],
        "update": [],
        "destroy": [],
    },
}

