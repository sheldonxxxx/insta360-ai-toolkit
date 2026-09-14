# Verification and known limits

Date: 2026-09-12. Scope: saved-file postprocessing, **no CameraSDK**. This is evidence for one SDK build, runtime, camera family and sample set, not a promise that every indexed method works on every camera.

## API coverage

- MediaSDK 3.1.5: all **98 unique explicit public callable declarations** across three headers, including constructors/destructors, seven global functions, 26 ImageStitcher members, 41 VideoStitcher members, 19 RealTimeStitcher members and five CameraInfo members. Three duplicated global declarations were deduplicated. The realtime/calibration types are indexed for completeness, outside this toolkit's offline workflow.
- All **39 offline vendor-demo options**, public enums/records/callbacks, and notable example defects are mapped in [media-sdk.md](media-sdk.md) and [machine-readable inventory](media-api-inventory.json).
- InsMetaDataSDK 2.0.2: all **11 public declarations** (constructor/destructor plus nine operations), five public record types, source lines and hashes in [metadata-sdk.md](metadata-sdk.md) and [inventory](metadata-api-inventory.json).
- Source coverage is complete for these delivered public headers. Video/real-time execution and successful content for every optional metadata stream are not implied.

## Inputs and runtime

**SDK host testing covers Apple Silicon and native x86-64 Linux**, using Ubuntu 22.04 amd64 containers, plus separately unsuccessful native Debian 13 graphics trials. NVIDIA compute testing used an RTX 5060 Ti and driver 595.58.03; details below distinguish model compute from graphics and clean execution from valid pixels. Insta360 Studio 5.9.10 was tested as a separate native macOS application. Its exports do not establish native macOS SDK support.

Verification used native INSP single photos and exposure brackets, RAW companions, and flat-image controls. Original bytes were preserved and checksummed. Source identities and photographs are not part of this skill.

Pixel inspection established side-by-side fisheyes in INSP, vertically stacked fisheyes in One RS DNG and flat controls. Native One RS files use EXIF make `Arashi Vision`. A macOS sips DNG preview was black, whereas LibRaw decoded the RAW; therefore a failed preview path alone did not establish source damage.

The initial runtime was a macOS arm64 host, Ubuntu 22.04 **linux/amd64** container, MediaSDK 3.1.5 libraries/models and CPU/Mesa with CUDA disabled. The same container root filesystem/configuration and checksummed SDK/inputs were then used on x86-64 Linux. Executions were network-isolated and source/SDK mounts read-only; no X server was needed for the successful container runs. These observations do not supersede the vendor support matrix or qualify native macOS, ARM MediaSDK, WSL, Windows, Intel Macs or other cameras/drivers.

## Initial CPU/Mesa photo results

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
| AI stitching | SDK returned true and JPEG decoded, but **every pixel was black** without GPU exposure. The subsequent Linux controls below isolate the missing compute environment. |
| One RS DNG via direct ImageStitcher | FlowState-on call failed without output. A later FlowState-off call exited 0 and wrote a nonblank diagnostic texture after a CFA decoding failure; actual scene verification rejected it. Three-DNG HDR failed without output. Current official API guide lists DNG support, but this build/runtime did not establish a usable route. |
| `GetMediaFileInfo` on valid INSP | Returned true with zero dimensions and zero other fields. Helper reports unusable result (exit 5), avoiding false classification. |
| Metadata/colour tags | Tested SDK JPEGs have no embedded ICC and no `GPano` marker. These SDK exports require a verified downstream colour and projection-metadata handoff. |

All ImageStitcher members and seven global functions were called through the helper across `image`/`info` modes. Calls with default values do not validate every option combination or accessory enum. Other accessories/cameras, HDR counts other than three, native JPEG extension variants and missing-model fallback behavior remain unqualified.

## Native Linux and GPU controls

Controlled reruns used the same Ubuntu 22.04 image root filesystem/configuration, MediaSDK 3.1.5 libraries/models and seven checksummed One RS originals from one scene. The x86-64 Linux host exposed an **RTX 5060 Ti, driver 595.58.03**. Results distinguish SDK status, process exit, decoded pixels and actual scene correspondence:

