---
name: pbi-dax-measures
description: Write, organise and document DAX measures for treasury and liquidity reporting (bank ALM + corporate treasury) on the liquidity dataset - as-of / reporting-date snapshot patterns, cash-flow measures with the + in / - out sign convention, stress-vs-base variance, flow-only time intelligence, funding KPIs (LTD, CASA, wholesale reliance, concentration, NII/NIM), corporate treasury KPIs (cash, net debt, facility utilisation, weeks of cover, DSO/DPO, overdue AR, forecast accuracy) and guarded calculation groups. Use whenever adding or fixing measures in the semantic model.
---

# DAX measures (treasury & liquidity)

## Workflow
1. Read the model first: tables, columns, relationships and existing measures. Reuse base measures; never define a measure twice.
2. Build in layers:
   - **Foundation**: dates & scenario, snapshot balances, cash flows (`references/treasury-liquidity-measures.md`)
   - **Regulatory & stress**: HQLA/LCR, NSFR, gap, CBC/survival, what-if (`liquidity-powerbi/references/liquidity-measures.md`)
   - **Comparisons**: vs BASE, time intelligence on flows, as measures or as guarded calc groups (`references/calc-groups.md`)
3. Propose the list (folder · name · plain-English definition · sign · format) and get approval.
4. Write the measures into `tables/_Measures.tmdl` (see `pbip-format/references/tmdl-syntax.md`).
5. Validate with `pbip-format/scripts/validate_pbip.py`. Reconcile against `Ref Liquidity Metrics` (generator reference values) and tell the user the differences.

## Rules
- **Display folders** in `_Measures`:
  - `1. Dates & Scenario`
  - `2. Balances`
  - `3. Cash Flows`
  - `4. Variance`
  - `5. Bank Liquidity`
  - `6. Corporate Treasury`
  - `9. Helpers` (hidden)
  - plus the `L2–L9` folders from liquidity-powerbi
- **Documentation:** every measure has a `///` description stating the definition, the **sign** (+ in / − out, or "positive balance"), and the view (contractual, behavioural or stressed).
- **Sign convention:** cash flows are + received / − paid; balances are positive. A higher signed cash amount is better. **Don't** invert variance by account type, which is P&L logic and doesn't apply here. Invert only for measures shown as positive outflows, such as `Stressed 30D Net Outflow`.
- **Snapshots:** bank balances use `[Reporting Date]` and corporate cash uses `[Corp Balance Date]`, both with `REMOVEFILTERS('Dim Date')`. **Never** use `LASTDATE('Dim Date'[Date])`: the calendar runs to the 2050s contractual tail, so unfiltered cards go blank. Never `SUM` balances across dates.
- **Scenario:**
  - `Dim Scenario` holds stress scenarios: ACT, BASE, IDIO, MARKET, COMBINED, REVERSE.
  - Read it via `[Selected Scenario]`, which defaults to BASE.
  - Compare scenarios with `REMOVEFILTERS('Dim Scenario')` + a key filter.
  - Budgets and planning versions need a separate `Dim Version`.
- **Time intelligence on flow measures only**, with the calendar year-end `"12-31"`. For snapshots and ratios, compare two dates (`DATEADD` / `SAMEPERIODLASTYEAR` moves `[Reporting Date]`). Don't use YTD.
- **Format strings:**

  | Measure kind | Format string |
  |---|---|
  | Amounts | `#,##0` |
  | Signed cash flows and variances | `#,##0;(#,##0);-` |
  | Ratios | `0.0%` |
  | Ratio deltas | `+0.0%;-0.0%;0.0%` (state "pp" in the title) |
  | Days | `0` |
  | Millions | `#,##0.0,,"M"` |

- **DAX style:**
  - Use `VAR` / `RETURN` and `DIVIDE`.
  - Use column predicates in `CALCULATE`, not `FILTER(table)`.
  - Precompute in Power Query or the generator where possible.
- **Annualise** NIM, ROA/ROE and cost of risk using `[Annualisation Factor]`.
- **Blank, not 0,** when there's no data. Exception: survival "beyond horizon" is shown as a label (`Survival Label`).

## References
- `references/treasury-liquidity-measures.md`: the foundation library (dates, balances, flows, variance, flow TI, bank funding KPIs, corporate treasury KPIs, helpers).
- `references/calc-groups.md`: Time Intelligence (flows only, guarded), Stress Comparison (vs BASE), Currency View.
- `liquidity-powerbi/references/liquidity-measures.md`: HQLA/LCR, NSFR, gap, CBC/survival, what-if, corporate headroom.
