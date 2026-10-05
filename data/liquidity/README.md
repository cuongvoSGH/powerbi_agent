# Liquidity simulation dataset

> **SYNTHETIC DATA.** Generated for liquidity stress-testing demos. It does not describe any real institution.

- Generated: 2026-10-03 08:42 UTC in 5.3s
- As-of date: **2026-09-30** · history 24 months · daily projection 182 days
- Size preset: `medium` · seed `42` · currencies EUR, USD, GBP (reporting currency **EUR**)
- Config used: `config_used.yaml` (re-run with the same config and seed to reproduce byte-identical files)

## Headline metrics (as-of date)

**Bank**

| Scenario | LCR | NSFR | CBC (EUR bn) | 30d stressed net outflow (EUR bn) | Survival days (pre mgmt actions) | Survival days (post mgmt actions) |
|---|---|---|---|---|---|---|
| BASE | 147.9% | 117.1% | 1.80 | 0.06 | > horizon | > horizon |
| IDIO | 106.0% |  | 1.80 | 1.04 | > horizon | > horizon |
| MARKET | 111.1% |  | 1.73 | 0.77 | > horizon | > horizon |
| COMBINED | 84.6% |  | 1.73 | 1.33 | 106 | > horizon |
| EXTREME | 66.7% |  | 1.70 | 1.63 | 33 | 52 |
| REVERSE | 70.8% |  | 1.70 | 1.70 | 30 | 39 |

**Notes:** Reverse stress multiplier on (COMBINED - BASE) shocks: x1.419.

## Scenarios

- **ACT - Actual**: Historical actuals (no projection).
- **BASE - Baseline**: Business-as-usual funding plan: normal rollover, modest deposit growth.
- **IDIO - Idiosyncratic**: Name-specific: 3-notch downgrade, retail and corporate deposit withdrawals, wholesale non-renewal, collateral calls.
- **MARKET - Market-wide**: System-wide: HQLA price falls, unsecured interbank market closed, USD/GBP funding stress, facilities drawn.
- **COMBINED - Combined severe**: Severe but plausible combination of idiosyncratic and market-wide shocks (EBA GL/2018/04 para 124).
- **EXTREME - Extreme**: Extreme digital-run style shock (LiST 2019 'extreme' analogue): fast retail and corporate outflows, full wholesale run.
- **REVERSE - Reverse stress**: COMBINED shock scaled until the bank survives the target number of days (pre management actions).

### Scenario drivers

