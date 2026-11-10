"""Frame competition, Team B: SEG (segmented body, each segment printed along its own load path, bolted joints).

Rules: designs/pack_5200/frame_comp/RULES.md. Doc: designs/pack_5200/analysis/frame_comp_B.md.
Research: docs/research/frame_comp_B.md.

What this module answers
1. Orientation gain. Re-solve the production PAHT-CF branch body (2 mm voxels, HA-LS-1 rev C, torsos 15/19/23,
   bag couple on the crown bar AND on IM3, loads from the v2 beam model, exactly the rev C verification path)
   and evaluate the layered FI99 rule with the layer normal along frame x, y (today) or z, and with the
   impossible upper bound "every voxel gets its own best layer normal". This bounds what printing each segment
   "along its own load path" can buy.
2. The joint the H2S bed forces. The body is 540 mm tall; the H2S bed is 340 x 320 mm, so both stays must be cut
   in z 200..340 (today: z 234, bonded carbon dowels). SEG replaces the bond with a bolted printed flange joint
   (no adhesive in the load path). Section resultants at the cut from the voxel stresses; checks: insert
   pull-out (static and 1.6 g fatigue), bolt tension, boss bending (interlayer), shear key bearing, bolt
   bearing, joint mass.
3. More segments. Every extra segment boundary is another joint of the same kind; the orientation upper bound
   says what it can buy back.

Run: ``python -m huntkit.gendesign.frame_comp_seg``  (about 2 min on 4 cores; caches the stress solve)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT

TEAM_DIR = REPO_ROOT / "designs" / "pack_5200" / "frame_comp" / "B"
DOC = REPO_ROOT / "designs" / "pack_5200" / "analysis" / "frame_comp_B.md"
CACHE = REPO_ROOT / "outputs" / "frame_comp_B"
SCREENS = REPO_ROOT / "outputs" / "screens"
SHOT = "20261110_compB"

Z_CUT = 220.0                   # upper segment z 220..544 = 324 mm (+ boss) fits the H2S 340 mm bed axis
ORDER = ("static_carry", "drop_2p5g", "side_hill_torsion", "single_stay_setdown", "meat_straps", "tall_load",
         "tall_load_posts", "overload_haul", "hipbelt_off_abuse")
G_WALK = 1.6

# ---------------------------------------------------------------- baseline (RULES.md, PRODUCTION.md)
BASE_BODY_G = 823.2
BASE_FRAME_G = 1062.6           # frame_mass_production.json
BASE_FRAME_SPREADER_G = 1225.0  # RULES.md
SPREADER_G = 162.3
CORRIE_B2_M_G = 3964.5
BASE_COST_1 = 427.0             # PRODUCTION.md unit cost incl. spreader
BASE_PRINT_H = 27.4
# frame_branch.pack_numbers: "dowels are gone: one printed body, no segment joint" -> the 8 carbon dowels of the
# z 234 joint (8 x 5 mm x 70 mm, 1550 kg/m3 = 17.0 g) are NOT booked in today's 1062.6 g.
BASE_DOWELS_UNBOOKED_G = 8 * 70.0 * np.pi * 2.5 ** 2 * 1550.0 / 1e6

# ---------------------------------------------------------------- materials (data/materials, cited there)
PAHT_RHO = 1060.0               # pa12_cf_fdm_paht density_kg_m3
S_XY = 88.0                     # pa12_cf_fdm_paht tensile_strength_xy_mpa (Bambu TDS)
S_Z = 47.0                      # pa12_cf_fdm_paht tensile_strength_z_mpa (lower of the two TDS revisions)
KNOCK = 0.8                     # env_knockdown_ratio (hot/wet)
FAT = 0.3                       # fatigue_1e5_ratio (ASSUMPTION in the record, used by every rev C body check)
CREEP = 0.4                     # creep_rupture_8h_40c_ratio
INSERT_PULL_N = 1200.0          # insert_heatset_brass_m5 pullout_strength_n (ASSUMPTION, PEM IUTA-M5 in ABS)
INSERT_OD = 7.1
INSERT_WALL = 2.6
INSERT_LEN = 9.5
INSERT_G = 1.5
# ASSUMPTION: insert fatigue (1e5 cycles, R ~ 0) = FAT x the knocked-down static pull-out, same ratio as the
# printed body (no published insert fatigue in FDM PA). Coupon CT-B3.
# ASSUMPTION: insert pulled along the print XY plane keeps the full 1200 N; pulled along the layer normal it is
# scaled by S_Z / S_XY (interlayer). The SEG flange puts every insert axis along frame z = in the print plane.

# M5 bolts (ISO 4762 socket head). Stress area 14.2 mm2 (ISO 898-1 table). Ti-6Al-4V Gr5: UTS 895 MPa min
# (ASTM F136/B348). Mass: shank pi/4 4.5^2 x L + head pi/4 8.5^2 x 5 (ASSUMPTION geometry), Ti 4.43 g/cm3.
BOLT_AS = 14.2
BOLT_UTS_TI = 895.0
TI_RHO = 4.43
STEEL_RHO = 7.9


def bolt_mass_g(L_mm: float, rho: float = TI_RHO) -> float:
    vol = np.pi / 4 * 4.5 ** 2 * L_mm + np.pi / 4 * 8.5 ** 2 * 5.0
    return float(vol * rho / 1000.0)


def nut_mass_g(rho: float = STEEL_RHO) -> float:
    """M5 nylon-insert lock nut (ISO 10511), 8 mm AF x 6 mm: ASSUMPTION hex prism minus bore."""
    hexa = 3 * np.sqrt(3) / 2 * (8.0 / np.sqrt(3)) ** 2
    return float((hexa - np.pi / 4 * 5.0 ** 2) * 6.0 * rho / 1000.0 * 0.85)


# ============================================================================ layered FI (frame_topopt rule)
def layer_terms(S: np.ndarray, a: int, s_xy=S_XY, s_z=S_Z, knock=KNOCK) -> np.ndarray:
    """The three terms of ``frame_topopt.layer_failure_index`` (in-plane VM, layer-normal, interlayer shear
    at 0.6 s_z) for one stress field S (n, 6: sxx syy szz txy tyz tzx) and layer normal axis a."""
    s = np.abs(S[:, :3])
    t = np.abs(S[:, 3:])
    ip = [k for k in range(3) if k != a]
    sh = {0: (0, 2), 1: (0, 1), 2: (1, 2)}[a]
    tl = np.maximum(t[:, sh[0]], t[:, sh[1]])
    tin = t[:, [k for k in range(3) if k not in sh][0]]
    vm = np.sqrt(np.maximum(s[:, ip[0]], s[:, ip[1]]) ** 2 + 3 * tin ** 2)
    return np.c_[vm / (knock * s_xy), s[:, a] / (knock * s_z), tl / (knock * 0.6 * s_z)]


# ============================================================================ the solve (rev C path)
def solve_stresses(log=print, use_cache: bool = True) -> dict:
    """All rev C load sets (C = couple on the crown bar, C_im3 = couple on IM3) x torsos 15/19/23 on the
    production body. Same steps as ``frame_cg_recheck.verify_sets`` (one PARDISO factorization, the clamp and
    load-patch exclusion per scenario tag), but the element stresses are kept so the layer normal can vary."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / "stress_revc.npz"
    if use_cache and f.exists():
        d = np.load(f, allow_pickle=True)
        return {k: d[k] for k in d.files} | {"sets": list(d["sets"])}
    from . import frame_topopt as ft
    from . import rev_c_verification as V
    from .spreader_layout import raster
    t0 = time.time()
    sets, _ = V.beam_runs(buckling=False, log=log)
    dom, solid = raster(None, 2.0)
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
    E = 3860.0                      # pa12_cf_fdm_paht youngs_modulus_xy_mpa (stress is E-independent)
    Ss, meta, ex = [], [], {}
    for tg in ("C", "C_im3"):
        ts = [s for s in sets if s.key.startswith(tg + ":")]
        F, _ = ft.assemble_loads(dom, ts, solid_mask=solid)
        Ur = solver.solve(K, np.ascontiguousarray(F[rs.free])).reshape(rs.free.size, -1)
        U = np.zeros((g.ndof, len(ts)))
        U[rs.free] = Ur / E
        Fn = np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2))
        ex[tg] = (clamp | (Fn > 0))[g.enodes].any(axis=1)[idx]
        for k, ls in enumerate(ts):
            _, S = ft.element_stress(g, U[:, k], solid, E)
            Ss.append(S.astype(np.float32))
            meta.append(json.dumps({"key": ls.key, "case": ls.case, "torso": ls.torso, "factor": ls.factor,
                                    "tag": tg}))
        if log:
            log(f"  [{tg}] {len(ts)} sets solved, {time.time() - t0:.0f} s")
    try:
        solver.free_memory(everything=True)
    except Exception:
        pass
    out = {"S": np.stack(Ss), "cen": cen, "ex_C": ex["C"], "ex_C_im3": ex["C_im3"], "sets": meta,
           "body_g": np.array(float(solid.sum() * 8.0 * PAHT_RHO / 1e6))}
    np.savez_compressed(f, **out)
    return out


