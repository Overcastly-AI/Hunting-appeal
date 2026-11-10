"""Printed-frame competition, Team A: MONO (designs/pack_5200/frame_comp/RULES.md).

Today's monolithic generative branch body, re-sized for the material, the print orientation and annealing on the
home Bambu H2S. Nothing else changes: same branch topology (sleeve limbs, inboard branches, lumbar struts, mid and
upper bars, pawl housing, fairleads), the same carbon crown, the same interfaces.

What is varied:
- the material (PAHT-CF as today, PPA-CF, PA6-CF), with cited allowables (docs/research/frame_comp_A.md);
- the radius of each member family of the body (foot, stay below the sleeve, sleeve limb, top / upper bar / pawl,
  inboard branch, lumbar strut, mid bar) by a fully-stressed resizing loop on the rev C utilisation, and the printed
  wall around the 18 mm crown bore (``sleeve_w``);
- the layer normal (x / y / z: which face sits on the plate);
- the z 234 print split, re-specified as a DRY joint (through-bolts in nut traps, no adhesive).

Method: the rev C load sets of ``rev_c_verification.beam_runs`` (beam model, every case at 15 / 19 / 23 in, bag couple
on the crown bar and on the IM3 hooks); the 2 mm voxel FE of ``frame_topopt`` (one factorisation per geometry); the
FI99 rule of ``frame_cg_recheck.verify_sets`` (layer failure index, clamp and load-patch elements excluded); fatigue
and creep from the static-carry sets as ``frame_cg_recheck.summarize_body``. Because the voxel model is linear and
isotropic and every load is applied (the hip pivot is the clamp), the stress field does not depend on E: one solve
per geometry serves every material.

Run:  python -m huntkit.gendesign.frame_comp_A            (sweep + figures + result.json, ~25 min on 2-4 cores)
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
TEAM_DIR = REPO / "designs" / "pack_5200" / "frame_comp" / "A"
DOC = REPO / "designs" / "pack_5200" / "analysis" / "frame_comp_A.md"
RESULTS = TEAM_DIR / "frame_comp_A_results.json"
RESULT_JSON = TEAM_DIR / "result.json"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261110_compA"
H = 2.0                                   # voxel size (mm): the production check resolution

# ------------------------------------------------------------------------------------------------ baseline (today)
TODAY = {"body_g": 823.2, "frame_g": 1063.0, "spreader_g": 162.3, "frame_plus_spreader_g": 1225.0,
         "strength": 1.51, "fatigue": 1.044, "creep": 2.228, "torsion_Nm_deg": 0.4375}
PACK_B2_M_TODAY = 3964.5                  # RULES.md: CORRIE B.2 at belt M with today's frame
NON_BODY_G = TODAY["frame_g"] - TODAY["body_g"]     # crown, rack, pawl, bushings, Ti mount, dowels, inserts: 239.8 g
SCALE_TODAY = 1.05
SLEEVE_W_TODAY = 4.2 * SCALE_TODAY        # printed wall over the 9 mm bore radius (reamed to 18.0 for the bushings)
TORSION_UNIT_E_TODAY = 0.0011261212551592862   # N m/deg per MPa: stiffness_tests on today's 2 mm body (this module)
CROWN_WORST = 1.12                        # rev_c_verification.md: crown legs FPF, IM3 couple (unchanged by the body)


# ------------------------------------------------------------------------------------------------ materials
@dataclass
class Mat:
    """Design allowables for a printed polymer. Every number is cited in docs/research/frame_comp_A.md."""
    key: str
    label: str
    rho: float          # kg/m3
    E_xy: float         # MPa
    E_z: float
    s_xy: float         # MPa, dry tensile strength in the layer plane (TDS)
    s_z: float          # MPa, normal to the layers (design value)
    knock: float        # hot/wet strength knockdown
    fat: float          # 1e5-cycle fatigue strength / knocked-down static strength (R ~ 0.1)
    rup: float          # 8 h 40 C creep-rupture / knocked-down static strength
    E_hot: float        # E(40 C, conditioned) / E(23 C dry)
    usd_per_kg: float
    flow_mm3_s: float   # effective print flow on the H2S, 0.6 mm hardened nozzle
    anneal: str
    notes: str = ""


MATS = {
    # today's record values (data/materials/polymers/pa12_cf_fdm_paht.yaml); fatigue 0.3 is the record ASSUMPTION
    "paht_rec": Mat("paht_rec", "PAHT-CF, record allowables (fatigue 0.30, ASSUMPTION)", 1060, 3860, 2180, 88, 47,
                    0.8, 0.30, 0.40, 0.6, 80.0, 8.0, "90 C 6 h (today)"),
    # same filament; fatigue ratio from published PA12 + 35 % CF FDM tension-tension data (Stratasys Nylon 12CF:
    # 3/3 run-outs to 1e6 at 40 % of strength, R 0.1, both XZ and ZX), applied at 1e5 (one decade of life margin)
    "paht_pub": Mat("paht_pub", "PAHT-CF, published PA12-CF fatigue (0.40 at 1e6 used at 1e5)", 1060, 3860, 2180, 88,
                    47, 0.8, 0.40, 0.40, 0.6, 80.0, 8.0, "90 C 6 h (today)"),
    # Bambu PPA-CF TDS V1.0 (unannealed, X1C, chamber 52 C): XY 168, Z 57 +/- 5. Design Z 45 (57 - 2.4 SD);
    # hot/wet knock 0.73 = Raise3D PPA-CF conditioned 122 / Bambu dry 168 (cross-brand, conservative)
    "ppa": Mat("ppa", "PPA-CF (Bambu), unannealed TDS, wet knock 0.73, Z 45 design, fatigue 0.30", 1250, 11800, 4300,
               168, 45, 0.73, 0.30, 0.55, 0.85, 120.0, 6.0, "none (120-140 C needs a forced-air oven; may warp)"),
    # Bambu PA6-CF TDS (XY 102); conditioned XY = 0.78 x dry (PolyMide PA6-CF); Z = 0.645 x XY (record)
    "pa6": Mat("pa6", "PA6-CF (Bambu), conditioned knock 0.75, fatigue 0.30", 1170, 4430, 2170, 102, 66, 0.75, 0.30,
               0.40, 0.55, 43.0, 8.0, "80-100 C"),
}


# ------------------------------------------------------------------------------------------------ geometry
GROUPS = ("foot", "low", "sleeve", "top", "branch", "strut", "mid")


@dataclass
class Body:
    """Per-member radius scales (1.05 = today's branch frame) and the printed wall over the 9 mm bore radius."""
    foot: float = SCALE_TODAY        # stay foot ball
    low: float = SCALE_TODAY         # stay below the sleeve (z < 160)
    sleeve: float = SCALE_TODAY      # sleeve limb outer radius above its wall floor (z 160-470)
    top: float = SCALE_TODAY         # stay top thickening, upper bar, pawl bulge (hipbelt-off region)
    branch: float = SCALE_TODAY      # inboard branches
    strut: float = SCALE_TODAY       # lumbar struts into the hip pivot
    mid: float = SCALE_TODAY         # mid bar z 330
    sleeve_w: float = SLEEVE_W_TODAY
    name: str = "today"

    def key(self) -> str:
        return "_".join(f"{g[0:2]}{getattr(self, g):.3f}" for g in GROUPS) + f"_w{self.sleeve_w:.2f}"

    def scales(self) -> dict:
        return {g: getattr(self, g) for g in GROUPS} | {"sleeve_w": self.sleeve_w}


def _stay_r(z, b: Body, part: str):
    z = np.asarray(z, float)
    low = np.interp(z, [0.0, 40.0, 150.0, 190.0], np.array([10.0, 9.0, 8.5, 13.4]) * b.low)
    slv = np.interp(z, [150.0, 190.0, 420.0, 532.0], np.array([8.5, 13.4, 13.0, 14.0]) * b.sleeve)
    r = np.where(z < 170.0, low, slv)
    r = np.maximum(r, np.where(z > 160.0, 9.0 + b.sleeve_w, 8.0 * b.low))
    return np.maximum(r, np.where(z > 470.0, 16.0 * b.top, 0.0))


def stay_radius(z, b: Body) -> np.ndarray:
    return _stay_r(z, b, "")


def parts_sdf(pts: np.ndarray, b: Body) -> dict:
    """Signed distance of each member family on its own (for the union and for assigning voxels to a group)."""
    from .frame_branch import _dist_to_segment, _sleeve_y, _smin
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    yc = np.asarray(_sleeve_y(z), float)
    big = np.full(len(pts), 80.0)
    P = {k: big.copy() for k in GROUPS}
    r_out = stay_radius(z, b)
    for sx in (1.0, -1.0):
        stay = np.hypot(x - sx * 115.0, y - yc) - r_out
        stay = np.where((z < -2.0) | (z > 540.0), 40.0, stay)
        P["low"] = np.minimum(P["low"], np.where(z < 165.0, stay, 40.0))
        P["sleeve"] = np.minimum(P["sleeve"], np.where((z >= 165.0) & (z <= 470.0), stay, 40.0))
        P["top"] = np.minimum(P["top"], np.where(z > 470.0, stay, 40.0))
        foot = np.sqrt((x - sx * 115.0) ** 2 + (y - yc) ** 2 + (z - 10.0) ** 2) - 12.0 * b.foot
        P["foot"] = np.minimum(P["foot"], foot)
        t = np.clip((z - 165.0) / 320.0, 0.0, 1.0)
        bow = np.sin(np.pi * t)
        xb = sx * (115.0 - 46.0 * bow)
        yb = yc + 6.0 * bow
        branch = np.hypot(x - xb, y - yb) - (6.2 * b.branch)
        P["branch"] = np.minimum(P["branch"], np.where((z < 155.0) | (z > 495.0), 30.0, branch))
        for z1, y1 in ((78.0, 0.0), (155.0, -4.0)):
            a = np.array([0.0, -42.0, 120.0])
            bb = np.array([sx * 115.0, float(_sleeve_y(z1)) + y1, z1])
            P["strut"] = np.minimum(P["strut"], _dist_to_segment(pts, a, bb) - 7.5 * b.strut)
    for zc, rad, grp in ((330.0, 6.5 * b.mid, "mid"), (508.0, 11.0 * b.top, "top")):
        bar = np.sqrt((y - float(_sleeve_y(zc))) ** 2 + (z - zc) ** 2) - rad
        P[grp] = np.minimum(P[grp], np.where(np.abs(x) > 118.0, 30.0, bar))
    yp = float(_sleeve_y(512.0))
    P["top"] = np.minimum(P["top"], np.sqrt(x ** 2 + (y - yp + 6.0) ** 2 + (z - 512.0) ** 2) - 16.0 * b.top)
    return P


def body_sdf(pts: np.ndarray, b: Body) -> np.ndarray:
    """frame_branch.frame_sdf with per-member scales (same primitives and blend radii); fairleads, bores and the
    spine channel at the released size. With every scale 1.05 and the wall 4.41 it reproduces today's body."""
    from .bag_attach import attachment_field
    from .frame_branch import _dist_to_segment, _sleeve_y, _smin
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    yc = np.asarray(_sleeve_y(z), float)
    sdf = np.full(len(pts), 80.0)
    r_out = stay_radius(z, b)
    for sx in (1.0, -1.0):
        stay = np.hypot(x - sx * 115.0, y - yc) - r_out
        stay = np.where((z < -2.0) | (z > 540.0), 40.0, stay)
        foot = np.sqrt((x - sx * 115.0) ** 2 + (y - yc) ** 2 + (z - 10.0) ** 2) - 12.0 * b.foot
        stay = _smin(stay, foot, 8.0)
        sdf = _smin(sdf, stay, 7.0)
        t = np.clip((z - 165.0) / 320.0, 0.0, 1.0)
        bow = np.sin(np.pi * t)
        xb = sx * (115.0 - 46.0 * bow)
        yb = yc + 6.0 * bow
        branch = np.hypot(x - xb, y - yb) - (6.2 * b.branch)
        branch = np.where((z < 155.0) | (z > 495.0), 30.0, branch)
        sdf = _smin(sdf, branch, 12.0)
    for sx in (1.0, -1.0):
        for z1, y1 in ((78.0, 0.0), (155.0, -4.0)):
            a = np.array([0.0, -42.0, 120.0])
            bb = np.array([sx * 115.0, float(_sleeve_y(z1)) + y1, z1])
            d = _dist_to_segment(pts, a, bb)
            sdf = _smin(sdf, d - 7.5 * b.strut, 10.0)
    for zc, rad in ((330.0, 6.5 * b.mid), (508.0, 11.0 * b.top)):
        bar = np.sqrt((y - float(_sleeve_y(zc))) ** 2 + (z - zc) ** 2) - rad
        bar = np.where(np.abs(x) > 118.0, 30.0, bar)
        sdf = _smin(sdf, bar, 9.0)
    yp = float(_sleeve_y(512.0))
    pawl = np.sqrt(x ** 2 + (y - yp + 6.0) ** 2 + (z - 512.0) ** 2) - 16.0 * b.top
    sdf = _smin(sdf, pawl, 8.0)
    sdf = _smin(sdf, attachment_field(pts, SCALE_TODAY), 4.5)
    for sx in (1.0, -1.0):
        r = np.hypot(x - sx * 115.0, y - yc)
        tool = np.where((z > 160.0) & (z < 546.0), r - 9.0, 80.0)
        sdf = np.maximum(sdf, -tool)
    ch = (np.abs(x) < 16.0) & (np.abs((y - yc) + 18.0) < 9.0) & (z > 300.0)
    return np.where(ch, np.maximum(sdf, 2.0), sdf)


def group_of(cen: np.ndarray, b: Body) -> np.ndarray:
    """Index into GROUPS of the nearest member family for each element centre."""
    P = parts_sdf(cen, b)
    return np.argmin(np.stack([P[g] for g in GROUPS], 1), axis=1)


def raster(b: Body, h: float = H):
    from . import frame_production as prod
    from . import frame_topopt as ft
    dom = ft.build_domain(h, sleeve_wall=max(min(b.sleeve_w, 4.2 * SCALE_TODAY), h))
    sdf = body_sdf(dom.grid.elem_centers(), b)
    solid = (sdf <= 0.0) | dom.passive_solid
    solid &= ~dom.passive_void
    solid = prod._largest_with_pivot(dom, solid)
    return dom, solid


def body_mesh(b: Body, h: float = 2.2):
    """Marching-cubes surface of the body (frame coordinates, mm)."""
    import trimesh
    from skimage.measure import marching_cubes
    x0 = np.array([-156.0, -64.0, -8.0])
    dims = np.array([312.0, 112.0, 562.0])
    n = np.maximum((dims / h).astype(int), 2)
    axes = [x0[i] + np.arange(n[i]) * h for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    sdf = body_sdf(np.c_[X.ravel(), Y.ravel(), Z.ravel()], b).reshape(X.shape)
    for ax in range(3):
        sl = [slice(None)] * 3
        for k in (0, -1):
            sl[ax] = k
            sdf[tuple(sl)] = np.maximum(sdf[tuple(sl)], 1.0)
    v, f, _, _ = marching_cubes(sdf, level=0.0, spacing=(h, h, h))
    m = trimesh.Trimesh(v + x0, f, process=True)
    parts = m.split(only_watertight=False)
    return max(parts, key=lambda p: len(p.faces)) if len(parts) > 1 else m


# ------------------------------------------------------------------------------------------------ evaluation
def fi_layer(S: np.ndarray, normal: int, m: Mat) -> np.ndarray:
    from . import frame_topopt as ft
    return ft.layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), normal, m.s_xy, m.s_z, m.knock)


