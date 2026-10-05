# Stress scenario design

## Standard scenario set
| Scenario | Narrative | Bank shocks | Corporate shocks |
|---|---|---|---|
| **BASE** | Business as usual | Normal rollover (90–100%), modest deposit growth | Budget revenue, normal payment behaviour |
| **IDIO** (idiosyncratic) | Rating downgrade, reputational event | Deposit run-off (retail 5–15%, operational 20%+ in 30d), wholesale non-renewal, collateral calls on downgrade, facility drawdowns | Loss of key customer, slower collections (DSO +10d), dividend suspended |
| **MARKET** (market-wide) | Systemic stress, funding markets shut | HQLA price falls (extra haircuts), interbank closed, FX depreciation, broad facility drawdowns | Sales fall 10–20%, suppliers shorten terms, banks cut credit lines, capex deferred |
| **COMBINED** | Both at once | Severe but plausible combination | Combination |
| **REVERSE** | What shock breaks us at day N? | Scale (COMBINED − BASE) until survival = target | Same multiplier |

## Driver catalogue (config `scenario_drivers`)
| Driver | Meaning | Typical BASE → severe |
|---|---|---|
| `nmd_runoff_30d` / `nmd_runoff_365d` | Cumulative share of non-maturity deposits withdrawn (front-loaded curve) | 0 → retail stable 5–10%, less stable 15–25%, operational 20–30% in 30d |
| `rollover` | Share of maturing funding renewed (liabilities) or re-lent (assets) | 0.9–1.0 → wholesale 0, retail term 0.6 |
| `facility_drawdown_30d/365d` | Share of undrawn commitments drawn | 0 → corporate liquidity lines 30–60% |
| `collateral_call_pct_assets` | One-off margin / downgrade collateral | 0 → 0.5–1% of assets |
| `hqla_haircut_addon` | Extra haircut on the HQLA market value | 0 → L1 2–5%, L2A 10%, L2B 20% |
| `fx_shock` | Change in the USD value of the currency | 0 → EM currency −10 to −20% |
| `lcr_outflow_multiplier` | Scales Basel outflows for the internal stressed LCR | 1.0 → 1.5 |
| `corp_revenue_shock` | Sales change, ramped over 30 days | 0 → −15 to −25% |
| `corp_dso_shift_days` | Customers pay later | 0 → +10–20 days |
| `corp_key_customer_defaults` | Top-N customers stop paying | 0 → 1–2 |
| `corp_supplier_terms_cut_days` | Suppliers demand faster payment | 0 → 15–30 days |
| `corp_rcf_availability` | Share of facility limits still usable | 1.0 → 0.4–0.6 |
| `corp_capex_deferral` | Management action: defer capex | 0 → 30–50% |
| `corp_dividend_suspended` | Management action | 0 → 1 |

## Design rules
1. **Severe but plausible.** Anchor the shocks to historical events: 2008 wholesale freeze, 2023 SVB/Credit Suisse digital runs (~25% of deposits in a day), 2020 COVID drawdowns (corporate RCF draws of 30–50%).
2. **Front-load the run-off.** Most outflow happens in the first 1–2 weeks. The simulation uses an exponential curve (tau = 7 days) to day 30, then linear.
3. **Separate shocks from management actions** (capex deferral, dividend suspension, lending cuts) so their effect can be shown on its own.
4. **Second-round effects:** FX shocks raise outflows in the weak currency *and* lower HQLA held in it. Model both.
5. **Reverse stress:** report the multiplier on (COMBINED − BASE), the breach day and which driver contributes most. Survival can jump past the target when a large single-day outflow exists. Report the smallest shock that breaches within the target.
6. **Document everything:** each scenario's narrative, every driver value and the source of the calibration. The `scenario_parameter` table and README do this automatically.
