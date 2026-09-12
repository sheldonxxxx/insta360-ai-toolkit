# Input qualification

## Identify camera originals

Use user-supplied local originals. Check `.insp` files and same-capture `.dng` companions. Native camera metadata may use make `Arashi Vision` rather than `Insta360`; camera branding alone does not establish projection.

Keep one native single photo, a complete native exposure bracket when available, its RAW companions, and one ordinary exported JPEG as a format-routing control. Search the shared capture basename to find bracket members and companions; do not assemble brackets from unrelated photographs. Check timestamps, filename sequence, camera, dimensions, exposure time and ISO. Keep each capture group together, and let native metadata inform the SDK's interpretation.

## Preserve source bytes

Preserve original bytes, extensions, basenames, EXIF, native trailers and companion pairing. Work from copies and record source hashes and capture grouping in a job manifest outside the skill. If obtaining files from a storage service, use its original-file capability rather than thumbnails or previews, and verify any supplied checksum. Storage integrations and authentication belong to the user's chosen workflow, not this SDK skill.

## Classify from both metadata and pixels

| Source | Qualification | Processing route |
|---|---|---|
| Native `.insp` | Camera metadata plus genuine dual fisheye pixels and preserved native trailer | MediaSDK still stitching |
| Camera-native JPEG | Verify native camera metadata and the actual projection; extension alone is insufficient | MediaSDK only when the installed SDK accepts that camera-native source |
| One RS `.dng` | RAW companion can store two fisheye circles vertically, with dimensions reversed from its INSP | Preserve RAW and use a separately verified RAW development route; direct DNG is not established for this skill's still helper |
| Ace Pro `.dng` | Single flat camera view, despite the Insta360 brand | Ordinary RAW editing route; do not force panoramic stitching |
| Exported/reframed JPEG | Cropped flat view or already stitched panorama; may still say `Insta360` in EXIF | Normal photo editing or a separate panorama/reframing route; do not treat as original dual fisheye |

A 2:1 aspect ratio does not prove an equirectangular panorama. An observed native INSP is 6528×3264 and contains two side-by-side fisheye circles. Its same-capture DNG is 3264×6528 and contains vertically stacked circles. Inspect source pixels before selecting stitch or reframe operations. Copying an INSP to JPEG through a generic image encoder discards the native trailer and is suitable only for viewing a preview, never for making an SDK source.

## Verify the input set

Confirm the originals decode through an appropriate reader, inspect at least one image per representation, and keep viewing derivatives clearly separate from processing originals. Generic system RAW rendering can return a black image without useful source pixels; this is a decoder failure, not evidence of a black or corrupt original. The observed One RS and Ace Pro DNGs decoded through LibRaw, while macOS `sips` produced black previews with gain-map warnings.

Input qualification proves provenance and representation only. Successful stitching, horizon/FlowState behavior, seam quality, HDR alignment, RAW colour accuracy, and final edit quality each require their own rendered-output verification.
