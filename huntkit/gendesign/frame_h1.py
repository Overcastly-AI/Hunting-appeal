"""H1: the adopted printed frame body (owner, docs/DECISIONS.md 2026-11-10; judge: analysis/frame_comp_verdict.md).

H1 = today's PAHT-CF branch body, locally re-sized with team D's fully-stressed SDF offset
(``frame_comp_d.offset_step``), with team A's member size floors (``frame_comp_A`` primitives) and A's branch
Euler buckling rule, fairleads and pads restored every step (``frame_comp_d.restore_hardpoints``), printed face
down on the home H2S in two halves joined DRY at z 234 with 4 Ti M5 through-bolts in printed bosses.

Nothing is copied from the team modules: geometry primitives, solver, failure rule, re-sizing step and buckling cuts
are imported. New here:
- the z 234 joint geometry (4 bolt bosses, fitted bolt holes, side-access nut + washer traps, head counterbores),
  added to the voxel model and to the print mesh;
- the joint check: rigid-face no-tension contact + bolt springs on the real cut section of every rev C set,
  washer bearing, plug shear-out, boss bending with prying (missing from team A), bolt tension / fatigue,
  fitted-bolt shear bearing, contact bearing;
- bore continuity across the split for the sliding crown leg (ligaments, leg travel, ream-through);
- re-meshed print files (smooth field + exact booleans with manifold3d), lay-flat halves, GLB.

Record: designs/pack_5200/analysis/frame_h1.md. Print package: designs/pack_5200/print/frame_h1/.
Run (about 15 min on 2 cores):  python -m huntkit.gendesign.frame_h1 all
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import frame_comp_A as A
from . import frame_comp_d as D

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "frame_h1"
PRINT_DIR = REPO / "designs" / "pack_5200" / "print" / "frame_h1"
DOC = REPO / "designs" / "pack_5200" / "analysis" / "frame_h1.md"
RESULT = REPO / "designs" / "pack_5200" / "analysis" / "frame_h1_results.json"
MASS_JSON = REPO / "designs" / "pack_5200" / "analysis" / "frame_mass_h1.json"
SCREENS = REPO / "outputs" / "screens"
GLB_DIR = REPO / "outputs" / "pack3d_h1"
H = 2.0
MAT = "paht_fdm"

# ------------------------------------------------------------------------------------------------ re-sizing setup
# Judge's continuation of D's tool (frame_comp_verdict.md section 1): local radius cap 0.45, thin below 0.85 x target,
# branches held at D's control section (buckling), fairleads and pads restored every iterate.
R_FRAC = 0.45
U_LO = 0.85
ITERS = 6
KEEP = 1.02            # ASSUMPTION (D FAT_KEEP / weight_c C-9): 2 % reserve for 2 mm voxel / FI99 noise
BUCKLE_KEEP = 1.0      # A's rule: P_cr >= 1.5 x factored compression, margin >= 1
# Team A's floors (frame_comp_A.MIN_SCALE comment): printed radius >= 5 mm on branches, struts, mid bar; foot ball
# >= 8.4 mm (hinge-pin boss and boot fit). Expressed as A primitive scales (A radii 6.2 / 7.5 / 6.5 / 12.0 mm).
FLOOR = A.Body(foot=8.4 / 12.0, branch=5.0 / 6.2, strut=5.0 / 7.5, mid=5.0 / 6.5, name="floors")
FLOOR_GROUPS = ("foot", "branch", "strut", "mid")
SLEEVE_WALL_FLOOR = 3.6   # A: bushing seat wall over the 18.0 mm reamed bore


# ------------------------------------------------------------------------------------------------ joint geometry
@dataclass
class Joint:
    """Dry z 234 joint, per stay: two M5 Ti through-bolts parallel to the stay axis at local positions ``xy``
    (x outboard, y aft, about the bore axis). The bosses never stand proud of the wearer face (XLPE rails), stand
    proud of the bag face only outboard of the spreader edge (x > 121), stay inside the bag envelope and end below
    the z 255-265 spreader clip (boss_envelope). Upper half: head + washer in an open counterbore.
    Lower half: washer + nut in a side-access trap (nut held by its flats). Bolt holes reamed 5.1 mm: the fitted
    bolts take the shear (no dowels)."""
    z: float = 234.0
    e: float = 19.0            # bolt axis to bore axis, mm
    theta_deg: float = 15.0
    r_boss: float = 8.0        # washer 12 / 2 + 2 mm wall
    z_lo: float = 198.0        # boss extent (capsule ends)
    z_hi: float = 252.0        # 3 mm below the z 255-265 spreader clip
    head_face: float = 250.0   # head washer bears here (upper plug 16 mm)
    nut_face: float = 212.0    # nut washer bears here (lower plug 22 mm)
    hole_d: float = 5.1        # printed 4.8, reamed 5.1 (fitted M5)
    washer_od: float = 12.0    # M5 x 12 x 1.0 washer (both ends)
    washer_t: float = 1.0
    nut_af: float = 8.0
    nut_t: float = 4.0
    tail_z: float = 202.0      # bolt tail clearance bottom
    bolt_len: float = 45.0     # M5 x 45 Ti gr5 low head DIN 7984 (grip 38 + 2 washers + nut 4 + 1)
    head_h: float = 3.5        # DIN 7984 low head (ISO 4762 is 5.0 and would reach 1 mm into the z 255 clip band)
    head_d: float = 8.5
    torque_nm: float = 1.0     # snug: ASSUMPTION preload ~1 kN (K 0.2), not credited
    # chosen layout (joint search, frame_h1.md section 3): outboard-aft bolt proud of the bag face but outboard of
    # the spreader edge; inboard-aft bolt inside the stay silhouette, its boss merging into the branch root
    xy: tuple | None = ((16.4, 10.0), (-19.0, 5.0))
    # nut-trap opening per bolt (local x outboard, y aft); None = radially out. The inboard trap opens toward the
    # wearer face so it does not cut the branch root.
    trap_dirs: tuple | None = (None, (0.0, -1.0))

    @property
    def slot_w(self):          # washer slot width
        return self.washer_od + 0.4

    @property
    def cbore_d(self):         # head + washer counterbore
        return self.washer_od + 0.4

    @property
    def L_upper(self):
        return self.head_face - self.z

    @property
    def L_lower(self):
        return self.z - self.nut_face

    def bolts_local(self) -> np.ndarray:
        """(2, 2) local (x outboard, y aft) bolt positions about the bore axis."""
        if self.xy is not None:
            return np.array(self.xy, float)
        t = math.radians(self.theta_deg)
        p = np.array([self.e * math.cos(t), self.e * math.sin(t)])
        return np.array([p, -p])

    def trap_dir(self, k: int) -> np.ndarray:
        bx, by = self.bolts_local()[k]
        d = None if self.trap_dirs is None else self.trap_dirs[k]
        v = np.array([bx, by]) if d is None else np.array(d, float)
        return v / np.linalg.norm(v)

    def radii(self) -> np.ndarray:
        return np.hypot(*self.bolts_local().T)


JOINT = Joint()


def _axis(z):
    from .frame_topopt import load_envelope
    env = load_envelope()
    return env, float(env.sleeve_y(z))


def bolt_axes(j: Joint = JOINT) -> list:
    """Bolt axes in frame coordinates: list of (side sx, k, base point at z_lo, unit axis)."""
    env, _ = _axis(j.z)
    slope = env.axis_slope
    u = np.array([0.0, slope, 1.0]) / math.sqrt(1 + slope ** 2)
    out = []
    for sx in (1.0, -1.0):
        for k, (bx, by) in enumerate(j.bolts_local()):
            p = np.array([sx * (115.0 + bx), float(env.sleeve_y(j.z)) + by, j.z])
            out.append((sx, k, p, u))
    return out


def _seg_dist(pts, a, b):
    ab = b - a
    t = np.clip(((pts - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(pts - (a + t[:, None] * ab), axis=1)


def boss_sdf(pts: np.ndarray, j: Joint = JOINT) -> np.ndarray:
    """Union of the 4 boss capsules (radius r_boss, ends rounded = tapered blend)."""
    d = np.full(len(pts), 80.0)
    for sx, k, p, u in bolt_axes(j):
        a = p + u * (j.z_lo + j.r_boss - j.z)
        b = p + u * (j.z_hi - j.r_boss - j.z)
        d = np.minimum(d, _seg_dist(pts, a, b) - j.r_boss)
    return d


def _local(pts, p, u, sx):
    """Coordinates about a bolt axis: s along the axis (0 at z = joint), radial unit (outward from the bore)."""
    rel = pts - p
    s = rel @ u
    return s, rel - s[:, None] * u


def hole_mask(pts: np.ndarray, j: Joint = JOINT) -> np.ndarray:
    """Voids of the joint: bolt holes, head counterbores (open upward), washer + nut traps (open radially out)."""
    void = np.zeros(len(pts), bool)
    for sx, k, p, u in bolt_axes(j):
        s, rad = _local(pts, p, u, sx)
        z = j.z + s
        r = np.linalg.norm(rad, axis=1)
        void |= (r < j.hole_d / 2) & (z > j.tail_z) & (z < j.head_face)
        void |= (r < j.cbore_d / 2) & (z >= j.head_face) & (z < j.z_hi + 20.0)
        # trap: direction pointing radially out from the bore axis through the bolt
        dx, dy = j.trap_dir(k)
        dirn = np.array([sx * dx, dy, 0.0])
        tang = np.array([-dirn[1], dirn[0], 0.0])
        a = rad @ dirn           # along the open direction (+ = out)
        b = rad @ tang
        w_lo, w_hi = j.nut_face - j.washer_t - 0.2, j.nut_face
        n_lo = w_lo - j.nut_t - 0.4
        a_hi = j.r_boss + 6.0
        washer = (z > w_lo) & (z <= w_hi) & (np.abs(b) < j.slot_w / 2) & (a > -j.slot_w / 2) & (a < a_hi)
        nut = ((z > n_lo) & (z <= w_lo) & (np.abs(b) < j.nut_af / 2 + 0.1) & (a > -(j.nut_af / 2 + 0.1))
               & (a < a_hi))
        void |= washer | nut
    return void


# ------------------------------------------------------------------------------------------------ body assembly
_CACHE: dict = {}


def base():
    """Domain, today's solid, the layout SDF, D's PAHT-CF control (shift + solid), group of every element."""
    if "dom" in _CACHE:
        return _CACHE
    from .spreader import SCALE
    from .spreader_layout import frame_sdf_layout, raster
    dom, solid0 = raster(None, H)
    cen = dom.grid.elem_centers()
    sdf0 = frame_sdf_layout(cen, None, SCALE)
    npz = D.SCRATCH / "paht_fdm_run2_best.npz"
    if not npz.exists():                       # D's control run (about 10 min)
        D.run2(mats=("paht_fdm",))
    z = np.load(npz)
    grp = np.full(dom.grid.ne, -1)
    near = np.where(dom.design() | dom.passive_solid)[0]
    near = near[A.body_sdf(cen[near], A.Body()) < 25.0]
    grp[near] = A.group_of(cen[near], A.Body())
    ctrl = z["solid"]
    floor = np.zeros(dom.grid.ne, bool)
    P = A.parts_sdf(cen[near], FLOOR)
    for gname in FLOOR_GROUPS:
        floor[near[P[gname] <= 0.0]] = True
    floor &= ~dom.passive_void
    boss = (boss_sdf(cen) <= 0.0) & ~dom.passive_void
    from scipy import ndimage
    g = dom.grid
    pads = g.from_array(ndimage.binary_dilation(g.to_array(np.asarray(dom.masks["pads"], bool)), iterations=3))
    pad_zone = pads & solid0          # today's material within 6 mm of every pad: keeps the pads attached
    holes = hole_mask(cen)
    _CACHE.update(dom=dom, solid0=solid0, sdf0=sdf0, cen=cen, shift0=z["shift"].astype(float), ctrl=ctrl, grp=grp,
                  branch_ctrl=ctrl & (grp == A.GROUPS.index("branch")), floor=floor, boss=boss, holes=holes, pad_zone=pad_zone,
                  solid0c=__import__("huntkit.gendesign.frame_production", fromlist=["x"])._largest_with_pivot(dom, solid0))
    return _CACHE


def assemble(shift: np.ndarray, joint: bool = True) -> np.ndarray:
    """H1 solid for a cumulative surface shift: D offset body + restored fairleads/pads + held branches + A floors
    + joint bosses - joint holes; keep-outs re-imposed; largest connected part with the pivot."""
    from . import frame_production as prod
    c = base()
    dom = c["dom"]
    s = D.solid_from_shift(dom, c["sdf0"], shift)
    s = D.restore_hardpoints(dom, c["solid0"], s) | c["branch_ctrl"] | c["floor"] | c["pad_zone"]
    if joint:
        s = (s | c["boss"]) & ~c["holes"]
    s &= ~dom.passive_void
    s |= dom.passive_solid & ~c["holes"] if joint else dom.passive_solid
    return prod._largest_with_pivot(dom, s)


# ------------------------------------------------------------------------------------------------ checks
def buckling(fields: dict, E: float | None = None) -> dict:
    """Team A's branch / mid-bar Euler rule (frame_comp_A.member_buckling: K 1, E x 0.6 hot x 0.7 creep,
    P_cr >= 1.5 x factored compression) evaluated on the stresses of an existing solve."""
    m = A.MATS["paht_rec"]
    E = E or m.E_xy * m.E_hot * 0.7
    c = base()
    idx, cen = fields["idx"], fields["cen"]
    grp = c["grp"][idx]
    out = {}
    for name, (gname, ax, cc, L) in A.BUCKLE_CUTS.items():
        lay = (grp == A.GROUPS.index(gname)) & (np.abs(cen[:, ax] - (cc + H / 2)) <= H / 2 + 1e-6)
        sides = {"all": lay} if ax == 0 else {"L": lay & (cen[:, 0] < 0), "R": lay & (cen[:, 0] > 0)}
        for sd, msk in sides.items():
            A_ = float(msk.sum() * H * H)
            r = math.sqrt(A_ / math.pi)
            pcr = math.pi ** 2 * E * (math.pi * r ** 4 / 4) / L ** 2
            nmin, where = 0.0, ""
            for S, mt in zip(fields["stress"], fields["meta"]):
                N = float(S[msk, ax].astype(float).sum() * H * H)
                if N < nmin:
                    nmin, where = N, mt["set"]
            P = -nmin
            out[f"{name} {sd}"] = {"A_mm2": A_, "r_eq_mm": round(r, 2), "L_mm": L, "Pcr_n": round(pcr),
                                   "P_factored_n": round(P), "set": where,
                                   "margin": round(pcr / (1.5 * P), 3) if P > 0 else None}
    return out


def by_torso(ev: dict) -> dict:
    """Strength minimum per torso and couple variant, fatigue and creep per torso (static carry sets)."""
    m = D.MATERIALS[MAT]
    out = {}
    for r in ev["rows"]:
        k = f"{r['scenario']}|{int(r['torso'])}"
        o = out.setdefault(k, {"strength": 9e9, "fatigue": 9e9, "creep": 9e9, "gov": ""})
        # loads are factored, so sf (= 1 / FI99) is the margin; fatigue / creep as frame_cg_recheck.summarize_body
        if r["sf"] < o["strength"]:
            o["strength"], o["gov"] = r["sf"], f"{r['case']} ({r['where']})"
        if r["case"] == "static_carry":
            fi_1g = r["fi99"] / r["factor"]
            o["fatigue"] = min(o["fatigue"], m["fat"] / (fi_1g * D.FAT_G))
            o["creep"] = min(o["creep"], m["rup"] / fi_1g)
    return {k: {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in o.items()} for k, o in out.items()}


def keepouts(solid: np.ndarray) -> dict:
    """Interface keep-outs: every fixed interface voxel present, bores and spine channel empty, fairleads intact,
    nothing outside the envelope, bosses inside the stay silhouette fore/aft and clear of the spreader clips."""
    from .bag_attach import attachment_field
    from .spreader import SCALE
    from .spreader import CLIP_Z, CLIP_W
    c = base()
    dom, cen = c["dom"], c["cen"]
    out = {}
    for k in ("sleeve_R", "sleeve_L", "pawl", "pivot", "pads"):
        m = np.asarray(dom.masks[k], bool) & ~c["holes"] & c["solid0c"]    # as present in today's printed body
        out[f"{k} present"] = float((solid & m).sum() / max(m.sum(), 1))
    for k in ("bore_R", "bore_L", "spine_channel"):
        m = np.asarray(dom.masks[k], bool)
        out[f"{k} empty"] = float(1.0 - (solid & m).sum() / max(m.sum(), 1))
    fl = (attachment_field(cen, SCALE) <= 0.0) & ~dom.passive_void
    out["fairleads present"] = float((solid & fl).sum() / max(fl.sum(), 1))
    out["outside envelope (voxels)"] = int((solid & dom.passive_void).sum())
    j = JOINT
    env, yc = _axis(j.z)
    bl = j.bolts_local()
    for k, v in boss_envelope(j).items():
        out[k] = v
    clip_lo = min(z - CLIP_W / 2 for z in CLIP_Z if z > j.z)
    out["boss top z / next spreader clip bottom z"] = [j.z_hi, clip_lo]
    out["boss clear of spreader clip"] = bool(j.z_hi <= clip_lo)
    head_top = j.head_face + j.washer_t + j.head_h
    out["bolt head top z"] = head_top
    out["bolt head clear of spreader clip"] = bool(head_top <= clip_lo)
    out["boss max |x| mm (half-width limit 152)"] = float(115.0 + max(abs(bl[:, 0])) + j.r_boss)
    return out


SPREADER_HALF_W = 121.0   # Sandwich v2 242 mm wide (print/frame/PRODUCTION.md), centred on the frame


def boss_envelope(j: Joint = JOINT) -> dict:
    """Where the bosses may go at z 234: never proud of the stay on the wearer face (the 10 mm XLPE rails sit there);
    proud of the stay on the bag face only outboard of the spreader edge and inside the bag envelope y_hi."""
    from .spreader import SCALE
    env, yc = _axis(j.z)
    r_out = 9.0 + 4.2 * SCALE
    y_bag = float(env.y_hi(j.z)) - yc - 0.5
    ok_wearer, ok_bag, ok_x = True, True, True
    for bx, by in j.bolts_local():
        if by - j.r_boss < -(r_out + 0.2):
            ok_wearer = False
        if by + j.r_boss > r_out + 0.2:
            if 115.0 + bx - j.r_boss < SPREADER_HALF_W + 0.5 or by + j.r_boss > y_bag:
                ok_bag = False
        if 115.0 + abs(bx) + j.r_boss > 151.0:
            ok_x = False
    return {"boss wearer face flush (rails)": ok_wearer, "boss bag side outboard of spreader and inside envelope": ok_bag,
            "boss inside x half-width 152": ok_x, "stay outer radius at z 234 mm": r_out,
            "bag envelope local y at z 234 mm": y_bag,
            "boss local extents (x, y) mm": [[round(bx, 1), round(by - j.r_boss, 1), round(by + j.r_boss, 1)]
                                             for bx, by in j.bolts_local()]}


def bore_continuity(j: Joint = JOINT) -> dict:
    """Bore across the dry split: ligaments from every joint void to the 18.0 mm reamed bore; the sliding crown leg
    (UHMWPE low bushing 70 mm on its bottom end) crosses z 234 at which torso settings; alignment method."""
    from .frame_topopt import SLEEVE_BORE_R, load_envelope
    env = load_envelope()
    # sample the joint voids on a 0.2 mm grid at each feature height; ligament = nearest void point to the bore wall
    _, yc = _axis(j.z)
    g = np.arange(-40.0, 40.0, 0.2)
    X, Y = np.meshgrid(g, g)
    lig = {}
    for nm, zz in (("bolt_hole", 0.5 * (j.z + j.nut_face)), ("washer_trap", j.nut_face - 0.5),
                   ("nut_trap", j.nut_face - j.washer_t - 2.5), ("counterbore", j.head_face + 2.0)):
        pts = np.c_[115.0 + X.ravel(), yc + Y.ravel(), np.full(X.size, zz)]
        m = hole_mask(pts, j)
        r = np.hypot(X.ravel()[m], Y.ravel()[m])
        lig[nm] = float(r.min() - SLEEVE_BORE_R) if m.any() else 99.0
    hole_lig, trap_lig, cb_lig = lig["bolt_hole"], min(lig["washer_trap"], lig["nut_trap"]), lig["counterbore"]
    legs = {}
    for t in (15, 19, 23):
        zb = env.leg_bottom_z(t)
        legs[str(t)] = {"leg_bottom_z": round(zb, 1), "bushing_span_z": [round(zb, 1), round(zb + 70.0, 1)],
                        "leg_crosses_z234": bool(zb < j.z), "bushing_over_joint": bool(zb <= j.z <= zb + 70.0)}
    return {"bolt_hole_ligament_mm": hole_lig, "trap_ligament_mm": trap_lig, "counterbore_ligament_mm": cb_lig,
            "wall_floor_mm": SLEEVE_WALL_FLOOR, "min_ligament_margin": min(hole_lig, trap_lig, cb_lig) / SLEEVE_WALL_FLOOR,
            "legs": legs,
            "alignment": "bolts in 5.1 mm reamed (fitted) holes locate the halves to about +-0.05 mm; the 18.0 mm "
                         "bore is reamed THROUGH both halves after bolt-up, so the leg and its bushing see one "
                         "continuous bore (step 0 by construction). Halves become a matched pair (mark them).",
            "step_allowed_mm": 0.1}


# ------------------------------------------------------------------------------------------------ joint mechanics
PAHT = {"s_xy": 88.0, "s_z": 47.0, "knock": 0.8, "fat": 0.30, "E": 3860.0, "E_hot": 0.6}
TI = {"E": 110000.0, "uts": 895.0, "As": 14.2, "d_minor": 4.13}    # B: ASTM F136 / ISO 898 stress area
PRYING = 1.25          # ASSUMPTION (team B): prying factor on bolt tension for a boss next to the wall
L_CONTACT = 10.0       # ASSUMPTION: effective compressed length of printed material under the dry face, mm


def cut_sections(fields: dict, j: Joint = JOINT) -> dict:
    """Per set and side: the layer of elements just below z 234 as (local x outboard, local y aft, sigma_zz,
    tau_zx, tau_yz) about the bore axis."""
    cen, idx = fields["cen"], fields["idx"]
    lay = np.abs(cen[:, 2] - (j.z - H / 2)) < H / 2 + 1e-6
    _, yc = _axis(j.z)
    out = {}
    for sd, sx in (("R", 1.0), ("L", -1.0)):
        m = lay & (np.sign(cen[:, 0]) == sx)
        lx = sx * (cen[m, 0] - sx * 115.0)
        ly = cen[m, 1] - yc
        out[sd] = {"x": lx, "y": ly, "rows": []}
        for S, mt in zip(fields["stress"], fields["meta"]):
            s = S[m].astype(float)
            out[sd]["rows"].append({**mt, "szz": s[:, 2], "tzx": sx * s[:, 5], "tyz": s[:, 4]})
    return out


def contact_solve(x, y, area, N, Mx, My, bolts, kb, kc):
    """Rigid dry face, no tension in the contact, bolts as tension-only springs (no preload credited).
    Opening d = a + bx x + by y. Equilibrium with the transmitted N (tension +), Mx = sum F y, My = sum F x.
    Active-set iteration (exact for this piecewise-linear problem). Returns bolt forces (N), peak contact pressure
    (MPa) and the equilibrium residual (N)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    area = np.broadcast_to(np.asarray(area, float), x.shape)
    P = np.c_[np.ones_like(x), x, y]
    Bp = np.c_[np.ones(len(bolts)), np.asarray(bolts, float)]
    tgt = np.array([N, My, Mx])
    wc, wb = kc * area, np.full(len(bolts), float(kb))
    act_c, act_b = np.ones(len(x), bool), np.ones(len(bolts), bool)
    q = np.zeros(3)
    for _ in range(200):
        K = (P[act_c].T * wc[act_c]) @ P[act_c] + (Bp[act_b].T * wb[act_b]) @ Bp[act_b]
        K += np.eye(3) * 1e-12 * max(np.trace(K), 1.0)
        q = np.linalg.solve(K, tgt)
        new_c, new_b = P @ q < 0.0, Bp @ q > 0.0
        if not new_c.any() and not new_b.any():
            new_c = np.ones(len(x), bool)
        if (new_c == act_c).all() and (new_b == act_b).all():
            break
        act_c, act_b = new_c, new_b
    d, db = P @ q, Bp @ q
    fc = wc * np.minimum(d, 0.0)
    fb = wb * np.maximum(db, 0.0)
    res = np.array([fc.sum() + fb.sum(), (fc * x).sum() + (fb * Bp[:, 1]).sum(),
                    (fc * y).sum() + (fb * Bp[:, 2]).sum()]) - tgt
    return {"bolt_n": fb, "contact_mpa": float(np.max(-fc / area)) if len(fc) else 0.0,
            "resid_n": float(np.abs(res).max())}


