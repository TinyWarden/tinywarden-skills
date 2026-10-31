"""A cached APT preview, one approval, then ordinary apt-get upgrade."""
from skill_actions import ActionFailure
from .command import CommandError, encode, preflight, run, save, load, UPGRADE_OPTIONS, UPGRADE_PREVIEW
from .logs import log
from ..skill import parse_output, INSTALL

POLICY = "plain-upgrade-v1"
PREVIEW = UPGRADE_PREVIEW
UPGRADE = ["/usr/bin/apt-get", "--assume-yes", *UPGRADE_OPTIONS,
           "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold", "upgrade"]


def _refusal(reason, uncertain=False):
    raise ActionFailure({"key": "actions.reason." + reason, "params": {}},
                        {"outcome": "Outcome uncertain" if uncertain else "Not started"},
                        "unknown" if uncertain else "none")


def preview(output, code):
    if len(output) > 1024 * 1024:
        raise CommandError("maintenance_reader_failed")
    text = output.decode("utf-8", errors="strict")
    summary = parse_output({"package_mode": "upgrade"}, {"exit_code": code, "stderr_bytes": 0, "stdout": text})
    if summary.get("problem") != "none" or summary["installed"] or summary["removed"]:
        raise CommandError("maintenance_reader_failed")
    packages, seen = [], set()
    for line in text.splitlines():
        if not line.startswith("Inst "):
            continue
        match = INSTALL.fullmatch(line)
        if not match or not match[2] or match[1] in seen:
            raise CommandError("maintenance_reader_failed")
        name, before, after = match.groups()
        if max(len(name), len(before), len(after)) > 4096 or len(packages) >= 5000:
            raise CommandError("maintenance_reader_failed")
        seen.add(name)
        packages.append({"name": name, "installed_version": before, "candidate_version": after})
    if len(packages) != summary["upgraded"]:
        raise CommandError("maintenance_reader_failed")
    return {"operation": "upgrade_packages", "command_policy": POLICY,
            "package_count": len(packages), "kept_back_count": summary["held_back"], "packages": packages}


def prepare(request, context):
    try:
        preflight()
        log(context, "plan")
        code, output = run(context, PREVIEW, capture=True)
        plan = preview(output, code)
    except (CommandError, UnicodeError) as error:
        _refusal(str(error) if isinstance(error, CommandError) else "maintenance_reader_failed")
    changed = bool(plan["package_count"])
    result = None if changed else {"effect": "none", "reason": None, "local_verified": True,
        "process_running": False, "facts": {"outcome": "Nothing to upgrade"}, "receipt_json": None}
    return {"plan_json": encode(plan), "has_changes": changed, "effect": "none", "result": result}


def _plan(request):
    if (request["plan"].get("operation") != "upgrade_packages" or
            request["plan"].get("command_policy") != POLICY):
        _refusal("maintenance_receipt_invalid")


def fetch(request, context):
    _plan(request)
    # APT owns downloading during the approved command; no separate archive engine.
    return {"downloaded": True, "plan_sha256": context.plan_sha256}


def apply(request, context):
    _plan(request)
    preflight()
    try:
        load(context, "upgrade.json")
    except FileNotFoundError:
        pass
    else:
        _refusal("maintenance_receipt_invalid", uncertain=True)
    context.check_start()
    receipt = {"schema_version": 1, "job_id": context.job_id,
        "content_sha256": context.binding["content_sha256"], "plan_sha256": context.plan_sha256,
        "outcome": "running"}
    save(context, "upgrade.json", receipt)
    log(context, "apply")
    code, _ = run(context, UPGRADE)
    receipt.update(outcome="Upgrade completed" if code == 0 else "Failed", exit_code=code)
    save(context, "upgrade.json", receipt)
    return {"effect": "changed", "reason": None if code == 0 else
        {"key": "actions.reason.maintenance_upgrade_failed", "params": {}},
        "local_verified": True, "process_running": False,
        "facts": {"outcome": receipt["outcome"], "exit_code": code}, "receipt_json": encode(receipt)}


def verify(request, context):
    receipt = load(context, "upgrade.json")
    return {"verified": receipt == request["receipt"] and receipt.get("plan_sha256") == context.plan_sha256
            and receipt.get("outcome") in {"Upgrade completed", "Failed"} and type(receipt.get("exit_code")) is int}


def inspect(request, context):
    log(context, "inspect")
    try:
        receipt = load(context, "upgrade.json")
    except FileNotFoundError:
        context.commit({"outcome": "Outcome uncertain"})
        return
    facts = {"outcome": "Outcome uncertain" if receipt.get("outcome") == "running" else receipt["outcome"]}
    if "exit_code" in receipt:
        facts["exit_code"] = receipt["exit_code"]
    context.commit(facts)