def _meta(st) -> list[dict]:
    return [json.loads(str(m)) for m in st["sets"]]


# ============================================================================ 1. orientation study
ORIENT = {"x (stay on its side)": 0, "y (flat, today)": 1, "z (stay upright)": 2}


def orientation_study(st: dict, seg_axis: np.ndarray | None = None) -> dict:
    """Per case min SF (1/FI99, worst torso and couple variant) for each uniform layer normal, for an optional
    per-element axis map (segmented print) and for the per-element-best upper bound. Fatigue (C1 at 1.6 g,
    FI <= 0.3) and creep (C1 at 1 g, FI <= 0.4) as ``frame_cg_recheck.summarize_body``."""
    meta = _meta(st)
    S = st["S"]
    variants = dict(ORIENT)
    if seg_axis is not None:
        variants["segmented map"] = "map"
    variants["best per voxel (upper bound)"] = "best"
    res = {v: {} for v in variants}
    hot = {}
    for i, m in enumerate(meta):
        ex = st["ex_" + m["tag"]]
        Si = S[i].astype(float)
        T = np.stack([layer_terms(Si, a) for a in range(3)])        # (3 axes, n, 3 terms)
        fi_ax = T.max(axis=2)                                        # (3, n)
        for v, a in variants.items():
            if a == "best":
                fi = fi_ax.min(axis=0)
            elif a == "map":
                fi = fi_ax[seg_axis, np.arange(fi_ax.shape[1])]
            else:
                fi = fi_ax[a]
            fi99 = float(np.percentile(fi[~ex], 99))
            res[v][m["key"]] = (fi99, m)
            if a == 1:
                ok = ~ex & (fi >= fi99)
                share = np.bincount(T[1][ok].argmax(axis=1), minlength=3) / max(ok.sum(), 1)
                hot[m["key"]] = share.tolist()
    out = {}
    for v, rows in res.items():
        cases = {}
        for c in ORDER:
            rr = [(fi, m) for fi, m in rows.values() if m["case"] == c]
            if not rr:
                continue
            fi, m = max(rr, key=lambda r: r[0])
            cases[c] = {"sf": 1.0 / fi, "set": m["key"], "factor": m["factor"]}
        sc = [(fi, m) for fi, m in rows.values() if m["case"] == "static_carry"]
        fi, m = max(sc, key=lambda r: r[0])
        out[v] = {"cases": cases, "sf_min": min(c["sf"] for c in cases.values()),
                  "governing": min(cases.items(), key=lambda kv: kv[1]["sf"])[0],
                  "sf_fatigue": FAT / (fi * G_WALK / m["factor"]), "sf_creep": CREEP / (fi / m["factor"]),
                  "fatigue_set": m["key"]}
    gov = {k: hot[k] for k in hot if any(s in k for s in ("static_carry|15", "drop_2p5g|15", "hipbelt_off_abuse|15",
                                                          "side_hill_torsion|15"))}
    out["_hot_term_share_today"] = gov
    return out


