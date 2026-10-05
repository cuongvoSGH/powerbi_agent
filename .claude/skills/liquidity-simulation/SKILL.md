---
name: liquidity-simulation
description: Generate, configure, calibrate and validate a synthetic liquidity cash-flow dataset (bank balance sheet + corporate treasury) as star-schema CSVs for LCR, NSFR, maturity gap, survival horizon and scenario / what-if analysis in Power BI. Use when the user wants simulated cash-flow or liquidity data, new stress scenarios, different balance-sheet size/mix, or to regenerate / validate data/liquidity.
---

# Liquidity cash-flow simulation

A seeded, reproducible Python generator. Its only dependencies are pandas, numpy and PyYAML.

## Files
| Path | Purpose |
|---|---|
| `config/default.yaml` | Profile **default**: Basel III generic, bank + corporate, USD reporting, 12-month horizon |
| `config/eba_sls.yaml` | Profile **eba_sls**: EBA-aligned severe liquidity stress (EUR, DR 2015/61, ALMM C 66.01 ladder, management actions, EXTREME, 6-month horizon). Run with `--entity bank`. |
| `scripts/generate.py` | CLI entry point |
| `scripts/liqsim/common.py` | Calendar, time buckets, FX (GBM), CSV writer |
| `scripts/liqsim/bank.py` | Contracts → schedules → positions, HQLA, history and contractual flows |
| `scripts/liqsim/corporate.py` | Customers/suppliers, invoices, daily actuals with revolver balancing, scenario forecast |
| `scripts/liqsim/scenarios.py` | Driver inheritance, bank stressed flows, CBC, survival, reverse-stress bisection |
| `scripts/liqsim/metrics.py` | Reference LCR / NSFR / gap / survival (for DAX reconciliation) |
| `scripts/liqsim/docs.py` | **Table registry** (keys, FKs, column notes) and README writer |
| `scripts/validate_dataset.py` | Integrity, reconciliation and plausibility checks |
| `references/data-dictionary.md` | Star schema, relationships, which table answers which question |

## Run
```
# 1. copy a profile and edit it (never edit the profile files for one run)
cp .claude/skills/liquidity-simulation/config/eba_sls.yaml data/liquidity/config.yaml   # or default.yaml

# 2. generate (medium: about 6 s and 0.5–0.6M rows; small: about 2 s)
python .claude/skills/liquidity-simulation/scripts/generate.py --config data/liquidity/config.yaml --out data/liquidity --seed 42 --size medium --entity bank

# 3. validate (exit code 1 on failure)
python .claude/skills/liquidity-simulation/scripts/validate_dataset.py data/liquidity
```
Options:
- `--entity bank|corporate|both`
- `--size small|medium`: presets in `sizes:`. Add a `large` preset there if needed.

Overwrite protection: the generator writes a `.liqsim` marker. It refuses to write into a non-empty folder without that marker unless you pass `--force`.

The same config and seed produce **byte-identical CSVs**. The README timestamp changes.

## Config features (all optional; absent = default behaviour)
| Key | Effect |
|---|---|
| `meta.reporting_currency` | Currency of every `*_rc` column. It must have `rate_to_rc: 1.0`. Other currencies' `rate_to_rc` = value of 1 unit in it. |
| `time_buckets.buckets` / `non_maturity_key` | Maturity ladder (list of `[key, label, from_day, to_day]`, last bucket open-ended) |
| product `hqla_level: L1 / L1B / L2A / L2B`, `hqla_haircut` | HQLA level and per-product haircut override (e.g. RMBS 25%) |
| `hqla.cap_l1b` | EU 70% cap on Level 1 covered bonds |
| product `cb_eligible: true`, `cb_haircut` | Central-bank-eligible non-HQLA collateral: counts in the CBC (level `CB_ELIGIBLE`), not in the LCR |
| `hqla.cbc_availability_day` | Monetisation day per level; CBC enters the survival position on that day |
| drivers `downgrade_notches` × `collateral_per_notch_pct_assets` | Downgrade collateral call (else `collateral_call_pct_assets`) |
| drivers `mgmt_actions.lending_cut` / `.asset_sale` | `MGMT_*` flows; survival is reported pre and post actions. Asset sale needs an event product `MGMT_ACTION`. |
| `scenarios` | Any number of `stress` scenarios; projection order follows the config |
| `validation.survival_min` / `survival_range` | Plausibility targets per scenario |

## Calibrating (edit the config, then regenerate)
| Goal | Change |
|---|---|
| Raise BASE LCR | Increase `CASH_CB` / `SEC_L1` shares and reduce loans by the same amount. Or lower `encumbered_share` or short wholesale funding (`DEP_FI`, `IB_BORROW`). |
| Raise NSFR | More retail deposits or equity, less FI/interbank funding. Longer `BOND_ISSUED` terms. |
| Make a scenario more or less severe | `scenario_drivers.<S>`: `nmd_runoff_*`, `rollover`, `facility_drawdown_*`, `collateral_call_pct_assets`, `hqla_haircut_addon` |
| Shorten survival | Lower rollover of maturing wholesale funding, or raise early run-off (`nmd_runoff_30d`) |
| Reverse stress target | `scenarios.REVERSE.target_survival_days` |
| Corporate tighter | Lower `opening_cash_rc`, facility limits or `corp_rcf_availability`; raise `corp_revenue_shock` / `corp_dso_shift_days` |
| Different country | `currencies` (`rate_to_rc`, `base_rate`, vol), `meta.reporting_currency`, `bank.currency_mix`, entity currencies |
| New product | Add it under `bank.products` with `class`, `share`, `lcr`, `nsfr`. Keep asset shares and liability+equity shares each summing to 1. Add it to scenario `rollover` / `nmd_runoff_*` / `facility_drawdown_*` if it should react to stress. |
| New scenario | Add it under `scenarios` (type `stress`) and `scenario_drivers`. It's picked up automatically. |

## Validation outcomes
| Outcome | What to do |
|---|---|
| FAIL on integrity or reconciliation | A code bug. Fix the generator, don't just tune the config. |
| FAIL on plausibility | Tune the config (table above) and regenerate. Explain each change to the user. |
| WARN on reverse breach day | Expected when one large single-day outflow pushes survival past the target. Report the multiplier as "smallest shock that breaches within N days". |

## Extending the generator
- **New table:** register it in `liqsim/docs.py` `TABLES` (pk, fk, cols) so the README and validator pick it up. Write it with `Writer.write`.
- **Keep it vectorised:** use numpy/pandas. Only the corporate revolver loop is per-day.
- **Sign convention:** + = cash in, − = cash out. Balances are positive. Keep both everywhere.
