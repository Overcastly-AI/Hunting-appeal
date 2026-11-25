"""BL-071: the PPA-CF H1-P build path (manufacturing-engineer, 2026-11-25).

    python designs/pack_5200/frame_h1p_build.py            # write print/frame_h1p/ and outputs/release/frame_h1p_ppa/
    python designs/pack_5200/frame_h1p_build.py --check    # build in memory, print the checks, write nothing

H1-P is the H1 frame re-tuned for Bambu PPA-CF (BL-070, ``iter1/frame/bl070_h1p.json``). It is built ALONGSIDE the
PAHT-CF H1 path (``frame_h1_build.py``, ``print/frame_h1/BUILD_H1.md``), which stays the fallback. This script writes
only what differs on the PPA path:

* ``print/frame_h1p/COUPONS_H1P.md``: the first print (coupons, about one spool) and the gate (no H1-P half before
  CA-3-PPA and CA-1-PPA pass), with one beginner sheet per coupon test (CA-3-PPA, CA-1-PPA, CA-4-PPA, T4c-PPA);
* ``print/frame_h1p/PRINT_SHEET_H2S.md``: the Bambu H2S settings for both halves, every value with its source;
* ``print/frame_h1p/BUILD_H1P.md``: the BOM / cost of the PPA path, the through-bolt hip mount (8 x Ti M5 x 20 DIN 7984
  + A2 DIN 934 nuts in traps; no brass inserts), and which BUILD_H1 sections carry over unchanged;
* ``print/frame_h1p/test_pieces/t4c_stay_R.stl``: the T4c-PPA stay coupon cut from the H1-P frame;
* ``outputs/release/frame_h1p_ppa/``: copies of the above, ``bom_h1p_ppa.csv``, ``coupon_plan.csv`` and a tech pack PDF
  (``huntkit.manufacturing.techpack``, CONTRACTS section 5).

The register rows and test-kit sheets of the four PPA coupon tests are built here (``register_rows``,
``guide_steps``, ``results_items``) and written by ``physical_test_kit.py`` (group G8, release R1-PPA).

Every pass line is read from ``bl070_h1p.json`` (``pass_lines``); every print value from the PPA-CF material record
or the BL-070 record; numbers with no source are marked ASSUMPTION and listed with what settles them. Units mm, g, N,
MPa, N m internally; inches, oz, lb, in lbf shown next to them.
"""
from __future__ import annotations

import argparse
import csv
import functools
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

DATE = "2026-11-25"
TICKET = "BL-071"
BL070 = HERE / "iter1" / "frame" / "bl070_h1p.json"
H1P_STL = HERE / "iter1" / "frame" / "h1p"
MAT = ROOT / "data" / "materials"
AN = HERE / "analysis"
PRINT = HERE / "print" / "frame_h1p"
TP_DIR = PRINT / "test_pieces"
REL = ROOT / "outputs" / "release" / "frame_h1p_ppa"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261125_bl071"
BUILD_H1 = "designs/pack_5200/print/frame_h1/BUILD_H1.md"

IN = 25.4
OZ = 28.3495
LB_G = 453.592
N_PER_LBF = 4.44822
NM_PER_INLBF = 0.112985
G = 9.81

# --- coupon geometry (standards; the shape is what bl070_h1p.json names)
ISO1A = dict(L=170.0, gauge_l=80.0, gauge_w=10.0, end_w=20.0, r=24.0, t=4.0)   # ISO 527-2 type 1A
SBS = dict(L=24.0, w=8.0, t=4.0, span=16.0, nose_d=6.0, sup_d=3.0)             # ASTM D2344: L 6t, w 2t, span 4t
FLEX = dict(L=80.0, w=10.0, t=4.0, span=64.0)                                  # ISO 178: 80 x 10 x 4, span 16 h
Z_TIE_EXTRA = 0.05      # ASSUMPTION Z-TIE: standing Z bars tied in threes by 2 mm ribs on the grip ends, +5 % volume
SPARES = 1              # ASSUMPTION SPARE: one spare per coupon type and build direction
WASTE = 0.08            # the BL-053 / BL-070 filament rule (+8 % purge, brim, skirt)
RATE_MM3_S = 8.0        # BL-053 print-time rule, x 1.08 (bl070_h1p ASSUMPTION PPA-TIME)
RATE_K = 1.08
T4C_CUT = dict(x_min=95.0, z_max=240.0)   # R stay z 0-240, cut inboard of the stay at x = +95 mm (strut stubs left on)

# --- lever rig (designs/pack_5200/tests_physical/CA1_fatigue_rig.md; physical_test_kit ASCII G4)
LEVER_RATIO = 4.0       # drive 480 mm / coupon 120 mm
LEVER_COUPON_ARM_M = 0.120
LEVER_W, LEVER_T = 40.0, 10.0       # 6061 lever 40 x 10 x 600
AL6061_YIELD = 276.0    # data/materials/metals/alu_6061_t6.yaml (read at run time when present)
CELL_KG = 100.0         # kit B S-type load cell
CRANE_STOP_KG = 280.0   # kit A crane scale stop (physical_test_kit G2 safety)

# --- hip through-bolts
NUT_DW_MIN = 6.9        # ISO 4032 / DIN 934 M5 bearing face dw min, mm (the trap seat sees this ring)
K_NUT = 0.2             # ASSUMPTION K-NUT: nut factor 0.2, the same as huntkit/gendesign/frame_h1.py Joint.torque_nm
CREEP_GOAL = 1.5        # hip mount creep goal (bl070_h1p.json h1p.hip_mount rows 'carry', goal 1.5)
MOUNT_SEAT_N = 20.0     # BUILD_H1 section 12 step 5 (ASSUMPTION MOUNT-SEAT there)

FACE_DOWN = "y/y (as printed)"
HOLD = "HOLD — not released (review 8 B-1/B-2)"
REVIEW8 = AN / "review_20261125_eighth.md"
TORQUE_TBD = "TBD by BL-073 (review 8 B-1): ASSUMPTION, no value set"
FREEZER_C = -20.0       # T4c-PPA soak (bl070_h1p.json)
COND_RH_BOX = 53.0      # the kit's magnesium nitrate box (physical_test_kit G1), against the 50 % the JSON names


# ============================================================================ sources
@functools.lru_cache(maxsize=None)
def h1p_json() -> dict:
    return json.loads(BL070.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def record(rid: str) -> dict:
    for p in MAT.rglob(f"{rid}.yaml"):
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    raise KeyError(rid)


def ppa() -> dict:
    return record("ppa_cf_fdm")


def spool() -> dict:
    """Spool size and price from the PPA-CF record's price basis ('0.75 kg spool $149.99')."""
    r = ppa()
    basis = r["properties"]["print_cost_basis"]
    m = re.search(r"([0-9.]+)\s*kg spool \$([0-9.]+)", basis)
    assert m, basis
    return {"g": float(m.group(1)) * 1000.0, "usd": float(m.group(2)), "basis": basis}


def rho() -> float:
    return ppa()["properties"]["density_kg_m3"] / 1e6       # g/mm3


def _yield_6061() -> float:
    try:
        return float(record("alu_6061_t6")["properties"]["yield_strength_mpa"])
    except Exception:                                         # pragma: no cover
        return AL6061_YIELD


def review8_rows() -> dict:
    """Review 8's summary table rows ('| id | class | what | booked | found | where |'), read at generation time."""
    out = {}
    if not REVIEW8.exists():
        return out
    for line in REVIEW8.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*([BM]-\d+)\s*\|\s*(\w+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
        if m:
            out[m.group(1)] = {"class": m.group(2), "what": m.group(3).strip(), "booked": m.group(4).strip(),
                               "found": m.group(5).replace("**", "").strip(), "where": m.group(6).strip()}
    return out


def coupons() -> dict:
    return {c["id"]: c for c in h1p_json()["coupons"]}


def _num(pat: str, txt: str, grp: int = 1) -> float:
    m = re.search(pat, txt)
    assert m, (pat, txt)
    return float(m.group(grp))


def pass_lines() -> dict:
    """Every pass line of the four PPA coupons, read from the bl070_h1p.json coupon text (never typed here)."""
    c = coupons()
    c1, c3, c4, t4 = c["CA-1-PPA"], c["CA-3-PPA"], c["CA-4-PPA"], c["T4c-PPA"]
    d = h1p_json()
    return {
        "ca1_smax_ratio": _num(r"Smax / UTS = ([0-9.]+)", c1["pass"]),
        "ca1_cycles": float(re.search(r"to (1e\d)", c1["pass"]).group(1)),
        "ca1_n_z": _num(r"all (\d+) Z-built", c1["pass"]),
        "ca1_n_xy": _num(r"all (\d+) XY-built", c1["pass"]),
        "ca1_n_static": _num(r"plus (\d+) static of each", c1["coupons"]),
        "ca1_hz_max": _num(r"<= (\d+) Hz", c1["load"]),
        "ca1_r": _num(r"R ([0-9.]+)", c1["what"]),
        "ca3_z_mpa": _num(r"\(a\) conditioned Z tensile mean - ([0-9.]+) SD >= ([0-9.]+) MPa", c3["pass"], 2),
        "ca3_k_sd": _num(r"\(a\) conditioned Z tensile mean - ([0-9.]+) SD", c3["pass"]),
        "ca3_sbs_mpa": _num(r"\(b\) conditioned SBS mean - [0-9.]+ SD >= ([0-9.]+) MPa", c3["pass"]),
        "ca3_dry_z_mpa": _num(r"dry Z mean >= ([0-9.]+) MPa", c3["pass"]),
        "ca3_wet_dry": _num(r"conditioned / dry >= ([0-9.]+)", c3["pass"]),
        "ca3_n": _num(r"(\d+) Z tensile \+ (\d+) SBS dry", c3["coupons"]),
        "ca3_hold_frac": _num(r"between [0-9.]+ and ([0-9.]+) x that", c3["if_below"]),
        "cond_days": _num(r"conditioned \((\d+) d at", c3["what"]),
        "cond_c": _num(r"(\d+) d at (\d+) C", c3["what"], 2),
        "cond_rh": _num(r"(\d+) C / (\d+) % RH", c3["what"], 2),
        "ca4_e40": _num(r"E\(40 C wet\) / E\(23 C dry\) >= ([0-9.]+)", c4["pass"]),
        "ca4_e60": _num(r"E\(60 C\) / E\(23 C\) >= ([0-9.]+)", c4["pass"]),
        "ca4_flex60_mpa": _num(r"flexural strength at 60 C >= .*?= ([0-9.]+) MPa", c4["pass"]),
        "ca4_n": _num(r"(\d+) per condition", c4["coupons"]),
        "t4c_n_ppa": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", t4["coupons"]),
        "t4c_n_paht": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", t4["coupons"], 2),
        "t4c_soak_h": _num(r"soaked >= (\d+) h", t4["coupons"]),
        "t4c_temp_c": _num(r"at (-\d+) C", t4["coupons"]),
        "t4c_drop_s": _num(r"within (\d+) s", t4["coupons"]),
        "t4c_drop_m": _num(r"([0-9.]+) m \(", t4["load"]),
        "t4c_slug_kg": _num(r"([0-9.]+) kg steel slug", t4["what"]),
        "t4c_bend_x": _num(r"([0-9.]+) x its C4 set-down stay moment", t4["pass"]),
        "hb6_ppa_n": float(d["h1_ppa"]["hip_inserts"]["hb6_ppa_min_static_n"]),
        "hb6_ppa_n_coupons": 6.0,     # bl070_h1p.md section 4 ('6 PPA coupons'); only if inserts are kept
    }


def pass_lines_recomputed() -> dict:
    """The same lines from the numeric fields (material dict, R1, joint fatigue, record): the tests compare them."""
    d = h1p_json()
    m = d["materials"]["ppa_design"]
    rows = d["h1p"]["rows_by_name"]
    r1 = rows["fatigue, cinch-cycled (R1)"]["value"]
    jf = rows["z 234 joint fatigue"]["value"]
    p = ppa()["properties"]
    z = m["knock"] * m["s_z"] / jf
    return {"ca1_smax_ratio": m["fat"] / r1, "ca3_z_mpa": z, "ca3_sbs_mpa": 0.6 * z,
            "ca3_dry_z_mpa": m["s_z"], "ca3_wet_dry": m["knock"],
            "ca4_e40": p["modulus_40c_wet_ratio"], "ca4_e60": p["modulus_60c_ratio"],
            "ca4_flex60_mpa": m["knock"] * p["bending_strength_xy_mpa"]}


# ============================================================================ coupon geometry and the first print
def iso1a_area() -> float:
    """Plan area of the ISO 527-2 1A bar (mm2): gauge, two R24 transitions, two grip ends."""
    g = ISO1A
    dw = (g["end_w"] - g["gauge_w"]) / 2.0
    lt = math.sqrt(g["r"] ** 2 - (g["r"] - dw) ** 2)
    n = 400
    a_tr = 0.0
    for i in range(n):
        x = (i + 0.5) / n * lt
        a_tr += (g["gauge_w"] + 2.0 * (g["r"] - math.sqrt(g["r"] ** 2 - x ** 2))) * lt / n
    l_end = (g["L"] - g["gauge_l"] - 2.0 * lt) / 2.0
    return g["gauge_l"] * g["gauge_w"] + 2.0 * a_tr + 2.0 * l_end * g["end_w"]


def t4c_stay_mesh():
    """The T4c-PPA coupon: the H1-P R stay z 0-240, cut at x = +95 mm, from the exported frame (frame coordinates)."""
    import numpy as np
    import trimesh
    import manifold3d as m3d
    m = trimesh.load(H1P_STL / "h1_assembled.stl")
    man = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                tri_verts=np.asarray(m.faces, np.uint32)))
    lo = (T4C_CUT["x_min"], m.bounds[0][1] - 5.0, m.bounds[0][2] - 1.0)
    hi = (m.bounds[1][0] + 5.0, m.bounds[1][1] + 5.0, T4C_CUT["z_max"])
    box = m3d.Manifold.cube(tuple(h - l for h, l in zip(hi, lo))).translate(lo)
    out = (man ^ box).to_mesh()
    return trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=True)


