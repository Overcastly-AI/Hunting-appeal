"""BL-071 / BL-074: the PPA-CF H1-P build path (manufacturing-engineer, 2026-11-25).

    python designs/pack_5200/frame_h1p_build.py            # write print/frame_h1p/ and outputs/release/frame_h1p_ppa/
    python designs/pack_5200/frame_h1p_build.py --check    # build in memory, print the checks, write nothing

H1-P is the H1 frame re-tuned for Bambu PPA-CF (BL-070) and re-tuned again on the hot/wet B-basis by BL-073 (p3,
``iter1/frame/bl070_h1p.json`` keys ``coupons_bl073``, ``bl071_requests``, ``assumptions_bl073``, ``bl073``,
``h1p.hip_mount``, ``h1p.z234_joint_xy``). It is built ALONGSIDE the PAHT-CF H1 path (``frame_h1_build.py``), which
stays the fallback. BL-074 rebuilds this path from the BL-073 keys:

* ``print/frame_h1p/COUPONS_H1P.md``: the first-article upper half, the BL-073 coupon jobs (every one beside a dummy
  tower so each layer takes the frame's layer time), the frame-print HOLD gate, and one beginner sheet per test;
* ``print/frame_h1p/PRINT_SHEET_H2S.md``: the H2S settings, the ``*_flat_print.stl`` files with their snap-off pads,
  and one planned filament change per half (Bambu Studio "Add Pause" at a layer);
* ``print/frame_h1p/BUILD_H1P.md``: BOM / cost, the trap-free hip mount (6061 bearing ring, printed nut keeper,
  Ti M5 x 35, 0.6 N m), the z 234 bolt positions, and what carries over from BUILD_H1;
* ``print/frame_h1p/test_pieces/``: the coupon pieces cut from the H1-P frame, the blocks and the dummy towers;
* ``outputs/release/frame_h1p_ppa/``: copies, ``bom_h1p_ppa.csv``, ``coupon_plan.csv``, ``spool_plan.csv`` and a tech
  pack PDF (``huntkit.manufacturing.techpack``, CONTRACTS section 5).

Register rows, sheets and results rows are built here (``register_rows``, ``guide_steps``, ``results_items``) and
written by ``physical_test_kit.py`` (group G8, release R1-PPA). The BL-070 rows stay in the register as SUPERSEDED.

Every pass line is read from ``bl070_h1p.json`` at generation time (``pass_lines``); every print value from the
PPA-CF record or the BL-070 / BL-073 record; numbers with no source are marked ASSUMPTION with what settles them.
Units mm, g, N, MPa, N m internally; inches, oz, lb, in lbf shown next to them.
"""
from __future__ import annotations

import argparse
import csv
import functools
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

DATE = "2026-11-25"
TICKET = "BL-074"
BL070 = HERE / "iter1" / "frame" / "bl070_h1p.json"
BL070_MD = HERE / "iter1" / "frame" / "bl070_h1p.md"
H1P_STL = HERE / "iter1" / "frame" / "h1p"
MAT = ROOT / "data" / "materials"
AN = HERE / "analysis"
PRINT = HERE / "print" / "frame_h1p"
TP_DIR = PRINT / "test_pieces"
REL = ROOT / "outputs" / "release" / "frame_h1p_ppa"
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261125_bl074"
BUILD_H1 = "designs/pack_5200/print/frame_h1/BUILD_H1.md"
DECISIONS = ROOT / "docs" / "DECISIONS.md"

IN = 25.4
OZ = 28.3495
LB_G = 453.592
N_PER_LBF = 4.44822
NM_PER_INLBF = 0.112985
G = 9.81
M5_PITCH = 0.8          # ISO 261 M5 coarse pitch, mm
THREADS_PROUD_MIN = 2   # the rule: >= 2 full threads past the nut (VDI 2230 practice; review 8 B-1 asked for proud)

# --- coupon blocks (BL-074 layout; the bar sizes are read from the JSON text)
KERF = 2.0              # ASSUMPTION CUT: saw kerf + sanding allowance between bars, mm
TRIM = 5.0              # ASSUMPTION CUT: edge strip trimmed off every block side (the outer walls are not tested)
FACE = 0.3              # one layer faced off the top and the bottom of the SBS block (mid-plane stays on a layer line)
Z_SLAB_T = 3.0          # Z slab printed 3 mm thick, sanded to the 2 mm 1BA gauge thickness
Z_END_W = 10.0          # ISO 527-2 type 1BA end width (gauge 5, overall 75, thickness 2)
Z_TRIM_END = 2.5        # slab height = 75 + 2 x 2.5 mm
SPARES = 1              # ASSUMPTION SPARE: one spare per coupon set
WASTE = 0.08            # the BL-053 / BL-070 filament rule (+8 % purge, brim, skirt)
TOWER_MIN_MM2 = 225.0   # ASSUMPTION TOWER: every plate carries a tower of at least 15 x 15 mm (also a prime tower)
TOWER_BAND_MM = 3.0     # the tower steps every 3 mm of height (10 layers)
FLEX = dict(L=80.0, w=10.0, t=4.0, span=64.0)      # ISO 178: 80 x 10 x 4, span 16 h (CA-4-HW names 80 x 10 x 4)
CROWN_CUT = dict(x_min=-15.0, z_min=480.0)          # ASSUMPTION CROWN-CUT: pawl housing (x 0) to the R crown corner
US2_CUT = dict(x_min=46.0, z_min=40.0, z_max=160.0)  # the PAHT us_route_stay_R box (frame_h1 test_pieces), on H1-P

# --- rig
LEVER_RATIO = 4.0       # kit B lever: drive 480 mm / coupon 120 mm (CA1_fatigue_rig.md)
CELL_KG = 100.0         # kit B S-type load cell
CRANE_STOP_KG = 280.0   # kit A crane scale stop (physical_test_kit G2 safety)
MOUNT_SEAT_N = 20.0     # BUILD_H1 section 12 step 5 (ASSUMPTION MOUNT-SEAT there)

FACE_DOWN = "y/y (as printed)"
PARKED = "PARKED (cost, 2026-11-25)"   # BL-078: owner cost cap (RUBRIC 1b, DECISIONS 2026-11-25); docs otherwise unchanged
PARKED_TXT = (f"**{PARKED}.** The owner parked the PPA-CF path on cost (docs/RUBRIC.md section 1b, docs/DECISIONS.md "
              "2026-11-25). Nothing in this file is to be bought or printed. The PAHT-CF H1 path is current: "
              "`designs/pack_5200/print/frame_h1/COUPONS_PAHT.md` is the next print.")
HOLD = "FRAME PRINT ON HOLD (BL-073 gate: coupons pass + US2 lug proof x lug factor + CLEVIS-SHARE B share)"
RELEASED = "RELEASED TO PRINT NOW: the first-article upper half (FA-H1P-UP) and the coupon jobs A-G"
REVIEW8 = AN / "review_20261125_eighth.md"
FREEZER_C = -20.0       # T4b / T4c cold soak (bl070_h1p.json coupons_bl073)

ACTIVE_IDS = ("FA-H1P-UP", "CA-3-HW", "CA-1-HW", "CA-4-HW", "T4c-PPA-HW", "T4c-PPA-CROWN", "CLEVIS-SHARE-B-PPA",
              "US2-LUG-PPA", "T4b-PPA-COLD", "T4c-PPA-COLD")
GATE_IDS = ("CA-3-HW", "CA-1-HW", "CA-4-HW", "T4c-PPA-HW", "T4c-PPA-CROWN", "US2-LUG-PPA", "CLEVIS-SHARE-B-PPA")
SUPERSEDED = {"CA-1-PPA": "CA-1-HW", "CA-3-PPA": "CA-3-HW", "CA-4-PPA": "CA-4-HW", "T4c-PPA": "T4c-PPA-HW"}


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
    basis = ppa()["properties"]["print_cost_basis"]
    m = re.search(r"([0-9.]+)\s*kg spool \$([0-9.]+)", basis)
    assert m, basis
    return {"g": float(m.group(1)) * 1000.0, "usd": float(m.group(2)), "basis": basis}


def rho() -> float:
    return ppa()["properties"]["density_kg_m3"] / 1e6       # g/mm3


def rho_paht() -> float:
    return record("pa12_cf_fdm_paht")["properties"]["density_kg_m3"] / 1e6


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
    """The BL-073 coupon rows (``coupons_bl073``): the active set."""
    return {c["id"]: c for c in h1p_json()["coupons_bl073"]}


def coupons_bl070() -> dict:
    """The BL-070 coupon rows (``coupons``): kept in the register as SUPERSEDED."""
    return {c["id"]: c for c in h1p_json()["coupons"]}


def b73() -> dict:
    return h1p_json()["bl073"]


def req() -> dict:
    return h1p_json()["bl071_requests"]


def assumption_73(aid: str) -> dict:
    return {a["id"]: a for a in h1p_json()["assumptions_bl073"]}[aid]


def _num(pat: str, txt: str, grp: int = 1) -> float:
    m = re.search(pat, txt)
    assert m, (pat, txt)
    return float(m.group(grp))


def booked_spools() -> int:
    """The spool count BL-073 booked ('book N spools' in its md section; the JSON has no numeric field for it)."""
    return int(_num(r"book (\d+) spools", BL070_MD.read_text(encoding="utf-8")))


@functools.lru_cache(maxsize=None)
def pass_lines() -> dict:
    """Every pass line and count of the BL-073 coupons, read from the bl070_h1p.json text (never typed here)."""
    c = coupons()
    c1, c3, c4 = c["CA-1-HW"], c["CA-3-HW"], c["CA-4-HW"]
    tb, tcc, th, cr = c["T4b-PPA-COLD"], c["T4c-PPA-COLD"], c["T4c-PPA-HW"], c["T4c-PPA-CROWN"]
    d = h1p_json()
    rows = d["h1p"]["rows_by_name"]
    lug = rows["US2 lug fatigue"]
    clev = rows["US2 clevis joint fatigue (share 1.0)"]
    lh = assumption_73("LAYER-H")["text"]
    pt = {a["id"]: a for a in d["assumptions"]}["PPA-TIME"]["text"]
    k_lug = lug["goal"] / lug["value"]
    share = 1.0 * clev["value"] / clev["goal"]        # clevis fatigue ~ 1 / share (0.91 at 1.0, 1.52 at 0.6)
    return {
        # CA-1-HW
        "ca1_sbs_l": _num(r"bars ([0-9.]+) x ([0-9.]+) x ([0-9.]+), span", c1["what"]),
        "ca1_sbs_w": _num(r"bars ([0-9.]+) x ([0-9.]+) x ([0-9.]+), span", c1["what"], 2),
        "ca1_sbs_t": _num(r"bars ([0-9.]+) x ([0-9.]+) x ([0-9.]+), span", c1["what"], 3),
        "ca1_span": _num(r"span ([0-9.]+)", c1["what"]),
        "ca1_temp_c": _num(r"tested at (\d+) \+/- (\d+) C", c1["what"]),
        "ca1_temp_tol": _num(r"tested at (\d+) \+/- (\d+) C", c1["what"], 2),
        "ca1_r": _num(r"R ([0-9.]+), <=", c1["what"]),
        "ca1_hz_max": _num(r"<= (\d+) Hz", c1["what"]),
        "ca1_n_fat": _num(r"(\d+) SBS fatigue \+ (\d+) SBS static", c1["coupons"]),
        "ca1_n_static": _num(r"(\d+) SBS fatigue \+ (\d+) SBS static", c1["coupons"], 2),
        "ca1_smax_mpa": _num(r"= ([0-9.]+) MPa, i\.e\. peak load", c1["load"]),
        "ca1_peak_n": _num(r"peak load (\d+) N", c1["load"]),
        "ca1_load_factor": _num(r"Smax \(shear\) = ([0-9.]+) x", c1["load"]),
        "ca1_cycles": float(re.search(r"run out to (1e\d)", c1["pass"]).group(1)),
        "layer_s": _num(r"every layer takes >= (\d+) s", c1["what"]),
        "cond_c": _num(r"constant mass at (\d+) C over saturated NaCl", c1["what"]),
        "cond_rh": _num(r"NaCl \(([0-9.]+) % RH", c1["what"]),
        "cond_dm_pct": _num(r"mass changes < ([0-9.]+) % in 24 h", c1["what"]),
        "uptake_tds_pct": _num(r"against the TDS ([0-9.]+) %", c1["what"]),
        # CA-3-HW
        "ca3_z_mpa": _num(r"\(a\) hot/wet Z B-basis >= ([0-9.]+) MPa", c3["pass"]),
        "ca3_z_hw": _num(r"\(= ([0-9.]+) / ([0-9.]+),", c3["pass"]),
        "ca3_r1": _num(r"\(= ([0-9.]+) / ([0-9.]+),", c3["pass"], 2),
        "ca3_sbs_mpa": _num(r"\(b\) hot/wet SBS B-basis >= ([0-9.]+) MPa", c3["pass"]),
        "ca3_pause_frac": _num(r"pause-layer SBS mean >= ([0-9.]+) x", c3["pass"]),
        "ca3_k": _num(r"k ([0-9.]+) at n (\d+)", c3["statistic"]),
        "ca3_n_hw": _num(r"hot/wet: (\d+) Z \+ (\d+) SBS", c3["coupons"]),
        "ca3_n_hw_sbs": _num(r"hot/wet: (\d+) Z \+ (\d+) SBS", c3["coupons"], 2),
        "ca3_n_dry": _num(r"dry: (\d+) Z \+ (\d+) SBS", c3["coupons"]),
        "ca3_n_dry_sbs": _num(r"dry: (\d+) Z \+ (\d+) SBS", c3["coupons"], 2),
        "ca3_n_pause": _num(r"pause-layer: (\d+) SBS", c3["coupons"]),
        "ca3_pause_min": _num(r"planned (\d+) min pause", c3["what"]),
        "ca3_z_gauge_w": _num(r"([0-9.]+) x ([0-9.]+) mm gauge", c3["what"]),
        "ca3_z_gauge_t": _num(r"([0-9.]+) x ([0-9.]+) mm gauge", c3["what"], 2),
        "ca3_knock_booked": _num(r"booked [0-9.]+ x [0-9.]+ = ([0-9.]+)", c3["pass"]),
        "ca3_r1_k": _num(r"R1 = ([0-9.]+) x Z_m / ([0-9.]+)", c3["if_below"]),
        "ca3_joint_k": _num(r"joint fatigue = ([0-9.]+) x Z_m", c3["if_below"]),
        "ca3_z_ref": _num(r"R1 = ([0-9.]+) x Z_m / ([0-9.]+)", c3["if_below"], 2),
        # CA-4-HW
        "ca4_e_ratio": _num(r"E\(23 C dry\) >= ([0-9.]+)", c4["pass"]),
        "ca4_flex60_mpa": _num(r"mean - [0-9.]+ SD \(n \d+\) >= ([0-9.]+) MPa", c4["pass"]),
        "ca4_k": _num(r"mean - ([0-9.]+) SD \(n \d+\)", c4["pass"]),
        "ca4_n": _num(r"(\d+) per condition", c4["coupons"]),
        "ca4_e_booked": _num(r"at the booked ([0-9.]+)", c4["pass"]),
        # T4b-PPA-COLD
        "t4b_kg": _num(r"(\d+) kg \((\d+) lb\) from", tb["load"]),
        "t4b_mm": _num(r"from (\d+) mm", tb["load"]),
        "t4b_j": _num(r"(\d+) J per drop", tb["load"]),
        "t4b_drops": _num(r"(\d+) drops per foot", tb["coupons"]),
        "t4b_min": _num(r"within (\d+) min of removal", tb["what"]),
        "soak_h": _num(r">= (\d+) h at (-\d+) C", tb["what"]),
        "soak_c": _num(r">= (\d+) h at (-\d+) C", tb["what"], 2),
        # T4c-PPA-COLD
        "t4cc_in": _num(r"\((\d+) in, (\d+) orientations", tcc["what"]),
        "t4cc_orient": _num(r"\((\d+) in, (\d+) orientations", tcc["what"], 2),
        "t4cc_min": _num(r"within (\d+) min of removal", tcc["what"]),
        "t4cc_resoak_min": _num(r"re-soak (\d+) min", tcc["what"]),
        # T4c-PPA-HW
        "t4c_z_max": _num(r"lower stay z 0-(\d+)", th["what"]),
        "t4c_n_ppa": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", th["coupons"]),
        "t4c_n_paht": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", th["coupons"], 2),
        "t4c_slug_kg": _num(r"([0-9.]+) kg slug", th["load"]),
        "t4c_drop_m": _num(r"from ([0-9.]+) m", th["load"]),
        "t4c_j": _num(r"\): (\d+) J", th["load"]),
        "t4c_p_n": float(th["bend"]["p_tip_n"]),
        "t4c_p_lbf": float(th["bend"]["p_tip_lbf"]),
        "t4c_arm_mm": float(th["bend"]["arm_mm"]),
        "t4c_m_nm": th["bend"]["m_test_nmm"] / 1000.0,
        "t4c_clamp": th["bend"]["set_up"],
        # T4c-PPA-CROWN
        "crown_n_ppa": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", cr["coupons"]),
        "crown_n_paht": _num(r"(\d+) PPA-CF \+ (\d+) PAHT-CF control", cr["coupons"], 2),
        "crown_slug_kg": _num(r"([0-9.]+) kg slug", cr["what"]),
        "crown_bar_mm": _num(r"(\d+) mm of upper bar", cr["what"]),
        "crown_drop_m": _num(r"([0-9.]+) m crown-corner", cr["load"]),
        "crown_j": _num(r"(\d+) J", cr["load"]),
        # US2 lug proof and CLEVIS-SHARE B (DECISIONS 2026-11-25 orchestrator call; numbers from the JSON rows)
        "lug_margin": lug["value"], "lug_goal": lug["goal"],
        "lug_factor": math.ceil(round(k_lug * 100, 6)) / 100.0,
        "clevis_f_share1": clev["value"], "clevis_goal": clev["goal"],
        "share_max": math.floor(round(share * 100, 6)) / 100.0,
        "clevis_f_share06": b73()["clevis"]["share_0.6"]["fatigue"],
        # print basis
        "layer_h": _num(r"([0-9.]+) mm layers", lh),
        "rate_mm3_s": _num(r"\(([0-9.]+) mm3/s x ([0-9.]+)\)", pt),
        "rate_k": _num(r"\(([0-9.]+) mm3/s x ([0-9.]+)\)", pt, 2),
        "spool_reserve_g": _num(r"(\d+) g of each", assumption_73("SPOOL-RESERVE")["text"]),
    }


