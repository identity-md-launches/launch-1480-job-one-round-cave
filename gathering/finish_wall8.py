#!/usr/bin/env python3
"""Confine the generated pigment addition, preserving every ancestor pixel."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from make_thumbnail import png_rgb, resize, jpeg

SOURCE_SHA = 'c732d3154abd373fa3085aceba7a10436b56f47fbba04b2beb2fa82883882a96'
RECT = (850, 185, 260, 120)


def encode_png(width, height, rows):
    def chunk(tag, content):
        body = tag + content
        return struct.pack('>I', len(content)) + body + struct.pack('>I', zlib.crc32(body))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(row) for row in rows), 9))
            + chunk(b'IEND', b''))


def main():
    source = Path('artifacts/gathering/wall.png').read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA:
        raise ValueError('record 06 source digest mismatch')
    width, height, old = png_rgb(source)
    new_width, new_height, generated = png_rgb(Path('artifacts/gathering/wall-v8.png').read_bytes())
    if (width, height) != (1254, 1254) or (new_width, new_height) != (1254, 1254):
        raise ValueError('unexpected wall dimensions')
    points = [(x, y) for y, row in enumerate(generated)
              for x in range(new_width) if min(row[x*3:x*3+3]) < 150]
    x0, x1 = min(x for x,y in points)-3, max(x for x,y in points)+4
    y0, y1 = min(y for x,y in points)-3, max(y for x,y in points)+4
    result = [bytearray(row) for row in old]
    left, top, rw, rh = RECT
    for y in range(top, top + rh):
        for x in range(left, left + rw):
            index = x * 3
            stone = old[y][index:index+3]
            sx = x0 + (x-left) * (x1-x0) // rw
            sy = y0 + (y-top) * (y1-y0) // rh
            draft = generated[sy][sx*3:sx*3+3]
            # Pure white contributes no pigment. Charcoal/ochre texture alone
            # is transferred; the underlying rock remains visible throughout.
            opacity = max(0, min(.75, (235-min(draft))/225 * .75))
            red, green, blue = draft
            pigment = (112, 43, 21) if red > green*1.6 and red > 60 else (35, 26, 18)
            result[y][index:index+3] = bytes(round(a*(1-opacity)+b*opacity)
                                             for a,b in zip(stone,pigment))
    changed = outside = 0
    for y in range(height):
        for x in range(width):
            if old[y][3*x:3*x+3] != result[y][3*x:3*x+3]:
                changed += 1
                outside += not (left <= x < left+rw and top <= y < top+rh)
    if changed < 300 or outside:
        raise ValueError('unexpected pigment extent')
    wall = encode_png(width, height, result)
    preview = jpeg(resize(width, height, result))
    if len(preview) >= 100000:
        raise ValueError('thumbnail exceeds 100 KB')
    for filename in ('wall-v8.png', 'wall.png'):
        Path('artifacts/gathering', filename).write_bytes(wall)
    Path('dist/gathering/07.jpg').write_bytes(preview)
    review = {'source_record': 6, 'record_number': 7, 'source_sha256': SOURCE_SHA,
              'wall_sha256': hashlib.sha256(wall).hexdigest(),
              'png_dimensions': [width, height], 'png_format': '8-bit RGB PNG',
              'generated_insert_dimensions': [new_width, new_height], 'png_bytes': len(wall), 'jpeg_dimensions': [512, 512],
              'jpeg_format': 'baseline JPEG', 'jpeg_bytes': len(preview),
              'addition_rectangle': list(RECT), 'changed_pixels': changed,
              'changed_pixels_outside_rectangle': outside,
              'method': 'Installed image tool generated a pigment insert; white removed in memory and pigment confined to vacant rock.'}
    Path('gathering/checks/round-08/image-preservation.json').write_text(json.dumps(review, indent=2)+'\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
