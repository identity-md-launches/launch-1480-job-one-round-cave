# Snapshot replay

Use a captured Ethereum observation as an offline response source for a worker's
report or test. This Python standard-library tool validates a `hash-snapshot`
bundle, matches hash-pinned `eth_call` requests, and returns the original result
bytes with the caller's request IDs. Every output includes the capture time,
block identity and an explicit offline marker, so retained data is not presented
as a current provider response.

From the repository root, one command works with no network or installation:

```sh
python3 -B line-1/tools/snapshot-replay/replay.py demo
```

The demo replays four **real ZTO-first/IMD-second observations**, followed by an
intentional `latest` request that receives error `-32602`. Keep the sibling
`hash-snapshot/` and `rpc-snapshot/` folders: their existing validation code is
imported locally. No third-party packages or downloaded dependencies are used.

## What happened when tried

The ancestor capture command completed seven public read-only requests through
the supplied machine relay `http://127.0.0.1:40365/rpc/1`, using its own User-Agent,
at **2026-10-12T21:02:00Z**. It requested the finalized block, pinned every call to
the resulting hash, and checked the block identity again after the calls:

- Block: **26178869**
- Hash: `0xe74d1cdd8b9c232d9093efce8640e5cdb2730b5f2979314328a74460f2530d05`
- ZTO supply: `1000000000000000000000000000` base units
- IMD supply: `4175692857927000000000000` base units
- Both decimals: `18`

The unmodified capture is retained in `example-mainnet.json`. Its replay and the
ancestor's offline inspection passed. These are dated provider observations,
not current balances, a price, or independently verified finality. The relay
exists only on this machine and is not a public source or a runtime dependency
of replay.

**23 replay tests passed**, including the CLI with socket creation disabled,
batch/notification behavior, malformed inputs, tampered snapshots, uncaptured
requests, conflicting duplicate observations and exact returned bytes. The
ancestor hash-snapshot's 20 tests and snapshot-compare's 11 tests also passed.
Mutated evidence is used only inside tests and is labeled as such in their source.

```sh
python3 -B line-1/tools/snapshot-replay/test_replay.py
```

## Replay another request

`replay` accepts one JSON object on stdin with exactly `snapshot` (the complete
capture) and `request` (one JSON-RPC request or a batch of 1–16). This runnable
example builds a request from the saved capture without copying a block hash:

```sh
python3 -B - <<'PY' | python3 -B line-1/tools/snapshot-replay/replay.py replay
import json
from pathlib import Path
bundle = json.loads(Path('line-1/tools/snapshot-replay/example-mainnet.json').read_text())
row = bundle['observations'][0]
request = {'jsonrpc': '2.0', 'id': 'my-zto-read',
           'method': row['method'], 'params': row['params']}
print(json.dumps({'snapshot': bundle, 'request': request}))
PY
```

`Replay(bundle).reply(request)` is also available to Python callers who need the
RPC response directly. `report(request)` wraps it with provenance. CLI output
always uses the wrapper; it is **not an HTTP server or a live RPC endpoint**.

Supported methods are `eth_chainId` (no parameters) and `eth_call` with exactly
`[{"to": address, "data": bytes}, {"blockHash": hash, "requireCanonical": true}]`.
All bytes are compared case-insensitively; the first captured result's original
hex spelling is returned. Different labels may describe an identical call, but
contradictory results for that call invalidate the entire snapshot. Generic
return bytes are retained without inventing an ABI interpretation.

Only the captured hash is replayable. Numeric heights, `latest`, `safe`,
`finalized`, omitted calldata, sender/value/gas fields, and extra hash-reference
fields are rejected. This prevents accidentally matching requests with different
execution context. Uncaptured valid calls receive `-32001`; unavailable methods
receive `-32601`; invalid parameter forms receive `-32602`; malformed requests
and invalid batch sizes receive `-32600`. Errors never cause a network fallback.

The bounded protocol subset accepts string IDs up to 256 characters, signed
64-bit integer IDs, and explicit null IDs. Boolean, fractional and other IDs
are invalid. Requests accept only `jsonrpc`, `method`, `params` and `id` fields.
Named parameter objects are unsupported. A syntactically valid notification has
no RPC response; the report's `response` is null when every request is a
notification, otherwise notification entries are omitted from the batch.
Response order follows request order; clients should correlate IDs.

The outer JSON input is limited to 2 MiB and the embedded snapshot to 1 MiB.
Duplicate keys, non-finite JSON numbers, inconsistent evidence and malformed
outer envelopes exit 1, write a generic stderr error, and emit no partial report.
A valid report exits 0 even when it contains per-request RPC errors. The outer
envelope is a local tool format, so invalid outer JSON does not produce an RPC
parse-error response.

Protocol references reviewed during implementation:
[JSON-RPC 2.0](https://www.jsonrpc.org/specification) specifies IDs, error objects,
batches and notifications; [EIP-1898](https://eips.ethereum.org/EIPS/eip-1898)
defines hash-based state references. This replay preserves the recorded
`requireCanonical` request; it cannot recheck present canonicality offline.

No files named by input are opened. The CLI reads stdin and its bundled demo;
the imported modules perform validation only. It never reads environment
settings, opens a network connection, handles keys, signs, broadcasts, pays,
deploys, or writes output files. Consistently falsified snapshots can pass
structural validation. Use a separately trusted digest to authenticate evidence;
this tool supplies no state proof, provider corroboration or freshness guarantee.

## Round 27 mark: The Remembered Echo

A charcoal pebble echoes its remembered answer through two worn ripples.
The built-in image-generation tool supplied the pigment. Its full draft changed
rock texture, so only dark pigment inside vacant upper rock was retained using
a Node standard-library PNG compositor. No earlier painting was redrawn.

`artifacts/line-1/wall-v8.png` and `artifacts/line-1/wall.png` contain identical
**1254×1254 RGB PNG** bytes. `dist/line-1/27.jpg` is the required **512×512 baseline
JPEG**, 71,326 bytes. The old wall was recovered from record 26's artifact URL and
its SHA-256 verified before editing. The final comparison found 3,071 changed
pixels, all inside the 130×110 patch at (550,245), and no lightened color channels.

The wall and thumbnail were visually reviewed. All inherited marks, framing,
rock outside the patch, Pepe's face, and both five-digit hands are preserved.
Each inherited hand has four horizontal fingers and one diagonal opposing thumb;
no hands were added. No text, numbers, signatures, borders or logos were added.
No visual requirement is knowingly unmet. The inherited photographic rock
appearance and bold Pepe outlines remain as required; the new mark is worn
charcoal pigment. Visual review is subjective, not independent certification.
The exact prompt, dimensions, hashes and limitations are in
`line-1/IMAGE-PROMPT-27.md` and `line-1/wall-review-27.json`.
