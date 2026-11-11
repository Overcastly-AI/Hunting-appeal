"""BL-003: one strap architecture for meat haul + compression (pack-designer, 2026-11-10).

Parts tables, procedure times, hardware and sewing-operation counts, changed load paths (for BL-010) and the patent
check for today's five overlapping strap systems and the candidate architectures:

* ``today``  CORRIE B.2 as booked in the ledger (IM1-IM3, US1/US2, B-24, W1-W3, wings, roll-top, pouch straps).
* ``a``      lighten in place: IM and US go 38 -> 25 mm with a 25 mm aluminium cam; the IM strap's left end becomes a
             sewn loop girth-hitched on the left fairlead eye (3 hooks instead of 6); B-24 goes 25 mm with a 25 mm
             rated G-hook.
* ``b1``     one external set as literally asked: S1-S3 at the IM heights (z 190/330/520), bag-anchored, W1-W3 and
             wings deleted. FAILS F3 (a bag-anchored strap cannot close bag + meat to the frame; section 4 of the doc).
* ``b2``     one external set that works: W1-W3 (frame-anchored, unchanged) become the only external straps; the wings,
             their bars and their 4 straps are deleted (team B's move, ``bag_comp/lean``).
* ``c``      meat-trip kit: the B-24 float links leave the base pack (BL-008 proposal row B24).
* ``rec``    the recommendation: (a) on IM and US + (b2) + (c), B-24 kept as built (same part as the bag hooks).

Every mass of a part that exists today is read from ``huntkit.mass.ledger`` (RULES.md rule 5). New parts take their
mass from a material record or from an ASSUMPTION line below that names the source and the test that settles it.
This module certifies nothing: changed load paths are listed for BL-010.

    python designs/pack_5200/concepts/strap_arch.py            # print the summary
    python designs/pack_5200/concepts/strap_arch.py --write    # also write analysis/strap_architecture.md + 2 PNGs
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
for _p in (ROOT, PACK, PACK / "concepts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from huntkit.gendesign import attach_system as AS  # noqa: E402
from huntkit.gendesign import meat_haul as MH  # noqa: E402
from huntkit.mass import ledger as L  # noqa: E402
from huntkit.materials import load  # noqa: E402

import build_geometry as BG  # noqa: E402

CONFIG, SIZE = "corrie_b2_h1", "M"
LB, OZ = 453.592, 28.3495
DATE = "20261110"
FUNCS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
FUNC_NAMES = {"F1": "meat in the bag", "F2": "bag-off haul", "F3": "float", "F4": "carry compression",
              "F5": "side carry", "F6": "door zip unloaded", "F7": "roll-top + pouch"}
GEO = yaml.safe_load((PACK / "geometry.yaml").read_text())

# ------------------------------------------------------------------------------------------------ records and inputs
WEB25 = float(load("poly_webbing_25mm").require("mass_g_m"))          # 18 g/m
WEB38 = float(load("poly_webbing_38mm").require("mass_g_m"))          # 28 g/m
WEB25_N = float(load("poly_webbing_25mm").require("breaking_strength_n"))
WEB38_N = float(load("poly_webbing_38mm").require("breaking_strength_n"))
LL_SLIP_N = float(load("ladder_lock_25mm").require("slip_load_n"))    # 300 N, estimate
SR25_N = float(load("buckle_side_release_25mm").require("breaking_strength_n"))

IM_CUTS_MM = [float(s["cut_length_mm"]) for s in GEO["meat_harness"]["straps"]]
IM_HOOK_G, IM_CAM_G = BG.MEAT_HOOK_G, BG.MEAT_CAM_G                   # 9 g, 22 g (ASSUMPTIONs in build_geometry)
IM_HOOK_N, CAM_N = BG.MEAT_HOOK_N, MH.CAM_N                           # 1500 N, 1100 N (ASSUMPTIONs)
BARTACK38_N = BG.BARTACK_38_N                                          # 2700 N (ASSUMPTION, proof-test)
STUB_M = BG.STUB_LEN
IM_REQ_N = float(GEO["meat_harness"]["load_cases"]["required_leg_capacity_n"])   # 605 N per leg
HOOK_RATED_N, HOOK_RATED_G = AS.HOOK_RATED_N, AS.HOOK_RATED_G         # bag hook / B-24 hook, 2200 N, 14 g
G_HOOK_HAUL_G = 4.0   # corrie.G_HOOK (weight_pass W.G_HOOK_G): 4 g ASSUMPTION, HAUL family, no record, no rating

# New parts (no record in data/materials yet; materials-engineer to add records). Sources: docs/research/strap_systems.md
# ASSUMPTION: 25 mm rated aluminium G-hook = AustriAlpin DY25K-G class: 8 g, 1.2 kN tensile break, no permanent
#   deformation up to 0.9 kN (maker page). Settled by: proof-test 5 hooks on 25 mm webbing to 900 N (no set) and
#   pull 5 to break (>= 1200 N), plus field test FT-S1 (hook stays on a slack eye through 1 km of brush).
G25R_G, G25R_N, G25R_YIELD_N = 8.0, 1200.0, 900.0
# ASSUMPTION: 25 mm aluminium cam buckle: 13 g (Austere Mfg 25 mm cam 12.2 g, maker-reseller listing, + 1 g glove
#   pull tab); slip >= 1100 N, the same slip ASSUMPTION the 38 mm cam carries today (meat_haul.CAM_N). No maker
#   publishes a slip rating; a 25 mm alloy cam is listed at 450 kg break (Jimmy Green, secondary). Settled by: the
#   open IM/US hardware proof test (meat_haul_modes.md "still open"), run on 25 mm webbing: 5 cams, wet and at -20 C,
#   pass = no slip > 5 mm below 1100 N.
CAM25_G, CAM25_N = 13.0, CAM_N
# ASSUMPTION: a box-X bartack on 25 mm webbing holds the 38 mm value scaled by width (2700 x 25/38). Settled by the
#   same bartack proof test that settles BARTACK_38_N.
BARTACK25_N = BARTACK38_N * 25.0 / 38.0
# ASSUMPTION: feeding or pulling one 25 mm strap end (with its G-hook) through a B-12 port takes 3 s with gloves.
#   Settled by timing it on the first sewn bag (the same glove trial as the PROCEDURES times).
PORT_S = 3
# ASSUMPTION: taking the B-24 pair out of the kill kit and shaking them out: 5 s (same glove trial).
KIT_S = 5

# Unit times derived from the existing glove procedures (attach_system.PROCEDURES), not new guesses
HOOK_S = AS.PROCEDURES["bag_off"]["steps"][2][1] / 4          # 16 s for the 4 bag hooks -> 4 s per hook
IM_STRAP_S = AS.PROCEDURES["float"]["steps"][2][1] / 3        # 24 s for IM1-IM3 (2 hooks + cam each) -> 8 s per strap
CRADLE_S = AS.PROCEDURES["float"]["steps"][1][1]              # 12 s
LINK_S = AS.PROCEDURES["float"]["steps"][3][1]                # 8 s
HANG_S = AS.PROCEDURES["float"]["steps"][4][1]                # 14 s
WRAP_S = AS.PROCEDURES["float"]["steps"][5][1]                # 18 s
STASH_S = AS.PROCEDURES["bag_off_haul"]["steps"][3][1]        # 20 s
BAG_OFF_S = sum(t for _, t in AS.PROCEDURES["bag_off"]["steps"])   # 52 s
BAG_ON_S = sum(t for _, t in AS.PROCEDURES["bag_on"]["steps"])     # 59 s

MH_JSON = json.loads((ANALYSIS / "meat_haul_modes.json").read_text())
FF_JSON = json.loads((ANALYSIS / "float_fea_results.json").read_text())
HOOP = json.loads((PACK / "bag_comp" / "C" / "result.json").read_text())["hoop"]


# ======================================================================================================= ledger rows
def _ledger_rows() -> list:
    return [r for r in L.parts(CONFIG, SIZE) if r["system"] in ("straps_meat", "straps_compression")]


def _lg(prefix: str, rows=None) -> float:
    """Ledger mass of the one strap row whose name starts with ``prefix`` (raises if not exactly one)."""
    rows = rows or _ledger_rows()
    hit = [r for r in rows if r["name"].startswith(prefix)]
    if len(hit) != 1:
        raise KeyError(f"{len(hit)} ledger rows start with {prefix!r}")
    return float(hit[0]["g"])


def ledger_baseline() -> dict:
    s = L.by_system(CONFIG, SIZE)
    return {"straps_meat": s["straps_meat"], "straps_compression": s["straps_compression"],
            "total": round(s["straps_meat"] + s["straps_compression"], 2)}


# ============================================================================================================== parts
@dataclass(frozen=True)
class Part:
    id: str
    name: str
    system: str                 # straps_meat / straps_compression (ledger systems)
    g: float
    funcs: tuple                # functions it serves
    hw: dict = field(default_factory=dict)   # hardware type -> count (moving hardware the user handles)
    ops: int = 0                # sewing operations (rule below)
    base: bool = True           # in the base pack (False = meat-trip kit)
    source: str = ""
    change: str = ""


# Sewing-operation rule (same for every architecture): 1 op per hot-cut piece + 1 per sewn join (box-X, sewn loop,
# hem run, seam catch, topstitch run). Threading hardware without a stitch is 0.
def _strap_ops(n_pieces: int, joins_each: int) -> int:
    return n_pieces * (1 + joins_each)


def today_parts() -> list:
    rows = _ledger_rows()
    im_row = _lg("internal meat harness: 3 x 38 mm", rows)
    im_web = sum(IM_CUTS_MM) / 1000.0 * WEB38
    im_eyes = 6 * STUB_M * WEB38
    im_hooks, im_cams = 6 * IM_HOOK_G, 3 * IM_CAM_G
    split = im_web + im_eyes + im_hooks + im_cams
    if abs(split - im_row) > 0.05:
        raise ValueError(f"IM split {split:.2f} != ledger row {im_row}")
    us = lambda s: _lg("under-straps US1/US2: " + s, rows)  # noqa: E731
    f13 = ("F1", "F2", "F3")
    P = [
        Part("IM-web", "IM1-IM3 straps, 38 mm webbing (cuts 990/1023/1083 mm)", "straps_meat", im_web, f13, {},
             _strap_ops(3, 3), True, "ledger IM row split: geometry.yaml cut lengths x poly_webbing_38mm"),
        Part("IM-eyes", "6 fairlead eyes (old stubs), 38 mm webbing 6 x 0.20 m", "straps_meat", im_eyes, f13, {},
             0, True, "ledger IM row split: build_geometry.STUB_LEN x poly_webbing_38mm (eyes also take the bag hooks)"),
        Part("IM-hooks", "6 x 38 mm sliding-gate hooks", "straps_meat", im_hooks, f13, {"38 mm sliding-gate hook": 6},
             0, True, "ledger IM row split: build_geometry.MEAT_HOOK_G 9 g ASSUMPTION"),
        Part("IM-cams", "3 x 38 mm cam buckles", "straps_meat", im_cams, f13, {"38 mm cam": 3}, 0, True,
             "ledger IM row split: build_geometry.MEAT_CAM_G 22 g ASSUMPTION"),
        Part("B-12", "B-12 strap ports x6 (Hypalon) + B-10 TPU swap", "straps_meat",
             _lg("internal meat harness: B-01 strap ports", rows) + _lg("B-10", rows), ("F1",), {}, 6, True,
             "ledger rows B-12 + B-10"),
        Part("US-anchor", "US1/US2 printed anchors, 7075 pins, UHMWPE sleeves (frame side)", "straps_meat",
             us("printed anchors") + us("7075 pins") + us("UHMWPE sleeves"), f13, {}, 0, True, "ledger US rows"),
        Part("US-cams", "US1/US2 38 mm cams (2)", "straps_meat", us("38 mm cams"), f13, {"38 mm cam": 2}, 0, True,
             "ledger"),
        Part("US-tg", "US1/US2 tri-glide keepers (2)", "straps_meat", us("tri-glide keepers"), f13,
             {"38 mm tri-glide": 2}, 0, True, "ledger"),
        Part("US-web", "US1/US2 38 mm webbing 1.10 m", "straps_meat", us("38 mm webbing"), f13, {},
             _strap_ops(2, 2), True, "ledger"),
        Part("US-chan", "US bag-floor channels", "straps_meat", us("bag-floor channels"), f13, {}, 2, True, "ledger"),
        Part("B-24-web", "B-24 float links, 38 mm webbing 2 x 435 mm", "straps_meat",
             _lg("float-mode stand-off links B-24: 38 mm webbing", rows), ("F3",), {}, _strap_ops(2, 4), True,
             "ledger"),
        Part("B-24-hooks", "B-24 rated 38 mm hooks (2), same part as the bag hooks", "straps_meat",
             _lg("float-mode stand-off links B-24: rated", rows), ("F3",), {"38 mm rated hook 2200 N": 2}, 0, True,
             "ledger"),
        Part("B-24-thr", "B-24 thread", "straps_meat", _lg("float-mode stand-off links B-24: thread", rows), ("F3",),
             {}, 0, True, "ledger"),
        Part("W-web", "W1-W3 haul wraps, 25 mm coyote webbing 4.67 m", "straps_compression",
             _lg("haul wraps: 3 frame-anchored", rows), ("F2", "F3", "F4"), {}, _strap_ops(3, 2), True, "ledger"),
        Part("W-hw", "W1-W3 G-hooks (3) + ladder locks (3)", "straps_compression",
             _lg("haul wraps: 3 aluminium", rows), ("F2", "F3", "F4"), {"25 mm G-hook (HAUL)": 3, "25 mm ladder lock": 3},
             0, True, "ledger"),
        Part("A-2", "A-2 wrap tails 250 -> 150 mm", "straps_compression", _lg("A-2", rows), ("F2", "F3", "F4"), {}, 0,
             True, "ledger"),
        Part("keepers", "6 haul-wrap keeper loops in the gore seams", "straps_compression",
             _lg("main bag: 6 haul-wrap keeper", rows), ("F2", "F3", "F4"), {}, 6, True, "ledger"),
        Part("M-01", "M-01 side wings x2 (330D, hemmed)", "straps_compression", _lg("M-01", rows), ("F4", "F5", "F6"),
             {}, 2 * (1 + 1 + 1), True, "ledger"),
        Part("SH-06", "SH-06 wing leading-edge bars x2", "straps_compression", _lg("SH-06", rows), ("F4", "F5", "F6"),
             {}, 2 * 2, True, "ledger"),
        Part("wing-straps", "wing straps x4 (25 mm + G-hook + ladder lock + seam loop)", "straps_compression",
             sum(_lg(f"wing strap {i}", rows) for i in range(1, 5)), ("F4", "F5", "F6"),
             {"25 mm G-hook (HAUL)": 4, "25 mm ladder lock": 4}, 4 * (_strap_ops(1, 2) + 2), True, "ledger"),
        Part("roll", "roll-top: 2 x 25 mm side-release + 2 x 0.35 m", "straps_compression",
             _lg("roll-top ROLL hardware", rows), ("F7",), {"25 mm side-release": 2}, _strap_ops(2, 2), True, "ledger"),
        Part("pouch-straps", "pouch: 4 x 25 mm 0.12 m straps + 4 G-hooks", "straps_compression",
             _lg("pouch: 4 x 25 mm", rows), ("F7",), {"25 mm G-hook (HAUL)": 4}, _strap_ops(4, 1), True, "ledger"),
    ]
    tot = sum(p.g for p in P)
    if abs(tot - ledger_baseline()["total"]) > 0.1:
        raise ValueError(f"today parts {tot:.2f} != ledger straps_meat + straps_compression {ledger_baseline()['total']}")
    return P


def _swap(parts: list, pid: str, **kw) -> list:
    return [replace(p, **kw) if p.id == pid else p for p in parts]


def _drop(parts: list, *ids) -> list:
    return [p for p in parts if p.id not in ids]


def _lighten_im_us(P: list) -> list:
    """(a) on IM and US: 38 -> 25 mm webbing, 25 mm Al cam, IM left end a sewn loop girth-hitched on the left eye."""
    f13 = ("F1", "F2", "F3")
    P = _swap(P, "IM-web", name="IM1-IM3 straps, 25 mm webbing (same cuts; left end a sewn loop, girth-hitched on the "
              "left fairlead eye)", g=sum(IM_CUTS_MM) / 1000.0 * WEB25, ops=_strap_ops(3, 2),
              source="geometry.yaml cuts x poly_webbing_25mm record; the sewn loop replaces the left hook loop (same cut)",
              change="38 -> 25 mm; left hook -> sewn loop")
    P = _swap(P, "IM-hooks", name="3 x 25 mm rated Al G-hooks (right end only)", g=3 * G25R_G,
              hw={"25 mm rated G-hook": 3}, source="ASSUMPTION G25R_G (AustriAlpin DY25K-G class, 8 g, 1.2 kN)",
              change="6 sliding-gate -> 3 rated G-hooks")
    P = _swap(P, "IM-cams", name="3 x 25 mm Al cams", g=3 * CAM25_G, hw={"25 mm cam": 3},
              source="ASSUMPTION CAM25_G (Austere 25 mm class)", change="38 -> 25 mm cam")
    P = _swap(P, "B-12", name="B-12 ports x6, slot 45 x 12 mm (passes a 25 mm G-hook)",
              change="slot 6 -> 12 mm open (pattern change, mass unchanged: ASSUMPTION)")
    P = _swap(P, "US-web", name="US1/US2 25 mm webbing 1.10 m", g=1.10 * WEB25,
              source="poly_webbing_25mm record x the 1.10 m of the ledger row", change="38 -> 25 mm")
    P = _swap(P, "US-cams", name="US1/US2 25 mm Al cams (2)", g=2 * CAM25_G, hw={"25 mm cam": 2},
              source="ASSUMPTION CAM25_G", change="38 -> 25 mm cam (same part as IM)")
    P = _swap(P, "US-tg", name="US1/US2 tri-glide keepers (2), 25 mm", hw={"25 mm tri-glide": 2},
              change="38 -> 25 mm, mass kept at the ledger's 38 mm value (conservative)")
    return P


def _lighten_b24(P: list) -> list:
    P = _swap(P, "B-24-web", name="B-24 float links, 25 mm webbing 2 x 435 mm", g=2 * MH.link_cut_mm() / 1000 * WEB25,
              source="meat_haul.link_cut_mm() x poly_webbing_25mm", change="38 -> 25 mm")
    return _swap(P, "B-24-hooks", name="B-24 25 mm rated Al G-hooks (2)", g=2 * G25R_G, hw={"25 mm rated G-hook": 2},
                 source="ASSUMPTION G25R_G", change="2200 N bag hook -> 1.2 kN G-hook (misuse 941 N > 900 N yield: BL-010)")


def _delete_wings(P: list) -> list:
    P = _drop(P, "M-01", "SH-06", "wing-straps")
    fun = ("F2", "F3", "F4", "F5", "F6")
    for pid in ("W-web", "W-hw", "A-2", "keepers"):
        P = _swap(P, pid, funcs=fun, change="now the only external set: carry compression, side carry, float wrap")
    return P


def b1_strap_cuts_mm() -> list:
    """S1-S3 at the IM heights: cut = haul path at that height (linear in z between the geometry.yaml wraps) + 150 mm
    tail (A-2). ASSUMPTION: interpolated, not a 3D path; settled by re-running build_geometry.haul_wraps at those z."""
    W = sorted(GEO["haul_wraps"], key=lambda w: w["z_at_19in"])
    zs, hp = [w["z_at_19in"] for w in W], [w["haul_path_mm"] for w in W]
    out = []
    for z in (190.0, 330.0, 520.0):
        for i in range(len(zs) - 1):
            if zs[i] <= z <= zs[i + 1]:
                out.append(hp[i] + (hp[i + 1] - hp[i]) * (z - zs[i]) / (zs[i + 1] - zs[i]) + 150.0)
    return out


def architectures() -> dict:
    T = today_parts()
    a = _lighten_b24(_lighten_im_us(T))
    # b1: W1-W3, A-2, keepers and wings deleted; S1-S3 bag-anchored at the IM heights (G-hook + ladder lock each,
    # 2 seam loops each 25 x 80 mm like the keeper loops).
    b1 = _drop(T, "M-01", "SH-06", "wing-straps", "W-web", "W-hw", "A-2", "keepers")
    cuts = b1_strap_cuts_mm()
    b1 += [Part("S-web", "S1-S3, 25 mm, bag-anchored at z 190/330/520", "straps_compression",
                sum(cuts) / 1000 * WEB25, ("F4", "F5", "F6"), {}, _strap_ops(3, 2), True,
                "b1_strap_cuts_mm() x poly_webbing_25mm", "new"),
           Part("S-hw", "S1-S3 G-hooks (3) + ladder locks (3)", "straps_compression",
                3 * G_HOOK_HAUL_G + 3 * float(load("ladder_lock_25mm").require("mass_g")), ("F4", "F5", "F6"),
                {"25 mm G-hook (HAUL)": 3, "25 mm ladder lock": 3}, 0, True, "as W-hw", "new"),
           Part("S-loops", "S1-S3 seam loops (6 x 25 x 80 mm)", "straps_compression", 6 * 0.08 * WEB25,
                ("F4", "F5", "F6"), {}, 6, True, "poly_webbing_25mm", "new")]
    b2 = _delete_wings(T)
    c = [replace(p, base=False, change="meat-trip kit (BL-008 row B24)") if p.id.startswith("B-24") else p for p in T]
    rec = _delete_wings(_lighten_im_us(T))
    rec = [replace(p, base=False, change="meat-trip kit (BL-008 row B24), part unchanged") if p.id.startswith("B-24")
           else p for p in rec]
    return {"today": T, "a": a, "b1": b1, "b2": b2, "c": c, "rec": rec}


ARCH_NAMES = {"today": "Today (CORRIE B.2)", "a": "(a) lighten in place", "b1": "(b1) S1-S3 at IM heights, bag-anchored",
              "b2": "(b2) W1-W3 the one external set, wings deleted", "c": "(c) meat-trip kit (B-24)",
              "rec": "REC = (a) on IM/US + (b2) + (c)"}


def summary(parts: list) -> dict:
    tot = sum(p.g for p in parts)
    base = sum(p.g for p in parts if p.base)
    hw = {}
    for p in parts:
        for k, n in p.hw.items():
            hw[k] = hw.get(k, 0) + n
    return {"total_g": round(tot, 1), "base_g": round(base, 1), "kit_g": round(tot - base, 1),
            "meat_g": round(sum(p.g for p in parts if p.system == "straps_meat" and p.base), 1),
            "comp_g": round(sum(p.g for p in parts if p.system == "straps_compression" and p.base), 1),
            "hw_count": sum(hw.values()), "hw_types": len(hw), "hw": hw, "ops": sum(p.ops for p in parts)}


def savings() -> dict:
    A = architectures()
    t = summary(A["today"])
    out = {}
    for k, P in A.items():
        s = summary(P)
        out[k] = {**s, "saved_removed_g": round(t["total_g"] - s["total_g"], 1),
                  "saved_base_g": round(t["base_g"] - s["base_g"], 1)}
    return out


def by_function(parts: list, base_only: bool = True) -> dict:
    """Mass split by function. Rule: a part serving n functions books g/n to each (documented in the doc)."""
    out = {f: 0.0 for f in FUNCS}
    for p in parts:
        if base_only and not p.base:
            continue
        for f in p.funcs:
            out[f] += p.g / len(p.funcs)
    return {k: round(v, 1) for k, v in out.items()}


# ================================================================================= task 1: today's margins (2x flag)
def today_margins() -> list:
    """Rated / required for every strap part with a load case. ``over2`` marks rated > 2 x the factored requirement."""
    us_d = MH_JSON["bag_off"]["cradle_tension_n"]
    us_lim = us_d * MH.QUARTER_KG and us_d * FF_JSON.get("meat_limit_kg", 53.0) / MH.QUARTER_KG \
        if "meat_limit_kg" in FF_JSON else us_d * 53.0 / MH.QUARTER_KG
    link = MH_JSON["float"]["link"]
    comp_n = max(max(v["straps"].values()) for v in HOOP["straps_on"].values()) * 3.0
    wrap_n = 150.0 * 1.5                    # float clamp: the 150 N hand-cinch ASSUMPTION x 1.5 (bag-off rule)
    rows = [
        ("IM1-IM3", "38 mm webbing", IM_REQ_N, WEB38_N, "605 N leg demand (geometry.yaml required_leg_capacity_n)"),
        ("IM1-IM3", "38 mm sliding-gate hook (ASSUMPTION 1500 N)", IM_REQ_N, IM_HOOK_N, "meat_haul_modes hook SF 2.48"),
        ("IM1-IM3", "38 mm cam slip (ASSUMPTION 1100 N)", IM_REQ_N, CAM_N, "IM-cam SF 1.82"),
        ("IM1-IM3", "box-X bartack (ASSUMPTION 2700 N)", IM_REQ_N, BARTACK38_N, "SF 4.46"),
        ("US1/US2", "38 mm webbing", us_lim, WEB38_N, "US1 at the 53 kg float limit (float_fea.md 2)"),
        ("US1/US2", "38 mm cam slip (ASSUMPTION 1100 N)", us_lim, CAM_N, "cam SF 2.25 at 36 kg, 1.53 at 53 kg"),
        ("US1/US2", "printed anchor, fatigue", us_lim, us_lim * 1.00, "fatigue SF 1.00 at 53 kg: sets the limit"),
        ("B-24", "38 mm webbing", link["tension_envelope_factored_n"], WEB38_N, "misuse envelope 941 N"),
        ("B-24", "rated 38 mm hook 2200 N", link["tension_envelope_factored_n"], HOOK_RATED_N,
         "SF 6.23 design, 2.34 misuse"),
        ("W1-W3", "25 mm webbing", wrap_n, WEB25_N, "float clamp 150 N x 1.5 (ASSUMPTION; no friction credited)"),
        ("W1-W3", "ladder lock slip 300 N (estimate)", wrap_n, LL_SLIP_N, "ladder_lock_25mm record"),
        ("W1-W3", "G-hook 4 g (no rating on file)", wrap_n, float("nan"), "no record: BL-010 / materials"),
        ("wing straps", "25 mm webbing", comp_n, WEB25_N, "hoop-strap tension 25.6 N x 3.0 (bag_comp C result.json)"),
        ("wing straps", "ladder lock slip", comp_n, LL_SLIP_N, ""),
        ("roll-top", "25 mm side-release 450 N", float("nan"), SR25_N, "no load case on file"),
    ]
    out = []
    for sysname, part, req, rated, note in rows:
        r = rated / req if req and not math.isnan(req) and not math.isnan(rated) else float("nan")
        out.append({"system": sysname, "part": part, "req_n": req, "rated_n": rated, "ratio": r,
                    "over2": (not math.isnan(r)) and r > 2.0, "note": note})
    return out


# ========================================================================= procedures (seconds, same method as DETACH_S)
def procedures() -> dict:
    """Steps and seconds for F1-F3, today and REC. Unit times come from attach_system.PROCEDURES (HOOK_S = 4 s per
    hook from the bag-off step, IM_STRAP_S = 8 s per two-hook strap from the float step); PORT_S and KIT_S are
    ASSUMPTIONs (above)."""
    im_rec = IM_STRAP_S - HOOK_S                                 # one hook fewer per strap
    im_out_today = 6 * HOOK_S                                    # unhook 6 IM hooks from the eyes (not in PROCEDURES)
    im_out_rec = 3 * HOOK_S + 3 * PORT_S                         # unhook 3 free ends, pull them out through the ports
    w_off = 3 * HOOK_S                                           # REC: W1-W3 cross the bag in carry
    T, R = {}, {}
    T["F1"] = [("Open the roll-top (or the door; the wings stay cinched outboard of the door zip).", 0),
               ("Set the meat (game bags) against B-01 over the spreader.", 0),
               ("Hook IM1-IM3 eye to eye across the meat (2 hooks each) and cam.", 3 * IM_STRAP_S),
               ("Close.", 0)]
    R["F1"] = [("Open the roll-top. Using the door instead: unhook the W1 and W2 G-hooks first (2 x 4 s).", 0),
               ("Set the meat against B-01 over the spreader. The IM straps are already on the left eyes.", 0),
               ("Hook each IM free end on its right eye (1 hook each) and cam.", 3 * im_rec),
               ("Close. Door used: re-hook W1, W2 and snug (2 x 4 s).", 0)]
    R["F1_door_extra"] = 2 * 2 * HOOK_S
    T["F2"] = [("Bag off (attach_system bag_off).", BAG_OFF_S),
               ("Unhook IM1-IM3 from the eyes (6 hooks; not in today's 52 s, counted here).", im_out_today),
               ("Set the quarter in the cradle, cam to a 70 mm belly.", CRADLE_S),
               ("Hook IM1-IM3 eye to eye over the meat and cam.", 3 * IM_STRAP_S),
               ("Fold the empty bag flat and strap it over the crown with W3.", STASH_S)]
    R["F2"] = [("Unhook W1-W3 at their G-hooks (3 x 4 s).", w_off),
               ("Bag off (attach_system bag_off).", BAG_OFF_S),
               ("Unhook the 3 IM free ends and pull them out through the B-12 ports; they stay on the left eyes.",
                im_out_rec),
               ("Set the quarter in the cradle, cam to a 70 mm belly.", CRADLE_S),
               ("Hook each IM free end on its right eye over the meat and cam.", 3 * im_rec),
               ("Fold the empty bag flat and strap it over the crown with W3.", STASH_S)]
    T["F3"] = [("Bag off.", BAG_OFF_S), ("Unhook IM1-IM3 (6 hooks).", im_out_today),
               ("Cradle.", CRADLE_S), ("IM1-IM3 eye to eye over the meat.", 3 * IM_STRAP_S),
               ("Hook a B-24 link on each IM3 eye.", LINK_S), ("Hang the bag on the loop that touches.", HANG_S),
               ("Close W1-W3 round bag and meat.", WRAP_S)]
    R["F3"] = [("Unhook W1-W3 (3 x 4 s).", w_off), ("Bag off.", BAG_OFF_S),
               ("Unhook the 3 IM free ends, pull them out through the ports.", im_out_rec),
               ("Cradle.", CRADLE_S), ("IM free ends on the right eyes over the meat, cam.", 3 * im_rec),
               ("Take the B-24 pair out of the kill kit.", KIT_S),
               ("Hook a B-24 link on each IM3 eye.", LINK_S), ("Hang the bag on the loop that touches.", HANG_S),
               ("Close W1-W3 round bag and meat.", WRAP_S)]
    T["bag_off"] = [("attach_system bag_off", BAG_OFF_S), ("IM straps unhooked (6)", im_out_today)]
    R["bag_off"] = [("W1-W3 off", w_off), ("attach_system bag_off", BAG_OFF_S), ("IM free ends out (3)", im_out_rec)]
    T["bag_on"] = [("attach_system bag_on", BAG_ON_S), ("IM straps hooked across port to port (6 hooks)", 6 * HOOK_S)]
    R["bag_on"] = [("attach_system bag_on", BAG_ON_S), ("feed 3 IM free ends in through the ports, hook, cam flat",
                                                        3 * (PORT_S + im_rec)), ("W1-W3 on and snug", w_off)]
    tot = lambda st: int(round(sum(t for _, t in st)))  # noqa: E731
    secs = {}
    for k in ("F1", "F2", "F3", "bag_off", "bag_on"):
        secs[k] = {"today": tot(T[k]), "rec": tot(R[k])}
    secs["F2"]["today_documented"] = AS.procedure_times()["bag_off_haul"]
    secs["F3"]["today_documented"] = AS.procedure_times()["float"]
    secs["F1"]["rec_door"] = secs["F1"]["rec"] + R["F1_door_extra"]
    return {"today": T, "rec": R, "seconds": secs}


# ============================================================================================ load paths for BL-010
def load_paths() -> list:
    """Every load path that changes in REC (or in a rejected option worth recording), with its factored load and the
    rated part. Strength is NOT certified here."""
    us_d = MH_JSON["bag_off"]["cradle_tension_n"]
    us_on = MH_JSON["bag_on"]["cradle_tension_n"]
    us_lim = us_d * 53.0 / MH.QUARTER_KG
    link = MH_JSON["float"]["link"]
    comp_n = max(max(v["straps"].values()) for v in HOOP["straps_on"].values()) * 3.0
    return [
        {"loc": "IM1-IM3 left fairlead eyes (z 190/330/520), girth hitch", "dir": "aft, across the meat (as today)",
         "n": IM_REQ_N, "part": "25 mm sewn loop on a 38 mm webbing eye; box-X 25 mm", "rated_n": BARTACK25_N,
         "note": "hook -> girth hitch: same force and direction at the eye; the hitch pinches the eye at the pin; "
                 "check the IM2 hitch in the spreader's 30 mm edge notch (thickness)"},
        {"loc": "IM1-IM3 right eyes, free-end hook", "dir": "aft", "n": IM_REQ_N, "part": "25 mm rated Al G-hook",
         "rated_n": G25R_N, "note": f"yield (no-set) {G25R_YIELD_N:.0f} N; today 1500 N ASSUMPTION"},
        {"loc": "IM1-IM3 cam", "dir": "along the strap", "n": IM_REQ_N, "part": "25 mm Al cam (slip)",
         "rated_n": CAM25_N, "note": "slip ASSUMPTION carried over from the 38 mm cam; proof test"},
        {"loc": "IM1-IM3 webbing", "dir": "along the strap", "n": IM_REQ_N, "part": "poly_webbing_25mm",
         "rated_n": WEB25_N, "note": "contact width on the meat 38 -> 25 mm: 1.5 x the strap-line pressure on the "
                                     "game bag (not a frame load)"},
        {"loc": "US1 cradle (z 95), 53 kg float limit", "dir": "along the strap, side legs 31 deg",
         "n": us_lim, "part": "25 mm Al cam (slip)", "rated_n": CAM25_N,
         "note": f"design 36 kg {us_d:.0f} N, bag-on {us_on:.0f} N; anchor fatigue (frame) unchanged, it sets 53 kg"},
        {"loc": "US1/US2 sewn eye on the left pin", "dir": "along the strap", "n": us_lim, "part": "25 mm box-X",
         "rated_n": BARTACK25_N, "note": "eye on the same pin; 25 mm webbing sits narrower in the 38 mm sleeve: "
                                         "check edge bearing on the UHMWPE sleeve"},
        {"loc": "US1/US2 webbing", "dir": "along the strap", "n": us_lim, "part": "poly_webbing_25mm",
         "rated_n": WEB25_N, "note": "cradle contact width 38 -> 25 mm under a bone-in quarter"},
        {"loc": "W1/W2 frame anchors (z 80/250/420 lash points), carry compression", "dir": "aft + inboard",
         "n": comp_n, "part": "25 mm ladder lock (slip)", "rated_n": LL_SLIP_N,
         "note": "NEW duty in carry (wings deleted): team C hoop straps 12-26 N at 1 g x 3.0; small"},
        {"loc": "W1-W3 float clamp", "dir": "round bag + meat", "n": 150.0 * 1.5, "part": "25 mm ladder lock (slip)",
         "rated_n": LL_SLIP_N, "note": "unchanged part, no friction credited; G-hook (4 g) has no rating: BL-010 "
                                       "to add a rated hook or a proof test"},
        {"loc": "W1/W2 G-hooks across the door (side carry, tripod)", "dir": "aft + inboard", "n": comp_n,
         "part": "25 mm G-hook (HAUL), unrated", "rated_n": float("nan"),
         "note": "tripod / scope pod now held by W1/W2 instead of the wings: proof on the first bag"},
        {"loc": "B-03 frame-side corner seams (wing roots)", "dir": "removed", "n": 0.0, "part": "none",
         "rated_n": float("nan"), "note": "wing side-compression load removed from the B-03 seams"},
        {"loc": "B-24 link (option a only; not in REC)", "dir": "aft + down 30 deg", "n":
            link["tension_envelope_factored_n"], "part": "25 mm rated Al G-hook", "rated_n": G25R_N,
         "note": f"misuse 941 N > {G25R_YIELD_N:.0f} N no-set load: REC keeps the 2200 N hook"},
    ]


# ====================================================================================================== patents
def patent_check(key: str) -> list:
    """The three guardrails the ticket names, per architecture."""
    shelf = ("no fabric shelf", "pass", "no panel added between frame and bag in any mode")
    pin = ("under-straps pin to pin", "pass", "US eye on the left pin, cam on the right pin (25 mm in a/rec)")
    gap = ("no bag webbing between the spreader and the z 330 cross member", "pass",
           "IM2 reaches its eye through the spreader's edge notch, aft of the spreader")
    if key in ("a", "rec"):
        gap = (gap[0], "pass, check", "the IM2 girth hitch sits on the IM2 eye at the notch, aft of the spreader; it is "
                                     "a frame strap, not bag webbing; confirm the hitch does not reach behind the "
                                     "spreader (prototype fit, BL-010 drawing check)")
    if key == "b1":
        gap = (gap[0], "pass", "S straps are on the outside of the bag")
    return [shelf, pin, gap]


# ======================================================================================== functions shown working
def functions_rec() -> list:
    return [
        ("F1", "IM1-IM3 (25 mm) inside the bag, left ends hitched to the left eyes through the B-12 ports, free ends "
               "hooked on the right eyes and cammed; meat against the spreader."),
        ("F2", "Bag off; the IM straps stay on the frame; quarter in the US1/US2 cradle (25 mm, 25 mm cams) at a 70 mm "
               "belly; IM over it; empty bag strapped over the crown with W3. Limit 53 kg unchanged (set by the "
               "US1 anchor fatigue, a frame part)."),
        ("F3", "As F2, then the B-24 links (from the kill kit, unchanged parts) on the IM3 eyes, bag hung at "
               "120/170/220 mm, W1-W3 closed round bag and meat."),
        ("F4", "W1-W3, frame-anchored, cinch the bag to the frame from three heights (mean z 165 / 335 / 703); tails "
               "in the 6 keeper loops; top guys (attachment) hold the top. Small load: pull W1-W3 further."),
        ("F5", "Tripod right: feet in the IMP-8 cup, under W1 and W2 on the right gore, W3 above. Poles/pad left. "
               "IMP-1 scope sleeve re-anchored on the left gusset B-03L (it hung inside the left wing)."),
        ("F6", "The door zip is not used as a clamp: cinch W1/W2 first, then zip (team C's rule). The zip's hoop load "
               "is a body result, not a strap result: 0.45 N/mm worst vs 35.4 N/mm crosswise (team C sim, SF 78 at "
               "1 g, 26 at 3 g, straps on or off). PT-7 / ZP-1 settle it."),
        ("F7", "Roll-top: 2 x 25 mm side-release (unchanged). Pouch: 4 straps + 4 G-hooks (unchanged)."),
    ]


# ============================================================================================================= charts
COL = {"straps_meat": "#b5651d", "straps_compression": "#4a6fa5", "kit": "#9aa0a6"}


def _side_panel(ax, arch: str, mode: str):
    """Schematic side view (y aft to the right, z up, mm). Not to scale for the straps' thickness."""
    import matplotlib.patches as mp
    ax.set_xlim(-60, 620)
    ax.set_ylim(-40, 860)
    ax.set_aspect("equal")
    ax.axis("off")
    # frame: stay line, crown, spreader
    ax.plot([0, 0], [0, 703], color="#222", lw=3)
    ax.plot([-20, 20], [703, 703], color="#222", lw=3)
    ax.add_patch(mp.Rectangle((3, 112), 8, 318, color="#555"))
    eyes = {190: "IM1", 330: "IM2", 520: "IM3"}
    for z in eyes:
        ax.plot(0, z, "o", ms=5, color="#222")
    lw = 3.0 if arch in ("today", "b2", "c") else 2.0     # 38 vs 25 mm IM/US
    meat_c, bag_c = "#c97b7b", "#d9d4c5"
    wings = arch in ("today", "a", "c")
    kit = arch in ("c", "rec")
    if mode == "carry":
        ax.add_patch(mp.FancyBboxPatch((20, 40), 290, 760, boxstyle="round,pad=2,rounding_size=30", fc=bag_c, ec="#777"))
        ax.add_patch(mp.Ellipse((95, 320), 140, 330, fc=meat_c, ec="none", alpha=0.9))
        for z in eyes:
            ax.plot([0, 175, 175, 0], [z, z + 12, z - 12, z], color=COL["straps_meat"], lw=lw)
        for z in (95, 142):
            ax.plot([0, 160, 0], [z, 40, z - 8], color=COL["straps_meat"], lw=lw, alpha=0.8)
        if wings:
            ax.add_patch(mp.Polygon([(30, 150), (270, 170), (270, 600), (30, 600)], fc="#4a6fa5", alpha=0.25, ec="#4a6fa5"))
            for z in (260, 490):
                ax.plot([30, 300], [z, z], color=COL["straps_compression"], lw=1.8)
        for z0, z1 in ((80, 250), (250, 420), (703, 703)):
            on = not wings
            ax.plot([0, 312], [z0, z1], color=COL["straps_compression"], lw=2.2 if on else 1.0,
                    ls="-" if on else ":")
        ttl = "F1 bag on, meat in bag"
    else:
        gap = 0 if mode == "off" else 170
        ax.add_patch(mp.Ellipse((19 + 85, 330), 170, 360, fc=meat_c, ec="none"))
        for z in eyes:
            ax.plot([0, 200, 200, 0], [z, z + 10, z - 10, z], color=COL["straps_meat"], lw=lw)
        ax.plot([0, 120, 200, 0], [95, 40, 60, 142], color=COL["straps_meat"], lw=lw)
        if mode == "off":
            ax.add_patch(mp.Rectangle((-30, 703), 60, 40, fc=bag_c, ec="#777"))
            ax.plot([-30, 30], [720, 720], color=COL["straps_compression"], lw=2)
            ttl = "F2 bag off, meat on frame"
        else:
            bx = 19 + gap + 20
            ax.add_patch(mp.FancyBboxPatch((bx, 60), 280, 740, boxstyle="round,pad=2,rounding_size=30", fc=bag_c,
                                           ec="#777"))
            ax.plot([0, bx], [520, 520 - math.tan(math.radians(30)) * 0 - 5], color=COL["kit"] if kit else
                    COL["straps_meat"], lw=2.5, ls="--" if kit else "-")
            for z in (165, 335, 703):
                ax.plot([0, bx + 285], [z, z], color=COL["straps_compression"], lw=2.0)
            if wings:
                ax.add_patch(mp.Polygon([(bx + 10, 150), (bx + 250, 170), (bx + 250, 600), (bx + 10, 600)],
                                        fc="#4a6fa5", alpha=0.25, ec="#4a6fa5"))
            ttl = "F3 float, 170 mm gap"
    ax.set_title(ttl, fontsize=9)