| Driver | BASE | IDIO | MARKET | COMBINED | EXTREME | REVERSE |
|---|---|---|---|---|---|---|
| lcr_outflow_multiplier | 1 | 1.3 | 1.2 | 1.5 | 1.8 | 1.70971 |
| hqla_haircut_addon [L1] | 0 | 0 | 0.02 | 0.02 | 0.03 | 0.0283885 |
| hqla_haircut_addon [L1B] | 0 | 0 | 0.05 | 0.05 | 0.08 | 0.0709712 |
| hqla_haircut_addon [L2A] | 0 | 0 | 0.1 | 0.1 | 0.15 | 0.141942 |
| hqla_haircut_addon [L2B] | 0 | 0 | 0.2 | 0.2 | 0.25 | 0.283885 |
| hqla_haircut_addon [CB_ELIGIBLE] | 0 | 0 | 0.08 | 0.08 | 0.12 | 0.113554 |
| fx_shock [EUR] | 0 | 0 | 0 | 0 | 0 | 0 |
| fx_shock [USD] | 0 | 0 | 0.1 | 0.1 | 0.15 | 0.141942 |
| fx_shock [GBP] | 0 | 0 | 0.05 | 0.05 | 0.08 | 0.0709712 |
| nmd_runoff_30d [DEP_RET_STABLE] | 0 | 0.04 | 0.02 | 0.05 | 0.06 | 0.0709712 |
| nmd_runoff_30d [DEP_RET_LESS] | 0 | 0.1 | 0.05 | 0.12 | 0.15 | 0.170331 |
| nmd_runoff_30d [DEP_RET_HIGHER] | 0 | 0.2 | 0.1 | 0.25 | 0.3 | 0.354856 |
| nmd_runoff_30d [DEP_OPER] | 0 | 0.15 | 0.08 | 0.18 | 0.2 | 0.255496 |
| nmd_runoff_365d [DEP_RET_STABLE] | -0.02 | 0.08 | 0.04 | 0.1 | 0.18 | 0.150331 |
| nmd_runoff_365d [DEP_RET_LESS] | -0.015 | 0.18 | 0.1 | 0.22 | 0.35 | 0.318565 |
| nmd_runoff_365d [DEP_RET_HIGHER] | -0.01 | 0.35 | 0.18 | 0.4 | 0.6 | 0.571964 |
| nmd_runoff_365d [DEP_OPER] | -0.01 | 0.25 | 0.15 | 0.3 | 0.45 | 0.430022 |
| rollover [DEP_RET_TERM] | 0.95 | 0.8 | 0.9 | 0.75 | 0.6 | 0.666115 |
| rollover [DEP_CORP_NONOP] | 0.9 | 0.5 | 0.7 | 0.4 | 0.2 | 0.190288 |
| rollover [DEP_FI] | 0.9 | 0.1 | 0.3 | 0 | 0 | 0 |
| rollover [IB_BORROW] | 1 | 0.2 | 0 | 0 | 0 | 0 |
| rollover [BOND_ISSUED] | 0.8 | 0 | 0 | 0 | 0 | 0 |
| rollover [COVERED_ISSUED] | 1 | 0.5 | 0.3 | 0.2 | 0 | 0 |
| rollover [LOAN_MORT] | 1 | 0.95 | 1 | 0.95 | 0.95 | 0.929029 |
| rollover [LOAN_RET] | 1 | 0.85 | 0.95 | 0.8 | 0.75 | 0.716115 |
| rollover [LOAN_SME] | 1 | 0.85 | 0.95 | 0.8 | 0.75 | 0.716115 |
| rollover [LOAN_CORP] | 1 | 0.8 | 0.9 | 0.75 | 0.7 | 0.645144 |
| rollover [IB_PLACE] | 1 | 0 | 0 | 0 | 0 | 0 |
| facility_drawdown_30d [FAC_RET] | 0 | 0.03 | 0.04 | 0.05 | 0.08 | 0.0709712 |
| facility_drawdown_30d [FAC_CORP_CREDIT] | 0 | 0.08 | 0.12 | 0.15 | 0.25 | 0.212914 |
| facility_drawdown_30d [FAC_CORP_LIQ] | 0 | 0.2 | 0.25 | 0.3 | 0.45 | 0.425827 |
| facility_drawdown_30d [FAC_FI] | 0 | 0.25 | 0.35 | 0.4 | 0.55 | 0.56777 |
| facility_drawdown_365d [FAC_RET] | 0.01 | 0.06 | 0.08 | 0.1 | 0.14 | 0.137748 |
| facility_drawdown_365d [FAC_CORP_CREDIT] | 0.015 | 0.15 | 0.2 | 0.25 | 0.35 | 0.348565 |
| facility_drawdown_365d [FAC_CORP_LIQ] | 0 | 0.35 | 0.4 | 0.45 | 0.6 | 0.638741 |
| facility_drawdown_365d [FAC_FI] | 0 | 0.4 | 0.5 | 0.55 | 0.7 | 0.780684 |
| downgrade_notches | 0 | 3 | 1 | 3 | 3 | 4.25827 |
| collateral_per_notch_pct_assets | 0.002 | 0.002 | 0.002 | 0.002 | 0.003 | 0.002 |
| collateral_call_day | 2 | 2 | 2 | 2 | 2 | 2 |
| mgmt_actions.lending_cut.start_day | 1 | 10 | 10 | 10 | 7 | 10 |
| mgmt_actions.lending_cut.rollover_reduction | 0 | 0.25 | 0.2 | 0.3 | 0.4 | 0.3 |
| mgmt_actions.asset_sale.day | 30 | 30 | 45 | 30 | 21 | 30 |
| mgmt_actions.asset_sale.pct_of_loans | 0 | 0.01 | 0.01 | 0.015 | 0.02 | 0.015 |
| mgmt_actions.asset_sale.discount | 0 | 0.15 | 0.25 | 0.2 | 0.25 | 0.2 |
| corp_dso_shift_days | 0 | 0 | 0 | 0 | 0 | 0 |
| corp_revenue_shock | 0 | 0 | 0 | 0 | 0 | 0 |
| corp_key_customer_defaults | 0 | 0 | 0 | 0 | 0 | 0 |
| corp_supplier_terms_cut_days | 0 | 0 | 0 | 0 | 0 | 0 |
| corp_rcf_availability | 1 | 1 | 1 | 1 | 1 | 1 |
| corp_capex_deferral | 0 | 0 | 0 | 0 | 0 | 0 |
| corp_dividend_suspended | 0 | 1 | 0 | 1 | 1 | 1 |
| reverse_shock_multiplier |  |  |  |  |  | 1.41942 |

