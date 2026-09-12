# Viewer verification

Tested on macOS only. The public source archive was extracted into a fresh directory and exercised locally on 2026-09-12 with temporary loopback servers and a temporary Chrome profile.

## Public distribution checks

- Twelve server tests passed: explicit photo catalogue/media bytes, MIME and HEAD behaviour, loopback binding, empty start, JPEG dimensions, static routes, invalid preloads, and rejection of traversal, symlink replacement and uploads.
- JavaScript syntax check passed with `node --check viewer/app.js`.
- Empty startup displayed the file picker and hid the unused Photos control. No personal sample catalogue or automatic directory discovery is included.
- The browser file picker loaded a full-resolution 6528×3264 stitched JPEG and displayed a perspective view from inside the sphere.
- Keyboard navigation changed heading; zoom changed field of view; reset restored the initial view; auto-rotate advanced the heading and could be paused.
- An explicit `--photo` JPEG preload loaded automatically and exposed the Photos control. No other photos appeared in the catalogue.
- A 390×844 viewport had no page overflow. No JavaScript page errors occurred in the checked flows.
- Test servers stopped after verification. No private photographs or screenshots are included in the repository or release archive.

## Earlier interaction checks

The same renderer's earlier macOS browser checks covered dragging, mouse wheel, fullscreen entry/exit, a non-2:1 image error that preserved the current panorama, help layout at 667×375 and a delayed catalogue response that did not replace an already chosen local file. GPU context loss/recovery and physical two-finger touch are implemented but were not exercised on touch hardware.

The server exposes viewer assets and only JPEGs explicitly chosen with `--photo`. Browser file selections use blob URLs and have no upload endpoint, external asset dependency or remote processing. INSP/DNG inputs require a stitched derivative. The viewer does not edit source photos or write projection/colour metadata.
