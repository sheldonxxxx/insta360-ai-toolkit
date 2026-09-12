#!/usr/bin/env python3
"""Run a separately obtained Insta360 Linux SDK in an offline Docker container.

Tested in Ubuntu 22.04 amd64 containers on Apple Silicon and x86-64 Linux.
Linux NVIDIA compute/Mesa qualification is documented in references/runtime.md.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lab', type=Path, default=os.environ.get('INSTA360_LAB'),
                   help='Legacy workspace containing sdk/, samples/ and outputs/')
    p.add_argument('--sdk-root', type=Path, default=os.environ.get('INSTA360_SDK_ROOT'),
                   help='Directory containing extracted MediaSDK, media-runtime and MetadataSDK')
    p.add_argument('--input-dir', type=Path, help='Project originals mounted read-only at /samples')
    p.add_argument('--output-dir', type=Path, help='Project build/results directory mounted at /work')
    p.add_argument('--image', default='insta360-postprocess:ubuntu22.04')
    p.add_argument('--timeout', type=int, default=120)
    p.add_argument('--gpu', action='store_true', help='Request existing NVIDIA device access; see runtime guide for the tested compute/Mesa path')
    p.add_argument('command', choices=['doctor', 'build', 'media', 'metadata'])
    p.add_argument('args', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.timeout < 1:
        p.error('--timeout must be positive')
    if not a.sdk_root and not a.lab:
        p.error('Set INSTA360_SDK_ROOT or --sdk-root (or legacy --lab)')
    sdk = (a.sdk_root or a.lab / 'sdk').resolve(strict=True)

    def one(pattern):
        matches = list(sdk.glob(pattern))
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one {pattern}; found {len(matches)}. Use one SDK version per root.')
        return matches[0]

    media = one('MediaSDK-*/include/ins_stitcher.h').parent.parent
    runtime = one('media-runtime/opt/MediaSDK-*-linux/lib/libMediaSDK.so').parent.parent
    metadata = one('InsMetaDataSDK-*/include/metaData.h').parent.parent
    if not (metadata / 'lib/libInsMetaDataSDK.so').is_file():
        raise ValueError('MetadataSDK library missing: lib/libInsMetaDataSDK.so')
    inputs = a.input_dir or (a.lab / 'samples' if a.lab else None)
    outputs = a.output_dir or (a.lab / 'outputs' if a.lab else None)
    scripts = Path(__file__).resolve().parent
    if a.command == 'doctor':
        if a.args:
            p.error('doctor takes no trailing arguments')
        inspect = subprocess.run(['docker', 'image', 'inspect', a.image, '--format', '{{.Os}}/{{.Architecture}}'],
                                 capture_output=True, text=True, timeout=30)
        platform = inspect.stdout.strip()
        ok = inspect.returncode == 0 and platform == 'linux/amd64'
        print(json.dumps({'sdk_root': str(sdk), 'models_present': (media / 'models/ai_stitcher.ins').is_file(),
                          'docker_image': a.image, 'image_platform': platform, 'ready': ok,
                          'input_dir_present': bool(inputs and inputs.is_dir()),
                          'output_dir_present': bool(outputs and outputs.is_dir()),
                          'network': 'none', 'gpu_requested': a.gpu,
                          'tested_host': 'Apple Silicon and x86-64 Linux; Ubuntu 22.04 amd64 containers (see runtime guide)'}, indent=2))
        if not ok:
            print('sdk_run: build the dependency image as linux/amd64 and check Docker is running', file=sys.stderr)
        return 0 if ok else 2
    if not inputs or not outputs or not inputs.is_dir() or not outputs.is_dir():
        raise ValueError('Provide existing --input-dir and --output-dir (or lab samples/ and outputs/)')
    inputs, outputs = inputs.resolve(strict=True), outputs.resolve(strict=True)
    # A writable mount must never contain the originals or licensed SDK.
    if inputs == outputs or inputs in outputs.parents or outputs in inputs.parents:
        raise ValueError('Input and output directories must be separate, non-nested directories')
    if sdk == outputs or sdk in outputs.parents or outputs in sdk.parents:
        raise ValueError('SDK and output directories must be separate, non-nested directories')
    common = ['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none']
    if a.gpu:
        common += ['--gpus', 'all']
    for src, dst, readonly in [(sdk, '/sdk', True), (inputs, '/samples', True),
                                (scripts, '/scripts', True), (outputs, '/work', False)]:
        if ',' in str(src):
            raise ValueError('Docker --mount paths cannot contain commas')
        common += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    common += ['-w', '/work', a.image, 'timeout', '--kill-after=5', str(a.timeout)]

    def inside(path):
        return '/sdk/' + str(path.relative_to(sdk))

    if a.command == 'build':
        if a.args:
            p.error('build takes no trailing arguments')
        for name, header_dir, lib_dir, lib in [
            ('media_tool', media / 'include', runtime / 'lib', 'MediaSDK'),
            ('metadata_probe', metadata / 'include', metadata / 'lib', 'InsMetaDataSDK')
        ]:
            cmd = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-I' + inside(header_dir),
                   '/scripts/' + name + '.cc', '-L' + inside(lib_dir),
                   '-Wl,-rpath,' + inside(lib_dir), '-l' + lib, '-o', '/work/' + name]
            result = subprocess.run(common + cmd)
            if result.returncode:
                return result.returncode
        return 0
    binary = 'media_tool' if a.command == 'media' else 'metadata_probe'
    if not (outputs / binary).is_file():
        raise ValueError('Run build first with the same --output-dir')
    return subprocess.run(common + ['/work/' + binary] + a.args).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'sdk_run: {exc}', file=sys.stderr)
        sys.exit(2)
