"""Bag-to-frame attachment SYSTEM (pack-designer, attachment phase 2026-11-05).

The frame side (printed fairleads, pins, sleeves) is ``bag_attach.py`` and its FEA record. This module is the rest of the
joint, bottom to top: hinge eye, under-straps, IM2/IM3 bag hooks, the crown hood (top anchor) and the two top side guys,
plus the sewn bag-side parts, their strength checks, proof tests, quiet checklist, procedures and patent guardrails.

Sources of every number:
- top-anchor performance: cloth-sim runs (``huntkit/clothsim``, scenarios ``pack5200_v31_att_*.yaml`` and the
  bag-top study ``pack5200_v31_anchor_*.yaml``), read from ``outputs/clothsim/<scenario>/results.json`` by
  :func:`compile_sims` and frozen into ``analysis/attach_system_results.json`` (git-tracked) so the doc regenerates
  without the scratch outputs;
- head clearance R-28: ``designs/pack_5200/build_geometry.py`` head model, re-run with the SIMULATED frame-side wall
  instead of the 15 mm bulge assumption (:func:`r28_loaded`);
- strengths: ``data/materials`` thread / webbing / textile / polymer / metal records, the seam rule of
  ``huntkit.clothsim.fabric`` (CONTRACTS 7) and the ASSUMPTIONs listed in :data:`ASSUMPTIONS`;
- factored loads: HA-LS-1 rev B (C5 / C2 = 2.0 g x 1.5 = 3.0 on the 1 g sim force) and the beam-model governing loads
  in ``analysis/bag_attachment_results.json``.

    python -m huntkit.gendesign.attach_system            # compile sims, checks, drawings, screens, JSON, docs
    python -m huntkit.gendesign.attach_system --docs-only
    python -m huntkit.gendesign.attach_system --refresh     # parts, procedures, drawings, screens on the frozen sims
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from huntkit.materials import load

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULT = ANALYSIS / "attach_system_results.json"
CUT = PACK / "cut" / "attachment"
SIMS = REPO / "outputs" / "clothsim"
SCREENS = REPO / "outputs" / "screens"
DATE = "20261105"
G = 9.80665
FACTOR = 3.0                       # HA-LS-1 C5 / C2: 2.0 g x 1.5 on the 1 g simulated force
QUAL = 1.5                         # ASSUMPTION: qualification proof = 1.5 x factored (n = 5 sample scatter allowance)
TARGET_CG = 180.0                  # owner goal for this phase (load CG aft of the frame axis)
TORSO_Z = {15: 601.0, 19: 702.6, 23: 804.2}          # crown top bar z (geometry.yaml crown_settings 0 / 8 / 16)
TORSO_BAR_Y = {15: 13.7, 19: 11.7, 23: 9.7}           # crown top bar centre y (ditto)

# ---------------------------------------------------------------- sim registry
# key: (scenario, torso_in, concept family, label)
RUNS = {
    "baseline": ("pack5200_v31_baseline", 19, "none", "phase-1 bag, no top anchor (before)"),
    "T0": ("pack5200_v31_tab_doubler", 19, "none", "IM3 tab B-17 + hinge doubler B-18, no top anchor"),
    "A": ("pack5200_v31_anchor_A_crownbar", 19, "tie", "crown-bar tie x +/-70 (study A)"),
    "D": ("pack5200_v31_anchor_D_low15", 15, "tie", "crown-bar tie at 15 in (study D)"),
    "G": ("pack5200_v31_anchor_G_stiff_forward", 19, "G", "study G: crown tie + fixed forward guys"),
    "G15": ("pack5200_v31_att_G15", 15, "G", "study G at 15 in"),
    "G23": ("pack5200_v31_att_G23", 23, "G", "study G at 23 in"),
    "L19": ("pack5200_v31_att_L19", 19, "lifter", "load lifters counted as the top anchor"),
    "P15": ("pack5200_v31_att_P15", 15, "hood", "crown hood only"),
    "P19": ("pack5200_v31_att_P19", 19, "hood", "crown hood only"),
    "P23": ("pack5200_v31_att_P23", 23, "hood", "crown hood only"),
    "PG15": ("pack5200_v31_att_PG15", 15, "hood+guys full lip", "crown hood (full-width lip, 2026-11-05) + top side guys"),
    "PG19": ("pack5200_v31_att_PG19", 19, "hood+guys full lip", "crown hood (full-width lip, 2026-11-05) + top side guys"),
    "PG23": ("pack5200_v31_att_PG23", 23, "hood+guys full lip", "crown hood (full-width lip, 2026-11-05) + top side guys"),
    # 2026-11-06: the lip, its HDPE stiffener and the lining stop at x +/-66 so they bear on bare OD 18 bar only, clear of
    # the crown corner wraps (frame_cg_recheck.md 5.1); the sim hood captures B-01 over x +/-66 only (conservative)
    "PR15": ("pack5200_v31_att_PR15", 15, "hood+guys", "crown hood, lip relieved at the corner wraps + top side guys"),
    "PR19": ("pack5200_v31_att_PR19", 19, "hood+guys", "crown hood, lip relieved at the corner wraps + top side guys"),
    "PR23": ("pack5200_v31_att_PR23", 23, "hood+guys", "crown hood, lip relieved at the corner wraps + top side guys"),
    "PGc15": ("pack5200_v31_att_PGc15", 15, "hood+guys cinched", "crown hood + guys cinched 60 N after loading"),
    "PGc19": ("pack5200_v31_att_PGc19", 19, "hood+guys cinched", "crown hood + guys cinched 60 N after loading"),
}
CHOSEN = "hood+guys"
MEAT_KG, GEAR_KG = 30.0, 38.0


# ---------------------------------------------------------------- R-28 with the simulated wall
_BG = None


def _bg():
    global _BG
    if _BG is None:
        sys.path.insert(0, str(PACK))
        import build_geometry as bg          # noqa: E402  (designs/pack_5200 is not a package)
        _BG = bg
    return _BG


_DRAFT = {}


def drafted_fore_face() -> dict:
    """x = 0 fore-face y of the DRAFTED sim mesh per 50 mm z band (same binning as clothsim.report)."""
    if not _DRAFT:
        from huntkit.clothsim.pack import PackModel, load_scenario
        pm = PackModel(load_scenario(), verbose=False)
        X = pm.mesh.X0
        sec = np.abs(X[:, 0]) < 0.6 * pm.h
        for z in np.arange(pm.c["Z0"], X[:, 2].max(), 50.0):
            s_ = sec & (np.abs(X[:, 2] - z) < 25)
            if s_.sum() > 0:
                _DRAFT[int(round(z))] = float(X[s_, 1].min())
    return _DRAFT


def wall_move(case: dict) -> list:
    """[(z, mm toward the head)] of the frame-side wall at x = 0: drafted sim face minus loaded sim face."""
    d = drafted_fore_face()
    out = []
    for row in case["profile"]["depth_by_z"]:
        z = int(round(row[0]))
        if z in d:
            out.append((float(row[0]), float(d[z] - row[1])))
    return out


R28_ALLOW = 3.0       # ASSUMPTION: fabric thickness + coarse-mesh scatter added to the simulated wall


HOOD_FRONT_MM = 1.0   # hood lip on the head side of the bar: one Hypalon ply (no lining, no stiffener above the bar centre)
HOOD_TOP_MM = 4.0     # hood crown over the bar: Hypalon 1 mm + XLPE lining 3 mm


def r28_loaded(torso_in: int, move: list | None, bulge: float | None = None, hood: bool = True) -> dict:
    """The DESIGN 4.7 head model (build_geometry.head_clearance) at one torso, with the frame-side wall above the crown
    taken as the drafted face moved toward the head by the SIMULATED ``move`` (+ R28_ALLOW), instead of the
    15 mm bulge assumption. ``move=None`` with ``bulge`` reproduces the design check (bulge = 15)."""
    from shapely.geometry import LineString, Point
    from shapely.geometry import Polygon as SPoly
    from shapely.ops import unary_union
    import yaml
    bg = _bg()
    A = yaml.safe_load(bg.ANTHRO.read_text())
    cva = A["posture"]["craniovertebral_angle_deg"]["used"]
    share = A["posture"]["upper_cervical_share"]["value"]
    heads = {"female_p05": A["ansur2"]["female"]["p05"], "male_p50": A["ansur2"]["male"]["p50"],
             "male_p95": A["ansur2"]["male"]["p95"]}
    cs = min(bg.crown_settings(), key=lambda c: abs(c["torso_in"] - torso_in))
    top_z = cs["crown_top_z"]
    zC7 = bg.Z_IC + torso_in * bg.IN
    c7 = (bg.y_on_axis(zC7) - bg.BACK_PAD - bg.C7_IN, zC7)
    yt = bg.y_on_axis(top_z)
    bar = Point(yt + bg.TOP_BAR_AFT, top_z).buffer(10.0)
    if hood:   # the crown hood wraps the bar: +1 mm on the head side, +4 mm over the top (design check: bare bar)
        bar = unary_union([Point(yt + bg.TOP_BAR_AFT, top_z).buffer(10.0 + HOOD_FRONT_MM),
                           Point(yt + bg.TOP_BAR_AFT, top_z + HOOD_TOP_MM - HOOD_FRONT_MM).buffer(10.0 + HOOD_FRONT_MM)])
    g = [bar,
         LineString([(bg.y_on_axis(top_z - 300) - bg.BACK_PAD, top_z - 300),
                     (bg.y_on_axis(top_z - 110) - bg.BACK_PAD, top_z - 110)]).buffer(1.0)]
    zz = np.linspace(top_z + 10, 1100.0, 60)
    if move is None:
        face = [(float(bg.y_frame(z)[0]) - float(bulge), float(z)) for z in zz]
    else:
        mz = np.array([m[0] for m in move])
        mv = np.array([m[1] for m in move])
        face = [(float(bg.y_frame(z)[0]) - max(float(np.interp(z, mz, mv)), 0.0) - R28_ALLOW, float(z)) for z in zz]
    g.append(LineString(face).buffer(1.0))
    obs = unary_union(g)
    rows = []
    for hn, h in heads.items():
        contact = next((float(th) for th in np.arange(0.0, 80.01, 1.0)
                        if SPoly(bg.head_pose(h, cva, c7, th, share)[0]).intersects(obs)), None)
        gap30 = SPoly(bg.head_pose(h, cva, c7, bg.HEAD_REQ_DEG, share)[0]).distance(obs)
        rows.append({"head": hn, "contact_deg": contact if contact is not None else 80.0, "gap_30_mm": round(gap30, 1)})
    worst = min(rows, key=lambda r: (r["contact_deg"], r["gap_30_mm"]))
    return {"torso_in": torso_in, "top_z": top_z, "rows": rows, "worst_contact_deg": worst["contact_deg"],
            "worst_gap_30_mm": worst["gap_30_mm"], "pass": all(r["contact_deg"] > bg.HEAD_REQ_DEG for r in rows),
            "basis": "simulated wall + %.0f mm" % R28_ALLOW if move is not None else f"design bulge {bulge:.0f} mm"}


# ---------------------------------------------------------------- compile the sims
def _case_metrics(r: dict, case: str, torso: int) -> dict:
    c = r["cases"][case]
    att = c["attachments"]
    cg = c["volume"]["contents_cg_mm"]
    im3 = [att[k]["tension_n"] for k in ("hook_im520_R", "hook_im520_L") if k in att]
    im2 = [att[k]["tension_n"] for k in ("hook_im330_R", "hook_im330_L") if k in att]
    hinge = [att[k]["tension_n"] for k in ("hinge_R", "hinge_L") if k in att]
    top = {k: float(v["tension_n"]) for k, v in att.items() if v["kind"] in ("tie", "pocket") and "." not in k}
    pocket_side = {}
    for k, v in att.items():
        if k.startswith("pocket."):
            pocket_side.setdefault("R", 0.0)
            pocket_side.setdefault("L", 0.0)
    mv = wall_move(c)
    zt = TORSO_Z[torso]
    above = [m for m in mv if m[0] - 25 >= zt]
    m = {"cg_y": float(cg[1]), "cg_z": float(cg[2]), "aft_depth": float(c["profile"]["max_depth_aft_mm"]),
         "im3_max_n": float(max(im3)) if im3 else 0.0, "im2_max_n": float(max(im2)) if im2 else 0.0,
         "hinge_max_n": float(max(hinge)) if hinge else 0.0, "top_n": top,
         "volume_L": float(c["volume"]["closed_L"]), "converged": bool(c["converged"]),
         "residual_n": float(c["solve"][-1]["residual_n"]),
         "wall_toward_head_mm": max([m_[1] for m_ in above], default=0.0),
         "wall_move": mv,
         "crown_contact_n": float(c["contact"].get("contact_crown", {}).get("force_total_n") or 0.0)}
    if case == "meat":
        m["mixed_cg_y"] = (MEAT_KG * 150.0 + GEAR_KG * cg[1]) / (MEAT_KG + GEAR_KG)
    return m


def compile_sims(log=print) -> dict:
    out = {}
    for key, (scen, torso, fam, label) in RUNS.items():
        f = SIMS / scen / "results.json"
        if not f.exists():
            log(f"  missing sim {scen}")
            continue
        r = json.loads(f.read_text())
        row = {"scenario": scen, "torso_in": torso, "family": fam, "label": label}
        for case in ("fill", "meat"):
            m = _case_metrics(r, case, torso)
            m["r28"] = r28_loaded(torso, m.pop("wall_move"))
            row[case] = m
        out[key] = row
        log(f"  {key:8} {torso} in  fill CG {row['fill']['cg_y']:.0f}  meat CG {row['meat']['cg_y']:.0f}  "
            f"R-28 {row['fill']['r28']['worst_contact_deg']:.0f}/{row['meat']['r28']['worst_contact_deg']:.0f} deg")
    return out


def r28_design_reference() -> dict:
    """The DESIGN 4.7 check as published (bare bar, 15 mm bulge), and the same with the hood on the bar."""
    return {"published": {t: r28_loaded(t, None, bulge=_bg().BULGE, hood=False) for t in (15, 19, 23)},
            "with_hood": {t: r28_loaded(t, None, bulge=_bg().BULGE, hood=True) for t in (15, 19, 23)}}


# ================================================================ sewn side: stitch standards and capacities
# Thread rule (CONTRACTS 7, huntkit.clothsim.fabric.stitch_strength_n_mm): q = 1.5 x thread break / stitch length (301).
ETA_BOX = 0.5          # ASSUMPTION: share of a box-X stitch path that carries load at failure (uneven sharing)
WEB_PIN_KD = 0.5       # ASSUMPTION: webbing wrapped on a 5 mm pin or a hook bed keeps 50 % of its straight break
SEAM_EFF = 0.80        # huntkit/clothsim/fabrics.yaml seam_efficiency: a 301 seam breaks at 80 % of the weaker strip
GRAB_TO_STRIP = 31.25  # huntkit/clothsim/fabrics.yaml grab_to_strip_mm
UHMW_STRIP = 60.0      # huntkit/clothsim/fabrics.yaml challenge_ultra_200 strip N/mm (ASSUMPTION there)
SPI = {"box": 7, "perim": 8}          # stitches per inch: 7 SPI = 3.63 mm (load box-X), 8 SPI = 3.18 mm (perimeter)
THREAD = {"box": "bonded_nylon_tex135", "perim": "bonded_nylon_tex90"}
NEEDLE = {"bonded_nylon_tex135": "Nm 140 / 22", "bonded_nylon_tex90": "Nm 110 / 18"}   # ASSUMPTION: thread-needle chart


def q_thread(kind: str) -> float:
    t = float(load(THREAD[kind]).require("breaking_strength_n"))
    return 1.5 * t / (25.4 / SPI[kind])


def strip_n_mm(material_id: str) -> float:
    if material_id == "challenge_ultra_200":
        return UHMW_STRIP
    m = load(material_id)
    return min(float(m.require("grab_warp_n")), float(m.get("grab_weft_n", m.require("grab_warp_n")))) / GRAB_TO_STRIP


def box_x(w: float, h: float) -> dict:
    path = 2 * (w + h) + 2 * math.hypot(w, h)
    return {"w": w, "h": h, "path_mm": path, "cap_n": ETA_BOX * q_thread("box") * path}


def patch_seam(loaded_mm: float, base: str, patch: str, rows: int = 2) -> dict:
    fab = SEAM_EFF * min(strip_n_mm(base), strip_n_mm(patch))
    thr = rows * q_thread("perim")
    return {"loaded_mm": loaded_mm, "line_n_mm": min(fab, thr), "governs": "fabric" if fab < thr else "thread",
            "cap_n": loaded_mm * min(fab, thr)}


def web_pin(material_id: str) -> float:
    return WEB_PIN_KD * float(load(material_id).require("breaking_strength_n"))


# ================================================================ geometry of the new parts (mm)
HOOD = {"width": 190.0, "back": 51.0, "crown": 36.0, "lip": 17.0, "curl": 12.0, "hem": 14.0, "depth": 16.0,
        "ear_w": 30.0, "ear_h": 40.0, "lip_half": 66.0, "relief_r": 4.0,
        "lip_stiff": (124.0, 22.0, 1.5), "lining": (128.0, 50.0, 3.0)}
# Crown corner wraps (frame.yaml joints; frame_cg_recheck.md 5.1): 0.75 mm wrap, 30 mm onto the bar from the leg face at
# x +/-107, ends ply-dropped over 8 mm, so the bar is OD ~19.5 from x +/-85 out and the step starts at x +/-77. The wrap
# cannot be shortened (an 11 mm overlap fails the corner bond), so the hood is relieved instead (2026-11-06).
WRAP = {"x_start": 77.0, "x_full": 85.0, "x_leg": 107.0, "od": 19.5}
BAR_OD = 18.0
LEG_INNER_X = 104.0                 # crown-leg inner faces


def wrap_clearance() -> dict:
    """Relieved hood vs the corner wraps. The hood floats (208 - 190) / 2 = 9 mm a side between the legs, so the lip,
    its stiffener and the lining must stop 9 mm + margin inside the start of the wrap step."""
    H = HOOD
    float_ = LEG_INNER_X - H["width"] / 2.0
    lip_edge = H["lip_half"] + float_
    radial_step = (WRAP["od"] - BAR_OD) / 2.0
    lining_t = H["lining"][2]
    return {"hood_float_mm": float_, "lip_half_mm": H["lip_half"], "lip_edge_worst_x_mm": lip_edge,
            "lip_margin_to_wrap_mm": WRAP["x_start"] - lip_edge,
            "stiffener_half_mm": H["lip_stiff"][0] / 2.0, "lining_half_mm": H["lining"][0] / 2.0,
            "relief_width_mm": H["width"] / 2.0 - H["lip_half"],
            "crown_over_wrap_clear_mm": lining_t - radial_step, "bearing_len_mm": 2.0 * H["lip_half"],
            "pass": WRAP["x_start"] - lip_edge >= 2.0 and lining_t - radial_step >= 2.0
                    and H["lip_stiff"][0] / 2.0 <= H["lip_half"] - 2.0 and H["lining"][0] / 2.0 <= H["lip_half"]}
# hood ladder: one rung per crown setting (12.7 mm), so the hood crown always sits on the bar (no vertical slop, no tap).
# Rung k (setting k, torso 15 + k/2 in) slot centre = crown top z(k) - 40 mm (tongue weave below the bar).
LADDER = {"w": 40.0, "h": 250.0, "slot": (27.0, 5.0), "pitch": 12.7, "rungs": 17, "x": 60.0, "z_lo": 545.0,
          "slot0_z": 601.0 - 40.0}
TONGUE_25 = 120.0      # hood tongue cut length (25 mm webbing), toggle sewn in the end
TOGGLE_G = 3.0         # ASSUMPTION: POM toggle 30 x 8 x 5 mm (DESIGN 4.5 LINK toggle mass)
TOGGLE_N = 670.0       # ASSUMPTION: POM toggle bending across a 27 mm slot (pom_acetal ~65 MPa, Z 33 mm3)
GUY = {"free_mm": 314.0, "cut_mm": 500.0, "bag_xz": (149.0, 752.0), "hood_x": 95.0}
LADDER_LOCK = "ladder_lock_25mm"
TRIGLIDE_G = 3.0       # ASSUMPTION (bag_attachment.md lifter keeper)
HOOK_RATED_N = 2200.0  # purchase requirement for the four bag hooks (set from the C5 hood-off case, below)
HOOK_RATED_G = 14.0    # ASSUMPTION: 38 mm forged 7075 sliding-gate hook in that class (old 1500 N part: 9 g)
PIN = {"d": 5.0, "L": 50.0}


def hood_flat() -> dict:
    """Developed blank of the crown hood B-19 (x across, v down the profile from the back-ply bottom edge)."""
    H = HOOD
    v = np.cumsum([0.0, H["back"], H["crown"], H["lip"], H["curl"], H["hem"]])
    return {"folds_v": v[1:-1].tolist(), "length": float(v[-1]), "width": H["width"]}


# ================================================================ loads, strength, proof tests
def factored_loads(sims: dict, rec: dict) -> dict:
    """Factored design loads per side, N. 1 g sim forces x 3.0 (HA-LS-1 C5/C2) or the beam-model governing load
    (bag_attachment_results.json), whichever is larger. The IM3 hook is designed for the hood-off misuse case (T0)."""
    gov = rec["governing"]
    chosen = [k for k, v in sims.items() if v["family"] == CHOSEN]

    def worst(keys, field):
        return max(max(sims[k]["fill"][field], sims[k]["meat"][field]) for k in keys if k in sims)
    top = {}
    for k in chosen + [k for k, v in sims.items() if v["family"] == "hood"]:   # hood alone = guys slack or not set
        for case in ("fill", "meat"):
            for nm, t in sims[k][case]["top_n"].items():
                top[nm] = max(top.get(nm, 0.0), t)
    hood_total_1g = top.get("pocket", 0.0)
    guy_1g = max(top.get("TG_R", 0.0), top.get("TG_L", 0.0))
    return {
        "hinge": max(FACTOR * worst(chosen + ["T0"], "hinge_max_n"), gov["hinge"]["n"]),
        "im2": max(FACTOR * worst(chosen + ["T0"], "im2_max_n"), gov["im2"]["n"]),
        "im3": max(FACTOR * worst(chosen + ["T0"], "im3_max_n"), gov["im3"]["n"]),
        "im3_chosen": FACTOR * worst(chosen, "im3_max_n"),
        "hood_capture_per_side": FACTOR * hood_total_1g / 2.0,
        "hood_total": FACTOR * (hood_total_1g + 2 * guy_1g),
        "guy": FACTOR * guy_1g,
        "basis": {"factor": FACTOR, "chosen_runs": chosen, "hood_1g_n": hood_total_1g, "guy_1g_n": guy_1g},
    }


def parts(F: dict) -> list[dict]:
    """Every sewn bag-side attachment part, with its make spec and strength check (per side unless qty says)."""
    w38, w25 = "poly_webbing_38mm", "poly_webbing_25mm"
    bx38, bx25 = box_x(38.0, 38.0), box_x(25.0, 25.0)
    out = []

    def add(pid, name, qty, mat, cut, fold, stitch, kind, backing, place, load_n, load_basis, caps):
        gov_k = min(caps, key=lambda k: caps[k])
        out.append({"id": pid, "name": name, "qty": qty, "material": mat, "cut": cut, "fold": fold, "stitch": stitch,
                    "spi": SPI[kind], "thread": THREAD[kind], "needle": NEEDLE[THREAD[kind]], "backing": backing,
                    "placement": place, "load_n": round(load_n, 0), "load_basis": load_basis,
                    "caps_n": {k: round(v, 0) for k, v in caps.items()}, "governs": gov_k,
                    "sf": round(caps[gov_k] / max(load_n, 1e-9), 2), "proof_n": round(QUAL * load_n / 10.0) * 10.0})
    # hinge eye on B-18
    add("HE", "hinge eye (sewn eye on the tethered z 60 pull-pin)", 2, w38, "38 mm x 150 mm",
        "end folded back 50 mm into a 25 mm eye for the 5 mm pin; first 30 mm tri-folded lengthwise to an 18 mm neck "
        "(fairlead throat) and held with a 304 bartack across the neck; tail runs down into the B-01|B-05 seam",
        "box-X 38 x 38 through eye plies + B-18 + B-01, 301", "box", "B-18 doubler (inside B-01), lower edge caught in "
        "the B-01|B-05 seam", "x +/-115 at the hinge-eye notch, eye top at z 60",
        F["hinge"], "max(sim hinge eye x 3.0, beam model)",
        {"box-X": bx38["cap_n"], "webbing on pin": web_pin(w38),
         "B-18 seam (80 mm, B-05 strip governs)": patch_seam(80.0, "cordura_500d_nylon66", "hypalon_coated_nylon")["cap_n"]})
    add("B-18", "hinge-eye doubler", 2, "hypalon_coated_nylon", "90 x 45, laser-cut, R6 corners",
        "flat", "double-row perimeter 3 / 9 mm from the edge, 301; lower edge in the B-01|B-05 seam", "perim",
        "-", "INSIDE B-01, centred on the hinge eye", F["hinge"], "as HE",
        {"perimeter seam (80 mm loaded)": patch_seam(80.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"]})
    add("T2", "IM2 bag-hook tongue", 2, w38, "38 mm x 160 mm",
        "end folded 45 mm round the hook bed into a 20 mm loop, box-X; other end box-X to B-01", "box-X 38 x 38 both ends, 301",
        "box", "B-23 backing 60 x 60 Hypalon inside B-01 (new)", "B-01 outside, box at x +/-115, z 260 (existing "
        "'im2 bag-hook strap box-X' drill marks); loop at the IM2 eye z 330", F["im2"], "max(sim IM2 x 3.0, beam model)",
        {"box-X": bx38["cap_n"], "webbing on hook bed": web_pin(w38),
         "B-23 tear-out (2 x 60 mm)": patch_seam(120.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"],
         "hook (rated)": HOOK_RATED_N})
    add("B-23", "IM2 tongue backing (new)", 2, "hypalon_coated_nylon", "60 x 60, laser-cut, R6", "flat",
        "single-row perimeter 3 mm, 301 (the tongue box-X goes through it)", "perim", "-",
        "INSIDE B-01, centred on the IM2 tongue box at x +/-115, z 260", F["im2"], "as T2",
        {"tear-out (2 x 60 mm)": patch_seam(120.0, "challenge_ultra_200", "hypalon_coated_nylon", rows=1)["cap_n"]})
    add("T3", "IM3 bag-hook tongue", 2, w38, "38 mm x 160 mm", "as T2", "box-X 38 x 38 both ends, 301", "box",
        "B-17 tab (outside B-01)", "box at x +/-115, z 450 on B-17; loop at the IM3 eye z 520", F["im3"],
        "max(sim IM3 x 3.0 incl. hood-off T0 472 N, beam model)",
        {"box-X": bx38["cap_n"], "webbing on hook bed": web_pin(w38), "hook (rated)": HOOK_RATED_N,
         "B-17 seam (80 mm loaded)": patch_seam(80.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"]})
    add("B-17", "IM3 bag-hook tab", 2, "hypalon_coated_nylon", "90 x 110, laser-cut, R6", "flat",
        "double-row perimeter 3 / 9 mm, 301; 80 mm stitch line across the load", "perim", "-",
        "OUTSIDE B-01 under the IM3 swell, centred x +/-115, z 450", F["im3"], "as T3",
        {"perimeter seam (80 mm loaded)": patch_seam(80.0, "challenge_ultra_200", "hypalon_coated_nylon")["cap_n"]})
    # crown hood
    hf = hood_flat()
    add("B-19", "crown hood shell (new)", 1, "hypalon_coated_nylon",
        f"{HOOD['width']:.0f} x {hf['length']:.0f} blank + 2 ears {HOOD['ear_w']:.0f} x {HOOD['ear_h']:.0f}, laser-cut",
        "fold 1 (back/crown) and fold 2 (crown/lip) square on a 19 mm dowel; lip relieved over the outer "
        f"{HOOD['width'] / 2 - HOOD['lip_half']:.0f} mm each side (lip on bare bar over x +/-{HOOD['lip_half']:.0f}, clear of the "
        "crown corner wraps); lip hem 14 mm turned in over the HDPE stiffener B-19s; lining B-19L glued inside the crown",
        "lip hem: single row 301 at 3 mm; tongues box-X 25 x 25; ears: guy box-X 25 x 25", "box", "-",
        f"rides on the crown top bar between the crown legs (shell x +/-95, lip bears on bare bar x +/-{HOOD['lip_half']:.0f})",
        F["hood_total"], "sim hood capture + 2 guys, x 3.0",
        {f"lip on bare bar (Hypalon strip x {2 * HOOD['lip_half']:.0f})": strip_n_mm("hypalon_coated_nylon") * 2 * HOOD["lip_half"] * SEAM_EFF,
         "2 tongue box-X 25": 2 * bx25["cap_n"]})
    add("HT", "hood tongues (woven into the ladder, POM toggle end)", 2, w25, f"25 mm x {TONGUE_25:.0f} mm",
        "one end box-X to the hood back ply at x +/-60; other end folded over a POM toggle 30 x 8 x 5 and box-X'd",
        "box-X 25 x 25 both ends, 301", "box", "-", "woven in at the rung for the torso setting (rung k = crown setting k)",
        F["hood_capture_per_side"], "sim hood capture per side x 3.0",
        {"box-X 25": bx25["cap_n"], "POM toggle (ASSUMPTION)": TOGGLE_N, "webbing": web_pin(w25)})
    # the rung bar between two slots is a membrane pulled out of plane by the tongue; each end goes into the edge seams
    # over the bar height. ASSUMPTION: 30 deg sag at failure, so P = 2 x end capacity x sin 30
    lad_bridge = (LADDER["pitch"] - LADDER["slot"][1]) * patch_seam(1.0, "challenge_ultra_200", "hypalon_coated_nylon")["line_n_mm"] \
        * 2 * math.sin(math.radians(30.0))
    add("B-20", "hood ladder strip (new)", 2, "hypalon_coated_nylon",
        f"{LADDER['w']:.0f} x {LADDER['h']:.0f}, {LADDER['rungs']} slots {LADDER['slot'][0]:.0f} x {LADDER['slot'][1]:.0f} "
        f"at {LADDER['pitch']} mm pitch, laser-cut", "flat", "double-row both long edges 2 / 5 mm (clear of the slots) + bartack both ends, 301",
        "perim", "-", f"OUTSIDE B-01b/B-01u, centred x +/-{LADDER['x']:.0f}, z {LADDER['z_lo']:.0f}-{LADDER['z_lo'] + LADDER['h']:.0f} "
        "(sewn after the B-01 tiers are joined; follows the setback)", F["hood_capture_per_side"], "as HT",
        {"rung bar (7.7 mm, 30 deg sag)": lad_bridge})
    add("TG", "top side guy (fixed length, set once)", 2, w25, f"25 mm x {GUY['cut_mm']:.0f} mm",
        "hood end box-X on the ear; bag end through a 25 mm ladder lock + tri-glide keeper on B-22, tail 100 mm in an elastic keeper",
        "box-X 25 x 25 (hood end), 301", "box", "B-22 corner tab", f"hood ear x +/-{GUY['hood_x']:.0f} -> B-02d at "
        f"x +/-{GUY['bag_xz'][0]:.0f}, z {GUY['bag_xz'][1]:.0f} (outer face, upper corner); free length about "
        f"{GUY['free_mm']:.0f} mm", F["guy"], "sim guy x 3.0",
        {"box-X 25": bx25["cap_n"], "ladder lock slip": float(load(LADDER_LOCK).require("slip_load_n")),
         "webbing": web_pin(w25)})
    add("B-22", "guy corner tab (new)", 2, "hypalon_coated_nylon", "50 x 60, laser-cut, R6", "flat",
        "double-row perimeter; ladder-lock tab (25 mm x 70 mm webbing) box-X 25 x 25 through it", "perim", "-",
        f"OUTSIDE B-02d at x +/-{GUY['bag_xz'][0]:.0f}, z {GUY['bag_xz'][1]:.0f}", F["guy"], "as TG",
        {"perimeter seam (50 mm loaded)": patch_seam(50.0, "cordura_330d_nylon66", "hypalon_coated_nylon")["cap_n"],
         "box-X 25": bx25["cap_n"]})
    # float-mode stand-off link (owner 2026-11-06): sized on the misuse envelope (the rest of the 68 kg rating in the bag)
    from huntkit.gendesign import meat_haul as MH
    gaps = " / ".join(f"{g_:.0f}" for g_ in MH.FLOAT_GAPS_MM)
    add(MH.LINK["id"], "float-mode stand-off link (new)", 2, w38, f"38 mm x {MH.link_cut_mm():.0f} mm",
        f"hook end folded {MH.LINK['hook_fold_mm']:.0f} mm round the bed of a rated 38 mm hook, box-X; three loops "
        f"({MH.LINK['loop_open_mm']:.0f} mm opening, {MH.LINK['loop_fold_mm']:.0f} mm of webbing each) with their bed at "
        f"{gaps} mm from the hook bed, each closed with a 38 x 20 box-X; {MH.LINK['tail_mm']:.0f} mm tail, heat-sealed",
        "box-X 38 x 38 (hook) + 3 x box-X 38 x 20 (loops), 301", "box", "-",
        "hook on the IM3 captive eye (z 520, x +/-115); the bag's T3 hook clips into a loop (float mode only; "
        "stowed in the lid or hipbelt pocket)",
        MH.link_tension(MH.FLOAT_BAG_ENVELOPE_KG), f"{MH.FLOAT_BAG_ENVELOPE_KG:.0f} kg bag on two links at "
        f"{MH.LINK_ANGLE_DEG:.0f} deg x 3.0 (misuse envelope; design case {MH.FLOAT_GEAR_KG:.0f} kg = "
        f"{MH.link_tension(MH.FLOAT_GEAR_KG):.0f} N)",
        {"box-X (hook end)": bx38["cap_n"], "loop box-X 38 x 20": box_x(38.0, 20.0)["cap_n"],
         "webbing on hook bed": web_pin(w38), "hook (rated)": HOOK_RATED_N})
    return out


def proof_tests(F: dict, P: list) -> list[dict]:
    """Qualification (5 samples, hold 60 s, no slip or tear) and lot checks. Loads = 1.5 x factored (ASSUMPTION QUAL)."""
    rows = [{"id": "PT-1", "what": "38 mm bag hook (all four bag hooks, one part)", "rig": "hook on a 5 mm pin, 38 mm webbing loop on the bed",
             "load_n": round(QUAL * F["im3"] / 10) * 10, "covers": f"C5 IM3 factored {F['im3']:.0f} N (hood-off, T0) x 1.5",
             "accept": "5 of 5 hold, gate closes after", "also": f"every lot of 25: one hook to {F['im3']:.0f} N"},
            {"id": "PT-2", "what": "T3 tongue on B-17 on a B-01 swatch", "rig": "swatch clamped 120 mm wide, pull on the tongue loop",
             "load_n": round(QUAL * F["im3"] / 10) * 10, "covers": "IM3 sewn path (box-X, tab seam, laminate)",
             "accept": "5 of 5 hold, no stitch break, no laminate tear", "also": "first article only"},
            {"id": "PT-3", "what": "HE eye on B-18 + B-01 + B-05 seam swatch", "rig": "5 mm pin through the eye",
             "load_n": round(QUAL * F["hinge"] / 10) * 10, "covers": f"hinge factored {F['hinge']:.0f} N", "accept": "5 of 5 hold",
             "also": "first article only"},
            {"id": "PT-4", "what": "crown hood on an 18 mm tube", "rig": "pull B-01 swatch aft through the ladder, guys pulled aft-outward",
             "load_n": round(QUAL * F["hood_total"] / 10) * 10, "covers": "hood capture + both guys x 3.0",
             "accept": "hood stays seated, no toggle pull-through", "also": "repeat at -10 C (HDPE lip)"},
            {"id": "PT-5", "what": "guy ladder lock with the tri-glide keeper", "rig": "25 mm webbing, 10 cycles 0-load",
             "load_n": round(QUAL * F["guy"] / 10) * 10, "covers": "guy x 3.0", "accept": "slip < 5 mm over 10 cycles", "also": "-"}]
    sl = next((p for p in P if p["id"] == "B-24"), None)
    if sl:
        rows.append({"id": "PT-6", "what": "B-24 stand-off link, hook end and the 220 mm loop", "rig": "link hook on a 5 mm "
                     "pin, 38 mm webbing loop through the 220 mm loop, pull in line",
                     "load_n": sl["proof_n"], "covers": f"link misuse envelope {sl['load_n']:.0f} N x 1.5",
                     "accept": "5 of 5 hold, no box-X break, gate closes after", "also": "first article; then 1 link per lot of 25 "
                     f"to {sl['load_n']:.0f} N"})
    return rows


# ================================================================ mass and cost delta
def mass_delta(P: list) -> dict:
    """Mass of THIS phase on top of the 2026-11-05 budget (which already has B-17/B-18 and the 1500 N hooks)."""
    hyp = float(load("hypalon_coated_nylon").require("areal_density_gsm")) * 1e-6     # g / mm2
    hdpe = float(load("hdpe_sheet").require("density_kg_m3")) * 1e-6                 # g / mm3
    xlpe = float(load("xlpe_foam").require("density_kg_m3")) * 1e-6
    g25 = float(load("poly_webbing_25mm").require("mass_g_m")) / 1000.0
    # cut parts: area of the 1:1 drawing pieces (the same pieces panels.yaml carries), x qty x areal mass / density
    area = {p.piece_id: p.area_mm2 * p.quantity for p in drawing_pieces()}
    ls, lt = HOOD["lip_stiff"], HOOD["lining"]
    rows = {
        "crown hood B-19 (Hypalon blank + ears + hem)": hyp * area["B-19"],
        "hood lip stiffener B-19s (HDPE 1.5)": hdpe * area["B-19s"] * ls[2],
        "hood lining B-19L (XLPE 3)": xlpe * area["B-19L"] * lt[2],
        "hood ladder strips B-20 x2": hyp * area["B-20"],
        "hood tongues x2 + POM toggles": 2 * (g25 * TONGUE_25 + TOGGLE_G),
        "hood grab tab (25 mm x 90)": g25 * 90.0,
        "top side guys x2 (25 mm webbing)": 2 * g25 * GUY["cut_mm"],
        "guy ladder locks + tri-glides + ladder-lock tabs": 2 * (float(load(LADDER_LOCK).require("mass_g")) + TRIGLIDE_G + g25 * 70.0),
        "guy corner tabs B-22 x2": hyp * area["B-22"],
        "guy tail elastic keepers x2": 2 * 0.6,
        "IM2 tongue backings B-23 x2": hyp * area["B-23"],
        "bag hooks 1500 N -> 2200 N rated (4 x +5 g)": 4 * (HOOK_RATED_G - 9.0),
        "thread (box-X + perimeters)": 2.0,
    }
    return {"parts_g": {k: round(v, 1) for k, v in rows.items()}, "delta_g": round(sum(rows.values()), 1),
            "basis": "hypalon_coated_nylon 1000 gsm, hdpe_sheet, xlpe_foam, poly_webbing_25mm, ladder_lock_25mm records; "
                     "toggle, tri-glide, hook masses ASSUMPTION; elastic keeper 0.6 g ASSUMPTION"}


# ================================================================ procedures (gloved hands; seconds are ASSUMPTIONS)
# Unit times: hook 4 s, tethered pin 4 s, cam pop 3 s (bag_attachment.md / meat_haul_modes.md), hood lift or drop 3 s,
# ladder-lock snug 3 s, clear or place the bag 10 s, floor channels on/off the straps 6 s.
PROCEDURES = {
    "bag_on": {"title": "Bag on (bag off, frame empty)", "steps": [
        ("Lay the frame on its back pad, crown away from you. Stand the bag behind it with the frame panel (B-01) facing the frame.", 10),
        ("First time only: weave the two hood tongues through the B-20 ladder at your crown setting (rung number = the setting "
         "number on the crown rack; the rung list is printed on B-20) and push each POM toggle through the next slot.", 0),
        ("Tip the bag onto the frame so each hinge eye sits between the cheeks of the z 60 fairlead. Push the pull-pin through "
         "cheek, sleeve, eye, cheek. Seat the silicone washer. Both sides.", 12),
        ("Lift the bag floor. Lay the two under-straps in the floor channels (US1 rear, US2 front) and cam them until the floor is snug.", 12),
        ("Clip the four bag hooks onto the IM2 and IM3 eyes, gate toward the bag. Work bottom up: IM2 left and right, then IM3.", 16),
        ("Lift the hood by its tab, press the top of the bag against the crown, let go. The hood drops over the top bar. "
         "Check: the hood sits on the bar across its width and its lip is in front of the bar.", 3),
        ("Pack the bag. Pull each top-guy tail until the guy is snug (no slack, do not crank it), slide the tri-glide against the "
         "ladder lock and tuck the tail in its keeper.", 6),
        ("Lifters and hipbelt as usual.", 0)]},
    "bag_off": {"title": "Bag off (keep it under 120 s)", "steps": [
        ("Set the pack down on its back pad.", 3),
        ("Lift the hood tab and ease the top of the bag about 10 cm aft so the hood clears the bar. The guys stay on the hood "
         "and come with the bag.", 3),
        ("Unclip the four bag hooks, IM3 first, then IM2. Hang each on its elastic keeper.", 16),
        ("Pop the two under-strap cams. Slide the floor channels off the straps. The straps stay on their pins: they are the cradle.", 12),
        ("Pull the two hinge pins. They stay tethered to the bag eyes.", 8),
        ("Lift the bag clear.", 10)]},
    "float": {"title": "Float mode (meat on the frame, bag hung upright behind it on the B-24 links)", "steps": [
        ("Take the bag off (procedure above). Lay the frame on its back pad, crown toward the meat.", None),
        ("Set the quarter (in a game bag) in the two under-straps, bone toward the spreader. Cam them until the belly is "
         "about 70 mm.", 12),
        ("Hook IM1-IM3 meat straps eye to eye over the meat and cam them. A hock can sit on IM1.", 24),
        ("Hook one B-24 stand-off link on each IM3 eye, gate toward the bag, beside the meat-strap hook. Let the loops hang "
         "aft along the sides of the meat.", 8),
        ("Stand the bag upright behind the meat, frame panel (B-01) toward it. Clip each T3 bag hook into the link loop that "
         "just touches the bag (120, 170 or 220 mm; use the smallest that fits). The T2 hooks stay on their keepers; the "
         "hood lies on the bag top and is not put on the bar.", 14),
        ("Close W1-W3 round the bag and the meat (ladder locks).", 18)]},
    "bag_off_haul": {"title": "Bag-off meat haul (frame and cradle only)", "steps": [
        ("Take the bag off (procedure above).", None),
        ("Set the quarter in the two under-straps, bone toward the spreader. Cam them until the belly is about 70 mm.", 12),
        ("Hook IM1-IM3 eye to eye over the meat and cam them. A hock can sit on IM1.", 24),
        ("Fold the empty bag flat and strap it over the crown with W3.", 20)]},
    "repair": {"title": "Field repair kit (hipbelt pocket)", "steps": [
        ("Lost hinge pin: fit the spare 5 mm pin. No spare: 6 turns of the 3 mm cord through the eye and the cleat hole, double fisherman's knot.", 120),
        ("Broken bag hook: clip the spare hook on the tongue loop. No spare: 4 turns of cord through the tongue loop and the eye, knot.", 90),
        ("Cracked fairlead cleat: girth-hitch the 0.6 m of 38 mm webbing round the stay above the cleat and clip the hook (or the eye) to it.", 120),
        ("Lost hood toggle: fit the spare toggle, or tie the tongue end through the next slot with cord.", 60),
        ("Torn hood: tie the hood ears to the top bar at x +/-70 with two turns of cord each. The guys still work (study candidate G).", 120),
        ("Clicking pin (oval sleeve): pin out, push the old UHMWPE sleeve out with the pin, press in the spare.", 180),
        ("Guy slipping: half hitch the tail round the ladder lock.", 15)]},
}
REPAIR_KIT = [("spare 5 mm 7075 pin with cord pull loop", 2.8), ("2 UHMWPE sleeves", 0.6), ("spare 38 mm bag hook (2.2 kN)", HOOK_RATED_G),
              ("3 mm Dyneema-core cord, 1.5 m", 1.5 * 5.5), ("38 mm webbing, 0.6 m", 0.6 * 28.0), ("spare POM toggle", TOGGLE_G)]


def procedure_times() -> dict:
    off = sum(t for _, t in PROCEDURES["bag_off"]["steps"])
    return {k: int(sum(off if t is None else t for _, t in v["steps"])) for k, v in PROCEDURES.items()}


def _step_s(t) -> int:
    return int(sum(t_ for _, t_ in PROCEDURES["bag_off"]["steps"])) if t is None else int(t)


# ================================================================ quiet (research 3.4 noise sources as the checklist)
QUIET = [
    ("dry webbing and buckles", "No side-release buckle anywhere in the joint. Only plastic: two guy ladder locks (set once, "
     "on the outer face, touching fabric only) and two POM toggles buried in webbing. Captive eyes and the hood lip are "
     "rubbed with paraffin at assembly (owners' wax fix)."),
    ("webbing loops at the frame", "Captive eyes sit on pins in UHMWPE sleeves in an 18 mm throat; the bag hooks are loaded "
     "whenever the bag is on, and hang on elastic keepers when it is off. Hooks keep their TPU sleeves. The B-24 float "
     "links ride in a pocket except in float mode, where the hanging bag keeps their hooks loaded."),
    ("frame rails rubbing inside the bag", "No frame part is inside the bag. B-01 keeps 2 mm of air over every cleat (swells). "
     "The hood is outside the bag, on the bar, and does not slide in use."),
    ("dirt in frame joints", "The hood is open at the bottom and the ladder slots drain. Pins and sleeves are field spares."),
    ("cold fabric", "Hypalon and HDPE stay flexible; PT-4 is repeated at -10 C."),
    ("hard part taps a hard part when empty", "Pull-pins have Dyneema cord loops, not metal rings. The hood crown rests on the bar "
     "at every setting (one rung per setting) and is lined with 3 mm XLPE where it touches. Toggles are inside webbing."),
    ("sliding cloth on the stays", "Nothing bears on the stays: the spreader takes the meat, the swells clear the cleats, the hood "
     "seats on the bar and moves only when the torso setting changes."),
    ("pin rattle", "Sleeve pressed into the cheek, silicone washer under the pull loop. Replace the sleeve when the eye clicks or "
     "has felt play (about 0.3 mm); spare sleeves are in the repair kit."),
    ("hook-and-loop in the opening path", "None in the joint (no hook-and-loop anywhere in hunt mode)."),
]


# ================================================================ patent guardrails (research section 2; not a legal opinion)
PATENTS = [
    ("US 12,495,885 (Eberlestock, load sling)", "Under-straps US1/US2 run frame pin to frame pin (eye on the left pin, cam on the "
     "right pin) through channels sewn on the bag floor. No separate fabric shelf panel, and no strap ends on the bag. The hood "
     "is above the bag top and is not a sling. Float mode (2026-11-06): the meat sits on those frame-to-frame straps; the two "
     "B-24 links run from the IM3 eyes (z 520, above the meat floor) to the bag's T3 hooks, and there is no fabric panel "
     "between frame and bag for any strap to run under.", "compliant as drawn; FTO read still required before release"),
    ("US 10,952,523 (Mystery Ranch, pop-up frame)", "Load lifters stay on the crown corner wraps at every setting and in every mode. "
     "The 'lifters as anchor' option (L19) would route the lifter to the bag in bag-on and to the frame in bag-off: that is "
     "the switching the claim describes, so it is rejected whatever its CG. The hood sits on the crown bar but is not a "
     "lifter connector.", "compliant"),
    ("US 8,381,956 (Mystery Ranch, membrane + stay gap, est. to 2027)", "No bag tab or strap is tucked between the spreader and the "
     "z 330 cross member. The IM2 tongue reaches the IM2 eye at the stay face through the spreader's 30 mm edge notch, aft "
     "of the spreader; nothing goes behind the spreader.", "compliant"),
    ("US 8,579,171 / 8,348,114 (Mystery Ranch, expired per Google)", "Their description includes a collar with an inverted pocket "
     "over the frame top. The crown hood is that family of idea (public domain if expired).", "confirm expiry in the FTO read"),
]
ORIGINAL_IP = ("The hood is a single J-profile Hypalon cap between the crown legs, on a woven one-rung-per-setting ladder, "
               "with the guys sewn to its ears. It is not KUIU's Hypalon stay pockets, Initial Ascent's slots or a Mystery "
               "Ranch frame cap, and copies no brand's hardware layout, shape, colour or name.")


# ================================================================ frame interface (no new printed features)
def frame_interface(F: dict) -> list:
    return [
        "No new printed feature and no edit to `print/frame`. The hood uses the existing carbon crown top bar.",
        f"Crown top bar (2026-11-06, replaces 'bare x +/-96'): the corner wraps stay as built (x +/-77 to +/-107, OD ~19.5). "
        f"The hood's lip, stiffener and lining bear on bare OD 18 +/- 0.3 bar over x +/-{HOOD['lip_half']:.0f} only "
        f"({wrap_clearance()['lip_margin_to_wrap_mm']:.0f} mm clear of the wrap step with the hood floated "
        f"{wrap_clearance()['hood_float_mm']:.0f} mm to one leg); keep x +/-75 free of any bonded lug, label or tape.",
        f"New load on the crown top bar (factored, HA-LS-1 x 3.0): hood capture {F['hood_capture_per_side'] * 2:.0f} N total, "
        f"spread over x +/-{HOOD['lip_half']:.0f} on the bar's wearer-side face, pointing aft "
        f"({F['hood_capture_per_side'] * 2 / (2 * HOOD['lip_half']):.2f} N/mm, was 0.83 over x +/-95); each guy "
        f"{F['guy']:.0f} N, from the hood ear at x +/-95 pointing aft and outboard toward the face corner (x +/-149, z 752), "
        f"now reaching the bar through the hood shell and the lip (x +/-{HOOD['lip_half']:.0f}), not at the ear. Nothing "
        "bears on the wraps. Add both to the C1/C5 re-check with the bag CG below.",
        "Bag CG envelope for the frame re-check, chosen system (1 g sim, +/-5 mm on fill): see the 'Top anchor' table; "
        "worst is the 15 in setting.",
    ] + float_interface(F)


def float_interface(F: dict) -> list:
    """Float mode (owner 2026-11-06): new IM3 eye load for the structural hand-off (meat_haul_modes.json 'float')."""
    from huntkit.gendesign import meat_haul as MH
    t, te = MH.link_tension(MH.FLOAT_GEAR_KG), MH.link_tension(MH.FLOAT_BAG_ENVELOPE_KG)
    a = math.radians(MH.LINK_ANGLE_DEG)
    cinch = 150.0 * 1.5
    eye = math.hypot(cinch + t * math.cos(a), t * math.sin(a))
    eye_e = math.hypot(cinch + te * math.cos(a), te * math.sin(a))
    return [f"Float mode (2026-11-06, replaces the hinge swing): each IM3 captive eye carries its meat-strap leg "
            f"({cinch:.0f} N aft, factored hand cinch) plus one B-24 link ({t:.0f} N factored, {MH.LINK_ANGLE_DEG:.0f} deg below "
            f"horizontal, aft and down; {MH.FLOAT_GEAR_KG:.0f} kg bag): resultant {eye:.0f} N per side. Misuse envelope "
            f"({MH.FLOAT_BAG_ENVELOPE_KG:.0f} kg in the bag): link {te:.0f} N, eye {eye_e:.0f} N per side, below the "
            f"{F['im3']:.0f} N bag-hook case the IM3 eye already carries in bag-on. The hinge pins carry "
            "nothing in float mode. Full list: analysis/meat_carry_alternatives.md section 8."]


# ================================================================ pattern-maker hand-off
HANDOFF = [
    ("B-01 (lower)", "Mark B-23 backing placements INSIDE at x +/-115, z 260, centred on the existing 'im2 bag-hook strap box-X' "
     "drill marks. No outline change."),
    ("B-01b / B-01u", f"Mark the two B-20 ladder strips OUTSIDE, centred x +/-{LADDER['x']:.0f}, z {LADDER['z_lo']:.0f}-"
     f"{LADDER['z_lo'] + LADDER['h']:.0f}, both long-edge stitch lines (3 and 9 mm in) and the end bartacks. They cross the "
     "B-01|B-01b and B-01b|B-01u seams: sew after the three tiers are joined, before B-01 joins B-03. No outline change."),
    ("B-02d", f"Mark the B-22 corner tabs OUTSIDE at x +/-{GUY['bag_xz'][0]:.0f}, z {GUY['bag_xz'][1]:.0f} and the ladder-lock "
     "tab box-X. Sew before B-02d joins the collar."),
    ("B-17, B-18", "Unchanged (2026-11-05). B-17 now carries tongue T3 for the rated hook."),
    ("B-19 / B-19s / B-19L (rev 2026-11-06)", f"Hood lip relieved: the lip, J-curl and hem exist only over the centre "
     f"{2 * HOOD['lip_half']:.0f} mm (x +/-{HOOD['lip_half']:.0f}); the outer {HOOD['width'] / 2 - HOOD['lip_half']:.0f} mm each "
     "side ends at fold 2 with an R4 root. Back ply, crown, ears and the 190 mm shell width are unchanged. B-19s HDPE "
     f"180 -> {HOOD['lip_stiff'][0]:.0f} mm, B-19L XLPE 180 -> {HOOD['lining'][0]:.0f} mm. Blank outline, fold 2 and hem lines "
     "redrawn in cut/attachment/attachment_parts.pdf / .dxf."),
    ("new pieces", "B-19 hood shell (Hypalon, laser-cut, fold lines etched), B-19s lip stiffener (HDPE 1.5), B-19L lining "
     "(XLPE 3), B-20 x2 ladder strips (Hypalon, 17 slots), B-22 x2 corner tabs, B-23 x2 IM2 backings. No seam allowance "
     "(laser-cut, edge-stitched). True-scale in cut/attachment/attachment_parts.pdf / .dxf."),
    ("webbing cut list", f"add: HT hood tongues 2 x 25 mm x {TONGUE_25:.0f}; TG guys 2 x 25 mm x {GUY['cut_mm']:.0f}; "
     "ladder-lock tabs 2 x 25 mm x 70; hood grab tab 1 x 25 mm x 90; B-24 float links 2 x 38 mm x 435 (2026-11-06). "
     "Unchanged: HE 2 x 38 x 150, T2/T3 4 x 38 x 160."),
    ("hardware list", f"bag hooks 4 x 38 mm rated >= {HOOK_RATED_N:.0f} N (replaces the 1500 N assumption on the bag hooks only; "
     "the meat-strap hooks are unchanged); 2 x POM toggle; 2 x 25 mm ladder lock; 2 x tri-glide; Dyneema cord pull loops "
     "replace the metal rings on the two hinge pins; 2 more rated 38 mm hooks on the B-24 float links (2026-11-06)."),
]


# ================================================================ 1:1 detail drawings (PDF + DXF)
def _box_x_lines(p, cx, cy, w, h, label):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    p.add_internal_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "stitch", f"{label} box-X {w:.0f}x{h:.0f}", closed=True)
    p.add_internal_line([(x0, y0), (x1, y1)], "stitch", "")
    p.add_internal_line([(x1, y0), (x0, y1)], "stitch", "")


def _rows(p, w, h, insets, label):
    for i, d in enumerate(insets):
        p.add_internal_line([(d, d), (w - d, d), (w - d, h - d), (d, h - d)], "stitch",
                            f"{label} row {i + 1} ({d:g} mm in)" if label else "", closed=True)


def drawing_pieces() -> list:
    from huntkit.patterns import Piece, rect_panel
    P = []
    hyp, hdpe, xlpe = "hypalon_coated_nylon", "hdpe_sheet", "xlpe_foam"
    note = "laser-cut, no seam allowance"
    # B-17 / B-18 (2026-11-05, repeated here so the joint has one drawing)
    b17 = rect_panel("IM3 bag-hook tab", 90, 110, 6.0, piece_id="B-17", material_id=hyp, quantity=2, seam_allowance_mm=0.0,
                     labels={"note": f"{note}; OUTSIDE B-01, centre x +/-115 z 450; tongue T3 box-X at centre"})
    _rows(b17, 90, 110, (3, 9), "perimeter 301 tex90 8 SPI")
    _box_x_lines(b17, 45, 55, 38, 38, "T3 tongue, 301 tex135 7 SPI")
    P.append(b17)
    b18 = rect_panel("hinge-eye doubler", 90, 45, 6.0, piece_id="B-18", material_id=hyp, quantity=2, seam_allowance_mm=0.0,
                     labels={"note": f"{note}; INSIDE B-01, lower edge in the B-01|B-05 seam; eye HE box-X at centre"})
    _rows(b18, 90, 45, (3, 9), "perimeter")
    _box_x_lines(b18, 45, 22.5, 38, 38, "HE eye")
    P.append(b18)
    # B-19 hood shell: x across (0..190), v along the profile from the back-ply bottom edge
    H = HOOD
    W = H["width"]
    v = np.cumsum([0.0, H["back"], H["crown"], H["lip"], H["curl"], H["hem"]])   # + hem over the stiffener
    L = float(v[-1])
    ev = H["back"] - 4.0                       # ears on the back ply, just under fold 1
    # lip relief (2026-11-06): lip, J-curl and hem only over x W/2 +/- lip_half (bare bar), R4 roots at fold 2
    xl, xr, v2, rr = W / 2 - H["lip_half"], W / 2 + H["lip_half"], float(v[2]), H["relief_r"]
    arc = lambda cx, cy, a0, a1: [(cx + rr * math.cos(math.radians(t)), cy + rr * math.sin(math.radians(t)))
                                  for t in np.linspace(a0, a1, 5)]
    out = ([(0, 0), (W, 0), (W, ev - H["ear_h"]), (W + H["ear_w"], ev - H["ear_h"] + 6), (W + H["ear_w"], ev - 6), (W, ev),
            (W, v2)] + arc(xr + rr, v2 + rr, 270, 180) + [(xr, L), (xl, L)] + arc(xl - rr, v2 + rr, 0, -90)
           + [(0, v2), (0, ev), (-H["ear_w"], ev - 6), (-H["ear_w"], ev - H["ear_h"] + 6), (0, ev - H["ear_h"])])
    b19 = Piece("crown hood shell", outline=out, grain=90.0, seam_allowance_mm=0.0, material_id=hyp, quantity=1,
                piece_id="B-19", labels={"note": f"{note}; fold 1 back|crown, fold 2 crown|lip on a 19 mm dowel; "
                                                  "lip hem 14 mm over B-19s; B-19L glued inside the crown"})
    b19.add_internal_line([(0, v[1]), (W, v[1])], "fold", "fold 1: back | crown")
    for vv, lab in zip(v[2:-1], ("fold 2: crown | lip (lip on bare bar only)", "J-curl start", "hem fold over B-19s")):
        b19.add_internal_line([(xl, vv), (xr, vv)], "fold", lab)
    b19.add_internal_line([(xl + 3, L - 3), (xr - 3, L - 3)], "stitch", "hem 301 tex90, 3 mm from edge")
    for x0 in (xl - 4, xr + 4):
        b19.add_internal_line([(x0, v2 + 2), (x0, v2 + 10)], "placement",
                              f"relief: clears the crown corner wrap (x +/-{WRAP['x_start']:.0f} out)")
    for sx in (-1, 1):
        _box_x_lines(b19, W / 2 + sx * LADDER["x"], 15.0, 25, 25, "tongue HT")
        _box_x_lines(b19, (W + H["ear_w"] / 2) if sx > 0 else -H["ear_w"] / 2 + 0.0, ev - H["ear_h"] / 2, 22, 25, "guy TG")
    _box_x_lines(b19, W / 2, v[1] + H["crown"] / 2, 25, 20, "grab tab")
    lh = H["lining"][0] / 2
    b19.add_internal_line([(W / 2 - lh, v[1] + 3), (W / 2 + lh, v[1] + 3), (W / 2 + lh, v[2] - 3), (W / 2 - lh, v[2] - 3)],
                          "placement", "B-19L lining (inside, bare-bar zone only)", closed=True)
    P.append(b19)
    s0 = rect_panel("hood lip stiffener", H["lip_stiff"][0], H["lip_stiff"][1], 3.0, piece_id="B-19s", material_id=hdpe,
                    quantity=1, seam_allowance_mm=0.0, labels={"note": "HDPE 1.5 mm; heat-form the J round a 19 mm dowel at the line; "
                                                         "centred in the relieved lip (ends 2 mm inside the relief roots)"})
    s0.add_internal_line([(0, 12), (H["lip_stiff"][0], 12)], "fold", "J bend (heat-form)")
    P.append(s0)
    P.append(rect_panel("hood lining", H["lining"][0], H["lining"][1], 0.0, piece_id="B-19L", material_id=xlpe, quantity=1,
                        seam_allowance_mm=0.0, labels={"note": "XLPE 3 mm, contact cement inside the crown, centred: bare-bar zone "
                                                                       "only (holds the crown 2.2 mm off the wraps)"}))
    # B-20 ladder strip: 17 slots, one per crown setting
    lw, lh = LADDER["w"], LADDER["h"]
    b20 = rect_panel("hood ladder strip", lw, lh, 3.0, piece_id="B-20", material_id=hyp, quantity=2, seam_allowance_mm=0.0,
                     labels={"note": f"{note}; OUTSIDE B-01b/B-01u at x +/-{LADDER['x']:.0f}, bottom edge z {LADDER['z_lo']:.0f}; "
                                     "rung k = crown setting k (15.0 in = 0 ... 23.0 in = 16)"})
    sw, sh = LADDER["slot"]
    for k in range(LADDER["rungs"]):
        zc = LADDER["slot0_z"] + k * LADDER["pitch"] - LADDER["z_lo"]
        b20.add_internal_line([((lw - sw) / 2, zc - sh / 2), ((lw + sw) / 2, zc - sh / 2), ((lw + sw) / 2, zc + sh / 2),
                               ((lw - sw) / 2, zc + sh / 2)], "cut_inside", f"slot {k} ({15 + k / 2:.1f} in)", closed=True)
    for d in (2.0, 5.0):
        for x in (d, lw - d):
            b20.add_internal_line([(x, 2.0), (x, lh - 2.0)], "stitch", f"edge row {d:g} mm, 301 tex90 8 SPI")
    for y in (4.0, lh - 4.0):
        b20.add_internal_line([(3.0, y), (lw - 3.0, y)], "stitch", "end bartack 304")
    P.append(b20)
    b22 = rect_panel("guy corner tab", 50, 60, 6.0, piece_id="B-22", material_id=hyp, quantity=2, seam_allowance_mm=0.0,
                     labels={"note": f"{note}; OUTSIDE B-02d at x +/-{GUY['bag_xz'][0]:.0f} z {GUY['bag_xz'][1]:.0f}"})
    _rows(b22, 50, 60, (3, 9), "perimeter")
    _box_x_lines(b22, 25, 30, 25, 25, "ladder-lock tab")
    P.append(b22)
    b23 = rect_panel("IM2 tongue backing", 60, 60, 6.0, piece_id="B-23", material_id=hyp, quantity=2, seam_allowance_mm=0.0,
                     labels={"note": f"{note}; INSIDE B-01 at x +/-115 z 260"})
    _rows(b23, 60, 60, (3,), "perimeter")
    _box_x_lines(b23, 30, 30, 38, 38, "T2 tongue (through B-01)")
    P.append(b23)
    # webbing parts (cut lengths, folds, box-X)
    for pid, name, w, L_, qty, mat, folds, boxes, nt in (
            ("HE", "hinge eye", 38, 150, 2, "poly_webbing_38mm", [(50, "fold back (eye)"), (100, "fold")],
             [(125, 38, "box-X through B-18 + B-01")], "neck: tri-fold the first 30 mm to 18 mm, bartack"),
            ("T2/T3", "bag-hook tongue", 38, 160, 4, "poly_webbing_38mm", [(45, "fold round the hook bed")],
             [(22, 30, "loop box-X"), (130, 38, "box-X to B-01/B-23 (T2) or B-17 (T3)")], ""),
            ("HT", "hood tongue", 25, TONGUE_25, 2, "poly_webbing_25mm", [(30, "fold over the POM toggle")],
             [(15, 22, "toggle box"), (100, 25, "box-X to B-19")], "weave: in slot k, out slot k+1"),
            ("TG", "top side guy", 25, GUY["cut_mm"], 2, "poly_webbing_25mm", [], [(20, 25, "box-X on the hood ear")],
             "free end through ladder lock + tri-glide on B-22; heat-seal"),
            ("LLT", "ladder-lock tab", 25, 70, 2, "poly_webbing_25mm", [(35, "fold round the ladder lock bar")],
             [(52, 25, "box-X through B-22 + B-02d")], ""),
            ("GT", "hood grab tab", 25, 90, 1, "poly_webbing_25mm", [(45, "fold (35 mm loop)")], [(75, 20, "box-X on B-19")], "")):
        p = rect_panel(name, w, L_, 0.0, piece_id=pid, material_id=mat, quantity=qty, seam_allowance_mm=0.0,
                       labels={"note": f"hot-knife cut; {nt}".rstrip("; ")})
        for y, lab in folds:
            p.add_internal_line([(0, y), (w, y)], "fold", lab)
        for y, hb, lab in boxes:
            _box_x_lines(p, w / 2, y, w - 4, hb, lab)
        P.append(p)
    P.append(link_piece())
    return P


def link_piece():
    """B-24 float-mode stand-off link, flat cut with fold and stitch lines (owner 2026-11-06, meat_haul.LINK).
    Cut coordinate c from the hook end. The hook end folds at c = hook_fold round the hook bed (finished 0). Loop k is
    pinched from the next loop_fold mm of webbing: it starts at s_k, its apex fold (where the T3 hook sits) is at
    s_k + loop_fold / 2, i.e. at the gap distance g_k from the hook bed in the finished link, and it is closed by a
    38 x 20 box-X across both plies at its base."""
    from huntkit.gendesign import meat_haul as MH
    from huntkit.patterns import rect_panel
    L_ = MH.LINK
    w, cut, hf, lf = L_["w_mm"], MH.link_cut_mm(), L_["hook_fold_mm"], L_["loop_fold_mm"]
    p = rect_panel("float-mode stand-off link", w, cut, 0.0, piece_id=L_["id"], material_id="poly_webbing_38mm",
                   quantity=2, seam_allowance_mm=0.0,
                   labels={"note": "hot-knife cut, heat-seal both ends; rated 38 mm hook (same part as the bag hooks) on the "
                                   "hook-end fold; 301 tex135 7 SPI"})
    p.add_internal_line([(0, hf), (w, hf)], "fold", "fold round the hook bed (finished 0)")
    _box_x_lines(p, w / 2, hf / 2, w - 4, 30, "hook box-X 38")
    for k, g_ in enumerate(MH.FLOAT_GAPS_MM):
        s_ = hf + (g_ - lf / 2) + lf * k
        p.add_internal_line([(0, s_), (w, s_)], "fold", f"loop {k + 1} start")
        p.add_internal_line([(0, s_ + lf / 2), (w, s_ + lf / 2)], "fold", f"loop {k + 1} apex: gap {g_:.0f} mm "
                            f"({g_ / 25.4:.1f} in) - T3 hook sits here")
        p.add_internal_line([(0, s_ + lf), (w, s_ + lf)], "fold", f"loop {k + 1} end (meets start)")
        _box_x_lines(p, w / 2, s_ - 11, w - 4, 20, f"loop {k + 1} base box-X 38 x 20 (both plies, after folding)")
    return p


def export_drawings(log=print) -> dict:
    from huntkit.patterns import export_dxf, export_pdf_tiled
    CUT.mkdir(parents=True, exist_ok=True)
    P = drawing_pieces()
    pdf = CUT / "attachment_parts.pdf"
    dxf = CUT / "attachment_parts.dxf"
    export_dxf(P, dxf)
    info = export_pdf_tiled(P, pdf, paper="letter", title="Pack 5200 bag-to-frame attachment: sewn parts, 1:1",
                            compress=True)
    log(f"  drawings {pdf} ({info.get('pages')} pages), {dxf}")
    return {"pdf": str(pdf.relative_to(REPO)), "dxf": str(dxf.relative_to(REPO)), "pages": info.get("pages"),
            "pieces": [p.piece_id for p in P]}


# ================================================================ screenshots (phone-readable PNG <= 1.5 MB)
def _save(fig, name: str) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    path = SCREENS / name
    fig.savefig(path, dpi=110)
    plt.close(fig)
    try:
        from huntkit.clothsim.report import shrink_png
        shrink_png(path)
    except Exception:  # noqa: BLE001
        pass
    return str(path.relative_to(REPO))


def _hood_profile(yc: float, zc: float):
    """Side section of the hood on a bar centred (yc, zc): y aft, z up. Returns (y, z) polyline (inner face)."""
    d = HOOD["depth"]
    pts = [(yc + 9 + d, zc - 40), (yc + 9 + d, zc + 11), (yc - 11, zc + 11), (yc - 11, zc - 6),
           (yc - 9, zc - 13), (yc - 4, zc - 17)]
    return np.array(pts)


def plot_exploded() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 10), gridspec_kw={"width_ratios": [1.25, 1]})
    # --- left: frame side of the bag (B-01 seen from the frame), parts pulled toward the viewer
    a1.add_patch(mp.Rectangle((-160, 35), 320, 740, fc="#ece7db", ec="#6b6252", lw=1.2))
    a1.add_patch(mp.Rectangle((-160, 775), 320, 300, fc="#f5f3ee", ec="#6b6252", lw=1, ls="--"))
    for zs, lab in ((560, "setback seam z 560"), (631.2, "shoulder seam z 631")):
        a1.plot([-160, 160], [zs, zs], color="#6b6252", lw=0.8, ls=":")
        a1.text(-170, zs, lab, ha="right", va="center", fontsize=9, color="#6b6252")
    a1.add_patch(mp.Rectangle((-121, 112), 242, 318, fc="#2b2e33", alpha=0.12, ec="#2b2e33", ls="--"))
    a1.text(0, 140, "spreader (frame side,\nnot on the bag)", ha="center", fontsize=9, color="#2b2e33")
    for sx in (1, -1):
        a1.add_patch(mp.Rectangle((sx * 115 - 45, 35), 90, 45, fc="#b03a2e", alpha=0.85, ec="k"))           # B-18
        a1.add_patch(mp.Rectangle((sx * 115 - 19, 50), 38, 25, fc="#d9d2c0", ec="k"))                      # HE
        a1.add_patch(mp.Rectangle((sx * 115 - 30, 230), 60, 60, fc="#8e6c8a", alpha=0.8, ec="k"))           # B-23
        a1.add_patch(mp.Rectangle((sx * 115 - 45, 395), 90, 110, fc="#c27c0e", alpha=0.85, ec="k"))         # B-17
        for zt, zl in ((260, 330), (450, 520)):
            a1.plot([sx * 115] * 2, [zt, zl], color="#4b3a1a", lw=7, solid_capstyle="butt")
            a1.plot(sx * 115, zl, "o", ms=12, mfc="#9aa0a6", mec="k")
        a1.plot(sx * 115, 60, "o", ms=10, mfc="#444", mec="k")
        a1.add_patch(mp.Rectangle((sx * LADDER["x"] - 20, LADDER["z_lo"]), 40, LADDER["h"], fc="#1f1f1f", alpha=0.75, ec="k"))
    for k in range(0, 17, 4):
        a1.text(0, LADDER["slot0_z"] + k * 12.7, f"rung {k}", ha="center", va="center", fontsize=7.5, color="#333")
    # hood (exploded upward at the 19 in bar)
    zb = TORSO_Z[19]
    a1.add_patch(mp.FancyBboxPatch((-95, zb - 40 + 120), 190, 51, boxstyle="round,pad=2", fc="#2e6fb0", alpha=0.9, ec="k"))
    a1.text(0, zb + 105, "B-19 crown hood\n(exploded up)", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
    a1.annotate("", (0, zb + 15), (0, zb + 78), arrowprops=dict(arrowstyle="-|>", lw=2, color="#2e6fb0"))
    a1.plot([-115, 115], [zb, zb], color="#5b6068", lw=6, alpha=0.7)
    a1.text(125, zb, "crown top bar\n(19 in, z 703)", va="center", fontsize=9)
    for sx in (1, -1):
        a1.plot([sx * 95, sx * 150], [zb + 140, zb + 49], color="#1e8a4c", lw=3)
        a1.add_patch(mp.Rectangle((sx * 149 - 25, 722), 50, 60, fc="#1e8a4c", alpha=0.5, ec="k"))
    L = dict(fontsize=9.5, va="center")
    a1.text(175, 57, "HE hinge eye on B-18\n(tethered 5 mm pin, z 60)", **L)
    a1.text(175, 260, "T2 tongue + B-23 backing\n(bag hook on IM2 eye, z 330)", **L)
    a1.text(175, 450, "T3 tongue on B-17\n(rated hook on IM3 eye, z 520)", **L)
    a1.text(175, 640, "B-20 ladder strips x2\n(17 rungs, one per setting)", **L)
    a1.text(175, 790, "TG top guys -> B-22\non the outer face corners", color="#1e8a4c", **L)
    a1.set_xlim(-330, 360)
    a1.set_ylim(0, 1000)
    a1.set_aspect("equal")
    a1.set_title("Frame panel B-01, seen from the frame (parts pulled toward you)", fontsize=12)
    a1.set_xlabel("x mm")
    a1.set_ylabel("z mm")
    # --- right: side view of the stack, bottom to top
    sys.path.insert(0, str(PACK))
    from bag_top_anchor import frame_side   # noqa: E402
    frame_side(a2)
    a2.add_patch(mp.Polygon([[19, 35], [19, 560], [49, 631], [49, 1101], [330, 1101], [339, 600], [300, 35]],
                            closed=True, fc="#ece7db", ec="#6b6252", alpha=0.6))
    hp = _hood_profile(TORSO_BAR_Y[19], zb)
    a2.plot(hp[:, 0], hp[:, 1], color="#2e6fb0", lw=3.5)
    a2.plot([TORSO_BAR_Y[19] + 9 + HOOD["depth"], 293], [zb - 10, 752], color="#1e8a4c", lw=2.5)
    for z, lab, col in ((60, "hinge pin", "#444"), (95, "US1", "#7a4fb0"), (142, "US2", "#7a4fb0"), (330, "IM2 hook", "#4b3a1a"),
                        (520, "IM3 hook (rated)", "#4b3a1a")):
        a2.plot(12, z, "o", ms=8, mfc=col, mec="k")
        a2.text(-55, z, lab, ha="right", va="center", fontsize=9, color=col)
    a2.annotate("crown hood", (TORSO_BAR_Y[19], zb + 12), (-140, zb + 90), color="#2e6fb0", fontsize=10,
                fontweight="bold", arrowprops=dict(arrowstyle="-", color="#2e6fb0"))
    a2.text(170, 700, "top guy (outside\nthe side gore)", color="#1e8a4c", fontsize=10)
    a2.set_xlim(-150, 380)
    a2.set_ylim(0, 1110)
    a2.set_aspect("equal")
    a2.set_title("Side view, 19 in: the stack bottom to top", fontsize=12)
    a2.set_xlabel("y mm aft")
    fig.suptitle("Bag-to-frame attachment, exploded: hinge eye, under-straps, IM2/IM3 hooks, crown hood, top guys",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_1.png")


def plot_hood_detail() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 7.2), gridspec_kw={"width_ratios": [1.1, 1.1, 1]})
    # (a) section on the bar, seated and while closing
    ax = axs[0]
    yc, zc = 0.0, 0.0
    ax.add_patch(mp.Circle((yc, zc), 9, fc="#5b6068"))
    hp = _hood_profile(yc, zc)
    ax.plot(hp[:, 0], hp[:, 1], color="#2e6fb0", lw=4)
    ax.plot([yc + 9 + HOOD["depth"] + 1.5] * 2, [-60, 30], color="#6b6252", lw=3)
    ax.text(yc + 9 + HOOD["depth"] + 5, -55, "B-01 + ladder", fontsize=9, color="#6b6252")
    ax.annotate("lip: 1 ply in front\nof the bar (+1 mm)", (-11, 2), (-75, 20), fontsize=9, arrowprops=dict(arrowstyle="-"))
    ax.annotate("J-curl, HDPE B-19s\n(below the bar centre)", (-6, -15), (-75, -40), fontsize=9, arrowprops=dict(arrowstyle="-"))
    ax.annotate("crown + 3 mm XLPE", (5, 11), (-10, 35), fontsize=9, arrowprops=dict(arrowstyle="-"))
    ax.annotate("", (14, 0), (40, 0), arrowprops=dict(arrowstyle="<|-", lw=2, color="#b03a2e"))
    ax.text(30, 4, "bag peel", color="#b03a2e", fontsize=9)
    ax.set_xlim(-90, 75)
    ax.set_ylim(-70, 50)
    ax.set_aspect("equal")
    ax.set_title("(a) Hood on the top bar: section", fontsize=11)
    ax.set_xlabel("y mm (aft +)")
    # (b) why it cannot snap on as the bag closes: kinematics
    ax = axs[1]
    r = 643.0
    for th in (0, 10, 20, 29):
        t = np.radians(th)
        y, z = -r * np.sin(t), r * np.cos(t) - r
        ax.add_patch(mp.Circle((y, z), 9, fc="#5b6068", alpha=0.6 if th else 1.0))
        ax.text(y, z + 14, f"{th} deg open", ha="center", fontsize=8.5)
    ax.plot(_hood_profile(0, 0)[:, 0], _hood_profile(0, 0)[:, 1], color="#2e6fb0", lw=3)
    ax.annotate("", (-14, -1), (-100, -8), arrowprops=dict(arrowstyle="-|>", lw=2, color="#444"))
    ax.text(-330, -175, "Where the top bar is, seen from the bag, as the bag is tipped\nonto the frame on its z 60 pins "
            "(radius 643 mm, bag-on only). It arrives\nlevel, from the wearer side, so the lip is in its way: capture is in the\n"
            "closing direction. Any part that stops peel also blocks closing.\nSo the hood is lifted 25 mm by its tab and dropped on.",
            fontsize=9)
    ax.set_xlim(-340, 70)
    ax.set_ylim(-185, 45)
    ax.set_aspect("equal")
    ax.set_title("(b) Why it is lift-and-drop, not snap-on", fontsize=11)
    ax.set_xlabel("y mm, bag frame")
    # (c) ladder and torso settings
    ax = axs[2]
    ax.add_patch(mp.Rectangle((-20, LADDER["z_lo"]), 40, LADDER["h"], fc="#1f1f1f", alpha=0.8))
    for k in range(LADDER["rungs"]):
        z = LADDER["slot0_z"] + k * LADDER["pitch"]
        ax.add_patch(mp.Rectangle((-13.5, z - 2.5), 27, 5, fc="white"))
        if k % 2 == 0:
            ax.text(26, z, f"{15 + k / 2:.0f} in", va="center", fontsize=8.5)
    for t, col in ((15, "#c27c0e"), (19, "#2e6fb0"), (23, "#1e8a4c")):
        z = TORSO_Z[t]
        ax.plot([-70, -25], [z, z], color=col, lw=5)
        ax.text(-72, z, f"bar {t} in", ha="right", va="center", color=col, fontsize=9)
        ax.plot([-5, -5], [z - 40, z - 40 + 12.7], color=col, lw=4)
    ax.text(-10, LADDER["z_lo"] - 20, "tongue weaves in at rung k,\nout at k+1, POM toggle stops it",
            ha="center", fontsize=8.5)
    ax.set_xlim(-160, 80)
    ax.set_ylim(500, 840)
    ax.set_aspect("equal")
    ax.set_title("(c) B-20 ladder: one rung per setting", fontsize=11)
    fig.suptitle("Crown hood: drops over the top bar, holds B-01 against peel, slides to the torso setting on the ladder",
                 fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_2.png")


def plot_profiles(sims: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, str(PACK))
    from bag_top_anchor import frame_side   # noqa: E402
    fig, axs = plt.subplots(1, 3, figsize=(15, 8.4), sharey=True)
    for ax, t in zip(axs, (15, 19, 23)):
        frame_side(ax)
        ax.plot([-10, TORSO_BAR_Y[t] + 25], [TORSO_Z[t], TORSO_Z[t]], color="#5b6068", lw=5, alpha=0.7)
        sets = [("baseline", "#b03a2e", "before: no top anchor"), ("T0", "#9aa0a6", "tab + doubler only"),
                (f"PR{t}", "#1e8a4c", "after: hood + guys")]
        for key, col, lab in sets:
            f = SIMS / RUNS[key][0] / "results.json"
            if not f.exists():
                continue
            c = json.loads(f.read_text())["cases"]["fill"]
            for i, sg in enumerate(c["profile"]["section_x0_segments_yz"]):
                sg = np.asarray(sg)
                ax.plot(sg[:, 0], sg[:, 1], color=col, lw=2, label=lab if i == 0 else None)
            cg = c["volume"]["contents_cg_mm"]
            ax.plot(cg[1], cg[2], "o", ms=11, mfc=col, mec="white", mew=1.5)
            dy = {"baseline": -26, "T0": -8, f"PR{t}": 12}[key]
            ax.annotate(f"{cg[1]:.0f}", (cg[1], cg[2]), xytext=(10, dy), textcoords="offset points", color=col,
                        fontsize=11, fontweight="bold")
        ax.axvline(TARGET_CG, color="#1e8a4c", ls=":", lw=1.2)
        ax.text(TARGET_CG + 4, 40, "180 mm goal", rotation=90, fontsize=9, color="#1e8a4c")
        ax.set_title(f"{t} in torso (bar z {TORSO_Z[t]:.0f})", fontsize=12)
        ax.set_xlim(-60, 520)
        ax.set_ylim(-80, 1130)
        ax.set_aspect("equal")
        ax.grid(alpha=0.2)
        ax.set_xlabel("y mm aft of the frame")
    axs[0].set_ylabel("z mm")
    axs[0].legend(loc="upper right", fontsize=9)
    fig.suptitle("Cloth sim, 68 kg fill (HA-LS-1 C1), x = 0 section: before vs after. Dots = load CG (mm aft)",
                 fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_3.png")


def plot_storyboard() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    from huntkit.gendesign import meat_haul as MH
    gv = MH.FLOAT_VIEW_GAP_MM
    panels = [("1  Lift the hood tab, ease\nthe bag top 10 cm aft", "hood"),
              ("2  Unclip IM3 then IM2\nbag hooks (4)", "hooks"),
              ("3  Pop US1/US2 cams, slide the\nfloor off: straps stay = cradle", "cams"),
              ("4  Pull both hinge pins\n(tethered)", "pins"),
              ("5  Lift the bag clear\n(about 52 s so far)", "off"),
              ("6  Float: meat in the cradle,\nIM1-IM3 over it, B-24 on IM3", "links"),
              ("7  Bag upright behind the meat,\nT3 hooks in a loop, W1-W3", "float"),
              ("8  Bag on: pins, floor, hooks,\nthen drop the hood on", "on")]
    fig, axs = plt.subplots(2, 4, figsize=(15, 8.6))
    for ax, (title, key) in zip(axs.ravel(), panels):
        ax.set_xlim(-60, 440)
        ax.set_ylim(-60, 1060)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=10.5, loc="left")
        # frame
        ax.plot([0, 0], [0, 520], color="#5b6068", lw=6)
        ax.plot([-8, -8], [520, 703], color="#5b6068", lw=4)
        ax.add_patch(mp.Circle((12, 703), 9, fc="#5b6068"))
        ax.add_patch(mp.Rectangle((6, 112), 6, 318, fc="#2b2e33", alpha=0.5))
        ang = {"off": None, "links": None, "float": None}.get(key, 0)
        if key in ("hood",):
            ang = 8
        if ang is not None:
            t = np.radians(ang)
            R = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
            bag = np.array([[20, 35], [20, 560], [50, 631], [50, 1000], [330, 1000], [339, 600], [300, 35]], float)
            bag = (bag - [12, 60]) @ R.T + [12, 60]
            ax.add_patch(mp.Polygon(bag, closed=True, fc="#ece7db", ec="#6b6252", alpha=0.9))
            hz = (np.array([[37, 703]]) - [12, 60]) @ R.T + [12, 60]
            ax.add_patch(mp.Rectangle((hz[0, 0] - 8, hz[0, 1] - 20 + (25 if key == "hood" else 0)), 22, 32,
                                      fc="#2e6fb0", ec="k"))
        elif key == "float":
            ax.set_xlim(-60, 560)
            dy = gv
            ax.add_patch(mp.Polygon(np.array([[20, 35], [20, 560], [50, 631], [50, 1000], [330, 1000], [339, 600], [300, 35]],
                                             float) + [dy, 0], closed=True, fc="#ece7db", ec="#6b6252", alpha=0.9))
        elif key == "off":
            ax.add_patch(mp.Polygon([[150, 35], [150, 560], [180, 631], [180, 1000], [400, 1000], [409, 600], [380, 35]],
                                    closed=True, fc="#ece7db", ec="#6b6252", alpha=0.5, ls="--"))
            ax.annotate("", (300, 500), (190, 500), arrowprops=dict(arrowstyle="-|>", lw=2.5, color="#b03a2e"))
        if key == "hooks":
            for z in (330, 520):
                ax.plot(14, z, "o", ms=11, mfc="#c27c0e", mec="k")
        if key == "cams":
            for z in (95, 142):
                ax.plot([0, 120], [z, z - 40], color="#7a4fb0", lw=3)
        if key == "pins":
            ax.plot(12, 60, "o", ms=12, mfc="#b03a2e", mec="k")
        if key in ("links", "float"):
            ax.add_patch(mp.FancyBboxPatch((16, 70), gv - 4, 560, boxstyle="round,pad=0,rounding_size=30", fc="#8b3a3a",
                                           alpha=0.85))
            for z in (95, 142):
                ax.plot([0, gv / 2, gv], [z, z - 60, z - 40], color="#7a4fb0", lw=3)
            for z in (190, 330):
                ax.plot([12, gv + 6], [z, z + 10], color="#4b3a1a", lw=3)
            ax.plot([12, gv + 20], [520, 520], color="#c27c0e", lw=5)
            ax.text(20, 560, f"B-24 link, gap {gv:.0f} mm", fontsize=9, color="#c27c0e", fontweight="bold")
        if key == "float":
            for z in (165, 335, 703):
                ax.plot([0, gv + 340], [z, z + 25], color="#3b3b3b", lw=1.5, ls="--")
        if key == "on":
            ax.annotate("", (40, 700), (40, 760), arrowprops=dict(arrowstyle="-|>", lw=2.5, color="#2e6fb0"))
    times = procedure_times()
    fig.suptitle(f"Procedures, gloved (estimates): bag off {times['bag_off']} s (limit 120), bag on {times['bag_on']} s, "
                 f"float mode {times['float']} s, bag-off haul {times['bag_off_haul']} s",
                 fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_4.png")


def plot_drawing_preview(pdf_rel: str) -> str:
    """Phone preview of the 1:1 parts: the pieces drawn at a common scale (the PDF itself is tiled 1:1)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    P = drawing_pieces()
    fig, ax = plt.subplots(figsize=(15, 9))
    x0, y0, rowh = 0.0, 0.0, 0.0
    for p in P:
        poly = np.asarray(p.outline)
        w, h = np.ptp(poly[:, 0]), np.ptp(poly[:, 1])
        if x0 + w > 1150:
            x0, y0, rowh = 0.0, y0 - rowh - 60, 0.0
        off = np.array([x0 - poly[:, 0].min(), y0 - h - poly[:, 1].min()])
        q = poly + off
        ax.fill(q[:, 0], q[:, 1], fc="#ece7db" if "webbing" not in (p.material_id or "") else "#d8d0bb", ec="k", lw=1)
        for il in p.internal_lines:
            pts = np.asarray(il.points) + off
            if il.closed:
                pts = np.vstack([pts, pts[:1]])
            st = {"stitch": dict(color="#b03a2e", lw=0.7, ls="--"), "fold": dict(color="#2e6fb0", lw=1.0, ls="-."),
                  "cut_inside": dict(color="k", lw=0.8), "placement": dict(color="#1e8a4c", lw=0.7, ls=":")}[il.kind] \
                if il.kind in ("stitch", "fold", "cut_inside", "placement") else dict(color="#888", lw=0.5)
            ax.plot(pts[:, 0], pts[:, 1], **st)
        ax.text(x0, y0 + 8, f"{p.piece_id} x{p.quantity}", fontsize=10, fontweight="bold")
        x0 += w + 45
        rowh = max(rowh, h)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Sewn attachment parts (red dashed = stitch, blue = fold, black inside = cut). 1:1 file: {pdf_rel}",
                 fontsize=11)
    fig.tight_layout()
    return _save(fig, f"{DATE}_attach_5.png")


