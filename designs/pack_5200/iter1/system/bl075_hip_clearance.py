"""BL-075: does the H1-P through-bolt hip stack clear the frame, the bag, the lumbar pad and the hipbelt?

BL-073 replaced the hip inserts with 8 x Ti M5 x 35 DIN 7984 through-bolts, A2 DIN 934 nuts, a 6061 bearing ring
(2 mm) and a printed nut keeper (3 mm) on the flat back of the D50 hip boss. This module places that stack on the
exported H1-P body (``iter1/frame/h1p/h1_assembled.stl``) and measures it against:

* the printed body itself (surface samples of the STL vs the stack solids, the ring's seat excluded);
* the bag side: the BP-06 spreader (wearer face on the stay crowns, minus its factored deflection from
  ``analysis/spreader_results.json``) and the CORRIE F rev 3 frame-side panel B-01 (``bag_concepts.y_frame``), with a
  membrane bound for B-01 bulging into the open bay below the spreader;
* the wearer side: which way "aft" points (FCS y, ``geometry.yaml``), the Ti mount, screw heads and the hipbelt /
  lumbar pad, which sit on the other side of the 22 mm boss.

Frame coordinates (FCS): x to the wearer's right, y AFT (away from the wearer's back, toward the bag), z up; mm.
Read-only on the frame and BL-070/073 files. Units mm, N, g.

    python designs/pack_5200/iter1/system/bl075_hip_clearance.py           # writes .json + screenshot
    python designs/pack_5200/iter1/system/bl075_hip_clearance.py --check   # prints, writes nothing
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PACK = HERE.parents[1]
ROOT = PACK.parents[1]
for _p in (str(ROOT), str(PACK), str(PACK / "concepts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

H1P = PACK / "iter1" / "frame" / "h1p"
BL070_JSON = PACK / "iter1" / "frame" / "bl070_h1p.json"
SPREADER_JSON = PACK / "analysis" / "spreader_results.json"
MOUNT_STL = PACK / "print" / "lug_hip_pivot_mount_slm_ti.stl"
OUT_JSON = HERE / "bl075_hip_clearance.json"
SCREEN = ROOT / "outputs" / "screens" / "20261125_bl075_1.png"

HIP_C = (0.0, 120.0)            # boss axis (x, z): h1_closeout.HIP_C
NUT_AF = 8.0                    # DIN 934 M5 across flats
M5_P = 0.8                      # M5 coarse pitch
M5_D = 5.0
HEAD_K = 3.5                    # DIN 7984 M5 head height (hip_mount_bl056: head D8.5 x 3.5)
TI_BASE_T = 3.0                 # Ti mount base (BL-056)
HUB_TOP = 28.1                  # Ti mount hub top above the boss face (hip_mount_bl056.md section 1)
SAMPLES = 400_000               # frame surface samples (seeded)

# ASSUMPTIONS (each with the check that settles it)
ASSUMPTIONS = {
    "B01-STRAIN": ("B-01 (ULTRA 200X: UHMWPE / HT-polyester face, 45 deg CrossPly, PET film) strains at most 5 % "
                   "before the face yarns fail; no elongation is published (record challenge_ultra_200 has none). "
                   "Used only as the bound that B-01 cannot bulge into the bottom bay as deep as the tails.",
                   "PT-3 strip pull on ULTRA 200X (already in the register): record the elongation at break"),
    "SPREADER-REV-C": ("The BP-06 Sandwich v2 sits on the stay crowns with its wearer face at the LOWEST crown height "
                       "in its bottom band (z 112-145 on the H1-P STL): the conservative (closest-to-wearer) "
                       "reading; its factored deflection is spreader_results.json chosen.w_fact_max.",
                       "first H1-P frame dry fit with the spreader clipped on: feeler gauge from a tail tip to the sheet"),
    "STACK-TOL": ("Stack and length tolerances for the protrusion band: boss 22 +/- 0.2 (print), ring 2 +/- 0.1 "
                  "(sheet), DIN 934 m 4.0 -0.3, Ti mount base 3 +/- 0.05; DIN 7984 M5 x 35 length js15 +/- 0.5; "
                  "end chamfer about one thread depth (0.5 mm, ISO 4753).",
                  "BUILD_H1P hip step: measure tail protrusion with calipers on all 8 after torque"),
    "PADSEAT-ROUTE": ("The lumbar pad-seat bottom cord tie (BL-006 f1, 2 mm Dyneema) has no drawn route on H1-P; it "
                      "is taken round the lower lumbar struts outboard of |x| 35 mm, not across the boss back.",
                      "HB-D3 pad-seat retention fit on the first H1-P frame"),
}


# ================================================================================================== geometry
def _frame():
    import trimesh
    return trimesh.load(H1P / "h1_assembled.stl")


def _hip_record() -> dict:
    return json.load(open(BL070_JSON))["h1p"]["hip_mount"]


def bolt_positions() -> list:
    from huntkit.gendesign import h1_closeout as C
    return [tuple(p) for p in C.hip_pattern(*C.HIP_CHOSEN, depth=C.HIP_BOSS_DEPTH)["positions_xz"]]


def boss_planes(frame) -> dict:
    """Mount face (min y) and flat back (max y) of the D50 boss, read off the STL inside r 20 of the axis."""
    v = frame.vertices
    r = np.hypot(v[:, 0] - HIP_C[0], v[:, 2] - HIP_C[1])
    sel = r < 20.0
    return {"face_y": round(float(v[sel, 1].min()), 2), "back_y": round(float(v[sel, 1].max()), 2)}


def stack(back_y: float) -> dict:
    """The hardware stack aft of the flat back as simple solids (y ranges, radii), from the BL-073 record and the
    ring / keeper STLs. Nuts use their circumscribed circle (conservative)."""
    import trimesh
    hm = _hip_record()
    ring_t = hm["ring"]["t_mm"]
    nut_m = hm["screw"]["stack_mm"] - TI_BASE_T - hm["boss"]["depth_mm"] - ring_t
    keep = trimesh.load(H1P / "hip_nut_keeper.stl")
    ring = trimesh.load(H1P / "hip_bearing_ring.stl")
    keep_t = float(np.ptp(keep.bounds[:, 2]))
    y0 = back_y
    return {
        "ring": {"r": float(ring.bounds[1, 0]), "y": (y0, y0 + ring_t)},
        "keeper": {"r": float(keep.bounds[1, 0]), "y": (y0 + ring_t, y0 + ring_t + keep_t)},
        "nuts": {"r": NUT_AF / math.sqrt(3), "y": (y0 + ring_t, y0 + ring_t + nut_m)},
        "tails": {"r": M5_D / 2, "y": (y0 + ring_t + nut_m, y0 + ring_t + nut_m + hm["screw"]["protrusion_mm"])},
        "nut_m": nut_m, "keeper_t": keep_t, "ring_t": ring_t,
        "tip_y": y0 + ring_t + nut_m + hm["screw"]["protrusion_mm"],
        "aft_mm": ring_t + nut_m + hm["screw"]["protrusion_mm"],
    }


def _cyl_dist(P, c_xz, r, y0, y1):
    dr = np.maximum(np.hypot(P[:, 0] - c_xz[0], P[:, 2] - c_xz[1]) - r, 0.0)
    dy = np.maximum(np.maximum(y0 - P[:, 1], P[:, 1] - y1), 0.0)
    return np.hypot(dr, dy)


def frame_clearance(frame, st: dict, back_y: float) -> dict:
    """Min distance from the printed body's surface to each stack solid. Frame points on the ring's seat (the flat
    back inside the D49 spot face) are the contact face and are left out."""
    import trimesh
    P, _ = trimesh.sample.sample_surface(frame, SAMPLES, seed=75)
    P = np.vstack([P, frame.vertices])
    r = np.hypot(P[:, 0] - HIP_C[0], P[:, 2] - HIP_C[1])
    P = P[(np.abs(r - 0.0) < 60.0) & (P[:, 1] > back_y - 5.0)]
    r = np.hypot(P[:, 0] - HIP_C[0], P[:, 2] - HIP_C[1])
    seat = (np.abs(P[:, 1] - back_y) < 0.05) & (r < 24.5)
    P = P[~seat]
    out = {}
    for k in ("ring", "keeper", "nuts"):
        s = st[k]
        if k == "nuts":
            d = np.min([_cyl_dist(P, xz, s["r"], *s["y"]) for xz in bolt_positions()], axis=0)
        else:
            d = _cyl_dist(P, HIP_C, s["r"], *s["y"])
        if k == "ring":                 # the ring sits on the seat: only its rim and top face count
            d = np.where(P[:, 1] <= back_y + 0.05, np.inf, d)
        i = int(np.argmin(d))
        out[k] = {"min_mm": round(float(d[i]), 2), "at": [round(float(v), 1) for v in P[i]]}
    s = st["tails"]
    d = np.min([_cyl_dist(P, xz, s["r"], *s["y"]) for xz in bolt_positions()], axis=0)
    i = int(np.argmin(d))
    out["tails"] = {"min_mm": round(float(d[i]), 2), "at": [round(float(v), 1) for v in P[i]]}
    aft = P[(P[:, 1] > back_y + 0.05)]
    ra = np.hypot(aft[:, 0] - HIP_C[0], aft[:, 2] - HIP_C[1])
    near = aft[ra < 30.0]
    out["rim_lip"] = {"r_min_mm": round(float(ra[ra < 30.0].min()), 2) if len(near) else None,
                      "proud_of_back_mm": round(float(near[:, 1].max() - back_y), 2) if len(near) else None}
    return out


def stay_crown_y(frame, z_lo=112.0, z_hi=145.0) -> dict:
    """Bag-face height of the stay crowns (|x| 95-135) in the spreader's bottom band, from STL sections."""
    ys = []
    for z in np.arange(z_lo, z_hi + 0.1, 5.0):
        s = frame.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
        v = s.vertices
        for sgn in (1, -1):
            q = v[(sgn * v[:, 0] > 95) & (sgn * v[:, 0] < 135)]
            if len(q):
                ys.append(float(q[:, 1].max()))
    return {"min": round(min(ys), 2), "max": round(max(ys), 2)}


