# Data profile

| Table | Rows | Columns | Candidate key(s) | Guess |
|---|---|---|---|---|
| dim_contract | 9,492 | 17 | contract_id | FACT (has measures + several keys/dates) |
| dim_counterparty_segment | 7 | 2 | segment_name | DIMENSION (unique key, descriptive columns) |
| dim_currency | 3 | 4 | currency_code | DIMENSION (unique key, descriptive columns) |
| dim_date | 11,250 | 12 | date, days_from_asof | DIMENSION (unique key, descriptive columns) |
| dim_entity | 1 | 5 | entity_code, currency_code | DIMENSION (unique key, descriptive columns) |
| dim_product | 31 | 19 | product_code | DIMENSION (unique key, descriptive columns) |
| dim_scenario | 7 | 5 | scenario_key | DIMENSION (unique key, descriptive columns) |
| dim_time_bucket | 22 | 8 | bucket_key | DIMENSION or small fact (check) |
| fact_bank_cashflow_contractual | 235,803 | 13 | — | FACT (has measures + several keys/dates) |
| fact_bank_cashflow_history | 30,210 | 6 | — | FACT (has measures + several keys/dates) |
| fact_bank_cashflow_stressed | 67,999 | 9 | — | FACT (has measures + several keys/dates) |
| fact_bank_position | 135,480 | 13 | — | FACT (has measures + several keys/dates) |
| fact_bank_survival | 4,368 | 7 | — | FACT (has measures + several keys/dates) |
| fact_fx_rate | 2,193 | 3 | — | FACT (has measures + several keys/dates) |
| fact_hqla_holding | 4,154 | 11 | — | FACT (has measures + several keys/dates) |
| fact_liquidity_gap | 588 | 7 | — | FACT or unclear grain (no single-column key) |
| fact_liquidity_metrics | 124 | 26 | — | FACT (has measures + several keys/dates) |
| scenario_parameter | 307 | 6 | — | FACT (has measures + several keys/dates) |

## dim_contract
Rows: 9,492 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| contract_id | string | KEY (unique) | 0.0 | 9,492 |  | B000001, B000002, B000003, B000004 |
| product_code | string | foreign key? | 0.0 | 29 |  | BOND_ISSUED, CASH_CB, COVERED_ISSUED, DEP_CORP_NONOP |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, USD, GBP |
| segment_code | string | foreign key? | 0.0 | 6 |  | FI, CENTRAL_BANK, CORPORATE, RETAIL |
| product_class | string | attribute | 0.0 | 6 |  | bullet_m, static, bullet_d, nmd |
| start_date | dateTime | date | 0.0 | 3,657 | 1995-04-12 … 2026-09-30 | 2020-02-18, 2021-02-08, 2021-03-26, 2021-11-05 |
| maturity_date | string | attribute | 0.0 | 3,093 |  | 2027-01-18, 2025-08-08, 2028-01-26, 2026-04-05 |
| term_months | int64 (stored as float, has nulls?) | measure | 26.8 | 351 | 1.00 … 360.00 | 83.0, 54.0, 82.0, 53.0 |
| term_days | int64 (stored as float, has nulls?) | measure | 12.3 | 1,255 | 1.00 … 10,958.00 | 2526.0, 1642.0, 2497.0, 1612.0 |
| pay_day | int64 | attribute | 0.0 | 32 | 0 … 31 | 18, 8, 26, 5 |
| coupon_months | int64 | attribute | 0.0 | 4 | 0 … 12 | 12, 0, 1, 3 |
| interest_rate | decimal | measure | 0.0 | 9,155 | 0.00 … 0.10 | 0.0388584453, 0.0379357315, 0.0399738762, 0.0390948355 |
| notional_local | double | measure | 0.0 | 9,492 | 67,253.87 … 1,000,000,000.00 | 143176956.74, 21075786.85, 11167429.21, 15911257.27 |
| hqla_level | string | attribute | 97.7 | 4 |  | L1, L1B, L2A, L2B |
| encumbered | int64 | attribute | 0.0 | 2 | 0 … 1 | 0, 1 |
| is_live_at_asof | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |
| notional_rc_at_asof_fx | double | measure | 0.0 | 9,492 | 78,687.02 … 1,000,000,000.00 | 143176956.74, 21075786.85, 11167429.21, 15911257.27 |