def evaluate(b: Body, sets, mats=("paht_rec", "paht_pub", "ppa", "pa6"), normals=(1,), h: float = H,
             sections: bool = True, stiffness: bool = True, keep_fields: bool = False, log=print) -> dict:
    """One voxel factorisation; per material and layer normal: FI99 per set, strength / fatigue / creep margins."""
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    t0 = time.time()
    dom, solid = raster(b, h)
    g = dom.grid
    idx = np.where(solid)[0]
    cen = g.elem_centers()[idx]
    _, fixed = ft.assemble_loads(dom, sets[:1], solid_mask=solid)
    clamp = np.zeros(g.nn, bool)
    clamp[np.where(fixed[0::3])[0]] = True
    rs = ft.ReducedSystem(g, solid, fixed, ft.ke_h8(g.h, 1.0, ft.NU))
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    K.sort_indices()
    import pypardiso
    solver = pypardiso.PyPardisoSolver(mtype=2)
    solver.factorize(K)
    rows = {(mk, nrm): [] for mk in mats for nrm in normals}
    env = {mk: np.zeros(idx.size) for mk in mats}
    fat_field = {mk: np.zeros(idx.size) for mk in mats}
    secs, U_show = [], None
    tags = list(dict.fromkeys(s.key.split(":")[0] for s in sets))
    for tg in tags:
        tsets = [s for s in sets if s.key.split(":")[0] == tg]
        F, _ = ft.assemble_loads(dom, tsets, solid_mask=solid)
        Ur = solver.solve(K, np.ascontiguousarray(F[rs.free])).reshape(rs.free.size, -1)
        U = np.zeros((g.ndof, len(tsets)))
        U[rs.free] = Ur                       # E = 1: stresses are E-independent, displacements scale 1/E
        Fn = np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2))
        ex = (clamp | (Fn > 0))[g.enodes].any(axis=1)[idx]
        del F, Ur
        for k, s in enumerate(tsets):
            _, S = ft.element_stress(g, U[:, k], solid, 1.0)
            for mk in mats:
                m = MATS[mk]
                for nrm in normals:
                    fi = fi_layer(S, nrm, m)
                    ok = fi[~ex]
                    fi99 = float(np.percentile(ok, 99))
                    pk = np.where(~ex)[0][np.argmax(ok)]
                    rows[(mk, nrm)].append({"set": s.key, "scenario": tg, "case": s.case, "torso": s.torso,
                                            "factor": s.factor, "fi99": fi99, "sf": 1.0 / max(fi99, 1e-9),
                                            "where": R.region_label(cen[pk]),
                                            "peak_xyz": [float(v) for v in cen[pk]]})
                    if nrm == 1:
                        env[mk] = np.maximum(env[mk], np.where(ex, 0.0, fi))
                        if s.case == "static_carry":
                            fat_field[mk] = np.maximum(fat_field[mk], np.where(ex, 0.0, fi * 1.6 / s.factor / m.fat))
            if sections:
                sec = ft.section_resultants(dom, solid, U[:, k], 234.0, E=1.0)
                secs.append({"set": s.key, "factor": s.factor, "case": s.case, "sec": sec})
            if s.case == "static_carry" and s.torso == 19.0 and tg == "C" and keep_fields:
                U_show = U[:, k].astype(np.float32)
        del U
        if log:
            log(f"    [{b.name} {b.key()}] voxel [{tg}] {len(tsets)} sets, {time.time() - t0:.0f} s")
    try:
        solver.free_memory(everything=True)
    except Exception:
        pass
    vox_cm3 = solid.sum() * h ** 3 / 1000.0
    out = {"body": asdict(b), "key": b.key(), "volume_cm3": float(vox_cm3), "n_vox": int(solid.sum()),
           "materials": {}, "seconds": time.time() - t0}
    for mk in mats:
        m = MATS[mk]
        out["materials"][mk] = {"body_g": float(vox_cm3 * m.rho / 1000.0)}
        for nrm in normals:
            mg = margins(rows[(mk, nrm)], m)
            out["materials"][mk][f"n{nrm}"] = mg
    if sections:
        out["joint"] = joint_check(secs)
    if stiffness:
        st = ft.stiffness_tests(dom, solid, E=1.0, sets=[s for s in sets if s.key.startswith("C:")])
        out["stiff_unitE"] = st
        out["torsion_vs_today"] = {mk: st["torsion_Nm_per_deg"] * MATS[mk].E_xy / (TORSION_UNIT_E_TODAY * 3860.0)
                                   for mk in mats}
        out["torsion_hot_vs_today_hot"] = {mk: st["torsion_Nm_per_deg"] * MATS[mk].E_xy * MATS[mk].E_hot /
                                           (TORSION_UNIT_E_TODAY * 3860.0 * MATS["paht_rec"].E_hot) for mk in mats}
    if keep_fields:
        out["_fields"] = {"dom": dom, "solid": solid, "cen": cen, "env": env, "fat": fat_field, "U": U_show}
    return out


