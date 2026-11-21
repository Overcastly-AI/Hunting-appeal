"""BL-055 Part A: H1 close-out before review 6 (structural-fea-engineer).

    python -m huntkit.gendesign.h1_closeout --body      # whole body on the BL-053 print body, nominal + sanded (heavy)
    python -m huntkit.gendesign.h1_closeout             # report: analysis/h1_closeout.md / .json, screens

1. **Whole body** (``body``): ``h1_buckling.full_check`` (strength, fatigue, creep per kit, member buckling, the z 234
   joint) on every R1 basis on the BL-053 body: ``h1_lanes.body_solid`` (BL-049 lanes, BL-051 crown) plus the BL-053
   lug fixes voxelised on the same 2 mm grid (``h1_rev5.fix_mask``). The 0.2 mm sanding allowance on the stays'
   wearer faces (``h1_rev5.SAND_ALLOW``) is a second run with every stay element's stress raised by the section
   ratio measured on the print (``sand_factor``: the print's stay sections, each with 0.2 mm taken off every
   down-facing (-y) edge, against the section as printed).
2. **Hip boss** (``hip_pattern`` / ``hip_check``): M5 brass heat-set inserts that hold the SLM Ti pivot mount on the
   printed hip boss (was D32 with 2 inserts; grown, the inserts split clear of the mount's two legs). Prying model of ``hipbelt_structure.pivot_check`` (tipping about the boss edge), generalised to
   any insert pattern and every tipping direction; capacity from ``data/materials`` ``insert_heatset_brass_m5`` with
   the PAHT-CF hot knock-down and the layer-normal pull. Pilot holes are cut into the print (``add_hip_pilots``, hooked
   into ``frame_h1.print_mesh``) and slice-checked on the exported STL (``hip_slices``).
3. **Pins**: US1 fairlead pins in Ti-6Al-4V (orchestrator call), pin rows and the ledger.

Units mm, N, MPa, g (imperial in the report). Frame coordinates: x lateral (+ = R), y towards the bag, z up.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
PRINT = PACK / "print" / "frame_h1"
RESULTS = ANALYSIS / "h1_closeout.json"
DOC = ANALYSIS / "h1_closeout.md"
OUT = REPO / "outputs" / "h1_closeout"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261121_BL055_"
STAY_X = 115.0

BODY_CHECK = "m1_u2.5_im3_bl053_body"            # h1_buckling.full_check cache: BL-053 body as printed
BODY_SANDED = "m1_u2.5_im3_bl053_body_sanded"    # same body, stay stresses x sand_factor (0.2 mm off the wearer faces)
BODY_BEFORE = "m1_u2.5_im3_bl051_crown"          # h1_crown.BODY_CHECK (the BL-051 body, the record before)
R1 = {"strength": 1.0, "fatigue": 1.0, "buckling": 1.0}   # R1 (load_standard rev C): SF/req >= 1 on every basis
SUPERSEDED_NOTE = ('> **SUPERSEDED (2026-11-14, BL-055) by `h1_rev5.md` (BL-053) and `h1_closeout.md` (BL-055)** for the print, the lane lugs, the US2 clevis joint, the pins, the gauge pass lines and the whole-body margins. BL-053 checks the lane lugs on a submodel cut from the print itself with the 3D cradle legs (down to a 40 mm belly, no minimum-belly rule), adds the lug fixes, hex nut traps and pin retention; BL-055 re-runs the whole body on the BL-053 body (incl. the 0.2 mm sanding allowance), adds the hip-boss insert pattern and the Ti US1 pins. Numbers below that differ from those two records are history.\n')   # written under the title of h1_crown.md, h1_bedfit.md, h1_lanes.md


# ============================================================================================ 1. whole body
def body_solid_bl053() -> tuple:
    """``h1_lanes.body_solid`` (the BL-049 / BL-051 voxel body) with the BL-053 lug fixes (US1 hull block + buttress,
    US2 buttress + root flare, both sides) voxelised on the same 2 mm grid by ``h1_rev5.fix_mask``; keep-outs (passive
    void, joint holes) stay empty."""
    from . import frame_h1 as H1
    from . import h1_fairleads as HF
    from . import h1_lanes as LN
    from . import h1_rev5 as R5
    s, info = LN.body_solid()
    c = H1.base()
    cen = c["cen"]
    out = s.copy()
    per = {}
    for p in HF.placed():
        if not p.get("lane"):
            continue
        near = (np.abs(cen[:, 2] - p["z"]) < 40.0) & (np.abs(cen[:, 0] - p["x"]) < 120.0)
        idx = np.where(near)[0]
        m = R5.fix_mask(p["name"])(cen[idx], p, out[idx])
        add = np.zeros(len(cen), bool)
        add[idx[m]] = True
        add &= ~c["dom"].passive_void & ~c["holes"]
        per[f"{p['name']}_{p['side']}"] = int((add & ~out).sum())
        out |= add
    info = dict(info)
    info["bl053_fix_voxels"] = per
    info["bl053_fix_g"] = round(sum(per.values()) * H1.H ** 3 * 1.06e-3, 1)
    return out, info


SAND_MM = 0.2                      # h1_rev5.SAND_ALLOW max_removed_mm
SAND_Z = (40.0, 60.0, 75.0, 170.0, 190.0, 210.0, 225.0, 250.0, 280.0, 320.0, 360.0, 400.0, 440.0, 480.0, 520.0)


def _section_props(P) -> dict:
    """Area, centroid and second moments of a shapely polygon (x, y): from its triangulated boundary (Green)."""
    def ring(c):
        c = np.asarray(c, float)
        x, y = c[:-1, 0], c[:-1, 1]
        x1, y1 = c[1:, 0], c[1:, 1]
        cr = x * y1 - x1 * y
        A = cr.sum() / 2
        Sx = ((x + x1) * cr).sum() / 6          # first moment about y (gives cx)
        Sy = ((y + y1) * cr).sum() / 6
        Ixx = ((y ** 2 + y * y1 + y1 ** 2) * cr).sum() / 12     # about x axis (y^2)
        Iyy = ((x ** 2 + x * x1 + x1 ** 2) * cr).sum() / 12
        return A, Sx, Sy, Ixx, Iyy
    geoms = getattr(P, "geoms", [P])
    tot = np.zeros(5)
    for g in geoms:
        r = np.array(ring(g.exterior.coords))
        tot += r * np.sign(r[0])
        for h in g.interiors:
            q = np.array(ring(h.coords))
            tot -= q * np.sign(q[0])
    A, Sx, Sy, Ixx, Iyy = tot
    cx, cy = Sx / A, Sy / A
    Ixc, Iyc = Ixx - A * cy ** 2, Iyy - A * cx ** 2
    b = P.bounds
    return {"A": A, "cx": cx, "cy": cy, "Ix": Ixc, "Iy": Iyc,
            "Zx_wearer": Ixc / (cy - b[1]), "Zx_bag": Ixc / (b[3] - cy), "Zy": Iyc / max(cx - b[0], b[2] - cx)}


def sand_factor(mesh=None, zs=SAND_Z, sand: float = SAND_MM) -> dict:
    """Stress ratio sanded / as printed for every stay section of the print: each section (|x| 115 +/- 13 mm at z)
    with ``sand`` mm taken off every down-facing (-y, wearer) edge, i.e. P n (P moved +sand in y). Ratios for the
    axial stress (A0 / A), bending in y at the wearer and the bag fibre (Z0 / Z, centroid shift included) and
    bending in x; ``k`` = the largest over all of them and every section (applied to every stay element). Only the
    outer skin is sanded: bores, sleeves and traps carry support blockers (print_settings_bl053.json)."""
    import trimesh
    from shapely import affinity
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    m = mesh if mesh is not None else trimesh.load(PRINT / "h1_assembled.stl", force="mesh")
    rows = []
    for z in zs:
        sec = m.section(plane_origin=[0.0, 0.0, float(z)], plane_normal=[0.0, 0.0, 1.0])
        if sec is None:
            continue
        loops = [Polygon(L[:, :2]) for L in sec.discrete if len(L) > 3]
        loops = [L.buffer(0) for L in loops if L.is_valid or L.buffer(0).area > 0]
        for s, tag in ((1.0, "R"), (-1.0, "L")):
            win = box(s * STAY_X - 13.0, -80.0, s * STAY_X + 13.0, 80.0)
            parts = [L.intersection(win) for L in loops]
            # even-odd: the stay section is the union of the outer loops minus the bores (sleeve) inside them
            outer = [p for p in parts if p.area > 1.0]
            if not outer:
                continue
            outer.sort(key=lambda p: -p.area)
            P = outer[0]
            for q in outer[1:]:
                P = P.difference(q) if P.contains(q.representative_point()) else P.union(q)
            if P.area < 50.0:
                continue
            # only the outer skin is sanded (bores and traps carry blockers, no support): fill the holes first
            from shapely.geometry import MultiPolygon
            geoms = getattr(P, "geoms", [P])
            filled = unary_union([Polygon(g.exterior.coords) for g in geoms])
            Ps = P.intersection(affinity.translate(filled, 0.0, sand))
            a, b = _section_props(P), _section_props(Ps)
            r = {"z": z, "side": tag, "A_mm2": round(a["A"], 1), "depth_y_mm": round(P.bounds[3] - P.bounds[1], 2),
                 "axial": a["A"] / b["A"], "bend_y_wearer": a["Zx_wearer"] / b["Zx_wearer"],
                 "bend_y_bag": a["Zx_bag"] / b["Zx_bag"], "bend_x": a["Zy"] / b["Zy"],
                 "removed_mm2": round(a["A"] - b["A"], 2)}
            r["k"] = max(r["axial"], r["bend_y_wearer"], r["bend_y_bag"], r["bend_x"])
            rows.append({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    k = max(r["k"] for r in rows)
    worst = max(rows, key=lambda r: r["k"])
    return {"sand_mm": sand, "k": round(k, 4), "worst": worst, "rows": rows,
            "rect_equivalent_loss": round(1 - (1 - sand / 18.0) ** 2, 4),
            "rule": "every stay element's stress x k (stay = h1_sleeve.region 'stay ...')"}


def stay_mask(cen: np.ndarray) -> np.ndarray:
    """Stay elements of a solved field (element centres): h1_sleeve.region labels that start with 'stay'."""
    from . import h1_sleeve as S
    return np.array([S.region(p).startswith("stay") for p in cen], bool)


def body(log=print, sanded: bool = True, solid=None, info=None, names=(BODY_CHECK, BODY_SANDED),
         out=None) -> dict:
    """``h1_buckling.full_check`` on the BL-053 body as h1_crown.body ran it (lane kit sets, real crown models), and
    the same with the stays sanded (stresses x sand_factor k on every stay element; buckling and the z 234 joint see
    the same scaled stress, which is conservative for both). BL-058: ``solid`` / ``info`` / ``names`` / ``out`` run
    the same check on another voxel body (bl058_frame.body_stl: the exported print re-rastered) under other cache
    names; the defaults are the BL-055 run."""
    from . import h1_buckling as B
    from . import h1_lanes as LN
    from . import h1_sleeve as S
    from . import h1_spine_channel as SC
    out = OUT if out is None else out
    if solid is None:
        solid, info = body_solid_bl053()
    out.mkdir(parents=True, exist_ok=True)
    (out / "body_solid.json").write_text(json.dumps(info, default=float))
    np.savez_compressed(out / "body_solid.npz", solid=solid)
    res = {"voxels": info}
    orig = S.kit_sets
    with SC.real_crown_models(), SC._real_caches():
        S.kit_sets = LN.lane_kit_sets(orig)
        try:
            res["nominal"] = B.full_check(names[0], solid, log=log)
            if sanded:
                sf = sand_factor()
                (out / "sand_factor.json").write_text(json.dumps(sf, default=float))
                k = sf["k"]
                o_solve = S.solve_fields_w

                def solve_sanded(dom, sol, sets, weights=None):
                    f = o_solve(dom, sol, sets, weights)
                    m = stay_mask(f["cen"])
                    for st in f["stress"]:
                        st[m] *= np.float32(k)
                    return f
                S.solve_fields_w = solve_sanded
                try:
                    res["sanded"] = B.full_check(names[1], solid, log=log)
                finally:
                    S.solve_fields_w = o_solve
        finally:
            S.kit_sets = orig
    return res


def body_summary() -> dict | None:
    """Per basis: the BL-051 record, the BL-053 body as printed and sanded; margins against R1."""
    from . import h1_buckling as B
    p0, p1, p2 = (B.OUT / f"check_{n}.json" for n in (BODY_BEFORE, BODY_CHECK, BODY_SANDED))
    if not p1.exists():
        return None
    keys = ("strength", "fatigue", "creep")

    def row(r):
        return {**{k: round(r["min"][k], 3) for k in keys}, "buckling": round(r["buckling_min"], 3),
                "joint_strength": round(r["joint_strength"], 3), "joint_fatigue": round(r["joint_fatigue"], 3),
                "governing_tag": r.get("governing_tag")}
    d0 = json.loads(p0.read_text()) if p0.exists() else {}
    d1 = json.loads(p1.read_text())
    d2 = json.loads(p2.read_text()) if p2.exists() else {}
    out = {"bases": {}}
    for b in B.BASES_CHECK:
        out["bases"][b] = {"bl051": row(d0[b]) if b in d0 else None, "bl053": row(d1[b]) if b in d1 else None,
                           "bl053_sanded": row(d2[b]) if b in d2 else None}
    out["raster_g"] = {"bl051": round(d0.get("raster_g", float("nan")), 1), "bl053": round(d1["raster_g"], 1)}
    out["governing_region"] = d1.get("governing_region")
    out["top_regions_fine_sm8"] = d1.get("fine_sm8", {}).get("top_regions")
    out["keepouts"] = d1.get("keepouts")
    sf = OUT / "sand_factor.json"
    if sf.exists():
        s = json.loads(sf.read_text())
        out["sand_factor"] = {k: s[k] for k in ("sand_mm", "k", "worst", "rect_equivalent_loss")}
    return out


# ============================================================================================ 2. hip boss inserts
HIP_C = (0.0, 120.0)               # boss axis (x, z): frame_topopt hard point 'hipbelt_pivot' (0, -48.1, 120)
HIP_FACE_Y = -48.4                 # the boss's wearer face on the BL-053 print (sliced: solid from y -48.4)
HIP_STAND = 21.0                   # hipbelt_structure.pivot_check 'stand': pin load stand-off from the boss face
HIP_PIN_HOLE_D = 10.0              # the SLM mount's pin bore through its base (lug_hip_pivot_mount_slm_ti.stl, D10)
HIP_LAND = 1.0                     # ASSUMPTION HIP-LAND: >= 1 mm of flange between an insert hole and the pin bore
INS_EXTRA_DEPTH = 2.0              # ASSUMPTION INS-DEPTH: pilot hole = insert length + 2 mm for the displaced melt
SF_GOAL = 1.5                      # ticket: SF >= 1.5 (strength rows carry the case factor: SF/req)
FAT_GOAL = 1.15                    # ticket: fatigue >= 1.15 (BL-021 scatter goal)


def insert_record() -> dict:
    """The insert and the host: data/materials insert_heatset_brass_m5, pa12_cf_fdm_paht."""
    from huntkit.materials import load
    ins = load("insert_heatset_brass_m5")
    pa = load("pa12_cf_fdm_paht")
    g = lambda r, k: float(r.require(k))   # noqa: E731
    out = {"pullout_n": g(ins, "pullout_strength_n"), "hole_d": g(ins, "hole_diameter_mm"),
           "od": g(ins, "outer_diameter_mm"), "length": g(ins, "length_mm"), "min_wall": g(ins, "min_wall_mm"),
           "mass_g": g(ins, "mass_g"), "hot": g(pa, "env_knockdown_ratio"),
           "z_ratio": g(pa, "tensile_strength_z_mpa") / g(pa, "tensile_strength_xy_mpa"),
           "fat_ratio": g(pa, "fatigue_1e5_ratio"), "creep_ratio": g(pa, "creep_rupture_8h_40c_ratio"),
           "torque_max_n_m": g(ins, "tightening_torque_max_n_m")}
    return out


MOUNT_STL = PACK / "print" / "legacy" / "lug_hip_pivot_mount_slm_ti_D44_drawn.stl"   # BL-056: the drawn D44 x 1.2
#   mount this study read, frozen; the print file itself is now the BL-056 redraw (huntkit/gendesign/hip_mount.py)
MOUNT_FLANGE_T = 1.2               # the SLM mount's base disc as drawn (sliced: D44 disc solid to z 1.2, legs above)
HEAD_D = 8.5                       # DIN 7984 M5 low head (frame_comp_B bolt row)
HEAD_LEG_CLEAR = 1.0               # ASSUMPTION HEAD-LEG: >= 1 mm between a screw head and a mount leg root (driver access)


@functools.lru_cache(maxsize=None)
def mount_legs() -> tuple:
    """Footprints of the SLM mount's two legs at their root (0.3 mm above the base disc), in frame (x, z - 120).
    ASSUMPTION MOUNT-ORIENT: the mount's local x is frame x and its local y is frame z (the legs stand above and below
    the pin, along the vertical pin load V); the disc centre (22, 22) is the boss axis."""
    import trimesh
    from shapely.geometry import Polygon
    m = trimesh.load(MOUNT_STL, force="mesh")
    c = m.bounds[0] + m.extents / 2.0
    sec = m.section(plane_origin=[0.0, 0.0, MOUNT_FLANGE_T + 0.3], plane_normal=[0.0, 0.0, 1.0])
    out = []
    for L in sec.discrete:
        P = Polygon(L[:, :2] - c[:2]).buffer(0)
        if P.area > 20.0 and P.centroid.distance(Polygon([(0, 0), (0.1, 0), (0, 0.1)])) > 5.0:
            out.append(P)
    return tuple(out)


def split_step(ring_r: float) -> float:
    """The least step (whole deg) between neighbours on a ``ring_r`` circle that keeps the insert-hole wall (record
    min_wall) and clear heads (HEAD_D): chord >= max(hole D + wall, HEAD_D)."""
    ir = insert_record()
    c = max(ir["hole_d"] + ir["min_wall"], HEAD_D)
    return float(math.ceil(math.degrees(2.0 * math.asin(c / 2.0 / ring_r)) - 1e-9))


def split_angles(n: int, step: float) -> list:
    """``n`` holes in two equal groups about the frame +x and -x axes (clear of the mount legs at +/-z), ``step`` deg
    between neighbours in a group."""
    k = n // 2
    half = [-step * (k - 1) / 2.0 + i * step for i in range(k)]
    return half + [180.0 - a for a in half]


def hip_pattern(n: int, ring_r: float, boss_d: float, rot_deg: float = 0.0, layout: str = "ring",
                depth: float | None = None, step: float | None = None) -> dict:
    """``n`` inserts on a ``ring_r`` circle about the boss axis (angle from frame +x towards +z): ``layout`` 'ring' =
    equally spaced from ``rot_deg``; 'split' = two groups of n/2 about +/-x, ``step`` deg apart (default split_step),
    clear of the mount legs. Boss face diameter ``boss_d``. Positions in frame (x, z) and the wall rules: insert hole to
    the boss edge, between holes, to the mount's pin bore (+ HIP_LAND), the hole floor, and the screw head to the
    mount's leg roots (HEAD_LEG_CLEAR)."""
    from shapely.geometry import Point
    ir = insert_record()
    if layout == "split":
        ang = split_angles(n, split_step(ring_r) if step is None else step)
    else:
        ang = list(rot_deg + 360.0 * np.arange(n) / n)
    a = np.radians(ang)
    pos = np.c_[HIP_C[0] + ring_r * np.cos(a), HIP_C[1] + ring_r * np.sin(a)]
    dh = ir["hole_d"]
    rel = pos - np.asarray(HIP_C)
    pitch = min(float(np.hypot(*(rel[i] - rel[j]))) for i in range(n) for j in range(i)) if n > 1 else float("inf")
    hole_depth = ir["length"] + INS_EXTRA_DEPTH
    walls = {"edge_mm": boss_d / 2 - ring_r - dh / 2, "between_mm": pitch - dh,
             "to_pin_bore_mm": ring_r - dh / 2 - HIP_PIN_HOLE_D / 2,
             "head_to_leg_mm": min(Point(x, z).distance(L) for x, z in rel for L in mount_legs()) - HEAD_D / 2,
             "head_to_head_mm": pitch - HEAD_D}
    if depth is not None:
        walls["floor_mm"] = depth - hole_depth
    rule = ir["min_wall"]
    ok = walls["edge_mm"] >= rule - 1e-9 and walls["between_mm"] >= rule - 1e-9 and \
        walls["to_pin_bore_mm"] >= HIP_LAND - 1e-9 and walls.get("floor_mm", rule) >= rule - 1e-9 and \
        walls["head_to_leg_mm"] >= HEAD_LEG_CLEAR - 1e-9 and walls["head_to_head_mm"] >= 0.0
    return {"n": n, "ring_r": ring_r, "boss_d": boss_d, "rot_deg": rot_deg, "layout": layout,
            "angles_deg": [round(float(v), 2) for v in ang],
            "positions_xz": [[round(float(x), 2), round(float(z), 2)] for x, z in pos],
            "hole_d": dh, "hole_depth": hole_depth, "pitch_mm": round(pitch, 2),
            "walls": {k: round(v, 2) for k, v in walls.items()}, "wall_rule_mm": rule, "walls_ok": bool(ok)}


