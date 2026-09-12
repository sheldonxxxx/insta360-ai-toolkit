#!/usr/bin/env python3
"""Decode an SDK image and detect empty/black outputs; visual review is still needed."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageStat

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('image',type=Path)
    p.add_argument('--expected-size',help='WIDTHxHEIGHT')
    p.add_argument('--reference',type=Path,help='Geometry-aligned image for pixel difference')
    a=p.parse_args()
    with Image.open(a.image) as im:
        im.load()
        rgb=im.convert('RGB'); stats=ImageStat.Stat(rgb)
        hist=rgb.convert('L').histogram()
        uniform=all(lo==hi for lo,hi in rgb.getextrema())
        r={'file':str(a.image.resolve()),'format':im.format,'size':list(im.size),'bytes':a.image.stat().st_size,'sha256':hashlib.sha256(a.image.read_bytes()).hexdigest(),'uniform_pixels':uniform,'near_black_fraction':sum(hist[:3])/(im.width*im.height),'mean_rgb':stats.mean,'stddev_rgb':stats.stddev,'icc_present':bool(im.info.get('icc_profile')),'gpano_marker_present':b'GPano' in a.image.read_bytes(),'visual_review_required':True}
        r['size_matches']=not a.expected_size or tuple(map(int,a.expected_size.lower().split('x')))==im.size
        if a.reference:
            with Image.open(a.reference) as ref:
                if ref.size!=im.size: raise ValueError('Reference dimensions differ; aligned comparison required')
                r['mean_absolute_pixel_difference']=ImageStat.Stat(ImageChops.difference(rgb,ref.convert('RGB'))).mean
        r['structural_check_passed']=not uniform and r['size_matches']
        print(json.dumps(r,indent=2))
        return 0 if r['structural_check_passed'] else 1

if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError) as exc:
        print(json.dumps({'structural_check_passed':False,'error':str(exc)}));sys.exit(2)
