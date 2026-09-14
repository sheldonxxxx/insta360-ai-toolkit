# Distribution validation

The initial version 0.1.0 distribution check was performed on 2026-09-12. Its extracted-package SDK smoke test used **macOS Apple Silicon**, the Linux x86-64 SDK in an Ubuntu 22.04 amd64 container, and CPU/Mesa with CUDA disabled. Broader SDK verification also covers x86-64 Linux and a qualified NVIDIA compute/Mesa path; see the [runtime evidence](../skills/insta360-sdk/references/verification.md). These are distinct scopes.

## Public package checks

- Explicit source allowlist, local Markdown links, JSON/Python parsing and focused privacy checks passed.
- The initial eighteen package and runtime-boundary tests passed, including repeatable ZIP bytes and checksums, source archive extraction, installed-file parity with the skill ZIP, existing-install preservation, rejection of unexpected photos/symlinks/private paths, and Docker invocation boundaries. Root-layout checks cover ignored local directories, forbidden manifest entries and accidentally tracked private files.
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

These results describe the recorded distribution smoke test, not a fresh SDK run for every documentation change. The current suite additionally covers deterministic sphere reprojection, RGB16 precision and GPano delivery metadata. Run all checks in the [distribution guide](distribution.md) for the source revision being released; the test runner reports the current count.

[GitHub Actions](https://github.com/sheldonxxxx/insta360-ai-toolkit/actions) runs source/package and helper tests on a Mac runner, without the proprietary SDK. A passing job does not establish SDK compatibility or photographic quality. Windows, Intel Macs, native macOS SDK execution, video and realtime processing remain unverified by this project; full NVIDIA graphics is also unqualified.
