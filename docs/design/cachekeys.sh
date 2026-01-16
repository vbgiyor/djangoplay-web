|Entity Type        |Cache Key (Individual)|Cache Key (Pagination)           |Services|tasks.py|refresh_redis_cache.py|Compression in Services|Compression in tasks.py        |Consistent?|
|-------------------|----------------------|---------------------------------|--------|--------|----------------------|-----------------------|-------------------------------|-----------|
|Country            |countries             |countries_page_<page_num>        |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Region             |regions               |regions_page_<page_num>          |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Subregion          |subregions            |subregions_page_<page_num>       |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|City               |cities                |cities_page_<page_num>           |Yes     |Yes     |Yes                   |Yes                    |Yes                            |Yes        |
|Location           |locations             |locations_page_<page_num>        |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Industry           |industries            |industries_page_<page_num>       |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Entity             |entities              |entities_page_<page_num>         |Yes     |Yes     |Yes                   |Yes                    |Yes                            |Yes        |
|Address            |addresses             |addresses_page_<page_num>        |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Contact            |contacts              |contacts_page_<page_num>         |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Tax Profile        |tax_profiles          |tax_profiles_page_<page_num>     |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Entity Mapping     |entity_mappings       |entity_mappings_page_<page_num>  |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Invoice            |invoices              |invoices_page_<page_num>         |Yes     |Yes     |Yes                   |Yes                    |Yes                            |Yes        |
|Line Item          |line_items            |line_items_page_<page_num>       |Yes     |Yes     |Yes                   |Yes                    |Yes                            |Yes        |
|Payment Method     |payment_methods       |payment_methods_page_<page_num>  |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|GST Configuration  |gst_configs           |gst_configs_page_<page_num>      |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Billing Schedule   |billing_schedules     |billing_schedules_page_<page_num>|Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Payment            |payments              |payments_page_<page_num>         |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Status             |statuses              |statuses_page_<page_num>         |Yes     |Yes     |Yes                   |No                     |No                             |Yes        |
|Invoice Search List|invoices_search_list  |N/A                              |Yes     |No      |Yes                   |Yes                    |Yes (in refresh_redis_cache.py)|Yes        |
|Last Cache Run     |last_cache_run        |N/A                              |No      |No      |Yes                   |N/A                    |N/A                            |N/A        |
