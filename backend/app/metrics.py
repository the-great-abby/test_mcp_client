from prometheus_client import Counter, Gauge

rate_limit_violations = Counter(
    "rate_limit_violations_total", "Total rate limit violations", ["user_id"]
)
backoff_active = Gauge(
    "rate_limit_backoff_active", "Number of clients currently in backoff"
)
admin_actions = Counter(
    "admin_actions_total", "Total admin actions", ["action"]
) 