def tip_tension(pat: dict, V: float, H: float, e: float = None, stand: float = HIP_STAND, n_dir: int = 72) -> dict:
    """Worst insert tension of a pattern under the pin load: the mount tips about the boss edge (the record's
    prying model, hipbelt_structure.pivot_check), generalised to any pattern and to every tipping direction phi:
    M = stand V + e H, less H R (H presses the face at the axis); a rigid flange, insert tension in proportion to its
    distance from the tipping line d_i = R + r_i cos(theta_i - phi): T_max = (M - H R) d_max / sum d_i^2.
    ``e`` = the pad-offset arm (hipbelt E_PAD_MM)."""
    from . import hipbelt_structure as HS
    e = HS.E_PAD_MM if e is None else e
    R = pat["boss_d"] / 2
    P = np.asarray(pat["positions_xz"], float) - np.asarray(HIP_C)
    M = stand * V + max(e, 0.0) * H - R * H
    worst = (0.0, 0.0)
    for ph in np.linspace(0.0, 2 * math.pi, n_dir, endpoint=False):
        d = R + P @ np.array([math.cos(ph), math.sin(ph)])
        T = max(M, 0.0) * d.max() / float((d ** 2).sum())
        if T > worst[0]:
            worst = (T, math.degrees(ph))
    return {"M_net_nmm": round(M, 1), "T_max_n": round(worst[0], 1), "phi_deg": round(worst[1], 1)}


