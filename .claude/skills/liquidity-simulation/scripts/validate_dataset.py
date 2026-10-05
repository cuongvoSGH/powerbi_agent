"""Validate a generated liquidity dataset: integrity, reconciliation and plausibility.

Usage:
    python validate_dataset.py [data/liquidity]

Checks
  integrity      primary keys unique, foreign keys resolve (registry in liqsim/docs.py), FX coverage of history
  reconciliation bank balance roll-forward (positions vs history principal flows), assets = liabilities + equity,
                 corporate cash roll-forward (opening + flows = closing, flows = fact tables)
  plausibility   BASE LCR / NSFR ranges, stressed LCR < BASE, survival ordering, reverse stress breaches within target
Exit code 1 if any check FAILS (warnings do not fail).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from liqsim.docs import TABLES  # noqa: E402

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "", warn: bool = False):
    results.append(("PASS" if ok else ("WARN" if warn else "FAIL"), name, detail))


def load(folder: Path) -> dict[str, pd.DataFrame]:
    dfs = {}
    for t in TABLES:
        f = folder / f"{t}.csv"
        if f.exists():
            dfs[t] = pd.read_csv(f, keep_default_na=False, na_values=[""], low_memory=False)
    return dfs


def integrity(d: dict[str, pd.DataFrame]):
    for t, meta in TABLES.items():
        if t not in d:
            continue
        df = d[t]
        dup = int(df.duplicated(meta["pk"]).sum())
        check(f"PK unique: {t}", dup == 0, f"{dup} duplicate keys on {meta['pk']}" if dup else f"{len(df):,} rows")
        for col, ref in meta.get("fk", {}).items():
            rt, rc = ref.split(".")
            if rt not in d or col not in df.columns:
                continue
            vals = df[col].dropna()
            vals = vals[vals.astype(str) != ""]
            missing = set(vals.astype(str).unique()) - set(d[rt][rc].astype(str))
            check(f"FK {t}.{col} -> {ref}", not missing, f"{len(missing)} missing, e.g. {sorted(missing)[:3]}" if missing else "")
    if "fact_fx_rate" in d:
        dates = d["dim_date"].loc[d["dim_date"]["days_from_asof"] <= 0, "date"]
        need = len(dates) * len(d["dim_currency"])
        have = d["fact_fx_rate"].merge(dates.to_frame(), on="date").shape[0]
        check("FX coverage: every history date x currency", have == need, f"{have:,}/{need:,}")


def bank_reconciliation(d, cfg):
    if "fact_bank_position" not in d:
        return
    prod = d["dim_product"].set_index("product_code")
    pos, hist = d["fact_bank_position"], d["fact_bank_cashflow_history"]
    me = sorted(pos["date"].unique())
    flows = hist[hist["flow_type"].isin(["ORIGINATION", "PRINCIPAL", "NMD_NET_CHANGE"])]
    bal = pos.groupby(["product_code", "currency_code", "date"])["balance_local"].sum()
    worst, n_bad = 0.0, 0
    for (code, ccy), g in bal.groupby(level=[0, 1]):
        if prod.loc[code, "product_class"] in ("static", "facility", "event"):
            continue
        series = g.droplevel([0, 1]).reindex(me, fill_value=0.0)
        f = flows[(flows["product_code"] == code) & (flows["currency_code"] == ccy)]
        side = prod.loc[code, "side_sign"]
        tol = 1e-6 * series.abs().max() + 50
        for i in range(1, len(me)):
            cash = f[(f["date"] > me[i - 1]) & (f["date"] <= me[i])]["amount_local"].sum()
            diff = (series.iloc[i] - series.iloc[i - 1]) - (-side * cash)
            if abs(diff) > tol:
                n_bad += 1
            worst = max(worst, abs(diff) / max(series.abs().max(), 1))
    check("Bank balance roll-forward (delta balance = -side x principal cash)", n_bad == 0,
          f"{n_bad} product-currency-months off; worst relative diff {worst:.2e}")
    asof = pos[pos["date"] == me[-1]]
    side = asof["product_code"].map(prod["side"])
    a = asof.loc[side == "Asset", "balance_rc"].sum()
    le = asof.loc[side.isin(["Liability", "Equity"]), "balance_rc"].sum()
    check("Bank assets = liabilities + equity at as-of (+-0.5%)", abs(a - le) / a < 0.005, f"A {a/1e9:,.3f}bn vs L+E {le/1e9:,.3f}bn")
    target = cfg["bank"]["total_assets_rc"]
    check("Bank total assets match config (+-0.5%)", abs(a - target) / target < 0.005, f"{a/1e9:,.3f}bn vs {target/1e9:,.3f}bn")


def corp_reconciliation(d):
    if "fact_corp_cash_balance" not in d:
        return
    b = d["fact_corp_cash_balance"].sort_values(["scenario_key", "account_id", "date"])
    err = (b["opening_local"] + b["net_flow_local"] - b["closing_local"]).abs()
    tol = 1e-6 * b["closing_local"].abs() + 0.05
    check("Corporate cash: opening + net flow = closing", bool((err <= tol).all()), f"{int((err > tol).sum())} rows off")
    prev = b.groupby(["scenario_key", "account_id"])["closing_local"].shift()
    m = prev.notna()
    gap = (b.loc[m, "opening_local"] - prev[m]).abs()
    check("Corporate cash: opening = previous closing", bool((gap <= tol[m]).all()), f"{int((gap > tol[m]).sum())} rows off")
    for scen, flows in (("ACT", d["fact_corp_cashflow_actual"].assign(scenario_key="ACT")), ("forecast", d["fact_corp_cashflow_forecast"])):
        fsum = flows.groupby(["scenario_key", "account_id", "date"])["amount_local"].sum()
        bb = b if scen == "forecast" else b[b["scenario_key"] == "ACT"]
        if scen == "forecast":
            bb = bb[bb["scenario_key"] != "ACT"]
        net = bb.set_index(["scenario_key", "account_id", "date"])["net_flow_local"]
        diff = (net - fsum.reindex(net.index, fill_value=0.0)).abs()
        check(f"Corporate {scen} flows = balance net flow", bool((diff <= 1e-6 * net.abs() + 0.05).all()), f"{int((diff > 0.05 + 1e-6 * net.abs()).sum())} days off")


def plausibility(d, cfg):
    if "fact_liquidity_metrics" not in d:
        return
    v = cfg.get("validation", {})
    H = cfg["meta"]["horizon_days"]
    m = d["fact_liquidity_metrics"]
    stress = [k for k, x in cfg["scenarios"].items() if x.get("type") == "stress"]
    bank = m[(m["entity_code"] == cfg["bank"]["code"]) & (m["currency_scope"] == "ALL") & (m["scenario_key"] != "ACT")].set_index("scenario_key")
    if len(bank):
        lo, hi = v.get("base_lcr_range", [1.1, 2.0])
        lcr = bank["lcr_ratio"]
        check(f"BASE LCR within [{lo:.0%}, {hi:.0%}]", lo <= lcr["BASE"] <= hi, f"{lcr['BASE']:.1%}")
        ns = bank.loc["BASE", "nsfr_ratio"]
        check(f"BASE NSFR >= {v.get('base_nsfr_min', 1.0):.0%}", ns >= v.get("base_nsfr_min", 1.0), f"{ns:.1%}")
        for s in stress:
            check(f"{s} LCR < BASE LCR", lcr[s] < lcr["BASE"], f"{lcr[s]:.1%} vs {lcr['BASE']:.1%}")
        sv = bank["survival_days"].fillna(H + 1)
        check("BASE survives the full horizon", sv["BASE"] > H, f"{sv['BASE']:.0f}")
        check("Survival: BASE >= every stress scenario", all(sv["BASE"] >= sv[s] for s in stress),
              ", ".join(f"{s} {sv[s]:.0f}" for s in stress) + f" ({H + 1} = survives)")
        if {"IDIO", "MARKET", "COMBINED"} <= set(sv.index):
            check("Survival: min(IDIO, MARKET) >= COMBINED", min(sv["IDIO"], sv["MARKET"]) >= sv["COMBINED"], f"COMBINED {sv['COMBINED']:.0f}")
        if {"COMBINED", "EXTREME"} <= set(sv.index):
            check("Survival: COMBINED >= EXTREME", sv["COMBINED"] >= sv["EXTREME"], f"EXTREME {sv['EXTREME']:.0f}")
        for s, mn in (v.get("survival_min") or {}).items():
            check(f"{s} survival >= {mn} days (risk appetite)", sv[s] >= mn, f"{sv[s]:.0f}")
        for s, (a, b) in (v.get("survival_range") or {}).items():
            check(f"{s} breach within [{a}, {b}] days", a <= sv[s] <= b, f"{sv[s]:.0f}")
        if "survival_days_post_mgmt" in bank.columns:
            post = bank["survival_days_post_mgmt"].fillna(H + 1)
            check("Survival post management actions >= pre", bool((post >= sv).all()),
                  ", ".join(f"{s} {sv[s]:.0f}->{post[s]:.0f}" for s in bank.index))
        if "REVERSE" in sv.index:
            tgt = cfg["scenarios"]["REVERSE"].get("target_survival_days", 30)
            tol = v.get("reverse_tolerance_days", 3)
            check(f"REVERSE breaches within target ({tgt} days)", sv["REVERSE"] <= tgt, f"breach on day {sv['REVERSE']:.0f}")
            check(f"REVERSE breach day within {tol} days of target", sv["REVERSE"] >= tgt - tol,
                  f"day {sv['REVERSE']:.0f} - survival jumps past the target (large single-day outflow); the multiplier is the smallest shock that breaches",
                  warn=True)
        cap = cfg["bank"]["hqla"].get("cap_l1b")
        if cap is not None and "hqla_l1b_share" in m.columns:
            worst = m["hqla_l1b_share"].max()
            check(f"L1B covered bonds <= {cap:.0%} of HQLA after caps (EU DR 2015/61)", worst <= cap + 1e-9, f"max {worst:.1%}")
    if "dim_time_bucket" in d:
        want = len((cfg.get("time_buckets") or {}).get("buckets") or [None] * 9) + 1
        check("Maturity ladder bucket count matches config (+ non-maturity)", len(d["dim_time_bucket"]) == want,
              f"{len(d['dim_time_bucket'])} buckets")
    corp = m[(m["entity_code"] == cfg.get("corporate", {}).get("group_code")) & (m["scenario_key"] == "BASE")]
    if len(corp):
        check("Corporate group BASE never breaches headroom", corp["survives_horizon"].iloc[0] == 1,
              f"min headroom {corp['min_headroom_rc'].iloc[0] / 1e6:,.1f}M", warn=True)


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/liquidity")
    cfg_file = folder / "config_used.yaml"
    if not cfg_file.exists():
        sys.exit(f"{cfg_file} not found - is {folder} a generated dataset?")
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    d = load(folder)
    integrity(d)
    bank_reconciliation(d, cfg)
    corp_reconciliation(d)
    plausibility(d, cfg)
    for status, name, detail in results:
        print(f"{status:4s}  {name}" + (f"  ({detail})" if detail else ""))
    fails = sum(r[0] == "FAIL" for r in results)
    warns = sum(r[0] == "WARN" for r in results)
    print(f"\n{len(results)} checks: {fails} failed, {warns} warnings")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
