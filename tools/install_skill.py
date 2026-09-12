#!/usr/bin/env python3
"""Install only reviewed skill files. Refuse to replace an existing installation."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile
from check_dist import ROOT, validate


def install(root, destination):
    root = Path(root).resolve()
    names = validate(root)
    destination = Path(destination).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / 'insta360-sdk'
    if target.exists() or target.is_symlink():
        raise FileExistsError(f'Skill already exists: {target}. Choose another --dest or move it aside.')
    staging = Path(tempfile.mkdtemp(prefix='.insta360-install-', dir=destination))
    try:
        prefix = 'skills/insta360-sdk/'
        for name in names:
            if name.startswith(prefix):
                path = staging / name.removeprefix(prefix)
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / name, path)
        for name in ['LICENSE', 'NOTICE.md', 'VERSION']:
            shutil.copyfile(root / name, staging / name)
        # Reserve the final name exclusively; never replace a concurrently installed skill.
        target.mkdir()
        try:
            for child in staging.iterdir():
                shutil.move(str(child), target / child.name)
        except BaseException:
            shutil.rmtree(target)
            raise
    finally:
        shutil.rmtree(staging)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', type=Path,
                        default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills',
                        help='Parent skills directory; will create insta360-sdk inside it')
    args = parser.parse_args()
    try:
        print(f'Installed: {install(ROOT, args.dest)}')
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Install failed: {exc}\n')