def t4c_print_mesh(t=None):
    """The stay coupon turned as the frame prints (wearer face, frame -y, on the plate: layers along frame y)."""
    import numpy as np
    t = (t or t4c_stay_mesh()).copy()
    R = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)    # (x, y, z) -> (x, -z, y)
    t.apply_transform(R)
    t.apply_translation(-t.bounds[0])
    return t


@functools.lru_cache(maxsize=None)
def t4c_piece() -> dict:
    t = t4c_stay_mesh()
    d = h1p_json()["h1p"]["print"]["lower"]
    sup = d["support_g_ppa_high"] / d["part_g_ppa"]           # the lower half's high support share (BL-070)
    g = t.volume * rho()
    return {"volume_mm3": t.volume, "g": g, "support_share": sup, "watertight": bool(t.is_watertight),
            "extents_mm": [float(v) for v in t.extents], "bodies": int(t.body_count)}


def coupon_plan(piece: dict | None = None) -> dict:
    """The first PPA-CF print: every coupon, its count (spares in), mass, and the spool plan. Counts read from the JSON."""
    pl = pass_lines()
    r = rho()
    a1 = iso1a_area() * ISO1A["t"]
    v_sbs = SBS["L"] * SBS["w"] * SBS["t"]
    v_flex = FLEX["L"] * FLEX["w"] * FLEX["t"]
    n_z_fat, n_xy_fat, n_st = int(pl["ca1_n_z"]), int(pl["ca1_n_xy"]), int(pl["ca1_n_static"])
    n3 = int(pl["ca3_n"])
    n4 = int(pl["ca4_n"])
    rows = [
        # (job, coupon, for, shape, orientation, count, volume each mm3)
        ("A flat", "XY tensile bar, ISO 527-2 1A (170 x 20, gauge 10 x 4 x 80)", "CA-1-PPA fatigue",
         "flat on its 20 mm face", n_xy_fat + SPARES, a1),
        ("A flat", "XY tensile bar, ISO 527-2 1A", "CA-1-PPA static (batch XY UTS)", "flat", n_st, a1),
        ("A flat", f"short-beam block {SBS['L']:.0f} x {SBS['w']:.0f} x {SBS['t']:.0f} (ASTM D2344, 4:1 span)",
         "CA-3-PPA interlayer shear, dry + conditioned", "flat (the mid-plane is a layer line)", 2 * n3 + SPARES, v_sbs),
        ("A flat", f"bend bar {FLEX['L']:.0f} x {FLEX['w']:.0f} x {FLEX['t']:.0f} (ISO 178)",
         "CA-4-PPA, 3 conditions", "flat on its 10 mm face", 3 * n4 + SPARES, v_flex),
        ("B standing", "Z tensile bar, ISO 527-2 1A, standing, tied in threes", "CA-3-PPA Z tensile dry",
         "standing on a 20 x 4 end", n3, a1 * (1 + Z_TIE_EXTRA)),
        ("B standing", "Z tensile bar, ISO 527-2 1A, standing", "CA-3-PPA Z tensile conditioned = CA-1-PPA Z static "
         "(same plate, same conditioning)", "standing", n3, a1 * (1 + Z_TIE_EXTRA)),
        ("B standing", "Z tensile bar, ISO 527-2 1A, standing", "CA-1-PPA fatigue", "standing", n_z_fat + SPARES,
         a1 * (1 + Z_TIE_EXTRA)),
    ]
    out = []
    for job, what, use, ori, n, v in rows:
        g = n * v * r
        out.append({"job": job, "coupon": what, "for": use, "orientation": ori, "count": n, "g_each": round(v * r, 2),
                    "g": round(g, 1), "filament_g": round(g * (1 + WASTE), 1),
                    "print_h": round(n * v / RATE_MM3_S * RATE_K / 3600.0, 1)})
    gate_g = sum(x["filament_g"] for x in out)
    pc = piece or t4c_piece()
    n_t4 = int(pl["t4c_n_ppa"])
    t4_fil = n_t4 * pc["g"] * (1 + pc["support_share"]) * (1 + WASTE)
    t4 = {"job": "C stay", "coupon": "T4c-PPA stay `test_pieces/t4c_stay_R.stl` (H1-P R stay z 0-240)",
          "for": "T4c-PPA", "orientation": "wearer face down, tree supports as the frame", "count": n_t4,
          "g_each": round(pc["g"], 1), "g": round(n_t4 * pc["g"], 1), "filament_g": round(t4_fil, 1),
          "print_h": round(n_t4 * pc["volume_mm3"] * (1 + pc["support_share"]) / RATE_MM3_S * RATE_K / 3600.0, 1)}
    sp = spool()
    half = h1p_json()["h1p"]["print"]
    swap_g = sum(max(0.0, half[h]["filament_g_high_with_waste"] - sp["g"]) for h in ("lower", "upper"))
    return {"rows": out, "t4c": t4, "gate_filament_g": round(gate_g, 1), "t4c_filament_g": round(t4_fil, 1),
            "spool_g": sp["g"], "gate_spools": round(gate_g / sp["g"], 2),
            "spool_b_left_after_gate_g": round(sp["g"] - gate_g, 1), "swap_g": round(swap_g, 1),
            "swap_fits_spool_b": sp["g"] - gate_g >= swap_g,
            "gate_print_h": round(sum(x["print_h"] for x in out), 1)}


def spool_plan(cp: dict | None = None) -> dict:
    """Which spool feeds what (BL-070: each half starts on a full dried spool, a second dried spool staged)."""
    cp = cp or coupon_plan()
    sp = spool()
    pr = h1p_json()["h1p"]["print"]
    rows = [
        ("1", "coupons, job A + job B (the gate coupons), then kept sealed and dried as the swap spool for both halves",
         cp["gate_filament_g"] + cp["swap_g"]),
        ("2", "H1-P lower half: starts full; run-out swap to spool 1", min(sp["g"], pr["lower"]["filament_g_high_with_waste"])),
        ("3", "H1-P upper half: starts full; run-out swap to spool 1", min(sp["g"], pr["upper"]["filament_g_high_with_waste"])),
        ("4", "T4c-PPA stays (3), job C, topped up from spool 1's rest after both halves are printed",
         min(sp["g"], cp["t4c_filament_g"])),
    ]
    left1 = sp["g"] - cp["gate_filament_g"] - cp["swap_g"]
    from1 = max(0.0, cp["t4c_filament_g"] - sp["g"])
    frame = 3
    return {"rows": [{"spool": a, "use": b, "g": round(c, 0)} for a, b, c in rows], "frame_path_spools": frame,
            "frame_path_usd": round(frame * sp["usd"], 2), "with_t4c_spools": 4,
            "with_t4c_usd": round(4 * sp["usd"], 2), "spool_usd": sp["usd"], "spool_g": sp["g"],
            "spool1_left_g": round(left1, 0), "t4c_from_spool1_g": round(from1, 0), "t4c_fits_4_spools": from1 <= left1}


# ============================================================================ lever rig and bench loads
def rig_loads() -> dict:
    """Peak loads of the PPA coupons on the kit's rigs (booked values: TDS dry / design conditioned)."""
    p = ppa()["properties"]
    m = h1p_json()["materials"]["ppa_design"]
    a_g = ISO1A["gauge_w"] * ISO1A["t"]
    xy_dry = p["tensile_strength_xy_mpa"] * a_g
    xy_cond = m["knock"] * p["tensile_strength_xy_mpa"] * a_g
    z_dry = p["tensile_strength_z_mpa"] * a_g
    lever_m = xy_dry * LEVER_COUPON_ARM_M
    z_mod = LEVER_W ** 2 * LEVER_T / 6.0
    sbs_dry_mpa = 0.6 * p["tensile_strength_z_mpa"]           # INTERLAYER-0.6 on the TDS mean, for sizing only
    return {"gauge_mm2": a_g, "xy_dry_n": xy_dry, "xy_cond_n": xy_cond, "z_dry_n": z_dry,
            "xy_dry_link_kg": xy_dry / LEVER_RATIO / G, "xy_cond_link_kg": xy_cond / LEVER_RATIO / G,
            "lever_sigma_mpa": lever_m * 1000.0 / z_mod, "lever_sigma_doubled_mpa": lever_m * 1000.0 / (2 * z_mod),
            "al_yield_mpa": _yield_6061(),
            "xy_fat_n": pass_lines()["ca1_smax_ratio"] * xy_cond, "z_fat_n": pass_lines()["ca1_smax_ratio"] * m["knock"] * z_dry,
            "sbs_dry_n": sbs_dry_mpa * SBS["w"] * SBS["t"] / 0.75,
            "flex60_n": pass_lines()["ca4_flex60_mpa"] * 2 * FLEX["w"] * FLEX["t"] ** 2 / (3 * FLEX["span"]),
            "flex_break_dry_n": p["bending_strength_xy_mpa"] * 2 * FLEX["w"] * FLEX["t"] ** 2 / (3 * FLEX["span"])}


# ============================================================================ hip mount (through-bolts)
def hip() -> dict:
    d = h1p_json()
    hm = d["h1p"]["hip_mount"]
    m = d["materials"]["ppa_design"]
    fl = json.loads((AN / "h1_closeout.json").read_text())["mount_flange"]
    from huntkit.gendesign.frame_h1 import JOINT
    n = len(d["h1_ppa"]["hip_inserts"]["pattern"]["positions_xz"])
    nut_hole = 5.5                                            # bl070_h1p.NUT_HOLE_D (D5.5 through hole)
    z_allow = m["knock"] * m["s_z"]
    a_dw = math.pi / 4 * (NUT_DW_MIN ** 2 - nut_hole ** 2)
    rup = ppa()["properties"]["creep_rupture_8h_40c_ratio"]
    f_pre = rup * z_allow * a_dw / CREEP_GOAL
    torque = K_NUT * 5.0 / 1000.0 * f_pre                      # information for BL-073 only, NOT a build value
    grip = fl["t_mm"] + hm["nut_seat_depth_mm"]
    rows = hm["rows"]
    walk = rows["walk|H_frame"]["T_max_n"]
    c2 = rows["C2|H_frame"]["T_max_n"]
    carry = rows["carry|H_frame"]["T_max_n"]
    fat = m["fat"]
    nut_bear_n = z_allow * a_dw
    return {"n": n, "screw": "Ti gr5 (Ti-6Al-4V) M5 x 20 low-head socket cap screw, DIN 7984",
            "nut": f"M5 hex nut A2 stainless, DIN 934, m = {JOINT.nut_t:.1f} mm, {JOINT.nut_af:.0f} AF",
            "nut_t": JOINT.nut_t, "nut_af": JOINT.nut_af, "flange_t": fl["t_mm"], "seat": hm["nut_seat_depth_mm"],
            "grip": grip, "screw_len": 20.0, "tip_vs_nut_top_mm": 20.0 - grip - JOINT.nut_t,
            "hole_d": nut_hole, "mount_hole_d": json.loads((AN / "bl058.json").read_text())["hip_mount"]["hole_d_mm"],
            "z_allow": z_allow, "a_dw": a_dw, "a_model": hm["bearing_ring_mm2"], "rup": rup, "f_pre": f_pre,
            "torque_info_creep_cap": torque, "torque": None, "torque_txt": TORQUE_TBD, "min_sf": hm["min_sf"], "hardware": hm["hardware"],
            "nut_bear_n_dw": nut_bear_n, "sf_strength_dw": nut_bear_n / c2, "sf_fatigue_dw": fat * nut_bear_n / walk,
            "sf_creep_dw": rup * nut_bear_n / carry}


