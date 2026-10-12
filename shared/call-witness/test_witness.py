#!/usr/bin/env python3
"""Integration and refusal checks with retained real evidence; mutations are fixtures."""
import contextlib
import copy
import hashlib
import io
import json
import socket
import sys
import unittest
from unittest.mock import patch
import witness as tool


class Tests(unittest.TestCase):
    def setUp(self):
        self.obj = tool.demo_input()

    def changed_tx(self, index, value):
        fields, _ = tool.budget.reader.D.rlp_item(bytes.fromhex(self.obj['transaction'][2:]), 1)
        fields[index] = value
        self.obj['transaction'] = '0x02' + tool.budget.reader.D.rlp_encode(fields).hex()

    def test_real_response_and_honest_context(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            result = tool.witness(self.obj)
        row = self.obj['snapshot']['observations'][0]
        self.assertEqual(result['replayed_call']['response']['result'], row['response']['result'])
        self.assertEqual(result['replayed_call']['request']['params'], row['params'])
        self.assertEqual(result['snapshot']['block_number_decimal'], '26178869')
        self.assertEqual(result['unsigned_gas_budget']['gas']['requiredMinimumGasLimit'], '21160')
        self.assertIs(result['transaction_execution_verified'], False)
        self.assertIs(result['snapshot']['expected_digest_matched'], False)
        self.assertTrue(any('not execution' in s for s in result['limitations']))

    def test_json_and_rlp_agree_on_original_unsigned_fields(self):
        a = tool.witness(self.obj)
        self.obj.update(transaction=json.dumps(tool.budget.reader.demo_object()), input_format='json')
        b = tool.witness(self.obj)
        self.assertEqual(a['replayed_call'], b['replayed_call'])
        self.assertEqual(a['unsigned_gas_budget']['inspection'], b['unsigned_gas_budget']['inspection'])
        self.assertNotEqual(a['unsigned_input']['text_sha256'], b['unsigned_input']['text_sha256'])

    def test_full_calldata_and_destination_must_match(self):
        for index, value in ((7, bytes.fromhex('18160ddd00')), (7, b''),
                              (5, bytes.fromhex(tool.budget.reader.intent.IMD[2:]))):
            self.obj = tool.demo_input()
            self.changed_tx(index, value)
            # IMD is actually captured too: changing destination to IMD should
            # match its response rather than falsely replaying ZTO.
            if index == 5:
                result = tool.witness(self.obj)
                self.assertEqual(result['matched_observation_labels'], ['IMD-supply'])
                self.assertNotEqual(result['replayed_call']['response']['result'],
                                    self.obj['snapshot']['observations'][0]['response']['result'])
            else:
                with self.assertRaisesRegex(ValueError, 'not captured'):
                    tool.witness(self.obj)
        self.obj = tool.demo_input()
        self.obj['snapshot']['observations'] = self.obj['snapshot']['observations'][1:]
        with self.assertRaisesRegex(ValueError, 'not captured'):
            tool.witness(self.obj)

    def test_wrong_chain_native_value_and_creation_refused(self):
        for index, value in ((0, 11155111), (6, 1), (5, b'')):
            self.obj = tool.demo_input()
            self.changed_tx(index, value)
            with self.assertRaisesRegex(ValueError, 'mainnet'):
                tool.witness(self.obj)

    def test_low_gas_is_reported_even_with_captured_call(self):
        self.changed_tx(4, 21159)
        report = tool.witness(self.obj)
        self.assertEqual(report['unsigned_gas_budget']['gas']['shortfallGas'], '1')
        self.assertFalse(report['unsigned_gas_budget']['passesCheckedConstraints'])
        self.assertIn('result', report['replayed_call']['response'])

    def test_fee_nonce_access_list_never_claimed_as_simulated(self):
        self.changed_tx(1, 123)
        self.changed_tx(2, 3_000_000_000)
        self.changed_tx(8, [[bytes.fromhex(tool.budget.reader.D.ZTO[2:]), []]])
        report = tool.witness(self.obj)
        self.assertEqual(report['unsigned_gas_budget']['inspection']['transaction']['nonce'], '123')
        self.assertIn('priority-fee-exceeds-max-fee', report['unsigned_gas_budget']['checkedViolations'])
        self.assertEqual(set(report['replayed_call']['request']['params'][0]), {'to', 'data'})
        self.assertFalse(report['transaction_execution_verified'])

    def test_conflicting_duplicate_calls_and_invalid_snapshot_refused(self):
        bad = copy.deepcopy(self.obj)
        duplicate = copy.deepcopy(bad['snapshot']['observations'][0])
        duplicate['label'] = 'conflict-fixture'
        duplicate['response']['result'] = '0x' + format(1, '064x')
        bad['snapshot']['observations'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            tool.witness(bad)
        for key, value in (('anchor_after', {}), ('chain_response', {}), ('schema', 'unknown')):
            bad = copy.deepcopy(self.obj)
            bad['snapshot'][key] = value
            with self.assertRaises((ValueError, RuntimeError)):
                tool.witness(bad)

    def test_identical_duplicates_and_case_are_byte_matches(self):
        duplicate = copy.deepcopy(self.obj['snapshot']['observations'][0])
        duplicate['label'] = 'same-fixture'
        duplicate['params'][0]['to'] = '0x' + duplicate['params'][0]['to'][2:].upper()
        self.obj['snapshot']['observations'].append(duplicate)
        self.assertEqual(tool.witness(self.obj)['matched_observation_labels'], ['ZTO-supply', 'same-fixture'])

    def test_expected_digest_requires_actual_match(self):
        self.obj['expected_snapshot_sha256'] = hashlib.sha256(tool.canonical(self.obj['snapshot'])).hexdigest()
        self.assertTrue(tool.witness(self.obj)['snapshot']['expected_digest_matched'])
        for digest in ('f'*64, None, '', True):
            self.obj['expected_snapshot_sha256'] = digest
            with self.assertRaises(ValueError):
                tool.witness(self.obj)

    def test_signed_json_and_incomplete_objects_refused(self):
        obj = tool.budget.reader.demo_object()
        self.obj['input_format'] = 'json'
        for field in ('r', 'from'):
            bad = dict(obj, **{field: '0x0'})
            self.obj['transaction'] = json.dumps(bad)
            with self.assertRaises(ValueError):
                tool.witness(self.obj)
        del obj['nonce']
        self.obj['transaction'] = json.dumps(obj)
        with self.assertRaises(ValueError):
            tool.witness(self.obj)

    def cli(self, raw, command='inspect'):
        with patch.object(sys, 'stdin', io.TextIOWrapper(io.BytesIO(raw))), \
                patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
                contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()) as err:
            status = tool.main([command])
        return status, out.getvalue(), err.getvalue()

    def test_cli_success_shortfall_and_invalid_exit_contract(self):
        status, out, err = self.cli(b'', 'demo')
        self.assertEqual((status, err), (0, ''))
        self.assertIn('synthetic', json.loads(out)['demo'])
        self.changed_tx(4, 1)
        status, out, err = self.cli(tool.canonical(self.obj))
        self.assertEqual((status, err), (1, ''))
        self.assertFalse(json.loads(out)['unsigned_gas_budget']['passesCheckedConstraints'])
        for raw in (b'{', b'null', b'\xff', b'NaN', b'['*1500,
                    b'{"snapshot":{},"snapshot":{}}', b' '*(tool.MAX_BYTES+1)):
            status, out, err = self.cli(raw)
            self.assertEqual((status, out), (2, ''))
            self.assertIn('no report emitted', err)
            self.assertNotIn('Traceback', err)

    def test_extra_fields_and_unselected_profiles_refused(self):
        for field, value in (('rpc', 'https://ethereum-rpc.publicnode.com'),
                             ('profile', 'latest'), ('input_format', 'summary'), ('transaction', {})):
            bad = dict(self.obj, **{field: value})
            with self.assertRaises(ValueError):
                tool.witness(bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)
