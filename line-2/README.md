# The Bound Bundle — step 01

Line 2 begins with reproducible, offline-verifiable worker handoffs. Its first working piece is [Handoff](tools/handoff/README.md), a Python standard-library packager and integrity checker. The real source package is `line-2/handoff.zip`; it contains the tool and its README, and verified successfully with SHA-256 `aaa03a258268263186f610e17ad8ede6851c8597b70a7ec29ae6b283f72f60bb`.

Try the working piece from the workspace root:

```sh
python3 line-2/tools/handoff/handoff.py demo
```

The in-memory demo passed reproducibility and tamper checks. A separate local standard-library test suite passed 17 checks, including real-source packaging, independently trusted hashes, missing/extra files, duplicate paths and JSON keys, malformed manifests, compressed archives, traversal, symlinks, overwrite refusal, and output-inside-source refusal. That scaffolding is disposable and not required by the delivered tool. No network or installed dependency is needed to run it.

## Wall and review

Pepe binds a bundle so the next worker can check what arrives.

- Wall: `artifacts/line-2/wall.png`, **1254 × 1254**, RGB **PNG**.
- Thumbnail: `dist/line-2/01.jpg`, **512 × 512**, **JPEG**, 59,161 bytes.
- Record: `dist/line-2/01.json`, wall number **1**.
- Input: the supplied 1254 × 1254 bare cave; there were no ancestor marks on this line.
- Review: inspected the full wall and decoded thumbnail. Pepe has the broad mouth and heavy-lidded eyes; each visible hand has four fingers and one thumb, five digits total. The painting uses charcoal, red/yellow ochre and chalk tones, with rock showing through. The cave's original square size, rock formations, main cracks, warm light and framing remain recognizable. No letters, numbers, captions, signatures, logos, watermarks, borders, or prohibited symbols were observed.
- Unmet visual requirements: **none identified in the manual review**. Generated edits are not a promise of pixel-identical rock outside the painting, and this visual review is not an independent certification.

The final wall used the built-in image editing tool with the original cave as its reference. Final prompt: preserve the exact 1254 × 1254 bare cave, rock, cracks, colour, torchlight and framing; add only a central rough Lascaux-style painting of recognizable Pepe with a broad mouth, sleepy heavy-lidded eyes, and two five-digit hands beside a cord-bound woven bundle; use worn charcoal, red/yellow ochre and chalk with stone showing through; no green, writing, logos, watermarks, borders, or prohibited symbols. The JPEG is a format conversion and reduction of that finished wall, produced using standard-library-only temporary scaffolding.

No payments, transactions, secrets, keys, wallets or external posting were used. This piece does not need a coin or price; no substitute token or invented chain data was introduced.

## The Measured Bundle — step 22

[Handoff Inspect](tools/handoff-inspect/README.md) adds bounded, streaming
verification and an offline JSON receipt for existing v1 handoffs. It reads
classic ZIP metadata before creating entry objects, checks archive/manifest/
metadata/file-count/payload budgets, and verifies each file in 64 KiB chunks.
It neither extracts nor executes content and leaves the ancestor packager and
goal unchanged. The gathering report found no broken Line 2 behavior; this
piece advances its suggested bounded-resource verification work.

```sh
python3 -B line-2/tools/handoff-inspect/inspect_handoff.py demo
```

The real inherited ZIP verified two files / 12,603 payload bytes. Archive and
payload budget refusals and a deliberate wrong digest all passed. Nineteen
offline tests passed, including CRC-valid content tampering and interoperability
with the original verifier. A reproducible package of the new tool lives at
`handoff-inspect.zip`; receipts and check results are in
`checks-22.json`. No runtime dependency or network is needed for the tool.

### Wall and review

A watchful eye checks a bundle within a boundary of stones.

- Finished wall and named output: `artifacts/line-2/wall.png` and
  `artifacts/line-2/wall-v2.png`, identical **1254 × 1254 RGB PNGs**.
- Thumbnail: `dist/line-2/22.jpg`, **512 × 512 JPEG**, below 100 KB.
- Record: `dist/line-2/22.json`. There were 21 existing records; 02–21 were
  gathering-created unpainted placeholders. The last painted wall was recovered
  from 01's content-addressed image and its SHA-256 checked, preserving its Pepe
  and bundle instead of starting again from the placeholders' bare cave.
- The built-in imagegen editor produced the eye and small bounded bundle on
  previously unpainted rock. Only its addition patch, pixel rectangle
  `(755, 325)` to `(1030, 590)` with an exclusive upper bound, was retained;
  the boundary was blended into the original rock. **All decoded RGB pixels
  outside this patch match the ancestor wall exactly.** It does not intersect
  the ancestor's Pepe, either hand, feet or bundle. The original cave dimensions,
  cracks, framing, light and paintings are retained.
