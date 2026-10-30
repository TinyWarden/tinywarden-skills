"""Refresh package lists through the public action SDK; never install packages."""
import json
import os
import stat
import selectors
import subprocess
import uuid

from skill_actions import ActionFailure
from .apt_policy import MaintenanceError, configure, package_lock, readonly_budget
from .apt_refresh import strict_refresh
from ..skill import parse_output
from .logs import log, command as log_command, exit_code, tee, failure


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _receipt(context, outcome, summary=None):
    return {"schema_version": 1, "job_id": context.job_id,
            "content_sha256": context.binding["content_sha256"], "outcome": outcome, "summary": summary}


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
                set(receipt) != {"schema_version", "job_id", "content_sha256", "outcome", "summary"} or
                receipt["schema_version"] != 1 or receipt["job_id"] != context.job_id or
                receipt["content_sha256"] != context.binding["content_sha256"] or
                receipt["outcome"] not in {"running", "refreshed", "failed"} or
                not valid_summary(receipt["summary"], receipt["outcome"])):
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
    log(context, "policy")
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
        log(context, "refresh")
        strict_refresh(before_start, context)
        log(context, "read_updates")
        summary = available_updates(request["settings"], context)
        receipt = _receipt(context, "refreshed", summary)
        _save(context, receipt)
    except Exception as error:
        failure(context, error)
        outcome, effect = ("failed", "unknown") if started else ("not_started", "none")
        receipt = _receipt(context, "failed") if started else None
        if receipt is not None:
            _save(context, receipt)
        reason = str(error) if isinstance(error, MaintenanceError) else "maintenance_adapter_failed"
        _failure(reason, context, outcome, effect, receipt)
    return {"effect": "changed", "reason": None, "local_verified": True,
            "process_running": False, "facts": {"outcome": "refreshed", **summary},
            "receipt_json": _encode(receipt)}


def verify(request, context):
    log(context, "verify_refresh")
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
    log(context, "inspect")
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


SUMMARY_KEYS = ("upgraded", "installed", "removed", "held_back")


def valid_summary(summary, outcome):
    if outcome != "refreshed":
        return summary is None
    return (isinstance(summary, dict) and set(summary) == set(SUMMARY_KEYS) and
            all(type(value) is int and 0 <= value <= 1000000 for value in summary.values()) and
            sum(summary.values()) <= 1000000)


def available_updates(settings, context=None):
    """Read the newly cached plan; simulation never authorizes installation."""
    command = ["/usr/bin/apt-get", "--simulate"]
    if settings["package_mode"] == "with-new-pkgs":
        command.append("--with-new-pkgs")
    command.append("upgrade")
    # Native package/list locks keep the read consistent with local package work.
    with package_lock():
        log_command(context, command)
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True,
                                 env={**os.environ, "LC_ALL": "C", "LANG": "C"})
        try:
            with readonly_budget(child, seconds=30):
                output, stderr_bytes = read_simulation_output(child)
                if len(output) > 1024 * 1024:
                    raise MaintenanceError("maintenance_reader_failed")
                code = child.wait()
        finally:
            child.stdout.close()
            child.stderr.close()
            exit_code(context, child.returncode)
    parsed = parse_output(settings, {"exit_code": code, "stderr_bytes": stderr_bytes,
                                    "stdout": output.decode("utf-8", errors="strict")})
    if parsed.get("problem") != "none":
        raise MaintenanceError("maintenance_reader_failed")
    return {key: parsed[key] for key in SUMMARY_KEYS}



def read_simulation_output(child):
    """Drain both pipes within one budget; any diagnostic keeps the read uncertain."""
    output, stderr_bytes, total = bytearray(), 0, 0
    with selectors.DefaultSelector() as selector:
        selector.register(child.stdout, selectors.EVENT_READ, "stdout")
        selector.register(child.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            for key, _ in selector.select():
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                tee(chunk, key.data)
                if total > 1024 * 1024:
                    raise MaintenanceError("maintenance_reader_failed")
                if key.data == "stdout":
                    output.extend(chunk)
                else:
                    stderr_bytes += len(chunk)
    return bytes(output), stderr_bytes