def margins(rows: list, m: Mat) -> dict:
    """Strength (min SF, both couple variants), fatigue and creep from the static-carry sets (summarize_body rule,
    with the material's fatigue and creep ratios), per scenario and overall."""
    from . import frame_cg_recheck as R
    out = {}
    for tg in dict.fromkeys(r["scenario"] for r in rows):
        bm = R.summarize_body(rows, tg, m.fat, m.rup)
        out[tg] = {"strength": bm["sf_min"], "governing": bm["governing"], "where": bm["where"],
                   "fatigue": bm["sf_fatigue"], "creep": bm["sf_creep"], "fatigue_set": bm.get("fatigue_set"),
                   "cases": {c: {"sf": v["sf"], "torso": v["torso"], "where": v["where"]}
                             for c, v in bm["cases"].items()}}
    tgs = [t for t in out]
    out["min"] = {k: min(out[t][k] for t in tgs) for k in ("strength", "fatigue", "creep")}
    gt = min(tgs, key=lambda t: out[t]["strength"])
    ft_ = min(tgs, key=lambda t: out[t]["fatigue"])
    out["min"]["strength_at"] = f"{gt}:{out[gt]['governing']} ({out[gt]['where']})"
    out["min"]["fatigue_at"] = f"{out[ft_]['fatigue_set']}"
    return out