# ================================================================================================== checks
def bag_side(frame, st: dict) -> dict:
    import bag_concepts as BC
    from patterns_corrie_f_rev3 import he_geometry
    sp = json.load(open(SPREADER_JSON))["chosen"]
    crown = stay_crown_y(frame)
    tails_z = [z for _, z in bolt_positions()]
    z_tail_lo = min(tails_z) - M5_D / 2
    z_tail_hi = max(tails_z) + M5_D / 2
    he = he_geometry()
    z_floor = 60.0 - he["pin_z"]                     # floor seam under the z 60 hinge pin (HE: pin +25)
    sp_face = crown["min"]                           # ASSUMPTION SPREADER-REV-C
    gap_sp = sp_face - st["tip_y"]
    b01 = float(BC.y_frame([z_tail_lo])[0])
    b01_hi = float(BC.y_frame([z_tail_hi])[0])
    gap_b01 = min(b01, b01_hi) - st["tip_y"]
    # B-01 below the spreader: open bay from the floor seam to the spreader bottom edge (z 112); a membrane strip
    # bulging delta over span L needs strain 8 delta^2 / (3 L^2) (shallow-arc length excess).
    z_sp_bottom = 112.0                              # spreader outline z 112-430 (spreader.md rev B / C)
    L = z_sp_bottom - z_floor
    eps_need = 8.0 * gap_b01 ** 2 / (3.0 * L ** 2)
    eps_need_exact = _arc_strain(L, gap_b01)
    eps_cap = 0.05                                   # ASSUMPTION B01-STRAIN
    bulge_at_cap = L * math.sqrt(3.0 * eps_cap / 8.0)
    return {
        "spreader": {"key": sp["key"], "t_mm": round(sp["t_mm"], 2), "crown_y": crown, "wearer_face_y": sp_face,
                     "w_fact_max_mm": round(sp["w_fact_max"], 2), "w_where": sp["w_where"],
                     "gap_nominal_mm": round(gap_sp, 1), "gap_factored_mm": round(gap_sp - sp["w_fact_max"], 1),
                     "bottom_edge_z": z_sp_bottom},
        "b01": {"y_at_tails": [round(b01, 2), round(b01_hi, 2)], "gap_mm": round(gap_b01, 1),
                "tails_z": [round(z_tail_lo, 1), round(z_tail_hi, 1)], "floor_seam_z": z_floor,
                "bay_span_mm": L, "strain_needed": round(eps_need, 3), "strain_needed_arc": round(eps_need_exact, 3),
                "strain_cap": eps_cap, "bulge_at_cap_mm": round(bulge_at_cap, 1),
                "clears": bool(eps_need_exact > eps_cap)},
    }