def boss_bending_fi(T: float, j: Joint = JOINT, L: float | None = None, k: int = 0) -> float:
    """Boss as a cantilever from the stay wall (root at r_out) to the bolt line, depth L along the stay (the plug
    between washer face and split), width 2 r_boss; bending stress along the radial direction at theta in the
    print plane (layer normal frame y). Failure index by the release layer rule (frame_topopt.layer_failure_index)."""
    from .frame_topopt import layer_failure_index
    from .spreader import SCALE
    L = L or min(j.L_upper, j.L_lower)
    bx, by = j.bolts_local()[k]
    a = max(math.hypot(bx, by) - (9.0 + 4.2 * SCALE), 0.0)
    sig = 6.0 * T * a / (2 * j.r_boss * L ** 2)
    n = np.array([bx, by]) / math.hypot(bx, by)
    S = np.zeros((1, 6))
    S[0, 0], S[0, 1], S[0, 3] = sig * n[0] ** 2, sig * n[1] ** 2, sig * n[0] * n[1]
    return float(layer_failure_index(np.abs(S[:, :3]), np.abs(S[:, 3:]), 1, PAHT["s_xy"], PAHT["s_z"], PAHT["knock"])[0])


def joint_capacities(j: Joint = JOINT) -> dict:
    k = PAHT["knock"]
    ring = math.pi / 4 * (j.washer_od ** 2 - j.hole_d ** 2)
    L = min(j.L_upper, j.L_lower)
    return {"washer_bearing_n": ring * k * PAHT["s_xy"],                       # load along frame z: in the layers
            "plug_shear_out_n": 2 * L * j.washer_od * 0.6 * k * PAHT["s_z"],  # A's 2-plane rule, interlayer shear
            "bolt_tension_n": 0.7 * TI["uts"] * TI["As"],                     # B rule
            "bolt_fatigue_n": 0.25 * TI["uts"] * TI["As"],                    # B rule, rolled thread R~0
            "hole_bearing_n": j.hole_d * L * k * PAHT["s_xy"],               # fitted bolt in shear, per bolt
            "bolt_shear_n": 0.6 * TI["uts"] * math.pi / 4 * TI["d_minor"] ** 2,
            "contact_mpa": k * PAHT["s_xy"]}


