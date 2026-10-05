# Liquidity DAX measure library

The table and column names follow `model-design.md`. All amounts are in the **reporting currency** (`… RC` columns; USD in the default profile, EUR in `eba_sls`). Every measure in TMDL also needs a `///` description, `formatString`, `displayFolder` and `lineageTag`.

**Prerequisite:** the foundation measures in `pbi-dax-measures/references/treasury-liquidity-measures.md`. These include:
- `As-of Date`, `Reporting Date`, `Corp Balance Date`, `Selected Scenario`
- balances: `Balance`, `Total Assets`, `Total Deposits`, `Gross Loans`
- `Corp Actual Net Flow`, `Corp Cash As-of`, DSO/DPO, Open AR/AP

They are defined **once** there. Don't redefine them here.

## L1. Scenario parameters
(`As-of Date`, `Reporting Date` and `Selected Scenario` come from the foundation library.)
```dax
// Generic scenario driver lookup helpers (0 / neutral when not defined, e.g. ACT)
Param Outflow Multiplier =
VAR _s = [Selected Scenario]
VAR _p = CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
                     'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "lcr_outflow_multiplier" )
RETURN COALESCE ( _p, 1 ) * [WI Outflow Multiplier Value]
```
Two lookups are used inline below, because they depend on the row's currency or HQLA level:
```dax
// FX factor for currency _ccy:  1 + scenario fx_shock (+ what-if shock on the currency chosen in 'WI FX Currency')
VAR _fx = 1 + COALESCE ( CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
              'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "fx_shock",
              'Scenario Parameter'[Currency Code] = _ccy ), 0 )
          + IF ( _ccy = [WI FX Shock Currency], [WI FX Shock Value], 0 )
// Haircut add-on for level _lvl
VAR _add = COALESCE ( CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
              'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "hqla_haircut_addon",
              'Scenario Parameter'[HQLA Level] = _lvl ), 0 ) + [WI Haircut Addon Value]
```

