---
name: pbi-report-visuals
description: Design and create Power BI report pages and visuals (PBIR visual.json) for finance and banking - executive summary, P&L, budget vs actual, balance sheet, loan and deposit portfolio pages - with layout grid, visual selection, IBCS-style variance colouring and the finance theme. Use when the user asks to create visualizations, pages, dashboards or to style the report.
---

# Report pages & visuals (finance & banking)

## Workflow
1. **Understand the questions.** Each page answers one question, for example "Are we on budget?" or "Is credit quality deteriorating?". List the audience and the decisions they make.
2. **Check the model.** Read the measures and columns that exist. If a measure the page needs is missing, add it first with the `pbi-dax-measures` skill. **Never bind raw numeric columns.**
3. **Propose the page plan:**
   - page name
   - an ASCII layout sketch
   - each visual: type, the fields in each role, and why that visual
   - slicers

   Use `assets/page-layouts.md` for coordinates and `references/finance-visual-guide.md` for visual choice. Wait for approval.
4. **Write PBIR:**
   - Create the page folder and `page.json`, and add the page to `pages.json`.
   - Create one folder and `visual.json` per visual from `references/visual-templates.md`.
   - Copy `$schema` URLs from existing Desktop-generated files.
5. **Validate** with `pbip-format/scripts/validate_pbip.py`.
6. **Hand off the theme:** tell the user to import `assets/finance-theme.json` (View → Themes → Browse for themes) the first time, and to reopen the report.

## Design rules
- **Canvas:** use the size of the existing pages. Desktop's default is 1920 × 1080, so scale the 1280 × 720 grid in `assets/page-layouts.md` by 1.5. Margins are 16 px and gaps 12 px at 1280 width. **Max 8 visuals per page**, including the KPI cards.
- **Reading order:** top-left most important. KPI row first, then the trend or bridge, then the detail table.
- Every number needs context: compare it with budget, prior year or a target. A bare total isn't enough.
- **Variance colours** (from the theme):
  - favourable = green `#1A7F5A`
  - unfavourable = red `#C23B22`
  - neutral = grey `#6B7280`

  Always pair colour with a sign or arrow (▲▼) for colour-blind users. For expense lines, "up" is bad: use the `Var Color` measure, not raw sign colouring.
- **Scenario styling (IBCS-inspired):**
  - Actual: solid navy `#1F3A5F`
  - Prior year: grey `#A0AEC0`
  - Budget: light outlined / pale blue `#A8C5DA`
  - Forecast: teal `#2A9D8F`

  Keep the same colour for the same scenario on every page.
- **Number display:**
  - Thousands or millions consistently per page, with the unit in the title, e.g. "Revenue (USD M)".
  - Negatives in brackets for variances.
  - Percentages to 1 decimal.
- **Chart choice:**
  - Time runs horizontally (column/line).
  - Categories run vertically (bar), sorted by value.
  - Bridges use a waterfall.
  - Statements use a matrix.
  - Pie/donut only for ≤ 4 parts of a whole.
  - Gauges: avoid.
- **Titles state the insight or the measure + unit.** Use a dynamic title measure where it helps.
- **Slicers** go in the header band: fiscal year, period, entity/branch. Use dropdown mode to save space. Sync them across pages in Desktop.
- **Accessibility:** set `tabOrder` top-left to bottom-right. Text has ≥ 4.5:1 contrast (the theme handles this). No information carried by colour alone.

## References
- `references/finance-visual-guide.md`: which visual for which finance or banking question, and recommended pages with their visuals.
- `references/visual-templates.md`: copy-ready `visual.json` for:
  - textbox title
  - card
  - KPI
  - clustered column (Actual vs Budget)
  - line trend
  - combo
  - waterfall bridge
  - matrix P&L with conditional formatting
  - bar ranking
  - table
  - slicer
- `assets/finance-theme.json`: the report theme.
- `assets/page-layouts.md`: grid coordinates for standard page layouts.