def plot_hood_relief(sims: dict) -> str:
    """2026-11-06: the relieved hood on the crown bar, seen from the wearer, with the corner wraps; plus the flat blank
    and the CG / R-28 of the re-run sims."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mp
    import matplotlib.pyplot as plt
    H, wc = HOOD, wrap_clearance()
    fig = plt.figure(figsize=(14, 9.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], width_ratios=[1.45, 1])
    ax = fig.add_subplot(gs[0, :])
    # bar, wraps, legs (front view, x across, z up; scale exaggerated in z for the OD step)
    ax.add_patch(mp.Rectangle((-WRAP["x_leg"], -BAR_OD / 2), 2 * WRAP["x_leg"], BAR_OD, fc="#5b6068", ec="k"))
    for sx in (-1, 1):
        xs, xf, xl_ = sx * WRAP["x_start"], sx * WRAP["x_full"], sx * WRAP["x_leg"]
        r = WRAP["od"] / 2
        poly = [(xs, -BAR_OD / 2), (xf, -r), (xl_, -r), (xl_, r), (xf, r), (xs, BAR_OD / 2)]
        ax.add_patch(mp.Polygon(poly, closed=True, fc="#222", ec="k", alpha=0.85))
        ax.add_patch(mp.Rectangle((sx * LEG_INNER_X if sx > 0 else -LEG_INNER_X - 16, -60), 16, 70 + r, fc="#5b6068", ec="k"))
        ax.text(sx * 92, -21, "corner wrap\nOD 19.5", ha="center", va="top", fontsize=9, color="#222")
    # hood shell (back/crown band) and the relieved lip
    ax.add_patch(mp.Rectangle((-H["width"] / 2, 10.5), H["width"], 5, fc="#2e6fb0", alpha=0.35, ec="#2e6fb0"))
    ax.text(0, 18, "hood shell 190 mm (back ply + crown): unchanged, ears and guys at x +/-95", ha="center", fontsize=10,
            color="#1d4f80")
    ax.add_patch(mp.Rectangle((-H["lip_half"], -13), 2 * H["lip_half"], 24, fc="#2e6fb0", alpha=0.75, ec="k"))
    ax.text(0, -4, f"lip + HDPE B-19s + XLPE lining: x +/-{H['lip_half']:.0f} on bare OD 18 bar", ha="center",
            color="white", fontsize=10.5, fontweight="bold")
    for sx in (-1, 1):
        e = sx * wc["lip_edge_worst_x_mm"]
        ax.plot([e, e], [-30, 12], color="#b03a2e", ls="--", lw=1.5)
        ax.annotate("", (sx * WRAP["x_start"], -27), (e, -27), arrowprops=dict(arrowstyle="<->", color="#b03a2e"))
    ax.text(0, -36, f"red dashed: lip edge with the hood floated {wc['hood_float_mm']:.0f} mm to one leg, still "
            f"{wc['lip_margin_to_wrap_mm']:.0f} mm short of the wrap step at x +/-{WRAP['x_start']:.0f}", fontsize=9.5,
            color="#b03a2e", ha="center")
    ax.set_xlim(-130, 130)
    ax.set_ylim(-45, 28)
    ax.set_aspect("equal")
    ax.set_xlabel("x mm across the crown top bar (seen from the wearer)")
    ax.set_yticks([])
    ax.set_title("B-19 crown hood, relieved over its outer 29 mm each side: nothing bears on the corner wraps", fontsize=12)
    # flat blank
    ax2 = fig.add_subplot(gs[1, 0])
    b19 = next(p for p in drawing_pieces() if p.piece_id == "B-19")
    o = np.asarray(b19.outline)
    o = np.vstack([o, o[:1]])
    ax2.fill(o[:, 0], o[:, 1], fc="#ece7db", ec="k")
    for il in b19.internal_lines:
        pts = np.asarray(il.points)
        if il.closed:
            pts = np.vstack([pts, pts[:1]])
        st = {"stitch": dict(color="#b03a2e", lw=0.8, ls="--"), "fold": dict(color="#2e6fb0", lw=1.2, ls="-."),
              "placement": dict(color="#1e8a4c", lw=0.8, ls=":")}.get(il.kind, dict(color="#888", lw=0.5))
        ax2.plot(pts[:, 0], pts[:, 1], **st)
    ax2.text(H["width"] / 2, -12, "B-19 blank (1:1 in cut/attachment): relief notches at the lip, R4 roots",
             ha="center", fontsize=9.5)
    ax2.set_aspect("equal")
    ax2.axis("off")
    # sims
    ax3 = fig.add_subplot(gs[1, 1])
    rows = [(t, sims.get(f"PG{t}"), sims.get(f"PR{t}")) for t in (15, 19, 23)]
    xs = np.arange(3)
    ax3.bar(xs - 0.2, [r[1]["fill"]["cg_y"] for r in rows], 0.38, color="#9aa0a6", label="full lip (11-05)")
    ax3.bar(xs + 0.2, [r[2]["fill"]["cg_y"] for r in rows], 0.38, color="#1e8a4c", label="relieved (11-06)")
    for i, r in enumerate(rows):
        ax3.text(i + 0.2, r[2]["fill"]["cg_y"] + 2, f"{r[2]['fill']['cg_y']:.0f}\nR-28 "
                 f"{min(r[2]['fill']['r28']['worst_contact_deg'], r[2]['meat']['r28']['worst_contact_deg']):.0f} deg",
                 ha="center", fontsize=9)
    ax3.axhline(TARGET_CG, color="k", ls="--", lw=1)
    ax3.set_xticks(xs, ["15 in", "19 in", "23 in"])
    ax3.set_ylim(140, 215)
    ax3.set_ylabel("load CG aft of the frame, 68 kg fill, mm")
    ax3.set_title("Cloth sim re-run: CG and head clearance hold", fontsize=11)
    ax3.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    return _save(fig, "20261106_backpanel_4.png")


# ================================================================ choose, record, render
def choose(sims: dict) -> dict:
    """Rank the top-anchor families on the worst torso they were run at, then the mean, then head margin."""
    fam = {}
    for k, v in sims.items():
        fam.setdefault(v["family"], []).append(k)
    rows = []
    for f, keys in fam.items():
        if f == "none":
            continue
        worst_fill = max(sims[k]["fill"]["cg_y"] for k in keys)
        worst_meat = max(sims[k]["meat"]["cg_y"] for k in keys)
        r28 = min(min(sims[k]["fill"]["r28"]["worst_contact_deg"], sims[k]["meat"]["r28"]["worst_contact_deg"]) for k in keys)
        rows.append({"family": f, "runs": keys, "torsos": sorted({sims[k]["torso_in"] for k in keys}),
                     "worst_fill_cg": worst_fill, "worst_meat_cg": worst_meat, "worst_r28_deg": r28})
    return {"families": rows, "chosen": CHOSEN}


def _pack_before(rows_group: str = "bag-to-frame attachment system") -> float:
    import yaml
    geo = yaml.safe_load((PACK / "geometry.yaml").read_text())
    w = geo["weight"]
    own = sum(r["mass_g"] for r in w.get("rows", w.get("lines", [])) if isinstance(r, dict) and r.get("group") == rows_group)
    return float(w["total_g"]) - own


def _cost(mass: dict) -> float:
    """Marginal material + hardware cost, USD (records' cost_usd; hook and toggle prices ASSUMPTION)."""
    yd2 = 0.9144 * 1.3716          # Hypalon priced per linear yard of a 54 in roll (record roll width)
    hyp_g = sum(v for k, v in mass["parts_g"].items() if "B-19 " in k or "B-20" in k or "B-22" in k or "B-23" in k)
    hyp_usd = hyp_g / 1000.0 / yd2 * 35.0
    web = (2 * GUY["cut_mm"] + 2 * TONGUE_25 + 2 * 70 + 90) / 1000.0 * 0.7
    hw = 2 * 0.4 + 2 * 0.3 + 2 * 0.5 + 4 * (6.0 - 3.5)       # ladder locks, tri-glides, toggles, hooks 6.00 vs 3.50
    return round(hyp_usd + web + hw + 1.0, 2)                  # + HDPE, XLPE, thread ~ $1


def run(log=print) -> dict:
    rec = json.loads((ANALYSIS / "bag_attachment_results.json").read_text())
    log("compile cloth-sim runs")
    sims = compile_sims(log)
    ref = r28_design_reference()
    F = factored_loads(sims, rec)
    P = parts(F)
    mass = mass_delta(P)
    before = _pack_before()
    log("drawings + screens")
    dr = export_drawings(log)
    shots = [plot_exploded(), plot_hood_detail(), plot_profiles(sims), plot_storyboard(), plot_drawing_preview(dr["pdf"]),
             plot_hood_relief(sims)]
    # milestone copies, git-tracked (outputs/ is scratch): the record cites these
    import shutil
    keep = REPO / "docs" / "screens"
    keep.mkdir(parents=True, exist_ok=True)
    screens = []
    for sh in shots:
        dst = keep / Path(sh).name
        shutil.copy2(REPO / sh, dst)
        screens.append(str(dst.relative_to(REPO)))
    res = {"date": "2026-11-06", "chosen": CHOSEN, "wrap_clearance": wrap_clearance(), "target_cg_mm": TARGET_CG, "sims": sims, "rank": choose(sims),
           "r28_reference": ref, "factored_n": F, "parts": P, "proof_tests": proof_tests(F, P), "mass": mass,
           "pack_before_g": round(before, 1), "pack_after_g": round(before + mass["delta_g"], 1), "cost_usd": _cost(mass),
           "times_s": procedure_times(), "drawings": dr, "screens": screens, "hook_rated_n": HOOK_RATED_N,
           "hook_rated_g": HOOK_RATED_G, "assumptions": ASSUMPTIONS}
    RESULT.write_text(json.dumps(res, indent=1, default=float))
    write_readme(res)
    log(f"  {RESULT.relative_to(REPO)}")
    from huntkit.gendesign import bag_attach
    bag_attach.docs_only(log)
    return res


ASSUMPTIONS = [
    "Box-X load share ETA_BOX 0.5 of the stitch path; webbing on a 5 mm pin or hook bed keeps 50 % of its break; "
    "seam efficiency 0.8 and grab/strip 31.25 mm from huntkit/clothsim/fabrics.yaml. Proof tests PT-1..PT-5 replace these.",
    "Qualification load = 1.5 x the HA-LS-1 factored load (n = 5 sample scatter allowance).",
    f"Bag hook: 38 mm forged 7075 sliding-gate class, rated >= {HOOK_RATED_N:.0f} N, {HOOK_RATED_G:.0f} g, $6.00: a purchase "
    "requirement, proven by PT-1. No hook record exists yet (materials-engineer to add one from the bought part).",
    f"POM toggle 30 x 8 x 5 mm, {TOGGLE_G:.0f} g, bending pull-through {TOGGLE_N:.0f} N (pom_acetal ~65 MPa, Z 33 mm3).",
    "Tri-glide 3 g, elastic keeper 0.6 g, hood rung bar fails at 30 deg sag.",
    "Cloth sim: crown hood = tension-only legs from the B-01 rows within 25 mm of the bar to the bar's bag face, free to "
    "slide in z and x (hood on a ladder, not sewn at one height); 1 mm Hypalon ply ~ 38 mm webbing EA per 40 mm strip; "
    "free hood depth 16 mm (the drafted gap at 19-23 in). Ladder tongues at x +/-60 hold B-01. Released (PR) runs hold "
    f"the row out to x +/-{HOOD['lip_half']:.0f} (the relieved lip on bare bar); the superseded PG runs held it to x +/-92. "
    "Hood-alone loads (P runs, x +/-92) stay the bound for the hood capture.",
    f"Hood float {LEG_INNER_X - HOOD['width'] / 2:.0f} mm a side between the crown legs; wrap step from x +/-{WRAP['x_start']:.0f} "
    f"(frame.yaml: 30 mm wrap, 8 mm ply drop, OD ~{WRAP['od']}); a 2 mm margin from the lip edge to the step.",
    "Guys fixed length: elastic 25 mm webbing snug (30 N) at the drafted shape, i.e. set once on the packed bag.",
    "R-28 with the sim wall adds 3 mm (fabric + coarse mesh) and the hood (+1 mm in front of the bar, +4 mm over it).",
    "Procedure seconds: 4 s a hook or pin, 3 s a cam pop or a hood lift, 10 s to place or clear the bag (gloved, not timed).",
]


def _f(x, n=0):
    return f"{x:.{n}f}"


def render_md(res: dict) -> list[str]:
    """The system sections of analysis/bag_attachment.md (bag_attach.write_docs appends the fairlead record)."""
    S, F = res["sims"], res["factored_n"]
    L = []
    a = L.append
    ch = {t: S.get(f"PR{t}") for t in (15, 19, 23)}
    pg = {t: S.get(f"PG{t}") for t in (15, 19, 23)}
    wc = res.get("wrap_clearance") or wrap_clearance()
    t_ = res["times_s"]
    m = res["mass"]
    a("# Bag-to-frame attachment system")
    a("")
    a("Owner: pack-designer. Attachment phase, 2026-11-05; hood relieved at the crown corner wraps 2026-11-06 (2.5); float "
      "mode with the B-24 stand-off links replaces the hinge swing 2026-11-06. This is the whole joint between the Spine bag and the printed "
      "branch frame, bottom to top: hinge eyes, under-straps, IM2/IM3 bag hooks, a **crown hood** on the top bar and two "
      "**top side guys**. The frame side (fairleads, pins, sleeves, their FEA) is unchanged and is kept at the end as the "
      "2026-11-01 record. Research: `docs/research/bag_attachment_research.md`. Load standard: HA-LS-1 rev B.")
    a("")
    a("Code: `huntkit/gendesign/attach_system.py` (system, sims, strengths, drawings, screens) and "
      "`huntkit/gendesign/bag_attach.py` (fairleads; `write_docs` / `docs_only` write this file). "
      "Numbers: `analysis/attach_system_results.json`. Drawings: `cut/attachment/attachment_parts.pdf` / `.dxf` (1:1).")
    a("")
    a("## Decision")
    a("")
    a(f"- **Top anchor: crown hood + two fixed-length top side guys** (cloth-sim runs PR15/PR19/PR23, hood lip relieved at the corner wraps). Load CG, 68 kg fill "
      f"(C1): **{_f(ch[15]['fill']['cg_y'])} / {_f(ch[19]['fill']['cg_y'])} / {_f(ch[23]['fill']['cg_y'])} mm** at "
      f"15 / 19 / 23 in (before: {_f(S['baseline']['fill']['cg_y'])} mm at 19 in). Meat case (C5 contents): "
      f"{_f(ch[15]['meat']['cg_y'])} / {_f(ch[19]['meat']['cg_y'])} / {_f(ch[23]['meat']['cg_y'])} mm; with the meat at "
      f"its HA-LS-1 150 mm: {_f(ch[15]['meat']['mixed_cg_y'])} / {_f(ch[19]['meat']['mixed_cg_y'])} / "
      f"{_f(ch[23]['meat']['mixed_cg_y'])} mm.")
    a(f"- **The 180 mm goal is met at 19 and 23 in and missed at 15 in by {_f(ch[15]['fill']['cg_y'] - TARGET_CG)} mm on the "
      "fill case** (meat case on the line). Nothing on the frame is higher than the 15 in top bar (z 601); every concept "
      "simulated is worst there. Owner choice 1 below.")
    a(f"- **Head clearance R-28 passes** at every torso with the simulated wall and the hood on the bar: first contact "
      f"**{_f(min(min(ch[t][c]['r28']['worst_contact_deg'] for c in ('fill', 'meat')) for t in ch))} deg or later** "
      f"(requirement > 30 deg).")
    a(f"- **IM3 hook fixed**: all four bag hooks become one **rated >= {res['hook_rated_n']:.0f} N** part, proof PT-1 at "
      f"**{res['proof_tests'][0]['load_n']:.0f} N**, which is 1.5 x the C5 IM3 load of {_f(F['im3'])} N (hood-off case). "
      f"SF on the rated hook **{res['hook_rated_n'] / F['im3']:.2f}** (was 1.06).")
    a(f"- **Bag off {t_['bag_off']} s** (limit 120 s), bag on {t_['bag_on']} s, float mode {t_['float']} s with the meat "
      f"loaded, bag-off haul {t_['bag_off_haul']} s. Estimates for gloved hands, not a timed trial.")
    a("- **Float mode replaces the hinge swing (owner 2026-11-06).** For bulk meat the bag comes off its pins, the meat goes "
      "on the frame (cradle + IM1-IM3) and the bag hangs upright behind it on two B-24 stand-off links clipped to the IM3 "
      "eyes, at a 120 / 170 / 220 mm gap. The bag never pivots in use. The hinge pins, HE eyes and B-18 doublers stay: "
      "they are the bag's bottom anchor in bag-on mode (factored 1019 N per side, section 5) and the bag is still put on "
      "by tipping it onto them. Links: +54.4 g, their own weight group (section 11). "
      "Study: `analysis/meat_carry_alternatives.md`; research: `docs/research/meat_carry_mechanisms.md`.")
    a(f"- **Mass +{m['delta_g']:.0f} g**: pack {res['pack_before_g']:.0f} -> **{res['pack_after_g']:.0f} g "
      f"({res['pack_after_g'] / 453.59237:.2f} lb)**. Marginal cost about **${res['cost_usd']:.0f}**. No new frame feature.")
    a("")
    a("## 1. The joint, bottom to top")
    a("")
    a("| # | station | frame side (unchanged) | bag side | closer | bag off | float mode |")
    a("|---|---|---|---|---|---|---|")
    a("| 1 | hinge, z 60 | fairlead, UHMWPE sleeve | HE eye on B-18 doubler | tethered 5 mm 7075 pull-pin (cord pull loop) | pull | pull (tethered to the bag) |")
    a("| 2 | US1 z 95, US2 z 142 | cradle fairleads, eye L, cam R | B-16 floor channels | 38 mm cam + tri-glide | pop, slide off (straps stay) | pop, slide off; the straps are the meat cradle |")
    a("| 3 | IM1, z 190 | captive eye | none (meat strap only) | - | - | meat strap |")
    a("| 4 | IM2, z 330 | captive eye | T2 tongue + B-23 backing | rated 38 mm hook | unclip | unclip (keeper) |")
    a("| 5 | IM3, z 520 | captive eye | T3 tongue on B-17 | rated 38 mm hook | unclip | T3 hook into a B-24 link loop; link hook on the IM3 eye |")
    a("| 6 | crown top bar, z 601-804 | carbon bar, OD 18 | B-19 hood on 2 x B-20 ladder (one rung per setting) | gravity + peel seat it; lift tab to release | lift | lift, lies on the bag top |")
    a("| 7 | top side guys | via the hood | TG from the hood ears to B-22 on B-02d (x +/-149, z 752) | ladder lock + tri-glide, set once | come with the hood | come with the hood |")
    a("")
    a("Lifters stay on the crown corner wraps (not part of the joint). W1-W3 stay the haul wraps / carry compression.")
    a("")
    a("## 2. Top anchor")
    a("")
    a("### 2.1 What was simulated")
    a("")
    a("`python -m huntkit.clothsim.cli run --scenario huntkit/clothsim/scenarios/pack5200_v31_att_<run>.yaml --cases "
      "packed,fill,meat --no-sweep --no-render`. Coarse mesh h 40, 68 kg at 1 g. Every run except the baseline has B-17, "
      "B-18 and crown contact; W3 moves with the crown. Fill CGs are +/-5 mm (fill cases stop at a 4-19 N residual, as in "
      "phase 1); meat cases converge. New sim key: `attachments.pocket` (CONTRACTS 7).")
    a("")
    a("| run | torso | concept | fill CG | meat CG | meat at 150 + gear | IM3 1 g N | top anchor 1 g N | R-28 first contact deg (fill / meat) | gap at 30 deg mm |")
    a("|---|---:|---|---:|---:|---:|---:|---|---|---:|")
    for k, v in S.items():
        tn = ", ".join(f"{n} {t:.0f}" for n, t in v["meat"]["top_n"].items()) or "-"
        a(f"| {k} | {v['torso_in']} | {v['label']} | {v['fill']['cg_y']:.0f} | {v['meat']['cg_y']:.0f} | "
          f"{v['meat']['mixed_cg_y']:.0f} | {v['meat']['im3_max_n']:.0f} | {tn} | "
          f"{v['fill']['r28']['worst_contact_deg']:.0f} / {v['meat']['r28']['worst_contact_deg']:.0f} | "
          f"{min(v['fill']['r28']['worst_gap_30_mm'], v['meat']['r28']['worst_gap_30_mm']):.1f} |")
    a("")
    a("Top anchor N is the meat case; `pocket` is the hood capture summed over its width. R-28 uses the DESIGN 4.7 head "
      "model with the simulated wall (drafted face moved by the sim + 3 mm) instead of the 15 mm bulge, plus the hood on "
      "the bar. The published check (bare bar, 15 mm bulge) gives "
      f"{res['r28_reference']['published']['19']['worst_contact_deg']:.0f} deg / "
      f"{res['r28_reference']['published']['19']['worst_gap_30_mm']:.1f} mm; with the hood on the bar "
      f"{res['r28_reference']['with_hood']['19']['worst_contact_deg']:.0f} deg / "
      f"{res['r28_reference']['with_hood']['19']['worst_gap_30_mm']:.1f} mm. The bar governs, not the wall.")
    a("")
    a("### 2.2 Why the hood + guys")
    a("")
    p19, a_, g_ = S["P19"], S["A"], S["G"]
    a(f"- **The hood beats the crown tie as the bar anchor.** Alone at 19 in it gives {p19['fill']['cg_y']:.0f} / "
      f"{p19['meat']['cg_y']:.0f} mm against {a_['fill']['cg_y']:.0f} / {a_['meat']['cg_y']:.0f} for the two-point tie (A): "
      "it holds B-01 across the bar width instead of at x +/-70. That is the research's best-in-class pattern: the frame top "
      "captured by the bag (KUIU ICON 6 stay pockets, Initial Ascent slots, the Mystery Ranch collar), here as one hood on the bar.")
    a(f"- **A bar anchor alone is not enough at any torso.** At 23 in the hood alone is {S['P23']['fill']['cg_y']:.0f} mm "
      "(the bag between IM3 at z 520 and the bar at z 804 bulges aft), at 15 in it carries nothing "
      f"({S['P15']['meat']['top_n'].get('pocket', 0):.0f} N) and gives {S['P15']['fill']['cg_y']:.0f} mm. "
      "What pulls the CG in is the pair of guys holding the aft upper corners forward (study finding 3).")
    a(f"- **Hood + guys vs study G (tie + guys):** {ch[19]['fill']['cg_y']:.0f} vs {g_['fill']['cg_y']:.0f} mm at 19 in, "
      f"{ch[23]['fill']['cg_y']:.0f} vs {S['G23']['fill']['cg_y']:.0f} at 23 in, {ch[15]['fill']['cg_y']:.0f} vs "
      f"{S['G15']['fill']['cg_y']:.0f} at 15 in: the same within the +/-5 mm scatter. The hood wins on use, not on CG: the "
      "guys are sewn to its ears, so one lift releases the whole top (hood and both guys) and one drop re-seats it. "
      "Nothing at the top is threaded, clipped or tensioned with the bag on, which is the field's failure point "
      "(K4 dealer's ~18 cases, research 3.3). G needs two more clips at the bar and the guy anchors crowd the lifter lugs at x +/-105.")
    lf = S["L19"]
    a(f"- **Load lifters as the anchor (L19)** reach {lf['fill']['cg_y']:.0f} / {lf['meat']['cg_y']:.0f} mm, about the "
      "same, but only by routing the lifter to the bag in bag-on and back to the frame in bag-off. That is the switching in "
      "US 10,952,523, and with the bag off the lifters would need a second anchor. Rejected. On our rigid crown a lifter "
      "that stays on the crown does not change the bag-to-frame peel at all (it loads the frame, not the bag).")
    if "PGc15" in S:
        c15, c19 = S["PGc15"], S.get("PGc19")
        r15 = min(c15["fill"]["r28"]["worst_contact_deg"], c15["meat"]["r28"]["worst_contact_deg"])
        ok15 = c15["fill"]["r28"]["pass"] and c15["meat"]["r28"]["pass"]
        a(f"- **Cinching the guys** (60 N after loading, PGc) buys {ch[15]['fill']['cg_y'] - c15['fill']['cg_y']:.0f} mm at "
          f"15 in ({c15['fill']['cg_y']:.0f} / {c15['meat']['cg_y']:.0f} mm) but R-28 then "
          + (f"passes at {r15:.0f} deg" if ok15 else f"**fails: first contact {r15:.0f} deg** (the top is pulled toward the head)")
          + (f"; at 19 in it gives {c19['fill']['cg_y']:.0f} / {c19['meat']['cg_y']:.0f} mm, R-28 "
             f"{min(c19['fill']['r28']['worst_contact_deg'], c19['meat']['r28']['worst_contact_deg']):.0f} deg" if c19 else "")
          + ". So the guys are set once on the packed bag and never cranked (the instruction is 'snug, do not crank'). "
          "This is the study's B finding again: cinched top straps over-pull toward the head.")
    a("")
    a("### 2.5 Hood and the crown corner wraps (2026-11-06)")
    a("")
    a(f"The frame re-check (`frame_cg_recheck.md` 5.1) found that the carbon corner wraps cover the top bar from the leg "
      f"face (x +/-{WRAP['x_leg']:.0f}) to about x +/-{WRAP['x_start']:.0f}, at OD about {WRAP['od']:.1f}, and cannot be "
      "shortened (an 11 mm overlap fails the corner bond). The 2026-11-05 hood asked for bare bar over x +/-96: its lip "
      f"and HDPE stiffener would have borne on the wrap step and the ply drop, putting the hood capture and the guy loads "
      "into the bond end. Fix on the hood, not the frame:")
    a("")
    a(f"- **Lip relief:** the lip, J-curl, hem, B-19s stiffener and B-19L lining stop at x +/-{HOOD['lip_half']:.0f} "
      f"({wc['bearing_len_mm']:.0f} mm on bare OD 18 bar). The outer {wc['relief_width_mm']:.0f} mm each side of the 190 mm "
      "shell is back ply and crown only, ending at fold 2 with an R4 root. Shell width, ears, guys, tongues and the ladder "
      "do not change.")
    a(f"- **Why {HOOD['lip_half']:.0f} and not 77:** the hood floats {wc['hood_float_mm']:.0f} mm a side between the crown "
      f"legs, so the lip edge can reach x {wc['lip_edge_worst_x_mm']:.0f}: {wc['lip_margin_to_wrap_mm']:.0f} mm short of the "
      f"wrap step. Over the wraps the crown sits on the {HOOD['lining'][2]:.0f} mm lining in the bare zone, "
      f"{wc['crown_over_wrap_clear_mm']:.2f} mm above the wrap (radial step {(WRAP['od'] - BAR_OD) / 2:.2f} mm). Nothing "
      "touches the wraps in use.")
    a(f"- **Cloth sim re-run** with the hood capture narrowed to x +/-{HOOD['lip_half']:.0f} (conservative: the shell still "
      "holds B-01 wider than that):")
    a("")
    a("| torso | fill CG full lip (PG) | fill CG relieved (PR) | meat CG PG | meat CG PR | hood 1 g N PG / PR (meat) | guys 1 g N PR (meat) | R-28 deg PR (fill / meat) | gap at 30 deg PR mm |")
    a("|---:|---:|---:|---:|---:|---|---|---|---:|")
    for t in (15, 19, 23):
        r_, g0 = ch[t], pg[t]
        if not (r_ and g0):
            continue
        a(f"| {t} | {g0['fill']['cg_y']:.0f} | **{r_['fill']['cg_y']:.0f}** | {g0['meat']['cg_y']:.0f} | **{r_['meat']['cg_y']:.0f}** | "
          f"{g0['meat']['top_n'].get('pocket', 0):.0f} / {r_['meat']['top_n'].get('pocket', 0):.0f} | "
          f"{r_['meat']['top_n'].get('TG_R', 0):.0f} / {r_['meat']['top_n'].get('TG_L', 0):.0f} | "
          f"{r_['fill']['r28']['worst_contact_deg']:.0f} / {r_['meat']['r28']['worst_contact_deg']:.0f} | "
          f"{min(r_['fill']['r28']['worst_gap_30_mm'], r_['meat']['r28']['worst_gap_30_mm']):.1f} |")
    a("")
    a("The CG holds within the +/-5 mm fill scatter (accepted 189 / 177 / 168 mm), and R-28 still passes at every torso. "
      "With the narrower capture the hood itself carries almost nothing and the two guys take the top (a few N more each); "
      "the hood's job is to give the guys their anchor and centre the top. The guy factored load and the lip capacity "
      "(132 mm of Hypalon on the bar) are in section 5. The PR19 meat case stops at a 0.8 N residual (not flagged converged); "
      "the other meat cases converge.")
    a("")
    a("### 2.3 Why the hood is lift-and-drop, not snap-on")
    a("")
    a("The bag goes on by tipping it onto the z 60 pins, 643 mm below the bar (in use it no longer pivots: the float "
      "replaced the swing, 2026-11-06). Seen from the bag, the bar arrives on a 643 mm arc that is "
      "level at the bar: it comes in from the wearer side. Peel is the same motion. So any bag part that stops the peel is "
      "also in the way when the bag is tipped shut. A pocket cannot be made to catch the bar passively. The hood is lifted "
      "25 mm by its tab (B-01 above IM3 is slack in compression, and the hood rides on its ladder), the bag top is pressed "
      "to the crown, and the hood is let go. It drops over the bar. Under load the J-lip seats it harder: the peel pushes it "
      "down onto the bar. Lift and drop are about 3 s each, with no strap to stretch over meat.")
    a("")
    a("### 2.4 The 15 in setting")
    a("")
    a(f"At 15 in the top bar is at z 601, 500 mm below the bag top. Best head-safe result: {ch[15]['fill']['cg_y']:.0f} mm "
      f"fill / {ch[15]['meat']['cg_y']:.0f} mm meat (meat at 150: {ch[15]['meat']['mixed_cg_y']:.0f}). The structural "
      "re-check already running uses a 205 mm C1 envelope and 175 mm for C5/C7, so the frame is covered. Higher anchors need "
      "a frame part above the crown (accessory posts: IP opinion on US 10,952,523, owner choice 1).")
    a("")
    a("## 3. IM3 hook")
    a("")
    a(f"With B-17 the IM3 bag hook carries {S['T0']['meat']['im3_max_n']:.0f} N at 1 g with no top anchor (T0) and "
      f"{max(ch[t]['meat']['im3_max_n'] for t in ch):.0f} N with the hood and guys: the top anchor relieves it only "
      f"{S['T0']['meat']['im3_max_n'] - max(ch[t]['meat']['im3_max_n'] for t in ch):.0f} N. The hook is designed for the "
      f"hood-off case (a user who forgets the hood): C5 factored **{F['im3']:.0f} N**.")
    a("")
    a("| option | rating N | SF at C5 | mass change | verdict |")
    a("|---|---:|---:|---:|---|")
    a(f"| keep the 1500 N hook (assumption) | 1500 | {1500 / F['im3']:.2f} | 0 | fails a 1.5 qualification margin |")
    a(f"| hood relieves IM3 | 1500 | {1500 / F['im3_chosen']:.2f} | 0 | still thin, and lost if the hood is off |")
    a(f"| two hooks per side on one eye | 2 x 1500 | not credited | +18 g | uneven share on one 38 mm eye; rejected |")
    a(f"| **rated 38 mm hook, all four bag hooks** | **>= {res['hook_rated_n']:.0f}** | **{res['hook_rated_n'] / F['im3']:.2f}** | "
      f"**+{4 * (res['hook_rated_g'] - 9):.0f} g** | **chosen**; same handling and times; one spare part |")
    a("")
    a(f"Proof test PT-1: five hooks hold **{res['proof_tests'][0]['load_n']:.0f} N** for 60 s (1.5 x C5), gate closes after; "
      f"then one hook per lot of 25 to {F['im3']:.0f} N. The old 830 N test is retired for the bag hooks. The meat-strap "
      "hooks (6) keep the 1500 N assumption and their own 830 N test (meat_haul_modes.md).")
    a("")
    a("## 4. Sway, barndoor and the side compression")
    a("")
    a("- **Barndoor (bag yawing on the frame):** held at three heights on both sides: the hinge pins (z 60), the IM2/IM3 "
      "hooks (z 330/520), and at the top the hood between the crown legs (190 mm hood, 208 mm between the leg faces: 9 mm "
      "a side, then Hypalon on carbon). The guys are symmetric, so they centre the top.")
    a("- **Sway (side lean of the top):** the guys are the top side-compression straps. They run from the hood ears outside "
      "the side gores to the aft corners, so cinching the top sideways and holding it forward is one strap per side. W1-W3 "
      "stay the frame-anchored wraps for the lower and middle bag and for float mode. The roll-top clips stay on the gores.")
    a("- **Small loads:** the guys are fixed at the full-bag length; for a part-full bag pull the tails one more step "
      "(they are ladder locks) and W1-W3 take up the rest.")
    a("")
    a("## 5. Sewn side")
    a("")
    a(f"Stitch standards. Load joints: box-X, ISO 301 lockstitch, **{SPI['box']} SPI** (3.6 mm), `{THREAD['box']}` "
      f"(98 N), needle {NEEDLE[THREAD['box']]}, 3-stitch backtack. Patch perimeters: double row 3 and 9 mm in, 301, "
      f"**{SPI['perim']} SPI** (3.2 mm), `{THREAD['perim']}` (64 N), needle {NEEDLE[THREAD['perim']]}. Thread line "
      f"strength = 1.5 x break / stitch length (CONTRACTS 7): {q_thread('box'):.1f} N/mm box, {q_thread('perim'):.1f} N/mm "
      "per perimeter row. Patches are capped by 0.8 x the weaker strip strength.")
    a("")
    a("| id | part | qty | material | cut | fold / make | stitch | backing | placement |")
    a("|---|---|---:|---|---|---|---|---|---|")
    for p in res["parts"]:
        a(f"| {p['id']} | {p['name']} | {p['qty']} | `{p['material']}` | {p['cut']} | {p['fold']} | {p['stitch']}, "
          f"{p['spi']} SPI, `{p['thread']}` | {p['backing']} | {p['placement']} |")
    a("")
    a("Strength (per side, factored HA-LS-1 x 3.0 or the beam model, whichever is larger):")
    a("")
    a("| id | factored N | basis | capacities N | governs | SF | qualification N |")
    a("|---|---:|---|---|---|---:|---:|")
    for p in res["parts"]:
        caps = "; ".join(f"{k} {v:.0f}" for k, v in p["caps_n"].items())
        a(f"| {p['id']} | {p['load_n']:.0f} | {p['load_basis']} | {caps} | {p['governs']} | **{p['sf']:.2f}** | {p['proof_n']:.0f} |")
    a("")
    a("Proof tests (owner bench, before the first sewn bag):")
    a("")
    a("| test | what | rig | load N | covers | accept | then |")
    a("|---|---|---|---:|---|---|---|")
    for t in res["proof_tests"]:
        a(f"| {t['id']} | {t['what']} | {t['rig']} | {t['load_n']:.0f} | {t['covers']} | {t['accept']} | {t['also']} |")
    a("")
    a("## 6. Quiet")
    a("")
    a("Checklist = the noise sources owners name (research 3.4) plus the four inferred rules there.")
    a("")
    a("| source | how this joint answers it |")
    a("|---|---|")
    for src, how in QUIET:
        a(f"| {src} | {how} |")
    a("")
    a("## 7. Procedures")
    a("")
    for key in ("bag_on", "bag_off", "float", "bag_off_haul", "repair"):
        pr = PROCEDURES[key]
        tot = t_[key]
        a(f"### {pr['title']}" + ("" if key == "repair" else f" - about {tot} s"))
        a("")
        for i, (txt, s_) in enumerate(pr["steps"], 1):
            sec = _step_s(s_)
            a(f"{i}. {txt}" + (f" ({sec} s)" if sec else ""))
        a("")
    a("Repair kit: " + ", ".join(f"{n}" for n, _ in REPAIR_KIT)
      + f", about {sum(g for _, g in REPAIR_KIT):.0f} g (not in the base weight).")
    a("")
    a("## 8. Patent guardrails (engineering read, not a legal opinion)")
    a("")
    a("| patent | how the joint stays clear | status |")
    a("|---|---|---|")
    for pt, how, st in PATENTS:
        a(f"| {pt} | {how} | {st} |")
    a("")
    a(f"Original IP: {ORIGINAL_IP}")
    a("")
    a("## 9. Frame interface (for the structural-fea-engineer)")
    a("")
    for line in frame_interface(F):
        a(f"- {line}")
    a("")
    a("## 10. Pattern-maker hand-off")
    a("")
    a("| piece | change |")
    a("|---|---|")
    for k, v in HANDOFF:
        a(f"| {k} | {v} |")
    a("")
    a("## 11. Mass and cost of this phase")
    a("")
    a("| part | g |")
    a("|---|---:|")
    for k, v in m["parts_g"].items():
        a(f"| {k} | {v:.1f} |")
    a(f"| **delta** | **{m['delta_g']:.1f}** |")
    a("")
    from huntkit.gendesign import meat_haul as MH
    lg = MH.float_link_parts_g()
    a("")
    a(f"Float-mode stand-off links B-24 (owner 2026-11-06), booked as their own weight group, not in the delta above: "
      + "; ".join(f"{k} {v:.1f} g" for k, v in lg.items()) + f"; **+{sum(lg.values()):.1f} g**.")
    a("")
    a(f"Pack (this phase) {res['pack_before_g']:.0f} -> **{res['pack_after_g']:.0f} g ({res['pack_after_g'] / 453.59237:.2f} lb)**, "
      f"{res['pack_after_g'] - 2976:.0f} g over the published 2976 g. Basis: {m['basis']}. Marginal cost about "
      f"${res['cost_usd']:.0f} (records' prices; hook $6.00 and toggle $0.50 ASSUMPTION).")
    a("")
    a("## 12. Owner choices (recommendation first)")
    a("")
    a("1. **15-16.5 in settings: accept the 15 in result (recommended)**, fill CG "
      f"{_f(ch[15]['fill']['cg_y'])} mm, inside the 205 mm envelope of the frame re-check that is running; cinching the "
      "guys there gets closer to 180 but fails R-28 (2.2). The alternative is a hood on the accessory extension posts for "
      "short torsos: it needs an IP opinion on US 10,952,523, a C6p-type frame case and an R-28 check with posts.")
    a("2. **Accept +{0:.0f} g for the joint (recommended)**: pack {1:.0f} g ({2:.2f} lb), {3:.0f} g over the published "
      "2976 g.".format(m["delta_g"], res["pack_after_g"], res["pack_after_g"] / 453.59237, res["pack_after_g"] - 2976)
      + " Without the top anchor the frame has to carry the 205 mm CG at every torso.")
    a(f"3. **One rated hook for all four bag hooks (recommended, +{4 * (res['hook_rated_g'] - 9):.0f} g)** or rated hooks "
      f"at IM3 only (+{2 * (res['hook_rated_g'] - 9):.0f} g, two hook types in the kit).")
    a("4. **FTO read on US 12,495,885 and confirmation that US 8,579,171 / 8,348,114 are expired** before release (recommended; open since the research).")
    a("5. Lighter options if the weight is not accepted: ladder strips in 500D Cordura with bound slots (about -11 g, less "
      "durable at the slots), rated hooks at IM3 only (-10 g), no tri-glide keepers on the guys (-6 g; research says keep them).")
    a("")
    a("## 13. Assumptions")
    a("")
    for s_ in res["assumptions"]:
        a(f"- {s_}")
    a("")
    a("## Screenshots (this phase)")
    a("")
    a("Phone previews in `outputs/screens/20261105_attach_1..5.png`; milestone copies (cited) in `docs/screens/`:")
    a("")
    for s_ in res["screens"]:
        a(f"- `{s_}`")
    a("")
    return L


SEW_ORDER = [
    "Laser-cut the Hypalon parts (B-17, B-18, B-19, B-20 x2, B-22 x2, B-23 x2) and the HDPE lip B-19s from the DXF. "
    "Hot-knife the webbing parts (HE, T2/T3, HT, TG, LLT, GT, B-24) to the lengths on the PDF.",
    "Flat B-01 (lower), before it goes 3D: B-23 inside at the IM2 marks, then box-X T2 through T2 + B-01 + B-23.",
    "B-17 outside under the IM3 swell (double row), then box-X T3 to B-17. B-18 inside at the hinge-eye notch; box-X HE.",
    "Join the B-01 tiers (B-01 | B-01b | B-01u). Then sew the two B-20 ladder strips on both long edges (2 and 5 mm "
    "in) and bartack their ends. Then B-01 joins B-03 as before.",
    "B-02d before it joins the collar: LLT round a ladder lock, box-X through B-22 + B-02d; B-22 double row.",
    "Hood: glue B-19L inside the crown (centred, bare-bar zone only), slide B-19s into the lip hem (centred) and sew the hem; heat-form the J on a 19 mm dowel; "
    "fold 1 and fold 2 square; box-X HT tongues (toggle end first), GT grab tab and the TG guy ends on the ears.",
    "Fit: weave each HT tongue into B-20 at the rung for the crown setting (in at k, out at k+1), push the toggle "
    "through. Thread each guy through its ladder lock and tri-glide, set snug on the packed bag.",
    "B-24 float links (separate, no bag sewing): fold the hook end round a rated hook, box-X; mark the three loop "
    "start / apex / end lines from the PDF, pinch each loop at its apex line so start meets end, box-X 38 x 20 across "
    "both plies at the base. Check each apex at 120 / 170 / 220 mm from the hook bed (+/-3 mm).",
    "Bench tests before the first field use: PT-1 to PT-6 in analysis/bag_attachment.md section 5.",
]


def write_readme(res: dict) -> str:
    L = ["# Bag-to-frame attachment: sewn parts (build sheet)", "",
         "Engineering record: `designs/pack_5200/analysis/bag_attachment.md` (generated by "
         "`python -m huntkit.gendesign.attach_system`). Numbers: `analysis/attach_system_results.json`.", "",
         "## Files", "", "| file | what it is | use it for |", "|---|---|---|",
         "| `attachment_parts.pdf` | every new or changed sewn part, 1:1, tiled on letter paper, with stitch lines "
         "(dashed), folds (dash-dot), slots and labels | print at 100 %, check the 100 mm square, cut paper templates |",
         "| `attachment_parts.dxf` | the same parts, layers CUT / SEW / TEXT (AAMA style) | laser cutter for the Hypalon and HDPE |",
         "", "## Parts", "", "| id | part | qty | material | cut | stitch |", "|---|---|---:|---|---|---|"]
    for p in res["parts"]:
        L.append(f"| {p['id']} | {p['name']} | {p['qty']} | `{p['material']}` | {p['cut']} | {p['stitch']}, "
                 f"{p['spi']} SPI, `{p['thread']}` ({p['needle']}) |")
    L += ["", f"Hardware: 4 bag hooks 38 mm rated >= {res['hook_rated_n']:.0f} N (PT-1 {res['proof_tests'][0]['load_n']:.0f} N), "
          "2 POM toggles, 2 ladder locks 25 mm, 2 tri-glides 25 mm, 2 elastic keepers, Dyneema cord pull loops on the "
          "two hinge pins; 2 more rated hooks on the B-24 float links.", "", "## Sewing order", ""]
    L += [f"{i}. {t}" for i, t in enumerate(SEW_ORDER, 1)]
    L.append("")
    path = CUT / "README.md"
    path.write_text("\n".join(L))
    return str(path)


def docs_only(log=print) -> str:
    from huntkit.gendesign import bag_attach
    return bag_attach.docs_only(log)


def refresh(log=print) -> dict:
    """Re-derive what changed with the float mode (2026-11-06) on top of the frozen record: parts and proof tests (B-24),
    procedure times, drawings and the screens that show procedures or parts. The cloth-sim results, factored loads, the
    phase mass delta and its pack before/after stay as recorded (they are the 2026-11-05/06 attachment phase; later
    weight changes are booked in geometry.yaml and listed in tests/test_attach_system.py)."""
    import shutil
    res = json.loads(RESULT.read_text())
    F = res["factored_n"]
    P = parts(F)
    res["parts"] = P
    res["proof_tests"] = proof_tests(F, P)
    res["times_s"] = procedure_times()
    res["drawings"] = export_drawings(log)
    keep = REPO / "docs" / "screens"
    redo = {"_attach_2": plot_hood_detail, "_attach_4": plot_storyboard,
            "_attach_5": lambda: plot_drawing_preview(res["drawings"]["pdf"])}
    for s_ in res["screens"]:
        for tag, fn in redo.items():
            if tag in s_:
                shutil.copy2(REPO / fn(), keep / Path(s_).name)
    res["float_mode"] = {"date": "2026-11-06", "procedure": "float", "link": "B-24",
                         "source": "analysis/meat_carry_alternatives.md, analysis/meat_haul_modes.json float"}
    RESULT.write_text(json.dumps(res, indent=1, default=float))
    write_readme(res)
    log(f"  {RESULT.relative_to(REPO)}")
    from huntkit.gendesign import bag_attach
    bag_attach.docs_only(log)
    return res


if __name__ == "__main__":
    if "--docs-only" in sys.argv:
        docs_only()
    elif "--refresh" in sys.argv:
        refresh()
    else:
        run()