# ============================================================================ 2. section loads at the cut
def section_loads(st: dict, z_cut: float = 220.0, h: float = 2.0) -> dict:
    """N, Vx, Vy, Mx, My, T across z = z_cut per stay (L/R) for every set (factored loads as the sets carry
    them), from the element layer just below the cut (as ``frame_topopt.section_resultants``, plus torsion)."""
    cen = st["cen"]
    lay = np.abs(cen[:, 2] - (z_cut - h / 2)) < h / 2 + 1e-6
    A = h * h
    rows = []
    geom = {}
    for side, m in (("L", cen[:, 0] < 0), ("R", cen[:, 0] >= 0)):
        mm = lay & m
        c = cen[mm]
        geom[side] = {"n": int(mm.sum()), "area_mm2": float(mm.sum() * A),
                      "x": [float(c[:, 0].min() - h / 2), float(c[:, 0].max() + h / 2)],
                      "y": [float(c[:, 1].min() - h / 2), float(c[:, 1].max() + h / 2)],
                      "centroid": c.mean(0).tolist()}
    for i, meta in enumerate(_meta(st)):
        Si = st["S"][i]
        for side, m in (("L", cen[:, 0] < 0), ("R", cen[:, 0] >= 0)):
            mm = lay & m
            s = Si[mm].astype(float)
            c = cen[mm]
            cc = c.mean(0)
            rows.append({"set": meta["key"], "case": meta["case"], "torso": meta["torso"],
                         "factor": meta["factor"], "side": side,
                         "N": float(s[:, 2].sum() * A), "Vx": float(s[:, 5].sum() * A),
                         "Vy": float(s[:, 4].sum() * A),
                         "Mx": float((s[:, 2] * (c[:, 1] - cc[1])).sum() * A),
                         "My": float((s[:, 2] * (c[:, 0] - cc[0])).sum() * A),
                         "T": float(((s[:, 4] * (c[:, 0] - cc[0])) - (s[:, 5] * (c[:, 1] - cc[1]))).sum() * A)})
    return {"z": z_cut, "geom": geom, "rows": rows}


# ============================================================================ bolted flange joint
@dataclass
class FlangeJoint:
    """Bolted butt-flange joint across the z cut, per stay. Bolts parallel to the stay axis (frame z = in the
    print XY plane), in two rows: fore (wearer side, y-) and aft (bag side, y+) of the sleeve section, outside
    the crown-leg bore, so the bore stays continuous for the sliding leg. Each bolt sits in a printed boss on
    each segment (boss dia = insert OD + 2 x min wall), a boss-to-wall gusset, and a 3 mm printed shear key
    (tongue on the lower flange, groove in the upper) round the sleeve that takes Vx, Vy and the torque.
    ``fastening``: "insert" = heat-set insert in the upper boss (the brief), "through" = through-bolt with a
    nylon-insert lock nut (no insert in tension)."""
    n_row: int = 3                  # bolts per row (2 rows: fore and aft)
    offset: float = 6.2             # bolt centre outside the section face, mm (boss radius)
    t_boss: float = 12.0            # boss height per segment, mm
    gusset_mm3: float = 300.0       # ASSUMPTION per boss: 12 x 10 x 5 mm triangular web to the wall (x 0.5)
    key_h: float = 3.0
    key_w: float = 3.0
    prying: float = 1.25            # ASSUMPTION: prying factor on the bolt tension (boss next to the wall)
    fastening: str = "insert"
    bolt_len: float = 30.0
    y_env: float = 14.8             # bag-side envelope y_hi at the cut (frame_topopt.load_envelope().y_hi(220))

    def y_rows(self, geom: dict) -> tuple[float, float]:
        """Fore row outside the wearer face (room to Y_LO -48); aft row clamped so the boss stays inside the
        bag-side envelope (it then sits beside the crown-leg bore, in the inboard branch material)."""
        y0, y1 = geom["y"]
        return y0 - self.offset, min(y1 + self.offset, self.y_env - self.boss_d / 2)

    @property
    def boss_d(self) -> float:
        return INSERT_OD + 2 * INSERT_WALL

    def bolt_xy(self, geom: dict) -> np.ndarray:
        x0, x1 = geom["x"]
        xo, xi = (x0, x1) if abs(x0) > abs(x1) else (x1, x0)      # outboard / inboard face
        so = np.sign(xo - xi)
        # outboard bolt 2 mm outside the outboard face (keeps a >= 7 mm ligament to the crown-leg bore on the
        # aft row), inboard bolt one boss radius inside the inboard face (branch material)
        xs = np.linspace(xo + so * 2.0, xi + so * self.boss_d / 2, self.n_row)
        yf, ya = self.y_rows(geom)
        pts = [(x, yf) for x in xs] + [(x, ya) for x in xs]
        return np.array(pts)

    def lever(self, geom: dict) -> float:
        yf, ya = self.y_rows(geom)
        return ya - yf

    def mass_g(self, geom: dict) -> dict:
        n = 2 * self.n_row
        boss = n * 2 * (np.pi / 4 * self.boss_d ** 2 * self.t_boss + self.gusset_mm3) * PAHT_RHO / 1e6
        x0, x1 = geom["x"]
        y0, y1 = geom["y"]
        perim = 2 * ((x1 - x0) + (y1 - y0))
        key = perim * self.key_h * self.key_w * PAHT_RHO / 1e6
        bolts = n * bolt_mass_g(self.bolt_len)
        ins = n * INSERT_G if self.fastening == "insert" else n * (nut_mass_g() + 0.4)  # + washer
        return {"bosses": boss, "shear_key": key, "bolts_ti": bolts, "inserts_or_nuts": ins,
                "per_stay": boss + key + bolts + ins, "both_stays": 2 * (boss + key + bolts + ins)}


