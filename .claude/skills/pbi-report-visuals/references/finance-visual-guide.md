# Finance & banking visual guide

> **Liquidity / treasury reports** (LCR, NSFR, maturity ladder, survival horizon, corporate cash forecast): use `liquidity-powerbi/references/liquidity-pages.md`. The pages below are for P&L-style finance reporting.

## Which visual for which question
| Question | Visual | Binding |
|---|---|---|
| Headline number vs target | `card` (value) + a second card or subtitle for var % | Values: Actual; second card: Var % vs Budget with `Var Color` font |
| Headline with trend and goal | `kpi` | Indicator: Actual YTD · TrendLine: Fiscal Period · Goal: Budget YTD |
| Monthly actual vs budget | `clusteredColumnChart` | Category: Year Month · Y: Actual, Budget |
| Trend vs prior year / forecast | `lineChart` | Category: Year Month · Y: Actual, Actual PY, Forecast |
| Volume + rate together (balances + NIM) | `lineClusteredColumnComboChart` | Category: Year Month · Y: Gross Loans · Y2: NIM % |
| Why did profit move? (bridge) | `waterfallChart` | Category: Account Group · Y: Var vs Budget (or Var vs PY) |
| Which units are over/under budget? | `clusteredBarChart` sorted by variance | Category: Cost Center/Branch · Y: Var vs Budget |
| P&L / income statement | `pivotTable` (matrix) | Rows: Report Line (or Account hierarchy) · Values: Actual, Budget, Var, Var %, Actual PY |
| Balance sheet | `pivotTable` | Rows: Statement Group → Account · Columns: Fiscal Period (latest 3) or none · Values: Closing Balance |
| Portfolio composition over time | `stackedColumnChart` | Category: Year Month · Y: Gross Loans · Series: IFRS9 Stage / DPD Bucket |
| Credit quality trend | `lineChart` | Y: NPL Ratio %, Stage 2 Ratio %, Coverage Ratio % (Y2) |
| Top/bottom N branches/customers | `clusteredBarChart` or `tableEx` with Top N filter | Category: Branch · Y: measure |
| Mix (≤ 4 parts) | `donutChart` | Category: Product Type · Y: Total Deposits |
| Transaction detail (drill-through) | `tableEx` on a drill-through page | Values: date, account, description, amount |

Avoid:
- gauges (they waste space)
- 3D charts or pies with more than 4 slices
- dual axes with unrelated units
- stacked bars for comparing non-base segments

## Recommended pages

### 1. Executive Summary ("Are we on track?")
- Header: title, Fiscal Year and Fiscal Period slicers, Entity slicer, "Data as of" text.
- KPI row (4 cards): Revenue, Operating Expenses, Net Profit, Cost-to-Income %. Each shows a var % vs budget subtitle.
- Main left: Actual vs Budget vs PY by month (column + line or clustered column).
- Main right: variance by division (bar, sorted).
- Bottom: P&L summary matrix (subtotal lines only).

### 2. P&L Detail ("Where exactly are we off?")
- Matrix rows: Report Line → Account. Columns: Actual, Budget, Var, Var %, Actual PY, Var vs PY.
- Conditional formatting: font colour from `Var Color` on Var and Var %.
- Right side: waterfall from Budget → Actual by Account Group.

### 3. Budget vs Actual by Cost Center
- Bar: Var vs Budget by cost center, sorted.
- Table: cost center, Actual YTD, Budget YTD, Var, Var %, FY Budget, % consumed.
- Line: cumulative YTD Actual vs Budget.

### 4. Balance Sheet
- Cards: Total Assets, Total Liabilities, Equity, LDR %.
- Matrix: assets / liabilities / equity groups with closing balance for the current period, prior month-end and prior year-end, plus movement.

### 5. Loan Portfolio & Credit Quality (banking)
- Cards: Gross Loans, NPL Ratio %, Coverage Ratio %, Cost of Risk %.
- Stacked column: Gross Loans by IFRS9 Stage over months.
- Line: NPL Ratio % and Stage 2 Ratio % trend.
- Bar: NPL Ratio % by product or segment.
- Table: top 10 branches by NPL balance.

### 6. Deposits & Funding (banking)
- Cards: Total Deposits, CASA Ratio %, LDR %, Weighted Avg Deposit Rate.
- Stacked column: deposits by product type over months.
- Combo: Total Deposits (columns) and CASA Ratio % (line).
- Bar: deposits by region/branch.

### 7. Profitability (banking)
- Cards: NII, NIM %, Fee Income, ROE %.
- Waterfall: Operating income → Opex → Impairment → PBT.
- Line: NIM % trend vs budget.

## Conditional formatting patterns
- **Variance font colour:** bind the `Var Color` measure (field value). See the matrix template in `visual-templates.md`.
- **Data bars on Var:** set them up in the Desktop UI. It's simpler to configure there than in raw PBIR.
- **Icons:** use the `Var Arrow` measure as a text column next to the variance instead of the built-in icon sets. It's easier to control.
