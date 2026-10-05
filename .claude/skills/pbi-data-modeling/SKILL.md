---
name: pbi-data-modeling
description: Design or change a Power BI semantic model as a star schema for treasury and liquidity data (bank ALM + corporate treasury) - as-of date, history vs projection, contractual / behavioural / stressed cash-flow facts, semi-additive snapshots (positions, HQLA, cash balances), stress-scenario dimension, maturity buckets, Basel LCR/NSFR attributes, facilities, invoices and FX rules. Aligned with the liquidity-data-simulator dataset in data/liquidity. Use before writing tables or relationships in TMDL, or when the user asks to "define the data model".
---

# Data modeling (treasury & liquidity)

The default source is the synthetic dataset in `data/liquidity/`:
- Read its `README.md` for keys, grain and the as-of date.
- Use `liquidity-powerbi/references/model-design.md` for the import list, friendly names and relationships.

This skill explains the *why*, and how to extend the model or map real sources onto it.

## Workflow
1. **Inventory the sources.**
   - Synthetic dataset: read `data/liquidity/README.md`.
   - Real data: profile with `pbi-power-query/scripts/profile_data.py`, or read the SQL DDL.
2. **Fix the core concepts first** (`references/treasury-liquidity-patterns.md` §1):
   - as-of date and projection horizon
   - which cash-flow view each source represents (contractual / behavioural / stressed)
   - sign convention (+ in / − out, balances positive)
   - scenario set
3. **Classify each table:**
   - **Snapshot fact:** positions, HQLA holdings, corporate cash balance. Semi-additive.
   - **Flow fact:** realised flows, contractual / stressed / forecast flows.
   - **Event fact:** invoices.
   - **Dimension:** date, scenario, currency, entity, product (with LCR/NSFR parameters), time bucket, segment, contract, counterparty, facility, CF category.
4. **State the grain of every fact** in one sentence, e.g. *"one row per contract per month-end"*, *"one row per scenario, day, product, currency and flow type"*.
5. **Define keys.** Use the dataset's codes as keys (`… Code`, `… Key`, `… Id`), unique and non-blank. Map orphan fact keys to an Unknown member in Power Query.
6. **Define relationships:** dimension (1) → fact (*), single direction, one active path. Two specific rules:
   - Don't relate `Dim Contract` to `Dim Product`, because the facts already carry `Product Code` (ambiguous path).
   - Reference tables (`Ref Liquidity Metrics`, `Ref Liquidity Gap`) are for reconciliation only.
7. **Date table:**
   - Use the dataset's `dim_date`. It spans history start to the last contractual flow (~26 years) and has `Days From Asof` and `Period Type`.
   - Mark it as the date table on `Date`.
   - Only use `templates/date-table.tmdl` when a source has no calendar. Its range must cover the projection horizon *and* the contractual tail.
   - Turn off auto date/time (`annotation __PBI_TimeIntelligenceEnabled = 0` in `model.tmdl`).
8. **Fill in `templates/model-spec.md`** and present it for approval. Only after approval, write TMDL (see `pbip-format`).

## Rules
- **Star schema.** `Dim Segment` hanging off `Dim Product` is the only accepted snowflake (tiny). No fact-to-fact relationships.
- **`Dim Scenario` = stress scenarios** (ACT, BASE, IDIO, MARKET, COMBINED, REVERSE). Budget or reforecast versions go in a separate `Dim Version`. Never mix the two.
- **Keep the regulatory parameters on `Dim Product`:** LCR basis, flow and rate; HQLA level and haircut; NSFR type and factors. Measures read them from there, so changing a rate means changing data, not DAX.
- **Snapshots are semi-additive:** one date per evaluation (`[Reporting Date]`, `[Corp Balance Date]`). Flows are additive.
- **Amounts** come in `… Local` and `… RC` (reporting currency) pairs. Report in RC. Never sum `Local` across currencies.
- **Naming:**
  - Tables: `Fact <Subject>`, `Dim <Entity>`, `Ref <Name>` (reconciliation), `WI <Name>` (what-if); measures in `_Measures`.
  - Columns: Title Case with acronyms kept (`Balance RC`, `LCR Rate`, `HQLA Level`).
- **Hide** keys, technical columns (`Days From Asof`, `NSFR Band`, `LCR Base RC`) and raw amount columns. Users interact through measures.
- **Data types:**
  - `decimal` for money
  - `double` for rates and factors
  - `summarizeBy: none` on rates, factors, days and keys
  - `sortByColumn` for month name, bucket label and scenario name
- **Keep it narrow:**
  - Import `Dim Contract` only if contract drill-through or concentration analysis is needed.
  - Drop `Fact Bank Survival` if the what-if DAX version is used instead.

## Questions to ask the user when unknown
- As-of date and projection horizon; whether forecasts are re-run (forecast vintages → `treasury-liquidity-patterns.md` §5).
- Regulatory framework and national discretion (Basel / SBV / EBA). Who sets the LCR/NSFR rates: the dataset or local rules?
- Sign convention of the real source cash flows (bank or customer perspective), and how non-maturity deposits are treated (contractual O/N vs behavioural core/non-core).
- Reporting currency, significant currencies for per-currency LCR, and the FX source for projections (spot vs forward).
- Corporate: minimum operating cash per entity, committed vs uncommitted facilities, covenants to monitor.

## References
- `references/treasury-liquidity-patterns.md`: core concepts, conformed dimensions, bank and corporate treasury table patterns, LCR/NSFR attributes for real sources, forecast vintages, FX rules, KPI → tables map.
- `templates/date-table.tmdl`: fallback calendar for sources without one.
- `templates/model-spec.md`: the proposal template.
