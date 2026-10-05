# Power BI finance & banking report project

This repo holds a Power BI Project (PBIP) plus a Claude Code agent and skills that help design the semantic model and build the report.

## Project format
- **Power BI Project (.pbip)**, with the semantic model in **TMDL** and the report in **PBIR**.
- In Power BI Desktop → Options → Preview features, enable:
  - "Power BI Project (.pbip) save option"
  - "Store semantic model using TMDL format"
  - "Store reports using enhanced metadata format (PBIR)"
- **Close Power BI Desktop before Claude edits files**, then reopen the `.pbip`.

## Agents and skills
- `.claude/agents/powerbi-developer.md`: data model, DAX, Power Query and report pages.
- `.claude/agents/liquidity-data-simulator.md`: generates **synthetic** liquidity cash-flow data into `data/liquidity/`. Profiles: `default` (Basel, bank + corporate, USD) and `eba_sls` (EBA-aligned severe liquidity stress, EUR, bank only). Amount columns end in `_rc` (reporting currency).
- Skills in `.claude/skills/`:
  - `pbip-format`: TMDL/PBIR syntax and `scripts/validate_pbip.py`
  - `pbi-data-modeling`: star schema and finance/banking patterns, date table, model spec template
  - `pbi-power-query`: M patterns for CSV/Excel/SQL and `scripts/profile_data.py`
  - `pbi-dax-measures`: finance and banking measure library, calculation groups
  - `pbi-report-visuals`: page layouts, visual templates, `assets/finance-theme.json`
  - `liquidity-risk-methodology`: Basel LCR/NSFR, maturity ladder, survival horizon, stress scenarios, corporate liquidity
  - `liquidity-simulation`: the generator (`config/default.yaml`, `scripts/generate.py`, `scripts/validate_dataset.py`)
  - `liquidity-powerbi`: model, DAX and pages for the liquidity dataset

## Workflow
Profile the data → propose a spec (`docs/model-spec.md`) → **user approves** → write TMDL/PBIR → run the validator.

## Conventions
- **Tables:** `Fact <Subject>`, `Dim <Entity>`. Measures live in `_Measures`, in numbered display folders.
- **Columns** use business names with spaces. Keys end in `Key` and are hidden.
- **Measures:** every one has a description and a format string. Use `DIVIDE` and `VAR`/`RETURN`. Balances are semi-additive.
- **Variance colours:** favourable `#1A7F5A`, unfavourable `#C23B22`, neutral `#6B7280`. Expense increases count as unfavourable.
- **Data files** go in `data/` (CSV/Excel). SQL connection details go in the `SqlServer` / `SqlDatabase` parameters.

## Useful commands
```
python .claude/skills/pbi-power-query/scripts/profile_data.py data/ --out docs/data-profile.md
python .claude/skills/pbip-format/scripts/validate_pbip.py .
# data/liquidity currently = EBA severe liquidity stress profile (eba_sls, EUR, bank only)
python .claude/skills/liquidity-simulation/scripts/generate.py --config data/liquidity/config.yaml --out data/liquidity --seed 42 --entity bank
python .claude/skills/liquidity-simulation/scripts/validate_dataset.py data/liquidity
```
