"""Optional package-owned progress messages; never execution or retry policy."""
import os
import shlex
import traceback


def output(context, text, stream="stdout"):
    writer = getattr(context, "output", None)
    if writer is not None:
        try:
            writer(text, stream=stream)
        except Exception:
            pass


def command(context, argv):
    if getattr(context, "output", None) is not None:
        output(context, shlex.join(argv), "command")
    else:
        tee(("$ " + shlex.join(argv) + "\n").encode(), "stdout")


def exit_code(context, code):
    if code is None:
        return
    if getattr(context, "output", None) is not None:
        output(context, str(code), "exit")
    else:
        tee(("[exit " + str(code) + "]\n").encode(), "stdout")


def failure(context, error):
    output(context, "".join(traceback.TracebackException.from_exception(error, capture_locals=False).format()), "runtime")


def tee(chunk, stream):
    """Mirror already-read native bytes to the runtime's optional capture pipes."""
    try:
        fd = 1 if stream == "stdout" else 2
        while chunk:
            chunk = chunk[os.write(fd, chunk):]
    except OSError:
        pass


def log(context, key):
    writer = getattr(context, "log", None)
    if writer is not None:
        try:
            writer({"key": "actions.log." + key, "params": {}})
        except Exception:
            # Older compatible execution remains useful without diagnostics.
            pass
