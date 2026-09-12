---
name: insta360-sdk
description: Postprocess saved Insta360 photos and videos with MediaSDK and inspect their native metadata. Use for INSP stitching, HDR brackets, FlowState, SDK colour/enhancement controls, video or frame export, and handoff to AI photo editing. Excludes CameraSDK and camera capture/control.
---

# Insta360 postprocessing

Turn preserved camera originals into verified stitched assets, then finish the requested photographic edit. This skill covers the supplied **MediaSDK 3.1.5** and **InsMetaDataSDK 2.0.2** public APIs. It does not operate cameras. All functions are indexed; runtime verification is narrower and explicitly recorded in [verification](references/verification.md).

**Runtime tested on macOS only:** Apple Silicon with the Linux x86-64 SDK in Docker, CPU/Mesa and CUDA disabled. No native macOS SDK is used. Native Linux, Windows, Intel Macs and GPU paths are untested by this project.

## Choose the relevant path

- **Find or qualify input:** [Originals and representation](references/inputs.md). Search `Arashi Vision` as well as `Insta360`; native files may use the former make. Use original bytes, not thumbnails, and record source identity/checksum.
- **Run a saved-photo workflow:** [runtime and helper commands](references/runtime.md), then the photo procedure below. Helpers use the user's locally supplied SDK; the skill does not distribute proprietary binaries or models.
- **Look up any SDK function, enum, callback, parameter, video export, or frame extraction:** [complete MediaSDK reference](references/media-sdk.md). Its realtime section is an API completeness reference, not a camera-control workflow.
- **Inspect native gyro, GPS, exposure, timestamps, model, or firmware:** [MetadataSDK reference](references/metadata-sdk.md). Parse success and optional stream presence are separate facts.
- **Finish in the AI photo editor:** [photo-edit handoff](references/photo-edit-handoff.md). Apply the available `photo-edit-master` for artistic direction and `rapidraw-mcp` for its supported editing operations when those are relevant and installed.

## Photo procedure

1. **Classify from pixels and metadata.** Distinguish native dual fisheye, stitched full-sphere equirectangular, flat reframe, and RAW. A 2:1 image can still contain two fisheye circles. Retain the native trailer, RAW companions, capture grouping, and original hashes. Do not stitch an ordinary flat JPEG just because its make says Insta360.
2. **Resolve prerequisites using current files.** Read the installed headers and helper/runtime version. Linux ELF cannot run natively on macOS. The tested Mac-hosted offline amd64 container has verified some CPU/Mesa paths; this is not vendor-supported emulation or CUDA qualification. `GetMediaFileInfo` returned true with zero fields for the tested INSP, so use decoded dimensions and MetadataSDK to corroborate it.
3. **Make a baseline.** Start with one native INSP, optical-flow stitching, automatic accessory detection, and explicit full-sphere output dimensions. Enable FlowState when source gyro and the desired horizon support it; compare orientation, rather than assuming default-off produces a level photo. Begin with a small review render, then export chosen settings at justified final resolution. Preserve the baseline and record exact inputs/options/runtime/output.
4. **Treat brackets deliberately.** Supply only distinct frames from the same capture with verified exposure variation and matching camera/geometry. One input means a single photo; exactly two is invalid; the current official API guide says three or more automatically invoke HDR fusion. Do not combine a RAW/JPEG pair as a bracket or send an unrelated batch in one call. The three-INSP bracket is tested. Some camera HDR files are already merged. DNG is documented as an API input but the tested One RS DNG failed; preserve it and report that boundary rather than converting it to an arbitrary JPEG and assuming calibration survives.
5. **Choose changes from the image.** Compare template/optical-flow/dynamic seams where relevant. All 11 global controls are available; their integers are SDK-relative, not exposure stops or Kelvin. ColorPlus and denoise need matching model files. Inspect effects before combining them. AI stitching produced an all-black JPEG on the tested runtime despite a true `Stitch()` result; treat it as failed here. Cooling-shell detection produced unchanged pixels on the tested bare-camera file, not a validated accessory correction.
6. **Verify bytes and pixels.** Check `Stitch()` or callback result, output existence, full decode, dimensions, blank pixels, and model logs. Run `verify_image.py`, then visually inspect the actual image, horizon, seams at both longitude boundaries, poles/nadir, faces/near objects, ghosting, highlights, noise and texture. A successful decoder or file size is insufficient. Matched comparisons require the same input, projection, orientation, and dimensions. For video, additionally check output duration, fps, codec/bit depth and audio and inspect representative frames; read the video workflow before running.
7. **Deliver or hand off.** Keep source files and sidecars unchanged. Pass an isolated stitched derivative to downstream editing with source/recipe provenance; preserve the source collection. Tested SDK JPEGs lacked embedded ICC and GPano markers: verify colour handling and projection metadata at the delivery boundary, and do not claim a spherical viewer or colour profile is correct just from the filename. Record incomplete features separately from accepted output.

## Execution details that matter

The supplied `media_tool.cc` calls every public `ImageStitcher` operation and all seven global MediaSDK functions across its `image` and `info` modes. It implements template selection directly, rejects duplicate inputs and existing output entries, and returns failure for false stitches/missing files or unusable media-info dimensions. Its JSON `ok` reports SDK/file completion, not visual approval; use [verify_image.py](scripts/verify_image.py) afterward. Do not run concurrent jobs targeting the same output path.

`metadata_probe.cc` calls all nine parser operations and reports each stream's boolean/count separately. Its JSON omits serial/GPS coordinate arrays by default, while preserving exact timestamp integers as strings. SDK diagnostics go to stderr. Use current source timestamps and types; the public metadata headers contain conflicting or absent unit descriptions.

Prefer explicit paths and a bounded process per job. On crash/timeout/partial output, inspect receipts/files first and choose a fresh output path for a retry. The native SDK has no durable photo job/session/undo protocol. Save recipes and results externally; do not invent RapidRAW-style revisions or masks for this SDK.
