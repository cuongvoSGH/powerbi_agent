# PBIR visual.json templates

How to use these templates:
- Replace `$schema` with the URL used by existing visuals in the project.
- Replace `name` with a fresh 20-char hex string (also used as the folder name).
- Replace the entities and properties with real model names.
- Positions come from `assets/page-layouts.md`.

Shorthand used below:
- `M(x)` means a measure field: `{"Measure":{"Expression":{"SourceRef":{"Entity":"_Measures"}},"Property":"x"}}`
- `C(T,x)` means a column field: `{"Column":{"Expression":{"SourceRef":{"Entity":"T"}},"Property":"x"}}`

**Always expand the shorthand to full JSON** when writing files. Each projection is:
```json
{ "field": <field>, "queryRef": "<Entity>.<Property>", "nativeQueryRef": "<Property>" }
```

---

## 1. Title textbox (no query)
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json",
  "name": "0a1b2c3d4e5f60718293",
  "position": { "x": 16, "y": 10, "z": 0, "width": 560, "height": 40, "tabOrder": 0 },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [
        {
          "properties": {
            "paragraphs": [
              {
                "textRuns": [
                  {
                    "value": "Executive Summary",
                    "textStyle": { "fontFamily": "Segoe UI Semibold", "fontSize": "18pt", "color": "#1F3A5F" }
                  }
                ]
              }
            ]
          }
        }
      ]
    }
  }
}
```

## 2. Card (KPI tile)
```json
{
  "$schema": "<copy from project>",
  "name": "1b2c3d4e5f6071829304",
  "position": { "x": 16, "y": 68, "z": 1000, "width": 303, "height": 104, "tabOrder": 1000 },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Revenue" } },
              "queryRef": "_Measures.Revenue",
              "nativeQueryRef": "Revenue"
            }
          ]
        }
      }
    },
    "visualContainerObjects": {
      "title": [ { "properties": {
        "show": { "expr": { "Literal": { "Value": "true" } } },
        "text": { "expr": { "Literal": { "Value": "'Revenue YTD (USD M)'" } } }
      } } ]
    },
    "drillFilterOtherVisuals": true
  }
}
```
To show variance under the card, place a second small card (h ≈ 36) below it, bound to `Var % vs Budget`, with font colour from `Var Color` (labels → color → field value, set in Desktop). Alternatively bind a text measure such as `Var Arrow & " " & FORMAT([Var % vs Budget], "0.0%") & " vs budget"`.

## 3. KPI
`visualType: "kpi"`. queryState roles:
```json
"Indicator": { "projections": [ { M(Actual YTD) } ] },
"TrendLine": { "projections": [ { C(Dim Date, Fiscal Period) } ] },
"Goal":      { "projections": [ { M(Budget YTD) } ] }
```

## 4. Clustered column: Actual vs Budget by month
```json
"visual": {
  "visualType": "clusteredColumnChart",
  "query": {
    "queryState": {
      "Category": { "projections": [
        { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Date" } }, "Property": "Year Month" } },
          "queryRef": "Dim Date.Year Month", "nativeQueryRef": "Year Month", "active": true }
      ] },
      "Y": { "projections": [
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Actual" } },
          "queryRef": "_Measures.Actual", "nativeQueryRef": "Actual" },
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Budget" } },
          "queryRef": "_Measures.Budget", "nativeQueryRef": "Budget" }
      ] }
    },
    "sortDefinition": {
      "sort": [ { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Date" } }, "Property": "Year Month" } }, "direction": "Ascending" } ],
      "isDefaultSort": true
    }
  },
  "objects": {
    "dataPoint": [
      { "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#1F3A5F'" } } } } } },
        "selector": { "metadata": "_Measures.Actual" } },
      { "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#A8C5DA'" } } } } } },
        "selector": { "metadata": "_Measures.Budget" } }
    ]
  },
  "drillFilterOtherVisuals": true
}
```
The `dataPoint` + `selector.metadata` pattern fixes the series colours per measure: Actual navy, Budget pale blue, PY grey `#A0AEC0`, Forecast teal `#2A9D8F`.

## 5. Line trend (Actual vs PY vs Forecast)
`visualType: "lineChart"`.
- Category: `C(Dim Date, Year Month)`
- Y: `M(Actual)`, `M(Actual PY)`, `M(Forecast)`
- Use the same `dataPoint` colour pattern.

## 6. Combo (balances + ratio)
`visualType: "lineClusteredColumnComboChart"`.
- Category: `C(Dim Date, Year Month)`
- Y: `M(Gross Loans)` (columns)
- Y2: `M(NIM %)` (line)

