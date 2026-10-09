# Fonts for Lola's screen (offline)

Lola's screen loads these woff2 files locally, with `font-display: swap`.
If a file is missing, the screen falls back to `system-ui` and still works.
No CDN, no remote fonts: everything must be served from this folder so the
screen runs with the network off.

## woff2 files still to add

Drop these exact filenames here (latin subset, SIL OFL releases, e.g.
Fontsource 5.3.0):

| File | Family | Weight | Used for |
|---|---|---|---|
| `Fredoka-Medium.woff2` | Fredoka | 500 | Speaker name under / inside the frame (name-m, name-l) |
| `Fredoka-SemiBold.woff2` | Fredoka | 600 | The time, the day-part line, the Start button |
| `DMSans-Regular.woff2` | DM Sans | 400 | The reassurance line, the listening caption, the reply line |
| `DMSans-Bold.woff2` | DM Sans | 700 | (loaded for parity with the design system; not required on this screen yet) |

TODO: add the four woff2 files above. They are not committed yet.

The design system also lists `DMSans-Medium.woff2` (500) and the fonts are
SIL OFL. Lola's screen does not use DM Sans Medium, so it is not loaded here.
