# Page layout grid (1280 × 720)

> **Match the page size of the existing pages** (read `page.json` `width`/`height`). Desktop's
> current default is **1920 × 1080**. For that size, multiply every x, y, width and height
> below by **1.5** (margin 24, gap 18), and use title text 24pt.

Grid rules:
- Margin 16, gap 12, so the usable width is 1248 (x 16 → 1264).
- Header band y 0–56.
- Content y 68 → 704.

`z` and `tabOrder` increase by 1000 per visual, in reading order (left→right, top→bottom).

## Standard executive layout
```
y=0   ┌──────────────────────── Header (title + slicers) ──────────────────────┐
y=68  │ KPI 1        │ KPI 2        │ KPI 3        │ KPI 4                     │ h=104
y=184 │ Main chart (trend)                     │ Side chart (variance bar)     │ h=260
y=456 │ Detail matrix / table                                                  │ h=248
y=704 └────────────────────────────────────────────────────────────────────────┘
```
| Element | x | y | width | height |
|---|---|---|---|---|
| Title textbox | 16 | 10 | 560 | 40 |
| Slicer 1 (Fiscal Year) | 760 | 6 | 160 | 46 |
| Slicer 2 (Period) | 932 | 6 | 160 | 46 |
| Slicer 3 (Entity) | 1104 | 6 | 160 | 46 |
| KPI 1 | 16 | 68 | 303 | 104 |
| KPI 2 | 331 | 68 | 303 | 104 |
| KPI 3 | 646 | 68 | 303 | 104 |
| KPI 4 | 961 | 68 | 303 | 104 |
| Main chart | 16 | 184 | 740 | 260 |
| Side chart | 768 | 184 | 496 | 260 |
| Detail | 16 | 456 | 1248 | 248 |

## Statement layout (P&L / balance sheet)
| Element | x | y | width | height |
|---|---|---|---|---|
| Title + slicers | as above | | | |
| Matrix | 16 | 68 | 800 | 636 |
| Waterfall / bridge | 828 | 68 | 436 | 312 |
| Supporting chart | 828 | 392 | 436 | 312 |

## Portfolio layout (banking)
| Element | x | y | width | height |
|---|---|---|---|---|
| KPI 1–4 | as executive | | | |
| Composition (stacked column) | 16 | 184 | 616 | 260 |
| Ratio trend (line) | 648 | 184 | 616 | 260 |
| Breakdown bar | 16 | 456 | 616 | 248 |
| Top-N table | 648 | 456 | 616 | 248 |

## Five KPI cards variant
Width 240.
- x positions: 16, 268, 520, 772, 1024 (gap 12)
- width = (1248 − 4×12) / 5 = 240

## Drill-through page
- Header with a back button (`actionButton`, created in Desktop) and a title.
- Full-width `tableEx` at x16 y68, w1248 h636.
- Set the page's drill-through field in Desktop: Format pane → Page information → Page type.
