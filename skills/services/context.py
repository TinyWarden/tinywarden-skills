"""Compact per-membership evidence. Reading an old sample never advances grace."""
GOOD = {"running", "reloading"}
BAD = {"stopped", "failed", "starting", "stopping", "restarting", "missing", "masked", "invalid"}


def advance(context):
    observed, settings = context["observation"], context["settings"]
    previous = context["previous_state"] or {}
    revision = context.get("evaluation_revision", "")
    epochs = context.get("resource_epochs", {}).get("services", {})
    boot = observed["boot_id"]
    usable = len(boot) == 36 and observed["uptime_ms"] <= context["captured_at"]
    same = previous.get("boot_id") == boot and previous.get("revision") == revision
    old = {r["key"]: r for r in previous.get("rows", [])} if same else {}
    readings = {r["key"]: r for r in observed["rows"]}
    captured = context["captured_at"]
    rows = []
    for key in settings["monitored_services"]:
        epoch = epochs.get(key, "")
        before = old.get(key, {})
        continuous = (before.get("epoch") == epoch and epoch != ""
                      and 0 < captured - before.get("last_at", 0) <= settings["interval_seconds"] * 3000)
        raw = readings.get(key, {}).get("raw", "unknown") if usable else "unknown"
        first = 0
        status = "unknown"
        if raw in GOOD:
            status = "healthy"
        elif raw in BAD:
            first = before.get("first_bad_at", 0) if continuous and before.get("raw") in BAD else captured
            if not first:
                first = captured
            delay = settings["alert_after_seconds"] * 1000
            startup = observed["uptime_ms"] >= settings["startup_grace_seconds"] * 1000
            if startup and (delay == 0 or continuous and first < captured and captured - first >= delay):
                status = "critical"
        rows.append({"key": key, "epoch": epoch, "last_at": captured, "first_bad_at": first,
                     "status": status, "raw": raw})
    return {"boot_id": boot, "revision": revision, "rows": rows}