# ------------------------------------------------------------------------------------------------ dry z 234 joint
# Released joint: 8 carbon dowels bonded with MMA (production_frame.md). Team A replaces it with a DRY joint:
# per stay, one M5 through-bolt in each flange (fore and aft of the 18 mm crown bore), parallel to the stay, head in a
# counterbored pocket of the upper segment and a nut in a side-access hex trap of the lower segment, 35 mm each side
# of the split; plus one 5 mm carbon dowel per flange as a dry press-fit shear / alignment pin.
JOINT = {
    "bolt": "M5 A4-80 stainless (or Ti gr5) socket head, 70 mm, one per flange, preloaded 1.5 N m",
    "bolt_As_mm2": 14.2,          # ISO 898 tensile stress area M5
    "bolt_proof_mpa": 450.0,      # A4-80 0.2 % proof (ISO 3506: Rp0.2 600; 450 used, ASSUMPTION margin for Ti gr5 at 828)
    "washer_od": 12.0,            # mm, bearing ring under the nut / head on the printed pocket floor (M5 x 12 washer)
    "hole_d": 5.5,
    "pocket_len_mm": 35.0,        # printed material between the pocket floor and the split face
    "lever_mm": 24.0,             # flange bolt spacing about the bore (today's dowel lever)
    "dowel_shear_mpa": 60.0,      # pultruded rod transverse shear (frame_production.DOWEL_TAU)
    "dowel_d": 5.0,
}


