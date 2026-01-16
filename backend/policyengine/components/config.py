# Maps model names to feature flag keys per action

FEATURE_FLAG_PERMISSIONS = {
    'customregion': {
        'create': 'region_create_feature',
        'update': 'region_update_feature',
        'destroy': 'region_delete_feature',
    },
    'country': {
        'create': 'country_create_feature',
    },
    # Add more as needed
}
