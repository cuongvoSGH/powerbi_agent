# PBIR structure reference

> **Schema versions change between Desktop releases.** Always copy the `$schema` URLs from
> files that already exist in the user's `*.Report/definition/` folder. The versions below are
> examples only.

## pages/pages.json
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
  "pageOrder": ["a1f0c2d3e4b5a6978812", "b2e1d3c4f5a6b7c8d9e0"],
  "activePageName": "a1f0c2d3e4b5a6978812"
}
```

## pages/<pageName>/page.json
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
  "name": "a1f0c2d3e4b5a6978812",
  "displayName": "Executive Summary",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280
}
```
The folder name must equal `name`. Options for `displayOption` are `FitToPage`, `FitToWidth` and `ActualSize`.

## pages/<pageName>/visuals/<visualName>/visual.json
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json",
  "name": "c3d4e5f6a7b8c9d0e1f2",
  "position": { "x": 16, "y": 76, "z": 1000, "width": 300, "height": 110, "tabOrder": 1000 },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Measures" } },
                  "Property": "Actual"
                }
              },
              "queryRef": "_Measures.Actual",
              "nativeQueryRef": "Actual"
            }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

### Field reference shapes
Column:
```json
{ "Column": { "Expression": { "SourceRef": { "Entity": "Dim Date" } }, "Property": "Year Month" } }
```
Measure:
```json
{ "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Budget" } }
```
Hierarchy level:
```json
{ "HierarchyLevel": { "Expression": { "Hierarchy": { "Expression": { "SourceRef": { "Entity": "Dim Account" } }, "Hierarchy": "Account Hierarchy" } }, "Level": "Account Group" } }
```
Rules for `queryRef` and `nativeQueryRef`:
- `queryRef` is `"<Entity>.<Property>"` (for hierarchy levels: `"Dim Account.Account Hierarchy.Account Group"`).
- `nativeQueryRef` is the display name.
- An aggregated column, e.g. `Sum(...)`, should not be used. Always bind measures.

### Sorting (inside `query`)
```json
"sortDefinition": {
  "sort": [ { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Actual" } }, "direction": "Descending" } ],
  "isDefaultSort": false
}
```

### Title and formatting (`visual.visualContainerObjects` / `visual.objects`)
Literal values are DAX-style literal strings:
- text: `"'Revenue'"`
- number: `"14D"`
- boolean: `"true"`
- colour: `{"solid":{"color":{"expr":{"Literal":{"Value":"'#1F3A5F'"}}}}}`
```json
"visualContainerObjects": {
  "title": [ { "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "text": { "expr": { "Literal": { "Value": "'Revenue vs Budget'" } } }
  } } ]
}
```
Prefer the theme for styling. Only set per-visual objects for titles and conditional formatting.

## Query roles by visualType
| visualType | Roles |
|---|---|
| `card` | `Values` |
| `cardVisual` (new card) | `Data` |
| `kpi` | `Indicator`, `TrendLine`, `Goal` |
| `clusteredColumnChart`, `clusteredBarChart`, `stackedColumnChart`, `stackedBarChart` | `Category`, `Y`, `Series` |
| `lineChart` | `Category`, `Y`, `Series` (`Y2` secondary axis) |
| `lineClusteredColumnComboChart` | `Category`, `Y` (columns), `Y2` (lines) |
| `waterfallChart` | `Category`, `Y`, `Breakdown` |
| `pivotTable` (matrix) | `Rows`, `Columns`, `Values` |
| `tableEx` (table) | `Values` |
| `donutChart`, `pieChart` | `Category`, `Y` |
| `gauge` | `Y`, `MinValue`, `MaxValue`, `TargetValue` |
| `slicer` | `Values` |
| `textbox`, `shape`, `image` | no query |

Concrete templates for each are in `pbi-report-visuals/references/visual-templates.md`.

## report.json theme
The safest way to apply a custom theme is in Desktop: **View → Themes → Browse for themes**. Desktop copies the theme into `StaticResources/RegisteredResources/` and updates `report.json`. Only edit `report.json` by hand if a custom theme is already registered and you are replacing its file contents in place, keeping the same file name.
