"""Destination footprint and writable filesystem checks."""
from .apt_policy import POLICY, MaintenanceError, Path, os, stat, apt_pkg

def capacity_directory(raw):
    # Resolve existing parent aliases (for example merged /usr), never a payload
    # symlink's target. Missing directories use their nearest actual ancestor.
    try:
        path = Path(raw).resolve(strict=False)
        while not path.exists():
            path = path.parent
        for ancestor in [path, *path.parents]:
            info = ancestor.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise MaintenanceError('maintenance_destination_invalid')
        return path
    except (OSError, RuntimeError):
        raise MaintenanceError('maintenance_destination_invalid') from None

def capacity(plan, installed=None, changes=None):
    # A footprint estimate with reserve, not a bound on arbitrary script writes.
    paths = {capacity_directory('/'),
             capacity_directory(Path(apt_pkg.config.find_file('Dir::State::status')).parent),
             capacity_directory(apt_pkg.config.find_dir('Dir::Cache::archives'))}
    payload_bytes, payload_inodes = 0, 0
    if installed is not None:
        for package in plan['packages']:
            key = (package['name'], package['architecture'])
            for name in installed[key]['paths']:
                path = Path(name)
                try:
                    if stat.S_ISDIR(path.lstat().st_mode):
                        continue
                except FileNotFoundError:
                    pass
                paths.add(capacity_directory(path.parent))
    if changes is not None:
        payload = [entry for value in changes.values() for entry in value['payload']]
        aliases = {entry['path'] for entry in payload if entry['kind'] in ('symlink', 'hardlink')}
        for entry in payload:
            path = Path(entry['path'])
            if any(str(parent) in aliases for parent in path.parents):
                raise MaintenanceError('maintenance_destination_invalid')
            if entry['kind'] == 'directory' and path.is_dir():
                continue
            paths.add(capacity_directory(path.parent))
            payload_bytes += max(entry['bytes'], 4096)
            payload_inodes += 1
    required = (plan['download_bytes'] + POLICY['unpack_multiplier'] *
                max(plan['unpacked_bytes'], payload_bytes) + POLICY['reserve_bytes'])
    inodes = POLICY['reserve_inodes'] + max(payload_inodes, len(plan['packages']) * POLICY['inodes_per_package'])
    # Check every relevant path's flags, even bind mounts sharing a device number.
    # Existing empty directories and terminal symlink targets never invent writes
    # into an unrelated /proc, EFI or other small filesystem.
    for path in paths:
        fs = os.statvfs(path)
        if (not os.access(path, os.W_OK) or fs.f_flag & os.ST_RDONLY or
                fs.f_bavail * fs.f_frsize < required or fs.f_favail < inodes):
            raise MaintenanceError('maintenance_disk_space')
