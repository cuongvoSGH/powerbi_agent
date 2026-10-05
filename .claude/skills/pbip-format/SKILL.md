---
name: pbip-format
description: How a Power BI Project (PBIP) is laid out on disk and how to read/write its TMDL semantic model and PBIR report files safely. Use whenever creating or editing files under *.SemanticModel/ or *.Report/, generating lineageTags, or validating a PBIP after changes.
---

# PBIP format (TMDL + PBIR)

## Folder layout
```
<Name>.pbip
<Name>.SemanticModel/
  definition.pbism
  definition/
    database.tmdl
    model.tmdl            # model settings + `ref table` list (controls table order)
    relationships.tmdl    # all relationships
    expressions.tmdl      # shared M queries and parameters (optional)
    cultures/en-US.tmdl
    tables/<Table Name>.tmdl   # one file per table: columns, measures, hierarchies, partitions
  .pbi/                   # DO NOT EDIT (cache, local settings)
<Name>.Report/
  definition.pbir         # points to the semantic model (byPath)
  definition/
    version.json
    report.json           # report-level settings, theme reference
    pages/
      pages.json          # pageOrder + activePageName
      <pageName>/page.json
      <pageName>/visuals/<visualName>/visual.json
  StaticResources/        # themes, images
```

## Rules for editing
1. **Desktop must be closed** while you write. It holds the files in memory and overwrites them on save.
2. **TMDL indentation uses TABS.**
   - Object properties are indented one level below the object.
   - Multi-line expressions (DAX/M) are indented one level deeper than the properties.
   - See `references/tmdl-syntax.md`.
3. **Names with spaces or special characters are single-quoted**, e.g. `table 'Fact Bank Position'` or `'Dim Date'[Date]`. A `'` inside a name is doubled.
4. **New table:** create `tables/<Table Name>.tmdl` **and** add `ref table <Name>` to `model.tmdl`.
5. **lineageTag:** every new table, column, measure, hierarchy and level gets a new GUID. Generate them with:
   ```
   python -c "import uuid;[print(uuid.uuid4()) for _ in range(10)]"
   ```
6. **Descriptions** go in `///` lines directly above the object declaration.
7. **PBIR `$schema` URLs:** copy the exact URL and version from files Desktop already generated in the project. Do not invent schema versions. If none exist yet, use the templates in `references/pbir-structure.md`.
8. **PBIR names:**
   - Page and visual names (the folder name equals the `name` property) are unique word-character strings. Use 20-char hex: `python -c "import uuid;print(uuid.uuid4().hex[:20])"`.
   - New pages must be added to `pages.json` → `pageOrder`.
9. **Field references** in visuals use `Entity` (table name, unquoted) + `Property` (column/measure name). They must match the TMDL names exactly, case included.

## Validate after every write
```
python .claude/skills/pbip-format/scripts/validate_pbip.py <project-root>
```
It checks:
- JSON parses
- every table in `tables/` is `ref`'d in `model.tmdl`
- relationship columns exist
- no duplicate lineageTags
- every visual field binding exists in the model
- `pages.json` matches the page folders

Fix every error before handing back to the user.

## References
- `references/tmdl-syntax.md`: tables, columns, measures, calculated columns/tables, hierarchies, partitions (M, calculated), relationships, parameters, calculation groups.
- `references/pbir-structure.md`: report.json, pages.json, page.json and visual.json skeletons, plus the field-reference shapes.
