# Call witness

Match the destination and **complete calldata** of an unsigned type-2 Ethereum
message to a recorded, hash-pinned `eth_call`. Carry its original result bytes,
capture provenance and an explicitly chosen gas-rule diagnostic in one offline
report. This helps a worker review a proposed call beside dated provider evidence
without pretending that the unsigned message was executed.

One command, from the repository root, works with Python's standard library and
no network or installation:

```sh
python3 -B shared/call-witness/witness.py demo
```

The demo combines Line 1's **real retained** ZTO/IMD snapshot at block 26178869
with Line 3's **synthetic unsigned inspection sample** addressed to ZTO's actual
Ethereum contract. It replays the captured ZTO supply result, reports a Prague
profile gas lower bound of 21,160, and keeps `transaction_execution_verified`
false. Neither the sample nor any other transaction was signed, sent or executed.
All 12 integration/refusal tests passed, including with socket creation disabled:

```sh
python3 -B shared/call-witness/test_witness.py
```

The folder also ran with only its own ordinary files copied into a disposable
workspace, without any line folders. Native Line 2 packaging, inspection and
source comparison verified a reproducible handoff of the complete kit. Fresh
PublicNode and dRPC ZTO supply captures at block 26178997 replayed successfully
through this receiving path. Those observations are dated, not current state.
Receipts live in `gathering/checks/round-08/` in this repository; the kit does not
depend on them.

## Inspect supplied evidence

`inspect` reads one UTF-8 JSON object on stdin. Supply exactly:

| Field | Value |
| --- | --- |
| `snapshot` | Complete Line 1 `ethereum-hash-snapshot/1` capture |
| `transaction` | Original unsigned input **as text**, not a decoded summary |
| `input_format` | `rlp` or `json` |
| `profile` | Explicit historical rules: `london`, `shanghai` or `prague` |
| `expected_snapshot_sha256` | Optional trusted digest of canonical snapshot JSON |

For example, build an input from the bundled demo without copying a block hash:

```sh
python3 -B - <<'PY' | python3 -B shared/call-witness/witness.py inspect
import importlib.util
spec = importlib.util.spec_from_file_location('witness', 'shared/call-witness/witness.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
print(tool.canonical(tool.demo_input()).decode('ascii'))
PY
```

The optional digest is SHA-256 of sorted, compact, ASCII-escaped JSON with no
terminal newline (`witness.canonical(snapshot)`), rather than a hash of original
file whitespace. `unsigned_input.text_sha256` fingerprints the exact supplied
UTF-8 text; it is neither an Ethereum transaction hash nor a signer identity.
Obtain any trusted digest independently of the input being checked.

Every successful report validates the entire snapshot, parses original unsigned
bytes, requires mainnet, an addressed destination and zero native value, and
matches the exact destination/full calldata at the recorded hash. Identical
duplicate observations are listed; contradictory duplicate replies invalidate
the snapshot. No selector-only match, `latest` lookup or network fallback exists.
Original response hex spelling is retained. ABI interpretation remains only a
pattern match. Inputs name no files and cannot supply an RPC endpoint.

Exit 0 means the match exists and the listed gas constraints passed. Exit 1
retains the full report when the gas limit is too low or fee caps are reversed.
Exit 2 means invalid, signed, ambiguous, unsupported, unmatched or over-limit
input, with no partial stdout. Duplicate keys, non-finite values and excessive
nesting are refused. Input and canonical report are bounded to 99,000 bytes.
The CLI prints indented JSON, so its text can be larger than the canonical form.

## What it establishes

Only a **to/data match to a recorded provider call**. Sender, nonce, gas, fees and
access list were not supplied in that captured `eth_call`. Even a zero-value
envelope can behave differently when those fields or the state differ. The
output explicitly says the transaction's execution is unverified. Gas bounds
are arithmetic under an explicit historical profile, not an execution estimate,
fork detector, balance check or full consensus-validity check. The tool cannot
verify freshness, present canonicality, finality, provider honesty, execution
success or safety to sign. Consistently falsified evidence can pass structural
validation.

Seven unchanged Line 1/3 modules and one exact retained example are ordinary
files under this folder; provenance includes source and copy hashes. Keep the
folder together. The wrapper calls only their offline validators and readers;
vendored capture code is not invoked. No third-party dependency, environment
lookup, wallet/key access, deployment, signing, payment, posting or transaction
submission is involved.