## dim_counterparty_segment
Rows: 7 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| segment_code | string | foreign key? | 14.3 | 6 |  | RETAIL, SME, CORPORATE, FI |
| segment_name | string | attribute | 0.0 | 7 |  | Retail, SME, Corporate, Financial institution |

## dim_currency
Rows: 3 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| currency_code | string | KEY (unique) | 0.0 | 3 |  | EUR, USD, GBP |
| currency_name | string | attribute | 0.0 | 3 |  | Euro, US Dollar, Pound Sterling |
| rate_to_rc_asof | double | attribute | 0.0 | 3 | 0.92 … 1.17 | 1.0, 0.92, 1.17 |
| is_reporting_currency | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |

## dim_date
Rows: 11,250 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 11,250 | 2024-09-30 … 2055-07-19 | 2024-09-30, 2024-10-01, 2024-10-02, 2024-10-03 |
| year | int64 | attribute | 0.0 | 32 | 2024 … 2055 | 2024, 2025, 2026, 2027 |
| quarter | string | attribute | 0.0 | 4 |  | Q3, Q4, Q1, Q2 |
| month_number | int64 | foreign key? | 0.0 | 12 | 1 … 12 | 9, 10, 11, 12 |
| month_name | string | attribute | 0.0 | 12 |  | Sep, Oct, Nov, Dec |
| year_month | string | attribute | 0.0 | 371 |  | 2024-09, 2024-10, 2024-11, 2024-12 |
| year_month_key | int64 | foreign key? | 0.0 | 371 | 202409 … 205507 | 202409, 202410, 202411, 202412 |
| day_of_week | string | attribute | 0.0 | 7 |  | Mon, Tue, Wed, Thu |
| is_business_day | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |
| is_month_end | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |
| days_from_asof | int64 | attribute | 0.0 | 11,250 | -730 … 10519 | -730, -729, -728, -727 |
| period_type | string | attribute | 0.0 | 4 |  | History, As-of, Projection, Contractual tail |

## dim_entity
Rows: 1 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| entity_code | string | KEY (unique) | 0.0 | 1 |  | BANK |
| entity_name | string | attribute | 0.0 | 1 |  | SimBank EU (synthetic) |
| entity_type | string | attribute | 0.0 | 1 |  | Bank |
| currency_code | string | KEY (unique) | 0.0 | 1 |  | EUR |
| parent_entity_code | double | foreign key? | 100.0 | 0 | nan … nan |  |

