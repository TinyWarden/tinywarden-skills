import os
import re
import subprocess
from .apt_policy import MaintenanceError, trusted_sources, budget_clock
from .logs import command as log_command, exit_code
"""Strict index-only refresh; bounded cancellation never targets dpkg."""
import selectors
import signal


def strict_refresh(on_start, context=None):
    trusted_sources(False)
    read_fd, write_fd = os.pipe()
    child = None
    selector = selectors.DefaultSelector()
    try:
        selector.register(read_fd, selectors.EVENT_READ)
        command = ['/usr/bin/apt-get', 'update', '--error-on=any', '-o', 'APT::Status-Fd=' + str(write_fd)]
        on_start()  # Persist possible partial changes before starting apt-get.
        log_command(context, command)
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                 pass_fds=(write_fd,), start_new_session=True)
        os.close(write_fd)
        write_fd = None
        started = changed = budget_clock()
        previous, pending = -1.0, b''
        while child.poll() is None:
            now = budget_clock()
            if now - started >= 1800 or now - changed >= 120:
                raise MaintenanceError('maintenance_refresh_timeout')
            if selector.select(timeout=1):
                block = os.read(read_fd, 8192)
                pending = (pending + block)[-16384:]
                lines = pending.split(b'\n')
                pending = lines.pop()
                for line in lines:
                    match = re.match(rb'dlstatus:([0-9]+(?:\.[0-9]+)?):', line)
                    if match:
                        progress = float(match[1])
                        if progress > previous:
                            previous, changed = progress, now
                if not block:
                    selector.unregister(read_fd)
        if budget_clock() - started >= 1800 or budget_clock() - changed >= 120:
            raise MaintenanceError('maintenance_refresh_timeout')
        if child.returncode != 0:
            raise MaintenanceError('maintenance_refresh_failed')
        return
    finally:
        if child is not None and child.poll() is None:
            # Fixed apt-get update only: these children never perform package installation.
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if child is not None:
            exit_code(context, child.returncode)
        selector.close()
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
