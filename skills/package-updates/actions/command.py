"""Small native command runner and action-owned durable receipts."""
import json
import os
import stat
import subprocess
import uuid
from .logs import command, exit_code, tee

# Keep both previews within the approved plain-upgrade scope even when native
# administrator defaults allow hold changes or additional packages.
UPGRADE_OPTIONS = ["-o", "APT::Get::Upgrade-Allow-New=false", "-o", "APT::Get::Remove=false",
                   "-o", "APT::Ignore-Hold=false", "-o", "APT::Get::allow-change-held-packages=false",
                   "-o", "APT::Get::allow-downgrades=false", "-o", "APT::Get::allow-remove-essential=false",
                   "-o", "APT::Get::force-yes=false", "-o", "APT::Get::Fix-Broken=false",
                   "-o", "APT::Get::AutomaticRemove=false"]
UPGRADE_PREVIEW = ["/usr/bin/apt-get", "--simulate", *UPGRADE_OPTIONS, "upgrade"]


class CommandError(Exception):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def preflight():
    if os.geteuid() != 0:
        raise CommandError("maintenance_root_required")
    if not os.access("/usr/bin/apt-get", os.X_OK):
        raise CommandError("maintenance_prerequisites")


def save(context, name, value):
    temporary = "receipt-" + uuid.uuid4().hex + ".tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=context.state_fd)
    try:
        remaining = encode(value).encode()
        while remaining:
            remaining = remaining[os.write(fd, remaining):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, name, src_dir_fd=context.state_fd, dst_dir_fd=context.state_fd)
    os.fsync(context.state_fd)


def load(context, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=context.state_fd)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077
                or info.st_nlink != 1 or info.st_size > 1024 * 1024):
            raise CommandError("maintenance_receipt_invalid")
        value = json.loads(os.read(fd, 1024 * 1024 + 1))
        if (not isinstance(value, dict) or value.get("job_id") != context.job_id
                or value.get("content_sha256") != context.binding["content_sha256"]):
            raise CommandError("maintenance_receipt_invalid")
        return value
    finally:
        os.close(fd)


def run(context, argv, capture=False):
    """APT owns its locks and mutations; native output uses the SDK transcript."""
    command(context, argv)
    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else None,
        stderr=None, env={**os.environ, "LC_ALL": "C", "LANG": "C",
                         "DEBIAN_FRONTEND": "noninteractive", "NEEDRESTART_MODE": "l"})
    output = bytearray()
    try:
        if capture:
            while block := child.stdout.read(65536):
                tee(block, "stdout")
                # Keep draining after the parsing limit. Never lose the native exit.
                if len(output) <= 1024 * 1024:
                    output.extend(block)
        code = child.wait()
    finally:
        if child.stdout is not None:
            child.stdout.close()
        exit_code(context, child.returncode)
    return code, bytes(output)