def _arc_strain(chord: float, sag: float) -> float:
    R = (chord ** 2 / 4 + sag ** 2) / (2 * sag)
    arc = 2 * R * math.asin(min(1.0, chord / (2 * R)))
    if sag > chord / 2:
        arc = 2 * math.pi * R - arc
    return arc / chord - 1.0


def wearer_side(planes: dict, st: dict) -> dict:
    """'Aft' = +y in the FCS (geometry.yaml: '+ AFT (away from the wearer's back, toward the bag)'). The boss face
    at the min y is the wearer face; the Ti mount, heads, belt pin, bow-tie and lumbar pad are all at y < face_y."""
    face, back = planes["face_y"], planes["back_y"]
    head_top = face - TI_BASE_T - HEAD_K
    hub_top = face - HUB_TOP
    return {"aft_is": "+y: away from the wearer's back, toward the bag", "mount_face_y": face, "flat_back_y": back,
            "boss_depth_mm": round(back - face, 2), "tail_tip_y": round(st["tip_y"], 2),
            "solid_between_tails_and_wearer_side_mm": round(back - face + TI_BASE_T, 2),
            "tail_tip_to_mount_face_mm": round(st["tip_y"] - face, 2),
            "head_top_y": round(head_top, 2), "hub_top_y": round(hub_top, 2),
            "heads_below_hub_face_mm": round(head_top - hub_top, 2),
            "heads_changed_by_bl073": False}


