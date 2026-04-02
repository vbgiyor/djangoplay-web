from django_hosts import host, patterns

host_patterns = patterns(
    "",
    host(r"issues", "paystream.urlconf.subdomains.issues", name="issues"),
    host(r"docs", "paystream.urlconf.subdomains.docs", name="docs"),
    host(r"", "paystream.urlconf.default", name="default"),
)
