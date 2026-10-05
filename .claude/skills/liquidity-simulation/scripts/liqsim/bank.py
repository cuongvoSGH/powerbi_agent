"""Bank balance sheet simulation: contracts, cash-flow schedules, positions, HQLA holdings.

Sign convention for cash flows: + = cash received by the bank, - = cash paid.
side_sign = +1 for assets, -1 for liabilities / equity / off-balance commitments.
Balance roll-forward: delta balance = -side_sign * sum(principal-type cash flows).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .common import (DAY, Calendar, add_months_day, bucket_of, buckets, day_of_month, fx_lookup, months_index, nm_bucket_key,
                     nsfr_band, spot)

SEGMENTS = {
    "RETAIL": "Retail", "SME": "SME", "CORPORATE": "Corporate", "FI": "Financial institution",
    "SOVEREIGN": "Sovereign", "CENTRAL_BANK": "Central bank", "NA": "Not applicable",
}
DATED = {"amortising", "bullet_m", "bullet_d"}
UNDATED = {"nmd", "static", "facility"}
PATH_VOL = {"nmd": None, "static": 0.005, "facility": 0.03}   # None -> cfg nmd_vol_monthly


@dataclass
class BankData:
    dim_product: pd.DataFrame
    dim_segment: pd.DataFrame
    contracts: pd.DataFrame          # dim_contract
    positions: pd.DataFrame          # fact_bank_position
    hqla: pd.DataFrame               # fact_hqla_holding
    flows_history: pd.DataFrame      # fact_bank_cashflow_history
    flows_contractual: pd.DataFrame  # fact_bank_cashflow_contractual


# ------------------------------------------------------------------ dimensions
def build_dim_product(cfg) -> pd.DataFrame:
    b = cfg["bank"]
    rows = []
    for i, (code, p) in enumerate(b["products"].items(), 1):
        lcr = p.get("lcr", {})
        side = p["side"]
        level = p.get("hqla_level")
        cbc_level = cbc_level_of(p)
        nsfr = p.get("nsfr", {})
        rows.append({
            "product_code": code,
            "product_name": p["name"],
            "side": side,
            "category": p["category"],
            "segment_code": p["segment"],
            "product_class": p["class"],
            "side_sign": 1 if side == "Asset" else -1,
            "hqla_level": level or "",
            "base_haircut": cbc_haircut_of(p, b) if cbc_level else None,
            "cbc_level": cbc_level,
            "cbc_availability_day": b["hqla"].get("cbc_availability_day", {}).get(cbc_level, 1) if cbc_level else None,
            "lcr_basis": lcr.get("basis", "none"),
            "lcr_flow": lcr.get("flow", "hqla" if lcr.get("basis") == "hqla" else ""),
            "lcr_rate": lcr.get("rate"),
            "nsfr_type": "ASF" if side in ("Liability", "Equity") else ("RSF" if p["class"] != "event" else ""),
            "nsfr_factor_lt6m": nsfr.get("lt6m"),
            "nsfr_factor_6m_1y": nsfr.get("m6_1y"),
            "nsfr_factor_ge1y": nsfr.get("ge1y"),
            "sort_order": i,
        })
    return pd.DataFrame(rows)


def cbc_level_of(p: dict) -> str:
    """HQLA level, or CB_ELIGIBLE for central-bank-eligible non-HQLA collateral, else ''."""
    if p.get("hqla_level"):
        return p["hqla_level"]
    return "CB_ELIGIBLE" if p.get("cb_eligible") else ""


def cbc_haircut_of(p: dict, b: dict) -> float:
    if p.get("hqla_level"):
        return float(p.get("hqla_haircut", b["hqla"]["haircuts"][p["hqla_level"]]))
    return float(p.get("cb_haircut", 0.0))


def build_dim_segment() -> pd.DataFrame:
    return pd.DataFrame({"segment_code": list(SEGMENTS), "segment_name": list(SEGMENTS.values())})


# ------------------------------------------------------------------ contracts
def _currencies(p, b, n, rng):
    mix = p.get("currency_mix", b["currency_mix"])
    codes, w = list(mix), np.array(list(mix.values()), dtype=float)
    ccy = rng.choice(codes, n, p=w / w.sum())
    k = min(n, len(codes))
    ccy[:k] = codes[:k]   # every currency in the mix is represented
    return ccy


def generate_contracts(cfg, cal: Calendar, rng: np.random.Generator) -> pd.DataFrame:
    b = cfg["bank"]
    scale = cfg["_size"]["contract_scale"]
    g = b["balance_growth_annual"]
    rates = {k: v["base_rate"] for k, v in cfg["currencies"].items()}
    hist_days = int((cal.as_of - cal.hist_start) / DAY)
    as_of_m = cal.as_of.astype("datetime64[M]")
    frames = []

    for code, p in b["products"].items():
        cls = p["class"]
        if cls == "event":
            continue
        mix = p.get("currency_mix", b["currency_mix"])
        if cls == "static":
            n_live = len(mix)
        else:
            n_live = max(len(mix), int(round(p["live_contracts"] * scale)))
        ccy = _currencies(p, b, n_live, rng)
        df = pd.DataFrame({"product_code": code, "currency_code": ccy, "live": True})

        if cls in DATED:
            if cls == "bullet_d":
                lo, hi = p["term_days"]
                mean_days = (lo + hi) / 2
            else:
                lo, hi = p["term_months"]
                mean_days = (lo + hi) / 2 * 30.44
            n_mat = int(round(n_live * hist_days / mean_days))
            ccy_m = _currencies(p, b, n_mat, rng) if n_mat else np.array([], dtype=object)
            df = pd.concat([df, pd.DataFrame({"product_code": code, "currency_code": ccy_m, "live": False})], ignore_index=True)
            n = len(df)
            live = df["live"].values
            term = rng.integers(lo, hi + 1, n)
            if cls == "bullet_d":
                age = rng.integers(0, term)                                # live: 0..term-1 days old
                mat_hist = cal.hist_start + DAY * rng.integers(1, hist_days + 1, n)
                start = np.where(live, cal.as_of - DAY * age, mat_hist - DAY * term)
                pay_day = day_of_month(start)
                maturity = start + DAY * term
                df["term_days"] = term
                df["term_months"] = np.nan
            else:
                pay_day = rng.integers(1, 29, n)
                age = rng.integers(0, term)                                # live: payments already made
                start_m_live = as_of_m - age
                mat_m_hist = cal.hist_start.astype("datetime64[M]") + rng.integers(1, cal.history_months + 1, n)
                start_m = np.where(live, start_m_live, mat_m_hist - term)
                start = start_m.astype("datetime64[D]") + (pay_day - 1)
                maturity = add_months_day(start, term, pay_day)
                df["term_months"] = term
                df["term_days"] = (maturity - start).astype("int64")
            df["start_date"] = start
            df["maturity_date"] = maturity
            df["pay_day"] = pay_day
            age_years = (start - cal.as_of).astype("int64") / 365.25
            df["notional_local"] = rng.lognormal(0, 0.8, n) * np.exp(g * age_years)
            df["weight"] = np.nan
        else:
            n = len(df)
            df["start_date"] = cal.hist_start - DAY * rng.integers(30, 3650, n)
            df["maturity_date"] = np.datetime64("NaT")
            df["pay_day"] = 0
            df["term_months"] = np.nan
            df["term_days"] = np.nan
            df["weight"] = rng.lognormal(0, 1.0, n)
            df["notional_local"] = np.nan

        floor = 0.001 if p["side"] == "Asset" else 0.0
        spread = p.get("rate_spread", 0.0)
        df["interest_rate"] = 0.0 if cls in ("static", "facility") else np.maximum(
            df["currency_code"].map(rates).values + spread + rng.normal(0, 0.002, len(df)), floor)
        df["coupon_months"] = p.get("coupon_months", 1) if cls == "bullet_m" else (1 if cls in ("amortising", "nmd") else 0)
        df["product_class"] = cls
        df["segment_code"] = p["segment"]
        df["side_sign"] = 1 if p["side"] == "Asset" else -1
        level = cbc_level_of(p)
        df["hqla_level"] = p.get("hqla_level") or ""
        enc_share = b["hqla"]["encumbered_share"].get(level, 0.0) if level and cls != "static" else 0.0
        df["encumbered"] = (rng.random(len(df)) < enc_share).astype(int)
        frames.append(df)

    with warnings.catch_warnings():   # all-NaN columns (e.g. maturity of non-maturity items) are intended
        warnings.simplefilter("ignore", FutureWarning)
        c = pd.concat(frames, ignore_index=True)
    c = c.sort_values(["product_code", "currency_code", "start_date"], kind="stable").reset_index(drop=True)
    c["contract_id"] = [f"B{i:06d}" for i in range(1, len(c) + 1)]
    _scale_to_targets(c, cfg, cal)
    return c


def dated_balance(c: pd.DataFrame, d: np.ndarray) -> np.ndarray:
    """Outstanding principal of dated contracts (rows of c) at dates d (same length)."""
    cls = c["product_class"].values
    P = c["notional_local"].values.astype(float)
    start = c["start_date"].values.astype("datetime64[D]")
    mat = c["maturity_date"].values.astype("datetime64[D]")
    pay_day = c["pay_day"].values.astype("int64")
    n = pd.to_numeric(c["term_months"], errors="coerce").fillna(1).values.astype("int64")
    k = months_index(d) - months_index(start) - (day_of_month(d) < pay_day)
    k = np.clip(k, 0, n)
    r = c["interest_rate"].values / 12
    with np.errstate(divide="ignore", invalid="ignore"):
        grow_n, grow_k = (1 + r) ** n, (1 + r) ** k
        f_am = np.where(r > 0, (grow_n - grow_k) / (grow_n - 1), 1 - k / n)
    bal = np.where(cls == "amortising", P * f_am,
          np.where(cls == "bullet_m", np.where(k < n, P, 0.0),
                   np.where(d < mat, P, 0.0)))
    return np.where(d >= start, bal, 0.0)


def _scale_to_targets(c: pd.DataFrame, cfg, cal: Calendar):
    b = cfg["bank"]
    fx = spot(cfg)
    total = b["total_assets_rc"]
    for (code, ccy), idx in c.groupby(["product_code", "currency_code"]).groups.items():
        p = b["products"][code]
        mix = p.get("currency_mix", b["currency_mix"])
        target_local = total * p["share"] * mix[ccy] / sum(mix.values()) / fx[ccy]
        sub = c.loc[idx]
        if p["class"] in DATED:
            cur = dated_balance(sub, np.full(len(sub), cal.as_of)).sum()
            c.loc[idx, "notional_local"] = sub["notional_local"].values * (target_local / cur)
        else:
            w = sub["weight"].values
            c.loc[idx, "notional_local"] = target_local * w / w.sum()


# ------------------------------------------------------------------ schedules
def schedule(c: pd.DataFrame) -> pd.DataFrame:
    """Every cash flow of every dated contract (origination, principal, interest)."""
    out = []
    m = c[c["product_class"].isin(["amortising", "bullet_m"])]
    if len(m):
        n = m["term_months"].values.astype("int64")
        rep = np.repeat(np.arange(len(m)), n)
        k = np.concatenate([np.arange(1, x + 1) for x in n])
        mm = m.iloc[rep]
        start = mm["start_date"].values.astype("datetime64[D]")
        pay_day = mm["pay_day"].values.astype("int64")
        dates = add_months_day(start, k, pay_day)
        P = mm["notional_local"].values
        r_ann = mm["interest_rate"].values
        r = r_ann / 12
        nn = n[rep]
        is_am = mm["product_class"].values == "amortising"
        with np.errstate(divide="ignore", invalid="ignore"):
            gn = (1 + r) ** nn
            f_prev = np.where(r > 0, (gn - (1 + r) ** (k - 1)) / (gn - 1), 1 - (k - 1) / nn)
            f_k = np.where(r > 0, (gn - (1 + r) ** k) / (gn - 1), 1 - k / nn)
        b_prev = np.where(is_am, P * f_prev, P)
        b_k = np.where(is_am, P * f_k, np.where(k < nn, P, 0.0))
        principal = b_prev - b_k
        cm = np.maximum(mm["coupon_months"].values.astype("int64"), 1)
        last_stub = np.where(nn % cm == 0, cm, nn % cm)
        coupon_due = (k % cm == 0) | (k == nn)
        months = np.where((k == nn), last_stub, cm)
        interest = np.where(is_am, b_prev * r, np.where(coupon_due, P * r_ann * months / 12, 0.0))
        out.append(pd.DataFrame({"contract_id": mm["contract_id"].values, "date": dates,
                                 "principal": principal, "interest": interest}))
    d = c[c["product_class"] == "bullet_d"]
    if len(d):
        days = d["term_days"].values.astype("int64")
        out.append(pd.DataFrame({"contract_id": d["contract_id"].values,
                                 "date": d["maturity_date"].values.astype("datetime64[D]"),
                                 "principal": d["notional_local"].values,
                                 "interest": d["notional_local"].values * d["interest_rate"].values * days / 365}))
    s = pd.concat(out, ignore_index=True)
    s = s[(s["principal"].abs() > 1e-9) | (s["interest"].abs() > 1e-9)]
    return s


# ------------------------------------------------------------------ build
def simulate_bank(cfg, cal: Calendar, fx: pd.DataFrame, rng: np.random.Generator) -> BankData:
    b = cfg["bank"]
    dim_product = build_dim_product(cfg)
    c = generate_contracts(cfg, cal, rng)
    meta = c.set_index("contract_id")

    # ---- positions: contracts x month-ends
    me = cal.month_ends
    nc, nm = len(c), len(me)
    rep = np.repeat(np.arange(nc), nm)
    dates = np.tile(me, nc)
    cc = c.iloc[rep].reset_index(drop=True)
    cls = cc["product_class"].values
    dated = np.isin(cls, list(DATED))

    bal = np.zeros(len(cc))
    due30 = np.zeros(len(cc))
    if dated.any():
        sub = cc[dated]
        bal[dated] = dated_balance(sub, dates[dated])
        due30[dated] = bal[dated] - dated_balance(sub, dates[dated] + DAY * 30)

    # undated: per (product, currency) random-walk path, contracts keep a fixed share
    path = np.ones(len(cc))
    g = b["balance_growth_annual"]
    for (code, ccy), grp in c[~c["product_class"].isin(list(DATED))].groupby(["product_code", "currency_code"]):
        vol = PATH_VOL[grp["product_class"].iloc[0]] or b["nmd_vol_monthly"]
        steps = rng.normal(g / 12, vol, nm - 1)
        logp = np.concatenate([[0.0], np.cumsum(steps)])
        logp -= logp[-1]
        mask = (cc["product_code"].values == code) & (cc["currency_code"].values == ccy)
        path[mask] = np.exp(logp)[np.tile(np.arange(nm), len(grp))]
    bal[~dated] = cc["notional_local"].values[~dated] * path[~dated]

    pos = pd.DataFrame({
        "date": dates, "contract_id": cc["contract_id"].values, "product_code": cc["product_code"].values,
        "currency_code": cc["currency_code"].values, "balance_local": bal, "principal_due_30d_local": due30,
    })
    keep = pos["balance_local"] > 0.005
    pos, cc = pos[keep].reset_index(drop=True), cc[keep.values].reset_index(drop=True)
    rate = fx_lookup(fx, pos["date"].values, pos["currency_code"].values)
    pos["balance_rc"] = pos["balance_local"] * rate
    pos["principal_due_30d_rc"] = pos["principal_due_30d_local"] * rate

    mat = cc["maturity_date"].values.astype("datetime64[D]")
    rem = (mat - pos["date"].values.astype("datetime64[D]")).astype("timedelta64[D]").astype("float64")
    is_dated = np.isin(cc["product_class"].values, list(DATED))
    rem = np.where(is_dated, rem, np.nan)
    pos["remaining_maturity_days"] = pd.array(np.where(np.isnan(rem), np.nan, rem), dtype="Int64")
    pcat = cc["product_code"].map(dim_product.set_index("product_code")["category"]).values
    bucket = np.where(is_dated, bucket_of(np.nan_to_num(rem, nan=1)),
             np.where(cc["product_class"].values == "static", nm_bucket_key(), buckets()[0][0]))
    bucket = np.where(pcat == "Cash & Reserves", buckets()[0][0], bucket)
    pos["bucket_key"] = bucket
    band = np.where(is_dated, nsfr_band(np.nan_to_num(rem, nan=0)), "lt6m")
    pos["nsfr_band"] = band
    fac = dim_product.set_index("product_code")[["nsfr_factor_lt6m", "nsfr_factor_6m_1y", "nsfr_factor_ge1y"]]
    fac.columns = ["lt6m", "m6_1y", "ge1y"]
    f = fac.reindex(pos["product_code"].values)
    nsfr_f = np.choose(pd.Categorical(band, categories=["lt6m", "m6_1y", "ge1y"]).codes, [f["lt6m"].values, f["m6_1y"].values, f["ge1y"].values])
    enc = cc["encumbered"].values == 1
    nsfr_f = np.where(enc, b["nsfr_encumbered_rsf"], nsfr_f)
    pos["nsfr_factor"] = nsfr_f.astype(float)
    basis = pos["product_code"].map(dim_product.set_index("product_code")["lcr_basis"]).values
    pos["lcr_base_rc"] = np.where(basis == "balance", pos["balance_rc"],
                          np.where(basis == "due_30d", pos["principal_due_30d_rc"], 0.0))

    # ---- HQLA holdings (securities + reserves) with price paths
    # counterbalancing stock: HQLA (L1/L1B/L2A/L2B) + central-bank-eligible non-HQLA (hqla_level = CB_ELIGIBLE)
    pidx = dim_product.set_index("product_code")
    hq = pos[pos["product_code"].map(pidx["cbc_level"]).values != ""].copy()
    hq["hqla_level"] = hq["product_code"].map(pidx["cbc_level"])
    hq = hq.sort_values(["contract_id", "date"]).reset_index(drop=True)
    vol = hq["hqla_level"].map(lambda lv: b["hqla"]["price_vol_monthly"].get(lv, 0.02)).values
    is_cash = hq["product_code"].map(dim_product.set_index("product_code")["category"]).values == "Cash & Reserves"
    price = np.ones(len(hq))
    shocks = rng.normal(0, 1, len(hq)) * vol
    x = 0.0
    prev = None
    for i, cid in enumerate(hq["contract_id"].values):
        x = shocks[i] if cid != prev else 0.8 * x + shocks[i]
        prev = cid
        price[i] = 1.0 if is_cash[i] else 1.0 + x
    hq["price"] = price
    hq["market_value_local"] = hq["balance_local"] * price
    hq["market_value_rc"] = hq["balance_rc"] * price
    hq["encumbered"] = hq["contract_id"].map(meta["encumbered"]).astype(int).values
    hq["base_haircut"] = hq["product_code"].map(pidx["base_haircut"]).astype(float)
    hqla = hq[["date", "contract_id", "product_code", "currency_code", "hqla_level", "balance_local", "price",
               "market_value_local", "market_value_rc", "encumbered", "base_haircut"]].rename(columns={"balance_local": "nominal_local"})

    # ---- cash flows
    side = meta["side_sign"]
    dated_c = c[c["product_class"].isin(list(DATED))]
    sch = schedule(dated_c)
    sch_side = sch["contract_id"].map(side).values
    sch["principal_cash"] = sch_side * sch["principal"]
    sch["interest_cash"] = sch_side * sch["interest"]
    sch["product_code"] = sch["contract_id"].map(meta["product_code"]).values
    sch["currency_code"] = sch["contract_id"].map(meta["currency_code"]).values

    # history (hist_start, as_of]
    h = sch[(sch["date"] > cal.hist_start) & (sch["date"] <= cal.as_of)]
    orig = dated_c[(dated_c["start_date"] > cal.hist_start) & (dated_c["start_date"] <= cal.as_of)]
    parts = [
        h.assign(flow_type="PRINCIPAL", amount_local=h["principal_cash"])[["date", "product_code", "currency_code", "flow_type", "amount_local"]],
        h.assign(flow_type="INTEREST", amount_local=h["interest_cash"])[["date", "product_code", "currency_code", "flow_type", "amount_local"]],
        pd.DataFrame({"date": orig["start_date"].values, "product_code": orig["product_code"].values,
                      "currency_code": orig["currency_code"].values, "flow_type": "ORIGINATION",
                      "amount_local": -orig["side_sign"].values * orig["notional_local"].values}),
    ]
    parts += _nmd_history_flows(pos, c, cal, rng)
    hist = pd.concat(parts, ignore_index=True)
    hist = hist[hist["amount_local"].abs() > 0.005]
    hist = hist.groupby(["date", "product_code", "currency_code", "flow_type"], as_index=False)["amount_local"].sum()
    hist["amount_rc"] = hist["amount_local"] * fx_lookup(fx, hist["date"].values, hist["currency_code"].values)

    # contractual future (as_of, maturity] + non-maturity balances on demand
    fut = sch[sch["date"] > cal.as_of].copy()
    fut["flow_type"] = "SCHEDULED"
    asof_pos = pos[pos["date"] == cal.as_of]
    nmd = asof_pos[asof_pos["contract_id"].map(meta["product_class"]).values == "nmd"]
    on_demand = pd.DataFrame({
        "contract_id": nmd["contract_id"].values, "date": cal.as_of + DAY,
        "principal_cash": nmd["contract_id"].map(side).values * nmd["balance_local"].values, "interest_cash": 0.0,
        "product_code": nmd["product_code"].values, "currency_code": nmd["currency_code"].values, "flow_type": "NMD_ON_DEMAND",
    })
    fut = pd.concat([fut[on_demand.columns], on_demand], ignore_index=True)
    sp = spot(cfg)
    fut["days_from_asof"] = ((fut["date"].values.astype("datetime64[D]") - cal.as_of) / DAY).astype("int64")
    fut["bucket_key"] = bucket_of(fut["days_from_asof"].values)
    fut["total_cash_local"] = fut["principal_cash"] + fut["interest_cash"]
    r = fut["currency_code"].map(sp).values
    fut["principal_cash_rc"] = fut["principal_cash"] * r
    fut["interest_cash_rc"] = fut["interest_cash"] * r
    fut["total_cash_rc"] = fut["total_cash_local"] * r
    fut = fut.rename(columns={"principal_cash": "principal_cash_local", "interest_cash": "interest_cash_local"})
    fut = fut.sort_values(["date", "contract_id"]).reset_index(drop=True)
    fut = fut[["date", "contract_id", "product_code", "currency_code", "flow_type", "days_from_asof", "bucket_key",
               "principal_cash_local", "interest_cash_local", "total_cash_local",
               "principal_cash_rc", "interest_cash_rc", "total_cash_rc"]]

    dim_contract = c[["contract_id", "product_code", "currency_code", "segment_code", "product_class", "start_date",
                      "maturity_date", "term_months", "term_days", "pay_day", "coupon_months", "interest_rate",
                      "notional_local", "hqla_level", "encumbered", "live"]].rename(columns={"live": "is_live_at_asof"})
    dim_contract["is_live_at_asof"] = dim_contract["is_live_at_asof"].astype(int)
    for col in ("term_months", "term_days"):
        dim_contract[col] = dim_contract[col].astype("Int64")
    dim_contract["notional_rc_at_asof_fx"] = dim_contract["notional_local"] * dim_contract["currency_code"].map(sp)

    pos = pos[["date", "contract_id", "product_code", "currency_code", "balance_local", "balance_rc",
               "principal_due_30d_local", "principal_due_30d_rc", "remaining_maturity_days", "bucket_key",
               "nsfr_band", "nsfr_factor", "lcr_base_rc"]]
    return BankData(dim_product, build_dim_segment(), dim_contract, pos, hqla, hist, fut)


def _nmd_history_flows(pos: pd.DataFrame, c: pd.DataFrame, cal: Calendar, rng) -> list[pd.DataFrame]:
    """Net balance changes (spread over the days of each month) and month-end interest for NMD accounts."""
    meta = c.set_index("contract_id")
    nmd = pos[pos["contract_id"].map(meta["product_class"]).values == "nmd"].copy()
    if nmd.empty:
        return []
    nmd["side"] = nmd["contract_id"].map(meta["side_sign"]).values
    nmd["rate"] = nmd["contract_id"].map(meta["interest_rate"]).values
    out = []
    # interest at each month-end after hist_start
    it = nmd[nmd["date"] > cal.hist_start]
    out.append(pd.DataFrame({"date": it["date"].values, "product_code": it["product_code"].values,
                             "currency_code": it["currency_code"].values, "flow_type": "NMD_INTEREST",
                             "amount_local": it["side"].values * it["balance_local"].values * it["rate"].values / 12}))
    grp = nmd.groupby(["product_code", "currency_code", "date"])["balance_local"].sum().unstack("date").fillna(0.0)
    side = nmd.groupby(["product_code", "currency_code"])["side"].first()
    me = cal.month_ends
    for (code, ccy), row in grp.iterrows():
        vals = row.reindex(pd.DatetimeIndex(me)).fillna(0.0).values
        for m in range(1, len(me)):
            days = np.arange(me[m - 1] + DAY, me[m] + DAY, dtype="datetime64[D]")
            delta = vals[m] - vals[m - 1]
            w = rng.dirichlet(np.full(len(days), 5.0))
            out.append(pd.DataFrame({"date": days, "product_code": code, "currency_code": ccy,
                                     "flow_type": "NMD_NET_CHANGE", "amount_local": -side[(code, ccy)] * delta * w}))
    return out