## Tables

| Table | Rows | Grain | Description |
|---|---|---|---|
| `dim_date` | 11,250 | one row per day | Calendar from the first history month-end to the last contractual cash flow. |
| `dim_currency` | 3 | one row per currency | Currencies. |
| `fact_fx_rate` | 2,193 | date x currency | Daily FX history (seeded GBM anchored to the as-of spot). |
| `dim_entity` | 1 | one row per entity | Reporting entities: the bank, the corporate group and its subsidiaries. |
| `dim_scenario` | 7 | one row per scenario | Scenarios. ACT = actual history; others are projections from the as-of date. |
| `scenario_parameter` | 307 | scenario x driver x (product | currency | HQLA level) | Every scenario driver value (long format) - use for what-if baselines in Power BI. |
| `dim_time_bucket` | 22 | one row per bucket | Maturity ladder buckets measured from the as-of date. |
| `dim_product` | 31 | one row per product | Bank products with Basel LCR / NSFR parameters. |
| `dim_counterparty_segment` | 7 | one row per segment | Bank counterparty segments. |
| `dim_contract` | 9,492 | one row per contract | Bank contracts (loans, deposits, securities, facilities, accounts). |
| `fact_bank_position` | 135,480 | contract x month-end | Month-end balances per contract with LCR / NSFR inputs. |
| `fact_hqla_holding` | 4,154 | security x month-end | HQLA stock (reserves and Level 1/2A/2B securities) at market value. |
| `fact_bank_cashflow_history` | 30,210 | date x product x currency x flow type | Realised bank cash flows. |
| `fact_bank_cashflow_contractual` | 235,803 | contract x payment date x flow type | Contractual future cash flows at the as-of date (to final maturity). NMD balances shown as repayable on demand. |
| `fact_bank_cashflow_stressed` | 67,999 | scenario x date x product x currency x flow type | Daily projected bank cash flows per scenario (behavioural). HQLA principal excluded - it is in the counterbalancing capacity. |
| `fact_bank_survival` | 4,368 | scenario x currency scope x date | Daily liquidity position = counterbalancing capacity + cumulative net stressed flow. |
| `fact_liquidity_metrics` | 124 | date x scenario x entity x currency scope | Reference metrics computed by the generator - reconcile Power BI measures against these. |
| `fact_liquidity_gap` | 588 | view x currency scope x bucket | Reference maturity ladder (reporting currency). |

### Keys, relationships and column notes

