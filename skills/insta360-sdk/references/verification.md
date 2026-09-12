# Verification and known limits

Date: 2026-09-12. Scope: saved-file postprocessing, **no CameraSDK**. This is evidence for one SDK build, runtime, camera family and sample set, not a promise that every indexed method works on every camera.

## API coverage

- MediaSDK 3.1.5: all **98 unique explicit public callable declarations** across three headers, including constructors/destructors, seven global functions, 26 ImageStitcher members, 41 VideoStitcher members, 19 RealTimeStitcher members and five CameraInfo members. Three duplicated global declarations were deduplicated. The realtime/calibration types are indexed for completeness, outside the requested offline workflow.
- All **39 offline vendor-demo options**, public enums/records/callbacks, and notable example defects are mapped in [media-sdk.md](media-sdk.md) and [machine-readable inventory](media-api-inventory.json).
- InsMetaDataSDK 2.0.2: all **11 public declarations** (constructor/destructor plus nine operations), five public record types, source lines and hashes in [metadata-sdk.md](metadata-sdk.md) and [inventory](metadata-api-inventory.json).
- Source coverage is complete for these delivered public headers. Video/real-time execution and successful content for every optional metadata stream are not implied.

## Inputs and runtime

**Host testing is macOS only (Apple Silicon).** The Linux SDK ran inside Docker; native Linux, Windows, Intel Macs and CUDA are untested.

Verification used native INSP single photos and exposure brackets, RAW companions, and flat-image controls. Original bytes were preserved and checksummed. Source identities and photographs are not part of this skill.

Pixel inspection established side-by-side fisheyes in INSP, vertically stacked fisheyes in One RS DNG and flat controls. Native One RS files use EXIF make `Arashi Vision`. A macOS sips DNG preview was black, whereas LibRaw decoded the RAW; therefore a failed preview path alone did not establish source damage.

Runtime: macOS arm64 host, Docker Linux, Ubuntu 22.04 **linux/amd64** image, supplied MediaSDK 3.1.5 libs/models, CPU image acceleration, CUDA disabled, Mesa/EGL dependency stack. Network disabled for every SDK execution; SDK and source mounts read-only. No X server was needed for the successful runs. These observations do not supersede the vendor's supported-platform matrix or validate native macOS, CUDA, discrete GPU, ARM MediaSDK, WSL, or all cameras.

## Actual photo results

The controlled matrix used 1920×960 JPEG review exports and preserved per-case inputs, flags, return code, duration, SDK logs, output hash and pixel measurements. Across 21 cases, 19 produced nonuniform decoded images, one produced an all-black image, and one produced no image. Contact sheets and individual baseline exports were visually inspected.

| Operation | Observed result |
|---|---|
| Optical-flow single INSP | Native image stitched successfully. With default FlowState off, orientation was sideways; FlowState on produced a level panorama. |
| Template / dynamic stitching | Both produced nonblank panoramas with measurable pixel differences. Template used the explicit C++ enum, bypassing the demo parser defect. |
| Three-INSP HDR | Produced stitched, level output. Logs include `RunHDR3`, alignment and motion-removal stages. Inputs were qualified as one capture, not a random batch. |
| All 11 colour/detail setters | Each tested separately at +35 against the same FlowState baseline; every output decoded and differed in pixels. This confirms operation, not that +35 is an appropriate preset. |
| ColorPlus | Model initialized on CPU; materially different output, stronger contrast/saturation visible. |
| Denoise | `jpg_denoise` model initialized on CPU; nonblank changed pixels. Bright low-ISO sample does not establish high-ISO denoise quality. |
| Stitch fusion | Output produced, small measurable seam changes; template incompatibility blocked by helper. |
| Cooling-shell detection | Output byte-identical to baseline; source/profile reports no cooling case. Actual accessory-removal effectiveness untested. |
| AI stitching | SDK returned true and JPEG decoded, but **every pixel was black**. Failed visual/structural acceptance. Logs include unknown AI-flow version diagnostics; exact cause unresolved. |
| One RS DNG via direct ImageStitcher | `Stitch()` returned false, no output. Current official API guide lists DNG support; this sample/build/runtime combination failed. |
| `GetMediaFileInfo` on valid INSP | Returned true with zero dimensions and zero other fields. Helper reports unusable result (exit 5), avoiding false classification. |
| Metadata/colour tags | Tested SDK JPEGs have no embedded ICC and no `GPano` marker. No downstream colour-managed/spherical-viewer delivery is claimed. |

All ImageStitcher members and seven global functions were called through the helper across `image`/`info` modes; explicit log-path smoke receipts are retained separately from the 21-case matrix. Calls with default values do not validate every option combination or accessory enum. Examples of untested routes: CUDA on, auto accelerator behaviour, other accessories/cameras, HDR counts other than three, native JPEG extension variants, successful DNG stitching, missing-model fallbacks and GPU AI stitching.

## Metadata runtime results

All nine methods ran after successful INSP parse. The single INSP returned model/firmware/first timestamp and 1,424 gyro samples. The first bracket frame returned 1,792 gyro samples; the two subsequent bracket frames parsed but had no gyro stream. GPS, exposure and timelapse getters returned false/empty on the tested files. Those absent streams are reported separately from parse success. Native DNG and exported flat JPEG failed metadata parsing, as recorded; the exported JPEG is still a valid ordinary photo.

`metadata_probe` stdout parsed as JSON for all six success/failure inputs, with SDK diagnostics isolated to stderr. Serial getter was exercised but identifying output was omitted. Successful GPS/exposure/timelapse extraction and timestamp-unit conversions remain unverified because the sample files lack those streams.

## Reproduction and review

Use [runtime.md](runtime.md) to rebuild and run the helpers. Keep input hashes, options, logs, pixel measurements and visual review notes in each new job directory outside the skill.

The helper rejects source duplicates, invalid two-frame input, invalid ranges, template/fusion combination, and existing output entries. `verify_image.py` rejects the actual all-black AI result. Skill structural validation checks packaging; the full API inventory is checked against supplied header source locations and SHA-256 hashes. These checks complement pixel review and do not replace it.

A separate full-resolution three-INSP HDR export at **6528×3264** decoded correctly and was visually inspected. An independent agent followed the skill to produce and inspect a level **960×480** single-photo panorama. Its review found a real logging discrepancy: the header describes `SetLogPath` as a directory, but passing a directory produces `open log file err`. The helper was corrected to pass a new explicit `media-sdk.log` filename and this was retested separately. Captured stderr is preserved alongside native SDK logs.

Independent review also corrected the command working directory and example retry semantics. The example now requires a fresh job directory before opening any receipts and only verifies an image after the stitch succeeds, preventing stale-output validation on a failed rerun. No downstream RapidRAW edit, native DNG stitch, video/real-time run, or spherical-viewer delivery was performed in this task.
