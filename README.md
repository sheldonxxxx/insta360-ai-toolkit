# Insta360 AI Toolkit

**Give your AI agent the full picture.** Stitch, level and prepare Insta360 360° photos for editing—with a reusable agent skill, local Docker tools and a 360° photo viewer.

![Insta360 AI Toolkit: from native INSP to a panorama ready to edit. Stitching, HDR, FlowState and verified exports.](docs/assets/hero.svg)

[Get started](#get-started) · [Try a prompt](#one-prompt-a-complete-photo-workflow) · [360° viewer](#explore-your-panorama) · [What works](#what-we-verified) · [SDK reference](skills/insta360-sdk/references/media-sdk.md) · [MIT license](LICENSE)

**Tested on Mac only** · **Bring your own Insta360 SDK** · **Saved-photo postprocessing**

## Your camera captures the sphere. Your agent handles the workflow.

An Insta360 original needs more than a normal image editor. It carries lens calibration, gyro data and sometimes an exposure bracket. This toolkit gives a coding agent the instructions and executable tools to inspect that input, stitch a panorama, correct its orientation, choose processing options and check the result before the photographic edit begins.

```text
Native INSP → inspect & group → stitch / HDR / FlowState → verify → 360° viewer → photo editor
```

- **Work in natural language.** Ask your agent for a level panorama, an HDR merge or a comparison of stitching settings.
- **Use the whole photo workflow.** Single-image stitching, exposure brackets, 11 colour/detail controls, ColorPlus, denoise and native metadata inspection.
- **Keep processing local.** Original files and SDK libraries are mounted read-only. Processing containers have networking disabled; outputs go to your project.
- **Check the actual result.** Detect blank images and wrong dimensions, preserve source hashes, then inspect horizons and seams. A successful SDK return value alone does not establish a good panorama.
- **Explore the result.** Open the included 360° viewer to look around, zoom, auto-rotate and inspect seams in context. Viewing an existing panorama needs no SDK or Docker.
- **Reuse the setup.** One SDK directory can serve multiple projects, each with its own originals and results.

The included installer targets Codex. Other file- and terminal-capable agents can read [SKILL.md](skills/insta360-sdk/SKILL.md) directly or install the folder in their skill directory. The toolkit supplies an agent skill and CLI helpers; your chosen agent provides the language model. Its own data-handling settings still apply.

## One prompt, a complete photo workflow

After setup, try:

> Use $insta360-sdk to turn the native INSP in originals into a level 360° panorama. Start with a review-size optical-flow stitch and FlowState. Check the horizon, seams and image integrity, then export the chosen settings at the source's full panorama resolution. Keep the original unchanged and save the processing recipe beside the output.

Or ask for a focused task:

| You want to… | Ask your agent… |
|---|---|
| Merge an exposure bracket | “Confirm these INSP files belong to one bracket, then stitch an HDR panorama.” |
| Compare processing choices | “Compare template and optical-flow stitching with the same orientation and dimensions.” |
| Prepare an editing handoff | “Export a stitched derivative for my photo editor with its source hashes and processing settings.” |

Photo-editor integration depends on the editor and tools available to your agent. Camera control is outside this project. Video/frame-export APIs are documented, but the CLI and runtime verification currently cover photos and metadata.

## Get started

You need **Python 3.10+**, a running Docker engine capable of `linux/amd64`, and approved **Linux MediaSDK and InsMetaDataSDK** downloads. Pillow is used for image verification. Runtime testing so far is on an **Apple Silicon Mac** running the Linux SDK inside Docker.

### 1. Get the SDK from Insta360

Apply at the [official Insta360 SDK application page](https://www.insta360.com/sdk/apply). Describe offline photo postprocessing with MediaSDK, complete the requested details and review the agreement. Insta360's [SDK guide](https://onlinemanual.insta360.com/developer/en-us/resource/sdk) describes approval by email followed by a download link, with results normally sent within three working days.

Download **Linux x86-64 MediaSDK**, even on a Mac, plus **InsMetaDataSDK**. If the metadata package is absent from your approved downloads, ask Insta360 for access. This project was tested with **MediaSDK 3.1.5** and **InsMetaDataSDK 2.0.2**; newer versions need revalidation. CameraSDK is not required.

SDK files and models are supplied by Insta360 and are not included in this repository. Follow the short [SDK extraction and directory setup](skills/insta360-sdk/references/runtime.md#sdk-layout) guide before continuing.

### 2. Install the skill and build the local image

From a downloaded or cloned copy of this repository:

```sh
python3 tools/install_skill.py

docker build --platform linux/amd64 \
  -t insta360-postprocess:ubuntu22.04 \
  -f skills/insta360-sdk/scripts/Dockerfile skills/insta360-sdk/scripts
```

The installer uses `$CODEX_HOME/skills`, or `~/.codex/skills` by default. Start a new agent session after installation. It preserves existing installations by refusing to overwrite them; use `--dest /path/to/skills` for another agent or an isolated install.

The Docker image contains build/render dependencies. Your licensed SDK is mounted at runtime. The image is built locally; no prebuilt registry image is published. Building downloads Ubuntu packages; SDK processing runs offline.

Ubuntu 22.04 is the Linux x86-64 environment listed in the [MediaSDK requirements](https://insta360develop.github.io/Insta360-Developer_Docs/en/x/desktop/guide/) and the base used in our Mac-hosted tests. Other distributions or Ubuntu versions need separate compatibility testing.

### 3. Connect a project and give your agent the task

In the project where you want to process photos:

```sh
export INSTA360_SDK_ROOT=/path/to/extracted-sdk-root
export INSTA360_SKILL="${CODEX_HOME:-$HOME/.codex}/skills/insta360-sdk"
mkdir -p originals processed

sdk() {
  python3 "$INSTA360_SKILL/scripts/sdk_run.py" \
    --input-dir "$PWD/originals" --output-dir "$PWD/processed" "$@"
}

sdk doctor
sdk build
```

Place untouched camera originals in `originals/`, then use one of the prompts above. Keep these machine-specific paths in your shell or private project configuration. Every processing job can use a separate output directory; run `build` for that directory first.

Prefer the terminal? Here is the first stitch, after replacing `photo.insp` with your original's filename:

```sh
mkdir processed/first-look &&
sdk media image \
  --input /samples/photo.insp \
  --output /work/first-look/panorama.jpg --width 1920 --height 960 \
  --stitch optflow --flowstate 1 --cuda 0 --accel cpu \
  --models /sdk/MediaSDK-3.1.5-20260819-linux64/models \
  --log-dir /work/first-look
```

Then [run the verifier and inspect the panorama](skills/insta360-sdk/references/runtime.md#stitch-and-check-one-photo). `/samples` maps to `originals/`, `/work` to `processed/`, and `/sdk` to the SDK root. Wrapper options such as `--timeout` go before `media`, `metadata`, `doctor` or `build`.

## Explore your panorama

The toolkit includes **Local 360**, a browser viewer for stitched equirectangular photos. Drag to look around, scroll to zoom, inspect the horizon and seams, or explore in fullscreen with auto-rotate.

```sh
python3 viewer/server.py
```

Open [localhost:8787](http://127.0.0.1:8787) and choose **Open photo**, or drop in a 2:1 JPEG, PNG or WebP panorama. The viewer starts empty; browser-selected photos stay on your device and are not uploaded. **No SDK, Docker or internet connection is needed to view an existing export.**

To open a freshly stitched JPEG directly:

```sh
python3 viewer/server.py --photo processed/first-look/panorama.jpg
```

Stop with **Ctrl+C**. The viewer ships in the repository and full source ZIP; the standalone skill ZIP contains the agent skill and SDK helpers. Read the [viewer guide](viewer/README.md) for shortcuts, multiple photos and format requirements. INSP/DNG originals need stitching first.

## What we verified

**Runtime testing is macOS only:** Apple Silicon host → Ubuntu 22.04 `linux/amd64` container → CPU/Mesa, CUDA off. This runs the Linux SDK on a Mac; it is not a native macOS SDK. The vendor's [desktop requirements](https://insta360develop.github.io/Insta360-Developer_Docs/en/x/desktop/guide/) list Windows/Linux and differ from this experimental setup.

| Capability | Observed result on the tested Mac setup |
|---|---|
| Single INSP stitching | Optical-flow, template and dynamic stitching produced nonblank panoramas |
| FlowState and HDR | Level output; a three-INSP HDR export was inspected at **6528×3264** |
| Colour and detail | All **11 setters**, ColorPlus and denoise executed and were compared with a baseline |
| Native metadata | All **9 parser methods** exercised; absent optional streams reported separately |
| Local 360 viewer | Drag, zoom, auto-rotate, fullscreen and local file loading; 12 server boundary tests |
| Distribution | **18 automated tests**, fresh installation, C++ compilation and a verified 960×480 stitch |
| AI stitching algorithm / direct DNG stitching | Failed acceptance in this runtime; do not rely on them |
| Video, realtime, CUDA, Intel Macs, native Linux/Windows | Not runtime-tested by this project |

AI-agent assistance and the SDK's optional **AI stitching algorithm** are separate capabilities. The latter returned an all-black JPEG during testing, which is why output verification is part of the workflow. Tested JPEGs also lacked embedded ICC/GPano markers; verify colour and panorama metadata when preparing a final delivery.

The references map **98 MediaSDK** and **11 MetadataSDK callable declarations**. API coverage is broader than executable support and verified output quality. Read the [SDK evidence and known limits](skills/insta360-sdk/references/verification.md) or the [distribution validation report](docs/validation.md) for details.

## Explore the toolkit

| Resource | What you'll find |
|---|---|
| [Agent skill](skills/insta360-sdk/SKILL.md) | Input decisions, processing workflow and verification guidance |
| [Local 360 viewer](viewer/README.md) | Explore stitched exports locally, without installing the SDK |
| [Runtime guide](skills/insta360-sdk/references/runtime.md) | SDK layout, Docker setup, CLI controls and troubleshooting |
| [MediaSDK reference](skills/insta360-sdk/references/media-sdk.md) | Functions, enums, callbacks and documented video/frame-export paths |
| [MetadataSDK reference](skills/insta360-sdk/references/metadata-sdk.md) | Gyro, GPS, exposure, timestamps and camera metadata APIs |
| [Photo-editing handoff](skills/insta360-sdk/references/photo-edit-handoff.md) | Preserve provenance and deliver a derivative to an editor |

## Help expand what is verified

Useful contributions include tests on additional camera models or hosts, reproducible stitching failures, and improvements to first-time setup. Include the host, SDK version, camera model, operation and expected result. Share only files you are permitted to publish; remove identifying metadata and private paths from issue reports.

For local development:

```sh
python3 tools/check_dist.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s viewer -p 'test_server.py' -v
python3 tools/package.py
```

Public files live at the repository root. Local SDKs, photos and logs are ignored; release archives use an explicit allowlist. See the [distribution guide](docs/distribution.md) for packaging and publication, and [launch settings](docs/launch.md) for the repository description, topics and social preview.

**Independent community project.** Not affiliated with or endorsed by Insta360. Original code and documentation are [MIT licensed](LICENSE); the SDK and other third-party materials retain their own terms. See [NOTICE.md](NOTICE.md).
