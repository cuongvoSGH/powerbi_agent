"""Shared helpers: config, calendar, time buckets, FX, CSV output."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

DAY = np.timedelta64(1, "D")

# (key, label, from_day, to_day) - days counted from the reference date (day 1 = next day).
# Default ladder; a config `time_buckets:` section replaces it (e.g. the EBA ALMM C 66.01 ladder).
_DEFAULT_BUCKETS = [
    ("B01", "O/N", 1, 1),
    ("B02", "2-7D", 2, 7),
    ("B03", "8-30D", 8, 30),
    ("B04", "1-3M", 31, 90),
    ("B05", "3-6M", 91, 180),
    ("B06", "6-12M", 181, 365),
    ("B07", "1-2Y", 366, 730),
    ("B08", "2-5Y", 731, 1825),
    ("B09", ">5Y", 1826, 99999),
]
_STATE = {"buckets": list(_DEFAULT_BUCKETS), "nm_key": "B10"}


def configure_buckets(cfg) -> None:
    tb = cfg.get("time_buckets") or {}
    if tb.get("buckets"):
        bk = [(str(k), str(lbl), int(a), int(b)) for k, lbl, a, b in tb["buckets"]]
        if any(bk[i][3] >= bk[i + 1][3] for i in range(len(bk) - 1)) or bk[-1][3] < 36500:
            raise SystemExit("time_buckets.buckets must have increasing to_day and end with an open bucket (to_day >= 36500)")
        _STATE["buckets"] = bk
    else:
        _STATE["buckets"] = list(_DEFAULT_BUCKETS)
    _STATE["nm_key"] = tb.get("non_maturity_key", "B10")


def buckets() -> list[tuple[str, str, int, int]]:
    return _STATE["buckets"]


def nm_bucket_key() -> str:
    """Bucket key for items without contractual maturity (equity, fixed assets, other)."""
    return _STATE["nm_key"]


def bucket_of(days) -> np.ndarray:
    """Map residual days (>=1; values <1 go to the first bucket) to bucket keys."""
    upper = np.array([b[3] for b in _STATE["buckets"]])
    keys = np.array([b[0] for b in _STATE["buckets"]])
    d = np.maximum(np.asarray(days, dtype="int64"), 1)
    return keys[np.searchsorted(upper, d, side="left")]


def nsfr_band(days) -> np.ndarray:
    d = np.asarray(days, dtype="float64")
    return np.where(d < 183, "lt6m", np.where(d <= 365, "m6_1y", "ge1y"))


# ------------------------------------------------------------------ config
def deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(path: Path, size: str | None) -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    size = size or cfg.get("meta", {}).get("size", "medium")
    preset = cfg.get("sizes", {}).get(size)
    if preset is None:
        raise SystemExit(f"Unknown size '{size}'. Options: {list(cfg.get('sizes', {}))}")
    cfg["meta"]["size"] = size
    cfg["meta"]["history_months"] = preset.get("history_months", cfg["meta"]["history_months"])
    cfg["_size"] = preset
    configure_buckets(cfg)
    return cfg


def projection_scenarios(cfg) -> list[str]:
    """Scenarios with a forward projection, in config order (everything except type 'actual')."""
    return [k for k, v in cfg["scenarios"].items() if v.get("type") != "actual"]


@dataclass
class Calendar:
    as_of: np.datetime64
    history_months: int
    horizon_days: int
    month_ends: np.ndarray = field(init=False)   # history month-ends incl. as-of (len = history_months + 1)
    hist_days: np.ndarray = field(init=False)    # days in (month_ends[0], as_of]
    proj_days: np.ndarray = field(init=False)    # as_of + 1 .. as_of + horizon

    def __post_init__(self):
        ts = pd.Timestamp(self.as_of)
        if not ts.is_month_end:
            raise SystemExit(f"meta.as_of_date {ts.date()} must be a month-end")
        me = pd.date_range(end=ts, periods=self.history_months + 1, freq="ME")
        self.month_ends = me.values.astype("datetime64[D]")
        self.hist_days = np.arange(self.month_ends[0] + DAY, self.as_of + DAY, dtype="datetime64[D]")
        self.proj_days = np.arange(self.as_of + DAY, self.as_of + DAY * (self.horizon_days + 1), dtype="datetime64[D]")

    @property
    def hist_start(self) -> np.datetime64:
        return self.month_ends[0]


def make_calendar(cfg) -> Calendar:
    m = cfg["meta"]
    return Calendar(np.datetime64(str(m["as_of_date"]), "D"), int(m["history_months"]), int(m["horizon_days"]))


# ------------------------------------------------------------------ dates
def months_index(d: np.ndarray) -> np.ndarray:
    return d.astype("datetime64[M]").astype("int64")


def day_of_month(d: np.ndarray) -> np.ndarray:
    return (d - d.astype("datetime64[M]").astype("datetime64[D]")).astype("int64") + 1


def add_months_day(start: np.ndarray, k: np.ndarray, pay_day: np.ndarray) -> np.ndarray:
    """Date in month (start + k) on day pay_day (pay_day <= 28)."""
    m = start.astype("datetime64[M]") + k.astype("int64")
    return m.astype("datetime64[D]") + (pay_day.astype("int64") - 1)


def next_business_day(d: np.ndarray) -> np.ndarray:
    d = np.asarray(d, dtype="datetime64[D]")
    return np.busday_offset(d, 0, roll="forward")


def prev_business_day(d: np.ndarray) -> np.ndarray:
    d = np.asarray(d, dtype="datetime64[D]")
    return np.busday_offset(d, 0, roll="backward")


def date_str(d) -> np.ndarray:
    return np.datetime_as_string(np.asarray(d, dtype="datetime64[D]"), unit="D")


# ------------------------------------------------------------------ FX
def fx_history(cfg, cal: Calendar, rng: np.random.Generator) -> pd.DataFrame:
    """Daily rate_to_rc (value in reporting currency) for history days + as-of, GBM anchored to the as-of rate."""
    days = np.concatenate([[cal.hist_start], cal.hist_days])
    n = len(days)
    rows = []
    for code, c in cfg["currencies"].items():
        if c["annual_vol"] == 0 and c["annual_drift"] == 0:
            path = np.full(n, float(c["rate_to_rc"]))
        else:
            dt = 1 / 365.25
            steps = rng.normal((c["annual_drift"] - 0.5 * c["annual_vol"] ** 2) * dt, c["annual_vol"] * np.sqrt(dt), n - 1)
            logp = np.concatenate([[0.0], np.cumsum(steps)])
            logp += np.log(c["rate_to_rc"]) - logp[-1]
            path = np.exp(logp)
        rows.append(pd.DataFrame({"date": days, "currency_code": code, "rate_to_rc": path}))
    return pd.concat(rows, ignore_index=True)


def fx_lookup(fx: pd.DataFrame, dates: np.ndarray, ccy: np.ndarray) -> np.ndarray:
    """Vectorised rate lookup for (date, currency) pairs present in fx."""
    key = pd.MultiIndex.from_arrays([fx["date"].values, fx["currency_code"].values])
    s = pd.Series(fx["rate_to_rc"].values, index=key)
    idx = pd.MultiIndex.from_arrays([np.asarray(dates, dtype="datetime64[ns]"), np.asarray(ccy)])
    out = s.reindex(idx).values
    if np.isnan(out).any():
        raise ValueError("FX rate missing for some (date, currency) pairs")
    return out


def spot(cfg) -> dict[str, float]:
    """Value of 1 unit of each currency in the reporting currency at the as-of date."""
    return {k: float(v["rate_to_rc"]) for k, v in cfg["currencies"].items()}


def reporting_currency(cfg) -> str:
    rc = cfg["meta"].get("reporting_currency", "USD")
    if rc not in cfg["currencies"] or abs(float(cfg["currencies"][rc]["rate_to_rc"]) - 1.0) > 1e-12:
        raise SystemExit(f"reporting currency {rc} must be listed in currencies with rate_to_rc: 1.0")
    return rc


# ------------------------------------------------------------------ output
KEEP_PRECISION = {"rate_to_rc", "value", "price", "survival_days"}
KEEP_SUFFIXES = ("_rate", "_pct", "_factor", "haircut", "_share", "_multiplier", "_ratio")


class Writer:
    def __init__(self, out: Path):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.counts: dict[str, int] = {}

    def write(self, name: str, df: pd.DataFrame):
        df = df.copy()
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c].dtype):
                df[c] = date_str(df[c].values)
            elif df[c].dtype.kind == "f":
                # amounts -> 2 dp; rates, factors, prices and ratios keep precision
                if c in KEEP_PRECISION or c.endswith(KEEP_SUFFIXES):
                    df[c] = df[c].round(10) if c != "rate_to_rc" else df[c]
                else:
                    df[c] = df[c].round(2)
        df.to_csv(self.out / f"{name}.csv", index=False, lineterminator="\n")
        self.counts[name] = len(df)