# ============================================================================ register rows, sheets, results
REG_COLS = ["id", "status", "tier", "title", "defined_in", "what_it_proves", "gates", "grams_at_stake_g",
            "safety_at_stake", "specimen", "kit", "steps", "pass_fail", "cost_usd", "cost_basis", "hours_hands_on",
            "hours_machine", "phase", "run_order", "first_weekend", "notes", "g_per_usd_eq"]
DEF = "designs/pack_5200/iter1/frame/bl070_h1p.json coupons; designs/pack_5200/print/frame_h1p/COUPONS_H1P.md"


def _mpa(x: float) -> str:
    return f"{x:g} MPa ({x * 145.038:,.0f} psi)"


def _n(x: float) -> str:
    return f"{x:,.0f} N ({x / G:.1f} kg on the scale, {x / N_PER_LBF:,.0f} lbf)"


def guide_steps() -> dict:
    """Beginner steps per PPA test, one list each (the register 'steps' cell and the sheets use these)."""
    pl = pass_lines()
    rl = rig_loads()
    cd, cc, crh = int(pl["cond_days"]), int(pl["cond_c"]), int(pl["cond_rh"])
    k = pl["ca3_k_sd"]
    lv = pl["ca1_smax_ratio"]
    sbs_f = "F_max x 0.75 / (width x thickness)"
    return {
        "CA-3-PPA": [
            f"Print job A and job B of the coupon plan (COUPONS_H1P.md section 2) from spool 1. Label each bar with a paint pen: CA3-Z-D1 to D{int(pl['ca3_n'])} (dry), CA3-Z-C1 to C{int(pl['ca3_n'])} (conditioned), the same for the short-beam blocks (CA3-S-D.., CA3-S-C..).",
            "DRY set: as soon as the plate is cool, put the dry bars and blocks in a zip bag with a desiccant pack. Test them within 24 h.",
            f"CONDITIONED set: into the conditioning box (kit D, about {COND_RH_BOX:.0f} % RH) at room temperature ({cc} C / {cc * 9 / 5 + 32:.0f} F) for {cd} days. Write the start date on the box.",
            "Measure every bar's gauge width and thickness, and every block's width and thickness, with the caliper at 3 points. Write the smallest on the part.",
            f"Z tensile (each bar): lever rig static set-up (turnbuckle in place of the spring, as CA-1 step 2). Clamp the 20 mm grip ends 35 mm deep. Turn the turnbuckle about 1 turn every 10 s until the bar breaks. Strength = peak cell force x {LEVER_RATIO:.0f} / (width x thickness). Expect about {_n(rl['z_dry_n'])} at the bar dry ({rl['z_dry_n'] / LEVER_RATIO / G:.0f} kg on the cell).",
            f"Short-beam shear (each block): 3-point fixture with a D{SBS['nose_d']:.0f} mm loading pin on top and two D{SBS['sup_d']:.0f} mm support pins {SBS['span']:.0f} mm apart ({SBS['span'] / IN:.2f} in); the block lies flat, as printed. Pull down on the loading pin with the come-along and crane scale (kit A) slowly until the load drops. Shear strength = {sbs_f}. Expect up to about {_n(rl['sbs_dry_n'])}.",
            "Look at every broken piece with the loupe: a Z bar should break flat along one layer line; a short-beam block should crack along the middle layer line. Photograph each.",
            f"For each set (dry Z, conditioned Z, dry SBS, conditioned SBS) type the 6 values into the results sheet. The sheet row 'mean - {k:g} SD' is a spreadsheet formula: =AVERAGE(the 6 values) - {k:g} * STDEV(the 6 values). Type its result.",
            "Send the sheet the same day: the frame print waits on it.",
        ],
        "CA-1-PPA": [
            f"Use the conditioned bars of job A (XY) and job B (Z) after their {cd} days in the box, the same plate as CA-3-PPA.",
            f"Batch strength first. XY: pull the {int(pl['ca1_n_static'])} conditioned XY static bars to failure as CA-3-PPA step 5. These bars need about {_n(rl['xy_cond_n'])} at the bar ({rl['xy_cond_link_kg']:.0f} kg at the cell; dry up to {rl['xy_dry_link_kg']:.0f} kg): fit the 200 kg cell (shopping list) and bolt the second 40 x 10 lever bar beside the lever for these {int(pl['ca1_n_static'])} pulls (ASSUMPTION LEVER-XY). Z: the batch Z strength is the CA-3-PPA conditioned Z mean (same bars, same plate).",
            f"UTS_xy = mean of the {int(pl['ca1_n_static'])} XY strengths; UTS_z = the CA-3-PPA conditioned Z mean. Peak force for each fatigue bar: F_max = {lv:g} x UTS x that bar's own gauge area (width x thickness). F_min = 0.1 x F_max (R 0.1). Booked values: XY about {_n(rl['xy_fat_n'])}, Z about {_n(rl['z_fat_n'])} at the bar; the cell reads F / {LEVER_RATIO:.0f}.",
            "Remove the second lever bar and put the 100 kg cell back. Set the crank throw and the turnbuckle so the cell swings between F_min / 4 and F_max / 4; check over 20 slow turns by hand before the motor runs.",
            f"Run each bar to {pl['ca1_cycles']:,.0f} cycles at 1 Hz (about 28 h; never faster than {pl['ca1_hz_max']:.0f} Hz). The rig stops itself if the bar breaks, its stiffness drops more than 10 % or the force drifts more than 5 %. Z bars first ({int(pl['ca1_n_z'])}), then XY ({int(pl['ca1_n_xy'])}).",
            "After each run-out look at the gauge with the loupe for a crack or whitening; photograph it. Type the cycles the bar reached in the results sheet (a broken bar: the counter reading when it broke).",
            "Any bar that breaks before 100,000 cycles: stop, photograph, send the sheet. Do not replace it with the spare to make the count.",
            "Send the rig's CSV log with the results sheet.",
        ],
        "CA-4-PPA": [
            f"Job A bend bars: {int(pl['ca4_n'])} stay dry for 23 C, {int(pl['ca4_n'])} go in the conditioning box for {cd} days (the '40 C wet' set), {int(pl['ca4_n'])} stay dry (sealed with desiccant) for 60 C.",
            f"Set the 3-point fixture's support pins {FLEX['span']:.0f} mm apart ({FLEX['span'] / IN:.2f} in). Bar flat, as printed. Dial indicator (0.01 mm) on top of the bar at mid-span, against the loading pin.",
            "Stiffness (each bar): hang 2.0 kg on the loading pin, zero the dial; add 5.0 kg more (7.0 kg total); read the dial (mm). Write the reading. E = span^3 x 49.0 N / (4 x width x thickness^3 x reading) in MPa (mm units). The sheet does this sum when you type the dial reading in the 'dial' row.",
            f"Strength (each bar, after its stiffness reading): pull down on the loading pin with the come-along and crane scale until it breaks. Strength = 3 x F x span / (2 x width x thickness^2). Expect about {_n(rl['flex_break_dry_n'])} dry at 23 C (73 F).",
            "23 C dry: the first set, at room temperature.",
            "40 C wet: take the conditioned set out of the box, put it with the fixture in the 40 C box for 1 h, test inside the box (lid open just enough for the hook), one bar at a time.",
            "60 C: set the 40 C box thermostat to 60 C (140 F); check with the thermometer that it holds 58-62 C for 30 min (ASSUMPTION BOX-60). Bars and fixture in for 1 h, test inside as above.",
            "Ratios: E(40 C wet) / E(23 C) and E(60 C) / E(23 C), each the mean of 5 over the mean of 5. Type them in the sheet.",
        ],
        "T4c-PPA": [
            f"Print job C: {int(pl['t4c_n_ppa'])} stays `test_pieces/t4c_stay_R.stl` in PPA-CF with the frame settings (PRINT_SHEET_H2S.md), and {int(pl['t4c_n_paht'])} in PAHT-CF with the BUILD_H1 settings (the control). Clean the supports off as the frame. Label them T4c-P1..P{int(pl['t4c_n_ppa'])} and T4c-A1.",
            f"Pin a {pl['t4c_slug_kg']:.1f} kg ({pl['t4c_slug_kg'] * 2.2046:.1f} lb) steel slug through the hinge eye with a 5 mm pin (kit A dowel).",
            f"Freezer soak: put the stays and an oven thermometer in the freezer for at least {pl['t4c_soak_h']:.0f} h. It must read {pl['t4c_temp_c']:.0f} C ({pl['t4c_temp_c'] * 9 / 5 + 32:.0f} F) or colder; a home freezer often reads only -18 C (ASSUMPTION FREEZER): use a chest freezer on its coldest setting and write the reading.",
            f"Lay a sheet of 19 mm (3/4 in) plywood flat on concrete. Mark {pl['t4c_drop_m'] * 1000:.0f} mm ({pl['t4c_drop_m'] / 0.0254:.0f} in) up a wall from the plywood face.",
            f"One stay at a time, within {pl['t4c_drop_s']:.0f} s of taking it out: hold it by the slug with the foot down, bottom of the foot at the mark, and let go. Pick it up, back in the freezer for 30 min, then drop it again side-on (stay lying flat, wearer face down).",
            "Look at the foot and the hinge eye with the 10x loupe: any crack, any white patch, any line along a layer? Then dye penetrant on the foot and the eye (spray cleaner, penetrant 10 min, wipe, developer): any red line is a crack. Tap the stay with a screwdriver handle: a dull note where it rang before is a crack.",
            f"Bend: when the engineer has posted the bend load (the {pl['t4c_bend_x']:g} x C4 set-down stay moment; PENDING, see the note), load the stay in the 3-point fixture to that load and hold 1 min. Look again.",
            "Type Y or N per stay and per drop in the results sheet. Photograph every stay, both faces, after each drop.",
        ],
    }


