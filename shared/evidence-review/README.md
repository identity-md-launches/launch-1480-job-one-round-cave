# Evidence review

Carry public Ethereum observations between workers, with an offline receipt that
checks both archive integrity and the meaning of the included evidence. This
combines Line 1's pinned ZTO supply snapshots, Line 2's bounded streaming handoff
inspection, Line 3's unsigned ERC-20 intent reader, and Line 4's raw-log validation
and two-provider comparisons. Python 3.10+ and its standard library are sufficient.
Copy this entire folder to another workspace; it needs no line folders, installer,
network or external dependency for inspection. Payload code is never executed.

One command to see it working, from this repository root:

```sh
python3 -B shared/evidence-review/review.py demo
```

The demo packages three retained real public-chain observations and an explicitly
synthetic unsigned ZTO envelope entirely in memory. It checks deterministic bytes,
streams the archive through Line 2's inspector, then rebuilds each evidence summary
from the original JSON and raw logs. The supply and historical event window are
from different blocks; the receipt explicitly reports **separate observations**.
The comparison retains both dated provider responses, including three events each.

On 2026-10-12 the live command below also worked through the supplied loopback relay.
It captured ZTO supply `1000000000000000000000000000` base units at block
26177592, hash `0x832d4c6e4af9e0834a7dd1e4d5ce2512fe7afe1cbe01afc2f1cd92249109d77f`.
The 12-block window 26177581–26177592 had zero reported transfers and 18 decimals.
The snapshot and window share the closing hash; the 71,992-byte HANDOFF ZIP
verified offline. The exact captured bytes are in the repository's
`gathering/checks/round-03/live-review.zip`. This is a dated provider observation,
not a current supply, balance or independent proof that no transfers occurred.

## Use

Package explicitly selected public evidence into a **new** workspace file:

```sh
python3 -B shared/evidence-review/review.py pack test/scratch/evidence.zip --pinned-snapshot shared/evidence-review/examples/pinned-snapshot.json --transfer-window shared/evidence-review/examples/transfer-window.json --transfer-comparison shared/evidence-review/examples/transfer-comparison.json --unsigned-transaction shared/evidence-review/examples/unsigned-transaction.json
python3 -B shared/evidence-review/review.py inspect test/scratch/evidence.zip
```

Create the output's parent directory first. Any nonempty subset of the four kinds
is supported. Original input bytes are preserved. The unsigned input is an object
with `transaction_hex` and `provenance`, either `synthetic unsigned demo` or
`user-supplied unsigned envelope`; the original RLP is decoded again on inspection.
Signed envelopes are rejected. Provenance text is descriptive, not authenticated.

Add `--sha256` to `inspect` when a trusted archive digest arrived independently.
Without it, both bytes and their checksums can be replaced together. Exit 0 means
the receipt's checks completed; exit 1 means invalid input, provider failure or a
controlled error, with no success receipt. A valid comparison reporting
**disagreement** remains useful evidence and can be packaged; inspect its status.

For fresh public reads on this worker, use the provided endpoint:

```sh
python3 -B shared/evidence-review/review.py capture test/scratch/live.zip --rpc http://127.0.0.1:44117/rpc/1 --blocks 12
```

On another machine substitute its own supplied endpoint or credential-free public
HTTPS RPC. The ephemeral loopback endpoint works only on this worker. Live capture
first reads a ZTO supply snapshot using the provider's `finalized` tag, then reads
the bounded window ending at that same explicit block. It verifies matching
closing hashes before packaging. Only public read RPC methods are allowed; no
wallet, key, signing, submission, payment, public posting or environment-variable
lookup is implemented. The tool does not ask for coins.

## Bounds and limits

Archives and individual JSON files are capped at 99,000 bytes. A large block or
window fails rather than truncating; capture a smaller explicit package elsewhere
when appropriate. Paths must be relative to the current workspace, without `..`
or symlinks; existing outputs are never overwritten. ZIPs are stored, never
extracted. The inspector checks metadata and limits before parsing payloads.

Supply observations, token windows and provider comparison results are checked by
their original validators, not just matched by field names. Known summaries and
comparison reports are recomputed. Matching block numbers with different closing
hashes are rejected. Matching anchors do not make separate calls atomic, establish
finality, authenticate endpoints, certify provider independence or prove event
completeness. The receipt verifies no token balance or transaction safety.

Copies of the line modules live under `vendor/` as ordinary committed Python.
`PROVENANCE.json` gives original and final hashes. Only capture endpoint policies
were amended: accept credential-free HTTPS and HTTP on numeric loopback
`127.0.0.1`, an explicit port, exact route `/rpc/1`. No credentials, query strings
or fragments are accepted. Mainnet chain-ID checks still run. Original line code
was not changed, and these copies do not update themselves when the lines change.

```sh
python3 -B shared/evidence-review/test_review.py
```

Sixteen offline tests exercise exact bytes, deterministic output, independent
digest comparisons, tampering with repaired ZIP CRCs, rehashed false summaries,
raw-log mutations, recomputed disagreement, canonical RLP, false block links,
numeric type confusion, bounded inputs, endpoint/method refusal and overwrite
refusal before networking. Demo behavior was also checked after copying just
this folder into scratch with no sibling line folders.
# Gathering 07 compatibility repair

The inherited validator rejected fresh schema-3 windows with `validated
read-only schema 2 mainnet capture required`. The current Line 4 producer and
schema-2/3 crosscheck are now copied here unchanged, with old and current hashes
in PROVENANCE.json. All historical examples remain intact. Optional address
summaries are recomputed from validated raw logs, including strict count types.

All 19 review tests passed, including three new producer-to-review regressions:
schema-3 round trips with and without an address summary, false summary values
and types, and comparisons recomputed from current captures. The exact fresh
PublicNode schema-3 capture also packaged and inspected successfully after this
repair. Receipt: `gathering/checks/round-08/evidence-review-after.json`.