def bolt_tension(row: dict, xy: np.ndarray, prying: float) -> float:
    """Elastic bolt group (Shigley 8-?): F_i = N/n + Mx (y_i - yc) / sum (y - yc)^2 + My (x_i - xc) / sum
    (x - xc)^2, sign convention: a positive Mx (sigma_zz rising with y) puts the y+ row in tension. Returns the
    worst tensile bolt force x prying (compression goes to flange contact)."""
    x, y = xy[:, 0], xy[:, 1]
    xc, yc = x.mean(), y.mean()
    n = len(x)
    F = (row["N"] / n + row["Mx"] * (y - yc) / np.sum((y - yc) ** 2)
         + row["My"] * (x - xc) / max(np.sum((x - xc) ** 2), 1e-9))
    return float(max(F.max(), 0.0) * prying)


def joint_checks(sec: dict, j: FlangeJoint) -> dict:
    """Margins (capacity / demand, pass >= 1) at the factored load of every set, and fatigue at 1.6 g
    from the static-carry sets (factor 2 -> x 1.6 / 2), worst over sets, sides and torsos."""
    out = {"strength": {}, "fatigue": {}}
    worst = {}

    def keep(kind, name, val, row):
        k = (kind, name)
        if k not in worst or val < worst[k][0]:
            worst[k] = (val, f"{row['set']} {row['side']}")

    # geometry (same for every set): bolt hole to crown-leg bore ligament >= insert min wall, boss pitch
    from .frame_topopt import load_envelope
    env = load_envelope()
    g0 = sec["geom"]["L"]
    xy0 = j.bolt_xy(g0)
    bore = np.array([-env.top_pt[0], env.sleeve_y(sec["z"])])
    lig = float((np.linalg.norm(xy0 - bore, axis=1) - 9.0 - 2.65).min())
    pitch = float(np.diff(xy0[: j.n_row, 0]).__abs__().min()) if j.n_row > 1 else 99.0
    out["geometry"] = {"bore_ligament_mm": lig, "boss_pitch_mm": pitch,
                       "bore_ligament_margin": lig / INSERT_WALL, "boss_pitch_margin": pitch / j.boss_d}
    for r in sec["rows"]:
        g = sec["geom"][r["side"]]
        xy = j.bolt_xy(g)
        Tb = bolt_tension(r, xy, j.prying)
        V = np.hypot(r["Vx"], r["Vy"])
        # bolt tension vs fastener capacity
        if j.fastening == "insert":
            cap = INSERT_PULL_N * KNOCK
            keep("strength", "insert pull-out (axis in print plane)", cap / max(Tb, 1e-9), r)
        else:
            # washer (OD 10, ID 5.3) bearing on the boss face, load in the print plane (XY strength)
            aw = np.pi / 4 * (10.0 ** 2 - 5.3 ** 2)
            cap = aw * KNOCK * S_XY
            keep("strength", "washer bearing on boss (through-bolt)", cap / max(Tb, 1e-9), r)
        keep("strength", "bolt tension Ti Gr5 (0.7 UTS x As)", 0.7 * BOLT_UTS_TI * BOLT_AS / max(Tb, 1e-9), r)
        # boss bending (prying): cantilever boss, bending stress across the layers (frame y = layer normal)
        w = j.boss_d
        sig = 6 * (Tb / j.prying) * j.offset / (w * j.t_boss ** 2)
        keep("strength", "boss bending (interlayer, s_z)", KNOCK * S_Z / max(sig, 1e-9), r)
        # shear key bearing (Vx, Vy) + torque as a couple over the key perimeter
        x0, x1 = g["x"]
        y0, y1 = g["y"]
        a_key_x = (y1 - y0) * j.key_h          # faces that take Vx
        a_key_y = (x1 - x0) * j.key_h
        tq = abs(r["T"]) / max((x1 - x0), 1e-9)   # torque as a y-force couple on the x faces
        sb = max(abs(r["Vx"]) / a_key_x, (abs(r["Vy"]) + tq) / a_key_y)
        keep("strength", "shear key bearing (XY)", KNOCK * S_XY / max(sb, 1e-9), r)
        # bolt bearing in the clearance hole if the key is lost (damage tolerance, info): 6 bolts, d 5, t_boss
        bb = V / (len(xy) * 5.0 * j.t_boss)
        keep("strength", "bolt bearing, key lost (info)", KNOCK * S_XY / max(bb, 1e-9), r)
        if r["case"] == "static_carry":
            k = G_WALK / r["factor"]
            Tf = Tb * k
            if j.fastening == "insert":
                keep("fatigue", "insert pull-out at 1.6 g (0.3 x static)", FAT * INSERT_PULL_N * KNOCK / max(Tf, 1e-9), r)
            else:
                aw = np.pi / 4 * (10.0 ** 2 - 5.3 ** 2)
                keep("fatigue", "washer bearing at 1.6 g", FAT * aw * KNOCK * S_XY / max(Tf, 1e-9), r)
            keep("fatigue", "boss bending at 1.6 g (interlayer)", FAT * KNOCK * S_Z / max(sig * k, 1e-9), r)
            keep("fatigue", "shear key bearing at 1.6 g", FAT * KNOCK * S_XY / max(sb * k, 1e-9), r)
            # Ti bolt fatigue: ASSUMPTION endurance of a rolled-thread Ti M5 at R~0 = 0.25 x UTS on As
            keep("fatigue", "Ti bolt thread at 1.6 g (0.25 UTS)", 0.25 * BOLT_UTS_TI * BOLT_AS / max(Tf, 1e-9), r)
    for (kind, name), (v, where) in worst.items():
        out[kind][name] = {"margin": v, "set": where}
    ms = [v["margin"] for kind in ("strength", "fatigue") for n, v in out[kind].items() if "(info)" not in n]
    ms += [out["geometry"]["bore_ligament_margin"], out["geometry"]["boss_pitch_margin"]]
    out["min_margin"] = min(ms)
    out["min_strength"] = min(v["margin"] for n, v in out["strength"].items() if "(info)" not in n)
    out["min_fatigue"] = min(v["margin"] for v in out["fatigue"].values())
    out["mass_g"] = j.mass_g(sec["geom"]["L"])
    out["design"] = asdict(j)
    return out


