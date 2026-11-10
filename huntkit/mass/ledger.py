"""The one mass ledger for the 5200 pack (BL-001, pack-designer, 2026-11-10).

Every later ticket reads pack masses from here (docs/backlog/RULES.md rule 5). This module types no masses and no
totals: it calls the existing sources and only sorts their rows into fixed systems.

Sources (called, never copied)
------------------------------
* ``weight_pass_corrie.breakdown(size)``: the weight-pass part list (geometry.yaml shared rows, corrie.build() pieces,
  zips and hardware, corrie.bag_pockets(), belt B BOM, hip_layout(), holster(), hipbelt_structural_results.json,
  pad_seat()). The weight pass books CORRIE B.1; this ledger runs the same part list on spec B.2 (``_wp_spec``) and adds
  ``corrie.b2_rows()`` (A-2, B-10, G-1, G-2), the rows B.2 books on top of the B.1 structure.
* ``corrie.weight_table(size, spec="B.2")``: the total every config is reconciled to. The one balancing row
  ("booking reconciliation", system ``misc``) is the difference between SPINE's geometry.yaml body rows and the
  333.2 g cut-set body metric that weight_table subtracts. It does not depend on the spec or the belt size (tested).
* ``analysis/frame_mass_production.json``: today's frame, plus the 18.5 g z 234 dowels + MMA that weight_table never
  booked (correction 2026-11-10). ``corrie_b2_today`` includes them, so it is the honest today's pack, not the
  weight_table figure: ``today total - dowel row = weight_table`` (tested at every belt size).
* ``analysis/frame_mass_h1.json``: the H1 frame (printed body, Ti M5 joint parts, no dowels).
* ``corrie.package_c_rows()``: package C as adopted (gated by prototype tests).

Configs (every belt size S, M, L, XL, XXL)
------------------------------------------
* ``corrie_b2_today``: CORRIE B.2 on today's printed frame (production raster body), dowels booked.
* ``corrie_b2_h1``:    CORRIE B.2 on the H1 frame.
* ``corrie_b2_h1_c``:  ``corrie_b2_h1`` + package C. C-9 (ligament offset of today's body raster) does not
  transfer to H1, whose body is a different raster: it is booked at 0 g with a note (DECISION, mass_ledger.md).

Systems (each row belongs to exactly one)
-----------------------------------------
* ``frame``: printed body, carbon crown, rack/pawl, bushings, Ti hip-pivot mount, inserts, crown fix, z 234 joint
  parts, torso-adjust pulley.
* ``back``: Sandwich v2 spreader, back panel (mesh, stay-rail foam, backers, sleeves, upper pad).
* ``belt``: hipbelt B body, load path (centre plate, hub, latch, doublers, washer), 50 mm webbing + buckle,
  stabilizers, 2:1 pull, lumbar pad seat, SH-05, IMP-5 hip pockets, IMP-3 bottle holster.
* ``harness``: J-straps, yoke, lifters, sternum, IMP-6 phone pocket (sewn to the J-strap in B.2, so it stays with the
  harness when the bag comes off).
* ``bag_shell``: body panels, collar, door, roll-top hem and HDPE strip, accents on the body, door zip and pulls,
  B-11 lash tabs and the bow riser carry, G-1 binding.
* ``bag_pockets``: IMP-1, IMP-2, IMP-4, IMP-8 (bag-mounted).
* ``pouch``: top pouch fabric, zip, pull tab, cord pull.
* ``fly``: rain fly, its base pocket, hem, zip, tether, G-2 re-cut.
* ``straps_meat``: IM1-IM3 internal meat harness and its B-12 ports, under-straps US1/US2, float links B-24.
* ``straps_compression``: haul wraps W1-W3 (+ A-2 tails), their keeper loops, side wings M-01 and SH-06 bars, wing
  straps, roll-top buckles and straps, pouch straps.
* ``attachment``: fairleads, pins, sleeves, bag hooks, hood B-19, ladder strips B-20, guys and tabs B-22, IM2 tongue
  backings B-23, B-17/B-18 spreaders, B-01 swell patches, the boxed fairlead swells B-13x, keepers.
* ``misc``: thread and labels (~3 % of soft goods, ASSUMPTION in geometry.yaml) and the booking reconciliation.

Group definitions (fixed; never define your own)
------------------------------------------------
* ``like_for_like()``: ``bag_side`` = bag_shell + bag_pockets + pouch + fly + straps_meat + straps_compression +
  attachment; ``suspension`` = frame + back + belt + harness. ``misc`` is in neither and is returned on its own so the
  three add up to the pack total (the ticket's two totals do not cover thread and labels).
* ``bag_system()``: THE definition used to compare bag entries = bag_shell + bag_pockets + pouch + fly +
  straps_compression. Meat straps, attachment, belt and harness parts (IMP-3, IMP-5, IMP-6 and any strap pocket) are
  out, because a bag entry should not win or lose on parts it shares with every other entry.

Row fields: ``id, name, group, system, g, source, load_path, base`` (+ ``note`` on corrections).
``load_path``: the part carries a HA-LS-1 rev C load case (frame, spreader, belt load path and wing stiffeners,
harness straps and yoke, meat straps, haul wraps, the attachment parts other than keepers, lining and swell fabric).
``base``: the part is in today's base weight. CORRIE B.2 books every part in base weight, so every row is True until
BL-008 (owner decision) defines base vs add-on.

    python -m huntkit.mass.ledger             # print the system table, belt M
    python -m huntkit.mass.ledger --write     # also write analysis/mass_ledger.md and the BL-001 screenshot
"""
from __future__ import annotations

