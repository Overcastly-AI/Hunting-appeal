"""BL-078: the PAHT-CF coupons that decide the H1 frame, and the SAFETY HOLD on the released H1 (manufacturing-engineer,
2026-11-25).

    python designs/pack_5200/frame_h1_paht_coupons.py            # write print/frame_h1/COUPONS_PAHT.md, the coupon
                                                                   # STLs and outputs/release/frame_h1_paht_coupons/
    python designs/pack_5200/frame_h1_paht_coupons.py --check    # build in memory, print the checks, write nothing

BL-077 (``iter1/frame/bl077.json``) re-checked the released PAHT-CF H1 on the honest hot/wet B-basis and booked its
strength row below goal. The orchestrator's call (DECISIONS 2026-11-25): measure before redesigning. This module turns
the BL-077 coupon rows (``coupons``) into the owner's next print and next session:

* CA-3-PAHT (Z tensile + short-beam shear, hot/wet n 10 + dry n 6), CA-1-PAHT (short-beam-shear fatigue at 40 C),
  CA-4-PAHT (3-point bend modulus 23 C dry / 40 C conditioned / 60 C dry); then, only if the coupons pick H1c, the two
  first-frame checks HB-6b-SLV and CLEVIS-SHARE-B-PAHT;
* two print jobs, each with a 15 x 15 mm prime pillar and a per-layer dwell so every layer takes at least the frame
  layer time (BL-079: re-derived at the real 0.20 mm layers; dummy towers dropped);
* conditioning to constant mass over saturated salt and a 40 C test method on kit equipment (<= USD 50);
* a results sheet that says which frame each outcome points to (H1 as is, H1c, or a redesign), from the BL-077 lines;
* the SAFETY HOLD text and the per-test hold marks the build pack (``frame_h1_build.py``) and the kit use.

Register rows, beginner sheets and results rows are built here (``register_rows``, ``guide_steps``,
``results_items``) and written by ``physical_test_kit.py`` (session G0, release PAHT-COUPONS), exactly as the parked
PPA-CF path does (``frame_h1p_build.py``, whose tower and PDF helpers are reused).

Every pass line is read from ``bl077.json`` when this runs (``pass_lines``), never typed. Units mm, g, N, MPa
internally; inches, oz, lb, F shown beside them.
"""
from __future__ import annotations

import argparse
import csv
import functools
import inspect
import json
import math
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import yaml  # noqa: E402

import frame_h1p_build as H1P  # noqa: E402  (tower mesh, rasteriser, PDF blocks: generic helpers of the parked path)

DATE = "2026-11-25"
TICKET = "BL-078"
BL077 = HERE / "iter1" / "frame" / "bl077.json"
BL077_MD = HERE / "iter1" / "frame" / "bl077.md"
LOAD_STD = HERE / "analysis" / "load_standard.md"
MAT = ROOT / "data" / "materials"
PRINT = HERE / "print" / "frame_h1"
CP_DIR = PRINT / "coupons_paht"
REL = ROOT / "outputs" / "release" / "frame_h1_paht_coupons"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261125_bl078"

IN = 25.4
OZ = 28.3495
G = 9.81
N_PER_LBF = 4.44822
NM_PER_INLBF = 0.112985

# --- coupon layout (BL-074 rules of the PPA path, kept the same so both paths cut coupons the same way)
KERF = H1P.KERF          # ASSUMPTION CUT (BL-074): saw kerf + sanding allowance between bars
TRIM = H1P.TRIM          # ASSUMPTION CUT (BL-074): edge strip trimmed off every block side
FACE = H1P.FACE          # one layer-ish faced off top and bottom of the SBS block (mid-plane stays on a layer line)
SPARES = H1P.SPARES      # ASSUMPTION SPARE (BL-074): one spare per coupon set
WASTE = H1P.WASTE        # BL-053 / BL-070 filament rule (+8 % purge, brim, skirt)
TOWER_MIN_MM2 = H1P.TOWER_MIN_MM2
TOWER_BAND_MM = H1P.TOWER_BAND_MM
LEVER_RATIO = H1P.LEVER_RATIO
CELL_KG = H1P.CELL_KG
COMB_N = 10              # bl077.json CA-3-PAHT: 'printed standing in a 10-bar comb tied at the grips'
COMB_GAP = 4.0           # ASSUMPTION COMB: 4 mm between the bars of a comb (bridged by the ties)
TIE_H = 2.0              # ASSUMPTION COMB: tie strip height at the bottom (on the plate) and near the top grip
TRAVELLER = (60.0, 60.0)  # BL-074 traveller plate plan size; thickness = the thickest conditioned coupon
FLEX_SPAN_RATIO = 16.0   # ISO 178: span = 16 x thickness
E_PRE_KG, E_ADD_KG = 0.5, 2.0   # ASSUMPTION E-LOAD: bend-modulus weights kept to ~1/3 of the hot/wet XY strength
BOX_KIT_USD = 35.0       # the kit's '40 C box: cooler + 60 W heater + thermostat' line (physical_test_kit.shopping)
ITC308 = {"usd": 37.99, "src": "eBay US listing 'Inkbird Thermostat Temperature Controller ITC-308' USD 37.99 "
                               "(store windemomo, search snapshot 2026-11-25, https://www.ebay.com/str/windemomo); "
                               "other US listings USD 25-38"}

# The three outcomes the coupons choose between (DECISIONS 2026-11-25 orchestrator call)
OUT_H1 = "H1 as is"
OUT_H1C = "H1c"
OUT_RE = "redesign"

SAFETY_HOLD = "SAFETY HOLD"