def joint_check(fields: dict | None, j: Joint = JOINT, secs: dict | None = None) -> dict:
    """Every rev C set, both sides: bolt forces from the contact solve; static margins at the factored load,
    fatigue at 1.6 g from the static-carry sets (x 1.6 / factor). ``secs`` (from cut_sections) skips the solve."""
    secs = secs if secs is not None else cut_sections(fields, j)
    bolts = j.bolts_local()
    kb = TI["E"] * TI["As"] / (j.head_face - j.nut_face + 2 * j.washer_t)
    kc = PAHT["E"] * PAHT["E_hot"] / L_CONTACT
    cap = joint_capacities(j)
    worst: dict = {}
    branch_t = {"max_tension_n": 0.0, "set": ""}

    def keep(kind, name, val, where):
        if (kind, name) not in worst or val < worst[(kind, name)][0]:
            worst[(kind, name)] = (val, where)

    for sd, sec in secs.items():
        x, y = sec["x"], sec["y"]
        area = np.full(len(x), H * H)
        is_branch = (np.hypot(x, y) > 21.0) & (np.min(np.hypot(x[:, None] - bolts[:, 0], y[:, None] - bolts[:, 1]),
                                                       axis=1) > j.r_boss + 1.0)
        for r in sec["rows"]:
            Fz = r["szz"] * H * H
            N, Mx, My = Fz.sum(), (Fz * y).sum(), (Fz * x).sum()
            V = math.hypot((r["tzx"] * H * H).sum(), (r["tyz"] * H * H).sum())
            Tq = float(((x * r["tyz"] - y * r["tzx"]) * H * H).sum())
            nb = float(Fz[is_branch].sum())
            if nb > branch_t["max_tension_n"]:
                branch_t = {"max_tension_n": nb, "set": f"{r['set']} {sd}"}
            cs = contact_solve(x, y, area, N, Mx, My, bolts, kb, kc)
            Tk = cs["bolt_n"] * PRYING
            Tb = float(Tk.max())
            where = f"{r['set']} {sd}"
            nb_ = len(bolts)
            Vb = V / nb_ + abs(Tq) / (nb_ * float(j.radii().mean()))
            bfi = max(boss_bending_fi(float(t_), j, k=k_) for k_, t_ in enumerate(Tk))
            rows_ = [("washer bearing (XY)", cap["washer_bearing_n"], Tb),
                     ("plug shear-out (interlayer)", cap["plug_shear_out_n"], Tb),
                     ("bolt tension Ti (0.7 UTS)", cap["bolt_tension_n"], Tb),
                     ("fitted-bolt hole bearing (shear)", cap["hole_bearing_n"], Vb),
                     ("bolt shear Ti", cap["bolt_shear_n"], Vb),
                     ("dry-face contact bearing", cap["contact_mpa"], cs["contact_mpa"])]
            for nm, c_, d_ in rows_:
                keep("strength", nm, c_ / max(d_, 1e-9), where)
            keep("strength", "boss bending + prying (layer FI)", 1.0 / max(bfi, 1e-9), where)
            if r["case"] == "static_carry":
                kf = D.FAT_G / r["factor"]
                f = PAHT["fat"]
                for nm, c_, d_ in rows_[:2] + rows_[3:4]:
                    keep("fatigue", nm + " at 1.6 g", f * c_ / max(d_ * kf, 1e-9), where)
                keep("fatigue", "bolt thread Ti at 1.6 g (0.25 UTS)", cap["bolt_fatigue_n"] / max(Tb * kf, 1e-9), where)
                keep("fatigue", "boss bending + prying at 1.6 g", f / max(bfi * kf, 1e-9), where)
            keep("info", "max bolt force (factored, with prying) N", 1e6 / max(Tb, 1e-9), where)
    out = {"strength": {}, "fatigue": {}}
    for (kind, nm), (v, wh) in worst.items():
        if kind == "info":
            out["max_bolt_force_n"] = {"value": round(1e6 / v), "set": wh}
            continue
        out[kind][nm] = {"margin": round(v, 3), "set": wh}
    out["min_strength"] = min(v["margin"] for v in out["strength"].values())
    out["min_fatigue"] = min(v["margin"] for v in out["fatigue"].values())
    out["capacities_n"] = {k: round(v, 1) for k, v in cap.items()}
    out["branch_axial_across_split"] = branch_t
    out["design"] = asdict(j)
    out["assumptions"] = [f"prying factor {PRYING} (team B)", f"contact length {L_CONTACT} mm, hot E",
                          "no preload credited (snug 1 N m; PAHT creep relaxes it)",
                          "bolt-group from the real z 234 voxel cut (stay + bosses + branch) as a rigid face"]
    return out


