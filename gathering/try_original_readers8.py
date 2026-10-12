#!/usr/bin/env python3
"""Exercise inherited reader CLIs with an explicit no-proxy/no-redirect transport."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'gathering/checks/round-08'


def load(name, folder, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'line-1/tools' / folder / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect refused')


def main():
    rpc = load('gathering_original_rpc', 'rpc-snapshot', 'rpc_snapshot.py')
    pinned = load('gathering_original_pinned', 'pinned-snapshot', 'pinned_snapshot.py')
    check = load('gathering_original_check', 'snapshot-check', 'check_snapshot.py')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    commands = [(['rpc_snapshot.py'], rpc.main),
                (['rpc_snapshot.py', 'eth_call', json.dumps([pinned.CALL, 'latest'])], rpc.main),
                (['pinned_snapshot.py', 'capture'], pinned.main)]
    results = []
    for index, (arguments, entry) in enumerate(commands, 1):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(urllib.request, 'urlopen', opener.open), \
                patch.object(sys, 'argv', arguments), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = entry()
        row = {'arguments': arguments, 'exit': status, 'stderr': stderr.getvalue(),
               'transport_adaptation': 'urlopen replaced only during trial with no-proxy/no-redirect opener'}
        if status == 0:
            raw = stdout.getvalue()
            if len(raw.encode()) >= 100000:
                raise ValueError('trial exceeds retained-file bound')
            (OUT / f'original-reader-{index}.json').write_text(raw)
            obj = json.loads(raw)
            row['offline_summary'] = pinned.inspect(obj) if index == 3 else check.summarize(obj)
        results.append(row)
    (OUT / 'original-reader-trials.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))
    return int(any(row['exit'] for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
