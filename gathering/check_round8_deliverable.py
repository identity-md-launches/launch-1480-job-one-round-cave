#!/usr/bin/env python3
"""Offline structural verification for record 07 and the named wall-v8 output."""
import hashlib
import json
from pathlib import Path

from check_deliverable import (Gallery, PLACEHOLDER, check_painted,
                               jpeg_dimensions, png_dimensions)
from make_thumbnail import png_rgb


def main():
    directory = Path('gathering/checks/round-08')
    baseline = json.loads((directory / 'line-baseline.json').read_text())
    current = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
               for n in range(1, 5) for p in Path(f'line-{n}').rglob('*') if p.is_file()}
    assert baseline == current, 'line folder changed'
    goals = [{'line': n, 'goal': Path(f'line-{n}/GOAL.md').read_text().strip()}
             for n in range(1, 5)]
    assert json.loads(Path('dist/goals.json').read_text()) == goals
    wall = Path('artifacts/gathering/wall-v8.png').read_bytes()
    assert wall == Path('artifacts/gathering/wall.png').read_bytes()
    assert png_dimensions(wall) == (1254, 1254)
    assert png_rgb(wall)[:2] == (1254, 1254), 'PNG full decode failed'
    assert jpeg_dimensions(Path('dist/gathering/07.jpg').read_bytes()) == (512, 512)
    record = json.loads(Path('dist/gathering/07.json').read_text())
    check_painted(record, 'Gathering', 7)
    digest = hashlib.sha256(wall).hexdigest()
    assert record['image'] == 'https://api.imd.fun/artifacts/' + digest
    assert record['attributes'][-1]['value'] == 'Gathering'
    preservation = json.loads((directory / 'image-preservation.json').read_text())
    assert preservation['wall_sha256'] == digest
    assert preservation['changed_pixels_outside_rectangle'] == 0
    assert preservation['source_sha256'] == json.loads(
        Path('dist/gathering/06.json').read_text())['image'].rsplit('/', 1)[1]
    assert preservation['changed_pixels'] > 0
    walls = ['line-1', 'line-2', 'line-3', 'line-4', 'gathering']
    gallery = Gallery()
    gallery.feed(Path('dist/index.html').read_text())
    assert gallery.sections == walls and not gallery.external_code
    paths, painted, pending = [], 0, 0
    for folder in walls:
        label = 'Gathering' if folder == 'gathering' else 'Line ' + folder[-1]
        for path in Path('dist', folder).glob('[0-9][0-9].json'):
            paths.append(path.relative_to('dist').as_posix())
            item = json.loads(path.read_text())
            if item == PLACEHOLDER:
                pending += 1
                assert not path.with_suffix('.jpg').exists()
            else:
                painted += 1
                check_painted(item, label, int(path.stem))
                assert path.with_suffix('.jpg').is_file()
        assert all(Path('dist', folder, f'{n:02d}.json').is_file() for n in range(1, 22))
    assert set(paths) <= set(gallery.links)
    assert len(gallery.images) == len(paths)
    for numbers in gallery.order.values():
        assert numbers == sorted(numbers, reverse=True)
    for src in gallery.images:
        assert src.startswith('https://api.imd.fun/artifacts/') or Path('dist', src).is_file()
    for folder in ['gathering', 'shared', 'dist']:
        for path in Path(folder).rglob('*'):
            assert not path.is_symlink(), str(path)
            if path.is_file():
                assert path.stat().st_size <= 100000, str(path)
            if path.suffix.lower() in {'.png', '.jpeg', '.jpg', '.webp', '.gif'}:
                assert folder == 'dist' and path.suffix == '.jpg', str(path)
    for item in json.loads(Path('shared/call-witness/PROVENANCE.json').read_text()):
        assert hashlib.sha256(Path(item['source']).read_bytes()).hexdigest() == item['source_sha256']
        copy = Path('shared/call-witness') / item['copy']
        assert hashlib.sha256(copy.read_bytes()).hexdigest() == item['copy_sha256']
    assert Path('shared/call-witness/examples/zto-imd-snapshot.json').read_bytes() == Path(
        'line-1/tools/snapshot-replay/example-mainnet.json').read_bytes()
    for item in json.loads(Path('shared/evidence-review/PROVENANCE.json').read_text())['sources']:
        copy = Path('shared/evidence-review') / item['copy']
        assert hashlib.sha256(copy.read_bytes()).hexdigest() == item['copy_sha256']
        if item['source'].startswith('line-4/'):
            assert hashlib.sha256(Path(item['source']).read_bytes()).hexdigest() == item['source_sha256']
    tests = json.loads((directory / 'tool-checks.json').read_text())
    assert all(row['exit'] == 0 for row in tests)
    assert sum(row['tests_run'] for row in tests) == 278
    assert json.loads((directory / 'visual-review.json').read_text())['unmet_visual_requirements'] == []
    assert Path('gathering/COINS.md').read_text().splitlines()[0] == 'none'
    assert not Path('gathering/coin-order.json').exists()
    assert not Path('gathering/deploy-order.json').exists()
    print(json.dumps({'passed': True, 'line_files_unchanged': len(current),
                      'goals': 4, 'walls': 5, 'records': len(paths),
                      'painted': painted, 'placeholders': pending,
                      'png': '1254x1254 8-bit RGB', 'jpeg': '512x512 baseline color',
                      'wall_sha256': digest,
                      'visual_review': 'Manual review in README.md; not certified by this checker.'}, indent=2))


if __name__ == '__main__':
    main()
