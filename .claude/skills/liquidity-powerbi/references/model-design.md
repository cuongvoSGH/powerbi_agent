# Model design: liquidity dataset

## Tables to import (CSV → friendly name)
| CSV | Power BI table | Notes |
|---|---|---|
| dim_date | Dim Date | **Mark as date table** on `date`. Sort `month_name` by `month_number` and `year_month` by `year_month_key`. |
| dim_scenario | Dim Scenario | Sort `scenario_name` by `sort_order` |
| dim_currency | Dim Currency | |
| dim_entity | Dim Entity | |
| dim_time_bucket | Dim Time Bucket | Sort `bucket_label` by `sort_order` |
| dim_product | Dim Product | Keep the LCR/NSFR parameter columns (used by measures) |
| dim_counterparty_segment | Dim Segment | |
| dim_contract | Dim Contract | Optional, for drill-through only. 10k rows. |
| fact_bank_position | Fact Bank Position | |
| fact_hqla_holding | Fact HQLA Holding | |
| fact_bank_cashflow_contractual | Fact Bank CF Contractual | |
| fact_bank_cashflow_stressed | Fact Bank CF Stressed | |
| fact_bank_cashflow_history | Fact Bank CF History | |
| fact_bank_survival | Fact Bank Survival | Optional: ready-made curve. DAX can rebuild it with what-if. |
| dim_cf_category | Dim CF Category | Sort by `sort_order` |
| dim_counterparty | Dim Counterparty | |
| dim_bank_account | Dim Bank Account | |
| dim_facility | Dim Facility | |
| fact_corp_invoice | Fact Corp Invoice | |
| fact_corp_cashflow_actual | Fact Corp CF Actual | |
| fact_corp_cashflow_forecast | Fact Corp CF Forecast | |
| fact_corp_cash_balance | Fact Corp Cash Balance | |
| scenario_parameter | Scenario Parameter | Used by measures, hidden from report view |
| fact_liquidity_metrics | Ref Liquidity Metrics | Reconciliation only, hidden |
| fact_liquidity_gap | Ref Liquidity Gap | Reconciliation only, no relationships |

Column names: convert snake_case to Title Case in Power Query, e.g. `Table.TransformColumnNames(t, each Text.Proper(Text.Replace(_, "_", " ")))`, then fix acronyms (`Rc` → `RC`, `Cbc` → `CBC`, `Lcr` → `LCR`, `Nsfr` → `NSFR`, `Hqla` → `HQLA`, `Fx` → `FX`). The measures in `liquidity-measures.md` assume these names, e.g. `'Fact Bank Position'[Balance RC]`, `'Dim Product'[LCR Rate]`.

Types: dates → Date; `*_rc`, `*_local`, `amount*` → Fixed decimal; rates/factors/value → Decimal; keys → Text. `survival_days` → Whole number, nullable.

## Relationships (many → one, single direction)
| From (many) | To (one) |
|---|---|
| Fact Bank Position[Date], Fact HQLA Holding[Date], Fact Bank CF Contractual[Date], Fact Bank CF Stressed[Date], Fact Bank CF History[Date], Fact Bank Survival[Date], Fact Corp CF Actual[Date], Fact Corp CF Forecast[Date], Fact Corp Cash Balance[Date] | Dim Date[Date] |
| Fact Bank Position / Fact HQLA Holding / Fact Bank CF Contractual / Stressed / History [Product Code] | Dim Product[Product Code] |
| all facts [Currency Code] | Dim Currency[Currency Code] |
| Fact Bank Position / Fact HQLA Holding / Fact Bank CF Contractual [Contract Id] | Dim Contract[Contract Id] |
| Fact Bank Position / Fact Bank CF Contractual / Fact Bank CF Stressed [Bucket Key] | Dim Time Bucket[Bucket Key] |
| Fact Bank CF Stressed / Fact Bank Survival / Fact Corp CF Forecast / Fact Corp Cash Balance / Scenario Parameter / Ref Liquidity Metrics [Scenario Key] | Dim Scenario[Scenario Key] |
| Fact Corp * [Entity Code], Dim Facility[Entity Code], Dim Bank Account[Entity Code] | Dim Entity[Entity Code] |
| Fact Corp CF Actual / Forecast [Category Code] | Dim CF Category[Category Code] |
| Fact Corp Invoice[Counterparty Id] | Dim Counterparty[Counterparty Id] |
| Fact Corp Invoice[Invoice Date] | Dim Date[Date] (DSO/DPO trends; ageing uses `Due Date` as an attribute) |
| Dim Product[Segment Code] | Dim Segment[Segment Code] (snowflake is acceptable: tiny dimension) |

Notes:
- `Dim Contract` → `Dim Product` would create an ambiguous path with facts → `Dim Product`. **Don't** relate Dim Contract to Dim Product. The facts carry `Product Code` themselves.
- `Fact Bank Survival[Currency Scope]` and `Ref *[Currency Scope]` are text, not related. Filter them with a small disconnected slicer table, or with `"ALL"`.
- Hide all keys and the reference tables. Set `discourageImplicitMeasures`.

## What-if parameter tables (calculated, disconnected)
```dax
WI Runoff Multiplier    = GENERATESERIES ( 0.5, 3, 0.1 )     // scales RUNOFF flows (1 = scenario as generated)
WI Drawdown Multiplier  = GENERATESERIES ( 0.5, 3, 0.1 )     // scales DRAWDOWN flows
WI Rollover Cut         = GENERATESERIES ( 0, 1, 0.05 )      // share of scenario rollover removed (0 = none)
WI Haircut Addon        = GENERATESERIES ( 0, 0.30, 0.01 )   // added to every HQLA haircut
WI Outflow Multiplier   = GENERATESERIES ( 1, 2, 0.05 )      // multiplies LCR outflows
WI FX Shock            = GENERATESERIES ( -0.30, 0.30, 0.01 ) // extra change in reporting-currency value of the currency picked in WI FX Currency
WI FX Currency          = DISTINCT ( 'Dim Currency'[Currency Code] )  // disconnected copy; measure WI FX Shock Currency = SELECTEDVALUE('WI FX Currency'[Currency Code], "")
Mgmt Actions            = DATATABLE ( "View", STRING, { { "Pre-management actions" }, { "Post-management actions" } } )   // EBA pre/post toggle
WI Revenue Shock        = GENERATESERIES ( -0.50, 0, 0.05 )  // corporate receipts scaling
WI DSO Shift Days       = GENERATESERIES ( 0, 30, 1 )        // corporate receipts delayed
WI RCF Availability     = GENERATESERIES ( 0, 1, 0.05 )      // overrides corporate facility availability
```
In TMDL these are calculated tables (`partition … = calculated`), each with a `[Value]` column and a `… Value` measure, e.g. `WI Runoff Multiplier Value = SELECTEDVALUE('WI Runoff Multiplier'[Value], 1)`. Defaults are the neutral values: 1 for multipliers, 0 for add-ons, and blank (meaning use scenario) for RCF availability.

Use slicers in single-value slider mode on the Scenario & What-if page. `WI FX Currency` must be a **calculated table** (not related) so it does not filter the model. `Mgmt Actions` defaults to pre-management actions. Sync them to the Survival and Corporate pages.