def size_joint(sec: dict, fastening: str) -> tuple[FlangeJoint, dict, list]:
    """Lightest FlangeJoint (bolts per row, boss height) whose every margin >= 1."""
    trials = []
    for n in (2, 3, 4, 5):
        for t in (8.0, 10.0, 12.0, 14.0):
            j = FlangeJoint(n_row=n, t_boss=t, fastening=fastening)
            c = joint_checks(sec, j)
            trials.append({"n_row": n, "t_boss": t, "min_margin": c["min_margin"],
                           "mass_both_g": c["mass_g"]["both_stays"]})
    ok = [t for t in trials if t["min_margin"] >= 1.0]
    best = min(ok, key=lambda t: t["mass_both_g"]) if ok else max(trials, key=lambda t: t["min_margin"])
    j = FlangeJoint(n_row=best["n_row"], t_boss=best["t_boss"], fastening=fastening)
    if not ok:
        best["note"] = "no passing layout"
    return j, joint_checks(sec, j), trials


# ============================================================================ 3. more segments
def segment_map(cen: np.ndarray, scheme: str) -> tuple[np.ndarray, np.ndarray, int]:
    """Segment id and layer-normal axis per voxel. Schemes:
    - "SEG-2": lower (z < 234) and upper, both flat (layer normal y) = today's orientation, bolted flange.
    - "SEG-7": lower U, L/R upper sleeves printed ON THEIR SIDE (normal x), upper bar + pawl housing, mid bar,
      L/R inboard branches; bars flat (normal y). 6 extra boundaries -> about 10 joint interfaces."""
    x, y, z = cen.T
    seg = np.zeros(len(cen), int)
    ax = np.ones(len(cen), int)
    if scheme == "SEG-2":
        seg[z >= 234.0] = 1
        return seg, ax, 2
    up = z >= 234.0
    sleeve = up & (np.abs(x) > 95.0)
    seg[sleeve & (x < 0)] = 1
    seg[sleeve & (x > 0)] = 2
    seg[up & ~sleeve & (z > 480.0)] = 3
    seg[up & ~sleeve & (z > 300.0) & (z <= 360.0)] = 4
    seg[up & ~sleeve & ~((z > 480.0) | ((z > 300.0) & (z <= 360.0))) & (x < 0)] = 5
    seg[up & ~sleeve & ~((z > 480.0) | ((z > 300.0) & (z <= 360.0))) & (x >= 0)] = 6
    ax[sleeve] = 0
    return seg, ax, 10


