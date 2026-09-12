import contextlib
import hashlib
import json
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np
import tifffile
from PIL import Image, ImageCms

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sphere_photo', ROOT / 'skills/insta360-sdk/scripts/sphere_photo.py')
sphere = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sphere)


def directional_sphere(width=720, height=360):
    longitude = ((np.arange(width) + .5) / width - .5) * 2 * np.pi
    latitude = (.5 - (np.arange(height) + .5) / height) * np.pi
    ll, pp = np.meshgrid(longitude, latitude)
    rays = np.stack((np.cos(pp) * np.sin(ll), np.sin(pp), np.cos(pp) * np.cos(ll)), axis=-1)
    return np.rint((rays + 1) * 127.5).astype(np.uint8)


class SpherePhotoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.input = self.root / 'sphere.jpg'
        self.icc = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        Image.fromarray(directional_sphere()).save(self.input, quality=95, icc_profile=self.icc)

    def run_helper(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return sphere.main(list(map(str, args)))

    def test_cardinal_longitudes_and_both_poles(self):
        source = directional_sphere()
        for yaw, pitch, target in [(0, 0, [128, 128, 255]), (90, 0, [255, 128, 128]),
                                   (180, 0, [128, 128, 0]), (-90, 0, [0, 128, 128]),
                                   (0, 90, [128, 255, 128]), (0, -90, [128, 0, 128])]:
            result = sphere.reproject(source, yaw, pitch, 80, 31, 21)
            np.testing.assert_allclose(result[10, 15], target, atol=1)

    def test_exact_seam_blends_first_and_last_columns(self):
        source = np.zeros((4, 8, 3), dtype=np.uint8)
        source[:, 0] = [240, 20, 40]
        source[:, -1] = [40, 220, 240]
        result = sphere.reproject(source, 180, 0, 70, 1, 1)
        np.testing.assert_array_equal(result[0, 0], [140, 120, 140])
        np.testing.assert_array_equal(result, sphere.reproject(source, -180, 0, 70, 1, 1))
        np.testing.assert_array_equal(result, sphere.reproject(source, 540, 0, 70, 1, 1))

    def test_horizontal_fov_and_pitch_sign(self):
        source = directional_sphere(1440, 720)
        result = sphere.reproject(source, 0, 0, 90, 101, 101)
        # Right edge sees nearly +45 degrees; top sees nearly +45 latitude.
        self.assertGreater(int(result[50, -1, 0]), 215)
        self.assertGreater(int(result[0, 50, 1]), 215)
        self.assertLess(int(result[50, 0, 0]), 40)
        self.assertLess(int(result[-1, 50, 1]), 40)

    def test_annotation_preserves_pixels_icc_and_other_xmp(self):
        root = ET.Element('{adobe:ns:meta/}xmpmeta')
        rdf = ET.SubElement(root, '{' + sphere.RDF + '}RDF')
        desc = ET.SubElement(rdf, '{' + sphere.RDF + '}Description')
        ET.SubElement(desc, '{http://purl.org/dc/elements/1.1/}title').text = 'Generated sphere'
        ET.SubElement(desc, '{' + sphere.GPANO + '}FullPanoWidthPixels').text = '1000'
        data = self.input.read_bytes()
        self.input.write_bytes(data[:2] + sphere.xmp_segment(root) + data[2:])
        output = self.root / 'delivery.jpg'
        self.assertEqual(self.run_helper('annotate', self.input, output), 0)
        report = sphere.verify(output)
        self.assertTrue(report['valid_full_sphere_metadata'])
        self.assertEqual(report['gpano']['FullPanoWidthPixels'], '720')
        self.assertNotIn('PoseHeadingDegrees', report['gpano'])
        before = [(kind, raw) for kind, raw, payload in sphere.jpeg_segments(self.input.read_bytes())
                  if not (kind == 0xE1 and payload.startswith(sphere.XMP))]
        after = [(kind, raw) for kind, raw, payload in sphere.jpeg_segments(output.read_bytes())
                 if not (kind == 0xE1 and payload.startswith(sphere.XMP))]
        self.assertEqual(before, after)
        self.assertIn(b'Generated sphere', output.read_bytes())
        with Image.open(self.input) as old, Image.open(output) as new:
            np.testing.assert_array_equal(np.asarray(old), np.asarray(new))
            self.assertEqual(new.info['icc_profile'], self.icc)

    def test_stale_dimensions_fail_verification(self):
        output = self.root / 'stale.jpg'
        output.write_bytes(sphere.annotate_bytes(self.input.read_bytes(), (1000, 500)))
        self.assertFalse(sphere.verify(output)['valid_full_sphere_metadata'])
        self.assertEqual(self.run_helper('verify', output), 1)

    def test_reframe_is_deterministic_flat_jpeg_with_icc(self):
        sphere_file = self.root / 'annotated.jpg'
        self.run_helper('annotate', self.input, sphere_file)
        outputs = [self.root / 'flat-a.jpg', self.root / 'flat-b.jpg']
        for output in outputs:
            self.run_helper('reframe', sphere_file, output, '--yaw', 179, '--pitch', -20,
                            '--hfov', 75, '--width', 180, '--height', 120)
            with Image.open(output) as image:
                self.assertEqual(image.size, (180, 120))
                self.assertEqual(image.info['icc_profile'], self.icc)
            self.assertEqual(sphere.gpano_fields(output.read_bytes()), {})
        self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())

    def test_rejects_geometry_orientation_nonfinite_and_overwrite(self):
        flat = self.root / 'flat.jpg'
        Image.new('RGB', (100, 70)).save(flat)
        with self.assertRaisesRegex(ValueError, '2:1'):
            self.run_helper('annotate', flat, self.root / 'new.jpg')
        with self.assertRaisesRegex(ValueError, 'new paths'):
            self.run_helper('annotate', self.input, self.input)
        for values in [(float('nan'), 0, 80), (0, 91, 80), (0, 0, 180)]:
            with self.assertRaises(ValueError):
                sphere.reproject(directional_sphere(), *values, 10, 10)
        rotated = self.root / 'rotated.jpg'
        exif = Image.Exif(); exif[274] = 6
        Image.new('RGB', (100, 50)).save(rotated, exif=exif)
        with self.assertRaisesRegex(ValueError, 'orientation'):
            sphere.image_info(rotated)

    def test_non_rgb_reframe_does_not_relabel_colour_profile(self):
        source = self.root / 'cmyk.jpg'
        Image.new('CMYK', (100, 50)).save(source)
        output = self.root / 'converted.jpg'
        with self.assertRaisesRegex(ValueError, 'must be RGB'):
            self.run_helper('reframe', source, output, '--width', 20, '--height', 10)
        self.assertFalse(output.exists())

    def test_rgb16_tiff_preserves_more_than_8bit_precision_icc_and_source(self):
        width, height = 1440, 720
        x = np.arange(width, dtype=np.uint16)
        y = np.arange(height, dtype=np.uint16)
        source = np.empty((height, width, 3), dtype=np.uint16)
        source[..., 0] = 10000 + x[None, :]
        source[..., 1] = 20000 + y[:, None]
        source[..., 2] = 30000 + (x[None, :] + y[:, None])
        input_file = self.root / 'developed-rgb16.tif'
        old_xmp = ('<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:GPano="' + sphere.GPANO +
                   '"><GPano:ProjectionType>equirectangular</GPano:ProjectionType></x:xmpmeta>').encode()
        tifffile.imwrite(input_file, source, photometric='rgb', compression='deflate',
                         iccprofile=self.icc, metadata=None, extratags=[(700, 'B', len(old_xmp), old_xmp, False)])
        source_hash = hashlib.sha256(input_file.read_bytes()).hexdigest()
        expected = sphere.reproject(source, 0, 0, 100, 900, 600)
        outputs = [self.root / 'flat-rgb16-a.tif', self.root / 'flat-rgb16-b.tif']
        for output in outputs:
            receipt = output.with_suffix('.json')
            self.run_helper('reframe', input_file, output, '--output-format', 'tiff16',
                            '--width', 900, '--height', 600, '--hfov', 100, '--receipt', receipt)
            with tifffile.TiffFile(output) as document:
                page = document.pages[0]
                decoded = page.asarray()
                self.assertEqual(decoded.dtype, np.dtype('uint16'))
                self.assertEqual(page.bitspersample, 16)
                self.assertEqual(page.samplesperpixel, 3)
                self.assertEqual(page.tags[34675].value, self.icc)
                self.assertNotIn(700, page.tags)
                self.assertNotIn(270, page.tags)
                np.testing.assert_array_equal(decoded, expected)
                self.assertGreater(len(np.unique(decoded[..., 0])), 256)
                self.assertGreater(np.count_nonzero(decoded % 257), decoded.size * .95)
            report = json.loads(receipt.read_text())
            self.assertEqual(report['source_bits_per_sample'], 16)
            self.assertEqual(report['bits_per_sample'], 16)
            self.assertFalse(report['bit_depth_reduced'])
            self.assertEqual(report['interpolation_precision'], 'float64')
            self.assertTrue(report['icc_preserved'])
            self.assertTrue(report['spherical_metadata_removed'])
        self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
        self.assertEqual(hashlib.sha256(input_file.read_bytes()).hexdigest(), source_hash)
        with self.assertRaisesRegex(ValueError, 'new paths'):
            self.run_helper('reframe', input_file, outputs[0], '--output-format', 'tiff16', '--width', 90, '--height', 60)

    def test_rgb16_tiff_seam_and_poles_keep_sub_8bit_values(self):
        source = np.zeros((36, 72, 3), dtype=np.uint16)
        source[:, 0] = [10001, 20003, 60005]
        source[:, -1] = [10003, 20007, 60009]
        source[0, :] = [50123, 62345, 45678]
        source[-1, :] = [1025, 23456, 61789]
        input_file = self.root / 'pole-seam.tif'
        tifffile.imwrite(input_file, source, photometric='rgb', metadata=None)
        for name, yaw, pitch, target in [('seam', 180, 0, [10002, 20005, 60007]),
                                         ('zenith', 0, 90, [50123, 62345, 45678]),
                                         ('nadir', 0, -90, [1025, 23456, 61789])]:
            output = self.root / (name + '.tif')
            self.run_helper('reframe', input_file, output, '--output-format', 'tiff16',
                            '--width', 1, '--height', 1, '--yaw', yaw, '--pitch', pitch)
            np.testing.assert_array_equal(tifffile.imread(output)[0, 0], target)

    def test_rgb16_tiff_planar_big_endian_and_lzw_input(self):
        source = np.empty((24, 48, 3), dtype=np.uint16)
        source[:] = [12001, 45003, 63005]
        input_file = self.root / 'planar-lzw.tiff'
        tifffile.imwrite(input_file, np.moveaxis(source, -1, 0), photometric='rgb',
                         planarconfig='separate', byteorder='>', compression='lzw', iccprofile=self.icc)
        output = self.root / 'contiguous.tif'
        self.run_helper('reframe', input_file, output, '--output-format', 'tiff16', '--width', 15, '--height', 10)
        with tifffile.TiffFile(output) as result:
            self.assertEqual(int(result.pages[0].planarconfig), 1)
            self.assertEqual(result.pages[0].tags[34675].value, self.icc)
            np.testing.assert_array_equal(result.asarray(), np.broadcast_to([12001, 45003, 63005], (10, 15, 3)))

    def test_rgb16_requires_explicit_8bit_delivery_conversion(self):
        source = self.root / 'source16.tif'
        data = np.full((24, 48, 3), 32897, dtype=np.uint16)
        tifffile.imwrite(source, data, photometric='rgb', iccprofile=self.icc)
        output = self.root / 'preview.jpg'
        with self.assertRaisesRegex(ValueError, 'requires explicit --output-format'):
            self.run_helper('reframe', source, output, '--width', 15, '--height', 10)
        self.assertFalse(output.exists())
        receipt = self.root / 'preview.json'
        self.run_helper('reframe', source, output, '--output-format', 'jpeg', '--width', 15, '--height', 10, '--receipt', receipt)
        with Image.open(output) as result:
            self.assertEqual(result.mode, 'RGB')
            self.assertEqual(result.info['icc_profile'], self.icc)
            self.assertEqual(result.getpixel((5, 5)), (128, 128, 128))
        self.assertTrue(json.loads(receipt.read_text())['bit_depth_reduced'])

    def test_tiff_rejects_raw_float_alpha_multipage_and_orientation(self):
        ordinary = np.zeros((24, 48, 3), dtype=np.uint16)
        cases = [
            ('raw', ordinary, {'extratags': [(50706, 'B', 4, (1, 4, 0, 0), False)]}, 'Camera DNG'),
            ('float', ordinary.astype(np.float32), {}, 'unsigned 8-bit or 16-bit'),
            ('alpha', np.zeros((24, 48, 4), dtype=np.uint16), {}, 'exactly three colour samples'),
            ('oriented', ordinary, {'extratags': [(274, 'H', 1, 6, False)]}, 'orientation'),
        ]
        for name, array, options, error in cases:
            path = self.root / (name + '.tif')
            tifffile.imwrite(path, array, photometric='rgb', **options)
            with self.assertRaisesRegex(ValueError, error):
                sphere.load_reframe_input(path)
        pages = self.root / 'pages.tif'
        with tifffile.TiffWriter(pages) as writer:
            writer.write(ordinary, photometric='rgb')
            writer.write(ordinary, photometric='rgb')
        with self.assertRaisesRegex(ValueError, 'one developed RGB image'):
            sphere.load_reframe_input(pages)

    def test_extended_xmp_is_rejected_without_mutation(self):
        payload = sphere.EXTENDED_XMP + b'unsupported'
        data = self.input.read_bytes()
        broken = data[:2] + b'\xff\xe1' + (len(payload) + 2).to_bytes(2, 'big') + payload + data[2:]
        with self.assertRaisesRegex(ValueError, 'Extended XMP'):
            sphere.annotate_bytes(broken, (720, 360))


if __name__ == '__main__':
    unittest.main()
