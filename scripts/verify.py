#!/usr/bin/env python3
"""Verify trusted skill behavior and reproducible SDK-admitted catalogue artifacts."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from sdk import ROOT, bootstrap

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sandbox', action='store_true', help='Also execute disk assessment through the delegated SDK sandbox')
args = parser.parse_args()
bootstrap()
subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_official.py'], cwd=ROOT, check=True)
if args.sandbox:
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_disk_display_sandbox.py'], cwd=ROOT, check=True)
from build import build
with tempfile.TemporaryDirectory(prefix='tw-skills-check-') as work:
    a, b = Path(work)/'one', Path(work)/'two'
    catalog = build(a)
    if catalog != build(b): raise ValueError('Catalogue not reproducible')
    for entry in catalog['skills']:
        name = entry['archive']['asset']
        if (a/name).read_bytes() != (b/name).read_bytes(): raise ValueError('ZIP not reproducible')
    if catalog != json.loads((ROOT/'SKILLS.json').read_text()): raise ValueError('SKILLS.json is stale')
print('Skill behavior, SDK admission, ZIP reproducibility and catalogue verified')