# ============================================================================ sources
@functools.lru_cache(maxsize=None)
def b77() -> dict:
    return json.loads(BL077.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def record(rid: str) -> dict:
    for p in MAT.rglob(f"{rid}.yaml"):
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    raise KeyError(rid)


def paht() -> dict:
    return record("pa12_cf_fdm_paht")["properties"]


def rho() -> float:
    return paht()["density_kg_m3"] / 1e6          # g/mm3


def usd_per_g() -> float:
    return float(paht()["print_cost_usd_per_g"])


def coupons() -> dict:
    return {c["id"]: c for c in b77()["coupons"]}


def rows_by_key() -> dict:
    return {r["key"]: r for r in b77()["rows"]}


def _num(pat: str, txt: str, grp: int = 1) -> float:
    m = re.search(pat, txt)
    assert m, (pat, txt[:200])
    return float(m.group(grp))


def frame_layer_h() -> float:
    """The layer height of the H1 frame profile (BUILD_H1 section 3, frame_h1_build.PROFILE_TXT)."""
    import frame_h1_build as FB
    return _num(r"([0-9.]+) mm\s+layers", FB.PROFILE_TXT)


def rate_rule() -> tuple[float, float]:
    """The BL-053 layer-time rule t = A h / rate x k: rate and k as bl077 used them (bl073_hotwet.layer_time_s)."""
    from huntkit.gendesign import bl073_hotwet as B
    p = inspect.signature(B.layer_time_s).parameters
    return float(p["rate_mm3_s"].default), float(p["k"].default)


def proof_level() -> dict:
    """HA-LS-1 rev C T1 (b): the frame's static proof load (load_standard.md 5.3)."""
    t = LOAD_STD.read_text(encoding="utf-8")
    m = re.search(r"\(b\) \*\*(\d+) lb / (\d+) kg\*\* \(= ([0-9.]+) x rated", t)
    assert m, "T1 (b) proof row not found in load_standard.md"
    return {"lb": float(m.group(1)), "kg": float(m.group(2)), "x_rated": float(m.group(3))}


@functools.lru_cache(maxsize=None)
def pass_lines() -> dict:
    """Every pass line and count of the BL-077 coupons, read from the bl077.json text and fields (never typed here)."""
    c = coupons()
    c3, c1, c4, hb, cs = c["CA-3-PAHT"], c["CA-1-PAHT"], c["CA-4-PAHT"], c["HB-6b-SLV"], c["CLEVIS-SHARE-B-PAHT"]
    d = b77()
    R = rows_by_key()
    w3, p3 = c3["what"], c3["pass"]
    return {
        # CA-3-PAHT
        "z_line": _num(r"\(a\) hot/wet Z B-basis >= ([0-9.]+) MPa", p3),
        "z_hw": _num(r"\(= ([0-9.]+) / ([0-9.]+) rounded up, the H1c body rows", p3),
        "m_body": _num(r"\(= ([0-9.]+) / ([0-9.]+) rounded up, the H1c body rows", p3, 2),
        "z_joint": _num(r">= ([0-9.]+) MPa also lifts the open z 234 joint fatigue", p3),
        "joint_now": _num(r"joint fatigue \(([0-9.]+)\)", p3),
        "sbs_line": _num(r"\(b\) hot/wet SBS B-basis >= ([0-9.]+) MPa", p3),
        "tau_hw": _num(r"tau_hw ([0-9.]+) /", p3),
        "sbs_joint": _num(r">= ([0-9.]+) for the joint", p3),
        "knock_booked": _num(r"hot/wet / dry Z \(booked ([0-9.]+)\)", p3),
        "k10": _num(r"k ([0-9.]+) at n (\d+)", c3["statistic"]),
        "k_n": _num(r"k ([0-9.]+) at n (\d+)", c3["statistic"], 2),
        "k_src": c3["statistic"].split("(", 1)[1].rstrip(")"),
        "n_z_hw": c3["n"]["z_hw"], "n_z_dry": c3["n"]["z_dry"], "n_sbs_hw": c3["n"]["sbs_hw"], "n_sbs_dry": c3["n"]["sbs_dry"],
        "z_t": _num(r"1BA, ([0-9.]+) mm thick", w3),
        "z_dry_mpa": _num(r"dry pull ([0-9.]+) MPa x ([0-9.]+) mm2 = (\d+) N", w3),
        "z_gauge_mm2": _num(r"dry pull ([0-9.]+) MPa x ([0-9.]+) mm2 = (\d+) N", w3, 2),
        "z_dry_n": _num(r"dry pull ([0-9.]+) MPa x ([0-9.]+) mm2 = (\d+) N", w3, 3),
        "comb_n": _num(r"in a (\d+)-bar comb", w3),
        "sbs_l": _num(r"proportions ([0-9.]+) x ([0-9.]+) x ([0-9.]+)", w3),
        "sbs_w": _num(r"proportions ([0-9.]+) x ([0-9.]+) x ([0-9.]+)", w3, 2),
        "sbs_t": _num(r"proportions ([0-9.]+) x ([0-9.]+) x ([0-9.]+)", w3, 3),
        "layer_s": _num(r"every layer >= (\d+) s", w3),
        "layer_s_json": float(d["layer_time_median_s"]),
        "layer_h_bl077": _num(r"at the BUILD_H1 ([0-9.]+) mm layers", w3),
        "layer_s_bl077_0p3": float(d["layer_time"]["bl077_floor_s_at_0p3"]),
        "cond_c": _num(r"saturated NaCl HEATED TO (\d+) C", w3),
        "cond_rh": _num(r"HEATED TO \d+ C \(([0-9.]+) % RH", w3),
        "cond_dm_pct": _num(r"mass changes < ([0-9.]+) % in 24 h", w3),
        "uptake_tds_pct": _num(r"against the TDS ([0-9.]+) %", w3),
        "test_c": _num(r"tested at (\d+) \+/- (\d+) C", w3),
        "test_tol": _num(r"tested at (\d+) \+/- (\d+) C", w3, 2),
        "dry_test_c": _num(r"within 24 h at (\d+) C", w3),
        # CA-1-PAHT
        "c1_n_fat": c1["n"]["fatigue"], "c1_n_static": c1["n"]["static"],
        "c1_smax": float(c1["smax_test_mpa"]), "c1_peak_n": float(c1["peak_load_n"]),
        "c1_factor": _num(r"at ([0-9.]+) x Smax", c1["pass"]),
        "c1_cycles": float(re.search(r"run out to (1e\d)", c1["pass"]).group(1)),
        "c1_r": _num(r"R ([0-9.]+), <= (\d+) Hz", c1["what"]),
        "c1_hz_max": _num(r"R ([0-9.]+), <= (\d+) Hz", c1["what"], 2),
        "c1_nose_d": _num(r"D(\d+) loading nose, two D(\d+) supports, span (\d+)", c1["what"]),
        "c1_pin_d": _num(r"D(\d+) loading nose, two D(\d+) supports, span (\d+)", c1["what"], 2),
        "c1_span": _num(r"D(\d+) loading nose, two D(\d+) supports, span (\d+)", c1["what"], 3),
        "c1_temp": _num(r"<= \d+ Hz, (\d+) \+/- (\d+) C", c1["what"]),
        "c1_tol": _num(r"<= \d+ Hz, (\d+) \+/- (\d+) C", c1["what"], 2),
        # CA-4-PAHT
        "c4_l": _num(r"XY bars (\d+) x (\d+) x (\d+)", c4["what"]),
        "c4_w": _num(r"XY bars (\d+) x (\d+) x (\d+)", c4["what"], 2),
        "c4_t": _num(r"XY bars (\d+) x (\d+) x (\d+)", c4["what"], 3),
        "c4_n": c4["n"]["per_condition"],
        "c4_hot_c": _num(r"; (\d+) C dry$", c4["what"]),
        "c4_e_ratio": _num(r"mean of \d+ >= ([0-9.]+) \(the H1c buckling need", c4["pass"]),
        "c4_flex_booked": _num(r"vs the booked ([0-9.]+)", c4["pass"]),
        # HB-6b-SLV
        "slv_lo": _num(r"boss back by ([0-9.]+)-([0-9.]+) mm", hb["what"]),
        "slv_hi": _num(r"boss back by ([0-9.]+)-([0-9.]+) mm", hb["what"], 2),
        "slv_nm": _num(r"plates seated, ([0-9.]+) N m", hb["what"]),
        # CLEVIS-SHARE-B-PAHT
        "share_max": _num(r"measured share <= ([0-9.]+)", cs["pass"]),
        "share_json": float(d["clevis_share_max"]),
        # BL-079: H1 as is (bl077.json h1_as_is; sleeved hip, and the inserts kept)
        **h1_lines(),
        # rows (honest basis), for the hold banner and the outcome table
        "h1_strength": R["strength"]["h1_hw"], "strength_goal": R["strength"]["goal"],
        "h1_r1": R["R1"]["h1_hw"], "h1c_r1": R["R1"]["after"],
    }


def h1_lines() -> dict:
    """The BL-079 H1-as-is lines (bl077.json h1_as_is), the sleeved hip and the inserts kept, three routes each."""
    h = b77()["h1_as_is"]
    out = {"h1_e_ratio": float(h["e_ratio_min"]), "h1_plaus": h["plausibility"], "h1_verdict": h["verdict"],
           "h1_z_typ": float(h["plausible"]["z_typ_mpa"]), "h1_z_best": float(h["plausible"]["z_best_mpa"]),
           "h1_fat_cited": h["plausible"]["fat_cited"]}
    for lab in ("sleeved", "inserts"):
        A, Bm, C = (h[lab][r] for r in ("layer_route", "ratio_route", "all_route"))
        out[f"h1_{lab}_ok"] = bool(A["reachable"])
        out[f"h1_{lab}_z_b_mpa"] = float(A["z_b_mpa"]) if A["reachable"] else None
        out[f"h1_{lab}_sbs_b_mpa"] = float(A["sbs_b_mpa"]) if A["reachable"] else None
        out[f"h1_{lab}_sat"] = ", ".join(f"{k} {v:g}" for k, v in A.get("at_fmax", {}).items())
        out[f"h1_{lab}_ratio"] = float(Bm["fat_ratio_min"])
        out[f"h1_{lab}_ratio_z"] = Bm.get("z_b_mpa")
        out[f"h1_{lab}_ratio_sbs"] = Bm.get("sbs_b_mpa")
        out[f"h1_{lab}_all"] = (float(C["xy_b_mpa"]), float(C["z_b_mpa"]), float(C["sbs_b_mpa"]))
    c1 = coupons()["CA-1-PAHT"]
    out["c1_n_fat_h1"] = int(c1["n"].get("fatigue_h1", 0))
    out["h1_c1_smax"] = float(c1.get("smax_h1_mpa", 0.0))
    out["h1_c1_peak_n"] = float(c1.get("peak_h1_n", 0.0))
    out["h1_xy_limited"] = [v["why"] for v in h["xy_limited"].values()]
    return out


def pass_lines_recomputed() -> dict:
    """The same lines from bl077.json's numeric fields (the tests compare them with the text)."""
    d = b77()
    R = rows_by_key()
    c = coupons()
    m_body = min(R["R1"]["after"], R["static_fatigue"]["after"])

    def up(x, st=0.1):                     # BL-079: every minimum line rounds UP
        return math.ceil(x / st - 1e-9) * st
    return {"z_line": up(d["basis"]["hw"]["z"] / m_body), "m_body": m_body, "z_hw": d["basis"]["hw"]["z"],
            "z_joint": c["CA-3-PAHT"]["need_z_mpa"], "sbs_line": up(d["basis"]["hw"]["tau"] / m_body),
            "tau_hw": d["basis"]["hw"]["tau"], "sbs_joint": c["CA-3-PAHT"]["need_sbs_mpa"],
            "knock_booked": d["basis"]["knock_z"], "joint_now": R["joint_fatigue"]["after"],
            "layer_s": d["layer_time_median_s"], "share_max": d["clevis_share_max"]}


# ============================================================================ coupon geometry
def _flex() -> dict:
    pl = pass_lines()
    t = pl["c4_t"]
    return {"L": pl["c4_l"], "w": pl["c4_w"], "t": t, "span": FLEX_SPAN_RATIO * t}


def _rnd_layers(h: float, lh: float) -> int:
    return int(round(h / lh))


@functools.lru_cache(maxsize=None)
def blocks() -> dict:
    """SBS block (bars sawn from it), the Z combs, the bend bars and the traveller plate, from the JSON counts."""
    pl = pass_lines()
    lh = frame_layer_h()
    L, w, t = pl["sbs_l"], pl["sbs_w"], pl["sbs_t"]
    n_sbs = int(pl["n_sbs_hw"] + pl["n_sbs_dry"] + SPARES + pl["c1_n_fat"] + pl["c1_n_static"] + SPARES
                + pl["c1_n_fat_h1"])
    cols = 9
    rows = math.ceil(n_sbs / cols)
    h_sbs = round((t + 2 * FACE) / lh) * lh
    n_z = int(pl["n_z_hw"] + pl["n_z_dry"] + SPARES)
    combs = [min(int(pl["comb_n"]), n_z - i) for i in range(0, n_z, int(pl["comb_n"]))]
    fx = _flex()
    n_fx = int(3 * pl["c4_n"] + SPARES)
    return {"sbs": {"n": n_sbs, "cols": cols, "rows": rows, "x": cols * (w + KERF) + 2 * TRIM,
                    "y": rows * (L + KERF) + 2 * TRIM, "h": h_sbs, "layers": _rnd_layers(h_sbs, lh),
                    "mid_line": _rnd_layers(h_sbs, lh) // 2},
            "z": {"n": n_z, "combs": combs, "t": pl["z_t"]},
            "flex": {"n": n_fx, **fx},
            "traveller": {"x": TRAVELLER[0], "y": TRAVELLER[1], "h": max(fx["t"], pl["sbs_t"] + 2 * FACE)}}


def iso1ba_outline():
    """ISO 527-2 type 1BA outline (overall 75, ends 10 wide, narrow 5 wide over 30, R 30 transitions) in (x, z),
    x centred, z from 0 at the lower grip end."""
    from shapely.geometry import Polygon
    l3, l1, b2, b1, r = 75.0, 30.0, 10.0, 5.0, 30.0
    d = (b2 - b1) / 2
    lt = math.sqrt(r * r - (r - d) ** 2)                 # horizontal length of one R 30 transition
    z_tab = (l3 - l1 - 2 * lt) / 2
    pts = []
    zs = [0.0, z_tab]
    for i in range(1, 13):
        zs.append(z_tab + lt * i / 12)
    zs += [l3 - z_tab - lt * (12 - i) / 12 for i in range(0, 13)] + [l3]

    def half(z):
        if z <= z_tab or z >= l3 - z_tab:
            return b2 / 2
        if z_tab + lt <= z <= l3 - z_tab - lt:
            return b1 / 2
        u = (z - z_tab) if z < l3 / 2 else (l3 - z_tab - z)
        return b1 / 2 + r - math.sqrt(max(r * r - (lt - u) ** 2, 0.0))
    zs = sorted(set(round(z, 6) for z in zs))
    pts = [(half(z), z) for z in zs] + [(-half(z), z) for z in reversed(zs)]
    return Polygon(pts), {"l3": l3, "l1": l1, "b2": b2, "b1": b1, "r": r, "z_tab": z_tab, "lt": lt}


def comb_outline(n: int):
    """Front view (x, print height) of a comb of n 1BA bars with its two tie strips."""
    from shapely.affinity import translate
    from shapely.geometry import box
    from shapely.ops import unary_union
    poly, g = iso1ba_outline()
    pitch = g["b2"] + COMB_GAP
    shapes = [translate(poly, xoff=i * pitch) for i in range(n)]
    x0, x1 = -g["b2"] / 2, (n - 1) * pitch + g["b2"] / 2
    shapes.append(box(x0, 0.0, x1, TIE_H))                                 # bottom tie, inside the lower grip
    zt = g["l3"] - g["z_tab"] / 2 - TIE_H / 2
    shapes.append(box(x0, zt, x1, zt + TIE_H))                             # top tie, inside the upper grip
    return unary_union(shapes)


def comb_mesh(n: int):
    """A comb of n standing 1BA bars, z_t thick, tied at the bottom (a strip on the plate) and near the top grip."""
    import numpy as np
    import trimesh
    m = trimesh.creation.extrude_polygon(comb_outline(n), pass_lines()["z_t"])               # outline in x-y, thickness along z
    rot = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)  # y -> z (standing)
    m.apply_transform(rot)
    m.apply_translation(-m.bounds[0])
    return m


def _layer_area(t, lh: float):
    from huntkit.gendesign.bl073_hotwet import layer_profile
    return layer_profile(t, lh)["area"]


def _area_req() -> float:
    pl = pass_lines()
    rate, k = rate_rule()
    return pl["layer_s"] * rate / (frame_layer_h() * k)


@functools.lru_cache(maxsize=None)
def jobs() -> list[dict]:
    """Job A: the SBS block. Job B: the Z combs, the bend bars and the traveller plate. Each with a 15 x 15 mm prime
    pillar and a per-layer park-and-dwell so every layer takes >= the frame layer time (bl077.json, BL-079 at the
    real 0.20 mm profile) by the BL-053 rule."""
    import numpy as np
    lh = frame_layer_h()
    rate, k = rate_rule()
    bk = blocks()
    r = rho()

    def box_item(nm, kind, x, y, h, n=1):
        layers = _rnd_layers(h, lh)
        return {"name": nm, "kind": kind, "count": n, "area": np.full(layers, x * y), "g": x * y * layers * lh * r}

    s, fx, tv = bk["sbs"], bk["flex"], bk["traveller"]
    items_a = [box_item(f"SBS block {s['x']:.0f} x {s['y']:.0f} x {s['h']:.1f} mm, {s['n']} bars (`coupons_paht/block_sbs.stl`)",
                        "sbs", s["x"], s["y"], s["h"])]
    items_b = []
    for i, n in enumerate(bk["z"]["combs"], 1):
        cm = comb_mesh(n)
        items_b.append({"name": f"Z comb {i}: {n} standing 1BA bars, {pass_lines()['z_t']:g} mm thick (`coupons_paht/z_comb_{n}.stl`)",
                        "kind": "z", "count": 1, "area": _layer_area(cm, lh), "g": cm.volume * r, "bars": n})
    items_b.append(box_item(f"bend bar {fx['L']:.0f} x {fx['w']:.0f} x {fx['t']:.0f} flat (`coupons_paht/bend_bar.stl`)", "flex",
                            fx["L"], fx["w"], fx["t"], fx["n"]))
    items_b.append(box_item(f"traveller plate {tv['x']:.0f} x {tv['y']:.0f} x {tv['h']:.0f} (`coupons_paht/traveller.stl`)",
                            "traveller", tv["x"], tv["y"], tv["h"]))
    target = pl_layer_s()
    J = []
    for job, title, items in (("A", "SBS block (CA-3-PAHT and CA-1-PAHT short-beam bars)", items_a),
                              ("B", "Z combs (CA-3-PAHT), bend bars (CA-4-PAHT), traveller plate", items_b)):
        n = max(len(it["area"]) for it in items)
        a = np.zeros(n)
        for it in items:
            a[:len(it["area"])] += it["count"] * it["area"]
        # BL-079: no dummy tower. A 15 x 15 mm prime pillar (TOWER_MIN_MM2) takes the ooze after each dwell; the
        # layer time is held by a per-layer park-and-dwell (bl077.json layer_time.method), one dwell per job:
        # dwell = target - the job's shortest printed layer, rounded up to 1 s, so every layer >= target.
        steps = [(0.0, n * lh, TOWER_MIN_MM2)]
        per = np.full(n, TOWER_MIN_MM2)
        tower_g = n * lh * TOWER_MIN_MM2 * r
        parts_g = sum(it["count"] * it["g"] for it in items)
        printed_t = (a + per) * lh / rate * k
        dwell = float(max(0, math.ceil(target - float(printed_t.min()))))
        layer_t = printed_t + dwell
        fil = (parts_g + tower_g) * (1 + WASTE)
        J.append(dict(job=job, title=title, items=items, layers=n, height=n * lh, tower_steps=steps, tower_g=tower_g,
                      parts_g=parts_g, support_g=0.0, filament_g=fil, usd=fil * usd_per_g(), dwell_s=dwell,
                      min_printed_s=float(printed_t.min()), min_layer_s=float(layer_t.min()),
                      median_layer_s=float(np.median(layer_t)), print_h=float(layer_t.sum()) / 3600.0,
                      tower_max_mm2=TOWER_MIN_MM2, mat="PAHT-CF",
                      fallback_tower_g=float(np.maximum(_area_req() - a, TOWER_MIN_MM2).sum() * lh * r)))
    return J


def fallback_tower_usd() -> float:
    """Filament of the BL-078 style dummy towers at the BL-079 floor (the fallback if the dwell oozes)."""
    return sum(j["fallback_tower_g"] for j in jobs()) * (1 + WASTE) * usd_per_g()


def pl_layer_s() -> float:
    return pass_lines()["layer_s"]


@functools.lru_cache(maxsize=None)
def coupon_plan() -> dict:
    J = jobs()
    rows = []
    for j in J:
        for it in j["items"]:
            rows.append({"job": j["job"], "item": it["name"].split(" (`")[0], "count": it["count"],
                         "g_each": round(it["g"], 1), "material": "PAHT-CF"})
        rows.append({"job": j["job"], "item": f"dummy tower tower_{j['job']}.stl (max {j['tower_max_mm2']:.0f} mm2)",
                     "count": 1, "g_each": round(j["tower_g"], 1), "material": "PAHT-CF"})
    g = sum(j["filament_g"] for j in J)
    return {"jobs": J, "rows": rows, "filament_g": round(g, 1), "filament_usd": round(g * usd_per_g(), 2),
            "area_req_mm2": _area_req(), "print_h": round(sum(j["print_h"] for j in J), 1),
            "tower_g": round(sum(j["tower_g"] for j in J) * (1 + WASTE), 1)}


# ============================================================================ cost (RUBRIC 1b: proving prints <= USD 150)
@functools.lru_cache(maxsize=None)
def cost() -> dict:
    """The coupon job, priced. Filament at the record price; the bl077 new items; the kit lines the job needs. The
    40 C box is a kit line already; it is shown both ways so the cap holds even if it is not built yet."""
    cp = coupon_plan()
    cc = b77()["coupon_cost"]
    lines = [{"item": f"PAHT-CF filament, jobs A + B with 15 x 15 mm prime pillars (no dummy towers: layer time by dwell) and +{WASTE:.0%} waste ({cp['filament_g']:.0f} g)",
              "usd": cp["filament_usd"], "source": f"record pa12_cf_fdm_paht print_cost_usd_per_g {usd_per_g():g} "
                                                    f"({paht()['print_cost_basis']})", "kind": "new"}]
    for nm, usd, src in cc["new_items"]:      # bl077: ASTM D2344 pins (D6 nose, D3 supports) and the NaCl (BL-079)
        lines.append({"item": nm, "usd": float(usd), "source": f"bl077.json coupon_cost: {src}", "kind": "new"})
    lines += [
        {"item": "jewellery scale 0.001 g, 50 g (traveller to constant mass)", "usd": 25.0,
         "source": "ASSUMPTION (shop price, check at purchase): kit shopping_list line (BL-074)", "kind": "new"},
        {"item": "2 L sealed glass jar with a wire rack (salt conditioning jar)", "usd": 9.0,
         "source": "ASSUMPTION (shop price, check at purchase): the BL-074 'salt + jar' kit line USD 12 less the salt USD 3", "kind": "new"},
        {"item": "40 C box: cooler + 60 W heater + thermostat (kit B; also runs 50 C and 60 C)", "usd": BOX_KIT_USD,
         "source": f"ASSUMPTION (shop price): kit shopping_list line; the thermostat alone, e.g. Inkbird ITC-308, USD {ITC308['usd']:.2f} ({ITC308['src']})",
         "kind": "kit"},
    ]
    new = sum(x["usd"] for x in lines if x["kind"] == "new")
    allin = new + sum(x["usd"] for x in lines if x["kind"] == "kit")
    cap = float(cc["cap_usd"])
    return {"lines": lines, "new_usd": round(new, 2), "all_in_usd": round(allin, 2), "cap_usd": cap,
            "within_cap": bool(allin <= cap), "bl077_usd": cc["usd"], "bl077_g": cc["grams"],
            "filament_g": cp["filament_g"], "filament_usd": cp["filament_usd"], "tower_g": cp["tower_g"]}


# ============================================================================ rig loads
def rig_check() -> dict:
    """Static bar loads of the coupon tests against the kit B 100 kg cell (the BL-074 convention: the bar force is
    compared with the cell rating, though the 4:1 lever puts a quarter of it on the cell)."""
    pl = pass_lines()
    fx = _flex()
    tau_dry = pl["z_dry_mpa"] * b77()["basis"]["tau_ratio"]          # same rule as the hot/wet line (TAU-VM)
    sbs_n = tau_dry * pl["sbs_w"] * pl["sbs_t"] / 0.75
    flex_n = 2 * paht()["bending_strength_xy_mpa"] * fx["w"] * fx["t"] ** 2 / (3 * fx["span"])
    loads = {"z bar static dry": pl["z_dry_n"], "sbs static dry": round(sbs_n, 0), "flex xy static dry": round(flex_n, 0),
             "sbs fatigue peak": pl["c1_peak_n"]}
    cell = CELL_KG * G
    return {"loads": loads, "cell_n": cell, "all_under_cell": all(v <= cell for v in loads.values()),
            "max_n": max(loads.values())}


# ============================================================================ the hold
HOLD_CLASS = {
    # test: (class, reason). HOLD = at or above its proof load, or a loaded carry; BELOW = loads the frame below its
    # proof level (may run under the hold, marked); NONE = no load on the frame.
    "IM3-EP": ("HOLD", "IM3 eye proof pull (2553 N): a proof load"),
    "W-PULL": ("HOLD", "lash-point proof pull (1.5 x factored): a proof load"),
    "MT-1cr": ("BELOW", "53 kg cradle pull, below the T1 proof"),
    "HB-6b": ("HOLD", "hip mount proof: a proof load"),
    "T9": ("BELOW", "68 kg hang, the rated load"),
    "T9-R3a": ("BELOW", "68 kg hang, the rated load"),
    "FIT-US": ("NONE", "fit check, no load"),
    "PIN-RET": ("BELOW", "50 N push on each pin; part (b) waits for the T9 walk, which is on hold"),
    "T9-R3c": ("BELOW", "strap length at the rated load"),
    "BP-3": ("HOLD", "includes a 5 min loaded walk: a loaded carry"),
    "RF-1": ("HOLD", "68 kg on three testers' backs: a loaded carry"),
    "T1": ("HOLD", "T1 (b) 300 lb and (c) 225 lb are the proof loads; T1 (a) 150 lb alone is below proof and may run"),
    "T1c-SW": ("HOLD", "top step 225 lb is the T1 (c) proof; the steps to 169 lb (77 kg) are below proof and may run"),
    "T3": ("HOLD", "side-hill 240 lb proof"),
    "T2": ("HOLD", "300 lb proof"),
    "MT-1c": ("HOLD", "stage 2 is a loaded walk (carry); stage 1 on the stand (0.4 -> 1.6 g, 600 cycles) is below proof and may run"),
    "CR-1": ("HOLD", "136 kg crown hang, at the proof load"),
    "BU-1": ("NONE", "crown kit change, no load"),
    "SP-1": ("NONE", "spreader proof: loads the spreader, not the PAHT-CF frame"),
    "T4a": ("HOLD", "2.0 g drop-step, the C2 limit (proof level)"),
    "T4b": ("BELOW", "150 lb set-down, the rated load"),
    "T4c": ("NONE", "empty pack drop, no load in the bag"),
    "T5": ("BELOW", "0.4 -> 1.6 g cycles (240 lb peak), below the 300 lb proof; on the stand only, nobody carries the frame after it"),
    "T5f": ("BELOW", "0 -> 1.6 g crank, below the proof"),
    "T2u": ("HOLD", "450 lb ultimate demo: over-proof"),
}
HOLD_GROUPS = ("G6", "G7")


def hold_mark(tid: str, group: str = "") -> tuple[str, str] | None:
    if tid in HOLD_CLASS:
        return HOLD_CLASS[tid]
    if group == "G7":
        return ("HOLD", "complete pack, loaded walks and fit: a loaded carry")
    return None


def hold_tag(cls: str) -> str:
    return {"HOLD": f"{SAFETY_HOLD}: do not run on the released H1",
            "BELOW": "BELOW PROOF: may run under the SAFETY HOLD",
            "NONE": "no frame load: may run under the SAFETY HOLD"}[cls]


def hold_text() -> str:
    pl = pass_lines()
    pf = proof_level()
    return (f"{SAFETY_HOLD} (BL-078, {DATE}). Do not carry the released PAHT-CF H1 frame with a load, and do not test it "
            f"at or above its proof load (HA-LS-1 T1 (b) {pf['lb']:.0f} lb / {pf['kg']:.0f} kg, {pf['x_rated']:g} x rated) "
            f"or over it, until the PAHT coupons CA-3-PAHT, CA-1-PAHT and CA-4-PAHT report. Why: on the honest hot/wet "
            f"basis BL-077 books the released H1 at strength {pl['h1_strength']:g} (goal {pl['strength_goal']:g}) and "
            f"cinch fatigue R1 {pl['h1_r1']:g}. Steps that load the frame below its proof level may still run; they "
            "are marked BELOW PROOF.")


def hold_block_md() -> list[str]:
    return [f"> **{hold_text().split('. ', 1)[0]}.** {hold_text().split('. ', 1)[1]}", ""]


# ============================================================================ outcomes (what the results mean)
def outcomes() -> list[dict]:
    """The decision table, every line from bl077.json. H1 as is has no coupon line in bl077.json: said so."""
    pl = pass_lines()
    d = b77()
    open_after = [f"{o['row']} {o['value']:g} (goal {o['goal']:g})" for o in d["open_rows"]
                  if not o["row"].startswith("z 234")]
    h1c_cost = d["cost"]["H1c_a2"]["per_frame_usd"] if "H1c_a2" in d["cost"] else None
    cap = d["cost"]["H1c_ti"]["cap_usd"]
    tail = (f" Still open on H1c whatever the coupons say: {'; '.join(open_after)}; H1c costs USD {h1c_cost:.2f} a frame "
            f"(A2 screws) against the USD {cap:.0f} cap (orchestrator / owner call).")
    rows = [
        {"if": (f"any of: CA-3-PAHT hot/wet Z B-basis < {pl['z_line']:g} MPa; hot/wet SBS B-basis < {pl['sbs_line']:g} MPa; "
                f"a CA-1-PAHT bar breaks before {pl['c1_cycles']:,.0f} cycles or a static SBS bar reads < {pl['sbs_line']:g} MPa; "
                f"CA-4-PAHT E ratio < {pl['c4_e_ratio']:g}"),
         "means": OUT_RE,
         "why": ("H1c fails too on the measured allowables (its body rows sit at R1 "
                 f"{pl['h1c_r1']:g} on the booked basis; these lines are where they reach goal). Back to the structural "
                 "engineer: DECISIONS 2026-11-25 alternatives (aluminium-tube frame with printed joints, or relax the cost cap).")},
        {"if": (f"CA-3-PAHT Z B-basis >= {pl['z_line']:g} and SBS B-basis >= {pl['sbs_line']:g} MPa, all CA-1-PAHT bars run "
                f"out and the static SBS >= {pl['sbs_line']:g}, CA-4-PAHT E ratio >= {pl['c4_e_ratio']:g}; but Z < "
                f"{pl['z_joint']:g} or SBS < {pl['sbs_joint']:g} MPa"),
         "means": f"{OUT_H1C} (z 234 joint still open)",
         "why": (f"H1c's body rows pass on measured allowables; its z 234 joint fatigue stays below goal "
                 f"({pl['joint_now']:g}).{tail} Then HB-6b-SLV and CLEVIS-SHARE-B-PAHT on the first H1c frame.")},
        {"if": (f"as above and Z B-basis >= {pl['z_joint']:g} MPa and SBS B-basis >= {pl['sbs_joint']:g} MPa"),
         "means": f"{OUT_H1C} (z 234 joint closed by the coupons)",
         "why": f"the z 234 joint fatigue reaches 1.0 as well.{tail} Then HB-6b-SLV and CLEVIS-SHARE-B-PAHT on the first H1c frame."},
    ]
    return [h1_outcome()] + rows


def h1_outcome() -> dict:
    """BL-079: the H1-as-is row, from bl077.json h1_as_is (every HA-LS-1 row of the released H1 at goal)."""
    pl = pass_lines()
    xy = "; ".join(pl["h1_xy_limited"])
    xa, za, sa = pl["h1_sleeved_all"]
    if not pl["h1_sleeved_ok"]:
        return {"if": ("no result these coupons can give: H1 as is needs EITHER a fatigue ratio >= "
                       f"{pl['h1_sleeved_ratio']:g} on every term (in-plane too) with Z >= {pl['h1_sleeved_ratio_z']:g} and "
                       f"SBS >= {pl['h1_sleeved_ratio_sbs']:g} MPa, OR XY >= {xa:g}, Z >= {za:g} and SBS >= {sa:g} MPa "
                       f"hot/wet B-basis (same with the inserts kept); and E ratio >= {pl['h1_e_ratio']:g}"),
                "means": f"{OUT_H1}: NOT cleared (the SAFETY HOLD on H1 stays)",
                "why": (f"bl077.json h1_as_is (BL-079): on Z / SBS alone the released H1 never reaches goal "
                        f"(saturates: {pl['h1_sleeved_sat']}; the in-plane terms govern once the layers are strong). "
                        f"CA-1-PAHT tests the shear ratio only, and the cited PA12-CF fatigue ratios are "
                        f"{pl['h1_fat_cited']}; the XY line is above the dry TDS mean. So the coupons choose between "
                        f"H1c and a redesign. Not closable by any coupon, on H1 as on H1c: {xy}.")}
    return {"if": (f"CA-3-PAHT hot/wet Z B-basis >= {pl['h1_sleeved_z_b_mpa']:g} MPa and SBS B-basis >= "
                   f"{pl['h1_sleeved_sbs_b_mpa']:g} MPa; the {pl['c1_n_fat_h1']} extra CA-1-PAHT bars all run out "
                   f"at Smax {pl['h1_c1_smax']:g} MPa (as well as the H1c set); CA-4-PAHT E ratio >= {pl['h1_e_ratio']:g}"),
            "means": f"{OUT_H1} (hip moved to sleeved through-bolts)",
            "why": (f"every H1 row reaches goal on the measured allowables, with the hip on the BL-077 sleeved "
                    f"through-bolts (HB-6b-SLV on the frame). Not closed by any coupon, on H1 as on H1c: {xy}. "
                    f"How likely: {pl['h1_plaus']} The SAFETY HOLD lifts only on this row.")}


# ============================================================================ sheets
def _mpa(x: float) -> str:
    return f"{x:g} MPa ({x * 145.038:,.0f} psi)"


def _n(x: float) -> str:
    return f"{x:,.0f} N ({x / G:.1f} kg on the scale, {x / N_PER_LBF:,.0f} lbf)"


def _c(x: float) -> str:
    return f"{x:g} C ({x * 9 / 5 + 32:.0f} F)"


def _mm(x: float, nd: int = 2) -> str:
    return f"{x:g} mm ({x / IN:.{3 if x < 10 else nd}f} in)"


def cond_steps() -> list[str]:
    """Conditioning to constant mass and the heat source (ASSUMPTION BOX-COND / DRYER-JAR)."""
    pl = pass_lines()
    tv = blocks()["traveller"]
    return [
        f"Salt jar: 2 L sealed glass jar, a 1 cm (0.4 in) layer of non-iodised salt (NaCl) wetted to a wet slush (some "
        f"undissolved salt must always show), a wire rack above it. Over saturated NaCl the air reads {pl['cond_rh']:g} % RH "
        f"at {_c(pl['cond_c'])} (Greenspan 1977, as bl077.json).",
        f"Heat: the jar goes in the kit's 40 C box with its thermostat set to {_c(pl['cond_c'])} (ASSUMPTION BOX-COND). No "
        f"box yet: the BUILD_H1 filament dryer set to {pl['cond_c']:g} C, if the closed jar fits inside (ASSUMPTION DRYER-JAR). "
        "A thermometer beside the jar; write the reading each day.",
        f"Traveller: the {tv['x']:.0f} x {tv['y']:.0f} x {tv['h']:.0f} mm plate from job B (as thick as the thickest "
        f"coupon, the bend bars). Weigh it on the 0.001 g scale before it goes in (dry, after the anneal) and every day at "
        f"the same hour: take it out, wipe it, weigh within 1 min, put it back.",
        f"Done when the traveller changes by less than {pl['cond_dm_pct']:g} % in 24 h ({pl['cond_dm_pct'] / 100 * tv['x'] * tv['y'] * tv['h'] * rho():.3f} g "
        f"on this plate). Expect 2 to 4 weeks (ASSUMPTION COND-TIME): the scale decides, not the calendar. Write the uptake "
        f"% = (wet - dry) / dry x 100 (the TDS says {pl['uptake_tds_pct']:g} % at 25 C / 55 % RH; more is expected here).",
        "Keep the conditioned parts in the jar until the hour they are tested; the jar rides in the 40 C box during the tests.",
    ]


def hot_txt(temp: float, tol: float) -> str:
    return (f"Test at {temp:g} +/- {tol:g} C ({temp * 9 / 5 + 32:.0f} F) inside the 40 C box round the lever rig's coupon "
            "station (link through a slot in the lid, ASSUMPTION BOX-ON-RIG of BL-074), 1 h soak first, thermometer touching "
            "the part")


def print_steps() -> list[str]:
    pl = pass_lines()
    lh = frame_layer_h()
    cp = coupon_plan()
    return [
        f"PAHT-CF dried as BUILD_H1 section 3 (80 C, 176 F, 10-12 h). Job B needs about {cp['jobs'][1]['filament_g']:.0f} g "
        "in one go: start it on a full 1 kg spool (ASSUMPTION SPOOL-FRESH); job A fits on any spool with 60 g left.",
        f"Profile: the frame profile of BUILD_H1 section 3 ({lh:g} mm layers, 6 walls, 100 % infill, chamber heater on), "
        "same printer and spool lot as the frame. Do not change it for the coupons.",
        f"Load the job's STLs from `designs/pack_5200/print/frame_h1/coupons_paht/` and its 15 x 15 mm prime pillar "
        f"(`tower_A.stl` or `tower_B.stl`), pillar 10 mm (0.4 in) from the parts, parts spaced as in the files.",
        "Layer time by a dwell, not a tower (BL-079): save a copy of the printer preset as 'PAHT coupons dwell' and, in "
        "Printer settings > Machine G-code > 'Layer change G-code', add at the end: a move that parks the nozzle clear "
        f"of the parts (copy the park / wipe move your printer's own timelapse code uses) and `G4 S<dwell>`, with the "
        "dwell of the job from the table below (job A " + f"{jobs()[0]['dwell_s']:.0f} s, job B {jobs()[1]['dwell_s']:.0f} s). "
        "Do NOT use the filament's 'Slow printing down for better layer cooling' for this: it keeps the hot nozzle over "
        "the coupon and stops at the minimum speed. Everything else stays the frame profile.",
        "Slice. Open the preview's layer-time view (it may not count the G4 dwell): every layer must show at least "
        f"{pl['layer_s']:.0f} s minus the dwell. On the printer, time 3 layers of each job with a watch: each >= "
        f"{pl['layer_s']:.0f} s. Write the shortest and the median layer time of each job in the results sheet. If the "
        "dwell leaves blobs or gaps at the restart, fall back to a dummy tower sized to the same layer time (one "
        "more filament, about USD " + f"{fallback_tower_usd():.0f}" + ", still inside the cap).",
        "Print. Watch the first layer: every comb tie, bar and plate flat on the plate.",
        "When cool: weigh each job's parts (pillar off), write it. Anneal everything as the frame (BUILD_H1 section 5: "
        "90 C (194 F) 6 h, cool in the oven); weigh the traveller straight after (its dry mass).",
    ]


def guide_steps() -> dict:
    pl = pass_lines()
    bk = blocks()
    s = bk["sbs"]
    lh = frame_layer_h()
    fx = bk["flex"]
    k10 = pl["k10"]
    hot = hot_txt(pl["test_c"], pl["test_tol"]) + "."
    h_e = E_ADD_KG * G
    cb = H1P.clevis_b()
    return {
        "CA-3-PAHT": [
            "Print job A and job B (COUPONS_PAHT.md section 3; " + "; ".join(print_steps()[2:4]) + ").",
            f"SBS block: sand {FACE:g} mm off the top and the bottom on 240-grit paper glued to glass ({s['h']:.1f} -> "
            f"{pl['sbs_t']:g} mm, {pl['sbs_t'] / IN:.3f} in), so the mid-plane stays on the line between layers "
            f"{s['mid_line']} and {s['mid_line'] + 1}. Trim the {TRIM:g} mm edge strip, then saw the bars "
            f"{pl['sbs_l']:g} x {pl['sbs_w']:g} mm on the pencil grid with a fine-tooth saw.",
            f"Z combs: snip each bar off its two ties with flush cutters and sand the tie stubs flat (they sit in the "
            f"grips, not the gauge). The 5 mm wide gauge crosses the layers. Do not sand the gauge faces.",
            f"Label with a paint pen: CA3-Z-H1..H{pl['n_z_hw']} and CA3-S-H1..H{pl['n_sbs_hw']} (hot/wet), "
            f"CA3-Z-D1..D{pl['n_z_dry']} and CA3-S-D1..D{pl['n_sbs_dry']} (dry). Measure each gauge width and thickness "
            "with the caliper at 3 points; write the smallest on the bar.",
            f"DRY set: in a zip bag with desiccant; test within 24 h at {_c(pl['dry_test_c'])}.",
            "HOT/WET set: condition it (COUPONS_PAHT.md section 4) with the CA-1-PAHT and CA-4-PAHT bars.",
            hot,
            f"Z tensile: lever rig static (turnbuckle in place of the spring), the bar's grips 10 mm deep. Strength = peak "
            f"cell force x {LEVER_RATIO:.0f} / (width x thickness). Dry bars about {_n(pl['z_dry_n'])} at the bar.",
            f"Short-beam shear: jig with the D{pl['c1_nose_d']:g} loading nose on top and two D{pl['c1_pin_d']:g} "
            f"supports {pl['c1_span']:g} mm "
            f"({pl['c1_span'] / IN:.2f} in) apart (ASTM D2344), bar flat as printed. Load slowly to the drop. Shear "
            f"strength = 0.75 x F_max / (width x thickness).",
            f"Sheet: B-basis of the {pl['n_z_hw']} = AVERAGE - {k10:g} x STDEV (the sheet does it). Type every bar; send the "
            "sheet the same day.",
        ],
        "CA-1-PAHT": [
            f"Bars from the SBS block: CA1-F1..F{pl['c1_n_fat']} (+1 spare) and CA1-S1..S{pl['c1_n_static']}, faced, cut, "
            "labelled and conditioned with the CA-3-PAHT hot/wet set.",
            "Fit the short-beam jig at the lever rig's coupon station and put the 40 C box round it. " + hot,
            f"Static first: the {pl['c1_n_static']} S bars to failure as CA-3-PAHT short-beam shear.",
            f"Fatigue peak for each bar: F_max = {pl['c1_smax']:g} MPa x width x thickness / 0.75 (about "
            f"{_n(pl['c1_peak_n'])} at the bar, {pl['c1_peak_n'] / LEVER_RATIO / G:.1f} kg on the cell); "
            f"F_min = {pl['c1_r']:g} x F_max (R {pl['c1_r']:g}).",
            "Set the crank throw and the turnbuckle so the cell swings between F_min / 4 and F_max / 4; check over 20 slow "
            "turns by hand before the motor runs.",
            f"Run each bar to {pl['c1_cycles']:,.0f} cycles at 1 Hz (about 28 h; never above {pl['c1_hz_max']:g} Hz). The rig "
            "stops itself on a break, a stiffness drop over 10 % or a force drift over 5 %.",
            "After each run-out: loupe on the bar's middle layer line, photograph, type the cycles. A bar that breaks: stop "
            "and send the sheet; never swap in the spare to make the count.",
        ] + ([f"H1 AS IS only (BL-079): if CA-3-PAHT reads Z >= {pl['h1_sleeved_z_b_mpa']:g} and SBS >= "
              f"{pl['h1_sleeved_sbs_b_mpa']:g} MPa, run the {pl['c1_n_fat_h1']} bars CA1-H1..H{pl['c1_n_fat_h1']} the same way "
              f"at Smax {pl['h1_sleeved_ca1_smax_mpa']:g} MPa (F_max = {pl['h1_sleeved_ca1_smax_mpa']:g} x width x thickness / "
              f"0.75, about {_n(pl['h1_sleeved_ca1_peak_n'])} at the bar). Otherwise leave them in the jar."]
             if pl["c1_n_fat_h1"] else []),
        "CA-4-PAHT": [
            f"Bend bars from job B: {pl['c4_n']} for 23 C dry (CA4-D), {pl['c4_n']} for 40 C conditioned (CA4-W), "
            f"{pl['c4_n']} for {pl['c4_hot_c']:g} C dry (CA4-H), +1 spare. Measure width and thickness (caliper, 3 points).",
            "The 23 C and the hot dry sets stay sealed with desiccant. The 40 C set is conditioned with the CA-3-PAHT hot/wet set.",
            f"3-point fixture: supports {fx['span']:.0f} mm ({fx['span'] / IN:.2f} in) apart (ISO 178, 16 x thickness), bar "
            "flat as printed, dial indicator (0.01 mm) on top at mid-span.",
            f"Stiffness: hang {E_PRE_KG:g} kg, zero the dial, add {E_ADD_KG:g} kg ({E_PRE_KG + E_ADD_KG:g} kg, "
            f"{(E_PRE_KG + E_ADD_KG) * 2.2046:.1f} lb total), read the dial in mm. E = span^3 x {h_e:.1f} N / (4 x width x "
            "thickness^3 x reading); the sheet does the sum (ASSUMPTION E-LOAD: light weights so a hot bar is not bent "
            "past its linear range).",
            f"Strength: load to the break with the come-along and the crane scale. Strength = 3 x F x span / (2 x width x "
            "thickness^2).",
            f"40 C set: {hot_txt(pl['test_c'], pl['test_tol'])}. {pl['c4_hot_c']:g} C set: box thermostat at "
            f"{_c(pl['c4_hot_c'])}, thermometer {pl['c4_hot_c'] - 2:g}-{pl['c4_hot_c'] + 2:g} C for 30 min first (ASSUMPTION BOX-60, BL-074).",
            f"Sheet: E ratio = mean E (40 C conditioned) / mean E (23 C dry), and the flexural strength ratio (record).",
        ],
        "HB-6b-SLV": [
            "Runs ONLY if the coupons point to H1c (COUPONS_PAHT.md section 1), on the first H1c frame, before any other "
            "frame test on it.",
            "Cut 8 sleeves from the 304 tube (1/4 x 0.010 in) with the mini tubing cutter, a little long. Depth rod of the "
            "caliper: measure each hip boss hole's depth; file each sleeve to that depth + "
            f"{pl['slv_lo']:g}-{pl['slv_hi']:g} mm ({pl['slv_lo'] / IN:.3f}-{pl['slv_hi'] / IN:.3f} in) and deburr.",
            f"Push each sleeve in: caliper depth rod from the boss back: proud by {pl['slv_lo']:g}-{pl['slv_hi']:g} mm. Write all 8.",
            f"Seat the two arc plates and the mount, 8 M5 x 35 with nuts, torque {pl['slv_nm']:g} N m "
            f"({pl['slv_nm'] / NM_PER_INLBF:.1f} in lbf) with the 0.5-2.5 N m driver in a cross pattern.",
            "Back the screws off, lift the plates, loupe on the PAHT-CF under them: no ring or shiny imprint (the preload "
            "sits on the sleeves). Re-fit, re-torque, paint mark across every head, nut and plate.",
            "Run the kit's HB-6b sequence (register row HB-6b) on this frame.",
            "After T5 on this frame: the paint marks unmoved. Type Y or N for each row.",
        ],
        "CLEVIS-SHARE-B-PAHT": [
            "Runs ONLY if the coupons point to H1c, on the first H1c frame (bl077.json), before any other frame test on it.",
            "Fit the US2 gauge and the clevis as the kit's CLEVIS-SHARE (register row CLEVIS-SHARE); frame clamped on the "
            "bare R stay only (z 40-48 and 110-122), nothing on the US2 block.",
            f"Loading B: pull direction {cb['unit']} (frame R), the real US2 pin set and a sewn US eye.",
            f"Reading 1 (share 1.0): 1 mm PTFE shim between the eye and the OUTER (clevis) cheek. Pull to {_n(cb['peak_n'])}, "
            "hold 10 s, read u1. Unload, read the zero.",
            f"Reading 0 (share 0): the same shim between the eye and the INNER cheek. Same {cb['peak_n']:.0f} N, read u0.",
            f"Reading 2 (as built): shim out, eye centred as sewn. Same {cb['peak_n']:.0f} N, read u.",
            "Repeat readings 1, 0 and 2 three times (eye off and refitted each time). Share = (u - u0) / (u1 - u0); the "
            "sheet takes the largest.",
        ],
    }


# ============================================================================ register rows and results
REG_COLS = H1P.REG_COLS
DEF = "designs/pack_5200/iter1/frame/bl077.json coupons; designs/pack_5200/print/frame_h1/COUPONS_PAHT.md"
IDS = ("CA-3-PAHT", "CA-1-PAHT", "CA-4-PAHT", "HB-6b-SLV", "CLEVIS-SHARE-B-PAHT")
COUPON_IDS = IDS[:3]
FRAME_IDS = IDS[3:]


def kind_g(kind: str) -> float:
    """Filament (g) booked to one coupon kind, its job's tower and waste pro rata."""
    out = 0.0
    for j in coupon_plan()["jobs"]:
        for it in j["items"]:
            if it["kind"] == kind:
                out += j["filament_g"] * it["count"] * it["g"] / j["parts_g"]
    return out


def _row(**k) -> dict:
    base = dict(status="ACTIVE", tier="safety", defined_in=DEF, grams_at_stake_g="0", kit="B, D", cost_usd="0",
                cost_basis="", hours_hands_on="2", hours_machine="", phase="1", run_order="0", first_weekend="Y",
                notes="", g_per_usd_eq="")
    base.update(k)
    return base


def gate_txt() -> str:
    return "the frame decision (COUPONS_PAHT.md section 1: H1 as is, H1c or a redesign); the SAFETY HOLD on the released H1"


def register_rows() -> list[dict]:
    pl = pass_lines()
    c = coupons()
    st = guide_steps()
    up = usd_per_g()
    pf = proof_level()

    def steps(t):
        return "; ".join(f"({i}) {s.replace('; ', ', ')}" for i, s in enumerate(st[t], 1))
    nxt = "BL-078: NEXT PRINT / NEXT SESSION (G0), ahead of every other frame test"
    sbs_share = (pl["n_sbs_hw"] + pl["n_sbs_dry"]) / (pl["n_sbs_hw"] + pl["n_sbs_dry"] + pl["c1_n_fat"] + pl["c1_n_static"])
    rows = [
        _row(id="CA-3-PAHT", title=f"PAHT-CF Z tensile + SBS, hot/wet B-basis at n {pl['n_z_hw']}, dry set, layer time >= {pl['layer_s']:.0f} s",
             what_it_proves=c["CA-3-PAHT"]["settles"], gates=gate_txt(),
             safety_at_stake=f"released H1 strength {pl['h1_strength']:g} / R1 {pl['h1_r1']:g} on the booked hot/wet Z {pl['z_hw']:g} MPa",
             specimen=(f"hot/wet {pl['n_z_hw']} Z + {pl['n_sbs_hw']} SBS; dry {pl['n_z_dry']} Z + {pl['n_sbs_dry']} SBS; "
                       "Z bars ISO 527-2 1BA from the combs (job B), SBS bars from the block (job A)"),
             steps=steps("CA-3-PAHT"),
             pass_fail=c["CA-3-PAHT"]["pass"] + f". B-basis = mean - {pl['k10']:g} SD. Meaning of each outcome: COUPONS_PAHT.md section 1",
             cost_usd=f"{(kind_g('sbs') * sbs_share + kind_g('z')) * up:.2f}",
             cost_basis="PAHT-CF filament of the SBS block (share) and the Z combs, towers pro rata (record pa12_cf_fdm_paht)",
             hours_hands_on="8", hours_machine="504", notes=nxt),
        _row(id="CA-1-PAHT", title=f"PAHT-CF short-beam-shear fatigue at {pl['c1_temp']:g} C, conditioned, {pl['c1_factor']:g} x Smax",
             defined_in=DEF + "; designs/pack_5200/tests_physical/CA1_fatigue_rig.md (rig)",
             what_it_proves=c["CA-1-PAHT"]["settles"], gates=gate_txt(),
             safety_at_stake=f"R1 {pl['h1c_r1']:g} on H1c (fatigue ratio 0.30 booked)",
             specimen=(f"{pl['c1_n_fat']} SBS fatigue + {pl['c1_n_static']} SBS static from the job A block"
                       + (f", + {pl['c1_n_fat_h1']} SBS fatigue at the H1-as-is level (run only if CA-3-PAHT reaches "
                          "the H1 lines)" if pl["c1_n_fat_h1"] else "")), steps=steps("CA-1-PAHT"),
             pass_fail=(f"all {pl['c1_n_fat']} SBS bars run out to {pl['c1_cycles']:,.0f} cycles at Smax {pl['c1_smax']:g} MPa "
                        f"(peak {pl['c1_peak_n']:g} N on the jig), R {pl['c1_r']:g}, {pl['c1_temp']:g} +/- {pl['c1_tol']:g} C; "
                        f"the {pl['c1_n_static']} static SBS >= the CA-3-PAHT SBS line {pl['sbs_line']:g} MPa"
                        + (f"; H1 AS IS: the {pl['c1_n_fat_h1']} H1 bars run out at Smax {pl['h1_sleeved_ca1_smax_mpa']:g} MPa"
                           if pl["c1_n_fat_h1"] else "")),
             cost_usd=f"{kind_g('sbs') * (1 - sbs_share) * up:.2f}", cost_basis="PAHT-CF filament of the SBS block (share); lever rig kit B",
             hours_hands_on="6", hours_machine=f"{pl['c1_n_fat'] * pl['c1_cycles'] / 3600:.0f}", notes=nxt),
        _row(id="CA-4-PAHT", title=f"PAHT-CF 3-point bend modulus at 23 C dry / 40 C conditioned / {pl['c4_hot_c']:g} C dry",
             what_it_proves=c["CA-4-PAHT"]["settles"], gates=gate_txt(),
             safety_at_stake="buckling (eigen, frame crown held) on the hot/wet modulus",
             specimen=f"{pl['c4_n']} XY bend bars {pl['c4_l']:g} x {pl['c4_w']:g} x {pl['c4_t']:g} per condition (job B)",
             steps=steps("CA-4-PAHT"), pass_fail=c["CA-4-PAHT"]["pass"],
             cost_usd=f"{(kind_g('flex') + kind_g('traveller')) * up:.2f}",
             cost_basis="PAHT-CF filament of the bend bars and the traveller; 40 C box kit B", hours_hands_on="4",
             hours_machine="3", notes=nxt),
        _row(id="HB-6b-SLV", title=f"hip mount proof on the first H1c frame with the 304 sleeves, {pl['slv_nm']:g} N m",
             what_it_proves=c["HB-6b-SLV"]["settles"], gates="H1c first frame (only if the coupons point to H1c)",
             safety_at_stake="hip mount through-bolts: the preload stays in the steel", specimen="the first H1c frame",
             kit="C, D", steps=steps("HB-6b-SLV"), pass_fail=c["HB-6b-SLV"]["pass"], phase="2", first_weekend="N",
             hours_hands_on="3", notes="BL-078: next frame test, only if the coupons point to H1c (before any other H1c frame test)"),
        _row(id="CLEVIS-SHARE-B-PAHT", title=f"US2 clevis outer-cheek share on the first frame (loading B), pass <= {pl['share_max']:g}",
             defined_in=DEF + "; analysis/clevis_bl056.json kit B",
             what_it_proves=c["CLEVIS-SHARE-B-PAHT"]["settles"], gates="H1c first frame (only if the coupons point to H1c)",
             safety_at_stake="US2 clevis hole-bearing fatigue (0.70 at share 1.0 on the hot/wet basis)",
             specimen="the first H1c frame, R stay, clevis hardware and the US2 gauge as CLEVIS-SHARE", kit="B, A, D",
             steps=steps("CLEVIS-SHARE-B-PAHT"), pass_fail=c["CLEVIS-SHARE-B-PAHT"]["pass"], phase="2", first_weekend="N",
             hours_hands_on="3", notes="BL-078: next frame test, only if the coupons point to H1c. ASSUMPTION SHARE-GAUGE (BL-076 rule)"),
    ]
    assert pf["kg"] > 0
    for r in rows:
        assert set(r) == set(REG_COLS), set(r) ^ set(REG_COLS)
    return rows


def results_items() -> dict:
    """Rows for outputs/release/test_kit/results_template.csv: (sample, quantity, unit, check, limit, settles). The
    quantity text of each deciding row says what the outcome means."""
    pl = pass_lines()
    cb = H1P.clevis_b()
    out = {}
    rows = [("job A", "shortest layer time, timed on the printer (print + dwell)", "s", "min", f"{pl['layer_s']:.0f}", "LAYER-DWELL"),
            ("job B", "shortest layer time, timed on the printer (print + dwell)", "s", "min", f"{pl['layer_s']:.0f}", "LAYER-DWELL"),
            ("traveller", "dry mass after the anneal", "g", "record", "", ""),
            ("traveller", f"mass change over the last 24 h at the end of conditioning", "%", "max", f"{pl['cond_dm_pct']:g}", "WET-PAHT"),
            ("traveller", f"water uptake at constant mass (TDS {pl['uptake_tds_pct']:g} %)", "%", "record", "", "WET-PAHT")]
    for setn, n, kind in (("hot/wet", pl["n_z_hw"], "Z tensile"), ("hot/wet", pl["n_sbs_hw"], "SBS"),
                          ("dry", pl["n_z_dry"], "Z tensile"), ("dry", pl["n_sbs_dry"], "SBS")):
        rows += [(f"{setn} {i}", f"{kind} strength, {setn}", "MPa", "record", "", "") for i in range(1, n + 1)]
    rows += [
        ("hot/wet set", (f"Z tensile B-basis (mean - {pl['k10']:g} SD). Below {pl['z_line']:g}: H1c fails too -> REDESIGN. "
                         f"{pl['z_line']:g} or more: H1c body rows pass"), "MPa", "min", f"{pl['z_line']:g}",
         "B-BASIS-N5; WET-PAHT; HOT-40-PAHT"),
        ("hot/wet set", (f"SBS B-basis (mean - {pl['k10']:g} SD). Below {pl['sbs_line']:g}: H1c fails too -> REDESIGN"),
         "MPa", "min", f"{pl['sbs_line']:g}", "TAU-VM"),
        ("hot/wet set", (f"Z B-basis again, for the z 234 joint: {pl['z_joint']:g} or more (with SBS {pl['sbs_joint']:g} or "
                         f"more) closes the H1c joint too; below it the joint stays open"), "MPa", "record", "", ""),
        ("both sets", f"hot/wet / dry Z B-basis (booked {pl['knock_booked']:g})", "ratio", "record", "", "WET-PAHT; HOT-40-PAHT"),
    ]
    if pl["h1_sleeved_ok"]:
        rows += [
            ("H1 as is", (f"Z B-basis again, for H1 AS IS (hip on sleeved through-bolts): {pl['h1_sleeved_z_b_mpa']:g} or more "
                          f"(with SBS {pl['h1_sleeved_sbs_b_mpa']:g} or more, the extra CA-1-PAHT bars and E ratio "
                          f"{pl['h1_e_ratio']:g}) -> H1 AS IS; below it H1 as is stays on hold"), "MPa", "record", "",
             "BL-079 h1_as_is"),
            ("H1 as is", f"SBS B-basis again, for H1 AS IS: {pl['h1_sleeved_sbs_b_mpa']:g} or more", "MPa", "record", "",
             "BL-079 h1_as_is"),
            ("H1 as is", "outcome: H1 AS IS / H1c / REDESIGN (COUPONS_PAHT.md section 1, first matching row)", "text",
             "record", "", "BL-079 h1_as_is")]
    else:
        rows += [("H1 as is", "no coupon value clears H1 as is (bl077.json h1_as_is): the SAFETY HOLD stays", "Y/N",
                  "record", "", "BL-079 h1_as_is")]
    out["CA-3-PAHT"] = rows
    rows = [(f"static {i}", f"SBS strength, hot/wet {pl['c1_temp']:g} C (below {pl['sbs_line']:g}: REDESIGN)", "MPa", "min",
             f"{pl['sbs_line']:g}", "FAT-0.30") for i in range(1, pl["c1_n_static"] + 1)]
    rows += [(f"fatigue {i}", f"cycles reached at Smax {pl['c1_smax']:g} MPa (a break before {pl['c1_cycles']:,.0f}: REDESIGN)",
              "cycles", "min", f"{pl['c1_cycles']:.0f}", "FAT-0.30") for i in range(1, pl["c1_n_fat"] + 1)]
    if pl["c1_n_fat_h1"]:
        rows += [(f"fatigue H1 {i}", (f"cycles reached at Smax {pl['h1_sleeved_ca1_smax_mpa']:g} MPa (run only if CA-3-PAHT "
                                      f"reaches the H1 lines; all to {pl['c1_cycles']:,.0f} -> H1 AS IS possible)"),
                  "cycles", "record", "", "BL-079 h1_as_is") for i in range(1, pl["c1_n_fat_h1"] + 1)]
    rows += [("40 C box", "thermometer during the runs", "C", "band",
              f"{pl['c1_temp'] - pl['c1_tol']:g}..{pl['c1_temp'] + pl['c1_tol']:g}", "HOT-40-PAHT")]
    out["CA-1-PAHT"] = rows
    out["CA-4-PAHT"] = [
        ("23 C dry", "E mean", "MPa", "record", "", ""),
        ("40 C conditioned", f"E(40 C conditioned) / E(23 C dry) (below {pl['c4_e_ratio']:g}: H1c buckling fails -> REDESIGN)",
         "ratio", "min", f"{pl['c4_e_ratio']:g}", "E-WET"),
        ("40 C conditioned", f"flexural strength ratio to 23 C dry (booked {pl['c4_flex_booked']:g})", "ratio", "record", "", "E-WET"),
        (f"{pl['c4_hot_c']:g} C dry", "E mean (record)", "MPa", "record", "", ""),
        ("40 C box", "thermometer during the 40 C tests", "C", "band",
         f"{pl['test_c'] - pl['test_tol']:g}..{pl['test_c'] + pl['test_tol']:g}", "HOT-40-PAHT"),
        (f"{pl['c4_hot_c']:g} C box", f"thermometer during the {pl['c4_hot_c']:g} C tests", "C", "band",
         f"{pl['c4_hot_c'] - 2:g}..{pl['c4_hot_c'] + 2:g}", "BOX-60"),
    ]
    out["HB-6b-SLV"] = ([(f"sleeve {i}", "proud of the boss back", "mm", "band", f"{pl['slv_lo']:g}..{pl['slv_hi']:g}", "SLEEVE-PROUD")
                         for i in range(1, 9)]
                        + [("plates", "no witness mark on the PAHT-CF before the load", "Y/N", "yes", "Y", "SLEEVE-PROUD"),
                           ("HB-6b", "the kit's HB-6b pass rule", "Y/N", "yes", "Y", "SLEEVE-PROUD"),
                           ("after T5", "paint marks unmoved", "Y/N", "yes", "Y", "SLEEVE-PROUD")])
    rows = []
    for i in range(1, 4):
        rows += [(f"set {i}", f"u1, shim on the outer cheek, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE"),
                 (f"set {i}", f"u0, shim on the inner cheek, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE"),
                 (f"set {i}", f"u, as built, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE")]
    rows += [("all sets", "largest share (u - u0) / (u1 - u0)", "ratio", "max", f"{pl['share_max']:g}", "CLEVIS-SHARE")]
    out["CLEVIS-SHARE-B-PAHT"] = rows
    return out


# ============================================================================ documents
ASSUMPTIONS = {
    "LAYER-DWELL": (lambda pl, lh: (f"The coupons print with the frame profile ({lh:g} mm layers, BUILD_H1 section 3) "
                                    f"and every layer takes >= {pl['layer_s']:.0f} s (bl077.json layer_time: the slowest "
                                    f"frame half's median at {pl['layer_h_bl077']:g} mm), by a per-layer park-and-dwell "
                                    "(G4) in the coupon preset; the cooling time between layers, with the nozzle away, "
                                    "is what sets the interlayer weld (Seppala 2017; Vaes 2021), not the tower volume. "
                                    "The slicer slow-down is not used (nozzle stays on the coupon; min-speed floor).",
                                    "the timed layers of each job (results sheet)")),
    "COMB": (lambda pl, lh: (f"Z bars print standing in combs of {COMB_N}, {COMB_GAP:g} mm apart, tied by {TIE_H:g} mm strips "
                             "at the plate and inside the top grip; the ties are snipped off and sit in the grips.", "first print")),
    "CUT / SPARE": (lambda pl, lh: (f"BL-074 rules: {KERF:g} mm saw kerf, {TRIM:g} mm edge strip trimmed, one spare per set.",
                                    "first coupon cut")),
    "ANNEAL-ALL": (lambda pl, lh: ("Every coupon is annealed as the frame (BUILD_H1 section 5) before the dry tests or the "
                                   "conditioning: the frame in service is annealed, then takes up water.", "engineer review")),
    "BOX-COND": (lambda pl, lh: (f"The kit's 40 C box (cooler, 60 W heater, thermostat) holds {pl['cond_c']:g} C for the salt "
                                 "jar for weeks; its thermostat reaches the setting (an Inkbird ITC-308 class controller "
                                 "covers it).", "the daily thermometer reading")),
    "DRYER-JAR": (lambda pl, lh: (f"If the box is not built, the BUILD_H1 filament dryer holds {pl['cond_c']:g} C round the "
                                  "closed jar (only if the jar fits).", "the daily thermometer reading")),
    "COND-TIME": (lambda pl, lh: ("2 to 4 weeks to constant mass at 50 C for 3-4 mm PAHT-CF; the traveller decides.",
                                  "the traveller log")),
    "SPOOL-FRESH": (lambda pl, lh: ("Job B starts on a full 1 kg spool (no spool change mid-job).", "spool weights")),
    "E-LOAD": (lambda pl, lh: (f"Bend modulus from a {E_PRE_KG:g} kg preload and a {E_ADD_KG:g} kg step: bending stress "
                               "stays near a third of the hot/wet XY strength, in the linear range.", "dial readings")),
    "BOX-ON-RIG / BOX-60 / SHARE-GAUGE": (lambda pl, lh: ("as BL-074 (frame_h1p_build.ASSUMPTIONS).", "the thermometer and gauge rows")),
}


def found() -> list[str]:
    """What BL-078 found in bl077.json and how BL-079 (structural) settled each one (all now read from bl077.json)."""
    pl = pass_lines()
    cs = cost()
    lh = frame_layer_h()
    hs = (f"Z >= {pl['h1_sleeved_z_b_mpa']:g} / SBS >= {pl['h1_sleeved_sbs_b_mpa']:g} MPa with the hip on sleeved "
          "through-bolts" if pl["h1_sleeved_ok"] else "not reachable")
    return [
        f"H1 as is had no coupon line. FIXED (BL-079): bl077.json h1_as_is gives the lines at which every row of the "
        f"released H1 reaches goal: {hs}; E ratio >= {pl['h1_e_ratio']:g}. {pl['h1_plaus']}",
        f"Layer time: bl077 put the floor at {pl['layer_s_bl077_0p3']:.0f} s from 0.3 mm layers. FIXED (BL-079): "
        f"re-derived at the real {lh:g} mm profile, {pl['layer_s']:.0f} s (slowest frame half's median), held by a "
        f"per-layer dwell, not by dummy towers (towers at this floor would still be "
        f"{sum(j['fallback_tower_g'] for j in jobs()) * (1 + WASTE):.0f} g, USD {fallback_tower_usd():.2f}: the fallback only).",
        f"CA-1-PAHT jig. FIXED (BL-079): ASTM D2344 D{pl['c1_nose_d']:g} loading nose, D{pl['c1_pin_d']:g} supports, "
        f"span {pl['c1_span']:g} mm.",
        f"Conditioning. FIXED (BL-079): the sealed salt jar heated to {pl['cond_c']:g} C (section 4), not the kit's "
        "room-temperature box.",
        "Rounding. FIXED (BL-079): every minimum line rounds UP to 0.1 MPa (E ratio to 0.01; the CA-1 test load up), "
        f"e.g. the Z line {pl['z_line']:g} MPa = {pass_lines_recomputed()['z_hw']:.2f} / {pl['m_body']:g} rounded up.",
        "CA-4 claim. FIXED (BL-079): kit_needs now says the PAHT rows are added and do not replace the kit's CA-1/3/4 "
        "(the kit's CA-4 is creep-rupture, which the bend-modulus test does not cover).",
        f"CA-3-PAHT's cell check uses a dry Z pull of {pl['z_dry_mpa']:g} MPa (TDS V2.0) while the record's Z mean is "
        f"{paht()['tensile_strength_z_mpa']} MPa (V3.0): conservative for the cell, no action.",
        "HB-6b-SLV and CLEVIS-SHARE-B-PAHT run on the first frame that the coupons pick (H1c, or H1 as is on sleeved "
        "through-bolts); BUILD_H1 still builds H1 with inserts (the H1c / sleeved hip build pack is not written yet).",
    ]


def coupons_md() -> str:
    pl = pass_lines()
    cp = coupon_plan()
    cs = cost()
    bk = blocks()
    st = guide_steps()
    reg = {r["id"]: r for r in register_rows()}
    rk = rig_check()
    lh = frame_layer_h()
    rate, k = rate_rule()
    L = ["# COUPONS_PAHT: the PAHT-CF coupons that decide the H1 frame (next print)", "",
         f"Generated by `designs/pack_5200/frame_h1_paht_coupons.py` ({TICKET}, manufacturing-engineer, {DATE}). **Do not "
         "edit by hand: re-run the script.** Every pass line is read from `designs/pack_5200/iter1/frame/bl077.json` "
         "(`coupons`, BL-077 hot/wet B-basis) when this file is generated. Metric first, imperial in brackets.", ""]
    L += hold_block_md()
    L += ["**This is the next print and the next test session**, ahead of every other frame print or frame test. "
          f"Cost USD {cs['new_usd']:.2f} new (USD {cs['all_in_usd']:.2f} if the 40 C box is not built yet), inside the "
          f"USD {cs['cap_usd']:.0f} proving-print cap.", "",
          "## 1. What the results mean (read this first)", "",
          "The coupons measure the real hot/wet strength of your PAHT-CF as printed. They choose between three paths. "
          "Read the table top-down: the first row that matches decides.", "",
          "| if the results show | it means | why |", "|---|---|---|"]
    for o in outcomes():
        L.append(f"| {o['if']} | **{o['means']}** | {o['why']} |")
    L += ["", f"B-basis = mean - {pl['k10']:g} x SD of the {pl['n_z_hw']} hot/wet bars ({pl['k_src']}). Lines: bl077.json "
          "`coupons` (CA-3-PAHT `pass`, CA-1-PAHT `pass`, CA-4-PAHT `pass`).", "",
          "Order: print (2 jobs, about "
          f"{cp['print_h']:.0f} h) -> anneal -> dry set tested within 24 h -> hot/wet set to constant mass (2-4 weeks) -> "
          f"CA-3-PAHT and CA-4-PAHT (2 days) -> CA-1-PAHT ({pl['c1_n_fat']} x about 28 h). About **5 to 7 weeks**.", "",
          "## 2. Cost (RUBRIC 1b: proving prints <= USD 150)", "",
          "| item | USD | source |", "|---|---:|---|"]
    for x in cs["lines"]:
        tag = "" if x["kind"] == "new" else " (kit line, counted only if not built yet)"
        L.append(f"| {x['item']}{tag} | {x['usd']:.2f} | {x['source']} |")
    L += [f"| **new money** | **{cs['new_usd']:.2f}** | |",
          f"| **all-in, with the 40 C box** | **{cs['all_in_usd']:.2f}** | cap {cs['cap_usd']:.0f}: "
          f"{'within' if cs['within_cap'] else '**OVER**'} |", "",
          "Reused from the kit (shopping_list.csv): kit B lever rig (gear motor, lever, 100 kg cell, HX711, Arduino), the "
          "3-point bend fixture, caliper, dial indicator, crane scale and come-along. No new tool over USD 50.", "",
          "## 3. Print jobs (layer time by a dwell, no dummy towers)", "",
          f"Every layer must take >= **{pl['layer_s']:.0f} s** (bl077.json `layer_time`: the slowest frame half's median "
          f"layer time at the real {pl['layer_h_bl077']:g} mm layers, BL-079; it was {pl['layer_s_bl077_0p3']:.0f} s at "
          f"0.3 mm). By the BL-053 rule (t = area x {lh:g} mm / {rate:g} mm3/s x {k:g}) a tower would need "
          f"{cp['area_req_mm2']:,.0f} mm2 per layer. What sets the bond between layers is how long the layer below "
          "cools with the nozzle away (Seppala 2017; Vaes 2021: bl077.json layer_time.sources), not the tower's volume, "
          "so each job prints at the frame speed and then parks the nozzle for a fixed dwell every layer.", ""]
    L += [f"{i}. {s}" for i, s in enumerate(print_steps(), 1)]
    L += ["", "| job | prints | layers | dwell s | parts g | prime pillar g | filament + 8 % | USD | about h | shortest layer s |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for j in cp["jobs"]:
        its = "; ".join(f"{it['count']} x {it['name']}" for it in j["items"])
        L.append(f"| {j['job']} | {its} | {j['layers']} | {j['dwell_s']:.0f} | {j['parts_g']:.0f} | {j['tower_g']:.0f} | "
                 f"{j['filament_g']:.0f} g | {j['usd']:.2f} | {j['print_h']:.1f} | {j['min_layer_s']:.0f} |")
    L += [f"| | **total** | | | | | **{cp['filament_g']:.0f} g ({cp['filament_g'] / OZ:.1f} oz)** | **{cp['filament_usd']:.2f}** | "
          f"**{cp['print_h']:.0f}** | |", "",
          f"- SBS block: {bk['sbs']['n']} bars ({pl['n_sbs_hw']} + {pl['n_sbs_dry']} CA-3-PAHT, {pl['c1_n_fat']} + "
          f"{pl['c1_n_static']} CA-1-PAHT, {pl['c1_n_fat_h1']} CA-1-PAHT H1-as-is, {2 * SPARES} spare), {bk['sbs']['layers']} layers; the bars are faced to "
          f"{pl['sbs_t']:g} mm so the shear mid-plane is the line between layers {bk['sbs']['mid_line']} and "
          f"{bk['sbs']['mid_line'] + 1}.",
          f"- Z combs: {bk['z']['n']} bars ({pl['n_z_hw']} hot/wet + {pl['n_z_dry']} dry + {SPARES} spare) in combs of "
          f"{' and '.join(str(n) for n in bk['z']['combs'])}; ISO 527-2 1BA outline, {pl['z_t']:g} mm thick, standing.",
          f"- Bend bars: {bk['flex']['n']} ({pl['c4_n']} per condition x 3 + {SPARES} spare).",
          "- No supports on either job.", "",
          "## 4. Conditioning to constant mass, and the 40 C method", ""]
    L += [f"{i}. {s}" for i, s in enumerate(cond_steps(), 1)]
    L += ["", f"40 C tests: {hot_txt(pl['test_c'], pl['test_tol'])}. The 40 C box is the kit B line (cooler + 60 W "
          f"heater + thermostat, USD {BOX_KIT_USD:.0f}, ASSUMPTION shop price); a stand-alone plug-in thermostat such as "
          f"the Inkbird ITC-308 is USD {ITC308['usd']:.2f} ({ITC308['src']}), so the method stays under USD 50.", ""]
    n = 5
    for t in IDS:
        r = reg[t]
        L += [f"## {n}. {t}: {r['title']}", "", f"**Why:** {r['what_it_proves']}. **Decides:** {r['gates']}.  ",
              f"**You need:** {r['specimen']}.", "", "**Steps**", ""]
        L += [f"{i}. {s}" for i, s in enumerate(st[t], 1)]
        L += ["", f"**Pass:** {r['pass_fail']}", ""]
        n += 1
    L += [f"## {n}. Rig loads: everything stays under the 100 kg cell", "", "| load | N | lbf | under the cell |", "|---|---:|---:|---|"]
    for kk, v in rk["loads"].items():
        L.append(f"| {kk} | {v:,.0f} | {v / N_PER_LBF:,.0f} | {'yes' if v <= rk['cell_n'] else '**NO**'} |")
    L += ["", f"Cell {rk['cell_n']:.0f} N (100 kg); the lever puts a quarter of the bar force on it. All under: **{rk['all_under_cell']}**.", "",
          f"## {n + 1}. The SAFETY HOLD on the released H1, test by test", "",
          "| test | mark | why |", "|---|---|---|"]
    for t, (cls, why) in HOLD_CLASS.items():
        L.append(f"| {t} | {hold_tag(cls)} | {why} |")
    L += ["| G7 (complete pack, field) | " + hold_tag("HOLD") + " | loaded carry |", "",
          f"## {n + 2}. Assumptions", "", "| id | assumption | settled by |", "|---|---|---|"]
    for aid, fn in ASSUMPTIONS.items():
        a, s = fn(pl, lh)
        L.append(f"| {aid} | {a} | {s} |")
    L += ["", f"## {n + 3}. Found in bl077.json by BL-078, settled by BL-079", ""] + [f"- {x}" for x in found()] + [""]
    return "\n".join(L)


def readme_md() -> str:
    cs = cost()
    return "\n".join(["# PAHT-CF coupons for the H1 decision (BL-078)", "",
                      f"Generated by `designs/pack_5200/frame_h1_paht_coupons.py`. **Do not edit by hand.**", ""]
                     + hold_block_md() + [
        "| file | what |", "|---|---|",
        "| `../COUPONS_PAHT.md` | **start here**: what the results mean, cost, the two print jobs, conditioning, one sheet per test |",
        "| `block_sbs.stl` | job A: the short-beam-shear block (bars sawn from it) |",
        "| `z_comb_*.stl` | job B: standing ISO 527-2 1BA Z bars in combs |",
        "| `bend_bar.stl`, `traveller.stl` | job B: ISO 178 bend bar and the conditioning traveller plate |",
        "| `tower_A.stl`, `tower_B.stl` | 15 x 15 mm prime pillars (the layer time is held by a per-layer dwell, BL-079) |", "",
        f"Cost USD {cs['new_usd']:.2f} new, USD {cs['all_in_usd']:.2f} all-in (cap {cs['cap_usd']:.0f}). "
        "Release copies, CSVs, PDF: `outputs/release/frame_h1_paht_coupons/`.", ""])


# ============================================================================ pictures, files
def _plt():
    return H1P._plt()


def coupon_figure(path: Path) -> Path:
    plt = _plt()
    cp = coupon_plan()
    J = cp["jobs"]
    pl = pass_lines()
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.6), dpi=100, gridspec_kw={"width_ratios": [1, 1.25]})
    co = comb_outline(int(pl["comb_n"]))
    xs, ys = co.exterior.xy
    ax[0].fill(xs, ys, fc="#9db7d5", ec="#2f5d8a", lw=1)
    for h in co.interiors:
        hx, hy = h.xy
        ax[0].fill(hx, hy, fc="white", ec="#2f5d8a", lw=1)
    _, g = iso1ba_outline()
    ax[0].axhspan(g["z_tab"] + g["lt"], g["l3"] - g["z_tab"] - g["lt"], color="#c9a227", alpha=0.25)
    ax[0].text(1, g["l3"] / 2, "gauge 5 mm wide:\nthe break crosses the layers", fontsize=8, va="center")
    ax[0].set_aspect("equal")
    ax[0].set_title(f"Z comb: {int(pl['comb_n'])} standing ISO 527-2 1BA bars,\nties at the plate and in the top grip", fontsize=10)
    ax[0].set_xlabel("mm")
    ax[0].set_ylabel("print height, mm")
    y = list(range(len(J)))
    parts = [j["parts_g"] for j in J]
    tw = [j["tower_g"] for j in J]
    ax[1].barh(y, parts, color="#4a6fa5", label="coupons")
    ax[1].barh(y, tw, left=parts, color="#c9a227", label="prime pillar")
    ax[1].set_yticks(y)
    ax[1].set_yticklabels([f"job {j['job']}" for j in J])
    for i, j in enumerate(J):
        ax[1].text(parts[i] + tw[i] + 8, i, f"{j['filament_g']:.0f} g, USD {j['usd']:.2f}\ndwell {j['dwell_s']:.0f} s, shortest layer {j['min_layer_s']:.0f} s",
                   va="center", fontsize=9)
    ax[1].invert_yaxis()
    ax[1].set_xlim(0, max(p + t for p, t in zip(parts, tw)) * 1.6)
    ax[1].legend(fontsize=9, loc="lower right")
    ax[1].set_xlabel("g")
    ax[1].set_title(f"two print jobs, no dummy towers: every layer >= {pl['layer_s']:.0f} s by a dwell", fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


SHOT_BL079 = "20261125_bl079_1"


def results_figure(path: Path) -> Path:
    """BL-079 screenshot: the results-meaning table (top-down) and the coupon cost, phone-readable."""
    import textwrap
    plt = _plt()
    oc = outcomes()
    cs = cost()
    fig = plt.figure(figsize=(8, 13.5), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.04, 0.985, "PAHT-CF coupons: what the results mean", fontsize=17, weight="bold", va="top")
    ax.text(0.04, 0.958, "Read top-down: the first row that matches decides (BL-079).", fontsize=11, va="top",
            style="italic")
    col = {OUT_H1: "#1f5f99", OUT_RE: "#b00000", OUT_H1C: "#2f6b2f"}
    y = 0.93
    for o in oc:
        c = next(v for k, v in col.items() if o["means"].startswith(k))
        ax.text(0.04, y, o["means"], fontsize=13, weight="bold", color=c, va="top")
        y -= 0.024
        t = textwrap.fill("IF " + o["if"], 78)
        ax.text(0.06, y, t, fontsize=9.6, va="top", family="DejaVu Sans")
        y -= 0.0158 * (t.count("\n") + 1) + 0.006
        w = textwrap.fill(textwrap.shorten(o["why"], 560), 84)
        ax.text(0.06, y, w, fontsize=8.6, va="top", color="#444")
        y -= 0.0142 * (w.count("\n") + 1) + 0.018
    y -= 0.005
    ax.plot([0.04, 0.96], [y + 0.008, y + 0.008], color="#999", lw=1)
    ax.text(0.04, y, "Coupon cost (RUBRIC 1b: proving prints <= USD 150)", fontsize=13, weight="bold", va="top")
    y -= 0.028
    for x in cs["lines"]:
        tag = " (kit line)" if x["kind"] != "new" else ""
        ax.text(0.06, y, textwrap.shorten(x["item"] + tag, 74), fontsize=9.4, va="top")
        ax.text(0.94, y, f"{x['usd']:.2f}", fontsize=9.4, va="top", ha="right")
        y -= 0.019
    ax.text(0.06, y, "new money", fontsize=11, weight="bold", va="top")
    ax.text(0.94, y, f"USD {cs['new_usd']:.2f}", fontsize=11, weight="bold", va="top", ha="right")
    y -= 0.022
    ax.text(0.06, y, "all-in, if the 40 C box is not built yet", fontsize=10, va="top")
    ax.text(0.94, y, f"USD {cs['all_in_usd']:.2f}", fontsize=10, va="top", ha="right")
    y -= 0.024
    ax.text(0.06, y, textwrap.fill(f"Filament {cs['filament_g']:.0f} g: no dummy towers; every layer >= "
                                   f"{pass_lines()['layer_s']:.0f} s by a per-layer dwell (frame layer time at 0.20 mm).", 90),
            fontsize=9, va="top", color="#444")
    ax.set_xlim(0, 1)
    ax.set_ylim(min(0.0, y - 0.05), 1)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return H1P._shrink(path)


def banner_figure(path: Path) -> Path:
    """The SAFETY HOLD banner as the owner sees it, with the hold marks of the stand tests."""
    import textwrap
    plt = _plt()
    from matplotlib.patches import FancyBboxPatch
    fig = plt.figure(figsize=(8, 10.5), dpi=110)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.03, 0.70), 0.94, 0.27, boxstyle="round,pad=0.01", fc="#fde2e1", ec="#b00000", lw=3))
    ax.text(0.5, 0.945, SAFETY_HOLD, ha="center", va="top", fontsize=30, weight="bold", color="#b00000")
    body = hold_text().split(". ", 1)[1]
    ax.text(0.06, 0.87, textwrap.fill(body, 62), ha="left", va="top", fontsize=12.5, color="#300")
    ax.text(0.05, 0.665, "Stand and carry tests on the released H1:", fontsize=13, weight="bold", va="top")
    yy = 0.63
    col = {"HOLD": "#b00000", "BELOW": "#2f6b2f", "NONE": "#555555"}
    for t, (cls, why) in list(HOLD_CLASS.items()) + [("G7 session", ("HOLD", "complete pack, loaded walks"))]:
        lab = {"HOLD": "HOLD", "BELOW": "BELOW PROOF, may run", "NONE": "no load, may run"}[cls]
        ax.text(0.05, yy, t, fontsize=10.5, weight="bold", va="top")
        ax.text(0.20, yy, lab, fontsize=10.5, color=col[cls], weight="bold", va="top")
        ax.text(0.47, yy, textwrap.shorten(why, 62), fontsize=9.5, va="top", color="#333")
        yy -= 0.0222
    ax.text(0.05, 0.012, "Next: print the PAHT coupons (COUPONS_PAHT.md). BL-078.", fontsize=11, style="italic")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def doc_pdf(title: str, md: str, path: Path, images: list | None = None) -> Path:
    from huntkit.manufacturing import techpack as T
    secs = [T.Section(md.splitlines()[0].lstrip("# "), H1P._blocks(md))]
    if images:
        secs.insert(0, T.Section("Pictures", [T.image(p, 250, 160) for p in images]))
    tp = T.TechPack(title=title, subtitle=TICKET, date=DATE, footer=f"Hunting-appeal {TICKET}",
                    cover=[["generated by", "designs/pack_5200/frame_h1_paht_coupons.py"],
                           ["data", "designs/pack_5200/iter1/frame/bl077.json; data/materials/polymers/pa12_cf_fdm_paht.yaml"],
                           ["status", hold_text().split(". ", 1)[0] + ": no loaded carry or proof test of the released H1"]],
                    sections=secs)
    return T.tech_pack(tp, path, strict=False)


