import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sdk_run', ROOT / 'skills/insta360-sdk/scripts/sdk_run.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.lab = Path(temp.name).resolve()
        self.sdk = self.lab / 'sdk'
        for name in ['MediaSDK-test/include/ins_stitcher.h',
                     'media-runtime/opt/MediaSDK-test-linux/lib/libMediaSDK.so',
                     'InsMetaDataSDK-test/include/metaData.h',
                     'InsMetaDataSDK-test/lib/libInsMetaDataSDK.so']:
            path = self.sdk / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        self.inputs, self.outputs = self.lab / 'originals', self.lab / 'results'
        self.inputs.mkdir(); self.outputs.mkdir()
        (self.outputs / 'media_tool').touch()

    def run_helper(self, tail, result=None):
        args = ['sdk_run', '--sdk-root', str(self.sdk), '--input-dir', str(self.inputs),
                '--output-dir', str(self.outputs)] + tail
        result = result or subprocess.CompletedProcess([], 0, 'linux/amd64\n', '')
        with patch('sys.argv', args), patch.dict('os.environ', {}, clear=True), \
             patch.object(runtime.subprocess, 'run', return_value=result) as run, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = runtime.main()
        return code, run.call_args_list

    def test_project_mounts_keep_originals_and_sdk_read_only_and_propagate_failure(self):
        code, calls = self.run_helper(['--timeout', '17', 'media', 'image', '--input', '/samples/photo.insp'],
                                     subprocess.CompletedProcess([], 4))
        self.assertEqual(code, 4)
        command = calls[0].args[0]
        for source, target in [(self.sdk, '/sdk'), (self.inputs, '/samples')]:
            self.assertIn(f'type=bind,src={source},dst={target},readonly', command)
        self.assertIn(f'type=bind,src={self.outputs},dst=/work', command)
        self.assertIn('--rm', command)
        self.assertEqual(command[command.index('--network') + 1], 'none')
        self.assertEqual(command[command.index('timeout'):command.index('timeout') + 3],
                         ['timeout', '--kill-after=5', '17'])
        self.assertEqual(command[-4:], ['/work/media_tool', 'image', '--input', '/samples/photo.insp'])

    def test_doctor_rejects_wrong_architecture(self):
        code, _ = self.run_helper(['doctor'], subprocess.CompletedProcess([], 0, 'linux/arm64\n', ''))
        self.assertEqual(code, 2)

    def test_doctor_accepts_amd64_image(self):
        self.assertEqual(self.run_helper(['doctor'])[0], 0)

    def test_overlapping_output_cannot_make_originals_writable(self):
        self.outputs = self.inputs
        with self.assertRaisesRegex(ValueError, 'non-nested'):
            self.run_helper(['media', '--help'])
        self.outputs = self.lab
        with self.assertRaisesRegex(ValueError, 'non-nested'):
            self.run_helper(['media', '--help'])

    def test_legacy_lab_still_works(self):
        (self.lab / 'samples').mkdir(); (self.lab / 'outputs').mkdir()
        (self.lab / 'outputs/media_tool').touch()
        with patch('sys.argv', ['sdk_run', '--lab', str(self.lab), 'media', '--help']), \
             patch.dict('os.environ', {}, clear=True), \
             patch.object(runtime.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(runtime.main(), 0)
            self.assertIn('dst=/work', ' '.join(run.call_args.args[0]))

    def test_build_stops_on_compiler_failure(self):
        code, calls = self.run_helper(['build'], subprocess.CompletedProcess([], 1))
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 1)
