# Handoff to AI photo editing

Keep a reproducible lineage: original identity and checksum → qualified native capture group → Studio version/export settings or MediaSDK version/models/settings → stitched derivative → chosen representation and viewpoint → editor session or sidecar → final export and verification. Native `.insp` is a JPEG container with an extra trailer; a generic re-encode can discard calibration or gyro data needed for stitching.

## Use with your editor or Lightweft

This handoff works independently with a suitable photo editor. [Lightweft](https://github.com/sheldonxxxx/lightweft) is an optional workspace for editing direction, personal style and shared review. The independent [RapidRAW fork](https://github.com/sheldonxxxx/RapidRAW) is the tested native editor for the recorded handoffs and provides optional MCP control. Install and qualify each companion using its own repository; this toolkit installs neither.

The instructions below describe the required image and export properties. RapidRAW examples are a tested implementation of that contract; another editor needs equivalent output verification.

## Choose the representation

| Source | Next step |
|---|---|
| Native INSP dual fisheye | Qualify native metadata per frame; stitch and apply FlowState when supported; merge only a verified exposure bracket. |
| Native 360 DNG | Preserve paired originals; import the DNG in Studio and use Export 360 → DNG. Direct One RS SDK DNG stitching failed acceptance. |
| Studio full-sphere DNG | Verify LinearRaw geometry/calibration, develop through a qualified RAW editor, then retain the sphere or export developed RGB16 for a flat reframe. |
| Flat Ace Pro DNG | Ordinary RAW editing; camera brand does not imply a spherical source. |
| Stitched full-sphere RGB JPEG/TIFF | Branch to a geometry-preserving 360 edit or a deliberate rectilinear reframe; retain sixteen-bit TIFF precision when present. |
| Flat exported JPEG | Ordinary photo editing; absence of a native trailer is expected. |

Choose the image-specific purpose before moving sliders; use Lightweft's optional `photo-edit-master` skill when installed. For a sphere, attend to the full horizon and the experience of looking around. For a flat photograph, explore the available directions, identify the strongest subject relationship, and choose yaw, pitch, field of view and aspect ratio together. A centre crop of an equirectangular image is not a perspective photograph.

## Studio DNG to a developed editing master

Use the [Studio export procedure](runtime.md#studio-full-sphere-dng-export) for the native RAW-derived route. Preserve the exported LinearRaw DNG separately from both its camera original and any later RGB export. A DNG extension does not establish an untouched sensor mosaic: tested Studio exports contain already stitched three-channel linear data in sixteen-bit storage with nominal WhiteLevel 16383.

Qualify the RAW editor on that DNG before grading. An all-white render can be a black/white-level normalization failure, not an overexposed source. A tested RapidRAW decoder required correct handling of a spatially repeated constant per-channel DNG BlackLevel grid; after that fix the scene rendered. Verify the installed build through actual pixels rather than reducing exposure to compensate for failed preprocessing. That decode result alone does not qualify every RAW scene or final edit.

For a full-sphere finish, edit the verified DNG in the native editor and preserve the complete domain. For a flat branch, develop to a colour-managed RGB16 TIFF, verify its actual sample depth and profile, then reproject it before the final flat-image treatment. The sphere helper rejects DNG input, including Studio LinearRaw, because it performs reprojection only and does not apply RAW calibration. A generic TIFF reader is useful for inspecting stored DNG samples but is not a substitute for colour-aware RAW development.

For method comparisons, keep a matched single-INSP baseline, a Studio DNG baseline, and any PureShot or HDR versions separately labelled. Studio and SDK may differ in orientation or stitch geometry even at equal dimensions. Start with side-by-side review and unconfirmed alignment; establish registration before pixel-aligned difference or divider judgments.

## Keep the edited result spherical

Open an isolated stitched derivative in your editor. With RapidRAW, follow its installed `rapidraw-mcp` procedure and verify the available MCP capabilities. Start with restrained tonal and colour changes. Preserve the complete 360 by 180 degree domain and exact 2:1 pixel dimensions; normal crop, perspective correction, straightening and rotated rectangular output can break the projection. Disable inherited lens distortion, vignetting and chromatic-aberration corrections intended for an unstitched lens image unless their behavior on the stitched sphere is independently qualified. Full-sphere rotation requires a spherical operation, not an ordinary flat-image rotation.

Inspect edits around the longitude boundary, horizon, zenith and nadir, including local masks, gradients, denoise and detail effects. Inspect the seam unobstructed in a single-image view or move the comparison divider away from it. An operation exposed as a global adjustment can still use spatial neighborhoods. Unequal treatment of the two longitude edges can create a new seam. Masks from fisheye inputs, another stitch orientation, or a rectilinear view do not transfer automatically. Defer scene-specific retouching to a reframe unless its spherical boundary behavior has been verified.

Save the editor session and export to a new path. Confirm the editor's actual colour-profile result and decode the exported file. If the active workspace provides a shared review application, publish both baseline and candidate through its registered manifest/API and use its spherical panel. Keep the unedited stitch, intermediate editor export and final tagged delivery distinct.

## Choose and export a normal photograph

MediaSDK 3.1.5 exposes output dimensions but no public perspective camera, yaw, pitch or FOV operation. The included [sphere helper](../scripts/sphere_photo.py) implements a separate deterministic reprojection; it does not call an undocumented SDK API.

Use Pillow and NumPy for JPEG, plus tifffile and imagecodecs for RGB TIFF. `uv run` resolves the helper's declared dependencies; an existing Python environment can install them with `python3 -m pip install Pillow numpy tifffile imagecodecs`. Paths below are placeholders for your own verified exports:

```sh
python3 "$INSTA360_SKILL/scripts/sphere_photo.py" reframe \
  processed/stitched.jpg processed/selected-view.jpg \
  --yaw 35 --pitch -5 --hfov 75 --width 1200 --height 800 \
  --receipt processed/selected-view.json
```

For a verified developed RGB16 panorama, preserve its precision explicitly:

```sh
uv run "$INSTA360_SKILL/scripts/sphere_photo.py" reframe \
  processed/developed-sphere.tif processed/selected-view.tif \
  --yaw 35 --pitch -5 --hfov 75 --width 1200 --height 800 \
  --output-format tiff16 --receipt processed/selected-view.json
```

This writes lossless Deflate RGB16 TIFF and preserves the embedded ICC profile. Sixteen-bit input requires an explicit format choice: `tiff16` retains sample precision, while `jpeg` deliberately reduces the result to eight bits for delivery. Expanding an eight-bit source to TIFF16 adds no source information. Read the receipt's source/output bit depth and reduction flag rather than inferring precision from the extension.

Yaw zero faces the panorama centre; positive yaw turns right and positive pitch looks up. `hfov` is horizontal field of view in degrees. Choose dimensions from the available source pixels and intended use; the example is not a resolution prescription. The receipt reports the source's equatorial pixel span across that FOV and the output-to-source-span ratio. Sampling density varies with projection and latitude, so output dimensions never prove added detail.

The helper uses pixel-centred rays and float64 bilinear interpolation with longitude wrapping and latitude clamping. It interpolates source-encoded RGB values without a colour-space conversion or transfer-function change. It preserves an existing ICC profile and strips source EXIF/XMP, including spherical tags that would misidentify the flat result. It does not add an ICC profile to an untagged source. Reframe input must be developed RGB. TIFF accepts one three-channel unsigned eight- or sixteen-bit image, including separate planes; RAW/DNG, float, alpha, multiple pages/subimages and unnormalized orientation are rejected. Sixteen-bit RGB PNG is rejected rather than silently reduced by Pillow; use developed RGB16 TIFF. Explicitly convert and verify other colour modes first. Full-sphere input must be visually confirmed and exactly 2:1; the helper rejects unnormalized EXIF orientation and existing output or receipt paths.

Inspect the rectilinear export before editing: horizon, subject position, edge stretching, near-object stitching and source-detail limits. Export alternate seam and pole viewpoints when testing coverage; they are inspection samples, not automatically meaningful compositions. Open the selected flat export in your editor, perform the photographic finish, save its session or sidecar and verify the final output as an ordinary photo.

## Verify full-sphere delivery metadata

SDK JPEGs tested here lacked both ICC and GPano markers. The absence of ICC leaves colour interpretation unestablished; use a verified editor conversion/export and record any input colour assumption. SDK colour control integers do not translate into another editor's exposure stops, Kelvin or detail settings.

After the final 360 editor export passes decode and visual review, author fresh full-sphere GPano metadata without recompressing the JPEG:

```sh
python3 "$INSTA360_SKILL/scripts/sphere_photo.py" annotate \
  processed/edited-sphere.jpg processed/delivered-sphere.jpg \
  --receipt processed/delivered-sphere.json
python3 "$INSTA360_SKILL/scripts/sphere_photo.py" verify \
  processed/delivered-sphere.jpg
```

The helper writes full and cropped dimensions from the actual decoded 2:1 image, with zero crop offsets, the equirectangular projection and panorama-viewer flag. It preserves compressed image data, ICC and other JPEG segments; unrelated ordinary XMP fields remain present. Existing pose fields are retained, while unknown compass orientation is never invented. Extended XMP is explicitly unsupported and must be normalized through a suitable metadata editor first. The [Google GPano specification](https://developers.google.com/streetview/spherical-metadata) defines the required geometry fields.

`verify` parses actual XMP properties and compares them with decoded dimensions. A `GPano` substring, a 2:1 ratio, or a successful decoder alone is insufficient. Passing metadata checks still requires spherical viewer inspection of the actual final bytes. Preserve process exits, SDK logs, input/output hashes, editor recipes, colour-profile evidence, selected angles and remaining visual defects alongside the deliverables.
