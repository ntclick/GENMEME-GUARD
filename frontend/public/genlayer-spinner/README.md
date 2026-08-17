# GenLayer Portal — "Beacon" spinner

A loading spinner built directly from the GenLayer mark. Pure SVG + CSS, no
JavaScript, no `<defs>`, no `id` attributes — safe to render dozens of times
on one page.

## Source of truth

Palette and usage rules are taken from **[genlayer.com/brand](https://genlayer.com/brand)**:

| Token | Hex | Use |
| --- | --- | --- |
| Kinetic Cobalt | `#110FFF` | The one moving color — the arc only |
| Carbon Void | `#070707` | The mark, on a light ground |
| Ceramic Node | `#F5F5F5` | The mark, on a dark ground |

Their guidelines describe the mark as **"a static system variable"** that
**"must remain uncompromised"** and kept isolated for legibility. Their own
reference marks bear this out — the mark itself is always monochrome (black
on light, white on dark); Kinetic Cobalt appears only as a fill/background
accent (the app-icon chip), never as the mark's own linework.

This spinner takes that rule literally: **the mark itself never moves.** It
sits fixed at the centre, always upright, at its correct proportions, filled
in the correct monochrome for the ground it's on. All the loading motion —
the part that has to move for this to read as "loading" — lives in a Kinetic
Cobalt arc that orbits around it, plus a faint breathing pulse on the mark
timed to the same revolution. The mark is never split apart, recolored, or
rotated upside down.

## Files

| File | Use |
| --- | --- |
| `genlayer-spinner.css` | The component. Drop into the Portal's stylesheet. |
| `genlayer-spinner.html` | Markup to copy, plus a light/dark demo bed. |
| `GenLayerSpinner.jsx` | React component with `size` / `variant` / `mono` / `ground` / `label`. |
| `genlayer-spinner.svg` | Self-contained animated SVG for `<img>`, `background-image`, favicons, or docs. |

## Usage

```jsx
import GenLayerSpinner from './GenLayerSpinner'

<GenLayerSpinner />                                  {/* 48px, full page loads */}
<GenLayerSpinner size={96} />                        {/* route transitions   */}
<GenLayerSpinner size={16} variant="compact" mono /> {/* inside a button     */}
<GenLayerSpinner size={64} ground="dark" />          {/* dark modal, light page */}
```

Plain HTML — the `<svg>` block in `genlayer-spinner.html`, sized with one
custom property. The `d` attribute on the mark path is the logo itself —
don't edit it:

```html
<svg class="gl-spinner" style="--gl-spin-size: 48px" viewBox="0 0 100 100" role="status" aria-label="Loading">…</svg>
```

## Sizing

| Size | Variant | Where |
| --- | --- | --- |
| 16–24px | `compact` + `mono` | Buttons, table rows, inline with text |
| 32–48px | default | Cards, panels, section loaders |
| 64–128px | default | Full-page and route transitions |

`compact` drops the orbiting arc — its stroke reads as a smudge below about
28px — and lets the mark itself carry a slightly stronger breathing pulse.
Timing and palette are otherwise shared with the default variant.

## Colour and theme

`--gl-mark` and `--gl-arc` are the two custom properties that drive
everything. Theme resolution covers `prefers-color-scheme`, an explicit
`data-theme` on the root, and a local `--on-dark` / `--on-light` override for
a surface whose ground doesn't match the page (a dark modal in a light
Portal, or vice versa) — every rule sits at the same specificity, so the
local override always wins. `mono` drops the palette entirely and inherits
`currentColor` for both the mark and the arc, for use inline with text of any
color.

## Accessibility

- `role="status"` with `aria-label`, plus a `<title>`, so the loading state is
  announced. Pass `label={null}` when adjacent text already says it.
- `prefers-reduced-motion: reduce` stops the arc's rotation entirely (it
  becomes a static ring at reduced opacity) and drops the mark's animation to
  an opacity-only fade — no scale, no movement of any kind on the mark.
- The mark is bold, solid-filled geometry, not hairline strokes, so it stays
  legible down to 16px without a separate simplified silhouette.

## On the mark's geometry

The path was reconstructed by eye from GenLayer's published mark images —
straight edges only, matching the mark's own construction, and re-derived
independently rather than traced pixel-for-pixel. If GenLayer has an official
vector source (brand kit download), swap the `d` attribute for the exact
path; the CSS classes and animation are unaffected either way.

## Licence

Released to GenLayer for use in the Portal and its brand system.
