"""YAML material record loader and property queries."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CATEGORIES = (
    "textiles",
    "laminates_membranes",
    "insulation",
    "foams",
    "composites",
    "metals",
    "polymers",
    "hardware",
    "thread",
    "webbing",
)
CONFIDENCE_LEVELS = ("datasheet", "handbook", "estimate")

_MISSING = object()


class MaterialError(Exception):
    """Base error for the material database."""


class MissingPropertyError(MaterialError, KeyError):
    """Raised by Material.require when a property is absent."""

    def __str__(self) -> str:  # KeyError quotes its arg; keep message readable
        return str(self.args[0]) if self.args else ""


def data_dir() -> Path:
    """Root of the material records (override with HUNTKIT_MATERIALS_DIR)."""
    env = os.environ.get("HUNTKIT_MATERIALS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data" / "materials"


@dataclass(frozen=True)
class Material:
    id: str
    name: str
    category: str
    props: dict[str, Any] = field(default_factory=dict)
    confidence: str = "estimate"
    generic: bool = True
    trade_names: list[str] = field(default_factory=list)
    supplier_examples: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    cost_usd: dict[str, Any] | None = None
    notes: str = ""
    path: Path | None = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.props.get(key, default)

    def require(self, key: str) -> Any:
        if key not in self.props or self.props[key] is None:
            have = ", ".join(sorted(self.props)) or "(none)"
            raise MissingPropertyError(
                f"Material '{self.id}' has no property '{key}'. "
                f"Available: {have}. Add it to {self.path or 'its YAML record'} with a source."
            )
        return self.props[key]

    @classmethod
    def from_dict(cls, d: dict[str, Any], path: Path | None = None) -> "Material":
        return cls(
            id=d["id"],
            name=d.get("name", d["id"]),
            category=d["category"],
            props=dict(d.get("properties") or {}),
            confidence=d.get("confidence", "estimate"),
            generic=bool(d.get("generic", True)),
            trade_names=list(d.get("trade_names") or []),
            supplier_examples=list(d.get("supplier_examples") or []),
            sources=list(d.get("sources") or []),
            cost_usd=d.get("cost_usd"),
            notes=d.get("notes") or "",
            path=path,
        )


def _iter_files(root: Path):
    return sorted(p for p in root.glob("*/*.yaml") if p.is_file())


def read_raw(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise MaterialError(f"{path}: top level must be a mapping")
    return data


@lru_cache(maxsize=4)
def _index(root: str) -> dict[str, Material]:
    out: dict[str, Material] = {}
    for p in _iter_files(Path(root)):
        raw = read_raw(p)
        if "id" not in raw or "category" not in raw:
            raise MaterialError(f"{p}: missing 'id' or 'category'")
        m = Material.from_dict(raw, p)
        if m.id in out:
            raise MaterialError(f"duplicate material id '{m.id}': {out[m.id].path} and {p}")
        out[m.id] = m
    return out


def _db() -> dict[str, Material]:
    return _index(str(data_dir()))


def reload() -> None:
    """Clear the cache (after editing YAML in the same process)."""
    _index.cache_clear()


def load(id: str) -> Material:  # noqa: A002 - contract name
    db = _db()
    try:
        return db[id]
    except KeyError:
        import difflib

        close = difflib.get_close_matches(id, db.keys(), n=3)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        raise MaterialError(f"Unknown material id '{id}'.{hint}") from None


def all_materials() -> list[Material]:
    return sorted(_db().values(), key=lambda m: (m.category, m.id))


# ---- query -----------------------------------------------------------------
_OPS = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
    "contains": lambda a, b: (b.lower() in a.lower()) if isinstance(a, str) and isinstance(b, str) else b in a,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}
_TOP_LEVEL = ("id", "name", "category", "confidence", "generic", "trade_names", "supplier_examples", "notes")


def _split(key: str) -> tuple[str, str]:
    if "__" in key:
        field_, op = key.rsplit("__", 1)
        if op in _OPS:
            return field_, op
    return key, "eq"


def _value(m: Material, field_: str) -> Any:
    if field_ in m.props:
        return m.props[field_]
    if field_ in _TOP_LEVEL:
        return getattr(m, field_)
    return _MISSING


def _match(m: Material, filters: dict[str, Any]) -> bool:
    for key, target in filters.items():
        field_, op = _split(key)
        val = _value(m, field_)
        if val is _MISSING or val is None:
            return False
        try:
            if not _OPS[op](val, target):
                return False
        except TypeError:
            return False
    return True


def query(category: str | None = None, **filters: Any) -> list[Material]:
    """Filter materials. Suffixes: __lt __lte __gt __gte __in __contains (also __eq __ne).

    Fields are looked up in ``props`` first, then top-level attributes
    (confidence, generic, trade_names, ...). Records lacking a filtered field are excluded.
    """
    if category is not None and category not in CATEGORIES:
        raise MaterialError(f"Unknown category '{category}'. Valid: {', '.join(CATEGORIES)}")
    return [
        m for m in all_materials()
        if (category is None or m.category == category) and _match(m, filters)
    ]
