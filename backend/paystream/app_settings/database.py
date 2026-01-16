from .common import get_decrypted_value

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_decrypted_value('DB_NAME'),
        'USER': get_decrypted_value('DB_USER'),
        'PASSWORD': get_decrypted_value('DB_PASSWORD'),
        'HOST': get_decrypted_value('DB_HOST'),
        'PORT': get_decrypted_value('DB_PORT'),
    }
}