def hip_capacity(z_ratio: bool = True) -> dict:
    """Insert pull-out design values (per insert): static = record pull-out x hot knock-down (x the PAHT-CF z / xy
    strength ratio when pulled along the layer normal: the boss axis is frame y, the print's layer normal);
    fatigue (1e5, 0 -> peak) = static x fatigue_1e5_ratio; sustained = static x creep_rupture ratio."""
    ir = insert_record()
    st = ir["pullout_n"] * ir["hot"] * (ir["z_ratio"] if z_ratio else 1.0)
    return {"static_n": round(st, 1), "fatigue_n": round(st * ir["fat_ratio"], 1),
            "sustained_n": round(st * ir["creep_ratio"], 1), "z_ratio_applied": z_ratio,
            "basis": f"{ir['pullout_n']:g} N (insert record) x hot {ir['hot']}"
                     + (f" x layer-normal {ir['z_ratio']:.3f} (47 / 88 MPa)" if z_ratio else "")}


def hip_check(pat: dict, z_ratio: bool = True) -> dict:
    """Every hipbelt load set (hipbelt_structure.load_sets: C2, C1 strength; walk fatigue; carry sustained) with the
    lumbar push H on the pin (the bound, hipbelt_structural 4) and on the frame pad (the recommended plate)."""
    from . import hipbelt_structure as HS
    cap = hip_capacity(z_ratio)
    rows = {}
    for hon in (True, False):
        piv = HS.pivot_check(h_on_pivot=hon)
        for k, v in piv.items():
            t = tip_tension(pat, v["V_n"], v["H_n"])
            kind = HS.load_sets()[k].kind
            c = {"strength": cap["static_n"], "fatigue": cap["fatigue_n"], "creep": cap["sustained_n"]}[kind]
            goal = {"strength": SF_GOAL, "fatigue": FAT_GOAL, "creep": SF_GOAL}[kind]
            rows[f"{k}|{'H_pin' if hon else 'H_frame'}"] = {**t, "V_n": round(v["V_n"], 1), "H_n": round(v["H_n"], 1),
                                                           "kind": kind, "cap_n": c,
                                                           "sf": round(c / max(t["T_max_n"], 1e-9), 3), "goal": goal}
    gov = {kd: min((r for r in rows.values() if r["kind"] == kd), key=lambda r: r["sf"] / r["goal"])
           for kd in ("strength", "fatigue", "creep")}
    return {"pattern": pat, "capacity": cap, "rows": rows,
            "min_sf": {kd: r["sf"] for kd, r in gov.items()},
            "pass": all(r["sf"] >= r["goal"] for r in gov.values()) and pat["walls_ok"]}


def hip_record_check() -> dict:
    """Reproduce hipbelt_structural 4 (2 x M5 at x +/-11 on the D32 boss, cap 1500 x 0.8): C2 with H on the pin
    0.995, H on the frame 1.14; then the same pattern on the insert record (1200 N x hot)."""
    pat = {"boss_d": 32.0, "positions_xz": [[-11.0, HIP_C[1]], [11.0, HIP_C[1]]]}
    from . import hipbelt_structure as HS
    out = {}
    for hon in (True, False):
        v = HS.pivot_check(h_on_pivot=hon)["C2"]
        # the record tips only about the lower edge (phi = -90 deg: V down): its 2 screws are 16 mm off that edge
        R = 16.0
        M = HIP_STAND * v["V_n"] + HS.E_PAD_MM * v["H_n"] - R * v["H_n"]
        d = np.array([R, R])
        T = M * d.max() / float((d ** 2).sum())
        out["H_pin" if hon else "H_frame"] = {"T_n": round(T, 1), "sf_record_cap": round(HS.M5_INSERT_PULLOUT_N * HS.HOT / T, 3),
                                              "sf_insert_record": round(hip_capacity(False)["static_n"] / T, 3),
                                              "sf_insert_record_z": round(hip_capacity(True)["static_n"] / T, 3),
                                              "all_directions": tip_tension({**pat, "boss_d": 32.0}, v["V_n"], v["H_n"])}
    return out


HIP_SWEEP = [(2, 11.0, 32.0, 0.0, "ring"), (4, 10.0, 32.0, 45.0, "ring"), (6, 10.0, 32.0, 0.0, "ring"),
             (6, 16.0, 44.0, 0.0, "ring"), (9, 16.0, 44.0, 0.0, "ring"), (10, 16.0, 44.0, 0.0, "ring"),
             (8, 16.0, 44.0, 0.0, "split"), (10, 16.0, 44.0, 0.0, "split"), (8, 17.0, 46.0, 0.0, "split"),
             (8, 18.0, 48.0, 0.0, "split"), (6, 19.0, 50.0, 0.0, "split"), (8, 19.0, 50.0, 0.0, "split"),
             (10, 19.0, 50.0, 0.0, "split")]
