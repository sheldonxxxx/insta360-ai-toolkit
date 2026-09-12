#!/usr/bin/env python3
"""Build deterministic source and standalone-skill ZIPs from reviewed files only."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from check_dist import ROOT, validate


def write_zip(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def build(root=ROOT, out=None):
    root = Path(root).resolve()
    names = validate(root)
    version = (root / 'VERSION').read_text().strip()
    out = Path(out).resolve() if out else root / 'dist'
    out.mkdir(parents=True, exist_ok=True)
    project = json.loads((root / 'repository.json').read_text())['name']
    source_prefix = f'{project}-{version}'
    source = {f'{source_prefix}/{name}': (root / name).read_bytes() for name in names}
    skill_prefix = 'skills/insta360-sdk/'
    skill = {'insta360-sdk/' + name.removeprefix(skill_prefix): (root / name).read_bytes()
             for name in names if name.startswith(skill_prefix)}
    for name in ['LICENSE', 'NOTICE.md', 'VERSION']:
        skill['insta360-sdk/' + name] = (root / name).read_bytes()
    paths = [out / f'{source_prefix}.zip', out / f'insta360-sdk-{version}.zip']
    for path, entries in zip(paths, [source, skill]):
        write_zip(path, entries)
    (out / 'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in paths))
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Release output directory (default: dist/)')
    args = parser.parse_args()
    for path in build(out=args.out):
        print(path.name)
