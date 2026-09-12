"""HTTP boundary checks for the local viewer; no external services required."""

import http.client
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest

from server import jpeg_dimensions, make_server


def jpeg_header(width=2048, height=1024):
    return b"\xff\xd8\xff\xc0\x00\x11\x08" + struct.pack(">HH", height, width) + b"\x03" + bytes(9) + b"\xff\xd9"


class ViewerServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "viewer").mkdir()
        (cls.root / "viewer/index.html").write_text("<!doctype html><title>360</title>")
        (cls.root / "viewer/app.js").write_text("'use strict';")
        (cls.root / "viewer/styles.css").write_text("html {color: white}")
        (cls.root / "secret.txt").write_text("not public")
        cls.photos = tuple(cls.root / "panoramas" / f"photo-{i}.jpg" for i in range(1, 4))
        for path in cls.photos:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(jpeg_header())
        cls.server = make_server(0, cls.root, photos=cls.photos)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_loopback_binding(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_catalog_has_only_public_fields_and_selected_media(self):
        status, headers, body = self.request("/api/photos")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(headers["Cache-Control"], "no-store")
        catalog = json.loads(body)
        self.assertEqual(catalog["defaultId"], "photo-1")
        self.assertEqual(len(catalog["photos"]), 3)
        self.assertNotIn(str(self.root), body.decode())
        for photo in catalog["photos"]:
            self.assertEqual(set(photo), {"id", "title", "filename", "width", "height", "url", "bytes"})
            self.assertEqual((photo["width"], photo["height"]), (2048, 1024))
            status, headers, image = self.request(photo["url"])
            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "image/jpeg")
            self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
            self.assertEqual(image, jpeg_header())
            self.assertEqual(len(image), photo["bytes"])

    def test_static_routes_and_query_strings(self):
        for route, content_type in (("/", "text/html"), ("/index.html", "text/html"), ("/app.js?v=1", "text/javascript"), ("/styles.css", "text/css")):
            with self.subTest(route=route):
                status, headers, body = self.request(route)
                self.assertEqual(status, 200)
                self.assertTrue(headers["Content-Type"].startswith(content_type))
                self.assertEqual(headers["Cache-Control"], "no-cache")
                self.assertEqual(int(headers["Content-Length"]), len(body))

    def test_head_matches_get_without_body(self):
        for route in ("/", "/api/photos", "/media/photo-1", "/unknown"):
            with self.subTest(route=route):
                get_status, get_headers, body = self.request(route)
                status, headers, head_body = self.request(route, "HEAD")
                self.assertEqual(status, get_status)
                self.assertEqual(headers["Content-Length"], str(len(body)))
                self.assertEqual(headers["Content-Type"], get_headers["Content-Type"])
                self.assertEqual(head_body, b"")

    def test_unknown_paths_and_traversal_do_not_expose_files(self):
        for route in ("/secret.txt", "/server.py", "/viewer/", "/outputs/", "/media/unknown", "/media/../secret.txt", "/../secret.txt", "/%2e%2e/secret.txt", "/%252e%252e/secret.txt", "/media/%2Fetc%2Fpasswd", "http://example.com/api/photos"):
            with self.subTest(route=route):
                status, _, body = self.request(route)
                self.assertEqual(status, 404)
                self.assertEqual(body, b"Not found\n")

    def test_no_upload_endpoint(self):
        status, _, _ = self.request("/api/photos", "POST")
        self.assertEqual(status, 501)

    def test_missing_samples_allow_empty_catalog(self):
        with tempfile.TemporaryDirectory() as missing:
            server = make_server(0, Path(missing))
            try:
                self.assertEqual(json.loads(server.RequestHandlerClass.keywords["catalog"]), {"photos": [], "defaultId": None})
            finally:
                server.server_close()

    def test_explicit_external_photo_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            server = make_server(0, Path(temp), photos=(self.photos[0],))
            try:
                catalog = json.loads(server.RequestHandlerClass.keywords["catalog"])
                self.assertEqual(len(catalog["photos"]), 1)
            finally:
                server.server_close()

    def test_reject_invalid_and_nonpanoramic_preloads(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.jpg"
            for content in (b"not jpeg", jpeg_header(100, 100)):
                path.write_bytes(content)
                with self.assertRaises(ValueError):
                    make_server(0, self.root, photos=(path,))

    def test_replaced_photo_symlink_is_not_served(self):
        path = self.photos[2]
        original = path.read_bytes()
        path.unlink()
        try:
            path.symlink_to(self.root / "secret.txt")
            status, _, _ = self.request("/media/photo-3")
            self.assertEqual(status, 404)
        finally:
            path.unlink()
            path.write_bytes(original)

    def test_static_symlink_cannot_expose_private_file(self):
        path = self.root / "viewer/app.js"
        original = path.read_bytes()
        path.unlink()
        try:
            path.symlink_to(self.root / "secret.txt")
            status, _, _ = self.request("/app.js")
            self.assertEqual(status, 404)
        finally:
            path.unlink()
            path.write_bytes(original)

    def test_jpeg_dimensions_skip_metadata(self):
        path = self.root / "dimensions-test.jpg"
        path.write_bytes(b"\xff\xd8\xff\xe1\x00\x06abcd" + jpeg_header(6528, 3264)[2:])
        try:
            self.assertEqual(jpeg_dimensions(path), (6528, 3264))
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
