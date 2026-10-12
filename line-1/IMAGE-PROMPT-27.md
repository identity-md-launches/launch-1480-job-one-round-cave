# The Remembered Echo

Built-in imagegen mode; input/edit target was the recovered record-26 wall,
SHA-256 `4b1e252d0d0695b594fee75ea2eea85da43f611b8f6ee62f769023b95c9cb76d`.

Exact generation prompt:

> Use case: precise-object-edit. Edit the provided existing square cave wall. Preserve the exact full 1254 by 1254 framing, rock texture, cracks, colors, torchlight, and ALL existing paintings, especially the central Pepe frog and his existing five-digit hands. Only ADD a small weathered charcoal-black cave pigment mark in the vacant rock directly ABOVE Pepe's head, within x=520..725 and y=230..330 of the original image. The added mark represents an echo: one uneven charcoal pebble on the left and two short curved ripples to its right, all crude hand-drawn burnt-stick pigment, with bare rock showing through. No new frog, hand or handprint. The existing central frog must remain completely unchanged, not redrawn. All old motifs must be preserved exactly. No letters, numbers, captions, logos, signature, borders, watermarks or symbols resembling text. Keep it restrained, ancient, imperfect and small. Do not regenerate or enhance background. Return the entire original square wall with only this additive pigment mark.

The tool returned a full square image but altered surrounding rock texture.
Finalization retained only its dark, substantially changed pigment within
`[550,245,130,110]` (x, y, width, height). Each retained color channel is at most
the original channel, with softened thresholds at the pigment edges. All other
original pixels were restored exactly. The generated draft was overwritten by
the completed wall; no extra picture was retained in the workspace.

The final PNG and the required JPEG were visually inspected. The new mark adds
no hand or text. The ancestor's five digits per hand were counted and preserved.
See `wall-review-27.json` for the pixel preservation receipt and visual limits.
