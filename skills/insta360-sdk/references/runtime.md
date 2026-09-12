# Runtime and executable helpers

## Obtain the SDK

Apply through the [official Insta360 SDK application](https://www.insta360.com/sdk/apply), describe offline MediaSDK processing, and review the terms. The [official guide](https://onlinemanual.insta360.com/developer/en-us/resource/sdk) describes approval by email followed by a download link. Obtain Linux x86-64 MediaSDK and InsMetaDataSDK from the approved downloads; ask Insta360 for the metadata package if absent. CameraSDK is not needed. Do not place vendor packages, private download links or photos in the skill.

## Tested platform

**Tested on macOS only**, specifically Apple Silicon hosting Ubuntu 22.04 `linux/amd64` Docker containers, CPU acceleration, CUDA disabled and Mesa/EGL. This is experimental use of Linux binaries, not native macOS SDK support. Native Linux, Windows, Intel Macs and GPU/CUDA paths have not been runtime-tested by this project. The [vendor desktop requirements](https://insta360develop.github.io/Insta360-Developer_Docs/en/x/desktop/guide/) list Windows/Linux and discrete GPU requirements; observed CPU operation here does not supersede them.

## SDK layout

Set `INSTA360_SDK_ROOT` to a directory outside the public repository. The helper expects one SDK version in this layout:

```text
<INSTA360_SDK_ROOT>/
  MediaSDK-3.1.5-20260819-linux64/{include,models,...deb}
  media-runtime/opt/MediaSDK-3.1.5-linux/{bin,lib,...}
  InsMetaDataSDK-20260629_184813-2.0.2-linux64-default/{include,lib,bin,example}
```

Preserve the versioned directories from your approved archives. These exact versions were tested. The glob-based locator permits other archive versions but compatibility must be checked against their headers and rendered output. MediaSDK and MetadataSDK headers/libraries are separate.

MediaSDK 3.1.5 includes its Linux runtime in a `.deb`. After inspecting the archive contents, extract into a **fresh** `media-runtime/` directory. In a macOS shell with `ar` and `tar`:

```sh
export INSTA360_SDK_ROOT=/path/to/extracted-sdk-root
set -o pipefail
mkdir "$INSTA360_SDK_ROOT/media-runtime" &&
ar -p "$INSTA360_SDK_ROOT/MediaSDK-3.1.5-20260819-linux64/MediaSDK-3.1.5-linux-amd64.deb" data.tar.gz \
  | tar -xz -C "$INSTA360_SDK_ROOT/media-runtime"
```

Do not extract over a customized installation. The tested Debian payload uses `data.tar.gz`; inspect another release before assuming that member exists. The extracted runtime is roughly 11.3 GiB; allow space for the original downloads and dependency image as well. A partial extraction should be inspected before retrying into a new destination.

## Build and select the dependency image

From the installed skill directory:

```sh
docker build --platform linux/amd64 -t insta360-postprocess:ubuntu22.04 \
  -f scripts/Dockerfile scripts
```

No prebuilt image is published. The Dockerfile builds only compiler/render dependencies; SDK libraries/models are mounted at runtime. Building needs network access; SDK executions use `--network none`. Image builds use current Ubuntu package versions, so the image is not claimed to be bit-for-bit reproducible. To select an existing local image, pass `--image NAME` before the command.

## Use project-local originals and results

Run from the project with the installed skill located explicitly:

```sh
export INSTA360_SKILL=/path/to/insta360-sdk
mkdir -p originals processed
sdk() {
  python3 "$INSTA360_SKILL/scripts/sdk_run.py" \
    --input-dir "$PWD/originals" --output-dir "$PWD/processed" "$@"
}
sdk doctor
sdk build
sdk metadata /samples/photo.insp
sdk media info --input /samples/photo.insp
```

Use your original file's actual name instead of `photo.insp`. `--sdk-root PATH` overrides `INSTA360_SDK_ROOT`. Legacy `--lab PATH` / `INSTA360_LAB` still supplies `sdk/`, `samples/` and `outputs/`; explicit paths override those defaults. Machine-specific configuration stays outside the skill.

Mounts: SDK → read-only `/sdk`, originals → read-only `/samples`, skill helper sources → read-only `/scripts`, project results → writable `/work`. Input/output directories must be separate and non-nested; the output must not overlap the SDK. Use a separate output directory for each concurrent job, and run `build` there before processing. Compiled helpers and runtime logs are private job artifacts, not distributable skill content.

Default process timeout is 120 seconds; pass `--timeout N` before the command. Containers are removed after completion. `--gpu` requests an existing NVIDIA runtime and remains untested. Host Python uses only its standard library; image verification additionally requires Pillow.

Helpers compile as C++17 and link `libMediaSDK.so` / `libInsMetaDataSDK.so` with explicit RPATH. The sources use POSIX file descriptors and are not drop-in Windows builds. `metadata` separates JSON stdout from SDK diagnostics on stderr. Keep logs private: the vendor may log input paths or native metadata even when the helper omits identifying fields.

`media info` exit 5 means the SDK returned true but dimensions were unusable; this happened for a valid INSP and does not prove that stitching will fail. Corroborate with native metadata and decoded source pixels.

## Stitch and check one photo

After qualification and `build`, create a **new** output subdirectory. In the same project shell with `sdk()` defined above:

```sh
mkdir processed/review &&
sdk media image \
  --input /samples/photo.insp \
  --output /work/review/stitched.jpg --width 1920 --height 960 \
  --stitch optflow --flowstate 1 --accessory -1 --cuda 0 --accel cpu \
  --models /sdk/MediaSDK-3.1.5-20260819-linux64/models \
  --log-dir /work/review \
  > processed/review/result.json 2> processed/review/sdk.log
```

Only after a successful stitch, run the verifier with a Pillow-enabled Python environment. One way to prepare it in the project is:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install Pillow
.venv/bin/python "$INSTA360_SKILL/scripts/verify_image.py" \
  processed/review/stitched.jpg --expected-size 1920x960
```

Then view the output and inspect horizon, seams, poles and near objects. The verifier checks full decode, dimensions, uniform pixels, hash, black fraction and ICC/GPano marker presence. It cannot certify seam quality, valid spherical metadata, colour management or artistic quality. On a failed run, use a new job subdirectory so stale files cannot pass a later check.

For HDR, repeat `--input` for distinct members of the same exposure bracket. The helper permits one or at least three inputs and rejects exactly two or duplicates. The caller verifies capture grouping. DNG is documented by the vendor but failed direct stitching in the tested runtime. Read the SDK reference for video/frame export; this CLI exposes only saved-photo processing and metadata.

## All still controls in the helper

| Option | Meaning/default |
|---|---|
| `--stitch` | `template`, `optflow` (helper default), `dynamicstitch`, `aistitch`. Template works here because the helper directly calls the enum; vendor demo silently ignores its template string. |
| `--flowstate`, `--fusion`, `--denoise`, `--cooling-shell`, `--colorplus` | Boolean `0` or `1`; defaults off. Fusion with template is rejected. Model-backed features require `--models`. |
| `--colorplus-strength` | Official guide [0,1], default 0.3 for images. Header alone gives only the default. |
| `--cuda` | Boolean, helper default 0. Vendor demo defaults CUDA on. |
| `--accel` | `auto` (helper default) or `cpu`; separate from CUDA/render backend. Examples explicitly request CPU. |
| `--accessory` | Enum integer -1 (auto, helper default) through 20; choose a known physical accessory only when established. See API enum index. |
| `--exposure`, `--highlights`, `--shadows`, `--contrast`, `--brightness`, `--blackpoint`, `--saturation`, `--vibrance`, `--warmth`, `--tint` | Integers [-100,100], default 0. These are relative SDK controls, not physical stops/Kelvin. |
| `--definition` | Integer [0,100], default 0. |
| `--width`, `--height` | Explicit positive 2:1 panorama dimensions; default 1920×960. Helper caps either dimension at 65536 as input validation, not a claimed SDK capacity. |
| `--models`, `--log-dir` | Existing directories; helper appends model-root slash. `--log-dir` resolves a new `media-sdk.log` file inside that directory because this runtime rejects a directory passed directly to `SetLogPath`. Existing log files are protected. Keep captured stderr as well. |

Output must be a new `.jpg`/`.jpeg` path with an existing parent. Duplicate source paths and all existing output entries (including dangling symlinks) are rejected. Exit 0 means SDK/file completion only; 2 validation/exception, 3 metadata parse false, 4 stitch false/missing output, 5 media-info fields unusable. Process signal/timeout exit codes remain visible. The helper does not implement an atomic cross-process output reservation; use unique per-job paths.

Keep `args`, source hashes, model/header/runtime versions, exit code, logs, output hash/dimensions and visual review notes as a recipe/receipt. Use the API reference for video or frame export; this wrapper intentionally exposes only saved-photo processing and metadata.