## L2. HQLA & LCR
```dax
// Unencumbered counterbalancing stock after base + scenario haircuts and FX shock, at the reporting date (no caps).
// Includes CB_ELIGIBLE (central-bank-eligible non-HQLA) holdings - use the level measures below for the LCR.
HQLA After Haircut =
VAR _d = [Reporting Date]
VAR _s = [Selected Scenario]
VAR _grp =
    CALCULATETABLE (
        SUMMARIZE ( 'Fact HQLA Holding', 'Fact HQLA Holding'[HQLA Level], 'Fact HQLA Holding'[Currency Code] ),
        REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Fact HQLA Holding'[Encumbered] = 0 )
RETURN
    SUMX ( _grp,
        VAR _lvl = 'Fact HQLA Holding'[HQLA Level]
        VAR _ccy = 'Fact HQLA Holding'[Currency Code]
        VAR _mv = CALCULATE ( SUM ( 'Fact HQLA Holding'[Market Value RC] ), REMOVEFILTERS ( 'Dim Date' ),
                              'Dim Date'[Date] = _d, 'Fact HQLA Holding'[Encumbered] = 0 )
        VAR _base = CALCULATE ( MAX ( 'Fact HQLA Holding'[Base Haircut] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d )
        VAR _add = COALESCE ( CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
                      'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "hqla_haircut_addon",
                      'Scenario Parameter'[HQLA Level] = _lvl ), 0 ) + [WI Haircut Addon Value]
        VAR _fx = 1 + COALESCE ( CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
                      'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "fx_shock",
                      'Scenario Parameter'[Currency Code] = _ccy ), 0 ) + IF ( _ccy = [WI FX Shock Currency], [WI FX Shock Value], 0 )
        RETURN _mv * ( 1 - MIN ( _base + _add, 1 ) ) * _fx
    )

HQLA L1  = CALCULATE ( [HQLA After Haircut], 'Fact HQLA Holding'[HQLA Level] = "L1" )    // Level 1 excl. covered bonds
HQLA L1B = CALCULATE ( [HQLA After Haircut], 'Fact HQLA Holding'[HQLA Level] = "L1B" )   // EU: EHQ covered bonds (7% haircut)
HQLA L2A = CALCULATE ( [HQLA After Haircut], 'Fact HQLA Holding'[HQLA Level] = "L2A" )
HQLA L2B = CALCULATE ( [HQLA After Haircut], 'Fact HQLA Holding'[HQLA Level] = "L2B" )
CB Eligible Collateral = CALCULATE ( [HQLA After Haircut], 'Fact HQLA Holding'[HQLA Level] = "CB_ELIGIBLE" )   // CBC only, not LCR

// Caps: Basel L2B <= 15% and L2 <= 40% of HQLA; EU DR 2015/61 Art. 17: L1B <= 70% (simplified Annex I, as the generator)
HQLA Stock =
VAR _l1a = [HQLA L1]
VAR _l1b = [HQLA L1B]
VAR _l1 = _l1a + _l1b
VAR _l2a = [HQLA L2A]
VAR _l2b = [HQLA L2B]
VAR _adj2b = MAX ( MAX ( _l2b - 15 / 85 * ( _l1 + _l2a ), _l2b - 15 / 60 * _l1 ), 0 )
VAR _adj2 = MAX ( _l2a + _l2b - _adj2b - 2 / 3 * _l1, 0 )
VAR _l2eff = _l2a + _l2b - _adj2b - _adj2
VAR _adj1b = MAX ( _l1b - 7 / 3 * ( _l1a + _l2eff ), 0 )
RETURN _l1 + _l2eff - _adj1b

HQLA Cap Adjustment = [HQLA L1] + [HQLA L1B] + [HQLA L2A] + [HQLA L2B] - [HQLA Stock]
// Share of L1B covered bonds in the capped buffer (EU limit 70%) - same steps as HQLA Stock
HQLA L1B Share % =
VAR _l1a = [HQLA L1]
VAR _l1b = [HQLA L1B]
VAR _l1 = _l1a + _l1b
VAR _l2a = [HQLA L2A]
VAR _l2b = [HQLA L2B]
VAR _adj2b = MAX ( MAX ( _l2b - 15 / 85 * ( _l1 + _l2a ), _l2b - 15 / 60 * _l1 ), 0 )
VAR _adj2 = MAX ( _l2a + _l2b - _adj2b - 2 / 3 * _l1, 0 )
VAR _l2eff = _l2a + _l2b - _adj2b - _adj2
VAR _adj1b = MAX ( _l1b - 7 / 3 * ( _l1a + _l2eff ), 0 )
RETURN DIVIDE ( _l1b - _adj1b, _l1 + _l2eff - _adj1b )

// 30-day outflows: Basel rate x (balance or principal due in 30 days) x scenario multiplier x FX
LCR Outflows =
VAR _d = [Reporting Date]
VAR _s = [Selected Scenario]
VAR _grp =
    CALCULATETABLE (
        SUMMARIZE ( 'Fact Bank Position', 'Dim Product'[Product Code], 'Fact Bank Position'[Currency Code] ),
        REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Dim Product'[LCR Flow] = "outflow" )
VAR _sum =
    SUMX ( _grp,
        VAR _ccy = 'Fact Bank Position'[Currency Code]
        VAR _base = CALCULATE ( SUM ( 'Fact Bank Position'[LCR Base RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d )
        VAR _rate = CALCULATE ( MAX ( 'Dim Product'[LCR Rate] ) )
        VAR _fx = 1 + COALESCE ( CALCULATE ( MAX ( 'Scenario Parameter'[Value] ), REMOVEFILTERS ( 'Dim Scenario' ),
                      'Scenario Parameter'[Scenario Key] = _s, 'Scenario Parameter'[Driver] = "fx_shock",
                      'Scenario Parameter'[Currency Code] = _ccy ), 0 ) + IF ( _ccy = [WI FX Shock Currency], [WI FX Shock Value], 0 )
        RETURN _base * _rate * _fx )
RETURN _sum * [Param Outflow Multiplier]

// Same pattern with 'Dim Product'[LCR Flow] = "inflow" and no multiplier
LCR Inflows = <as LCR Outflows with "inflow" and RETURN _sum>

LCR Inflows Capped = MIN ( [LCR Inflows], 0.75 * [LCR Outflows] )
LCR Net Outflows = [LCR Outflows] - [LCR Inflows Capped]
LCR % = DIVIDE ( [HQLA Stock], [LCR Net Outflows] )
LCR Surplus = [HQLA Stock] - [LCR Net Outflows]
LCR Label = IF ( [Selected Scenario] IN { "ACT", "BASE" }, "LCR (regulatory)", "Stressed LCR (internal)" )
```
To break outflows down by product or category, put `'Dim Product'[Category]` on the axis. The measure respects product filters because `_grp` is built inside the filter context.