import contextlib
import functools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
for _p in (ROOT, PACK, PACK / "concepts", PACK / "bag_comp"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import corrie as C  # noqa: E402
import weight_pass_corrie as WP  # noqa: E402

LB = 453.592
OZ = 28.3495
SPEC = "B.2"
SIZES = tuple(C.BELT_SIZES)
CONFIGS = ("corrie_b2_today", "corrie_b2_h1", "corrie_b2_h1_c")
SYSTEMS = ("frame", "back", "belt", "harness", "bag_shell", "bag_pockets", "pouch", "fly", "straps_meat",
           "straps_compression", "attachment", "misc")
BAG_SIDE = ("bag_shell", "bag_pockets", "pouch", "fly", "straps_meat", "straps_compression", "attachment")
SUSPENSION = ("frame", "back", "belt", "harness")
BAG_SYSTEM = ("bag_shell", "bag_pockets", "pouch", "fly", "straps_compression")
G_FRAME = WP.GROUP_OF["frame (printed branch body + carbon crown)"]
G_BELT = WP.GROUP_OF["hipbelt (M)"]
G_HARNESS = WP.GROUP_OF["harness"]
G_MEAT = WP.GROUP_OF["internal meat harness"]
G_FLY = WP.GROUP_OF["rain fly"]
G_BODY = WP.GROUP_OF["main bag"]
G_C = "Package C (gated)"


def _json(name: str) -> dict:
    return json.loads((ANALYSIS / name).read_text())


# =====================================================================================================================
# classification
# =====================================================================================================================
def _system(group: str, name: str, zone: str = "") -> str:
    """The one system a weight-pass row belongs to. Unknown rows raise, so a new row cannot slip through unsorted."""
    if group == G_FRAME or group.startswith("Torso adjust"):
        return "frame"
    if group.startswith("Back system"):
        return "back"
    if group == G_HARNESS:
        return "harness"
    if group == G_BELT:
        return "belt"
    if group == WP.G_POCK:
        return "harness" if name.startswith("IMP-6") else "bag_pockets"
    if group == WP.G_POUCH:
        return "straps_compression" if name.startswith("pouch: ") and "straps" in name else "pouch"
    if group == G_BODY:
        if zone == "swell":
            return "attachment"
        if zone == "wing" or name.startswith(("SH-06", "wing strap", "roll-top ROLL hardware")) or "keeper loops" in name:
            return "straps_compression"
        return "bag_shell"
    if group == WP.GROUP_OF["bag-to-frame attachment system"]:
        return "attachment"
    if group == G_MEAT:
        return "straps_compression" if name.startswith(("haul wraps", "A-2")) else "straps_meat"
    if group == G_FLY:
        return "fly"
    if group == WP.GROUP_OF["misc"] or group == WP.G_REC:
        return "misc"
    raise KeyError(f"no system for row {group!r} / {name!r}")


_LP_NOT = ("keeper", "lining", "grab tab", "bag-floor channels", "strap ports", "B-12")
_LP_BELT = ("load path", "50 mm belt webbing", "wing stiffener", "wing load foam", "2:1 pull", "lock legs", "D-ring",
            "C-1+C-2+C-3")


def _load_path(system: str, name: str, zone: str = "") -> bool:
    if system == "frame":
        return not name.startswith("torso adjust")
    if system == "back":
        return "spreader" in name
    if system == "belt":
        return any(k in name for k in _LP_BELT)
    if system == "harness":
        return not name.startswith("IMP-6")
    if system == "straps_meat":
        return not any(k in name for k in _LP_NOT)
    if system == "straps_compression":
        return name.startswith(("haul wraps", "A-2"))
    if system == "attachment":
        return zone != "swell" and not any(k in name for k in _LP_NOT)
    return False


_ID_RE = re.compile(r"^([A-Z]{1,3}-[0-9A-Za-z]+)\b")


def _key(name: str) -> str:
    m = _ID_RE.match(name)
    if m:
        return m.group(1)
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return "_".join(s.split("_")[:6])


# =====================================================================================================================
# part rows
# =====================================================================================================================
@contextlib.contextmanager
def _wp_spec(spec: str):
    """weight_pass_corrie.breakdown() books the spec named by its module constant BASE (B.1). Run it on ``spec``."""
    old = WP.BASE
    WP.BASE = spec
    try:
        yield
    finally:
        WP.BASE = old


@functools.lru_cache(maxsize=None)
def _b2_rows(size: str) -> tuple:
    """Weight-pass part list on spec B.2 + corrie.b2_rows(), reconciled to corrie.weight_table(size, 'B.2')."""
    with _wp_spec(SPEC):
        bd = WP.breakdown(size)
    rows = [dict(p) for p in bd["parts"] if p["group"] != WP.G_REC]
    b2_group = {"A-2": G_MEAT, "B-10": G_MEAT, "G-1": G_BODY, "G-2": G_FLY}
    for n, g, src in C.b2_rows(bd["concept"], bd["body"], SPEC):
        rows.append({"group": b2_group[n.split()[0]], "part": n, "g": round(float(g), 2), "source": "corrie.b2_rows(): " + src,
                     "zone": ""})
    wt = C.weight_table(size, bd["concept"], spec=SPEC)
    recon = wt["total_g"] - sum(r["g"] for r in rows)
    rows.append({"group": WP.G_REC, "part": "booking reconciliation: SPINE body as booked in geometry.yaml vs the cut-set "
                 "body metric that corrie.weight_table() subtracts", "g": recon,
                 "source": "balance to corrie.weight_table(size, 'B.2') (spec- and size-independent, tested)", "zone": ""})
    return tuple(rows), wt["total_g"]


def _frame_rows(config: str) -> list:
    """Frame rows for a config, replacing the weight-pass frame rows (which are today's frame without the dowels)."""
    fm = _json("frame_mass_production.json")
    out = []
    if config == "corrie_b2_today":
        out.append((G_FRAME, "frame: PAHT-CF printed branch body (production raster)", fm["printed_body_g"],
                    "analysis/frame_mass_production.json printed_body_g", ""))
    else:
        h1 = _json("frame_mass_h1.json")["h1"]
        out.append((G_FRAME, "frame: H1 PAHT-CF printed body (bosses and floors included)", h1["body_g"],
                    "analysis/frame_mass_h1.json h1.body_g", ""))
    out += [(G_FRAME, "frame: carbon crown as built, rack + pawl + guides, bushings, Ti hip-pivot mount, inserts",
             fm["non_body_g"], "analysis/frame_mass_production.json non_body_g", ""),
            (G_FRAME, "frame: rev C crown inner plies (fix)", fm["crown_fix_g"],
             "analysis/frame_mass_production.json crown_fix_g", "")]
    if config == "corrie_b2_today":
        out.append((G_FRAME, "frame: z 234 splice, 8 carbon dowels 5 x 70 mm + MMA", fm["z234_dowels_mma_g"],
                    "analysis/frame_mass_production.json z234_dowels_mma_g",
                    f"CORRECTION: never booked in corrie.weight_table (frame_g kept at the released {fm['frame_g']} g)"))
    else:
        h1 = _json("frame_mass_h1.json")["h1"]
        for n, g in h1["joint_hardware_g"].items():
            out.append((G_FRAME, f"frame: H1 z 234 joint, {n}", g, "analysis/frame_mass_h1.json h1.joint_hardware_g", ""))
    return out


def _c_rows(config: str) -> list:
    out = []
    for n, g, src in C.package_c_rows():
        tag = n.split(":")[0].split(" ")[0]
        if tag.startswith("C-1"):
            out.append((G_BELT, n, g, "corrie.package_c_rows(): " + src, "belt", ""))
        elif tag == "C-9":
            note = ("NOT APPLIED on H1: C-9 offsets the ligaments of today's "
                    f"{_json('frame_mass_production.json')['printed_body_g']} g body raster; H1 is a different "
                    "printed body (analysis/frame_mass_h1.json). Booked 0 g; C-9 on today's frame would be "
                    f"{g:+.1f} g")
            out.append((G_FRAME, n, 0.0 if config != "corrie_b2_today" else g, "corrie.package_c_rows(): " + src,
                        "frame", note))
        elif tag == "C-4":
            out.append((G_BELT, n, g, "corrie.package_c_rows(): " + src, "belt", ""))
        elif tag == "C-7":
            out.append((G_HARNESS, n, g, "corrie.package_c_rows(): " + src, "harness", ""))
        else:
            raise KeyError(f"package C row not sorted: {n}")
    return out


def _row(rid, name, group, system, g, source, zone="", note=""):
    r = {"id": rid, "name": name, "group": group, "system": system, "g": round(float(g), 2), "source": source,
         "load_path": _load_path(system, name, zone), "base": True}
    if note:
        r["note"] = note
    return r


@functools.lru_cache(maxsize=None)
def _parts(config: str, size: str) -> tuple:
    if config not in CONFIGS:
        raise KeyError(f"config {config!r}; one of {CONFIGS}")
    if size not in SIZES:
        raise KeyError(f"belt size {size!r}; one of {SIZES}")
    rows, _ = _b2_rows(size)
    out, seen = [], {}

    def add(name, group, system, g, source, zone="", note=""):
        k = f"{system}:{_key(name)}"
        seen[k] = seen.get(k, 0) + 1
        rid = k if seen[k] == 1 else f"{k}#{seen[k]}"
        out.append(_row(rid, name, group, system, g, source, zone, note))

    for g_, n, g, src, note in _frame_rows(config):
        add(n, g_, "frame", g, src, note=note)
    for r in rows:
        if r["group"] == G_FRAME:
            continue                                    # replaced by _frame_rows()
        add(r["part"], r["group"], _system(r["group"], r["part"], r.get("zone", "")), r["g"], r["source"],
            r.get("zone", ""))
    if config == "corrie_b2_h1_c":
        for g_, n, g, src, sysname, note in _c_rows(config):
            add(n, G_C if g_ is None else g_, sysname, g, src, note=note)
    return tuple(out)


def parts(config: str = "corrie_b2_h1", size: str = "M") -> list:
    """Ledger rows ``{id, name, group, system, g, source, load_path, base}`` for a config at a belt size."""
    return [dict(r) for r in _parts(config, size)]


def weight_table_total(size: str = "M") -> float:
    """corrie.weight_table(size, spec='B.2')['total_g'] (the booking the ledger reconciles to)."""
    return _b2_rows(size)[1]


# =====================================================================================================================
# totals and the fixed group definitions
# =====================================================================================================================
def _rows_of(rows_or_config, size="M"):
    return parts(rows_or_config, size) if isinstance(rows_or_config, str) else rows_or_config


def total(rows_or_config="corrie_b2_h1", size: str = "M") -> float:
    return round(sum(r["g"] for r in _rows_of(rows_or_config, size)), 1)


def by_system(rows_or_config="corrie_b2_h1", size: str = "M") -> dict:
    rows = _rows_of(rows_or_config, size)
    return {s: round(sum(r["g"] for r in rows if r["system"] == s), 1) for s in SYSTEMS}


def like_for_like(rows_or_config="corrie_b2_h1", size: str = "M") -> dict:
    """``bag_side`` (bag_shell + bag_pockets + pouch + fly + straps_meat + straps_compression + attachment) and
    ``suspension`` (frame + back + belt + harness); ``misc`` (thread, labels, reconciliation) is returned on its own.
    bag_side + suspension + misc = total."""
    rows = _rows_of(rows_or_config, size)
    s = lambda keys: round(sum(r["g"] for r in rows if r["system"] in keys), 1)  # noqa: E731
    return {"bag_side": s(BAG_SIDE), "suspension": s(SUSPENSION), "misc": s(("misc",))}


def bag_system(rows_or_config="corrie_b2_h1", size: str = "M") -> float:
    """THE bag-system definition for comparing bag entries: bag_shell + bag_pockets + pouch + fly +
    straps_compression (meat straps, attachment, belt, harness and misc out)."""
    rows = _rows_of(rows_or_config, size)
    return round(sum(r["g"] for r in rows if r["system"] in BAG_SYSTEM), 1)


def corrie_bag_system() -> float:
    """CORRIE B.2's bag system (frame- and belt-size-independent; tested)."""
    return bag_system(parts("corrie_b2_h1", "M"))


# =====================================================================================================================
# the five bag-competition teams on this one basis
# =====================================================================================================================
def _imp(path: str, name: str):
    d = str(PACK / "bag_comp" / path)
    if d not in sys.path:
        sys.path.insert(0, d)
    import importlib
    return importlib.import_module(name)


def _corrie_body_mass() -> dict:
    import bag_concepts as BC
    return BC.metrics(C.build(C.make(), True, spec=SPEC))["mass_g"]


def team_inputs() -> list:
    """Each team's own numbers, read live from its modules (never edited), and the adjustments that move them onto the
    ledger definition. ``delta`` = entry - the team's own CORRIE B.2 baseline, both by the team's metric.
    Adjustments (each from code):
      * swells B-13x are ``attachment`` here but inside every team's body metric: their delta is taken out;
      * a strap-mounted pocket is ``harness`` here: it is taken out of the bag system (D's SP, E's IMP-6R);
      * D's baseline books the geometry.yaml roll-top row (HDPE strip + buckles + webbing) on top of a body that
        already carries the B-07s HDPE strip, and D deletes both: the strip is counted twice in D's saving, so the
        difference to the ledger's roll-top hardware row is added back.
    Parts outside a team's metric (haul wraps for A/B/C/E, B-11, bow carry, keeper loops, roll-top hardware) are
    taken as unchanged in the entry (ASSUMPTION: each write-up says so)."""
    import bag_concepts as BC
    cb = _corrie_body_mass()
    led_roll = next(r["g"] for r in parts("corrie_b2_h1", "M") if r["name"].startswith("roll-top ROLL hardware"))
    out = []

    # ---- A EVOLVE
    E = _imp("A", "evolve")
    s = E.system()
    with E.corrie_door():
        ba = C.build(E.make())
    res = lambda d: json.loads((PACK / "bag_comp" / d / "result.json").read_text())["pack_mass_M_g"]  # noqa: E731
    out.append({"team": "A", "entry": "CORRIE E (EVOLVE)", "published_g": s["corrie_e"]["bag_system_g"],
                "pack_published_g": res("A"),
                "baseline_g": s["corrie_b2"]["bag_system_g"],
                "metric": "body group + IMP-1/2/4/8 + F-01 fly scaled (evolve.system)",
                "adj": [("swells B-13x -> attachment", -(BC.metrics(ba)["mass_g"]["swell"] - cb["swell"]))]})

    # ---- B LEAN (FELL), published = max config
    F = _imp(".", "lean.fell")
    cmp = F.comparison()
    sw = -(cmp["max"]["body_mass"]["swell"] - cmp["corrie_b2"]["body"]["swell"])
    for cfg, lab in (("max", "FELL (LEAN), max = sheep8"), ("day", "FELL (LEAN), day")):
        out.append({"team": "B" if cfg == "max" else "B day", "entry": lab, "published_g": cmp["configs"][cfg]["total_g"],
                    "baseline_g": cmp["corrie_b2"]["total_g"], "pack_published_g": cmp["configs"][cfg]["pack_M_on_H1_g"],
                    "metric": "body group + IMP-1/2/4/8 + F-01 fly scaled + F-02 (fell.corrie_bag_system)",
                    "adj": [("swells B-13x -> attachment", sw)]})

    # ---- C OPEN (TAILGATE)
    TG = _imp("C", "tailgate")
    tb = TG.bag_system(TG.build(), TG.pockets())
    tc = TG.corrie_bag_system()
    out.append({"team": "C", "entry": "TAILGATE (OPEN)", "published_g": tb["total_g"], "baseline_g": tc["total_g"],
                "pack_published_g": res("C"),
                "metric": "body group + IMP-1/2/4/8 (+ IMP-C1) + F-01 fly scaled (tailgate.bag_system)",
                "adj": [("swells B-13x -> attachment",
                         -(tb["metrics"]["mass_g"]["swell"] - tc["metrics"]["mass_g"]["swell"]))]})

    # ---- D MODULE (CACHE)
    D = _imp("D", "cache")
    sd = D.system()
    out.append({"team": "D", "entry": "CACHE (MODULE)", "published_g": sd["bag_system_g"],
                "baseline_g": sd["corrie_b2"]["total_g"], "pack_published_g": res("D"),
                "metric": "body + roll-top row + keeper loops + IMP-1/2/4/8 + W1-W3 + full fly (cache.corrie_b2_system)",
                "adj": [("swells B-13x -> attachment", -(sd["shell_metrics"]["mass_g"]["swell"] - cb["swell"])),
                        ("SP right shoulder-strap snack pocket -> harness", -D.part_mass(D.strap_pocket_r())),
                        ("baseline roll-top row double-counts the HDPE strip (also B-07s in the body)",
                         D.CORRIE_ROLLTOP_HW_G - led_roll)]})

    # ---- E FORM (CHERT): knap_mass keeps CORRIE's swells (it replaces shell, kick plates, collar and zip only)
    FO = _imp("form", "form")
    cr = FO.corrie_parts_g()
    km = FO.knap_mass(FO.make(), cr=cr)
    out.append({"team": "E", "entry": "CHERT (FORM)", "published_g": km["bag_system_g"], "baseline_g": km["corrie_bag_system_g"],
                "pack_published_g": res("form"),
                "metric": "body group + IMP-1/2/4/6/8 + F-01 fly scaled (form.corrie_parts_g)",
                "adj": [("IMP-6R right-strap snack pocket -> harness", -FO.STRAP_SNACK_G)]})
    return out


def _teams_h1() -> float:
    """The CORRIE-B.2-on-H1 pack mass the bag-competition teams were given (bag_comp/RULES.md; lean.fell.H1_PACK_M)."""
    return float(_imp(".", "lean.fell").H1_PACK_M)


def teams() -> list:
    """The five entries on the ledger basis: ``ledger_g`` = CORRIE B.2 ledger bag system + the team's own delta +
    the adjustments. ``pack_M_h1_g`` = ledger H1 pack (belt M) - CORRIE bag system + entry bag system."""
    base = corrie_bag_system()
    h1_m = total("corrie_b2_h1", "M")
    rows = []
    for t in team_inputs():
        d = t["published_g"] - t["baseline_g"]
        adj = sum(g for _, g in t["adj"])
        led = base + d + adj
        rows.append({**t, "published_delta_g": round(d, 1), "adj_g": round(adj, 1), "ledger_g": round(led, 1),
                     "ledger_delta_g": round(led - base, 1), "moves_g": round(led - t["published_g"], 1),
                     "delta_moves_g": round(adj, 1), "pack_M_h1_g": round(h1_m - base + led, 1)})
    return rows


# =====================================================================================================================
# report + chart (python -m huntkit.mass.ledger --write)
# =====================================================================================================================
def _lb(g):
    return f"{g / LB:.2f} lb"


def _lboz(g):
    lb = int(abs(g) // LB)
    oz = (abs(g) - lb * LB) / OZ
    return f"{'-' if g < 0 else ''}{lb} lb {oz:.1f} oz"


def chart(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = {"corrie_b2_today": "CORRIE B.2\ntoday's frame", "corrie_b2_h1": "CORRIE B.2\nH1 frame",
              "corrie_b2_h1_c": "CORRIE B.2\nH1 + package C"}
    cols = {"frame": "#3b4a3f", "back": "#5d6e55", "belt": "#7f8f6a", "harness": "#a3ad8a",
            "bag_shell": "#8a5a2b", "bag_pockets": "#b07a3f", "pouch": "#c99a5b", "fly": "#dcbf8a",
            "straps_meat": "#7a2e2e", "straps_compression": "#a8473a", "attachment": "#4a5d7a", "misc": "#9a9a9a"}
    fig, ax = plt.subplots(figsize=(9.0, 9.5), dpi=110)
    xs = range(len(CONFIGS))
    for i, cfg in enumerate(CONFIGS):
        bs = by_system(cfg, "M")
        y = 0.0
        for s in SYSTEMS:
            g = bs[s]
            ax.bar(i, g, bottom=y, color=cols[s], edgecolor="white", linewidth=0.8, width=0.62,
                   label=s.replace("_", " ") if i == 0 else None)
            if g >= 90:
                ax.text(i, y + g / 2, f"{s.replace('_', ' ')}\n{g:.0f} g", ha="center", va="center", fontsize=8,
                        color="white")
            y += g
        tot = total(cfg, "M")
        ax.text(i, y + 40, f"{tot:.0f} g\n{_lb(tot)}", ha="center", va="bottom", fontsize=11, weight="bold")
    ax.set_xticks(list(xs), [labels[c] for c in CONFIGS], fontsize=10)
    ax.set_ylabel("mass, g (belt M)")
    ax.set_ylim(0, max(total(c, "M") for c in CONFIGS) * 1.12)
    lf = like_for_like("corrie_b2_h1", "M")
    ax.set_title(f"Pack 5200 mass ledger (BL-001), belt M\nbag system {corrie_bag_system():.0f} g · bag side "
                 f"{lf['bag_side']:.0f} g · suspension (H1) {lf['suspension']:.0f} g", fontsize=12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=4, fontsize=9, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def report(team_rows: list, shot: str) -> str:
    L = []
    w = L.append
    base = corrie_bag_system()
    tot = {c: {s: total(c, s) for s in SIZES} for c in CONFIGS}
    bs = {c: by_system(c, "M") for c in CONFIGS}
    lf = {c: like_for_like(c, "M") for c in CONFIGS}
    h1 = _json("frame_mass_h1.json")
    w("# Mass ledger, pack 5200 (BL-001)")
    w("")
    w("pack-designer, 2026-11-10. Generated by `python -m huntkit.mass.ledger --write` from `huntkit/mass/ledger.py`; "
      "do not edit by hand. Every gram below is a row the ledger reads from an existing source (weight-pass part list "
      "on spec B.2, `corrie.b2_rows`, `corrie.weight_table`, `frame_mass_production.json`, `frame_mass_h1.json`, "
      "`corrie.package_c_rows`). From now on every ticket takes masses from the ledger (RULES.md rule 5).")
    w("")
    w(f"**CORRIE B.2 bag system: {base:.1f} g ({_lboz(base)}).** This is the one number bag entries are compared "
      "against (definition below). It does not depend on the frame or the belt size.")
    w("")
    w("## 1. Definitions (fixed)")
    w("")
    w("| system | what is in it |")
    w("|---|---|")
    defs = {
        "frame": "printed body, carbon crown, rack/pawl/guides, bushings, Ti hip-pivot mount, inserts, crown fix, z 234 joint parts, torso-adjust pulley",
        "back": "Sandwich v2 spreader; back panel (mesh, stay-rail foam, carbon backers, sleeves, upper pad)",
        "belt": "belt B body, load path (plate, hub, latch, doublers, washer), 50 mm webbing + buckle, stabilizers, 2:1 pull, pad seat, SH-05, IMP-5 hip pockets, IMP-3 holster",
        "harness": "J-straps, yoke, lifters, sternum; IMP-6 phone pocket (sewn to the J-strap in B.2)",
        "bag_shell": "body panels, collar, door, roll-top hem + HDPE strip, body accents, door zip and pulls, B-11 lash tabs, bow riser carry, G-1 binding",
        "bag_pockets": "IMP-1, IMP-2, IMP-4, IMP-8",
        "pouch": "top pouch fabric, zip, pull tab, cord pull",
        "fly": "rain fly, base pocket, hem, zip, tether, G-2 re-cut",
        "straps_meat": "IM1-IM3 + B-12 ports, under-straps US1/US2, float links B-24",
        "straps_compression": "haul wraps W1-W3 (+ A-2), keeper loops, wings M-01 + SH-06 bars, wing straps, roll-top buckles/straps, pouch straps",
        "attachment": "fairleads, pins, sleeves, bag hooks, hood B-19, ladders B-20, guys + tabs B-22, B-23, B-17/B-18, swell patches, fairlead swells B-13x, keepers",
        "misc": "thread + labels (ASSUMPTION ~3 % of soft goods, geometry.yaml) and the booking reconciliation",
    }
    for s in SYSTEMS:
        w(f"| `{s}` | {defs[s]} |")
    w("")
    w("- **`like_for_like()`**: `bag_side` = bag_shell + bag_pockets + pouch + fly + straps_meat + straps_compression + "
      "attachment; `suspension` = frame + back + belt + harness. `misc` is in neither and is reported on its own, so "
      "bag_side + suspension + misc = total.")
    w("- **`bag_system()`** (compare bag entries with this, nothing else): bag_shell + bag_pockets + pouch + fly + "
      "straps_compression.")
    w("- **Configs**: `corrie_b2_today` (today's printed frame, z 234 dowels booked), `corrie_b2_h1` (H1 frame), "
      "`corrie_b2_h1_c` (H1 + package C, gated by tests HB-5, pad-seat sag, T1(c), T5).")
    w("- Volume is not booked here: the 85 L main bag is a geometry result (corrie_body.md); the pouch, pockets and "
      "fly add mass but are not counted in the 5200 cu in.")
    w("")
    w("## 2. Pack total by config and belt size")
    w("")
    w("| config | " + " | ".join(SIZES) + " |")
    w("|---|" + "---:|" * len(SIZES))
    for c in CONFIGS:
        w(f"| `{c}` | " + " | ".join(f"{tot[c][s]:.1f} g ({_lb(tot[c][s])})" for s in SIZES) + " |")
    w(f"| check: `corrie.weight_table(size, 'B.2')` | " + " | ".join(f"{weight_table_total(s):.1f}" for s in SIZES) + " |")
    w("")
    dow = next(r["g"] for r in parts("corrie_b2_today", "M") if "dowels" in r["name"])
    w(f"`corrie_b2_today` = weight_table + {dow:.1f} g z 234 dowels + MMA (never booked there). Cross-checks against "
      f"`frame_mass_h1.json`: today belt M {h1['today_corrected']['corrie_b2_M_g']} g, H1 belt M "
      f"{h1['h1']['corrie_b2_M_g']} g (both reproduced to 0.5 g, tested).")
    w("")
    w("## 3. Systems, belt M")
    w("")
    w("| system | " + " | ".join(f"`{c}`" for c in CONFIGS) + " | load-path share (H1) |")
    w("|---|" + "---:|" * (len(CONFIGS) + 1))
    p_h1 = parts("corrie_b2_h1", "M")
    for s in SYSTEMS:
        lp = sum(r["g"] for r in p_h1 if r["system"] == s and r["load_path"])
        sh = f"{lp / bs['corrie_b2_h1'][s] * 100:.0f} %" if bs["corrie_b2_h1"][s] else "-"
        w(f"| {s} | " + " | ".join(f"{bs[c][s]:.1f}" for c in CONFIGS) + f" | {sh} |")
    w("| **bag_side** | " + " | ".join(f"**{lf[c]['bag_side']:.1f}**" for c in CONFIGS) + " | |")
    w("| **suspension** | " + " | ".join(f"**{lf[c]['suspension']:.1f}**" for c in CONFIGS) + " | |")
    w("| misc | " + " | ".join(f"{lf[c]['misc']:.1f}" for c in CONFIGS) + " | |")
    w("| **bag system** | " + " | ".join(f"**{bag_system(c, 'M'):.1f}**" for c in CONFIGS) + " | |")
    w("| **total** | " + " | ".join(f"**{total(c, 'M'):.1f} ({_lboz(total(c, 'M'))})**" for c in CONFIGS) + " | |")
    w("")
    w("Package C on H1 (rows in the ledger, `corrie_b2_h1_c`):")
    w("")
    for r in parts("corrie_b2_h1_c", "M"):
        if r["group"] in (G_C,) or r["name"].startswith(("C-1", "C-4", "C-7", "C-9")):
            w(f"- {r['name']}: {r['g']:+.1f} g (`{r['system']}`)" + (f". {r['note']}" if r.get("note") else ""))
    w("")
    w("## 4. CORRIE B.2 bag system, by system")
    w("")
    w("| system | g |")
    w("|---|---:|")
    for s in BAG_SYSTEM:
        w(f"| {s} | {bs['corrie_b2_h1'][s]:.1f} |")
    w(f"| **bag system** | **{base:.1f}** ({_lboz(base)}) |")
    w("")
    bl = sorted({t["baseline_g"] for t in team_rows})
    n_lo = sum(1 for t in team_rows if t["team"] != "B day" and t["baseline_g"] < base)
    w(f"The teams' own CORRIE baselines ({' / '.join(f'{x:.1f}' for x in bl)} g) left out, in different ways, the "
      "roll-top buckles, haul wraps and keeper loops, the bow carry and B-11 tabs, the fly's hem/zip/pocket, or added "
      f"the swells and IMP-6. The ledger number is larger than {n_lo} of the 5 because it books every compression "
      "part (haul wraps, wings, roll-top and pouch straps).")
    w("")
    w("## 5. The five entries on one basis")
    w("")
    w("`ledger` = CORRIE B.2 ledger bag system + (entry - team's own CORRIE baseline, both by the team's metric) + "
      "adjustments. Pack M uses the ledger's H1 pack (belt M) "
      f"{total('corrie_b2_h1', 'M'):.1f} g, not the {_teams_h1():.0f} g the teams were given.")
    w("")
    w("| team | entry | published g | team's CORRIE g | published delta | adjustments | **ledger bag system g** | "
      "**vs CORRIE (ledger)** | published number moves by | pack M published | pack M on H1, ledger |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for t in team_rows:
        w(f"| {t['team']} | {t['entry']} | {t['published_g']:.1f} | {t['baseline_g']:.1f} | {t['published_delta_g']:+.1f} "
          f"| {t['adj_g']:+.1f} | **{t['ledger_g']:.1f}** | **{t['ledger_delta_g']:+.1f}** | {t['moves_g']:+.1f} "
          f"| {t['pack_published_g']:.1f} | {t['pack_M_h1_g']:.1f} |")
    w(f"| - | CORRIE B.2 | - | - | - | - | **{base:.1f}** | 0 | - | - | {total('corrie_b2_h1', 'M'):.1f} |")
    w("")
    w("Adjustments (each computed from the team's own module):")
    w("")
    for t in team_rows:
        for n, g in t["adj"]:
            w(f"- {t['team']}: {n}: {g + 0.0:+.1f} g")
    w("")
    w("What moves:")
    w("")
    for t in team_rows:
        if t["team"] == "B day":
            continue
        dm = t["delta_moves_g"]
        w(f"- **{t['team']} {t['entry']}**: the absolute number moves {t['moves_g']:+.1f} g (the ledger books "
          f"{base:.1f} g for CORRIE, the team {t['baseline_g']:.1f} g); the delta against CORRIE "
          + ("does not move." if abs(dm) < 0.05 else f"moves {dm:+.1f} g ({t['published_delta_g']:+.1f} -> "
                                                    f"{t['ledger_delta_g']:+.1f} g)."))
    w("")
    ranked = sorted((t for t in team_rows if t["team"] != "B day"), key=lambda t: t["ledger_delta_g"])
    w("Ranking on the ledger basis (lightest first): " + ", ".join(f"{t['team']} {t['ledger_delta_g']:+.1f} g"
                                                                    for t in ranked) + ".")
    w("")
    w("## 6. Assumptions and decisions that govern")
    w("")
    w("- ASSUMPTION: parts outside a team's metric (haul wraps for A/B/C/E, B-11 tabs, bow riser carry, keeper loops, "
      "roll-top buckles for A/B/C/E) are unchanged in its entry, as each write-up states. Settled by BL-002 "
      "re-booking each entry part by part in the ledger.")
    w("- ASSUMPTION (inherited): thread + labels ~3 % of soft goods (geometry.yaml). Settled by weighing the first "
      "prototype's thread cones before and after.")
    w("- DECISION: IMP-6 (and any strap pocket) is `harness`: it is sewn to the J-strap in B.2 and stays with the "
      "harness when the bag comes off.")
    w("- DECISION: wings and wing straps, roll-top buckles and pouch straps are `straps_compression` (ticket), so the "
      "bag system books them; the fairlead swells B-13x are `attachment`.")
    w("- DECISION: C-9 is not applied on H1 (0 g row): it is a ligament offset of today's body raster; H1 replaces "
      "that body. A C-9-style offset on H1 needs its own FEA (frame_h1.md section 6 lists CA-1 as the next H1 cut).")
    w("- `base` is True on every row: CORRIE B.2 books every part in base weight. BL-008 proposes base vs add-on.")
    w("")
    w("## 7. Found, not fixed")
    w("")
    rv = lf["corrie_b2_h1"]["bag_side"]
    w(f"- The teams used {_teams_h1():.0f} g for CORRIE B.2 on H1 (bag_comp RULES.md, lean.fell.H1_PACK_M); `frame_mass_h1.json` and the ledger give "
      f"{total('corrie_b2_h1', 'M'):.1f} g. Every published `pack_mass_M_g` is "
      f"{_teams_h1() - total('corrie_b2_h1', 'M'):.1f} g high on that count alone.")
    c9 = next(g for n, g, _ in C.package_c_rows() if n.startswith("C-9"))
    w(f"- bag_weight_review_20261110.md section 1 gives 'about 3873 g' for H1 + package C; that applies C-9 "
      f"({c9:+.1f} g) to H1. The ledger gives {total('corrie_b2_h1_c', 'M'):.1f} g.")
    w(f"- The review's like-for-like bag side (quoted there as 1709 g, section 2, from the B.1 weight-pass groups) is {rv:.1f} g on "
      "the ledger (B.2 parts; IMP-6 in harness; roll-top buckles, B-11, bow carry, keeper loops sorted by system).")
    w("- D's `cache.corrie_b2_system()` counts the roll-top HDPE strip twice (B-07s in the body and again in the "
      "geometry.yaml roll-top row, cache.CORRIE_ROLLTOP_HW_G); corrected above.")
    fmp = _json("frame_mass_production.json")
    w(f"- `frame_mass_production.json` `frame_g` ({fmp['frame_g']}) still omits the dowels for its consumers "
      f"(weight_pass_corrie, build_geometry), so `corrie.weight_table` is {fmp['z234_dowels_mma_g']} g light for "
      "today's frame.")
    w("")
    w("## 8. Screenshot")
    w("")
    w(f"`{shot}`: stacked bars by system, three configs, belt M.")
    w("")
    return "\n".join(L)


def write(date: str = "20261110") -> dict:
    shot = ROOT / "outputs" / "screens" / f"{date}_BL001_1.png"
    chart(shot)
    tr = teams()
    (ANALYSIS / "mass_ledger.md").write_text(report(tr, str(shot.relative_to(ROOT))))
    return {"md": str(ANALYSIS / "mass_ledger.md"), "png": str(shot), "teams": tr}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for c in CONFIGS:
        print(c, {s: total(c, s) for s in SIZES})
    print("systems M (H1):", by_system("corrie_b2_h1", "M"))
    print("like_for_like M (H1):", like_for_like("corrie_b2_h1", "M"))
    print("CORRIE B.2 bag system:", corrie_bag_system())
    if "--write" in argv:
        o = write()
        print(o["md"], o["png"])
        for t in o["teams"]:
            print(t["team"], t["published_g"], "->", t["ledger_g"], "delta", t["ledger_delta_g"])


if __name__ == "__main__":
    main()
