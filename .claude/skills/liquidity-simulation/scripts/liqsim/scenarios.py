"""Scenario drivers, bank stressed cash flows, survival horizon, reverse stress calibration."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .common import DAY, Calendar, bucket_of, deep_merge, reporting_currency, spot
FRACTION_DRIVERS = {"rollover", "nmd_runoff_30d", "nmd_runoff_365d", "facility_drawdown_30d", "facility_drawdown_365d",
                    "corp_rcf_availability", "corp_capex_deferral"}


# ------------------------------------------------------------------ drivers
def resolve_drivers(cfg) -> dict[str, dict]:
    """BASE + overrides for every baseline/stress scenario in config order (REVERSE is calibrated later)."""
    sd = cfg["scenario_drivers"]
    base = sd["BASE"]
    out = {}
    for s, meta in cfg["scenarios"].items():
        if meta.get("type") in ("baseline", "stress"):
            out[s] = base if s == "BASE" else deep_merge(base, sd.get(s, {}))
    return out


def scale_drivers(base: dict, target: dict, lam: float, cfg) -> dict:
    """base + lam * (target - base) on numeric leaves, clipped to valid ranges."""
    def walk(b, t, key=None):
        if isinstance(t, dict):
            return {k: walk(b.get(k, 0.0) if isinstance(b, dict) else 0.0, v, k if key is None else key) for k, v in t.items()}
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            if key in ("corp_dividend_suspended", "collateral_call_day", "mgmt_actions"):
                return t   # flags, timing and management actions come from the target scenario, not scaled
            v = b + lam * (t - b)
            if key in FRACTION_DRIVERS:
                v = min(max(v, -1.0 if "runoff" in key else 0.0), 1.0)
            if key == "fx_shock":
                v = max(v, -0.9)
            if key == "corp_key_customer_defaults":
                v = int(min(round(v), cfg["corporate"]["key_accounts"]))
            if key in ("corp_dso_shift_days", "corp_supplier_terms_cut_days"):
                v = int(round(v))
            if key == "hqla_haircut_addon":
                v = max(v, 0.0)
            return v
        return t
    out = walk(base, target)
    hc = cfg["bank"]["hqla"]["haircuts"]
    out["hqla_haircut_addon"] = {k: min(v, 1 - hc.get(k, 0.0)) for k, v in out["hqla_haircut_addon"].items()}
    return out


# ------------------------------------------------------------------ bank stressed flows
def _cum_curve(r30: float, r365: float, H: int) -> np.ndarray:
    """Cumulative fraction by day 0..H: front-loaded (tau = 7d) to day 30, linear afterwards."""
    d = np.arange(H + 1, dtype=float)
    tau = 7.0
    first = r30 * (1 - np.exp(-np.minimum(d, 30) / tau)) / (1 - np.exp(-30 / tau))
    later = np.where(d > 30, (r365 - r30) * (d - 30) / max(H - 30, 1), 0.0)
    return first + later


class BankStress:
    """Pre-aggregated as-of inputs so scenario flows can be rebuilt quickly (used by reverse bisection)."""

    def __init__(self, bank, cfg, cal: Calendar):
        self.cfg, self.cal = cfg, cal
        self.H = len(cal.proj_days)
        self.sp = spot(cfg)
        self.rc = reporting_currency(cfg)
        prod = bank.dim_product.set_index("product_code")
        self.prod = prod
        f = bank.flows_contractual
        f = f[(f["flow_type"] == "SCHEDULED") & (f["days_from_asof"] <= self.H)]
        self.cf = f.groupby(["product_code", "currency_code", "days_from_asof"], as_index=False)[
            ["principal_cash_local", "interest_cash_local"]].sum()
        # products held in the counterbalancing capacity (HQLA + CB-eligible): principal is not a stressed inflow
        self.cf["is_hqla"] = self.cf["product_code"].map(prod["cbc_level"]).fillna("").values != ""
        pos = bank.positions[bank.positions["date"] == cal.as_of]
        cls = pos["product_code"].map(prod["product_class"]).values
        self.nmd = pos[cls == "nmd"].groupby(["product_code", "currency_code"])["balance_local"].sum()
        self.undrawn = pos[cls == "facility"].groupby(["product_code", "currency_code"])["balance_local"].sum()
        hq = bank.hqla[(bank.hqla["date"] == cal.as_of) & (bank.hqla["encumbered"] == 0)].copy()
        hq["mv_x_haircut"] = hq["market_value_local"] * hq["base_haircut"]
        self.hqla = hq.groupby(["hqla_level", "currency_code"])[["market_value_local", "mv_x_haircut"]].sum()
        self.avail_day = cfg["bank"]["hqla"].get("cbc_availability_day", {})
        self.loan_products = [c for c in prod.index if prod.loc[c, "category"] == "Loans"]
        loans = pos[pos["product_code"].isin(self.loan_products)]
        self.loans_by_ccy = loans.groupby("currency_code")["balance_local"].sum()
        assets = pos[pos["product_code"].map(prod["side"]).values == "Asset"]
        self.total_assets_rc = float(assets["balance_rc"].sum())

    def flows(self, drv: dict, scenario: str) -> pd.DataFrame:
        H, parts = self.H, []
        days = np.arange(1, H + 1)
        cf = self.cf
        # contractual principal (HQLA principal excluded: those securities sit in the counterbalancing capacity)
        p = cf[~cf["is_hqla"]]
        parts.append(pd.DataFrame({"product_code": p["product_code"], "currency_code": p["currency_code"],
                                   "days_from_asof": p["days_from_asof"], "flow_type": "CONTRACTUAL_PRINCIPAL",
                                   "amount_local": p["principal_cash_local"]}))
        parts.append(pd.DataFrame({"product_code": cf["product_code"], "currency_code": cf["currency_code"],
                                   "days_from_asof": cf["days_from_asof"], "flow_type": "CONTRACTUAL_INTEREST",
                                   "amount_local": cf["interest_cash_local"]}))
        roll = drv["rollover"]
        r = p[p["product_code"].isin(list(roll))]
        parts.append(pd.DataFrame({"product_code": r["product_code"], "currency_code": r["currency_code"],
                                   "days_from_asof": r["days_from_asof"], "flow_type": "ROLLOVER",
                                   "amount_local": -r["product_code"].map(roll).values * r["principal_cash_local"].values}))
        for (code, ccy), bal in self.nmd.items():
            c = _cum_curve(drv["nmd_runoff_30d"].get(code, 0.0), drv["nmd_runoff_365d"].get(code, 0.0), H)
            side = self.prod.loc[code, "side_sign"]
            parts.append(pd.DataFrame({"product_code": code, "currency_code": ccy, "days_from_asof": days,
                                       "flow_type": "RUNOFF", "amount_local": side * np.diff(c) * bal}))
        for (code, ccy), und in self.undrawn.items():
            c = _cum_curve(drv["facility_drawdown_30d"].get(code, 0.0), drv["facility_drawdown_365d"].get(code, 0.0), H)
            parts.append(pd.DataFrame({"product_code": code, "currency_code": ccy, "days_from_asof": days,
                                       "flow_type": "DRAWDOWN", "amount_local": -np.diff(c) * und}))
        # collateral call: n-notch downgrade x pct of assets per notch (3-notch per LCR/EBA), or a flat pct
        coll = drv.get("downgrade_notches", 0) * drv.get("collateral_per_notch_pct_assets", 0.0) \
            or drv.get("collateral_call_pct_assets", 0.0)
        if coll > 0:
            parts.append(pd.DataFrame({"product_code": ["DERIV_COLL"], "currency_code": [self.rc],
                                       "days_from_asof": [int(drv["collateral_call_day"])], "flow_type": ["COLLATERAL_CALL"],
                                       "amount_local": [-coll * self.total_assets_rc / self.sp[self.rc]]}))
        parts += self._mgmt_actions(drv, r, roll)
        f = pd.concat(parts, ignore_index=True)
        f = f[f["amount_local"].abs() > 0.005]
        f = f.groupby(["product_code", "currency_code", "days_from_asof", "flow_type"], as_index=False)["amount_local"].sum()
        fx = {k: self.sp[k] * (1 + drv["fx_shock"].get(k, 0.0)) for k in self.sp}
        f["amount_rc"] = f["amount_local"] * f["currency_code"].map(fx)
        f["date"] = self.cal.as_of + DAY * f["days_from_asof"].values.astype("int64")
        f["bucket_key"] = bucket_of(f["days_from_asof"].values)
        f.insert(0, "scenario_key", scenario)
        return f[["scenario_key", "date", "days_from_asof", "bucket_key", "product_code", "currency_code",
                  "flow_type", "amount_local", "amount_rc"]]

    def _mgmt_actions(self, drv: dict, maturing: pd.DataFrame, roll: dict) -> list[pd.DataFrame]:
        """Management actions (EBA GL/2018/04): separate MGMT_* flows so survival can be shown pre and post actions."""
        ma = drv.get("mgmt_actions") or {}
        out = []
        lc = ma.get("lending_cut") or {}
        if lc.get("rollover_reduction", 0) > 0:
            m = maturing[maturing["product_code"].isin(self.loan_products) & (maturing["days_from_asof"] >= lc.get("start_day", 1))]
            cut = m["product_code"].map(lambda c: min(lc["rollover_reduction"], roll.get(c, 0.0))).values
            out.append(pd.DataFrame({"product_code": m["product_code"], "currency_code": m["currency_code"],
                                     "days_from_asof": m["days_from_asof"], "flow_type": "MGMT_LENDING_CUT",
                                     "amount_local": cut * m["principal_cash_local"].values}))
        sale = ma.get("asset_sale") or {}
        if sale.get("pct_of_loans", 0) > 0:
            if "MGMT_ACTION" not in self.prod.index:
                raise SystemExit("mgmt_actions.asset_sale needs an event product MGMT_ACTION in bank.products")
            for ccy, bal in self.loans_by_ccy.items():
                out.append(pd.DataFrame({"product_code": ["MGMT_ACTION"], "currency_code": [ccy],
                                         "days_from_asof": [int(sale.get("day", 30))], "flow_type": ["MGMT_ASSET_SALE"],
                                         "amount_local": [bal * sale["pct_of_loans"] * (1 - sale.get("discount", 0.0))]}))
        return out

    def cbc(self, drv: dict, by_level: bool = False) -> pd.Series:
        """Counterbalancing capacity (reporting currency): unencumbered HQLA and CB-eligible collateral after base +
        scenario haircuts and FX shock. Indexed by currency, or by (level, currency) when by_level."""
        out = {}
        for (level, ccy), row in self.hqla.iterrows():
            mv, mvh = row["market_value_local"], row["mv_x_haircut"]
            add = drv["hqla_haircut_addon"].get(level, 0.0)
            val = max(mv - mvh - mv * add, 0.0) * self.sp[ccy] * (1 + drv["fx_shock"].get(ccy, 0.0))
            key = (level, ccy) if by_level else ccy
            out[key] = out.get(key, 0.0) + val
        return pd.Series(out, dtype=float)

    def survival(self, flows: pd.DataFrame, drv: dict) -> dict:
        """Daily liquidity position = available CBC + cumulative net stressed flow, per scope (ALL + currencies).
        CBC of each level becomes available on its monetisation day (cbc_availability_day, default day 1).
        survival_days excludes management actions (MGMT_* flows); *_post_mgmt includes them."""
        H = self.H
        cbc_lv = self.cbc(drv, by_level=True)
        days = np.arange(1, H + 1)
        res = {}
        is_mgmt = flows["flow_type"].str.startswith("MGMT_").values
        for scope in ["ALL"] + sorted(self.sp):
            in_scope = np.ones(len(flows), bool) if scope == "ALL" else (flows["currency_code"].values == scope)
            avail = np.zeros(H)
            for (level, ccy), v in cbc_lv.items():
                if scope in ("ALL", ccy):
                    avail += np.where(days >= int(self.avail_day.get(level, 1)), v, 0.0)
            out = {"cbc_rc": float(sum(v for (lv, c), v in cbc_lv.items() if scope in ("ALL", c))), "cbc_available": avail}
            for tag, mask in (("", in_scope & ~is_mgmt), ("_post_mgmt", in_scope)):
                f = flows[mask]
                net = np.zeros(H + 1)
                np.add.at(net, f["days_from_asof"].values.astype(int), f["amount_rc"].values)
                cum = np.cumsum(net[1:])
                pos = avail + cum
                neg = np.flatnonzero(pos < 0)
                out[f"survival_days{tag}"] = int(neg[0] + 1) if len(neg) else None
                out[f"min_position{tag}_rc"] = float(pos.min())
                out[f"position{tag}"] = pos
                if not tag:
                    out["stressed_net_outflow_30d_rc"] = float(max(-cum[min(29, H - 1)], 0.0))
            res[scope] = out
        return res


def calibrate_reverse(stress: BankStress | None, corp_fn, cfg, drivers: dict) -> tuple[dict, float, str]:
    """Bisection on lam so that survival(lam) == target. Uses bank survival when available, else corporate group."""
    sc = cfg["scenarios"]["REVERSE"]
    target = int(sc.get("target_survival_days", 30))
    base, comb = drivers["BASE"], drivers[sc.get("based_on", "COMBINED")]
    H = len(stress.cal.proj_days) if stress else None

    def surv(lam):
        d = scale_drivers(base, comb, lam, cfg)
        if stress is not None:
            s = stress.survival(stress.flows(d, "REVERSE"), d)["ALL"]["survival_days"]
            return s if s is not None else H + 1
        return corp_fn(d)

    lo, hi = 0.0, 1.0
    while surv(hi) > target and hi < 64:
        lo, hi = hi, hi * 2
    note = ""
    if surv(hi) > target:
        note = f"target {target} days not reachable (max shock x{hi:g}); using x{hi:g}"
        return scale_drivers(base, comb, hi, cfg), hi, note
    for _ in range(40):
        mid = (lo + hi) / 2
        if surv(mid) > target:
            lo = mid
        else:
            hi = mid
    lam = hi
    return scale_drivers(base, comb, lam, cfg), lam, note


def scenario_parameter_table(cfg, drivers: dict, reverse_lambda: float | None) -> pd.DataFrame:
    """Long table: scenario_key, driver, product_code, currency_code, hqla_level, value.
    Nested driver groups (e.g. mgmt_actions.lending_cut.start_day) are flattened with dots."""
    levels = set(cfg["bank"]["hqla"]["haircuts"]) | {"CB_ELIGIBLE"}
    rows = []

    def add(s, driver, key, v):
        if isinstance(v, dict):
            for kk, vv in v.items():
                if key and kk not in cfg["bank"]["products"] and kk not in cfg["currencies"] and kk not in levels:
                    add(s, f"{driver}.{key}", kk, vv)
                elif key:
                    add(s, f"{driver}.{key}", kk, vv)
                else:
                    add(s, driver, kk, vv)
            return
        rows.append({"scenario_key": s, "driver": driver,
                     "product_code": key if key in cfg["bank"]["products"] else "",
                     "currency_code": key if key in cfg["currencies"] else "",
                     "hqla_level": key if key in levels else "",
                     "value": float(v)})
        if key and not (key in cfg["bank"]["products"] or key in cfg["currencies"] or key in levels):
            rows[-1]["driver"] = f"{driver}.{key}"

    for s, d in drivers.items():
        for k, v in d.items():
            add(s, k, "", v)
    if reverse_lambda is not None:
        rows.append({"scenario_key": "REVERSE", "driver": "reverse_shock_multiplier", "product_code": "",
                     "currency_code": "", "hqla_level": "", "value": float(reverse_lambda)})
    return pd.DataFrame(rows)
