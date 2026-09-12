#!/usr/bin/env python3
"""Serve the local 360 viewer and explicitly chosen JPEG panoramas on loopback only."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import struct
import sys
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    """Read a JPEG frame header without loading or decoding the image."""
    with path.open("rb") as image:
        if image.read(2) != b"\xff\xd8":
            raise ValueError("Not a JPEG")
        while True:
            if image.read(1) != b"\xff":
                raise ValueError("Missing JPEG frame header")
            marker = image.read(1)
            while marker == b"\xff":
                marker = image.read(1)
            if not marker or marker[0] in (0xD9, 0xDA):
                raise ValueError("Missing JPEG dimensions")
            if marker[0] in range(0xD0, 0xD9) or marker[0] == 0x01:
                continue
            raw_length = image.read(2)
            if len(raw_length) != 2:
                raise ValueError("Truncated JPEG segment")
            length = struct.unpack(">H", raw_length)[0]
            if length < 2:
                raise ValueError("Invalid JPEG segment")
            if marker[0] in SOF_MARKERS:
                frame = image.read(5)
                if length < 7 or len(frame) != 5:
                    raise ValueError("Truncated JPEG frame")
                height, width = struct.unpack(">HH", frame[1:])
                if width == 0 or height == 0:
                    raise ValueError("Invalid JPEG dimensions")
                return width, height
            image.seek(length - 2, 1)


def contained_file(base: Path, relative: str) -> Path | None:
    """Allow existing regular files only, including after symlink resolution."""
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
        return None
    return candidate


def photo_catalog(paths: tuple[Path, ...]) -> tuple[list[dict], dict[str, Path]]:
    photos, media = [], {}
    for index, chosen in enumerate(paths, 1):
        path = chosen.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg"}:
            raise ValueError("--photo requires a stitched JPEG export; use Open photo for PNG/WebP")
        width, height = jpeg_dimensions(path)
        if abs(width / height - 2) > 0.02:
            raise ValueError("--photo requires a stitched 2:1 panorama")
        photo_id = f"photo-{index}"
        photos.append({
            "id": photo_id,
            "title": path.stem,
            "filename": path.name,
            "width": width,
            "height": height,
            "url": f"/media/{photo_id}",
            "bytes": path.stat().st_size,
        })
        media[f"/media/{photo_id}"] = path
    return photos, media


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = "Local360/1.0"
    sys_version = ""

    def __init__(self, *args, root: Path, catalog: bytes, media: dict[str, Path], **kwargs):
        self.root, self.catalog, self.media = root, catalog, media
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)

    def _headers(self, status: int, content_type: str, length: int, cache: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.end_headers()

    def _not_found(self, head_only: bool):
        body = b"Not found\n"
        self._headers(404, "text/plain; charset=utf-8", len(body), "no-store")
        if not head_only:
            self.wfile.write(body)

    def _serve(self, head_only: bool):
        # Match exact URL paths: never turn an arbitrary request into a file path.
        try:
            request = urlsplit(self.path)
        except ValueError:
            self._not_found(head_only)
            return
        if request.scheme or request.netloc:
            self._not_found(head_only)
            return
        route = request.path
        if route == "/api/photos":
            self._headers(200, "application/json; charset=utf-8", len(self.catalog), "no-store")
            if not head_only:
                self.wfile.write(self.catalog)
            return

        if route in STATIC_FILES:
            relative, content_type = STATIC_FILES[route]
            path = contained_file(self.root / "viewer", relative)
            cache = "no-cache"
        else:
            path = self.media.get(route)
            content_type, cache = "image/jpeg", "private, max-age=3600"
            # Recheck the resolved allowlisted path if files change while serving.
            if path is not None:
                path = path if path.resolve() == path and path.is_file() else None
        if path is None:
            self._not_found(head_only)
            return
        try:
            with path.open("rb") as source:
                size = path.stat().st_size
                self._headers(200, content_type, size, cache)
                if not head_only:
                    shutil.copyfileobj(source, self.wfile)
        except (FileNotFoundError, PermissionError, IsADirectoryError):
            self._not_found(head_only)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A client may cancel a large panorama download.


def make_server(port: int = 8787, root: Path = PROJECT_ROOT,
                photos: tuple[Path, ...] = ()) -> ThreadingHTTPServer:
    root = root.resolve()
    photos, media = photo_catalog(photos)
    catalog = json.dumps({
        "photos": photos,
        "defaultId": photos[0]["id"] if photos else None,
    }, ensure_ascii=False).encode("utf-8")
    handler = partial(ViewerHandler, root=root, catalog=catalog, media=media)
    # Deliberately no configurable host: this viewer is local to this computer.
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787, help="local HTTP port (default: 8787)")
    parser.add_argument("--photo", type=Path, action="append", default=[],
                        help="preload a stitched 2:1 JPEG; repeat to add more (optional)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    try:
        server = make_server(args.port, photos=tuple(args.photo))
    except (OSError, ValueError) as error:
        print(f"Could not start viewer: {error}. Check --photo paths or try a different --port.", file=sys.stderr)
        return 1
    with server:
        print(f"360 photo viewer: http://127.0.0.1:{server.server_port}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
