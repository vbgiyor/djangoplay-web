RUNSERVER_PLUS = {
    "DEBUGGER": True,
    "IPYTHON": False,
    "ADMIN": False,
    "THREADING": True,   # preserve threaded behaviour
}

WERKZEUG_CONSOLE_ENDPOINT = "wconsole"

# Change Werkzeug console endpoint
'''
    python manage.py runserver_plus <port> --cert-file cert.pem --key-file key.pem --werkzeug-console /wconsole
    Then Werkzeug console moves to: https://<domain>:<port>/wconsole
    WERKZEUG_CONSOLE_ENDPOINT = "wconsole"
'''

# Disable Werkzeug debugger completely

'''
    python manage.py runserver_plus <port> --cert-file cert.pem --key-file key.pem --nopin --noreload --debugger=False
'''
