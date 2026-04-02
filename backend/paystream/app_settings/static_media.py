from .common import BASE_DIR

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'paystream' / 'static' / 'design' / 'css' / 'banners',
    BASE_DIR / 'paystream' / 'static' / 'design' / 'css' / 'app',
    BASE_DIR / 'paystream' / 'static' / 'design' / 'css' / 'themes',
    BASE_DIR / 'paystream' / 'static' / 'design' / 'js',
    BASE_DIR / 'paystream' / 'static' / 'design' / 'css' / 'emails',
    BASE_DIR / 'paystream' / 'static' / 'fonts',
    BASE_DIR / 'paystream' / 'static' / 'elements',
    BASE_DIR / 'paystream' / 'static' / 'sounds',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = False
COMPRESS_OFFLINE_MANIFEST = 'manifest.json'
COMPRESS_ROOT = STATIC_ROOT