def joint_capacity(m: Mat, fatigue: bool = False) -> dict:
    """Per-flange tension capacity of the dry bolted joint (N), knocked-down, and the per-flange shear capacity.
    Pocket bearing (washer ring on the in-plane pocket floor) at the knocked-down XY strength; shear-out of the printed
    plug above the pocket (2 planes, 35 mm, width = washer OD) at 0.6 x Z (interlayer shear rule of the FI);
    bolt at proof. Fatigue: printed allowables x the material fatigue ratio (bolt preloaded: bolt fatigue not governing)."""
    j = JOINT
    ring = math.pi / 4 * (j["washer_od"] ** 2 - j["hole_d"] ** 2)
    f = m.fat if fatigue else 1.0
    bearing = ring * m.knock * m.s_xy * f
    shear_out = 2 * j["pocket_len_mm"] * j["washer_od"] * 0.6 * m.knock * m.s_z * f
    bolt = j["bolt_As_mm2"] * j["bolt_proof_mpa"] * (0.3 if fatigue else 1.0)
    dowel = math.pi / 4 * j["dowel_d"] ** 2 * j["dowel_shear_mpa"] * 2       # 2 flanges, shear per stay
    return {"tension_n": min(bearing, shear_out, bolt), "bearing_n": bearing, "shear_out_n": shear_out, "bolt_n": bolt,
            "shear_per_stay_n": dowel}


def joint_check(secs: list) -> dict:
    """Flange force |N|/2 + M / lever per stay (frame_cg_recheck.segment_joint rule) for every factored set, and the
    static-carry set at 1.6 g for fatigue. Returns per-set demands; capacities are applied per material later."""
    rows = []
    for r in secs:
        for side, s in r["sec"].items():
            M = float(np.hypot(s["Mx"], s["My"]))
            flange = abs(s["N"]) / 2 + M / JOINT["lever_mm"]
            V = float(np.hypot(s["Vx"], s["Vy"]))
            rows.append({"set": r["set"], "case": r["case"], "factor": r["factor"], "side": side,
                         "flange_n": flange, "shear_n": V})
    worst = max(rows, key=lambda r: r["flange_n"])
    sc = [r for r in rows if r["case"] == "static_carry"]
    fat = max(sc, key=lambda r: r["flange_n"] / r["factor"])
    return {"worst_flange_n": worst["flange_n"], "worst_set": f"{worst['set']}|{worst['side']}",
            "worst_shear_n": max(r["shear_n"] for r in rows),
            "fatigue_flange_n_1p6g": fat["flange_n"] / fat["factor"] * 1.6, "fatigue_set": fat["set"]}


def joint_margins(j: dict, m: Mat) -> dict:
    c = joint_capacity(m)
    cf = joint_capacity(m, fatigue=True)
    return {"strength": c["tension_n"] / j["worst_flange_n"], "fatigue": cf["tension_n"] / j["fatigue_flange_n_1p6g"],
            "shear": c["shear_per_stay_n"] / max(j["worst_shear_n"], 1e-9), "cap": c, "cap_fat": cf}


def joint_boss_g(m: Mat, n_bolts: int = 4) -> float:
    """Printed bosses that carry the bolts and pockets beside the 4.4 mm sleeve wall: a cylinder of radius
    washer/2 + 2 mm over 70 mm, 60 % outside the existing wall (ASSUMPTION, hand-detailed on the STL)."""
    r = JOINT["washer_od"] / 2 + 2.0
    return n_bolts * math.pi * r ** 2 * 70.0 * 0.6 * m.rho / 1e6


JOINT_HW_DELTA_G = {
    "Ti gr5 M5 x 70 socket heads (4 x 7.0 g) + nuts (4 x 0.6 g)": 30.4,
    "4 of the 8 carbon dowels kept as dry press-fit pins (5 x 70 mm, 2.1 g each): 4 removed": -8.5,
    "MMA in the dowel holes removed (ASSUMPTION about 3 g)": -3.0,
}


# ------------------------------------------------------------------------------------------------ loads cache
LOADS_PKL = REPO / "outputs" / "frame_comp_A" / "revc_sets.pkl"


def load_sets(log=print):
    """Rev C load sets (both couple variants, 15 / 19 / 23 in), cached: the beam model does not depend on the body."""
    import pickle
    from . import rev_c_verification as V
    if LOADS_PKL.exists():
        return pickle.loads(LOADS_PKL.read_bytes())
    sets, _ = V.beam_runs(buckling=False, log=log)
    LOADS_PKL.parent.mkdir(parents=True, exist_ok=True)
    LOADS_PKL.write_bytes(pickle.dumps(sets))
    return sets


# ------------------------------------------------------------------------------------------------ resizing loop
TARGET_U = 1.0 / 1.04          # ASSUMPTION: aim each member at margin 1.04 (2 mm voxel / FI99 noise reserve)
MIN_SCALE = {"foot": 0.70, "low": 0.80, "sleeve": 0.80, "top": 0.75, "branch": 0.81, "strut": 0.67, "mid": 0.77}
#   floors: printed radius >= 5 mm on branches, struts and the mid bar (2.5 voxels at 2 mm, 6 walls at 0.6 mm nozzle
#   is 3.4 mm per side) and the foot ball >= 8.4 mm (hinge-pin boss and boot fit)
MAX_STEP = 0.10                # at most 10 % radius change per iteration
SLEEVE_W_MIN = 3.6             # ASSUMPTION: bushing seat wall over the 18.0 mm reamed bore (>= 6 walls of 0.6 mm)