def pass_lines_recomputed() -> dict:
    """The same lines from the JSON's numeric fields: the tests compare them with the text."""
    d = h1p_json()
    b = b73()
    M = b["margins_bl073_hw"]
    c = coupons()
    m_z = min(M["R1"], M["z 234 joint fatigue"])
    zn = b["basis"]["z_knocked_hw"] / m_z
    pl = pass_lines()
    return {"ca3_z_mpa": zn, "ca3_sbs_mpa": 0.6 * zn, "ca3_k": b["basis"]["k_n10"],
            "ca1_smax_mpa": c["CA-1-HW"]["smax_test_mpa"], "ca1_peak_n": c["CA-1-HW"]["peak_load_n"],
            "t4c_p_n": req()["t4c_bend_load"]["p_tip_n"],
            "layer_s": min(v["median_s"] for v in b["layer_time"].values()),
            "ca3_r1": M["R1"], "ca3_z_hw": b["basis"]["z_knocked_hw"],
            "ca3_knock_booked": b["basis"]["knock_hw"],
            "lug_factor": pl["lug_goal"] / b["lug"]["fatigue"],
            "share_max": b["clevis"]["share_1"]["fatigue"] / pl["clevis_goal"],
            "t4c_z_max": req()["t4c_stay_cut_z_mm"]}


def pass_lines_bl070() -> dict:
    """The BL-070 lines of the superseded rows (read from the 'coupons' text, as BL-071 did)."""
    c = coupons_bl070()
    c1, c3, c4 = c["CA-1-PPA"], c["CA-3-PPA"], c["CA-4-PPA"]
    return {"ca1_smax_ratio": _num(r"Smax / UTS = ([0-9.]+)", c1["pass"]),
            "ca3_z_mpa": _num(r"SD >= ([0-9.]+) MPa", c3["pass"]),
            "ca4_e40": _num(r"E\(40 C wet\) / E\(23 C dry\) >= ([0-9.]+)", c4["pass"])}


# ============================================================================ coupon pieces, blocks, towers
def _manifold(m):
    import numpy as np
    import manifold3d as m3d
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                                 tri_verts=np.asarray(m.faces, np.uint32)))


def _trimesh(man):
    import numpy as np
    import trimesh
    out = man.to_mesh()
    return trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=True)


@functools.lru_cache(maxsize=None)
def _assembled():
    import trimesh
    return trimesh.load(H1P_STL / "h1_assembled.stl")


def cut_frame(lo, hi):
    """Box cut of the exported H1-P frame (frame coordinates)."""
    import manifold3d as m3d
    box = m3d.Manifold.cube(tuple(h - l for h, l in zip(hi, lo))).translate(tuple(lo))
    return _trimesh(_manifold(_assembled()) ^ box)


def t4c_stay_mesh():
    """T4c-PPA-HW: the H1-P R stay z 0-140 (bl071_requests.t4c_stay_cut_z_mm), cut at x = +95 mm."""
    m = _assembled()
    return cut_frame((95.0, m.bounds[0][1] - 5.0, m.bounds[0][2] - 1.0),
                     (m.bounds[1][0] + 5.0, m.bounds[1][1] + 5.0, float(req()["t4c_stay_cut_z_mm"])))


def crown_mesh():
    """T4c-PPA-CROWN: the R crown corner, the pawl housing on the spine (x 0) and the upper bar between (ASSUMPTION CROWN-CUT)."""
    m = _assembled()
    return cut_frame((CROWN_CUT["x_min"], m.bounds[0][1] - 5.0, CROWN_CUT["z_min"]),
                     (m.bounds[1][0] + 5.0, m.bounds[1][1] + 5.0, m.bounds[1][2] + 5.0))


def us2_piece_mesh():
    """CLEVIS-SHARE-B-PPA / US2-LUG-PPA: the H1-P R stay x >= 46, z 40-160 (hinge, US1, US2 lugs), the PAHT route piece box."""
    m = _assembled()
    return cut_frame((US2_CUT["x_min"], m.bounds[0][1] - 5.0, US2_CUT["z_min"]),
                     (m.bounds[1][0] + 5.0, m.bounds[1][1] + 5.0, US2_CUT["z_max"]))


def print_pose(t):
    """Turned as the frame prints (wearer face, frame -y, on the plate: layers along frame y), corner at the origin."""
    import numpy as np
    t = t.copy()
    t.apply_transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float))
    t.apply_translation(-t.bounds[0])
    return t


def t4c_print_mesh(t=None):
    return print_pose(t if t is not None else t4c_stay_mesh())


def _layer_area(t, h: float):
    from huntkit.gendesign.bl073_hotwet import layer_profile
    return layer_profile(t, h)["area"]


