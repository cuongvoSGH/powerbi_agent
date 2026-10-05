"""Table registry (single source for README, validation keys and FK checks) and README writer."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

# name: dict(desc, grain, pk, fk={col: "table.col"}, cols={col: description})
TABLES: dict[str, dict] = {
    # ---------------- shared
    "dim_date": dict(desc="Calendar from the first history month-end to the last contractual cash flow.", grain="one row per day",
                     pk=["date"], cols={"date": "Calendar date", "period_type": "History / As-of / Projection / Contractual tail",
                                        "days_from_asof": "Days after the as-of date (negative = history)", "is_business_day": "Mon-Fri flag"}),
    "dim_currency": dict(desc="Currencies.", grain="one row per currency", pk=["currency_code"],
                         cols={"rate_to_rc_asof": "USD value of 1 unit at as-of (spot used for all projections)"}),
    "fact_fx_rate": dict(desc="Daily FX history (seeded GBM anchored to the as-of spot).", grain="date x currency",
                         pk=["date", "currency_code"], fk={"date": "dim_date.date", "currency_code": "dim_currency.currency_code"},
                         cols={"rate_to_rc": "USD value of 1 unit of currency"}),
    "dim_entity": dict(desc="Reporting entities: the bank, the corporate group and its subsidiaries.", grain="one row per entity",
                       pk=["entity_code"], cols={"entity_type": "Bank / Corporate", "parent_entity_code": "Group parent"}),
    "dim_scenario": dict(desc="Scenarios. ACT = actual history; others are projections from the as-of date.", grain="one row per scenario",
                         pk=["scenario_key"], cols={"scenario_type": "actual / baseline / stress / reverse"}),
    "scenario_parameter": dict(desc="Every scenario driver value (long format) - use for what-if baselines in Power BI.",
                               grain="scenario x driver x (product | currency | HQLA level)",
                               pk=["scenario_key", "driver", "product_code", "currency_code", "hqla_level"],
                               fk={"scenario_key": "dim_scenario.scenario_key"},
                               cols={"driver": "Driver name (see config scenario_drivers)", "value": "Driver value (fractions as decimals)"}),
    "dim_time_bucket": dict(desc="Maturity ladder buckets measured from the as-of date.", grain="one row per bucket", pk=["bucket_key"],
                            cols={"in_lcr_30d": "1 if the bucket lies inside the 30-day LCR window", "in_6m": "1 if within six months",
                                  "in_1y": "1 if within one year", "bucket_key": "Configurable ladder (config time_buckets); EBA profile = ALMM C 66.01"}),
    # ---------------- bank
    "dim_product": dict(desc="Bank products with Basel LCR / NSFR parameters.", grain="one row per product", pk=["product_code"],
                        fk={"segment_code": "dim_counterparty_segment.segment_code"},
                        cols={"side_sign": "+1 asset, -1 liability / equity / off-balance", "lcr_basis": "hqla | balance | due_30d | none",
                              "lcr_flow": "outflow | inflow | hqla", "lcr_rate": "Basel run-off / inflow rate",
                              "nsfr_type": "ASF (funding) or RSF (requirement)", "nsfr_factor_*": "Factor by residual maturity band"}),
    "dim_counterparty_segment": dict(desc="Bank counterparty segments.", grain="one row per segment", pk=["segment_code"], cols={}),
    "dim_contract": dict(desc="Bank contracts (loans, deposits, securities, facilities, accounts).", grain="one row per contract",
                         pk=["contract_id"], fk={"product_code": "dim_product.product_code", "currency_code": "dim_currency.currency_code",
                                                 "segment_code": "dim_counterparty_segment.segment_code"},
                         cols={"notional_local": "Original principal (dated) or as-of balance (non-maturity)",
                               "is_live_at_asof": "1 if outstanding at the as-of date", "encumbered": "1 if pledged (excluded from HQLA)"}),
    "fact_bank_position": dict(desc="Month-end balances per contract with LCR / NSFR inputs.", grain="contract x month-end",
                               pk=["date", "contract_id"], fk={"date": "dim_date.date", "contract_id": "dim_contract.contract_id",
                                                               "product_code": "dim_product.product_code", "currency_code": "dim_currency.currency_code",
                                                               "bucket_key": "dim_time_bucket.bucket_key"},
                               cols={"principal_due_30d_local": "Principal falling due in the next 30 days",
                                     "lcr_base_rc": "Amount the product's LCR rate applies to (balance or due-30d)",
                                     "nsfr_factor": "ASF/RSF factor for this residual maturity (encumbered HQLA overridden)",
                                     "bucket_key": "Residual-maturity bucket (B01 for on-demand, B10 non-maturity)"}),
    "fact_hqla_holding": dict(desc="HQLA stock (reserves and Level 1/2A/2B securities) at market value.", grain="security x month-end",
                              pk=["date", "contract_id"], fk={"date": "dim_date.date", "contract_id": "dim_contract.contract_id",
                                                              "product_code": "dim_product.product_code", "currency_code": "dim_currency.currency_code"},
                              cols={"hqla_level": "L1 (Level 1 excl. covered bonds), L1B (EHQ covered bonds), L2A, L2B, or CB_ELIGIBLE (central-bank-eligible non-HQLA: CBC only, not LCR)",
                                    "price": "Clean price (1.0 = par)", "base_haircut": "Regulatory haircut of the holding (HQLA level / product override / central bank haircut)"}),
    "fact_bank_cashflow_history": dict(desc="Realised bank cash flows.", grain="date x product x currency x flow type",
                                       pk=["date", "product_code", "currency_code", "flow_type"],
                                       fk={"date": "dim_date.date", "product_code": "dim_product.product_code", "currency_code": "dim_currency.currency_code"},
                                       cols={"flow_type": "ORIGINATION / PRINCIPAL / INTEREST / NMD_NET_CHANGE / NMD_INTEREST",
                                             "amount_local": "+ received by the bank, - paid"}),
    "fact_bank_cashflow_contractual": dict(desc="Contractual future cash flows at the as-of date (to final maturity). NMD balances shown as repayable on demand.",
                                           grain="contract x payment date x flow type", pk=["date", "contract_id", "flow_type"],
                                           fk={"date": "dim_date.date", "contract_id": "dim_contract.contract_id", "product_code": "dim_product.product_code",
                                               "currency_code": "dim_currency.currency_code", "bucket_key": "dim_time_bucket.bucket_key"},
                                           cols={"flow_type": "SCHEDULED / NMD_ON_DEMAND", "*_rc": "Converted at as-of spot"}),
    "fact_bank_cashflow_stressed": dict(desc="Daily projected bank cash flows per scenario (behavioural). HQLA principal excluded - it is in the counterbalancing capacity.",
                                        grain="scenario x date x product x currency x flow type",
                                        pk=["scenario_key", "date", "product_code", "currency_code", "flow_type"],
                                        fk={"scenario_key": "dim_scenario.scenario_key", "date": "dim_date.date", "product_code": "dim_product.product_code",
                                            "currency_code": "dim_currency.currency_code", "bucket_key": "dim_time_bucket.bucket_key"},
                                        cols={"flow_type": "CONTRACTUAL_PRINCIPAL / CONTRACTUAL_INTEREST / ROLLOVER / RUNOFF / DRAWDOWN / COLLATERAL_CALL / MGMT_* (management actions)",
                                              "amount_rc": "At as-of spot x (1 + scenario FX shock)"}),
    "fact_bank_survival": dict(desc="Daily liquidity position = counterbalancing capacity + cumulative net stressed flow.",
                               grain="scenario x currency scope x date", pk=["scenario_key", "currency_scope", "date"],
                               fk={"scenario_key": "dim_scenario.scenario_key", "date": "dim_date.date"},
                               cols={"currency_scope": "ALL or a currency code (not a key)", "cbc_available_rc": "CBC monetised by that day (cbc_availability_day)",
                                     "liquidity_position_rc": "Before management actions; breach when < 0",
                                     "liquidity_position_post_mgmt_rc": "After management actions (MGMT_* flows)"}),
    # ---------------- corporate
    "dim_cf_category": dict(desc="Corporate cash-flow categories (IAS 7).", grain="one row per category", pk=["category_code"],
                            cols={"activity": "Operating / Investing / Financing (interest paid classified as Financing)"}),
    "dim_counterparty": dict(desc="Corporate customers and suppliers.", grain="one row per counterparty", pk=["counterparty_id"],
                             fk={"entity_code": "dim_entity.entity_code", "currency_code": "dim_currency.currency_code"},
                             cols={"avg_delay_days": "Average days paid after due date (customers)", "is_key_account": "Top customers by volume"}),
    "dim_bank_account": dict(desc="Corporate bank accounts.", grain="one row per account", pk=["account_id"],
                             fk={"entity_code": "dim_entity.entity_code", "currency_code": "dim_currency.currency_code"}, cols={}),
    "dim_facility": dict(desc="Corporate borrowing facilities (revolvers, overdraft, term loan).", grain="one row per facility", pk=["facility_id"],
                         fk={"entity_code": "dim_entity.entity_code", "currency_code": "dim_currency.currency_code"},
                         cols={"drawn_asof_local": "Drawn amount at as-of", "covenant": "Key covenant (text)"}),
    "fact_corp_invoice": dict(desc="AR and AP invoices; OPEN items drive the forecast.", grain="one row per invoice", pk=["invoice_id"],
                              fk={"entity_code": "dim_entity.entity_code", "counterparty_id": "dim_counterparty.counterparty_id",
                                  "currency_code": "dim_currency.currency_code"},
                              cols={"expected_pay_date": "Baseline expected payment date (OPEN only)"}),
    "fact_corp_cashflow_actual": dict(desc="Realised corporate cash flows.", grain="date x entity x category x currency",
                                      pk=["date", "entity_code", "category_code", "currency_code"],
                                      fk={"date": "dim_date.date", "entity_code": "dim_entity.entity_code", "account_id": "dim_bank_account.account_id",
                                          "category_code": "dim_cf_category.category_code", "currency_code": "dim_currency.currency_code"},
                                      cols={"amount_local": "+ received, - paid"}),
    "fact_corp_cashflow_forecast": dict(desc="Daily corporate cash-flow forecast per scenario (expected values).",
                                        grain="scenario x date x entity x category x currency",
                                        pk=["scenario_key", "date", "entity_code", "category_code", "currency_code"],
                                        fk={"scenario_key": "dim_scenario.scenario_key", "date": "dim_date.date", "entity_code": "dim_entity.entity_code",
                                            "account_id": "dim_bank_account.account_id", "category_code": "dim_cf_category.category_code",
                                            "currency_code": "dim_currency.currency_code"}, cols={}),
    "fact_corp_cash_balance": dict(desc="Daily cash balance per account: actual (ACT) and forecast per scenario, with facility headroom.",
                                   grain="scenario x date x account", pk=["scenario_key", "date", "account_id"],
                                   fk={"scenario_key": "dim_scenario.scenario_key", "date": "dim_date.date", "entity_code": "dim_entity.entity_code",
                                       "account_id": "dim_bank_account.account_id", "currency_code": "dim_currency.currency_code"},
                                   cols={"headroom_local": "closing + undrawn available facilities - minimum cash (breach when < 0)"}),
    # ---------------- reference metrics
    "fact_liquidity_metrics": dict(desc="Reference metrics computed by the generator - reconcile Power BI measures against these.",
                                   grain="date x scenario x entity x currency scope", pk=["date", "scenario_key", "entity_code", "currency_scope"],
                                   fk={"date": "dim_date.date", "scenario_key": "dim_scenario.scenario_key", "entity_code": "dim_entity.entity_code"},
                                   cols={"currency_scope": "ALL or currency code (not a key)", "lcr_ratio": "HQLA / net 30-day outflows",
                                         "nsfr_ratio": "ASF / RSF", "survival_days": "First projection day with negative position before management actions (blank = survives horizon)",
                                         "survival_days_post_mgmt": "Same after management actions",
                                         "hqla_l1b_share": "Share of L1B covered bonds in HQLA after caps (EU cap 70%)"}),
    "fact_liquidity_gap": dict(desc="Reference maturity ladder (reporting currency).", grain="view x currency scope x bucket",
                               pk=["view", "currency_scope", "bucket_key"], fk={"bucket_key": "dim_time_bucket.bucket_key"},
                               cols={"view": "CONTRACTUAL or a scenario key (behavioural within horizon, contractual beyond)"}),
}


def write_readme(path, cfg, counts: dict, drivers_tbl: pd.DataFrame, metrics: pd.DataFrame, notes: list[str], seed: int, elapsed: float):
    m = cfg["meta"]
    lines = [
        "# Liquidity simulation dataset",
        "",
        "> **SYNTHETIC DATA.** Generated for liquidity stress-testing demos. It does not describe any real institution.",
        "",
        f"- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} in {elapsed:.1f}s",
        f"- As-of date: **{m['as_of_date']}** · history {m['history_months']} months · daily projection {m['horizon_days']} days",
        f"- Size preset: `{m['size']}` · seed `{seed}` · currencies {', '.join(cfg['currencies'])} (reporting currency **{m.get('reporting_currency', 'USD')}**)",
        "- Config used: `config_used.yaml` (re-run with the same config and seed to reproduce byte-identical files)",
        "",
        "## Headline metrics (as-of date)",
        "",
    ]
    rc = m.get("reporting_currency", "USD")
    bank = metrics[(metrics["entity_code"] == cfg["bank"]["code"]) & (metrics["currency_scope"] == "ALL") & (metrics["scenario_key"] != "ACT")]
    if len(bank):
        lines += ["**Bank**", "", f"| Scenario | LCR | NSFR | CBC ({rc} bn) | 30d stressed net outflow ({rc} bn) | Survival days (pre mgmt actions) | Survival days (post mgmt actions) |", "|---|---|---|---|---|---|---|"]
        for _, r in bank.iterrows():
            lines.append(f"| {r['scenario_key']} | {_pct(r.get('lcr_ratio'))} | {_pct(r.get('nsfr_ratio'))} | {r['cbc_rc'] / 1e9:,.2f} | "
                         f"{r['stressed_net_outflow_30d_rc'] / 1e9:,.2f} | {_days(r['survival_days'])} | {_days(r.get('survival_days_post_mgmt'))} |")
        lines.append("")
    corp = metrics[(metrics["entity_code"] == cfg.get("corporate", {}).get("group_code")) & (metrics["scenario_key"] != "ACT")]
    if len(corp):
        lines += ["**Corporate group**", "", f"| Scenario | Cash at as-of ({rc} M) | Undrawn facilities ({rc} M) | Min headroom ({rc} M) | Days to breach |",
                  "|---|---|---|---|---|"]
        for _, r in corp.iterrows():
            lines.append(f"| {r['scenario_key']} | {r['cash_rc'] / 1e6:,.1f} | {r['undrawn_facilities_rc'] / 1e6:,.1f} | "
                         f"{r['min_headroom_rc'] / 1e6:,.1f} | {_days(r['survival_days'])} |")
        lines.append("")
    if notes:
        lines += ["**Notes:** " + " ".join(notes), ""]

    lines += ["## Scenarios", ""]
    for k, s in cfg["scenarios"].items():
        lines.append(f"- **{k} - {s['name']}**: {s['description']}")
    piv = drivers_tbl.copy()
    piv["driver_full"] = piv["driver"] + piv[["product_code", "currency_code", "hqla_level"]].agg(
        lambda r: "" if not "".join(r) else " [" + "".join(r) + "]", axis=1)
    piv = piv.pivot_table(index="driver_full", columns="scenario_key", values="value", aggfunc="first", sort=False)
    lines += ["", "### Scenario drivers", "", "| Driver | " + " | ".join(piv.columns) + " |", "|---" * (len(piv.columns) + 1) + "|"]
    for drv, row in piv.iterrows():
        lines.append(f"| {drv} | " + " | ".join("" if pd.isna(v) else f"{v:g}" for v in row.values) + " |")

    lines += ["", "## Tables", "", "| Table | Rows | Grain | Description |", "|---|---|---|---|"]
    for t, d in TABLES.items():
        if t in counts:
            lines.append(f"| `{t}` | {counts[t]:,} | {d['grain']} | {d['desc']} |")
    lines += ["", "### Keys, relationships and column notes", ""]
    for t, d in TABLES.items():
        if t not in counts:
            continue
        lines.append(f"**`{t}`**: key ({', '.join(d['pk'])})")
        for col, ref in d.get("fk", {}).items():
            lines.append(f"- `{col}` -> `{ref}`")
        for col, txt in d.get("cols", {}).items():
            lines.append(f"- `{col}`: {txt}")
        lines.append("")

    lines += ["## Methodology & simplifications", "",
              "- Sign convention: **+ cash received, - cash paid** (bank and corporate). Balances are positive.",
              "- Bank contracts: amortising (annuity), bullet in months (periodic coupon), bullet in days, non-maturity deposits (random-walk balance), static items, undrawn facilities. Each product/currency is scaled so the as-of balance sheet matches `bank.total_assets_rc` and the configured shares; assets = liabilities + equity at the as-of date only.",
              "- LCR: Basel III (BCBS 238) rates from config; HQLA = unencumbered market value after haircuts with the 15% (L2B) and 40% (L2) caps; inflows capped at 75% of outflows; only principal due within 30 days counts for term items (interest ignored). Stressed LCR applies scenario haircut add-ons, FX shock and an outflow multiplier.",
              "- NSFR: Basel III (BCBS 295) ASF/RSF factors by residual maturity of the whole contract (amortising loans are not split by instalment); encumbered HQLA uses `nsfr_encumbered_rsf`.",
              "- Survival horizon: unencumbered HQLA after scenario haircuts is the counterbalancing capacity (available day 1); stressed flows exclude HQLA principal to avoid double counting.",
              "- Behavioural flows: maturing principal x rollover share is renewed; non-maturity deposits run off on a front-loaded curve (tau 7 days to day 30, linear to day 365); undrawn facilities are drawn on the same curve shape; a one-off collateral call hits on the configured day.",
              "- Projections use the as-of spot rate x (1 + scenario FX shock); history uses daily rates.",
              "- Corporate: invoices are simulated from revenue (seasonality, growth) with customer payment delays; revolvers/overdraft balance cash to the minimum in history; forecasts are expected values with no automatic revolver draw - headroom = cash + undrawn available - minimum cash.",
              ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _pct(v):
    return "" if v is None or pd.isna(v) else f"{v:.1%}"


def _days(v):
    return "> horizon" if v is None or pd.isna(v) else f"{int(v)}"
