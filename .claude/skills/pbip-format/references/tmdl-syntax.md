# TMDL syntax reference

These examples use real TAB indentation:
- object at level 1
- properties at level 2
- multi-line expression bodies at level 3

GUIDs below are placeholders (`<guid>`). Always generate new ones.

## model.tmdl
```tmdl
model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	discourageImplicitMeasures
	sourceQueryCulture: en-US

ref table 'Dim Date'
ref table 'Dim Product'
ref table 'Fact Bank Position'
ref table _Measures

ref cultureInfo en-US
```
Keep the existing header lines as Desktop wrote them. Usually you only add `ref table` lines and `discourageImplicitMeasures`.

## Import table with M partition
```tmdl
/// Bank positions: one row per contract per month-end (snapshot - semi-additive).
table 'Fact Bank Position'
	lineageTag: <guid>

	column Date
		dataType: dateTime
		formatString: Short Date
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: date

	column 'Product Code'
		dataType: string
		isHidden
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: product_code

	column 'Balance RC'
		dataType: decimal
		isHidden
		formatString: #,##0.00
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: balance_rc

	partition 'Fact Bank Position' = m
		mode: import
		source =
				let
				    Source = Csv.Document(File.Contents(DataFolder & "fact_bank_position.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
				    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
				    Typed = Table.TransformColumnTypes(Promoted, {{"date", type date}, {"product_code", type text}, {"balance_rc", Currency.Type}}, "en-US")
				in
				    Typed
```
Notes:
- `sourceColumn` is the column name produced by the M query. The TMDL `column` name is the friendly display name.
- dataType values: `string`, `int64`, `double`, `decimal` (fixed decimal / Currency.Type), `dateTime`, `boolean`.
- Flags with no value: `isHidden`, `isKey`, `isNameInferred`, `discourageImplicitMeasures`.
- `summarizeBy`: `none` for keys, attributes, rates and **all snapshot balances** (semi-additive); `sum` only for additive flow amounts, which should still be hidden behind measures.
- Sorting: `sortByColumn: 'Month Number'` on the text column.
- Other column properties: `displayFolder: Keys`, `dataCategory: City` (geo).

## Measures (usually in the `_Measures` table)
```tmdl
table _Measures
	lineageTag: <guid>

	/// Realised corporate net cash flow, reporting currency. Sign: + received, - paid.
	measure 'Corp Actual Net Flow' = SUM('Fact Corp CF Actual'[Amount RC])
		formatString: #,##0;(#,##0);-
		displayFolder: 3. Cash Flows
		lineageTag: <guid>

	/// Bank balance (reporting currency, positive) at the reporting date = last month-end snapshot on/before the selected date.
	measure Balance =
			VAR _d = [Reporting Date]
			RETURN CALCULATE(SUM('Fact Bank Position'[Balance RC]), REMOVEFILTERS('Dim Date'), 'Dim Date'[Date] = _d)
		formatString: #,##0
		displayFolder: 2. Balances
		lineageTag: <guid>

	column Column
		dataType: string
		isHidden
		lineageTag: <guid>
		summarizeBy: none
		isNameInferred
		sourceColumn: [Column]

	partition _Measures = calculated
		mode: import
		source = Row("Column", BLANK())
```
- A single-line expression stays on the declaration line.
- A multi-line expression starts on the next line, indented one level deeper than the properties.
- Nested display folders use a backslash: `displayFolder: 5. Bank Liquidity\Funding`.
- Hidden measure: add `isHidden`.

## Calculated column / calculated table
```tmdl
	column 'Is HQLA' = 'Dim Product'[HQLA Level] <> ""
		dataType: boolean
		lineageTag: <guid>
		summarizeBy: none
```
Calculated table: `partition <Name> = calculated` with a DAX `source`. Its columns use `isNameInferred` and `sourceColumn: [ColumnName]` (square brackets). See `pbi-data-modeling/templates/date-table.tmdl`.

## Date table marking
On the table add `dataCategory: Time`. On the date column add `isKey`. The column must be `dateTime`, unique and contiguous.

## Hierarchy
```tmdl
	hierarchy 'Product Hierarchy'
		lineageTag: <guid>

		level Side
			lineageTag: <guid>
			column: Side

		level Category
			lineageTag: <guid>
			column: Category

		level Product
			lineageTag: <guid>
			column: 'Product Name'
```

## relationships.tmdl
```tmdl
relationship <guid>
	fromColumn: 'Fact Bank Position'.Date
	toColumn: 'Dim Date'.Date

relationship <guid>
	fromColumn: 'Fact Bank Position'.'Product Code'
	toColumn: 'Dim Product'.'Product Code'

relationship <guid>
	isActive: false
	fromColumn: 'Fact Corp Invoice'.'Due Date'
	toColumn: 'Dim Date'.Date
```
- `from` is the many side (the fact) and `to` is the one side (the dimension). The default is many-to-one, single direction.
- Optional properties:
  - `crossFilteringBehavior: bothDirections`
  - `toCardinality: many` (many-to-many)
  - `isActive: false`
  - `joinOnDateBehavior: datePartOnly`
- Column refs here use `Table.Column`, both quoted when needed. (DAX uses `Table[Column]`.)

## Parameters / shared queries (expressions.tmdl)
```tmdl
expression DataFolder = "D:\Personal\powerbi\bi_report_using_agent\data\liquidity\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: <guid>

expression SqlServer = "sql-prod-01" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: <guid>

expression SqlDatabase = "TreasuryDW" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
	lineageTag: <guid>
```

## Calculation group
See `pbi-dax-measures/references/calc-groups.md`. Shape:
```tmdl
table 'Time Intelligence'
	lineageTag: <guid>

	calculationGroup
		precedence: 10

		calculationItem Current = SELECTEDMEASURE()

		calculationItem YTD = CALCULATE(SELECTEDMEASURE(), DATESYTD('Dim Date'[Date], "12-31"))

	column 'Time Calc'
		dataType: string
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Name
		sortByColumn: Ordinal

	column Ordinal
		dataType: int64
		isHidden
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Ordinal

	partition 'Time Intelligence' = calculationGroup
		mode: import
```
- Calculation items take `ordinal: <n>` as a property line if you need explicit ordering.
- The model must have `discourageImplicitMeasures`.