HIP_CHOSEN = (8, 19.0, 50.0, 0.0, "split")  # n, ring r, boss face D, rotation, layout: the fewest inserts that pass with
#   the walls and the leg clearance, on the smallest boss that keeps the fatigue row >= 5 % over its goal (the prying
#   model assumes a rigid flange: unvalidated until HB-6); D48 / r18 passes at 1.16 (1 % over)
HIP_BOSS_DEPTH = 16.0                       # grown boss: solid from the face HIP_FACE_Y to y + 16 (floor wall 4.5)


def hip_study() -> dict:
    """The sweep (with and without the layer-normal ratio), the chosen pattern, and the record reproduction."""
    rows = []
    for n, r, D, rot, lay in HIP_SWEEP:
        pat = hip_pattern(n, r, D, rot, lay, depth=HIP_BOSS_DEPTH if D > 32 else 19.2)
        a, b = hip_check(pat, True), hip_check(pat, False)
        rows.append({"n": n, "ring_r": r, "boss_d": D, "layout": lay, "walls_ok": pat["walls_ok"], "walls": pat["walls"],
                     "z_ratio": {**a["min_sf"], "pass": a["pass"]}, "no_z_ratio": {**b["min_sf"], "pass": b["pass"]}})
    pat = hip_pattern(*HIP_CHOSEN, depth=HIP_BOSS_DEPTH)
    ch = hip_check(pat, True)
    ir = insert_record()
    return {"record": hip_record_check(), "sweep": rows, "chosen": ch, "insert": ir,
            "inserts_g": round(HIP_CHOSEN[0] * ir["mass_g"], 2)}



# ---------------------------------------------------------------------------------------------- print: boss + pilots
HIP_PILOTS = True                  # frame_h1.print_mesh grows the hip boss and cuts the insert pilot holes


def _cyl_y(x, z, y0, y1, d, seg=96):
    import manifold3d as m3d
    return m3d.Manifold.cylinder(y1 - y0, d / 2.0, d / 2.0, seg).rotate((-90.0, 0.0, 0.0)).translate((x, y0, z))


def add_hip_pilots(man, log=print, stats: dict | None = None):
    """The hip boss grown to the Ti mount's flange (HIP_CHOSEN boss D, HIP_BOSS_DEPTH deep from the wearer face,
    whose plane drops 0.05 mm so no face is coplanar) and the insert pilot holes (record hole D x insert length +
    INS_EXTRA_DEPTH) cut from the face. The face is the print's plate face (wearer face down): the holes print as
    vertical blind holes open to the plate, no support."""
    from . import h1_rev5 as R5
    n, r, D = HIP_CHOSEN[:3]
    pat = hip_pattern(*HIP_CHOSEN, depth=HIP_BOSS_DEPTH)
    cx, cz = HIP_C
    probe = man ^ R5._box_m((cx - 10.0, -80.0, cz - 10.0), (cx + 10.0, -20.0, cz + 10.0))
    y_face = float(probe.bounding_box()[1])
    y0 = y_face - 0.05
    v0 = man.volume()
    man = man + _cyl_y(cx, cz, y0, y_face + HIP_BOSS_DEPTH, D)
    v1 = man.volume()
    for x, z in pat["positions_xz"]:
        man = man - _cyl_y(x, z, y0 - 1.0, y0 + pat["hole_depth"], pat["hole_d"], 48)
    v2 = man.volume()
    st = {"y_face_before": round(y_face, 3), "y_face": round(y0, 3), "boss_added_g": round((v1 - v0) * 1.06e-3, 2),
          "holes_cut_g": round((v1 - v2) * 1.06e-3, 2), "net_g": round((v2 - v0) * 1.06e-3, 2), "pattern": pat}
    if stats is not None:
        stats.update(st)
    if log:
        log(f"  hip boss D{D:g} + {n} pilot holes D{pat['hole_d']:g} x {pat['hole_depth']:g} (BL-055): "
            f"{st['net_g']:+.2f} g")
    return man


def hip_slices(path: Path | None = None) -> dict:
    """Slice the assembled print normal to y at the boss: 1 / 6 / 10.5 mm into the face every pilot hole is there at
    the record's hole size on its position, the boss section is at least the boss face less the holes; 2 mm past the
    hole floor the boss is closed (no hole). The flat lower half (print coordinates) is sliced at 0.6 / 6 / 10.5 mm
    above the plate and must show the same n round holes."""
    import trimesh
    from shapely.geometry import Polygon
    m = trimesh.load(path or PRINT / "h1_assembled.stl", force="mesh")
    n, r, D = HIP_CHOSEN[:3]
    pat = hip_pattern(*HIP_CHOSEN, depth=HIP_BOSS_DEPTH)
    pos = np.asarray(pat["positions_xz"], float)
    y_face = float(m.bounds[0][1])
    out = {"y_face": round(y_face, 3), "rows": {}}
    ok = True
    for dy in (1.0, 6.0, 10.5, pat["hole_depth"] + 2.0):
        sec = m.section(plane_origin=[0.0, y_face + dy, 0.0], plane_normal=[0.0, 1.0, 0.0])
        loops = [Polygon(L[:, [0, 2]]) for L in sec.discrete if len(L) > 3]
        loops = [L for L in loops if L.is_valid and L.area > 0.5]
        near = [L for L in loops if math.hypot(L.centroid.x - HIP_C[0], L.centroid.y - HIP_C[1]) < D / 2 + 1.0]
        holes = [L for L in near if L.area < 60.0]
        outer = max(near, key=lambda L: L.area) if near else None
        found = []
        for x, z in pos:
            h = [L for L in holes if math.hypot(L.centroid.x - x, L.centroid.y - z) < 0.3]
            found.append(round(2 * math.sqrt(h[0].area / math.pi), 2) if h else None)
        want_holes = dy < pat["hole_depth"]
        row = {"holes_d_eq": found, "outer_area_mm2": round(outer.area, 1) if outer is not None else 0.0,
               "outer_bounds_xz": [round(v, 2) for v in outer.bounds] if outer is not None else None}
        if want_holes:
            row["pass"] = bool(all(f is not None and abs(f - pat["hole_d"]) < 0.25 for f in found)
                               and outer is not None and outer.bounds[2] - outer.bounds[0] >= D - 0.5)
        else:
            row["pass"] = bool(all(f is None for f in found))
        ok &= row["pass"]
        out["rows"][f"y_face+{dy:g}"] = row
    # the flat lower half as it goes to the slicer
    f = trimesh.load(PRINT / "h1_lower_flat.stl", force="mesh")
    flat = {}
    for z in (0.6, 6.0, 10.5):
        sec = f.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
        loops = [Polygon(L[:, :2]) for L in sec.discrete if len(L) > 3]
        rnd = [L for L in loops if L.is_valid and 25.0 < L.area < 40.0
               and abs(2 * math.sqrt(L.area / math.pi) - pat["hole_d"]) < 0.25
               and L.length / (math.pi * 2 * math.sqrt(L.area / math.pi)) < 1.02]
        flat[f"z{z:g}"] = len(rnd)
    out["lower_flat_round_holes"] = flat
    ok &= all(v == n for v in flat.values())
    out["pass"] = bool(ok)
    return out



# ============================================================================================ 3. pins
PIN_MATERIAL = {"hinge": "ti_6al_4v", "us1": "ti_6al_4v"}   # BL-055 (orchestrator call): US1 in Ti; the rest 7075-T6


