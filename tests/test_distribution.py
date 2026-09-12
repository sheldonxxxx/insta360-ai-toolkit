import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_dist import manifest, validate
from install_skill import install
from package import build


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'source'
        for name in manifest(ROOT):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_archives_are_reproducible_and_install_matches_skill_zip(self):
        first = build(self.repo, self.base / 'first')
        second = build(self.repo, self.base / 'second')
        for a, b in zip(first, second):
            self.assertEqual(a.read_bytes(), b.read_bytes())
        lines = (first[0].parent / 'SHA256SUMS').read_text().splitlines()
        for path, line in zip(first, lines):
            self.assertEqual(line, f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}')
        target = install(self.repo, self.base / 'installed')
        with zipfile.ZipFile(first[1]) as archive:
            expected = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
            self.assertEqual(expected, {name.removeprefix('insta360-sdk/') for name in archive.namelist()})
            for name in archive.namelist():
                self.assertEqual(archive.read(name), (target / name.removeprefix('insta360-sdk/')).read_bytes())
        with zipfile.ZipFile(first[0]) as archive:
            archive.extractall(self.base / 'extracted')
        extracted = next((self.base / 'extracted').iterdir())
        self.assertEqual(validate(extracted), validate(self.repo))
        self.assertTrue((extracted / 'viewer/server.py').is_file())
        self.assertFalse((target / 'viewer').exists())

    def test_install_refuses_existing_and_dangling_symlink_without_changes(self):
        dest = self.base / 'installed'
        target = install(self.repo, dest)
        marker = target / 'local-note.md'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            install(self.repo, dest)
        self.assertEqual(marker.read_text(), 'keep')
        other = self.base / 'other'
        other.mkdir()
        (other / 'insta360-sdk').symlink_to(self.base / 'missing')
        with self.assertRaises(FileExistsError):
            install(self.repo, other)

    def test_unreviewed_photo_blocks_release(self):
        (self.repo / 'private.insp').write_bytes(b'private sample')
        with self.assertRaisesRegex(ValueError, 'Unreviewed files'):
            build(self.repo, self.base / 'release')
        self.assertFalse((self.base / 'release').exists())

    def test_symlink_blocks_release(self):
        path = self.repo / 'README.md'
        path.unlink()
        path.symlink_to(ROOT / 'README.md')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            validate(self.repo)

    def test_private_path_in_allowed_document_blocks_release(self):
        with (self.repo / 'README.md').open('a') as file:
            file.write('\n' + '/' + 'Users' + '/example/private-photo\n')
        with self.assertRaisesRegex(ValueError, 'machine-specific'):
            validate(self.repo)

    def test_private_files_in_dist_are_never_packaged(self):
        (self.repo / 'dist').mkdir()
        (self.repo / 'dist/private.insp').write_bytes(b'not a release file')
        paths = build(self.repo)
        for path in paths:
            with zipfile.ZipFile(path) as archive:
                self.assertFalse(any('private.insp' in name for name in archive.namelist()))

    def test_local_workspace_directories_are_not_packaged(self):
        for name in ['sdk', 'samples', 'outputs', 'research', 'runtime', 'Linux_CameraSDK-test']:
            folder = self.repo / name
            folder.mkdir()
            (folder / 'private.txt').write_text('private local data')
            (folder / 'outside').symlink_to(self.base / 'missing')
        for path in build(self.repo, self.base / 'release'):
            with zipfile.ZipFile(path) as archive:
                self.assertFalse(any('private.txt' in name or '/outside' in name for name in archive.namelist()))

    def test_local_workspace_cannot_enter_manifest(self):
        path = self.repo / 'sdk/private.md'
        path.parent.mkdir()
        path.write_text('must stay local')
        definition = self.repo / 'distribution.json'
        data = json.loads(definition.read_text())
        data['files'] = sorted(data['files'] + ['sdk/private.md'])
        definition.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'cannot be distributed'):
            validate(self.repo)

    def test_tracked_private_file_blocks_release_even_when_ignored(self):
        path = self.repo / 'sdk/private.md'
        path.parent.mkdir()
        path.write_text('must stay local')
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True)
        subprocess.run(['git', 'add', '-f', 'sdk/private.md'], cwd=self.repo, check=True)
        with self.assertRaisesRegex(ValueError, 'Tracked files outside distribution'):
            validate(self.repo)

    def test_social_preview_slot_rejects_other_binary_formats(self):
        (self.repo / 'docs/assets/social-preview.png').write_bytes(b'not a PNG')
        with self.assertRaisesRegex(ValueError, 'must be a PNG'):
            validate(self.repo)

    def test_social_preview_metadata_blocks_release(self):
        path = self.repo / 'docs/assets/social-preview.png'
        png = path.read_bytes()
        chunk = b'tEXt' + b'Comment\x00unreviewed metadata'
        encoded = struct.pack('>I', len(chunk) - 4) + chunk + struct.pack('>I', zlib.crc32(chunk))
        path.write_bytes(png[:-12] + encoded + png[-12:])
        with self.assertRaisesRegex(ValueError, 'stripped of metadata'):
            validate(self.repo)

    def test_repository_name_cannot_escape_archive_prefix(self):
        path = self.repo / 'repository.json'
        data = json.loads(path.read_text())
        data['name'] = '../outside'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'lowercase slug'):
            build(self.repo, self.base / 'release')