def register_rows() -> list[dict]:
    pl = pass_lines()
    c = coupons()
    st = guide_steps()
    sp = spool()
    cp = coupon_plan()
    hm = hip()

    def steps(t):
        return "; ".join(f"({i}) {s.replace('; ', ', ')}" for i, s in enumerate(st[t], 1))

    tie = "H1-P full-frame print (BUILD_H1P gate): no H1-P half is printed before CA-3-PPA and CA-1-PPA pass"
    rows = [
        dict(id="CA-3-PPA", status="ACTIVE", tier="safety",
             title=f"PPA-CF Z tensile + interlayer shear, dry and conditioned {int(pl['cond_days'])} d (H2S prints)",
             defined_in=DEF, what_it_proves=c["CA-3-PPA"]["settles"], gates=tie, grams_at_stake_g="0",
             safety_at_stake=f"H1-P margins tied: {c['CA-3-PPA']['margin_tied']}",
             specimen=c["CA-3-PPA"]["coupons"] + f"; Z bars ISO 527-2 1A standing, short-beam blocks {SBS['L']:.0f} x {SBS['w']:.0f} x {SBS['t']:.0f} flat",
             kit="B, A, D", steps=steps("CA-3-PPA"),
             pass_fail=(f"(a) conditioned Z tensile, mean - {pl['ca3_k_sd']:g} SD >= {pl['ca3_z_mpa']:g} MPa; (b) conditioned "
                        f"short-beam shear, mean - {pl['ca3_k_sd']:g} SD >= {pl['ca3_sbs_mpa']:g} MPa; (c) record only: dry Z "
                        f"mean (booked >= {pl['ca3_dry_z_mpa']:g} MPa) and conditioned / dry (booked >= {pl['ca3_wet_dry']:g}). "
                        f"Between {pl['ca3_z_mpa']:g} and {pl['ca3_hold_frac']:g} x that: hold the PPA build; below: stay on PAHT-CF"),
             cost_usd=f"{cp['rows'][2]['filament_g'] * sp['usd'] / sp['g'] + 2 * cp['rows'][4]['filament_g'] * sp['usd'] / sp['g']:.2f}",
             cost_basis=f"PPA-CF filament at USD {sp['usd']} / {sp['g']:.0f} g (record ppa_cf_fdm); rigs from kits A, B",
             hours_hands_on="4", hours_machine=f"{24 * pl['cond_days']:.0f}", phase="1", run_order="90", first_weekend="N",
             notes="BL-071: PPA path. The conditioned Z bars also give CA-1-PPA's batch Z strength. ASSUMPTION COND-BOX: the kit's ~53 % RH box stands in for 50 % RH", g_per_usd_eq=""),
        dict(id="CA-1-PPA", status="ACTIVE", tier="safety",
             title=f"PPA-CF R {pl['ca1_r']:g} fatigue coupons, Z and XY, at {pl['ca1_smax_ratio']:g} x conditioned UTS",
             defined_in=DEF + "; designs/pack_5200/tests_physical/CA1_fatigue_rig.md (rig)",
             what_it_proves=c["CA-1-PPA"]["settles"], gates=tie, grams_at_stake_g="0",
             safety_at_stake=f"H1-P {c['CA-1-PPA']['margin_tied']}",
             specimen=c["CA-1-PPA"]["coupons"] + "; the Z statics are the CA-3-PPA conditioned Z bars",
             kit="B, D", steps=steps("CA-1-PPA"),
             pass_fail=(f"all {int(pl['ca1_n_z'])} Z-built and all {int(pl['ca1_n_xy'])} XY-built bars run out to "
                        f"{pl['ca1_cycles']:,.0f} cycles at Smax = {pl['ca1_smax_ratio']:g} x the batch's conditioned mean UTS (R {pl['ca1_r']:g})"),
             cost_usd=f"{(cp['rows'][0]['filament_g'] + cp['rows'][1]['filament_g'] + cp['rows'][6]['filament_g']) * sp['usd'] / sp['g'] + 30 + 15:.2f}",
             cost_basis="PPA-CF filament (record ppa_cf_fdm) + 200 kg S cell USD 30 + second lever bar USD 15 (ASSUMPTION, shopping list)",
             hours_hands_on="6", hours_machine=f"{(pl['ca1_n_z'] + pl['ca1_n_xy']) * pl['ca1_cycles'] / 3600:.0f}",
             phase="2", run_order="91", first_weekend="N",
             notes="BL-071: PPA path. 12 x 27.8 h at 1 Hz: about 2 weeks of rig time after the 14 d conditioning. ASSUMPTION LEVER-XY (static XY pulls only)", g_per_usd_eq=""),
        dict(id="CA-4-PPA", status="ACTIVE", tier="safety",
             title="PPA-CF 3-point bend modulus and strength at 23 C dry, 40 C wet, 60 C",
             defined_in=DEF, what_it_proves=c["CA-4-PPA"]["settles"],
             gates="H1-P first carry (stiffness and 60 C truck-cab rows); not a print gate",
             grams_at_stake_g="0", safety_at_stake=f"H1-P {c['CA-4-PPA']['margin_tied']}",
             specimen=f"{int(pl['ca4_n'])} XY bend bars {FLEX['L']:.0f} x {FLEX['w']:.0f} x {FLEX['t']:.0f} per condition (job A)",
             kit="B, A, D", steps=steps("CA-4-PPA"),
             pass_fail=(f"E(40 C wet) / E(23 C dry) >= {pl['ca4_e40']:g}; E(60 C) / E(23 C) >= {pl['ca4_e60']:g}; "
                        f"flexural strength at 60 C >= {pl['ca4_flex60_mpa']:g} MPa"),
             cost_usd=f"{cp['rows'][3]['filament_g'] * sp['usd'] / sp['g']:.2f}", cost_basis="PPA-CF filament (record); 40 C box and bend fixture from kit B",
             hours_hands_on="4", hours_machine="3", phase="2", run_order="92", first_weekend="N",
             notes="BL-071: PPA path. ASSUMPTION BOX-60: the 40 C box holds 60 C", g_per_usd_eq=""),
        dict(id="T4c-PPA", status="ACTIVE", tier="safety",
             title=f"{pl['t4c_temp_c']:.0f} C drop of a printed H1-P stay, PPA-CF vs a PAHT-CF control",
             defined_in=DEF + "; designs/pack_5200/analysis/load_standard.md 5.3 (T4c)",
             what_it_proves=c["T4c-PPA"]["settles"], gates="cold-weather use of a PPA-CF frame; not a print gate",
             grams_at_stake_g="0", safety_at_stake=c["T4c-PPA"]["margin_tied"],
             specimen=c["T4c-PPA"]["coupons"] + "; stay file designs/pack_5200/print/frame_h1p/test_pieces/t4c_stay_R.stl",
             kit="A, D", steps=steps("T4c-PPA"), pass_fail=c["T4c-PPA"]["pass"],
             cost_usd=f"{cp['t4c_filament_g'] * sp['usd'] / sp['g'] + 15:.2f}",
             cost_basis="PPA-CF filament (record) + dye penetrant kit USD 15 (ASSUMPTION)",
             hours_hands_on="3", hours_machine=f"{pl['t4c_soak_h']:.0f}", phase="2", run_order="93", first_weekend="N",
             notes="BL-071: PPA path. PENDING (structural-fea-engineer): the bend load in N for 1.5 x the C4 set-down stay moment is not in bl070_h1p.json; the drop part runs without it",
             g_per_usd_eq=""),
        dict(id="HB-6-PPA", status="NOT-NEEDED", tier="safety",
             title=f"M5 heat-set insert pull-out in PPA-CF at 60 C, each >= {pl['hb6_ppa_n']:.0f} N (only if inserts replace the through-bolts)",
             defined_in="designs/pack_5200/iter1/frame/bl070_h1p.md section 4; bl070_h1p.json h1_ppa.hip_inserts",
             what_it_proves="INS-PPA", gates="none while the H1-P hip mount uses through-bolts (DECISIONS 2026-11-25)",
             grams_at_stake_g="0", safety_at_stake=f"insert hip mount on PPA: needs {pl['hb6_ppa_n']:.0f} N, booked 448 N (fails on design values)",
             specimen=f"{int(pl['hb6_ppa_n_coupons'])} PPA-CF insert blocks", kit="",
             steps="not run: the H1-P hip mount is 8 through-bolts with nuts in traps (BUILD_H1P section 5); HB-6b on the frame proves the mount",
             pass_fail=f"each >= {pl['hb6_ppa_n']:.0f} N along the build z at 60 C", cost_usd="0", cost_basis="not run",
             hours_hands_on="0", hours_machine="", phase="-", run_order="", first_weekend="N",
             notes=f"BL-071: NOT NEEDED while through-bolts are used ({hm['hardware']})", g_per_usd_eq=""),
    ]
    rv = review8_rows()
    for r in rows:
        if r["status"] == "ACTIVE" and rv:
            r["notes"] += (f". REVIEW 8: the H1-P frame is on {HOLD}; these pass lines are BL-070's and BL-073 is "
                           "re-specifying them (COUPONS_H1P.md section 9: " + ", ".join(k for k in ("B-2", "M-3", "M-4", "M-6", "M-7", "M-8") if k in rv) + ")")
    for r in rows:
        assert list(r) == REG_COLS or set(r) == set(REG_COLS), set(r) ^ set(REG_COLS)
    return rows


def results_items() -> dict:
    """Rows for outputs/release/test_kit/results_template.csv: (sample, quantity, unit, check, limit, settles)."""
    pl = pass_lines()
    k = pl["ca3_k_sd"]
    n3 = int(pl["ca3_n"])
    out = {}
    rows = []
    for cond in ("dry", "conditioned"):
        for kind, u in (("Z tensile strength", "MPa"), ("short-beam shear strength", "MPa")):
            rows += [(f"{cond} {i}", f"{kind}, {cond}", u, "record", "", "") for i in range(1, n3 + 1)]
    rows += [("conditioned set", f"Z tensile, mean - {k:g} SD", "MPa", "min", f"{pl['ca3_z_mpa']:g}", "WET-PPA; LINEAR-Z"),
             ("conditioned set", f"short-beam shear, mean - {k:g} SD", "MPa", "min", f"{pl['ca3_sbs_mpa']:g}", "INTERLAYER-0.6"),
             ("dry set", f"Z tensile mean (booked >= {pl['ca3_dry_z_mpa']:g})", "MPa", "record", "", "WET-PPA"),
             ("both sets", f"conditioned / dry Z mean (booked >= {pl['ca3_wet_dry']:g})", "ratio", "record", "", "WET-PPA")]
    out["CA-3-PPA"] = rows
    rows = [(f"XY static {i}", "XY tensile strength, conditioned", "MPa", "record", "", "") for i in range(1, int(pl["ca1_n_static"]) + 1)]
    rows += [(f"Z {i}", f"cycles reached at {pl['ca1_smax_ratio']:g} x UTS_z", "cycles", "min", f"{pl['ca1_cycles']:.0f}", "FAT-PPA")
             for i in range(1, int(pl["ca1_n_z"]) + 1)]
    rows += [(f"XY {i}", f"cycles reached at {pl['ca1_smax_ratio']:g} x UTS_xy", "cycles", "min", f"{pl['ca1_cycles']:.0f}", "FAT-PPA")
             for i in range(1, int(pl["ca1_n_xy"]) + 1)]
    out["CA-1-PPA"] = rows
    out["CA-4-PPA"] = [
        ("23 C dry, 5 bars", "E mean", "MPa", "record", "", ""),
        ("40 C wet, 5 bars", "E(40 C wet) / E(23 C dry)", "ratio", "min", f"{pl['ca4_e40']:g}", "E-SCALE"),
        ("60 C, 5 bars", "E(60 C) / E(23 C dry)", "ratio", "min", f"{pl['ca4_e60']:g}", "E-SCALE"),
        ("60 C, 5 bars", "flexural strength mean", "MPa", "min", f"{pl['ca4_flex60_mpa']:g}", "E-SCALE"),
        ("60 C box", "thermometer reading during the 60 C tests", "C", "band", "58..62", "BOX-60"),
    ]
    rows = [("freezer", "thermometer reading at the end of the soak", "C", "max", f"{pl['t4c_temp_c']:g}", "COLD")]
    for i in range(1, int(pl["t4c_n_ppa"]) + 1):
        rows += [(f"PPA stay {i}", "foot-first drop: no crack, no whitening, dye clean, tap clean", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA stay {i}", "side-on drop: no crack, no whitening, dye clean, tap clean", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA stay {i}", "bend at the posted load, 1 min: no crack", "Y/N", "yes", "Y", "COLD")]
    rows += [("PAHT control", "both drops and the bend: no crack (record Y or N)", "Y/N", "record", "", "")]
    out["T4c-PPA"] = rows
    return out


# ============================================================================ BOM (CONTRACTS section 5 BOMLine)
DRYER = {"item": "forced-air drying oven that holds 120 C (248 F) or more, chamber >= 250 mm (one 0.75 kg spool), digital thermostat",
         "usd": 376.90,
         "source": ("ASSUMPTION price: generic benchtop forced-air drying oven, Walmart listings USD 376.90-749.00 "
                    "(search snapshot 2026-11-25, https://www.walmart.com/ip/5181282844 , https://www.walmart.com/ip/6985519683 ; "
                    "Sanfa DHG-9023J USD 583, https://www.nbclab.com/p/27228/). Consumer filament dryers top out below "
                    "120 C (SUNLU FilaDryer E2 110 C max, USD 299.99, https://www.matterhackers.com/store/l/sunlu-filadryer-e2-filament-dryer/sk/MLY0M6YG): "
                    "they do not meet the rule")}


def bom() -> list:
    from huntkit.manufacturing.records import BOMLine
    sp = spool()
    pr = h1p_json()["h1p"]["print"]
    cp = coupon_plan()
    hm = hip()
    A = "ASSUMPTION (shop price, check at purchase)"
    up = sp["usd"] / sp["g"]
    frame_fil = pr["lower"]["filament_g_high_with_waste"] + pr["upper"]["filament_g_high_with_waste"]
    L = [
        BOMLine("filament", "Bambu PPA-CF 1.75 mm, 0.75 kg spool: the two H1-P halves (spools 2 and 3 + the swaps from spool 1)",
                "ppa_cf_fdm", 2, "spool", round(100 * WASTE, 1), sp["usd"], round(2 * sp["usd"], 2), kit="FRAME",
                source=sp["basis"], notes=f"halves need {frame_fil:.0f} g with supports, high bound, + 8 % (bl070_h1p.json h1p.print)",
                proto_qty=2),
        BOMLine("filament", "Bambu PPA-CF 0.75 kg spool: spool 1, the gate coupons (jobs A + B) and the run-out swap reserve",
                "ppa_cf_fdm", 1, "spool", round(100 * WASTE, 1), sp["usd"], sp["usd"], kit="FRAME",
                source=sp["basis"], notes=f"coupons {cp['gate_filament_g']:.0f} g + swaps {cp['swap_g']:.0f} g", proto_qty=1),
        BOMLine("filament", "Bambu PPA-CF 0.75 kg spool: spool 4, the T4c-PPA stays (job C)", "ppa_cf_fdm", 1, "spool",
                round(100 * WASTE, 1), sp["usd"], sp["usd"], kit="TEST", source=sp["basis"],
                notes=f"{cp['t4c_filament_g']:.0f} g; not needed to print the frame (T4c-PPA gates cold use, not the print)",
                proto_qty=1),
        BOMLine("hip mount", f"HW-HIP-SCR-P: {hm['screw']}", "ti_6al_4v", hm["n"] + 1, "each", 0.0, 2.50,
                round((hm["n"] + 1) * 2.50, 2), kit="FRAME", source=A + " (as the kit's Ti DIN 7984 lines)",
                notes=f"{hm['n']} + 1 spare; replaces the PAHT path's 8 x M5 x 12", proto_qty=hm["n"] + 1),
        BOMLine("hip mount", f"HW-HIP-NUT-P: {hm['nut']}", "sst_304_annealed", hm["n"] + 2, "each", 0.0, 0.10,
                round((hm["n"] + 2) * 0.10, 2), kit="FRAME", source=A,
                notes="NOT ISO 4032 (4.4-4.7 mm thick); caliper each <= 4.1 mm", proto_qty=hm["n"] + 2),
        BOMLine("hip mount", "Loctite 243 medium-strength threadlocker, 10 ml", "", 1, "bottle", 0.0, 9.00, 9.00,
                kit="FRAME", source=A, notes="one drop per screw, on the screw thread only (keep it off the print)"),
        BOMLine("tools", "small torque screwdriver with a 3 mm hex bit, range to suit the hip nut torque", "", 1, "each", 0.0, 60.00, 60.00,
                kit="TOOL", source=A, notes=f"hip nut torque {hm['torque_txt']}; buy when it is set (it may sit below the PAHT path's 0.5-2.5 N m driver)"),
        BOMLine("tools", DRYER["item"], "", 1, "each", 0.0, DRYER["usd"], DRYER["usd"], kit="TOOL (one-time)",
                source=DRYER["source"], notes="PPA-CF drying 100-140 C, 8-12 h (record ppa_cf_fdm, Bambu TDS); DECISIONS 2026-11-25: >= 120 C"),
        BOMLine("tools", "spare hardened-steel 0.6 mm H2 nozzle", "", 1, "each", 0.0, 40.00, 40.00, kit="TOOL", source=A,
                notes="PPA-CF is abrasive; expect faster wear than PAHT-CF (BL-069 section 5)"),
        BOMLine("tools", "glue stick for PA / engineering filaments", "", 1, "each", 0.0, 6.00, 6.00, kit="TOOL", source=A,
                notes="PPA-CF needs glue on textured PEI (record notes)"),
    ]
    return L


