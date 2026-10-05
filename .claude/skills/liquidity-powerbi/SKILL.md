---
name: liquidity-powerbi
description: Model and visualise the liquidity simulation dataset (data/liquidity) in Power BI - star schema for bank positions, HQLA, contractual/stressed cash flows and corporate cash forecasts; DAX for LCR (with HQLA caps), NSFR, maturity gap, counterbalancing capacity, survival horizon, corporate headroom; what-if parameters layered on scenarios; and liquidity dashboard pages. Use with pbip-format, pbi-dax-measures and pbi-report-visuals when building liquidity / stress-testing reports.
---

# Liquidity stress testing in Power BI

Works on the CSVs from the `liquidity-simulation` skill (`data/liquidity/`). Read `data/liquidity/README.md` first. It lists every table, its keys and the as-of date.

## Workflow
1. **Model:** follow `references/model-design.md`, which covers:
   - which tables to import
   - friendly names
   - relationships
   - the date table (use `dim_date` from the dataset, marked as the date table)
   - what-if tables

   Load the CSVs with the "Folder of CSVs" / single-CSV patterns from `pbi-power-query`, using a `DataFolder` parameter.
2. **Measures:** first add the foundation layer from `pbi-dax-measures/references/treasury-liquidity-measures.md` (dates, balances, flows, funding and treasury KPIs). Then copy from `references/liquidity-measures.md` into `_Measures`. For many measures × periods or scenarios, use the guarded calc groups in `pbi-dax-measures/references/calc-groups.md`. Display folders:
   - `L1. Scenario Parameters` (the foundation measures keep their own folders `1.`–`9.`)
   - `L2. HQLA & LCR`
   - `L3. NSFR`
   - `L4. Gap`
   - `L5. Survival`
   - `L6. Corporate`
   - `L9. Reconciliation`
3. **Reconcile:** before building pages, put the DAX `LCR %`, `NSFR %`, `Survival Days` and `CBC` next to the `fact_liquidity_metrics` values for every scenario in a table visual. Differences must be < 0.1%. If they aren't, fix the DAX. Don't change the reference.
4. **Pages:** use `references/liquidity-pages.md` (layouts and visual bindings) with the `pbi-report-visuals` theme and templates.

## Rules specific to liquidity
- **Balances are snapshots.** Positions and HQLA always use the reporting date (`[Reporting Date]`, the last month-end ≤ the selected date). Never sum them across months.
- **The scenario drives everything forward-looking.** Single-select the `Dim Scenario` slicer on pages with KPIs. Line charts can use Scenario as the legend; the measures read the scenario per series.
- **ACT vs projections:**
  - ACT has history (positions, actual flows) and no stressed flows.
  - Projection scenarios start the day after the as-of date.
  - Show "as-of" in every page title.
- **Signs:** + inflow, − outflow. Outflow bars show negative. Use a diverging colour (inflow teal `#2A9D8F`, outflow navy/red) consistently.
- **What-if parameters add to the selected scenario.** They don't replace it. Reset them to neutral values (0, or multiplier 1) before comparing scenarios, and show the active what-if values on the page.
- **Regulatory vs internal:** label the LCR under stress scenarios "Stressed LCR (internal)". Only ACT/BASE is the regulatory figure.
- **Synthetic data:** put a subtitle or footer "Synthetic data, for demonstration" on every page.
