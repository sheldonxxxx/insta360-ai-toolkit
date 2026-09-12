# Handoff to AI photo editing

The geometry step is distinct from the photographic finish. Keep one lineage: Source file and original hash → native input group → MediaSDK version/models/settings → stitched derivative → editor session/sidecar → final output. A result is reproducible only if the inputs, orientation, dimensions, algorithm and enhancements are retained. Native `.insp` is a JPEG container with extra calibration/gyro metadata; a generic re-encode can destroy the information needed for stitching.

## Choose the representation

| Source | Useful next step |
|---|---|
| Native INSP dual fisheye | SDK stitch/FlowState and, when qualified, HDR merge; then inspect output. |
| Native 360 DNG | Preserve paired INSP and RAW. Current guide lists DNG support, but lab One RS DNG failed in ImageStitcher. Do not assume external RAW development preserves the SDK calibration/geometry. Use a separately verified RAW stitching route or the verified paired-INSP path and disclose which was used. |
| Flat Ace Pro DNG | Ordinary RAW editor such as RapidRAW; no panoramic stitching just because it is Insta360-branded. |
| Stitched equirectangular JPEG | Can be globally graded; keep full-sphere geometry if delivering 360. |
| Flat exported JPEG | Ordinary photo-edit workflow; missing native trailer does not make the photo invalid. |

For an ordinary perspective photograph, first choose yaw/pitch/FOV in a separate spherical reprojection tool or Insta360 Studio, then do local masks/retouch/crop in the photo editor. MediaSDK 3.1.5 has no public yaw, pitch, roll, FOV, little-planet, perspective camera, keyframe, or interactive viewer controls. Do not confuse `SetOutputSize` with reframing. If another tool performs reprojection, identify it as that tool's operation and verify the resulting view. Native source pixels stay preserved.

For a full 360 panorama, local masks and texture operations can create a seam at longitude ±180° and unusual behaviour near poles. Avoid cropping away the sphere; preserve 2:1 geometry and inspect left/right boundary continuity using a spherical viewer or wrap-aware comparison. Masks and coordinates from the fisheye input or an old projection do not transfer to the stitched or reframed image.

## Editing and delivery

Use the installed editor's current capabilities and adjustment schema, then inspect its baseline. SDK control values are not transferable slider presets: SDK exposure [-100,100] is not RapidRAW exposure stops; warmth is not Kelvin; definition is not a calibrated sharpening amount. Avoid stacking ColorPlus, contrast, saturation and sharpening without checking for clipped colours, halos or lost texture.

The SDK output tested here was 8-bit JPEG, with no embedded ICC profile and no `GPano` marker. That does not establish the actual working colour space or all metadata contents. Do not label an untagged file as colour-managed solely from its extension. Use a verified downstream colour conversion/export, keep requested EXIF/projection fields on derived outputs, and inspect the actual final viewer. For full spheres, correctly authored GPano metadata should describe the current full/cropped panorama dimensions and projection; never copy stale crop dimensions from another file.

With RapidRAW MCP, open an isolated derivative, render and inspect, make the requested edits, save the editor's native session/sidecar, export using a verified supported colour profile, and inspect the exported image. Follow the current `rapidraw-mcp` skill for its API/revision semantics. This task did not run a RapidRAW edit or prove a spherical-viewer integration; those are separate future delivery steps.
