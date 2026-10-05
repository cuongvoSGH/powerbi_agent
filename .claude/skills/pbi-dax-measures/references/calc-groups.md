# Calculation groups (liquidity model)

## When to use
- **Use them** when the same transformation applies to many measures:
  - period logic on cash-flow measures
  - "vs BASE" on stress metrics
  - reporting currency vs local currency
- **Skip them** when there are only a few measures, or when users analyse in Excel or Q&A.
- The model must have `discourageImplicitMeasures` in `model.tmdl`.

**Liquidity rule:** a calculation group applies to *every* measure in the visual. Two kinds of measure must not be transformed:
- **Snapshot** measures: balances, HQLA, CBC, cash, headroom
- **Ratio / day-count** measures: LCR %, NSFR %, Survival Days, LTD %

Each item below starts with a guard that returns `SELECTEDMEASURE()` unchanged for those measures. Keep the guard list in sync with the measure library.

## 1. Time Intelligence: flow measures only (tables/Time Intelligence.tmdl)
The calendar year-end is `"12-31"`, matching the dataset's `dim_date`. History stops at the as-of date, so YTD/PY work on actual flows. Projection flows have no prior year.

```tmdl
/// Period logic for cash-flow measures. Snapshot and ratio measures are passed through unchanged.
table 'Time Intelligence'
	lineageTag: <guid>

	calculationGroup
		precedence: 20

		calculationItem Current = SELECTEDMEASURE()
			ordinal: 0

		calculationItem MTD =
				IF ( ISSELECTEDMEASURE ( [Balance], [Total Assets], [Total Deposits], [Gross Loans], [HQLA Stock], [CBC],
				                         [LCR %], [NSFR %], [Survival Days], [Loan to Deposit %], [Corp Cash], [Corp Headroom] ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESMTD ( 'Dim Date'[Date] ) ) )
			ordinal: 1

		calculationItem QTD =
				IF ( ISSELECTEDMEASURE ( [Balance], [Total Assets], [Total Deposits], [Gross Loans], [HQLA Stock], [CBC],
				                         [LCR %], [NSFR %], [Survival Days], [Loan to Deposit %], [Corp Cash], [Corp Headroom] ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESQTD ( 'Dim Date'[Date] ) ) )
			ordinal: 2

		calculationItem YTD =
				IF ( ISSELECTEDMEASURE ( [Balance], [Total Assets], [Total Deposits], [Gross Loans], [HQLA Stock], [CBC],
				                         [LCR %], [NSFR %], [Survival Days], [Loan to Deposit %], [Corp Cash], [Corp Headroom] ),
				     SELECTEDMEASURE (),
				     CALCULATE ( SELECTEDMEASURE (), DATESYTD ( 'Dim Date'[Date], "12-31" ) ) )
			ordinal: 3

		calculationItem PY = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Dim Date'[Date] ) )
			ordinal: 4

		calculationItem 'YoY %' =
				VAR _cur = SELECTEDMEASURE ()
				VAR _py = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( 'Dim Date'[Date] ) )
				RETURN DIVIDE ( _cur - _py, ABS ( _py ) )
			ordinal: 5

			formatStringDefinition = "0.0%"
```
`PY` is safe for snapshots too: shifting the date filter moves `[Reporting Date]` back a year, giving last year's LCR or balance. So it has no guard.

Calc-group columns (`'Time Calc'` sourced from `Name` and sorted by `Ordinal`) and the `partition … = calculationGroup` block are the same as in `pbip-format/references/tmdl-syntax.md`.

## 2. Stress Comparison: vs BASE (tables/Stress Comparison.tmdl)
This is for scenario-driven measures: stressed flows, LCR %, CBC, Survival Days, corporate headroom. Use it on matrices with Dim Scenario on rows.
```tmdl
/// Compare the scenario in context with the BASE scenario.
table 'Stress Comparison'
	lineageTag: <guid>

	calculationGroup
		precedence: 10

		calculationItem Selected = SELECTEDMEASURE ()
			ordinal: 0

		calculationItem Base =
				CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )
			ordinal: 1

		calculationItem 'Δ vs Base' =
				SELECTEDMEASURE ()
				    - CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )
			ordinal: 2

		calculationItem 'Δ % vs Base' =
				VAR _b = CALCULATE ( SELECTEDMEASURE (), REMOVEFILTERS ( 'Dim Scenario' ), 'Dim Scenario'[Scenario Key] = "BASE" )
				RETURN IF ( ISSELECTEDMEASURE ( [LCR %], [NSFR %] ), BLANK (), DIVIDE ( SELECTEDMEASURE () - _b, ABS ( _b ) ) )
			ordinal: 3

			formatStringDefinition = "0.0%"
```
Notes:
- The liquidity measures read the scenario through `[Selected Scenario]` = `SELECTEDVALUE('Dim Scenario'[Scenario Key], "BASE")`. Filtering `Dim Scenario` inside the calc item is therefore enough.
- For ratios, read `Δ vs Base` as percentage points. `Δ %` is blanked for them.
- **ACT has no projections.** Comparing ACT with BASE is only meaningful for snapshot measures at the as-of date.
- Planning versions (Budget/Reforecast), if added later, go in a separate `Dim Version` with its own calc group. Never put them in `Dim Scenario`.

## 3. Currency View (optional)
For measures that exist as reporting-currency (RC) and local pairs. Use it only when one currency is filtered; local amounts of different currencies must not be summed.
```tmdl
table 'Currency View'
	lineageTag: <guid>

	calculationGroup
		precedence: 5

		calculationItem 'Reporting currency' = SELECTEDMEASURE ()
			ordinal: 0

		calculationItem Local =
				IF ( HASONEVALUE ( 'Dim Currency'[Currency Code] ),
				     SWITCH ( TRUE (),
				         ISSELECTEDMEASURE ( [Balance] ), CALCULATE ( SUM ( 'Fact Bank Position'[Balance Local] ),
				                                         REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = [Reporting Date] ),
				         ISSELECTEDMEASURE ( [Corp Actual Net Flow] ), SUM ( 'Fact Corp CF Actual'[Amount Local] ),
				         SELECTEDMEASURE () ) )
			ordinal: 1
```

## Precedence
A higher `precedence` is applied first, i.e. outermost:
- Time Intelligence = 20
- Stress Comparison = 10
- Currency View = 5

So "YTD flow Δ vs Base" applies the scenario switch inside the YTD window.

## Using them in visuals
- Put the calc-group column on matrix **Columns**, with base measures in **Values**.
- Alternatively, filter a card to one item.

In PBIR the column is a normal `Column` reference, e.g. Entity `Stress Comparison`, Property `Stress Calc`.