## L3. NSFR
```dax
ASF =
VAR _d = [Reporting Date]
RETURN CALCULATE ( SUMX ( 'Fact Bank Position', 'Fact Bank Position'[Balance RC] * 'Fact Bank Position'[NSFR Factor] ),
                   REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _d, 'Dim Product'[NSFR Type] = "ASF" )
RSF = <same with "RSF">
NSFR % = DIVIDE ( [ASF], [RSF] )
NSFR Surplus = [ASF] - [RSF]
```
Balances and funding KPIs (`Balance`, `Total Assets`, `Loan to Deposit %`, CASA, concentration) are in the foundation library.

## L4. Maturity gap
```dax
// Contractual view (all buckets)
Contractual Inflows  = CALCULATE ( SUM ( 'Fact Bank CF Contractual'[Total Cash RC] ), 'Fact Bank CF Contractual'[Total Cash RC] > 0 )
Contractual Outflows = CALCULATE ( SUM ( 'Fact Bank CF Contractual'[Total Cash RC] ), 'Fact Bank CF Contractual'[Total Cash RC] < 0 )
Contractual Net Gap  = SUM ( 'Fact Bank CF Contractual'[Total Cash RC] )

// Management-action toggle (disconnected table 'Mgmt Actions'[View] = {"Pre-management actions", "Post-management actions"})
Include Mgmt Actions = SELECTEDVALUE ( 'Mgmt Actions'[View], "Pre-management actions" ) = "Post-management actions"

// Stressed / behavioural view for the selected scenario, with what-if scaling.
// MGMT_* flows (EBA GL/2018/04 management actions) only count when the toggle is "Post-management actions".
Stressed Net CF =
VAR _mgmt = [Include Mgmt Actions]
RETURN
SUMX ( VALUES ( 'Fact Bank CF Stressed'[Flow Type] ),
    VAR _ft = 'Fact Bank CF Stressed'[Flow Type]
    VAR _amt = CALCULATE ( SUM ( 'Fact Bank CF Stressed'[Amount RC] ) )
    RETURN SWITCH ( TRUE (),
        LEFT ( _ft, 5 ) = "MGMT_", IF ( _mgmt, _amt, 0 ),
        _ft = "RUNOFF", _amt * [WI Runoff Multiplier Value],
        _ft = "DRAWDOWN", _amt * [WI Drawdown Multiplier Value],
        _ft = "ROLLOVER", _amt * ( 1 - [WI Rollover Cut Value] ),
        _amt ) )

// Beyond the projection horizon the stressed ladder uses contractual scheduled flows
Behavioural Net Gap =
VAR _h = CALCULATE ( MAX ( 'Fact Bank CF Stressed'[Days From Asof] ), REMOVEFILTERS () )
RETURN [Stressed Net CF]
     + CALCULATE ( SUM ( 'Fact Bank CF Contractual'[Total Cash RC] ),
                   'Fact Bank CF Contractual'[Flow Type] = "SCHEDULED", 'Fact Bank CF Contractual'[Days From Asof] > _h )

Cumulative Gap (Contractual) =
VAR _b = MAX ( 'Dim Time Bucket'[Sort Order] )
RETURN CALCULATE ( [Contractual Net Gap], REMOVEFILTERS ( 'Dim Time Bucket' ), 'Dim Time Bucket'[Sort Order] <= _b )

Cumulative Gap (Behavioural) = <same pattern over [Behavioural Net Gap]>
Cumulative Gap + CBC = [Cumulative Gap (Behavioural)] + [CBC]
Gap % of Assets = DIVIDE ( [Cumulative Gap (Behavioural)], CALCULATE ( [Total Assets], REMOVEFILTERS ( 'Dim Time Bucket' ) ) )
```

