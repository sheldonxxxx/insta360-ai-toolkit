# InsMetaDataSDK 2.0.2 — saved-file metadata

## Scope and evidence

Source root: `sdk/InsMetaDataSDK-20260629_184813-2.0.2-linux64-default/` in the lab workspace. Locations below are relative to that directory. The complete public API has **11 explicit callable declarations**: constructor, destructor, and nine operations. It extracts telemetry and camera identity; it does not stitch, reframe, develop RAW, modify metadata, or write photographs. Use [MediaSDK](media-sdk.md) for postprocessing. No camera connection or CameraSDK is required.

The class comment says INSV, while the delivered `example/main.cc:5` explicitly names `.insv` **and `.insp`** and supplies an INSP usage example. Treat those as documented input families, and check `Parse` on each actual file. Do not promise support for generic JPEG, DNG, edited exports, or telemetry that the source never recorded. Header coverage is separate from runtime evidence; see the task's verification results for tested files and outcomes. The machine-readable declaration inventory and header hashes are in [metadata-api-inventory.json](metadata-api-inventory.json).

## Workflow

1. Retain the original file byte-for-byte. Parse a local copy or read-only path; metadata extraction does not need a rewritten image or upload to any service.
2. Construct a fresh `ins_metadata::MetaDataParser` for the file and call `Parse(path)`. If false, stop and report unsupported/unreadable/failed input as an unresolved cause; the bool alone does not distinguish those causes.
3. After successful parse, call each getter needed by the task. Start with empty vectors and record each getter's boolean **and** the resulting vector size. An empty stream is not the same as a failed getter, and neither proves that the photo is invalid. The header does not promise every stream exists on every capture.
4. Read camera model and firmware for processing decisions. Serial number is sensitive identifying metadata; the provided probe queries it to cover the function but omits it from output unless `--include-serial` is explicitly used. The probe does not export GPS coordinates.
5. Preserve native timestamp values and units in diagnostic data. Normalize or align timelines only after comparing the file's actual data with the required consumer's timing contract. Do not infer that GPS, gyro, exposure, first timestamp, and video presentation timestamps share one origin or unit.
6. Release the parser through normal C++ lifetime management. Reuse/thread safety are not documented; a fresh parser per input and serialized operations avoid assuming either contract. Metadata extraction is read-only with respect to the original, but the vendor example itself writes text files in the current directory.

## Complete public function index

All declarations are in `ins_metadata::MetaDataParser`, from `include/metaData.h`. Rows document the header, not runtime success.

| Declaration | Purpose and return semantics | Source |
| --- | --- | --- |
| `MetaDataParser();` | Create a parser. | `include/metaData.h:29` |
| `~MetaDataParser();` | Release its implementation through the declared destructor. | `include/metaData.h:30` |
| `bool Parse(const std::string& filePath);` | Parse the supplied local path; check bool before getters. | `include/metaData.h:37` |
| `bool GetGPSData(std::vector<GpsDataItem_t>& GpsData);` | Fill GPS records; bool is independent of vector emptiness. | `include/metaData.h:43` |
| `bool GetGyroData(std::vector<GyroDataItem_t>& GyroData);` | Fill acceleration and rotation records; check bool and count. | `include/metaData.h:49` |
| `bool GetExposureData(std::vector<ExposureDataItem_t>& ExposureData);` | Fill timestamp and shutter-seconds records; check bool and count. | `include/metaData.h:55` |
| `bool GetTimelapsePtsData(std::vector<RawTimelapseItem_t>& RawTimelapsePtsData);` | Fill raw timelapse frame/system timestamps; check bool and count. | `include/metaData.h:61` |
| `int64_t GetFirstTimeStamp() const;` | Read first timestamp used for gyro data; header explicitly says milliseconds. | `include/metaData.h:68` |
| `std::string GetFireWareVersion() const;` | Read firmware string. Preserve this exact misspelled method name. | `include/metaData.h:75` |
| `std::string GetCameraType() const;` | Read camera model/type string; do not cast it to another SDK enum without a mapping. | `include/metaData.h:82` |
| `std::string GetSerialNumber() const;` | Read serial string; omit from ordinary reports unless needed and authorized. | `include/metaData.h:89` |

