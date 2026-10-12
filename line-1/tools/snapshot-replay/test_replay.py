#!/usr/bin/env python3
"""Offline replay contract checks; retained real evidence plus labeled mutations."""
import contextlib
import copy
import io
import json
import socket
import sys
import unittest
from unittest.mock import patch
import replay as tool

EXAMPLE = tool.demo_input()['snapshot']


class Tests(unittest.TestCase):
    def setUp(self):
        self.bundle = copy.deepcopy(EXAMPLE)
        self.player = tool.Replay(self.bundle)

    def request(self, row=0, identifier='worker-27'):
        observation = self.bundle['observations'][row]
        return {'jsonrpc': '2.0', 'id': identifier, 'method': 'eth_call',
                'params': copy.deepcopy(observation['params'])}

    def cli(self, raw, command='replay'):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['replay.py', command]), \
             patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw))), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
             patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            status = tool.main()
        return status, out.getvalue(), err.getvalue()

    def test_replays_actual_capture_with_new_ids(self):
        requests = [self.request(i, i + 20) for i in range(4)]
        responses = self.player.reply(requests)
        self.assertEqual([r['id'] for r in responses], [20, 21, 22, 23])
        self.assertEqual([r['result'] for r in responses],
                         [r['response']['result'] for r in EXAMPLE['observations']])
        self.assertEqual(EXAMPLE['observations'][0]['params'][0]['to'], tool.snapshot.ZTO)

    def test_byte_equivalent_hex_case_matches(self):
        request = self.request()
        for obj, key in [(request['params'][0], 'to'), (request['params'][0], 'data'),
                         (request['params'][1], 'blockHash')]:
            obj[key] = '0x' + obj[key][2:].upper()
        self.assertIn('result', self.player.reply(request))

    def test_latest_numbers_and_missing_canonicality_are_refused(self):
        for ref in ['latest', 'safe', 'finalized', self.bundle['anchor']['number'],
                    {'blockHash': self.bundle['anchor']['hash']},
                    {'blockHash': self.bundle['anchor']['hash'], 'requireCanonical': False},
                    {'blockHash': self.bundle['anchor']['hash'], 'requireCanonical': 1}]:
            request = self.request()
            request['params'][1] = ref
            with self.subTest(ref=ref):
                self.assertEqual(self.player.reply(request)['error']['code'], -32602)

    def test_uncaptured_hash_and_selector_do_not_return_a_result(self):
        # The parent hash is real but not the state captured in this snapshot.
        for index, key, value in [(1, 'blockHash', self.bundle['anchor']['parentHash']),
                                  (0, 'data', '0x')]:
            request = self.request()
            request['params'][index][key] = value
            response = self.player.reply(request)
            self.assertEqual(response['error']['code'], -32001)
            self.assertNotIn('result', response)

    def test_uncaptured_call_fields_are_not_ignored(self):
        for key, value in [('from', tool.snapshot.IMD), ('value', '0x0'), ('gas', '0x1')]:
            request = self.request()
            request['params'][0][key] = value
            self.assertEqual(self.player.reply(request)['error']['code'], -32602)
        request = self.request()
        del request['params'][0]['data']
        self.assertEqual(self.player.reply(request)['error']['code'], -32602)

    def test_method_allowlist_is_exact(self):
        for method in ['eth_sendRawTransaction', 'eth_sign', 'eth_blockNumber',
                       'eth_getBlockByNumber', 'net_version', 'ETH_CALL']:
            request = self.request()
            request['method'] = method
            self.assertEqual(self.player.reply(request)['error']['code'], -32601)

    def test_chain_id_is_the_validated_captured_network(self):
        for params in [[], None]:
            request = {'jsonrpc': '2.0', 'id': 0, 'method': 'eth_chainId'}
            if params is not None:
                request['params'] = params
            self.assertEqual(self.player.reply(request)['result'], '0x1')
        request['params'] = {}
        self.assertEqual(self.player.reply(request)['error']['code'], -32602)

    def test_notifications_and_null_identifier(self):
        request = self.request()
        del request['id']
        self.assertIsNone(self.player.reply(request))
        request['method'] = 'eth_sendRawTransaction'
        self.assertIsNone(self.player.reply([request, request]))
        request['id'] = None
        response = self.player.reply(request)
        self.assertIsNone(response['id'])
        self.assertEqual(response['error']['code'], -32601)

    def test_mixed_batch_preserves_ids_and_suppresses_notifications(self):
        notification = self.request()
        del notification['id']
        response = self.player.reply([self.request(identifier='a'), notification,
                                      False, self.request(identifier='b')])
        self.assertEqual([r['id'] for r in response], ['a', None, 'b'])
        self.assertEqual(response[1]['error']['code'], -32600)

    def test_batch_limits(self):
        for request in [[], [self.request()] * (tool.MAX_BATCH + 1)]:
            self.assertEqual(self.player.reply(request)['error']['code'], -32600)
        self.assertEqual(len(self.player.reply([self.request()] * tool.MAX_BATCH)), 16)

    def test_malformed_request_types_and_ids(self):
        for request in [None, 7, 'eth_call', True, {}, [[]],
                        {'jsonrpc': '2.0', 'method': 5}]:
            response = self.player.reply(request)
            if isinstance(response, list):
                response = response[0]
            self.assertEqual(response['error']['code'], -32600)
        for identifier in [True, 1.5, [], {}, 2**63, -(2**63)-1, 'a' * 257]:
            response = self.player.reply(self.request(identifier=identifier))
            self.assertEqual(response['error']['code'], -32600)
            self.assertIsNone(response['id'])

    def test_extra_fields_wrong_versions_and_scalar_params(self):
        for key, value in [('jsonrpc', '1.0'), ('extra', 1), ('params', None)]:
            request = self.request()
            request[key] = value
            self.assertEqual(self.player.reply(request)['error']['code'], -32600)

    def test_full_snapshot_is_validated_even_for_chain_id(self):
        for key, value in [('schema', 'unknown'), ('chain_response',
                           {'jsonrpc': '2.0', 'id': 1, 'result': '0x2'})]:
            bundle = copy.deepcopy(EXAMPLE)
            bundle[key] = value
            with self.assertRaises(ValueError):
                tool.Replay(bundle)
        self.bundle['observations'][0]['params'][1]['requireCanonical'] = False
        with self.assertRaises(ValueError):
            tool.Replay(self.bundle)

    def test_conflicting_duplicate_calls_rejected(self):
        duplicate = copy.deepcopy(self.bundle['observations'][0])
        duplicate['label'] = 'conflict-fixture'
        # Deliberately altered evidence, never presented as a live observation.
        duplicate['response']['result'] = '0x' + format(1, '064x')
        self.bundle['observations'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            tool.Replay(self.bundle)

    def test_identical_duplicate_calls_allowed(self):
        duplicate = copy.deepcopy(self.bundle['observations'][0])
        duplicate['label'] = 'same-observation'
        self.bundle['observations'].append(duplicate)
        self.assertIn('result', tool.Replay(self.bundle).reply(self.request()))

    def test_generic_return_bytes_are_not_abi_decoded(self):
        self.bundle['observations'][0]['params'][0]['data'] = '0x'
        self.bundle['observations'][0]['response']['result'] = '0x1234'
        response = tool.Replay(self.bundle).reply(self.request())
        self.assertEqual(response['result'], '0x1234')

    def test_input_mutation_cannot_change_validated_lookup(self):
        request = self.request()
        expected = self.player.reply(request)
        self.bundle['observations'][0]['response']['result'] = '0x'
        self.assertEqual(self.player.reply(request), expected)

    def test_report_keeps_offline_provenance(self):
        result = self.player.report(self.request())
        self.assertIs(result['offline'], True)
        self.assertEqual(result['anchor'], EXAMPLE['anchor'])
        self.assertEqual(result['captured_at'], EXAMPLE['captured_at'])
        self.assertIn('not rechecked', result['evidence_limits'])
        result['anchor']['hash'] = 'changed'
        self.assertEqual(self.player.anchor, EXAMPLE['anchor'])

    def test_duplicate_nonfinite_and_bad_envelope_json_rejected(self):
        for raw in [b'{"snapshot":{},"snapshot":{},"request":null}', b'NaN',
                    b'{"snapshot":Infinity,"request":null}', b'[]', b'{}',
                    b'{"snapshot":{},"request":null,"rpc":"https://example.com"}']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                tool.load_input(raw)

    def test_input_size_bound(self):
        with self.assertRaises(ValueError):
            tool.load_input(b' ' * (tool.MAX_INPUT + 1))

    def test_cli_demo_with_network_disabled(self):
        status, out, err = self.cli(b'', 'demo')
        self.assertEqual(status, 0)
        self.assertEqual(err, '')
        result = json.loads(out)
        self.assertEqual(len(result['response']), 5)
        self.assertEqual(result['response'][-1]['error']['code'], -32602)

    def test_cli_replays_live_format_and_keeps_rpc_errors_in_report(self):
        request = self.request()
        raw = json.dumps({'snapshot': EXAMPLE, 'request': request}).encode()
        status, out, err = self.cli(raw)
        self.assertEqual((status, err), (0, ''))
        self.assertEqual(json.loads(out)['response'], self.player.reply(request))
        request['method'] = 'not-captured'
        raw = json.dumps({'snapshot': EXAMPLE, 'request': request}).encode()
        status, out, err = self.cli(raw)
        self.assertEqual(status, 0)
        self.assertIn('error', json.loads(out)['response'])

    def test_cli_failure_emits_no_partial_report_or_traceback(self):
        for raw in [b'null', b'{', b'\xff', b'[' * 1500,
                    b'{"snapshot":{},"request":null}']:
            status, out, err = self.cli(raw)
            self.assertEqual((status, out), (1, ''))
            self.assertIn('no report emitted', err)
            self.assertNotIn('Traceback', err)


if __name__ == '__main__':
    unittest.main(verbosity=2)