def pins(bl058: bool = True) -> dict:
    """The 12 fairlead pin rows of h1_rev5.pins (BL-053 retention scheme, shank, head, cross hole, clip, tether) with
    the US1 pins in Ti-6Al-4V: mass from the record density on the same shank + head, bending re-checked on the same
    rows (h1_lanes.pin_check: S-basis yield, fatigue limit x 0.9, Goodman to R 0). ``mass`` stays the BL-055 booking
    (ledger BL055 row). BL-058 (``bl058``): each station's pin, retainer and tether as bl058_frame.pin_overlay
    re-specifies them (rows, BOM, ``mass_bl058``; the ledger's BL058 row books the change)."""
    from huntkit.materials import load
    from . import h1_fairleads as HF
    from . import h1_lanes as LN
    from . import h1_rev5 as R5
    base = R5.pins()
    out = {k: v for k, v in base.items() if k not in ("stations", "mass")}
    out["stations"] = {}
    geo = {p["name"]: p["geom"] for p in HF.placed() if p["side"] == "R"}
    delta = 0.0
    for name, row in base["stations"].items():
        mat = PIN_MATERIAL.get(name, "alu_7075_t6")
        r = dict(row)
        if mat != row["material"]:
            g = geo[name]
            rho_new = float(load(mat).require("density_kg_m3"))
            rho_old = float(load(row["material"]).require("density_kg_m3"))
            m_new = row["pin_g"] * rho_new / rho_old
            delta += 2 * (m_new - row["pin_g"])
            r.update({"material": mat, "pin_g": round(m_new, 2),
                      "set_g": round(m_new + R5.RETAINER["mass_g"] + R5.RETAINER["tether_g"], 2),
                      "was": {"material": row["material"], "pin_g": row["pin_g"], "bending": row.get("bending")}})
            if "bending" in row:
                b = row["bending"]
                pc = LN.pin_check(b["design_yz_n"], g.throat, g.cheek, g.pin_d, mat, R5.G_CRADLE)
                pc95 = LN.pin_check(b["dy95_yz_n"], g.throat, g.cheek, g.pin_d, mat, R5.G_CRADLE)
                r["bending"] = {"design_yz_n": b["design_yz_n"], "sf_yield": round(pc["sf_yield"], 2),
                                "sf_fatigue": round(pc["sf_fatigue"], 2), "dy95_yz_n": b["dy95_yz_n"],
                                "dy95_sf_yield": round(pc95["sf_yield"], 2),
                                "dy95_sf_fatigue": round(pc95["sf_fatigue"], 2)}
        out["stations"][name] = r
    out["mass"] = {"pins_g": round(sum(2 * r["pin_g"] for r in out["stations"].values()), 2),
                   "clips_tethers_g": base["mass"]["clips_tethers_g"], "delta_vs_bl053_g": round(delta, 2)}
    if bl058:                          # BL-058 (review 6 M-2 / M-3): retainer per station, US2 groove + E-clip
        from . import bl058_frame as B58
        for n, r in out["stations"].items():
            ov = B58.pin_overlay(n, r["material"])
            r["bl055"] = {k: r[k] for k in ("shank_mm", "cross_hole", "clip_side", "pin_g", "set_g")}
            r.update(ov)
        out["retainer"] = B58.retainer_record(out["retainer"])
        out["retainers_bl058"] = B58.retainer_summary()
        out["clip_double_shear_n"] = B58.clip_double_shear_n()
        out["mass_bl058"] = {"pins_g": round(sum(2 * r["pin_g"] for r in out["stations"].values()), 2),
                             "retainers_tethers_g": round(sum(2 * (r["set_g"] - r["pin_g"])
                                                              for r in out["stations"].values()), 2)}
        out["scheme"] = ("headed pin; hairpin clip (McMaster 90153A214) in a 1.5 mm cross hole on the far side at "
                         "hinge / US1 / IM1-3, body pointing fore; US2: head in a D9 x 2 clevis counterbore, DIN 6799 "
                         "E-clip in a groove on the far side, tether from a tail hole round the lug arm")
    out["bom"] = [{"id": f"PIN-{n.upper()}", "station": n, "qty": r["qty"], "material": r["material"],
                   "pin_d_mm": r["pin_d_mm"], "shank_mm": r["shank_mm"], "head_mm": r["head_mm"],
                   "cross_hole_d_mm": r["cross_hole"]["d_mm"],
                   "cross_hole_from_far_cheek_face_mm": r["cross_hole"]["from_far_cheek_face_mm"],
                   "clip_side": r["clip_side"], "pin_g": r["pin_g"], "set_g": r["set_g"],
                   **({k: r[k] for k in ("retainer", "retainer_part", "groove", "tether_hole", "head_seat")
                       if k in r})}
                  for n, r in out["stations"].items()]
    return out


# ============================================================================================ mass
HIP_INSERTS_BOOKED = 2             # ASSUMPTION HIP-BOOKED: the frame's fixed lump (frame_h1.FIXED_G 'Ti mount, inserts';
#                                    frame_eval.INSERTS_G 'brass heat-set inserts ... joint bolts (2 x M5 x 2)') books
#                                    the 2 hip-mount inserts and 2 screws of hipbelt_structural 4
HIP_SCREW_L = 12.0                 # BL-058 (review 6 m-2): M5 x 12 = Ti mount base 3 + 9.0 in the 9.5 mm insert; the x 14
#                                    tip reached 11.0 mm into the 11.5 mm pilot whose bottom 2 mm is the melt reservoir
HIP_SCREW_L_BOOKED = 14.0          # the length BL-055 booked in the ledger (mass_rows; the BL058 ledger row books the change)


def mass_rows(export: dict | None, pn: dict, hip: dict) -> dict:
    """BL-055 deltas: the print (assembled now - BL-053) from the export, the extra hip inserts and screws, the US1
    pins in Ti (pins())."""
    from .frame_comp_B import bolt_mass_g
    n = HIP_CHOSEN[0]
    ins_g = hip["insert"]["mass_g"]
    scr = bolt_mass_g(HIP_SCREW_L_BOOKED)
    out = {"hip_inserts": n, "hip_inserts_booked": HIP_INSERTS_BOOKED,
           "hip_inserts_delta_g": round((n - HIP_INSERTS_BOOKED) * ins_g, 2),
           "hip_screw": f"Ti gr5 M5 x {HIP_SCREW_L_BOOKED:g} DIN 7984", "hip_screw_g": round(scr, 2),
           "booked_note": f"the BL-055 booking (ledger BL055); the screw is now M5 x {HIP_SCREW_L:g} (BL-058, "
                          "analysis/bl058.json hip_screws; the ledger's BL058 row books the change)",
           "hip_screws_delta_g": round((n - HIP_INSERTS_BOOKED) * scr, 2),
           "us1_ti_pins_delta_g": pn["mass"]["delta_vs_bl053_g"]}
    if export:
        a = export["assembled"]["g"]
        b53 = json.loads((ANALYSIS / "h1_rev5.json").read_text())["mass"]["assembled_g"]
        out.update({"assembled_g": a, "assembled_bl053_g": b53, "print_delta_g": round(a - b53, 1),
                    "lower_g": export["lower"]["g"], "upper_g": export["upper"]["g"],
                    "hip_boss": export.get("fairleads_bl042", {}).get("hip_boss_bl055")})
    out["hardware_delta_g"] = round(out["hip_inserts_delta_g"] + out["hip_screws_delta_g"], 2)
    return out


# ---------------------------------------------------------------------------------------------- Ti mount flange
FLANGE_T = 3.0                     # ASSUMPTION FLANGE-RIGID: the SLM mount's base redrawn as a 3 mm disc (was 1.2 mm)
FLANGE_HOLE_D = 5.5                # M5 clearance (ISO 273 medium) as BL-055 booked the flange; the mount is drawn with
#                                    D5.8 since BL-058 (hip_mount.HOLE_D; its mass change is in the BL058 ledger row)


def mount_flange(hip: dict) -> dict:
    """The SLM Ti mount's base as the chosen pattern needs it: a FLANGE_T disc of the boss D with n clearance holes
    (the drawn mount has a 1.2 mm D44 disc and no screw holes). Mass delta against the drawn disc (record density),
    and the flange bending between a leg root and the screw row: sigma = 6 T a / (b t^2), T the worst insert tension
    of each row, a = screw x less the leg half width, b = the hole pitch (one screw's strip), against the Ti S-basis
    yield (strength rows x their goal) and the fatigue limit (walk row)."""
    from huntkit.materials import load
    ti = load("ti_6al_4v")
    rho = float(ti.require("density_kg_m3")) * 1e-6
    sy = float(ti.require("yield_strength_sbasis_mpa"))
    se = float(ti.require("fatigue_limit_mpa"))
    pat = hip["chosen"]["pattern"]
    D, n = pat["boss_d"], pat["n"]
    legs = mount_legs()
    leg_a = sum(L.area for L in legs)
    a_new = math.pi / 4 * (D ** 2 - HIP_PIN_HOLE_D ** 2 - n * FLANGE_HOLE_D ** 2)
    a_old = math.pi / 4 * (44.0 ** 2 - HIP_PIN_HOLE_D ** 2)
    v_add = a_new * FLANGE_T - a_old * MOUNT_FLANGE_T - leg_a * (FLANGE_T - MOUNT_FLANGE_T)
    leg_half = max(max(abs(L.bounds[0]), abs(L.bounds[2])) for L in legs)
    xs = min(abs(x - HIP_C[0]) for x, _ in pat["positions_xz"])
    arm = xs - leg_half
    b = pat["pitch_mm"]
    rows = {}
    for k, r in hip["chosen"]["rows"].items():
        sig = 6.0 * r["T_max_n"] * arm / (b * FLANGE_T ** 2)
        lim = se if r["kind"] == "fatigue" else sy
        rows[k] = {"sigma_mpa": round(sig, 1), "limit_mpa": lim, "sf": round(lim / sig, 2), "goal": r["goal"]}
    return {"t_mm": FLANGE_T, "d_mm": D, "holes": n, "hole_d_mm": FLANGE_HOLE_D, "leg_half_w_mm": round(leg_half, 2),
            "arm_mm": round(arm, 2), "strip_b_mm": b, "rows": rows,
            "min_sf_over_goal": round(min(v["sf"] / v["goal"] for v in rows.values()), 2),
            "delta_g": round(v_add * rho, 2),
            "drawn": f"D44 x {MOUNT_FLANGE_T:g} mm disc, no screw holes (designs/pack_5200/print/{MOUNT_STL.name})"}