## L5. Survival horizon
```dax
// Projection horizon in days (365 default profile, 182 eba_sls)
Horizon Days = CALCULATE ( MAX ( 'Fact Bank CF Stressed'[Days From Asof] ), REMOVEFILTERS () )

// Counterbalancing capacity = unencumbered HQLA + CB-eligible collateral after stressed haircuts, at the as-of date, no caps
CBC = CALCULATE ( [HQLA After Haircut], REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = [As-of Date] )

// CBC monetised by the date in context: each level counts from its availability day (Dim Product[CBC Availability Day])
CBC Available =
VAR _asof = [As-of Date]
VAR _t = INT ( MAX ( 'Dim Date'[Date] ) - _asof )
RETURN CALCULATE ( [HQLA After Haircut], REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _asof,
                   'Dim Product'[CBC Availability Day] <= _t )

// Daily liquidity position for the selected scenario (use on a line chart with Dim Date[Date] on the axis)
Liquidity Position =
VAR _asof = [As-of Date]
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN
    IF ( _d > _asof && _d <= _asof + [Horizon Days],
         [CBC Available] + CALCULATE ( [Stressed Net CF], REMOVEFILTERS ( 'Dim Date' ),
                                       'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _d ) )

Survival Days =
VAR _asof = [As-of Date]
VAR _days = CALCULATETABLE ( VALUES ( 'Dim Date'[Date] ), REMOVEFILTERS ( 'Dim Date' ),
                             'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _asof + [Horizon Days] )
VAR _breach = MINX ( FILTER ( _days, [Liquidity Position] < 0 ), 'Dim Date'[Date] )
RETURN IF ( ISBLANK ( _breach ), BLANK (), INT ( _breach - _asof ) )

Survival Days (pre-mgmt)  = CALCULATE ( [Survival Days], TREATAS ( { "Pre-management actions" }, 'Mgmt Actions'[View] ) )
Survival Days (post-mgmt) = CALCULATE ( [Survival Days], TREATAS ( { "Post-management actions" }, 'Mgmt Actions'[View] ) )

Survival Label = IF ( ISBLANK ( [Survival Days] ), "> " & [Horizon Days] & " days", FORMAT ( [Survival Days], "0" ) & " days" )

Stressed 30D Net Outflow =
VAR _asof = [As-of Date]
RETURN - MIN ( 0, CALCULATE ( [Stressed Net CF], REMOVEFILTERS ( 'Dim Date' ),
                              'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _asof + 30 ) )
```
`Survival Days` evaluates `Liquidity Position` once per horizon day (up to 365 times). It's fine on a card or a small scenario table. Avoid putting it in large matrices.