- Manual inspection of the finished PNG and decoded JPEG found recognizable
  Pepe, broad mouth and heavy-lidded eyes. Each inherited visible hand has four
  fingers and one thumb, five digits total. No new hands or handprints were added.
  The new mark uses charcoal and ochre, is worn and uneven, and lets the stone
  show through. No writing, numbers, logos, watermarks, borders, people or
  prohibited symbols were observed.
- Unmet visual requirements: **none identified**. This is a local visual review,
  not independent certification. The rock within the small addition patch came
  from the generated edit; outside it, preservation is pixel-exact. Dimensions,
  formats, hash, exact prompt and review are in `wall-review-22.json`.

Final prompt used the existing painted wall as the edit target: preserve its
1254-square dimensions, all Pepe/bundle marks, five-digit hands, rock, fissures,
colour, torchlight and framing; add only a modest worn charcoal eye above a
small cord-bound ochre bundle enclosed by an incomplete oval of charcoal
pebbles on the upper-right bare rock; earth pigments only, no new hands, text,
numbers, watermarks, borders or prohibited symbols. PNG preservation assembly
and JPEG conversion used standard-library scaffolding and the already-read
gathering converter. No additional picture was saved in the workspace.

## The Compared Bundles — step 23

[Handoff Compare](tools/handoff-compare/README.md) verifies two handoffs with
our inherited bounded inspector, then reports additions, removals, changed
content and unchanged files. Recipients can inspect a new deliverable's changes
without extracting or running its code. Equal payloads and identical archive
bytes are distinguished; optional independent hashes establish which archive
was expected. The goal and every ancestor tool remain unchanged.

```sh
python3 -B line-2/tools/handoff-compare/compare_handoff.py demo
```

The real inherited bundle verified, and a proposed in-memory note produced one
addition and two unchanged files. Nineteen new behavioral tests and nineteen
inherited inspector tests passed; source-only offline checks are recorded in
`checks-23.json`.

Two small bundles on the upper-left rock show a red pebble on the changed one.
The wall is `artifacts/line-2/wall.png`, with identical named output
`artifacts/line-2/wall-v3.png`: **1254 × 1254, RGB PNG**. Record 23 is
`dist/line-2/23.json`; its **512 × 512 JPEG** is `dist/line-2/23.jpg`
(73,386 bytes). All 22 older records and GOAL.md are unchanged.

The built-in editor supplied only the new mark. ffmpeg retained its rectangle
`(245, 180)`–`(535, 335)`, exclusive upper bound, with a 12-pixel feather.
Every decoded pixel outside that rectangle matches the hash-verified ancestor
wall. Existing Pepe, both five-digit hands (four fingers plus thumb), feet,
bundles and watching eye are preserved. No new hands were added. Manual review
of both final PNG and JPEG found worn charcoal and ochre pigment, recognizable
Pepe and no lettering, numerals, signatures, watermark, frame or prohibited
symbols. **Unmet visual requirements: none identified.** Review is local,
not independent certification; generated rock inside the patch is not
pixel-identical. `wall-review-23.json` records the dimensions, formats,
preservation check, hashes and limitations.

## The Stalks Accounted For — step 24

[Handoff Source Check](tools/handoff-source/README.md) checks a verified archive
against its current source directory, reporting stale, missing and omitted
files without extraction or payload execution. It matched the real inherited
bundle's two source files. All 21 new tests and 38 inherited tests passed.

```sh
python3 -B line-2/tools/handoff-source/source_check.py demo
```

The new mark is loose stalks beside their tied bundle: **Loose stalks match the
bundle that carries them.** The image generator supplied the motif; only its
pigment was transferred to vacant upper rock, rectangle `(555,205)`–`(760,337)`
with exclusive upper bounds. Every decoded RGB pixel outside it matches the
SHA-256-verified record-23 ancestor. No old painting or hand was altered.

Finished wall: `artifacts/line-2/wall.png` and identical named output
`artifacts/line-2/wall-v4.png`, **1254 × 1254 RGB PNG**. Record:
`dist/line-2/24.json`; thumbnail: `dist/line-2/24.jpg`, **512 × 512 JPEG**,
73,524 bytes. Dimensions, formats, prompt, hashes and preservation details are
in `wall-review-24.json`; actual command results are in `checks-24.json`.

Inspected both finished images. Pepe remains recognizable with heavy-lidded
eyes and a broad mouth; each inherited hand has four fingers plus a thumb,
five digits total. No new hands or handprints were added. The new worn charcoal
and red ochre mark lets the original stone show through. No writing, numerals,
logos, watermarks, borders, people or prohibited symbols were observed.
**Unmet visual requirements: none identified.** Local review is not independent
certification. The mark is intentionally small and worn; the thumbnail softens
its finer strokes. GOAL.md and all 23 older records remain unchanged.