def group_util(fields: dict, b: Body, mk: str = "paht_rec", q: float = 99.0) -> dict:
    """Per member family: q-th percentile of max(strength FI, fatigue utilisation) over its loaded elements."""
    g = group_of(fields["cen"], b)
    u = np.maximum(fields["env"][mk], fields["fat"][mk])
    out = {}
    for i, name in enumerate(GROUPS):
        sel = (g == i) & (u > 0)
        out[name] = float(np.percentile(u[sel], q)) if sel.sum() > 20 else 0.0
    return out


def resize(b: Body, gu: dict, target: float = TARGET_U, name: str = "") -> Body:
    """Fully stressed update: bending-governed round members, r_new = r (u / target)^(1/3), step-limited."""
    nb = Body(**{**asdict(b), "name": name or b.name})
    for grp in GROUPS:
        u = gu.get(grp, 0.0)
        if u <= 0:
            continue
        f = float(np.clip((u / target) ** (1 / 3), 1 - MAX_STEP, 1 + MAX_STEP))
        setattr(nb, grp, float(max(getattr(b, grp) * f, MIN_SCALE[grp])))
    # sleeve wall follows the sleeve group utilisation (thin ring: stress ~ 1 / wall)
    u = gu.get("sleeve", 0.0)
    if u > 0:
        f = float(np.clip(u / target, 1 - MAX_STEP, 1 + MAX_STEP))
        nb.sleeve_w = float(max(b.sleeve_w * f, SLEEVE_W_MIN))
    return nb


def passes(r: dict, mk: str) -> bool:
    m = r["materials"][mk]["n1"]["min"]
    return m["strength"] >= 1.0 and m["fatigue"] >= 1.0 and m["creep"] >= 1.0


def fully_stressed(sets, mk: str = "paht_rec", iters: int = 5, keep: float = 1.03, log=print) -> list:
    """Resizing loop from today's body; every iterate verified with the full FI99 rule (all 42 rev C sets).
    The group target T is the group utilisation level at which the GLOBAL rule (FI99 over the body, fatigue and creep
    from static carry) sits at ``keep``: T_0 = max group util x (global margin / keep), then T_k = T_(k-1) x
    (global margin_k / keep). Every family is driven to the same T (fully stressed), within the size floors."""
    b = Body(name="it0")
    hist, T = [], None
    for it in range(iters + 1):
        r = evaluate(b, sets, mats=(mk,), normals=(1,), sections=True, stiffness=True, keep_fields=True, log=None)
        f = r.pop("_fields")
        gu = group_util(f, b, mk)
        mg = r["materials"][mk]["n1"]["min"]
        gm = min(mg["strength"], mg["fatigue"], mg["creep"])
        T = (max(gu.values()) if T is None else T) * gm / keep
        r.update({"group_util": gu, "iter": it, "target_u": T})
        hist.append(r)
        if log:
            log(f"  it{it} {b.key()} body {r['materials'][mk]['body_g']:.1f} g  S {mg['strength']:.3f} "
                f"F {mg['fatigue']:.3f} C {mg['creep']:.3f}  T {T:.3f} util {({k: round(v, 2) for k, v in gu.items()})}",
                )
        if it < iters:
            b = resize(b, gu, target=T, name=f"it{it + 1}")
    return hist


# ------------------------------------------------------------------------------------------------ mass, time, cost
def frame_mass(body_g: float, m: Mat) -> dict:
    """Frame = today's non-body parts (crown with the rev C fix, rack, pawl, bushings, Ti mount, inserts, dowels)
    + the new body + the dry-joint delta (bosses, Ti bolts, half the dowels, no MMA)."""
    boss = joint_boss_g(m)
    hw = sum(JOINT_HW_DELTA_G.values())
    frame = NON_BODY_G + body_g + boss + hw
    return {"body_g": body_g, "joint_bosses_g": boss, "joint_hw_delta_g": hw, "frame_g": frame,
            "frame_plus_spreader_g": frame + TODAY["spreader_g"],
            "pack_corrie_b2_M_g": PACK_B2_M_TODAY - (TODAY["frame_plus_spreader_g"] - (frame + TODAY["spreader_g"]))}


def print_hours(body_g: float, m: Mat) -> float:
    """Volume / effective flow + 8 % waste, + 0.15 h per segment (frame_production.print_hours rule)."""
    vol = (body_g + joint_boss_g(m)) / (m.rho / 1e6)
    return vol / m.flow_mm3_s * 1.08 / 3600.0 + 2 * 0.15


BOUGHT_USD = {     # per frame, from PRODUCTION.md "Unit cost" unless marked
    "two 304 pawl bushings": 8.0, "M5 heat-set inserts": 3.0, "carbon crown tubes (rev C)": 50.3,
    "SLM Ti hip mount (ASSUMPTION)": 35.0, "UHMWPE bushings (ASSUMPTION)": 5.0, "MMA for the crown corners": 2.0,
    "4 Ti gr5 M5 x 70 + nuts + M5 x 12 washers (ASSUMPTION $4.5 each)": 18.0, "4 carbon dowels (half of today's)": 2.3,
}
COUPON_ONE_OFF_USD = 60.0      # ASSUMPTION: filament + hardware for coupon tests CA-1..CA-5 (section 7 of the doc)