def blocks() -> dict:
    """The solid blocks the bars are cut from (plan size, height), from the JSON bar sizes and counts."""
    pl = pass_lines()
    lh = pl["layer_h"]
    L, w, t = pl["ca1_sbs_l"], pl["ca1_sbs_w"], pl["ca1_sbs_t"]
    n_a = int(pl["ca1_n_fat"] + pl["ca1_n_static"] + SPARES + pl["ca3_n_hw_sbs"] + pl["ca3_n_dry_sbs"] + SPARES)
    n_b = int(pl["ca3_n_pause"] + SPARES)
    n_z = int(pl["ca3_n_hw"] + pl["ca3_n_dry"] + SPARES)
    h_sbs = round((t + 2 * FACE) / lh) * lh

    def grid(n, cols):
        rows = math.ceil(n / cols)
        return (cols * (w + KERF) + 2 * TRIM, rows * (L + KERF) + 2 * TRIM)

    a = grid(n_a, 9)
    b = grid(n_b, 4)
    z_len = n_z * (Z_END_W + KERF) + 2 * TRIM
    z_h = 75.0 + 2 * Z_TRIM_END
    n_layers_sbs = int(round(h_sbs / lh))
    return {"sbs": {"n": n_a, "x": a[0], "y": a[1], "h": h_sbs, "layers": n_layers_sbs,
                    "mid_layer_line": n_layers_sbs // 2},
            "sbs_pause": {"n": n_b, "x": b[0], "y": b[1], "h": h_sbs, "layers": n_layers_sbs,
                          "pause_before_layer": n_layers_sbs // 2 + 1, "pause_z": (n_layers_sbs // 2) * lh},
            "z": {"n": n_z, "x": z_len, "y": Z_SLAB_T, "h": z_h},
            "flex": {"n": int(3 * pl["ca4_n"] + SPARES), "x": FLEX["L"], "y": FLEX["w"], "h": FLEX["t"]}}


@functools.lru_cache(maxsize=None)
def pieces() -> dict:
    """Coupon pieces cut from the H1-P frame: print-pose mesh, mass, layer areas, support share."""
    import trimesh
    pr = h1p_json()["h1p"]["print"]
    lh = pass_lines()["layer_h"]
    sup_lo = pr["lower"]["support_g_ppa_high"] / pr["lower"]["part_g_ppa"]
    sup_up = pr["upper"]["support_g_ppa_high"] / pr["upper"]["part_g_ppa"]
    out = {}
    for k, fn, sup in (("stay", t4c_stay_mesh, sup_lo), ("crown", crown_mesh, sup_up), ("us2", us2_piece_mesh, sup_lo)):
        fr = fn()
        pm = print_pose(fr)
        out[k] = {"frame": fr, "print": pm, "g": fr.volume * rho(), "volume": fr.volume, "support": sup,
                  "area": _layer_area(pm, lh), "extents": [float(v) for v in pm.extents],
                  "bodies": int(fr.body_count), "watertight": bool(fr.is_watertight)}
    for k, f in (("clevis", "us2_clevis_R.stl"), ("keeper", "hip_nut_keeper.stl")):
        m = trimesh.load(H1P_STL / f)
        m.apply_translation(-m.bounds[0])
        out[k] = {"frame": m, "print": m, "g": m.volume * rho(), "volume": m.volume, "support": 0.0,
                  "area": _layer_area(m, lh), "extents": [float(v) for v in m.extents], "bodies": int(m.body_count),
                  "watertight": bool(m.is_watertight)}
    return out


def _area_req() -> float:
    """Plate area per layer (mm2) that takes the frame layer time by the BL-053 rule: t = A h / rate x k."""
    pl = pass_lines()
    return pl["layer_s"] * pl["rate_mm3_s"] / (pl["layer_h"] * pl["rate_k"])


def job_spec(n_st: int, n_cr: int, n_st_a: int, n_cr_a: int) -> list:
    """(job, title, [(kind, count)], pause?, material). Plates balanced so each PPA-CF job fits one spool after its
    reserve (a coupon job never changes spool) and tall pieces share the tower with the Z slab."""
    a, b = n_st // 2, n_st - n_st // 2
    return [
        ("A", "SBS block (CA-1-HW + CA-3-HW no-pause bars)", [("sbs", 1)], False, "PPA-CF"),
        ("B", "SBS pause block (CA-3-HW pause layer)", [("sbs_pause", 1)], True, "PPA-CF"),
        ("C", f"crown corners {n_cr - 1} + Z slab (T4c-PPA-CROWN, CA-3-HW Z bars)", [("crown", n_cr - 1), ("z", 1)], False, "PPA-CF"),
        ("D", f"stays {a} + bend bars (T4c-PPA-HW, CA-4-HW)", [("stay", a), ("flex", 1)], False, "PPA-CF"),
        ("E", "US2 piece + clevis + crown corner 1 + 2 hip nut keepers (CLEVIS-SHARE-B-PPA / US2-LUG-PPA, T4c-PPA-CROWN)",
         [("us2", 1), ("clevis", 1), ("crown", 1), ("keeper", 2)], False, "PPA-CF"),
        ("F", f"stays {b} (T4c-PPA-HW)", [("stay", b)], False, "PPA-CF"),
        ("G", "PAHT-CF controls (1 stay + 1 crown corner), PAHT-CF profile of BUILD_H1",
         [("stay_paht", n_st_a), ("crown_paht", n_cr_a)], False, "PAHT-CF"),
    ]


def jobs() -> list[dict]:
    """The coupon print jobs. Each: items (name, count, layer-area array, height, g each, support share, material),
    then the dummy tower sized band by band so every layer reaches the frame layer time."""
    import numpy as np
    pl = pass_lines()
    lh = pl["layer_h"]
    bk = blocks()
    pc = pieces()

    def box(nm, b, n=1):
        layers = int(round(b["h"] / lh))
        return {"name": nm, "count": n, "area": np.full(layers, b["x"] * b["y"]), "h": layers * lh,
                "g": b["x"] * b["y"] * b["h"] * rho(), "support": 0.0}

    def piece(nm, k, n, mat="PPA-CF"):
        q = pc[k]
        r = rho() if mat == "PPA-CF" else rho_paht()
        return {"name": nm, "count": n, "area": q["area"], "h": len(q["area"]) * lh, "g": q["volume"] * r,
                "support": q["support"], "mat": mat}

    fx = bk["flex"]
    lib = {
        "sbs": lambda n: box(f"SBS block {bk['sbs']['x']:.0f} x {bk['sbs']['y']:.0f} x {bk['sbs']['h']:.1f} mm, "
                             f"{bk['sbs']['n']} bars (`block_sbs.stl`)", bk["sbs"]),
        "sbs_pause": lambda n: box(f"SBS block {bk['sbs_pause']['x']:.0f} x {bk['sbs_pause']['y']:.0f} x "
                                   f"{bk['sbs_pause']['h']:.1f} mm, {bk['sbs_pause']['n']} bars (`block_sbs_pause.stl`)", bk["sbs_pause"]),
        "z": lambda n: box(f"Z slab {bk['z']['x']:.0f} x {bk['z']['y']:.0f} x {bk['z']['h']:.0f} mm standing, "
                           f"{bk['z']['n']} 1BA bars (`block_z.stl`)", bk["z"]),
        "flex": lambda n: {"name": f"bend bar {fx['x']:.0f} x {fx['y']:.0f} x {fx['h']:.0f} flat", "count": fx["n"],
                           "area": np.full(int(round(fx["h"] / lh)), fx["x"] * fx["y"]), "h": fx["h"],
                           "g": fx["x"] * fx["y"] * fx["h"] * rho(), "support": 0.0},
        "stay": lambda n: piece("T4c stay `t4c_stay_R.stl`", "stay", n),
        "crown": lambda n: piece("crown corner `crown_corner_R.stl`", "crown", n),
        "us2": lambda n: piece("US2 route piece `us2_route_stay_R_h1p.stl`", "us2", n),
        "clevis": lambda n: piece("US2 clevis `h1p/us2_clevis_R.stl`", "clevis", n),
        "keeper": lambda n: piece("hip nut keeper `h1p/hip_nut_keeper.stl` (1 + 1 spare)", "keeper", n),
        "stay_paht": lambda n: piece("T4c stay control", "stay", n, "PAHT-CF"),
        "crown_paht": lambda n: piece("crown corner control", "crown", n, "PAHT-CF"),
    }
    n_st, n_cr = int(pl["t4c_n_ppa"]), int(pl["crown_n_ppa"])
    J = []
    for job, title, spec, pause, mat in job_spec(n_st, n_cr, int(pl["t4c_n_paht"]), int(pl["crown_n_paht"])):
        if not any(n > 0 for _, n in spec):
            continue
        J.append(dict(job=job, title=title, items=[{**lib[k](n), "kind": k} for k, n in spec if n > 0], mat=mat,
                      pause=(f"Add Pause at layer {bk['sbs_pause']['pause_before_layer']} (print z "
                             f"{bk['sbs_pause']['pause_z']:.2f} mm, the block's mid-plane), wait {pl['ca3_pause_min']:.0f} "
                             "min with the door shut, resume") if pause else None))
    areq = _area_req()
    band = int(round(TOWER_BAND_MM / lh))
    for j in J:
        n = max(len(it["area"]) for it in j["items"])
        a = np.zeros(n)
        for it in j["items"]:
            a[:len(it["area"])] += it["count"] * it["area"]
        tw = np.maximum(areq - a, 0.0)
        steps = []
        per = np.zeros(n)
        for i0 in range(0, n, band):
            s = max(float(tw[i0:i0 + band].max()), TOWER_MIN_MM2)
            steps.append((i0 * lh, min(n, i0 + band) * lh, s))
            per[i0:i0 + band] = s
        r = rho_paht() if j.get("mat") == "PAHT-CF" else rho()
        tower_g = sum((z1 - z0) * s for z0, z1, s in steps) * r
        parts_g = sum(it["count"] * it["g"] for it in j["items"])
        sup_g = sum(it["count"] * it["g"] * it["support"] for it in j["items"])
        layer_t = (a + per) * lh / pl["rate_mm3_s"] * pl["rate_k"]
        j.update(layers=n, height=n * lh, tower_steps=steps, tower_g=tower_g, parts_g=parts_g, support_g=sup_g,
                 filament_g=(parts_g + sup_g + tower_g) * (1 + WASTE), min_layer_s=float(layer_t.min()),
                 print_h=float(layer_t.sum()) / 3600.0, tower_max_mm2=max(s for _, _, s in steps),
                 mat=j.get("mat", "PPA-CF"))
    return J


def tower_mesh(j: dict):
    """The stepped square dummy tower of a job (STL in test_pieces/)."""
    import manifold3d as m3d
    out = None
    for z0, z1, s in j["tower_steps"]:
        a = math.sqrt(s)
        b = m3d.Manifold.cube((a, a, z1 - z0)).translate((-a / 2, -a / 2, z0))
        out = b if out is None else out + b
    return _trimesh(out)


@functools.lru_cache(maxsize=None)
def coupon_plan() -> dict:
    J = jobs()
    ppa_j = [j for j in J if j["mat"] == "PPA-CF"]
    rows = []
    for j in J:
        for it in j["items"]:
            rows.append({"job": j["job"], "item": it["name"], "count": it["count"], "g_each": round(it["g"], 1),
                         "material": j["mat"]})
        rows.append({"job": j["job"], "item": f"dummy tower `tower_{j['job']}.stl` (max {j['tower_max_mm2']:.0f} mm2)",
                     "count": 1, "g_each": round(j["tower_g"], 1), "material": j["mat"]})
    return {"jobs": J, "rows": rows, "ppa_filament_g": round(sum(j["filament_g"] for j in ppa_j), 1),
            "paht_filament_g": round(sum(j["filament_g"] for j in J if j["mat"] != "PPA-CF"), 1),
            "area_req_mm2": _area_req(), "print_h": round(sum(j["print_h"] for j in J), 1)}


# ============================================================================ spools
def spool_plan(cp: dict | None = None) -> dict:
    """Which 0.75 kg spool feeds what, in print order: first-article upper half, coupons, then (after the gate) the two
    halves. A half starts on a spool that holds its pre-change use (high bound) + the reserve and changes at its
    planned layer to a spool that finishes it (total - low bound) + the reserve; a coupon job never changes spool."""
    cp = cp or coupon_plan()
    sp = spool()
    pl = pass_lines()
    res = pl["spool_reserve_g"]
    s73 = b73()["spool_plan"]
    spools: list[dict] = []

    def new(use: str) -> dict:
        s = {"spool": len(spools) + 1, "left": sp["g"], "uses": []}
        spools.append(s)
        return s

    def take(s, g, use):
        s["left"] -= g
        s["uses"].append(f"{use}: {g:.0f} g")
        assert s["left"] >= res - 1e-6, (use, s)

    def half(name, label):
        h = s73[name]
        lo, hi = h["swap"]["spool1_g_range"]
        tot = h["filament_total_g"]
        a = next((s for s in spools if s["left"] - res >= hi), None) or new(label)
        take(a, hi, f"{label} to the change at layer {h['swap']['layer']}")
        b = new(label)
        take(b, tot - lo, f"{label} from layer {h['swap']['layer']}")
        return {"start": a["spool"], "finish": b["spool"], "start_needs_g": hi + res, "finish_needs_g": tot - lo + res}

    fa = half("upper", "first-article upper half")
    for j in sorted([j for j in cp["jobs"] if j["mat"] == "PPA-CF"], key=lambda q: -q["filament_g"]):
        s = next((s for s in spools if s["left"] - res >= j["filament_g"]), None) or new(f"job {j['job']}")
        take(s, j["filament_g"], f"job {j['job']}")
    n_before_gate = len(spools)
    lo_h = half("lower", "frame lower half")
    up_h = half("upper", "frame upper half")
    n = len(spools)
    return {"rows": [{"spool": s["spool"], "uses": "; ".join(s["uses"]), "left_g": round(s["left"], 0)} for s in spools],
            "spools": n, "usd": round(n * sp["usd"], 2), "spool_usd": sp["usd"], "spool_g": sp["g"], "reserve_g": res,
            "before_gate": n_before_gate, "booked_bl073": booked_spools(),
            "fa": fa, "lower": lo_h, "upper": up_h,
            "halves_g": round(s73["lower"]["filament_total_g"] + s73["upper"]["filament_total_g"], 0),
            "fa_g": s73["upper"]["filament_total_g"], "coupons_g": cp["ppa_filament_g"],
            "total_g": round(s73["lower"]["filament_total_g"] + 2 * s73["upper"]["filament_total_g"] + cp["ppa_filament_g"], 0),
            "left_g": round(sum(s["left"] for s in spools), 0)}


# ============================================================================ rig loads
def rig_check() -> dict:
    """Every static load of the BL-074 rows against the kit B 100 kg cell (JSON rig_loads + the lug proof)."""
    rl = dict(req()["rig_loads"])
    pl = pass_lines()
    cl = clevis_b()
    cell = rl.pop("cell_n")
    rl.pop("all_under_cell", None)
    rl["lug_proof_n"] = round(pl["lug_factor"] * cl["proof_n"], 0)
    rl["sbs_fatigue_peak_n"] = pl["ca1_peak_n"]
    return {"loads": rl, "cell_n": cell, "all_under_cell": all(v <= cell for v in rl.values()),
            "max_n": max(rl.values())}


@functools.lru_cache(maxsize=None)
def clevis_b() -> dict:
    """CLEVIS-SHARE B (clevis_bl056.json kit 'B'): the loading the US2 lug proof and the share measurement reuse."""
    k = json.loads((AN / "clevis_bl056.json").read_text())["kit"]["B"]
    return {"proof_n": k["proof_n"], "peak_n": k["cycle_peak_n"], "R": k["R"], "cycles": int(k["cycles"]),
            "unit": k["pull_unit_vector_frame_R"], "row": k["row"], "test": k["test"]}


# ============================================================================ hip mount (trap-free boss)
RING_SOURCE = {
    "service": "SendCutSend (laser cut, 6061-T6, .063 in = 1.60 mm, +/-0.005 in)",
    "url": "https://sendcutsend.com/materials/6061-aluminum",
    "read": "2026-11-25: 6061-T6 laser cut in .040-.750 in, .063 in listed; design guide: holes and cut-outs 1.5-2x the "
            "thickness from an edge, holes no smaller than the thickness; instant quote from 0.25 x 0.375 in",
    "usd_each": 8.00,
    "price": "ASSUMPTION RING-PRICE: USD 8 per plate in an order of 4 (two sets: one spare), shipping in; no price is "
             "published, check the instant quote with hip_bearing_ring.dxf (BL-076: two arc plates per frame)",
    "fallback": "cut by hand from 1.6 mm (0.063 in) 6061-T6 sheet: print the DXF 1:1, glue it on, centre-punch, drill "
                "the D5.5 holes, saw and file the two arc outlines to the line (R1.5 corners), deburr",
}
TORQUE_DRIVER = {
    "item": "Wera 7440 Kraftform adjustable torque screwdriver 0.3-1.2 N m (2.7-10.6 in lbf), 1/4 in hex drive, "
            "+/-6 %, part 05074700001",
    "usd": 137.51,
    "source": "TestEquity listing USD 137.51 (search snapshot 2026-11-25, https://www.testequity.com/product/10238639-05074700001); "
              "Rapid Online GBP 95 ex VAT (https://rapidonline.com/wera-05074700001-7440-kraftform-adjustable-torque-screwdriver-0-3-1-2nm-54-8011)",
}


def ring_pieces(hm: dict) -> int:
    return int(hm["ring"].get("pieces", 1))


def share_gauge() -> dict:
    """BL-076 SHARE-GAUGE: the US2 gauge read with the pin load on each cheek (bl070_h1p.json bl076.share_gauge)."""
    return h1p_json()["bl076"]["share_gauge"]


def hip() -> dict:
    d = h1p_json()
    hm = d["h1p"]["hip_mount"]
    fl = json.loads((AN / "h1_closeout.json").read_text())["mount_flange"]
    sc = hm["screw"]
    pat = d["h1_ppa"]["hip_inserts"]["pattern"]
    from huntkit.gendesign.frame_h1 import JOINT
    thr = sc["protrusion_mm"] / M5_PITCH
    return {"n": pat["n"], "pattern": pat, "hardware": hm["hardware"], "torque": hm["torque_nm"],
            "torque_inlbf": hm["torque_nm"] / NM_PER_INLBF, "preload": hm["preload_n"], "screw_len": sc["screw_l_mm"],
            "stack": sc["stack_mm"], "protrusion_mm": sc["protrusion_mm"], "protrusion_threads": sc["protrusion_threads"],
            "threads_calc": thr, "threads_min": THREADS_PROUD_MIN, "proud_min_mm": THREADS_PROUD_MIN * M5_PITCH,
            "ring": hm["ring"], "boss": hm["boss"], "webs": hm["webs"], "cold": hm["cold"], "relax": hm["relaxation"],
            "min_sf": hm["min_sf"], "flange_t": fl["t_mm"], "nut_t": JOINT.nut_t, "nut_af": JOINT.nut_af,
            "keeper_g": b73()["hip_parts"]["hip_nut_keeper"]["g"], "keeper_wall": b73()["hip_parts"]["keeper_min_wall_mm"],
            "files": b73()["hip_parts"]["files"],
            "mount_hole_d": json.loads((AN / "bl058.json").read_text())["hip_mount"]["hole_d_mm"],
            "screw": "Ti gr5 (Ti-6Al-4V) M5 x 35 low-head socket cap screw, DIN 7984",
            "nut": f"M5 hex nut A2 stainless, DIN 934, m = {JOINT.nut_t:.1f} mm, {JOINT.nut_af:.0f} AF"}


# ============================================================================ register rows, sheets, results
REG_COLS = ["id", "status", "tier", "title", "defined_in", "what_it_proves", "gates", "grams_at_stake_g",
            "safety_at_stake", "specimen", "kit", "steps", "pass_fail", "cost_usd", "cost_basis", "hours_hands_on",
            "hours_machine", "phase", "run_order", "first_weekend", "notes", "g_per_usd_eq"]
DEF = "designs/pack_5200/iter1/frame/bl070_h1p.json coupons_bl073; designs/pack_5200/print/frame_h1p/COUPONS_H1P.md"
DEF_DEC = "docs/DECISIONS.md 2026-11-25 (orchestrator call after BL-073); bl070_h1p.json h1p.rows_by_name"


def _mpa(x: float) -> str:
    return f"{x:g} MPa ({x * 145.038:,.0f} psi)"


def _n(x: float) -> str:
    return f"{x:,.0f} N ({x / G:.1f} kg on the scale, {x / N_PER_LBF:,.0f} lbf)"


def _c(x: float) -> str:
    return f"{x:g} C ({x * 9 / 5 + 32:.0f} F)"


def kind_jobs(kind: str) -> list[str]:
    return [j["job"] for j in coupon_plan()["jobs"] if any(it["kind"] == kind for it in j["items"])]


def kind_g(kind: str) -> float:
    """Filament (g, + towers and waste pro rata) booked to one kind of coupon across its jobs."""
    out = 0.0
    for j in coupon_plan()["jobs"]:
        tot = j["parts_g"] + j["support_g"]
        for it in j["items"]:
            if it["kind"] == kind:
                out += j["filament_g"] * it["count"] * it["g"] * (1 + it["support"]) / tot
    return out


def _job_txt(kind: str) -> str:
    js = kind_jobs(kind)
    return ("job" if len(js) == 1 else "jobs") + " " + " + ".join(js)


def gate_txt() -> str:
    pl = pass_lines()
    return (f"(a) the BL-073 coupons pass: CA-3-HW, CA-1-HW, CA-4-HW (a), T4c-PPA-HW and T4c-PPA-CROWN; (b) US2-LUG-PPA, "
            f"the US2 lug proof at x {pl['lug_factor']:g} load, passes; (c) CLEVIS-SHARE-B-PPA measures an outer-cheek "
            f"share <= {pl['share_max']:g}")


def guide_steps() -> dict:
    """Beginner steps per test, one list each (the register 'steps' cell and the sheets use these)."""
    pl = pass_lines()
    bk = blocks()
    cb = clevis_b()
    lh = pl["layer_h"]
    k10, k6 = pl["ca3_k"], b73()["basis"]["k_n6"]
    tw = f"Every coupon job prints beside its dummy tower (`test_pieces/tower_<job>.stl`) so every layer takes >= {pl['layer_s']:.0f} s"
    cond = (f"CONDITION: tray of non-iodised salt (NaCl) wetted to a slush in a sealed glass jar, parts on a rack above it, "
            f"jar in the box at {_c(pl['cond_c'])} ({pl['cond_rh']:g} % RH over the salt). Weigh the traveller plate on "
            f"the 0.001 g scale every day at the same hour; done when it changes < {pl['cond_dm_pct']:g} % in 24 h. "
            f"Write the uptake % (TDS: {pl['uptake_tds_pct']:g} %)")
    hot = f"Test at {pl['ca1_temp_c']:g} +/- {pl['ca1_temp_tol']:g} C ({pl['ca1_temp_c'] * 9 / 5 + 32:.0f} F) inside the 40 C box, 1 h soak first, thermometer beside the part"
    f_lug_p, f_lug_c = pl["lug_factor"] * cb["proof_n"], pl["lug_factor"] * cb["peak_n"]
    return {
        "FA-H1P-UP": [
            "Dry spools 1 and 2 at 120 C (248 F) for 10 h (PRINT_SHEET_H2S.md). Spool 1 must be FULL.",
            "Slice `designs/pack_5200/iter1/frame/h1p/h1_upper_flat_print.stl` (the part with its 6 snap-off pads) with the settings of PRINT_SHEET_H2S.md section 1. Do not rotate it.",
            f"Add the planned filament change (PRINT_SHEET_H2S.md section 3): Add Pause at layer {b73()['spool_plan']['upper']['swap']['layer']} (print z {b73()['spool_plan']['upper']['swap']['print_z_mm']:.2f} mm, {b73()['spool_plan']['upper']['swap']['print_z_mm'] / IN:.2f} in). Screenshot the layer-time view and write the shortest and the median layer time.",
            "Print. Stay at the printer for the first layer: all 6 pad feet and the brim stuck flat.",
            "At the pause: swap to spool 2 within 10 min, door shut the whole time, check the chamber reads 65 C (149 F) before Resume.",
            "When done and below 40 C (104 F) in the chamber: feeler gauge under each pad foot and the brim edge: write the largest gap (pass <= 0.5 mm, 0.02 in).",
            "Snap the pads off with flush cutters at the neck; sand each scar flush (no dent deeper than 0.6 mm, 0.024 in). Supports off as BUILD_H1 section 4.",
            f"Weigh the half (pads and supports off): write it. Expected {h1p_json()['h1p']['export']['upper']['g_ppa']:.0f} g ({h1p_json()['h1p']['export']['upper']['g_ppa'] / OZ:.1f} oz), -3 / +4 %.",
            "Look at the change layer with the 10x loupe all round: write any gap, blob or line you can catch a fingernail on. Photograph it.",
        ],
        "CA-3-HW": [
            f"Print {_job_txt('sbs')}, {_job_txt('sbs_pause')} and {_job_txt('z')} (COUPONS_H1P.md section 2). {tw}: check the slicer preview's layer-time view and write the shortest layer time of each job.",
            f"SBS block: sand {FACE:g} mm off the top and the bottom on 240-grit paper glued to glass ({bk['sbs']['h']:.1f} -> {pl['ca1_sbs_t']:g} mm, {pl['ca1_sbs_t'] / IN:.3f} in), so the mid-plane stays on the line between layers {bk['sbs']['mid_layer_line']} and {bk['sbs']['mid_layer_line'] + 1}. Saw the bars {pl['ca1_sbs_l']:g} x {pl['ca1_sbs_w']:g} mm on the pencil grid with a fine-tooth saw, trim the {TRIM:g} mm edge strip off first.",
            f"Z slab: trim {Z_TRIM_END:g} mm off each end, saw it into {Z_END_W + KERF:g} mm strips, file each to the ISO 527-2 1BA outline with the filing template (gauge {pl['ca3_z_gauge_w']:g} mm wide), sand both faces to {pl['ca3_z_gauge_t']:g} mm ({pl['ca3_z_gauge_t'] / IN:.3f} in). The gauge crosses the layers.",
            f"Label with a paint pen: CA3-Z-H1..H{int(pl['ca3_n_hw'])} and CA3-S-H1..H{int(pl['ca3_n_hw_sbs'])} (hot/wet), CA3-Z-D1..D{int(pl['ca3_n_dry'])} and CA3-S-D1..D{int(pl['ca3_n_dry_sbs'])} (dry), CA3-P1..P{int(pl['ca3_n_pause'])} (pause block B).",
            "DRY set: sealed in a zip bag with desiccant; test within 24 h at 23 C (73 F).",
            cond + ". The hot/wet Z and SBS bars and the pause bars go in together.",
            hot + ".",
            f"Z tensile: lever rig static (turnbuckle in place of the spring). Strength = peak cell force x {LEVER_RATIO:.0f} / (width x thickness). Dry bars need about {_n(req()['rig_loads']['z_bar_static_dry_n'])} at the bar, under the 100 kg cell.",
            f"Short-beam shear: jig with the D6 loading pin on top and two D3 supports {pl['ca1_span']:g} mm ({pl['ca1_span'] / IN:.2f} in) apart, bar flat as printed. Load slowly to the drop. Shear strength = 0.75 x F_max / (width x thickness). Dry bars about {_n(req()['rig_loads']['sbs_static_dry_n'])}.",
            f"Sheet formulas: B-basis of a set of {int(pl['ca3_n_hw'])} = AVERAGE - {k10:g} x STDEV; of the {int(pl['ca3_n_pause'])} pause bars = AVERAGE - {k6:g} x STDEV. Type every value; send the sheet the same day.",
        ],
        "CA-1-HW": [
            f"Bars from block A: CA1-F1..F{int(pl['ca1_n_fat'])} (+1 spare) and CA1-S1..S{int(pl['ca1_n_static'])}, faced, cut and labelled with the CA-3-HW bars; conditioned with the CA-3-HW hot/wet set.",
            "Fit the short-beam jig at the coupon station of the lever rig and put the 40 C box round it (link through the slot in its lid, ASSUMPTION BOX-ON-RIG). " + hot + ".",
            f"Measure each bar's width and thickness (caliper, 3 points, smallest). Static first: the {int(pl['ca1_n_static'])} S bars to failure as CA-3-HW short-beam shear.",
            f"Fatigue peak for each bar: F_max = {pl['ca1_smax_mpa']:g} MPa x width x thickness / 0.75 (about {_n(pl['ca1_peak_n'])} at the bar, {pl['ca1_peak_n'] / LEVER_RATIO / G:.1f} kg on the cell); F_min = {pl['ca1_r']:g} x F_max (R {pl['ca1_r']:g}).",
            "Set the crank throw and the turnbuckle so the cell swings between F_min / 4 and F_max / 4; check over 20 slow turns by hand before the motor runs.",
            f"Run each bar to {pl['ca1_cycles']:,.0f} cycles at 1 Hz (about 28 h; never above {pl['ca1_hz_max']:g} Hz). The rig stops itself on a break, a stiffness drop over 10 % or a force drift over 5 %.",
            "After each run-out: loupe on the bar's middle layer line, photograph, type the cycles reached. A bar that breaks: stop and send the sheet; never swap in the spare to make the count.",
        ],
        "CA-4-HW": [
            f"Bend bars from {_job_txt('flex')}: {int(pl['ca4_n'])} for 23 C dry, {int(pl['ca4_n'])} for 40 C conditioned, {int(pl['ca4_n'])} for 60 C dry (+1 spare). Label CA4-D, CA4-W, CA4-H.",
            "The 23 C and 60 C sets stay sealed with desiccant. " + cond + " (the 40 C set).",
            f"3-point fixture: supports {FLEX['span']:.0f} mm ({FLEX['span'] / IN:.2f} in) apart, bar flat as printed, dial indicator (0.01 mm) on top at mid-span.",
            "Stiffness (each bar): hang 2.0 kg, zero the dial, add 5.0 kg (7.0 kg total), read the dial. E = span^3 x 49.0 N / (4 x width x thickness^3 x reading); the sheet does the sum.",
            f"Strength: load to the break with the come-along and the crane scale. Strength = 3 x F x span / (2 x width x thickness^2). Dry bars about {_n(req()['rig_loads']['flex_xy_static_n'])}.",
            "40 C set: tested at 40 +/- 2 C (104 F) in the 40 C box after 1 h. 60 C set: box thermostat at 60 C (140 F), thermometer 58-62 C for 30 min first (ASSUMPTION BOX-60).",
            f"Sheet: E ratio = mean E (40 C conditioned) / mean E (23 C dry); 60 C strength = AVERAGE - {pl['ca4_k']:g} x STDEV of the {int(pl['ca4_n'])}.",
        ],
        "T4c-PPA-HW": [
            f"Print the stays ({_job_txt('stay')}) in PPA-CF and the PAHT-CF control ({_job_txt('stay_paht')}). Supports off as the frame. Label T4c-P1..P{int(pl['t4c_n_ppa'])}, T4c-A1.",
            f"Pin a {pl['t4c_slug_kg']:g} kg ({pl['t4c_slug_kg'] * 2.2046:.1f} lb) steel slug through the hinge eye with a 5 mm pin.",
            f"Freezer: stays and a thermometer in a chest freezer for >= {pl['soak_h']:g} h; it must read {_c(pl['soak_c'])} or colder (ASSUMPTION FREEZER).",
            f"19 mm (3/4 in) plywood flat on concrete. Mark {pl['t4c_drop_m'] * 1000:.0f} mm ({pl['t4c_drop_m'] / 0.0254:.0f} in) up the wall from the plywood face.",
            "One stay at a time, within 60 s of taking it out: foot down, bottom of the foot at the mark, let go. Back in the freezer 30 min, then drop it side-on (wearer face down).",
            "Loupe on the foot, the hinge eye and every layer line; dye penetrant on the foot and the eye (cleaner, penetrant 10 min, wipe, developer): a red line is a crack.",
            f"Bend (cantilever): {pl['t4c_clamp']}. Clamp the stay in the vise over z 120-140 (its top 20 mm, 0.8 in), pull sideways at the foot {pl['t4c_arm_mm']:.0f} mm ({pl['t4c_arm_mm'] / IN:.1f} in) from the clamp edge to {_n(pl['t4c_p_n'])} with the come-along and the crane scale; hold 1 min; loupe again.",
            "Type Y or N per stay per drop and for the bend. Photograph every stay, both faces, after each step.",
        ],
        "T4c-PPA-CROWN": [
            f"Print the crown corners ({_job_txt('crown')}) in PPA-CF and the PAHT-CF control ({_job_txt('crown_paht')}). Label CR-P1..P{int(pl['crown_n_ppa'])}, CR-A1.",
            f"Pin a {pl['crown_slug_kg']:g} kg ({pl['crown_slug_kg'] * 2.2046:.1f} lb) steel slug through the crown bore (a bolt through the bore, nuts both sides).",
            f"Freezer >= {pl['soak_h']:g} h at {_c(pl['soak_c'])} or colder, thermometer beside the parts.",
            f"Drop from {pl['crown_drop_m'] * 1000:.0f} mm ({pl['crown_drop_m'] / 0.0254:.0f} in) onto the plywood, crown corner first, within 60 s of removal; re-soak 30 min; then side-on.",
            "Loupe and dye penetrant on the crown corner, the pawl housing and the upper bar.",
            "Fit a spine-tube rack offcut and the pawl: the pawl still drops into the teeth and holds a 5 kg (11 lb) pull on the rack.",
            "Type Y or N per part per drop; photograph both faces after each drop.",
        ],
        "CLEVIS-SHARE-B-PPA": [
            f"Print {_job_txt('us2')}: the H1-P route piece `test_pieces/us2_route_stay_R_h1p.stl` and the H1-P clevis `iter1/frame/h1p/us2_clevis_R.stl`. Ream and bolt the clevis as BUILD_H1 section 10; fit the US2 gauge as CLEVIS-SHARE.",
            f"Set up as CLEVIS-SHARE loading B: piece clamped on the bare stay only (z 40-48 and 110-122), pull direction {cb['unit']} (frame R), the real US2 pin set and a sewn US eye.",
            f"Reading 1 (share 1.0): 1 mm PTFE shim between the eye and the OUTER (clevis) cheek, eye pushed against it. Pull to {_n(cb['peak_n'])}, hold 10 s, read the gauge (microstrain) = u1. Unload, read the zero.",
            f"Reading 0 (share 0, BL-076): the same 1 mm PTFE shim between the eye and the INNER (body) cheek, eye pushed against it. Pull to the same {cb['peak_n']:.0f} N, read u0. Unload. u0 / u1 must read {share_gauge()['u0_over_u1_expected'][0]:g}-{share_gauge()['u0_over_u1_expected'][1]:g}; outside that the gauge is off its site: stop and flag it.",
            f"Reading 2 (as built): shim out, eye centred in the throat as sewn. Pull to the same {cb['peak_n']:.0f} N, read u. Unload.",
            "Repeat readings 1, 0 and 2 three times (take the eye off and refit it each time).",
            f"Share = (u - u0) / (u1 - u0) for each set (ASSUMPTION SHARE-GAUGE, BL-076: the gauge does not read zero at share 0, so u / u1 over-reads). Type all nine readings; the sheet takes the largest share.",
            "Keep the piece: it goes on to US2-LUG-PPA.",
        ],
        "US2-LUG-PPA": [
            f"The CLEVIS-SHARE-B-PPA piece and clevis, after its readings. Condition it with the coupons ({_c(pl['cond_c'])} over salt) to constant mass on its traveller, at most 28 days (ASSUMPTION LUG-COND); write the uptake.",
            "Same set-up as loading B with the 1 mm PTFE shim on the OUTER cheek (share 1.0), in the 40 C box on the lever rig. " + hot + ".",
            f"Proof: pull in steps of 25 % to {_n(f_lug_p)} (x {pl['lug_factor']:g} the B proof), hold 60 s, feeler 0.05 mm (0.002 in) at the joint face, unload.",
            f"Cycles: {round(cb['R'] * f_lug_c):.0f} -> {f_lug_c:.0f} N (x {pl['lug_factor']:g} the B cycle peak, R {cb['R']:g}), 1 Hz, {cb['cycles']:,} cycles; stop at 1e3, 1e4 and the end for the feeler, the pencil lines and the gauge at the peak.",
            "End: loupe on the lug root, arm root, cheeks, throat floor and bolt holes; torque marks on the clevis bolts.",
            "Type every reading; send the sheet and the rig log.",
        ],
        "T4b-PPA-COLD": [
            "Runs on the P1 H1-P frame at the end of the P1 stand sequence, before T2u (only after the frame print is released).",
            "Paint marks across every hip screw head, nut and the ring before the soak.",
            f"Frame + bag (empty) in the chest freezer >= {pl['soak_h']:g} h at {_c(pl['soak_c'])} or colder.",
            f"Out, load to {pl['t4b_kg']:g} kg ({pl['t4b_kg'] * 2.2046:.0f} lb) with the sand bags, and drop {pl['t4b_mm']:g} mm ({pl['t4b_mm'] / IN:.0f} in) onto one stay foot within {pl['t4b_min']:g} min of removal ({pl['t4b_j']:g} J).",
            f"{int(pl['t4b_drops'])} drops per foot; re-soak between feet if more than {pl['t4b_min']:g} min have passed.",
            "Loupe on both stay feet, the hip boss and the z 234 bosses for any crack along a layer; check the hip paint marks.",
        ],
        "T4c-PPA-COLD": [
            "Runs on P1 with T4c (HA-LS-1), only after the frame print is released.",
            f"Empty pack in the chest freezer >= {pl['soak_h']:g} h at {_c(pl['soak_c'])} or colder.",
            f"Each drop from {pl['t4cc_in']:g} in ({pl['t4cc_in'] * IN:.0f} mm) within {pl['t4cc_min']:g} min of removal; {int(pl['t4cc_orient'])} orientations incl. crown top and side.",
            f"Re-soak {pl['t4cc_resoak_min']:g} min between drops.",
            "Loupe on the crown corners, the pawl housing and the upper bar after every drop.",
            "Type Y or N per drop; photograph each orientation.",
        ],
    }


def _row(**k) -> dict:
    base = dict(status="ACTIVE", tier="safety", defined_in=DEF, grams_at_stake_g="0", kit="B, A, D",
                cost_usd="0", cost_basis="", hours_hands_on="2", hours_machine="", phase="2", run_order="",
                first_weekend="N", notes="", g_per_usd_eq="")
    base.update(k)
    return base


def register_rows() -> list[dict]:
    pl = pass_lines()
    c = coupons()
    st = guide_steps()
    sp = spool()
    cp = coupon_plan()
    cb = clevis_b()
    up = sp["usd"] / sp["g"]

    def steps(t):
        return "; ".join(f"({i}) {s.replace('; ', ', ')}" for i, s in enumerate(st[t], 1))

    gate = f"H1-P frame print (BUILD_H1P gate {gate_txt()})"
    rel = "BL-074: released to print now"
    s73 = b73()["spool_plan"]["upper"]
    rows = [
        _row(id="FA-H1P-UP", tier="build",
             title="First-article H1-P upper half (PPA-CF): snap-off pads, planned filament change, layer time",
             defined_in="bl070_h1p.json bl073.print_files / spool_plan, assumptions_bl073 PAD / SPOOL-RESERVE / LAYER-H; PRINT_SHEET_H2S.md",
             what_it_proves="PAD, SPOOL-RESERVE, LAYER-H (review 8 M-5, M-6)",
             gates="the coupon jobs (printed before any coupon spool is opened, bl070_h1p.md BL-073 printability)",
             safety_at_stake="plate contact 163 -> 2873 mm2 with pads; the change layer of the upper half",
             specimen="`designs/pack_5200/iter1/frame/h1p/h1_upper_flat_print.stl`, spools 1 + 2", kit="D",
             steps=steps("FA-H1P-UP"),
             pass_fail=(f"every pad and the brim stay down (gap <= 0.5 mm); pads snap off, scars sanded <= 0.6 mm; spool "
                        f"change at layer {s73['swap']['layer']} done within 10 min; filament within 10 % of "
                        f"{s73['filament_total_g']:.0f} g; shortest and median layer time written; mass of the half "
                        "-3 / +4 % of the export"),
             cost_usd=f"{s73['filament_total_g'] * up:.2f}", cost_basis="PPA-CF filament (record ppa_cf_fdm)",
             hours_hands_on="3", hours_machine=f"{h1p_json()['h1p']['print']['upper']['print_h_est']:.0f}", phase="1",
             run_order="89", notes=rel),
        _row(id="CA-3-HW", title=f"PPA-CF Z tensile + SBS, hot/wet B-basis at n {int(pl['ca3_n_hw'])}, dry set, pause-layer SBS",
             what_it_proves=c["CA-3-HW"]["settles"], gates=gate,
             safety_at_stake=f"R1 {pl['ca3_r1']:g} and z 234 joint fatigue on knocked Z {pl['ca3_z_hw']:g} MPa",
             specimen=c["CA-3-HW"]["coupons"] + f"; Z bars ISO 527-2 1BA cut from the Z slab ({_job_txt('z')}), SBS bars from the blocks ({_job_txt('sbs')}, {_job_txt('sbs_pause')})",
             steps=steps("CA-3-HW"),
             pass_fail=(f"(a) hot/wet Z B-basis (mean - {pl['ca3_k']:g} SD) >= {pl['ca3_z_mpa']:g} MPa; (b) hot/wet SBS "
                        f"B-basis >= {pl['ca3_sbs_mpa']:g} MPa; (c) pause-layer SBS mean >= {pl['ca3_pause_frac']:g} x the "
                        f"no-pause hot/wet SBS mean and its B-basis >= {pl['ca3_sbs_mpa']:g} MPa; (d) record: uptake, "
                        f"hot/wet / dry Z (booked {pl['ca3_knock_booked']:g}). Below (a): R1 = {pl['ca3_r1_k']:g} x Z_m / "
                        f"{pl['ca3_z_ref']:g}, z 234 joint fatigue = {pl['ca3_joint_k']:g} x Z_m / {pl['ca3_z_ref']:g}; hold "
                        "the build and grow the hot spot by the shortfall"),
             cost_usd=f"{(kind_g('sbs') * 17 / 27 + kind_g('sbs_pause') + kind_g('z')) * up:.2f}",
             cost_basis="PPA-CF filament of the SBS blocks (share), the pause block and the Z slab, towers pro rata (record ppa_cf_fdm); rigs from kits A, B",
             hours_hands_on="8", hours_machine="336", phase="1", run_order="90", notes=rel + ". " + c["CA-3-HW"]["replaces"]),
        _row(id="CA-1-HW", title=f"PPA-CF short-beam-shear fatigue at {pl['ca1_temp_c']:g} C, conditioned, {pl['ca1_load_factor']:g} x Smax",
             defined_in=DEF + "; designs/pack_5200/tests_physical/CA1_fatigue_rig.md (rig)",
             what_it_proves=c["CA-1-HW"]["settles"], gates=gate, safety_at_stake=c["CA-1-HW"]["margin_tied"],
             specimen=c["CA-1-HW"]["coupons"], kit="B, D", steps=steps("CA-1-HW"),
             pass_fail=(f"all {int(pl['ca1_n_fat'])} SBS bars run out to {pl['ca1_cycles']:,.0f} cycles at Smax = "
                        f"{pl['ca1_smax_mpa']:g} MPa (peak {pl['ca1_peak_n']:g} N on the jig), R {pl['ca1_r']:g}, "
                        f"{pl['ca1_temp_c']:g} +/- {pl['ca1_temp_tol']:g} C; the {int(pl['ca1_n_static'])} static SBS >= the "
                        f"CA-3-HW SBS line {pl['ca3_sbs_mpa']:g} MPa"),
             cost_usd=f"{kind_g('sbs') * 10 / 27 * up:.2f}", cost_basis="PPA-CF filament of the SBS block (share); lever rig kit B",
             hours_hands_on="6", hours_machine=f"{pl['ca1_n_fat'] * pl['ca1_cycles'] / 3600:.0f}", run_order="91",
             notes=rel + ". " + c["CA-1-HW"]["replaces"]),
        _row(id="CA-4-HW", title="PPA-CF 3-point bend modulus at 23 C dry / 40 C conditioned / 60 C dry",
             what_it_proves=c["CA-4-HW"]["settles"], gates=gate + " (row (a) only)",
             safety_at_stake=f"buckling and the z 234 joint contact stiffness at E ratio {pl['ca4_e_booked']:g}",
             specimen=f"{int(pl['ca4_n'])} XY bend bars {FLEX['L']:.0f} x {FLEX['w']:.0f} x {FLEX['t']:.0f} per condition ({_job_txt('flex')})",
             steps=steps("CA-4-HW"),
             pass_fail=(f"(a) E(40 C conditioned) / E(23 C dry), mean of {int(pl['ca4_n'])}, >= {pl['ca4_e_ratio']:g}; "
                        f"(b) record: 60 C dry flexural strength mean - {pl['ca4_k']:g} SD >= {pl['ca4_flex60_mpa']:g} MPa"),
             cost_usd=f"{kind_g('flex') * up:.2f}", cost_basis="PPA-CF filament of the bend bars; 40 C box kit B",
             hours_hands_on="4", hours_machine="3", run_order="92", notes=rel + ". " + c["CA-4-HW"]["replaces"]),
        _row(id="T4c-PPA-HW", title=f"{FREEZER_C:.0f} C drop of {int(pl['t4c_n_ppa'])} H1-P stay coupons (z 0-{pl['t4c_z_max']:.0f}) at {pl['t4c_j']:g} J + cantilever bend",
             defined_in=DEF + "; designs/pack_5200/analysis/load_standard.md 5.3 (T4c)",
             what_it_proves=c["T4c-PPA-HW"]["settles"], gates=gate, safety_at_stake="cold impact on the stay foot (T4b energy)",
             specimen=c["T4c-PPA-HW"]["coupons"] + "; `designs/pack_5200/print/frame_h1p/test_pieces/t4c_stay_R.stl`",
             kit="A, D", steps=steps("T4c-PPA-HW"),
             pass_fail=(f"no crack or whitening (10x loupe, dye penetrant) after both drops, then the cantilever bend at "
                        f"{pl['t4c_p_n']:g} N ({pl['t4c_p_lbf']:g} lbf) at {pl['t4c_arm_mm']:g} mm ({pl['t4c_m_nm']:.1f} N m) "
                        "held 1 min without a crack"),
             cost_usd=f"{kind_g('stay') * up + 15:.2f}", cost_basis="PPA-CF filament of the stays + dye penetrant USD 15 (ASSUMPTION)",
             hours_hands_on="3", hours_machine=f"{pl['soak_h']:g}", run_order="93", notes=rel + ". " + c["T4c-PPA-HW"]["replaces"]),
        _row(id="T4c-PPA-CROWN", title=f"{FREEZER_C:.0f} C drop of {int(pl['crown_n_ppa'])} H1-P crown-corner coupons at {pl['crown_j']:g} J",
             what_it_proves=c["T4c-PPA-CROWN"]["settles"], gates=gate, safety_at_stake="cold impact on the crown / upper bar",
             specimen=c["T4c-PPA-CROWN"]["coupons"] + "; `designs/pack_5200/print/frame_h1p/test_pieces/crown_corner_R.stl`",
             kit="A, D", steps=steps("T4c-PPA-CROWN"), pass_fail=c["T4c-PPA-CROWN"]["pass"],
             cost_usd=f"{kind_g('crown') * up:.2f}", cost_basis="PPA-CF filament of the crown corners", hours_hands_on="2",
             hours_machine=f"{pl['soak_h']:g}", run_order="94", notes=rel + ". ASSUMPTION CROWN-CUT (the cut box)"),
        _row(id="CLEVIS-SHARE-B-PPA", title=f"US2 clevis outer-cheek share measured on H1-P PPA parts (loading B), pass <= {pl['share_max']:g}",
             defined_in=DEF_DEC + " 'US2 clevis joint fatigue (share 1.0)'; analysis/clevis_bl056.json kit B",
             what_it_proves=(f"the US2 clevis fatigue row: {pl['clevis_f_share1']:g} at share 1.0, goal {pl['clevis_goal']:g} "
                             f"reached at share <= {pl['share_max']:g} (fatigue ~ 1 / share; {pl['clevis_f_share06']:g} at 0.6)"),
             gates=gate, safety_at_stake="US2 cradle anchor fatigue (clevis cheek)",
             specimen=f"{_job_txt('us2')}: `test_pieces/us2_route_stay_R_h1p.stl` + `iter1/frame/h1p/us2_clevis_R.stl`, clevis hardware and US2 gauge as CLEVIS-SHARE",
             steps=steps("CLEVIS-SHARE-B-PPA"),
             pass_fail=(f"the largest of 3 measured shares (u - u0) / (u1 - u0) <= {pl['share_max']:g} (BL-076; without u0: "
                        f"u / u1 <= {share_gauge()['pass_ratio_no_u0']:g}); otherwise metal clevis hole sleeves (DECISIONS alt)"),
             cost_usd=f"{(kind_g('us2') + kind_g('clevis')) * up:.2f}", cost_basis="PPA-CF filament of the US2 piece and clevis; gauge set from CLEVIS-SHARE",
             hours_hands_on="3", run_order="95", notes=rel + ". ASSUMPTION SHARE-GAUGE"),
        _row(id="US2-LUG-PPA", title=f"US2 lug proof on H1-P PPA parts at x {pl['lug_factor']:g} the CLEVIS-SHARE B load, hot/wet, 40 C",
             defined_in=DEF_DEC + " 'US2 lug fatigue'; analysis/clevis_bl056.json kit B",
             what_it_proves=(f"US2 lug fatigue {pl['lug_margin']:g} on hot/wet (goal {pl['lug_goal']:g}): a proof at "
                             f"{pl['lug_goal']:g} / {pl['lug_margin']:g} = x {pl['lug_factor']:g} load"),
             gates=gate, safety_at_stake="US2 lug root fatigue",
             specimen="the CLEVIS-SHARE-B-PPA piece and clevis after its readings, conditioned", steps=steps("US2-LUG-PPA"),
             pass_fail=(f"proof {pl['lug_factor'] * cb['proof_n']:.0f} N 60 s and {cb['cycles']:,} cycles at "
                        f"{pl['lug_factor'] * cb['peak_n']:.0f} N (R {cb['R']:g}) at 40 C: the 0.05 mm feeler never enters "
                        "the joint face, no crack at the lug root, arm root, cheeks or bolt holes, gauge peak at the end "
                        "within 10 % of the 1e3 reading"),
             cost_usd="0", cost_basis="the CLEVIS-SHARE-B-PPA piece", hours_hands_on="4",
             hours_machine=f"{cb['cycles'] / 3600:.0f}", run_order="96", notes=rel + ". ASSUMPTION LUG-COND"),
        _row(id="T4b-PPA-COLD", title=f"P1 H1-P frame T4b set-down after {pl['soak_h']:g} h at {FREEZER_C:.0f} C ({pl['t4b_j']:g} J)",
             what_it_proves=c["T4b-PPA-COLD"]["settles"], gates="cold use of the PPA-CF frame (after the frame print)",
             safety_at_stake="COLD on both halves; hip preload gone at -20 C (CTE-Z), paint marks checked",
             specimen=c["T4b-PPA-COLD"]["coupons"], kit="C, A, D", steps=steps("T4b-PPA-COLD"),
             pass_fail=c["T4b-PPA-COLD"]["pass"] + "; hip paint marks unmoved", hours_hands_on="3", phase="4",
             run_order="97", notes="BL-074: after the frame print is released. " + c["T4b-PPA-COLD"]["replaces"]),
        _row(id="T4c-PPA-COLD", title=f"P1 empty-pack T4c drops after {pl['soak_h']:g} h at {FREEZER_C:.0f} C",
             what_it_proves=c["T4c-PPA-COLD"]["settles"], gates="cold use of the PPA-CF frame (after the frame print)",
             safety_at_stake="COLD on the upper half / crown", specimen=c["T4c-PPA-COLD"]["coupons"], kit="C, D",
             steps=steps("T4c-PPA-COLD"), pass_fail=c["T4c-PPA-COLD"]["pass"], hours_hands_on="3", phase="4",
             run_order="98", notes="BL-074: after the frame print is released. " + c["T4c-PPA-COLD"]["replaces"]),
        _row(id="HB-6-PPA", status="NOT-NEEDED", title="M5 heat-set insert pull-out in PPA-CF at 60 C (only if inserts replace the through-bolts)",
             defined_in="designs/pack_5200/iter1/frame/bl070_h1p.md section 4; bl070_h1p.json h1_ppa.hip_inserts",
             what_it_proves="INS-PPA", gates="none while the H1-P hip mount uses through-bolts (DECISIONS 2026-11-25)",
             safety_at_stake="insert hip mount on PPA (fails on design values)", specimen="PPA-CF insert blocks", kit="",
             steps="not run: the H1-P hip mount is 8 through-bolts on a 6061 bearing ring (BUILD_H1P section 5); HB-6b on the frame proves the mount",
             pass_fail=f"each >= {h1p_json()['h1_ppa']['hip_inserts']['hb6_ppa_min_static_n']:.0f} N along the build z at 60 C",
             cost_basis="not run", hours_hands_on="0", phase="-", notes=f"NOT NEEDED while through-bolts are used ({hip()['hardware']})"),
    ]
    old = coupons_bl070()
    po = pass_lines_bl070()
    for oid, new in SUPERSEDED.items():
        o = old[oid]
        note = f"SUPERSEDED by {new} (BL-073 coupons_bl073; BL-074). Kept for the record; not run"
        if oid == "CA-3-PPA":
            note += f". Corrected 'if below' band (review 8 m-4): {o['if_below_corrected']}"
        rows.append(_row(id=oid, status=f"SUPERSEDED->{new}", title=f"(BL-070) {o['what'][:90]}",
                         defined_in="designs/pack_5200/iter1/frame/bl070_h1p.json coupons (BL-070 record)",
                         what_it_proves=o["settles"], gates="none (superseded)", safety_at_stake=o.get("margin_tied", ""),
                         specimen=o["coupons"], kit="", steps="not run (superseded)", pass_fail=o["pass"],
                         cost_basis="not run", hours_hands_on="0", phase="-", notes=note))
    assert po["ca3_z_mpa"] > 0
    for r in rows:
        assert set(r) == set(REG_COLS), set(r) ^ set(REG_COLS)
    return rows


def results_items() -> dict:
    """Rows for outputs/release/test_kit/results_template.csv: (sample, quantity, unit, check, limit, settles)."""
    pl = pass_lines()
    cb = clevis_b()
    out = {}
    s73 = b73()["spool_plan"]["upper"]
    out["FA-H1P-UP"] = [
        ("slicer", "shortest layer time (preview)", "s", "record", "", "LAYER-H"),
        ("slicer", "median layer time (preview)", "s", "record", "", "LAYER-H"),
        ("plate", "largest gap under a pad foot or the brim", "mm", "max", "0.5", "PAD"),
        ("pads", "deepest scar after sanding", "mm", "max", "0.6", "PAD"),
        ("change", f"spool change at layer {s73['swap']['layer']}: minutes paused", "min", "max", "10", "SPOOL-RESERVE"),
        ("change", "chamber at resume", "C", "record", "", ""),
        ("filament", "filament used (spool weights before and after)", "g", "band",
         f"{0.9 * s73['filament_total_g']:.0f}..{1.1 * s73['filament_total_g']:.0f}", "SPOOL-RESERVE"),
        ("half", "mass, pads and supports off", "g", "band",
         f"{0.97 * h1p_json()['h1p']['export']['upper']['g_ppa']:.0f}..{1.04 * h1p_json()['h1p']['export']['upper']['g_ppa']:.0f}", ""),
    ]
    rows = []
    for setn, n, kind in (("hot/wet", int(pl["ca3_n_hw"]), "Z tensile"), ("hot/wet", int(pl["ca3_n_hw_sbs"]), "SBS"),
                          ("dry", int(pl["ca3_n_dry"]), "Z tensile"), ("dry", int(pl["ca3_n_dry_sbs"]), "SBS"),
                          ("pause", int(pl["ca3_n_pause"]), "SBS")):
        rows += [(f"{setn} {i}", f"{kind} strength, {setn}", "MPa", "record", "", "") for i in range(1, n + 1)]
    rows += [("hot/wet set", f"Z tensile B-basis (mean - {pl['ca3_k']:g} SD)", "MPa", "min", f"{pl['ca3_z_mpa']:g}", "WET-PPA; HOT-40; B-BASIS-N5"),
             ("hot/wet set", f"SBS B-basis (mean - {pl['ca3_k']:g} SD)", "MPa", "min", f"{pl['ca3_sbs_mpa']:g}", "INTERLAYER-0.6"),
             ("pause set", "pause SBS mean / no-pause hot/wet SBS mean", "ratio", "min", f"{pl['ca3_pause_frac']:g}", "pause layer"),
             ("pause set", f"pause SBS B-basis (mean - {b73()['basis']['k_n6']:g} SD)", "MPa", "min", f"{pl['ca3_sbs_mpa']:g}", "pause layer"),
             ("traveller", "water uptake at constant mass", "%", "record", "", "WET-PPA"),
             ("both sets", f"hot/wet / dry Z B-basis (booked {pl['ca3_knock_booked']:g})", "ratio", "record", "", "WET-PPA; HOT-40")]
    out["CA-3-HW"] = rows
    rows = [(f"static {i}", "SBS strength, hot/wet 40 C", "MPa", "min", f"{pl['ca3_sbs_mpa']:g}", "FAT-PPA") for i in range(1, int(pl["ca1_n_static"]) + 1)]
    rows += [(f"fatigue {i}", f"cycles reached at Smax {pl['ca1_smax_mpa']:g} MPa", "cycles", "min", f"{pl['ca1_cycles']:.0f}", "FAT-PPA")
             for i in range(1, int(pl["ca1_n_fat"]) + 1)]
    rows += [("40 C box", "thermometer during the runs", "C", "band",
              f"{pl['ca1_temp_c'] - pl['ca1_temp_tol']:g}..{pl['ca1_temp_c'] + pl['ca1_temp_tol']:g}", "HOT-40")]
    out["CA-1-HW"] = rows
    out["CA-4-HW"] = [
        ("23 C dry", "E mean", "MPa", "record", "", ""),
        ("40 C conditioned", "E(40 C conditioned) / E(23 C dry)", "ratio", "min", f"{pl['ca4_e_ratio']:g}", "E-HW"),
        ("60 C dry", f"flexural strength mean - {pl['ca4_k']:g} SD (record)", "MPa", "record", f"{pl['ca4_flex60_mpa']:g}", "E-HW"),
        ("60 C box", "thermometer reading during the 60 C tests", "C", "band", "58..62", "BOX-60"),
    ]
    rows = [("freezer", "thermometer at the end of the soak", "C", "max", f"{pl['soak_c']:g}", "COLD")]
    for i in range(1, int(pl["t4c_n_ppa"]) + 1):
        rows += [(f"PPA stay {i}", "foot-first drop: no crack, no whitening, dye clean", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA stay {i}", "side-on drop: no crack, no whitening, dye clean", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA stay {i}", f"cantilever bend {pl['t4c_p_n']:g} N at {pl['t4c_arm_mm']:g} mm, 1 min: no crack", "Y/N", "yes", "Y", "COLD")]
    rows += [("PAHT control", "both drops and the bend (record)", "Y/N", "record", "", "")]
    out["T4c-PPA-HW"] = rows
    rows = [("freezer", "thermometer at the end of the soak", "C", "max", f"{pl['soak_c']:g}", "COLD")]
    for i in range(1, int(pl["crown_n_ppa"]) + 1):
        rows += [(f"PPA crown {i}", "corner-first drop: no crack, no whitening", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA crown {i}", "side-on drop: no crack, no whitening", "Y/N", "yes", "Y", "COLD"),
                 (f"PPA crown {i}", "pawl still locks on the rack", "Y/N", "yes", "Y", "COLD")]
    rows += [("PAHT control", "drops (record)", "Y/N", "record", "", "")]
    out["T4c-PPA-CROWN"] = rows
    rows = []
    for i in range(1, 4):
        sg = share_gauge()
        rows += [(f"set {i}", f"u1, shim on the outer cheek, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE"),
                 (f"set {i}", f"u0, shim on the inner cheek, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE"),
                 (f"set {i}", "u0 / u1 (gauge on its site)", "ratio", "band",
                  f"{sg['u0_over_u1_expected'][0]:g}..{sg['u0_over_u1_expected'][1]:g}", "SHARE-GAUGE"),
                 (f"set {i}", f"u, as built, {cb['peak_n']:.0f} N", "microstrain", "record", "", "SHARE-GAUGE")]
    rows += [("all sets", "largest share (u - u0) / (u1 - u0)", "ratio", "max", f"{pl['share_max']:g}", "US2 clevis fatigue (share)")]
    out["CLEVIS-SHARE-B-PPA"] = rows
    out["US2-LUG-PPA"] = [
        ("traveller", "uptake at the test (days conditioned in the notes)", "%", "record", "", "LUG-COND"),
        ("proof", f"feeler at {pl['lug_factor'] * cb['proof_n']:.0f} N, 60 s: does not enter", "Y/N", "yes", "Y", "US2 lug fatigue"),
        ("cycles", f"cycles reached at {pl['lug_factor'] * cb['peak_n']:.0f} N", "cycles", "min", f"{cb['cycles']}", "US2 lug fatigue"),
        ("end", "no crack (loupe) at the lug root, arm root, cheeks, bolt holes", "Y/N", "yes", "Y", "US2 lug fatigue"),
        ("end", "gauge peak at the end / at 1e3", "ratio", "band", "0.9..1.1", "US2 lug fatigue"),
    ]
    out["T4b-PPA-COLD"] = [("freezer", "thermometer at the end of the soak", "C", "max", f"{pl['soak_c']:g}", "COLD"),
                           ("P1", "HA-LS-1 T4b rule + no crack along a layer", "Y/N", "yes", "Y", "COLD"),
                           ("P1", "hip paint marks unmoved", "Y/N", "yes", "Y", "CTE-Z")]
    out["T4c-PPA-COLD"] = [("freezer", "thermometer at the end of the soak", "C", "max", f"{pl['soak_c']:g}", "COLD"),
                           ("P1", "HA-LS-1 T4c rule; no crack at the crown corners, pawl housing, upper bar", "Y/N", "yes", "Y", "COLD")]
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
    spl = spool_plan()
    hm = hip()
    A = "ASSUMPTION (shop price, check at purchase)"
    n = spl["spools"]
    L = [
        BOMLine("filament", f"Bambu PPA-CF 1.75 mm, 0.75 kg spool: first-article upper half, coupon jobs A-F, both frame halves ({n} spools, SPOOL_PLAN.csv)",
                "ppa_cf_fdm", n, "spool", round(100 * WASTE, 1), sp["usd"], round(n * sp["usd"], 2), kit="FRAME",
                source=sp["basis"],
                notes=(f"first article {spl['fa_g']:.0f} g + coupons {spl['coupons_g']:.0f} g + halves {spl['halves_g']:.0f} g = "
                       f"{spl['total_g']:.0f} g; BL-073 booked {spl['booked_bl073']} (see FOUND); {spl['before_gate']} spools before the gate"),
                proto_qty=n),
        BOMLine("hip mount", f"HW-HIP-SCR-P: {hm['screw']}", "ti_6al_4v", hm["n"] + 1, "each", 0.0, 3.00,
                round((hm["n"] + 1) * 3.00, 2), kit="FRAME", source=A + " (as the kit's Ti DIN 7984 lines)",
                notes=f"{hm['n']} + 1 spare; replaces BL-071's M5 x 20", proto_qty=hm["n"] + 1),
        BOMLine("hip mount", f"HW-HIP-NUT-P: {hm['nut']}", "sst_304_annealed", hm["n"] + 2, "each", 0.0, 0.10,
                round((hm["n"] + 2) * 0.10, 2), kit="FRAME", source=A,
                notes="NOT ISO 4032 (4.4-4.7 mm thick); caliper each <= 4.1 mm", proto_qty=hm["n"] + 2),
        BOMLine("hip mount", (f"HW-HIP-RING: bearing plates (BL-076), 6061-T6 {hm['ring']['t_mm']:g} mm "
                              f"({hm['ring']['t_mm'] / IN:.3f} in), {hm['ring'].get('outline', 'ring')} "
                              f"({hm['ring']['id_mm']:g} / {hm['ring']['od_mm']:g} mm), {hm['ring']['holes']}, laser cut from `{hm['files'][0]}`"),
                "alu_6061_t6", 2 * ring_pieces(hm), "each", 0.0, RING_SOURCE["usd_each"],
                round(2 * ring_pieces(hm) * RING_SOURCE["usd_each"], 2), kit="FRAME",
                source=f"{RING_SOURCE['service']}, {RING_SOURCE['url']} ({RING_SOURCE['read']}); {RING_SOURCE['price']}",
                notes=f"{ring_pieces(hm)} per frame + {ring_pieces(hm)} spare, {hm['ring']['g']:g} g per frame set. "
                      f"Fallback: {RING_SOURCE['fallback']}", proto_qty=2 * ring_pieces(hm)),
        BOMLine("hip mount", f"HW-HIP-KEEP: printed PPA-CF nut keeper `{hm['files'][2]}` (3 mm, 2 pockets)", "ppa_cf_fdm",
                2, "each", 0.0, 0.0, 0.0, kit="FRAME", source=f"printed on coupon {_job_txt('keeper')} (filament in the spool line)",
                notes=f"1 + 1 spare, {hm['keeper_g']:.2f} g; non-structural", proto_qty=2),
        BOMLine("hip mount", "Loctite 243 medium-strength threadlocker, 10 ml", "", 1, "bottle", 0.0, 9.00, 9.00,
                kit="FRAME", source=A, notes="one drop per screw, on the screw thread only (keep it off the print)"),
        BOMLine("tools", TORQUE_DRIVER["item"], "", 1, "each", 0.0, TORQUE_DRIVER["usd"], TORQUE_DRIVER["usd"],
                kit="TOOL (one-time)", source=TORQUE_DRIVER["source"],
                notes=f"set to {hm['torque']:g} N m ({hm['torque_inlbf']:.1f} in lbf): inside 0.3-1.2, +/-6 %; the PAHT path's 0.5-2.5 N m driver cannot be trusted at its bottom end"),
        BOMLine("tools", "3 mm hex bit, 1/4 in hex shank, 50 mm (e.g. Wera 840/1 Z 3.0)", "", 1, "each", 0.0, 4.00, 4.00,
                kit="TOOL", source=A, notes="turns the hip screws from the mount side; the nuts sit in the keeper"),
        BOMLine("tools", "flush cutters (Xuron 170-II type)", "", 1, "each", 0.0, 10.00, 10.00, kit="TOOL", source=A,
                notes="snap-off pads (PRINT_SHEET_H2S section 4)"),
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
    spl = spool_plan()
    sp = spool()
    fil = sum(x.cost_usd for x in b if x.section == "filament")
    hw = bom_cost(b, ["hip mount"])
    tools = sum(x.cost_usd for x in b if x.section == "tools")
    dryer = sum(x.cost_usd for x in b if x.item == DRYER["item"])
    halves = 4 * sp["usd"]          # a later frame: 2 halves x (start + change spool)
    return {"filament_usd": round(fil, 2), "spools": spl["spools"], "booked_bl073": spl["booked_bl073"],
            "booked_bl073_usd": round(spl["booked_bl073"] * sp["usd"], 2),
            "hip_hw_usd": round(hw, 2), "dryer_usd": round(dryer, 2), "tools_usd": round(tools, 2),
            "per_frame_usd": round(halves + hw, 2), "first_frame_all_usd": round(fil + hw + tools, 2)}


# ============================================================================ documents
ASSUMPTIONS = {
    "SPARE": ("One spare per coupon set.", "coupon print"),
    "CUT": (f"Bars are sawn from the blocks with {KERF:g} mm between them and a {TRIM:g} mm edge strip trimmed off every "
            "block side (the outer walls are not tested); 1BA bars are filed to a printed template.", "first coupon cut"),
    "TOWER": (f"Each coupon plate carries a stepped dummy tower sized by the BL-053 rule (8 mm3/s x 1.08 at 0.3 mm) so "
              f"every layer reaches the frame-half median layer time; at least 15 x 15 mm on every plate. The slicer's "
              "layer-time view is the check.", "the slicer preview of each job (logged)"),
    "CROWN-CUT": (f"Crown-corner coupon = H1-P frame x >= {CROWN_CUT['x_min']:g}, z >= {CROWN_CUT['z_min']:g} mm: the R "
                  "crown corner, the pawl housing on the spine (x 0) and the upper bar between them.", "engineer review of the cut"),
    "BOX-ON-RIG": ("The 40 C box (cooler, 60 W heater, thermostat) fits round the lever rig's coupon station with the link "
                   "through a slot in its lid; the coupon holds 40 +/- 2 C.", "the thermometer row in the results sheet"),
    "BOX-60": ("The 40 C box holds 60 C for the CA-4-HW 60 C set.", "the thermometer row in the results sheet"),
    "FREEZER": ("A chest freezer on its coldest setting reaches -20 C; a home upright freezer often holds only -18 C.",
                "the thermometer row in the results sheet"),
    "SHARE-GAUGE": ("The US2 gauge reading is linear in the outer-cheek share at the B peak load (BL-076 checked it on the "
                    "H1-P voxel model: inner cheek only, outer cheek only and both superpose) but it is NOT proportional: "
                    "at share 0 it still reads about 0.43 of the share-1 reading (the inner cheek's load bends the arm root "
                    "too), so share = (u - u0) / (u1 - u0) with u0 the reading with the shim on the inner cheek.",
                    "the u0 / u1 band check in the CLEVIS-SHARE-B-PPA readings (bl070_h1p.json bl076.share_gauge)"),
    "LUG-COND": ("The US2 piece is thick: it is conditioned with the coupons to constant mass or 28 days, whichever comes "
                 "first, and tested at 40 C; the uptake is written down.", "engineer review of the uptake"),
    "RING-PRICE": (RING_SOURCE["price"].split(": ", 1)[1], "the SendCutSend instant quote"),
    "PAUSE-HEAT": ("During a Bambu Studio pause the H2S keeps the bed and the chamber heater on; the chamber is read before "
                   "Resume.", "first article (the chamber reading at resume)"),
    "PAHT-STOCK": ("The PAHT-CF controls (the PAHT-CF job) come from the PAHT-CF spool of the fallback path.", "coupon print"),
    "FAN": ("Part cooling for PPA-CF as the PAHT-CF profile (<= 30 %), off below z 3 mm (BL-070 WARP).", "first article"),
}


def _gt(x: float) -> str:
    return f"{x:,.1f} g ({x / OZ:.1f} oz)"


def hold_block() -> list[str]:
    return [f"> **{HOLD}.** The H1-P frame halves stay on hold until all three are true: {gate_txt()}. "
            "The engineer writes PASS against each in the results sheet, then the frame halves may be printed "
            "(DECISIONS 2026-11-25).", ">",
            f"> **{RELEASED}** (COUPONS_H1P.md section 2).", ""]


def coupons_md(cp: dict, spl: dict) -> str:
    pl = pass_lines()
    st = guide_steps()
    reg = {r["id"]: r for r in register_rows()}
    rk = rig_check()
    L = ["# COUPONS_H1P: the first article, the BL-073 coupons and the frame-print gate", "",
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, manufacturing-engineer, {DATE}). **Do not edit "
         "by hand: re-run the script.** Every pass line is read from `designs/pack_5200/iter1/frame/bl070_h1p.json` "
         "(`coupons_bl073`, BL-073 hot/wet B-basis) when this file is generated. Metric first, imperial in brackets.", "",
         "This is the PPA-CF path (frame H1-P). The PAHT-CF H1 path (`designs/pack_5200/print/frame_h1/BUILD_H1.md`) "
         "is still the fallback and is unchanged.", ""] + hold_block() + [
         "## 1. The gate (read this first)", "",
         f"1. **First:** print the first-article upper half (FA-H1P-UP, section 4) from spools 1 and 2, before any "
         "coupon job.",
         f"2. **Then** print coupon jobs A to F in PPA-CF (and G in PAHT-CF), each beside its dummy tower so every layer "
         f"takes >= **{pl['layer_s']:.0f} s** (the frame-half median, BL-073).",
         f"3. **The frame halves wait** for: CA-3-HW (a) hot/wet Z B-basis >= **{pl['ca3_z_mpa']:g} MPa**, (b) SBS B-basis "
         f">= **{pl['ca3_sbs_mpa']:g} MPa**, (c) pause layer; CA-1-HW all {int(pl['ca1_n_fat'])} run out at "
         f"{pl['ca1_smax_mpa']:g} MPa, {pl['ca1_temp_c']:g} C; CA-4-HW E ratio >= **{pl['ca4_e_ratio']:g}**; T4c-PPA-HW and "
         f"T4c-PPA-CROWN clean; **US2-LUG-PPA** at x {pl['lug_factor']:g} load; **CLEVIS-SHARE-B-PPA** share <= "
         f"**{pl['share_max']:g}**.",
         f"4. If CA-3-HW (a) reads below the line with a measured B-basis Z_m: R1 = {pl['ca3_r1_k']:g} x Z_m / "
         f"{pl['ca3_z_ref']:g} and z 234 joint fatigue = {pl['ca3_joint_k']:g} x Z_m / {pl['ca3_z_ref']:g} (BL-073 "
         "LINEAR-Z): the build stays on hold and the engineer grows the hot spot by the shortfall.",
         f"5. If CLEVIS-SHARE-B-PPA reads above {pl['share_max']:g}: the DECISIONS alternative (metal clevis hole sleeves) "
         "comes in before the frame print.",
         "6. T4b-PPA-COLD and T4c-PPA-COLD run on the P1 frame after the print and gate cold use, not the print.", "",
         "Calendar: first article about 1 day; coupon jobs about 3 days; conditioning to constant mass about 2 weeks "
         "(ASSUMPTION); CA-3-HW 2 days; CA-1-HW 6 x 28 h on the lever rig, then US2-LUG-PPA about 28 h. About **5 "
         "weeks** from the first article to the frame print.", "",
         "## 2. Coupon jobs (every one beside a dummy tower)", "",
         f"Print with the frame settings of PRINT_SHEET_H2S.md section 1 (0.6 nozzle, {pl['layer_h']:g} mm layers, 6 walls, "
         "100 % infill, 30 min chamber pre-heat), same printer, same spool lot. The tower is the job's own STL "
         f"(`test_pieces/tower_<job>.stl`), placed 10 mm from the parts. The plate needs {cp['area_req_mm2']:,.0f} mm2 "
         f"per layer to take {pl['layer_s']:.0f} s by the BL-053 rule; the tower adds what the parts lack, band by band. "
         "**Check:** the slicer's layer-time view shows no layer under the line; write the shortest layer time of each "
         "job in the results sheet. If one is short, scale the tower up in x and y until none is.", "",
         "| job | prints | material | layers | tower max mm2 | parts g | supports g | tower g | filament + 8 % | about h | shortest layer s (rule) |",
         "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for j in cp["jobs"]:
        its = "; ".join(f"{it['count']} x {it['name']}" for it in j["items"])
        if j["pause"]:
            its += f". **{j['pause']}**"
        L.append(f"| {j['job']} | {its} | {j['mat']} | {j['layers']} | {j['tower_max_mm2']:,.0f} | {j['parts_g']:.0f} | "
                 f"{j['support_g']:.0f} | {j['tower_g']:.0f} | {j['filament_g']:.0f} g | {j['print_h']:.1f} | {j['min_layer_s']:.0f} |")
    L += [f"| | **PPA-CF coupons** | | | | | | | **{cp['ppa_filament_g']:.0f} g ({cp['ppa_filament_g'] / OZ:.0f} oz)** | **{cp['print_h']:.0f}** | |",
          "",
          f"- Blocks: A and B are {blocks()['sbs']['h']:.1f} mm ({blocks()['sbs']['layers']} layers) tall; the bars are "
          f"faced {FACE:g} mm each side to {pl['ca1_sbs_t']:g} mm, so the shear mid-plane is the line between layers "
          f"{blocks()['sbs']['mid_layer_line']} and {blocks()['sbs']['mid_layer_line'] + 1}. Block B pauses there "
          f"for {pl['ca3_pause_min']:.0f} min (Bambu Studio: PRINT_SHEET_H2S.md section 3).",
          "- Each conditioned set carries a traveller: a 60 x 60 mm plate of the block's thickness printed in the same job "
          "(weighed on the 0.001 g scale).",
          "- Supports: tree supports from the plate on jobs D, E, F as the frame halves; none on A, B, C.", "",
          "### Spools (in print order)", "",
          f"A half starts on a spool that holds its pre-change use plus the {spl['reserve_g']:.0f} g reserve and changes at "
          "its planned layer to a FULL spool; a coupon job never changes spool mid-print (a pause layer would sit in the "
          "coupons).", "",
          "| spool | feeds | left g |", "|---:|---|---:|"] + [f"| {r['spool']} | {r['uses']} | {r['left_g']:.0f} |" for r in spl["rows"]] + [
          "",
          f"**{spl['spools']} spools** ({spl['before_gate']} before the gate). "
          + (f"BL-073 booked {spl['booked_bl073']}: see BUILD_H1P.md FOUND." if spl['booked_bl073'] != spl['spools'] else
             f"bl070_h1p.md books the same {spl['booked_bl073']} (BL-076 reads this plan); "
             f"{spl['spools'] - len([r for r in spl['rows'] if r['uses'].startswith('frame upper half')])} if the first-article "
             "upper half becomes the frame's upper half (orchestrator call)."), "",
          "## 3. Rig loads: everything stays under the 100 kg cell", "",
          "| load | N | lbf | under the cell |", "|---|---:|---:|---|"]
    for k, v in rk["loads"].items():
        L.append(f"| {re.sub(r'_n$', '', k).replace('_', ' ')} | {v:,.0f} | {v / N_PER_LBF:,.0f} | {'yes' if v <= rk['cell_n'] else '**NO**'} |")
    L += ["", f"Cell {rk['cell_n']:.0f} N (100 kg). All under: **{rk['all_under_cell']}**. "
          + ("The 200 kg cell and the second lever bar BL-071 added for the XY tension pulls are no longer needed and are "
             "off the shopping list." if rk["all_under_cell"] else "A load is over the cell: keep the 200 kg cell."), ""]
    titles = list(ACTIVE_IDS)
    for i, t in enumerate(titles, 4):
        r = reg[t]
        L += [f"## {i}. {t}: {r['title']}", "", f"**Why:** {r['what_it_proves']}. **Holds:** {r['gates']}.  ",
              f"**You need:** {r['specimen']}.", "", "**Steps**", ""]
        L += [f"{k}. {s}" for k, s in enumerate(st[t], 1)]
        L += ["", f"**Pass:** {r['pass_fail']}.", ""]
        if r["notes"]:
            L += [f"Note: {r['notes']}.", ""]
    n = 4 + len(titles)
    L += [f"## {n}. Superseded BL-070 rows (kept in the register, not run)", "",
          "| BL-070 row | replaced by | BL-070 pass line (record) |", "|---|---|---|"]
    for oid, new in SUPERSEDED.items():
        L.append(f"| {oid} | {new} | {reg[oid]['pass_fail'][:160]} |")
    L += ["", f"CA-3-PPA corrected 'if below' band (review 8 m-4, kept for the record): "
          f"{coupons_bl070()['CA-3-PPA']['if_below_corrected']}", "",
          f"## {n + 1}. HB-6-PPA: not needed", "", f"{reg['HB-6-PPA']['title']}. **{reg['HB-6-PPA']['status']}.** "
          f"{reg['HB-6-PPA']['notes']}.", "",
          "## ASSUMPTIONS used on these sheets", ""]
    L += [f"- **{k}**: {v[0]} Settled by: {v[1]}." for k, v in ASSUMPTIONS.items()
          if k in ("SPARE", "CUT", "TOWER", "CROWN-CUT", "BOX-ON-RIG", "BOX-60", "FREEZER", "SHARE-GAUGE", "LUG-COND", "PAHT-STOCK")]
    L += ["- BL-073: " + ", ".join(a["id"] for a in h1p_json()["assumptions_bl073"]) + " (bl070_h1p.json `assumptions_bl073`).", ""]
    return "\n".join(L)


PAUSE_SOURCE = ("Bambu Lab wiki 'View slicing information' (custom operations per layer: pause, filament change; "
                "https://wiki.bambulab.com/en/software/bambu-studio/view-slicing-information); Bambu forum 'Filament change "
                "without AMS mid-print' and 'Is there a way to Pause at layer X to manually change filament?' (right-click "
                "the layer slider in Preview, Add Pause; without an AMS use Add Pause, not Change Filament; "
                "https://forum.bambulab.com/t/filament-change-without-ams-mid-print/2589 , "
                "https://forum.bambulab.com/t/is-there-a-way-to-pause-at-layer-x-to-manually-change-filament/3005)")


def print_sheet() -> dict:
    """The H2S settings for H1-P, each with its source."""
    p = ppa()["properties"]
    d = h1p_json()
    pr = d["h1p"]["print"]
    orient = d["h1p"]["orientation"]["fine_sm8.cyc"]
    sp = spool()
    pl = pass_lines()
    rec = "record `data/materials/polymers/ppa_cf_fdm.yaml`"
    tds = "Bambu PPA-CF TDS V1.0 (cited in the record)"
    w = {a["id"]: a for a in d["assumptions"]}
    pf = b73()["print_files"]
    rows = [
        ("filament", "Bambu PPA-CF, 1.75 mm, 0.75 kg spool (not AMS compatible: fed from the external spool holder)", f"{rec} (trade name, {sp['basis']}); record source 'BL-073 spool'"),
        ("dryer", "forced-air oven that HOLDS 120 C (248 F) or more", f"DECISIONS 2026-11-25 ('a dryer that holds >= 120 C'); {tds}: dry 100-140 C 8-12 h in a forced-air (blast) oven"),
        ("drying", f"{p['drying_temp_c']} C ({p['drying_temp_c'] * 9 / 5 + 32:.0f} F) for {p['drying_time_hours']} h, then a dry box < 20 % RH for the whole print", f"{rec} drying_temp_c / drying_time_hours; bl070_h1p.md BL-073 printability (m-5: 120 C is under the cardboard spool's 145 C)"),
        ("nozzle", f"hardened steel {p['nozzle_diameter_mm']} mm, {p['nozzle_temp_c']} C ({p['nozzle_temp_c'] * 9 / 5 + 32:.0f} F)", f"{rec} nozzle_temp_c / nozzle_diameter_mm; {tds}: 280-310 C, 0.6 recommended, hardened"),
        ("bed", f"{p['bed_temp_c']} C ({p['bed_temp_c'] * 9 / 5 + 32:.0f} F), textured PEI + glue stick", f"{rec} bed_temp_c; {tds}: 100-120 C, glue"),
        ("chamber", f"{p['chamber_temp_c']} C ({p['chamber_temp_c'] * 9 / 5 + 32:.0f} F), chamber heater on", f"{rec} chamber_temp_c (the H2S maximum); {tds}: 50-80 C"),
        ("chamber pre-heat", "30 min at 65 C with the plate in, BEFORE the print starts", f"bl070_h1p.json ASSUMPTION WARP: {w['WARP']['text']}"),
        ("brim", "15 mm (0.59 in), around the part and the pad feet", "bl070_h1p.json ASSUMPTION WARP / bl070_h1p.md section 3"),
        ("snap-off pads", f"in the print file: lower {pf['lower']['n_pads']} pads, upper {pf['upper']['n_pads']} pads (D24 x 0.6 foot, D12 column, D6 -> D3 neck); plate contact lower {pf['lower']['plate_contact_part_mm2']:.0f} -> {pf['lower']['plate_contact_with_pads_mm2']:.0f} mm2, upper {pf['upper']['plate_contact_part_mm2']:.0f} -> {pf['upper']['plate_contact_with_pads_mm2']:.0f} mm2", f"bl070_h1p.json bl073.print_files; ASSUMPTION PAD: {assumption_73('PAD')['text']}"),
        ("part cooling", "off for the first 3 mm (0.12 in) of height; then <= 30 %, aux fan off", "bl070_h1p.md section 3 (WARP); above it ASSUMPTION FAN (the PAHT-CF profile)"),
        ("layers / walls / infill", f"{pl['layer_h']:.2f} mm (Bambu Studio '0.30mm Standard' for the 0.6 nozzle) / 6 walls / 6 top-bottom / 100 % infill", f"bl070_h1p.json ASSUMPTION LAYER-H ({assumption_73('LAYER-H')['text']}): the change layers and the coupon layer time rest on it; walls / infill {BUILD_H1} section 3"),
        ("speed", "outer walls and the default profile <= 100 mm/s", "bl070_h1p.json ASSUMPTION PPA-TIME ('TDS speed < 100 mm/s')"),
        ("orientation", "BOTH halves face down (wearer face on the plate) exactly as written in the STL; do not rotate", f"bl070_h1p.json h1p.orientation (fine_sm8.cyc): R1 {orient[FACE_DOWN]['fatigue']:.3f} face down vs {min(v['fatigue'] for k, v in orient.items() if k != FACE_DOWN):.3f}-{max(v['fatigue'] for k, v in orient.items() if k != FACE_DOWN):.3f} on an edge or end"),
        ("supports", "tree supports in PPA-CF from the build plate, as BUILD_H1 section 3 (same areas)", "bl070_h1p.md section 3; BL-069 section 5 (PA/PET interface not recommended)"),
        ("filament change", "ONE planned change per half at the layer of section 2 (Preview, right-click the layer slider, Add Pause)", PAUSE_SOURCE),
        ("anneal", "NO. Do not anneal the halves", f"BL-069 section 5 / {tds}: anneal may warp and cut toughness; no annealing credit taken"),
    ]
    halves = []
    for h in ("lower", "upper"):
        q = pr[h]
        s = b73()["spool_plan"][h]
        halves.append({"half": h, "file": f"designs/pack_5200/iter1/frame/h1p/h1_{h}_flat_print.stl",
                       "clean": f"designs/pack_5200/iter1/frame/h1p/h1_{h}_flat.stl",
                       "filament_g": s["filament_total_g"], "spools": s["spools"], "swap": s["swap"],
                       "print_h": q["print_h_est"], "contact_mm2": pf[h]["plate_contact_with_pads_mm2"],
                       "contact_part_mm2": pf[h]["plate_contact_part_mm2"], "pads": pf[h]["n_pads"], "pad_g": pf[h]["pad_g"],
                       "fits": q["fits_h2s_340x320x340"], "part_g": q["part_g_ppa"],
                       "swap_after_h": q["print_h_est"] * s["swap"]["print_z_mm"] / q["extents_mm"][2]})
    return {"rows": rows, "halves": halves}


def print_sheet_md(ps: dict) -> str:
    pl = pass_lines()
    L = ["# PRINT_SHEET_H2S: printing the H1-P halves in PPA-CF on the Bambu H2S", ""] + hold_block() + [
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, {DATE}). Every value has its source in the last "
         "column. The settings of section 1 apply to the first-article upper half and every PPA-CF coupon job now.", "",
         "## 1. Settings (both halves, the clevises and every PPA-CF coupon)", "",
         "| setting | value | source |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in ps["rows"]]
    L += ["", "## 2. The two halves: files, pads, the planned filament change", "",
          "| half | print this file | pads (g) | plate contact | filament | spools | change at print z | layer | time to the change | print time |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for h in ps["halves"]:
        s = h["swap"]
        L.append(f"| {h['half']} | `{h['file']}` | {h['pads']} ({h['pad_g']:g} g) | {h['contact_part_mm2']:.0f} -> **{h['contact_mm2']:.0f} mm2** | "
                 f"{_gt(h['filament_g'])} | {h['spools']:.2f} | **{s['print_z_mm']:.2f} mm ({s['print_z_mm'] / IN:.2f} in)** | "
                 f"**{s['layer']}** | about {h['swap_after_h']:.1f} h | {h['print_h']:.1f} h |")
    L += ["", "The change layer is BL-073's least-stressed layer plane inside the window where the first spool still has "
          f"its {pl['spool_reserve_g']:.0f} g reserve and the second can finish (hot/wet fatigue use in that plane: lower max "
          f"{ps['halves'][0]['swap']['fat_u_max']:g}, upper {ps['halves'][1]['swap']['fat_u_max']:g}). The clean "
          "`h1_<half>_flat.stl` files stay the geometry of record; print the `_flat_print.stl` files. Time to the change: "
          "print time x change z / part height (ASSUMPTION, the slicer shows the real time).", "",
          "## 3. Adding the filament change in Bambu Studio (H2S, no AMS)", "",
          "1. Slice the half. Open the **Preview** tab.",
          f"2. Drag the vertical **layer slider** on the right to the layer number in section 2 (lower "
          f"**{ps['halves'][0]['swap']['layer']}**, upper **{ps['halves'][1]['swap']['layer']}** at {pl['layer_h']:g} mm layers). The slider label shows the layer number and its height; check the height "
          "reads the change z of section 2 within one layer.",
          "3. **Right-click** the slider handle and pick **Add Pause** (not 'Change Filament': that one is for an AMS). A "
          "marker appears on the slider. The printer pauses BEFORE it prints that layer.",
          "4. Slide off and back to the marker to check it sits on the right layer; re-slice if Bambu Studio asks.",
          "5. Send to the printer. Write the predicted time to the pause from the slicer's layer list.",
          f"Source: {PAUSE_SOURCE}.", "",
          "At the pause (be there before it): open the external spool holder only, not the door; cut the filament at "
          "the extruder inlet, pull it back, load the next dried spool through the dry-box tube until clean PPA-CF purges, "
          "check the chamber reads 65 C (149 F; ASSUMPTION PAUSE-HEAT), press Resume. **Within 10 minutes** "
          "(BL-073: CA-3-HW tests a 20 min pause layer, so 10 min has margin).", "",
          "## 4. Step by step, each half (after the gate) and the first-article upper half (now)", "",
          "1. Dry the two spools of SPOOL_PLAN for the half at 120 C for 10 h: the start spool and a FULL change spool.",
          "2. Clean the textured PEI plate with soap and water, dry it, glue stick over the whole footprint, the pad feet "
          "and the brim area.",
          "3. Slicer: load the half's `_flat_print.stl`. Do NOT rotate it. Settings of section 1, 15 mm brim. Supports: "
          "tree, from the plate. Do not add mouse ears: the pads are in the file. Slice.",
          "4. CHECK the preview: nothing outside the plate; every pad foot is on layer 1; filament and time within 10 % of "
          "section 2; no support inside a bore, pin hole or the 8 hip holes. Add the pause (section 3). Screenshot.",
          "5. Plate in, door shut, chamber heater on to 65 C, bed 110 C. **Wait 30 min** after the chamber reads 65 C.",
          "6. Feed from the start spool through the dry box. Start. Watch the first layer: every pad foot and the brim stuck.",
          "7. The change: section 3.",
          "8. When it finishes, leave it on the plate with the door shut until the chamber is below 40 C (104 F). Feeler "
          "gauge under each pad foot and the brim edge: write the largest gap. Then flex the plate off.",
          "9. **Pads off:** hold the part, put the flush cutters flat against the part at each neck (the D3 waist) and "
          "snip; or rock the column sideways until the neck snaps. Never lever against the part. Sand each scar flush "
          "with 180 then 320 grit on a block; no dent deeper than 0.6 mm (0.024 in).",
          "10. Supports off and clean-up as BUILD_H1 section 4. **No anneal**.",
          "11. CHECK the change layer with the 10x loupe all round: no gap, no blob you can catch a fingernail on. "
          "Photograph it.", "",
          "## ASSUMPTIONS", "",
          "- PPA-TIME, WARP: `bl070_h1p.json` assumptions; LAYER-H, PAD, SPOOL-RESERVE: `assumptions_bl073` (settled by the "
          "slicer preview and the first-article upper half).",
          f"- PAUSE-HEAT: {ASSUMPTIONS['PAUSE-HEAT'][0]} Settled by: {ASSUMPTIONS['PAUSE-HEAT'][1]}.",
          f"- FAN: {ASSUMPTIONS['FAN'][0]} Settled by: {ASSUMPTIONS['FAN'][1]}.", ""]
    return "\n".join(L)


BL075 = HERE / "iter1" / "system" / "bl075_hip_clearance.json"
BL075_MD = HERE / "iter1" / "system" / "bl075_hip_clearance.md"


@functools.lru_cache(maxsize=None)
def bl075() -> dict:
    """BL-075 hip clearance (pack-designer): the tail band, keeper play, the cord rule and the optional caps."""
    d = json.loads(BL075.read_text(encoding="utf-8"))
    pr = d["protrusion"]["standard"]["M5x35"]
    md = BL075_MD.read_text(encoding="utf-8")
    caps = next(v for k, v in d["fixes"].items() if "TPU" in k)
    return {"tail_min": math.floor(pr["min_proud_mm"] * 10 + 1e-6) / 10.0,
            "tail_max": math.ceil(pr["max_proud_mm"] * 10 - 1e-6) / 10.0,
            "keeper_play": d["frame"]["rim_lip"]["r_min_mm"] - d["stack"]["keeper"]["r"],
            "cord_x": _num(r"outboard of \|x\| (\d+)", md), "caps_g": caps["g"], "fix": d["fix"],
            "clears": all(d["clears"].values()),
            "src": "designs/pack_5200/iter1/system/bl075_hip_clearance.md / .json"}


def hip_steps(hm: dict) -> list[str]:
    c = bl075()
    return [
        f"CHECK the print: the D50 boss is solid (no nut traps); {hm['n']} D{hm['boss']['holes_d_mm']:g} holes go straight "
        f"through its {hm['boss']['depth_mm']:g} mm; the back is a flat D{hm['boss']['spot_face_d_mm']:g} spot face. A "
        f"{hm['boss']['holes_d_mm']:g} mm drill shank slides through each hole by hand; clear stringing by turning the drill in your fingers.",
        f"CHECK the {ring_pieces(hm)} bearing plates (HW-HIP-RING): flat on glass (no rock), burr-free (file and 320 grit), "
        f"{hm['ring']['t_mm']:g} mm ({hm['ring']['t_mm'] / IN:.3f} in) thick. Lay them on the boss back, one under each "
        "group of 4 holes, curved edges following the spot face: every plate hole shows a boss hole.",
        f"CHECK the nuts: caliper each **HW-HIP-NUT-P** <= {hm['nut_t'] + 0.1:.1f} mm thick (a thicker nut is ISO 4032: set it aside).",
        f"Keeper dry fit (BL-075): set the empty printed keeper in the D{hm['boss']['spot_face_d_mm']:g} spot face on the plates. "
        f"It has only about {c['keeper_play']:.2f} mm radial play inside the printed lip: if it binds, sand its outside edge "
        "(240 grit on a block, turning it evenly) until it drops in and sits flat. If it still binds after light sanding, "
        "STOP and flag it to the engineer: do not force it.",
        "Push the 8 nuts into the printed keeper's pockets, flats radial. Put the keeper on the plates (pockets over the "
        "holes), the plates on the boss back. Tape the keeper to the boss with masking tape at two edges.",
        f"Turn the frame wearer face up. Lay the Ti mount on the boss face: its {hm['n']} holes over the boss holes.",
        "One drop of Loctite 243 on the last 5 mm of each **HW-HIP-SCR-P** (M5 x 35) thread. Keep it off the print.",
        "Start every screw by hand through the mount, the boss and the plate into its nut, turning with the 3 mm hex bit; "
        "if one does not catch, back it out, press the keeper flat, try again. Never force it.",
        f"Set the Wera 7440 to **{hm['torque']:g} N m ({hm['torque_inlbf']:.1f} in lbf)**. Tighten in a star order "
        "(1-5-3-7-2-6-4-8), then go round again at the same setting: stop at the first click each time.",
        f"CALIPER CHECK on all 8 screw tails (BL-075): the thread sticking out past each nut must read "
        f"**{c['tail_min']:g}-{c['tail_max']:g} mm** ({c['tail_min'] / IN:.3f}-{c['tail_max'] / IN:.3f} in), at least "
        f"{hm['threads_min']} full threads (nominal {hm['protrusion_mm']:g} mm = {hm['protrusion_threads']:g} threads). Write "
        "all 8. Outside the band: wrong screw, a nut or the keeper not seated, or a thick nut: stop.",
        f"CHECK seating: push the mount's pin end with the spring scale to {MOUNT_SEAT_N:.0f} N ({MOUNT_SEAT_N / G:.1f} kg, "
        f"{MOUNT_SEAT_N / N_PER_LBF:.1f} lb) up, down, left and right: a 0.05 mm (0.002 in) feeler does not enter under the base edge.",
        "Paint marks across every screw head and the mount, and across every nut, the keeper and the plates. Remove the "
        "tape. Let the Loctite cure 24 h before any load.",
        f"CORD RULE BL075-CORD: route the lumbar pad-seat bottom cord tie round the lower struts OUTBOARD of |x| "
        f"{c['cord_x']:g} mm ({c['cord_x'] / IN:.1f} in) each side of the frame centre. It must NEVER cross the back of the "
        "boss: there it would rub on the screw threads.",
        f"OPTIONAL: 8 TPU push-on caps on the screw tails (+{c['caps_g']:g} g). Fit them only if the T1 load test leaves "
        "a witness mark on the bag (B-01 inside face) or the spreader over the boss. No other hip hardware is added (BL-075).",
    ]


def build_md(cp: dict, spl: dict, ps: dict) -> str:
    d = h1p_json()
    hm = hip()
    b = bom()
    cs = cost()
    ex = d["h1p"]["export"]
    body = d["h1p"]["body_g"]
    lo_b, hi_b = body * 0.97, body * 1.04
    pat = hm["pattern"]
    jxy = d["h1p"]["z234_joint_xy"]
    pl = pass_lines()
    L = ["# BUILD_H1P: building the H1-P frame in PPA-CF (Pack 5200)", "",
         f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}, manufacturing-engineer, {DATE}). **Do not "
         "edit by hand: re-run the script.** Data: `designs/pack_5200/iter1/frame/bl070_h1p.json` (BL-070, BL-073) and "
         "the material records. Metric first, imperial in brackets.", "",
         f"H1-P (BL-073 p3) is the H1 frame re-tuned for Bambu PPA-CF on the hot/wet B-basis: {body:.1f} g "
         f"({body / LB_G:.2f} lb) printed body, +{d['h1p']['delta_vs_paht_h1_g']:.1f} g "
         f"(+{d['h1p']['delta_vs_paht_h1_g'] / OZ:.1f} oz) on the PAHT-CF H1, hip hardware +{b73()['mass']['hip_hardware_delta_vs_bl070_g']:g} g. "
         "**The PAHT-CF H1 (`../frame_h1/BUILD_H1.md`) stays the fallback.**", ""] + hold_block() + [
         "## 0. Read in this order", "",
         "1. `COUPONS_H1P.md`: the first-article upper half, then the coupon jobs, then the gate.",
         "2. This file, section 1 (shopping) and section 2 (what is different from BUILD_H1).",
         "3. `PRINT_SHEET_H2S.md`: printing the halves (pads, the planned filament change).",
         "4. This file, sections 3-6 (weigh, joints, hip mount, checks).", "",
         "## 1. Bill of materials and cost (the PPA path only; everything else is BUILD_H1 section 1)", "",
         "| section | item | qty | unit | USD each | USD | price source | note |", "|---|---|---:|---|---:|---:|---|---|"]
    for x in b:
        L.append(f"| {x.section} | {x.item} | {x.qty:g} | {x.unit} | {x.unit_cost_usd:.2f} | {x.cost_usd:.2f} | "
                 f"{x.source[:200]} | {x.notes} |")
    L += ["",
          f"- **Filament: {cs['spools']} spools, USD {cs['filament_usd']:.2f}** (first-article upper half, coupon jobs A-F, "
          f"both halves; SPOOL_PLAN in COUPONS_H1P.md section 2). "
          + (f"BL-073 booked {cs['booked_bl073']} (USD {cs['booked_bl073_usd']:.2f}): it does not close, see FOUND."
             if cs['booked_bl073'] != cs['spools'] else
             f"bl070_h1p.md books the same {cs['booked_bl073']} (BL-076)."),
          f"- Hip mount hardware: USD {cs['hip_hw_usd']:.2f}. A later frame (4 spools for two halves + hip hardware): "
          f"about USD {cs['per_frame_usd']:.0f}.",
          f"- One-time tools: dryer USD {cs['dryer_usd']:.2f}; all new tools USD {cs['tools_usd']:.2f}.",
          f"- First PPA frame, everything on this list: **USD {cs['first_frame_all_usd']:.2f}**.",
          "- Not on this list (as the PAHT path, BUILD_H1 section 1): z 234 joint and US2 clevis screws, nuts and washers, "
          "pins, sleeves, retainers, pawl, crown, the SLM Ti hip mount (HW-HIP-MNT).",
          "- **Removed on the PPA path:** HW-HIP-INS, HW-HIP-SCR (M5 x 12), HW-HIP-GUIDE, the insert tips, and BL-071's "
          "M5 x 20 in nut traps. The 200 kg cell and second lever bar are off the test-kit list (COUPONS_H1P.md section 3).", "",
          "## 2. What is different from BUILD_H1", "",
          "| BUILD_H1 section | on the PPA path |", "|---|---|",
          "| 2. gates | replaced: `COUPONS_H1P.md` section 1 (the BL-073 gate) |",
          "| 3. print settings | replaced: `PRINT_SHEET_H2S.md` (files `designs/pack_5200/iter1/frame/h1p/*_flat_print.stl`) |",
          "| 4. supports off, clean-up | same, after the pads are snapped off; lift the plate below 40 C |",
          "| 5. anneal | **deleted: do not anneal PPA-CF** |",
          "| 6. weigh | replaced: section 3 below |",
          "| 7. z 234 joint | same hardware, **new bolt positions** (section 4 below) |",
          "| 8-11. crown bores, pins, clevises, pawl | same steps, same hardware, H1-P halves |",
          f"| 12. hip mount (inserts) | **replaced: section 5 below (trap-free boss, bearing plates, {hm['torque']:g} N m)** |",
          "| 13 onward. crown, first-article checks | same; add section 6 below |", "",
          "## 3. Weigh (after pad and support removal, before reaming)", "",
          "| part | expected (STL x 1.25 g/cm3) |", "|---|---:|",
          f"| lower half | {_gt(ex['lower']['g_ppa'])} |", f"| upper half | {_gt(ex['upper']['g_ppa'])} |",
          f"| US2 clevis, each | {_gt((body - ex['lower']['g_ppa'] - ex['upper']['g_ppa']) / 2)} |",
          f"| body (halves + 2 clevises) | **{_gt(body)}** |", "",
          f"CHECK: the body reads **{lo_b:.0f} to {hi_b:.0f} g** ({lo_b / OZ:.1f}-{hi_b / OZ:.1f} oz), the BUILD_H1 MASS-BAND "
          "(-3 / +4 %). Lighter: wet filament or gaps; heavier: over-extrusion or pad stubs left on.", "",
          "## 4. z 234 joint: bolt positions (BL-073)", "",
          "Bolt the halves exactly as BUILD_H1 section 7: same M5 x 45 Ti screws, washers, DIN 934 nuts and torque. The "
          "holes are printed in the halves at the BL-073 positions below (local joint mm, `bl070_h1p.json` "
          "`h1p.z234_joint_xy`); BL-070's are shown so an old drawing is not used.", "",
          "| bolt | BL-073 (print these files) | BL-070 (superseded) | moved |", "|---|---:|---:|---:|"]
    for nm, a, o in zip(("outboard", "inboard"), jxy["bl073"], jxy["bl070"]):
        L.append(f"| {nm} | ({a[0]:+.1f}, {a[1]:+.1f}) | ({o[0]:+.1f}, {o[1]:+.1f}) | "
                 f"{math.hypot(a[0] - o[0], a[1] - o[1]):.1f} mm |")
    L += ["", "CHECK before bolting: a 5 mm drill shank passes each joint hole of both halves; the halves meet flat at "
          "the joint face with the two holes in line (a 5 mm pin goes through both).", "",
          "## 5. Hip mount: trap-free boss, bearing plates, nut keeper (replaces BUILD_H1 section 12)", "",
          f"Hardware (bl070_h1p.json `h1p.hip_mount`): {hm['hardware']}.", "",
          f"Stack: mount base {hm['flange_t']:.1f} + boss {hm['boss']['depth_mm']:g} + plate {hm['ring']['t_mm']:g} + nut "
          f"{hm['nut_t']:.1f} = {hm['stack']:g} mm; the M5 x {hm['screw_len']:g} screw stands {hm['protrusion_mm']:g} mm "
          f"= {hm['protrusion_threads']:g} threads proud. **Rule: at least {hm['threads_min']} full threads proud** "
          f"({hm['proud_min_mm']:.1f} mm).", "",
          f"**Torque: {hm['torque']:g} N m ({hm['torque_inlbf']:.1f} in lbf)** with the Wera 7440 (0.3-1.2 N m, +/-6 %) "
          f"and the 3 mm hex bit, star order, twice. Preload {hm['preload']['min']:.0f}-{hm['preload']['max']:.0f} N "
          f"(nominal {hm['preload']['nom']:.0f} N, nut factor 0.14-0.26, ASSUMPTION K-NUT).", "",
          f"**Cold:** at -20 C (-4 F) the boss shrinks {hm['cold']['shrink_mm']:g} mm more than the screws "
          f"({hm['cold']['preload_loss_n']:.0f} N of preload lost, more than the {hm['preload']['max']:.0f} N put in), so "
          "**the preload is gone at -20 C**. No HA-LS-1 row relies on it: the BL-055 tipping model the hip rows use "
          f"(strength {hm['min_sf']['strength']:g}, fatigue {hm['min_sf']['fatigue']:g}, creep {hm['min_sf']['creep']:g}) "
          "is preload-free; Loctite 243 keeps the nuts on, and T4b-PPA-COLD checks the paint marks after the cold drops.", "",
          f"Plate source: **{RING_SOURCE['service']}** from `{hm['files'][0]}` ({RING_SOURCE['url']}); {RING_SOURCE['price']}. "
          f"Fallback: {RING_SOURCE['fallback']}.", "",
          f"**BL-075 hip clearance** (`{bl075()['src']}`): the stack clears the frame, the bag, the spreader, the wearer "
          f"side and the hipbelt ({'all clear' if bl075()['clears'] else 'NOT all clear'}); decision: {bl075()['fix']}. "
          f"Steps 3 (keeper dry fit), 10 (tail band {bl075()['tail_min']:g}-{bl075()['tail_max']:g} mm, ASSUMPTION STACK-TOL), "
          "13 (cord rule BL075-CORD, ASSUMPTION PADSEAT-ROUTE) and 14 (optional caps) come from it.", "",
          "| screw | towards the R stay from the boss centre (mm) | above the boss centre (mm) |", "|---:|---:|---:|"]
    cx = sum(p[0] for p in pat["positions_xz"]) / len(pat["positions_xz"])
    cz = sum(p[1] for p in pat["positions_xz"]) / len(pat["positions_xz"])
    L += [f"| {i} | {x - cx:+.1f} | {z - cz:+.1f} |" for i, (x, z) in enumerate(pat["positions_xz"], 1)]
    L += [""] + [f"{i}. {s}" for i, s in enumerate(hip_steps(hm), 1)]
    L += ["", "## 6. First-article checks added on the PPA path", "",
          "1. Before any use below 0 C (32 F): T4b-PPA-COLD and T4c-PPA-COLD passed on P1.",
          f"2. HB-6b (test kit G6) runs on this frame: no paint mark moves; after T5, re-torque check at {hm['torque']:g} N m: no screw "
          "turns more than 1/8 turn (ASSUMPTION CREEP-LONG).",
          "3. Every 10 outings: paint marks on the hip screws and nuts unmoved; no white ring on the boss round the plates.", "",
          "## ASSUMPTIONS on this path", "",
          f"- **RING-PRICE**: {ASSUMPTIONS['RING-PRICE'][0]} Settled by: {ASSUMPTIONS['RING-PRICE'][1]}.",
          "- BL-073: K-NUT, CTE-Z, CREEP-LONG, BEARING-RING, JOINT-XY, PAD, SPOOL-RESERVE, LAYER-H are in "
          "`bl070_h1p.json` `assumptions_bl073` with what settles each.", "",
          "## FOUND (for the orchestrator)", ""]
    L += found_lines()
    L.append("")
    return "\n".join(L)


def found_lines() -> list[str]:
    spl = spool_plan()
    hm = hip()
    saved = len([r for r in spl["rows"] if all(u.strip().startswith("frame upper half") for u in r["uses"].split(";"))])
    if spl["booked_bl073"] != spl["spools"]:
        out = [f"- **Spools:** BL-073 books {spl['booked_bl073']} spools (a text line in its md, written by "
               "`bl073_hotwet.py`; not a JSON number). With its own fixed change layers each half needs a start spool with "
               f">= {spl['lower']['start_needs_g']:.0f} / {spl['upper']['start_needs_g']:.0f} g and a change spool with >= "
               f"{spl['lower']['finish_needs_g']:.0f} / {spl['upper']['finish_needs_g']:.0f} g (lower / upper), which only fresh "
               f"spools give, and the coupon jobs come to {spl['coupons_g']:.0f} g. The plan books **{spl['spools']}** spools; "
               f"{spl['left_g']:.0f} g is left over on part spools for reprints or P2. Using the first-article upper half as "
               f"the frame's upper half (if it passes) would save {saved} spools: an owner call."]
    else:
        out = [f"- **Spools (closed, BL-076):** bl070_h1p.md now books the plan's **{spl['spools']}** spools, read from "
               f"`spool_plan.csv`; {spl['spools'] - saved} if the first-article upper half becomes the frame's upper half "
               f"(orchestrator call). {spl['left_g']:.0f} g is left over on part spools for reprints or P2."]
    rl = hm["webs"]["ring_outer_ligament_mm"]
    t = hm["ring"]["t_mm"]
    if rl >= 1.5 * t - 1e-9:
        out.append(f"- **Ring edge distance (closed, BL-076):** {ring_pieces(hm)} arc plates, .063 in ({t:g} mm); smallest "
                   f"hole-to-edge ligament {min(v for k, v in hm['webs'].items() if k.startswith('ring_') and v):g} mm "
                   f">= 1.5 x t ({1.5 * t:.1f} mm), SendCutSend's guide 1.5-2 x t. Torque {hm['torque']:g} N m "
                   "(bl070_h1p.md BL-076).")
    else:
        out.append(f"- **Ring edge distance:** the ring's hole-to-OD ligament is {rl:g} mm, under SendCutSend's guide of "
                   f"1.5-2 x the thickness ({1.5 * t:.1f}-{2 * t:.1f} mm).")
    if "## Open items" in BL070_MD.read_text(encoding="utf-8"):
        out.append("- **'see OPEN' (closed, BL-076):** bl070_h1p.md has an 'Open items' section, generated by "
                   "`huntkit/gendesign/bl076.py`.")
    else:
        out.append("- **'see OPEN':** the US2 lug fatigue row's `gated_by` text points to an OPEN section that bl070_h1p.md "
                   "does not have.")
    return out


def readme_md(cp: dict) -> str:
    pl = pass_lines()
    cs = cost()
    return "\n".join([
        "# H1-P printed frame in PPA-CF: files (Pack 5200)", "",
        f"Generated by `designs/pack_5200/frame_h1p_build.py` ({TICKET}). **Do not edit by hand.**", "",
        "The PPA-CF build path, alongside the PAHT-CF H1 path in `../frame_h1/` (still the fallback).", ""] + hold_block() + [
        "| file | what |", "|---|---|",
        "| `COUPONS_H1P.md` | **start here**: the first-article upper half, coupon jobs A-G with towers, the gate, one sheet per test |",
        "| `PRINT_SHEET_H2S.md` | the H2S settings, the pad files, the planned filament change (Bambu Studio Add Pause) |",
        "| `BUILD_H1P.md` | BOM and cost, z 234 bolt positions, the trap-free hip mount at 0.6 N m |",
        "| `test_pieces/*.stl` | coupon pieces cut from H1-P (stay, crown corner, US2 piece), blocks, dummy towers |",
        "| `../../iter1/frame/h1p/*_flat_print.stl` | the halves with their snap-off pads (print these) |",
        "| `../../iter1/frame/h1p/hip_bearing_ring.dxf` | the two 6061 bearing plates (BL-076), for the laser-cut order |", "",
        f"Gate summary: CA-3-HW Z >= {pl['ca3_z_mpa']:g} MPa and SBS >= {pl['ca3_sbs_mpa']:g} MPa (B-basis), CA-1-HW "
        f"{int(pl['ca1_n_fat'])} run-outs, CA-4-HW >= {pl['ca4_e_ratio']:g}, the cold coupons, US2 lug x {pl['lug_factor']:g}, "
        f"clevis share <= {pl['share_max']:g}.", "",
        f"Cost: filament {cs['spools']} spools USD {cs['filament_usd']:.2f}; hip hardware USD {cs['hip_hw_usd']:.2f}; "
        f"tools USD {cs['tools_usd']:.2f} (one-time).", "",
        "Release copies, CSVs and a tech pack PDF: `outputs/release/frame_h1p_ppa/`.", ""])


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
        elif line.strip() and line.strip() != ">":
            out.append(T.para(re.sub(r"[*`]", "", re.sub(r"^>\s*", "", line))))
    flush()
    return out


def techpack(docs: dict, path: Path, images: list[Path]) -> Path:
    from huntkit.manufacturing import techpack as T
    b = bom()
    pl = pass_lines()
    hm = hip()
    cs = cost()
    sec = [
        T.Section("Flats and piece map: H1-P halves and coupon pieces", [T.para(
            "Printed body: lower half, upper half (both with snap-off pads), two US2 clevises (designs/pack_5200/iter1/frame/h1p/). "
            "Coupon pieces cut from the frame: stay, crown corner, US2 piece. No sewn parts on this package.")]
            + [T.image(p, 250, 150) for p in images]),
        T.Section("Bill of materials (PPA path)", [T.bom_table(b), T.para(
            f"Filament {cs['spools']} spools USD {cs['filament_usd']:.2f}; hip hardware USD {cs['hip_hw_usd']:.2f}; "
            f"one-time tools USD {cs['tools_usd']:.2f}.")]),
        T.Section("Cutting / print plan: first article, coupons, gate", _blocks(docs["COUPONS_H1P.md"])),
        T.Section("Operation sequence: H2S print sheet", _blocks(docs["PRINT_SHEET_H2S.md"])),
        T.Section("Operation sequence: build and hip mount", _blocks(docs["BUILD_H1P.md"])),
        T.Section("QC points", [T.table([["check", "pass"],
                                         ["CA-3-HW hot/wet Z, B-basis", f">= {pl['ca3_z_mpa']:g} MPa"],
                                         ["CA-3-HW hot/wet SBS, B-basis", f">= {pl['ca3_sbs_mpa']:g} MPa"],
                                         ["CA-1-HW all bars", f"{pl['ca1_cycles']:,.0f} cycles at {pl['ca1_smax_mpa']:g} MPa, {pl['ca1_temp_c']:g} C"],
                                         ["CA-4-HW E ratio", f">= {pl['ca4_e_ratio']:g}"],
                                         ["US2 lug proof", f"x {pl['lug_factor']:g} load, run-out"],
                                         ["clevis share B", f"<= {pl['share_max']:g}"],
                                         ["coupon layer time", f">= {pl['layer_s']:.0f} s every layer (slicer)"],
                                         ["body mass", f"-3 / +4 % of {h1p_json()['h1p']['body_g']:g} g"],
                                         ["hip screws", f">= {hm['threads_min']} threads proud (expect {hm['protrusion_threads']:g})"],
                                         ["hip torque", f"{hm['torque']:g} N m ({hm['torque_inlbf']:.1f} in lbf), paint marks"]], [150, 100])]),
        T.Section("Packaging", [T.para("Each printed half bagged with a desiccant pack in a 4 mil poly bag, labelled with the "
                                       "half, the spool numbers and the print date; hip hardware (screws, nuts, ring, keeper) in "
                                       "its own labelled bag. Ship flat in a carton with 25 mm foam each side.")]),
    ]
    tp = T.TechPack(title="Pack 5200 frame H1-P (PPA-CF)", subtitle="BL-074: BL-073 coupons, pads + filament change, trap-free hip mount, BOM",
                    date=DATE, footer="Hunting-appeal BL-074 H1-P build path",
                    cover=[["generated by", "designs/pack_5200/frame_h1p_build.py"],
                           ["data", "designs/pack_5200/iter1/frame/bl070_h1p.json (BL-070, BL-073); data/materials/polymers/ppa_cf_fdm.yaml"],
                           ["status", f"{PARKED}. {HOLD}. {RELEASED}. PAHT-CF H1 is the fallback"]],
                    sections=sec)
    return T.tech_pack(tp, path, strict=False)


def doc_pdf(title: str, md: str, path: Path, images: list | None = None) -> Path:
    from huntkit.manufacturing import techpack as T
    secs = [T.Section(md.splitlines()[0].lstrip("# "), _blocks(md))]
    if images:
        secs.insert(0, T.Section("Pictures", [T.image(p, 250, 160) for p in images]))
    tp = T.TechPack(title=title, subtitle=f"{TICKET}", date=DATE, footer=f"Hunting-appeal {TICKET}",
                    cover=[["generated by", "designs/pack_5200/frame_h1p_build.py"], ["status", PARKED]], sections=secs)
    return T.tech_pack(tp, path, strict=False)


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def coupon_figure(path: Path) -> Path:
    plt = _plt()
    pc = pieces()
    full = _assembled()
    fig, ax = plt.subplots(1, 2, figsize=(11, 6), dpi=100)
    v = full.vertices
    ax[0].scatter(v[::9, 0], v[::9, 2], s=0.15, c="0.8")
    for k, col in (("stay", "tab:red"), ("crown", "tab:blue"), ("us2", "tab:green")):
        w = pc[k]["frame"].vertices
        ax[0].scatter(w[::3, 0], w[::3, 2], s=0.3, c=col, label=f"{k}: {pc[k]['g']:.0f} g")
    ax[0].set_aspect("equal")
    ax[0].legend(loc="center", fontsize=9, markerscale=12)
    ax[0].set_title("coupon pieces cut from H1-P (front view, mm)")
    cp = coupon_plan()
    J = cp["jobs"]
    y = range(len(J))
    parts = [j["parts_g"] + j["support_g"] for j in J]
    tw = [j["tower_g"] for j in J]
    ax[1].barh(list(y), parts, color="#4a6fa5", label="parts + supports")
    ax[1].barh(list(y), tw, left=parts, color="#c9a227", label="dummy tower")
    ax[1].set_yticks(list(y))
    ax[1].set_yticklabels([f"{j['job']}: {j['title'][:34]}" for j in J], fontsize=8)
    for i, j in enumerate(J):
        ax[1].text(parts[i] + tw[i] + 5, i, f"{j['filament_g']:.0f} g, min {j['min_layer_s']:.0f} s", va="center", fontsize=8)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("g (filament + 8 % shown at the bar end)")
    ax[1].legend(fontsize=8, loc="lower right")
    ax[1].set_title(f"coupon jobs: every layer >= {pass_lines()['layer_s']:.0f} s")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def print_figure(path: Path) -> Path:
    import trimesh
    plt = _plt()
    pf = b73()["print_files"]
    sp = b73()["spool_plan"]
    fig, ax = plt.subplots(2, 2, figsize=(11, 9), dpi=90, gridspec_kw={"height_ratios": [3, 1.3]})
    for c, h in enumerate(("lower", "upper")):
        m = trimesh.load(H1P_STL / f"h1_{h}_flat_print.stl")
        v = m.vertices
        a = ax[0][c]
        a.scatter(v[::5, 0], v[::5, 1], s=0.1, c="0.6")
        for x, yy, z in pf[h]["sites_xyz_mm"]:
            a.add_patch(plt.Circle((x, yy), 12, color="tab:orange", alpha=0.8))
        a.set_aspect("equal")
        a.set_title(f"{h} half on the plate: {pf[h]['n_pads']} snap-off pads (orange)\n"
                    f"contact {pf[h]['plate_contact_part_mm2']:.0f} -> {pf[h]['plate_contact_with_pads_mm2']:.0f} mm2", fontsize=10)
        b = ax[1][c]
        b.scatter(v[::5, 0], v[::5, 2], s=0.1, c="0.6")
        z = sp[h]["swap"]["print_z_mm"]
        b.axhline(z, color="tab:red", lw=1.5)
        b.text(2, z + 2, f"Add Pause: layer {sp[h]['swap']['layer']}, z {z:.2f} mm -> change spool", color="tab:red", fontsize=9)
        b.set_aspect("equal")
        b.set_xlabel("mm (side view, print height up)")
    fig.suptitle("PRINT_SHEET_H2S: print the *_flat_print.stl files, one planned filament change per half", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def hip_figure(path: Path) -> Path:
    plt = _plt()
    hm = hip()
    fig = plt.figure(figsize=(12, 8.2), dpi=90)
    a = fig.add_axes([0.03, 0.08, 0.36, 0.84])
    layers = [("Ti mount base", hm["flange_t"], "#9aa5b1"), ("PPA-CF boss (no traps)", hm["boss"]["depth_mm"], "#3b3b3b"),
              ("6061 bearing ring", hm["ring"]["t_mm"], "#c0c6cc"), ("A2 nut in printed keeper", hm["nut_t"], "#d9a441")]
    z = 0.0
    for nm, t, col in layers:
        a.add_patch(plt.Rectangle((-20, z), 40, t, color=col, alpha=0.9))
        a.text(23, z + t / 2, f"{nm} {t:g} mm", va="center", fontsize=9)
        z += t
    a.add_patch(plt.Rectangle((-2.5, 0), 5, hm["screw_len"], fill=False, ec="tab:blue", lw=2))
    a.add_patch(plt.Rectangle((-4.5, -3), 9, 3, color="tab:blue", alpha=0.6))
    a.annotate(f"{hm['protrusion_mm']:g} mm = {hm['protrusion_threads']:g} threads proud\n(rule >= {hm['threads_min']})",
               (2.5, hm["stack"] + 2), (8, hm["stack"] + 6), fontsize=9, arrowprops=dict(arrowstyle="->"))
    a.text(-20, -7, f"Ti M5 x {hm['screw_len']:g} DIN 7984, {hm['torque']:g} N m ({hm['torque_inlbf']:.1f} in lbf)", fontsize=9, color="tab:blue")
    a.set_xlim(-25, 75)
    a.set_ylim(-10, hm["screw_len"] + 12)
    a.set_aspect("equal")
    a.axis("off")
    a.set_title("hip stack (section through one screw)", fontsize=10)
    t = fig.add_axes([0.42, 0.04, 0.56, 0.9])
    t.axis("off")
    import textwrap
    txt = "\n".join(textwrap.fill(f"{i}. {s.replace('**', '')}", 78, subsequent_indent="   ") for i, s in enumerate(hip_steps(hm), 1))
    t.text(0, 1, "BUILD_H1P section 5: hip mount assembly\n\n" + txt, va="top", fontsize=8.6, family="DejaVu Sans")
    fig.savefig(path)
    plt.close(fig)
    return path


def checks(pk: dict) -> list[str]:
    pl, rc = pass_lines(), pass_lines_recomputed()
    msgs = []
    for k, v in rc.items():
        ok = abs(pl[k] - v) <= 0.005 * abs(v) or (k in ("lug_factor", "share_max") and abs(pl[k] - v) < 0.01)
        msgs.append(f"{k}: JSON text {pl[k]:g} vs numeric {v:.4f} {'OK' if ok else 'MISMATCH'}")
    cp = pk["coupons"]
    msgs.append(f"coupon jobs PPA {cp['ppa_filament_g']:.0f} g, PAHT {cp['paht_filament_g']:.0f} g; shortest layer "
                f"{min(j['min_layer_s'] for j in cp['jobs']):.0f} s (need {pl['layer_s']:.0f})")
    s = pk["spools"]
    msgs.append(f"spools {s['spools']} (BL-073 booked {s['booked_bl073']}), total {s['total_g']:.0f} g")
    h = pk["hip"]
    msgs.append(f"hip torque {h['torque']} N m; {h['protrusion_threads']:g} threads proud (rule >= {h['threads_min']})")
    msgs.append(f"rig: all static loads under the cell: {rig_check()['all_under_cell']} (max {rig_check()['max_n']:.0f} N)")
    msgs.append(f"cost {pk['cost']}")
    return msgs


@functools.lru_cache(maxsize=None)
def package() -> dict:
    cp = coupon_plan()
    spl = spool_plan(cp)
    ps = print_sheet()
    docs = {"COUPONS_H1P.md": coupons_md(cp, spl), "PRINT_SHEET_H2S.md": print_sheet_md(ps),
            "BUILD_H1P.md": build_md(cp, spl, ps), "README.md": readme_md(cp)}
    docs = {k: parked(v) for k, v in docs.items()}          # BL-078
    pk = {"coupons": cp, "spools": spl, "print_sheet": ps, "docs": docs, "hip": hip(), "cost": cost(),
          "register": register_rows(), "results": results_items()}
    pk["checks"] = checks(pk)
    return pk


def parked(md: str) -> str:
    """BL-078: the PARKED banner under the title line; the rest of the document is unchanged."""
    title, rest = md.split("\n", 1)
    return f"{title}\n\n> {PARKED_TXT}\n{rest}"


def _w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _shrink(dst: Path) -> Path:
    from PIL import Image
    im = Image.open(dst).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, int(im.height * 1600 / im.width)))
    im.save(dst, optimize=True)
    assert dst.stat().st_size <= 1.5e6, dst
    return dst


def _raster(pdf: Path, page: int, dst: Path, r: int = 110) -> Path:
    tmp = dst.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", str(r), "-f", str(page), "-l", str(page), "-singlefile", str(pdf), str(tmp)],
                   check=True, capture_output=True)
    return _shrink(dst)


def _csv(path: Path, rows: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write(pk: dict) -> dict:
    PRINT.mkdir(parents=True, exist_ok=True)
    REL.mkdir(parents=True, exist_ok=True)
    for name, txt in pk["docs"].items():
        _w(PRINT / name, txt)
        _w(REL / name, txt)
    TP_DIR.mkdir(parents=True, exist_ok=True)
    pc = pieces()
    for k, fn in (("stay", "t4c_stay_R"), ("crown", "crown_corner_R"), ("us2", "us2_route_stay_R_h1p")):
        pc[k]["print"].export(TP_DIR / f"{fn}.stl")
        pc[k]["frame"].export(TP_DIR / f"{fn}_frame_coords.stl")
    import trimesh
    bk = blocks()
    for k in ("sbs", "sbs_pause", "z"):
        q = bk[k]
        m = trimesh.creation.box((q["x"], q["y"], q["h"]))
        m.apply_translation(-m.bounds[0])
        m.export(TP_DIR / f"block_{k}.stl")
    for j in pk["coupons"]["jobs"]:
        tower_mesh(j).export(TP_DIR / f"tower_{j['job']}.stl")
    from huntkit.manufacturing.records import bom_rows
    _csv(REL / "bom_h1p_ppa.csv", bom_rows(bom()))
    _csv(REL / "coupon_plan.csv", pk["coupons"]["rows"])
    _csv(REL / "spool_plan.csv", pk["spools"]["rows"])
    for old in ("t4c_stay_R.png",):
        if (REL / old).exists():
            (REL / old).unlink()
    SCREENS.mkdir(parents=True, exist_ok=True)
    f1 = coupon_figure(REL / "coupon_pieces.png")
    f2 = print_figure(REL / "print_pads_change.png")
    f3 = hip_figure(REL / "hip_assembly.png")
    tp = techpack(pk["docs"], REL / "h1p_ppa_techpack.pdf", [f1, f2, f3])
    cpdf = doc_pdf("H1-P coupons and gate", pk["docs"]["COUPONS_H1P.md"], REL / "COUPONS_H1P.pdf", [f1])
    ppdf = doc_pdf("H1-P H2S print sheet", pk["docs"]["PRINT_SHEET_H2S.md"], REL / "PRINT_SHEET_H2S.pdf", [f2])
    bpdf = doc_pdf("H1-P build", pk["docs"]["BUILD_H1P.md"], REL / "BUILD_H1P.pdf", [f3])
    import shutil
    shots = [_raster(cpdf, 3, SCREENS / f"{SHOT}_1.png")]
    for src, n in ((f2, 2), (f3, 3), (f1, 4)):
        dst = SCREENS / f"{SHOT}_{n}.png"
        shutil.copyfile(src, dst)
        shots.append(_shrink(dst))
    man = {"ticket": TICKET, "date": DATE, "checks": pk["checks"], "cost": pk["cost"],
           "files": sorted(str(p.relative_to(REL)) for p in REL.rglob("*") if p.is_file()),
           "screens": [str(p.relative_to(ROOT)) for p in shots], "pdfs": [str(p.relative_to(ROOT)) for p in (tp, cpdf, ppdf, bpdf)]}
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
