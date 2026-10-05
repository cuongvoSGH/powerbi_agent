# Liquidity report pages

The coordinates follow `pbi-report-visuals/assets/page-layouts.md`, on a 1280 × 720 grid. Scale them by 1.5 on 1920 × 1080 pages. Every page has:
- a header: title, "as of <date> · Synthetic data", Scenario slicer (single-select, dropdown), Currency slicer
- the finance theme
- signs: + inflow, − outflow

Colours:

| Element | Colour |
|---|---|
| Scenarios: BASE | navy `#1F3A5F` |
| Scenarios: IDIO | teal `#2A9D8F` |
| Scenarios: MARKET | gold `#C9A227` |
| Scenarios: COMBINED | red `#C23B22` |
| Scenarios: REVERSE | plum `#7A5C8E` |
| Scenarios: ACT | grey `#A0AEC0` |
| Inflows | teal `#2A9D8F` |
| Outflows | navy `#1F3A5F` |
| Breach / limit lines | red `#C23B22` |

## 1. Liquidity Overview (bank), "Can we meet our obligations?"
| Visual | Type | Binding |
|---|---|---|
| KPI 1–4 | card | `LCR %` (subtitle `LCR Label`), `NSFR %`, `Survival Label`, `CBC` |
| LCR & NSFR trend | lineChart | Category: Dim Date[Year Month] (month-ends, ACT) · Y: `LCR %`, `NSFR %` · constant line 100% |
| LCR by scenario | clusteredBarChart | Category: Dim Scenario[Scenario Name] · Y: `LCR %` (ignore the page scenario slicer via Edit interactions) |
| Survival by scenario | tableEx | Scenario · `Survival Label` · `Stressed 30D Net Outflow` · `CBC` |

## 2. LCR Breakdown, "What drives the ratio?"
| Visual | Type | Binding |
|---|---|---|
| HQLA composition | stackedBarChart | Category: Dim Currency · Y: `HQLA L1`, `HQLA L2A`, `HQLA L2B` + card `HQLA Cap Adjustment` |
| Outflows by category | clusteredBarChart sorted | Category: Dim Product[Category] / [Product Name] · Y: `LCR Outflows` |
| LCR bridge | waterfallChart | Breakdown via a small disconnected table {HQLA, Outflows, Inflows capped, Surplus} with a SWITCH measure, or a matrix if preferred |
| Inflows vs cap | card pair | `LCR Inflows`, `LCR Inflows Capped` |

## 3. Maturity Ladder, "Where are the funding gaps?"
| Visual | Type | Binding |
|---|---|---|
| Gap by bucket | lineClusteredColumnComboChart | Category: Dim Time Bucket[Bucket Label] · Y: `Contractual Inflows`, `Contractual Outflows` (or behavioural) · Y2: `Cumulative Gap (Behavioural)`, `Cumulative Gap + CBC` |
| View toggle | slicer on a disconnected `Ladder View` table {Contractual, Behavioural} | Measures use `SWITCH(SELECTEDVALUE('Ladder View'[View]), …)` |
| Ladder detail | pivotTable | Rows: Dim Product[Category] → [Product Name] · Columns: Bucket Label · Values: `Behavioural Net Gap` |
| Gap ratio | card | `Gap % of Assets` at the 1M bucket (filter visual to B01–B03) |

## 4. NSFR & Funding, "Is the structure stable?"
| Visual | Type | Binding |
|---|---|---|
| ASF vs RSF | clusteredBarChart | Category: Dim Product[Category] · Y: `ASF`, `RSF` |
| Funding mix | donutChart (≤ 5 slices) or stacked bar | Category: Dim Product[Category] (liabilities) · Y: `Balance` |
| NSFR trend | lineChart | Year Month · `NSFR %` + 100% line |
| Concentration | tableEx | Top-10 wholesale contracts by `Balance` (Dim Contract drill-through) |