def unit_cost(body_g: float, m: Mat, hours: float) -> dict:
    fil = (body_g + joint_boss_g(m)) * 1.08 * m.usd_per_kg / 1000.0
    out = {}
    for q, disc_bought, disc_fil in ((1, 1.0, 1.0), (10, 0.9, 1.0), (100, 0.75, 0.9)):   # ASSUMPTION volume discounts
        c = fil * disc_fil * 1.15 + hours * 1.0 + sum(BOUGHT_USD.values()) * disc_bought + COUPON_ONE_OFF_USD / q
        out[str(q)] = round(c, 0)
    return out


# ------------------------------------------------------------------------------------------------ figures
def _shrink(path: Path, limit: int = 1_500_000):
    from .weight_c import shrink
    shrink(path, limit)


def plot_util(today: dict, best: dict, mk: str, path: Path) -> str:
    """Utilisation max(strength FI, fatigue use) per voxel, front (x-z) and side (y-z), today vs MONO."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 4, figsize=(16, 9), gridspec_kw={"width_ratios": [3, 1.1, 3, 1.1]})
    sc = None
    for k, (lab, F, mass, mg) in enumerate(today and [("Today", today["f"], today["g"], today["m"]),
                                                       ("MONO", best["f"], best["g"], best["m"])]):
        u = np.maximum(F["env"][mk], F["fat"][mk])
        c = F["cen"]
        o = np.argsort(u)
        for j, (ia, ib, xl) in enumerate(((0, 2, "x mm"), (1, 2, "y mm"))):
            ax = axs[2 * k + j]
            sc = ax.scatter(c[o, ia], c[o, ib], c=u[o], s=2.2, cmap="turbo", vmin=0, vmax=1.0, linewidths=0)
            ax.set_aspect("equal")
            ax.set_xlabel(xl)
            if j == 0:
                ax.set_title(f"{lab}: {mass:.0f} g body\nstrength {mg['strength']:.2f}  fatigue {mg['fatigue']:.2f}  "
                             f"creep {mg['creep']:.2f}", fontsize=12)
                ax.set_ylabel("z mm")
            else:
                ax.set_title("side", fontsize=11)
                ax.set_yticklabels([])
    cb = fig.colorbar(sc, ax=axs, shrink=0.75, pad=0.02)
    cb.set_label("utilisation = max(FI strength, fatigue use)   (1.0 = limit)")
    fig.suptitle("Team A MONO: rev C utilisation, worst of 42 sets (bag couple on crown bar and IM3, 15/19/23 in), "
                 "PAHT-CF, layer normal y", fontsize=12)
    fig.savefig(path, dpi=90, bbox_inches="tight")
    plt.close(fig)
    _shrink(path)
    return str(path)


def plot_deformed(best: dict, path: Path, E: float, mag: float = 5.0) -> str:
    """Static carry (C1, 1 g, couple on the crown bar, 19 in) deformed shape, magnified."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    F = best["f"]
    dom, solid, U = F["dom"], F["solid"], F["U"]
    g = dom.grid
    idx = np.where(solid)[0]
    c = g.elem_centers()[idx]
    u = U.reshape(-1, 3)[g.enodes[idx]].mean(axis=1) / E / best["factor_c1"]   # 1 g, real modulus
    d = np.linalg.norm(u, axis=1)
    fig, axs = plt.subplots(1, 2, figsize=(13, 9), gridspec_kw={"width_ratios": [3, 1.3]})
    for ax, (ia, ib, xl) in zip(axs, ((0, 2, "x mm"), (1, 2, "y mm (aft +)"))):
        ax.scatter(c[:, ia], c[:, ib], s=1.5, c="0.8", linewidths=0, label="undeformed")
        s = ax.scatter(c[:, ia] + mag * u[:, ia], c[:, ib] + mag * u[:, ib], c=d, s=1.5, cmap="viridis",
                       linewidths=0, label=f"deformed x{mag:g}")
        ax.set_aspect("equal")
        ax.set_xlabel(xl)
    axs[0].set_ylabel("z mm")
    axs[0].legend(loc="upper center", markerscale=6)
    cb = fig.colorbar(s, ax=axs, shrink=0.7)
    cb.set_label("|u| mm at 1 g, 68 kg, PAHT-CF 23 C (E 3860 MPa)")
    fig.suptitle(f"MONO deformed shape, static carry C1 at 1 g (19 in, couple on the crown bar); "
                 f"max {d.max():.1f} mm, shown x{mag:g}", fontsize=12)
    fig.savefig(path, dpi=90, bbox_inches="tight")
    plt.close(fig)
    _shrink(path)
    return str(path)


