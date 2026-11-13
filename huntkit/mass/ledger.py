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
* ``<config>_v2`` (BL-023): the same config plus the BL-013 booking corrections C1-C8 as signed rows with sources
  (``corrections()``), and on the two H1 configs H1B (2026-11-12): the H1 body as adopted by BL-024 / BL-027 with the
  BL-021 28 mm IM3 cheeks, 757.7 -> 800.7 g, from ``analysis/h1_buckling.json`` (``h1_body_update()``).
  The names above reproduce the BL-001 booking unchanged; ``corrected=True`` on ``parts`` /
  ``total`` / ``by_system`` / ``like_for_like`` / ``bag_system`` selects the ``_v2`` rows. New tickets use
  ``DEFAULT_CONFIG`` (``corrie_b2_h1_v2``), which is also the default of those functions.

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
    if config in CONFIGS_V2:
        base = config[: -len(SUFFIX)]
        out = list(_parts(base, size))
        n = {}
        for tag, name, system, g, src, cfg in _correction_rows(base, size):
            n[tag] = n.get(tag, 0) + 1
            r = _row(f"correction:{tag}#{n[tag]}", name, G_CORR, system, g, src,
                     note=f"CORRECTION {tag} (BL-013, folded into the ledger by BL-023)")
            r.update(correction=tag, cfg=cfg, base=cfg == "base")
            out.append(r)
        return tuple(out)
    if config not in CONFIGS:
        raise KeyError(f"config {config!r}; one of {ALL_CONFIGS}")
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


# =====================================================================================================================
# BL-013 booking corrections, folded into the ledger (BL-023, manufacturing-engineer, 2026-11-11)
# =====================================================================================================================
# BL-013 (weight_rollup_v2.py) resolved eight booking errors against their source files, but kept them as roll-up
# steps, so every ticket reading the ledger inherited the errors (BL-014 S9). They now live here, as signed rows with a
# source each. The BL-001 config names reproduce the BL-001 booking unchanged (other tickets' code and documents
# quote them); the corrected configs carry the suffix ``_v2`` (or pass ``corrected=True``). New tickets use
# ``DEFAULT_CONFIG`` = ``corrie_b2_h1_v2``.
#   C1 printed fairleads (8) double-booked: frame_branch.frame_sdf adds bag_attach.attachment_field to the body SDF,
#      so both the production raster and the H1 raster already hold them.
#   C2 B-01 swell patches booked twice: bag_attach's 2-ply patch estimate and CORRIE's cut piece B-13x are the
#      same 8 swells; B-13x stays.
#   C3 crown-corner carbon wraps + gussets and their bond: frame_eval.REPLACED_G drops all of them as replaced by
#      the printed body, but the two crown corners stay carbon (frame.yaml joints.crown_corner).
#   C4 POM pawl housing double-booked: the printed body forms the housing and its cheeks.
#   C5 non-body lump short of its own sources (M4 sets subtracted that frame_g never held).
#   C6 lifter tri-glide keepers: attachment -> harness (a move, 0 g).
#   C7 IMP-3 holster wing tabs stay sewn to the belt: base, out of the as-hunted add-on (0 g on the total).
#   C8 belt B webbing re-booked to the 2:1 routing (hipbelt_diet.closure, BL-006 a2).
# Every correction applies to all three frame configs: the production raster and H1 both carry the fairleads and the
# pawl housing in the printed body, and both inherit the same non-body lump and crown corners.
SUFFIX = "_v2"
CONFIGS_V2 = tuple(c + SUFFIX for c in CONFIGS)
ALL_CONFIGS = CONFIGS + CONFIGS_V2
DEFAULT_CONFIG = "corrie_b2_h1" + SUFFIX
CORRECTIONS = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "H1B", "BL031", "H1F", "BL046", "BL047", "BL049",
               "BL050", "BL051")
