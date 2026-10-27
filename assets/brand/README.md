# Tely brand

The mark is a pair of headphones with a football between the ear cups: the match, heard. It sits on a
near-black tile in the phone UI's palette. On the app's own black background the tile edge disappears and only
the cream shape shows.

| Colour | Hex | Use |
|---|---|---|
| Near-black | `#0d0c0b` | Tile, ball patches, background, wordmark on light |
| Cream | `#f2ead8` | Headphones, ball, wordmark on dark |
| Pitch green | `#1f8a5a` | Primary buttons in the UI (not used in the logo) |

The hex values were sampled from the phone UI mock-up (unverified against the final UI code).

| File | Use |
|---|---|
| `tely-mark.svg`, `tely-mark-512.png` | App icon and avatar |
| `tely-favicon.svg`, `tely-favicon-32.png` | Browser tab. A bolder cut with a simpler ball so it stays clear at 16 px |
| `tely-apple-touch-180.png` | Home-screen icon. A square tile, because iOS rounds the corners itself |
| `tely-logo-dark.svg/.png` | Mark and wordmark on dark backgrounds (cream text) |
| `tely-logo-light.svg/.png` | Mark and wordmark on light backgrounds (near-black text) |

The wordmark is Fraunces at weight 800 (SIL Open Font License), converted to outlines, so the SVGs need no font
installed. The PNGs have transparent backgrounds and are 4× the SVG size.

`options/` keeps the other concepts we considered, with a comparison sheet. Those SVGs use live Fraunces text,
so they only render correctly where the font is installed.
