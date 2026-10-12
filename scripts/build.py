#!/usr/bin/env python3
"""Build reproducible release ZIPs and catalogue using the pinned production SDK."""
import argparse
import hashlib
import json
import tempfile
import sys
from pathlib import Path
from sdk import ROOT, bootstrap

SDK = bootstrap()
sys.path.insert(0, str(SDK / 'sdk/python/runtime'))
from packages import content, load
from archives import canonical_archive, extract


def build(output):
    output = Path(output).absolute()
    if output.exists() or ROOT / 'skills' == output or ROOT / 'skills' in output.parents:
        raise ValueError('Use a new output directory outside skills/')
    output.mkdir(parents=True)
    entries = []
    for directory in sorted((ROOT / 'skills').iterdir()):
        if not directory.is_dir(): continue
        metadata = load(directory, official=True)
        manifest = metadata['manifest']
        files, digest, _ = content(directory)
        name = directory.name + '-' + manifest['version'] + '.zip'
        with tempfile.TemporaryDirectory(prefix='tw-skill-release-') as temporary:
            store = Path(temporary)
            archive = canonical_archive(store, digest, files)
            data = (store / '.archives' / (digest + '.zip')).read_bytes()
            extracted = store / 'roundtrip'
            extract(store / '.archives' / (digest + '.zip'), extracted)
            if load(extracted, official=True)['content_sha256'] != digest: raise ValueError('Roundtrip digest')
        (output / name).write_bytes(data)
        entries.append({'id':manifest['id'], 'version':manifest['version'],
            'name':metadata['catalog'][manifest['name_key']]['text'],
            'description':metadata['catalog'][manifest['description_key']]['text'],
            'content_sha256':digest, 'archive':{'tag':directory.name+'-v'+manifest['version'],
                'asset':name, 'sha256':hashlib.sha256(data).hexdigest(), 'size':archive['size']}})
    result = {'format':1, 'skills':sorted(entries, key=lambda v:v['name'].casefold())}
    (output / 'SKILLS.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output)))