#   BL051 (2026-11-13, BL-051): on the H1 configs, the stay crown h1_lanes.strip_old_us had cut away over the old US1 /
#      US2 stub sites, restored (print-mesh delta); BL050's pins / sleeves row retired (a double count: the cradle rows
#      book the US1 / US2 pins).
#   BL050 (2026-11-13, BL-050 A): in every config, the 7075 pins and UHMWPE sleeves of the 4 fairlead stations the
#      attachment rows never booked (bag_attach._mass_budget counts 8; bag_attach.stations() places 12; BL-051 found
#      the US1 / US2 pins booked in the cradle rows, meat_haul.cradle_parts_g: a double count, the row is gone); on the H1 configs, the US2 bolt-on clevis (joint blocks and bolt cuts in the print, the Ti
#      M5 joint hardware). All from analysis/h1_bedfit.json ``mass``.
#   BL047 (2026-11-13, BL-047): spine clamp webs thinned (crown_gnl.md section 7) in every config; on the H1 configs the H1 print's pawl
#      bosses / pivot bore / fore-wall window and the m-1 hinge relief (print-mesh volume deltas), and the low-profile
#      pawl against the old SLM pawl (mesh volumes). All from analysis/crown_gnl.json ``mass``.
#   BL046 (2026-11-13, BL-045 / BL-046): the spine clamp as sized (crown_spine_clamp.size_clamp on the real crown, a
#      7075 T-fitting) less the 6 g pack5200.HW still books, in every config; and, on the H1 configs only, the H1 spine
#      channel + pawl housing re-made for the OD 20 spine tube and its 6 mm rack (print-mesh volume delta,
#      h1_spine_channel.add_channel). Both from analysis/h1_spine_channel.json ``mass``.
#   BL031 (2026-11-12, BL-031 strap tails, not a booking error): the harness and belt side of the tail rule
#      (``strap_tails.suspension_rows``: lifters, sternum and hip stabilizers cut to length, the 2:1 belt tail to the
#      gloved grip, two belt tail keepers). The bag side of BL-031 is booked by corrie_f.parts (adopted bag rows).
# BL-030: the ADOPTED bag. Every config above books the CORRIE B.2 bag (their names are quoted in other documents and
# stay); the adopted bag is CORRIE F at ADOPTED_BAG["revision"] (owner, DECISIONS 2026-11-12: rev 3 = B-27 port guys
# inside + B-29 crown lid on B-28 crown straps, the top pouch out). ``adopted_bag_rows`` books it on this ledger's
# basis by calling corrie_f.parts (corrie_f subtracts B.2's bag side from these configs and adds its own); the whole
# pack with it is analysis/weight_rollup_v2.md, which reads the revision from here.
ADOPTED_BAG = {"concept": "CORRIE F", "module": "designs/pack_5200/concepts/corrie_f.py", "revision": 3, "door": "D2",
               "top": "B-29 crown lid + B-28 crown straps (as hunted); the top pouch out",
               "decision": "DECISIONS 2026-11-12: owner adopts CORRIE F rev 3 (BL-029 / BL-030)"}


def adopted_bag_rows(size: str = "M") -> list:
    """The adopted bag's bag-side rows ({system, name, g, cfg, source}, BL-008 cfg tags) at belt ``size``:
    ``corrie_f.parts`` at ``ADOPTED_BAG['revision']``. Lazy import (corrie_f reads this module)."""
    import importlib
    for p in (PACK / "concepts", PACK):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    F = importlib.import_module("corrie_f")
    with F.revision(ADOPTED_BAG["revision"]):
        return F.parts(size, door=ADOPTED_BAG["door"])


H1_ONLY = ("H1B", "H1F", "BL049", "BL050", "BL051")   # corrections that apply to the H1 configs only (not to today's
#   production raster). BL050 joined with BL-051: its only all-config row (pins / sleeves) was a double count.
#   H1F (2026-11-13, BL-042) the H1 fairleads completed outside the voxel envelope. The H1 raster stops at the bag
#      envelope (frame_topopt Y_HI_GRID 16 mm), so it holds only the fairlead stubs below y 16, not the cheek tops,
#      front walls and pin holes (C1 assumed it held them whole). The print files now carry every fairlead complete
#      (h1_fairleads.add_fairleads, hinge saddle); the print-mesh volume delta is booked here (analysis/h1_fairleads.json
#      mass.net_g). Today's production raster (frame_branch, no envelope clip at the fairleads) is unaffected.
G_CORR = "BL-013 booking corrections (folded into the ledger by BL-023)"
#   H1B (2026-11-12) the H1 printed body as adopted since frame_mass_h1.json was written: BL-024 H1-G0.55 grow-only
#      offset, the BL-027 buckling members and the BL-021 28 mm IM3 cheeks, all on the same 2 mm raster
#      (analysis/h1_buckling.json ``chosen``). frame_mass_h1.json is left as BL-007's record of the H1 body; the ledger
#      adds the three steps as signed rows, so the H1 _v2 configs book the adopted body. The 28 mm cheek is inside this
#      raster (cheek mask minus the body it overlaps), so the roll-up no longer adds a separate cheek row.


