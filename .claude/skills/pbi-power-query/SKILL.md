---
name: pbi-power-query
description: Write Power Query (M) for Power BI tables from CSV, Excel and SQL databases - parameters, query folding, typing, cleaning, flattening hierarchies, unknown members - and profile source data files before modeling. Use when creating table partitions/source queries in TMDL or when the user shares data files or a SQL schema.
---

# Power Query (M)

## Step 1: Profile before you write
```
python .claude/skills/pbi-power-query/scripts/profile_data.py <file-or-folder> [more ...] [--out docs/data-profile.md]
```
The output covers:
- rows and columns
- inferred types
- null %
- distinct counts
- candidate keys
- likely role (key, date, measure, attribute)
- cross-file foreign-key candidates (value containment)

Use it to decide grain, keys and relationships.

- Excel files need `openpyxl`. If it's missing, the script tells the user to run `pip install openpyxl`.
- For SQL, ask the user for the DDL or `INFORMATION_SCHEMA.COLUMNS` output. Don't guess.

## Step 2: Write queries
The partition goes in each `tables/<Table>.tmdl` (`partition <Table> = m`, see `pbip-format`). Shared parameters go in `expressions.tmdl`.

### Rules
1. **Parameterise locations:**
   - CSV/Excel: `DataFolder`
   - SQL: `SqlServer`, `SqlDatabase`

   Never hard-code a path or server inside a table query.
2. **SQL: keep query folding.**
   - Navigate with `Source{[Schema="dbo",Item="FactGL"]}[Data]`.
   - Then select columns, filter, rename and type. These steps fold.
   - Add columns that break folding (custom M functions, `Table.Buffer`, index columns) last, or push them to a SQL view.
   - Use `Value.NativeQuery(..., [EnableFolding=true])` only when a view isn't possible.
3. **Select columns explicitly** with `Table.SelectColumns` early. Drop everything the model doesn't need.
4. **Type every column** in one `Table.TransformColumnTypes` step:
   - money: `Currency.Type` (fixed decimal) → TMDL `decimal`
   - integers: `Int64.Type`
   - dates: `type date`
   - Pass a culture (`"en-US"`, `"en-GB"`) when parsing text dates or numbers from CSV.
5. **Rename to business names in M.** Make the M output column names match `sourceColumn`, or keep the source names and set friendly names in TMDL `column` declarations. Pick one approach and keep to it within the project.
6. **Clean keys:**
   - `Text.Trim`, consistent case.
   - Replace null or blank foreign keys with an Unknown key (e.g. `-1`).
   - Add a matching `-1 "Unknown"` row to the dimension.
7. **Finance transforms belong here, not in DAX calculated columns:**
   - Reporting sign: merge `Report Sign` from the account mapping and multiply.
   - Flatten parent-child CoA into level columns.
   - Normalise budget files from wide (Jan…Dec columns) to long with `Table.UnpivotOtherColumns`, then build `Month Start Date`.
   - FX conversion, when it's static.
8. **Helper queries:** staging queries such as a CSV folder combine or a CoA lookup are shared expressions in `expressions.tmdl`. They don't load to the model: TMDL expressions without a table partition are not loaded.

## References
- `references/source-patterns.md`: copy-ready M for:
  - CSV file / CSV folder
  - Excel table or sheet
  - SQL Server, PostgreSQL, Snowflake
  - wide-to-long budget unpivot
  - parent-child flattening
  - unknown-member handling
