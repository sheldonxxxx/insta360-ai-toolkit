# Input qualification

## Identify camera originals

Use user-supplied local originals. Check `.insp` files and same-capture `.dng` companions. Native camera metadata may use make `Arashi Vision` rather than `Insta360`; camera branding alone does not establish projection.

Keep one native single photo, a complete native exposure bracket when available, its RAW companions, and one ordinary exported JPEG as a format-routing control. Search the shared capture basename to find bracket members and companions; do not assemble brackets from unrelated photographs. Check timestamps, filename sequence, camera, dimensions, exposure time and ISO. Count, filename proximity and repeated timestamps alone do not qualify an HDR group; require actual exposure evidence and consistent capture geometry. Keep each capture group together, and let native metadata inform the SDK's interpretation.

## Preserve source bytes

Preserve original bytes, extensions, basenames, EXIF, native trailers and companion pairing. Work from copies and record source hashes and capture grouping in a job manifest outside the skill. If obtaining files from a storage service, use its original-file capability rather than thumbnails or previews, and verify any supplied checksum. Storage integrations and authentication belong to the user's chosen workflow, not this SDK skill.

## Classify from both metadata and pixels

| Source | Qualification | Processing route |
|---|---|---|
| Native `.insp` | Camera metadata plus genuine dual fisheye pixels and preserved native trailer | MediaSDK still stitching |
| Camera-native JPEG | Verify native camera metadata and the actual projection; extension alone is insufficient | MediaSDK only when the installed SDK accepts that camera-native source |
| One RS camera `.dng` | RAW companion can store two fisheye circles vertically, with dimensions reversed from its INSP | Preserve paired originals; use the verified Studio full-sphere DNG export route. Direct SDK DNG failed acceptance. |
| Studio-exported `.dng` | Inspect decoded geometry and DNG tags; tested exports are stitched, three-channel LinearRaw rather than camera CFA | Develop through a qualified RAW editor before display or RGB reprojection. Retain Studio export settings. |
| Ace Pro `.dng` | Single flat camera view, despite the Insta360 brand | Ordinary RAW editing route; do not force panoramic stitching |
| Exported/reframed JPEG | Cropped flat view or already stitched panorama; may still say `Insta360` in EXIF | Normal photo editing or a separate panorama/reframing route; do not treat as original dual fisheye |

A 2:1 aspect ratio does not prove an equirectangular panorama. An observed native INSP is 6528×3264 and contains two side-by-side fisheye circles. Its same-capture DNG is 3264×6528 and contains vertically stacked circles. Inspect source pixels before selecting stitch or reframe operations. Copying an INSP to JPEG through a generic image encoder discards the native trailer and is suitable only for viewing a preview, never for making an SDK source.

## Match RAW and INSP comparisons

Match the exact capture and frame basename, camera, ISO and exposure. Library/import timestamps may differ between companions, so timestamp equality alone is not a reliable pairing rule. Keep each original byte-identical. If Studio needs companion discovery, place isolated copies with their original basenames together and hash them before and after use. Import the DNG as the selected source; keeping its INSP companion alongside is not the same as passing both files as two SDK HDR inputs.

Record whether a result is single-frame, HDR fusion or PureShot. For a format comparison, use one DNG and its exact single INSP companion. A complete three-frame INSP HDR merge is a separate method with additional exposures. Studio PureShot changed the exported LinearRaw sample values in a tested interior; retain on/off exports separately rather than treating its DNG as an unchanged baseline.

## Qualify gyro per frame

Run MetadataSDK on every native frame proposed for single-image FlowState processing. Parse success and camera identity do not imply a usable gyro stream. Some bracket companions have no gyro while another member carries it; the tested runtime rejected FlowState on such companions. Preserve the whole group and select a gyro-bearing member only after checking its exposure and intended use. A complete, exposure-qualified HDR group is a different route from treating an arbitrary companion as a single photo. Do not hide missing gyro by disabling stabilization without documenting and reviewing the resulting orientation.

## Verify the input set

Confirm the originals decode through an appropriate reader, inspect at least one image per representation, and keep viewing derivatives clearly separate from processing originals. Generic system RAW rendering can return a black image without useful source pixels; this is a decoder failure, not evidence of a black or corrupt original. The observed One RS and Ace Pro DNGs decoded through LibRaw, while macOS `sips` produced black previews with gain-map warnings.

Input qualification proves provenance and representation only. Successful stitching, horizon/FlowState behavior, seam quality, HDR alignment, RAW colour accuracy, and final edit quality each require their own rendered-output verification.
