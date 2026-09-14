# MediaSDK 3.1.5 complete public API reference

Scope: the three public C++ headers and both examples in `MediaSDK-3.1.5-20260819-linux64`, reviewed 2026-09-12 and reconciled with the [official MediaSDK guide](https://github.com/Insta360Develop/Insta360-Developer_Docs/blob/main/docs/en/sdk/x-ace-go/desktop/media.md). This is a source-reviewed capability inventory; it does not assert runtime success. Check the [verification reference](verification.md) for executed cases. The executable workflow is **offline postprocessing**: CameraSDK/capture is excluded; realtime MediaSDK signatures are indexed only for completeness.

Coverage: **98 unique public callable declarations**, including constructors/destructors and CameraInfo copy/assignment; **39 offline demo options**. Duplicate environment declarations in offline/realtime headers are merged. Exact signatures, line references, enum values, and source hashes are in [media-api-inventory.json](media-api-inventory.json). Source paths are relative to the supplied SDK root, so locate them in the user's installed archive.

## Operation routing

| Task | Route | Boundary |
|---|---|---|
| Stitch a native photo | `ImageStitcher` → synchronous `Stitch()` | Native camera geometry/metadata required; demo routes `.insp` and `.jpg`. |
| Stitch video | `VideoStitcher` → callbacks → async `StartStitch()` | Demo routes `.insv`, `.mp4`, `.lrv`; keep lens pairs together. |
| Extract stitched video frames | Video stitcher + image sequence + optional zero-based indices | JPEG/PNG; no indices can write the entire video. |
| Inspect capture properties | `GetMediaFileInfo()` | Type, dimensions, frame rate, bitrate, duration only. |
| Stabilize/lock horizon | FlowState; direction lock for video/live | Needs source gyro; no arbitrary yaw/pitch/FOV controls. |
| Realtime MediaSDK methods | Inventory only | Reference only; no capture operations in this toolkit. |
| Grade/enhance | 11 global controls; ColorPlus/denoise; other enhancements by class | Global operations; no masks, retouch, LUT, or adjustment keyframes. |
| Reframe/view/export perspective crops | Separate downstream software | This release exposes no reframe/projection/playback API. |
| DNG/HDR photo processing | C++ `ImageStitcher`; one input or >=3 established bracket members | Documented support; consult validation results for tested source cases. Exactly two photo inputs invalid. |
| PureShot | No explicit processing control | Classification enum does not establish a PureShot processing API. |

The official guide documents **DNG/JPEG/INSP** input, but the stock executable dispatches only `.insp` and `.jpg` for stills (`example/main.cc:721`); use a C++ wrapper to test native `.dng`/`.jpeg`, preserving the original extension. Exactly **two still inputs are invalid**; **three or more are automatically treated as HDR**. Group only confirmed members of the same bracketed capture, never a random batch. X4 default HDR is already fused in-camera into a single file. Video vectors contain at most two files: older >=5.7K material often needs both components; X4/X5/X4 Air/X6 store both lens tracks in one file. These are [documented input rules](https://github.com/Insta360Develop/Insta360-Developer_Docs/blob/main/docs/en/sdk/x-ace-go/desktop/media.md#common-parameters-apply-to-both-videostitcher-and-imagestitcher), and each camera/source case needs runtime verification.

## Linux runtime, model files, and initialization

The package is **Linux amd64**, not a macOS or arm64 binary. Debian metadata reports approximately 11.3 GiB installed. Its declared dependencies are `libx11-6, libgomp1, libxcb1, libpng16-16, libgl1, libglx0, libglvnd0, libegl1, libjpeg-turbo8, libxdmcp6, libbsd0, libxau6, libmd0, libxext6, libvulkan1, libglfw3, libdc1394-dev, libopenblas0`. The GL/EGL/GLX/Vulkan/X11 requirements remain relevant when requesting software acceleration. A container or emulation can satisfy architecture only when its libraries and rendering stack also work; do not equate `-disable_cuda` with a proven headless CPU pipeline.

The bundled README installs under `/opt/MediaSDK-3.1.5-linux/` and says runtime RPATH is embedded. The official guide targets Ubuntu 22.04 x64, NVIDIA driver >=470 and no WSL; CUDA runtime/MNN/OpenCV are bundled. For development it lists GCC >=11, CUDA Toolkit 11.7 and Conan 2. The guide claims system GL/X11 dependencies are bundled whereas Debian control declares them as dependencies; trust loader inspection and observed runtime requirements. Multi-GPU use requires a separate process per GPU (`ins_stitcher.h:18–21`). A macOS-hosted amd64 VM/emulation is an experimental runtime outside that stated platform matrix.

Call `InitEnv()` once, configure log level/path, set model root with a **trailing `/`**, then construct/configure a stitcher. The header requires initialization before other calls even though the offline demo gets version/sets log level first. The README says absent models cause a warning and feature skip; validate the actual effect. A requested flag is not evidence that a model ran.

| Bundled asset | Relevant operation |
|---|---|
| `ai_stitcher.ins` | AI stitching |
| `colorplus_model.ins` | ColorPlus |
| `jpg_denoise_9d006262.ins` | Official guide: actual photo inference model; video uses file presence as a gate, then built-in denoise configuration |
| `deflicker_86ccba0d.ins` | Deflicker |
| `defringe_hr_dynamic_7b56e80f.ins`, `defringe_air_hr_dynamic_6fbc2886.ins` | Camera-specific defringe assets |
| `cameraaccessory/*.xml`, `coolingshell/*.xml` | Accessory and cooling-shell profiles |

Asset names establish inventory, not a guarantee of camera compatibility. SDK selects appropriate profiles internally.

## Complete function index

Defaults below are identified as header defaults or demo defaults. Unspecified constructor defaults, valid ranges, error details, and support matrices must be queried/tested rather than invented. Source paths and line numbers identify files under the supplied SDK root.

### ins

| Signature | Use / constraints | Source |
|---|---|---|
| `std::string GetVersion();` | Return the full SDK version string; log it with the run. | `include/ins_common.h:241` |
| `int GetVersionMajor();` | Return SDK major version for compatibility checks. | `include/ins_common.h:243` |
| `void InitEnv();` | Initialize once before SDK work. Header requires this before other SDK calls; demo contradicts this for version/log setup. | `include/ins_realtime_stitcher.h:27`; `include/ins_stitcher.h:27` |
| `void SetLogPath(const std::string& log_path);` | Set logging destination. Header says directory; demo passes a full file path after making its parent. Verify logs were written. | `include/ins_realtime_stitcher.h:33`; `include/ins_stitcher.h:33` |
| `void SetLogLevel(InsLogLevel level);` | Choose VERBOSE/INFO/WARNING/ERR/FATAL. Demo default ERR; use INFO to see degradation warnings. | `include/ins_realtime_stitcher.h:39`; `include/ins_stitcher.h:39` |
| `void SetModelFileRootDir(const std::string& root_dir);` | Point to bundled model root with a trailing slash. Default demo location: models/ beside executable. Missing models may skip features. | `include/ins_stitcher.h:46` |
| `bool GetMediaFileInfo(const std::vector<std::string>& file_paths, MediaFileInfo& info);` | Parse input path vector into MediaFileInfo; validate both bool AND fields. The tested INSP probe returned true with all-zero dimensions/type/rate/duration; unusable photo properties require metadata/EXIF fallback. No demo CLI query. | `include/ins_stitcher.h:54` |

### ins::CameraInfo

| Signature | Use / constraints | Source |
|---|---|---|
| `CameraInfo();` | Construct/copy/assign owned camera description. | `include/ins_common.h:197` |
| `~CameraInfo();` | Construct/copy/assign owned camera description. | `include/ins_common.h:198` |
| `CameraInfo(const CameraInfo&);` | Construct/copy/assign owned camera description. | `include/ins_common.h:199` |
| `CameraInfo& operator=(const CameraInfo&);` | Construct/copy/assign owned camera description. | `include/ins_common.h:200` |
| `void SetCalibration(const std::vector<std::string>& offsets, uint32_t src_width, uint32_t src_height, uint32_t dst_width, uint32_t dst_height, int32_t crop_offset_x, int32_t crop_offset_y);` | Copy opaque lens offsets and crop source/destination dimensions and offsets from CameraSDK preview metadata; do not invent calibration. | `include/ins_common.h:209` |

### ins::ImageStitcher

| Signature | Use / constraints | Source |
|---|---|---|
| `ImageStitcher();` | Construct stitcher / release owned resources on destruction. | `include/ins_stitcher.h:329` |
| `~ImageStitcher() = default;` | Construct stitcher / release owned resources on destruction. | `include/ins_stitcher.h:330` |
| `void SetInputPath(const std::vector<std::string>& input_paths);` | Use one logical capture. Official guide: photos accept one or >=3 originals (>=3 implies HDR fusion), never exactly 2; establish bracket membership first. Video at most 2 files: older >=5.7K is dual-file, X4/X5/X4 Air/X6 contain both tracks in one file. | `include/ins_stitcher.h:337` |
| `void SetOutputPath(const std::string& output_path);` | Set a new output file including extension; preserve originals. Official guide specifies .jpg stills and .mp4 video. IMAGE_TYPE PNG/JPEG controls video frame sequences, not still output; test other still extensions before relying on them. | `include/ins_stitcher.h:342` |
| `void SetOutputSize(int width, int height);` | Require explicit positive 2:1 width:height; official guide says SDK does not enforce ratio and other ratios distort panoramas. Video/realtime header defaults source size; offline demo overrides to 1920x960, realtime demo 960x480. | `include/ins_stitcher.h:347` |
| `void EnableFlowState(bool enable);` | Enable gyro-driven FlowState; documented default off. Realtime needs synchronized gyro samples; validate horizon visually. | `include/ins_stitcher.h:353` |
| `void EnableColorPlus(bool enable, float strength = 0.3f);` | Enable model-based automatic color enhancement; default off. Official guide strength range 0–1; C++ defaults image 0.3, video 1.0. CLI has no strength flag. | `include/ins_stitcher.h:360` |
| `void EnableDenoise(bool enable);` | Enable denoise; default off. A toggle does not promise arbitrary strength controls or PureShot/HDR merging. | `include/ins_stitcher.h:366` |
| `void SetStitchType(STITCH_TYPE type);` | Choose TEMPLATE, OPTFLOW, DYNAMICSTITCH, or AIFLOW. AI needs models. Demo default OPTFLOW; its template option is broken (no parser branch). Use C++ TEMPLATE directly. | `include/ins_stitcher.h:376` |
| `void EnableCuda(bool enable);` | Toggle CUDA stitching acceleration. Offline demo defaults true. False plus CPU image processing is a fallback request, not proof of a GPU-free runtime. | `include/ins_stitcher.h:382` |
| `void SetImageProcessingAccelType(ImageProcessingAccel type);` | Select kAuto (0) or kCPU (1). Demo defaults auto. Independent from CUDA and codec settings. | `include/ins_stitcher.h:388` |
| `void EnableStitchFusion(bool enable);` | Enable seam fusion; default off and unsupported with TEMPLATE. | `include/ins_stitcher.h:394` |
| `void EnableCoolingShellDetection(bool enable);` | Enable camera cooling-shell detection; default off. Official guide limits support to X4 Air/X5/X6; other cameras auto-skip. Models required. | `include/ins_stitcher.h:400` |
| `void SetCameraAccessoryType(CameraAccessoryType type);` | Choose exact CameraAccessoryType from metadata/known physical accessory. Demo defaults kNormal (0); use -1 for auto-detection rather than assume bare lenses. | `include/ins_stitcher.h:405` |
| `bool Stitch();` | Run image stitching synchronously and check returned bool. Stock demo discards the bool, so inspect logs and decode a nonempty new output. | `include/ins_stitcher.h:410` |
| `void SetExposure(int exposure);` | Set global exposure integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:416` |
| `void SetHighlights(int highlights);` | Set global highlights integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:422` |
| `void SetShadows(int shadows);` | Set global shadows integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:428` |
| `void SetContrast(int contrast);` | Set global contrast integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:434` |
| `void SetBrightness(int brightness);` | Set global brightness integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:440` |
| `void SetBlackpoint(int blackpoint);` | Set global blackpoint integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:446` |
| `void SetSaturation(int saturation);` | Set global saturation integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:452` |
| `void SetVibrance(int vibrance);` | Set global vibrance integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:458` |
| `void SetWarmth(int warmth);` | Set global warmth integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:464` |
| `void SetTint(int tint);` | Set global tint integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:470` |
| `void SetDefinition(int definition);` | Set global detail/definition integer in [0,100]; demo default 0 and clamps input. No negative values or local controls. | `include/ins_stitcher.h:476` |

### ins::VideoStitcher

| Signature | Use / constraints | Source |
|---|---|---|
| `VideoStitcher();` | Construct stitcher / release owned resources on destruction. | `include/ins_stitcher.h:62` |
| `~VideoStitcher() = default;` | Construct stitcher / release owned resources on destruction. | `include/ins_stitcher.h:67` |
| `void SetInputPath(const std::vector<std::string>& input_paths);` | Use one logical capture. Official guide: photos accept one or >=3 originals (>=3 implies HDR fusion), never exactly 2; establish bracket membership first. Video at most 2 files: older >=5.7K is dual-file, X4/X5/X4 Air/X6 contain both tracks in one file. | `include/ins_stitcher.h:80` |
| `void SetStabDataOutputPath(const std::string& file_path);` | Export stabilization data to a file. Format and downstream reader are unspecified; no demo CLI flag. | `include/ins_stitcher.h:85` |
| `void SetImageSequenceInfo(const std::string& output_dir, IMAGE_TYPE image_type);` | Set existing directory (no filename) and JPEG/PNG for video frame export; overrides video output path. Official guide says all-frame files use frame timestamps in milliseconds. | `include/ins_stitcher.h:92` |
| `void SetExportFrameSequence(const std::vector<uint64_t>& vec);` | Select zero-based video frame indices. Demo accepts a hyphen-separated list, not a range; omission means all frames. Official guide says selected-frame filenames use the frame index. | `include/ins_stitcher.h:98` |
| `void EnableCuda(bool enable);` | Toggle CUDA stitching acceleration. Offline demo defaults true. False plus CPU image processing is a fallback request, not proof of a GPU-free runtime. | `include/ins_stitcher.h:104` |
| `void SetOutputPath(const std::string& output_path);` | Set a new output file including extension; preserve originals. Official guide specifies .jpg stills and .mp4 video. IMAGE_TYPE PNG/JPEG controls video frame sequences, not still output; test other still extensions before relying on them. | `include/ins_stitcher.h:109` |
| `void SetOutputBitRate(int64_t bitRate);` | Set output bitrate in bits/second. API int64_t; demo uses int/atoi and defaults to 0, meaning match source. | `include/ins_stitcher.h:114` |
| `void SetOutputSize(int width, int height);` | Require explicit positive 2:1 width:height; official guide says SDK does not enforce ratio and other ratios distort panoramas. Video/realtime header defaults source size; offline demo overrides to 1920x960, realtime demo 960x480. | `include/ins_stitcher.h:119` |
| `void EnableFlowState(bool enable);` | Enable gyro-driven FlowState; documented default off. Realtime needs synchronized gyro samples; validate horizon visually. | `include/ins_stitcher.h:125` |
| `void EnableDirectionLock(bool enable);` | Lock direction while FlowState is enabled. Documented video default off; enable FlowState first. | `include/ins_stitcher.h:132` |
| `void EnableStitchFusion(bool enable);` | Enable seam fusion; default off and unsupported with TEMPLATE. | `include/ins_stitcher.h:138` |
| `void EnableCoolingShellDetection(bool enable);` | Enable camera cooling-shell detection; default off. Official guide limits support to X4 Air/X5/X6; other cameras auto-skip. Models required. | `include/ins_stitcher.h:144` |
| `void EnableDenoise(bool enable);` | Enable denoise; default off. A toggle does not promise arbitrary strength controls or PureShot/HDR merging. | `include/ins_stitcher.h:150` |
| `void EnableColorPlus(bool enable, float strength = 1.0f);` | Enable model-based automatic color enhancement; default off. Official guide strength range 0–1; C++ defaults image 0.3, video 1.0. CLI has no strength flag. | `include/ins_stitcher.h:158` |
| `void EnableH265Encoder(bool enable);` | Enable HEVC instead of default H.264. Official guide: H.264 output over 4096 in either dimension forces software encoding; H.265 retains hardware eligibility subject to device capabilities. | `include/ins_stitcher.h:164` |
| `void Enable10BitExport(bool enable);` | Request 10-bit video; default off. Needs 10-bit source, otherwise 8-bit warning fallback; 10-bit source/output selects H.265. Official guide says denoise/defringe/deflicker plus 10-bit source also enables 10-bit export automatically. | `include/ins_stitcher.h:177` |
| `void SetStitchType(STITCH_TYPE type);` | Choose TEMPLATE, OPTFLOW, DYNAMICSTITCH, or AIFLOW. AI needs models. Demo default OPTFLOW; its template option is broken (no parser branch). Use C++ TEMPLATE directly. | `include/ins_stitcher.h:187` |
| `void SetStitchProgressCallback(stitch_process_callback callback);` | Install callback before async start; progress 0–100. Synchronize callback state and object lifetime. | `include/ins_stitcher.h:194` |
| `void SetStitchStateCallback(stitch_error_callback callback);` | Install error/state callback before start; capture numeric code and nullable text. Do not treat a printed message or process exit 0 as success. | `include/ins_stitcher.h:201` |
| `void StartStitch();` | Start asynchronous video/realtime stitching after configuration and callbacks. Official guide: settings changed after starting have no effect. Keep objects alive; use timeout and terminal error/completion handling. | `include/ins_stitcher.h:206` |
| `bool CancelStitch();` | Cancel active work and check returned bool; ensure callbacks cannot outlive captured application state. | `include/ins_stitcher.h:211` |
| `int GetStitchProgress() const;` | Query stitching progress, 0–100; progress alone does not validate output content. | `include/ins_stitcher.h:216` |
| `std::map<std::string, int> GetFeatureStatusMap() const;` | After video run, record actual feature statuses: -1 unknown, 0 off, 1 on, 2 skipped(auto), 3 failed. Feature-key vocabulary is not declared; preserve returned keys. | `include/ins_stitcher.h:223` |
| `void SetCameraAccessoryType(CameraAccessoryType type);` | Choose exact CameraAccessoryType from metadata/known physical accessory. Demo defaults kNormal (0); use -1 for auto-detection rather than assume bare lenses. | `include/ins_stitcher.h:228` |
| `void EnableDeflicker(bool enable);` | Toggle deflicker on video/realtime. No still method or strength control. Offline demo default off. | `include/ins_stitcher.h:233` |
| `void SetSoftwareCodecUsage(bool enable_encoder, bool enable_decoder);` | Independent software encoder/decoder toggles. Demo defaults both false (prefer hardware); does not remove render-stack requirements. | `include/ins_stitcher.h:240` |
| `void SetImageProcessingAccelType(ImageProcessingAccel type);` | Select kAuto (0) or kCPU (1). Demo defaults auto. Independent from CUDA and codec settings. | `include/ins_stitcher.h:246` |
| `void EnableDefringe(bool enable);` | Toggle video/realtime defringe; no still method. Official guide supports X4 Air/X5/X6, but bundled demo help says X6 skipped: unresolved documentation conflict, so inspect actual feature status/logs. | `include/ins_stitcher.h:251` |
| `void SetExposure(int exposure);` | Set global exposure integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:257` |
| `void SetHighlights(int highlights);` | Set global highlights integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:263` |
| `void SetShadows(int shadows);` | Set global shadows integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:269` |
| `void SetContrast(int contrast);` | Set global contrast integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:275` |
| `void SetBrightness(int brightness);` | Set global brightness integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:281` |
| `void SetBlackpoint(int blackpoint);` | Set global blackpoint integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:287` |
| `void SetSaturation(int saturation);` | Set global saturation integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:293` |
| `void SetVibrance(int vibrance);` | Set global vibrance integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:299` |
| `void SetWarmth(int warmth);` | Set global warmth integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:305` |
| `void SetTint(int tint);` | Set global tint integer in [-100,100]; demo default 0 and clamps input. No per-mask/keyframe variant exposed. | `include/ins_stitcher.h:311` |
| `void SetDefinition(int definition);` | Set global detail/definition integer in [0,100]; demo default 0 and clamps input. No negative values or local controls. | `include/ins_stitcher.h:317` |

### ins::RealTimeStitcher

| Signature | Use / constraints | Source |
|---|---|---|
| `RealTimeStitcher();` | Construct stitcher / release owned resources on destruction. | `include/ins_realtime_stitcher.h:47` |
| `~RealTimeStitcher();` | Construct stitcher / release owned resources on destruction. | `include/ins_realtime_stitcher.h:52` |
| `void SetCameraAccessoryType(CameraAccessoryType type);` | Choose exact CameraAccessoryType from metadata/known physical accessory. Demo defaults kNormal (0); use -1 for auto-detection rather than assume bare lenses. | `include/ins_realtime_stitcher.h:58` |
| `void SetStitchType(STITCH_TYPE type);` | Choose TEMPLATE, OPTFLOW, DYNAMICSTITCH, or AIFLOW. AI needs models. Demo default OPTFLOW; its template option is broken (no parser branch). Use C++ TEMPLATE directly. | `include/ins_realtime_stitcher.h:68` |
| `void SetStitchStateCallback(stitch_error_callback callback);` | Install error/state callback before start; capture numeric code and nullable text. Do not treat a printed message or process exit 0 as success. | `include/ins_realtime_stitcher.h:75` |
| `void SetCameraInfo(const CameraInfo& cameraInfo);` | Provide camera model, codec, calibration/crop, and synchronization metadata before realtime start. | `include/ins_realtime_stitcher.h:81` |
| `void StartStitch();` | Start asynchronous video/realtime stitching after configuration and callbacks. Official guide: settings changed after starting have no effect. Keep objects alive; use timeout and terminal error/completion handling. | `include/ins_realtime_stitcher.h:86` |
| `bool CancelStitch();` | Cancel active work and check returned bool; ensure callbacks cannot outlive captured application state. | `include/ins_realtime_stitcher.h:91` |
| `void SetStitchRealTimeDataCallback(stitch_realtime_data_callback callback);` | Receive borrowed raw frame planes, per-plane strides, dimensions, FFmpeg-style pixel format, and microsecond timestamp. Respect format/stride and copy before returning if retaining. | `include/ins_realtime_stitcher.h:98` |
| `void SetOutputSize(int width, int height);` | Require explicit positive 2:1 width:height; official guide says SDK does not enforce ratio and other ratios distort panoramas. Video/realtime header defaults source size; offline demo overrides to 1920x960, realtime demo 960x480. | `include/ins_realtime_stitcher.h:103` |
| `void EnableFlowState(bool enable);` | Enable gyro-driven FlowState; documented default off. Realtime needs synchronized gyro samples; validate horizon visually. | `include/ins_realtime_stitcher.h:109` |
| `void EnableDirectionLock(bool enable);` | Lock direction while FlowState is enabled. Documented video default off; enable FlowState first. | `include/ins_realtime_stitcher.h:116` |
| `void SetVideoDelayMs(int video_delay_ms);` | Delay incoming video by milliseconds to align gyro data. No default/range exposed and no demo flag. | `include/ins_realtime_stitcher.h:122` |
| `void EnableDeflicker(bool enable);` | Toggle deflicker on video/realtime. No still method or strength control. Offline demo default off. | `include/ins_realtime_stitcher.h:127` |
| `void SetSoftwareCodecUsage(bool enable_encoder, bool enable_decoder);` | Independent software encoder/decoder toggles. Demo defaults both false (prefer hardware); does not remove render-stack requirements. | `include/ins_realtime_stitcher.h:134` |
| `void EnableDefringe(bool enable);` | Toggle video/realtime defringe; no still method. Official guide supports X4 Air/X5/X6, but bundled demo help says X6 skipped: unresolved documentation conflict, so inspect actual feature status/logs. | `include/ins_realtime_stitcher.h:139` |
| `void HandleVideoData(const uint8_t* data, size_t size, int64_t timestamp, uint8_t stream_type, int stream_index = 0);` | Forward encoded packet, byte count, microsecond timestamp, stream type, and lens stream index (default 0); preserve synchronization. | `include/ins_realtime_stitcher.h:149` |
| `void HandleGyroData(const std::vector<GyroData>& data);` | Forward GyroData samples with camera-clock microsecond timestamps and six-axis readings for FlowState; prefer field-by-field conversion across SDK versions. | `include/ins_realtime_stitcher.h:155` |
| `void HandleExposureData(const ExposureData& data);` | Forward camera-clock exposure timestamp (microseconds) and exposure duration (seconds). | `include/ins_realtime_stitcher.h:161` |

## Shared types and wire units

`stitch_process_callback`: `void(int process, int error)`, progress 0–100. `stitch_error_callback`: `void(int error, const char* errinfo)`, nullable text. `stitch_realtime_data_callback`: `void(uint8_t* data[4], int linesize[4], int width, int height, int format, int64_t timestamp)`, FFmpeg-style pixel format, byte strides, timestamp in microseconds. These buffers are borrowed; copy retained frame data before returning.

`GyroData`: `int64_t timestamp` in camera-clock microseconds; `double ax/ay/az` in m/s²; `double gx/gy/gz` in rad/s. `ExposureData`: double timestamp in microseconds and exposure duration in seconds. Do not confuse duration with packet/frame timestamps.

`CameraInfo`: `cameraName`; `decode_type` default H.264; `gyro_timestamp` and `sweep_timestamp` default 0, both microseconds. Calibration/crop internals are private; populate through `SetCalibration()`. `MediaFileInfo`: `media_type`, integer width/height, double fps, int64 bitrate in bits/s, int64 duration in milliseconds. Source: `ins_common.h:165–237`.

### Enumerations

**ins::STITCH_TYPE** — `include/ins_common.h:47`

`TEMPLATE=0`, `OPTFLOW=1`, `DYNAMICSTITCH=2`, `AIFLOW=3`.

**ins::IMAGE_TYPE** — `include/ins_common.h:57`

`JPEG=0`, `PNG=1`.

**ins::ImageProcessingAccel** — `include/ins_common.h:62`

`kAuto=0`, `kCPU=1`.

**ins::CameraAccessoryType** — `include/ins_common.h:68`

`kAutoDetect=-1`, `kNormal=0`, `kWaterproof=1`, `kOnerLensGuard=2`, `kOnerLensGuardPro=3`, `kOnex2LensGuard=4`, `kOnex2LensGuardPro=5`, `k283PanoLensGuardPro=6`, `kDiveCaseAir=7`, `kDiveCaseWater=8`, `kInvisibleDiveCaseAir=9`, `kInvisibleDiveCaseWater=10`, `kLensGuardA=11`, `kLensGuardS=12`, `kLensGuardAS=13`, `kOnex5ND16=14`, `kOnex5ND32=15`, `kOnex5ND64=16`, `kOner283LensGuardPro=17`, `kOnerLensGuardFpv=18`, `kOnex4AirDiveCaseAir=19`, `kOnex4AirDiveCaseWater=20`, `kUndetermined=100`.

**ins::InsLogLevel** — `include/ins_common.h:97`

`VERBOSE=0`, `INFO=1`, `WARNING=2`, `ERR=3`, `FATAL=4`.

**ins::SDKErrorCode** — `include/ins_common.h:108`

`E_SUCCESS=0`, `E_OPEN_FILE=1`, `E_PARSE_METADATA=2`, `E_CREATE_OFFSCREEN=3`, `E_CREATE_RENDER_MODEL=4`, `E_FRAME_PARSE=5`, `E_CREATE_RENDER_SOURCE=6`, `E_UPDATE_RENDER_SOURCE=7`, `E_RENDER_FRAME=8`, `E_SAVE_FRAME=9`, `E_VIDEO_FRAME_EXPORTOR=10`, `E_FILE_TYPE_UNSUPPORT=11`, `E_INTERNAL_ERROR=998`, `E_UNKNOWN=999`.

**ins::MediaFileType** — `include/ins_common.h:128`

`UNDEFINED=65535`, `VIDEO_NORMAL=0`, `VIDEO_BULLETTIME=1`, `VIDEO_TIMELAPSE=2`, `VIDEO_HDR=6`, `VIDEO_STATIC_TIMELAPSE=8`, `VIDEO_TIMESHIFT=9`, `VIDEO_SUPER_NORMAL=11`, `VIDEO_LOOPRECORDING=12`, `VIDEO_FPV=15`, `VIDEO_MOVIE=16`, `VIDEO_SLOWMOTION=17`, `VIDEO_SELFIE=18`, `VIDEO_PURE=20`, `VIDEO_STARLAPSE=21`, `VIDEO_DASH_CAM=23`, `VIDEO_VIR_PTZ=24`, `PHOTO_NORMAL=3`, `PHOTO_HDR=4`, `PHOTO_INTERVALSHOOTING=5`, `PHOTO_BURST=7`, `PHOTO_AEB_NIGHT_MODE=10`, `PHOTO_STARLAPSE=13`, `PHOTO_PANO_MODE=14`, `PHOTO_PURESHOTPLUS=19`, `PHOTO_STARTRAIL=22`.

**ins::VideoDecodeType** — `include/ins_common.h:161`

`kH264=0`, `kH265=1`.

`LOG_VERB`, `LOG_INFO`, `LOG_WARN`, `LOG_ERR`, and `LOG_FATAL` alias the matching `InsLogLevel`. `SDK_LOG` is a macro that expects an external `LOG` macro; it is not a standalone exported logger.

## Offline demo command reference

All boolean switches are presence-only: do not append `true`/`false`. Quote UTF-8 paths, use absolute input/output paths, validate numeric inputs yourself, and explicitly enforce **positive dimensions at 2:1**. The SDK does not enforce the panorama ratio and other ratios distort output. The demo silently ignores unknown switches/enum strings and `atoi` turns invalid numeric input into zero. `-camera_accessory_type -1` is accepted because it uses a value parser; do not treat negative adjustment values as independent switches.

| Option / arguments | Demo default | Applies to | Usage | Source |
|---|---|---|---|---|
| `-help` none | none | meta | Print options; does not exit immediately and absent input/output still returns -1. | `example/main.cc:613` |
| `-model_root_dir` directory ending / | <exe>/models/ | both | Global model directory; explicit paths are not normalized by the demo. | `example/main.cc:379` |
| `-inputs` one or more paths | required | both | One logical capture, including all required lens components. Paths beginning with - are unsafe for this parser; use absolute paths. | `example/main.cc:363` |
| `-output` new output path | required unless video frame directory | both | Still and video file output. | `example/main.cc:374` |
| `-stitch_type` template / optflow / dynamicstitch / aistitch | optflow | both | BUG: template has no parser branch and stays at existing setting (normally optflow). | `example/main.cc:391` |
| `-bitrate` integer bps | 0 (match video input) | video | Parsed with 32-bit int/atoi although API accepts int64_t. | `example/main.cc:464` |
| `-enable_flowstate` flag | off | both | Gyroscope stabilization. | `example/main.cc:418` |
| `-enable_directionlock` flag | off | video | Requires FlowState; ignored for still-image branch. | `example/main.cc:445` |
| `-output_size` WIDTHxHEIGHT | 1920x960 | both | Overrides SDK source-size default; validate positive dimensions before invocation. | `example/main.cc:469` |
| `-enable_stitchfusion` flag | off | both | Unsupported with actual TEMPLATE stitching. | `example/main.cc:429` |
| `-enable_denoise` flag | off | both | Denoise; source/camera/model-dependent. | `example/main.cc:434` |
| `-enable_colorplus` flag | off | both | C++ default strength 0.3 for stills and 1.0 for video; no CLI strength. | `example/main.cc:439` |
| `-enable_coolingshell` flag | off | both | Cooling-shell detection. | `example/main.cc:384` |
| `-enable_deflicker` flag | off | video | No corresponding ImageStitcher function. | `example/main.cc:509` |
| `-enable_defringe` flag | off | video | No corresponding ImageStitcher function; help says skipped for X6. | `example/main.cc:515` |
| `-image_sequence_dir` new directory | none | video | Video frame export; omit indices to export all, potentially many files. | `example/main.cc:479` |
| `-image_type` jpg / png | jpg | video | Applied only to video frame-sequence output, despite wider comment. | `example/main.cc:485` |
| `-export_frame_index` 0-20-50 (list) | all frames | video | Zero-based individual indices, not an inclusive range. | `example/main.cc:503` |
| `-camera_accessory_type` integer enum | 0 (bare camera) | both | Use known accessory or -1 auto-detect; parser performs no enum validation. | `example/main.cc:497` |
| `-enable_h265_encoder` flag | off / H.264 | video | Video HEVC output. | `example/main.cc:452` |
| `-enable_10bit` flag | off | video | Requires 10-bit source and H.265; source capability may downgrade. | `example/main.cc:459` |
| `-disable_cuda` flag | absent / CUDA enabled | both | Disables CUDA request; does not prove all GPU/render requirements removed. | `example/main.cc:424` |
| `-enable_soft_encode` flag | off | video | Force software video encoding. | `example/main.cc:522` |
| `-enable_soft_decode` flag | off | video | Force software video decoding. | `example/main.cc:525` |
| `-image_processing_accel` auto / cpu | auto | both | Independent from CUDA and software codecs. | `example/main.cc:407` |
| `--debug` flag | off | diagnostics | Sets log level VERBOSE; order matters relative to --log_level. | `example/main.cc:575` |
| `--log_level` verbose / info / warning / error / fatal | error | diagnostics | Case-insensitive; unknown value warns and leaves prior level. | `example/main.cc:582` |
| `--log_file` optional path | disabled | diagnostics | Optional file or directory; bare flag writes timestamped log under <exe>/logs/. | `example/main.cc:605` |
| `-exposure` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:529` |
| `-highlights` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:533` |
| `-shadows` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:537` |
| `-contrast` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:541` |
| `-brightness` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:545` |
| `-blackpoint` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:549` |
| `-saturation` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:553` |
| `-vibrance` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:557` |
| `-warmth` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:561` |
| `-tint` integer | 0 | both | Clamped to [-100,100]. | `example/main.cc:565` |
| `-definition` integer | 0 | both | Clamped to [0,100]. | `example/main.cc:569` |

### Example recipes (templates, not a record of tests)

Use the executable from the configured Linux environment and substitute absolute paths inside that environment. Create output directories first. Capture stderr and omit optional SDK file logging by default; the tested photo runtime showed teardown crashes with file logging enabled. See [runtime guidance](runtime.md#tested-platform). A small still baseline:

```sh
MediaSDKTest -inputs /work/samples/photo.insp \
  -output /work/outputs/photo-baseline.jpg -output_size 1920x960 \
  -stitch_type optflow -camera_accessory_type -1 \
  -disable_cuda -image_processing_accel cpu \
  -model_root_dir /opt/MediaSDK-3.1.5-linux/bin/models/ \
  --log_level info 2> /work/outputs/photo-baseline.log
```

Compare one change per candidate (FlowState, accessory choice, stitch type, denoise, ColorPlus). Increase to an explicit source-appropriate full panorama size only after the baseline decodes and seam/horizon/color have been inspected. For `TEMPLATE`, use the C++ API because the stock parser ignores that name.

Video frame export for a bounded contact sheet:

```sh
MediaSDKTest -inputs /work/samples/lens00.insv /work/samples/lens10.insv \
  -image_sequence_dir /work/outputs/frames -image_type png \
  -export_frame_index 0-30-90 -output_size 1920x960 \
  -enable_flowstate -enable_directionlock -camera_accessory_type -1 \
  -disable_cuda -image_processing_accel cpu -enable_soft_decode \
  -model_root_dir /opt/MediaSDK-3.1.5-linux/bin/models/ \
  --log_level info 2> /work/outputs/frames.log
```

For normal video use `-output new.mp4` instead of the image-sequence options; add software encode as needed. Use `-enable_h265_encoder -enable_10bit` only for a verified 10-bit source and inspect the actual output codec/pixel format. The API also exposes stabilization-data export, ColorPlus strength, cancellation, metadata queries, and live-packet APIs that have no CLI equivalents.

## Realtime bridge and example caveats

`RealTimeStitcher` accepts encoded packets, gyro/exposure samples, and opaque camera calibration, then emits raw panoramic frames. Its 19 callable declarations and CameraInfo support types are indexed above because they belong to MediaSDK. They are outside this skill's offline postprocessing execution path; do not discover/open/control cameras or start preview streams as part of this workflow.

These MediaSDK APIs are catalogued for completeness and do not activate camera capture. The bundled sample uses `DYNAMICSTITCH`, FlowState on and 960×480 stitched output (`realtime_stitcher_demo.cc:258–269`). Its interactive commands are `1` start, `2` stop, `0` quit; flags `--debug`, `--log_file <path>`. Those flags affect CameraSDK logging; despite its comment, `--debug` does not change MediaSDK logging. `--log_file` lacks a missing-value guard.

Do not copy the demo uncritically: its display callback assumes RGBA and ignores the supplied pixel-format and line-stride arguments; create correctly strided buffers and convert according to `format`. It uses `memcpy` between SDK gyro structs based on an assumed matching layout; prefer explicit fields or ABI checks. It picks the first camera rather than a deliberate device. It lacks a registered MediaSDK error callback, starts a display thread even if preview start failed, and final quit calls `Close()` without explicit `StopLiveStreaming()`/`CancelStitch()`. Other comments claim AIFLOW while actual code selects DYNAMICSTITCH. The provided sample is a demonstration, not production-safe playback or camera control.

## Error handling and verification

Numeric error codes: 0 success; 1 input open; 2 metadata parse; 3 offscreen target; 4 render model; 5 video frame parse; 6 render source creation; 7 upload/update source; 8 frame render; 9 save frame; 10 frame exporter; 11 unsupported file type; 998 internal; 999 unknown. Preserve code, description, inputs, SDK version, settings, model root, and runtime logs. For code 3/4/6/8 inspect render/display dependencies before changing photo settings. For 1/2/11 verify exact originals, complete component sets, and native metadata before retries.

Stock demo success hazards (`main.cc:618–642,721–755,855–907`): it discards the image `Stitch()` bool; video errors only wake the wait and still reach exit 0; unknown file extensions silently fall through to exit 0; `-help` does not exit immediately; frame-list/numeric validation is weak. Missing option values do exit 1, but that does not make runtime exit status reliable. Use a bounded timeout, inspect logs for failure/degradation, require a fresh nonempty file, decode it, confirm dimensions/codec/bit depth, then visually inspect seam, horizon, retained detail, halos, color, and geometry.

For video, save the actual feature map, including any skipped/failed entries. Check the `[Codec] encode=..., decode=..., format=...` log to distinguish requested from actual codec paths. Official automatic rules include H.264 above 4096 → software encoding, Windows dimensions <=360 → software encoding, and 10-bit source plus denoise/defringe/deflicker → automatic 10-bit export/H.265. The guide supports X6 defringe while the bundled help says it is skipped, so runtime evidence decides that case.

For stills no feature-status method exists: compare matched-geometry candidates and logs. `GetMediaFileInfo()` returned true with all-zero fields on the tested native INSP probe, so treat zero dimensions/type as unavailable and consult dedicated metadata/EXIF readers. Hash originals before/after and store only new outputs. Keep an explicit 2:1 full-sphere master for the downstream photo-editing/viewing workflow; a perspective crop is a derivative made by a separate tool.

## Explicit limits

- Coverage is all explicit public callable declarations in three headers shipped in this specific MediaSDK 3.1.5 linux64 archive, not every product called Insta360 SDK and not private exported symbols.
- The inventory records static source review only. Runtime evidence belongs to the [verification reference](verification.md) and must not be inferred from documentation coverage.
- Official guide documents DNG/JPEG/INSP photo input and automatic HDR fusion via >=3 photo SetInputPath entries. DNG and HDR support are documented through the image input contract; consult the validation report for executed cases. Stock demo routes only .insp/.jpg and therefore needs a C++ wrapper for DNG/.jpeg.
- No explicit public APIs here for RAW-development controls, PureShot processing, exposure-bracket discovery, local masks/retouch, LUTs, yaw/pitch/FOV keyframes, sphere-to-perspective reframing, little-planet projections, deep tracking, object removal, playback timeline, audio mixing, subtitles, or metadata writing.
- MediaFileType contains HDR/PureShot/night/starlapse classification values; only HDR has an additional documented input-vector behavior. Other enum names are not proof of processing modes.
- ImageStitcher does not expose GetFeatureStatusMap, callbacks, cancellation, defringe, deflicker, direction lock, codec controls, or a denoise strength.
- No documented image 10-bit export control, JPEG quality control, ICC profile selector, or bit-depth selector. Inspect actual exported file.
- No public SetAiStitchModelFile despite stale header comments mentioning it; use SetModelFileRootDir.
- No public GetFrameTimeStampsList: its declaration is commented out.
- SDK_LOG macro depends on an external LOG macro; LOG_VERB/INFO/WARN/ERR/FATAL are enum aliases, not callable SDK entry points.
