#!/usr/bin/env python3
"""Run reviewed line checks in a disposable workspace mirror, preserving lines."""
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'test/scratch/gathering-08'
RECEIPTS = ROOT / 'gathering/checks/round-08'


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    for n in range(1, 5):
        shutil.copytree(ROOT / f'line-{n}', STAGE / f'line-{n}',
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    (STAGE / 'test/scratch').mkdir(parents=True, exist_ok=True)
    # The inherited source suite explicitly creates fixtures under /tmp. Only
    # its disposable copy is adapted so all fixture I/O stays in this workspace.
    source_test = STAGE / 'line-2/tools/handoff-source/test_source.py'
    source_test.write_text(source_test.read_text().replace(
        'dir="/tmp"', 'dir=str(self.previous / "test/scratch")'))
    commands = []
    for n in range(1, 5):
        for test in sorted((ROOT / f'line-{n}/tools').glob('*/test*.py')):
            commands.append([test.relative_to(ROOT).as_posix()])
    commands += [
        ['line-1/tools/hash-snapshot/hash_snapshot.py', 'demo'],
        ['line-1/tools/snapshot-replay/replay.py', 'demo'],
        ['line-1/tools/snapshot-compare/snapshot_compare.py', 'demo'],
        ['line-1/tools/endpoint-policy/endpoint_policy.py', '--demo'],
        ['line-2/tools/handoff/handoff.py', 'demo'],
        ['line-2/tools/handoff/handoff.py', 'verify', 'line-2/handoff.zip'],
        ['line-2/tools/handoff-inspect/inspect_handoff.py', 'demo'],
        ['line-2/tools/handoff-compare/compare_handoff.py', 'demo'],
        ['line-2/tools/handoff-source/source_check.py', 'demo'],
        ['line-2/tools/handoff-catalog/catalog.py', 'demo'],
        ['line-2/tools/handoff-portability/portability.py', 'demo'],
        ['line-3/tools/zto-eip1559-decoder/tx_decode.py', '--demo'],
        ['line-3/tools/erc20-intent/intent.py', '--demo'],
        ['line-3/tools/unsigned-diff/unsigned_diff.py', '--demo'],
        ['line-3/tools/unsigned-guard/guard.py', '--demo'],
        ['line-3/tools/rpc-unsigned-reader/rpc_reader.py', '--demo'],
        ['line-3/tools/gas-budget/gas_budget.py', '--profile', 'prague', '--demo'],
        ['line-3/tools/gas-budget/gas_budget.py', '--profile', 'prague', '--format', 'json', '--demo'],
        ['line-4/tools/transfer-crosscheck/crosscheck.py', '--demo'],
        ['line-4/tools/transfer-window-receipt/receipt.py', '--demo'],
    ]
    summary = []
    for index, args in enumerate(commands, 1):
        command = ['python3', '-B', *args]
        run = subprocess.run(command, cwd=STAGE, text=True, capture_output=True, timeout=60)
        record = {'command': command, 'exit': run.returncode, 'stdout': run.stdout,
                  'stderr': run.stderr, 'workspace': 'disposable mirror in test/scratch',
                  'fixture_adaptation': 'source suite /tmp redirected into test/scratch'}
        tests = re.search(r'Ran (\d+) tests?', run.stderr)
        if tests:
            record['tests_run'] = int(tests[1])
        raw = json.dumps(record, indent=2) + '\n'
        if len(raw.encode()) >= 100000:
            raise ValueError('receipt too large')
        (RECEIPTS / f'tool-{index:02d}.json').write_text(raw)
        summary.append({'command': args, 'exit': run.returncode,
                        'tests_run': record.get('tests_run', 0)})
        print(index, run.returncode, args[0], record.get('tests_run', ''), flush=True)
    (RECEIPTS / 'tool-checks.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(any(row['exit'] for row in summary))


if __name__ == '__main__':
    raise SystemExit(main())
