# Model spec: liquidity (EBA SLS, bank only) — load + relationships

Status: **approved and implemented** (tables, Power Query, relationships). Phase 2 implemented 2026-10-05: `_Measures` (foundation + L1, L2, L4, L5, L9), what-if / Mgmt Actions / Ladder View calculated tables, `Dim Date[Projection Week]`, 5 report pages. Reconciliation: `docs/reconciliation.md` (script `docs/reconcile_liquidity.py`).

- Source: `data/liquidity/` (synthetic, profile `eba_sls`), as-of **2026-09-30**, reporting currency **EUR**.
- Parameter: `DataFolder` (expressions.tmdl), trailing backslash.
- Power Query per table: `Csv.Document` (UTF-8, comma) → `PromoteHeaders` → `""` → null (all columns; `NaT` → null on `maturity_date`) → explicit rename snake_case → Title Case with acronyms (RC, LCR, NSFR, HQLA, CBC, FX, ASF, RSF, 30D, 6M, 1Y, LT6M, GE1Y, L1/L1B/L2A/L2B) → `TransformColumnTypes(..., "en-US")`.
- Types: dates `date` (dateTime, Short Date); `*_rc`, `*_local`, amounts, nominal → fixed decimal; rates, factors, haircuts, price, ratios, shares, value → double; keys/codes → text; days, sort orders, flags, year/month numbers → int64 (nullable where blank).
- Sign convention: cash flows + received / − paid; balances positive.

## Tables and grain

| Table | CSV | Grain | Key | Notes |
|---|---|---|---|---|
| Dim Date | dim_date | day (2024-09-30 → 2055-07-19, contiguous) | Date | Marked date table (`dataCategory: Time`, `isKey`). Month Name ← Month Number; Year Month ← Year Month Key |
| Dim Scenario | dim_scenario | scenario (ACT, BASE, IDIO, MARKET, COMBINED, EXTREME, REVERSE) | Scenario Key | Scenario Name sorted by Sort Order |
| Dim Currency | dim_currency | currency (EUR, USD, GBP) | Currency Code | |
| Dim Entity | dim_entity | entity (BANK) | Entity Code | |
| Dim Time Bucket | dim_time_bucket | bucket (22) | Bucket Key | Bucket Label sorted by Sort Order |
| Dim Product | dim_product | product (31) | Product Code | LCR/NSFR/HQLA parameters |
| Dim Segment | dim_counterparty_segment | segment (7, incl. `NA` = not applicable) | Segment Code | Snowflake off Dim Product |
| Dim Contract | dim_contract | contract (9,492) | Contract Id | Not related to Product/Currency/Segment |
| Fact Bank Position | fact_bank_position | contract × month-end | — | Snapshot, semi-additive |
| Fact HQLA Holding | fact_hqla_holding | security × month-end | — | Snapshot, semi-additive |
| Fact Bank CF Contractual | fact_bank_cashflow_contractual | contract × payment date × flow type | — | Contractual view |
| Fact Bank CF Stressed | fact_bank_cashflow_stressed | scenario × date × product × currency × flow type | — | Behavioural (BASE) / stressed |
| Fact Bank CF History | fact_bank_cashflow_history | date × product × currency × flow type | — | Actual |
| Fact Bank Survival | fact_bank_survival | scenario × currency scope × date | — | Cumulative position, not additive over dates |
| Fact FX Rate | fact_fx_rate | date × currency | — | |
| Scenario Parameter (hidden) | scenario_parameter | scenario × driver × (product \| currency \| HQLA level) | — | |
| Ref Liquidity Metrics (hidden) | fact_liquidity_metrics | date × scenario × entity × currency scope | — | Reconciliation only |
| Ref Liquidity Gap (hidden) | fact_liquidity_gap | view × currency scope × bucket | — | Reconciliation only, unrelated |

## Relationships (31; all many → one, single direction, active)

| From (many) | To (one) |
|---|---|
| [Date] on the 7 facts + Ref Liquidity Metrics | Dim Date[Date] |
| [Product Code] on Position, HQLA, CF Contractual, CF Stressed, CF History | Dim Product[Product Code] |
| [Currency Code] on the same 5 + Fact FX Rate | Dim Currency[Currency Code] |
| [Contract Id] on Position, HQLA, CF Contractual | Dim Contract[Contract Id] |
| [Bucket Key] on Position, CF Contractual, CF Stressed | Dim Time Bucket[Bucket Key] |
| [Scenario Key] on CF Stressed, Survival, Scenario Parameter, Ref Liquidity Metrics | Dim Scenario[Scenario Key] |
| Ref Liquidity Metrics[Entity Code] | Dim Entity[Entity Code] |
| Dim Product[Segment Code] | Dim Segment[Segment Code] |

Not related by design: Dim Contract → Product/Currency/Segment (ambiguous paths), `Currency Scope` columns, Ref Liquidity Gap, and Scenario Parameter's product/currency/HQLA columns.

Referential integrity checked on 2026-10-05: **0 orphan keys** across all 31 relationships.

## Hidden columns
- Facts: all FK/code columns (Date, Contract Id, Product Code, Currency Code, Bucket Key, Scenario Key), plus technical columns: Days From Asof, NSFR Band, LCR Base RC.
- Dims: Scenario Key, Bucket Key, Year Month Key, Sort Order, Dim Product[Segment Code].
- Whole tables: Scenario Parameter, Ref Liquidity Metrics, Ref Liquidity Gap.

## Next steps (not in this scope)
`_Measures` (foundation + L1–L9 liquidity folders), `discourageImplicitMeasures`, what-if tables, reconciliation against Ref Liquidity Metrics, pages.
