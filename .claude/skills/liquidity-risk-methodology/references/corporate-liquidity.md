# Corporate treasury liquidity

## Cash-flow classification (IAS 7)
| Activity | Typical lines |
|---|---|
| Operating | Customer receipts, supplier payments, payroll, rent & overheads, taxes (interest received/paid may be here) |
| Investing | Capex, acquisitions, asset disposals |
| Financing | Debt drawdowns and repayments, interest paid (policy choice), dividends, share buybacks |

The simulation classifies interest paid as Financing. Say so in reports.

## Forecasting horizons
| Horizon | Method | Use |
|---|---|---|
| 13-week (daily/weekly) | **Direct method**: open AR by expected pay date, open AP by due date, payroll/tax calendars, known debt service | Liquidity management, covenant headroom, lender reporting |
| 12-month (monthly) | Direct method for the first quarter, then indirect (EBITDA − working capital − capex − tax − debt service) | Budget, facility sizing |

## Working-capital drivers
```
DSO = AR / Revenue x days        (collection period)
DPO = AP / COGS x days           (payment period)
DIO = Inventory / COGS x days
Cash conversion cycle = DSO + DIO - DPO
```
Under stress:
- DSO rises (customers delay).
- DPO falls (suppliers tighten terms, credit insurers withdraw cover).
- Both consume cash.

## Liquidity sources and headroom
```
Liquidity headroom = Cash + Undrawn committed facilities (available) - Minimum operating cash
```
- **Committed** facilities (RCF) count. Uncommitted lines and overdrafts can be withdrawn, so count them at a haircut, or not at all under stress.
- Check facility **maturity**: a facility expiring inside the horizon is not available after expiry.
- **Covenants:**
  - typically Net debt / EBITDA ≤ 3.0x and Interest cover ≥ 4.0x
  - minimum liquidity covenants

  A covenant breach can make undrawn facilities unavailable. Show covenant headroom alongside liquidity headroom.

## Stress levers
- **Revenue shock:** model costs as part fixed, part variable. The simulation scales purchases with revenue; payroll and rent stay fixed.
- **Key customer default:** remove that customer's open AR and future receipts.
- **Supplier terms cut:** pay open AP earlier.
- **Bank line cuts:** lower the available facility amount.
- **Management actions:** capex deferral, dividend suspension, factoring of receivables, cost cuts.

## Simulation mapping
| Table | Contents |
|---|---|
| `fact_corp_invoice` | OPEN items drive the first ~60 days of the forecast |
| `fact_corp_cashflow_actual` / `_forecast` | Daily flows by category |
| `fact_corp_cash_balance` | Opening/closing cash, drawn and undrawn facility amounts, minimum cash, headroom per scenario |
| `dim_facility` | Limits, drawn amount at as-of, maturity, covenant text |
