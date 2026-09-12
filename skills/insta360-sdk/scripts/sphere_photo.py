#!/usr/bin/env python3
# /// script
# dependencies = ["Pillow>=10", "numpy>=1.24", "tifffile>=2024.8.30", "imagecodecs>=2024.9.22"]
# ///
"""Reframe confirmed full-sphere panoramas and verify JPEG GPano delivery metadata."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

GPANO = 'http://ns.google.com/photos/1.0/panorama/'
RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
XMP = b'http://ns.adobe.com/xap/1.0/\0'
EXTENDED_XMP = b'http://ns.adobe.com/xmp/extension/\0'
ET.register_namespace('x', 'adobe:ns:meta/')
ET.register_namespace('rdf', RDF)
ET.register_namespace('GPano', GPANO)


def jpeg_segments(data):
    """Yield untouched JPEG headers, followed by the entire compressed scan tail."""
    if not data.startswith(b'\xff\xd8'):
        raise ValueError('GPano delivery requires a JPEG')
    yield 0xD8, b'\xff\xd8', b''
    pos = 2
    while pos < len(data):
        start = pos
        if data[pos] != 255:
            raise ValueError('Invalid JPEG marker boundary')
        while pos < len(data) and data[pos] == 255:
            pos += 1
        if pos >= len(data):
            raise ValueError('Truncated JPEG marker')
        marker = data[pos]
        pos += 1
        if marker in (0xDA, 0xD9):
            yield marker, data[start:], b''
            return
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:
            yield marker, data[start:pos], b''
            continue
        if pos + 2 > len(data):
            raise ValueError('Truncated JPEG header')
        length = struct.unpack('>H', data[pos:pos + 2])[0]
        end = pos + length
        if length < 2 or end > len(data):
            raise ValueError('Invalid JPEG segment length')
        yield marker, data[start:end], data[pos + 2:end]
        pos = end
    raise ValueError('JPEG has no image scan')


def image_info(path):
    with Image.open(path) as image:
        image.load()
        if image.getexif().get(274, 1) != 1:
            raise ValueError('Normalize and verify the panorama orientation before projection or GPano authoring')
        return {'size': list(image.size), 'format': image.format, 'mode': image.mode,
                'icc_present': bool(image.info.get('icc_profile'))}


def tiff_runtime():
    try:
        import tifffile
    except ImportError as error:
        raise ValueError('TIFF reframing requires tifffile and imagecodecs; use uv run or install the declared script dependencies') from error
    return tifffile


def load_reframe_input(path):
    """Decode developed RGB without routing multichannel uint16 through Pillow."""
    with path.open('rb') as stream:
        signature = stream.read(4)
    if signature in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        tifffile = tiff_runtime()
        with tifffile.TiffFile(path) as container:
            if len(container.pages) != 1 or container.pages[0].subifds:
                raise ValueError('TIFF input must contain one developed RGB image, without additional pages or subimages')
            page = container.pages[0]
            if 50706 in page.tags:
                raise ValueError('Camera DNG is not a developed panorama; develop and stitch it with a qualified RAW workflow first')
            if 274 in page.tags and int(page.tags[274].value) != 1:
                raise ValueError('Normalize and verify the panorama orientation before projection or GPano authoring')
            if int(page.photometric) != 2 or page.samplesperpixel != 3 or page.extrasamples:
                raise ValueError('Reframe TIFF input must be RGB with exactly three colour samples and no alpha')
            if page.dtype.kind != 'u' or page.dtype.itemsize not in (1, 2) or page.bitspersample not in (8, 16):
                raise ValueError('Reframe TIFF input requires unsigned 8-bit or 16-bit RGB samples')
            rgb = page.asarray()
            if int(page.planarconfig) == 2:
                rgb = np.moveaxis(rgb, 0, -1)
            if rgb.shape != (page.imagelength, page.imagewidth, 3):
                raise ValueError('TIFF sample layout does not match one RGB image')
            rgb = np.ascontiguousarray(rgb, dtype=np.uint16 if page.bitspersample == 16 else np.uint8)
            icc = page.tags[34675].value if 34675 in page.tags else None
            if icc is not None:
                icc = bytes(icc)
            info = {'size': [page.imagewidth, page.imagelength], 'format': 'TIFF', 'mode': 'RGB',
                    'bits_per_sample': page.bitspersample, 'icc_present': bool(icc),
                    'decoder': 'tifffile', 'decoder_version': tifffile.__version__,
                    'planar_configuration': 'separate' if int(page.planarconfig) == 2 else 'contiguous'}
            return rgb, icc, info
    with Image.open(path) as image:
        image.load()
        if image.getexif().get(274, 1) != 1:
            raise ValueError('Normalize and verify the panorama orientation before projection or GPano authoring')
        if image.mode != 'RGB':
            raise ValueError('Reframe input must be RGB; explicitly convert and verify other colour modes before preserving an ICC profile')
        # PNG can also carry RGB16 samples that Pillow would silently reduce.
        if image.format == 'PNG':
            with path.open('rb') as stream:
                header = stream.read(25)
            if len(header) == 25 and header[24] == 16:
                raise ValueError('Use a developed RGB16 TIFF for high-precision reframing; this PNG decoder would reduce samples to 8 bits')
        info = {'size': list(image.size), 'format': image.format, 'mode': image.mode,
                'bits_per_sample': 8, 'icc_present': bool(image.info.get('icc_profile')), 'decoder': 'Pillow'}
        return np.asarray(image).copy(), image.info.get('icc_profile'), info


def full_sphere_size(size):
    width, height = size
    if width != height * 2:
        raise ValueError(f'A confirmed full 360 by 180 degree sphere must have exact 2:1 pixels; got {width}x{height}')
    return width, height


def gpano_fields(data):
    fields = {}
    for marker, _, payload in jpeg_segments(data):
        if marker == 0xE1 and payload.startswith(EXTENDED_XMP):
            raise ValueError('Extended XMP is unsupported; inspect and normalize metadata with a metadata editor first')
        if marker != 0xE1 or not payload.startswith(XMP):
            continue
        root = ET.fromstring(payload[len(XMP):])
        for node in root.iter():
            values = [(node.tag, node.text)] + list(node.attrib.items())
            for tag, value in values:
                if tag.startswith('{' + GPANO + '}'):
                    name = tag.split('}', 1)[1]
                    if name in fields:
                        raise ValueError(f'Duplicate GPano property: {name}')
                    fields[name] = value
    return fields


def expected_gpano(size):
    width, height = full_sphere_size(size)
    return {'ProjectionType': 'equirectangular', 'UsePanoramaViewer': 'True',
            'FullPanoWidthPixels': str(width), 'FullPanoHeightPixels': str(height),
            'CroppedAreaImageWidthPixels': str(width), 'CroppedAreaImageHeightPixels': str(height),
            'CroppedAreaLeftPixels': '0', 'CroppedAreaTopPixels': '0'}


def verify(path):
    info = image_info(path)
    fields = gpano_fields(path.read_bytes())
    expected = expected_gpano(info['size'])
    errors = [f'{name}: expected {value}, found {fields.get(name)!r}'
              for name, value in expected.items() if fields.get(name) != value]
    return {**info, 'gpano': fields, 'errors': errors, 'valid_full_sphere_metadata': not errors,
            'projection_requires_visual_confirmation': True}


def xmp_segment(root):
    payload = XMP + ET.tostring(root, encoding='utf-8')
    if len(payload) + 2 > 65535:
        raise ValueError('XMP packet is too large for one JPEG APP1 segment')
    return b'\xff\xe1' + struct.pack('>H', len(payload) + 2) + payload


def annotate_bytes(data, size):
    # Parsing also rejects extended XMP and ambiguous duplicate properties.
    previous = gpano_fields(data)
    expected = expected_gpano(size)
    roots, retained = [], []
    for marker, raw, payload in jpeg_segments(data):
        if marker == 0xE1 and payload.startswith(XMP):
            root = ET.fromstring(payload[len(XMP):])
            for node in root.iter():
                for key in list(node.attrib):
                    if key.startswith('{' + GPANO + '}'):
                        del node.attrib[key]
                for child in list(node):
                    if child.tag.startswith('{' + GPANO + '}'):
                        node.remove(child)
            roots.append(root)
        else:
            retained.append(raw)
    if roots:
        root = roots[0]
        rdf = root.find('.//{' + RDF + '}RDF')
        if rdf is None:
            raise ValueError('XMP has no RDF container')
    else:
        root = ET.Element('{adobe:ns:meta/}xmpmeta')
        rdf = ET.SubElement(root, '{' + RDF + '}RDF')
        roots.append(root)
    description = ET.SubElement(rdf, '{' + RDF + '}Description', {'{' + RDF + '}about': ''})
    # Retain only existing measured pose fields; never invent compass orientation.
    for key in ('PoseHeadingDegrees', 'PosePitchDegrees', 'PoseRollDegrees'):
        if key in previous:
            expected[key] = previous[key]
    for key, value in expected.items():
        ET.SubElement(description, '{' + GPANO + '}' + key).text = value
    return retained[0] + b''.join(xmp_segment(item) for item in roots) + b''.join(retained[1:])


def reproject(rgb, yaw, pitch, hfov, width, height):
    """Pixel-centred rays, bilinear longitude wrapping and latitude clamping."""
    if not all(math.isfinite(v) for v in (yaw, pitch, hfov)) or not -90 <= pitch <= 90 or not 0 < hfov < 170:
        raise ValueError('Use finite yaw, pitch in [-90,90], and horizontal FOV in (0,170)')
    if width < 1 or height < 1 or width * height > 100_000_000:
        raise ValueError('Output dimensions must be positive and at most 100 megapixels')
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype.kind != 'u' or rgb.dtype.itemsize not in (1, 2):
        raise ValueError('Projection requires an H by W by 3 unsigned 8-bit or 16-bit RGB array')
    source_h, source_w = rgb.shape[:2]
    full_sphere_size((source_w, source_h))
    output_dtype = np.uint16 if rgb.dtype.itemsize == 2 else np.uint8
    ceiling = np.iinfo(output_dtype).max
    output = np.empty((height, width, 3), dtype=output_dtype)
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    tangent = math.tan(math.radians(hfov) / 2)
    x = ((np.arange(width, dtype=np.float64) + .5) / width * 2 - 1) * tangent
    # Bounded row blocks avoid full-frame coordinate arrays at delivery resolution.
    for start in range(0, height, 128):
        end = min(height, start + 128)
        y = (1 - (np.arange(start, end, dtype=np.float64) + .5) / height * 2) * tangent * height / width
        xx, yy = np.broadcast_arrays(x[None, :], y[:, None])
        ry, rz = yy * cp + sp, cp - yy * sp
        rx, rz = xx * cy + rz * sy, rz * cy - xx * sy
        longitude = np.arctan2(rx, rz)
        latitude = np.arctan2(ry, np.hypot(rx, rz))
        u = (longitude / (2 * np.pi) + .5) * source_w - .5
        v = np.clip((.5 - latitude / np.pi) * source_h - .5, 0, source_h - 1)
        x0, y0 = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
        dx, dy = (u - x0)[..., None], (v - y0)[..., None]
        x1, y1 = (x0 + 1) % source_w, np.minimum(y0 + 1, source_h - 1)
        x0 %= source_w
        top = rgb[y0, x0] * (1 - dx) + rgb[y0, x1] * dx
        bottom = rgb[y1, x0] * (1 - dx) + rgb[y1, x1] * dx
        output[start:end] = np.clip(np.rint(top * (1 - dy) + bottom * dy), 0, ceiling).astype(output_dtype)
    return output


def exclusive_write(path, data):
    with path.open('xb') as stream:
        stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('verify', help='Validate actual GPano XML against fully decoded JPEG dimensions')
    check.add_argument('input', type=Path)
    for command in ('annotate', 'reframe'):
        sub = commands.add_parser(command)
        sub.add_argument('input', type=Path)
        sub.add_argument('output', type=Path)
        sub.add_argument('--receipt', type=Path)
        if command == 'reframe':
            for name, default in (('yaw', 0), ('pitch', 0), ('hfov', 75)):
                sub.add_argument('--' + name, type=float, default=default)
            sub.add_argument('--width', type=int, required=True)
            sub.add_argument('--height', type=int, required=True)
            sub.add_argument('--quality', type=int, default=95, help='JPEG quality; does not affect lossless TIFF output')
            sub.add_argument('--output-format', choices=('jpeg', 'tiff16'),
                             help='8-bit input defaults to jpeg; 16-bit input requires an explicit choice')
    args = parser.parse_args(argv)
    if args.command == 'verify':
        result = verify(args.input)
        print(json.dumps(result, indent=2))
        return 0 if result['valid_full_sphere_metadata'] else 1
    if args.output.exists() or args.output.is_symlink() or (args.receipt and (args.receipt.exists() or args.receipt.is_symlink())):
        raise ValueError('Output and receipt must be new paths; originals and earlier exports are never overwritten')
    if args.receipt and args.output.resolve() == args.receipt.resolve():
        raise ValueError('Output and receipt must have different paths')
    if args.command == 'reframe':
        rgb, icc, info = load_reframe_input(args.input)
    else:
        info = image_info(args.input)
    full_sphere_size(info['size'])
    receipt = {'operation': args.command, 'input': str(args.input.resolve()), 'output': str(args.output.resolve()),
               'source_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(), 'source': info}
    if args.command == 'annotate':
        exclusive_write(args.output, annotate_bytes(args.input.read_bytes(), info['size']))
        receipt.update(verify(args.output))
        receipt['compressed_image_scan_unchanged'] = True
    else:
        if info['bits_per_sample'] == 16 and args.output_format is None:
            raise ValueError('16-bit input requires explicit --output-format tiff16 to retain precision, or jpeg for an 8-bit delivery conversion')
        output_format = args.output_format or 'jpeg'
        if output_format == 'tiff16':
            tifffile = tiff_runtime()
        if output_format == 'tiff16' and args.output.suffix.lower() not in ('.tif', '.tiff'):
            raise ValueError('Use a .tif or .tiff output path for --output-format tiff16')
        if output_format == 'jpeg' and args.output.suffix.lower() in ('.tif', '.tiff'):
            raise ValueError('A TIFF output path requires explicit --output-format tiff16')
        if not 1 <= args.quality <= 100:
            raise ValueError('JPEG quality must be between 1 and 100')
        output = reproject(rgb, args.yaw, args.pitch, args.hfov, args.width, args.height)
        source_bits = info['bits_per_sample']
        output_bits = 16 if output_format == 'tiff16' else 8
        if source_bits == 8 and output_bits == 16:
            output = output.astype(np.uint16) * 257
        elif source_bits == 16 and output_bits == 8:
            output = ((output.astype(np.uint32) + 128) // 257).astype(np.uint8)
        with args.output.open('xb') as stream:
            if output_format == 'tiff16':
                tifffile.imwrite(stream, output, photometric='rgb', planarconfig='contig',
                                 byteorder='<', compression='deflate', rowsperstrip=128,
                                 metadata=None, software='sphere_photo.py', iccprofile=icc)
            else:
                Image.fromarray(output).save(stream, format='JPEG', quality=args.quality,
                                             subsampling=0, icc_profile=icc)
        angular_width = info['size'][0] * args.hfov / 360
        receipt.update({'projection': 'rectilinear', 'view': {'yaw': args.yaw, 'pitch': args.pitch, 'hfov': args.hfov},
                        'size': [args.width, args.height], 'quality': args.quality if output_format == 'jpeg' else None,
                        'format': 'TIFF' if output_format == 'tiff16' else 'JPEG',
                        'bits_per_sample': output_bits, 'source_bits_per_sample': source_bits,
                        'bit_depth_reduced': output_bits < source_bits,
                        'bit_depth_expanded': output_bits > source_bits,
                        'compression': 'lossless_deflate' if output_format == 'tiff16' else 'jpeg',
                        'interpolation_precision': 'float64',
                        'colour_processing': 'Interpolate source-encoded RGB code values; no colour-space conversion or transfer-function change',
                        'sampling': 'pixel-centred bilinear; longitude wraps; latitude clamps',
                        'equatorial_source_pixels_across_hfov': angular_width,
                        'output_to_equatorial_source_span_ratio': args.width / angular_width,
                        'resolution_note': 'Output dimensions are resampling dimensions, not new detail; sampling density varies across the projection and with latitude.',
                        'icc_preserved': bool(info['icc_present']), 'spherical_metadata_removed': True})
    receipt['output_sha256'] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    if args.receipt:
        exclusive_write(args.receipt, (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, ET.ParseError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}), file=sys.stderr)
        sys.exit(2)
