# Treasury & liquidity model patterns (bank + corporate)

This is aligned with the dataset produced by the `liquidity-data-simulator` agent (`data/liquidity/`).
- Import list, friendly names and relationships: `liquidity-powerbi/references/model-design.md`.
- Column notes and as-of date: `data/liquidity/README.md`.
- Methodology: `liquidity-risk-methodology`.

Friendly names below follow the model-design mapping (snake_case → Title Case, acronyms RC/LCR/NSFR/HQLA kept; RC = reporting currency).

## 1. Core concepts to fix before modeling
| Concept | Rule |
|---|---|
| **As-of date** | The month-end the projection starts from. History is ≤ as-of; projections run from as-of + 1. `Dim Date[Days From Asof]` and `[Period Type]` (History / As-of / Projection / Contractual tail) come from the dataset. |
| **Three cash-flow views** | **Contractual** (what contracts say; `Fact Bank CF Contractual`), **behavioural** (BASE scenario) and **stressed** (other scenarios; `Fact Bank CF Stressed`). Never mix views in one measure without labelling. |
| **Sign convention** | Cash flows: **+ received, − paid** (bank and corporate). Balances are **positive**; the `Side Sign` on `Dim Product` (+1 asset / −1 liability, equity, off-balance) gives direction. There is no debit/credit `Report Sign`. |
| **Snapshot vs flow** | Snapshot tables (positions, HQLA, cash balance) are semi-additive: pick one date (`[Reporting Date]`), never sum over time. Flow tables are additive over time. |
| **Scenario** | `Dim Scenario` = **stress scenarios**: ACT (history), BASE, IDIO, MARKET, COMBINED, REVERSE, with `Scenario Type` actual / baseline / stress / reverse. Planning versions (Budget, Reforecast) are **not** scenarios. If they are ever needed, add a separate `Dim Version`. |
| **Currency** | Every amount exists as `… Local` and `… RC` (reporting currency: `meta.reporting_currency`, USD in `default`, EUR in `eba_sls`). Report in RC. Per-currency views filter `Dim Currency`. |

## 2. Conformed dimensions
| Dimension | Key | Used by | Notes |
|---|---|---|---|
| Dim Date | Date | all facts | Shipped in the dataset (history start → last contractual flow, ~26 years). Mark as the date table. Don't build a new one from a fact. |
| Dim Scenario | Scenario Key | stressed flows, survival, corporate forecast and balance, scenario parameter, reference metrics | Single-select slicer on KPI pages |
| Dim Currency | Currency Code | all facts | `Rate To RC Asof`, `Is Reporting Currency` = spot used for projections |
| Dim Entity | Entity Code | corporate facts, facilities, reference metrics | Bank, corporate group and subsidiaries (`Parent Entity Code`) |
| Dim Time Bucket | Bucket Key | positions, contractual and stressed flows | O/N … >5Y plus Non-maturity; `In LCR 30D`, `In 1Y`; sort by `Sort Order` |
| Dim Product | Product Code | all bank facts | Carries the regulatory parameters: `LCR Basis`, `LCR Flow`, `LCR Rate`, `HQLA Level`, `Base Haircut`, `NSFR Type`, NSFR factors, `Side`, `Category`, `Product Class` |
| Dim Segment | Segment Code | via Dim Product | Retail, SME, Corporate, FI, Sovereign, Central bank |

## 3. Bank (ALM / liquidity) patterns
```
Dim Date ─┬─ Fact Bank Position ─────┐
          ├─ Fact HQLA Holding ──────┤
          ├─ Fact Bank CF Contractual┼── Dim Product ── Dim Segment
          ├─ Fact Bank CF Stressed ──┤        Dim Contract (drill-through)
          ├─ Fact Bank CF History ───┘        Dim Time Bucket
          └─ Fact Bank Survival               Dim Scenario
```
| Table | Grain | Kind | Liquidity role |
|---|---|---|---|
| Fact Bank Position | contract × month-end | snapshot | Balances, `Principal Due 30D RC`, `Remaining Maturity Days`, `Bucket Key`, `NSFR Factor`, `LCR Base RC`. Feeds LCR outflows/inflows, NSFR, funding mix. |
| Fact HQLA Holding | security × month-end | snapshot | `HQLA Level`, `Price`, `Market Value RC`, `Encumbered`, `Base Haircut`. Feeds the HQLA stock and CBC. |
| Fact Bank CF Contractual | contract × payment date | flow (future) | Contractual ladder. `Flow Type` = SCHEDULED or NMD_ON_DEMAND (non-maturity balances repayable O/N). |
| Fact Bank CF Stressed | scenario × day × product × currency × flow type | flow (future) | Behavioural/stressed ladder and survival. `Flow Type`: CONTRACTUAL_PRINCIPAL, CONTRACTUAL_INTEREST, ROLLOVER, RUNOFF, DRAWDOWN, COLLATERAL_CALL. HQLA principal is excluded (it sits in the CBC). |
| Fact Bank CF History | day × product × currency × flow type | flow (past) | Realised flows: ORIGINATION, PRINCIPAL, INTEREST, NMD_NET_CHANGE, NMD_INTEREST. NII and funding trends. |
| Fact Bank Survival | scenario × currency scope × day | derived | Ready-made liquidity position curve (no what-if) |
| Dim Contract | contract | dimension | Start/maturity, rate, notional, encumbered, segment. Use for drill-through and concentration. **Do not** relate it to Dim Product (ambiguous path). |