@functools.lru_cache(maxsize=None)
def corner_wraps() -> dict:
    """C3: crown-corner wraps + gussets and their bond, from the beam model's own hardware formula
    (``pack5200.hardware_mass``) run with and without the two crown_corner joints, less the rev C 0.8 mm corner line
    already booked (frame_mass_production.json crown_fix_lines_g.corner_bondline)."""
    from huntkit.fea import pack5200 as P5
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.gendesign import frame_topopt as ft
    m = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19)   # 19 in, as BL-013
    full = P5.hardware_mass(m)["items"]
    m2 = dict(m)
    m2["joints"] = [j for j in m["joints"] if not j["id"].startswith("crown_corner")]
    no = P5.hardware_mass(m2)["items"]
    wk = "carbon wraps (sleeves/hubs) + gussets"
    ak = "adhesive (incl. lumbar-plate bond)"
    booked = _json("frame_mass_production.json")["crown_fix_lines_g"]["corner_bondline"]
    return {"wraps_g": full[wk] - no[wk], "adhesive_g": full[ak] - no[ak], "booked_line_g": booked,
            "unbooked_g": full[wk] - no[wk] + full[ak] - no[ak] - booked}


@functools.lru_cache(maxsize=None)
def non_body_sources() -> dict:
    """C5: the non-body lump (frame_mass_production.json non_body_g) against its own named sources:
    frame_eval.kept_g() + crown_diet.PAWL_BUSH_G + frame_eval.INSERTS_G."""
    from huntkit.gendesign import crown_diet as CD
    from huntkit.gendesign import frame_eval as FE
    lump = _json("frame_mass_production.json")["non_body_g"]
    src = FE.kept_g() + CD.PAWL_BUSH_G + FE.INSERTS_G
    return {"lump_g": lump, "sources_g": src, "short_g": src - lump}


@functools.lru_cache(maxsize=None)
def h1_fairleads_update() -> dict:
    """H1F: the fairlead volume the H1 print mesh adds over the voxel raster (analysis/h1_fairleads.json ``mass``,
    written by huntkit.gendesign.h1_fairleads)."""
    return dict(_json("h1_fairleads.json")["mass"])


@functools.lru_cache(maxsize=None)
def bl046_update() -> dict:
    """BL046: spine clamp and H1 spine channel masses (analysis/h1_spine_channel.json ``mass``, written by
    huntkit.gendesign.h1_spine_channel)."""
    return dict(_json("h1_spine_channel.json")["mass"])


@functools.lru_cache(maxsize=None)
def bl047_update() -> dict:
    """BL047: clamp web, H1 pawl features + hinge relief, LP pawl (analysis/crown_gnl.json ``mass``, written by
    huntkit.gendesign.crown_gnl)."""
    return dict(_json("crown_gnl.json")["mass"])


@functools.lru_cache(maxsize=None)
def bl049_update() -> dict:
    """BL049: hinge fairlead grown, US lane lugs, Ti hinge pins (analysis/h1_lanes.json ``mass``, written by
    huntkit.gendesign.h1_lanes)."""
    return dict(_json("h1_lanes.json")["mass"])


@functools.lru_cache(maxsize=None)
def bl050_update() -> dict:
    """BL050: pins / sleeves for 12 stations, the US2 bolt-on clevis (analysis/h1_bedfit.json ``mass``, written by
    huntkit.gendesign.h1_bedfit)."""
    return dict(_json("h1_bedfit.json")["mass"])


@functools.lru_cache(maxsize=None)
def bl051_update() -> dict:
    """BL051: the stay crown restored over the old US stub sites (analysis/h1_crown.json ``mass``, written by
    huntkit.gendesign.h1_crown)."""
    return dict(_json("h1_crown.json")["mass"])


