#!/usr/bin/env python3
"""Offline adversarial tests over retained chain evidence; no network requests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import zipfile
import review as r


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {p.stem: p.read_bytes() for p in (r.HERE / 'examples').glob('*.json')}

    def test_deterministic_archive_exact_original_bytes(self):
        archive = r.build(self.inputs)
        self.assertEqual(archive, r.build(dict(reversed(list(self.inputs.items())))))
        receipt = r.inspect(archive)
        self.assertFalse(receipt['integrity']['trusted_digest_matched'])
        self.assertEqual(receipt['integrity']['file_count'], 5)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            for kind, raw in self.inputs.items():
                self.assertEqual(z.read('evidence/' + kind + '.json'), raw)

    def test_original_line2_verifier_interoperates(self):
        data = r.build(self.inputs)
        self.assertEqual(r.handoff.verify(data)['sha256'], r.inspect(data)['integrity']['archive_sha256'])

    def current_window(self, include_address=True):
        """Current producer, with retained real responses replayed offline."""
        source = json.loads(self.inputs['transfer-window'])
        anchors = {source[key]['number']: source[key]['hash']
                   for key in ('from_block_anchor', 'to_block_anchor')}
        def replies(endpoint, method, params):
            if method == 'eth_chainId': return '0x1'
            if method == 'eth_blockNumber': return hex(source['head_at_capture'])
            if method == 'eth_call': return '0x' + format(source['decimals'], '064x')
            if method == 'eth_getLogs': return copy.deepcopy(source['raw_logs'])
            if method == 'eth_getBlockByNumber':
                number = int(params[0], 16)
                return {'number': hex(number), 'hash': anchors[number]}
            raise AssertionError(method)
        arguments = ['--from-block', str(source['from_block']), '--to-block', str(source['to_block'])]
        if include_address:
            arguments += ['--address', source['transfers'][0]['to']]
        with patch.object(r.cross.window, 'rpc', side_effect=replies), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            r.cross.window.main(arguments)
        return json.loads(out.getvalue())

    def test_current_schema3_producer_roundtrip(self):
        for address in (True, False):
            obj = self.current_window(address)
            self.assertEqual(obj['schema_version'], 3)
            raw = r.encode(obj)
            packed = r.build({'transfer-window': raw})
            receipt = r.inspect(packed)
            self.assertEqual(receipt['evidence'][0]['summary']['transfer_count'], 3)
            with zipfile.ZipFile(io.BytesIO(packed)) as archive:
                self.assertEqual(archive.read('evidence/transfer-window.json'), raw)

    def test_current_address_summary_types_and_values_revalidated(self):
        for field, value in (('received_raw', '0'), ('incoming_transfer_count', True),
                             ('incoming_transfer_count', 1.0), ('address', 'bad'), ('scope', 'balance')):
            obj = self.current_window()
            obj['address_window_summary'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(RuntimeError):
                r.build({'transfer-window': r.encode(obj)})

    def test_current_comparison_recomputed(self):
        left, right = self.current_window(), self.current_window(False)
        right['rpc'] = 'https://eth.drpc.org'
        report = r.cross.compare(left, right)
        report['evidence'] = {'left': left, 'right': right}
        receipt = r.inspect(r.build({'transfer-comparison': r.encode(report)}))
        self.assertEqual(receipt['evidence'][0]['summary']['status'], 'agreement')

    def test_separate_blocks_not_claimed_atomic(self):
        result = r.inspect(r.build(self.inputs))
        self.assertEqual(result['context']['status'], 'separate observations')
        self.assertFalse(result['context']['same_closing_block_number'])

    def test_wrong_digest_rejected(self):
        data = r.build(self.inputs)
        with self.assertRaises(ValueError):
            r.inspect(data, r.handoff.digest(b'different archive'))
        self.assertTrue(r.inspect(data, r.handoff.digest(data))['integrity']['trusted_digest_matched'])

    def test_repaired_crc_cannot_hide_payload_change(self):
        data = r.build(self.inputs)
        changed = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as a, zipfile.ZipFile(changed, 'w') as b:
            for item in a.infolist():
                raw = a.read(item.filename)
                if item.filename.endswith('unsigned-transaction.json'):
                    raw += b' '
                b.writestr(item, raw)
        with self.assertRaisesRegex(ValueError, 'byte count|integrity'):
            r.inspect(changed.getvalue())

    def rewrite_index(self, change):
        with zipfile.ZipFile(io.BytesIO(r.build(self.inputs))) as z:
            files = {n: z.read(n) for n in z.namelist() if n != r.handoff.MANIFEST}
        index = json.loads(files[r.INDEX])
        change(index)
        files[r.INDEX] = r.encode(index)
        return r.handoff.build(files)

    def test_rehashed_index_still_rechecks_semantics(self):
        bad = self.rewrite_index(lambda obj: obj['entries'][0].__setitem__('summary', {}))
        with self.assertRaisesRegex(ValueError, 'differs from evidence'):
            r.inspect(bad)

    def test_false_context_rejected_after_rehash(self):
        bad = self.rewrite_index(lambda obj: obj['context'].__setitem__('status', 'matching closing anchor'))
        with self.assertRaisesRegex(ValueError, 'context differs'):
            r.inspect(bad)

    def test_raw_log_removal_and_summary_mismatch_rejected(self):
        obj = json.loads(self.inputs['transfer-window'])
        obj['raw_logs'][0]['removed'] = True
        with self.assertRaises(RuntimeError):
            r.build({'transfer-window': r.encode(obj)})
        obj = json.loads(self.inputs['transfer-window'])
        obj['transfers'][0]['raw_value'] = '1'
        with self.assertRaises(RuntimeError):
            r.build({'transfer-window': r.encode(obj)})

    def test_comparison_is_recomputed_not_trusted(self):
        obj = json.loads(self.inputs['transfer-comparison'])
        obj['evidence']['right']['raw_logs'].pop()
        win = obj['evidence']['right']
        events, duplicates = r.cross.window.validate_logs(win['raw_logs'], win['decimals'],
                        win['token_address'], win['from_block'], win['to_block'])
        win.update(transfers=events, transfer_count=len(events), duplicate_count=duplicates)
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            r.build({'transfer-comparison': r.encode(obj)})
        report = r.cross.compare(obj['evidence']['left'], obj['evidence']['right'])
        report['evidence'] = obj['evidence']
        self.assertEqual(r.describe('transfer-comparison', r.encode(report))['status'], 'disagreement')

    def test_comparison_boolean_schema_not_equal_to_integer(self):
        obj = json.loads(self.inputs['transfer-comparison'])
        obj['schema_version'] = True
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            r.build({'transfer-comparison': r.encode(obj)})

    def test_snapshot_block_and_call_context_rejected(self):
        for change in (lambda b: b['params'].__setitem__(1, 'latest'),
                       lambda b: b['block_after'].__setitem__('hash', b['block']['parentHash'])):
            obj = json.loads(self.inputs['pinned-snapshot'])
            change(obj)
            with self.assertRaises(ValueError):
                r.build({'pinned-snapshot': r.encode(obj)})

    def test_same_number_conflicting_closing_hash(self):
        snap = json.loads(self.inputs['pinned-snapshot'])
        win = json.loads(self.inputs['transfer-window'])
        # Explicit mutation, only to test cross-producer conflict detection.
        for key in ('block', 'block_after'):
            snap[key]['number'] = hex(win['to_block'])
        snap['params'][1] = snap['block']['number']
        snap['requested_block'] = snap['block']['number']
        with self.assertRaisesRegex(ValueError, 'conflicting hashes'):
            r.build({'pinned-snapshot': r.encode(snap), 'transfer-window': self.inputs['transfer-window']})

    def test_noncanonical_unsigned_rlp_is_rejected(self):
        obj = json.loads(self.inputs['unsigned-transaction'])
        decoder = r.intent.decoder
        fields, _ = decoder.rlp_item(bytes.fromhex(obj['transaction_hex'][2:]), 1)
        fields[1] = b'\x00'
        obj['transaction_hex'] = '0x02' + decoder.rlp_encode(fields).hex()
        with self.assertRaises(ValueError):
            r.build({'unsigned-transaction': r.encode(obj)})

    def test_endpoint_and_readonly_policy_precedes_network(self):
        for endpoint in ('http://remote.example/rpc/1', 'http://127.0.0.1:44117/rpc/56',
                         'http://127.0.0.1:44117/other', 'https://user:password@example.org',
                         'https://example.org?key=value', 'file:///data'):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises((ValueError, RuntimeError)):
                    r.pinned.rpc.validate_endpoint(endpoint)
                with self.assertRaises(RuntimeError):
                    r.cross.window.validate_endpoint(endpoint)
        for endpoint in ('https://ethereum-rpc.publicnode.com', 'http://127.0.0.1:44117/rpc/1'):
            r.pinned.rpc.validate_endpoint(endpoint)
            r.cross.window.validate_endpoint(endpoint)
        with patch.object(r.pinned.urllib.request, 'urlopen') as network:
            with self.assertRaises(ValueError):
                r.pinned.public_read('http://127.0.0.1:44117/rpc/1', 'not_a_public_read', [])
            network.assert_not_called()

    def test_json_and_resource_limits(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{}' * r.LIMIT, b'null'):
            with self.assertRaises((ValueError, RuntimeError)):
                r.build({'pinned-snapshot': raw})
        with patch.object(r, 'LIMIT', 100):
            with self.assertRaises(ValueError):
                r.build({'unsigned-transaction': self.inputs['unsigned-transaction']})

    def test_cli_failure_has_no_receipt_or_output(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = r.main(['inspect', '../outside.zip'])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), '')
        with patch.object(r, 'capture') as capture, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(r.main(['capture', 'shared/evidence-review/review.py',
                                     '--rpc', 'http://127.0.0.1:44117/rpc/1']), 1)
            capture.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
