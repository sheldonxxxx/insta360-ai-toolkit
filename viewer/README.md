# Local 360 viewer

Explore a stitched panorama from inside the sphere. Drag to look around, scroll to zoom, switch to fullscreen, or let auto-rotate take you around the scene.

From the repository root, with Python 3.10+:

```sh
python3 viewer/server.py
```

Open [the viewer](http://127.0.0.1:8787), then choose **Open photo** or drop in a stitched 2:1 equirectangular JPEG, PNG or WebP. Photos selected in the browser stay in memory on your device; they are not uploaded or copied. The viewer starts empty and does not scan local folders for photos.

To preload a JPEG export explicitly:

```sh
python3 viewer/server.py --photo processed/first-look/panorama.jpg
```

Repeat `--photo` to preload multiple JPEG panoramas, then switch between them with **Photos**. Preloaded photos are served only at their assigned local media URLs. Use `--port 8788` if the default port is busy. Stop with **Ctrl+C**.

The viewer runs independently of the SDK: **no SDK approval, Docker, build step or internet connection is needed to view an existing panorama.** It ships in the full source repository/archive. The standalone skill ZIP contains the agent skill and SDK helpers.

| Action | Control |
|---|---|
| Look around | Drag or arrow keys |
| Zoom | Scroll, pinch, slider, or + / − |
| Auto-rotate | Play button or Space |
| Reset view | Reset button, R, or double-click |
| Fullscreen | Fullscreen button or F |

Use a WebGL-capable browser. Very large images may be scaled for display to fit the device's graphics limits. Fullscreen availability depends on the browser. A 2:1 aspect ratio alone does not establish the correct projection: supply a full-sphere equirectangular export, not unstitched fisheyes. INSP/DNG/INSV originals need processing first.

The standard-library server binds only to `127.0.0.1` and exposes only viewer assets and JPEGs explicitly passed with `--photo`. It provides no uploads, directory listing or arbitrary-file endpoint. The viewer does not edit photos or write projection/colour metadata. Runtime testing so far is on macOS only.

```sh
python3 -m unittest discover -s viewer -p 'test_server.py' -v
node --check viewer/app.js
```
