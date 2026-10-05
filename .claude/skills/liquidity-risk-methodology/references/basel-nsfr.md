# Net Stable Funding Ratio (Basel III, BCBS 295)

```
NSFR = Available Stable Funding (ASF) / Required Stable Funding (RSF)   >= 100%
ASF  = sum(liability & capital carrying values x ASF factor)
RSF  = sum(asset carrying values x RSF factor) + off-balance exposures x RSF factor
```
NSFR is structural, with a one-year horizon. Unlike LCR it is not stressed with scenario shocks. Instead, track its trend and run what-ifs on balance-sheet mix.

## ASF factors
| Funding source | < 6 months | 6–12 months | ≥ 1 year |
|---|---|---|---|
| Regulatory capital (CET1, AT1, T2 ≥ 1y), equity | 100% | 100% | 100% |
| Retail & SME deposits, stable | 95% | 95% | 100% |
| Retail & SME deposits, less stable | 90% | 90% | 100% |
| Operational deposits | 50% | 50% | 100% |
| Non-financial corporate / sovereign / PSE funding | 50% | 50% | 100% |
| Funding from financial institutions and central banks | 0% | 50% | 100% |
| Other liabilities, derivatives, deferred tax | 0% | 0% | 0% (100% if ≥ 1y term) |

## RSF factors
| Asset | < 6 months | 6–12 months | ≥ 1 year |
|---|---|---|---|
| Cash, central bank reserves | 0% | 0% | 0% |
| Unencumbered Level 1 securities | 5% | 5% | 5% |
| Unencumbered Level 2A | 15% | 15% | 15% |
| Unencumbered Level 2B | 50% | 50% | 50% |
| Loans to financial institutions secured by L1 | 10% | 50% | 100% |
| Other loans to financial institutions | 15% | 50% | 100% |
| Loans to non-financial corporates, retail, SME | 50% | 50% | 85% (65% if RW ≤ 35%) |
| Residential mortgages, RW ≤ 35% | 50% | 50% | 65% |
| Non-HQLA securities, not in default | 50% | 50% | 85% |
| Non-performing loans, fixed assets, other assets | 100% | 100% | 100% |
| Encumbered assets ≥ 1 year | 100% | 100% | 100% |
| Undrawn committed credit / liquidity facilities | 5% of undrawn amount | | |

## Simulation notes
- Factors are in `bank.products.<code>.nsfr` with keys `lt6m`, `m6_1y`, `ge1y`, chosen by residual maturity.
- Amortising loans use the whole contract's residual maturity. Basel splits each instalment into its own band, so this simplification slightly overstates RSF.
- Encumbered HQLA uses `bank.nsfr_encumbered_rsf` (default 100%).
- Typical NSFR for a deposit-funded commercial bank is 110–130%.