@functools.lru_cache(maxsize=None)
def h1_body_update() -> dict:
    """H1B: the H1 body raster as adopted (BL-024 + BL-027 + BL-021 28 mm IM3 cheeks), from analysis/h1_buckling.json
    ``chosen`` (written by ``huntkit.gendesign.h1_buckling``). Raises if that file's H1 base is not the body the ledger
    books (frame_mass_h1.json h1.body_g), so the steps can never be added to a different body."""
    c = _json("h1_buckling.json")["chosen"]
    booked = _json("frame_mass_h1.json")["h1"]["body_g"]
    if abs(c["h1_raster_g"] - booked) > 0.05:
        raise ValueError(f"h1_buckling.json H1 base {c['h1_raster_g']:.2f} g != ledger H1 body {booked} g")
    steps = {"bl024_g": c["g055_raster_g"] - c["h1_raster_g"], "bl027_members_g": c["members_added_g"],
             "im3_cheek_28_g": c["im3_cheek_added_g"]}
    return {**steps, "name": c["name"], "d_mid": c["d_mid"], "d_up": c["d_up"], "body_g": c["body_raster_g"], "booked_g": booked,
            "added_g": c["body_raster_g"] - booked, "steps_sum_g": sum(steps.values())}


def _correction_rows(config: str, size: str) -> list:
    """The C1-C8 rows for a BL-001 config: ``(tag, name, system, g, source, cfg)``. A removed part is a negative copy of
    its ledger row; ``cfg`` is BL-008's tag (base / as_hunted)."""
    import hipbelt_diet as HD                       # imports this module; lazy so the ledger loads first
    from huntkit.gendesign import crown_diet as CD
    led = {r["name"]: r for r in _parts(config, size)}
    fl = led["attachment: printed fairleads (8)"]
    sw = led["attachment: B-01 swell patches"]
    lk = led["attachment: lifter tri-glide keepers"]
    cw, nb = corner_wraps(), non_body_sources()
    hs, cl = HD.holster_split(), HD.closure(size)
    h1b = []
    if config != "corrie_b2_today":
        hb, src = h1_body_update(), "analysis/h1_buckling.json chosen."
        h1b = [
            ("H1B", "H1 body: BL-024 H1-G0.55 grow-only offset (lumbar struts, sleeve bottom, hip-pivot boss)", "frame",
             hb["bl024_g"], src + "g055_raster_g - h1_raster_g (2 mm raster x PAHT-CF density; h1_sleeve.md)", "base"),
            ("H1B", f"H1 body: BL-027 buckling members ({hb['name']}: mid bar +{hb['d_mid']:g} mm, upper branches "
             f"+{hb['d_up']:g} mm)",
             "frame", hb["bl027_members_g"], src + "members_added_g (h1_buckling.md, member mass table)", "base"),
            ("H1B", "H1 body: IM3 fairlead cheeks 18 -> 28 mm (2 sides, BL-021), as rastered into the body", "frame",
             hb["im3_cheek_28_g"], src + "im3_cheek_added_g (cheek mask minus the body it overlaps)", "base"),
            ("H1F", "H1 print: 12 fairleads completed outside the voxel envelope (cheek tops, front walls, pin holes, "
             "hinge saddle; BL-042)", "frame", h1_fairleads_update()["net_g"],
             "analysis/h1_fairleads.json mass.net_g (print-mesh volume with / without h1_fairleads.add_fairleads x "
             "the PAHT-CF print density)", "base"),
        ]
    b46 = bl046_update()
    src46 = "analysis/h1_spine_channel.json mass."
    bl046 = [("BL046", f"spine clamp: 7075 T-fitting as sized ({b46['clamp_g']:.1f} g) less the "
                       f"{b46['clamp_booked_g']:.1f} g booked (BL-045 / BL-046)", "frame",
              b46["clamp_g"] - b46["clamp_booked_g"],
              src46 + "clamp_g (crown_spine_clamp.size_clamp, real crown) - clamp_booked_g (pack5200.HW spine_clamp_g)",
              "base")]
    if config != "corrie_b2_today":
        bl046.append(("BL046", "H1 print: spine channel + pawl housing for the OD 20 spine tube and 6 mm rack (BL-046)",
                      "frame", b46["channel_net_g"],
                      src46 + "channel_net_g (print-mesh volume with / without h1_spine_channel.add_channel x the "
                      "PAHT-CF print density)", "base"))
    b47, src47 = bl047_update(), "analysis/crown_gnl.json mass."
    bl046.append(("BL047", f"spine clamp webs thinned (BL-047; {b47['clamp_bl046_g']:.1f} -> {b47['clamp_g']:.1f} g)",
                  "frame", b47["clamp_delta_g"], src47 + "clamp_delta_g (crown_spine_clamp.size_clamp)", "base"))
    if config != "corrie_b2_today":
        bl046.append(("BL047", "H1 print: pawl cheek bosses, pivot bore, fore-wall window; hinge floor relief (BL-047)",
                      "frame", b47["h1_print_delta_g"], src47 + "h1_print_delta_g (print-mesh volume deltas x PAHT-CF "
                      "print density: h1_pawl.add_pawl, bl047_frame_items.hinge_relief)", "base"))
        bl046.append(("BL047", "low-profile Ti pawl (fits the H1 housing) against the old SLM pawl (BL-047)", "frame",
                      b47["pawl_delta_g"], src47 + "pawl_delta_g (mesh volumes x Ti-6Al-4V density)", "base"))
    if config != "corrie_b2_today":
        b49, src49 = bl049_update(), "analysis/h1_lanes.json mass."
        bl046 += [
            ("BL049", "H1 print: US1 / US2 lug arms to the lanes (x +/-70, +/-165; BL-049)", "frame", b49["lug_arms_g"],
             src49 + "lug_arms_g (print-mesh volume added by h1_lanes.add_lugs x PAHT-CF print density)", "base"),
            ("BL049", "H1 print: hinge fairleads grown (cheeks 10 mm, 27 mm up), US fairleads moved onto the lugs, old "
             "US stubs and the hinge relief groove gone (BL-049)", "frame", b49["print_rest_g"],
             src49 + "print_rest_g (assembled print mesh BL-049 - BL-047 - lug_arms_g)", "base"),
            ("BL049", "hinge pins: 5 mm Ti-6Al-4V (2, 44 mm) in place of 7075 as booked (BL-049)", "attachment",
             b49["hinge_pins_delta_g"], src49 + "hinge_pins_delta_g (h1_lanes.hinge_pin mass - attachment 7075 pin "
             "row / 8, x 2)", "base"),
        ]
    b50, src50 = bl050_update(), "analysis/h1_bedfit.json mass."
    # BL-051: the BL050 row "7075 pins + UHMWPE sleeves for the 4 fairlead stations booked short" (every config) is
    # retired: it double-counted. The 4 US1 / US2 pins + sleeves were already booked by
    # meat_haul.cradle_parts_g ('under-straps US1/US2: 7075 pins (4)', 'UHMWPE sleeves (4)'; CORRIE F: 'US-anchor'
    # row); bag_attach._mass_budget books the other 8 (bag_attach._pins_booked_here, CRADLE_PIN_STATIONS).
    if config != "corrie_b2_today":
        hw50 = "; ".join(k for k in b50.get("hardware", {}))
        bl046 += [
            ("BL050", "H1 print: US2 bolt-on clevis, joint blocks and bolt / trap cuts (BL-050)", "frame",
             b50["print_delta_g"], src50 + "print_delta_g (assembled print mesh BL-050 - BL-049, clevises included)",
             "base"),
            ("BL050", f"US2 clevis joint hardware (BOM HW-US2: {hw50}; BL-050)", "frame",
             b50["hardware_g"], src50 + "hardware_g (h1_bedfit.hardware_g: frame_comp_B.bolt_mass_g, steel nut / "
             "washer volumes)", "base"),
        ]
        b51, src51 = bl051_update(), "analysis/h1_crown.json mass."
        bl046.append(("BL051", "H1 print: stay crown restored over the old US1 / US2 stub sites; US2 clevis heads "
                      "counterbored (BL-051)", "frame", b51["print_delta_g"],
                      src51 + "print_delta_g (assembled print mesh BL-051 - BL-050)", "base"))
        bl046.append(("BL051", f"US2 clevis hardware re-specified (BOM HW-US2: {'; '.join(b51['hardware'])}; was BL-050's "
                      "M5 x 40 + 8 washers; BL-051)", "frame", b51["hardware_delta_g"],
                      src51 + "hardware_delta_g (h1_bedfit.hardware_g now - BL-050 hardware_g)", "base"))
    import strap_tails as ST                        # BL-031 (lazy: it reads corrie_f, which reads this module)
    bl031 = [("BL031", n, sys_, g, src, cfg) for n, sys_, g, src, cfg in ST.suspension_rows(size)]
    return h1b + bl031 + bl046 + [
        ("C1", f"REMOVED: {fl['name']} (already inside the printed body raster)", "attachment", -fl["g"],
         "frame_branch.frame_sdf adds bag_attach.attachment_field to the body SDF (frame_h1.md section 4: bag "
         "fairleads 100 % present); negative copy of ledger row " + fl["id"], "base"),
        ("C2", f"REMOVED: {sw['name']} (same 8 swells as cut piece B-13x)", "attachment", -sw["g"],
         "corrie.build B-13x 'replaces the cone caps'; negative copy of ledger row " + sw["id"], "base"),
        ("C3", "crown-corner carbon wraps + CF gussets (2 corners), unbooked", "frame", cw["wraps_g"],
         "ledger.corner_wraps(): pack5200.hardware_mass crown_corner share (frame.yaml wrap per tube)", "base"),
        ("C3", "crown-corner MMA bond (2 corners) less the rev C corner line already booked", "frame",
         cw["adhesive_g"] - cw["booked_line_g"],
         "ledger.corner_wraps(): pack5200.hardware_mass crown_corner adhesive - frame_mass_production corner_bondline",
         "base"),
        ("C4", "POM pawl housing double-booked (the printed body forms the housing and its cheeks)", "frame",
         -(CD.PAWL_HOUSING_G - CD.PAWL_SPRING_G),
         "crown_diet.PAWL_HOUSING_G - PAWL_SPRING_G (ASSUMPTION there; settled by weighing pawl + spring); "
         "print/frame/PRODUCTION.md step 2", "base"),
        ("C5", "non-body lump short of its sources (M4 sets subtracted that frame_g never held)", "frame",
         nb["short_g"], "ledger.non_body_sources(): frame_eval.kept_g + crown_diet.PAWL_BUSH_G + frame_eval.INSERTS_G"
         " - frame_mass_production.non_body_g", "base"),
        ("C6", f"REMOVED: {lk['name']} (moved to harness)", "attachment", -lk["g"],
         "bag_attach: 'lifter backup' is a harness part; negative copy of ledger row " + lk["id"], "base"),
        ("C6", "lifter tri-glide keepers (moved from attachment)", "harness", lk["g"], "ledger row " + lk["id"], "base"),
        ("C7", "IMP-3 holster: its 2 wing tabs stay sewn to the belt (base)", "belt", hs["tabs_g"],
         "hipbelt_diet.holster_split (corrie.holster hardware row)", "base"),
        ("C7", "IMP-3 holster: wing tabs out of the as-hunted add-on", "belt", -hs["tabs_g"],
         "hipbelt_diet.holster_split", "as_hunted"),
        ("C8", "old 50 mm belt strap (C0 1:1 relic) -> two 50 mm buckle tabs", "belt",
         (cl["need_50_m"] - HD.BOOKED_50_M) * HD.WEB50, "hipbelt_diet.closure (BL-006 a2) x nylon_webbing_50mm", "base"),
        ("C8", f"25 mm 2:1 webbing re-booked to {cl['need_25_m']:.2f} m (routing geometry)", "belt",
         (cl["need_25_m"] - HD.BOOKED_25_M) * HD.WEB25, "hipbelt_diet.closure (BL-006 a2) x poly_webbing_25mm", "base"),
    ]


