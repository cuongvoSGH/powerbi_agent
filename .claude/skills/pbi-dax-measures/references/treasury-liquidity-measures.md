# Treasury & liquidity measure library (foundation)

This is the foundation layer for the liquidity dataset (`data/liquidity`), with names as in `liquidity-powerbi/references/model-design.md`.

The **regulatory and stress metrics** are in `liquidity-powerbi/references/liquidity-measures.md` and build on the measures here. They aren't repeated:
- HQLA, LCR, NSFR
- maturity gap
- CBC, survival
- what-if
- corporate headroom / days to breach

Each measure in TMDL needs a `///` description (definition + sign), `formatString`, `displayFolder` and `lineageTag`.

## 1. Dates & scenario (folder `1. Dates & Scenario`)
```dax
// Month-end the projection starts from (works for bank-only, corporate-only or both)
As-of Date = CALCULATE ( MAX ( 'Dim Date'[Date] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Period Type] = "As-of" )

// Last bank snapshot on/before the selected date: ALL snapshot measures use this, never LASTDATE
Reporting Date =
VAR _sel = MAX ( 'Dim Date'[Date] )
RETURN CALCULATE ( MAX ( 'Fact Bank Position'[Date] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] <= _sel )

// Last corporate balance date on/before the selected date (daily table, ACT + projections)
Corp Balance Date =
VAR _sel = MAX ( 'Dim Date'[Date] )
RETURN CALCULATE ( MAX ( 'Fact Corp Cash Balance'[Date] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] <= _sel )

Selected Scenario = SELECTEDVALUE ( 'Dim Scenario'[Scenario Key], "BASE" )
Is Projection = MAX ( 'Dim Date'[Date] ) > [As-of Date]
Scenario Label = SELECTEDVALUE ( 'Dim Scenario'[Scenario Name], "Multiple scenarios" )
```
`Reporting Date` uses `REMOVEFILTERS('Dim Date')`, so a filter on Year Month, Quarter or any other date column doesn't break the snapshot lookup. This is the fix for the old `Closing Balance` pattern.

## 2. Bank balances (folder `2. Balances`), snapshots: never sum across dates
```dax
Balance =
VAR _d = [Reporting Date]
RETURN CALCULATE ( SUM ( 'Fact Bank Position'[Balance RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d )

Total Assets      = CALCULATE ( [Balance], 'Dim Product'[Side] = "Asset" )
Total Funding     = CALCULATE ( [Balance], 'Dim Product'[Side] IN { "Liability", "Equity" } )
Total Deposits    = CALCULATE ( [Balance], 'Dim Product'[Category] IN { "Retail Deposits", "Wholesale Deposits" } )
Gross Loans       = CALCULATE ( [Balance], 'Dim Product'[Category] = "Loans" )
Wholesale Funding = CALCULATE ( [Balance], 'Dim Product'[Side] = "Liability",
                                'Dim Product'[Category] IN { "Wholesale Deposits", "Interbank", "Debt Securities" } )
Undrawn Commitments = CALCULATE ( [Balance], 'Dim Product'[Product Class] = "facility" )

// Average of month-end balances inside the selected period (history only), for annualised ratios
Average Balance =
AVERAGEX (
    CALCULATETABLE ( VALUES ( 'Dim Date'[Date] ), 'Dim Date'[Is Month End] = 1, 'Dim Date'[Days From Asof] <= 0 ),
    VAR _d = 'Dim Date'[Date]
    RETURN CALCULATE ( SUM ( 'Fact Bank Position'[Balance RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d ) )
```

