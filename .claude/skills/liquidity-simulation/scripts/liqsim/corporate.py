"""Corporate treasury simulation: AR/AP invoices, daily actual cash flows, facilities, scenario forecasts.

Sign convention: + = cash received by the entity, - = cash paid. Amounts in entity currency (local)
plus reporting currency _rc (daily FX for actuals, as-of spot x scenario FX shock for forecasts).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .common import DAY, Calendar, add_months_day, fx_lookup, next_business_day, prev_business_day, spot

CATEGORIES = [
    # code, name, IAS 7 activity, direction, sort
    ("OP_RECEIPTS", "Customer receipts", "Operating", "Inflow", 1),
    ("OP_SUPPLIERS", "Supplier payments", "Operating", "Outflow", 2),
    ("OP_PAYROLL", "Payroll", "Operating", "Outflow", 3),
    ("OP_OPEX", "Rent & overheads", "Operating", "Outflow", 4),
    ("OP_TAX", "Income tax", "Operating", "Outflow", 5),
    ("INV_CAPEX", "Capital expenditure", "Investing", "Outflow", 6),
    ("FIN_INTEREST", "Interest paid", "Financing", "Outflow", 7),
    ("FIN_DEBT_REPAY", "Term loan repayment", "Financing", "Outflow", 8),
    ("FIN_RCF_DRAW", "Revolver / overdraft drawdown", "Financing", "Inflow", 9),
    ("FIN_RCF_REPAY", "Revolver / overdraft repayment", "Financing", "Outflow", 10),
    ("FIN_DIVIDEND", "Dividends paid", "Financing", "Outflow", 11),
]
FLOW_COLS = ["date", "entity_code", "account_id", "category_code", "currency_code", "amount_local"]


@dataclass
class CorpState:
    dim_cf_category: pd.DataFrame
    dim_counterparty: pd.DataFrame
    dim_bank_account: pd.DataFrame
    dim_facility: pd.DataFrame
    entities: pd.DataFrame
    invoices: pd.DataFrame
    actual: pd.DataFrame
    balances: pd.DataFrame        # ACT daily balances
    loan_schedule: pd.DataFrame   # term-loan flows, all dates
    cash_asof: dict
    drawn_asof: dict              # facility_id -> drawn local at as-of


# ------------------------------------------------------------------ helpers
def _daily_revenue_local(cfg, ent, days: np.ndarray, as_of) -> np.ndarray:
    c = cfg["corporate"]
    season = np.array(c["seasonality"])
    month = (days.astype("datetime64[M]").astype("int64") % 12)
    years = (days - as_of).astype("timedelta64[D]").astype("int64") / 365.25
    usd = c["revenue_rc_annual"] * ent["revenue_share"] / 365 * season[month] * np.exp(c["revenue_growth_annual"] * years)
    return usd / spot(cfg)[ent["currency"]]


def _monthly_dates(first: np.datetime64, last: np.datetime64, day: int) -> np.ndarray:
    months = np.arange(first.astype("datetime64[M]"), last.astype("datetime64[M]") + 1)
    return months.astype("datetime64[D]") + (day - 1)


def _terms(rng, weights: dict, n: int) -> np.ndarray:
    keys = np.array([int(k) for k in weights])
    w = np.array(list(weights.values()), dtype=float)
    return rng.choice(keys, n, p=w / w.sum())


# ------------------------------------------------------------------ dimensions
def _counterparties(cfg, rng) -> pd.DataFrame:
    c = cfg["corporate"]
    size = cfg["_size"]
    rows = []
    for kind, n_total, terms_w in (("Customer", size["customers"], c["ar_terms_days"]),
                                   ("Supplier", size["suppliers"], c["ap_terms_days"])):
        for ecode, e in c["entities"].items():
            n = max(5, int(round(n_total * e["revenue_share"])))
            w = rng.pareto(1.2, n) + 1
            w = w / w.sum()
            delay = np.maximum(0, rng.normal(c["customer_delay_mean_days"], 5, n)) if kind == "Customer" else np.zeros(n)
            rows.append(pd.DataFrame({
                "counterparty_type": kind, "entity_code": ecode, "currency_code": e["currency"],
                "payment_terms_days": _terms(rng, terms_w, n), "avg_delay_days": delay.round(1), "volume_share": w,
                "volume_share_rc": w * e["revenue_share"],
            }))
    cp = pd.concat(rows, ignore_index=True)
    cp["counterparty_id"] = np.where(cp["counterparty_type"] == "Customer", "CU", "SU") + \
        (cp.groupby("counterparty_type").cumcount() + 1).map("{:04d}".format)
    cp["counterparty_name"] = np.where(cp["counterparty_type"] == "Customer", "Customer ", "Supplier ") + cp["counterparty_id"].str[2:]
    cust = cp["counterparty_type"] == "Customer"
    rank = cp.loc[cust, "volume_share_rc"].rank(ascending=False, method="first")
    cp["key_account_rank"] = pd.array([pd.NA] * len(cp), dtype="Int64")
    cp.loc[cust, "key_account_rank"] = rank.astype(int).values
    cp["is_key_account"] = (cp["key_account_rank"].fillna(10**6) <= c["key_accounts"]).astype(int)
    cp.loc[cp["is_key_account"] == 0, "key_account_rank"] = pd.NA
    return cp[["counterparty_id", "counterparty_name", "counterparty_type", "entity_code", "currency_code",
               "payment_terms_days", "avg_delay_days", "volume_share", "is_key_account", "key_account_rank"]]


def _facilities(cfg, cal: Calendar) -> pd.DataFrame:
    c = cfg["corporate"]
    sp = spot(cfg)
    rows = []
    for fid, f in c["facilities"].items():
        ccy = f["currency"]
        rate = cfg["currencies"][ccy]["base_rate"] + f["rate_spread"]
        amount_rc = f.get("limit_rc", f.get("amount_rc"))
        rows.append({"facility_id": fid, "entity_code": f["entity"], "facility_type": f["type"], "currency_code": ccy,
                     "limit_local": amount_rc / sp[ccy], "interest_rate": rate,
                     "start_date": np.datetime64(str(f.get("start", cal.hist_start)), "D"),
                     "maturity_date": np.datetime64(str(f["maturity"]), "D"), "covenant": f.get("covenant", "")})
    return pd.DataFrame(rows)


def _term_loan_schedule(fac: pd.DataFrame) -> pd.DataFrame:
    """Equal semi-annual principal, quarterly interest on outstanding (day 28 of the month)."""
    out = []
    for _, f in fac[fac["facility_type"] == "TERM"].iterrows():
        start = np.datetime64(f["start_date"], "D")
        mat = np.datetime64(f["maturity_date"], "D")
        months = int((mat.astype("datetime64[M]") - start.astype("datetime64[M]")).astype(int))
        n_inst = months // 6
        q = np.arange(1, months // 3 + 1)
        q_dates = add_months_day(np.full(len(q), start), q * 3, np.full(len(q), 28))
        inst = f["limit_local"] / n_inst
        outstanding_before = f["limit_local"] - inst * np.maximum(0, (q - 1) // 2)
        interest = outstanding_before * f["interest_rate"] / 4
        principal = np.where(q % 2 == 0, inst, 0.0)
        principal[q // 2 > n_inst] = 0.0
        out.append(pd.DataFrame({"facility_id": f["facility_id"], "entity_code": f["entity_code"],
                                 "currency_code": f["currency_code"], "date": q_dates,
                                 "interest": interest, "principal": principal}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["facility_id", "entity_code", "currency_code", "date", "interest", "principal"])


# ------------------------------------------------------------------ invoices
def _invoices(cfg, cal: Calendar, cp: pd.DataFrame, rng) -> pd.DataFrame:
    c = cfg["corporate"]
    sp = spot(cfg)
    first = cal.hist_start - DAY * 150
    days = np.arange(first, cal.as_of + DAY, dtype="datetime64[D]")
    days = days[np.is_busday(days)]
    frames = []
    for ecode, e in c["entities"].items():
        rev = _daily_revenue_local(cfg, e, days, cal.as_of) * 7 / 5      # issue on business days only
        for kind, ratio, avg_rc in (("AR", 1.0, c["avg_ar_invoice_rc"]), ("AP", c["cogs_ratio"], c["avg_ap_invoice_rc"])):
            amt_day = rev * ratio
            lam = amt_day * sp[e["currency"]] / avg_rc
            cnt = np.maximum(rng.poisson(lam), 1)
            day_idx = np.repeat(np.arange(len(days)), cnt)
            w = rng.lognormal(0, 0.9, len(day_idx))
            w = w / np.bincount(day_idx, w)[day_idx]
            amount = amt_day[day_idx] * w
            ctype = "Customer" if kind == "AR" else "Supplier"
            pool = cp[(cp["counterparty_type"] == ctype) & (cp["entity_code"] == ecode)]
            pick = rng.choice(len(pool), len(day_idx), p=pool["volume_share"].values / pool["volume_share"].sum())
            terms = pool["payment_terms_days"].values[pick]
            delay = pool["avg_delay_days"].values[pick]
            inv_date = days[day_idx]
            due = inv_date + DAY * terms
            noise = rng.normal(delay, 4.0) if kind == "AR" else rng.normal(0, 1.5, len(day_idx))
            pay = next_business_day(due + DAY * np.round(noise).astype(int))
            pay = np.maximum(pay, inv_date + DAY)
            exp_pay = next_business_day(due + DAY * np.round(delay).astype(int))
            frames.append(pd.DataFrame({
                "invoice_type": kind, "entity_code": ecode, "counterparty_id": pool["counterparty_id"].values[pick],
                "currency_code": e["currency"], "invoice_date": inv_date, "due_date": due,
                "actual_pay_date": pay, "expected_pay_date": np.maximum(exp_pay, cal.as_of + DAY), "amount_local": amount,
            }))
    inv = pd.concat(frames, ignore_index=True)
    inv["status"] = np.where(inv["actual_pay_date"] <= cal.as_of, "PAID", "OPEN")
    inv.loc[inv["status"] == "OPEN", "actual_pay_date"] = np.datetime64("NaT")
    inv.loc[inv["status"] == "PAID", "expected_pay_date"] = np.datetime64("NaT")
    inv = inv.sort_values(["invoice_date", "entity_code", "invoice_type"], kind="stable").reset_index(drop=True)
    inv["invoice_id"] = np.where(inv["invoice_type"] == "AR", "AR", "AP") + \
        (inv.groupby("invoice_type").cumcount() + 1).map("{:07d}".format)
    inv["amount_rc_at_asof_fx"] = inv["amount_local"] * inv["currency_code"].map(sp)
    return inv[["invoice_id", "invoice_type", "entity_code", "counterparty_id", "currency_code", "invoice_date",
                "due_date", "status", "actual_pay_date", "expected_pay_date", "amount_local", "amount_rc_at_asof_fx"]]


# ------------------------------------------------------------------ calendar flows (actual or forecast)
def _calendar_flows(cfg, ecode, e, first, last, as_of, rng=None, rev_factor=None) -> list[pd.DataFrame]:
    """Payroll, opex, tax, capex, dividend for one entity between first..last (inclusive).
    rng=None -> deterministic expected values (forecast). rev_factor(dates) scales tax with revenue shocks."""
    c = cfg["corporate"]
    ccy = e["currency"]
    annual = c["revenue_rc_annual"] * e["revenue_share"] / spot(cfg)[ccy]

    def growth(d):
        return np.exp(c["revenue_growth_annual"] * (d - as_of).astype("timedelta64[D]").astype("int64") / 365.25)

    out = []

    def add(dates, amounts, cat):
        m = (dates >= first) & (dates <= last)
        if m.any():
            out.append(pd.DataFrame({"date": dates[m], "entity_code": ecode, "category_code": cat,
                                     "currency_code": ccy, "amount_local": amounts[m]}))

    pay = prev_business_day(_monthly_dates(first, last, 25))
    add(pay, -annual * c["payroll_ratio"] / 12 * growth(pay), "OP_PAYROLL")
    opx = next_business_day(_monthly_dates(first, last, 1))
    add(opx, -annual * c["opex_ratio"] / 12 * growth(opx), "OP_OPEX")
    tax = _monthly_dates(first, last, 15)
    tax = next_business_day(tax[np.isin(tax.astype("datetime64[M]").astype(int) % 12, [0, 3, 6, 9])])
    tax_amt = -annual * c["tax_ratio"] / 4 * growth(tax)
    if rev_factor is not None:
        tax_amt = tax_amt * rev_factor(tax)
    add(tax, tax_amt, "OP_TAX")
    cx = next_business_day(_monthly_dates(first, last, 20))
    lump = rng.gamma(2.0, 0.5, len(cx)) if rng is not None else np.ones(len(cx))
    add(cx, -annual * c["capex_ratio"] / 12 * growth(cx) * lump, "INV_CAPEX")
    div = e.get("dividend")
    if div:
        years = np.arange(first.astype("datetime64[Y]").astype(int), last.astype("datetime64[Y]").astype(int) + 1) + 1970
        dd = next_business_day(np.array([np.datetime64(f"{y}-{div['month']:02d}-{div['day']:02d}") for y in years]))
        add(dd, np.full(len(dd), -div["amount_rc"] / spot(cfg)[ccy]), "FIN_DIVIDEND")
    return out


# ------------------------------------------------------------------ history
def simulate_corporate_history(cfg, cal: Calendar, fx: pd.DataFrame, rng) -> CorpState:
    c = cfg["corporate"]
    sp = spot(cfg)
    cp = _counterparties(cfg, rng)
    fac = _facilities(cfg, cal)
    loans = _term_loan_schedule(fac)
    inv = _invoices(cfg, cal, cp, rng)

    ent = pd.DataFrame([{"entity_code": k, "entity_name": v["name"], "currency_code": v["currency"],
                         "min_cash_local": v["min_cash_rc"] / sp[v["currency"]]} for k, v in c["entities"].items()])
    acct = pd.DataFrame({"account_id": "ACC_" + ent["entity_code"], "entity_code": ent["entity_code"],
                         "currency_code": ent["currency_code"], "account_name": "Operating account " + ent["entity_code"],
                         "bank_name": "SimBank (synthetic)"})

    first, last = cal.hist_days[0], cal.as_of
    flows = []
    paid = inv[inv["status"] == "PAID"]
    paid = paid[(paid["actual_pay_date"] > cal.hist_start)]
    flows.append(pd.DataFrame({"date": paid["actual_pay_date"].values, "entity_code": paid["entity_code"].values,
                               "category_code": np.where(paid["invoice_type"] == "AR", "OP_RECEIPTS", "OP_SUPPLIERS"),
                               "currency_code": paid["currency_code"].values,
                               "amount_local": np.where(paid["invoice_type"] == "AR", 1, -1) * paid["amount_local"].values}))
    for ecode, e in c["entities"].items():
        flows += _calendar_flows(cfg, ecode, e, first, last, cal.as_of, rng=rng)
    lh = loans[(loans["date"] >= first) & (loans["date"] <= last)]
    for col, cat in (("interest", "FIN_INTEREST"), ("principal", "FIN_DEBT_REPAY")):
        x = lh[lh[col] > 0]
        flows.append(pd.DataFrame({"date": x["date"].values, "entity_code": x["entity_code"].values, "category_code": cat,
                                   "currency_code": x["currency_code"].values, "amount_local": -x[col].values}))
    base = pd.concat(flows, ignore_index=True)
    base["date"] = base["date"].values.astype("datetime64[D]")

    # daily loop: revolver / overdraft balancing + revolver interest (paid at month-end)
    days = cal.hist_days
    rev_fac = fac[fac["facility_type"].isin(["RCF", "OVERDRAFT"])].set_index("entity_code")
    extra, bal_rows, cash_asof, drawn_asof = [], [], {}, {}
    month_end = np.isin(days, cal.month_ends)
    for _, en in ent.iterrows():
        ecode, ccy = en["entity_code"], en["currency_code"]
        e_cfg = c["entities"][ecode]
        net = base[base["entity_code"] == ecode].groupby("date")["amount_local"].sum()
        net = net.reindex(pd.DatetimeIndex(days), fill_value=0.0).values
        cash = e_cfg["opening_cash_rc"] / sp[ccy]
        minc = en["min_cash_local"]
        f = rev_fac.loc[ecode] if ecode in rev_fac.index else None
        limit = f["limit_local"] if f is not None else 0.0
        r = f["interest_rate"] if f is not None else 0.0
        drawn, accrued = 0.0, 0.0
        for i, d in enumerate(days):
            opening = cash
            day_flow = net[i]
            cash += net[i]
            accrued += drawn * r / 365
            if month_end[i] and accrued > 0:
                cash -= accrued
                day_flow -= accrued
                extra.append((d, ecode, "FIN_INTEREST", ccy, -accrued))
                accrued = 0.0
            if cash < minc and drawn < limit:
                amt = min(minc * 1.2 - cash, limit - drawn)
                drawn += amt
                cash += amt
                day_flow += amt
                extra.append((d, ecode, "FIN_RCF_DRAW", ccy, amt))
            elif cash > minc * c["rcf_target_cash_multiple"] and drawn > 0:
                amt = min(drawn, cash - minc * c["rcf_target_cash_multiple"])
                drawn -= amt
                cash -= amt
                day_flow -= amt
                extra.append((d, ecode, "FIN_RCF_REPAY", ccy, -amt))
            bal_rows.append((d, ecode, ccy, opening, day_flow, cash, drawn, max(limit - drawn, 0.0), minc))
        cash_asof[ecode] = cash
        if f is not None:
            drawn_asof[f["facility_id"]] = drawn

    ex = pd.DataFrame(extra, columns=["date", "entity_code", "category_code", "currency_code", "amount_local"])
    actual = pd.concat([base, ex], ignore_index=True)
    actual = actual.groupby(["date", "entity_code", "category_code", "currency_code"], as_index=False)["amount_local"].sum()
    actual["account_id"] = "ACC_" + actual["entity_code"]
    actual["amount_rc"] = actual["amount_local"] * fx_lookup(fx, actual["date"].values, actual["currency_code"].values)
    actual = actual[FLOW_COLS + ["amount_rc"]].sort_values(["date", "entity_code", "category_code"]).reset_index(drop=True)

    bal = pd.DataFrame(bal_rows, columns=["date", "entity_code", "currency_code", "opening_local", "net_flow_local",
                                          "closing_local", "facility_drawn_local", "undrawn_available_local", "min_cash_local"])
    bal["scenario_key"] = "ACT"
    bal["account_id"] = "ACC_" + bal["entity_code"]
    rate = fx_lookup(fx, bal["date"].values, bal["currency_code"].values)
    bal = _finish_balances(bal, rate)

    # term loans outstanding at as-of
    for _, f in fac[fac["facility_type"] == "TERM"].iterrows():
        paid_p = loans[(loans["facility_id"] == f["facility_id"]) & (loans["date"] <= cal.as_of)]["principal"].sum()
        drawn_asof[f["facility_id"]] = f["limit_local"] - paid_p
    fac["drawn_asof_local"] = fac["facility_id"].map(drawn_asof).fillna(0.0)
    fac["drawn_asof_rc"] = fac["drawn_asof_local"] * fac["currency_code"].map(sp)
    fac["limit_rc"] = fac["limit_local"] * fac["currency_code"].map(sp)
    fac["min_cash_rc"] = fac["entity_code"].map({k: v["min_cash_rc"] for k, v in c["entities"].items()})

    cat = pd.DataFrame(CATEGORIES, columns=["category_code", "category_name", "activity", "direction", "sort_order"])
    return CorpState(cat, cp, acct, fac, ent, inv, actual, bal, loans, cash_asof, drawn_asof)


def _finish_balances(bal: pd.DataFrame, rate: np.ndarray) -> pd.DataFrame:
    bal["headroom_local"] = bal["closing_local"] + bal["undrawn_available_local"] - bal["min_cash_local"]
    bal["closing_rc"] = bal["closing_local"] * rate
    bal["undrawn_available_rc"] = bal["undrawn_available_local"] * rate
    bal["min_cash_rc"] = bal["min_cash_local"] * rate
    bal["headroom_rc"] = bal["headroom_local"] * rate
    return bal[["date", "scenario_key", "entity_code", "account_id", "currency_code", "opening_local", "net_flow_local",
                "closing_local", "facility_drawn_local", "undrawn_available_local", "min_cash_local", "headroom_local",
                "closing_rc", "undrawn_available_rc", "min_cash_rc", "headroom_rc"]]


# ------------------------------------------------------------------ forecast
def forecast_corporate(st: CorpState, cfg, cal: Calendar, drv: dict, scenario: str):
    c = cfg["corporate"]
    sp = spot(cfg)
    H = len(cal.proj_days)
    first, last = cal.proj_days[0], cal.proj_days[-1]
    shock = drv["corp_revenue_shock"]
    dso = int(round(drv["corp_dso_shift_days"]))
    cut = int(round(drv["corp_supplier_terms_cut_days"]))
    n_def = int(round(drv["corp_key_customer_defaults"]))
    cp = st.dim_counterparty
    defaulted = set(cp.loc[cp["key_account_rank"].fillna(10**6) <= n_def, "counterparty_id"])

    def rev_factor(d):
        t = (d - cal.as_of).astype("timedelta64[D]").astype("int64")
        return 1 + shock * np.clip(t / 30, 0, 1)

    flows = []
    # open items
    op = st.invoices[st.invoices["status"] == "OPEN"]
    ar = op[(op["invoice_type"] == "AR") & ~op["counterparty_id"].isin(defaulted)]
    ar_date = next_business_day(np.maximum(ar["expected_pay_date"].values.astype("datetime64[D]") + DAY * dso, first))
    flows.append(pd.DataFrame({"date": ar_date, "entity_code": ar["entity_code"].values, "category_code": "OP_RECEIPTS",
                               "currency_code": ar["currency_code"].values, "amount_local": ar["amount_local"].values}))
    ap = op[op["invoice_type"] == "AP"]
    ap_date = next_business_day(np.maximum(ap["due_date"].values.astype("datetime64[D]") - DAY * cut, first))
    flows.append(pd.DataFrame({"date": ap_date, "entity_code": ap["entity_code"].values, "category_code": "OP_SUPPLIERS",
                               "currency_code": ap["currency_code"].values, "amount_local": -ap["amount_local"].values}))

    # new sales and purchases (expected values), collected/paid per counterparty lag
    days = cal.proj_days
    bdays = days[np.is_busday(days)]
    for ecode, e in c["entities"].items():
        sales = _daily_revenue_local(cfg, e, bdays, cal.as_of) * 7 / 5 * rev_factor(bdays)
        for ctype, ratio, sign, cat in (("Customer", 1.0, 1, "OP_RECEIPTS"), ("Supplier", c["cogs_ratio"], -1, "OP_SUPPLIERS")):
            pool = cp[(cp["counterparty_type"] == ctype) & (cp["entity_code"] == ecode)]
            share = pool["volume_share"].values / pool["volume_share"].sum()
            if ctype == "Customer":
                lag = pool["payment_terms_days"].values + np.round(pool["avg_delay_days"].values).astype(int) + dso
                share = np.where(pool["counterparty_id"].isin(defaulted).values, 0.0, share)
            else:
                lag = np.maximum(pool["payment_terms_days"].values - cut, 0)
            pay = bdays[None, :] + DAY * lag[:, None]
            amt = sign * ratio * sales[None, :] * share[:, None]
            pay = next_business_day(pay.ravel())
            m = pay <= last
            flows.append(pd.DataFrame({"date": pay[m], "entity_code": ecode, "category_code": cat,
                                       "currency_code": e["currency"], "amount_local": amt.ravel()[m]}))
        cal_flows = _calendar_flows(cfg, ecode, e, first, last, cal.as_of, rng=None, rev_factor=rev_factor)
        for f in cal_flows:
            if f["category_code"].iloc[0] == "INV_CAPEX":
                f["amount_local"] *= 1 - drv["corp_capex_deferral"]
            if f["category_code"].iloc[0] == "FIN_DIVIDEND" and drv["corp_dividend_suspended"]:
                continue
            flows.append(f)

    # debt service: term loans + revolver interest on as-of drawn amount
    lf = st.loan_schedule[(st.loan_schedule["date"] >= first) & (st.loan_schedule["date"] <= last)]
    for col, cat in (("interest", "FIN_INTEREST"), ("principal", "FIN_DEBT_REPAY")):
        x = lf[lf[col] > 0]
        flows.append(pd.DataFrame({"date": x["date"].values, "entity_code": x["entity_code"].values, "category_code": cat,
                                   "currency_code": x["currency_code"].values, "amount_local": -x[col].values}))
    fac = st.dim_facility
    for _, f in fac[fac["facility_type"].isin(["RCF", "OVERDRAFT"])].iterrows():
        drawn = st.drawn_asof.get(f["facility_id"], 0.0)
        if drawn > 0:
            me = pd.date_range(first, last, freq="ME").values.astype("datetime64[D]")
            flows.append(pd.DataFrame({"date": me, "entity_code": f["entity_code"], "category_code": "FIN_INTEREST",
                                       "currency_code": f["currency_code"], "amount_local": -drawn * f["interest_rate"] / 12}))

    fc = pd.concat(flows, ignore_index=True)
    fc["date"] = fc["date"].values.astype("datetime64[D]")
    fc = fc[(fc["date"] >= first) & (fc["date"] <= last) & (fc["amount_local"].abs() > 0.005)]
    fc = fc.groupby(["date", "entity_code", "category_code", "currency_code"], as_index=False)["amount_local"].sum()
    fc["account_id"] = "ACC_" + fc["entity_code"]
    fx_s = {k: sp[k] * (1 + drv["fx_shock"].get(k, 0.0)) for k in sp}
    fc["amount_rc"] = fc["amount_local"] * fc["currency_code"].map(fx_s)
    fc.insert(0, "scenario_key", scenario)
    fc = fc[["scenario_key"] + FLOW_COLS + ["amount_rc"]].sort_values(["date", "entity_code", "category_code"])

    # balances
    rows = []
    for _, en in st.entities.iterrows():
        ecode, ccy = en["entity_code"], en["currency_code"]
        net = fc[fc["entity_code"] == ecode].groupby("date")["amount_local"].sum()
        net = net.reindex(pd.DatetimeIndex(days), fill_value=0.0).values
        closing = st.cash_asof[ecode] + np.cumsum(net)
        opening = np.concatenate([[st.cash_asof[ecode]], closing[:-1]])
        rf = fac[(fac["entity_code"] == ecode) & fac["facility_type"].isin(["RCF", "OVERDRAFT"])]
        drawn = sum(st.drawn_asof.get(x, 0.0) for x in rf["facility_id"])
        limit = rf["limit_local"].sum()
        undrawn = max(limit * drv["corp_rcf_availability"] - drawn, 0.0)
        rows.append(pd.DataFrame({"date": days, "entity_code": ecode, "currency_code": ccy, "opening_local": opening,
                                  "net_flow_local": net, "closing_local": closing, "facility_drawn_local": drawn,
                                  "undrawn_available_local": undrawn, "min_cash_local": en["min_cash_local"]}))
    bal = pd.concat(rows, ignore_index=True)
    bal["scenario_key"] = scenario
    bal["account_id"] = "ACC_" + bal["entity_code"]
    bal = _finish_balances(bal, bal["currency_code"].map(fx_s).values)
    return fc.reset_index(drop=True), bal


def corp_survival(bal: pd.DataFrame, H: int) -> dict:
    """First projection day (1-based) on which headroom < 0, per entity and for the group (reporting currency)."""
    out = {}
    for ecode, g in bal.groupby("entity_code"):
        neg = np.flatnonzero(g["headroom_local"].values < 0)
        out[ecode] = int(neg[0] + 1) if len(neg) else None
    grp = bal.groupby("date")["headroom_rc"].sum().values
    neg = np.flatnonzero(grp < 0)
    out["__GROUP__"] = int(neg[0] + 1) if len(neg) else None
    return out
