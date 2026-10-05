# Maturity ladder / liquidity gap

## Buckets (from the as-of date)
| Key | Bucket | Days |
|---|---|---|
| B01 | O/N | 1 |
| B02 | 2–7D | 2–7 |
| B03 | 8–30D | 8–30 (end of the LCR window) |
| B04 | 1–3M | 31–90 |
| B05 | 3–6M | 91–180 |
| B06 | 6–12M | 181–365 |
| B07 | 1–2Y | 366–730 |
| B08 | 2–5Y | 731–1825 |
| B09 | >5Y | > 1825 |
| B10 | Non-maturity | equity, fixed assets, other (no contractual date) |

## Measures
```
Net gap (bucket)         = Inflows(bucket) + Outflows(bucket)      (outflows negative)
Cumulative gap (bucket)  = sum of net gaps from O/N up to this bucket
Cumulative gap + CBC     = cumulative gap + counterbalancing capacity   (should stay > 0 in short buckets)
Gap ratio                = Cumulative gap / Total assets              (limits e.g. >= -10% at 1M, >= -20% at 3M)
```

## Three views
| View | Non-maturity deposits (NMD) | Term items | Use |
|---|---|---|---|
| **Contractual** | 100% in O/N (repayable on demand) | Contractual maturity | Regulatory maturity ladder; shows the worst case on paper |
| **Behavioural** | Split into **core** (stable, spread over 1–5Y) and **non-core** (volatile, short buckets) | Expected rollover / prepayment | ALM and FTP, the realistic baseline |
| **Stressed** | Scenario run-off curve | Scenario rollover | Survival horizon and contingency planning |

Core/non-core NMD estimate: core = the minimum balance over a 12-month window, or a statistical floor such as the 1st percentile of balance. Non-core is the rest.

## Simulation mapping
- `fact_bank_cashflow_contractual` gives the contractual view. `flow_type = NMD_ON_DEMAND` holds the NMD balances in O/N, and `SCHEDULED` holds everything else.
- `fact_bank_cashflow_stressed` gives the behavioural/stressed view within the projection horizon, one per scenario. BASE is the behavioural baseline. Beyond the horizon, use contractual `SCHEDULED` flows.
- `fact_liquidity_gap` is a reference ladder for each view, used to reconcile DAX.

## Reading the ladder
- A **negative cumulative gap in the short buckets** (≤ 1M) is normal for a deposit-funded bank under the contractual view. Compare it with the CBC.
- A **negative cumulative gap in 1–12M under BASE** is a structural funding issue: the bank relies on rollover.
- Watch for **concentrations**: one bucket dominated by a single funding source, such as a bond maturity.
