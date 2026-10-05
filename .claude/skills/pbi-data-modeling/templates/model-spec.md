# Model spec: <Report name>

_Status: DRAFT, awaiting approval · Date: <yyyy-mm-dd>_

## 1. Purpose & audience
- Business questions this report answers (3–6 bullets), e.g. *Can the bank meet 30-day stressed outflows?*, *How many days do we survive under COMBINED stress?*, *Does the corporate group keep headroom above minimum cash over 13 weeks?*
- Primary users (ALCO, Treasury, Risk, CFO):
- Refresh frequency / as-of cadence:

## 2. Assumptions (confirm or correct)
| Topic | Assumption |
|---|---|
| As-of date & horizon | <2026-09-30>; daily projection 365 days; contractual tail to final maturity |
| Data | Synthetic dataset `data/liquidity` (seed <42>) / real source <…> |
| Sign convention | Cash flows + received / − paid; balances positive (`Side Sign` gives direction) |
| Cash-flow views | Contractual (`Fact Bank CF Contractual`), behavioural = BASE, stressed = other scenarios (`Fact Bank CF Stressed`) |
| Scenarios | ACT, BASE, IDIO, MARKET, COMBINED, REVERSE (stress only; no budget versions) |
| Regulatory basis | Basel III LCR (BCBS 238) / NSFR (BCBS 295); national discretion: <none / SBV …> |
| Non-maturity deposits | Contractual: O/N. Behavioural: run-off curve per scenario. |
| Currency | Reporting currency <EUR / USD> (`… RC` columns); projections at as-of spot × scenario FX shock; per-currency LCR for significant currencies <EUR, USD, GBP> |
| Corporate | Minimum cash per entity; committed facilities only count as headroom |

## 3. Sources
| Source | Type | Rows | Used for |
|---|---|---|---|
| data/liquidity/fact_bank_position.csv | CSV | 134k | Fact Bank Position |

## 4. Tables
| Table | Kind | Grain (one row per …) | Key | Source / transform |
|---|---|---|---|---|
| Fact Bank Position | Snapshot | contract × month-end | Date + Contract Id | fact_bank_position.csv |
| Fact HQLA Holding | Snapshot | security × month-end | Date + Contract Id | fact_hqla_holding.csv |
| Fact Bank CF Stressed | Flow (projection) | scenario × day × product × currency × flow type | composite | fact_bank_cashflow_stressed.csv |
| Fact Corp Cash Balance | Snapshot (daily) | scenario × day × account | composite | fact_corp_cash_balance.csv |
| Dim Product | Dimension | product | Product Code | dim_product.csv (LCR/NSFR parameters) |
| Dim Scenario | Dimension | scenario | Scenario Key | dim_scenario.csv |
| Dim Date | Dimension | day | Date | dim_date.csv (marked date table) |
| _Measures | Measure table | — | — | — |

### Columns (visible columns only; hidden keys and technical columns are implied)
**Dim Product**: Product Name, Side, Category, Product Class, HQLA Level (parameters hidden)

## 5. Relationships
| From (many) | To (one) | Active | Direction | Note |
|---|---|---|---|---|
| Fact Bank Position[Date] | Dim Date[Date] | ✔ | Single | snapshot: measures pick `[Reporting Date]` |
| Fact Bank CF Stressed[Scenario Key] | Dim Scenario[Scenario Key] | ✔ | Single | |

## 6. Hierarchies
- Dim Product › Product Hierarchy: Side → Category → Product Name
- Dim Date › Calendar: Year → Quarter → Year Month → Date

## 7. Measures
| Folder | Measure | Definition (plain English) | Sign / view | Format |
|---|---|---|---|---|
| 1. Dates & Scenario | Reporting Date | Last month-end snapshot ≤ selected date | n/a | Short Date |
| L2. HQLA & LCR | LCR % | HQLA stock after haircuts & caps / net 30-day outflows | ratio; regulatory for ACT/BASE, internal for stress | 0.0% |
| L5. Survival | Survival Days | First projection day with CBC + cumulative stressed flow < 0 | days; stressed | 0 |

## 8. Report pages
| Page | Question it answers | Visuals |
|---|---|---|
| Liquidity Overview | Can we meet our obligations? | 4 KPI cards (LCR, NSFR, Survival, CBC), LCR/NSFR trend, LCR by scenario, survival table |

```
┌──────── Title · as of <date> · Synthetic data ── Scenario ▾ Currency ▾ ─┐
│ LCR %   │ NSFR %   │ Survival days │ CBC                                │
│ LCR & NSFR trend (100% line)          │ LCR by scenario                 │
│ Survival by scenario (table)                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## 9. Reconciliation
DAX vs `Ref Liquidity Metrics` for LCR %, NSFR %, CBC and Survival Days per scenario; tolerance < 0.1%.

## 10. Open questions
1. …

## 11. Files to be written
- `definition/tables/*.tmdl` (list)
- `definition/relationships.tmdl`, `definition/model.tmdl` (`ref table` lines)
- `definition/expressions.tmdl` (`DataFolder` parameter)
- `*.Report/definition/pages/...`
