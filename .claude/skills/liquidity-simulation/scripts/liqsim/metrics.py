"""Reference liquidity metrics (for reconciling Power BI DAX): LCR, NSFR, maturity gap, survival horizon."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .common import buckets, spot

LCR_LEVELS = ("L1", "L1B", "L2A", "L2B")


def _fx_factor(ccy: pd.Series, drv: dict | None) -> np.ndarray:
    if not drv:
        return np.ones(len(ccy))
    return ccy.map(lambda c: 1 + drv["fx_shock"].get(c, 0.0)).values


def lcr(pos_d: pd.DataFrame, hq_d: pd.DataFrame, prod: pd.DataFrame, cfg, drv: dict | None) -> dict:
    """Basel III LCR on one date's positions (reporting currency). drv adds scenario haircuts, outflow multiplier and FX shock."""
    b = cfg["bank"]
    add = drv["hqla_haircut_addon"] if drv else {}
    mult = drv["lcr_outflow_multiplier"] if drv else 1.0

    # HQLA only (CB-eligible non-HQLA collateral counts in the CBC, not in the LCR); haircut per holding row
    h = hq_d[(hq_d["encumbered"] == 0) & hq_d["hqla_level"].isin(LCR_LEVELS)]
    haircut = np.minimum(h["base_haircut"].values + h["hqla_level"].map(lambda lv: add.get(lv, 0.0)).values, 1.0)
    val = h["market_value_rc"].values * (1 - haircut) * _fx_factor(h["currency_code"], drv)
    lv = h["hqla_level"].values
    l1a, l1b = float(val[lv == "L1"].sum()), float(val[lv == "L1B"].sum())
    l2a, l2b = float(val[lv == "L2A"].sum()), float(val[lv == "L2B"].sum())
    hq = hqla_caps(l1a, l1b, l2a, l2b, b["hqla"])

    p = prod.set_index("product_code")
    flow = pos_d["product_code"].map(p["lcr_flow"]).values
    rate = pos_d["product_code"].map(p["lcr_rate"]).fillna(0.0).values
    w = pos_d["lcr_base_rc"].values * rate * _fx_factor(pos_d["currency_code"], drv)
    out_f = float(w[flow == "outflow"].sum()) * mult
    in_f = float(w[flow == "inflow"].sum())
    in_c = min(in_f, b["lcr_inflow_cap"] * out_f)
    net = out_f - in_c
    return {"hqla_l1_rc": l1a, "hqla_l1b_rc": l1b, "hqla_l2a_rc": l2a, "hqla_l2b_rc": l2b,
            "hqla_cap_adjustment_rc": hq["adjustment"], "hqla_l1b_share": hq["l1b_share"], "hqla_total_rc": hq["total"],
            "lcr_outflows_rc": out_f, "lcr_inflows_rc": in_f, "lcr_inflows_capped_rc": in_c,
            "lcr_net_outflows_rc": net, "lcr_ratio": hq["total"] / net if net > 0 else None}


def hqla_caps(l1a: float, l1b: float, l2a: float, l2b: float, hcfg: dict) -> dict:
    """Composition caps on post-haircut values (simplified, without unwinding secured funding):
    Basel: L2B <= cap_l2b and L2 <= cap_l2 of HQLA (L1 = L1A + L1B).
    EU DR 2015/61 (when cap_l1b is set): Level 1 covered bonds (L1B) <= cap_l1b of HQLA."""
    cap2b, cap2 = hcfg["cap_l2b"], hcfg["cap_l2"]
    l1 = l1a + l1b
    adj_2b = max(l2b - cap2b / (1 - cap2b) * (l1 + l2a), l2b - cap2b / (1 - cap2) * l1, 0.0)
    adj_2 = max(l2a + l2b - adj_2b - cap2 / (1 - cap2) * l1, 0.0)
    l2_eff = l2a + l2b - adj_2b - adj_2
    adj_1b = 0.0
    if hcfg.get("cap_l1b") is not None:
        c = hcfg["cap_l1b"]
        adj_1b = max(l1b - c / (1 - c) * (l1a + l2_eff), 0.0)
    total = l1 + l2_eff - adj_1b
    return {"total": total, "adjustment": adj_2b + adj_2 + adj_1b,
            "l1b_share": (l1b - adj_1b) / total if total > 0 else 0.0}


def nsfr(pos_d: pd.DataFrame, prod: pd.DataFrame) -> dict:
    t = pos_d["product_code"].map(prod.set_index("product_code")["nsfr_type"]).values
    w = pos_d["balance_rc"].values * pos_d["nsfr_factor"].values
    asf, rsf = float(w[t == "ASF"].sum()), float(w[t == "RSF"].sum())
    return {"asf_rc": asf, "rsf_rc": rsf, "nsfr_ratio": asf / rsf if rsf > 0 else None}