The `GetFireWareVersion`, `GetCameraType`, and `GetSerialNumber` comments mistakenly say their return is milliseconds; their declarations return `std::string`. These scalar/string getters have no separate success flag, so retain empty values as observations rather than inventing success statuses.

## All public record types and units

Source: `include/common.h`. There are no public functions in that header.

| Type | Fields | Units/limits documented by source |
| --- | --- | --- |
| `ExposureDataItem_t` (`ExposureDataItem`, line 7) | `int64_t timestamp`; `double shutter_speed_s` | Timestamp milliseconds; shutter duration seconds. |
| `GpsDataItem_t` (`GpsDataItem`, line 14) | `int64_t timestampMs`; `double latitude`; `char north_south`; `double longitude`; `char east_west`; `double altitude` | **Timestamp conflict:** field name says Ms, comment says seconds. N/S and E/W direction characters are explicit. Angular/altitude units and coordinate reference system are not stated here; verify before route export or cross-library conversion. Preserve hemisphere information instead of silently treating all numeric coordinates as signed. |
| `GyroDataItem_t` (`GyroDataItem`, line 24) | `int64_t timestamp`; `double acceleration[3]`; `double rotation[3]` | Timestamp units, axes, signs, gravity handling, and sensor-unit scaling are not stated in this header. Do not assume degrees, radians, or SI acceleration. |
| `TimelapseQuatDataItem` (line 30) | `double timeStampS`; `double quat[4]` | Type is declared, but **no public getter returns it**. Timestamp naming suggests seconds but no comment defines it; quaternion element order is unspecified. Do not invent `GetTimelapseQuatData` or assume wxyz/xyzw. |
| `RawTimelapseItem_t` (`RawTimelapseItem`, line 35) | `int64_t timestamp` | System timestamp of the frame, milliseconds. |

`MetaDataParser::GetFirstTimeStamp` is explicitly milliseconds (`metaData.h:64`). That alone does not resolve the undocumented timestamp units or origins of the other streams.

## Read-only probe

Source: [metadata_probe.cc](../scripts/metadata_probe.cc). It exercises all nine public operations after constructing the parser; the destructor runs normally on exit. It redirects proprietary SDK stdout diagnostics to stderr for the complete parser lifetime, then prints a compact JSON summary to stdout and creates no output files of its own. This file-descriptor redirection uses Linux/POSIX APIs and is intended for the bundled Linux build. It records `parse_ok`, camera/firmware, first timestamp, and each vector getter's `ok`, count, first/last raw timestamps. Native `int64_t` timestamps are JSON strings to avoid precision loss in JavaScript. First/last refer to returned vector order; the probe does not sort or assert monotonicity.

Compile in a runtime matching the delivered **Linux x86_64** library, using that runtime's C++ toolchain and the SDK's own headers:

```sh
META_SDK=/absolute/path/to/InsMetaDataSDK-20260629_184813-2.0.2-linux64-default
c++ -std=c++17 -I"$META_SDK/include" /absolute/path/to/metadata_probe.cc \
  -L"$META_SDK/lib" -lInsMetaDataSDK -Wl,-rpath,"$META_SDK/lib" \
  -o /absolute/path/to/metadata_probe
/absolute/path/to/metadata_probe /absolute/path/to/input.insp
```

The Linux ELF shared library cannot be loaded directly into native macOS merely by changing an extension. Use the skill's verified runtime setup and mount the input read-only when practical. Keep SDK and platform selection explicit; do not claim that a containerized probe validates another platform build.

Exit statuses: 0 means `Parse` succeeded and the summary completed; 1 means parse failure or a caught C++ exception; 2 means incorrect usage. A successful exit **does not require every optional stream getter to succeed**. Read each `ok` field. `--include-serial` adds the serial field, but no option exports GPS coordinate arrays. Unknown native-library process failures/signals must be reported as such, not rewritten as empty metadata.

The vendor example calls these getters without checking each bool and writes `GpsData.txt`, `GyroData.txt`, `ExposureData.txt`, and `timelapseTimestampData.txt` when their vectors are nonempty. Its `findDuplicate` checks only adjacent gyro timestamps and returns an `int` despite timestamps being 64-bit. Use the probe for compact diagnostics; if building a full telemetry exporter, check bool results, preserve 64-bit time, choose explicit output paths, and define the timestamp/coordinate conversion from verified evidence.