def cost() -> dict:
    from huntkit.manufacturing.records import bom_cost
    b = bom()
    fil = sum(x.cost_usd for x in b if x.section == "filament" and x.kit == "FRAME")
    t4 = sum(x.cost_usd for x in b if x.section == "filament" and x.kit == "TEST")
    hw = bom_cost(b, ["hip mount"])
    dryer = sum(x.cost_usd for x in b if x.kit.startswith("TOOL (one-time)"))
    tools = sum(x.cost_usd for x in b if x.section == "tools")
    return {"filament_frame_usd": round(fil, 2), "filament_t4c_usd": round(t4, 2), "hip_hw_usd": round(hw, 2),
            "dryer_usd": round(dryer, 2), "tools_usd": round(tools, 2),
            "per_frame_usd": round(fil + hw, 2), "first_frame_all_usd": round(fil + t4 + hw + tools, 2)}


# ============================================================================ documents
ASSUMPTIONS = {
    "Z-TIE": ("Standing Z bars (170 mm tall on a 20 x 4 mm end) print tied in threes by 2 mm ribs on the grip ends; "
              "the ribs are snipped and sanded off the grips before testing (+5 % volume).", "first coupon print"),
    "SPARE": ("One spare per coupon type and build direction.", "coupon print"),
    "COND-BOX": ("The kit's saturated magnesium nitrate box (about 53 % RH at room temperature) stands in for the 23 C / "
                 "50 % RH conditioning bl070_h1p.json names.", "a hygrometer in the box; engineer review of CA-3-PPA"),
    "LEVER-XY": ("The conditioned XY static pulls (about 4.9 kN at the bar) put 1.4x the PAHT load through the kit B "
                 "lever and over the 100 kg cell: fit a 200 kg S cell and bolt a second 6061 40 x 10 bar beside the "
                 "lever for those 3 pulls only (fatigue loads stay inside the rig as built).", "engineer check of the rig before the XY statics"),
    "BOX-60": ("The 40 C box (cooler + 60 W heater + thermostat) holds 60 C for the CA-4-PPA 60 C set.", "the thermometer row in the results sheet"),
    "FREEZER": ("A chest freezer on its coldest setting reaches -20 C; a home upright freezer often holds only -18 C.", "the thermometer row in the results sheet"),
    "TORQUE-TBD": ("The H1-P hip nut torque is not set. Review 8 B-1 found the D10 washer of NUT-BEAR cannot fit the hex trap, "
                   "and on the nut's own face the fatigue row reads below its goal; BL-073 owns the fix and the torque.",
                   "BL-073, then HB-6b on the first H1-P frame"),
    "K-NUT": ("Nut factor K = 0.2 for a Ti screw in an A2 nut with Loctite 243 (as frame_h1.Joint.torque_nm).", "first article: the paint mark does not move in HB-6b"),
    "TB-TORQUE": ("Hip nut torque = K x d x F, with the preload F capped so the nut's bearing ring (dw 6.9 mm, D5.5 hole) "
                  "stays at or below the PPA creep line / 1.5: F = creep-rupture 0.55 x knocked design Z x ring area / 1.5. "
                  "The BL-070 hip rows check each nut seat against the external screw load (T_max per screw, tipping "
                  "model, FLANGE-RIGID) with no preload term, so a low torque costs no booked margin; Loctite 243 holds the nut.", "HB-6b on the first H1-P frame (paint marks, no turn)"),
    "SPOOL-PLAN": ("Spool 1's left-over after the coupons is the dried swap reserve for both halves (BL-070 SPOOL-SWAP).", "first article"),
    "RUNOUT": ("The H2S pauses on filament run-out when fed from an external spool; the owner is there at the predicted swap time.",
               "first article (the lower half)"),
    "FAN": ("Part cooling for PPA-CF as the PAHT-CF profile (<= 30 %), off below z 3 mm (BL-070 WARP).", "first article"),
}


def print_sheet() -> dict:
    """The H2S settings for H1-P, each with its source."""
    p = ppa()["properties"]
    d = h1p_json()
    pr = d["h1p"]["print"]
    orient = d["h1p"]["orientation"]["fine_sm8.cyc"]
    sp = spool()
    rec = "record `data/materials/polymers/ppa_cf_fdm.yaml`"
    tds = "Bambu PPA-CF TDS V1.0 (cited in the record)"
    w = {a["id"]: a for a in d["assumptions"]}
    rows = [
        ("filament", "Bambu PPA-CF, 1.75 mm, 0.75 kg spool", f"{rec} (trade name, {sp['basis']})"),
        ("dryer", "forced-air oven that HOLDS 120 C (248 F) or more", f"DECISIONS 2026-11-25 (orchestrator: 'a dryer that holds >= 120 C'); {tds}: dry 100-140 C 8-12 h in a forced-air (blast) oven"),
        ("drying", f"{p['drying_temp_c']} C ({p['drying_temp_c'] * 9 / 5 + 32:.0f} F) for {p['drying_time_hours']} h, spool on its side, then straight into a dry box < 20 % RH", f"{rec} drying_temp_c / drying_time_hours; dry box: record notes"),
        ("nozzle", f"hardened steel {p['nozzle_diameter_mm']} mm, {p['nozzle_temp_c']} C ({p['nozzle_temp_c'] * 9 / 5 + 32:.0f} F)", f"{rec} nozzle_temp_c / nozzle_diameter_mm; {tds}: 280-310 C, 0.6 recommended, hardened"),
        ("bed", f"{p['bed_temp_c']} C ({p['bed_temp_c'] * 9 / 5 + 32:.0f} F), textured PEI + glue stick", f"{rec} bed_temp_c; {tds}: 100-120 C, glue"),
        ("chamber", f"{p['chamber_temp_c']} C ({p['chamber_temp_c'] * 9 / 5 + 32:.0f} F), chamber heater on", f"{rec} chamber_temp_c (the H2S maximum); {tds}: 50-80 C"),
        ("chamber pre-heat", "30 min at 65 C with the plate in, BEFORE the print starts", f"bl070_h1p.json ASSUMPTION WARP: {w['WARP']['text']}"),
        ("brim", "15 mm (0.59 in)", "bl070_h1p.json ASSUMPTION WARP / bl070_h1p.md section 3"),
        ("mouse ears", "20 mm (0.79 in) discs, 1 layer, at both stay feet (lower half) and both upper stay ends (upper half). "
         "CANNOT BE BUILT AS WRITTEN: review 8 M-5 (those ends are not on the plate); BL-073 owns the fix", "bl070_h1p.md section 3 (WARP); review 8 M-5"),
        ("part cooling", "off for the first 3 mm (0.12 in) of height; then <= 30 %, aux fan off", "bl070_h1p.md section 3 (WARP: no part cooling below z 3 mm); above it ASSUMPTION FAN (the PAHT-CF profile, BUILD_H1 section 3)"),
        ("layers / walls / infill", "0.20 mm / 6 walls / 6 top-bottom / 100 % infill", f"{BUILD_H1} section 3 (the H1 profile the FE layer rule assumes); bl070_h1p.json coupon profile '100 % infill'"),
        ("speed", "outer walls and the default profile <= 100 mm/s", f"bl070_h1p.json ASSUMPTION PPA-TIME ('TDS speed < 100 mm/s')"),
        ("orientation", "BOTH halves face down (wearer face on the plate) exactly as written in the STL; do not rotate", f"bl070_h1p.json h1p.orientation (fine_sm8.cyc): R1 {orient[FACE_DOWN]['fatigue']:.3f} face down vs {min(v['fatigue'] for k, v in orient.items() if k != FACE_DOWN):.3f}-{max(v['fatigue'] for k, v in orient.items() if k != FACE_DOWN):.3f} on an edge or end"),
        ("supports", "tree supports in PPA-CF from the build plate, as BUILD_H1 section 3 (same areas)", "bl070_h1p.md section 3; BL-069 section 5 (PA/PET interface not recommended)"),
        ("anneal", "NO. Do not anneal the halves", f"BL-069 section 5 / {tds}: anneal may warp and cut toughness; no annealing credit taken"),
    ]
    halves = []
    for h, f in (("lower", "h1_lower_flat.stl"), ("upper", "h1_upper_flat.stl")):
        q = pr[h]
        swap_h = q["print_h_est"] * sp["g"] / q["filament_g_high_with_waste"]
        halves.append({"half": h, "file": f"designs/pack_5200/iter1/frame/h1p/{f}", "filament_g": q["filament_g_high_with_waste"],
                       "spools": q["spools"], "swap": q["needs_spool_swap"], "swap_after_h": swap_h,
                       "print_h": q["print_h_est"], "contact_mm2": q["plate_contact_mm2"], "fits": q["fits_h2s_340x320x340"],
                       "extents": q["extents_mm"], "part_g": q["part_g_ppa"],
                       "support_g": (q["support_g_ppa_est"], q["support_g_ppa_high"])})
    return {"rows": rows, "halves": halves}


FINDING_EFFECT = {
    "B-1": "the hip-mount nut face: fatigue below goal on the real nut ring; the torque is TBD (BUILD_H1P section 5).",
    "B-2": "the hot/wet knock-down is wet-only at 23 C and CA-3-PPA tests at 23 C, so it cannot catch the hot loss: "
           "the CA-3-PPA and CA-1-PPA test temperatures and pass lines are expected to change.",
    "M-3": "CA-1-PPA tests R 0.1 TENSION, but interlayer SHEAR governs H1-P's fatigue; 6/6 run-outs at 1e5 show little "
           "reliability, and the ratio is set from R1 only (the z 234 joint and clevis need a little more). Expect a "
           "short-beam-shear fatigue coupon, a longer run or a higher load, and a 40 C test.",
    "M-4": "'mean - 2.4 SD' at n = 6 is not B-basis (the one-sided 90/95 factor is 3.01 at n = 6), and lone standing Z bars "
           "lay each layer in seconds where a frame half takes minutes, so they over-read the interlayer bond. Expect the "
           "Z and short-beam coupons to be cut from a block printed with a frame-half layer time, and a new factor or n.",
    "M-5": "both halves stand on supports: the upper half touches the plate at one end only and the stay feet are not on "
           "the plate, so the mouse ears of section 1 cannot be added as written.",
    "M-6": "the mid-print spool swap leaves a pause layer at a random height in an interlayer-governed frame. Expect a "
           "planned filament change outside the hot-spot band (or verified auto-refill), and a pause-layer SBS coupon.",
    "M-7": "T4c-PPA covers one stay at about 24 J; the T4b set-down (33 J) and the crown / upper bar are never tested "
           "cold, and 3/3 on a brittle material is weak. Expect 5 stays sized to 33 J, a crown-corner coupon, and a cold "
           "soak on the frame's own T4b / T4c.",
    "M-8": "the booked 40 C wet modulus ratio (0.85) contradicts the record's own conditioned data (about 0.66 at 23 C), "
           "so CA-4-PPA's '>= 0.85' will probably fail on a number the frame does not need; expect a new CA-4 line.",
}