**`dim_date`**: key (date)
- `date`: Calendar date
- `period_type`: History / As-of / Projection / Contractual tail
- `days_from_asof`: Days after the as-of date (negative = history)
- `is_business_day`: Mon-Fri flag

**`dim_currency`**: key (currency_code)
- `rate_to_rc_asof`: USD value of 1 unit at as-of (spot used for all projections)

**`fact_fx_rate`**: key (date, currency_code)
- `date` -> `dim_date.date`
- `currency_code` -> `dim_currency.currency_code`
- `rate_to_rc`: USD value of 1 unit of currency

**`dim_entity`**: key (entity_code)
- `entity_type`: Bank / Corporate
- `parent_entity_code`: Group parent

**`dim_scenario`**: key (scenario_key)
- `scenario_type`: actual / baseline / stress / reverse

**`scenario_parameter`**: key (scenario_key, driver, product_code, currency_code, hqla_level)
- `scenario_key` -> `dim_scenario.scenario_key`
- `driver`: Driver name (see config scenario_drivers)
- `value`: Driver value (fractions as decimals)

**`dim_time_bucket`**: key (bucket_key)
- `in_lcr_30d`: 1 if the bucket lies inside the 30-day LCR window
- `in_6m`: 1 if within six months
- `in_1y`: 1 if within one year
- `bucket_key`: Configurable ladder (config time_buckets); EBA profile = ALMM C 66.01

**`dim_product`**: key (product_code)
- `segment_code` -> `dim_counterparty_segment.segment_code`
- `side_sign`: +1 asset, -1 liability / equity / off-balance
- `lcr_basis`: hqla | balance | due_30d | none
- `lcr_flow`: outflow | inflow | hqla
- `lcr_rate`: Basel run-off / inflow rate
- `nsfr_type`: ASF (funding) or RSF (requirement)
- `nsfr_factor_*`: Factor by residual maturity band

**`dim_counterparty_segment`**: key (segment_code)

**`dim_contract`**: key (contract_id)
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `segment_code` -> `dim_counterparty_segment.segment_code`
- `notional_local`: Original principal (dated) or as-of balance (non-maturity)
- `is_live_at_asof`: 1 if outstanding at the as-of date
- `encumbered`: 1 if pledged (excluded from HQLA)

**`fact_bank_position`**: key (date, contract_id)
- `date` -> `dim_date.date`
- `contract_id` -> `dim_contract.contract_id`
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `bucket_key` -> `dim_time_bucket.bucket_key`
- `principal_due_30d_local`: Principal falling due in the next 30 days
- `lcr_base_rc`: Amount the product's LCR rate applies to (balance or due-30d)
- `nsfr_factor`: ASF/RSF factor for this residual maturity (encumbered HQLA overridden)
- `bucket_key`: Residual-maturity bucket (B01 for on-demand, B10 non-maturity)

**`fact_hqla_holding`**: key (date, contract_id)
- `date` -> `dim_date.date`
- `contract_id` -> `dim_contract.contract_id`
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `hqla_level`: L1 (Level 1 excl. covered bonds), L1B (EHQ covered bonds), L2A, L2B, or CB_ELIGIBLE (central-bank-eligible non-HQLA: CBC only, not LCR)
- `price`: Clean price (1.0 = par)
- `base_haircut`: Regulatory haircut of the holding (HQLA level / product override / central bank haircut)

**`fact_bank_cashflow_history`**: key (date, product_code, currency_code, flow_type)
- `date` -> `dim_date.date`
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `flow_type`: ORIGINATION / PRINCIPAL / INTEREST / NMD_NET_CHANGE / NMD_INTEREST
- `amount_local`: + received by the bank, - paid

**`fact_bank_cashflow_contractual`**: key (date, contract_id, flow_type)
- `date` -> `dim_date.date`
- `contract_id` -> `dim_contract.contract_id`
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `bucket_key` -> `dim_time_bucket.bucket_key`
- `flow_type`: SCHEDULED / NMD_ON_DEMAND
- `*_rc`: Converted at as-of spot