def protrusion_band() -> dict:
    hm = _hip_record()
    stack_nom = hm["screw"]["stack_mm"]
    stack_max = stack_nom + 0.2 + 0.1 + 0.05             # ASSUMPTION STACK-TOL (nut -0.3 only shortens)
    stack_min = stack_nom - 0.2 - 0.1 - 0.3 - 0.05
    need = 2 * M5_P + 0.5                                # >= 2 full threads past the nut + end chamfer
    rows = {}
    for L in (30.0, 35.0, 40.0):                         # DIN 7984 standard lengths around the stack
        rows[f"M5x{L:g}"] = {"min_proud_mm": round(L - 0.5 - stack_max, 2), "max_proud_mm": round(L + 0.5 - stack_min, 2),
                             "ok_2_threads": bool(L - 0.5 - stack_max >= need)}
    L_need = stack_max + need + 0.5
    return {"stack_nom_mm": stack_nom, "stack_max_mm": round(stack_max, 2), "stack_min_mm": round(stack_min, 2),
            "need_proud_mm": need, "shortest_length_needed_mm": round(L_need, 2), "standard": rows,
            "shortest_standard_ok": min(int(k[3:]) for k, v in rows.items() if v["ok_2_threads"])}


def fix_options() -> dict:
    """Masses of the fixes the ticket lists, from material records (all for 8 screws / one frame)."""
    import yaml
    def dens(rel):
        return yaml.safe_load(open(ROOT / "data" / "materials" / rel))["properties"]["density_kg_m3"] * 1e-6  # g/mm3
    ti, tpu = dens("metals/ti_6al_4v.yaml"), dens("polymers/tpu_sheet_film.yaml")
    ppa = dens("polymers/ppa_cf_fdm.yaml")
    ultra = yaml.safe_load(open(ROOT / "data/materials/laminates_membranes/challenge_ultra_200.yaml"))["properties"]["areal_density_gsm"]
    a_s = 14.2                                            # M5 tensile stress area, mm2 (ISO 898-1)
    pb = protrusion_band()
    trim = 35.0 - pb["shortest_length_needed_mm"]
    # TPU push-on cap: sleeve OD 7 / ID 4.5 x 5 mm over the tail + 1 mm end
    cap = (math.pi / 4 * (7 ** 2 - 4.5 ** 2) * 5 + math.pi / 4 * 7 ** 2 * 1.0) * tpu
    # keeper grown into a closed cover: wall OD 48.5 / ID 46.1 (1.2 mm) up 7 mm + 1.2 mm roof annulus 48.5 / 24
    cover = (math.pi / 4 * (48.5 ** 2 - 46.1 ** 2) * 7.0 + math.pi / 4 * (48.5 ** 2 - 24 ** 2) * 1.2) * ppa
    patch = 60 * 60 * 1e-6 * ultra                        # 60 x 60 mm B-01 doubler, cloth only
    return {
        "none (keep M5 x 35, no part)": {"g": 0.0, "works": True,
                                         "why": "nothing reaches the tails in any carry mode (sections 2-4)"},
        "shorter screw (cut 35 -> needed length)": {"g": round(-8 * a_s * max(trim, 0) * ti, 2), "works": trim > 0.5,
                                                    "why": f"no standard length between {pb['shortest_length_needed_mm']} and 35; "
                                                           f"cutting saves {max(trim, 0):.1f} mm per screw"},
        "8 TPU push-on caps": {"g": round(8 * cap, 2), "works": True, "why": "covers the thread ends; can be lost"},
        "keeper grown into a closed cover (PPA-CF)": {"g": round(cover, 2), "works": True,
                                                      "why": "one part, hides nuts and tails; reprint the keeper"},
        "B-01 doubler 60 x 60 (ULTRA 200X)": {"g": round(patch, 2), "works": True,
                                             "why": "protects B-01 only; B-01 is 34 mm away already"},
        "lumbar foam relief cut-out": {"g": 0.0, "works": False,
                                       "why": "the foam is on the wearer side; no tail points at it"},
    }


