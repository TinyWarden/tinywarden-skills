"""Refresh APT indexes, then read a plain-upgrade summary. Never install."""
from skill_actions import ActionFailure
from .command import CommandError, encode, preflight, run, save, load, UPGRADE_PREVIEW
from .logs import log, failure
from ..skill import parse_output

PLAN = {"operation": "refresh_package_lists"}
SUMMARY_KEYS = ("upgraded", "installed", "removed", "held_back")


def _refusal(reason):
    raise ActionFailure({"key": "actions.reason." + reason, "params": {}},
                        {"outcome": "not_started"}, "none")


def prepare(request, context):
    try:
        preflight()
    except CommandError as error:
        _refusal(str(error))
    return {"plan_json": encode(PLAN), "has_changes": True, "effect": "none", "result": None}


def fetch(request, context):
    return {"downloaded": True, "plan_sha256": context.plan_sha256}


def _result(receipt):
    reason = receipt.get("reason")
    return {"effect": "changed", "reason": None if reason is None else
            {"key": "actions.reason." + reason, "params": {}},
            "local_verified": True, "process_running": False,
            "facts": {"outcome": receipt["outcome"], **receipt.get("summary", {}),
                      "refresh_exit": receipt["refresh_exit"],
                      **({"summary_exit": receipt["summary_exit"]} if "summary_exit" in receipt else {})},
            "receipt_json": encode(receipt)}


def apply(request, context):
    if request["plan"] != PLAN:
        _refusal("maintenance_receipt_invalid")
    preflight()
    context.check_start()
    receipt = {"schema_version": 1, "job_id": context.job_id,
               "content_sha256": context.binding["content_sha256"], "outcome": "running"}
    save(context, "refresh.json", receipt)
    log(context, "refresh")
    code, _ = run(context, ["/usr/bin/apt-get", "update", "--error-on=any"])
    receipt.update(refresh_exit=code, outcome="failed" if code else "refreshed")
    if code:
        receipt["reason"] = "maintenance_refresh_failed"
    # Save the known native exit before the next command or parser can fail.
    save(context, "refresh.json", receipt)
    if not code:
        log(context, "read_updates")
        try:
            code, output = run(context, UPGRADE_PREVIEW, capture=True)
            receipt["summary_exit"] = code
            parsed = parse_output({"package_mode": "upgrade"},
                {"exit_code": code, "stderr_bytes": 0, "stdout": output.decode("utf-8", errors="strict")})
            if len(output) > 1024 * 1024 or parsed.get("problem") != "none":
                raise CommandError("maintenance_reader_failed")
            receipt["summary"] = {key: parsed[key] for key in SUMMARY_KEYS}
        except Exception as error:
            failure(context, error)
            receipt.update(outcome="summary_failed", reason="maintenance_refresh_summary_failed")
        save(context, "refresh.json", receipt)
    return _result(receipt)


def verify(request, context):
    receipt = load(context, "refresh.json")
    return {"verified": receipt == request["receipt"] and receipt.get("outcome") in
            {"refreshed", "failed", "summary_failed"} and type(receipt.get("refresh_exit")) is int}


def inspect(request, context):
    log(context, "inspect")
    try:
        receipt = load(context, "refresh.json")
    except FileNotFoundError:
        context.commit({"outcome": "interrupted"})
        return
    # A running marker never proves a stopped command, even if its launcher vanished.
    outcome = receipt["outcome"]
    context.commit({"outcome": "interrupted" if outcome == "running" else outcome})