def corrections(config: str = "corrie_b2_h1", size: str = "M") -> dict:
    """{tag: [ledger rows]} of the C1-C8 corrections for a BL-001 config (or its ``_v2`` name)."""
    base = config[: -len(SUFFIX)] if config.endswith(SUFFIX) else config
    out: dict = {t: [] for t in CORRECTIONS}
    for r in _parts(base + SUFFIX, size):
        if r["group"] == G_CORR:
            out[r["correction"]].append(dict(r))
    return out


def _resolve(config: str, corrected: bool) -> str:
    if corrected and not config.endswith(SUFFIX):
        return config + SUFFIX
    return config


def parts(config: str = DEFAULT_CONFIG, size: str = "M", corrected: bool = False) -> list:
    """Ledger rows ``{id, name, group, system, g, source, load_path, base}`` for a config at a belt size.
    ``corrected=True`` (or a ``_v2`` config name) adds the BL-013 corrections C1-C8; correction rows also carry
    ``correction`` (tag), ``cfg`` (BL-008 tag) and ``note``."""
    return [dict(r) for r in _parts(_resolve(config, corrected), size)]


def weight_table_total(size: str = "M") -> float:
    """corrie.weight_table(size, spec='B.2')['total_g'] (the booking the ledger reconciles to)."""
    return _b2_rows(size)[1]