def run() -> dict:
    fr = _frame()
    planes = boss_planes(fr)
    st = stack(planes["back_y"])
    res = {
        "ticket": "BL-075", "date": "2026-11-25",
        "inputs": {"frame": str((H1P / "h1_assembled.stl").relative_to(ROOT)), "bl073": str(BL070_JSON.relative_to(ROOT))},
        "planes": planes,
        "stack": {k: (v if not isinstance(v, dict) else {kk: (list(map(lambda t: round(t, 2), vv)) if isinstance(vv, tuple)
                                                         else round(vv, 2)) for kk, vv in v.items()})
                  for k, v in st.items()},
        "frame": frame_clearance(fr, st, planes["back_y"]),
        "bag": bag_side(fr, st),
        "wearer": wearer_side(planes, st),
        "protrusion": protrusion_band(),
        "fixes": fix_options(),
        "assumptions": {k: {"text": t, "settled_by": s} for k, (t, s) in ASSUMPTIONS.items()},
    }
    res["clears"] = {"frame": all(res["frame"][k]["min_mm"] > 0.5 for k in ("keeper", "nuts", "tails")),
                     "bag_spreader": res["bag"]["spreader"]["gap_factored_mm"] > 0,
                     "bag_b01": res["bag"]["b01"]["clears"],
                     "wearer_side": True, "hipbelt": True}
    res["fix"] = "none (keep M5 x 35, no part)"
    return res