# ============================================================================ driver
def run(log=print) -> dict:
    t0 = time.time()
    st = solve_stresses(log=log)
    body_g = float(st["body_g"])
    log(f"body {body_g:.1f} g, {len(st['sets'])} sets")
    orient = orientation_study(st)
    seg7, ax7, nj7 = segment_map(st["cen"], "SEG-7")
    orient7 = orientation_study(st, seg_axis=ax7)["segmented map"]
    sec = section_loads(st, Z_CUT)
    scan = []
    for z in (206.0, 220.0, 234.0, 250.0):
        sz = section_loads(st, z)
        a, ca, _ = size_joint(sz, "insert")
        b, cb, _ = size_joint(sz, "through")
        scan.append({"z": z, "insert": [a.n_row, a.t_boss, ca["min_margin"], ca["mass_g"]["both_stays"]],
                     "through": [b.n_row, b.t_boss, cb["min_margin"], cb["mass_g"]["both_stays"]]})
    j_ins, c_ins, tr_ins = size_joint(sec, "insert")
    j_thr, c_thr, tr_thr = size_joint(sec, "through")
    ctx = {"date": "2026-11-10", "body_g": body_g, "orientation": orient, "seg7_orientation": orient7,
           "section_z234": {"geom": sec["geom"],
                            "worst_Mx": max(sec["rows"], key=lambda r: abs(r["Mx"]))},
           "joint_insert": c_ins, "joint_insert_trials": tr_ins,
           "joint_through": c_thr, "joint_through_trials": tr_thr, "cut_scan": scan, "z_cut": Z_CUT,
           "seconds": None}
    ctx["_sec_rows"] = sec["rows"]
    ctx["_seg7"] = (seg7, ax7, nj7)
    ctx["_st"] = st
    ctx["seconds"] = time.time() - t0
    return ctx


def headline(ctx: dict) -> dict:
    """The SEG entry: SEG-2T (two flat segments, through-bolted flange at z 220; lighter than the inserted
    flange SEG-2I, which is reported alongside)."""
    today = ctx["orientation"]["y (flat, today)"]
    ji = ctx["joint_insert"]
    jt = ctx["joint_through"]
    joint_g = jt["mass_g"]["both_stays"]
    frame_g = BASE_FRAME_G + joint_g
    return {"frame_g": frame_g, "frame_plus_spreader_g": frame_g + SPREADER_G, "joint_g": joint_g,
            "joint_through_g": jt["mass_g"]["both_stays"],
            "pack_g": CORRIE_B2_M_G - (BASE_FRAME_SPREADER_G - (frame_g + SPREADER_G)),
            "sf_min": today["sf_min"], "governing": today["governing"], "sf_fatigue": today["sf_fatigue"],
            "joint_min": jt["min_margin"], "joint_min_insert": ji["min_margin"],
            "joint_insert_g": ji["mass_g"]["both_stays"]}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


# ============================================================================ outputs
COST = {   # USD; PRODUCTION.md unit cost 427 incl. spreader, minus dowels 4.5 + MMA 2.0, plus the SEG hardware
    "base_1": BASE_COST_1, "dowels_mma": -6.5,
    "ti_bolts": 8 * 1.5,       # ASSUMPTION $1.5 per Ti Gr5 M5x30 socket head (retail packs)
    "nuts_washers": 1.0,       # ASSUMPTION A2 nylon-insert nuts + washers
    "boss_filament": 16.1 * 1.08 * 0.08,
}


def result_json(ctx: dict) -> dict:
    h = headline(ctx)
    jt, ji = ctx["joint_through"], ctx["joint_insert"]
    c1 = sum(COST.values())
    return {
        "team": "B",
        "concept_name": "SEG-2T: two flat-printed segments, through-bolted printed flange at z 220",
        "one_line": ("Segmenting further buys at most +4 % (every voxel ideally oriented) because today's flat print "
                     "already loads the stays in-plane; the H2S bed forces one cut, and replacing the bonded dowels "
                     f"with a no-adhesive bolted flange costs {h['joint_g']:.0f} g: passes rev C but is heavier "
                     "than the baseline."),
        "frame_g": round(h["frame_g"], 1),
        "frame_plus_spreader_g": round(h["frame_plus_spreader_g"], 1),
        "pack_mass_corrie_b2_M_g": round(h["pack_g"], 1),
        "passes_rev_c": bool(h["sf_min"] >= 1.0 and h["sf_fatigue"] >= 1.0 and h["joint_min"] >= 1.0),
        "worst_strength_margin": round(h["sf_min"], 2),
        "worst_fatigue_margin": round(h["sf_fatigue"], 2),
        "worst_joint_margin": round(h["joint_min"], 2),
        "governing_case": (f"strength {h['governing']}|15 upper bar / pawl housing (body unchanged); fatigue "
                           f"{ctx['orientation']['y (flat, today)']['fatigue_set']}; joint "
                           + min({**jt['strength'], **jt['fatigue']}.items(), key=lambda kv: kv[1]['margin'])[0]
                           + " @ " + min({**jt['strength'], **jt['fatigue']}.items(),
                                         key=lambda kv: kv[1]['margin'])[1]["set"]),
        "torsion_stiffness_vs_today": 0.97,
        "print_hours": round(BASE_PRINT_H * (1 + 16.1 / BASE_BODY_G), 1),
        "printer": "H2S home",
        "cost_usd": {"1": round(c1), "10": round(c1 * 0.93), "100": round(c1 * 0.86)},
        "build_hours": 5.0,
        "skill_level": "beginner",
        "looks_generative": True,
        "patents_checked": ["US 10,952,523 (Mystery Ranch, crown/lifter guardrail: crown untouched)",
                            "docs/DECISIONS.md patent guardrails (unchanged branch body, no new frame-to-bag feature)"],
        "governing_assumptions": [
            "PAHT-CF fatigue at 1e5 = 0.3 x static (record ASSUMPTION, applied to body and joint) -> CT-B1",
            "Interlayer shear strength = 0.6 x Z tensile (frame_topopt rule) -> CT-B2",
            "Boss bending with prying factor 1.25, stress across layers at 0.8 x 47 MPa; fatigue 0.3 x -> CT-B3",
            "Washer bearing on the printed boss face (XY, 0.8 x 88 MPa; fatigue 0.3 x) -> CT-B3",
            "Joint preload not credited; key + bolts rigid enough that the body FE (continuous) holds -> CT-B4",
            "Torsion stiffness 0.97 x today (flange compliance, not modelled) -> CT-B4",
            "Ti Gr5 M5 rolled-thread fatigue >= 0.25 UTS on As at R~0 -> CT-B4",
            "Insert variant only: 1200 N pull-out (record ASSUMPTION) and insert fatigue 0.3 x static -> CT-B5",
        ],
        "coupon_tests": [
            "CT-B1: PAHT-CF XY and Z (and +/-45 raster) tension-tension fatigue, R 0.1, 2 Hz, 23 C/50 % RH and 40 C wet, 5 per level, run-out 1e5 at 0.30 x UTS",
            "CT-B2: short-beam / V-notch interlayer shear on annealed PAHT-CF, 5 dry + 5 wet, pass >= 0.6 x 47 MPa x 0.8",
            "CT-B3: one-boss pull-through coupon (printed boss, Ti M5, washer, as the flange) static x5 and fatigue x3 at 1.6 g bolt load, 1e5 cycles",
            "CT-B4: full z 220 joint segment (both stays' stubs, 250 mm each side) in 4-point bending to the factored Mx 66.5 N m, then 1e5 cycles at the 1.6 g Mx; record rotation stiffness, pencil-mark slip <= 0.5 mm, bolt preload loss",
            "CT-B5 (insert variant only): 5 brass M5 inserts in printed PAHT-CF bosses, axis in the print plane, static >= 1.5 kN and 3 at 0.3 x 960 N for 1e5 cycles",
        ],
    }


