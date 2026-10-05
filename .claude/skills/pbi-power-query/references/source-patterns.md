# Power Query source patterns

These go in `source =` of a TMDL partition, indented one level deeper than `source`. Parameters (`DataFolder`, `SqlServer`, `SqlDatabase`) are defined in `expressions.tmdl`. `DataFolder` ends with a backslash.

## Single CSV
```m
let
    Source = Csv.Document(
        File.Contents(DataFolder & "gl_transactions.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Selected = Table.SelectColumns(Promoted, {"PostingDate", "AccountCode", "CostCenter", "Amount"}),
    Typed = Table.TransformColumnTypes(
        Selected,
        {{"PostingDate", type date}, {"AccountCode", type text}, {"CostCenter", type text}, {"Amount", Currency.Type}},
        "en-US"
    )
in
    Typed
```

## Folder of CSVs with the same layout (e.g. one file per month)
```m
let
    Files = Folder.Files(DataFolder & "gl\"),
    CsvOnly = Table.SelectRows(Files, each Text.Lower([Extension]) = ".csv" and not Text.StartsWith([Name], "~")),
    Parsed = Table.AddColumn(CsvOnly, "Data", each
        Table.PromoteHeaders(
            Csv.Document([Content], [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            [PromoteAllScalars = true])),
    Combined = Table.Combine(Parsed[Data]),
    Typed = Table.TransformColumnTypes(Combined, {{"PostingDate", type date}, {"Amount", Currency.Type}}, "en-US")
in
    Typed
```

## Excel table (preferred) or sheet
```m
let
    Source = Excel.Workbook(File.Contents(DataFolder & "budget_2026.xlsx"), null, true),
    // Named table:
    Budget = Source{[Item = "tblBudget", Kind = "Table"]}[Data],
    // Or a sheet: Source{[Item = "Budget", Kind = "Sheet"]}[Data] then Table.PromoteHeaders(...)
    Typed = Table.TransformColumnTypes(Budget, {{"AccountCode", type text}, {"CostCenter", type text}})
in
    Typed
```

## Budget wide → long (Jan..Dec columns)
```m
let
    Source = ...,   // columns: AccountCode, CostCenter, FiscalYear, Jan, Feb, ..., Dec
    Long = Table.UnpivotOtherColumns(Source, {"AccountCode", "CostCenter", "FiscalYear"}, "MonthName", "Amount"),
    WithMonthNo = Table.AddColumn(Long, "MonthNo", each
        List.PositionOf({"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"}, [MonthName]) + 1,
        Int64.Type),
    // Calendar-year budget. For a fiscal year starting in month S, use the year in which that month falls instead.
    WithDate = Table.AddColumn(WithMonthNo, "MonthStartDate", each #date([FiscalYear], [MonthNo], 1), type date),
    Result = Table.TransformColumnTypes(
        Table.RemoveColumns(WithDate, {"MonthName", "MonthNo", "FiscalYear"}),
        {{"Amount", Currency.Type}})
in
    Result
```

## SQL Server (folding)
```m
let
    Source = Sql.Database(SqlServer, SqlDatabase),
    FactGL = Source{[Schema = "dbo", Item = "FactGL"]}[Data],
    Selected = Table.SelectColumns(FactGL, {"PostingDate", "AccountKey", "CostCenterKey", "EntityKey", "Amount"}),
    Filtered = Table.SelectRows(Selected, each [PostingDate] >= #date(2022, 1, 1))
in
    Filtered
```
Other connectors:
- PostgreSQL: `PostgreSQL.Database(SqlServer, SqlDatabase)`, navigation `{[Schema="public",Item="fact_gl"]}`.
- Snowflake: `Snowflake.Databases(SqlServer, Warehouse){[Name=SqlDatabase]}[Data]{[Name="PUBLIC",Kind="Schema"]}[Data]{[Name="FACT_GL",Kind="Table"]}[Data]`.

Native SQL, only when a view isn't possible:
```m
Value.NativeQuery(Sql.Database(SqlServer, SqlDatabase),
    "SELECT PostingDate, AccountKey, SUM(Amount) AS Amount FROM dbo.FactGL GROUP BY PostingDate, AccountKey",
    null, [EnableFolding = true])
```

## Reporting sign (merge from account mapping)
```m
let
    GL = ...,
    Accounts = #"Stg Account",   // shared expression
    Joined = Table.NestedJoin(GL, {"AccountCode"}, Accounts, {"AccountCode"}, "Acc", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "Acc", {"AccountKey", "ReportSign"}),
    Signed = Table.AddColumn(Expanded, "AmountReporting",
        each [Amount] * (if [ReportSign] = null then 1 else [ReportSign]), Currency.Type),
    UnknownKey = Table.ReplaceValue(Signed, null, -1, Replacer.ReplaceValue, {"AccountKey"})
in
    Table.RemoveColumns(UnknownKey, {"ReportSign", "AccountCode"})
```

## Parent-child chart of accounts → level columns
```m
let
    Src = ...,   // AccountCode, AccountName, ParentCode (null at root)
    Lookup = Record.FromList(Src[ParentCode], Src[AccountCode]),
    Names  = Record.FromList(Src[AccountName], Src[AccountCode]),
    PathOf = (code as text) as list =>
        List.Reverse(List.Generate(
            () => code,
            each _ <> null,
            each Record.FieldOrDefault(Lookup, _, null))),
    WithPath = Table.AddColumn(Src, "Path", each PathOf([AccountCode])),
    L1 = Table.AddColumn(WithPath, "Level 1", each Record.FieldOrDefault(Names, List.First([Path]), null), type text),
    L2 = Table.AddColumn(L1, "Level 2", each
        if List.Count([Path]) >= 2 then Record.FieldOrDefault(Names, [Path]{1}, null) else [AccountName], type text),
    L3 = Table.AddColumn(L2, "Level 3", each
        if List.Count([Path]) >= 3 then Record.FieldOrDefault(Names, [Path]{2}, null) else [AccountName], type text),
    Result = Table.RemoveColumns(L3, {"Path"})
in
    Result
```
Leaves that are shallower than the deepest level repeat their own name in the lower levels. That avoids blank rows in the matrix (the "ragged hierarchy" fix). Keep only leaf (posting) accounts if the GL only posts to leaves.

## Unknown member row for a dimension
```m
let
    Dim = ...,
    Unknown = #table(Table.ColumnNames(Dim), {List.Transform(Table.ColumnNames(Dim),
        each if _ = "AccountKey" then -1 else if Text.Contains(_, "Name") then "Unknown" else null)}),
    Result = Table.Combine({Dim, Unknown})
in
    Result
```