def bank_metrics(bank, cfg, cal, drivers: dict, surv: dict) -> pd.DataFrame:
    prod = bank.dim_product
    scopes = ["ALL"] + sorted(cfg["currencies"])
    rows = []

    def sel(df, d, scope):
        x = df[df["date"] == d]
        return x if scope == "ALL" else x[x["currency_code"] == scope]

    for d in cal.month_ends:
        for scope in scopes:
            ps, hs = sel(bank.positions, d, scope), sel(bank.hqla, d, scope)
            rows.append({"date": d, "scenario_key": "ACT", "entity_code": cfg["bank"]["code"], "currency_scope": scope,
                         **lcr(ps, hs, prod, cfg, None), **nsfr(ps, prod)})
    for s, drv in drivers.items():
        for scope in scopes:
            ps, hs = sel(bank.positions, cal.as_of, scope), sel(bank.hqla, cal.as_of, scope)
            sv = surv[s][scope]
            row = {"date": cal.as_of, "scenario_key": s, "entity_code": cfg["bank"]["code"], "currency_scope": scope,
                   **lcr(ps, hs, prod, cfg, drv),
                   "cbc_rc": sv["cbc_rc"], "stressed_net_outflow_30d_rc": sv["stressed_net_outflow_30d_rc"],
                   "survival_days": sv["survival_days"], "survives_horizon": int(sv["survival_days"] is None),
                   "min_liquidity_position_rc": sv["min_position_rc"],
                   "survival_days_post_mgmt": sv["survival_days_post_mgmt"],
                   "min_liquidity_position_post_mgmt_rc": sv["min_position_post_mgmt_rc"]}
            if s == "BASE":
                row.update(nsfr(ps, prod))
            rows.append(row)
    return pd.DataFrame(rows)


def bank_survival_curve(surv: dict, cal) -> pd.DataFrame:
    rows = []
    for s, by_scope in surv.items():
        for scope, v in by_scope.items():
            rows.append(pd.DataFrame({"scenario_key": s, "currency_scope": scope, "date": cal.proj_days,
                                      "days_from_asof": np.arange(1, len(cal.proj_days) + 1),
                                      "cbc_available_rc": v["cbc_available"],
                                      "liquidity_position_rc": v["position"],
                                      "liquidity_position_post_mgmt_rc": v["position_post_mgmt"]}))
    return pd.concat(rows, ignore_index=True)


def corp_metrics(corp, corp_bal: dict, corp_surv: dict, cfg, cal) -> pd.DataFrame:
    rows = []
    act = corp.balances
    me = act[act["date"].isin(cal.month_ends)]
    for d, g in me.groupby("date"):
        for ecode, x in list(g.groupby("entity_code")) + [(cfg["corporate"]["group_code"], g)]:
            rows.append({"date": d, "scenario_key": "ACT", "entity_code": ecode,
                         "currency_scope": x["currency_code"].iloc[0] if ecode != cfg["corporate"]["group_code"] else "ALL",
                         "cash_rc": x["closing_rc"].sum(), "undrawn_facilities_rc": x["undrawn_available_rc"].sum(),
                         "headroom_rc": x["headroom_rc"].sum()})
    asof_cash = act[act["date"] == cal.as_of].set_index("entity_code")["closing_rc"]
    for s, bal in corp_bal.items():
        first = bal[bal["date"] == cal.proj_days[0]]
        for ecode in list(corp.entities["entity_code"]) + [cfg["corporate"]["group_code"]]:
            is_grp = ecode == cfg["corporate"]["group_code"]
            x = bal if is_grp else bal[bal["entity_code"] == ecode]
            daily = x.groupby("date")["headroom_rc"].sum()
            sd = corp_surv[s]["__GROUP__" if is_grp else ecode]
            f0 = first if is_grp else first[first["entity_code"] == ecode]
            rows.append({"date": cal.as_of, "scenario_key": s, "entity_code": ecode,
                         "currency_scope": "ALL" if is_grp else x["currency_code"].iloc[0],
                         "cash_rc": float(asof_cash.sum() if is_grp else asof_cash[ecode]),
                         "undrawn_facilities_rc": float(f0["undrawn_available_rc"].sum()),
                         "min_headroom_rc": float(daily.min()), "survival_days": sd, "survives_horizon": int(sd is None)})
    return pd.DataFrame(rows)


def gap_table(bank, stressed: pd.DataFrame, cal) -> pd.DataFrame:
    """Maturity ladder (reporting currency): CONTRACTUAL view + one behavioural view per scenario (stressed <= horizon, contractual beyond)."""
    H = len(cal.proj_days)
    cf = bank.flows_contractual
    views = [("CONTRACTUAL", cf[["bucket_key", "currency_code", "total_cash_rc"]].rename(columns={"total_cash_rc": "amount_rc"}))]
    tail = cf[(cf["flow_type"] == "SCHEDULED") & (cf["days_from_asof"] > H)][["bucket_key", "currency_code", "total_cash_rc"]]
    tail = tail.rename(columns={"total_cash_rc": "amount_rc"})
    for s, g in stressed.groupby("scenario_key"):
        views.append((s, pd.concat([g[["bucket_key", "currency_code", "amount_rc"]], tail], ignore_index=True)))
    keys = [b[0] for b in buckets()]
    rows = []
    for view, f in views:
        for scope in ["ALL"] + sorted(f["currency_code"].unique()):
            x = f if scope == "ALL" else f[f["currency_code"] == scope]
            inflow = x[x["amount_rc"] > 0].groupby("bucket_key")["amount_rc"].sum().reindex(keys, fill_value=0.0)
            outflow = x[x["amount_rc"] < 0].groupby("bucket_key")["amount_rc"].sum().reindex(keys, fill_value=0.0)
            net = inflow + outflow
            rows.append(pd.DataFrame({"view": view, "currency_scope": scope, "bucket_key": keys, "inflows_rc": inflow.values,
                                      "outflows_rc": outflow.values, "net_gap_rc": net.values,
                                      "cumulative_gap_rc": net.cumsum().values}))
    return pd.concat(rows, ignore_index=True)
