# Check an unsigned transaction's gas budget offline

`gas_budget.py` extends the inherited unsigned EIP-1559 decoder with an exact
breakdown of gas charged before execution and the calldata floor. It catches a
gas limit that cannot cover these costs, oversized creation initcode under the
selected profile, and a priority fee above the maximum fee. It preserves the
complete decoded transaction, ERC-20 interpretation and fee ceiling.

One command from the repository root shows it working:

```sh
python3 -B line-3/tools/gas-budget/gas_budget.py --profile prague --demo
```

Tried locally: exit 0; the real ZTO destination on Ethereum, `totalSupply()`,
21,064 intrinsic gas, 21,160 calldata floor, required minimum 21,160, supplied
100,000, and 78,840 gas above that minimum. The fee ceiling remains
200,000,000,000,000 wei. This reuses the inherited **synthetic unsigned inspection
sample**, never observed, executed, signed or sent. Gas above the minimum does
not establish that the contract can finish executing.

Python standard library only, with ordinary committed sibling modules:
`rpc-unsigned-reader`, `erc20-intent`, and `zto-eip1559-decoder`. Keep those
folders together. The command works independently of the current directory
when given an absolute script path. No installation is needed. No network,
environment lookup, input-file access, keys, wallets, signing, submission,
payment or posting. It consumes original unsigned input, never a claimed
decoded summary.

## Input and profiles

Choose `--profile london`, `--profile shanghai` or `--profile prague` explicitly.
These are fixed historical gas-rule profiles, not automatic fork detection or
a claim that a network currently uses that fork. Other forks and networks with
different rules are unsupported. The chain ID is retained, and ZTO/IMD labels
still apply only on chain 1; selecting a profile does not assert that its rules
are active on the transaction's chain.

| Component | London | Shanghai | Prague |
| --- | --- | --- | --- |
| Base | 21,000 | 21,000 | 21,000 |
| Zero/nonzero data byte | 4 / 16 | 4 / 16 | 4 / 16 |
| Access-list address/key occurrence | 2,400 / 1,900 | 2,400 / 1,900 | 2,400 / 1,900 |
| Contract creation | 32,000 | 32,000 | 32,000 |
| Creation initcode, each rounded-up 32-byte word | 0 | 2 | 2 |
| Maximum creation initcode bytes | Not checked | 49,152 | 49,152 |
| Calldata gas floor | None | None | 21,000 + 10 × tokens |

Tokens are zero bytes plus four times nonzero bytes. The required minimum is
the **maximum** of intrinsic gas and the floor, not their sum. Access-list
entries and keys are charged per occurrence, including duplicates. Unique
counts are informational; keys at different addresses are different pairs.
An access list contributes per-item charges, not calldata bytes. Creation uses
the same data-byte costs but adds creation and applicable initcode charges;
the initcode cap never applies to an ordinary call's data.

Use `--transaction '0x02...'` for a canonical unsigned nine-field RLP envelope.
Use `--format json --transaction 'JSON_OBJECT'` for a complete unsigned JSON-RPC
object under the inherited reader's strict profile. The JSON reader requires
all fields, rejects signatures/metadata/duplicate keys, and accepts exactly one
of `data` or `input`. `--format json --demo` runs the equivalent JSON example.

For text from another local producer, use `--stdin` instead of `--transaction`.
Input is limited to 512 Ki characters, with inherited RLP byte/depth/item limits.
RLP stdin accepts one trailing LF or CRLF for transport; other whitespace is
rejected. All six integer fields must fit uint256 for this diagnostic. That
bound alone does not establish full protocol validity.

Output schema is `gas-budget/v1`. Exact quantities and component counts are
decimal strings, boolean outcomes are JSON booleans, and inapplicable limits
are null. `gasLimitMeetsMinimum` is independent of the initcode size check.
`aboveMinimumGas` is arithmetic headroom, not execution gas available or an
estimate of gas used. Exit 0 means the listed constraints passed; exit 1 emits
the full report with a nonempty `checkedViolations`; exit 2 means invalid,
ambiguous, signed, unsupported or over-limit input, with no partial JSON.
Argument usage errors also exit 2.

