"""Translate the two read-only broker operations; selection never follows discovery."""
import json
def reason(key, **params):
    return {"key": key, "params": params}


def eligible(item):
    if not item["available"]:
        return False
    p = item["properties"]
    return (not p["Id"].endswith("@.service") and p["Type"] not in {"", "oneshot"}
            and p["RemainAfterExit"] == "no"
            and not any(n.endswith((".socket", ".timer", ".path")) for n in p["TriggeredBy"].split()))


def state(item):
    if not item["available"]:
        return "review" if item["reason"] == "template" else "unknown"
    p = item["properties"]
    if p["Id"] != item["requested"]:
        return "review"
    load = p["LoadState"]
    if load == "not-found":
        return "missing"
    if load == "masked":
        return "masked"
    if load in {"error", "bad-setting"}:
        return "invalid"
    if load != "loaded" or not eligible(item):
        return "review"
    active, sub = p["ActiveState"], p["SubState"]
    if active == "active" and sub == "running":
        return "running"
    if active == "reloading" and sub in {"reload", "reload-signal", "reload-notify", "running"}:
        return "reloading"
    if sub == "auto-restart":
        return "restarting"
    return {"inactive": "stopped", "failed": "failed", "activating": "starting",
            "deactivating": "stopping"}.get(active, "unknown")


def observe(settings, host):
    # Selected reads happen first and do not depend on discovery truncation.
    reading = host.request("systemd.services.read", {"units": settings["monitored_services"]})
    inventory = host.request("systemd.services.list", {})
    rows = []
    by_name = {r["requested"]: r for r in reading["items"]}
    for key in settings["monitored_services"]:
        item = by_name.get(key, {"requested": key, "available": False, "reason": "unreadable", "properties": {}})
        p = item["properties"]
        rows.append({"key": key, "raw": state(item), "result": p.get("Result", "")[:64],
                     "exit_status": p.get("ExecMainStatus", "")[:32]})
    items, size, complete, limit = [], 2, inventory["complete"], inventory["reason"] == "limit"
    for item in inventory["items"]:
        p = item["properties"]
        key = p.get("Id", item["requested"])
        selectable = eligible(item)
        # Broker descriptions are UTF-8 bounded. Mark truncation in the UI.
        description = p.get("Description", "")
        if len(description.encode()) >= 253:
            description = description.encode()[:250].decode(errors="ignore") + "…"
        candidate = {"key": key, "label": key, "description": description,
                      "selectable": selectable,
                      "selection_reason": None if selectable else reason("ineligible" if item["available"] or item["reason"] == "template" else "not_readable"),
                      "state": reason("raw_" + state(item))}
        encoded = len(json.dumps(candidate, ensure_ascii=True, separators=(",", ":")).encode()) + 1
        if size + encoded > 258048:
            complete, limit = False, True
            break
        items.append(candidate)
        size += encoded
    problem = None if complete else reason("inventory_limit" if limit else "inventory_unavailable")
    return {"observation": {"boot_id": reading["boot_id"], "uptime_ms": reading["uptime_ms"], "rows": rows},
            "resources": [{"collection": "services", "complete": complete, "reason": problem, "items": items}]}