## dim_product
Rows: 31 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| product_code | string | KEY (unique) | 0.0 | 31 |  | CASH_CB, SEC_L1, SEC_L1B_CB, SEC_L2A |
| product_name | string | attribute | 0.0 | 31 |  | Cash & central bank reser, EU sovereign bonds (Level, Extremely high quality co, Level 2A corporate & cove |
| side | string | attribute | 0.0 | 4 |  | Asset, Liability, Equity, Off-Balance |
| category | string | attribute | 0.0 | 12 |  | Cash & Reserves, Securities, Interbank, Loans |
| segment_code | string | foreign key? | 12.9 | 6 |  | CENTRAL_BANK, SOVEREIGN, FI, CORPORATE |
| product_class | string | attribute | 0.0 | 7 |  | static, bullet_m, bullet_d, amortising |
| side_sign | int64 | attribute | 0.0 | 2 | -1 … 1 | 1, -1 |
| hqla_level | string | attribute | 80.6 | 4 |  | L1, L1B, L2A, L2B |
| base_haircut | double | attribute | 77.4 | 6 | 0.00 … 0.50 | 0.0, 0.07, 0.15, 0.25 |
| cbc_level | string | attribute | 77.4 | 5 |  | L1, L1B, L2A, L2B |
| cbc_availability_day | int64 (stored as float, has nulls?) | attribute | 77.4 | 4 | 1.00 … 5.00 | 1.0, 2.0, 3.0, 5.0 |
| lcr_basis | string | attribute | 0.0 | 4 |  | hqla, due_30d, none, balance |
| lcr_flow | string | attribute | 16.1 | 3 |  | hqla, inflow, outflow |
| lcr_rate | double | attribute | 35.5 | 8 | 0.05 … 1.00 | 1.0, 0.5, 0.05, 0.1 |
| nsfr_type | string | attribute | 6.5 | 2 |  | RSF, ASF |
| nsfr_factor_lt6m | double | attribute | 0.0 | 9 | 0.00 … 1.00 | 0.0, 0.07, 0.15, 0.25 |
| nsfr_factor_6m_1y | double | attribute | 0.0 | 9 | 0.00 … 1.00 | 0.0, 0.07, 0.15, 0.25 |
| nsfr_factor_ge1y | double | attribute | 0.0 | 11 | 0.00 … 1.00 | 0.0, 0.07, 0.15, 0.25 |
| sort_order | int64 | attribute | 0.0 | 31 | 1 … 31 | 1, 2, 3, 4 |

## dim_scenario
Rows: 7 · Guess: **DIMENSION (unique key, descriptive columns)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| scenario_key | string | KEY (unique) | 0.0 | 7 |  | ACT, BASE, IDIO, MARKET |
| scenario_name | string | attribute | 0.0 | 7 |  | Actual, Baseline, Idiosyncratic, Market-wide |
| scenario_type | string | attribute | 0.0 | 4 |  | actual, baseline, stress, reverse |
| sort_order | int64 | attribute | 0.0 | 7 | 0 … 6 | 0, 1, 2, 3 |
| description | string | attribute | 0.0 | 7 |  | Historical actuals (no pr, Business-as-usual funding, Name-specific: 3-notch do, System-wide: HQLA price f |

## dim_time_bucket
Rows: 22 · Guess: **DIMENSION or small fact (check)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| bucket_key | string | KEY (unique) | 0.0 | 22 |  | B01, B02, B03, B04 |
| bucket_label | string | attribute | 0.0 | 22 |  | Overnight, >1D-2D, >2D-3D, >3D-4D |
| from_day | int64 (stored as float, has nulls?) | measure | 4.5 | 21 | 1.00 … 1,827.00 | 1.0, 2.0, 3.0, 4.0 |
| to_day | int64 (stored as float, has nulls?) | measure | 4.5 | 21 | 1.00 … 99,999.00 | 1.0, 2.0, 3.0, 4.0 |
| sort_order | int64 | attribute | 0.0 | 22 | 1 … 22 | 1, 2, 3, 4 |
| in_lcr_30d | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |
| in_6m | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |
| in_1y | int64 | attribute | 0.0 | 2 | 0 … 1 | 1, 0 |

## fact_bank_cashflow_contractual
Rows: 235,803 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 8,781 | 2026-10-01 … 2055-07-19 | 2026-10-01, 2026-10-02, 2026-10-03, 2026-10-04 |
| contract_id | string | foreign key? | 0.0 | 5,386 |  | B000443, B000452, B000552, B000553 |
| product_code | string | foreign key? | 0.0 | 21 |  | DEP_CORP_NONOP, DEP_FI, DEP_OPER, DEP_RET_HIGHER |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, USD, GBP |
| flow_type | string | attribute | 0.0 | 2 |  | SCHEDULED, NMD_ON_DEMAND |
| days_from_asof | int64 | attribute | 0.0 | 8,781 | 1 … 10519 | 1, 2, 3, 4 |
| bucket_key | string | foreign key? | 0.0 | 21 |  | B01, B02, B03, B04 |
| principal_cash_local | decimal | measure | 0.0 | 224,712 | -143,176,956.74 … 73,561,204.71 | -0.0, -6572576.36, -2514906.99, -18483801.76 |
| interest_cash_local | decimal | measure | 0.0 | 204,159 | -6,576,922.80 … 2,412,103.84 | -7185.55, -714.04, -11653.44, -8822.58 |
| total_cash_local | double | measure | 0.0 | 6,160 | -148,276,954.53 … 73,985,882.53 | -7185.55, -714.04, -6584229.8, -8822.58 |
| principal_cash_rc | decimal | measure | 0.0 | 224,709 | -143,176,956.74 … 73,561,204.71 | -0.0, -6572576.36, -2942441.17, -17005097.62 |
| interest_cash_rc | decimal | measure | 0.0 | 203,984 | -6,050,768.98 … 2,412,103.84 | -7185.55, -714.04, -11653.44, -8822.58 |
| total_cash_rc | double | measure | 0.0 | 6,160 | -148,276,954.53 … 73,985,882.53 | -7185.55, -714.04, -6584229.8, -8822.58 |

## fact_bank_cashflow_history
Rows: 30,210 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 730 | 2024-10-01 … 2026-09-30 | 2024-10-01, 2024-10-02, 2024-10-03, 2024-10-04 |
| product_code | string | foreign key? | 0.0 | 21 |  | DEP_CORP_NONOP, DEP_OPER, DEP_RET_HIGHER, DEP_RET_LESS |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, GBP, USD |
| flow_type | string | attribute | 0.0 | 5 |  | INTEREST, ORIGINATION, PRINCIPAL, NMD_NET_CHANGE |
| amount_local | decimal | measure | 0.0 | 28,904 | -368,853,848.20 … 152,020,899.87 | -60388.85, 17303935.11, -11176457.87, 160095.15 |
| amount_rc | decimal | measure | 0.0 | 29,612 | -368,853,848.20 … 142,674,533.35 | -60388.85, 17303935.11, -11176457.87, 160095.15 |

## fact_bank_cashflow_stressed
Rows: 67,999 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| scenario_key | string | foreign key? | 0.0 | 6 |  | BASE, IDIO, MARKET, COMBINED |
| date | dateTime | date | 0.0 | 182 | 2026-10-01 … 2027-03-31 | 2026-10-20, 2027-01-18, 2027-03-12, 2027-03-16 |
| days_from_asof | int64 | attribute | 0.0 | 182 | 1 … 182 | 20, 110, 163, 167 |
| bucket_key | string | foreign key? | 0.0 | 16 |  | B09, B14, B16, B12 |
| product_code | string | foreign key? | 0.0 | 27 |  | BOND_ISSUED, COVERED_ISSUED, DEP_CORP_NONOP, DEP_FI |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, USD, GBP |
| flow_type | string | attribute | 0.0 | 8 |  | CONTRACTUAL_INTEREST, CONTRACTUAL_PRINCIPAL, ROLLOVER, RUNOFF |
| amount_local | decimal | measure | 0.0 | 22,017 | -143,176,956.74 … 114,541,565.40 | -1953809.94, -5099997.78, -143176956.74, 114541565.4 |
| amount_rc | decimal | measure | 0.0 | 30,941 | -143,176,956.74 … 114,541,565.40 | -1953809.94, -5099997.78, -143176956.74, 114541565.4 |

## fact_bank_position
Rows: 135,480 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 25 | 2024-09-30 … 2026-09-30 | 2024-09-30, 2024-10-31, 2024-11-30, 2024-12-31 |
| contract_id | string | foreign key? | 0.0 | 9,340 |  | B000001, B000002, B000003, B000004 |
| product_code | string | foreign key? | 0.0 | 29 |  | BOND_ISSUED, CASH_CB, COVERED_ISSUED, DEP_CORP_NONOP |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, USD, GBP |
| balance_local | decimal | measure | 0.0 | 111,034 | 725.75 … 1,001,152,564.74 | 143176956.74, 21075786.85, 11167429.21, 15911257.27 |
| balance_rc | decimal | measure | 0.0 | 116,380 | 725.75 … 1,001,152,564.74 | 143176956.74, 21075786.85, 11167429.21, 15911257.27 |
| principal_due_30d_local | decimal | measure | 0.0 | 80,121 | 0.00 … 368,853,848.20 | 0.0, 21075786.85, 15911257.27, 83022950.89 |
| principal_due_30d_rc | decimal | measure | 0.0 | 80,109 | 0.00 … 368,853,848.20 | 0.0, 21075786.85, 15911257.27, 78435779.93 |
| remaining_maturity_days | int64 (stored as float, has nulls?) | measure | 21.5 | 9,122 | 1.00 … 10,746.00 | 840.0, 809.0, 779.0, 748.0 |
| bucket_key | string | foreign key? | 0.0 | 22 |  | B20, B19, B18, B17 |
| nsfr_band | string | attribute | 0.0 | 3 |  | ge1y, m6_1y, lt6m |
| nsfr_factor | double | attribute | 0.0 | 11 | 0.00 … 1.00 | 1.0, 0.5, 0.0, 0.9 |
| lcr_base_rc | double | measure | 0.0 | 109,045 | 0.00 … 368,853,848.20 | 0.0, 21075786.85, 15911257.27, 78435779.93 |

## fact_bank_survival
Rows: 4,368 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| scenario_key | string | foreign key? | 0.0 | 6 |  | BASE, IDIO, MARKET, COMBINED |
| currency_scope | string | attribute | 0.0 | 4 |  | ALL, EUR, GBP, USD |
| date | dateTime | date | 0.0 | 182 | 2026-10-01 … 2027-03-31 | 2026-10-01, 2026-10-02, 2026-10-03, 2026-10-04 |
| days_from_asof | int64 | attribute | 0.0 | 182 | 1 … 182 | 1, 2, 3, 4 |
| cbc_available_rc | double | measure | 0.0 | 64 | 69,853,846.58 … 1,804,291,794.08 | 1127853825.93, 1355452778.2, 1703464067.04, 1804291794.08 |
| liquidity_position_rc | double | measure | 0.0 | 4,365 | -1,260,400,921.90 … 1,805,906,513.09 | 1126171267.52, 1352858422.01, 1696455053.83, 1696836895.49 |
| liquidity_position_post_mgmt_rc | double | measure | 0.0 | 4,365 | -649,705,478.71 … 1,805,906,513.09 | 1126171267.52, 1352858422.01, 1696455053.83, 1696836895.49 |

## fact_fx_rate
Rows: 2,193 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 731 | 2024-09-30 … 2026-09-30 | 2024-09-30, 2024-10-01, 2024-10-02, 2024-10-03 |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, USD, GBP |
| rate_to_rc | double | measure | 0.0 | 1,463 | 0.89 … 1.22 | 1.0, 0.9772692896872044, 0.9759263016137782, 0.9796664471438576 |

## fact_hqla_holding
Rows: 4,154 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 25 | 2024-09-30 … 2026-09-30 | 2024-09-30, 2024-10-31, 2024-11-30, 2024-12-31 |
| contract_id | string | foreign key? | 0.0 | 267 |  | B000015, B000016, B000017, B009229 |
| product_code | string | foreign key? | 0.0 | 7 |  | CASH_CB, SEC_L1, SEC_L1B_CB, SEC_L2A |
| currency_code | string | foreign key? | 0.0 | 3 |  | EUR, GBP, USD |
| hqla_level | string | attribute | 0.0 | 5 |  | L1, L1B, L2A, L2B |
| nominal_local | double | measure | 0.0 | 339 | 386,253.91 … 510,000,000.00 | 477511574.12, 482693195.36, 482281452.93, 481284063.55 |
| price | decimal | measure | 0.0 | 4,080 | 0.87 … 1.11 | 1.0, 1.0030613237, 1.0042823266, 0.9996904312 |
| market_value_local | decimal | measure | 0.0 | 4,154 | 373,021.49 … 510,000,000.00 | 477511574.12, 482693195.36, 482281452.93, 481284063.55 |
| market_value_rc | decimal | measure | 0.0 | 4,154 | 373,021.49 … 510,000,000.00 | 477511574.12, 482693195.36, 482281452.93, 481284063.55 |
| encumbered | int64 | attribute | 0.0 | 2 | 0 … 1 | 0, 1 |
| base_haircut | double | attribute | 0.0 | 6 | 0.00 … 0.50 | 0.0, 0.07, 0.15, 0.5 |

## fact_liquidity_gap
Rows: 588 · Guess: **FACT or unclear grain (no single-column key)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| view | string | attribute | 0.0 | 7 |  | CONTRACTUAL, BASE, COMBINED, EXTREME |
| currency_scope | string | attribute | 0.0 | 4 |  | ALL, EUR, GBP, USD |
| bucket_key | string | foreign key? | 0.0 | 21 |  | B01, B02, B03, B04 |
| inflows_rc | double | measure | 0.0 | 445 | 36,271.21 … 2,689,515,072.70 | 21309844.03, 38374888.93, 13479158.65, 43155366.47 |
| outflows_rc | double | measure | 0.0 | 458 | -4,331,282,406.86 … 0.00 | -4331282406.86, -35287471.94, -48847184.07, -22275252.46 |
| net_gap_rc | double | measure | 0.0 | 468 | -4,309,972,562.83 … 2,556,308,224.38 | -4309972562.83, 3087416.99, -35368025.42, 20880114.01 |
| cumulative_gap_rc | double | measure | 0.0 | 588 | -5,030,925,814.32 … 6,775,385,730.19 | -4309972562.83, -4306885145.85, -4342253171.26, -4321373057.25 |

## fact_liquidity_metrics
Rows: 124 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| date | dateTime | date | 0.0 | 25 | 2024-09-30 … 2026-09-30 | 2024-09-30, 2024-10-31, 2024-11-30, 2024-12-31 |
| scenario_key | string | foreign key? | 0.0 | 7 |  | ACT, BASE, IDIO, MARKET |
| entity_code | string | foreign key? | 0.0 | 1 |  | BANK |
| currency_scope | string | attribute | 0.0 | 4 |  | ALL, EUR, GBP, USD |
| hqla_l1_rc | double | measure | 0.0 | 112 | 53,442,691.19 … 1,127,853,825.93 | 1022584310.68, 819861803.01, 59518221.5, 143204286.17 |
| hqla_l1b_rc | double | measure | 0.0 | 112 | 10,266,355.69 … 240,102,559.88 | 172024781.77, 131602090.19, 10297281.84, 30125409.74 |
| hqla_l2a_rc | double | measure | 0.0 | 107 | 0.00 … 141,117,663.28 | 87210482.51, 70083309.66, 1645554.36, 15481618.49 |
| hqla_l2b_rc | double | measure | 0.0 | 112 | 3,116,495.28 … 188,379,724.42 | 185553017.72, 54116165.87, 6014721.08, 125422130.77 |
| hqla_cap_adjustment_rc | double | attribute | 0.0 | 17 | 0.00 … 92,102,487.06 | 0.0, 92102487.06, 81164244.1, 87053557.25 |
| hqla_l1b_share | double | measure | 0.0 | 112 | 0.11 … 0.18 | 0.117233198, 0.1223450514, 0.1329096913, 0.1356200414 |
| hqla_total_rc | double | measure | 0.0 | 112 | 70,046,109.47 … 1,591,050,800.42 | 1467372592.67, 1075663368.72, 77475778.78, 222130958.11 |
| lcr_outflows_rc | double | measure | 0.0 | 120 | 26,386,916.18 … 2,617,793,682.91 | 1158769638.73, 1004551911.32, 26386916.18, 127830811.23 |
| lcr_inflows_rc | double | measure | 0.0 | 109 | 2,192,770.61 … 394,240,073.14 | 249229884.25, 191477822.29, 5634407.03, 52117654.93 |
| lcr_inflows_capped_rc | double | measure | 0.0 | 109 | 2,192,770.61 … 394,240,073.14 | 249229884.25, 191477822.29, 5634407.03, 52117654.93 |
| lcr_net_outflows_rc | double | measure | 0.0 | 120 | 20,752,509.16 … 2,262,276,767.01 | 909539754.48, 813074089.03, 20752509.16, 75713156.3 |
| lcr_ratio | double | measure | 0.0 | 120 | 0.46 … 3.75 | 1.6133133109, 1.3229586126, 3.7333210262, 2.9338488707 |
| asf_rc | double | measure | 16.1 | 100 | 178,039,363.32 … 6,974,264,481.82 | 6782874423.98, 5419461648.39, 178039363.32, 1185373412.27 |
| rsf_rc | double | measure | 16.1 | 100 | 206,367,458.89 … 5,953,375,167.13 | 5086476640.35, 4101927528.61, 214399188.38, 770149923.36 |
| nsfr_ratio | double | measure | 16.1 | 100 | 0.81 … 1.54 | 1.3335113682, 1.3211987805, 0.8304106217, 1.5391463095 |
| cbc_rc | double | attribute | 80.6 | 16 | 107,338,292.78 … 1,804,291,794.08 | 1804291794.08, 1475730254.84, 108247854.24, 220313685.0 |
| stressed_net_outflow_30d_rc | double | measure | 80.6 | 24 | 2,204,089.30 … 1,697,663,777.21 | 57484735.78, 50913062.46, 2204089.3, 4367584.02 |
| survival_days | int64 (stored as float, has nulls?) | attribute | 91.1 | 11 | 14.00 … 156.00 | 106.0, 108.0, 52.0, 33.0 |
| survives_horizon | int64 (stored as float, has nulls?) | attribute | 80.6 | 2 | 0.00 … 1.00 | 1.0, 0.0 |
| min_liquidity_position_rc | double | measure | 80.6 | 24 | -1,260,400,921.90 … 1,126,171,267.52 | 1126171267.52, 930226737.48, 69593916.23, 126350613.8 |
| survival_days_post_mgmt | int64 (stored as float, has nulls?) | attribute | 95.2 | 6 | 15.00 … 52.00 | 52.0, 45.0, 18.0, 39.0 |
| min_liquidity_position_post_mgmt_rc | double | measure | 80.6 | 24 | -649,705,478.71 … 1,126,171,267.52 | 1126171267.52, 930226737.48, 69593916.23, 126350613.8 |

## scenario_parameter
Rows: 307 · Guess: **FACT (has measures + several keys/dates)**

| Column | PBI type | Role | Null % | Distinct | Range | Samples |
|---|---|---|---|---|---|---|
| scenario_key | string | foreign key? | 0.0 | 6 |  | BASE, IDIO, MARKET, COMBINED |
| driver | string | attribute | 0.0 | 24 |  | lcr_outflow_multiplier, hqla_haircut_addon, fx_shock, nmd_runoff_30d |
| product_code | string | foreign key? | 47.2 | 19 |  | DEP_RET_STABLE, DEP_RET_LESS, DEP_RET_HIGHER, DEP_OPER |
| currency_code | string | foreign key? | 94.1 | 3 |  | EUR, USD, GBP |
| hqla_level | string | attribute | 90.2 | 5 |  | L1, L1B, L2A, L2B |
| value | decimal | measure | 0.0 | 74 | -0.02 … 45.00 | 1.0, 0.0, -0.02, -0.015 |

## Foreign-key candidates

| Fact column | → Dimension key | Value match | Orphan values | Note |
|---|---|---|---|---|
| fact_bank_cashflow_contractual[contract_id] | dim_contract[contract_id] | 100% | 0 | same name |
| fact_bank_position[contract_id] | dim_contract[contract_id] | 100% | 0 | same name |
| fact_hqla_holding[contract_id] | dim_contract[contract_id] | 100% | 0 | same name |
| dim_contract[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_bank_cashflow_contractual[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_bank_cashflow_history[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_bank_position[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_fx_rate[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| fact_hqla_holding[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| scenario_parameter[currency_code] | dim_currency[currency_code] | 100% | 0 | same name |
| dim_contract[maturity_date] | dim_date[date] | 100% | 1 | |
| fact_bank_cashflow_contractual[date] | dim_date[date] | 100% | 0 | same name |
| fact_bank_cashflow_history[date] | dim_date[date] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[date] | dim_date[date] | 100% | 0 | same name |
| fact_bank_position[date] | dim_date[date] | 100% | 0 | same name |
| fact_bank_survival[date] | dim_date[date] | 100% | 0 | same name |
| fact_fx_rate[date] | dim_date[date] | 100% | 0 | same name |
| fact_hqla_holding[date] | dim_date[date] | 100% | 0 | same name |
| fact_liquidity_metrics[date] | dim_date[date] | 100% | 0 | same name |
| dim_contract[pay_day] | dim_date[days_from_asof] | 100% | 0 | |
| dim_contract[coupon_months] | dim_date[days_from_asof] | 100% | 0 | |
| dim_contract[encumbered] | dim_date[days_from_asof] | 100% | 0 | |
| dim_contract[is_live_at_asof] | dim_date[days_from_asof] | 100% | 0 | |
| dim_currency[is_reporting_currency] | dim_date[days_from_asof] | 100% | 0 | |
| dim_product[side_sign] | dim_date[days_from_asof] | 100% | 0 | |
| dim_time_bucket[in_lcr_30d] | dim_date[days_from_asof] | 100% | 0 | |
| dim_time_bucket[in_6m] | dim_date[days_from_asof] | 100% | 0 | |
| dim_time_bucket[in_1y] | dim_date[days_from_asof] | 100% | 0 | |
| fact_bank_cashflow_contractual[days_from_asof] | dim_date[days_from_asof] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[days_from_asof] | dim_date[days_from_asof] | 100% | 0 | same name |
| fact_bank_survival[days_from_asof] | dim_date[days_from_asof] | 100% | 0 | same name |
| fact_hqla_holding[encumbered] | dim_date[days_from_asof] | 100% | 0 | |
| dim_contract[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_bank_cashflow_contractual[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_bank_cashflow_history[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_bank_position[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_hqla_holding[product_code] | dim_product[product_code] | 100% | 0 | same name |
| scenario_parameter[product_code] | dim_product[product_code] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[scenario_key] | dim_scenario[scenario_key] | 100% | 0 | same name |
| fact_bank_survival[scenario_key] | dim_scenario[scenario_key] | 100% | 0 | same name |
| fact_liquidity_metrics[scenario_key] | dim_scenario[scenario_key] | 100% | 0 | same name |
| scenario_parameter[scenario_key] | dim_scenario[scenario_key] | 100% | 0 | same name |
| fact_bank_cashflow_contractual[bucket_key] | dim_time_bucket[bucket_key] | 100% | 0 | same name |
| fact_bank_cashflow_stressed[bucket_key] | dim_time_bucket[bucket_key] | 100% | 0 | same name |
| fact_bank_position[bucket_key] | dim_time_bucket[bucket_key] | 100% | 0 | same name |
| fact_liquidity_gap[bucket_key] | dim_time_bucket[bucket_key] | 100% | 0 | same name |