def plot_study(hist: list, mats_today: dict, orient: dict, path: Path) -> str:
    """(a) resizing loop: body g vs margins; (b) materials at today's geometry; (c) layer normal."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.5))
    ax = axs[0]
    g = [h["materials"]["paht_rec"]["body_g"] for h in hist]
    for key, lab, mk in (("strength", "strength", "o-"), ("fatigue", "fatigue", "s-"), ("creep", "creep / 2", "^-")):
        v = [h["materials"]["paht_rec"]["n1"]["min"][key] / (2 if key == "creep" else 1) for h in hist]
        ax.plot(g, v, mk, label=lab)
    for i, (x, h) in enumerate(zip(g, hist)):
        ax.annotate(f"it{i}", (x, h["materials"]["paht_rec"]["n1"]["min"]["fatigue"]), textcoords="offset points",
                    xytext=(4, -12), fontsize=8)
    ax.axhline(1.0, color="r", lw=1)
    ax.set_xlabel("printed body g (PAHT-CF)")
    ax.set_ylabel("min margin (rev C, 42 sets)")
    ax.set_title("(a) fully stressed resizing from today's body")
    ax.legend()
    ax = axs[1]
    labs = list(mats_today)
    x = np.arange(len(labs))
    for k, key in enumerate(("strength", "fatigue")):
        ax.bar(x + (k - 0.5) * 0.38, [mats_today[l][key] for l in labs], 0.38, label=key)
    for i, l in enumerate(labs):
        ax.text(i, 0.05, f"{mats_today[l]['body_g']:.0f} g", ha="center", color="w", fontsize=9, rotation=90)
    ax.axhline(1.0, color="r", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labs, fontsize=9)
    ax.set_title("(b) materials on today's geometry")
    ax.legend()
    ax = axs[2]
    labs = list(orient)
    x = np.arange(len(labs))
    for k, key in enumerate(("strength", "fatigue")):
        ax.bar(x + (k - 0.5) * 0.38, [orient[l][key] for l in labs], 0.38, label=key)
    ax.axhline(1.0, color="r", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labs, fontsize=9)
    ax.set_title("(c) layer normal (face on the plate), PAHT-CF")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=85)
    plt.close(fig)
    _shrink(path)
    return str(path)


# ------------------------------------------------------------------------------------------------ Cycles render
WORK = REPO / "outputs" / "frame_comp_A" / "render"
TODAY_DX = -380.0


def build_meshes(b: Body) -> dict:
    """STLs for the render: MONO body, today's released body (shifted), the same carbon crown on both."""
    import trimesh
    from .frame_branch import _sleeve_y
    from .frame_light2_render import _cyl
    WORK.mkdir(parents=True, exist_ok=True)
    files = {}
    mono = body_mesh(b)
    mono.export(WORK / "mono_printed.stl")
    files["mono_printed"] = str(WORK / "mono_printed.stl")
    today = trimesh.load(REPO / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    today.apply_translation((TODAY_DX, 0, 0))
    today.export(WORK / "today_printed.stl")
    files["today_printed"] = str(WORK / "today_printed.stl")
    y_top = float(_sleeve_y(540.0))
    for nm, dx in (("mono_carbon", 0.0), ("today_carbon", TODAY_DX)):
        parts = [_cyl((sx * 115 + dx, y_top, 420.0), (sx * 113 + dx, y_top + 4, 760.0), 8.0) for sx in (-1, 1)]
        parts.append(_cyl((-113 + dx, y_top + 4, 760.0), (113 + dx, y_top + 4, 760.0), 9.0))
        parts.append(_cyl((dx, y_top - 18, 560.0), (dx, y_top - 2, 760.0), 10.0))
        m = trimesh.util.concatenate(parts)
        m.export(WORK / f"{nm}.stl")
        files[nm] = str(WORK / f"{nm}.stl")
    (WORK / "manifest.json").write_text(json.dumps({"files": files}, indent=1))
    return files


def _bpy_main(argv):
    """Runs inside the bpy venv: python frame_comp_A.py --bpy <work> <out_png> <samples> <caption> <sub>"""
    import sys
    import bpy
    sys.path.insert(0, str(REPO))
    from huntkit.viz3d import cycles_render as CR
    work, out_png, samples, cap, sub = Path(argv[0]), Path(argv[1]), int(argv[2]), argv[3], argv[4]
    man = json.loads((work / "manifest.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = CR.setup_scene(samples, (1200, 900), 4)
    mats = {}
    for key, base, rough, coat, bump in (("carbon", "#101112", 0.28, 0.9, 0.0), ("printed", "#4b4945", 0.72, 0.0, 0.35)):
        mt = bpy.data.materials.new(key)
        mt.use_nodes = True
        CR.solid(mt, CR.hexlin(base), rough, coat=coat, noise_bump=bump)
        mats[key] = mt
    objs = []
    for name, path in man["files"].items():
        bpy.ops.wm.stl_import(filepath=path)
        ob = bpy.context.selected_objects[0]
        ob.scale = (0.001, 0.001, 0.001)
        ob.data.materials.clear()
        ob.data.materials.append(mats["carbon" if "carbon" in name else "printed"])
        for p in ob.data.polygons:
            p.use_smooth = True
        objs.append(ob)
    bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    CR.solid(fm, CR.hexlin("#d9d6cd"), 0.9, spec=0.2)
    floor.data.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    rig = (CR._area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2), CR._area("fill", 22.0, 2.4, (0.88, 0.93, 1.0), 1.6),
           CR._area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0))
    lo, hi = CR.visible_bounds(objs)
    floor.location = (0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2] - 0.001)
    cd.angle_y = math.radians(28.0)
    az, el = 160.0, 12.0          # wearer side three-quarter: the branch body reads best from the back
    pos, tgt = CR.fit_camera(lo, hi, az, el, 28.0, 1200 / 900, 1.0)
    cam.location = pos
    CR._aim(cam, tgt)
    dist = math.dist(pos, tgt)
    cd.dof.use_dof = True
    cd.dof.focus_distance = dist
    cd.dof.aperture_fstop = 8.0
    CR.place_rig(rig, az, tgt, max(1.6, 0.75 * dist))
    raw = work / "_raw_pair.png"
    sc.render.filepath = str(raw)
    bpy.ops.render.render(write_still=True)
    CR.composite(raw, out_png, cap, sub)
    CR.shrink_png(out_png)
    print("RENDERED", out_png, flush=True)


def render_pair(b: Body, out_png: Path, cap: str, sub: str, samples: int = 32) -> str:
    import os
    import subprocess
    build_meshes(b)
    bpy = os.environ.get("HUNTKIT_BPY", "/tmp/claude-0/-home-user-Hunting-appeal/4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/"
                                       "scratchpad/bpyenv/bin/python")
    r = subprocess.run([bpy, str(Path(__file__).resolve()), "--bpy", str(WORK), str(out_png), str(samples), cap, sub],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    return str(out_png)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--bpy":
        _bpy_main(sys.argv[2:])
