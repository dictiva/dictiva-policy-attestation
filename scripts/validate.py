#!/usr/bin/env python3
"""Validate documentation artifacts without installing application dependencies."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in sorted(ROOT.rglob('*.py')):
        if '.git' not in path.parts:
            ast.parse(path.read_text(), filename=str(path))
    paths = [*ROOT.glob('examples/*.jsonld'),
             ROOT / 'contexts/policy-commitment/v1.jsonld',
             ROOT / 'contexts/policy-commitment/v1',
             ROOT / 'scripts/merge-pr.json']
    for path in paths:
        json.loads(path.read_text())

    feed = ROOT / 'changelog.atom'
    original = feed.read_bytes()
    try:
        command = [sys.executable, '.github/scripts/generate-changelog-atom.py']
        subprocess.run(command, cwd=ROOT, check=True, timeout=30)
        first = feed.read_bytes()
        root = ET.fromstring(first)
        entries = root.findall('{http://www.w3.org/2005/Atom}entry')
        if root.tag != '{http://www.w3.org/2005/Atom}feed' or not entries:
            raise ValueError('Generated Atom feed must contain entries')
        subprocess.run(command, cwd=ROOT, check=True, timeout=30)
        if first != feed.read_bytes():
            raise ValueError('Atom generator is not deterministic')
    finally:
        feed.write_bytes(original)
    print(f'PASS: {len(paths)} JSON documents, Python syntax, valid deterministic Atom feed')


if __name__ == '__main__':
    main()