# ------------------------------------------------------------------------------------------------ the run
def _eval(solid, log=print, sections=False):
    from .frame_cg_recheck import region_label  # noqa: F401  (D.evaluate uses it)
    c = base()
    sets, _ = D.load_sets(log=None)
    f = D.solve_fields(c["dom"], solid, sets, log=None)
    ev = D.evaluate(f, MAT)
    return f, ev


def push(log=print) -> dict:
    """D's offset tool continued (judge settings) with A's floors and the joint bosses in the model every step.
    Each iterate: 42 sets (strength / fatigue / creep) + A's branch buckling on the same solve."""
    import gc
    c = base()
    D.R_FRAC = R_FRAC
    shift = c["shift0"].copy()
    hist, best = [], None
    for it in range(ITERS + 1):
        solid = assemble(shift)
        t0 = time.time()
        f, ev = _eval(solid)
        bk = buckling(f)
        bmin = min(v["margin"] for v in bk.values() if v["margin"] is not None)
        rec = {"it": it, "raster_g": D.mass_g(solid, H, 1060.0), "min": ev["min"], "buckling_min": bmin,
               "gov": ev["governing"], "s": round(time.time() - t0)}
        ok = min(ev["min"].values()) >= KEEP and bmin >= BUCKLE_KEEP
        rec["pass"] = bool(ok)
        hist.append(rec)
        if log:
            log(json.dumps(rec, default=float))
        if ok and (best is None or rec["raster_g"] < best["raster_g"]):
            best = {**rec, "shift": shift.copy()}
        if it == ITERS:
            break
        util = ev["util"]
        del f, ev
        gc.collect()
        shift = D.offset_step(c["dom"], c["sdf0"], solid, util, shift, 1.04, grow_only=False, u_lo=U_LO)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "h1_shift.npz", shift=best["shift"], it=best["it"])
    (OUT / "push.json").write_text(json.dumps(hist, indent=1, default=float))
    return {"history": hist, "best_it": best["it"]}


