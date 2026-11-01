"""Schema validation for material YAML records (contract §1)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .loader import CATEGORIES, CONFIDENCE_LEVELS, MaterialError, data_dir, read_raw

REQUIRED_FIELDS = ("id", "name", "category", "generic", "properties", "confidence", "sources")
OPTIONAL_FIELDS = ("trade_names", "supplier_examples", "cost_usd", "notes")
COST_PER = ("kg", "m", "m2", "unit", "yd", "lb", "g", "pair", "set", "roll")

# Numeric property keys must end in one of these unit suffixes ...
UNIT_SUFFIXES = (
    "_kg_m3", "_g_cm3", "_mpa", "_gpa", "_kpa", "_pa",
    "_n", "_n_50mm", "_n_25mm", "_n_cm", "_kn",
    "_g", "_kg", "_g_m", "_g_unit", "_gsm", "_g_m2", "_oz_yd2",
    "_mm", "_um", "_m", "_cm3_g", "_in3_oz",
    "_pct", "_c", "_k", "_j_m", "_j", "_s",
    "_g_m2_24h", "_m2pa_w", "_m2k_w", "_clo", "_cfm", "_l_m2_s",
    "_cycles", "_hours", "_1to5", "_1to10", "_shore_a", "_shore_d",
    "_per_10cm", "_spi", "_ppm_c", "_w_mk", "_mm_s", "_n_mm", "_shore_c", "_asker_c", "_minutes",
)
# ... or be one of these dimensionless/conventional keys.
DIMENSIONLESS = {
    "poisson", "nu12", "nu23", "denier", "tex", "fiber_volume_fraction",
    "zipper_size", "fill_power", "ply_count", "upf", "aatcc_spray_rating",
    "yarn_count", "gauge", "layers", "coefficient_of_friction",
    "abrasion_cycles_martindale",  # contract key (unit is cycles)
}
ID_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
# Property keys are snake_case; the contract's composite keys (E1_mpa, Xt_mpa, G12_mpa) may
# capitalize the leading symbol.
PROP_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(_[a-z0-9]+)*$")


def _numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_numeric_key(key: str, val: Any, errs: list[str]) -> None:
    if key in DIMENSIONLESS or key.endswith(UNIT_SUFFIXES):
        return
    errs.append(f"numeric property '{key}'={val!r} has no unit suffix (e.g. _mpa, _gsm, _n)")


def validate_record(raw: dict[str, Any], path: Path | None = None) -> list[str]:
    """Return a list of human-readable problems (empty list = valid)."""
    errs: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in raw:
            errs.append(f"missing required field '{f}'")
    unknown = set(raw) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        errs.append(f"unknown top-level fields: {sorted(unknown)}")

    mid = raw.get("id")
    if not isinstance(mid, str) or not ID_RE.match(mid or ""):
        errs.append(f"id {mid!r} must be snake_case")
    if path is not None:
        if mid != path.stem:
            errs.append(f"id '{mid}' != filename stem '{path.stem}'")
        if raw.get("category") != path.parent.name:
            errs.append(f"category '{raw.get('category')}' != folder '{path.parent.name}'")
    if raw.get("category") not in CATEGORIES:
        errs.append(f"invalid category {raw.get('category')!r}; valid: {CATEGORIES}")
    if raw.get("confidence") not in CONFIDENCE_LEVELS:
        errs.append(f"confidence {raw.get('confidence')!r} not in {CONFIDENCE_LEVELS}")
    if "generic" in raw and not isinstance(raw["generic"], bool):
        errs.append("generic must be true/false")
    if not isinstance(raw.get("name"), str) or not raw.get("name"):
        errs.append("name must be a non-empty string")

    src = raw.get("sources")
    if not isinstance(src, list) or not src or not all(isinstance(s, str) and s for s in src):
        errs.append("sources must be a non-empty list of strings")
    for lf in ("trade_names", "supplier_examples"):
        if lf in raw and not isinstance(raw[lf], list):
            errs.append(f"{lf} must be a list")

    props = raw.get("properties")
    if not isinstance(props, dict) or not props:
        errs.append("properties must be a non-empty mapping")
    else:
        for k, v in props.items():
            if not isinstance(k, str) or not PROP_KEY_RE.match(k):
                errs.append(f"property key {k!r} must be snake_case (leading symbol may be capitalized)")
                continue
            if _numeric(v):
                _check_numeric_key(k, v, errs)
                if v < 0 and not k.endswith(("_c", "_ppm_c")):
                    errs.append(f"property '{k}' is negative ({v})")
            elif isinstance(v, (list, tuple)) and v and all(_numeric(x) for x in v):
                _check_numeric_key(k, v, errs)  # ranges like [min, max]
            elif v is None:
                errs.append(f"property '{k}' is null; omit it instead")

    cost = raw.get("cost_usd")
    if cost is not None:
        if not isinstance(cost, dict) or not _numeric(cost.get("value")) or cost.get("per") not in COST_PER:
            errs.append(f"cost_usd must be {{value: number, per: one of {COST_PER}}}, got {cost!r}")
    return errs


def validate_all(root: Path | None = None) -> dict[Path, list[str]]:
    """Validate every YAML under root. Returns {path: [errors]} for failing files only."""
    root = Path(root) if root else data_dir()
    problems: dict[Path, list[str]] = {}
    seen: dict[str, Path] = {}
    files = sorted(root.glob("**/*.yaml")) + sorted(root.glob("**/*.yml"))
    for p in files:
        try:
            raw = read_raw(p)
        except (MaterialError, Exception) as exc:  # yaml errors
            problems[p] = [f"cannot parse: {exc}"]
            continue
        errs = validate_record(raw, p)
        if p.suffix == ".yml":
            errs.append("use the .yaml extension")
        if p.parent.parent != root:
            errs.append("records must live at data/materials/<category>/<id>.yaml")
        mid = raw.get("id")
        if mid in seen:
            errs.append(f"duplicate id also in {seen[mid]}")
        elif isinstance(mid, str):
            seen[mid] = p
        if errs:
            problems[p] = errs
    return problems