## 3. Cash flows (folder `3. Cash Flows`), additive over time; + in / − out
```dax
// Bank realised flows
Bank Net Cash Flow = SUM ( 'Fact Bank CF History'[Amount RC] )
Bank Cash Inflows  = CALCULATE ( [Bank Net Cash Flow], 'Fact Bank CF History'[Amount RC] > 0 )
Bank Cash Outflows = CALCULATE ( [Bank Net Cash Flow], 'Fact Bank CF History'[Amount RC] < 0 )

// Corporate realised and forecast flows
Corp Actual Net Flow   = SUM ( 'Fact Corp CF Actual'[Amount RC] )
Corp Operating CF      = CALCULATE ( [Corp Actual Net Flow], 'Dim CF Category'[Activity] = "Operating" )
Corp Investing CF      = CALCULATE ( [Corp Actual Net Flow], 'Dim CF Category'[Activity] = "Investing" )
Corp Financing CF      = CALCULATE ( [Corp Actual Net Flow], 'Dim CF Category'[Activity] = "Financing" )
Corp Free Cash Flow    = [Corp Operating CF] + [Corp Investing CF]
Corp Forecast Net Flow (Generated) = SUM ( 'Fact Corp CF Forecast'[Amount RC] )

// Cumulative projected flow from the as-of date to the date in context (bank, selected scenario, what-if aware)
Cumulative Projected CF =
VAR _asof = [As-of Date]
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN IF ( _d > _asof, CALCULATE ( [Stressed Net CF], REMOVEFILTERS ( 'Dim Date' ),
                                    'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _d ) )
```
`[Stressed Net CF]` is defined in liquidity-measures §L4.

## 4. Variance (folder `4. Variance`), cash sign convention
Under **+ in / − out**, a higher signed cash amount is always better. There is **no expense inversion**; that was the old P&L logic. For metrics where *lower is better* (outflow amounts shown as positives, gap shortfalls), invert explicitly.
```dax
// Stress impact vs baseline (any scenario-driven measure follows the same pattern)
Stressed CF vs BASE =
[Stressed Net CF]
    - CALCULATE ( [Stressed Net CF], REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )

LCR vs BASE (pp) =
[LCR %] - CALCULATE ( [LCR %], REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )

// Forecast accuracy: needs forecast vintages (see treasury-liquidity-patterns §5).
// With the single-vintage synthetic data, forecast and actual do not overlap in time.
Forecast Error % =
VAR _act = [Corp Actual Net Flow]
VAR _fc = CALCULATE ( [Corp Forecast Net Flow (Generated)], REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )
RETURN DIVIDE ( _act - _fc, ABS ( _fc ) )

// Direction helper: +1 good, -1 bad. Pass the variance of a higher-is-better measure.
Cash Var Favourable = SIGN ( [Stressed CF vs BASE] )
Var Color = SWITCH ( [Cash Var Favourable], 1, "#1A7F5A", -1, "#C23B22", "#6B7280" )
Var Arrow = SWITCH ( [Cash Var Favourable], 1, "▲", -1, "▼", "●" )
```

## 5. Time intelligence: **flow measures only**
The dataset calendar is January to December (`"12-31"`). Never wrap snapshot or ratio measures (balances, HQLA, LCR %, NSFR %, CBC, survival, headroom) in YTD/MTD. Compare them at two dates instead, e.g. `CALCULATE([LCR %], DATEADD('Dim Date'[Date], -1, YEAR))`.
```dax
Corp Net Flow MTD = CALCULATE ( [Corp Actual Net Flow], DATESMTD ( 'Dim Date'[Date] ) )
Corp Net Flow YTD = CALCULATE ( [Corp Actual Net Flow], DATESYTD ( 'Dim Date'[Date], "12-31" ) )
Corp Net Flow PY  = CALCULATE ( [Corp Actual Net Flow], SAMEPERIODLASTYEAR ( 'Dim Date'[Date] ) )
Corp Net Flow Rolling 12M =
VAR _end = MIN ( MAX ( 'Dim Date'[Date] ), [As-of Date] )
RETURN CALCULATE ( [Corp Actual Net Flow], DATESINPERIOD ( 'Dim Date'[Date], _end, -12, MONTH ) )
Bank Net Cash Flow YTD = CALCULATE ( [Bank Net Cash Flow], DATESYTD ( 'Dim Date'[Date], "12-31" ) )
Months In Period = CALCULATE ( DISTINCTCOUNT ( 'Dim Date'[Year Month] ), 'Fact Bank CF History' )
Annualisation Factor = DIVIDE ( 12, [Months In Period] )
```
For many flow measures × periods, use the guarded Time Intelligence calculation group in `calc-groups.md` instead.