## 7. Waterfall bridge
```json
"visual": {
  "visualType": "waterfallChart",
  "query": {
    "queryState": {
      "Category": { "projections": [
        { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Account" } }, "Property": "Account Group" } },
          "queryRef": "Dim Account.Account Group", "nativeQueryRef": "Account Group", "active": true }
      ] },
      "Y": { "projections": [
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Var vs Budget Signed" } },
          "queryRef": "_Measures.Var vs Budget Signed", "nativeQueryRef": "Var vs Budget Signed" }
      ] }
    }
  },
  "drillFilterOtherVisuals": true
}
```
For a profit bridge, the Y measure must use the **profit-impact sign**: revenue var as-is, expense var negated. That way green means "helped profit". Create `Var vs Budget Signed = [Var vs Budget] * IF(SELECTEDVALUE('Dim Account'[Account Class]) = "Expense", -1, 1)` in the measures skill. For a sorted bridge, add `sortDefinition` on the Y measure, descending.

## 8. Matrix: P&L with variance colouring
```json
"visual": {
  "visualType": "pivotTable",
  "query": {
    "queryState": {
      "Rows": { "projections": [
        { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Account" } }, "Property": "Account Group" } },
          "queryRef": "Dim Account.Account Group", "nativeQueryRef": "Account Group", "active": true },
        { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Account" } }, "Property": "Account Name" } },
          "queryRef": "Dim Account.Account Name", "nativeQueryRef": "Account Name" }
      ] },
      "Values": { "projections": [
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Actual" } },
          "queryRef": "_Measures.Actual", "nativeQueryRef": "Actual" },
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Budget" } },
          "queryRef": "_Measures.Budget", "nativeQueryRef": "Budget" },
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Var vs Budget" } },
          "queryRef": "_Measures.Var vs Budget", "nativeQueryRef": "Var vs Budget" },
        { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Var % vs Budget" } },
          "queryRef": "_Measures.Var % vs Budget", "nativeQueryRef": "Var % vs Budget" }
      ] }
    }
  },
  "objects": {
    "values": [
      {
        "properties": {
          "fontColor": { "solid": { "color": { "expr": {
            "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Var Color" }
          } } } }
        },
        "selector": { "data": [ { "dataViewWildcard": { "matchingOption": 1 } } ], "metadata": "_Measures.Var vs Budget" }
      },
      {
        "properties": {
          "fontColor": { "solid": { "color": { "expr": {
            "Measure": { "Expression": { "SourceRef": { "Entity": "_Measures" } }, "Property": "Var Color" }
          } } } }
        },
        "selector": { "data": [ { "dataViewWildcard": { "matchingOption": 1 } } ], "metadata": "_Measures.Var % vs Budget" }
      }
    ]
  },
  "drillFilterOtherVisuals": true
}
```
- If Desktop drops or reformats the conditional-formatting block, set it once in the UI (Cell elements → Font colour → fx → Field value → Var Color). Then copy the JSON Desktop writes back into this template.
- To order Rows by P&L line order, set `sortByColumn` in the model rather than sorting the visual.
- For a hierarchy, bind `HierarchyLevel` refs (see `pbip-format/references/pbir-structure.md`).

## 9. Bar ranking (variance by cost center)
`visualType: "clusteredBarChart"`.
- Category: `C(Dim Cost Center, Cost Center Name)`
- Y: `M(Var vs Budget Signed)`
- Sort by Y descending.
- Colour by rule: set it in Desktop (Bars → Colour → fx → Field value → `Var Color`). The PBIR is like the matrix block with `"dataPoint"` / `"fill"` and selector `{ "data": [ { "dataViewWildcard": { "matchingOption": 1 } } ] }`.

## 10. Table (top-N / detail)
`visualType: "tableEx"`.
- Values: columns and measures in display order.
- For Top N, add a visual-level filter in Desktop (Filters pane → Top N). It's simpler than writing filterConfig by hand.

## 11. Slicer (dropdown)
```json
"visual": {
  "visualType": "slicer",
  "query": {
    "queryState": {
      "Values": { "projections": [
        { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Dim Date" } }, "Property": "Fiscal Year" } },
          "queryRef": "Dim Date.Fiscal Year", "nativeQueryRef": "Fiscal Year", "active": true }
      ] }
    }
  },
  "objects": {
    "data": [ { "properties": { "mode": { "expr": { "Literal": { "Value": "'Dropdown'" } } } } } ],
    "selection": [ { "properties": { "singleSelect": { "expr": { "Literal": { "Value": "true" } } } } } ]
  },
  "drillFilterOtherVisuals": true
}
```
