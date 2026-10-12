# Handoff Portability

Screen a verified HANDOFF v1 ZIP for filename hazards when a worker passes a
deliverable between systems using UTF-8 or UTF-16 filenames. Python 3.8+ and only
the standard library are required. Run from the workspace root:

```sh
python3 -B line-2/tools/handoff-portability/portability.py demo
```

The demo checks the real inherited `line-2/handoff.zip`, reads no other payload
source files, writes nothing, and never extracts or executes archive content.

For your own archive:

```sh
python3 -B line-2/tools/handoff-portability/portability.py check line-2/handoff.zip
```

Optional `--sha256 HASH` compares an independently trusted archive digest.
Exit 0 means no hazards in this conservative profile; exit 2 emits a complete
JSON report of hazards in an integrity-valid archive; exit 1 refuses invalid
input with no partial report. Issues and paths are sorted deterministically.
Archive integrity is checked first with the unchanged bounded sibling
`line-2/tools/handoff-inspect/inspect_handoff.py`; retain that dependency at its
workspace-relative location when moving this piece.

The screen detects Windows forbidden punctuation, reserved device names
(including extensions and superscript device digits), trailing spaces/dots,
non-NFC Unicode, UTF-16 component lengths over 255 and relative path lengths
over 240. Profile `conservative-filenames-v2` also reports
`long-utf8-component` for each path containing a component over **255 UTF-8
bytes**. It counts the original spelling, including extensions and directory
components, before normalization. For example, 85 copies of `界` occupy 255
UTF-8 bytes and pass this check; 86 occupy 258 and are flagged despite needing
only 86 UTF-16 units. This is a conservative budget, not a measurement of the
eventual filesystem. The JSON format remains `handoff-portability-v1`; the
changed profile name distinguishes the stricter policy from the old one.

It compares every file and implicit directory after NFC normalization,
case folding and trimming trailing spaces/dots. It reports spelling collisions
and file/directory collisions, including collisions with the root HANDOFF.json
metadata. It never renames, removes, rewrites, installs or extracts anything.

This is intentionally conservative: Unicode case folding can flag names that
some filesystems distinguish. Conversely, filesystem versions, destination
prefixes, permissions, executable bits, platform-specific program behavior,
short-name aliases and OS extraction policies are outside this screen. A clean
report does not guarantee successful extraction or execution. Integrity does
not establish sender identity or code safety. No network, environment variables,
keys, wallets, signatures, transactions, payments or uploads are used.

Behavioral checks:

```sh
python3 -B line-2/tools/handoff-portability/test_portability.py
```

Step 27 repairs the Python 3.12 test fixtures reported by the gathering review:
temporary paths are made workspace-relative before inspection, without relaxing
the inspector. Absolute and relative fixture roots are covered explicitly.
The invalid-ZIP and corruption tests now assert the actual parser/CRC failure,
so an early path refusal cannot give a false pass.

When tried on Python 3.12, all 23 portability tests and 19 inherited inspector
tests passed. The real inherited archive verified its two files with zero
hazards. A valid ZIP with a 258-byte UTF-8 filename now produces exit 2 and a
complete verified hazard report; a 255-byte name passes. Tests also cover
two-byte characters, emoji, nested paths, original decomposed spelling,
trusted-digest mismatch and exact CLI exit behavior. Results are retained in
`line-2/checks-27.json`. The demo's self-computed hash is an integrity identifier,
not independent authentication. These local checks do not certify every OS.