| Control | Observed result |
|---|---|
| AI, no GPU exposure | `--cuda 0 --accel cpu` still selected the CUDA model backend; missing `libcuda.so.1` and flow estimator error 25 accompanied all-black output, despite exit 0 and SDK success. |
| AI, NVIDIA compute visible | All four combinations of `--cuda 0/1` and `--accel cpu/auto` produced byte-identical actual-scene images. MNN `RunSession` executed; GL remained Mesa/llvmpipe and CUDA texture loading was disabled. CPU options did not force CPU AI inference in this build. |
| SDK file logging omitted | The unchanged helper completed **4/4 CPU** INSP jobs and **5/5 GPU-visible** INSP/AI jobs with exit 0 and usable images. Their bytes matched corresponding file-logged runs that crashed during teardown. Capture stderr; omit `--log-dir` for the normal workflow. |
| Logging controls | Vendor demo without file logging completed **3/3** jobs cleanly. Two file-logged vendor runs created actual log files and ended once with exit 0, once with exit 139. A helper variant changing logging-call order still crashed **5/5** times. File logging is an observed crash trigger; the workaround does not establish the proprietary root cause or guarantee stability elsewhere. |
| INSP optical flow / HDR / denoise | Corresponding container outputs were byte-identical with and without NVIDIA compute visibility. Six full-resolution single-INSP repeats also matched. GPU access alone did not improve these pixels. |
| Native CFA DNG | Without SDK file logging, FlowState on exited 4 without output; FlowState off exited 0 with an unrelated diagnostic texture after CFA decode failure; three-DNG HDR exited 4 without output. Compute access did not qualify this route. |
| Native Debian 13 graphics | NVIDIA OpenGL/RTX renderer initialized, but rendering segfaulted before output, also with CUDA and SDK file logging disabled. Legacy `libtiff5`/`libjpeg8` dependencies came from the same image in an isolated library directory; host packages were unchanged. Different native libraries prevent attributing this solely to graphics. |

