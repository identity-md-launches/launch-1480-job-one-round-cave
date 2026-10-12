#!/usr/bin/env python3
"""Behavioral checks; disposable ZIP fixtures stay inside test/scratch."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    'portability', Path(__file__).with_name('portability.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PortabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)

    def codes(self, names):
        return {item['code'] for item in p.analyze(names)}

    def test_ordinary_paths(self):
        self.assertEqual(p.analyze(['README.md', 'src/tool.py', '資料/説明.txt']), [])

    def test_case_collision(self):
        self.assertIn('normalized-path-collision', self.codes(['README', 'readme']))

    def test_normalization_collision(self):
        self.assertEqual(self.codes(['é.txt', 'e\u0301.txt']),
                         {'normalized-path-collision', 'non-nfc-component'})

    def test_directory_case_collision(self):
        self.assertIn({'code': 'normalized-path-collision', 'paths': ['Dir', 'dir']},
                      p.analyze(['Dir/one', 'dir/two']))

    def test_file_directory_conflict(self):
        self.assertIn('file-directory-collision', self.codes(['a', 'a/x']))
        self.assertIn('file-directory-collision', self.codes(['A', 'a/x']))

    def test_manifest_alias(self):
        self.assertIn('normalized-path-collision', self.codes(['handoff.JSON']))
        self.assertIn('file-directory-collision', self.codes(['HANDOFF.json/x']))

    def test_devices(self):
        for name in ['con', 'NUL.txt', 'dir/COM1.log', 'LPT²', 'CONIN$', 'aux .txt']:
            with self.subTest(name=name):
                self.assertIn('windows-device-name', self.codes([name]))
        for name in ['console', 'COM0', 'COM10', 'LPT0', 'auxiliary']:
            self.assertNotIn('windows-device-name', self.codes([name]))

    def test_forbidden_punctuation(self):
        for char in '<>"|?*':
            self.assertIn('windows-forbidden-character', self.codes(['x'+char]))

    def test_trailing_trim_collisions(self):
        self.assertIn('normalized-path-collision', self.codes(['file', 'file.']))
        self.assertIn('trailing-space-or-dot', self.codes(['dir /file']))

    def test_utf16_lengths(self):
        self.assertIn('long-component', self.codes(['😀'*128]))
        self.assertNotIn('long-component', self.codes(['😀'*127]))
        self.assertIn('long-relative-path', self.codes(['a'*120+'/'+ 'b'*120]))
        self.assertNotIn('long-relative-path', self.codes(['a'*120+'/'+ 'b'*119]))

    def test_deterministic(self):
        names = ['CON', 'Dir/a', 'dir/B', 'foo.', 'foo']
        self.assertEqual(p.analyze(names), p.analyze(list(reversed(names))))

    def test_utf8_component_boundary(self):
        for prefix, fits, exceeds in [
                ('', 'a'*255, 'a'*256),
                ('', 'é'*127+'a', 'é'*128),
                ('', '界'*85, '界'*86),
                ('', '😀'*63+'abc', '😀'*64),
                ('docs/', '界'*85, '界'*86)]:
            with self.subTest(prefix=prefix, character=fits[0]):
                self.assertNotIn('long-utf8-component', self.codes([prefix+fits]))
                self.assertIn('long-utf8-component', self.codes([prefix+exceeds]))

    def test_utf8_counts_original_spelling(self):
        # NFC would shrink this below the budget. Extraction receives the
        # original bytes, so screening must not silently normalize first.
        name = 'e\u0301'*86
        self.assertIn('long-utf8-component', self.codes([name]))
        self.assertIn('non-nfc-component', self.codes([name]))

    def test_utf8_directory_component(self):
        name = '界'*86+'/file.txt'
        self.assertIn({'code': 'long-utf8-component', 'paths': [name]},
                      p.analyze([name]))
        # The budget applies to components, not the sum of a whole path.
        self.assertNotIn('long-utf8-component', self.codes(['界'*50+'/'+ '界'*50]))

    def test_verified_utf8_hazard_cli(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            name = '界'*86+'.txt'
            path = self.fixture(Path(root), [name])
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = p.main(['check', path])
            result = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertTrue(result['archive_verified'])
            self.assertEqual(result['issues'],
                             [{'code': 'long-utf8-component', 'paths': [name]}])
            self.assertEqual(result['profile'], 'conservative-filenames-v2')

    def test_verified_utf8_boundary_is_portable(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            path = self.fixture(Path(root), ['界'*85])
            self.assertTrue(p.check_path(path)['portable'])

    def fixture(self, root, names):
        target = root / 'bundle.zip'
        files = []
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name in names:
                data = ('payload for '+name).encode()
                archive.writestr(name, data)
                files.append({'path': name, 'bytes': len(data),
                              'sha256': hashlib.sha256(data).hexdigest()})
            archive.writestr('HANDOFF.json', json.dumps(
                {'version': 1, 'algorithm': 'sha256', 'files': files}).encode())
        # Python 3.12 returns absolute TemporaryDirectory names, even when
        # dir is relative. Keep the inspector's workspace path policy intact.
        return target.absolute().relative_to(Path.cwd()).as_posix()

    def test_fixture_absolute_and_relative_roots(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            absolute = Path(root).absolute()
            relative = absolute.relative_to(Path.cwd())
            for location in (absolute, relative):
                with self.subTest(location=location):
                    path = self.fixture(location, ['ok.txt'])
                    self.assertFalse(Path(path).is_absolute())
                    self.assertTrue(p.check_path(path)['archive_verified'])

    def test_real_inherited_archive(self):
        result = p.check_path('line-2/handoff.zip')
        self.assertTrue(result['archive_verified'])
        self.assertTrue(result['portable'])
        self.assertEqual(result['file_count'], 2)

    def test_verified_hazard_cli(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            path = self.fixture(Path(root), ['README', 'readme', 'CON.txt'])
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = p.main(['check', path])
            result = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertTrue(result['archive_verified'])
            self.assertFalse(result['portable'])
            self.assertEqual(result['issue_count'], 2)

    def test_invalid_archive_no_partial_json(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            path = Path(root)/'invalid.zip'
            path.write_bytes(b'bad archive')
            with contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                status = p.main(['check', path.absolute().relative_to(Path.cwd()).as_posix()])
            self.assertEqual(status, 1)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('handoff-portability:', err.getvalue())
            self.assertIn('truncated ZIP archive', err.getvalue())

    def test_trusted_digest_and_mismatch(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            path = self.fixture(Path(root), ['ok.txt'])
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            self.assertTrue(p.check_path(path, digest)['trusted_digest_matched'])
            with self.assertRaises(ValueError):
                p.check_path(path, 'f'*64)

    def test_workspace_path_refusal(self):
        for path in ['/outside.zip', '../outside.zip']:
            with self.assertRaises(ValueError):
                p.check_path(path)

    def test_payload_integrity_before_path_analysis(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            path = self.fixture(Path(root), ['CON.txt'])
            data = Path(path).read_bytes().replace(b'payload for CON.txt', b'changed for CON.txt')
            Path(path).write_bytes(data)
            # Prove corruption was reached, rather than passing on a path
            # refusal before the inspector even opened the fixture.
            with self.assertRaisesRegex(zipfile.BadZipFile, 'CRC'):
                p.check_path(path)


if __name__ == '__main__':
    Path('test/scratch').mkdir(parents=True, exist_ok=True)
    unittest.main()