def review8_md(ids: tuple, head: str) -> list[str]:
    """Review 8 findings, as bullets: what the review booked / found (read from its summary table) and the effect."""
    rv = review8_rows()
    L = [head, ""]
    if not rv:
        return L + [f"- Review 8 file not found (`{REVIEW8.relative_to(ROOT)}`).", ""]
    for i in ids:
        r = rv.get(i)
        if not r:
            continue
        L.append(f"- **{i}** ({r['class']}, {r['what']}): booked {r['booked']}, review 8 found {r['found']}. "
                 f"{FINDING_EFFECT.get(i, '')[:1].upper() + FINDING_EFFECT.get(i, '')[1:]} Owner: BL-073. Not fixed here.")
    return L + [""]


def _gt(x: float) -> str:
    return f"{x:,.1f} g ({x / OZ:.1f} oz)"


def coupons_md(cp: dict, spl: dict) -> str:
    pl = pass_lines()
    rl = rig_loads()
    st = guide_steps()
    reg = {r["id"]: r for r in register_rows()}
    L = ["# COUPONS_H1P: the first PPA-CF print, the gate, and the four coupon tests", "",
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, manufacturing-engineer, {DATE}). **Do not edit "
         "by hand: re-run the script.** Pass lines are read from `designs/pack_5200/iter1/frame/bl070_h1p.json` "
         "(BL-070). Metric first, imperial in brackets.", "",
         "This is the PPA-CF path (frame H1-P). The PAHT-CF H1 path (`designs/pack_5200/print/frame_h1/BUILD_H1.md`) "
         "is still the fallback and is unchanged.", "",
         f"> **{HOLD}.** The H1-P frame halves and the frame build are held by review 8 "
         f"(`{REVIEW8.relative_to(ROOT)}`). **Coupon prints are allowed as the first step.** The pass lines below are "
         "BL-070's, read from `bl070_h1p.json` when this file is generated; BL-073 is re-specifying them (section 9), so "
         "re-read this file before you run a test.", "",
         "## 1. The gate (read this first)", "",
         f"> **Do not print either H1-P frame half until CA-3-PPA and CA-1-PPA have both passed** and the engineer has "
         "written PASS against them in the results sheet. The coupons are the first thing you print in PPA-CF.", "",
         f"1. CA-3-PPA (a) and (b) pass: conditioned Z >= **{pl['ca3_z_mpa']:g} MPa** and conditioned short-beam shear >= "
         f"**{pl['ca3_sbs_mpa']:g} MPa** (both as mean - {pl['ca3_k_sd']:g} SD).",
         f"2. CA-1-PPA passes: all {int(pl['ca1_n_z'] + pl['ca1_n_xy'])} bars reach {pl['ca1_cycles']:,.0f} cycles at "
         f"{pl['ca1_smax_ratio']:g} x their conditioned strength.",
         "3. Review 8 (BL-072) blockers B-1 and B-2 are closed by BL-073 and the HOLD above is lifted (review 8: do not "
         "release H1-P for printing until then).",
         f"4. If CA-3-PPA reads between {pl['ca3_z_mpa']:g} and {pl['ca3_hold_frac'] * pl['ca3_z_mpa']:.1f} MPa: HOLD "
         "(the engineer adds material at the hot spot). Below that: build the PAHT-CF H1 instead.", "",
         "CA-4-PPA (stiffness hot and wet) and T4c-PPA (cold drop) do not hold the print. They must pass before the "
         "first loaded carry (CA-4-PPA) and before any use below freezing (T4c-PPA).", "",
         f"Calendar: print about 2 days; dry CA-3 tests within 24 h; {int(pl['cond_days'])} days in the box; CA-3 "
         f"conditioned (1 day); CA-1 {int(pl['ca1_n_z'] + pl['ca1_n_xy'])} bars x about 28 h at 1 Hz on the one lever rig "
         "(about 2 weeks). About **5 weeks** from the first print to the frame print.", "",
         "## 2. Coupon print plan (spool 1, about one spool)", "",
         "Dry spool 1 first (PRINT_SHEET_H2S.md: 120 C, 10 h). Print with the frame settings of PRINT_SHEET_H2S.md "
         "(same nozzle, temperatures, layer height, 6 walls, 100 % infill, 30 min chamber pre-heat), on the same "
         "printer, from the same spool lot as the frame. No supports on job A or B.", "",
         "| job | coupon | for | how it lies on the plate | count | g each | filament + 8 % | about h |",
         "|---|---|---|---|---:|---:|---:|---:|"]
    for r in cp["rows"]:
        L.append(f"| {r['job']} | {r['coupon']} | {r['for']} | {r['orientation']} | {r['count']} | {r['g_each']:.1f} | "
                 f"{r['filament_g']:.0f} g | {r['print_h']:.1f} |")
    L += [f"| | **gate coupons (jobs A + B)** | | | | | **{cp['gate_filament_g']:.0f} g ({cp['gate_filament_g'] / OZ:.1f} oz), "
          f"{cp['gate_spools']:.2f} spool** | **{cp['gate_print_h']:.0f}** |", "",
          f"- Spool 1 holds {cp['spool_g']:.0f} g. After the gate coupons about {cp['spool_b_left_after_gate_g']:.0f} g is "
          f"left: keep it sealed and dried. It is the run-out reserve for both frame halves ({cp['swap_g']:.0f} g needed; "
          f"{'fits' if cp['swap_fits_spool_b'] else 'DOES NOT FIT'}; ASSUMPTION SPOOL-PLAN).",
          f"- Job C, the {int(pl['t4c_n_ppa'])} T4c-PPA stays, needs {cp['t4c_filament_g']:.0f} g "
          f"({cp['t4c']['g_each']:.0f} g each + supports): **a 4th spool** plus {spl['t4c_from_spool1_g']:.0f} g of spool 1's "
          f"last {spl['spool1_left_g']:.0f} g, so print job C AFTER both frame halves (T4c-PPA does not hold the frame "
          "print), or buy a 5th spool to print it earlier. BL-070's '3 spools, about $450' covers the frame and the gate "
          "coupons only.",
          "",
          "| spool | feeds | g |", "|---|---|---:|"] + [f"| {r['spool']} | {r['use']} | {r['g']:.0f} |" for r in spl["rows"]] + [
          "",
          "- Job A (flat): XY tensile bars, short-beam blocks and bend bars together on one plate; space them 5 mm apart. "
          "The short-beam blocks are small: put them in the middle of the plate.",
          "- Job B (standing): every Z bar stands on one 20 x 4 mm grip end, in rows of three tied by 2 mm ribs on the "
          "grip ends (ASSUMPTION Z-TIE). Turn the 'brim' to 5 mm for this job. Snip and sand the ribs off the grips "
          "only (never the gauge) before testing.",
          "- Job C: print `test_pieces/t4c_stay_R.stl` as written (wearer face down), tree supports and the 15 mm brim of "
          "the frame (PRINT_SHEET_H2S.md).", "",
          "After printing: label every part with a paint pen as each sheet below says; put the dry sets in a zip bag "
          f"with desiccant; put the conditioned sets in the conditioning box for {int(pl['cond_days'])} days.", "",
          "## 3. Rig loads (so nothing is overloaded)", "",
          "| coupon | peak at the coupon | at the lever cell (/ 4) | limit |", "|---|---:|---:|---|",
          f"| Z tensile, dry (TDS 57 MPa) | {_n(rl['z_dry_n'])} | {rl['z_dry_n'] / LEVER_RATIO / G:.0f} kg | 100 kg cell |",
          f"| XY tensile, conditioned (122 MPa booked) | {_n(rl['xy_cond_n'])} | **{rl['xy_cond_link_kg']:.0f} kg** | over the 100 kg cell: 200 kg cell |",
          f"| XY tensile, dry (168 MPa) | {_n(rl['xy_dry_n'])} | **{rl['xy_dry_link_kg']:.0f} kg** | 200 kg cell |",
          f"| lever bending for the XY statics | {rl['lever_sigma_mpa']:.0f} MPa in one 40 x 10 bar, {rl['lever_sigma_doubled_mpa']:.0f} MPa with two | | 6061-T6 yield {rl['al_yield_mpa']:.0f} MPa: use two bars (ASSUMPTION LEVER-XY) |",
          f"| XY fatigue peak | {_n(rl['xy_fat_n'])} | {rl['xy_fat_n'] / LEVER_RATIO / G:.0f} kg | fine |",
          f"| Z fatigue peak | {_n(rl['z_fat_n'])} | {rl['z_fat_n'] / LEVER_RATIO / G:.0f} kg | fine |",
          f"| short-beam block, dry (sizing) | {_n(rl['sbs_dry_n'])} | crane scale | {CRANE_STOP_KG:.0f} kg stop |",
          f"| bend bar, dry 23 C | {_n(rl['flex_break_dry_n'])} | crane scale | fine |", ""]
    titles = {"CA-3-PPA": "4", "CA-1-PPA": "5", "CA-4-PPA": "6", "T4c-PPA": "7"}
    for t, sec in titles.items():
        r = reg[t]
        L += [f"## {sec}. {t}: {r['title']}", "", f"**Why:** {r['what_it_proves']}. **Holds:** {r['gates']}.  ",
              f"**You need:** {r['specimen']}.", "", "**Steps**", ""]
        L += [f"{i}. {s}" for i, s in enumerate(st[t], 1)]
        L += ["", f"**Pass:** {r['pass_fail']}.", ""]
        if r["notes"]:
            L += [f"Note: {r['notes']}.", ""]
    hb = reg["HB-6-PPA"]
    L += ["## 8. HB-6-PPA: not needed", "", f"{hb['title']}. **Status: {hb['status']}.** {hb['notes']}. "
          "If the engineer ever goes back to heat-set inserts in PPA-CF, this test comes back as a gate.", "",
          ]
    L += review8_md(("B-2", "M-3", "M-4", "M-6", "M-7", "M-8"),
                    "## 9. Review 8 findings on the coupons (BL-073 owns the new pass lines; nothing here is fixed by BL-071)")
    L += ["What this means for you now: job A's XY tensile and bend bars are the least likely to change. Job B's "
          "standing Z bars and the short-beam blocks are the most likely to change (M-4, M-6), and the stays of job C "
          "may grow to 5 (M-7). If you print before BL-073 reports, expect to reprint those.", "",
          "## ASSUMPTIONS used on these sheets", ""]
    L += [f"- **{k}**: {v[0]} Settled by: {v[1]}." for k, v in ASSUMPTIONS.items()
          if k in ("Z-TIE", "SPARE", "COND-BOX", "LEVER-XY", "BOX-60", "FREEZER", "SPOOL-PLAN")]
    L.append("")
    return "\n".join(L)


