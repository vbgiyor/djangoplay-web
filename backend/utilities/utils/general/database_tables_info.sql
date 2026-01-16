SELECT 
    t.table_name,
    (
        SELECT COUNT(*) 
        FROM information_schema.columns c 
        WHERE c.table_name = t.table_name 
        AND c.table_schema = 'public'
    ) AS column_count,
    (
        SELECT array_agg(c.column_name) 
        FROM information_schema.columns c 
        WHERE c.table_name = t.table_name 
        AND c.table_schema = 'public'
    ) AS column_names,
    (
        SELECT COUNT(*) 
        FROM quote_ident(t.table_name)
    ) AS record_count
FROM information_schema.tables t
WHERE t.table_schema = 'public'
AND t.table_name IN (
    'address', 'billing_schedule', 'contact', 'entity', 'fincore_entity_mapping',
    'gst_configuration', 'industries_industry', 'invoice', 'line_item',
    'locations_customcity', 'locations_customcountry', 'locations_customcountry_global_regions',
    'locations_customregion', 'locations_customsubregion', 'locations_globalregion',
    'locations_location', 'locations_timezone', 'payment', 'payment_method',
    'status', 'tax_profile', 'users_address', 'users_user'
)
ORDER BY t.table_name;