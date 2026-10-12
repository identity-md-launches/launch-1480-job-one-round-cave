#!/usr/bin/env python3
"""Join unsigned-call inspection with recorded hash-pinned response bytes offline."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
MAX_BYTES = 99000
FIELDS = {'snapshot', 'transaction', 'input_format', 'profile'}


def load(name, folder, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / 'vendor' / folder / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


replay = load('call_witness_replay', 'snapshot-replay', 'replay.py')
budget = load('call_witness_budget', 'gas-budget', 'gas_budget.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def parse(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError('input must be at most 99,000 UTF-8 bytes')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=replay.snapshot.unique_object,
                      parse_constant=replay.snapshot.reject_constant)


def witness(obj):
    # Detach callers' mutable data and apply the same bound as the CLI.
    obj = parse(canonical(obj))
    if (not isinstance(obj, dict) or not FIELDS <= set(obj)
            or set(obj) - FIELDS - {'expected_snapshot_sha256'}):
        raise ValueError('expected snapshot, transaction text, input_format and profile only')
    original = canonical(obj['snapshot'])
    digest = hashlib.sha256(original).hexdigest()
    expected = obj.get('expected_snapshot_sha256')
    if 'expected_snapshot_sha256' in obj:
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('expected snapshot digest must be 64 lowercase hexadecimal digits')
        if digest != expected:
            raise ValueError('snapshot differs from expected canonical-content digest')
    # Always validate the full snapshot and original unsigned payload.
    player = replay.Replay(obj['snapshot'])
    gas = budget.inspect(obj['transaction'], obj['profile'], obj['input_format'])
    tx = gas['inspection']['transaction']
    if tx['chainId'] != '1' or tx['value'] != '0' or tx['to'] is None:
        raise ValueError('only zero-native-value, addressed mainnet calls can be matched')
    request = {'jsonrpc': '2.0', 'id': 'call-witness', 'method': 'eth_call',
               'params': [{'to': tx['to'], 'data': tx['data']},
                          {'blockHash': player.anchor['hash'], 'requireCanonical': True}]}
    response = player.reply(request)
    if 'result' not in response:
        raise ValueError('exact destination and full calldata were not captured')
    matches = [row['label'] for row in obj['snapshot']['observations']
               if replay.call_key(row['params']) == replay.call_key(request['params'])]
    result = {
        'schema': 'call-witness/v1', 'offline': True,
        'match_kind': 'destination-and-full-calldata-at-recorded-hash',
        'snapshot': {'canonical_content_sha256': digest,
                     'expected_digest_matched': expected is not None,
                     'endpoint': player.endpoint, 'captured_at': player.captured_at,
                     'anchor': player.anchor, 'block_number_decimal': str(int(player.anchor['number'], 16))},
        'unsigned_input': {'format': obj['input_format'],
                           'text_sha256': hashlib.sha256(obj['transaction'].encode('utf-8')).hexdigest(),
                           'meaning': 'SHA-256 of supplied UTF-8 inspection text, not an Ethereum transaction hash.'},
        'matched_observation_labels': matches,
        'replayed_call': {'request': request, 'response': response},
        'unsigned_gas_budget': gas,
        'transaction_execution_verified': False,
        'limitations': [
            'The response belongs to the captured to/data eth_call, not execution of the unsigned transaction.',
            'Sender, nonce, fees, gas and access list were not supplied in that captured call; matching bytes do not establish matching execution context.',
            'Gas arithmetic uses the explicitly selected historical profile, without checking fork activation or estimating EVM execution.',
            'No fresh RPC, canonicality, finality, provider honesty, balance, execution success or safety to sign is checked.',
            'An expected digest authenticates evidence only when obtained through a separately trusted channel.',
        ],
    }
    if len(canonical(result)) > MAX_BYTES:
        raise ValueError('report exceeds 99,000 bytes; use a smaller input')
    return result


def demo_input():
    return {'snapshot': parse((HERE / 'examples/zto-imd-snapshot.json').read_bytes()),
            'transaction': budget.reader.D.demo_transaction(), 'input_format': 'rlp', 'profile': 'prague'}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command', choices=('demo', 'inspect'))
    args = cli.parse_args(argv)
    try:
        obj = demo_input() if args.command == 'demo' else parse(sys.stdin.buffer.read(MAX_BYTES + 1))
        result = witness(obj)
        if args.command == 'demo':
            result['demo'] = 'Real dated provider snapshot plus synthetic unsigned inspection sample; never executed or sent.'
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0 if result['unsigned_gas_budget']['passesCheckedConstraints'] else 1
    except (ValueError, TypeError, KeyError, RuntimeError, OSError, UnicodeError, RecursionError):
        print('call-witness: invalid, unsupported or unmatched input; no report emitted', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