def print_sheet_md(ps: dict) -> str:
    L = ["# PRINT_SHEET_H2S: printing the H1-P halves in PPA-CF on the Bambu H2S", "",
         f"> **{HOLD}. Do not print an H1-P half from this sheet.** Review 8 holds the frame (B-1, B-2) and finds the "
         "plate contact and spool-swap rows below cannot be used as written (M-5, M-6, section 4). The settings in "
         "section 1 also apply to the coupons, which may be printed now.", "",
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, {DATE}). Every value has its source in the last "
         "column. Do not print a half until the gate in `COUPONS_H1P.md` section 1 is passed.", "",
         "## 1. Settings (both halves, the clevises and every PPA-CF coupon)", "",
         "| setting | value | source |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in ps["rows"]]
    L += ["", "## 2. The two halves", "",
          "| half | file | part | filament (high, + 8 %) | spools | swap after about | print time | plate contact | fits 340 x 320 with brim |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for h in ps["halves"]:
        L.append(f"| {h['half']} | `{h['file']}` | {_gt(h['part_g'])} | {_gt(h['filament_g'])} | {h['spools']:.2f} | "
                 f"{h['swap_after_h']:.1f} h | **{h['print_h']:.1f} h** | {h['contact_mm2']:.0f} mm2 | {'yes' if h['fits'] else 'NO'} |")
    L += ["", "Source: `bl070_h1p.json` h1p.print (filament, spools, time: BL-053 rule at the PAHT volume rate, "
          "ASSUMPTION PPA-TIME; the slicer preview settles it). Swap time = print time x 750 g / filament (ASSUMPTION RUNOUT).", "",
          "## 3. Step by step, each half", "",
          "1. Dry the spool you start on (a FULL spool: spool 2 for the lower half, spool 3 for the upper) at 120 C for "
          "10 h. Dry spool 1's left-over at the same time: it is the swap spool.",
          "2. Clean the textured PEI plate with soap and water, dry it, rub a thin even coat of glue stick over the whole "
          "footprint and the brim area.",
          "3. Slicer: load the half's STL. Do NOT rotate it. Set the settings of section 1. Add the 15 mm brim. Add the "
          "mouse ears: 20 mm discs, 1 layer thick, under both stay feet (lower half) or both upper stay ends (upper half). "
          "Supports: tree, from the build plate, as BUILD_H1 section 3. Slice.",
          "4. CHECK the preview: nothing red or outside the plate (brim and supports included); filament and time within "
          "10 % of section 2; no support inside a bore, pin hole, bolt hole or nut trap; the 8 hip nut traps open UPWARD "
          "(on the lower half, on the top face). Screenshot and send it before the first half.",
          "5. Plate in, door shut, chamber heater on to 65 C, bed to 110 C. **Wait 30 min** after the chamber reads 65 C.",
          "6. Feed from the dried spool through the dry box. Start the print. Watch the first layer and the brim go "
          "down: every brim line stuck, no corner lifting.",
          "7. Be at the printer at the swap time of section 2. When the printer pauses for run-out: take the empty spool "
          "off, put the dried swap spool on, feed it until clean filament comes out, resume. If it does not pause, the "
          "half is lost: stop and send a photo (ASSUMPTION RUNOUT).",
          "8. When it finishes, leave it on the plate with the door shut until the chamber is below 40 C (warm PPA-CF "
          "bends and the plate can pull a corner). Then flex the plate off.",
          "9. Supports off and clean-up exactly as BUILD_H1 section 4. **No anneal** (section 1).",
          "10. CHECK: a corner or a stay foot lifted from the plate by more than 0.5 mm (feeler gauge under the brim "
          "edge before removal)? Write it down with a photo: the plate contact of the upper half is only 163 mm2 and "
          "warp is the main print risk (BL-070).", "",
          ]
    L += review8_md(("B-1", "B-2", "M-5", "M-6"), "## 4. Review 8 findings on this sheet (BL-073 owns the fixes)")
    L += ["## ASSUMPTIONS", "",
          "- PPA-TIME, WARP, SPOOL-SWAP: `bl070_h1p.json` assumptions (settled by the slicer preview and the first article).",
          f"- RUNOUT: {ASSUMPTIONS['RUNOUT'][0]} Settled by: {ASSUMPTIONS['RUNOUT'][1]}.",
          f"- FAN: {ASSUMPTIONS['FAN'][0]} Settled by: {ASSUMPTIONS['FAN'][1]}.", ""]
    return "\n".join(L)


def build_md(cp: dict, spl: dict, ps: dict) -> str:
    d = h1p_json()
    hm = hip()
    b = bom()
    cs = cost()
    ex = d["h1p"]["export"]
    rho_r = rho() * 1e6 / 1060.0                     # clevis mass in PPA from the PAHT-density g of the export
    pr = d["h1p"]["print"]
    body = d["h1p"]["body_g"]
    lo_b, hi_b = body * 0.97, body * 1.04
    pat = d["h1_ppa"]["hip_inserts"]["pattern"]
    L = ["# BUILD_H1P: building the H1-P frame in PPA-CF (Pack 5200)", "",
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, manufacturing-engineer, {DATE}). **Do not "
         "edit by hand: re-run the script.** Data: `designs/pack_5200/iter1/frame/bl070_h1p.json` (BL-070) and the "
         "material records. Metric first, imperial in brackets.", "",
         "H1-P is the H1 frame re-tuned for Bambu PPA-CF (BL-070): same bag, crown, pins, clevises and hip mount "
         f"position as H1, {body:.1f} g ({body / LB_G:.2f} lb) printed body, +{d['h1p']['delta_vs_paht_h1_g']:.1f} g "
         f"(+{d['h1p']['delta_vs_paht_h1_g'] / OZ:.1f} oz) on the PAHT-CF H1. **The PAHT-CF H1 (`../frame_h1/BUILD_H1.md`) "
         "stays the fallback.** Status: candidate, gated on the PPA coupons (DECISIONS 2026-11-25).", "",
         f"> **{HOLD}.** Review 8 (`{REVIEW8.relative_to(ROOT)}`) holds the H1-P frame from printing and building. "
         "Only the coupons (`COUPONS_H1P.md`) may be printed now. Sections 3-6 below are for when BL-073 lifts the hold.", "",
         "## 0. Read in this order", "",
         "1. `COUPONS_H1P.md`: print the coupons FIRST, then wait for CA-3-PPA and CA-1-PPA to pass (the gate).",
         "2. This file, section 1 (shopping) and section 2 (what is different from BUILD_H1).",
         "3. `PRINT_SHEET_H2S.md`: printing the two halves.",
         "4. This file, sections 3-6 (weigh, joints, hip mount, checks).", "",
         "## 1. Bill of materials and cost (the PPA path only; everything else is BUILD_H1 section 1)", "",
         "| section | item | qty | unit | USD each | USD | price source | note |", "|---|---|---:|---|---:|---:|---|---|"]
    for x in b:
        L.append(f"| {x.section} | {x.item} | {x.qty:g} | {x.unit} | {x.unit_cost_usd:.2f} | {x.cost_usd:.2f} | "
                 f"{x.source[:160]} | {x.notes} |")
    L += ["",
          f"- **Filament for the frame: 3 spools, USD {cs['filament_frame_usd']:.2f}** (two halves + the gate coupons + "
          f"the run-out swaps). **T4c-PPA stays: a 4th spool, USD {cs['filament_t4c_usd']:.2f}.**",
          f"- Hip mount hardware: USD {cs['hip_hw_usd']:.2f}. Per frame after the first (filament + hip hardware): about "
          f"USD {cs['per_frame_usd']:.0f}.",
          f"- One-time tools: dryer USD {cs['dryer_usd']:.2f}; all new tools USD {cs['tools_usd']:.2f}.",
          f"- First PPA frame, everything on this list: **USD {cs['first_frame_all_usd']:.2f}**.",
          "- Not on this list (same as the PAHT path, BUILD_H1 section 1): z 234 joint and US2 clevis screws, nuts and "
          "washers, pins, sleeves, retainers, pawl, crown, the SLM Ti hip mount (HW-HIP-MNT).",
          "- **Removed on the PPA path:** HW-HIP-INS (8 brass heat-set inserts), HW-HIP-SCR (8 x M5 x 12), "
          "HW-HIP-GUIDE (the insert-setting guide) and the soldering-iron insert tips.", "",
          "## 2. What is different from BUILD_H1", "",
          "| BUILD_H1 section | on the PPA path |", "|---|---|",
          "| 2. gates | replaced: `COUPONS_H1P.md` section 1 (CA-3-PPA + CA-1-PPA, BL-072). CA-1 / CA-5 / HB-6 in PAHT-CF do not gate a PPA frame |",
          "| 3. print settings | replaced: `PRINT_SHEET_H2S.md` (files in `designs/pack_5200/iter1/frame/h1p/`) |",
          "| 4. supports off, clean-up | same, but wait until the chamber is below 40 C before lifting the plate |",
          "| 5. anneal | **deleted: do not anneal PPA-CF** |",
          "| 6. weigh | replaced: section 3 below |",
          "| 7-11. z 234 joint, crown bores, pins, clevises, pawl | same steps, same hardware, H1-P halves |",
          "| 12. hip mount (inserts) | **replaced: section 5 below (through-bolts). The insert-setting steps are deleted on this path** |",
          "| 13 onward. crown, first-article checks | same; add section 6 below |", "",
          "## 3. Weigh (after support removal, before reaming) [HOLD]", "",
          "| part | expected (STL x 1.25 g/cm3) |", "|---|---:|",
          f"| lower half | {_gt(ex['lower']['g_ppa'])} |", f"| upper half | {_gt(ex['upper']['g_ppa'])} |",
          f"| US2 clevis, each | {_gt(ex['us2_clevis_R']['g'] * rho_r)} |",
          f"| body (halves + 2 clevises) | **{_gt(body)}** |", "",
          f"CHECK: the body reads **{lo_b:.0f} to {hi_b:.0f} g** ({lo_b / OZ:.1f}-{hi_b / OZ:.1f} oz), the BUILD_H1 MASS-BAND "
          "(-3 / +4 %) on the PPA mass. Lighter: wet filament or gaps; heavier: over-extrusion.", "",
          "## 4. Joints [HOLD]", "",
          "Bolt the halves (z 234 joint), ream the crown bores, fit the pins, clevises and pawl exactly as BUILD_H1 "
          "sections 7-11. Same screws, nuts, washers and torques.", "",
          "## 5. Hip mount: through-bolts (replaces BUILD_H1 section 12) [HOLD]", "",
          f"The Ti hip pivot mount (HW-HIP-MNT, unchanged, {hm['flange_t']:.1f} mm base, D{hm['mount_hole_d']:g} holes) sits "
          f"on the D{pat['boss_d']:.0f} boss face as on H1. On H1-P its {hm['n']} screws go **straight through** the boss "
          f"(D{hm['hole_d']:.1f} holes) into **A2 hex nuts** sitting in hex traps that open on the boss's back face; each "
          f"nut seat is {hm['seat']:.0f} mm behind the mount face. Hardware (bl070_h1p.json): {hm['hardware']}.", "",
          f"Stack: mount base {hm['flange_t']:.1f} + boss to the nut seat {hm['seat']:.0f} + nut {hm['nut_t']:.1f} = "
          f"{hm['grip'] + hm['nut_t']:.0f} mm = the screw length, so each screw tip ends flush with the nut's top.", "",
          f"**Torque: {hm['torque_txt']}.** Do not tighten the hip nuts for load until BL-073 sets the torque "
          "(ASSUMPTION TORQUE-TBD). Do not use the PAHT path's 2.5 N m: that is the brass insert's limit, not a value "
          "for a nut bearing on PPA-CF layers.", "",
          "| screw | towards the R stay from the boss centre (mm) | above the boss centre (mm) |", "|---:|---:|---:|"]
    cx = sum(p[0] for p in pat["positions_xz"]) / len(pat["positions_xz"])
    cz = sum(p[1] for p in pat["positions_xz"]) / len(pat["positions_xz"])
    L += [f"| {i} | {x - cx:+.1f} | {z - cz:+.1f} |" for i, (x, z) in enumerate(pat["positions_xz"], 1)]
    L += ["",
          f"1. CHECK the print: {hm['n']} through holes in the boss: a {hm['hole_d']:.1f} mm drill shank slides through each "
          "by hand, end to end (hold the half to a light). Clear stringing with the drill turned in your fingers.",
          f"2. CHECK the nuts: caliper each **HW-HIP-NUT-P** <= {hm['nut_t'] + 0.1:.1f} mm thick; a thicker nut is the wrong "
          "standard (ISO 4032), set it aside.",
          f"3. Dry-fit: drop a nut into each of the {hm['n']} hex traps from the back face: it falls to the seat and does not "
          "turn when you push a 3 mm hex key into it. Tight: file the trap walls lightly, never more than 0.2 mm.",
          "4. With the nuts in, put a strip of masking tape over the trap openings so they cannot fall out. Turn the "
          "frame wearer face up.",
          f"5. Lay the Ti mount on the boss face: every one of its {hm['n']} holes shows a through hole under it.",
          f"6. One drop of Loctite 243 on the last 5 mm of each **HW-HIP-SCR-P** ({hm['screw']}) thread. Keep it off the "
          "print (wipe any drip with IPA at once).",
          "7. Start every screw by hand through the mount into its nut; if one does not start, back it out, check the nut "
          "sits flat in its trap, try again. Never force it.",
          f"8. Tighten in a star order to the BL-073 torque (**{hm['torque_txt']}**) with the small torque screwdriver "
          "and the 3 mm hex bit. Go round twice. Until the torque is set: finger-snug only, for a dry fit.",
          f"9. CHECK from the back face: each screw tip is level with the nut's top face (0 to 0.8 mm below it is OK: the "
          f"nut still has 4 full threads). A tip more than 0.8 mm below: wrong screw length, stop.",
          f"10. CHECK seating (BUILD_H1 section 12 step 5): push the mount's pin end with the spring scale to "
          f"{MOUNT_SEAT_N:.0f} N ({MOUNT_SEAT_N / G:.1f} kg, {MOUNT_SEAT_N / N_PER_LBF:.1f} lb) up, down, left and right: a "
          "0.05 mm (0.002 in) feeler does not enter under the base edge.",
          "11. Paint mark across every screw head and the mount base, and across every nut and the boss back face. "
          "Remove the tape. Let the Loctite cure 24 h before any load.", "",
          "## 6. First-article checks added on the PPA path [HOLD]", "",
          "1. Before the first carry: CA-4-PPA passed. Before any use below 0 C (32 F): T4c-PPA passed.",
          "2. HB-6b (test kit G6) runs on this frame with the through-bolts: no paint mark moves.",
          "3. Every 10 outings: paint marks on the hip nuts unmoved; no white line under any nut (look from the back face).", "",
          "## ASSUMPTIONS on this path", ""]
    L += [f"- **{k}**: {v[0]} Settled by: {v[1]}." for k, v in ASSUMPTIONS.items() if k in ("TORQUE-TBD", "SPOOL-PLAN")]
    L += ["- The BL-070 assumptions (PPU=PPA, WET-PPA, FAT-PPA, INTERLAYER-0.6, NUT-BEAR, WARP, PPA-TIME, COLD, SPOOL-SWAP) "
          "are in `bl070_h1p.json` with what settles each.", "",
          "## FOUND (for the structural-fea-engineer: review 8 B-1, BL-073)", "",
          f"- NUT-BEAR booked the nut bearing on a D10 ring ({hm['a_model']:.1f} mm2). An {hm['nut_af']:.0f} AF hex trap "
          f"cannot hold a D10 washer, so the seat sees only the nut's own bearing ring (dw {NUT_DW_MIN} mm: "
          f"{hm['a_dw']:.1f} mm2). On the same rule that reads strength {hm['sf_strength_dw']:.2f} (goal 1.5), fatigue "
          f"**{hm['sf_fatigue_dw']:.2f} (goal 1.15)**, creep {hm['sf_creep_dw']:.2f} (goal 1.5). The rule takes Z "
          "TENSILE strength for compression across the layers, which is conservative; HB-6b settles it. Review 8 B-1 found "
          "the same. Not changed here (BL-073 owns it).",
          f"- For BL-073 only, not a build value: capping the preload at the creep line / {CREEP_GOAL} on that dw ring, with "
          f"K {K_NUT} (ASSUMPTION K-NUT, as frame_h1.Joint), gives {hm['torque_info_creep_cap']:.2f} N m: barely snug.", ""]
    return "\n".join(L)


