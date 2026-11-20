# Pixel-snap compatibility check

From `asset/`, run `npm ci --prefix pipeline/pixel_snap --include=optional` then
`npm --prefix pipeline/pixel_snap test`. The suite uses the public Python CLI
from an unrelated working directory; no provider, game files or upstream repo
are needed.

The three small Factory-owned inputs are an opaque RGB room (259×131), an RGBA
sprite with an interior cutout and translucent fringes (47×59), and an indexed
PNG icon with transparency (19×15). These are technical fixtures, not game art.

`upstream.json` is independent of the implementation under test. The oracle
was `Renaiss-Protocol/renaiss-verse:scripts/pixel_snap.js` at `d413e7f5`,
SHA-256 `c93ecf52e9f74daf0609448d586ea5ca322a52d9cc208ff467570753dd4496f1`
(Node 22.14, Sharp 0.34.5, libvips 8.17.3). For each fixture it was run with
each named profile, plus `balanced` with `targetScale: 5`:

- `rgba256`: SHA-256 of the upstream PNG's **decoded row-major RGBA bytes**,
  not its PNG compression stream. Profile, scale, grid and palette metadata
  were taken from the upstream return value.
- `gridRgba256`: SHA-256 of the original's four-channel raw buffer as passed to
  its final Sharp constructor, **before** the nearest-neighbour resize.
  This checks the actual cells even for dimensions not divisible by the scale.

Do not refresh these references from the Factory implementation.
