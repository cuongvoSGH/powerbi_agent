# Liquidity Coverage Ratio (Basel III, BCBS 238)

> EU institutions: the EU Delegated Regulation 2015/61 adds Level 1 covered bonds (7% haircut, 70% cap) and higher-outflow retail categories. See `eba-sls.md`.

```
LCR = Stock of HQLA / Total net cash outflows over the next 30 calendar days   >= 100%
Net outflows = Outflows - min(Inflows, 75% x Outflows)
```

## 1. HQLA: unencumbered, at market value
| Level | Examples | Haircut | Cap |
|---|---|---|---|
| Level 1 | Cash, central bank reserves (withdrawable), 0% RW sovereign / central bank securities | 0% | none |
| Level 2A | 20% RW sovereign/PSE, corporate bonds and covered bonds rated AA- or better | 15% | L2 total ≤ 40% of HQLA |
| Level 2B | RMBS AA (25%), corporate bonds A+ to BBB- (50%), listed equities (50%) | 25–50% | L2B ≤ 15% of HQLA |

**Cap adjustment.** This is the simplified form, without unwinding secured funding:
```
Adj L2B = max(L2B - 15/85 x (L1 + L2A), L2B - 15/60 x L1, 0)
Adj L2  = max(L2A + L2B - Adj L2B - 2/3 x L1, 0)
HQLA    = L1 + L2A + L2B - Adj L2B - Adj L2
```
All L-values here are after haircuts. Encumbered assets (pledged in repo or as collateral) are excluded.

## 2. Outflow (run-off) rates, 30-day horizon
| Item | Rate |
|---|---|
| Retail deposits, stable (insured, established relationship) | 5% (3% where the jurisdiction allows) |
| Retail deposits, less stable | 10% |
| Retail term deposits, residual maturity > 30 days with withdrawal penalty | 0% (excluded) |
| Operational deposits (clearing, custody, cash management) | 25% (5% for the insured part) |
| Non-operational deposits, non-financial corporates / sovereigns / PSEs | 40% (20% if fully insured) |
| Non-operational deposits, financial institutions | 100% |
| Unsecured wholesale funding maturing (bonds, interbank) | 100% |
| Secured funding backed by L1 / L2A / L2B / other | 0% / 15% / 25–50% / 100% |
| Committed credit facilities: retail & SME | 5% |
| Committed credit facilities: non-financial corporates | 10% |
| Committed liquidity facilities: non-financial corporates | 30% |
| Committed facilities to banks | 40% |
| Committed facilities to other financial institutions | 40% (credit) / 100% (liquidity) |
| Derivative net outflows, downgrade triggers (3 notches) | 100% of collateral required |
| Market valuation changes on derivatives | largest 30-day net collateral flow in 24 months |

## 3. Inflow rates
Only contractual inflows from performing exposures, due within 30 days.

| Item | Rate |
|---|---|
| Retail and SME loans | 50% |
| Non-financial wholesale loans | 50% |
| Financial institutions (loans, placements) | 100% |
| Operational deposits held at other banks | 0% |
| Maturing non-HQLA securities | 100% |
| Reverse repo backed by L1 / L2A / other | 0% / 15% / 100% |
| Credit or liquidity facilities the bank has *received* | 0% |

## 4. How the simulation implements it
- Product parameters live in `config/default.yaml` → `bank.products.<code>.lcr` (`basis`, `rate`, `flow`).
- `basis: balance` means the rate × balance; it's used for non-maturity deposits and undrawn facilities.
- `basis: due_30d` means the rate × principal due in the next 30 days.
- Interest flows within 30 days are ignored, which is conservative for net lenders.
- **Stressed LCR** (an internal metric, not regulatory):
  - adds the scenario `hqla_haircut_addon`
  - applies `fx_shock` to both HQLA and flows
  - multiplies outflows by `lcr_outflow_multiplier`

## 5. Typical ranges
| Ratio | Typical value |
|---|---|
| Large banks | LCR 120–160% |
| Small banks | LCR 150–250% |
| Internal management target | 110–120% minimum |

A regulatory breach under stress (LCR < 100%) is expected. That is what the HQLA buffer exists to absorb.