## 6. Bank funding & liquidity KPIs (folder `5. Bank Liquidity`)
```dax
Loan to Deposit % = DIVIDE ( [Gross Loans], [Total Deposits] )

// Non-maturity (current/savings/operational) deposits: the CASA-like, behaviourally sticky base
NMD Balance = CALCULATE ( [Balance], 'Dim Product'[Product Class] = "nmd" )
CASA Ratio % = DIVIDE ( [NMD Balance], [Total Deposits] )
Retail Funding Share % = DIVIDE ( CALCULATE ( [Balance], 'Dim Product'[Category] = "Retail Deposits" ), [Total Funding] )
Wholesale Funding Reliance % = DIVIDE ( [Wholesale Funding], [Total Funding] )
Short-term Wholesale Share % =
DIVIDE ( CALCULATE ( [Wholesale Funding], 'Dim Time Bucket'[In LCR 30D] = 1 ), [Wholesale Funding] )

// Concentration: share of deposits held by the 10 largest deposit contracts/accounts
Top 10 Deposit Concentration % =
VAR _d = [Reporting Date]
VAR _acc =
    CALCULATETABLE ( VALUES ( 'Fact Bank Position'[Contract Id] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d,
                     'Dim Product'[Category] IN { "Retail Deposits", "Wholesale Deposits" } )
VAR _top = TOPN ( 10, _acc, CALCULATE ( SUM ( 'Fact Bank Position'[Balance RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d ) )
RETURN DIVIDE ( CALCULATE ( [Total Deposits], _top ), [Total Deposits] )

// Balance-weighted contractual rate (use with a product/category filter)
Weighted Avg Rate % =
VAR _d = [Reporting Date]
RETURN DIVIDE (
    CALCULATE ( SUMX ( 'Fact Bank Position', 'Fact Bank Position'[Balance RC] * RELATED ( 'Dim Contract'[Interest Rate] ) ),
                REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d ),
    [Balance] )

// Net interest income, cash basis (asset interest +, liability interest -)
Net Interest Income = CALCULATE ( [Bank Net Cash Flow], 'Fact Bank CF History'[Flow Type] IN { "INTEREST", "NMD_INTEREST" } )
Interest Income  = CALCULATE ( [Net Interest Income], 'Dim Product'[Side] = "Asset" )
Interest Expense = - CALCULATE ( [Net Interest Income], 'Dim Product'[Side] <> "Asset" )
Avg Interest Earning Assets =
CALCULATE ( [Average Balance], 'Dim Product'[Side] = "Asset", NOT 'Dim Product'[Category] IN { "Other", "Cash & Reserves" } )
NIM % = DIVIDE ( [Net Interest Income] * [Annualisation Factor], [Avg Interest Earning Assets] )
```
Regulatory and stress metrics (`LCR %`, `NSFR %`, `HQLA Stock`, `CBC`, `Survival Days`, gaps) are in `liquidity-powerbi/references/liquidity-measures.md`.

