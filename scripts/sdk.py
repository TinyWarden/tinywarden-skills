"""Fetch only exact, hash-pinned SDK files into an ignored authoring cache."""
import hashlib
import io
import json
import os
import shutil
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / '.cache/sdk'


def bootstrap():
    # Explicit source development only; published builds use the pinned SDK below.
    source = os.environ.get('TW_SKILL_SDK_SOURCE')
    if source:
        directory = Path(source).resolve(strict=True)
        artifact = directory / 'sdk/python/runtime/artifact.json'
        record = json.loads(artifact.read_text())
        for name, digest in record['files'].items():
            path = artifact.parent / name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Source SDK runtime hash mismatch')
        return directory
    lock = json.loads((ROOT / 'SDK.lock.json').read_text())
    def matches():
        return all((SDK / name).is_file() and not (SDK / name).is_symlink()
                   and hashlib.sha256((SDK / name).read_bytes()).hexdigest() == digest
                   for name, digest in lock['files'].items())
    if SDK.exists():
        if matches(): return SDK
        raise ValueError('SDK cache differs from SDK.lock.json; remove .cache/sdk and retry')
    url = f"https://codeload.github.com/{lock['repository']}/tar.gz/{lock['commit']}"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != lock['archive_sha256']:
        raise ValueError('SDK archive hash mismatch')
    SDK.mkdir(parents=True)
    try:
        prefix = 'tinywarden-agent-' + lock['commit'] + '/'
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            members = {m.name: m for m in archive.getmembers()}
            for name, digest in lock['files'].items():
                if '..' in Path(name).parts or Path(name).is_absolute(): raise ValueError('SDK path')
                member = members.get(prefix + name)
                if not member or not member.isfile() or member.size > 1024 * 1024: raise ValueError('SDK member')
                raw = archive.extractfile(member).read(1024 * 1024 + 1)
                if hashlib.sha256(raw).hexdigest() != digest: raise ValueError('SDK file hash')
                target = SDK / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        if not matches(): raise ValueError('SDK cache verification')
    except BaseException:
        shutil.rmtree(SDK)
        raise
    return SDK


if __name__ == '__main__':
    print(bootstrap())
