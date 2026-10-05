"""Profile CSV / Excel files to support Power BI data modeling.

Usage:
    python profile_data.py <file-or-folder> [<file-or-folder> ...] [--out report.md] [--max-rows N]

For every table (CSV file or Excel sheet) reports: row count, columns with inferred type,
null %, distinct count, min/max, sample values, likely role (key / foreign key / date /
measure / attribute), candidate keys, a fact-vs-dimension guess, and cross-table
foreign-key candidates (column values contained in another table's unique key).

Requires pandas. Excel additionally requires openpyxl (pip install openpyxl).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas")

KEY_NAME = re.compile(r"(key|id|code|no|number|nbr|num)$", re.I)
DATE_NAME = re.compile(r"(date|dt|day|month|period|time)", re.I)
MONEY_NAME = re.compile(r"(amount|amt|balance|bal|value|revenue|cost|price|principal|interest|provision|ecl|qty|quantity)", re.I)


def load_tables(paths: list[str], max_rows: int | None) -> dict[str, pd.DataFrame]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files += sorted(f for f in p.rglob("*") if f.suffix.lower() in {".csv", ".txt", ".xlsx", ".xlsm", ".xls"})
        elif p.exists():
            files.append(p)
        else:
            print(f"WARNING: {p} not found", file=sys.stderr)

    tables: dict[str, pd.DataFrame] = {}
    for f in files:
        if f.name.startswith("~$"):
            continue
        if f.suffix.lower() in {".csv", ".txt"}:
            df = read_csv(f, max_rows)
            if df is not None:
                tables[f.stem] = df
        else:
            try:
                sheets = pd.read_excel(f, sheet_name=None, nrows=max_rows)
            except ImportError:
                sys.exit("Reading Excel needs openpyxl: pip install openpyxl")
            for sheet, df in sheets.items():
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if not df.empty:
                    tables[f"{f.stem}[{sheet}]"] = df
    return tables


def read_csv(f: Path, max_rows: int | None) -> pd.DataFrame | None:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(f, sep=None, engine="python", encoding=enc, nrows=max_rows)
        except UnicodeDecodeError:
            continue
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: cannot read {f}: {e}", file=sys.stderr)
            return None
    return None


def try_parse_dates(s: pd.Series) -> pd.Series | None:
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    if s.dtype != object:
        # yyyymmdd integer keys
        if pd.api.types.is_integer_dtype(s) and s.dropna().between(19000101, 21001231).all() and len(s.dropna()):
            parsed = pd.to_datetime(s.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
            return parsed if parsed.notna().mean() > 0.95 else None
        return None
    sample = s.dropna().astype(str).head(500)
    if sample.empty or not sample.str.contains(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}").mean() > 0.9:
        return None
    parsed = pd.to_datetime(s, errors="coerce", format="mixed")
    return parsed if parsed.notna().sum() >= 0.95 * s.notna().sum() else None


def pbi_type(s: pd.Series, is_date: bool) -> str:
    if is_date:
        return "dateTime"
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_integer_dtype(s):
        return "int64"
    if pd.api.types.is_float_dtype(s):
        nonnull = s.dropna()
        if len(nonnull) and (nonnull == nonnull.round(0)).all():
            return "int64 (stored as float, has nulls?)"
        return "decimal" if MONEY_NAME.search(s.name or "") else "double"
    return "string"


MONTHS = re.compile(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*$|^(m|p)(0?[1-9]|1[0-2])$", re.I)


def profile_table(name: str, df: pd.DataFrame) -> dict:
    n = len(df)
    cols = []
    month_cols = {str(c) for c in df.columns if MONTHS.match(str(c).strip())}
    wide = len(month_cols) >= 3
    for c in df.columns:
        s = df[c]
        parsed = try_parse_dates(s)
        is_date = parsed is not None
        nn = s.notna().sum()
        distinct = s.nunique(dropna=True)
        numeric = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        unique = n > 0 and distinct == n and nn == n

        if wide and str(c) in month_cols:
            role = "measure (wide month column → unpivot)"
        elif is_date:
            role = "date"
        elif unique and KEY_NAME.search(str(c)):
            role = "KEY (unique)"
        elif KEY_NAME.search(str(c)):
            role = "foreign key?"
        elif numeric and (MONEY_NAME.search(str(c)) or (distinct > 20 and pd.api.types.is_float_dtype(s))):
            role = "measure"
        else:
            role = "attribute"

        src = parsed if is_date else s
        if is_date or numeric:
            mn, mx = src.min(), src.max()
            rng = f"{fmt(mn)} … {fmt(mx)}"
        else:
            rng = ""
        samples = ", ".join(map(lambda v: str(v)[:25], s.dropna().unique()[:4]))
        cols.append(dict(
            name=str(c), type=pbi_type(s, is_date), null_pct=0 if n == 0 else 100 * (1 - nn / n),
            distinct=distinct, range=rng, samples=samples, role=role, unique=unique,
        ))

    keys = [c["name"] for c in cols if c["role"] == "KEY (unique)"]
    if not keys:  # fall back to any unique non-measure column (e.g. a unique name/code)
        keys = [c["name"] for c in cols if c["unique"] and not c["role"].startswith("measure")]
    n_measures = sum(c["role"].startswith("measure") for c in cols)
    n_fk = sum(c["role"] in ("foreign key?", "date") for c in cols)
    if wide:
        kind = "FACT, wide layout (unpivot month columns to long in Power Query)"
    elif n_measures >= 1 and n_fk >= 2:
        kind = "FACT (has measures + several keys/dates)"
    elif keys and n_measures == 0:
        kind = "DIMENSION (unique key, descriptive columns)"
    elif keys:
        kind = "DIMENSION or small fact (check)"
    else:
        kind = "FACT or unclear grain (no single-column key)"
    return dict(name=name, rows=n, cols=cols, keys=keys, kind=kind)


def fmt(v) -> str:
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


def fk_candidates(tables: dict[str, pd.DataFrame], profiles: dict[str, dict]) -> list[str]:
    out = []
    for dim_name, dim in profiles.items():
        for key in dim["keys"]:
            key_vals = set(tables[dim_name][key].dropna().astype(str).str.strip())
            if len(key_vals) < 2:
                continue
            for fact_name, fact in profiles.items():
                if fact_name == dim_name:
                    continue
                for c in fact["cols"]:
                    if c["unique"] or c["role"].startswith("measure"):
                        continue
                    vals = tables[fact_name][c["name"]].dropna().astype(str).str.strip()
                    if vals.empty:
                        continue
                    distinct = set(vals.unique())
                    hit = len(distinct & key_vals) / len(distinct)
                    same_name = norm(c["name"]) == norm(key)
                    if hit >= 0.9 or (same_name and hit >= 0.5):
                        orphans = len(distinct - key_vals)
                        out.append(
                            f"| {fact_name}[{c['name']}] | {dim_name}[{key}] | {hit:.0%} | {orphans} |"
                            + (" same name |" if same_name else " |")
                        )
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def render(profiles: dict[str, dict], fks: list[str]) -> str:
    lines = ["# Data profile", ""]
    lines += ["| Table | Rows | Columns | Candidate key(s) | Guess |", "|---|---|---|---|---|"]
    for p in profiles.values():
        lines.append(f"| {p['name']} | {p['rows']:,} | {len(p['cols'])} | {', '.join(p['keys']) or '—'} | {p['kind']} |")
    lines.append("")
    for p in profiles.values():
        lines += [f"## {p['name']}", f"Rows: {p['rows']:,} · Guess: **{p['kind']}**", ""]
        lines += ["| Column | PBI type | Role | Null % | Distinct | Range | Samples |", "|---|---|---|---|---|---|---|"]
        for c in p["cols"]:
            lines.append(
                f"| {c['name']} | {c['type']} | {c['role']} | {c['null_pct']:.1f} | {c['distinct']:,} | {c['range']} | {c['samples']} |"
            )
        lines.append("")
    lines += ["## Foreign-key candidates", ""]
    if fks:
        lines += ["| Fact column | → Dimension key | Value match | Orphan values | Note |", "|---|---|---|---|---|", *fks]
    else:
        lines.append("_None detected._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", help="write markdown to this file instead of stdout")
    ap.add_argument("--max-rows", type=int, default=None, help="read at most N rows per table")
    args = ap.parse_args()

    tables = load_tables(args.paths, args.max_rows)
    if not tables:
        sys.exit("No CSV/Excel tables found.")
    profiles = {name: profile_table(name, df) for name, df in tables.items()}
    md = render(profiles, fk_candidates(tables, profiles))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Profile written to {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(md)


if __name__ == "__main__":
    main()
