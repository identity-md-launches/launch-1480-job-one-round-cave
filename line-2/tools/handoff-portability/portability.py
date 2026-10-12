#!/usr/bin/env python3
"""Report cross-platform path hazards in a fully verified HANDOFF v1 archive."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unicodedata
import zipfile


PROFILE = 'conservative-filenames-v2'


def inspector():
    path = Path('line-2/tools/handoff-inspect/inspect_handoff.py')
    current = Path.cwd()
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('dependency symlinks are not allowed')
    spec = importlib.util.spec_from_file_location('handoff_portability_inspector', current)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def key(component):
    return unicodedata.normalize('NFC', component).casefold().rstrip(' .')


def device(component):
    stem = component.split('.', 1)[0].rstrip(' ').upper()
    return (stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
            or (len(stem) == 4 and stem[:3] in {'COM', 'LPT'}
                and stem[3] in '123456789¹²³'))


def analyze(names):
    """Check payload paths plus the reserved root manifest, without reading files."""
    issues = set()
    nodes = {}
    def add(code, paths):
        issues.add((code, tuple(sorted(set(paths)))))
    for name in sorted(names):
        components = name.split('/')
        if len(name.encode('utf-16-le')) // 2 > 240:
            add('long-relative-path', [name])
        for component in components:
            if any(c in '<>"|?*' for c in component):
                add('windows-forbidden-character', [name])
            if component.endswith((' ', '.')):
                add('trailing-space-or-dot', [name])
            if device(component):
                add('windows-device-name', [name])
            if len(component.encode('utf-16-le')) // 2 > 255:
                add('long-component', [name])
            # Count the original spelling, including extensions, before any
            # normalization. A short Unicode name can still be too many bytes
            # for a destination with a 255-byte component limit.
            if len(component.encode('utf-8')) > 255:
                add('long-utf8-component', [name])
            if unicodedata.normalize('NFC', component) != component:
                add('non-nfc-component', [name])
    # Include implicit directories: a payload 'A' cannot coexist with 'a/x',
    # and 'Dir/x' plus 'dir/y' loses its original directory spelling.
    for name in sorted(set(names) | {'HANDOFF.json'}):
        components = name.split('/')
        for count in range(1, len(components) + 1):
            prefix = '/'.join(components[:count])
            folded = tuple(key(c) for c in components[:count])
            kind = 'file' if count == len(components) else 'directory'
            nodes.setdefault(folded, set()).add((prefix, kind))
    for entries in nodes.values():
        spellings = {path for path, _ in entries}
        kinds = {kind for _, kind in entries}
        if len(spellings) > 1:
            add('normalized-path-collision', spellings)
        if len(kinds) > 1:
            add('file-directory-collision', spellings)
    return [{'code': code, 'paths': list(paths)} for code, paths in sorted(issues)]


def check_path(archive, expected=None):
    receipt = inspector().inspect_path(archive, expected=expected)
    issues = analyze([entry['path'] for entry in receipt['files']])
    return {'format': 'handoff-portability-v1', 'profile': PROFILE,
            'archive_verified': True, 'archive_sha256': receipt['archive_sha256'],
            'trusted_digest_matched': receipt['trusted_digest_matched'],
            'file_count': receipt['file_count'], 'portable': not issues,
            'issue_count': len(issues), 'issues': issues,
            'note': 'Conservative filename screen, not an OS extraction test, '
                    'software safety review or sender authentication. '
                    'Each original component is screened against both 255 '
                    'UTF-8 bytes and 255 UTF-16 units. '
                    'Relative paths over 240 UTF-16 units are flagged without '
                    'knowing the eventual destination prefix.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    command = commands.add_parser('check')
    command.add_argument('archive')
    command.add_argument('--sha256', help='independently trusted archive digest')
    args = parser.parse_args(argv)
    try:
        result = check_path('line-2/handoff.zip' if args.command == 'demo'
                            else args.archive,
                            None if args.command == 'demo' else args.sha256)
        if args.command == 'demo':
            result['demo'] = 'real inherited handoff screened without extraction'
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True))
        return 0 if result['portable'] else 2
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError,
            zipfile.BadZipFile, EOFError, NotImplementedError, struct.error) as error:
        print('handoff-portability: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