# =====================================================================================================================
# totals and the fixed group definitions
# =====================================================================================================================
def _rows_of(rows_or_config, size="M", corrected=False):
    return parts(rows_or_config, size, corrected) if isinstance(rows_or_config, str) else rows_or_config


def total(rows_or_config=DEFAULT_CONFIG, size: str = "M", corrected: bool = False) -> float:
    return round(sum(r["g"] for r in _rows_of(rows_or_config, size, corrected)), 1)


def by_system(rows_or_config=DEFAULT_CONFIG, size: str = "M", corrected: bool = False) -> dict:
    rows = _rows_of(rows_or_config, size, corrected)
    return {s: round(sum(r["g"] for r in rows if r["system"] == s), 1) for s in SYSTEMS}


def like_for_like(rows_or_config=DEFAULT_CONFIG, size: str = "M", corrected: bool = False) -> dict:
    """``bag_side`` (bag_shell + bag_pockets + pouch + fly + straps_meat + straps_compression + attachment) and
    ``suspension`` (frame + back + belt + harness); ``misc`` (thread, labels, reconciliation) is returned on its own.
    bag_side + suspension + misc = total."""
    rows = _rows_of(rows_or_config, size, corrected)
    s = lambda keys: round(sum(r["g"] for r in rows if r["system"] in keys), 1)  # noqa: E731
    return {"bag_side": s(BAG_SIDE), "suspension": s(SUSPENSION), "misc": s(("misc",))}


