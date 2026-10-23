# Clean-up after a template swap

Read after a background or template swap, before delivery.

## Decided by the user (2026-10-23)

- **Delete compliance codes everywhere**: 幻灯编号…, 本幻灯仅针对/仅供…医疗卫生专业人士…, PP-XXX-CN-…, on slides, layouts and masters. Remove only the matching paragraphs, and remove the shape only if nothing else is left in it, because the code was often a single line inside a content box.

## Not deleted for now

The user said to leave everything else for now. `apply` does not touch it; `audit` only lists it:

- References, abbreviation notes and annotations whose text box covers the new series mark (17-deck batch: about 190 boxes on 116 really covered pages).
- Body text, cards, charts and pictures covering the mark.
- Page numbers sitting on the mark.
- Text boxes parked outside the slide (85 in the 17-deck batch).
- Case-template fill-ins (2026.xx.xx, （文字描述）), very small text, and product names in literature.

## How

```text
python3 scripts/cleanup_after_swap.py audit <decks>... --mark x1,y1,x2,y2 \
    [--png-dir <renders> --background content.jpg]
python3 scripts/cleanup_after_swap.py apply <decks>... --mark x1,y1,x2,y2 --out-dir <new-dir>
```

- `apply` deletes compliance codes only. Everything else is reported.
- `--mark` is the series mark on the content image, in points on a 960×540 slide. Measure it from the template image. It was `730,490,945,530` for the 宫颈癌 series; for the 2026 慢性病 series, `750,455,945,512` is only an estimate.
- Overlapping boxes overstate the problem. With renders, `audit` measures how much of the mark area differs from the bare background; above 3% counts as covered.
- Write to a new directory, re-run `audit` on the output, and render only the pages that changed.