# ============================================================================================ export + report
def export(log=print) -> dict:
    """Re-export the H1 print (h1_buckling.export_print at its CHOSEN settings: frame_h1.print_mesh now grows the hip
    boss and cuts the pilots), cached as OUT/export_info.json."""
    from . import h1_buckling as B
    p = OUT / "export_info.json"
    if p.exists():
        return json.loads(p.read_text())
    info = B.export_print(*B.CHOSEN, log=log)
    p.write_text(json.dumps(info, indent=1, default=float))
    return info


def stl_check() -> dict:
    """Closed single shells of every exported file, bed fit of the flat halves (h1_bedfit.bed_check)."""
    import trimesh
    from . import h1_bedfit as BF
    out = {}
    for f in ("h1_assembled", "h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R"):
        m = trimesh.load(PRINT / f"{f}.stl", force="mesh")
        out[f] = {"watertight": bool(m.is_watertight), "shells": len(m.split(only_watertight=False)),
                  "g": round(m.volume * 1.06e-3, 1)}
    out["bed"] = {nm: BF.bed_check(PRINT / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    return out


ASSUMPTIONS = [
    ("MOUNT-ORIENT", "The SLM mount's local y is frame z: its two legs stand above and below the pin (along V), so the "
     "inserts split into two groups at the sides.", "First-article fit of the mount on the boss; the mount drawing."),
    ("FLANGE-RIGID", f"The mount base is redrawn as a {FLANGE_T:g} mm Ti disc (drawn: 1.2 mm) and acts as a rigid "
     "flange in the prying model (tipping about the boss edge, tension in proportion to the distance).",
     "HB-6b hip-mount proof on the frame with the redrawn mount, a gauge on the most-loaded screw."),
    ("INS-Z", "Insert pull-out along the layer normal = record pull-out x hot 0.8 x PAHT-CF z / xy tensile ratio "
     "(47 / 88).", "HB-6 insert pull-out on printed coupons, hole axis along the build z, at 60 C."),
    ("INS-DEPTH", f"Pilot hole = insert length + {INS_EXTRA_DEPTH:g} mm for displaced melt.",
     "Section one HB-6 coupon: no melt plug under the insert."),
    ("HIP-LAND", f">= {HIP_LAND:g} mm flange between an insert hole and the mount's D10 pin bore.", "Mount drawing."),
    ("HEAD-LEG", f">= {HEAD_LEG_CLEAR:g} mm between a DIN 7984 head (D8.5) and a leg root, for the driver.",
     "First-article assembly with a 3 mm hex screwdriver (DIN 7984 M5: socket s 3; BL-058)."),
    ("HIP-BOOKED", "The frame's fixed lump books 2 hip inserts and 2 screws; BL-055 books the rest.", "Ledger audit."),
    ("BOSS-LOCAL", "The grown boss (solid, at the hard point x 0, z 120) is not in the 2 mm voxel body of the "
     "BL-055 whole-body run: it adds material at a hard point the body already treats as fixed and the pilots stay "
     "inside it.", "BL-058: the whole body re-run on the exported print re-rastered (the boss, the BL-056 blocks and "
     "the fairleads in it): analysis/bl058.json body (bl058_frame.heavy, h1_buckling caches "
     "check_m1_u2.5_im3_bl058_stl / _sanded)."),
    ("SAND-K", "The 0.2 mm sanding of the stays' wearer faces is a uniform stress factor k on every stay element "
     "(worst section ratio over 15 stations, both stays).", "CA-1 bars printed over supports and sanded (BL-053 SCAR-KD)."),
]


def compute(log=print) -> dict:
    res = {"ticket": "BL-055 Part A", "date": "2026-11-21"}
    res["body"] = body_summary()
    res["voxels"] = json.loads((OUT / "body_solid.json").read_text()) if (OUT / "body_solid.json").exists() else None
    res["hip"] = hip_study()
    res["mount_flange"] = mount_flange(res["hip"])
    res["pins"] = pins()
    ex = export(log=log)
    res["export"] = {k: ex[k] for k in ("assembled", "lower", "upper", "us2_clevis_R", "us2_clevis_L") if k in ex}
    res["hip_slices"] = hip_slices()
    res["stl_check"] = stl_check()
    res["mass"] = mass_rows(ex, res["pins"], res["hip"])
    res["mass"]["mount_flange_delta_g"] = res["mount_flange"]["delta_g"]
    res["bl058"] = {"screw_spec": f"Ti gr5 M5 x {HIP_SCREW_L:g} DIN 7984 (8), 3 mm hex key",
                    "mount_holes": "D5.8 (hip_mount.HOLE_D)", "record": "analysis/bl058.json"}
    res["assumptions"] = [{"id": a, "text": t, "settled_by": s_} for a, t, s_ in ASSUMPTIONS]
    return res


def _save(fig, path: Path) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    if path.stat().st_size > 1.5e6:
        from PIL import Image
        Image.open(path).convert("P", palette=Image.ADAPTIVE).save(path, optimize=True)
    return str(path.relative_to(REPO))


def plot_hip(res: dict, path: Path) -> str:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon as MPoly
    pat = res["hip"]["chosen"]["pattern"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1, 1.25]})
    c = HIP_C
    ax.add_patch(Circle(c, pat["boss_d"] / 2, fc="#d9d9d9", ec="k", lw=1.2, label=f"boss / flange D{pat['boss_d']:g}"))
    ax.add_patch(Circle(c, 16.0, fc="none", ec="#888", ls=":", lw=1, label="old boss D32"))
    ax.add_patch(Circle(c, 22.0, fc="none", ec="#c55", ls="--", lw=1, label="drawn mount disc D44"))
    for L in mount_legs():
        xy = np.asarray(L.exterior.coords) + np.asarray(c)
        ax.add_patch(MPoly(xy, fc="#7aa0c4", ec="#2b5d8a", label="mount legs (root)"))
    ax.add_patch(Circle(c, HIP_PIN_HOLE_D / 2, fc="w", ec="k"))
    for i, (x, z) in enumerate(pat["positions_xz"]):
        ax.add_patch(Circle((x, z), HEAD_D / 2, fc="none", ec="#e08a00", lw=0.8))
        ax.add_patch(Circle((x, z), pat["hole_d"] / 2, fc="#333", ec="k"))
    h, l_ = ax.get_legend_handles_labels()
    keep = dict(zip(l_, h))
    ax.legend(keep.values(), keep.keys(), fontsize=7, loc="lower left")
    ax.set_xlim(-30, 30)
    ax.set_ylim(c[1] - 30, c[1] + 30)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)")
    ax.set_ylabel("frame z (mm)")
    ax.set_title(f"Hip boss: {pat['n']} x M5 inserts (pilot D{pat['hole_d']:g} x {pat['hole_depth']:g})\n"
                 f"ring r{pat['ring_r']:g}, two groups clear of the mount legs", fontsize=9)
    sw = res["hip"]["sweep"]
    lab = [f"{r['n']} {r['layout']} D{r['boss_d']:g}" for r in sw]
    yv = np.arange(len(sw))
    fs = [r["z_ratio"]["fatigue"] / FAT_GOAL for r in sw]
    ss = [r["z_ratio"]["strength"] / SF_GOAL for r in sw]
    bx.barh(yv + 0.2, ss, 0.4, color="#7aa0c4", label="strength SF / 1.5")
    bx.barh(yv - 0.2, fs, 0.4, color="#e08a00", label="fatigue SF / 1.15")
    for i, r in enumerate(sw):
        if not r["walls_ok"]:
            bx.text(0.02, i, "walls / legs clash", fontsize=7, va="center", color="#a00")
    bx.axvline(1.0, color="k", lw=1)
    bx.set_yticks(yv, lab, fontsize=7)
    i_ch = next(i for i, r in enumerate(sw) if (r["n"], r["ring_r"], r["boss_d"], r["layout"]) ==
                (HIP_CHOSEN[0], HIP_CHOSEN[1], HIP_CHOSEN[2], HIP_CHOSEN[4]))
    bx.get_yticklabels()[i_ch].set_fontweight("bold")
    bx.set_xlabel("margin against the BL-055 goal (1 = goal)")
    bx.legend(fontsize=7, loc="lower right")
    bx.set_title("Insert patterns (layer-normal pull-out, hot)", fontsize=9)
    fig.tight_layout()
    return _save(fig, path)


def plot_body(res: dict, path: Path) -> str:
    import matplotlib.pyplot as plt
    b = res["body"]["bases"]
    keys = ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")
    fig, axs = plt.subplots(1, len(b), figsize=(13, 4.2), sharey=True)
    for ax, (bn, v) in zip(axs, b.items()):
        y = np.arange(len(keys))
        for j, (tag, col) in enumerate((("bl051", "#bbbbbb"), ("bl053", "#2b5d8a"), ("bl053_sanded", "#e08a00"))):
            if v.get(tag):
                ax.barh(y + 0.27 * (1 - j), [v[tag][k] for k in keys], 0.27, color=col,
                        label={"bl051": "BL-051 record", "bl053": "BL-053 body", "bl053_sanded": "BL-053 sanded 0.2"}[tag])
        ax.axvline(1.0, color="r", lw=1)
        ax.set_title(bn, fontsize=9)
        ax.set_yticks(np.arange(len(keys)), keys, fontsize=8)
        ax.set_xlabel("SF / req")
    axs[0].legend(fontsize=7, loc="lower right")
    fig.suptitle("H1 whole body on the BL-053 print (red line = R1: SF / req 1)", fontsize=10)
    fig.tight_layout()
    return _save(fig, path)


