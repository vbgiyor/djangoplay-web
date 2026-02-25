from django_hosts import host, patterns

host_patterns = patterns(
    "",
    host(r"issues", "paystream.integrations.issuetracker.ui.urls", name="issues"),
    host(r"", "paystream.urls", name="default"),
)
