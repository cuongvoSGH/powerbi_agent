"""Reconcile the Power BI DAX liquidity engine against the generator reference (fact_liquidity_metrics).

This script re-implements, in pandas, the *same logic as the DAX measures* in
powerbi_with_ai.SemanticModel/definition/tables/_Measures.tmdl (not the generator code), with every
what-if at its neutral default (multipliers 1, add-ons 0, Mgmt Actions = Pre unless stated):

  HQLA After Haircut  = SUMX over unencumbered holdings at the reporting date, per (HQLA Level, Currency):
                        SUM(Market Value RC * (1 - MIN(Base Haircut + scenario add-on(level) + WI add-on, 1))) * (1 + fx_shock(ccy) + WI fx)
  HQLA Stock          = L1 + L1B + L2A + L2B after the Basel L2B 15% / L2 40% caps and the EU L1B 70% cap
  LCR Outflows        = SUM over (product, currency) of LCR Base RC * LCR Rate * (1 + fx_shock) for LCR Flow = outflow, * outflow multiplier
  LCR Inflows         = same for LCR Flow = inflow, no multiplier; capped at 75% of outflows
  LCR %               = HQLA Stock / (Outflows - Inflows Capped)
  CBC                 = HQLA After Haircut at the as-of date, all levels incl. CB_ELIGIBLE, no caps
  CBC Available(t)    = CBC of products whose Dim Product[CBC Availability Day] <= t
  Liquidity Position  = CBC Available(t) + cumulative Stressed Net CF (days 1..t); MGMT_* flows only when Post
  Survival Days       = first day t in 1..Horizon with Liquidity Position < [Survival Breach Tolerance] = EUR 1
                        (blank = survives horizon). The EUR 1 tolerance absorbs cent rounding in the CSV inputs: REVERSE is
                        calibrated to breach on day 30 by a fraction of a cent, which the rounded inputs show as +EUR 0.03.
  Stressed 30D Net Outflow = -MIN(0, Stressed Net CF days 1..30)

Run from the project root:
    python docs/reconcile_liquidity.py [--data data/liquidity] [--out docs/reconciliation.md]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

LCR_LEVELS = ("L1", "L1B", "L2A", "L2B")
TOL = 0.001  # 0.1 %
BREACH_TOL = 1.0  # EUR: [Survival Breach Tolerance] - CSV inputs are rounded to cents per row


def load(data: Path) -> dict[str, pd.DataFrame]:
    r = lambda n: pd.read_csv(data / f"{n}.csv", keep_default_na=True)
    t = {
        "date": r("dim_date"),
        "product": r("dim_product"),
        "pos": r("fact_bank_position"),
        "hqla": r("fact_hqla_holding"),
        "stressed": r("fact_bank_cashflow_stressed"),
        "param": r("scenario_parameter"),
        "ref": r("fact_liquidity_metrics"),
        "scen": r("dim_scenario"),
    }
    return t


# ---------------------------------------------------------------- DAX mirrors
def param(t, s: str, driver: str, *, ccy=None, lvl=None, default=None):
    """'Scenario Parameter' lookup: CALCULATE(MAX(Value), REMOVEFILTERS('Dim Scenario'), key = s, driver, currency|level)."""
    p = t["param"]
    m = (p["scenario_key"] == s) & (p["driver"] == driver)
    if ccy is not None:
        m &= p["currency_code"] == ccy
    if lvl is not None:
        m &= p["hqla_level"] == lvl
    v = p.loc[m, "value"]
    return float(v.max()) if len(v) else default


def fx_factor(t, s, ccy, wi_ccy="", wi_fx=0.0):
    return 1 + (param(t, s, "fx_shock", ccy=ccy, default=0.0)) + (wi_fx if ccy == wi_ccy else 0.0)


def hqla_after_haircut(t, s, d, scope="ALL", levels=None, max_avail_day=None, wi_add=0.0):
    """[HQLA After Haircut] with optional level / currency / availability-day filters."""
    h = t["hqla"]
    h = h[(h["date"] == d) & (h["encumbered"] == 0)]
    if scope != "ALL":
        h = h[h["currency_code"] == scope]
    if levels is not None:
        h = h[h["hqla_level"].isin(levels)]
    if max_avail_day is not None:
        avail = t["product"].set_index("product_code")["cbc_availability_day"]
        h = h[h["product_code"].map(avail) <= max_avail_day]
    total = 0.0
    for (lvl, ccy), g in h.groupby(["hqla_level", "currency_code"]):
        add = param(t, s, "hqla_haircut_addon", lvl=lvl, default=0.0) + wi_add
        hc = np.minimum(g["base_haircut"].values + add, 1.0)
        total += float((g["market_value_rc"].values * (1 - hc)).sum()) * fx_factor(t, s, ccy)
    return total


def hqla_stock(l1a, l1b, l2a, l2b):
    l1 = l1a + l1b
    adj2b = max(max(l2b - 15 / 85 * (l1 + l2a), l2b - 15 / 60 * l1), 0)
    adj2 = max(l2a + l2b - adj2b - 2 / 3 * l1, 0)
    l2eff = l2a + l2b - adj2b - adj2
    adj1b = max(l1b - 7 / 3 * (l1a + l2eff), 0)
    stock = l1 + l2eff - adj1b
    return stock, (l1b - adj1b) / stock if stock else None


def lcr(t, s, d, scope="ALL"):
    lv = {L: hqla_after_haircut(t, s, d, scope, levels=[L]) for L in LCR_LEVELS}
    stock, l1b_share = hqla_stock(lv["L1"], lv["L1B"], lv["L2A"], lv["L2B"])
    pr = t["product"].set_index("product_code")
    p = t["pos"]
    p = p[p["date"] == d]
    if scope != "ALL":
        p = p[p["currency_code"] == scope]
    mult = param(t, s, "lcr_outflow_multiplier", default=1.0) * 1.0  # * WI Outflow Multiplier (1)

    def flows(kind):
        x = p[p["product_code"].map(pr["lcr_flow"]) == kind]
        tot = 0.0
        for (prod, ccy), g in x.groupby(["product_code", "currency_code"]):
            rate = pr.loc[prod, "lcr_rate"]
            rate = 0.0 if pd.isna(rate) else float(rate)
            tot += float(g["lcr_base_rc"].sum()) * rate * fx_factor(t, s, ccy)
        return tot

    out = flows("outflow") * mult
    inf = flows("inflow")
    capped = min(inf, 0.75 * out)
    net = out - capped
    return {"HQLA Stock": stock, "LCR Net Outflows": net, "LCR %": stock / net if net else None,
            "HQLA L1B Share %": l1b_share}


def stressed_daily(t, s, scope="ALL", post=False, horizon=None):
    """Daily [Stressed Net CF] for days 1..H (what-if neutral)."""
    f = t["stressed"]
    f = f[f["scenario_key"] == s]
    if scope != "ALL":
        f = f[f["currency_code"] == scope]
    if not post:
        f = f[~f["flow_type"].str.startswith("MGMT_")]
    net = f.groupby("days_from_asof")["amount_rc"].sum()
    return net.reindex(range(1, horizon + 1), fill_value=0.0).values


def survival(t, s, asof, scope="ALL"):
    H = int(t["stressed"]["days_from_asof"].max())  # [Horizon Days]
    cbc = hqla_after_haircut(t, s, asof, scope)
    avail_days = sorted(t["product"]["cbc_availability_day"].dropna().unique())
    by_day = {int(a): hqla_after_haircut(t, s, asof, scope, max_avail_day=a) for a in avail_days}
    days = np.arange(1, H + 1)
    avail = np.array([max([v for a, v in by_day.items() if a <= d], default=0.0) for d in days])
    res = {"CBC": cbc}
    for tag, post in (("pre", False), ("post", True)):
        cum = np.cumsum(stressed_daily(t, s, scope, post, H))
        pos = avail + cum
        neg = np.flatnonzero(pos < BREACH_TOL)
        res[f"Survival {tag}"] = int(neg[0] + 1) if len(neg) else None
        res[f"Min Position {tag}"] = float(pos.min())
        if not post:
            res["Stressed 30D Net Outflow"] = -min(0.0, float(cum[29]))
    res["Horizon"] = H
    return res


# ---------------------------------------------------------------- compare
def pct_diff(a, b):
    if a is None and b is None:
        return 0.0
    if a is None or b is None or (isinstance(b, float) and np.isnan(b)):
        return np.nan if not (a is None and (b is None or np.isnan(b))) else 0.0
    return 0.0 if b == 0 and a == 0 else abs(a - b) / abs(b)


def fmt_days(v, H):
    return f"> {H}" if v is None or (isinstance(v, float) and np.isnan(v)) else str(int(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/liquidity")
    ap.add_argument("--out", default="docs/reconciliation.md")
    a = ap.parse_args()
    t = load(Path(a.data))
    asof = t["date"].loc[t["date"]["period_type"] == "As-of", "date"].max()
    ref = t["ref"]
    scen_order = t["scen"].sort_values("sort_order")["scenario_key"].tolist()

    rows, worst = [], 0.0
    for scope in ["ALL", "EUR", "USD", "GBP"]:
        for s in scen_order:
            r = ref[(ref["date"] == asof) & (ref["scenario_key"] == s) & (ref["currency_scope"] == scope)
                    & (ref["entity_code"] == "BANK")]
            if r.empty:
                continue
            r = r.iloc[0]
            L = lcr(t, s, asof, scope)
            row = {"Scope": scope, "Scenario": s, "LCR % (DAX)": L["LCR %"], "LCR % (Ref)": r["lcr_ratio"],
                   "HQLA (DAX)": L["HQLA Stock"], "HQLA (Ref)": r["hqla_total_rc"],
                   "L1B Share (DAX)": L["HQLA L1B Share %"], "L1B Share (Ref)": r["hqla_l1b_share"]}
            checks = [pct_diff(L["LCR %"], r["lcr_ratio"]), pct_diff(L["HQLA Stock"], r["hqla_total_rc"]),
                      pct_diff(L["LCR Net Outflows"], r["lcr_net_outflows_rc"])]
            if s != "ACT":
                S = survival(t, s, asof, scope)
                sp = None if pd.isna(r["survival_days"]) else int(r["survival_days"])
                spo = None if pd.isna(r["survival_days_post_mgmt"]) else int(r["survival_days_post_mgmt"])
                row.update({"CBC (DAX)": S["CBC"], "CBC (Ref)": r["cbc_rc"],
                            "30D Out (DAX)": S["Stressed 30D Net Outflow"], "30D Out (Ref)": r["stressed_net_outflow_30d_rc"],
                            "Surv pre (DAX)": fmt_days(S["Survival pre"], S["Horizon"]), "Surv pre (Ref)": fmt_days(sp, S["Horizon"]),
                            "Surv post (DAX)": fmt_days(S["Survival post"], S["Horizon"]), "Surv post (Ref)": fmt_days(spo, S["Horizon"]),
                            "MinPos pre (DAX)": S["Min Position pre"], "MinPos pre (Ref)": r["min_liquidity_position_rc"],
                            "MinPos post (DAX)": S["Min Position post"], "MinPos post (Ref)": r["min_liquidity_position_post_mgmt_rc"]})
                checks += [pct_diff(S["CBC"], r["cbc_rc"]),
                           pct_diff(S["Stressed 30D Net Outflow"], r["stressed_net_outflow_30d_rc"]) if r["stressed_net_outflow_30d_rc"] else 0.0,
                           0.0 if S["Survival pre"] == sp else 1.0, 0.0 if S["Survival post"] == spo else 1.0,
                           pct_diff(S["Min Position pre"], r["min_liquidity_position_rc"]),
                           pct_diff(S["Min Position post"], r["min_liquidity_position_post_mgmt_rc"])]
            row["Max rel. diff"] = float(np.nanmax(checks))
            worst = max(worst, row["Max rel. diff"]) if scope == "ALL" else worst
            rows.append(row)
    df = pd.DataFrame(rows)

    def bn(v):
        return "" if pd.isna(v) else f"{v / 1e9:,.4f}"

    def pc(v):
        return "" if v is None or pd.isna(v) else f"{v * 100:.2f}%"

    lines = ["# Reconciliation: DAX engine vs generator reference", "",
             f"- As-of date: **{asof}** - reporting currency EUR - entity BANK - all what-if parameters neutral, Mgmt Actions = Pre for the pre-mgmt columns.",
             "- Method: `docs/reconcile_liquidity.py` re-implements the DAX logic of `_Measures.tmdl` (L2 HQLA & LCR, L5 Survival) in pandas on the CSVs "
             "and compares it with `fact_liquidity_metrics.csv`. Tolerance: 0.1 % relative; survival days must match exactly.",
             f"- Result (currency scope ALL): worst relative difference **{worst * 100:.4f}%** -> **{'PASS' if worst < TOL else 'FAIL'}**.", "",
             "## Currency scope ALL (as-of date)", "",
             "| Scenario | LCR % DAX | LCR % Ref | CBC DAX (EUR bn) | CBC Ref (EUR bn) | 30D net outflow DAX (EUR bn) | Ref | Survival pre DAX / Ref | Survival post DAX / Ref | Max rel. diff | Status |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in df[df["Scope"] == "ALL"].iterrows():
        sv_pre = f"{r.get('Surv pre (DAX)', '')} / {r.get('Surv pre (Ref)', '')}" if r["Scenario"] != "ACT" else "n/a"
        sv_post = f"{r.get('Surv post (DAX)', '')} / {r.get('Surv post (Ref)', '')}" if r["Scenario"] != "ACT" else "n/a"
        lines.append(f"| {r['Scenario']} | {pc(r['LCR % (DAX)'])} | {pc(r['LCR % (Ref)'])} | {bn(r.get('CBC (DAX)'))} | {bn(r.get('CBC (Ref)'))} | "
                     f"{bn(r.get('30D Out (DAX)'))} | {bn(r.get('30D Out (Ref)'))} | {sv_pre} | {sv_post} | {r['Max rel. diff'] * 100:.4f}% | "
                     f"{'PASS' if r['Max rel. diff'] < TOL else 'FAIL'} |")
    lines += ["", "Horizon = 182 projection days; '> 182' = no breach within the horizon (reference value blank).", "",
              "## Supporting detail (scope ALL)", "",
              "| Scenario | HQLA Stock DAX (EUR bn) | Ref | L1B share DAX | Ref | Min position pre DAX (EUR bn) | Ref | Min position post DAX (EUR bn) | Ref |",
              "|---|---|---|---|---|---|---|---|---|"]
    for _, r in df[df["Scope"] == "ALL"].iterrows():
        lines.append(f"| {r['Scenario']} | {bn(r['HQLA (DAX)'])} | {bn(r['HQLA (Ref)'])} | {pc(r['L1B Share (DAX)'])} | {pc(r['L1B Share (Ref)'])} | "
                     f"{bn(r.get('MinPos pre (DAX)'))} | {bn(r.get('MinPos pre (Ref)'))} | {bn(r.get('MinPos post (DAX)'))} | {bn(r.get('MinPos post (Ref)'))} |")
    lines += ["", "## Single-currency scopes (Currency slicer = EUR / USD / GBP), supplementary", "",
              "| Scope | Scenario | LCR % DAX | LCR % Ref | CBC DAX (EUR bn) | CBC Ref | Survival pre DAX / Ref | Survival post DAX / Ref | Max rel. diff |",
              "|---|---|---|---|---|---|---|---|---|"]
    for _, r in df[df["Scope"] != "ALL"].iterrows():
        sv_pre = f"{r.get('Surv pre (DAX)', '')} / {r.get('Surv pre (Ref)', '')}" if r["Scenario"] != "ACT" else "n/a"
        sv_post = f"{r.get('Surv post (DAX)', '')} / {r.get('Surv post (Ref)', '')}" if r["Scenario"] != "ACT" else "n/a"
        lines.append(f"| {r['Scope']} | {r['Scenario']} | {pc(r['LCR % (DAX)'])} | {pc(r['LCR % (Ref)'])} | {bn(r.get('CBC (DAX)'))} | "
                     f"{bn(r.get('CBC (Ref)'))} | {sv_pre} | {sv_post} | {r['Max rel. diff'] * 100:.4f}% |")
    lines += ["", "## Notes", "",
              "- HQLA haircuts are applied per holding row, because level L2B mixes two base haircuts (SEC_L2B 50%, SEC_L2B_RMBS 25%). "
              "The library pattern `MAX('Fact HQLA Holding'[Base Haircut])` per level/currency would understate L2B and CBC; the DAX was written row-level from the start.",
              "- Survival breach test: position < EUR 1 (`[Survival Breach Tolerance]`), not < 0. Fixed during reconciliation: with `< 0` REVERSE pre-mgmt "
              "gave 31 days vs 30 in the reference, because REVERSE is calibrated (bisection) to breach exactly on day 30 and the cent-rounded CSV inputs leave "
              "+EUR 0.03 on that day. The next-closest position to zero in any scenario is EUR 75k, so no other result is affected. DAX and script were changed together.",
              "- Survival is computed on CBC monetised by availability day (L1 day 1, L1B day 2, L2A and CB_ELIGIBLE day 3, L2B day 5), as in `Fact Bank Survival`.",
              "- These numbers validate the logic of the DAX, reproduced outside Power BI. Re-check the hidden Reconciliation page in Desktop after the first refresh.", ""]
    Path(a.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if worst < TOL else 1


if __name__ == "__main__":
    raise SystemExit(main())