def bag_system(rows_or_config=DEFAULT_CONFIG, size: str = "M", corrected: bool = False) -> float:
    """THE bag-system definition for comparing bag entries: bag_shell + bag_pockets + pouch + fly +
    straps_compression (meat straps, attachment, belt, harness and misc out)."""
    rows = _rows_of(rows_or_config, size, corrected)
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
    w("## 7a. Corrected configs (`_v2`, the default for new tickets)")
    w("")
    w("BL-023 folded BL-013's booking corrections C1-C8 into the ledger; on 2026-11-12 the H1 configs gained **H1B**, "
      "the H1 body as adopted (BL-024 + BL-027 + the BL-021 28 mm IM3 cheeks), read from `analysis/h1_buckling.json` "
      "`chosen` (`ledger.h1_body_update`). `frame_mass_h1.json` stays BL-007's record of the H1 body; the "
      "ledger raises if h1_buckling.json was computed on a different H1 base. The BL-001 config names above are "
      "unchanged (other documents quote them); `DEFAULT_CONFIG` = `corrie_b2_h1_v2`. These are the CORRIE B.2 bag "
      "on each frame; the whole-pack scenarios (CORRIE F, gated changes) are `analysis/weight_rollup_v2.md`.")
    w("")
    hb = h1_body_update()
    w(f"H1B (belt-size independent): body {hb['booked_g']} -> {hb['body_g']:.1f} g raster ({hb['steps_sum_g']:+.1f} g booked, "
      f"{_lboz(hb['steps_sum_g'])}) = BL-024 {hb['bl024_g']:+.1f} + BL-027 members {hb['bl027_members_g']:+.1f} + "
      f"28 mm IM3 cheeks {hb['im3_cheek_28_g']:+.1f} g ({hb['name']}).")
    w("")
    w("| correction | " + " | ".join(CONFIGS_V2) + " |")
    w("|---|" + "---:|" * len(CONFIGS_V2))
    cor = {c: corrections(c, "M") for c in CONFIGS}
    for k in CORRECTIONS:
        w(f"| {k} | " + " | ".join(f"{sum(r['g'] for r in cor[c][k]):+.1f}" if cor[c][k] else "-" for c in CONFIGS)
          + " |")
    w("")
    w("| config | " + " | ".join(SIZES) + " |")
    w("|---|" + "---:|" * len(SIZES))
    for c in CONFIGS_V2:
        w(f"| `{c}` | " + " | ".join(f"{total(c, s):.1f}" for s in SIZES) + " |")
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
    for c in ALL_CONFIGS:
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
