---
name: liquidity-risk-methodology
description: Liquidity risk methodology for banks and corporate treasury - Basel III and EU (DR 2015/61, EBA GL/2018/04, ALMM C 66.01, ECB LiST) LCR (HQLA levels, haircuts, caps, run-off and inflow rates), NSFR (ASF/RSF factors), maturity gap / liquidity ladder, survival horizon and counterbalancing capacity, stress scenario design (idiosyncratic, market-wide, combined, reverse), and corporate cash forecasting (13-week, DSO/DPO, facility headroom). Use when designing, calibrating or explaining liquidity stress tests or simulated cash-flow data.
---

# Liquidity risk methodology

Domain reference for the `liquidity-data-simulator` agent and for `powerbi-developer`, which uses the `liquidity-powerbi` skill. It contains no code. Read the reference that matches the question.

| Question | Reference |
|---|---|
| How is LCR calculated? Which rates and caps apply? | `references/basel-lcr.md` |
| How is NSFR calculated? Which factors apply? | `references/basel-nsfr.md` |
| How do I build a maturity ladder or gap report? What do I do with non-maturity deposits? | `references/maturity-ladder.md` |
| How long can the bank or company survive? What counts as counterbalancing capacity? | `references/survival-horizon.md` |
| How do I design stress scenarios, set shock severities or run a reverse stress test? | `references/stress-scenarios.md` |
| Corporate treasury: cash forecast, working capital, facilities, covenants | `references/corporate-liquidity.md` |
| EU / EBA: DR 2015/61 LCR specifics, EBA GL/2018/04 stress tests, ALMM C 66.01 ladder, LiST survival period, compliance map | `references/eba-sls.md` |

## Principles to apply every time
1. **State the framework and any national discretion.** Rates in the references follow the Basel Committee standards: BCBS 238 for LCR, BCBS 295 for NSFR. Local regulators, such as the SBV in Vietnam, the EBA in the EU or the Fed in the US, change some rates. Say which you assume.
2. **Keep the three views separate:**
   - **contractual** flows: what the contracts say
   - **behavioural** flows: what customers actually do (rollover, run-off)
   - **stressed** flows: behavioural flows under a scenario

   Every report should say which view it shows.
3. **Don't double count:**
   - HQLA held in the liquidity buffer is counted as stock, not as maturing inflows.
   - Facility drawdowns are outflows; the undrawn amount is not also counted as available funding.
4. **Balances are point-in-time; flows are period amounts.** Never sum balances across dates.
5. **Currency:** compute metrics in the reporting currency and, for significant currencies, per currency as well. FX shocks change both the HQLA value and the outflows.
6. **Reverse stress** asks what shock breaks us, not how bad a given shock is. Report the multiplier and the breach day.
7. **Synthetic data** must be labelled as synthetic wherever it's shown.
