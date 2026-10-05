# Liquidity dataset: star schema & data dictionary

Column-level notes, row counts and keys are written to `data/liquidity/README.md` on every run, from the registry in `scripts/liqsim/docs.py`. This page shows the **shape** and **which table answers which question**.

## Star schema
```
                         dim_date ────────────────────────────────┐
                            │                                     │
 dim_scenario ──┬── fact_bank_cashflow_stressed ── dim_product ── dim_counterparty_segment
                │           │                         │
                │     dim_time_bucket            dim_contract ── fact_bank_position
                │           │                         │      └── fact_hqla_holding
                │   fact_bank_cashflow_contractual ───┘
                │   fact_bank_cashflow_history (date, product, currency)
                │   fact_bank_survival (scenario, date)
                │
                ├── fact_corp_cashflow_forecast ──┬── dim_cf_category
                ├── fact_corp_cash_balance        ├── dim_bank_account ── dim_entity
                │   fact_corp_cashflow_actual ────┘
                │   fact_corp_invoice ── dim_counterparty
                │   dim_facility ── dim_entity
                │
                ├── fact_liquidity_metrics (reference)  ── dim_entity
                └── scenario_parameter (what-if baselines)
 dim_currency ── every fact with currency_code;   fact_fx_rate (history)
```
Rules:
- All relationships are many-to-one and single direction, from facts to dimensions.
- `fact_bank_position` and `fact_hqla_holding` both relate to `dim_contract`, `dim_product`, `dim_currency` and `dim_date`.
- `fact_liquidity_gap` is a reference-only table, not related to other tables. Its `view` and `currency_scope` columns are text, not keys.
- Use `fact_liquidity_metrics` and `fact_liquidity_gap` to **check** DAX, not to drive visuals, except for quick prototypes.

## Which table for which question
| Question | Table(s) | Key columns |
|---|---|---|
| LCR today and its trend | `fact_hqla_holding` + `fact_bank_position` + `dim_product` | `market_value_rc`, `encumbered`, `base_haircut`; `lcr_base_rc` × `lcr_rate` by `lcr_flow` |
| NSFR | `fact_bank_position` + `dim_product.nsfr_type` | `balance_rc` × `nsfr_factor` |
| Contractual maturity ladder | `fact_bank_cashflow_contractual` + `dim_time_bucket` | `total_cash_rc`, `bucket_key`, `flow_type` |
| Behavioural / stressed ladder | `fact_bank_cashflow_stressed` (≤ 1Y) + contractual `SCHEDULED` beyond | `amount_rc`, `flow_type` |
| Survival horizon | `fact_bank_survival` (ready-made) or CBC + cumulative stressed flows | `liquidity_position_rc` |
| What drove the 30-day stress outflow? | `fact_bank_cashflow_stressed` where `days_from_asof` ≤ 30 | `flow_type`, `product_code` |
| Funding mix & concentration | `fact_bank_position` + `dim_product` / `dim_counterparty_segment` | `balance_rc` |
| Bank historic cash flows | `fact_bank_cashflow_history` | `flow_type`, `amount_rc` |
| Corporate 13-week / 12-month cash forecast | `fact_corp_cashflow_forecast` + `fact_corp_cash_balance` | `amount_rc`, `closing_rc`, `headroom_rc` |
| Corporate actual cash and working capital | `fact_corp_cashflow_actual`, `fact_corp_invoice` | DSO from invoices (pay date − invoice date) |
| Facility headroom & covenants | `dim_facility`, `fact_corp_cash_balance` | `limit_local`, `drawn_asof_local`, `undrawn_available_rc` |
| Scenario assumptions | `scenario_parameter`, `dim_scenario` | `driver`, `value` |

## Conventions
- `*_rc` = reporting currency (`meta.reporting_currency`: USD in `default`, EUR in `eba_sls`); `*_local` = item currency.
- `dim_time_bucket` follows the config ladder: 9 Basel buckets plus `B10` non-maturity (`default`), or 21 ALMM C 66.01 buckets plus `BNM` (`eba_sls`).
- `fact_hqla_holding.hqla_level`: L1, L1B, L2A, L2B (LCR), or CB_ELIGIBLE (CBC only).
- Stressed flow types `MGMT_*` are management actions; survival is shown pre (`survival_days`) and post (`survival_days_post_mgmt`).

## Grain cheat-sheet
| Table | Grain | Approx. rows (medium) |
|---|---|---|
| `fact_bank_position` | contract × month-end (25) | 130k |
| `fact_bank_cashflow_contractual` | contract × payment date | 200k |
| `fact_bank_cashflow_stressed` | scenario × day × product × currency × flow type | 90k |
| `fact_bank_cashflow_history` | day × product × currency × flow type | 30k |
| `fact_corp_invoice` | invoice | 90k |
| `fact_corp_cashflow_forecast` | scenario × day × entity × category | 8k |
| `fact_corp_cash_balance` | scenario (incl. ACT) × day × account | 8k |
| `dim_date` | day from history start to last contractual flow (~26 years) | 9.5k |
