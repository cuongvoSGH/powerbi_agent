# EBA-aligned Severe Liquidity Stress (SLS)

This is the reference for the `eba_sls` simulation profile (`liquidity-simulation/config/eba_sls.yaml`). It summarises the EU rules the profile follows and maps each requirement to a dataset feature.

> **Synthetic data.** The dataset *illustrates* an EBA-style severe liquidity stress test. It is not a regulatory submission, does not use COREP/ALMM XBRL formats, and leaves out the elements listed in §6.

## 1. Legal and supervisory basis
| Topic | Source |
|---|---|
| LCR requirement | CRR (EU) 575/2013 Art. 412; detailed rules in **Commission Delegated Regulation (EU) 2015/61**, as amended by **(EU) 2018/1620** |
| NSFR | CRR2 (EU) 2019/876, Part Six Title IV |
| Stress-testing governance and design | **EBA GL/2018/04**, Guidelines on institutions' stress testing (incl. liquidity stress testing and reverse stress testing) |
| ILAAP in SREP | EBA GL/2016/10 (ICAAP/ILAAP information); EBA SREP Guidelines; ECB Guide to the ILAAP (2018) |
| Survival period benchmark | **ECB Liquidity Stress Test (LiST) 2019**: idiosyncratic shock, adverse and extreme calibrations, survival period over 6 months |
| Maturity ladder | Additional Liquidity Monitoring Metrics (ALMM), template **C 66.01**, in the ITS on supervisory reporting (Implementing Regulation (EU) 2021/451) |

## 2. EU LCR: differences from Basel used in the profile
| Element | EU rule (DR 2015/61) | Profile setting |
|---|---|---|
| Level 1 covered bonds (extremely high quality) | Art. 10(1)(f): Level 1, **7% haircut** | Product `SEC_L1B_CB`, level `L1B`, haircut 0.07 |
| Composition caps | Art. 17: L2 ≤ 40%, L2B ≤ 15%, **L1 covered bonds ≤ 70%** of the buffer (Annex I formula) | `cap_l2`, `cap_l2b`, `cap_l1b`. The generator uses a simplified Annex I formula without unwinding secured transactions. |
| Level 2B | Art. 12: RMBS 25%, corporate debt 50%, shares 50% | `SEC_L2B_RMBS` (`hqla_haircut: 0.25`), `SEC_L2B` (0.50) |
| Stable retail deposits | Art. 24: 5% (3% under conditions) | `DEP_RET_STABLE` 5% |
| Other retail | Art. 25(1): 10% | `DEP_RET_LESS` 10% |
| **Higher-outflow retail categories** | Art. 25(2)–(3): 10–20% by category (balance thresholds, internet-only, high rates…) | `DEP_RET_HIGHER` 15% |
| Operational deposits | Art. 27: 25% (5% for the DGS-covered part) | `DEP_OPER` 25% |
| Non-operational deposits | Art. 28: non-financial 40% (20% if DGS-covered); financial customers 100% | `DEP_CORP_NONOP` 40%, `DEP_FI` 100% |
| Downgrade collateral | Art. 30(2): additional collateral for a **3-notch downgrade** | `downgrade_notches: 3` × `collateral_per_notch_pct_assets` |
| Committed facilities | Art. 31: retail 5%; non-financial credit 10% / liquidity 30%; credit institutions 40% | `FAC_*` products |
| Inflows | Art. 32: 50% from non-financial, 100% from financial customers; Art. 33: **75% cap** (exemptions possible) | `lcr_inflow_cap: 0.75` |

## 3. EBA GL/2018/04: liquidity stress-test elements
| Requirement | How the profile covers it |
|---|---|
| Idiosyncratic, market-wide and combined scenarios, severe but plausible | `IDIO`, `MARKET`, `COMBINED` (severe), plus `EXTREME` (LiST-style) |
| Several horizons, short-term acute plus protracted | Daily projection over **182 days**. Front-loaded run-off curve (τ = 7 days) to day 30, then linear to the horizon. |
| Retail and wholesale funding withdrawal, by stability category | `nmd_runoff_*` per deposit product; `rollover` per term product |
| Loss of unsecured and secured market funding | `IB_BORROW`, `BOND_ISSUED`, `COVERED_ISSUED` rollover 0–30% in stress |
| Contingent outflows: facilities, derivatives, rating downgrade | `facility_drawdown_*`, 3-notch `COLLATERAL_CALL` on day 2 |
| Counterbalancing capacity with **realistic monetisation** and market haircuts | CBC = unencumbered HQLA + **ECB-eligible non-HQLA** (`CB_ELIGIBLE`) after base + scenario haircuts. Each level becomes available on its `cbc_availability_day`. |
| Asset encumbrance | `encumbered_share` per level; encumbered assets are excluded from LCR and CBC |
| FX: significant currencies, convertibility | EUR reporting with USD and GBP; `fx_shock`; LCR and survival per currency (`currency_scope`) |
| **Management actions** shown separately, credible and timed | `mgmt_actions` (lending cut, asset sale at a discount) produce `MGMT_*` flows. Survival is reported **before** (`survival_days`) and **after** (`survival_days_post_mgmt`). |
| **Reverse stress test** | `REVERSE`: the smallest multiple of (COMBINED − BASE) shocks that breaches within 30 days, before management actions |
| Documentation of assumptions | `scenario_parameter` table and README driver matrix (every value per scenario) |

## 4. Survival period (ECB LiST 2019 style)
```
Available CBC(t)   = sum of CBC of each level with availability day <= t
Net position(t)    = Available CBC(t) + cumulative net stressed cash flow(1..t)
Survival period    = first day t with Net position(t) < 0      (blank = beyond the 6-month horizon)
```
Risk-appetite targets in the profile (`validation:`):
- COMBINED survival ≥ 90 days
- EXTREME breach within 30–60 days
- REVERSE breach ≤ 30 days

Report both the pre- and post-management-action figures.

## 5. ALMM C 66.01 maturity ladder
- 21 time buckets from the reporting date: overnight; >1–7 days one by one; >7 days–2 weeks; >2–3 weeks; >3 weeks–30 days; >30 days–5 weeks; >5 weeks–2 months; then monthly to 6 months; 9 months; 12 months; 2 years; 5 years; >5 years.
- The profile writes these as `dim_time_bucket` (`B01`–`B21`, plus `BNM` for non-maturity items).
- Contractual flows go in `fact_bank_cashflow_contractual`, behavioural/stressed flows in `fact_bank_cashflow_stressed`, and the reference ladder per view in `fact_liquidity_gap`.
- C 66.01 also lists **counterbalancing capacity** by asset type per bucket. The dataset provides CBC by level (`fact_hqla_holding`) and its availability over time (`fact_bank_survival.cbc_available_rc`).

## 6. Not covered (state this when presenting)
- **Intraday liquidity** (BCBS 248 monitoring tools, payment-system usage)
- Intragroup liquidity transfers and legal-entity / sub-consolidation ring-fencing
- Exact COREP C 72–C 76 (LCR) and ALMM C 66–C 71 template layouts, row codes and XBRL
- Secured-funding unwind in the HQLA cap calculation (Annex I is simplified)
- Behavioural models estimated from real data. Run-off, rollover and drawdown rates are scenario assumptions.
- Contingency funding plan triggers and early-warning indicators. They can be derived from the metrics, but aren't generated.
