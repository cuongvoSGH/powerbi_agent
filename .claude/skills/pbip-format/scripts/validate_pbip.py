"""Validate a Power BI Project (TMDL semantic model + PBIR report) after edits.

Usage:
    python validate_pbip.py <project-root>

Checks:
  * every *.json / *.pbir / *.pbism parses
  * every tables/*.tmdl is listed with `ref table` in model.tmdl (and vice versa)
  * TMDL lines are tab-indented (no leading spaces outside expressions)
  * lineageTags are unique
  * relationships point at existing table columns
  * visual / filter field bindings (Entity + Property) exist in the model
  * pages.json pageOrder matches page folders; page/visual `name` equals folder name

Exit code 1 if any ERROR was found. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

NAME = r"'(?:[^']|'')*'|[^\s='.]+"
OBJ_RE = re.compile(rf"^\t(column|measure|hierarchy)\s+({NAME})")
CALC_ITEM_RE = re.compile(rf"^\t\tcalculationItem\s+({NAME})")
TABLE_RE = re.compile(rf"^table\s+({NAME})")
REF_TABLE_RE = re.compile(rf"^ref table\s+({NAME})")
LINEAGE_RE = re.compile(r"^\s*lineageTag:\s*(\S+)")
REL_COL_RE = re.compile(rf"^\s*(fromColumn|toColumn):\s*({NAME})\.({NAME}|.+)$")

errors: list[str] = []
warnings: list[str] = []


def unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


class Model:
    def __init__(self, root: Path):
        self.root = root
        self.columns: dict[str, set[str]] = defaultdict(set)
        self.measures: dict[str, set[str]] = defaultdict(set)
        self.hierarchies: dict[str, set[str]] = defaultdict(set)
        self.tables: set[str] = set()
        self.lineage: dict[str, list[str]] = defaultdict(list)

    def all_measures(self) -> set[str]:
        return {m for ms in self.measures.values() for m in ms}


def parse_model(sm_dir: Path) -> Model:
    model = Model(sm_dir)
    definition = sm_dir / "definition"
    tables_dir = definition / "tables"
    file_tables: dict[str, Path] = {}

    for tmdl in sorted(definition.rglob("*.tmdl")):
        lines = tmdl.read_text(encoding="utf-8-sig").splitlines()
        current = None
        for i, line in enumerate(lines, 1):
            loc = f"{tmdl.relative_to(sm_dir.parent)}:{i}"
            m = LINEAGE_RE.match(line)
            if m:
                model.lineage[m.group(1)].append(loc)
            if line.startswith(" ") and line.strip():
                warnings.append(f"{loc}: line starts with spaces; TMDL indentation must use tabs")
            if tmdl.parent == tables_dir:
                m = TABLE_RE.match(line)
                if m:
                    current = unquote(m.group(1))
                    model.tables.add(current)
                    file_tables[current] = tmdl
                    continue
                if current is None:
                    continue
                m = OBJ_RE.match(line)
                if m:
                    kind, name = m.group(1), unquote(m.group(2))
                    target = {"column": model.columns, "measure": model.measures, "hierarchy": model.hierarchies}[kind]
                    if name in target[current]:
                        errors.append(f"{loc}: duplicate {kind} '{name}' in table '{current}'")
                    target[current].add(name)
                    continue
                m = CALC_ITEM_RE.match(line)
                if m:
                    continue

    # model.tmdl refs
    model_tmdl = definition / "model.tmdl"
    if model_tmdl.exists():
        refs = {
            unquote(m.group(1))
            for line in model_tmdl.read_text(encoding="utf-8-sig").splitlines()
            if (m := REF_TABLE_RE.match(line))
        }
        for t in sorted(model.tables - refs):
            errors.append(f"model.tmdl: table '{t}' ({file_tables[t].name}) is missing `ref table` line")
        for t in sorted(refs - model.tables):
            errors.append(f"model.tmdl: `ref table {t}` has no matching tables/*.tmdl file")
    else:
        errors.append(f"{definition}: model.tmdl not found")

    # Measure names must be unique across the whole model.
    seen: dict[str, str] = {}
    for table, ms in model.measures.items():
        for mname in ms:
            if mname in seen:
                errors.append(f"measure '{mname}' defined in both '{seen[mname]}' and '{table}'")
            seen[mname] = table

    for tag, locs in model.lineage.items():
        if len(locs) > 1:
            errors.append(f"duplicate lineageTag {tag} at: {', '.join(locs)}")

    # relationships
    rel = definition / "relationships.tmdl"
    if rel.exists():
        for i, line in enumerate(rel.read_text(encoding="utf-8-sig").splitlines(), 1):
            m = REL_COL_RE.match(line)
            if not m:
                continue
            t, c = unquote(m.group(2)), unquote(m.group(3))
            if t not in model.tables:
                errors.append(f"relationships.tmdl:{i}: unknown table '{t}'")
            elif c not in model.columns[t]:
                errors.append(f"relationships.tmdl:{i}: unknown column '{t}'[{c}]")
    return model


def iter_field_refs(node, path=""):
    """Yield (kind, entity, property_or_level, extra) for every field ref with an explicit Entity."""
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            ref = node.get(kind)
            if isinstance(ref, dict) and "Property" in ref:
                entity = ref.get("Expression", {}).get("SourceRef", {}).get("Entity")
                if entity:
                    yield kind, entity, ref["Property"], None
        hl = node.get("HierarchyLevel")
        if isinstance(hl, dict):
            h = hl.get("Expression", {}).get("Hierarchy", {})
            entity = h.get("Expression", {}).get("SourceRef", {}).get("Entity")
            if entity:
                yield "Hierarchy", entity, h.get("Hierarchy"), hl.get("Level")
        for v in node.values():
            yield from iter_field_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_field_refs(v)


def load_json(path: Path, base: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        errors.append(f"{path.relative_to(base)}: invalid JSON ({e})")
        return None


def check_report(rep_dir: Path, models: dict[str, Model], base: Path):
    pbir = rep_dir / "definition.pbir"
    model = None
    if pbir.exists():
        data = load_json(pbir, base)
        ref_path = ((data or {}).get("datasetReference", {}).get("byPath") or {}).get("path")
        if ref_path:
            target = (rep_dir / ref_path).resolve()
            model = models.get(str(target))
            if model is None:
                warnings.append(f"{pbir.relative_to(base)}: semantic model '{ref_path}' not found locally; field checks skipped")
        else:
            warnings.append(f"{pbir.relative_to(base)}: not bound byPath (byConnection?); field checks skipped")
    if model is None and len(models) == 1 and not pbir.exists():
        model = next(iter(models.values()))

    definition = rep_dir / "definition"
    if not definition.exists():
        warnings.append(f"{rep_dir.name}: no definition/ folder (report not saved in PBIR format?)")
        return

    for f in definition.rglob("*.json"):
        load_json(f, base)

    pages_dir = definition / "pages"
    pages_json = pages_dir / "pages.json"
    folders = {p.name for p in pages_dir.iterdir() if p.is_dir()} if pages_dir.exists() else set()
    if pages_json.exists():
        meta = load_json(pages_json, base) or {}
        order = meta.get("pageOrder", [])
        for p in order:
            if p not in folders:
                errors.append(f"pages.json: pageOrder lists '{p}' but folder pages/{p} is missing")
        for p in folders - set(order):
            errors.append(f"pages.json: page folder '{p}' is not in pageOrder")
        active = meta.get("activePageName")
        if active and active not in folders:
            errors.append(f"pages.json: activePageName '{active}' does not exist")

    for page in sorted(folders):
        pj = pages_dir / page / "page.json"
        pdata = load_json(pj, base) if pj.exists() else None
        if pdata is None:
            if not pj.exists():
                errors.append(f"pages/{page}: page.json missing")
            continue
        if pdata.get("name") != page:
            errors.append(f"pages/{page}/page.json: name '{pdata.get('name')}' != folder name")
        check_fields(pdata, pj, model, base)
        vdir = pages_dir / page / "visuals"
        if not vdir.exists():
            continue
        for v in sorted(p for p in vdir.iterdir() if p.is_dir()):
            vj = v / "visual.json"
            if not vj.exists():
                errors.append(f"{v.relative_to(base)}: visual.json missing")
                continue
            vdata = load_json(vj, base)
            if vdata is None:
                continue
            if vdata.get("name") != v.name:
                errors.append(f"{vj.relative_to(base)}: name '{vdata.get('name')}' != folder name")
            check_fields(vdata, vj, model, base)


def check_fields(data, path: Path, model: Model | None, base: Path):
    if model is None:
        return
    rel = path.relative_to(base)
    for kind, entity, prop, level in iter_field_refs(data):
        if entity not in model.tables:
            errors.append(f"{rel}: unknown table '{entity}'")
        elif kind == "Column" and prop not in model.columns[entity]:
            hint = " (it is a measure: use Measure, not Column)" if prop in model.measures[entity] else ""
            errors.append(f"{rel}: unknown column '{entity}'[{prop}]{hint}")
        elif kind == "Measure" and prop not in model.measures[entity]:
            hint = ""
            if prop in model.columns[entity]:
                hint = " (it is a column: use Column, not Measure)"
            elif prop in model.all_measures():
                hint = " (measure exists but in a different table)"
            errors.append(f"{rel}: unknown measure '{entity}'[{prop}]{hint}")
        elif kind == "Hierarchy" and prop not in model.hierarchies[entity]:
            errors.append(f"{rel}: unknown hierarchy '{entity}'.'{prop}'")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    sm_dirs = [p for p in root.rglob("*.SemanticModel") if p.is_dir()]
    rep_dirs = [p for p in root.rglob("*.Report") if p.is_dir()]
    if not sm_dirs and not rep_dirs:
        print(f"No *.SemanticModel or *.Report folders found under {root}")
        return 1

    models: dict[str, Model] = {}
    for sm in sm_dirs:
        for f in list(sm.glob("*.pbism")):
            load_json(f, root)
        models[str(sm.resolve())] = parse_model(sm)
    for rep in rep_dirs:
        check_report(rep, models, root)

    for sm, m in models.items():
        n_cols = sum(len(c) for c in m.columns.values())
        n_meas = sum(len(c) for c in m.measures.values())
        print(f"Model {Path(sm).name}: {len(m.tables)} tables, {n_cols} columns, {n_meas} measures")
    for w in warnings:
        print(f"WARNING  {w}")
    for e in errors:
        print(f"ERROR    {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
