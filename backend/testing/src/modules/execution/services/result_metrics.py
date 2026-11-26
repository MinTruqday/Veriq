from datetime import datetime, timezone


def result_timestamp(result):
    for field in ("completed_at", "executed_at", "updated_at", "created_at"):
        value = result.get(field)
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if value:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def pass_rate_metrics(passed, failed):
    denominator = passed + failed
    return {
        "pass_rate": round(100 * passed / denominator, 2) if denominator else None,
        "pass_rate_denominator": denominator,
    }
