"""Refresh package lists through the public action SDK; never install packages."""
import json
import os
import stat
import uuid

from skill_actions import ActionFailure
from .apt_policy import MaintenanceError, configure, package_lock
from .apt_refresh import strict_refresh


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _receipt(context, outcome):
    return {"schema_version": 1, "job_id": context.job_id,
            "content_sha256": context.binding["content_sha256"], "outcome": outcome}


def _save(context, receipt):
    name = "receipt-" + uuid.uuid4().hex + ".tmp"
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=context.state_fd)
    try:
        data = _encode(receipt).encode()
        while data:
            data = data[os.write(fd, data):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(name, "refresh.json", src_dir_fd=context.state_fd,
               dst_dir_fd=context.state_fd)
    os.fsync(context.state_fd)


def _load(context):
    fd = os.open("refresh.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                 dir_fd=context.state_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or
                info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 4096):
            raise MaintenanceError("maintenance_receipt_invalid")
        receipt = json.loads(os.read(fd, 4097))
        if (not isinstance(receipt, dict) or
                set(receipt) != {"schema_version", "job_id", "content_sha256", "outcome"} or
                receipt["schema_version"] != 1 or receipt["job_id"] != context.job_id or
                receipt["content_sha256"] != context.binding["content_sha256"] or
                receipt["outcome"] not in {"running", "refreshed", "failed"}):
            raise MaintenanceError("maintenance_receipt_invalid")
        return receipt
    finally:
        os.close(fd)


def _failure(reason, context, outcome="not_started", effect="none", receipt=None):
    raise ActionFailure({"key": "actions.reason." + reason, "params": {}},
                        {"outcome": outcome}, effect,
                        None if receipt is None else _encode(receipt))


def _preflight(context):
    try:
        if os.geteuid() != 0:
            raise MaintenanceError("maintenance_root_required")
        configure(upgrade=False)
    except MaintenanceError as error:
        _failure(str(error), context)


def prepare(request, context):
    _preflight(context)
    return {"plan_json": _encode({"operation": "refresh_package_lists"}),
            "has_changes": True, "effect": "none", "result": None}


def fetch(request, context):
    _preflight(context)
    return {"downloaded": True, "plan_sha256": context.plan_sha256}


def apply(request, context):
    _preflight(context)
    if request["plan"] != {"operation": "refresh_package_lists"}:
        _failure("maintenance_receipt_invalid", context)
    started = False

    def before_start():
        nonlocal started
        context.check_start()
        _save(context, _receipt(context, "running"))
        started = True

    try:
        strict_refresh(before_start)
        receipt = _receipt(context, "refreshed")
        _save(context, receipt)
    except Exception as error:
        outcome, effect = ("failed", "unknown") if started else ("not_started", "none")
        receipt = _receipt(context, "failed") if started else None
        if receipt is not None:
            _save(context, receipt)
        reason = str(error) if isinstance(error, MaintenanceError) else "maintenance_adapter_failed"
        _failure(reason, context, outcome, effect, receipt)
    return {"effect": "changed", "reason": None, "local_verified": True,
            "process_running": False, "facts": {"outcome": "refreshed"},
            "receipt_json": _encode(receipt)}


def verify(request, context):
    _preflight(context)
    try:
        with package_lock():
            receipt = _load(context)
            if receipt != request["receipt"] or receipt["outcome"] != "refreshed":
                raise MaintenanceError("maintenance_receipt_invalid")
    except (MaintenanceError, OSError, ValueError):
        _failure("maintenance_receipt_invalid", context, "interrupted", "unknown")
    return {"verified": True}


def inspect(request, context):
    _preflight(context)
    try:
        with package_lock():
            try:
                outcome = _load(context)["outcome"]
            except FileNotFoundError:
                outcome = "not_started"
            if outcome == "running":
                outcome = "interrupted"
            context.commit({"outcome": outcome})
    except MaintenanceError as error:
        _failure(str(error), context, "interrupted", "unknown")