def plot_slices(res: dict, path: Path) -> str:
    import matplotlib.pyplot as plt
    import trimesh
    m = trimesh.load(PRINT / "h1_assembled.stl", force="mesh")
    y0 = float(m.bounds[0][1])
    pat = res["hip"]["chosen"]["pattern"]
    dys = (1.0, 6.0, pat["hole_depth"] + 2.0)
    fig, axs = plt.subplots(1, len(dys), figsize=(12, 4.3))
    for ax, dy in zip(axs, dys):
        sec = m.section(plane_origin=[0.0, y0 + dy, 0.0], plane_normal=[0.0, 1.0, 0.0])
        for L in sec.discrete:
            ax.fill(L[:, 0], L[:, 2], fc="#9ab", ec="k", lw=0.6, alpha=0.6)
        ax.set_xlim(-40, 40)
        ax.set_ylim(HIP_C[1] - 40, HIP_C[1] + 40)
        ax.set_aspect("equal")
        ax.set_title(f"STL slice {dy:g} mm into the boss face", fontsize=9)
        ax.set_xlabel("x (mm)")
    axs[0].set_ylabel("z (mm)")
    fig.suptitle(f"Exported h1_assembled.stl at the hip boss: {pat['n']} pilot holes, closed past the floor", fontsize=10)
    fig.tight_layout()
    return _save(fig, path)


def figures(res: dict) -> list:
    out = []
    for i, f in enumerate((plot_body, plot_hip, plot_slices), 1):
        out.append(f(res, SCREENS / f"{SHOT}{i}.png"))
    return out


def _oz(g: float) -> str:
    return f"{g / 28.3495:.2f} oz"