## 5. Scenario & What-if, "How bad could it get?"
| Visual | Type | Binding |
|---|---|---|
| What-if sliders | slicer (single value) × 6 | WI Runoff Multiplier, WI Drawdown Multiplier, WI Rollover Cut, WI Haircut Addon, WI Outflow Multiplier, WI FX Currency + WI FX Shock, Mgmt Actions |
| Scenario matrix | pivotTable | Rows: Scenario · Values: `LCR %`, `CBC`, `Stressed 30D Net Outflow`, `Survival Days` |
| 30-day stress by driver | waterfallChart | Category: Fact Bank CF Stressed[Flow Type] · Y: `Stressed Net CF` (page filter: Days From Asof ≤ 30) |
| Scenario assumptions | tableEx | Scenario Parameter: Driver, Product Code, Value (filtered to the selected scenario) |

## 6. Survival Horizon, "How many days do we last?"
| Visual | Type | Binding |
|---|---|---|
| Liquidity position | lineChart | Category: Dim Date[Date] (projection range) · Y: `Liquidity Position` · Legend: Dim Scenario[Scenario Name] (multi-select allowed here) · constant line at 0 (red) |
| Breach table | tableEx | Scenario · `Survival Label` · `CBC` · minimum position |
| Cumulative outflows by type | stackedAreaChart or stacked column (weekly) | Date (week) · `Stressed Net CF` · Legend Flow Type |

## 6b. EBA ALMM Maturity Ladder & Management Actions (eba_sls profile)
| Visual | Type | Binding |
|---|---|---|
| ALMM ladder | pivotTable | Rows: Dim Product[Side] → [Category] → [Product Name] · Columns: Dim Time Bucket[Bucket Label] (21 C 66.01 buckets) · Values: `Contractual Net Gap` |
| Ladder totals | lineClusteredColumnComboChart | Category: Bucket Label · Y: `Contractual Inflows`, `Contractual Outflows` · Y2: `Cumulative Gap (Contractual)`, `CBC Available` |
| CBC by level | stackedBarChart | Category: Fact HQLA Holding[HQLA Level] (L1, L1B, L2A, L2B, CB_ELIGIBLE) · Y: `HQLA After Haircut` + card `HQLA L1B Share %` |
| Pre vs post management actions | clusteredBarChart | Category: Scenario · Y: `Survival Days (pre-mgmt)`, `Survival Days (post-mgmt)` · constant line at the risk-appetite target (e.g. 90 days) |
| Position curve | lineChart | Date · `Liquidity Position` · Legend Scenario · slicer `Mgmt Actions` |
| Compliance note | textbox | "EBA-aligned illustration (DR 2015/61, EBA GL/2018/04, ALMM C 66.01). Synthetic data. Not covered: intraday, intragroup, template formats." |

## 7. Corporate Cash Forecast, "Do we have enough headroom?"
| Visual | Type | Binding |
|---|---|---|
| KPIs | card × 4 | `Corp Cash As-of`, `Corp Undrawn Available`, minimum `Corp Headroom`, `Corp Days to Breach` |
| 13-week cash flow | lineClusteredColumnComboChart | Category: week (Dim Date) · Y: flows by Dim CF Category[Activity] (stacked) · Y2: `Corp Closing Cash (What-if)`, `Corp Min Cash` |
| Headroom by entity | lineChart | Date · `Corp Headroom` · Legend: Dim Entity |
| Facilities | tableEx | Dim Facility: type, currency, Limit RC, Drawn Asof RC, maturity, covenant |
| What-if | slicers | WI Revenue Shock, WI DSO Shift Days, WI RCF Availability |

## 8. Corporate Actuals & Working Capital
| Visual | Type | Binding |
|---|---|---|
| Cash flow by IAS 7 activity | stackedColumnChart | Year Month · `Corp Actual Net Flow` · Legend Activity |
| DSO trend | lineChart | Year Month (invoice date) · `DSO (days)` |
| Open AR / AP ageing | clusteredBarChart | Due-date bucket · `Open AR`, `Open AP` |

## 9. Reconciliation (hidden)
Use the table in `liquidity-measures.md` §L9. Keep it in the report for auditors and hide it from navigation.
