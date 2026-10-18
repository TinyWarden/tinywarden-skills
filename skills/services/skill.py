"""One Services skill; no service management actions or automatic enrollment."""
from collector import observe, reason
from context import advance


def validate_settings(settings):
    return []


def collect(settings, host):
    return observe(settings, host)


def reduce(context):
    return advance(context)


def evaluate(context):
    subjects = []
    counts = {"healthy": 0, "critical": 0, "unknown": 0}
    for row in context["state"]["rows"]:
        status, raw, key = row["status"], row["raw"], row["key"]
        code = "healthy_reason" if status == "healthy" else "critical_reason" if status == "critical" else "pending_reason" if row["first_bad_at"] else "unknown_reason"
        params = {"service": key} if code == "unknown_reason" else {"service": key, "state": raw}
        facts = [{"key": "raw_state", "label_key": "raw_label", "kind": "text", "value": raw},
                 {"key": "observed_at", "label_key": "observed_label", "kind": "time", "value": context["captured_at"]}]
        if row["first_bad_at"]:
            facts.append({"key": "first_bad_at", "label_key": "first_bad_label", "kind": "time", "value": row["first_bad_at"]})
        subjects.append({"collection": "services", "key": key, "status": status, "reason": reason(code, **params), "facts": facts})
        counts[status] += 1
    return [{"from": context["now"], "subjects": subjects,
             "facts": [{"key": key + "_count", "label_key": key + "_count", "kind": "number", "value": value} for key, value in counts.items()]}]
