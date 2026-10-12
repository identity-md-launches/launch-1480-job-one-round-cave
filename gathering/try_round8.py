#!/usr/bin/env python3
"""Bounded public-read trials, with proxy discovery and redirects disabled."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gathering/checks/round-08'


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


witness = load('gathering_call_witness', 'shared/call-witness/witness.py')
bridge = load('gathering_anchor_bridge', 'shared/anchor-bridge/anchor_bridge.py')
snapshot = load('gathering_hash_snapshot', 'line-1/tools/hash-snapshot/hash_snapshot.py')
crosscheck = load('gathering_crosscheck', 'line-4/tools/transfer-crosscheck/crosscheck.py')
native_receipt = load('gathering_native_receipt', 'line-4/tools/transfer-window-receipt/receipt.py')
kit = load('gathering_window_handoff', 'shared/window-handoff/window_handoff.py')


def save(name, value):
    raw = json.dumps(value, indent=2) + '\n'
    if len(raw.encode()) >= 100000:
        raise ValueError('trial receipt exceeds file bound')
    (OUT / name).write_text(raw)


def read(endpoint, method, params):
    window = crosscheck.window
    window.validate_endpoint(endpoint)
    if method not in window.READ_METHODS:
        raise ValueError('not a public read')
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(endpoint, data=body, headers={
        'Content-Type': 'application/json', 'User-Agent': 'Pepeolithic-Gathering-08/1.0 (public reads)'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), snapshot.NoRedirect())
    with opener.open(request, timeout=12) as response:
        raw = response.read(99001)
    if len(raw) > 99000:
        raise ValueError('public response exceeds trial bound')
    payload = json.loads(raw, object_pairs_hook=kit.unique, parse_constant=kit.invalid_constant)
    return snapshot.rpc.validate_response(payload)


def main():
    trials = []
    for index, endpoint in enumerate(['https://ethereum-rpc.publicnode.com', 'https://eth.drpc.org'], 1):
        row = {'endpoint': endpoint, 'network': 'read-only, dedicated User-Agent, no proxy discovery or redirects'}
        try:
            evidence = snapshot.capture(endpoint, calls=[{'label': 'ZTO-supply',
                                        'to': snapshot.ZTO, 'data': '0x18160ddd'}])
            save(f'live-snapshot-{index}.json', evidence)
            witness_input = witness.demo_input()
            witness_input['snapshot'] = evidence
            row['call_witness'] = witness.witness(witness_input)
            save(f'live-call-witness-{index}.json', row['call_witness'])
            row['snapshot'] = snapshot.inspect(evidence)
            end = int(row['snapshot']['block_number'])
            crosscheck.window.rpc = read
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                crosscheck.window.main(['--rpc', endpoint, '--from-block', str(end-1),
                                        '--to-block', str(end), '--address', snapshot.ZTO])
            capture = kit.parse(output.getvalue().encode())
            save(f'live-window-{index}.json', capture)
            try:
                native_receipt.receipt(capture)
                row['native_receipt'] = native_receipt.receipt(capture)
                row['anchor_bridge'] = bridge.link(evidence, capture)
            except RuntimeError as error:
                row['native_receipt'] = {'rejected': str(error)}
            archive = kit.build(output.getvalue().encode())
            row['shared_handoff'] = kit.inspect_bytes(archive)
            (OUT / f'live-window-{index}.zip').write_bytes(archive)
            row['success'] = True
        except (OSError, ValueError, RuntimeError, TypeError, KeyError) as error:
            row['success'] = False
            row['failure'] = type(error).__name__ + ': ' + str(error)
        trials.append(row)
        if len(trials) == 2 and all(r['success'] for r in trials):
            left, right = [kit.parse((OUT / f'live-window-{i}.json').read_bytes()) for i in (1,2)]
            save('native-live-crosscheck.json', crosscheck.compare(left, right))
        save('live-trials.json', trials)
        print(endpoint, row['success'], row.get('failure', 'captured and replayed'), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
