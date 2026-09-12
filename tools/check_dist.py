#!/usr/bin/env python3
"""Validate the explicit public-file boundary without loading SDKs or media."""
import ast
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    (re.compile(r'/(?:Users|Volumes)/[^\s`"<>]+'), 'machine-specific absolute path'),
    (re.compile(r'IMG_\d{8}_\d{6}'), 'capture-identifying filename'),
    (re.compile(r'\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)\b'), 'private network address'),
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'), 'private key'),
    (re.compile(r'\bAKIA[A-Z0-9]{16}\b'), 'access key'),
]
ALLOWED_SUFFIXES = {'.md', '.json', '.yaml', '.yml', '.py', '.cc', '.svg', '.html', '.js', '.css'}
ALLOWED_NAMES = {'LICENSE', 'VERSION', 'Dockerfile', '.gitignore', '.dockerignore'}
LOCAL_ROOTS = {'.git', 'dist', '.venv', 'sdk', 'samples', 'outputs', 'research', 'runtime'}


def local_root(name):
    return name in LOCAL_ROOTS or name.startswith('Linux_CameraSDK-')


def validate_social_preview(file):
    # The only approved binary is this original project illustration.
    content = file.read_bytes()
    if len(content) >= 1_000_000 or content[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Social preview must be a PNG under 1 MB')
    offset, chunks = 8, []
    while offset < len(content):
        if offset + 12 > len(content):
            raise ValueError('Truncated social preview')
        size = struct.unpack('>I', content[offset:offset + 4])[0]
        kind = content[offset + 4:offset + 8]
        if kind not in {b'IHDR', b'IDAT', b'IEND'} or offset + 12 + size > len(content):
            raise ValueError('Social preview must be stripped of metadata')
        if kind == b'IHDR' and (size != 13 or struct.unpack('>II', content[offset + 8:offset + 16]) != (1280, 640)):
            raise ValueError('Social preview must be 1280 by 640')
        chunks.append(kind)
        offset += size + 12
    if not chunks or chunks[0] != b'IHDR' or chunks[-1] != b'IEND' or b'IDAT' not in chunks:
        raise ValueError('Incomplete social preview')


def manifest(root):
    data = json.loads((root / 'distribution.json').read_text())
    names = data['files']
    if len(names) != len(set(names)) or names != sorted(names):
        raise ValueError('Distribution file list must be unique and sorted')
    if 'distribution.json' not in names:
        raise ValueError('Manifest must include itself')
    return names


def validate(root=ROOT):
    root = Path(root).resolve()
    names = manifest(root)
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError(f'Invalid distribution path: {name}')
        if local_root(path.parts[0]):
            raise ValueError(f'Local workspace path cannot be distributed: {name}')
        for i in range(1, len(path.parts) + 1):
            if root.joinpath(*path.parts[:i]).is_symlink():
                raise ValueError(f'Symlink in distribution path: {name}')
        file = root / name
        if not file.is_file():
            raise ValueError(f'Missing distribution file: {name}')
        if name == 'docs/assets/social-preview.png':
            validate_social_preview(file)
            continue
        if file.suffix not in ALLOWED_SUFFIXES and file.name not in ALLOWED_NAMES:
            raise ValueError(f'Non-source file in distribution: {name}')
        if file.stat().st_size > 2_000_000:
            raise ValueError(f'Oversized distribution file: {name}')
        content = file.read_text(encoding='utf-8')
        if '\x00' in content:
            raise ValueError(f'Binary content: {name}')
        for pattern, reason in PATTERNS:
            if pattern.search(content):
                raise ValueError(f'{reason}: {name}')
        if file.suffix == '.py':
            ast.parse(content, filename=name)
        if file.suffix == '.json':
            json.loads(content)
        if file.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', content):
                if '://' in target or target.startswith('#'):
                    continue
                destination = (file.parent / target.split('#')[0]).resolve()
                if not destination.is_relative_to(root) or not destination.is_file():
                    raise ValueError(f'Broken local link in {name}: {target}')
    # Prune private/runtime trees before traversal; never read their contents.
    actual = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        dirs[:] = [name for name in dirs if name != '__pycache__'
                   and not (parent == root and local_root(name))]
        for name in dirs + files:
            if name == '.DS_Store' or (parent == root and local_root(name)):
                continue
            file = parent / name
            relative = file.relative_to(root)
            if file.is_symlink():
                raise ValueError(f'Unreviewed symlink: {relative}')
            if file.is_file():
                actual.add(relative.as_posix())
    if actual != set(names):
        raise ValueError(f'Unreviewed files: {sorted(actual - set(names))}')
    if (root / '.git').exists():
        tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\x00')
        unexpected = set(filter(None, tracked)) - set(names)
        if unexpected:
            raise ValueError(f'Tracked files outside distribution: {sorted(unexpected)}')
    skill = (root / 'skills/insta360-sdk/SKILL.md').read_text()
    if not skill.startswith('---\nname: insta360-sdk\ndescription: ') or '\n---\n' not in skill[4:]:
        raise ValueError('Invalid skill frontmatter')
    if not re.fullmatch(r'\d+\.\d+\.\d+\n?', (root / 'VERSION').read_text()):
        raise ValueError('VERSION must be a plain semantic version')
    project = json.loads((root / 'repository.json').read_text())
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', project['name']):
        raise ValueError('Repository name must be a lowercase slug')
    if len(project['topics']) > 20 or any(not re.fullmatch(r'[a-z0-9-]{1,50}', t) for t in project['topics']):
        raise ValueError('Invalid repository topics')
    return names


if __name__ == '__main__':
    try:
        print(f'Validated {len(validate())} public source files')
    except (OSError, ValueError, SyntaxError) as exc:
        print(f'Distribution check failed: {exc}', file=sys.stderr)
        sys.exit(1)
