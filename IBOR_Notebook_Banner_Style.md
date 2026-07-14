# IBOR / Solutions Onboarding — Notebook Banner Style

A reusable spec for the teal header banner used across the IBOR and ABOR training notebooks.
Drop the two markdown cells below at the very top of any notebook (banner first, breadcrumb second).

## Colours
| Token | Hex | Use |
|-------|-----|-----|
| Deep teal | `#143840` | Gradient start (top-left) |
| Mid teal | `#2B6264` | Gradient end (bottom-right) |
| Accent orange | `#FF4B31` | Eyebrow label |
| White | `#FFFFFF` | Title text |
| White 82% | `rgba(255,255,255,.82)` | Subtitle text |

Font: `'DM Sans', Arial, sans-serif` (falls back to Arial if DM Sans is unavailable).

## Cell 1 — Banner (markdown)
Replace the THREE bracketed values: eyebrow label, title, subtitle.

```html
<div style="background:linear-gradient(135deg,#143840 0%,#2B6264 100%);border-radius:14px;padding:32px 36px;color:#fff;font-family:'DM Sans',Arial,sans-serif;">
  <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#FF4B31;font-weight:700;margin-bottom:10px;">Solutions Onboarding &middot; IBOR Training</div>
  <div style="font-size:30px;font-weight:700;line-height:1.15;margin-bottom:10px;">IBOR NB00 &mdash; Instrument Enrichment &amp; Market Data</div>
  <div style="font-size:15px;color:rgba(255,255,255,.82);max-width:640px;line-height:1.55;">One-sentence description of what this notebook does and why it matters.</div>
</div>
```

## Cell 2 — Breadcrumb (markdown)
Bold the current notebook with `**NBxx**`.

```html
<sub>IBOR pack sequence: NB00 &nbsp;&rarr;&nbsp; NB01 &nbsp;&rarr;&nbsp; NB02 &nbsp;&rarr;&nbsp; <b>NB03</b> &nbsp;&rarr;&nbsp; NB04 &nbsp;&rarr;&nbsp; NB05 &nbsp;&rarr;&nbsp; NB06 &nbsp;&rarr;&nbsp; NB07 &nbsp;&rarr;&nbsp; NB08</sub>
```
(In Jupyter markdown you can also use `**NB03**` instead of `<b>NB03</b>`.)

## Conventions
- **Eyebrow**: always `Solutions Onboarding &middot; <Pack> Training` (e.g. `IBOR Training`, `ABOR Training`).
- **Title**: `<PACK> <NBxx> &mdash; <Notebook Title>`.
- **Subtitle**: one sentence, kept under ~640px width via `max-width`. Describe the outcome, not the steps.
- **Banner is always the FIRST cell**; breadcrumb is the SECOND. Any existing `# Title` markdown can stay beneath them.
- Use HTML entities: `&middot;` (·), `&mdash;` (em dash for the title only), `&rarr;` (arrow), `&amp;` (&), `&nbsp;` (spacing).
- Validation/summary notebooks use title `<PACK> &mdash; End-to-End Validation` and a breadcrumb of `Run last &middot; after <PACK> pack NB00 &rarr; NB08`.

## Applying to the whole set programmatically
The banner/breadcrumb were inserted as two new markdown cells at index 0 and 1 of each notebook,
leaving all existing cells (and code) untouched. To re-apply or refresh, remove the first two
cells if a banner is already present (detect by the eyebrow string `Solutions Onboarding &middot;`),
then prepend the new pair. This keeps the operation idempotent.

## Rendering notes
- Renders in Jupyter and JupyterHub (inline styles supported).
- Some minimal nbviewer-style renderers strip inline CSS; the text still shows, just unstyled.
- DM Sans renders if installed in the environment; otherwise Arial is used.