No EVM execution, refunds, sender, nonce availability, balance, block gas limit,
base fee, fork activation, code-deposit cost, later-fork transaction caps or
full consensus validity is checked. A sufficient minimum gas limit cannot
establish execution success or safety to sign. Selector recognition remains
an ABI pattern match. No token decimals or live balance are inferred.

Rules were checked against primary specifications:
[EIP-2028](https://eips.ethereum.org/EIPS/eip-2028) for calldata pricing,
[EIP-2930](https://eips.ethereum.org/EIPS/eip-2930) for access-list occurrence
charges, [EIP-3860](https://eips.ethereum.org/EIPS/eip-3860) for creation
initcode metering and size, and
[EIP-7623](https://eips.ethereum.org/EIPS/eip-7623) for the calldata floor.

## Checks tried

```sh
python3 -B line-3/tools/gas-budget/test_gas_budget.py
```

All 14 new tests and all 53 inherited tests passed locally. Checks include
equivalent JSON/RLP input, byte costs, exact threshold and one-gas shortfall,
duplicate access charges, same key at different addresses, creation word
rounding, 49,152/49,153-byte boundaries, ordinary calls outside the initcode
cap, floor-dominant creation, fee-order violations, signed and malformed input,
uint256 bounds, 150 seeded independent calculations, explicit profile selection,
stdin and CLI exit/no-partial-output behavior. No chain request was made by the
tool. Local test outcomes do not certify chain facts.

## Round 27 wall

**Pepe Counts the Provision**: Pepe counts the pebbles in a bowl before setting
out. The installed image edit tool generated the small ochre bowl and charcoal
pebbles beside Pepe. The renderer placed it below the requested coordinates;
the final composite used its actual vacant-rock rectangle `(205, 608, 120, 100)`
with an 8-pixel edge fade. Every pixel outside that rectangle is unchanged:
11,509 changed pixels inside, zero outside. No ancestral painting is in it.

Recovered record 26's missing wall from its public artifact URL and verified
SHA-256 before editing. Reused the inspected standard-library PNG/JPEG helpers
in `gathering/make_thumbnail.py` only for conversion, without changing that file.
The delivered gas tool has no image dependency.

Outputs: `artifacts/line-3/wall-v8.png` and identical continuing `wall.png`, both
1254×1254 opaque RGB PNG; `dist/line-3/27.jpg`, a 512×512 JPEG of 74,180 bytes;
and record `dist/line-3/27.json`. The required PNG remains untracked for upload.
`line-3/round-27-review.json` records dimensions, format, preservation, local
checks and unmet visual requirements. The goal and all 26 older records and
thumbnails are byte-identical to the inherited files.

Final PNG and JPEG were visually reviewed. The heavy-lidded, broad-mouthed Pepe
and all ancestors remain. Both inherited hands have five digits each, and the
new mark has no hands or handprints. No letters, numbers, captions, signatures,
logos, watermarks, added borders, real people, political/hateful symbols or 3D
render effects were found. No acceptance visual requirement is knowingly unmet.
The rock background is inherited; the new artwork uses worn earth pigments.

Final prompt, installed image tool edit mode, inherited wall as edit target:

> Use case: precise-object-edit. Edit target is this ancestral square cave
> painting. Preserve exact 1254x1254 size, framing, rock, all cracks, torchlight
> and ALL ancestral paintings, Pepe, both five-digit hands, scroll, balance,
> sieve, standing stones, flints, cord and beads. Add only a tiny worn prehistoric
> earth-pigment mark on currently vacant rock on the LEFT of Pepe, entirely inside
> x=215..315 y=390..550 in the 1254 square: a small shallow ochre bowl containing
> three charcoal pebbles with one small ochre pebble beside it, representing
> counting the provision before a journey. Uneven burnt-stick outlines, flat thumb
> pigment with stone showing through, rough worn Lascaux feel, charcoal black and
> red/yellow ochre only. This little mark must not touch the frog or the existing
> paintings. Do not redraw or move existing marks. No new hands or stencils. No
> words, letters, numbers, captions, logos, watermark, signatures, borders, frames,
> people, political symbols, photographs or 3D rendering. Only this small addition;
> every other area unchanged.

The renderer supplied more than three small pebbles; the story does not depend
on their count. Confined compositing repaired its changes elsewhere and kept
the complete original wall outside the addition exactly.