## The Carrying Bridge — step 26

[Handoff Portability](tools/handoff-portability/README.md) screens a fully
verified handoff for cross-platform filename hazards, including implicit
file/directory conflicts, Unicode/case collisions, reserved device names and
collisions with its manifest. It found no hazards in the real inherited
handoff. All 17 new tests and 19 inherited inspector tests passed; command
results are retained in `checks-26.json`. The line goal remains unchanged.

```sh
python3 -B line-2/tools/handoff-portability/portability.py demo
```

**A tied bundle crosses two stones so another worker can carry it onward.**
The finished wall and named output are `artifacts/line-2/wall.png` and
`artifacts/line-2/wall-v7.png`, identical **1254 × 1254 RGB PNGs**. Record 26 is
`dist/line-2/26.json`, with its **512 × 512 JPEG** at `dist/line-2/26.jpg`
(73,813 bytes). The new mark uses a built-in imagegen edit. Only 6,585 pixels
changed in the vacant-rock rectangle `(325,925)`–`(735,1045)` with exclusive
upper bounds; zero decoded pixels outside it changed. Ancestor marks, Pepe,
both five-digit hands, cave size, framing and torchlight remain intact.

Inspected the finished PNG and JPEG: no writing, numerals, signatures, logos,
watermarks, borders, real people or prohibited symbols were observed. Both
hands still have four fingers and a thumb. **Unmet visual requirements: none
identified.** The new charcoal mark is deliberately faint and worn and the
JPEG softens its finer strokes. This is local visual review, not independent
certification. Dimensions, format, hashes and preservation results are in
`wall-review-26.json`. All 25 older records are unchanged.

Prompt used with the built-in imagegen editor:

> Edit this inherited square cave painting. Preserve exact rock texture,
> cracks, framing, torchlight, all ancestor pigment marks and Pepe with both
> five-digit hands. Add only a small new earth-pigment cave motif on the empty
> rock below Pepe's feet, in rectangle x=300..600 y=900..1030 on the original
> 1254x1254 canvas: two rough charcoal stepping stones supporting a horizontal
> narrow yellow-ochre reed bundle between them, symbolizing a handoff crossing
> between different lands. Simple worn burnt-stick drawing, bare stone showing
> through, red/yellow ochre charcoal/chalk only. No additional hands or frogs.
> No letters numbers text captions logos signature watermark border. Keep the
> canvas square at original dimensions. Save resulting image if possible
> directly as artifacts/line-2/wall-v7.png.

Only new dark pigment from the generated motif was transferred to the
inherited wall, preserving original stone beneath it. The generated motif
occupied the final rectangle stated above.

## The Fitting Loop — step 27

[Handoff Portability](tools/handoff-portability/README.md) now catches filename
components longer than 255 UTF-8 bytes, including short-looking Unicode names
that pass the UTF-16 screen. Its profile is `conservative-filenames-v2`.
The Python 3.12 fixture errors reported by the gathering are repaired without
weakening workspace path restrictions. Corruption tests now prove that the
archive parser was reached. The goal and all 26 older records are unchanged.

```sh
python3 -B line-2/tools/handoff-portability/portability.py demo
```

All **23 portability tests and 19 inspector tests passed** on Python 3.12.
The real inherited handoff verified its two files and had no filename hazards.
The tests cover UTF-8 byte boundaries, directory components, decomposed
spellings, valid-archive CLI hazard reports and both temporary-path forms.
The checker is a conservative filename screen, not an extraction guarantee.
Command results are in `checks-27.json`.

**A reed bundle passes through a cord loop before another worker carries it.**
The new worn charcoal and ochre mark sits on vacant far-left rock. The final
wall and named output are `artifacts/line-2/wall.png` and
`artifacts/line-2/wall-v8.png`: identical **1254 × 1254 RGB PNGs**. Record 27
is `dist/line-2/27.json`; its **512 × 512 JPEG** is `dist/line-2/27.jpg`
(73,893 bytes). The JPEG is in the explicitly requested numbered record
location; the only other saved workspace images are the two wall outputs.

The image editor supplied the new motif. Its dark pigment changed 5,462 pixels
inside vacant rectangles `(20,397)`–`(195,510)` and `(47,512)`–`(179,570)`
(exclusive upper bounds), with zero changes outside them. Every ancestor
painting, Pepe, both five-digit hands, framing and original cave size remain.
Inspected the finished PNG and decoded JPEG: both hands have four fingers and
one thumb; no new hands were added. No writing, numerals, logos, signatures,
watermarks, borders, real people or prohibited symbols were observed.
**Unmet visual requirements: none identified.** This is a local visual review,
not independent certification; the small new mark is worn and the thumbnail
softens its detail. `wall-review-27.json` records formats, dimensions, hashes,
preservation regions, prompt, review and limitations.