def readme_md(cp: dict) -> str:
    pl = pass_lines()
    cs = cost()
    return "\n".join([
        "# H1-P printed frame in PPA-CF: files (Pack 5200)", "",
        f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}). **Do not edit by hand.**", "",
        "The PPA-CF build path, alongside the PAHT-CF H1 path in `../frame_h1/` (still the fallback).", "",
        f"**{HOLD}.** Frame halves and build held by review 8; coupon prints allowed (COUPONS_H1P.md).", "",
        "| file | what |", "|---|---|",
        "| `COUPONS_H1P.md` | **start here**: the first print (coupons), the gate, and the CA-3-PPA, CA-1-PPA, CA-4-PPA, T4c-PPA sheets |",
        "| `PRINT_SHEET_H2S.md` | the H2S settings for both halves, each with its source |",
        "| `BUILD_H1P.md` | BOM and cost, the through-bolt hip mount, what differs from BUILD_H1 |",
        "| `test_pieces/t4c_stay_R.stl` | the T4c-PPA stay coupon (H1-P R stay z 0-240), turned wearer face down for printing |",
        "| `../../iter1/frame/h1p/*.stl` | the H1-P halves and clevises (BL-070), as written for the plate |", "",
        f"Gate: no H1-P half before CA-3-PPA (conditioned Z >= {pl['ca3_z_mpa']:g} MPa, SBS >= {pl['ca3_sbs_mpa']:g} MPa) "
        f"and CA-1-PPA ({pl['ca1_n_z'] + pl['ca1_n_xy']:.0f} run-outs at {pl['ca1_smax_ratio']:g} x UTS) pass.", "",
        f"Cost: frame filament 3 spools USD {cs['filament_frame_usd']:.2f}; T4c spool USD {cs['filament_t4c_usd']:.2f}; "
        f"dryer USD {cs['dryer_usd']:.2f} (one-time).", "",
        "Release copies, the BOM CSV, the coupon plan CSV and a tech pack PDF: `outputs/release/frame_h1p_ppa/`.", ""])


# ============================================================================ tech pack, files, previews
def _blocks(md: str) -> list:
    from huntkit.manufacturing import techpack as T
    out, tab = [], []

    def flush():
        if tab:
            rows = [[re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", c).replace("**", "").replace("`", "").strip()
                     for c in r.strip().strip("|").split("|")] for r in tab if not re.match(r"^\|[-:| ]+\|$", r.strip())]
            n = max(len(r) for r in rows)
            rows = [r + [""] * (n - len(r)) for r in rows]
            out.append(T.table(rows, [250 / n] * n))
            tab.clear()

    for line in md.splitlines()[1:]:
        if line.startswith("|"):
            tab.append(line)
            continue
        flush()
        if line.startswith("#"):
            out.append(T.h2(line.lstrip("# ")))
        elif line.strip():
            out.append(T.para(re.sub(r"[*`]", "", re.sub(r"^>\s*", "", line))))
    flush()
    return out


def techpack(docs: dict, path: Path, images: list[Path]) -> Path:
    from huntkit.manufacturing import techpack as T
    from huntkit.manufacturing.records import bom_rows
    b = bom()
    pl = pass_lines()
    hm = hip()
    cs = cost()
    sec = [
        T.Section("Flats and piece map: H1-P halves (BL-070 STLs)", [T.para(
            "Printed body: lower half, upper half, two US2 clevises (designs/pack_5200/iter1/frame/h1p/). No sewn parts on "
            "this package: the bag is the CORRIE F rev 3 tech pack.")] + [T.image(p, 250, 150) for p in images[:1]]),
        T.Section("Bill of materials (PPA path)", [T.bom_table(b), T.para(
            f"Frame filament USD {cs['filament_frame_usd']:.2f} (3 spools); T4c spool USD {cs['filament_t4c_usd']:.2f}; hip "
            f"hardware USD {cs['hip_hw_usd']:.2f}; one-time tools USD {cs['tools_usd']:.2f}.")]),
        T.Section("Cutting / print plan: coupons first", _blocks(docs["COUPONS_H1P.md"])),
        T.Section("Operation sequence: H2S print sheet", _blocks(docs["PRINT_SHEET_H2S.md"])),
        T.Section("Operation sequence: build and hip mount", _blocks(docs["BUILD_H1P.md"])),
        T.Section("QC points", [T.table([["check", "pass"],
                                         ["CA-3-PPA conditioned Z (mean - 2.4 SD)", f">= {pl['ca3_z_mpa']:g} MPa"],
                                         ["CA-3-PPA conditioned SBS", f">= {pl['ca3_sbs_mpa']:g} MPa"],
                                         ["CA-1-PPA all bars", f"{pl['ca1_cycles']:,.0f} cycles at {pl['ca1_smax_ratio']:g} x UTS"],
                                         ["body mass", "-3 / +4 % of 1268.1 g"],
                                         ["hip screw tip", "0 to 0.8 mm below the nut top"],
                                         ["hip torque", f"{hm['torque_txt']}; paint marks"]], [150, 100])]),
        T.Section("Packaging", [T.para("Each printed half bagged with a desiccant pack in a 4 mil poly bag, labelled with the "
                                       "half, the spool lot and the print date; hip hardware in its own labelled bag (HW-HIP-SCR-P, "
                                       "HW-HIP-NUT-P). Ship flat in a carton with 25 mm foam each side.")]),
    ]
    tp = T.TechPack(title="Pack 5200 frame H1-P (PPA-CF)", subtitle="BL-071: coupons, H2S print sheet, through-bolt hip mount, BOM",
                    date=DATE, footer="Hunting-appeal BL-071 H1-P build path",
                    cover=[["generated by", "designs/pack_5200/frame_h1p_build.py"],
                           ["data", "designs/pack_5200/iter1/frame/bl070_h1p.json; data/materials/polymers/ppa_cf_fdm.yaml"],
                           ["status", f"{HOLD}: frame print and build held; coupon prints allowed. PAHT-CF H1 is the fallback"]],
                    sections=sec)
    return T.tech_pack(tp, path, strict=False)


def doc_pdf(title: str, md: str, path: Path) -> Path:
    from huntkit.manufacturing import techpack as T
    tp = T.TechPack(title=title, subtitle=f"{TICKET}", date=DATE, footer=f"Hunting-appeal {TICKET}",
                    cover=[["generated by", "designs/pack_5200/frame_h1p_build.py"]],
                    sections=[T.Section(md.splitlines()[0].lstrip("# "), _blocks(md))])
    return T.tech_pack(tp, path, strict=False)


def stay_figure(path: Path, t=None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    full = trimesh.load(H1P_STL / "h1_assembled.stl")
    t = t if t is not None else t4c_stay_mesh()
    fig, ax = plt.subplots(1, 2, figsize=(9, 5), dpi=110)
    for a, (i, j, lab) in zip(ax, ((0, 2, "front view (x, z)"), (1, 2, "side view (y, z)"))):
        v = full.vertices
        a.scatter(v[::7, i], v[::7, j], s=0.2, c="0.8")
        w = t.vertices
        a.scatter(w[:, i], w[:, j], s=0.3, c="tab:red")
        a.set_aspect("equal")
        a.set_title(lab)
        a.set_xlabel("mm")
    fig.suptitle("T4c-PPA stay coupon (red): H1-P R stay z 0-240, cut at x = +95 mm")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def checks(pk: dict) -> list[str]:
    pl, rc = pass_lines(), pass_lines_recomputed()
    msgs = []
    for k, v in rc.items():
        ok = abs(pl[k] - v) <= 0.005 * abs(v)          # the JSON text rounds to 3 figures
        msgs.append(f"{k}: JSON text {pl[k]:g} vs recomputed {v:.4f} {'OK' if ok else 'MISMATCH'}")
    cp = pk["coupons"]
    msgs.append(f"gate coupons {cp['gate_filament_g']:.0f} g = {cp['gate_spools']:.2f} spool; swap reserve fits: {cp['swap_fits_spool_b']}")
    msgs.append(f"T4c stays {cp['t4c_filament_g']:.0f} g (4th spool)")
    h = pk["hip"]
    msgs.append(f"hip torque: {h['torque_txt']}; screw tip vs nut top {h['tip_vs_nut_top_mm']:+.1f} mm")
    msgs.append(f"review 8 rows read: {sorted(review8_rows())}")
    msgs.append(f"cost {pk['cost']}")
    return msgs


def package() -> dict:
    cp = coupon_plan()
    spl = spool_plan(cp)
    ps = print_sheet()
    docs = {"COUPONS_H1P.md": coupons_md(cp, spl), "PRINT_SHEET_H2S.md": print_sheet_md(ps),
            "BUILD_H1P.md": build_md(cp, spl, ps), "README.md": readme_md(cp)}
    pk = {"coupons": cp, "spools": spl, "print_sheet": ps, "docs": docs, "hip": hip(), "cost": cost(),
          "register": register_rows(), "results": results_items()}
    pk["checks"] = checks(pk)
    return pk


def _w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _raster(pdf: Path, page: int, dst: Path, r: int = 110) -> Path:
    tmp = dst.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", str(r), "-f", str(page), "-l", str(page), "-singlefile", str(pdf), str(tmp)],
                   check=True, capture_output=True)
    from PIL import Image
    im = Image.open(dst).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, int(im.height * 1600 / im.width)))
    im.save(dst, optimize=True)
    assert dst.stat().st_size <= 1.5e6, dst
    return dst


def write(pk: dict) -> dict:
    PRINT.mkdir(parents=True, exist_ok=True)
    REL.mkdir(parents=True, exist_ok=True)
    for name, txt in pk["docs"].items():
        _w(PRINT / name, txt)
        _w(REL / name, txt)
    t = t4c_stay_mesh()
    TP_DIR.mkdir(parents=True, exist_ok=True)
    t4c_print_mesh(t).export(TP_DIR / "t4c_stay_R.stl")
    t.export(TP_DIR / "t4c_stay_R_frame_coords.stl")
    from huntkit.manufacturing.records import bom_rows
    rows = bom_rows(bom())
    with open(REL / "bom_h1p_ppa.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    cp = pk["coupons"]
    with open(REL / "coupon_plan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cp["rows"][0]))
        w.writeheader()
        w.writerows(cp["rows"] + [cp["t4c"]])
    fig = stay_figure(REL / "t4c_stay_R.png", t)
    tp = techpack(pk["docs"], REL / "h1p_ppa_techpack.pdf", [fig])
    cpdf = doc_pdf("H1-P coupons and gate", pk["docs"]["COUPONS_H1P.md"], REL / "COUPONS_H1P.pdf")
    ppdf = doc_pdf("H1-P H2S print sheet", pk["docs"]["PRINT_SHEET_H2S.md"], REL / "PRINT_SHEET_H2S.pdf")
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [_raster(cpdf, 2, SCREENS / f"{SHOT}_1.png"), _raster(cpdf, 3, SCREENS / f"{SHOT}_2.png"),
             _raster(ppdf, 2, SCREENS / f"{SHOT}_3.png"), _raster(ppdf, 3, SCREENS / f"{SHOT}_4.png")]
    man = {"ticket": TICKET, "date": DATE, "checks": pk["checks"], "cost": pk["cost"],
           "files": sorted(str(p.relative_to(REL)) for p in REL.rglob("*") if p.is_file()),
           "screens": [str(p.relative_to(ROOT)) for p in shots]}
    _w(REL / "manifest.json", json.dumps(man, indent=1))
    return {"techpack": tp, "screens": shots}


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