**Attributes a real bank source must provide to support LCR/NSFR.** Map them when replacing the synthetic data:

| Attribute | Why |
|---|---|
| Deposit stability (insured + established relationship → stable) | Retail run-off 5% vs 10% |
| Operational deposit flag | 25% vs 40% run-off |
| Counterparty segment (retail, SME, corporate, FI, sovereign) | Run-off and inflow rates, ASF/RSF factors |
| Contractual maturity / repayment schedule | Due within 30 days, buckets, NSFR bands |
| Early-withdrawal option / penalty on term deposits | Whether > 30-day deposits are excluded from LCR |
| HQLA level, eligibility, encumbrance (repo / pledged) | HQLA stock and CBC |
| Undrawn committed amount by facility type | Facility outflows (5–100%) |
| Performing / NPL flag | Only performing inflows count |

## 4. Corporate treasury patterns
```
Dim Date ─┬─ Fact Corp CF Actual ───┬── Dim CF Category (IAS 7)
          ├─ Fact Corp CF Forecast ─┤   Dim Bank Account ── Dim Entity
          ├─ Fact Corp Cash Balance ┘   Dim Scenario
          └─ (Fact Corp Invoice: Invoice Date is an attribute; relate on Due Date only if ageing by date is needed)
Dim Facility ── Dim Entity        Fact Corp Invoice ── Dim Counterparty
```
| Table | Grain | Kind | Role |
|---|---|---|---|
| Fact Corp Cash Balance | scenario (incl. ACT) × day × account | snapshot | Opening, net flow, closing, drawn, undrawn available, minimum cash, **headroom**. Feeds cash position, headroom, days to breach. |
| Fact Corp CF Actual | day × entity × category × currency | flow | Realised cash by IAS 7 activity (interest paid classified as Financing) |
| Fact Corp CF Forecast | scenario × day × entity × category | flow | Direct-method 12-month forecast; first ~60 days driven by open AR/AP |
| Fact Corp Invoice | invoice | event | AR/AP with `Status` (PAID/OPEN), `Due Date`, `Actual Pay Date`, `Expected Pay Date`. Feeds DSO/DPO, ageing, collection forecast. |
| Dim Facility | facility | dimension | RCF / overdraft / term loan: limit, drawn at as-of, rate, maturity, covenant |
| Dim Counterparty | customer / supplier | dimension | Payment terms, average delay, key account rank (concentration) |

## 5. Forecast vintage (forecast accuracy)
Treasury re-forecasts weekly. To measure forecast accuracy, keep each forecast run instead of overwriting it:
- Add `Forecast Asof Date` to the forecast fact. The PK becomes scenario × forecast as-of × date × entity × category.
- Add a small `Dim Forecast Vintage` (date list), single-select. Default to the latest vintage.
- Accuracy = actual vs forecast for the same target date, made N weeks earlier. See `Forecast Error %` in `treasury-liquidity-measures.md`.

The synthetic dataset has one vintage (the as-of date). Add this pattern when real weekly forecasts arrive.

## 6. FX rules
| Amount | Rate |
|---|---|
| Realised cash flows (history) | Daily rate on the cash-flow date (`Fact FX Rate`) |
| Balances / snapshots | Closing rate on the snapshot date |
| Projections (contractual, stressed, forecast) | **As-of spot** (or forward rates if available) × (1 + scenario `fx_shock`) |
| Ratios across currencies (LCR, NSFR) | Compute in the reporting currency and per significant currency. FX shocks hit both HQLA and outflows. |

Convert in the source or in Power Query. The dataset already provides `… RC` columns, so there's no runtime FX lookup in DAX except for what-if FX shocks.

## 7. KPI → required tables
| KPI | Tables | Measures in |
|---|---|---|
| LCR (regulatory + stressed) | HQLA Holding, Bank Position, Dim Product, Scenario Parameter | `liquidity-powerbi/references/liquidity-measures.md` |
| NSFR | Bank Position, Dim Product | liquidity-measures |
| Maturity gap (contractual / behavioural) | Bank CF Contractual, Bank CF Stressed, Dim Time Bucket | liquidity-measures |
| CBC, survival horizon | HQLA Holding, Bank CF Stressed | liquidity-measures |
| Loan-to-deposit, CASA / stable funding, wholesale reliance, concentration | Bank Position, Dim Product, Dim Contract | `pbi-dax-measures/references/treasury-liquidity-measures.md` |
| NII, NIM | Bank CF History (interest flow types), Bank Position | treasury-liquidity-measures |
| Corporate cash, headroom, days to breach, weeks of cover | Corp Cash Balance, Corp CF Forecast, Dim Facility | treasury-liquidity-measures + liquidity-measures §L6 |
| Net debt, facility utilisation, covenant (minimum cash) headroom | Dim Facility, Corp Cash Balance | treasury-liquidity-measures |
| DSO, DPO, cash conversion, overdue AR | Corp Invoice | treasury-liquidity-measures |
| Forecast accuracy | Corp CF Forecast (with vintage) + Corp CF Actual | treasury-liquidity-measures |