def verify(log=print) -> dict:
    """Final H1 body: all rev C checks on one solve, plus the variants."""
    c = base()
    shift = np.load(OUT / "h1_shift.npz")["shift"]
    solid = assemble(shift)
    f, ev = _eval(solid)
    bk = buckling(f)
    jc = joint_check(f)
    tor = by_torso(ev)
    m40 = dict(D.MATERIALS[MAT], fat=0.40)
    D.MATERIALS["paht_fat040"] = m40
    ev40 = D.evaluate(f, "paht_fat040")
    sets, _ = D.load_sets(log=None)
    k_today = D.torsion_k(c["dom"], c["solid0"], sets, 3860.0)
    k_h1 = D.torsion_k(c["dom"], solid, sets, 3860.0)
    # family masses (A groups), floors and joint contribution
    grp = c["grp"]
    fam = {g: round(float(((grp == i) & solid).sum() * H ** 3 * 1.06e-3), 1) for i, g in enumerate(A.GROUPS)}
    np.savez_compressed(OUT / "h1_final.npz", solid=solid, util=ev["util"])
    out = {
        "date": "2026-11-10", "material": "PAHT-CF (pa12_cf_fdm_paht), layer normal frame y",
        "raster_g": D.mass_g(solid, H, 1060.0), "today_raster_g": D.mass_g(c["solid0"], H, 1060.0),
        "boss_raster_g": D.mass_g(solid & c["boss"] & ~D.restore_hardpoints(c["dom"], c["solid0"],
                                                                           D.solid_from_shift(c["dom"], c["sdf0"], shift)),
                                  H, 1060.0),
        "floor_added_g": D.mass_g(solid & c["floor"] & ~D.solid_from_shift(c["dom"], c["sdf0"], shift), H, 1060.0),
        "family_g": fam,
        "min": ev["min"], "governing": ev["governing"], "body": ev["body"], "by_torso": tor,
        "fatigue_at_0.40": ev40["min"]["fatigue"],
        "ca1_flip_ratio": round(D.MATERIALS[MAT]["fat"] / ev["min"]["fatigue"], 3),
        "buckling": bk, "buckling_min": min(v["margin"] for v in bk.values() if v["margin"] is not None),
        "joint": jc, "keepouts": keepouts(solid), "bore": bore_continuity(),
        "torsion_vs_today": k_h1 / k_today,
    }
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    if log:
        log(json.dumps({k: out[k] for k in ("raster_g", "min", "buckling_min", "fatigue_at_0.40")}, default=float))
        log(json.dumps({"joint_strength": jc["min_strength"], "joint_fatigue": jc["min_fatigue"]}))
    return out


# ------------------------------------------------------------------------------------------------ mass booking
FIXED_G = 239.4        # verdict basis: crown (rev C), rack, pawl, bushings, Ti mount, inserts (no dowels)
SPREADER_G = 162.3
PACK_REST_G = 2739.5   # CORRIE B.2 belt M without frame + spreader (verdict section 2)
TODAY_BODY_G = 823.2
TODAY_DOWELS_G = 18.5  # 8 x 5 x 70 mm carbon dowels 17.0 + MMA 1.5 (verdict section 2)


