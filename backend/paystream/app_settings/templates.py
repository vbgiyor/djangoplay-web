from .common import BASE_DIR

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'paystream' / 'templates',
            BASE_DIR / 'templates',
            BASE_DIR / 'frontend' / 'templates',
            BASE_DIR / 'invoices' / 'templates',
            BASE_DIR / 'users' / 'templates',
            BASE_DIR / 'apidocs' / 'templates',
            BASE_DIR / 'ui' / 'apps',
        ],
        # 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'utilities.context_processors.report_bug.report_bug_context',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ]
        },
    },
]
# Test settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_MIGRATIONS = True
