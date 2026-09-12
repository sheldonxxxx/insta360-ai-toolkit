# Distribution and release process

This workspace root is the repository root. Publish its reviewed source files using `distribution.json`. This project distributes original source code and a skill. Local SDK files, private media and logs can remain in their ignored workspace directories.

## Local release checks

From the repository root with Python 3.10+:

```sh
python3 tools/check_dist.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s viewer -p 'test_server.py' -v
python3 tools/package.py
```

Run the checksum command **from `dist/`**, since the manifest names are relative:

```sh
(cd dist && shasum -a 256 -c SHA256SUMS)
```

`distribution.json` is an explicit file allowlist. Adding a public file requires reviewing it and updating that list. `check_dist.py` rejects unexpected source files, symlinks, binary/non-source files, broken local Markdown links and common private-path/credential patterns. It skips local root directories `sdk/`, `samples/`, `outputs/`, `research/`, `runtime/` and `Linux_CameraSDK-*`, which are also ignored by Git. The only allowed binary asset is the original, metadata-stripped `docs/assets/social-preview.png` illustration; it is checked for PNG format, dimensions and size. Those local directories cannot be added to the distribution manifest. Any Git-tracked file outside the manifest blocks release, even if its directory is ignored. Generated `dist/`, Git internals, Python caches and virtual environments are also excluded. This is a focused accidental-disclosure check, not proof that arbitrary prose contains no private information; inspect the archive listing and changes before release.

`package.py` creates:

- `insta360-ai-toolkit-<version>.zip`: full public source repository including the local 360° viewer, without Git history.
- `insta360-sdk-<version>.zip`: directly installable `insta360-sdk/` folder with helpers, references, license, notices and version.
- `SHA256SUMS`: SHA-256 checksums for both archives.

Archive order, timestamps and permissions are fixed; ZIP entries are stored without compression so identical source bytes yield identical archives across hosts. This does not imply that subsequent Docker/apt builds reproduce identical binaries. Private build receipts remain outside the tracked source and release archives.

## Test the distributed artifact

Extract the source ZIP into a fresh directory, run its checks/tests, and install using `tools/install_skill.py --dest /path/to/temporary-skills`. Compare the installed files with the standalone skill ZIP. The installer must reject an existing destination without changing it.

For licensed integration testing on a Mac, build the Dockerfile from that extracted skill, run `doctor`, compile the helpers, inspect an original with `metadata`, stitch a new output and run `verify_image.py`. Inspect the output visually. Point `--sdk-root`, `--input-dir` and `--output-dir` at directories outside the repository. Do not add those paths, logs or images to a public commit.

Only **macOS Apple Silicon hosting linux/amd64 Docker** has runtime evidence. CI validates source packaging without proprietary SDK files; a CI pass does not establish Linux, Windows, Intel Mac, GPU, video or realtime compatibility. Keep the platform statement and known failures in the README and skill current.

## Publish when ready

1. Review `VERSION`, README, SDK acquisition links, MIT license and third-party notices. Use the project name, About text, topics and sharing asset prepared in [launch settings](launch.md).
2. Review `distribution.json`, the full diff, and archive contents. Confirm no private files are tracked.
3. Push the reviewed source to the intended remote. A private repository can be used for preparation; make it public only when its owner chooses to launch. Keep the ignored SDK, media and runtime directories untracked.
4. Tag the reviewed version as `v<version>` and create a release with the two ZIPs and `SHA256SUMS`.
5. Download the release artifacts and verify their checksums before announcing them.

The included CI workflow runs packaging/tests and uploads review artifacts. It does not create releases, publish Docker images, download SDKs or use private test media. No registry or repository account is embedded in the skill. A registry image, if added later, should continue to contain only dependencies and carry their license notices; never bake licensed SDK files or photographs into it.