def write_md(res: dict, shots: list) -> str:
    L = []
    a = L.append
    b = res["body"]
    hp = res["hip"]
    ch = hp["chosen"]
    pat = ch["pattern"]
    fl = res["mount_flange"]
    pn = res["pins"]
    m = res["mass"]
    sf = b["sand_factor"]
    a("# H1 close-out before review 6 (BL-055 Part A)\n")
    a("structural-fea-engineer, 2026-11-21 (resumed from the 2026-11-14 WIP). Ticket `docs/backlog/BL-055-close-out.md` "
      "Part A. Code `huntkit/gendesign/h1_closeout.py` (`python -m huntkit.gendesign.h1_closeout --body` for the whole "
      "body, the report with no flag); print hook `frame_h1.print_mesh` (`h1_closeout.add_hip_pilots`); tests "
      "`tests/test_h1_closeout.py`. Results `h1_closeout.json`. Units mm, N, MPa, g (imperial in brackets). "
      "Supersedes the body margins of `h1_crown.md` and the hip-insert row of `hipbelt_structural.md` section 4.\n")
    a("## Summary\n")
    w = {k: min(v["bl053_sanded"][k] for v in b["bases"].values() if v.get("bl053_sanded")) for k in
         ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")}
    noncyc = {k: min(v["bl053_sanded"][k] for bn, v in b["bases"].items() if not bn.endswith(".cyc"))
              for k in ("fatigue", "joint_fatigue")}
    a(f"- **Whole body, BL-053 print, sanded 0.2 mm (governing):** strength {w['strength']:.2f}, fatigue "
      f"{noncyc['fatigue']:.2f} on the three static-cinch bases and **{w['fatigue']:.2f} on fine_sm8.cyc** (below R1, "
      f"as on every body since BL-024: R1 hold for MT-1), creep {w['creep']:.2f}, buckling {w['buckling']:.2f}, "
      f"z 234 joint {w['joint_strength']:.2f} / {noncyc['joint_fatigue']:.2f} ({w['joint_fatigue']:.2f} on .cyc). "
      f"The sanding costs at most {100 * (sf['k'] - 1):.1f} % (k {sf['k']:.3f}, worst section z {sf['worst']['z']:g} "
      f"{sf['worst']['side']}); the BL-053 lug fixes gain 1-3 % on every basis against BL-051.")
    a(f"- **Hip boss:** {pat['n']} x M5 brass heat-set inserts on r {pat['ring_r']:g} in two groups of "
      f"{pat['n'] // 2} at the sides (angles {', '.join(f'{v:g}' for v in pat['angles_deg'])} deg from +x), boss and "
      f"mount flange D{pat['boss_d']:g}, pilot D{pat['hole_d']:g} x {pat['hole_depth']:g} deep. SF strength "
      f"**{ch['min_sf']['strength']:.2f}** (goal 1.5), fatigue **{ch['min_sf']['fatigue']:.2f}** (goal 1.15), creep "
      f"{ch['min_sf']['creep']:.2f}, with the layer-normal pull-out. The 2-insert record was 0.995 on an assumed "
      f"1500 N insert; on the insert record (1200 N) and the layer-normal ratio it is "
      f"{hp['record']['H_pin']['sf_insert_record_z']:.2f}.")
    a(f"- **Change from the 2026-11-14 WIP:** the WIP chose 9 inserts equally spaced on a D44 boss; the holes "
      f"next to the mount's two legs put screw heads on them ( head-to-leg {next(r for r in hp['sweep'] if r['n'] == 9)['walls']['head_to_leg_mm']:.1f} mm). With the legs "
      f"kept, no pattern under the drawn D44 disc reaches fatigue 1.15 (best 8 split, 1.07); the mount base must be "
      f"redrawn anyway (it is a 1.2 mm disc with no screw holes), so it grows to D{pat['boss_d']:g} x {fl['t_mm']:g} mm.")
    a(f"- **Pins:** US1 pins in Ti-6Al-4V (orchestrator call): dy 95 fatigue {pn['stations']['us1']['was']['bending']['dy95_sf_fatigue']} -> "
      f"**{pn['stations']['us1']['bending']['dy95_sf_fatigue']}**, +{m['us1_ti_pins_delta_g']:.2f} g.")
    tot = m["print_delta_g"] + m["hardware_delta_g"] + m["us1_ti_pins_delta_g"] + m["mount_flange_delta_g"]
    a(f"- **Mass:** print {m['print_delta_g']:+.1f} g (assembled {m['assembled_g']:.1f} g), {m['hip_inserts'] - m['hip_inserts_booked']} more inserts "
      f"and screws {m['hardware_delta_g']:+.2f} g, Ti mount flange {m['mount_flange_delta_g']:+.2f} g, US1 Ti pins "
      f"{m['us1_ti_pins_delta_g']:+.2f} g: **{tot:+.1f} g ({_oz(tot)})**, booked in the ledger (BL055).")
    a(f"- **Print:** re-exported; slice check of the pilots {'passes' if res['hip_slices']['pass'] else 'FAILS'}; "
      f"every STL a closed single shell: {all(v['watertight'] and v['shells'] == 1 for k, v in res['stl_check'].items() if k != 'bed')}.\n")

    a("## 1. Whole body on the BL-053 print\n")
    a("`h1_buckling.full_check` (H1's FI99 rule per kit and setting, member Euler margins, the z 234 joint) on the "
      "lane kit sets with the real crown models, as `h1_crown.body` ran it, on `h1_lanes.body_solid` plus the BL-053 "
      f"lug fixes voxelised on the 2 mm grid ({res['voxels']['bl053_fix_g'] if res['voxels'] else '-'} g of fix voxels). "
      "Sanded: every stay element's stress x k (below). All values SF / req; R1 needs >= 1.\n")
    a("| basis | strength | fatigue | creep | buckling | joint str / fat | governing |")
    a("|---|---|---|---|---|---|---|")
    for bn, v in b["bases"].items():
        o, n, s_ = v["bl051"], v["bl053"], v["bl053_sanded"]
        f = lambda k: f"{o[k]:.3f} / {n[k]:.3f} / **{s_[k]:.3f}**"   # noqa: E731
        a(f"| {bn} | {f('strength')} | {f('fatigue')} | {f('creep')} | {f('buckling')} | "
          f"{s_['joint_strength']:.2f} / {s_['joint_fatigue']:.2f} | {n['governing_tag']} |")
    a("\nEach cell: BL-051 record / BL-053 as printed / BL-053 sanded 0.2 mm.\n")
    a(f"Margins against R1 (sanded): strength +{100 * (w['strength'] - 1):.0f} %, fatigue "
      f"+{100 * (noncyc['fatigue'] - 1):.0f} % (static-cinch bases), {100 * (w['fatigue'] - 1):+.0f} % on fine_sm8.cyc, "
      f"buckling +{100 * (w['buckling'] - 1):.0f} %, joint +{100 * (w['joint_strength'] - 1):.0f} % / "
      f"{100 * (noncyc['joint_fatigue'] - 1):+.0f} % ({100 * (w['joint_fatigue'] - 1):+.0f} % on .cyc). Raster "
      f"{b['raster_g']['bl051']} -> {b['raster_g']['bl053']} g.\n")
    a(f"**Sanding factor.** The print's stay sections at {len(SAND_Z)} heights, both stays, each with 0.2 mm taken off "
      f"every wearer-facing edge (bores and traps not sanded): worst ratio k = **{sf['k']:.4f}** (z {sf['worst']['z']:g} "
      f"{sf['worst']['side']}, {sf['worst']['A_mm2']} mm2, {sf['worst']['depth_y_mm']} mm deep), against "
      f"{100 * sf['rect_equivalent_loss']:.1f} % for an 18 mm rectangle (the BL-053 estimate). Applied as a uniform "
      "factor on every stay element (ASSUMPTION SAND-K), so buckling and the joint see it too (conservative).\n")
    a("The cache was resumed: the 2026-11-14 run had finished 7 of the 8 basis runs before the stop; the last "
      "(sanded fine_sm8.cyc) was re-run on 2026-11-21. A fresh beam-basis run reproduced the cached nominal result "
      "(test `test_whole_body_cache_reproduces`).\n")

    a("## 2. Hip boss insert pattern\n")
    a("Prying model of `hipbelt_structure.pivot_check` (the mount tips about the boss edge; V at the 21 mm pin "
      "stand-off plus e H, less H R), generalised to any pattern and to every tipping direction (72 directions; the "
      "worst is reported). Insert tension in proportion to the distance from the tipping line (rigid flange). "
      f"Capacity per insert: {ch['capacity']['basis']} = **{ch['capacity']['static_n']} N** static, "
      f"{ch['capacity']['fatigue_n']} N at 1e5 (x 0.3), {ch['capacity']['sustained_n']} N sustained (x 0.4). Hole "
      "axis = the print's build z (the boss face is on the plate), so the pull is along the layer normal.\n")
    a("| pattern | walls ok | head to leg (mm) | strength | fatigue | creep | pass |")
    a("|---|---|---|---|---|---|---|")
    for r in hp["sweep"]:
        z = r["z_ratio"]
        a(f"| {r['n']} {r['layout']} r{r['ring_r']:g} D{r['boss_d']:g} | {r['walls_ok']} | {r['walls']['head_to_leg_mm']:.1f} | "
          f"{z['strength']:.2f} | {z['fatigue']:.2f} | {z['creep']:.2f} | {bool(z['pass']) and r['walls_ok']} |")
    a(f"\n**Chosen: {pat['n']} split, r {pat['ring_r']:g}, boss D{pat['boss_d']:g}** (the fewest inserts that pass on "
      "the smallest boss that keeps the fatigue row >= 5 % over its goal; 8 at D48 passes at 1.16).\n")
    a("| item | value |")
    a("|---|---|")
    a(f"| insert | `insert_heatset_brass_m5`, {hp['insert']['od']:g} OD x {hp['insert']['length']:g} long, "
      f"{hp['insert']['mass_g']:g} g |")
    a(f"| pilot hole | D{pat['hole_d']:g} x {pat['hole_depth']:g} deep from the boss face (insert + {INS_EXTRA_DEPTH:g}) |")
    a("| positions (frame x, z) | " + "; ".join(f"({x:g}, {z:g})" for x, z in pat["positions_xz"]) + " |")
    a(f"| walls (rule {pat['wall_rule_mm']:g}) | " + ", ".join(f"{k} {v:g}" for k, v in pat["walls"].items()) + " |")
    a(f"| boss | D{pat['boss_d']:g}, solid {HIP_BOSS_DEPTH:g} mm from the face (was D32) |")
    a(f"| screws | {pat['n']} x Ti gr5 M5 x {HIP_SCREW_L:g} DIN 7984 (BL-058; BL-055 booked {m['hip_screw']}, "
      f"{m['hip_screw_g']} g each), 3 mm hex key, torque <= {hp['insert']['torque_max_n_m']:g} N m |")
    a(f"| mount base (redraw) | D{fl['d_mm']:g} x {fl['t_mm']:g} mm Ti disc, {fl['holes']} x D{fl['hole_d_mm']:g} on the "
      f"same positions (BL-058: drawn D5.8, hip_mount.HOLE_D) (drawn: {fl['drawn']}); flange bending leg root to screw row min SF / goal "
      f"{fl['min_sf_over_goal']} |")
    a("\n| row | V (N) | H (N) | T max (N) | capacity (N) | SF | goal |")
    a("|---|---|---|---|---|---|---|")
    for k, r in ch["rows"].items():
        a(f"| {k} | {r['V_n']} | {r['H_n']} | {r['T_max_n']} | {r['cap_n']} | {r['sf']:.2f} | {r['goal']} |")
    rc = hp["record"]
    a(f"\nRecord reproduced: 2 x M5 at x +/-11 on D32, C2 with H on the pin T = {rc['H_pin']['T_n']} N, SF "
      f"{rc['H_pin']['sf_record_cap']} on the record's assumed 1500 N x 0.8 (hipbelt_structural 0.995); on the insert "
      f"record {rc['H_pin']['sf_insert_record']}, with the layer normal {rc['H_pin']['sf_insert_record_z']}.\n")
    a("**Slice check of the exported print** (`hip_slices`, sections normal to y from the boss face):\n")
    a("| slice | pilot holes (D eq) | boss outer bounds x/z | pass |")
    a("|---|---|---|---|")
    for k, r in res["hip_slices"]["rows"].items():
        a(f"| {k} | {', '.join('-' if h is None else f'{h:g}' for h in r['holes_d_eq'])} | {r['outer_bounds_xz']} | {r['pass']} |")
    a(f"\nFlat lower half (as it goes to the slicer), round D{pat['hole_d']:g} holes counted at 0.6 / 6 / 10.5 mm above "
      f"the plate: {res['hip_slices']['lower_flat_round_holes']}. The holes print as vertical blind holes open to the "
      "plate: no support.\n")

    a("## 3. Pins\n")
    a("| station | qty | material | pin g | set g | design SF yield / fatigue | dy 95 SF yield / fatigue |")
    a("|---|---|---|---|---|---|---|")
    for n, r in pn["stations"].items():
        bb = r.get("bending", {})
        a(f"| {n} | {r['qty']} | {r['material']} | {r['pin_g']} | {r['set_g']} | {bb.get('sf_yield', '-')} / "
          f"{bb.get('sf_fatigue', '-')} | {bb.get('dy95_sf_yield', '-')} / {bb.get('dy95_sf_fatigue', '-')} |")
    a(f"\nPins total {pn['mass']['pins_g']} g, clips + tethers {pn['mass']['clips_tethers_g']} g; US1 in Ti "
      f"{pn['mass']['delta_vs_bl053_g']:+.2f} g against BL-053. BOM rows in `h1_closeout.json` `pins.bom`.\n")

    a("## 4. Cleanup\n")
    a("- `us_route.section_bearing`: the hull kept the -y (lower) chain; it now keeps the bag-side hull (test "
      "`test_section_bearing_keeps_the_bag_side_hull`).")
    a("- Superseded notes at the head of `h1_crown.md`, `h1_bedfit.md`, `h1_lanes.md` (and their generators).")
    a("- `bag_attach.THROAT` 18 -> 20 (as printed on all 12 stations); the 2026-11-01 value kept as `THROAT_LEGACY` "
      "for the legacy fairlead model, the eye FEA and the voxel stubs. The US1 wrap text no longer says 'pin sleeve'.\n")

    a("## 5. Mass\n")
    a("| item | g | source |")
    a("|---|---|---|")
    a(f"| print (assembled {m['assembled_bl053_g']} -> {m['assembled_g']} g) | {m['print_delta_g']:+.1f} | export |")
    a(f"| {m['hip_inserts'] - m['hip_inserts_booked']} more inserts + screws | {m['hardware_delta_g']:+.2f} | insert record, frame_comp_B.bolt_mass_g |")
    a(f"| Ti mount base D{fl['d_mm']:g} x {fl['t_mm']:g} (was D44 x 1.2) | {m['mount_flange_delta_g']:+.2f} | ti_6al_4v density |")
    a(f"| US1 pins in Ti | {m['us1_ti_pins_delta_g']:+.2f} | pins() |")
    a(f"| **total BL-055** | **{tot:+.1f} ({_oz(tot)})** | ledger BL055 |\n")
    a("Mass reductions that keep the SF: (1) D48 boss / flange with the same 8 inserts passes at fatigue 1.16 "
      "(about -4 g, 1 % margin); (2) a measured layer-normal pull-out (HB-6) above 0.534 x the record would allow 6 "
      "inserts (-3 g + screws).\n")

    a("## 6. Assumptions\n")
    for x in res["assumptions"]:
        a(f"- ASSUMPTION {x['id']}: {x['text']} Settled by: {x['settled_by']}")
    a("\n## 7. Screenshots\n")
    for s_ in shots:
        a(f"- `{s_}`")
    return "\n".join(L) + "\n"


def report(log=print) -> dict:
    res = compute(log=log)
    shots = figures(res)
    res["screenshots"] = shots
    RESULTS.write_text(json.dumps(res, indent=1, default=float))
    DOC.write_text(write_md(res, shots))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--body", action="store_true", help="whole body on the BL-053 body, nominal + sanded (heavy)")
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.body:
        body()
        return 0
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
