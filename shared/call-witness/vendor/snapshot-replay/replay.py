#!/usr/bin/env python3
"""Replay captured hash-pinned eth_call requests offline, with explicit provenance."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'hash-snapshot' / 'hash_snapshot.py'
SPEC = importlib.util.spec_from_file_location('replay_hash_snapshot', SOURCE)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)
MAX_INPUT = 2 * 1024 * 1024
MAX_BATCH = 16
LIMITS = ('Offline replay of recorded provider responses only. requireCanonical was '
          'requested at capture time; canonicality, finality and contract state are '
          'not rechecked. This report is not a live RPC service or a state proof.')


def load_input(raw):
    if len(raw) > MAX_INPUT:
        raise ValueError('input exceeds 2 MiB')
    obj = json.loads(raw, object_pairs_hook=snapshot.unique_object,
                     parse_constant=snapshot.reject_constant)
    if not isinstance(obj, dict) or set(obj) != {'snapshot', 'request'}:
        raise ValueError('expected exactly snapshot and request')
    return obj


def error(code, message, identifier=None):
    return {'jsonrpc': '2.0', 'id': identifier,
            'error': {'code': code, 'message': message}}


def call_key(params):
    """Accept the captured to/data plus canonical-hash form, without guessing fields."""
    if not isinstance(params, list) or len(params) != 2:
        raise ValueError('expected two positional parameters')
    call, ref = params
    if not isinstance(call, dict) or set(call) != {'to', 'data'}:
        raise ValueError('expected to/data only')
    if (not snapshot.rpc.hex_data(call['to'], 20)
            or not snapshot.rpc.hex_data(call['data'])
            or len(call['data']) > 2 + snapshot.MAX_DATA * 2):
        raise ValueError('invalid call bytes')
    if (not isinstance(ref, dict) or set(ref) != {'blockHash', 'requireCanonical'}
            or not snapshot.rpc.hex_data(ref['blockHash'], 32)
            or ref['requireCanonical'] is not True):
        raise ValueError('expected exact canonical hash reference')
    return call['to'].lower(), call['data'].lower(), ref['blockHash'].lower()


class Replay:
    """Validated lookup detached from input mutations; construction performs no IO."""

    def __init__(self, bundle):
        # Round-trip to bound input, reject non-JSON values, and detach caller mutations.
        raw = json.dumps(bundle, allow_nan=False).encode('utf-8')
        bundle = snapshot.load_json(raw)
        checked = snapshot.inspect(bundle)
        self.anchor = dict(bundle['anchor'])
        self.captured_at = checked['captured_at']
        self.endpoint = checked['endpoint']
        self.calls = {}
        for row in bundle['observations']:
            key = call_key(row['params'])
            result = row['response']['result']
            if key in self.calls and self.calls[key].lower() != result.lower():
                raise ValueError('conflicting responses for the same captured call')
            self.calls.setdefault(key, result)

    def one(self, request):
        if (not isinstance(request, dict)
                or set(request) - {'jsonrpc', 'id', 'method', 'params'}
                or request.get('jsonrpc') != '2.0'
                or not isinstance(request.get('method'), str)):
            return error(-32600, 'Invalid Request')
        identifier = request.get('id')
        if not (identifier is None
                or (type(identifier) is int and -(2**63) <= identifier < 2**63)
                or (isinstance(identifier, str) and len(identifier) <= 256)):
            return error(-32600, 'Invalid Request')
        if 'params' in request and not isinstance(request['params'], (list, dict)):
            return error(-32600, 'Invalid Request')
        # A syntactically valid notification never receives an RPC response.
        if 'id' not in request:
            return None
        method, params = request['method'], request.get('params', [])
        if method == 'eth_chainId':
            if params != []:
                return error(-32602, 'Expected no positional parameters', identifier)
            return {'jsonrpc': '2.0', 'id': identifier, 'result': '0x1'}
        if method != 'eth_call':
            return error(-32601, 'Method not available in offline replay', identifier)
        try:
            key = call_key(params)
        except ValueError:
            return error(-32602, 'Expected to/data and captured canonical blockHash', identifier)
        if key not in self.calls:
            return error(-32001, 'Call or block hash not captured', identifier)
        return {'jsonrpc': '2.0', 'id': identifier, 'result': self.calls[key]}

    def reply(self, request):
        if isinstance(request, list):
            if not request or len(request) > MAX_BATCH:
                return error(-32600, 'Batch must contain 1 to 16 requests')
            responses = [self.one(item) for item in request]
            return [item for item in responses if item is not None] or None
        return self.one(request)

    def report(self, request):
        return {'schema': 'ethereum-snapshot-replay/1', 'offline': True,
                'captured_at': self.captured_at, 'endpoint': self.endpoint,
                'anchor': dict(self.anchor), 'response': self.reply(request),
                'evidence_limits': LIMITS}


def demo_input():
    bundle = snapshot.load_json(
        (Path(__file__).resolve().parent / 'example-mainnet.json').read_bytes())
    requests = [{'jsonrpc': '2.0', 'id': row['label'], 'method': row['method'],
                 'params': row['params']} for row in bundle['observations']]
    # Show both successful replay and refusal to impersonate a current provider.
    requests.append({'jsonrpc': '2.0', 'id': 'latest-is-not-captured',
                     'method': 'eth_call',
                     'params': [bundle['observations'][0]['params'][0], 'latest']})
    return {'snapshot': bundle, 'request': requests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'replay'])
    args = parser.parse_args()
    try:
        obj = (demo_input() if args.command == 'demo'
               else load_input(sys.stdin.buffer.read(MAX_INPUT + 1)))
        report = Replay(obj['snapshot']).report(obj['request'])
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, RuntimeError, OSError, RecursionError):
        print('snapshot-replay: invalid input or inconsistent evidence; no report emitted',
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