def _page_with(pdf: Path, needle: str) -> int:
    import subprocess
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    for i, pg in enumerate(out.split("\f"), 1):
        if needle in pg:
            return i
    return 1


def checks(pk: dict) -> list[str]:
    pl, rc = pass_lines(), pass_lines_recomputed()
    msgs = []
    for k_, v in rc.items():
        ok = abs(pl[k_] - v) <= max(0.005 * abs(v), 0.051)
        msgs.append(f"{k_}: JSON text {pl[k_]:g} vs numeric {v:.4f} {'OK' if ok else 'MISMATCH'}")
    cp = pk["coupons"]
    msgs.append(f"coupon jobs {cp['filament_g']:.0f} g (prime pillars {cp['tower_g']:.0f} g); shortest layer "
                f"{min(j['min_layer_s'] for j in cp['jobs']):.0f} s (need {pl['layer_s']:.0f})")
    c = pk["cost"]
    msgs.append(f"cost new USD {c['new_usd']:.2f}, all-in USD {c['all_in_usd']:.2f}, cap {c['cap_usd']:.0f}: within {c['within_cap']}")
    msgs.append(f"rig: all under the cell {rig_check()['all_under_cell']} (max {rig_check()['max_n']:.0f} N)")
    return msgs


@functools.lru_cache(maxsize=None)
def package() -> dict:
    pk = {"coupons": coupon_plan(), "cost": cost(), "docs": {"COUPONS_PAHT.md": coupons_md()},
          "readme": readme_md(), "register": register_rows(), "results": results_items(), "outcomes": outcomes()}
    pk["checks"] = checks(pk)
    return pk


