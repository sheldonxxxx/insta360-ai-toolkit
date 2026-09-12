# Distribution validation

Reviewed 2026-09-12 for version 0.1.0. Runtime testing was performed **only on macOS Apple Silicon**, using the Linux x86-64 SDK inside Docker with CPU/Mesa and CUDA disabled.

## Public package checks

- Explicit source allowlist, local Markdown links, JSON/Python parsing and focused privacy checks passed.
- Eighteen automated tests passed, including repeatable ZIP bytes and checksums, source archive extraction, installed-file parity with the skill ZIP, existing-install preservation, rejection of unexpected photos/symlinks/private paths, and Docker invocation boundaries. Root-layout checks cover ignored local directories, forbidden manifest entries and accidentally tracked private files.
- The same tests passed from an extracted source archive in a fresh directory.
- The skill frontmatter/structure validator passed.
- The full source archive also includes the local 360° viewer. Its twelve HTTP boundary tests and an extracted-archive browser check passed; see [viewer verification](../viewer/VERIFICATION.md).
- Both archives include MIT licensing and the third-party notice. No vendor packages, headers, libraries, models, personal inputs or logs are included.

## Licensed integration check

The source archive was extracted and its installer run into a separate skills directory. From that installed copy:

1. The included Dockerfile built `insta360-postprocess:ubuntu22.04` as `linux/amd64`, reusing cached dependency layers.
2. `doctor` passed; both C++ helpers compiled against MediaSDK 3.1.5 and InsMetaDataSDK 2.0.2.
3. Native INSP metadata inspection returned success.
4. Optical-flow stitching with FlowState produced a new 960×480 JPEG. The verifier passed full decode, dimensions and nonuniform-pixel checks.
5. Visual inspection showed a level, nonblank panorama. Original source hashes remained unchanged.

SDKs, original files, logs and output images stayed outside the public repository and release artifacts. This check is a single-photo distribution smoke test; broader prior SDK observations and known failures are in the skill's [verification reference](../skills/insta360-sdk/references/verification.md).

These results describe local validation. GitHub Actions is configured for source/package validation on a Mac runner; consult the repository's Actions tab for the result on a particular commit. It does not execute the proprietary SDK. No release artifacts or container images have been published. Native Linux, Windows, Intel Macs, GPU/CUDA, video and realtime paths remain untested.