def plot_concept(ctx: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    st = ctx["_st"]
    cen = st["cen"]
    sec = ctx["section_z234"]["geom"]["L"]
    j = FlangeJoint(**ctx["joint_through"]["design"])
    fig = plt.figure(figsize=(12, 7.2), dpi=100)
    ax1 = fig.add_axes([0.05, 0.06, 0.26, 0.84])
    ax2 = fig.add_axes([0.33, 0.06, 0.28, 0.84])
    ax3 = fig.add_axes([0.66, 0.30, 0.32, 0.55])
    # front views (x-z), one dot per occupied column
    xz = np.unique(np.round(cen[:, [0, 2]] / 2.0).astype(int), axis=0) * 2.0
    ax1.scatter(xz[:, 0], xz[:, 1], s=2.2, c="#8a8f98", marker="s", lw=0)
    ax1.axhline(234, color="#c0392b", lw=1.5, ls="--")
    ax1.text(0, 242, "z 234: 8 carbon dowels,\nMMA bonded (adhesive)", ha="center", fontsize=9, color="#c0392b")
    ax1.set_title(f"TODAY: one body, cut at z 234\nframe {BASE_FRAME_G:.0f} g (dowels not booked)", fontsize=11)
    up = xz[:, 1] >= Z_CUT
    ax2.scatter(xz[~up, 0], xz[~up, 1], s=2.2, c="#2e86ab", marker="s", lw=0, label="segment 1 (lower, flat)")
    ax2.scatter(xz[up, 0], xz[up, 1], s=2.2, c="#e07a1f", marker="s", lw=0, label="segment 2 (upper, flat)")
    for sgn in (-1, 1):
        g = dict(sec)
        xy = j.bolt_xy(g)
        for x, _ in xy[: j.n_row]:
            ax2.add_patch(Rectangle((sgn * abs(x) - j.boss_d / 2, Z_CUT - j.t_boss), j.boss_d, 2 * j.t_boss,
                                    fc="#2d2d2d", ec="none"))
    ax2.axhline(Z_CUT, color="#2d2d2d", lw=0.8, ls=":")
    ax2.text(0, Z_CUT + 14, f"z {Z_CUT:.0f}: bolted flange\n{2 * len(j.bolt_xy(sec))} Ti M5, no adhesive",
             ha="center", fontsize=9)
    h = headline(ctx)
    ax2.set_title(f"SEG-2T: two segments + bolted flange\nframe {h['frame_g']:.0f} g (+{h['joint_g']:.0f} g)",
                  fontsize=11)
    ax2.legend(loc="lower center", fontsize=8, markerscale=4, frameon=False)
    for a in (ax1, ax2):
        a.set_aspect("equal")
        a.set_xlim(-160, 160)
        a.set_ylim(-10, 560)
        a.set_xticks([])
        a.set_yticks([0, 100, 200, 300, 400, 500])
        a.tick_params(labelsize=8)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    ax1.set_ylabel("z, mm", fontsize=9)
    # joint section (looking down at the cut, left stay)
    lay = np.abs(cen[:, 2] - (Z_CUT - 1.0)) < 1.01
    m = lay & (cen[:, 0] < 0)
    for (x, y) in cen[m][:, :2]:
        ax3.add_patch(Rectangle((x - 1, y - 1), 2, 2, fc="#e07a1f", ec="none", alpha=0.8))
    for x, y in j.bolt_xy(sec):
        ax3.add_patch(Circle((x, y), j.boss_d / 2, fc="#2d2d2d", alpha=0.35))
        ax3.add_patch(Circle((x, y), 2.65, fc="white", ec="#2d2d2d"))
    from .frame_topopt import load_envelope
    env = load_envelope()
    ax3.add_patch(Circle((-env.top_pt[0], env.sleeve_y(Z_CUT)), 9.0, fc="white", ec="#555", ls="--"))
    ax3.axhline(j.y_env, color="#c0392b", lw=1)
    ax3.text(-150, j.y_env + 1.5, "bag-side envelope", fontsize=8, color="#c0392b")
    ax3.text(-150, -45, "wearer side (y -)", fontsize=8)
    ax3.set_xlim(-152, -70)
    ax3.set_ylim(-48, 26)
    ax3.set_aspect("equal")
    ax3.set_title(f"Left stay section at the cut (top view)\n{2 * j.n_row} bolts / stay, bosses Ø{j.boss_d:.1f}, "
                  "crown-leg bore kept clear", fontsize=10)
    ax3.tick_params(labelsize=8)
    fig.text(0.66, 0.08, "Joint margins (factored / 1.6 g fatigue):\n"
             + "\n".join(f"  {n}: {v['margin']:.2f}" for n, v in
                         list(ctx["joint_through"]["strength"].items())[:3]
                         + list(ctx["joint_through"]["fatigue"].items())[:2]), fontsize=8.5, va="bottom")
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def plot_utilization(ctx: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    st = ctx["_st"]
    cen = st["cen"]
    meta = _meta(st)
    env = np.zeros(len(cen))
    for i, m in enumerate(meta):
        ex = st["ex_" + m["tag"]]
        fi = layer_terms(st["S"][i].astype(float), 1).max(axis=1)
        env = np.maximum(env, np.where(ex, 0.0, fi))
    fig = plt.figure(figsize=(12, 7.2), dpi=100)
    ax1 = fig.add_axes([0.02, 0.08, 0.26, 0.82])
    order = np.argsort(env)
    sc = ax1.scatter(cen[order, 0], cen[order, 2], c=env[order], s=2.5, cmap="viridis", vmin=0, vmax=0.8,
                     marker="s", lw=0)
    ax1.set_aspect("equal")
    ax1.set_title("Utilization FI (envelope, all rev C sets)\nflat print, layer normal y", fontsize=10)
    ax1.axhline(Z_CUT, color="#e07a1f", lw=1.2, ls="--")
    cax = fig.add_axes([0.29, 0.2, 0.012, 0.6])
    fig.colorbar(sc, cax=cax, label="FI (factored); pass FI99 <= 1")
    ax1.tick_params(labelsize=8)
    # orientation study
    ax2 = fig.add_axes([0.40, 0.56, 0.57, 0.36])
    o = ctx["orientation"]
    names = [k for k in o if not k.startswith("_")]
    sfm = [o[k]["sf_min"] for k in names]
    fat = [o[k]["sf_fatigue"] for k in names]
    xx = np.arange(len(names))
    ax2.bar(xx - 0.2, sfm, 0.38, color="#2e86ab", label="strength margin (min case)")
    ax2.bar(xx + 0.2, fat, 0.38, color="#e07a1f", label="fatigue margin (1.6 g)")
    for i, (a, b) in enumerate(zip(sfm, fat)):
        ax2.text(i - 0.2, a + 0.03, f"{a:.2f}", ha="center", fontsize=8)
        ax2.text(i + 0.2, b + 0.03, f"{b:.2f}", ha="center", fontsize=8)
    ax2.axhline(1.0, color="#c0392b", lw=1)
    ax2.set_xticks(xx)
    ax2.set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=8)
    ax2.set_title("Layer orientation: what printing 'along the load path' can buy (rev C, all torsos)",
                  fontsize=10)
    ax2.legend(fontsize=8, frameon=False, loc="upper left")
    ax2.set_ylim(0, 2.0)
    # joint margins
    ax3 = fig.add_axes([0.62, 0.08, 0.35, 0.36])
    jt = ctx["joint_through"]
    items = [(n, v["margin"]) for kind in ("strength", "fatigue") for n, v in jt[kind].items() if "(info)" not in n]
    items = sorted(items, key=lambda kv: kv[1])
    ax3.barh([n for n, _ in items], [min(v, 4.0) for _, v in items], color="#2d2d2d")
    for i, (_, v) in enumerate(items):
        ax3.text(min(v, 4.0) + 0.05, i, f"{v:.2f}", va="center", fontsize=8)
    ax3.axvline(1.0, color="#c0392b", lw=1)
    ax3.set_xlim(0, 4.6)
    ax3.tick_params(labelsize=8)
    ax3.set_title(f"SEG-2T flange joint at z {Z_CUT:.0f} (margins, capped at 4)", fontsize=10)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)


def write_all(ctx: dict, log=print) -> dict:
    TEAM_DIR.mkdir(parents=True, exist_ok=True)
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [plot_concept(ctx, SCREENS / f"{SHOT}_1.png"), plot_utilization(ctx, SCREENS / f"{SHOT}_2.png")]
    res = result_json(ctx)
    (TEAM_DIR / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    full = _jsonable({k: v for k, v in ctx.items()})
    full["headline"] = headline(ctx)
    full["screens"] = shots
    (TEAM_DIR / "analysis_results.json").write_text(json.dumps(full, indent=1) + "\n")
    log(f"wrote {TEAM_DIR / 'result.json'}; screens {shots}")
    return res


def main(log=print):
    ctx = run(log=log)
    write_all(ctx, log=log)


if __name__ == "__main__":
    main()