def chart_sideviews(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    keys = ("today", "a", "b2", "c", "rec")
    S = savings()
    fig, axes = plt.subplots(len(keys), 3, figsize=(9.0, 15.0))
    for i, k in enumerate(keys):
        for j, m in enumerate(("carry", "off", "float")):
            _side_panel(axes[i, j], k, m)
        s = S[k]
        axes[i, 0].text(-60, 900, f"{ARCH_NAMES[k]}   base {s['base_g']:.0f} g, saves {s['saved_base_g']:.0f} g "
                        f"(removed {s['saved_removed_g']:.0f} g)", fontsize=10, weight="bold", va="bottom")
    h = [Line2D([], [], color=COL["straps_meat"], lw=3, label="meat straps IM / US (thick = 38 mm, thin = 25 mm)"),
         Line2D([], [], color=COL["straps_compression"], lw=2, label="W1-W3 / wing straps (dotted = on keepers)"),
         Line2D([], [], color=COL["kit"], lw=2.5, ls="--", label="B-24 link from the meat-trip kit"),
         Line2D([], [], color="#4a6fa5", lw=8, alpha=0.25, label="side wing M-01")]
    fig.legend(handles=h, loc="lower center", ncol=2, fontsize=8, frameon=False)
    fig.suptitle("BL-003 strap architectures, side view (frame left, aft right; schematic)", fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=85)
    plt.close(fig)
    return path


def chart_mass(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    A = architectures()
    keys = ("today", "a", "b1", "b2", "c", "rec")
    cols = ["#7f3c10", "#b5651d", "#e0a96d", "#2f4b7c", "#4a6fa5", "#8fb0d9", "#9a9a9a"]
    fig, ax = plt.subplots(figsize=(9, 6))
    x = np.arange(len(keys))
    bottom = np.zeros(len(keys))
    for f, c in zip(FUNCS, cols):
        v = np.array([by_function(A[k])[f] for k in keys])
        ax.bar(x, v, bottom=bottom, color=c, label=f"{f} {FUNC_NAMES[f]}", edgecolor="white", lw=0.5)
        bottom += v
    kit = np.array([summary(A[k])["kit_g"] for k in keys])
    ax.bar(x, kit, bottom=bottom, color="none", edgecolor="#555", hatch="//", label="meat-trip kit (not base)")
    for i, k in enumerate(keys):
        ax.text(i, bottom[i] + kit[i] + 8, f"{bottom[i]:.0f} g", ha="center", fontsize=9, weight="bold")
    base0 = summary(A["today"])["base_g"]
    ax.axhline(base0 - 200, color="#c00", ls="--", lw=1)
    ax.text(len(keys) - 0.5, base0 - 196, "target: today - 200 g", color="#c00", fontsize=8, ha="right", va="bottom")
    ax.set_xticks(x, ["today", "(a)", "(b1)\nfails F3", "(b2)", "(c)", "REC"])
    ax.set_ylabel("g (base weight, ledger straps_meat + straps_compression)")
    ax.set_title("Strap mass by function (a part serving n functions books g/n to each)", fontsize=11)
    ax.legend(fontsize=8, loc="upper right", ncol=2)
    ax.set_ylim(0, base0 * 1.25)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


# ============================================================================================================= report
def _f(v, d=1):
    return "-" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{d}f}"


def _lboz(g):
    oz = g / OZ
    return f"{oz:.1f} oz" if abs(oz) < 16 else f"{int(oz // 16)} lb {oz % 16:.1f} oz"


def report(shots: list) -> str:
    A = architectures()
    S = savings()
    base = ledger_baseline()
    pr = procedures()
    sec = pr["seconds"]
    r = S["rec"]
    L_ = []
    a = L_.append
    a("# Strap architecture: meat haul + compression (BL-003)\n")
    a("pack-designer, 2026-11-10. Generated by `python designs/pack_5200/concepts/strap_arch.py --write`; do not edit "
      "by hand. Masses of existing parts come from `huntkit/mass/ledger.py` (CORRIE B.2 on H1, belt M); new parts "
      "from a record or an ASSUMPTION in `strap_arch.py`. Research: `docs/research/strap_systems.md`. Nothing here "
      "certifies strength: section 7 lists the changed load paths for BL-010.\n")
    a(f"**Result.** Ledger `straps_meat + straps_compression` = {base['straps_meat']:.1f} + "
      f"{base['straps_compression']:.1f} = **{base['total']:.1f} g ({_lboz(base['total'])})**. The recommended "
      f"architecture REC books **{r['base_g']:.1f} g** in the base pack: **{r['saved_base_g']:.1f} g "
      f"({_lboz(r['saved_base_g'])}) less**, of which **{r['saved_removed_g']:.1f} g is hardware and fabric that no "
      f"longer exists** and {r['kit_g']:.1f} g (the B-24 links, unchanged) moves to the meat-trip kit. Target "
      f"(>= 200 g) **met on both counts**; stretch (300 g) **not met** ({r['saved_base_g']:.0f} g base, "
      f"{r['saved_removed_g']:.0f} g removed). Hardware the user handles: {S['today']['hw_count']} -> "
      f"{r['hw_count']} pieces, {S['today']['hw_types']} -> {r['hw_types']} part types; sewing operations "
      f"{S['today']['ops']} -> {r['ops']}.\n")
    a("REC = (a) on IM and US (38 -> 25 mm, 25 mm Al cams, IM left end a sewn loop girth-hitched on the left eye) + "
      "(b2) the wings go and W1-W3 become the one external strap set + (c) the B-24 links ride in the kill kit. Two "
      "owner decisions gate it (section 9).\n")

    a("## 1. Today's parts, loads and margins\n")
    a("Ledger rows, belt M, H1 frame. The IM harness row (240.3 g) is split by `build_geometry` constants; the split "
      "is tested to equal the ledger row.\n")
    a("| part | system | g | functions | hardware |\n|---|---|---:|---|---|")
    for p in A["today"]:
        hw = ", ".join(f"{n} x {k}" for k, n in p.hw.items()) or "-"
        a(f"| {p.name} | `{p.system}` | {p.g:.1f} | {' '.join(p.funcs)} | {hw} |")
    t = S["today"]
    a(f"| **total** | | **{t['total_g']:.1f}** | | {t['hw_count']} pieces |\n")
    a("Rated / required (requirement = factored load; `> 2x` = over-strength by more than 2x):\n")
    a("| system | part | required N | rated N | ratio | > 2x | basis |\n|---|---|---:|---:|---:|---|---|")
    for m in today_margins():
        a(f"| {m['system']} | {m['part']} | {_f(m['req_n'], 0)} | {_f(m['rated_n'], 0)} | {_f(m['ratio'], 2)} | "
          f"{'**yes**' if m['over2'] else 'no'} | {m['note']} |")
    a("\nReading: every webbing is 20-60x over its load, so width is free to drop; what governs is the hardware "
      "(cams 1.5-1.8x, ladder locks 1.3x) and, for the cradle, the printed US1 anchor's fatigue (a frame part, which "
      "sets the 53 kg float limit and is not touched here). The 38 mm sliding-gate hook (2.48x) and the B-24 hook "
      "(2.34x misuse, 6.2x design) are over 2x; so are the bartacks.\n")

    a("## 2. Research summary (detail and URLs in `docs/research/strap_systems.md`)\n")
    a("- **Stone Glacier:** meat rides on an integrated load shelf in the frame, between frame and bag; the frame is "
      "connected to the bag at 12 points by 1 in (25 mm) webbing with Duraflex hardware. Pack-out: separate the bag, "
      "load, tighten the shelf, re-attach the bag bottom-up.\n"
      "- **Exo:** 4 pairs of straps on the frame: 2 pairs secure the load, 2 pairs connect the bag; with the bag off "
      "all 4 pairs hold the load. One strap set, two jobs: the closest model to REC's frame-anchored W1-W3.\n"
      "- **Seek Outside:** 8 removable, movable compression straps + 1 over-the-top, joinable for long loads; the "
      "same straps do compression and odd-load lashing.\n"
      "- **Mystery Ranch:** Overload sling between frame and bag (a fabric shelf; we may not use one, patent "
      "guardrail), bag folds over the meat and its own compression straps cinch the quarters.\n"
      "- **Kifaru:** ARK frame with Loop Lock attachment points for strapping quarters; no strap specs published "
      "(secondary).\n"
      "- **Rated light hardware:** AustriAlpin 25 mm Al G-hook 8 g / 1.2 kN break / 0.9 kN no-set; 38 mm 16 g / "
      "1.5 kN; Austere 25 mm Al cam 12.2 g (no rating); a 25 mm alloy cam at 450 kg break (secondary); ITW ladder "
      "locks 687-981 N tensile, no maker publishes slip. No leader publishes a strap or hook rating.\n")
    a("Takeaway: the leaders use **one 25 mm strap set** for compression and meat, mostly frame-anchored (SG, Exo). "
      "Nobody runs 38 mm webbing for meat straps, and nobody carries side wings and wrap straps together.\n")

    a("## 3. Architectures\n")
    a("| architecture | base g | kit g | saved, base | saved, removed | hardware pieces / types | sewing ops | "
      "F1-F7 |\n|---|---:|---:|---:|---:|---|---:|---|")
    ok = {"today": "all", "a": "all", "b1": "**F3 fails**", "b2": "all", "c": "all (F3 needs the kit)",
          "rec": "all (F3 needs the kit)"}
    for k in ("today", "a", "b1", "b2", "c", "rec"):
        s = S[k]
        a(f"| {ARCH_NAMES[k]} | {s['base_g']:.1f} | {s['kit_g']:.1f} | {s['saved_base_g']:.1f} | "
          f"{s['saved_removed_g']:.1f} | {s['hw_count']} / {s['hw_types']} | {s['ops']} | {ok[k]} |")
    a("\n*saved, base* = against the ledger's base booking; *saved, removed* = mass that no longer exists (the kit "
      "still exists). Function split rule for the bar chart: a part serving n functions books g/n to each.\n")
    a("### (a) lighten in place\n")
    a(f"IM1-IM3: 38 -> 25 mm webbing (same cuts), 25 mm Al cam (ASSUMPTION {CAM25_G:.0f} g, slip {CAM25_N:.0f} N), left "
      f"end a sewn loop girth-hitched on the left fairlead eye, so 3 rated 25 mm G-hooks ({G25R_G:.0f} g, "
      f"{G25R_N:.0f} N) instead of 6 sliding-gate hooks. US1/US2: 25 mm webbing, the same 25 mm cam. B-24: 25 mm "
      f"webbing and the 25 mm rated G-hook. Saves {S['a']['saved_removed_g']:.1f} g; short of 200 g on its own. The "
      f"B-24 hook swap puts the 941 N misuse load above the hook's {G25R_YIELD_N:.0f} N no-set load, so REC does not "
      "take it (the B-24 hook stays the 2200 N bag-hook part, which is also the repair-kit spare).\n")
    a("### (b1) three straps at the IM heights, wings and W1-W3 deleted (as the ticket worded it)\n")
    cuts = b1_strap_cuts_mm()
    a(f"S1-S3 at z 190/330/520, cut {', '.join(f'{c:.0f}' for c in cuts)} mm (haul path interpolated + 150 mm tail). "
      f"It saves {S['b1']['saved_removed_g']:.1f} g, but **it cannot do F3**. To close bag and meat to the frame, each "
      "strap needs a frame anchor at both ends. At the IM heights the only frame points are the IM eyes. In float the "
      "IM3 eye already carries the IM3 meat-strap hook and the B-24 link hook side by side in its 18 mm throat "
      "(`float_fea.md` assumptions), so a third hook does not fit. Bag-anchored straps, on the other hand, pull the "
      "bag's own seams, not the stack. The W anchors (z 80/250/420 lash points and the crown bar) are the only free "
      "frame anchors, and adding new ones means a new printed feature, which is out of bounds. Also, with no strap "
      "above z 520 the float bag's top tips aft: its CG (about z 550, 129 mm aft of its face) sits above and behind "
      "the link. W3 at the crown holds it today. **Rejected.**\n")
    a("### (b2) W1-W3 as the one external set, wings deleted\n")
    a(f"W1-W3 are already frame-anchored and sized for the float path. They take over carry compression and side carry "
      f"from the wings (team B's FELL did this). Deleted: M-01 x2, SH-06 x2, 4 wing straps, "
      f"{S['b2']['saved_removed_g']:.1f} g. The heights are W's (mean z 165 / 335 / 703), not the IM heights: "
      "W2 is at IM2, W1 is 25 mm below IM1, and W3 stays at the crown for the float-bag top, the C6 tall-load lash "
      "(>= 25 mm on the crown bar) and the F2 bag stash. Cost: W1/W2 cross the door in carry, so a door opening "
      f"adds 2 hook-offs and 2 hook-ons ({pr['rec']['F1_door_extra']:.0f} s); the roll-top route adds nothing. IMP-1 "
      "(scope sleeve, inside the left wing today) re-anchors on the left gusset B-03L, as team C did; IMP-8 "
      "(bow cam cup) is already sewn in the corner seam below the wing and stays.\n")
    a("### (c) meat-trip kit\n")
    a(f"The only parts used in F3 and nowhere else are the B-24 links ({S['c']['kit_g']:.1f} g). BL-008 already "
      "proposed them as a meat-trip kit. The cradle (US1/US2) is not F2/F3-only: in F1 it cinches the floor and "
      "takes 55 % of the floor vertical (`meat_haul.CRADLE_SHARE`), and F2 is a day-of-kill mode, so the cradle "
      "stays on the pack. Honest note: the kill kit rides in the pack on hunt days, so (c) lowers the base-weight "
      "booking, not what the hunter carries, unless the links stay in camp until a planned pack-out (the loadout "
      "study found float is never needed in its six loadouts).\n")
    a("### REC\n")
    a("| part | g | change | functions |\n|---|---:|---|---|")
    for p in A["rec"]:
        tag = "" if p.base else " (kit)"
        a(f"| {p.name}{tag} | {p.g:.1f} | {p.change or '-'} | {' '.join(p.funcs)} |")
    a(f"| **base total** | **{r['base_g']:.1f}** | | |")
    a(f"| kit | {r['kit_g']:.1f} | | |\n")
    a("Hardware, today vs REC:\n")
    a("| part type | today | REC |\n|---|---:|---:|")
    for k in sorted(set(S["today"]["hw"]) | set(r["hw"])):
        a(f"| {k} | {S['today']['hw'].get(k, 0)} | {r['hw'].get(k, 0)} |")
    a("\nAll straps on the pack are now 25 mm (the fairlead eyes and the bag hooks stay 38 mm, `attachment`). The "
      "MEAT family is no longer told apart by width: it keeps its bone/stone colour and is the only strap with a cam. "
      "R-25 (one-width families) needs that sentence changed (owner decision 3).\n")

    a("## 4. Functions F1-F7 in REC\n")
    a("| function | how |\n|---|---|")
    for f, txt in functions_rec():
        a(f"| {f} {FUNC_NAMES[f]} | {txt} |")
    a("")

    a("## 5. Procedures and seconds (gloves)\n")
    a(f"Unit times from `attach_system.PROCEDURES` (the method behind `meat_haul.DETACH_S`): one hook = "
      f"{HOOK_S:.0f} s (bag-off step 3, 4 hooks in 16 s); one two-hook IM strap with its cam = {IM_STRAP_S:.0f} s "
      f"(float step 3), so a one-hook IM strap = {IM_STRAP_S - HOOK_S:.0f} s. ASSUMPTION: a strap end through a "
      f"port {PORT_S} s, kit out {KIT_S} s.\n")
    a("| procedure | today, as documented | today, IM straps counted | REC |\n|---|---:|---:|---:|")
    a(f"| F1 meat into the bag (strap steps) | - | {sec['F1']['today']} s | {sec['F1']['rec']} s "
      f"(door route {sec['F1']['rec_door']} s) |")
    a(f"| bag off (limit 120 s) | {BAG_OFF_S} s | {sec['bag_off']['today']} s | {sec['bag_off']['rec']} s |")
    a(f"| bag on | {BAG_ON_S} s | {sec['bag_on']['today']} s | {sec['bag_on']['rec']} s |")
    a(f"| F2 bag-off haul | {sec['F2']['today_documented']} s | {sec['F2']['today']} s | {sec['F2']['rec']} s |")
    a(f"| F3 float | {sec['F3']['today_documented']} s | {sec['F3']['today']} s | {sec['F3']['rec']} s |\n")
    a("Today's documented bag-off (52 s) never unhooks the IM straps, yet they hook to the fairlead eyes through the "
      "B-12 ports; the middle column counts them (6 hooks). REC is about as fast as today in F2/F3 and slower on "
      "bag-on because W1-W3 now go on with the bag; it is faster in F1 (3 hooks instead of 6).\n")
    for k, title in (("F1", "F1 meat in the bag"), ("F2", "F2 bag-off haul"), ("F3", "F3 float")):
        a(f"**{title}, REC:**\n")
        for i, (txt, s_) in enumerate(pr["rec"][k], 1):
            a(f"{i}. {txt} ({s_:.0f} s)")
        a("")
    a("**F4 carry compression, REC:** pack; hook W1-W3 at their left G-hooks; pull each tail snug at the right "
      "ladder lock; tuck the tail in its keeper loop. Small load: pull further; a W3 tail can go once more round.\n")
    a("**F5 side carry, REC:** tripod feet in the IMP-8 cup, legs under W1 and W2 on the right gore, cinch; poles or "
      "a pad on the left the same way; spotter in IMP-1 on the left gusset.\n")
    a("**F6 door, REC:** unhook W1/W2, unzip, load, zip, re-hook W1/W2 and cinch before the next heavy carry. The zip "
      "is closed after the straps are snug (never used as the clamp).\n")
    a("**F7, REC:** unchanged roll-top and pouch straps.\n")

    a("## 6. Patent guardrails\n")
    a("| architecture | guardrail | status | note |\n|---|---|---|---|")
    for k in ("a", "b1", "b2", "c", "rec"):
        for g, st, note in patent_check(k):
            a(f"| {k} | {g} | {st} | {note} |")
    a("\nNone of the candidates adds a fabric panel, moves a lifter or routes bag webbing behind the spreader. FTO "
      "read before release is unchanged.\n")

    a("## 7. Load paths for BL-010\n")
    a("Factored loads as the existing analyses give them; rated values from records or the ASSUMPTIONs in "
      "`strap_arch.py`. Not certified here.\n")
    a("| location | direction | factored N | part | rated N | rated / factored | note |\n"
      "|---|---|---:|---|---:|---:|---|")
    for lp in load_paths():
        rr = lp["rated_n"] / lp["n"] if lp["n"] and not math.isnan(lp["rated_n"]) else float("nan")
        a(f"| {lp['loc']} | {lp['dir']} | {_f(lp['n'], 0)} | {lp['part']} | {_f(lp['rated_n'], 0)} | {_f(rr, 2)} | "
          f"{lp['note']} |")
    a("\nUnchanged and not re-listed: IM/US/B-24 forces at the printed fairleads and anchors (same magnitude and "
      "direction), the hinge pins, the bag hooks, the hood and guys. The wing deletion removes load; it adds none to "
      "the frame beyond the small W1/W2 carry tension at the existing lash points.\n")

    a("## 8. Benchmark (frame side, BL-008 basis)\n")
    sysm = L.by_system(CONFIG, SIZE)
    fs_today = sum(sysm[k] for k in ("frame", "back", "belt", "harness")) + sysm["straps_meat"]
    fs_rec = fs_today - (S["today"]["meat_g"] - r["meat_g"])
    a(f"SG and Exo book their meat carry in the frame: SG Krux 1247 g with M belt and the integrated shelf; Exo K4 "
      f"frame 1332 g with its frame compression straps (`published_weight_definitions.md`). Ours, frame + back + belt "
      f"+ harness + base `straps_meat`: {fs_today:.1f} g today, {fs_rec:.1f} g with REC. The base meat-strap set alone "
      f"goes {S['today']['meat_g']:.1f} -> {r['meat_g']:.1f} g. The strap work closes "
      f"{fs_today - fs_rec:.0f} g of a gap of about {fs_rec - 1332:.0f} g to Exo; the rest is frame, back, belt and "
      "harness (BL-005/006/007/017).\n")

    a("## 9. Owner decisions\n")
    a("1. **Delete the side wings** (M-01, SH-06, 4 wing straps): W1-W3 do carry compression and side carry; door "
      "access then costs 16 s more through the door (not through the roll-top). IMP-1 moves to the left gusset.\n"
      "2. **B-24 float links as a meat-trip kit** outside the base weight (BL-008 already proposes it).\n"
      "3. **IM and US straps 38 -> 25 mm** with a rated 25 mm cam; the MEAT family is told apart by colour and cam, "
      "not width (changes the R-25 wording). Gated by the cam/hook proof tests below.\n")

    a("## 10. Assumptions that govern (each with the test that settles it)\n")
    a(f"- ASSUMPTION: 25 mm Al cam {CAM25_G:.0f} g, slip >= {CAM25_N:.0f} N. Test: 5 cams on the chosen 25 mm webbing, "
      "wet and at -20 C, no slip > 5 mm below 1100 N (the open IM/US hardware proof test, now on 25 mm).\n"
      f"- ASSUMPTION: 25 mm rated Al G-hook {G25R_G:.0f} g, {G25R_N:.0f} N break, {G25R_YIELD_N:.0f} N no-set "
      "(maker data, no record yet). Test: 5 hooks to 900 N with no set, 5 to break; FT-S1: a slack IM hook stays on "
      "its eye through 1 km of brush.\n"
      f"- ASSUMPTION: 25 mm box-X bartack {BARTACK25_N:.0f} N (38 mm value scaled by width). Test: the bartack proof "
      "test, on 25 mm.\n"
      "- ASSUMPTION: the IM left-end girth hitch fits the fairlead eye and, at IM2, the spreader notch, without "
      "reaching behind the spreader. Test: fit on the first printed fairleads (BL-010 drawing check).\n"
      "- ASSUMPTION: B-12 port slot opened 6 -> 12 mm passes the 25 mm G-hook and still self-closes; mass "
      "unchanged. Test: pattern-maker sample.\n"
      f"- ASSUMPTION: strap end through a port {PORT_S} s, kit out {KIT_S} s. Test: glove timing on the first bag.\n"
      "- ASSUMPTION: W1/W2 hold a tripod and a spotter pod as well as the wings did. Test: FT-S2, 5 km of side-hill "
      "with tripod and spotter, no shift > 20 mm.\n"
      "- ASSUMPTION (b1 cut lengths): haul path linear in z between the geometry.yaml wraps. Only b1 uses it.\n"
      "- Inherited: the float clamp 150 N hand cinch; compression strap demand from team C's hoop sim (25.6 N at 1 g).\n")

    a("## 11. Found, not fixed\n")
    a("- `attach_system.PROCEDURES['bag_off']` (52 s) has no step that unhooks IM1-IM3 from the eyes, though the "
      "straps run through the B-12 ports to those eyes; counted, today's bag-off is about 76 s.\n"
      "- The 38 mm sliding-gate meat hook is booked at 9 g (ASSUMPTION); the one rated 38 mm Al G-hook found is "
      "16 g at 1.5 kN (AustriAlpin DY38K). The HAUL G-hook is booked at 4 g with no rating; rated 25 mm aluminium "
      "hooks found are 8-13 g. Today's ledger may be light by roughly 40-60 g across the 13 G-hooks and 6 meat "
      "hooks if rated parts are bought (materials-engineer to add records).\n"
      "- The W1-W3 G-hook has no rating anywhere, yet W1-W3 carry the float clamp (`load_path` True in the ledger).\n")

    a("## 12. Screenshots\n")
    for s in shots:
        a(f"- `{s}`")
    return "\n".join(L_) + "\n"


def write() -> dict:
    shots = [f"outputs/screens/{DATE}_BL003_1.png", f"outputs/screens/{DATE}_BL003_2.png"]
    chart_sideviews(ROOT / shots[0])
    chart_mass(ROOT / shots[1])
    (ANALYSIS / "strap_architecture.md").write_text(report(shots))
    return {"doc": str(ANALYSIS / "strap_architecture.md"), "shots": [str(ROOT / s) for s in shots]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    b = ledger_baseline()
    print(f"ledger straps_meat + straps_compression = {b['total']:.1f} g")
    for k, s in savings().items():
        print(f"{k:6s} base {s['base_g']:7.1f}  kit {s['kit_g']:5.1f}  saved base {s['saved_base_g']:6.1f}  "
              f"removed {s['saved_removed_g']:6.1f}  hw {s['hw_count']}/{s['hw_types']}  ops {s['ops']}")
    print(procedures()["seconds"])
    if "--write" in argv:
        print(write())


if __name__ == "__main__":
    main()
