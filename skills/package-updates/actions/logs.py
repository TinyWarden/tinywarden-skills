"""Optional package-owned progress messages; never execution or retry policy."""


def log(context, key):
    writer = getattr(context, "log", None)
    if writer is not None:
        try:
            writer({"key": "actions.log." + key, "params": {}})
        except Exception:
            # Older compatible execution remains useful without diagnostics.
            pass