def hardware_g(j: Joint = JOINT) -> dict:
    from .frame_comp_B import bolt_mass_g
    nut = (3 * math.sqrt(3) / 2 * (j.nut_af / math.sqrt(3)) ** 2 - math.pi / 4 * 5.0 ** 2) * j.nut_t * 7.9e-3
    washer = math.pi / 4 * (j.washer_od ** 2 - 5.3 ** 2) * j.washer_t * 7.9e-3
    return {f"4 Ti gr5 M5 x {j.bolt_len:.0f} DIN 7984 (ISO 4762 head mass, conservative)": 4 * bolt_mass_g(j.bolt_len), "4 A2 M5 hex nuts ISO 4032": 4 * nut,
            "8 A2 M5 x 12 x 1 washers": 8 * washer}


def mass_booking(res: dict, mesh_g: dict | None = None) -> dict:
    body_g = TODAY_BODY_G - (res["today_raster_g"] - res["raster_g"])   # on today's 823.2 g basis
    hw = hardware_g()
    frame = FIXED_G + body_g + sum(hw.values())
    today = FIXED_G + TODAY_BODY_G + TODAY_DOWELS_G
    out = {
        "date": "2026-11-10",
        "basis": "frame_comp_verdict.md section 2: fixed interfaces 239.4 g, spreader 162.3 g, pack rest 2739.5 g; "
                 "body booked as 823.2 - (today raster - H1 raster) on the same 2 mm raster",
        "today_corrected": {"body_g": TODAY_BODY_G, "fixed_g": FIXED_G, "z234_dowels_mma_g": TODAY_DOWELS_G,
                            "frame_g": round(today, 1), "frame_plus_spreader_g": round(today + SPREADER_G, 1),
                            "corrie_b2_M_g": round(today + SPREADER_G + PACK_REST_G, 1),
                            "note": "frame_mass_production.json frame_g 1062.6 omits the 8 z 234 dowels + MMA"},
        "h1": {"body_g": round(body_g, 1), "body_incl_bosses_note": "the 4 bosses are inside the body raster",
               "boss_g": round(res["boss_raster_g"], 1), "floors_added_g": round(res["floor_added_g"], 1),
               "fixed_g": FIXED_G, "joint_hardware_g": {k: round(v, 2) for k, v in hw.items()},
               "dowels_g": 0.0, "frame_g": round(frame, 1), "frame_plus_spreader_g": round(frame + SPREADER_G, 1),
               "corrie_b2_M_g": round(frame + SPREADER_G + PACK_REST_G, 1),
               "delta_vs_today_g": round(frame - today, 1)},
    }
    if mesh_g:
        out["h1"]["print_mesh_g"] = mesh_g
    MASS_JSON.write_text(json.dumps(out, indent=1))
    return out


# ------------------------------------------------------------------------------------------------ print mesh
def _ring(p_axis, u, r_in, r_out, z0, z1, seg=96):
    from .surface import _to_manifold
    import trimesh
    outer = trimesh.creation.cylinder(radius=r_out, height=z1 - z0, sections=seg)
    inner = trimesh.creation.cylinder(radius=r_in, height=z1 - z0 + 2.0, sections=seg)
    return _place(_to_manifold(outer) - _to_manifold(inner), p_axis, u, 0.5 * (z0 + z1))


def _place(man, p, u, zmid):
    """Move a z-aligned manifold (centred at the origin) onto an axis through p (at z = p[2]) direction u."""
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, u)
    s, cth = np.linalg.norm(v), float(z @ u)
    R = np.eye(3)
    if s > 1e-12:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - cth) / s ** 2)
    c = p + u * (zmid - p[2]) / u[2]
    M = np.eye(4)[:3]
    M[:, :3] = R
    M[:, 3] = c
    return man.transform(M)


def _cyl(r, z0, z1, p, u, seg=48):
    import manifold3d as m3d
    return _place(m3d.Manifold.cylinder(z1 - z0, r, r, seg, center=True), p, u, 0.5 * (z0 + z1))


def _box_local(p, u, dirn, along0, along1, half_w, z0, z1):
    """Box in the bolt frame: radial 'dirn' from along0 to along1, tangential +-half_w, z0..z1."""
    import manifold3d as m3d
    tang = np.cross(u, dirn)
    b = m3d.Manifold.cube((along1 - along0, 2 * half_w, z1 - z0), center=True)
    R = np.column_stack([dirn, tang, u])
    c = p + u * (0.5 * (z0 + z1) - p[2]) / u[2] + dirn * 0.5 * (along0 + along1)
    M = np.eye(4)[:3]
    M[:, :3] = R
    M[:, 3] = c
    return b.transform(M)


SIMPLIFY_MM = 0.04     # manifold3d simplify tolerance: about 45 % fewer faces, volume change < 0.1 %


def print_mesh(solid: np.ndarray, j: Joint = JOINT, log=print):
    """Smooth surface of the voxel body (2x upsampled field, Taubin), then exact features with manifold3d:
    boss capsules, sleeve bore rings re-cut at the 17.4 mm pre-ream size, bolt holes 4.8 mm (ream 5.1),
    counterbores, washer + nut traps."""
    import manifold3d as m3d
    from .surface import _from_manifold, _to_manifold, field_to_mesh
    from scipy import ndimage
    c = base()
    dom = c["dom"]
    body = solid & ~c["boss"]                        # bosses are added as exact solids
    field = ndimage.zoom(dom.grid.to_array(body.astype(float)), 2, order=1)
    field = ndimage.gaussian_filter(field, 0.7)
    mesh = field_to_mesh(field, dom.h / 2, dom.grid.x0 - dom.h / 4, level=0.5, smooth_iters=10, upsample=1)
    man = _to_manifold(mesh)
    if man.status() != m3d.Error.NoError if hasattr(m3d, "Error") else False:
        raise RuntimeError("body surface is not manifold")
    env, _ = _axis(j.z)
    slope = env.axis_slope
    u = np.array([0.0, slope, 1.0]) / math.sqrt(1 + slope ** 2)
    feats = []
    for sx in (1.0, -1.0):
        p = np.array([sx * 115.0, float(env.sleeve_y(j.z)), j.z])
        feats.append(("ring", _ring(p, u, 8.0, 9.0 + 4.2 * 1.05, 162.0, 543.0)))
    for sx, k, p, uu in bolt_axes(j):
        a = p + uu * (j.z_lo + j.r_boss - j.z)
        b = p + uu * (j.z_hi - j.r_boss - j.z)
        L = float(np.linalg.norm(b - a))
        cyl = m3d.Manifold.cylinder(L, j.r_boss, j.r_boss, 64, center=True)
        cap = m3d.Manifold.sphere(j.r_boss, 64)
        caps = cyl + cap.translate((0, 0, L / 2)) + cap.translate((0, 0, -L / 2))
        feats.append(("boss", _place(caps, p, uu, 0.5 * (j.z_lo + j.z_hi))))
    for kind, f in feats:
        man = man + f
    cuts = []
    for sx in (1.0, -1.0):
        p = np.array([sx * 115.0, float(env.sleeve_y(j.z)), j.z])
        cuts.append(_cyl(8.7, 155.0, 560.0, p, u, 96))             # print 17.4, ream 18.0
    for sx, k, p, uu in bolt_axes(j):
        dx, dy = j.trap_dir(k)
        dirn = np.array([sx * dx, dy, 0.0])
        dirn = dirn - uu * (dirn @ uu)
        dirn /= np.linalg.norm(dirn)
        cuts.append(_cyl(2.4, j.tail_z, j.head_face + 1.0, p, uu))   # print 4.8, ream 5.1
        cuts.append(_cyl(j.cbore_d / 2, j.head_face, j.z_hi + 20.0, p, uu))
        w_lo = j.nut_face - j.washer_t - 0.2
        n_lo = w_lo - j.nut_t - 0.4
        cuts.append(_box_local(p, uu, dirn, 0.0, j.r_boss + 6.0, j.slot_w / 2, w_lo, j.nut_face))
        cuts.append(_cyl(j.slot_w / 2, w_lo, j.nut_face, p, uu))
        hexp = m3d.Manifold.cylinder(w_lo - n_lo, j.nut_af / math.sqrt(3) + 0.12, j.nut_af / math.sqrt(3) + 0.12,
                                     6, center=True)
        cuts.append(_place(hexp, p, uu, 0.5 * (w_lo + n_lo)))
        cuts.append(_box_local(p, uu, dirn, 0.0, j.r_boss + 6.0, j.nut_af / 2 + 0.1, n_lo, w_lo))
    for cc in cuts:
        man = man - cc
    man = man.simplify(SIMPLIFY_MM)
    out = _from_manifold(man)
    if log:
        log(f"  print mesh: {len(out.faces)} faces, watertight {out.is_watertight}, {out.volume / 1000:.1f} cm3")
    return out


