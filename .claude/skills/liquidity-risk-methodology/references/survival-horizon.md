# Survival horizon & counterbalancing capacity

## Definitions
```
Liquidity position(t) = CBC + sum over days 1..t of net stressed cash flow
Survival horizon      = first day t on which Liquidity position(t) < 0   (or "beyond horizon")
```
**Counterbalancing capacity (CBC):** liquidity the entity can raise quickly without changing its business. For a bank:
- unencumbered HQLA after stressed haircuts
- central-bank-eligible non-HQLA collateral, after the central bank haircut (optional, often excluded in idiosyncratic stress)
- committed facilities *received*, if they can be relied on under stress (usually 0 for banks)

**Monetisation timing:**
- Level 1 is available on day 1.
- Level 2 can take 1–5 days (repo / sale).
- The simulation assumes all CBC is available on day 1, which is common in management reporting. State this when presenting.

## Typical targets
| Measure | Typical target |
|---|---|
| Bank survival under combined stress | ≥ 30 days (LCR horizon); many risk-appetite statements require ≥ 60–90 days |
| Bank survival under idiosyncratic or market stress | ≥ 90 days |
| Corporate | Headroom (cash + committed undrawn − minimum operating cash) > 0 over the 13-week and 12-month forecasts under downside |

## Corporate equivalent
```
Headroom(t) = Cash(t) + Undrawn committed facilities available(t) - Minimum operating cash
Days to breach = first t with Headroom(t) < 0
Weeks of cover = Liquidity sources / average weekly net outflow (stress)
```

## Presenting
- Plot the **daily liquidity position per scenario** (line chart) with a zero line, marking the breach day.
- Show a **waterfall** of the stressed 30-day outflows by driver: run-off, wholesale non-rollover, drawdowns, collateral, FX.
- Pair survival days with the minimum liquidity position. A bank that survives with a thin margin is not "safe".

## Simulation mapping
- `fact_bank_survival` holds the daily liquidity position per scenario and currency scope.
- `fact_liquidity_metrics` holds `cbc_rc`, `survival_days` (blank means it survives the horizon) and `min_liquidity_position_rc` (and `survival_days_post_mgmt` after management actions).
- `fact_corp_cash_balance` holds `headroom_local` / `headroom_rc` per day and scenario.