## L6. Corporate
```dax
// Forecast with what-if: receipts delayed by DSO shift and scaled by revenue shock
Corp Receipts (What-if) =
VAR _shift = [WI DSO Shift Days Value]
VAR _r = CALCULATE ( SUM ( 'Fact Corp CF Forecast'[Amount RC] ), 'Dim CF Category'[Category Code] = "OP_RECEIPTS",
                     DATEADD ( 'Dim Date'[Date], -_shift, DAY ) )
RETURN _r * ( 1 + [WI Revenue Shock Value] )
Corp Other Forecast Flows = CALCULATE ( SUM ( 'Fact Corp CF Forecast'[Amount RC] ), 'Dim CF Category'[Category Code] <> "OP_RECEIPTS" )
Corp Forecast Net Flow = [Corp Receipts (What-if)] + [Corp Other Forecast Flows]

// Semi-additive: always bind to [Corp Balance Date] (last balance date <= selected date), never LASTDATE,
// which returns the last calendar date (2050s contractual tail) when no date filter is set -> blank cards.
Corp Closing Cash (Generated) = [Corp Cash]        // foundation measure

Corp Closing Cash (What-if) =
VAR _asof = [As-of Date]
VAR _d = MAX ( 'Dim Date'[Date] )
RETURN IF ( _d > _asof, [Corp Cash As-of] + CALCULATE ( [Corp Forecast Net Flow], REMOVEFILTERS ( 'Dim Date' ),
                                                       'Dim Date'[Date] > _asof, 'Dim Date'[Date] <= _d ) )

Corp Undrawn Available =
VAR _wi = [WI RCF Availability Value]       // blank = use scenario
VAR _bd = [Corp Balance Date]
VAR _gen = CALCULATE ( SUM ( 'Fact Corp Cash Balance'[Undrawn Available RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _bd )
VAR _lim = CALCULATE ( SUMX ( FILTER ( 'Dim Facility', 'Dim Facility'[Facility Type] <> "TERM" ),
                              'Dim Facility'[Limit RC] * _wi - 'Dim Facility'[Drawn Asof RC] ) )
RETURN IF ( ISBLANK ( _wi ), _gen, MAX ( _lim, 0 ) )

Corp Min Cash =
VAR _bd = [Corp Balance Date]
RETURN CALCULATE ( SUM ( 'Fact Corp Cash Balance'[Min Cash RC] ), REMOVEFILTERS ( 'Dim Date' ), 'Dim Date'[Date] = _bd )
Corp Headroom = [Corp Closing Cash (What-if)] + [Corp Undrawn Available] - [Corp Min Cash]

Corp Days to Breach = <same pattern as Survival Days over [Corp Headroom] < 0>
```
Working-capital KPIs (DSO, DPO, Open/Overdue AR, Net Debt, Weeks of Cover) are in the foundation library.
For `Corp Undrawn Available` the `WI RCF Availability Value` measure must return BLANK by default (`SELECTEDVALUE('WI RCF Availability'[Value])`, no default).

## L9. Reconciliation (hidden page)
```dax
Ref LCR % = CALCULATE ( MAX ( 'Ref Liquidity Metrics'[LCR Ratio] ), 'Ref Liquidity Metrics'[Currency Scope] = "ALL",
                        'Ref Liquidity Metrics'[Entity Code] = "BANK", 'Ref Liquidity Metrics'[Date] = [Reporting Date] )
Ref Survival Days = CALCULATE ( MAX ( 'Ref Liquidity Metrics'[Survival Days] ), 'Ref Liquidity Metrics'[Currency Scope] = "ALL",
                                'Ref Liquidity Metrics'[Entity Code] = "BANK" )
Ref Survival Days (post-mgmt) = CALCULATE ( MAX ( 'Ref Liquidity Metrics'[Survival Days Post Mgmt] ), 'Ref Liquidity Metrics'[Currency Scope] = "ALL",
                                            'Ref Liquidity Metrics'[Entity Code] = "BANK" )
LCR Diff = [LCR %] - [Ref LCR %]
```
Build a table with Scenario × {LCR %, Ref LCR %, LCR Diff, NSFR %, Survival Days, Ref Survival Days}. Set every what-if to neutral first. The ACT row at a historic month-end checks the LCR trend.
Because `Ref Liquidity Metrics` relates to `Dim Scenario`, the scenario filter applies automatically. Its `Date` should **not** relate to `Dim Date`: filter it with the measure, as shown.