FLAT_R = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])   # frame y -> print z (wearer face, min y, on the plate)


def lay_flat(mesh):
    m = mesh.copy()
    T = np.eye(4)
    T[:3, :3] = FLAT_R
    m.apply_transform(T)
    m.apply_translation(-m.bounds[0])
    return m


def export_print(log=print) -> dict:
    import trimesh
    from .frame_topopt import split_mesh
    solid = np.load(OUT / "h1_final.npz")["solid"]
    mesh = print_mesh(solid, log=log)
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    mesh.export(PRINT_DIR / "h1_assembled.stl")
    lo, hi = split_mesh(mesh, JOINT.z)
    info = {"assembled": {"faces": len(mesh.faces), "volume_cm3": mesh.volume / 1000, "g": mesh.volume * 1.06e-3,
                          "watertight": bool(mesh.is_watertight)}}
    for nm, m in (("lower", lo), ("upper", hi)):
        f = lay_flat(m)
        f.export(PRINT_DIR / f"h1_{nm}_flat.stl")
        try:
            f.export(PRINT_DIR / f"h1_{nm}_flat.3mf")
        except Exception as e:  # pragma: no cover
            info[f"{nm}_3mf_error"] = str(e)
        info[nm] = {"faces": len(f.faces), "volume_cm3": round(f.volume / 1000, 1), "g": round(f.volume * 1.06e-3, 1),
                    "footprint_mm": [round(v, 1) for v in f.extents], "watertight": bool(f.is_watertight),
                    "fits_h2s_340x320x340": bool(sorted(f.extents)[-1] <= 340 and sorted(f.extents)[-2] <= 320)}
    # GLB + assembled STL for the pack viewers (frame coordinates -> glTF, huntkit.viz3d.export convention)
    from huntkit.viz3d.export import M_FCS_TO_GLTF
    GLB_DIR.mkdir(parents=True, exist_ok=True)
    mesh.export(GLB_DIR / "genframe_assembled.stl")
    g = mesh.copy()
    T = np.eye(4)
    T[:3, :3] = M_FCS_TO_GLTF
    g.apply_transform(T)
    if np.linalg.det(M_FCS_TO_GLTF) < 0:
        g.invert()
    g.visual = trimesh.visual.ColorVisuals(g, face_colors=[60, 60, 58, 255])
    parts = [("h1_body", g)]
    for sx, k, p, uu in bolt_axes():
        b = trimesh.creation.cylinder(radius=2.5, height=JOINT.bolt_len)
        b.apply_translation((0, 0, 0))
        R = np.eye(4)
        R[:3, 3] = p + uu * ((JOINT.head_face - JOINT.bolt_len / 2) - p[2])
        b.apply_transform(R)
        hd = trimesh.creation.cylinder(radius=JOINT.head_d / 2, height=JOINT.head_h)
        hd.apply_translation(p + uu * ((JOINT.head_face + JOINT.washer_t + JOINT.head_h / 2) - p[2]))
        bb = trimesh.util.concatenate([b, hd])
        bb.apply_transform(T)
        if np.linalg.det(M_FCS_TO_GLTF) < 0:
            bb.invert()
        bb.visual = trimesh.visual.ColorVisuals(bb, face_colors=[150, 150, 155, 255])
        parts.append((f"ti_bolt_{'R' if sx > 0 else 'L'}{k}", bb))
    sc = trimesh.Scene()
    for nm, m in parts:
        sc.add_geometry(m, node_name=nm, geom_name=nm)
    (GLB_DIR / "h1_frame.glb").write_bytes(trimesh.exchange.gltf.export_glb(sc, include_normals=True))
    (GLB_DIR / "README.md").write_text(
        "# H1 frame for the 3D pack views\n\n"
        "- `h1_frame.glb`: H1 printed body + 4 Ti bolts, glTF axes (huntkit.viz3d.export.M_FCS_TO_GLTF: metres, "
        "frame z -> glTF y). Drop-in for the frame node of the pack GLBs.\n"
        "- `genframe_assembled.stl`: same body in frame coordinates (mm). Point `generative_frame_dir` in the "
        "viz3d params at this folder to swap it into `huntkit.viz3d.model`.\n"
        "Source: `huntkit/gendesign/frame_h1.py`, record `designs/pack_5200/analysis/frame_h1.md`.\n")
    (OUT / "print_info.json").write_text(json.dumps(info, indent=1, default=float))
    return info


# ------------------------------------------------------------------------------------------------ figures
def plot_util(res: dict, path: Path) -> str:
    np.savez_compressed(OUT / "_util_plot.npz", **dict(np.load(OUT / "h1_final.npz")))
    D.plot_utilisation(OUT / "_util_plot.npz",
                       f"H1 PAHT-CF body {mass_booking(res)['h1']['body_g']:.0f} g: utilisation, worst of 42 rev C sets "
                       f"(S {res['min']['strength']:.2f}  F {res['min']['fatigue']:.2f}  C {res['min']['creep']:.2f})",
                       path)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