## 7. Corporate treasury KPIs (folder `6. Corporate Treasury`)
```dax
// Snapshot helpers (bound to Corp Balance Date; respect Dim Scenario: ACT for history, a scenario for projections)
Corp Cash =
VAR _d = [Corp Balance Date]
RETURN CALCULATE ( SUM ( 'Fact Corp Cash Balance'[Closing RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d )

Corp Cash As-of =
CALCULATE ( SUM ( 'Fact Corp Cash Balance'[Closing RC] ), REMOVEFILTERS ( 'Dim Date' ), REMOVEFILTERS ( 'Dim Scenario' ),
            'Dim Date'[Date] = [As-of Date], 'Dim Scenario'[Scenario Key] = "ACT" )

Revolver Limit   = CALCULATE ( SUM ( 'Dim Facility'[Limit RC] ), 'Dim Facility'[Facility Type] <> "TERM" )
Revolver Drawn   = CALCULATE ( SUM ( 'Dim Facility'[Drawn Asof RC] ), 'Dim Facility'[Facility Type] <> "TERM" )
Facility Utilisation % = DIVIDE ( [Revolver Drawn], [Revolver Limit] )
Gross Debt (As-of) = SUM ( 'Dim Facility'[Drawn Asof RC] )
Net Debt (As-of)   = [Gross Debt (As-of)] - [Corp Cash As-of]

// Minimum-cash covenant headroom (cash only, before facilities)
Min Cash Covenant Headroom =
VAR _d = [Corp Balance Date]
RETURN CALCULATE ( SUM ( 'Fact Corp Cash Balance'[Closing RC] ) - SUM ( 'Fact Corp Cash Balance'[Min Cash RC] ),
                   REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d )

// Weeks of cover: liquidity sources / average weekly forecast outflow over the next 13 weeks
Weeks of Cover =
VAR _asof = [As-of Date]
VAR _out = CALCULATE ( SUM ( 'Fact Corp CF Forecast'[Amount RC] ), REMOVEFILTERS ( 'Dim Date' ),
                       'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _asof + 91, 'Fact Corp CF Forecast'[Amount RC] < 0 )
RETURN DIVIDE ( [Corp Cash As-of] + [Corp Undrawn Available], - _out / 13 )

// Working capital from invoices (relate Fact Corp Invoice[Invoice Date] -> Dim Date to trend by month)
DSO (days) =
VAR _t = FILTER ( 'Fact Corp Invoice', 'Fact Corp Invoice'[Invoice Type] = "AR" && 'Fact Corp Invoice'[Status] = "PAID" )
RETURN DIVIDE ( SUMX ( _t, DATEDIFF ( 'Fact Corp Invoice'[Invoice Date], 'Fact Corp Invoice'[Actual Pay Date], DAY )
                           * 'Fact Corp Invoice'[Amount RC At Asof FX] ),
                SUMX ( _t, 'Fact Corp Invoice'[Amount RC At Asof FX] ) )
DPO (days) = <same with "AP">
Cash Conversion Gap (days) = [DSO (days)] - [DPO (days)]          // no inventory in the dataset (DIO = 0)

Open AR = CALCULATE ( SUM ( 'Fact Corp Invoice'[Amount RC At Asof FX] ), 'Fact Corp Invoice'[Invoice Type] = "AR", 'Fact Corp Invoice'[Status] = "OPEN" )
Open AP = CALCULATE ( SUM ( 'Fact Corp Invoice'[Amount RC At Asof FX] ), 'Fact Corp Invoice'[Invoice Type] = "AP", 'Fact Corp Invoice'[Status] = "OPEN" )
Overdue AR =
VAR _asof = [As-of Date]
RETURN CALCULATE ( [Open AR], 'Fact Corp Invoice'[Due Date] < _asof )
Overdue AR % = DIVIDE ( [Overdue AR], [Open AR] )
Key Account AR Share % = DIVIDE ( CALCULATE ( [Open AR], 'Dim Counterparty'[Is Key Account] = 1 ), [Open AR] )
```
AR ageing bucket, as a calculated column on `Fact Corp Invoice` (as-of = 2026-09-30 in the default dataset; read it from `dim_date`):
```dax
AR Ageing =
VAR _asof = CALCULATE ( MAX ( 'Dim Date'[Date] ), ALL ( 'Dim Date' ), 'Dim Date'[Period Type] = "As-of" )
VAR _dpd = DATEDIFF ( 'Fact Corp Invoice'[Due Date], _asof, DAY )
RETURN IF ( 'Fact Corp Invoice'[Status] = "PAID", "Paid",
       SWITCH ( TRUE (), _dpd <= 0, "Not due", _dpd <= 30, "1-30", _dpd <= 60, "31-60", "60+" ) )
```
Cash/headroom projections, `Corp Undrawn Available`, `Corp Headroom`, `Corp Days to Breach` and the what-if versions are in liquidity-measures §L6.

## 8. Display helpers (folder `9. Helpers`)
```dax
Title As-of = "As of " & FORMAT ( [As-of Date], "dd MMM yyyy" ) & " · " & [Scenario Label]
Synthetic Data Label = "Synthetic data, for demonstration"
Amount Unit Label = MAXX ( FILTER ( 'Dim Currency', 'Dim Currency'[Is Reporting Currency] = 1 ), 'Dim Currency'[Currency Code] ) & " M"
```