The container's full NVIDIA graphics-capability launch failed because `/dev/nvidia-modeset` was absent; that path remains unqualified. MediaInfo's zero fields reproduced under CPU/Mesa and were not compared across GPU profiles. One scene and one GPU/driver establish neither cross-camera compatibility nor a performance benchmark. Follow the [runtime procedure](runtime.md#stitch-and-check-one-photo) with a fresh output directory and separate stderr capture to reproduce the default route.

## RAW-derived and output-precision qualification

Studio 5.9.10 on macOS exported four matched One RS captures through Media → DNG import → Export 360 → DNG at **6528×3264**, spanning bright daylight, snow, a warm mixed-light interior and night. The exported representation is three-channel `LinearRaw` (PhotometricInterpretation 34892), unsigned sixteen-bit storage and per-channel WhiteLevel 16383. This establishes a stitched RAW-derived intermediate, not sixteen bits of original sensor precision. A RapidRAW build with corrected constant repeated BlackLevel handling rendered all four exported scenes correctly. Two focused regression tests cover equivalent per-channel collapse and preservation of spatially varying black levels. Native rendering correctness and photographic preference remain separate judgments.

PureShot on the interior produced a separate DNG and JPEG. Its DNG sample array differed from the disabled export, so it is a distinct processing treatment. Sample changes alone do not establish denoise quality or artistic preference.

Each of the four matched scenes was subsequently edited through native RapidRAW on both the stitched DNG and single-INSP JPEG routes, with full-resolution sRGB JPEGs, saved sessions and recipes. A night RAW denoise child and its untreated parent were also preserved. Independent overview and native-detail review found a processing tradeoff: the INSP night rendition was cleaner but smoother, while the RAW rendition retained stronger texture and more coloured noise; the tested BM3D treatment reduced noise only modestly. The interior RAW rendition offered more restrained warmth. These observations do not establish a universal RAW winner or recover source motion blur.

One actual stitched DNG was developed to RGB16 TIFF, reframed to a 2000×1333 RGB16 TIFF, and finished in a separate native RapidRAW session with verified sRGB JPEG and 16-bit TIFF exports. Source and reframe ICC bytes matched; an independent nine-point geometry/interpolation check matched exactly and fine sample distinctions survived the reframe. The flat output had no GPano fields. Its explicit JPEG control was not independently edited, so this establishes a working precision-preserving branch rather than an isolated aesthetic advantage over eight-bit editing.

A direct SDK DNG probe with FlowState disabled logged unsupported CFA `PhotometricInterpretation=32803` and failed image loading, yet exited 0 with a nonblank 960×480 diagnostic texture. A qualified three-DNG HDR probe failed frame parsing without an output. These results require checking source-loading diagnostics and actual scene correspondence in addition to decode, dimensions and blank-image tests.

An isolated copy of the still helper changed only output-suffix validation to admit PNG. Single INSP input produced actual opaque RGBA **eight-bit** PNG at review resolution and at 6528×3264; no still-image bit-depth selector was established. The shipped helper remains JPEG-only. Matched full-size JPEG and PNG exports used identical source and stitching options, and clean retries produced the same bytes as earlier exit134/139 teardown failures. Native-resolution inspection found very close appearance; PNG avoided another JPEG encoding step but demonstrated no recovery of RAW latitude. A separate three-INSP HDR result had modest differences from the matched single frame in inspected regions and must remain labelled as exposure fusion.

Reproduce the Studio path with your own paired originals using [runtime.md](runtime.md#studio-full-sphere-dng-export). Record version, export/PureShot settings, source/output hashes, decoded representation and the RAW editor's actual render. Do not convert camera CFA data to arbitrary RGB and assume its calibration survived.

## Metadata runtime results

All nine methods ran after successful INSP parse. The single INSP returned model/firmware/first timestamp and 1,424 gyro samples. The first bracket frame returned 1,792 gyro samples; the two subsequent bracket frames parsed but had no gyro stream. GPS, exposure and timelapse getters returned false/empty on the tested files. Those absent streams are reported separately from parse success. Native DNG and exported flat JPEG failed metadata parsing, as recorded; the exported JPEG is still a valid ordinary photo.

`metadata_probe` stdout parsed as JSON for all six success/failure inputs, with SDK diagnostics isolated to stderr. Serial getter was exercised but identifying output was omitted. Successful GPS/exposure/timelapse extraction and timestamp-unit conversions remain unverified because the sample files lack those streams.

## Reproduction and review

Use [runtime.md](runtime.md) to rebuild and run the helpers. Keep input hashes, options, logs, pixel measurements and visual review notes in each new job directory outside the skill.

The helper rejects source duplicates, invalid two-frame input, invalid ranges, template/fusion combination, and existing output entries. `verify_image.py` rejects the actual all-black AI result. Skill structural validation checks packaging; the full API inventory is checked against supplied header source locations and SHA-256 hashes. These checks complement pixel review and do not replace it.

A full-resolution three-INSP HDR export at **6528×3264** decoded correctly and was visually inspected. The extracted-package smoke test also produced a level **960×480** single-photo panorama; see the [distribution validation](https://github.com/sheldonxxxx/insta360-ai-toolkit/blob/main/docs/validation.md).

The default procedure uses a fresh job directory, captures stderr and requires a successful process exit before image verification. This prevents stale files from passing validation after a failed rerun. Optional `SetLogPath` accepts an explicit filename in this build despite the header's directory description, but omitting SDK file logging is the qualified default because of the teardown failures described above. Direct SDK DNG stitching remains unaccepted; Studio photo DNG export is qualified separately. Video and realtime execution remain unverified.

## Full-sphere and rectilinear handoff qualification

Seven scene groups were subsequently stitched at 6528×3264 with clean process exits, including an exposure-qualified three-INSP HDR group. Two first attempts returned `ok:true` and created decodable JPEGs before exiting 134 during native teardown with heap-corruption diagnostics. Fresh bounded retries completed with zero exit. Later matched controls identified optional SDK file logging as a trigger and qualified stderr-only runs. Those controls do not establish the proprietary root cause or erase the earlier runtime failures.

Three proposed single-frame companions failed FlowState because their native gyro data were unavailable. Other members of each capture group contained gyro and stitched successfully with FlowState still enabled. This establishes the need for per-frame stream qualification; it does not establish that every bracket companion or arbitrary same-time group is interchangeable.

A downstream RapidRAW 1.2 export reported embedded and verified sRGB. GPano annotation preserved its ICC and compressed JPEG scan while writing full/cropped dimensions matching the actual 6528×3264 output. The resulting HDR scene was opened in a shared spherical reviewer: matched baseline and edited viewpoints, the unobstructed longitude seam and nadir were visually inspected. This verifies the handoff on that output, not the absence of all source stitching defects or photographer acceptance.

Across both delivery branches, fourteen final JPEGs passed full decode, intended dimensions, readable embedded sRGB ICC profiles and editor-session lineage checks. The seven full spheres retained exact 6528×3264 GPano geometry and unchanged compressed scan/ICC bytes from their editor exports; the seven rectilinear outputs had no GPano properties and matched their editor export bytes. Registered review media returned the same final bytes. All 41 preserved originals matched acquisition and suite hashes and recorded server checksums, with no sidecars or added files in their original directories. These integrity results do not establish the original SDK JPEG colour encoding, source stitching perfection or photographer acceptance.

The source repository's `tests/test_sphere_photo.py` covers the four cardinal directions, exact longitude wrap blending, both poles, horizontal FOV and pitch direction, deterministic JPEG reframing, ICC preservation, unchanged compressed scan bytes during annotation, stale GPano dimensions, and rejection of unsafe geometry, colour-mode assumptions and overwritten outputs. RGB16 tests additionally cover sub-eight-bit distinctions, seam/pole sampling, ICC preservation, planar big-endian and LZW TIFF input, explicit eight-bit conversion and rejection of RAW/float/alpha/multipage inputs. From the source repository root, run this test module in a Pillow/NumPy/tifffile/imagecodecs environment (the tests are not included in the standalone installed skill):

```sh
python3 -m unittest discover -s tests -p test_sphere_photo.py -v
```

These are generated-fixture geometry and delivery checks. Actual output selection and photographic editing remain image-specific and require the [handoff procedure](photo-edit-handoff.md).