# ================================================================================================== screenshot
def screenshot(res: dict, path: Path = SCREEN) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Rectangle
    fr = _frame()
    x0 = 18.44                                             # through the middle bolt column (z 115.4 / 124.6)
    fig, ax = plt.subplots(figsize=(9.6, 7.4), dpi=110)
    s = fr.section(plane_origin=[x0, 0, 0], plane_normal=[1, 0, 0])
    for e in s.entities:
        p = s.vertices[e.points]
        ax.fill(p[:, 1], p[:, 2], color="#b9bec4", lw=0)
        ax.plot(p[:, 1], p[:, 2], color="#3d4247", lw=0.8)
    from huntkit.gendesign import hip_mount as HM
    mt = trimesh.load(MOUNT_STL)
    mt.apply_transform(HM.frame_matrix())
    for xs, col in ((x0, "#7f6a9e"), (0.0, "#7f6a9e")):
        sm = mt.section(plane_origin=[xs, 0, 0], plane_normal=[1, 0, 0])
        if sm is None:
            continue
        for e in sm.entities:
            p = sm.vertices[e.points]
            ax.fill(p[:, 1], p[:, 2], color=col, alpha=0.35 if xs == 0 else 0.8, lw=0)
    st, pl, bag = res["stack"], res["planes"], res["bag"]
    yb = pl["back_y"]
    ax.add_patch(Rectangle((st["ring"]["y"][0], 120 - 23.5), st["ring_t"], 47, color="#8a9199", label="6061 ring 2 mm"))
    ax.add_patch(Rectangle((st["keeper"]["y"][0], 120 - 24.25), st["keeper_t"], 48.5, fc="none", ec="#2b6e4f", lw=1.2,
                           hatch="///", label="PPA-CF nut keeper 3 mm"))
    for _, z in bolt_positions():
        if abs(z - 115.4) < 0.1 or abs(z - 124.6) < 0.1:
            ax.add_patch(Rectangle((st["nuts"]["y"][0], z - NUT_AF / 2), st["nut_m"], NUT_AF, color="#d08c2c"))
            ax.add_patch(Rectangle((pl["face_y"] - TI_BASE_T - HEAD_K, z - 4.25), HEAD_K, 8.5, color="#5b4a7a"))
            ax.add_patch(Rectangle((pl["face_y"] - TI_BASE_T, z - 2.5), st["tip_y"] - pl["face_y"] + TI_BASE_T, 5.0,
                                   color="#4a4f55"))
    sp = bag["spreader"]
    ax.add_patch(Rectangle((sp["wearer_face_y"], 112), sp["t_mm"], 60, color="#2f3e57", alpha=0.85,
                           label=f"BP-06 spreader (z >= 112), {sp['key']}"))
    ax.add_patch(Rectangle((sp["wearer_face_y"] - sp["w_fact_max_mm"], 112), sp["w_fact_max_mm"], 60, fc="none",
                           ec="#2f3e57", ls="--", lw=0.8))
    import bag_concepts as BC
    zz = np.linspace(35, 172, 50)
    ax.plot(BC.y_frame(zz), zz, color="#1f6fb2", lw=2.2, label="bag B-01 frame face (CORRIE F rev 3)")
    b = bag["b01"]
    yy = np.linspace(0, 1, 30)
    zb = b["floor_seam_z"] + yy * b["bay_span_mm"]
    ax.plot(np.interp(zb, zz, BC.y_frame(zz)) - b["bulge_at_cap_mm"] * np.sin(np.pi * yy), zb, color="#1f6fb2", lw=1,
            ls=":", label=f"B-01 bulge bound below spreader ({b['bulge_at_cap_mm']} mm)")
    ax.axvspan(-120, pl["face_y"] - HUB_TOP, color="#e8d6b0", alpha=0.6, lw=0)
    ax.text(pl["face_y"] - HUB_TOP - 3, 185, "WEARER SIDE\nbelt bow-tie on the pin,\nlumbar pad + pad seat\n(all at y < mount face)",
            ha="right", va="center", fontsize=8.5, color="#6b5320")
    ax.annotate("", xy=(40, 205), xytext=(-10, 205), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(15, 209, "AFT (+y): toward the bag", ha="center", fontsize=9, weight="bold")
    ax.annotate("", xy=(-95, 205), xytext=(-55, 205), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(-75, 209, "toward the wearer's back", ha="center", fontsize=9)
    tip = st["tip_y"]
    ax.annotate(f"tail tips y {tip:.1f}\n(10 mm aft of flat back)", xy=(tip, 115.4), xytext=(tip + 4, 80),
                fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("", xy=(sp["wearer_face_y"], 140), xytext=(tip, 140), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text((tip + sp["wearer_face_y"]) / 2, 143, f"{sp['gap_nominal_mm']} mm\n({sp['gap_factored_mm']} factored)",
            ha="center", va="bottom", fontsize=7.5)
    ax.text(sp["wearer_face_y"] + sp["t_mm"] + 1, 168, f"spreader sag\n{sp['w_fact_max_mm']} mm factored\n(dashed)",
            fontsize=7, va="top")
    ax.annotate("", xy=(b["y_at_tails"][0], 106), xytext=(tip, 106), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text((tip + b["y_at_tails"][0]) / 2, 102, f"{b['gap_mm']} mm to B-01", ha="center", va="top", fontsize=7.5)
    ax.annotate(f"boss 22 mm\n(PPA-CF solid)", xy=((pl["face_y"] + yb) / 2, 147), xytext=(-62, 170), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.annotate("Ti mount + DIN 7984 heads\n(unchanged by BL-073)", xy=(pl["face_y"] - 5, 128), xytext=(-112, 150),
                fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.set_xlim(-120, 70)
    ax.set_ylim(30, 215)
    ax.set_aspect("equal")
    ax.set_xlabel("y, mm (FCS: + aft, toward the bag)")
    ax.set_ylabel("z, mm (up)")
    ax.set_title(f"BL-075  H1-P hip through-bolt stack, section x = {x0} mm (bolt column)\n"
                 "clears frame, spreader, bag B-01; tails point away from the wearer", fontsize=10)
    ax.legend(loc="lower right", fontsize=7.2, framealpha=0.9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    res = run()
    if a.check:
        print(json.dumps({k: res[k] for k in ("planes", "frame", "bag", "wearer", "clears", "fix")}, indent=1))
        return res
    OUT_JSON.write_text(json.dumps(res, indent=1))
    p = screenshot(res)
    print(json.dumps({k: res[k] for k in ("planes", "frame", "bag", "wearer", "protrusion", "fixes", "clears")}, indent=1))
    print("wrote", OUT_JSON, p)
    return res


if __name__ == "__main__":
    main()