def _w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _csv(path: Path, rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write(pk: dict) -> dict:
    import trimesh
    REL.mkdir(parents=True, exist_ok=True)
    CP_DIR.mkdir(parents=True, exist_ok=True)
    md = pk["docs"]["COUPONS_PAHT.md"]
    _w(PRINT / "COUPONS_PAHT.md", md)
    _w(REL / "COUPONS_PAHT.md", md)
    _w(CP_DIR / "README.md", pk["readme"])
    bk = blocks()

    def box(x, y, h):
        m = trimesh.creation.box((x, y, h))
        m.apply_translation(-m.bounds[0])
        return m
    s = bk["sbs"]
    box(s["x"], s["y"], s["h"]).export(CP_DIR / "block_sbs.stl")
    fx = bk["flex"]
    box(fx["L"], fx["w"], fx["t"]).export(CP_DIR / "bend_bar.stl")
    tv = bk["traveller"]
    box(tv["x"], tv["y"], tv["h"]).export(CP_DIR / "traveller.stl")
    for n in sorted(set(bk["z"]["combs"])):
        comb_mesh(n).export(CP_DIR / f"z_comb_{n}.stl")
    for j in pk["coupons"]["jobs"]:
        H1P.tower_mesh(j).export(CP_DIR / f"tower_{j['job']}.stl")
    _csv(REL / "coupon_plan.csv", pk["coupons"]["rows"])
    _csv(REL / "coupon_cost.csv", [{k: v for k, v in x.items()} for x in pk["cost"]["lines"]])
    f1 = coupon_figure(REL / "coupon_jobs.png")
    f2 = banner_figure(REL / "safety_hold.png")
    pdf = doc_pdf("PAHT-CF coupons: the H1 decision", md, REL / "COUPONS_PAHT.pdf", [f2, f1])
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [H1P._raster(pdf, _page_with(pdf, "What the results mean"), SCREENS / f"{SHOT}_1.png")]
    shots.append(results_figure(SCREENS / f"{SHOT_BL079}.png"))
    for src, n in ((f2, 2), (f1, 3)):
        dst = SCREENS / f"{SHOT}_{n}.png"
        shutil.copyfile(src, dst)
        shots.append(H1P._shrink(dst))
    man = {"ticket": TICKET, "date": DATE, "checks": pk["checks"], "cost": {k: v for k, v in pk["cost"].items() if k != "lines"},
           "files": sorted(str(p.relative_to(REL)) for p in REL.rglob("*") if p.is_file()),
           "stl": sorted(str(p.relative_to(ROOT)) for p in CP_DIR.glob("*.stl")),
           "screens": [str(p.relative_to(ROOT)) for p in shots], "pdf": str(pdf.relative_to(ROOT))}
    _w(REL / "manifest.json", json.dumps(man, indent=1))
    return {"pdf": pdf, "screens": shots}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="build in memory, print the checks, write nothing")
    a = ap.parse_args(argv)
    pk = package()
    for m in pk["checks"]:
        print("-", m)
    if not a.check:
        out = write(pk)
        for p in out["screens"]:
            print("SCREEN", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
