#!/usr/bin/env python3
"""Offline boundaries and independently calculated gas-budget expectations."""
import contextlib
import io
import json
import random
import unittest
from unittest.mock import patch

import gas_budget as tool

D = tool.reader.D


def envelope(data=b'', gas=100000, creation=False, access=None, **numbers):
    fields = [numbers.get('chain', 1), numbers.get('nonce', 0), numbers.get('tip', 1),
              numbers.get('fee', 2), gas, b'' if creation else bytes.fromhex(D.ZTO[2:]),
              numbers.get('value', 0), data, [] if access is None else access]
    return '0x02' + D.rlp_encode(fields).hex()


class GasTests(unittest.TestCase):
    def test_demo_agrees_across_formats(self):
        raw = tool.inspect(D.demo_transaction(), 'prague')
        obj = tool.inspect(json.dumps(tool.reader.demo_object()), 'prague', 'json')
        for key in ('gas', 'counts', 'inspection', 'initcode', 'checkedViolations'):
            self.assertEqual(raw[key], obj[key])
        self.assertEqual(raw['inspection']['destinationLabel'], 'ZTO')
        self.assertEqual(raw['gas']['intrinsicGas'], '21064')
        self.assertEqual(raw['gas']['calldataFloorGas'], '21160')
        self.assertTrue(raw['passesCheckedConstraints'])

    def test_empty_call_and_creation_all_profiles(self):
        for profile in tool.PROFILES:
            for creation, expected in ((False, 21000), (True, 53000)):
                r = tool.inspect(envelope(creation=creation, gas=expected), profile)
                self.assertEqual(r['gas']['requiredMinimumGasLimit'], str(expected))
                self.assertTrue(r['gas']['gasLimitMeetsMinimum'])
                self.assertEqual(r['gas']['aboveMinimumGas'], '0')

    def test_zero_nonzero_costs_and_prague_floor_not_sum(self):
        raw = envelope(b'\x00\x00\x01\xff')
        london = tool.inspect(raw, 'london')
        prague = tool.inspect(raw, 'prague')
        self.assertEqual(london['gas']['requiredMinimumGasLimit'], '21040')
        self.assertIsNone(london['gas']['calldataFloorGas'])
        self.assertEqual(prague['gas']['requiredMinimumGasLimit'], '21100')
        self.assertEqual(prague['counts']['calldataTokens'], '10')

    def test_minimum_exact_boundary_and_shortfall(self):
        for profile, required in (('london', 21016), ('shanghai', 21016), ('prague', 21040)):
            for delta in (-1, 0, 1):
                r = tool.inspect(envelope(b'\xff', gas=required+delta), profile)
                self.assertEqual(r['gas']['gasLimitMeetsMinimum'], delta >= 0)
                self.assertEqual(r['gas']['shortfallGas'], str(max(0, -delta)))
                self.assertEqual(r['gas']['aboveMinimumGas'], str(max(0, delta)))

    def test_access_duplicates_charged_without_deduplication(self):
        a = bytes.fromhex(D.ZTO[2:])
        k = b'\xab'*32
        r = tool.inspect(envelope(access=[[a, [k, k]], [a, [k]]]), 'prague')
        self.assertEqual(r['gas']['intrinsicGas'], '31500')
        self.assertEqual(r['gas']['requiredMinimumGasLimit'], '31500')
        self.assertEqual(r['counts']['accessAddressOccurrences'], '2')
        self.assertEqual(r['counts']['accessStorageKeyOccurrences'], '3')
        self.assertEqual(r['counts']['uniqueAddressStorageKeyPairs'], '1')
        self.assertTrue(any('Duplicate' in w for w in r['warnings']))

    def test_same_slot_different_address_is_two_pairs(self):
        a = bytes.fromhex(D.ZTO[2:])
        b = bytes.fromhex(tool.reader.intent.IMD[2:])
        r = tool.inspect(envelope(access=[[a, [b'\xab'*32]], [b, [b'\xab'*32]]]), 'london')
        self.assertEqual(r['counts']['uniqueAddressStorageKeyPairs'], '2')
        self.assertFalse(any('Duplicate' in w for w in r['warnings']))

    def test_creation_word_rounding_and_fork_change(self):
        for size, words in ((0, 0), (1, 1), (31, 1), (32, 1), (33, 2), (64, 2), (65, 3)):
            raw = envelope(b'\x01'*size, creation=True)
            london = tool.inspect(raw, 'london')
            shanghai = tool.inspect(raw, 'shanghai')
            self.assertEqual(london['gas']['intrinsicGas'], str(53000+16*size))
            self.assertEqual(shanghai['gas']['intrinsicGas'], str(53000+16*size+2*words))
            self.assertEqual(shanghai['counts']['initcodeWords'], str(words))

    def test_creation_size_boundary_not_applied_to_calls(self):
        for size, ok in ((49152, True), (49153, False)):
            raw = envelope(b'\x00'*size, gas=3000000, creation=True)
            for profile in ('shanghai', 'prague'):
                r = tool.inspect(raw, profile)
                self.assertEqual(r['initcode']['sizeWithinLimit'], ok)
                self.assertEqual(r['passesCheckedConstraints'], ok)
            self.assertIsNone(tool.inspect(raw, 'london')['initcode']['sizeWithinLimit'])
            call = tool.inspect(envelope(b'\x00'*size, gas=3000000), 'prague')
            self.assertIsNone(call['initcode']['sizeWithinLimit'])
            self.assertEqual(call['gas']['components']['initcodeWordGas'], '0')

    def test_creation_prague_floor_can_dominate(self):
        r = tool.inspect(envelope(b'\xff'*2000, gas=101000, creation=True), 'prague')
        self.assertEqual(r['gas']['intrinsicGas'], '85126')
        self.assertEqual(r['gas']['calldataFloorGas'], '101000')
        self.assertEqual(r['gas']['requiredMinimumGasLimit'], '101000')

    def test_fee_violation_retains_report(self):
        r = tool.inspect(envelope(tip=3, fee=2), 'london')
        self.assertFalse(r['passesCheckedConstraints'])
        self.assertEqual(r['checkedViolations'], ['priority-fee-exceeds-max-fee'])
        self.assertTrue(r['gas']['gasLimitMeetsMinimum'])

    def test_bad_profiles_signed_input_and_integers(self):
        for profile in (None, 'latest', 'Prague', 'cancun'):
            with self.assertRaises(ValueError):
                tool.inspect(D.demo_transaction(), profile)
        for raw in ('0x', '0x01c0', '0x02cc'+'80'*12, envelope(gas=2**256)):
            with self.assertRaises(ValueError):
                tool.inspect(raw, 'prague')
        with self.assertRaises(ValueError):
            tool.inspect('{}', 'prague', 'other')
        obj = tool.reader.demo_object()
        obj['r'] = '0x0'
        with self.assertRaises(ValueError):
            tool.inspect(json.dumps(obj), 'prague', 'json')

    def test_seeded_independent_gas_calculations(self):
        rng = random.Random(27)
        address = bytes.fromhex(D.ZTO[2:])
        for _ in range(150):
            data = bytes(rng.choice((0, 1, 2, 255)) for _ in range(rng.randrange(400)))
            access = [[address, [b'\xab'*32]*rng.randrange(4)] for _ in range(rng.randrange(4))]
            creation = bool(rng.randrange(2))
            profile = rng.choice(tool.PROFILES)
            expected = 53000 if creation else 21000
            expected += sum(4 if b == 0 else 16 for b in data)
            expected += sum(2400+1900*len(e[1]) for e in access)
            if creation and profile != 'london':
                expected += 2*((len(data)+31)//32)
            if profile == 'prague':
                expected = max(expected, 21000+sum(10 if b == 0 else 40 for b in data))
            r = tool.inspect(envelope(data, creation=creation, access=access), profile)
            self.assertEqual(r['gas']['requiredMinimumGasLimit'], str(expected))

    def test_cli_exit_codes_and_clean_malformed_output(self):
        cases = [(['--profile', 'prague', '--demo'], 0, ''),
                 (['--profile', 'prague', '--format', 'json', '--demo'], 0, ''),
                 (['--profile', 'london', '--transaction', envelope(gas=20999)], 1, ''),
                 (['--profile', 'prague', '--stdin'], 0, D.demo_transaction()+'\r\n'),
                 (['--profile', 'prague', '--format', 'json', '--stdin'], 0,
                  json.dumps(tool.reader.demo_object())),
                 (['--profile', 'prague', '--stdin'], 2, 'bad'),
                 (['--profile', 'prague', '--stdin'], 2, ' '*(tool.MAX_INPUT_CHARS+1))]
        for args, code, stdin in cases:
            with patch('sys.stdin', io.StringIO(stdin)), \
                    contextlib.redirect_stdout(io.StringIO()) as out, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(tool.main(args), code)
            if code == 2:
                self.assertEqual(out.getvalue(), '')
                self.assertTrue(err.getvalue().startswith('error:'))
            else:
                self.assertEqual(json.loads(out.getvalue())['schema'], 'gas-budget/v1')

    def test_cli_requires_explicit_profile(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ex:
            tool.main(['--demo'])
        self.assertEqual(ex.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
