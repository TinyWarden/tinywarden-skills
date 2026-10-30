"""Conservative upgrades owned by Updates, using public approval/state/recovery APIs."""
import json
import os
import re
import stat
import uuid

from skill_actions import ActionFailure
from .apt_policy import (MaintenanceError, apt, canonical, digest, configure, audit,
                         package_lock, file_digest, apt_pkg)
from .apt_archives import protected_mirror_cache
from .apt_plan import resolve, selections
from .apt_boot import installed_metadata
from .apt_capacity import capacity
from .apt_refresh import strict_refresh
from . import apt_transaction
from .logs import log, failure, output


def _facts(outcome, kept=0, native=None):
    native = native or {}
    label = {"packages_applied": "Packages upgraded", "no_changes": "Nothing to upgrade",
             "failed": "Failed", "interrupted": "Outcome uncertain",
             "not_started": "Not started"}[outcome]
    return {"outcome": label, "kept_back_count": kept,
            "reboot_required": native.get("reboot_required"),
            "configuration_review": native.get("configuration_review"),
            "services_restart_required": native.get("services_restart_required")}


def _failure(error, facts, effect="none", receipt=None):
    reason = str(error) if isinstance(error, MaintenanceError) else "maintenance_adapter_failed"
    raise ActionFailure({"key": "actions.reason." + reason, "params": {}}, facts,
                        effect, None if receipt is None else canonical(receipt).decode())


def _preflight():
    if os.geteuid() != 0:
        raise MaintenanceError("maintenance_root_required")
    configure(upgrade=True)


def _save(context, outcome, facts, native=None):
    value = {"schema_version": 1, "job_id": context.job_id,
             "content_sha256": context.binding["content_sha256"],
             "plan_sha256": context.plan_sha256, "outcome": outcome,
             "facts": facts, "proof": native}
    name = "receipt-" + uuid.uuid4().hex + ".tmp"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=context.state_fd)
    try:
        data = canonical(value)
        while data:
            data = data[os.write(fd, data):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(name, "upgrade.json", src_dir_fd=context.state_fd, dst_dir_fd=context.state_fd)
    os.fsync(context.state_fd)
    return value


def _load(context):
    fd = os.open("upgrade.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                 dir_fd=context.state_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 16384):
            raise MaintenanceError("maintenance_receipt_invalid")
        value = json.loads(os.read(fd, 16385))
    finally:
        os.close(fd)
    if (not isinstance(value, dict) or set(value) != {"schema_version", "job_id",
            "content_sha256", "plan_sha256", "outcome", "facts", "proof"} or
            type(value["schema_version"]) is not int or value["schema_version"] != 1 or
            value["job_id"] != context.job_id or
            value["content_sha256"] != context.binding["content_sha256"] or
            (not isinstance(value["plan_sha256"], str) or
             not re.fullmatch("[0-9a-f]{64}", value["plan_sha256"]) or
             context.plan_sha256 is not None and value["plan_sha256"] != context.plan_sha256) or
            value["outcome"] not in {"running", "packages_applied", "failed"}):
        raise MaintenanceError("maintenance_receipt_invalid")
    return value


def _verify_proof(proof):
    if (not isinstance(proof, dict) or set(proof) != {"state_sha256", "selection_sha256"} or
            any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v) for v in proof.values())):
        raise MaintenanceError("maintenance_receipt_invalid")
    audit()
    cache = apt.Cache(progress=apt.progress.base.OpProgress())
    if (cache.broken_count or selections(cache) != proof["selection_sha256"] or
            file_digest(apt_pkg.config.find_file("Dir::State::status")) != proof["state_sha256"]):
        raise MaintenanceError("maintenance_verification_failed")


def prepare(request, context):
    refreshed = False
    def before_refresh():
        nonlocal refreshed
        refreshed = True
    try:
        log(context, "policy")
        _preflight()
        log(context, "refresh")
        strict_refresh(before_refresh, context)
        log(context, "package_state")
        audit()
        with package_lock(), protected_mirror_cache():
            log(context, "plan")
            cache, plan = resolve()
            log(context, "capacity")
            capacity(plan, installed=installed_metadata(cache))
        changed = bool(plan["packages"])
        no_changes = None if changed else {"effect": "changed", "reason": None,
            "local_verified": True, "process_running": False,
            "facts": _facts("no_changes", len(plan["kept_back"])), "receipt_json": None}
        return {"plan_json": canonical(plan).decode(), "has_changes": changed,
                "effect": "changed", "result": no_changes}
    except Exception as error:
        failure(context, error)
        _failure(error, _facts("not_started"), "unknown" if refreshed else "none")


def fetch(request, context):
    try:
        _preflight()
        log(context, "download")
        apt_transaction.fetch(digest(request["plan"]))
    except Exception as error:
        failure(context, error)
        _failure(error, _facts("not_started", request["plan"]["kept_back_count"]))
    return {"downloaded": True, "plan_sha256": context.plan_sha256}


def apply(request, context):
    started = False
    kept = request["plan"]["kept_back_count"]
    def before_start():
        nonlocal started
        _save(context, "running", _facts("interrupted", kept))
        context.check_start()
        started = True
    try:
        _preflight()
        log(context, "apply")
        output(context, "python-apt: install_archives\n")
        native = apt_transaction.apply(digest(request["plan"]), before_start)
        output(context, "python-apt: installation and verification completed\n")
        facts = _facts(native["outcome"], kept, native)
        proof = {key: native[key] for key in ("state_sha256", "selection_sha256")}
        receipt = _save(context, "packages_applied", facts, proof)
    except Exception as error:
        failure(context, error)
        facts = _facts("failed" if started else "not_started", kept)
        receipt = _save(context, "failed", facts) if started else None
        _failure(error, facts, "unknown" if started else "none", receipt)
    return {"effect": "changed", "reason": None, "local_verified": True,
            "process_running": False, "facts": facts, "receipt_json": canonical(receipt).decode()}


def verify(request, context):
    try:
        log(context, "verify_upgrade")
        _preflight()
        with package_lock():
            value = _load(context)
            if value != request["receipt"] or value["outcome"] != "packages_applied":
                raise MaintenanceError("maintenance_receipt_invalid")
            _verify_proof(value["proof"])
    except Exception as error:
        failure(context, error)
        _failure(error, _facts("interrupted"), "unknown")
    return {"verified": True}


def inspect(request, context):
    try:
        log(context, "inspect")
        _preflight()
        with package_lock():
            audit()
            try:
                value = _load(context)
            except FileNotFoundError:
                context.commit(_facts("not_started"))
                return
            if value["outcome"] == "packages_applied":
                _verify_proof(value["proof"])
            # An interrupted native operation is never repeated or inferred successful.
            context.commit(value["facts"])
    except Exception as error:
        failure(context, error)
        _failure(error, _facts("interrupted"), "unknown")