def plot_joint(res: dict, path: Path) -> str:
    """z 234 cut: section voxels, bolts, bosses, bore, and the joint margins as bars."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = base()
    solid = np.load(OUT / "h1_final.npz")["solid"]
    cen = c["cen"]
    j = JOINT
    _, yc = _axis(j.z)
    lay = solid & (np.abs(cen[:, 2] - (j.z - 1.0)) < 1.01) & (cen[:, 0] > 0)
    fig, ax = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw={"width_ratios": [1, 1.25]})
    p = cen[lay]
    ax[0].scatter(p[:, 0] - 115, p[:, 1] - yc, marker="s", s=38, c="#5d5a54", label="H1 cut at z 234 (R stay)")
    t = np.linspace(0, 2 * np.pi, 100)
    ax[0].plot(9 * np.cos(t), 9 * np.sin(t), "k-", lw=1.2, label="18.0 mm reamed bore")
    for k, (bx, by) in enumerate(j.bolts_local()):
        ax[0].plot(bx + j.r_boss * np.cos(t), by + j.r_boss * np.sin(t), "-", c="#d9480f", lw=1.5,
                   label="boss" if k == 0 else None)
        ax[0].plot(bx + j.washer_od / 2 * np.cos(t), by + j.washer_od / 2 * np.sin(t), ":", c="#2b6cb0",
                   label="washer 12" if k == 0 else None)
        ax[0].plot(bx, by, "o", c="#2b6cb0")
    ax[0].set_aspect("equal")
    ax[0].set_xlabel("x outboard from the stay axis, mm")
    ax[0].set_ylabel("y aft (bag side) mm")
    ax[0].legend(fontsize=8, loc="lower right")
    ax[0].set_title("Dry z 234 joint, right stay (left mirrored)")
    jc = res["joint"]
    names, vals, cols = [], [], []
    for kind, col in (("strength", "#2b6cb0"), ("fatigue", "#d9480f")):
        for nm, v in jc[kind].items():
            names.append(f"{kind[0].upper()}: {nm}")
            vals.append(min(v["margin"], 6.0))
            cols.append(col)
    y = np.arange(len(names))
    ax[1].barh(y, vals, color=cols)
    for k, v in enumerate(vals):
        ax[1].text(v + 0.05, k, f"{v:.2f}", va="center", fontsize=8)
    ax[1].axvline(1.0, color="k", lw=1)
    ax[1].set_yticks(y, names, fontsize=8)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("margin (capacity / demand), pass >= 1 (bars capped at 6)")
    ax[1].set_title(f"Joint margins, 42 sets; max bolt force {jc['max_bolt_force_n']['value']} N")
    fig.tight_layout()
    fig.savefig(path, dpi=95)
    plt.close(fig)
    from .weight_c import shrink
    shrink(path, 1_500_000)
    return str(path)


def plot_push(path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hist = json.loads((OUT / "push.json").read_text())
    g = [h["raster_g"] for h in hist]
    fig, ax = plt.subplots(figsize=(8, 5))
    for key, mk in (("strength", "o-"), ("fatigue", "s-")):
        ax.plot(g, [h["min"][key] for h in hist], mk, label=key)
    ax.plot(g, [h["buckling_min"] for h in hist], "^-", label="branch buckling (A rule)")
    for h in hist:
        ax.annotate(f"it{h['it']}", (h["raster_g"], h["min"]["fatigue"]), textcoords="offset points",
                    xytext=(3, -12), fontsize=8)
    ax.axhline(1.0, color="r", lw=1)
    ax.set_xlabel("H1 body raster g (PAHT-CF, bosses and floors included)")
    ax.set_ylabel("min margin over 42 rev C sets")
    ax.set_title("H1 re-sizing (D offset tool + A floors + joint bosses)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)
    return str(path)


BPY = ("/tmp/claude-0/-home-user-Hunting-appeal/4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/scratchpad/bpyenv/bin/python")


def render(out_png: Path, files: list, cap: str, sub: str, az=160.0, el=12.0, zoom=1.0, samples=24,
           floor_z: float | None = None) -> str:
    import os
    import subprocess
    work = OUT / "render"
    work.mkdir(parents=True, exist_ok=True)
    mf = work / f"{out_png.stem}.json"
    mf.write_text(json.dumps({"files": files, **({"floor_z": floor_z} if floor_z is not None else {})}))
    env = dict(os.environ, OMP_NUM_THREADS="2")
    code = (f"import sys; sys.path.insert(0, {str(REPO)!r}); from huntkit.viz3d import frame_pair_render as R; "
            "R.main(sys.argv[1:])")
    r = subprocess.run(["nice", "-n", "10", os.environ.get("HUNTKIT_BPY", BPY), "-c", code,
                        str(mf), str(out_png), str(samples), cap, sub, str(az), str(el), str(zoom)],
                       capture_output=True, text=True, timeout=3600, env=env)
    if r.returncode != 0 or "RENDERED" not in r.stdout:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    return str(out_png)


def render_all(res: dict) -> list:
    import trimesh
    from .frame_light2_render import _cyl as tcyl
    from .frame_branch import _sleeve_y
    work = OUT / "render"
    work.mkdir(parents=True, exist_ok=True)
    h1 = trimesh.load(PRINT_DIR / "h1_assembled.stl")
    dx = 380.0
    today = trimesh.load(REPO / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    today.apply_translation((dx, 0, 0))
    today.export(work / "today.stl")
    h1.export(work / "h1.stl")
    y_top = float(_sleeve_y(540.0))
    files = [{"path": str(work / "h1.stl"), "mat": "printed"}, {"path": str(work / "today.stl"), "mat": "today"}]
    for nm, off in (("h1_carbon", 0.0), ("today_carbon", dx)):
        parts = [tcyl((sx * 115 + off, y_top, 420.0), (sx * 113 + off, y_top + 4, 760.0), 8.0) for sx in (-1, 1)]
        parts.append(tcyl((-113 + off, y_top + 4, 760.0), (113 + off, y_top + 4, 760.0), 9.0))
        parts.append(tcyl((off, y_top - 18, 560.0), (off, y_top - 2, 760.0), 10.0))
        trimesh.util.concatenate(parts).export(work / f"{nm}.stl")
        files.append({"path": str(work / f"{nm}.stl"), "mat": "carbon"})
    bolts = []
    for sx, k, p, uu in bolt_axes():
        b = trimesh.creation.cylinder(radius=2.5, height=JOINT.bolt_len)
        b.apply_translation(p + uu * ((JOINT.head_face - JOINT.bolt_len / 2) - p[2]))
        hd = trimesh.creation.cylinder(radius=JOINT.head_d / 2, height=JOINT.head_h)
        hd.apply_translation(p + uu * ((JOINT.head_face + JOINT.washer_t + JOINT.head_h / 2) - p[2]))
        bolts += [b, hd]
    trimesh.util.concatenate(bolts).export(work / "bolts.stl")
    files.append({"path": str(work / "bolts.stl"), "mat": "ti"})
    mb = mass_booking(res)
    shots = []
    p1 = SCREENS / "20261110_h1_1.png"
    render(p1, files, f"H1 (left, {mb['h1']['body_g']:.0f} g body) vs today (right, 823 g)",
           f"PAHT-CF, dry z 234 joint with 4 Ti M5 bolts in bosses; frame {mb['h1']['frame_g']:.0f} g vs "
           f"{mb['today_corrected']['frame_g']:.0f} g (dowels booked)", az=160.0, el=12.0, zoom=1.0)
    shots.append(str(p1))
    # close-up of the joint (H1 only, crop z 150-320)
    crop = h1.slice_plane((0, 0, 170.0), (0, 0, 1)).slice_plane((0, 0, 300.0), (0, 0, -1))
    crop.export(work / "h1_crop.stl")
    p2 = SCREENS / "20261110_h1_2.png"
    render(p2, [{"path": str(work / "h1_crop.stl"), "mat": "printed"}, {"path": str(work / "bolts.stl"), "mat": "ti"}],
           "H1 z 234 dry joint: 4 bolt bosses (2 per stay)",
           "outboard-aft boss outside the spreader edge, inboard boss into the branch root; wearer face flush", az=215.0, el=22.0, zoom=1.0, floor_z=160.0)
    shots.append(str(p2))
    return shots


def run_all(log=print):
    push(log=log)
    res = verify(log=log)
    info = export_print(log=log)
    mb = mass_booking(res, mesh_g={k: info[k]["g"] for k in ("lower", "upper") if k in info})
    shots = [plot_util(res, SCREENS / "20261110_h1_3.png"), plot_joint(res, SCREENS / "20261110_h1_4.png"),
             plot_push(SCREENS / "20261110_h1_5.png")]
    return {"res": res, "print": info, "mass": mb, "shots": shots}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        push()
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify()
    elif len(sys.argv) > 1 and sys.argv[1] == "export":
        print(json.dumps(export_print(), indent=1, default=float))
    elif len(sys.argv) > 1 and sys.argv[1] == "render":
        print(render_all(json.loads(RESULT.read_text())))
    else:
        print(json.dumps(run_all(), default=float)[:2000])
