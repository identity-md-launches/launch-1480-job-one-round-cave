# The Remembered Provision — record 07, named PNG v8

Mode: installed built-in raster image tool, `mcp__image__generate_image`;
no CLI/API fallback, environment lookup or key. The ancestral edit target was
recovered from record 06's artifact URL and SHA-256 verified, then inspected.
The tool has a prompt interface; its generated insert was saved at the named
output path and subsequently overwritten by the complete preserved wall.

Selected production prompt, verbatim:

> A sparse flat primitive cave-painting pictogram ON AN ENTIRELY PURE WHITE
> BACKGROUND. The pure white background must fill the full square, no dark
> background, no shadow, no vignette, no glow, no gradients. Center one rough
> charcoal-black pebble, two thin charcoal curved echo ripples just above the
> pebble; to the right a tiny shallow red-ochre outlined bowl containing three
> charcoal pebbles. One simple red-ochre uneven cord joins the pebble to the bowl.
> Small motif with large white margins. Hand-made worn burnt-stick lines, very
> simple Lascaux thumb pigment shapes, flat black and muted red ochre only, blank
> white interiors and white gaps. Two-dimensional, no lighting, no volume, no
> photographic or render appearance. No words, no letters, no numbers, no
> captions, no logos, no watermarks, no signatures, no borders, no frames, no
> hands, no stencils, no people, no political symbols. White background is only
> backing for pigment extraction; final artwork will be confined to an unchanged
> existing cave wall.

The first production requested the same echo pebble, bowl and joining cord with
white backing, but supplied a dark background and glow. It was discarded in
place. The selected second production was inspected and had the desired white
backing and spare worn pigment. No separate image was saved. The tool was asked
for 1024×1024 but returned 1254×1254; dimensions were read from actual bytes.

`finish_wall8.py` removed white in memory, mapped charcoal and red ochre to a
260×120 patch at (850,185), and blended pigment into the original rock. The patch
was vacant: outside the eye/knot, Pepe, hands, torch, scroll and other inherited
marks. 6,257 pixels changed, zero outside the patch. Every ancestor mark remains.
Whole-wall PNG and the actual JPEG were inspected using view_image. Both hands
have four fingers and one opposing thumb each; no new hand or stencil was added.
No prohibited text, logos, symbols, people or borders were observed.

Final files: `artifacts/gathering/wall-v8.png` and continuing `wall.png`, identical
1254×1254 8-bit RGB PNGs; `dist/gathering/07.jpg`, 512×512 baseline color JPEG.
Final wall SHA-256:
`846767d546efffd0fe4f223989c803aaafcb52e8c629b5528140be2dc380a5d5`.

Unmet visual requirements: none identified in local review. Limits: subjective
inspection is not independent artistic certification; inherited naturalistic
rock remains untouched outside the pigment footprint. The little upper-right
mark is subdued against dark rock and softens in the thumbnail.
