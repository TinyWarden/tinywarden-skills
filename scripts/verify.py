#!/usr/bin/env python3
"""Verify trusted skill behavior and reproducible SDK-admitted catalogue artifacts."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from sdk import ROOT, bootstrap

def verify_catalogue(catalog, published, pending, include_unreleased):
    """Check released identities without replacing an unpublished entry in public."""
    def released(value):
        return {**value, 'skills': [entry for entry in value['skills']
                if entry['id'].split('/', 1)[1] not in pending]}
    if released(catalog) != released(published):
        raise ValueError('Released catalogue identities changed')
    candidates = {entry['id'].split('/', 1)[1] for entry in catalog['skills']
                  if entry['id'].split('/', 1)[1] in pending}
    if candidates != (set(pending) if include_unreleased else set()):
        raise ValueError('Unexpected candidate catalogue scope')
    prior = {entry['id']: entry for entry in published['skills']}
    for entry in catalog['skills']:
        old = prior.get(entry['id'])
        if old and old['version'] == entry['version'] and old != entry:
            raise ValueError('Published package version is immutable')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sandbox', action='store_true', help='Also execute disk assessment through the delegated SDK sandbox')
    parser.add_argument('--include-unreleased', action='store_true',
                        help='Also admit and reproducibly build unpublished source; never updates SKILLS.json')
    args = parser.parse_args()
    bootstrap()
    for pattern in ('test_official.py', 'test_services.py', 'test_update_actions_policy.py', 'test_verification.py'):
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern], cwd=ROOT, check=True)
    if args.sandbox:
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_disk_display_sandbox.py'], cwd=ROOT, check=True)
    from build import build
    with tempfile.TemporaryDirectory(prefix='tw-skills-check-') as work:
        a, b = Path(work)/'one', Path(work)/'two'
        catalog = build(a, include_unreleased=args.include_unreleased)
        if catalog != build(b, include_unreleased=args.include_unreleased):
            raise ValueError('Catalogue not reproducible')
        for entry in catalog['skills']:
            name = entry['archive']['asset']
            if (a/name).read_bytes() != (b/name).read_bytes(): raise ValueError('ZIP not reproducible')
        pending = json.loads((ROOT/'UNRELEASED.json').read_text())['skills']
        verify_catalogue(catalog, json.loads((ROOT/'SKILLS.json').read_text()), pending, args.include_unreleased)
    scope = 'including unpublished candidates' if args.include_unreleased else 'published source excluding declared unpublished replacements'
    print('Skill behavior, SDK admission, ZIP reproducibility and catalogue verified:', scope)


if __name__ == '__main__':
    main()