**`fact_bank_cashflow_stressed`**: key (scenario_key, date, product_code, currency_code, flow_type)
- `scenario_key` -> `dim_scenario.scenario_key`
- `date` -> `dim_date.date`
- `product_code` -> `dim_product.product_code`
- `currency_code` -> `dim_currency.currency_code`
- `bucket_key` -> `dim_time_bucket.bucket_key`
- `flow_type`: CONTRACTUAL_PRINCIPAL / CONTRACTUAL_INTEREST / ROLLOVER / RUNOFF / DRAWDOWN / COLLATERAL_CALL / MGMT_* (management actions)
- `amount_rc`: At as-of spot x (1 + scenario FX shock)

**`fact_bank_survival`**: key (scenario_key, currency_scope, date)
- `scenario_key` -> `dim_scenario.scenario_key`
- `date` -> `dim_date.date`
- `currency_scope`: ALL or a currency code (not a key)
- `cbc_available_rc`: CBC monetised by that day (cbc_availability_day)
- `liquidity_position_rc`: Before management actions; breach when < 0
- `liquidity_position_post_mgmt_rc`: After management actions (MGMT_* flows)

**`fact_liquidity_metrics`**: key (date, scenario_key, entity_code, currency_scope)
- `date` -> `dim_date.date`
- `scenario_key` -> `dim_scenario.scenario_key`
- `entity_code` -> `dim_entity.entity_code`
- `currency_scope`: ALL or currency code (not a key)
- `lcr_ratio`: HQLA / net 30-day outflows
- `nsfr_ratio`: ASF / RSF
- `survival_days`: First projection day with negative position before management actions (blank = survives horizon)
- `survival_days_post_mgmt`: Same after management actions
- `hqla_l1b_share`: Share of L1B covered bonds in HQLA after caps (EU cap 70%)

**`fact_liquidity_gap`**: key (view, currency_scope, bucket_key)
- `bucket_key` -> `dim_time_bucket.bucket_key`
- `view`: CONTRACTUAL or a scenario key (behavioural within horizon, contractual beyond)

## Methodology & simplifications

- Sign convention: **+ cash received, - cash paid** (bank and corporate). Balances are positive.
- Bank contracts: amortising (annuity), bullet in months (periodic coupon), bullet in days, non-maturity deposits (random-walk balance), static items, undrawn facilities. Each product/currency is scaled so the as-of balance sheet matches `bank.total_assets_rc` and the configured shares; assets = liabilities + equity at the as-of date only.
- LCR: Basel III (BCBS 238) rates from config; HQLA = unencumbered market value after haircuts with the 15% (L2B) and 40% (L2) caps; inflows capped at 75% of outflows; only principal due within 30 days counts for term items (interest ignored). Stressed LCR applies scenario haircut add-ons, FX shock and an outflow multiplier.
- NSFR: Basel III (BCBS 295) ASF/RSF factors by residual maturity of the whole contract (amortising loans are not split by instalment); encumbered HQLA uses `nsfr_encumbered_rsf`.
- Survival horizon: unencumbered HQLA after scenario haircuts is the counterbalancing capacity (available day 1); stressed flows exclude HQLA principal to avoid double counting.
- Behavioural flows: maturing principal x rollover share is renewed; non-maturity deposits run off on a front-loaded curve (tau 7 days to day 30, linear to day 365); undrawn facilities are drawn on the same curve shape; a one-off collateral call hits on the configured day.
- Projections use the as-of spot rate x (1 + scenario FX shock); history uses daily rates.
- Corporate: invoices are simulated from revenue (seasonality, growth) with customer payment delays; revolvers/overdraft balance cash to the minimum in history; forecasts are expected values with no automatic revolver draw - headroom = cash + undrawn available - minimum cash.
