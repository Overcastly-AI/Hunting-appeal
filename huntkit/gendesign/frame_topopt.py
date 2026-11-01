"""Whole-frame generative design: ONE topology-optimized, 3D-printed frame body (owner 2026-11-01).

What is optimized
- The FIXED frame (everything below the crown): stays, cross bars, lumbar pan, hubs, foot boots and the
  hip-pivot seat become one printed body, in the 3D envelope between the wearer's back panel and the
  bag's frame-side panel (geometry.yaml). The telescoping crown (carbon legs + top bar + spine, frame v2)
  is KEPT and slides in printed sleeves moulded into the body (decision in printed_frame_study.md).
- Design domain (FCS, mm): x in [-152, 152], y in [Y_LO, bag frame-side panel - 1 mm], z in [0, 544].
- Non-design SOLID: crown-leg sleeves (bore 18 mm = leg OD 16 + UHMWPE bushing; printed wall), the
  hip-pivot boss (Ti insert seat), the pawl housing around the spine channel, and pads at every bag /
  harness / internal-strap anchor, load-wing lash point, pulley guide, cam buckle and stay foot.
- Non-design VOID: the leg bores, the crown-spine channel (spine + rack travel 296..544), the bag
  (y above the frame-side panel) and the back-pad clearance (y < Y_LO).

Loads (HA-LS-1 rev B, all 9 cases at torso 15 / 19 / 23 in)
- The v2 tube-frame beam model (huntkit.fea.pack5200 via frame.yaml) is solved for every case; every
  external load, body-spring reaction and d'Alembert load on a FIXED-frame node, plus the crown link
  forces (top bushing, leg-end bushing, pawl) are the loads on the printed body. The hipbelt pivot is the
  clamp (it takes the hipbelt reaction; every other reaction is applied as a load). Applied loads go on
  the bag-side face, body reactions on the wearer-side face, bushing forces on the sleeve ring at the
  bushing height; nodal moments (bag CG offset) are spread over a 50 mm patch as F/n + omega x r.
- Every set is multiplied by its HA-LS-1 required factor (stress <= allowable is the check).

Optimization (huntkit.gendesign.simp machinery, extended here)
- SIMP p = 3, hat density filter (minimum member size), Heaviside projection continuation, x-mirror
  symmetry (design variables and sensitivities averaged with the mirror image), multi-load weighted
  compliance (weights 1 / c_i at the start so every case counts), OC update, AMG-PCG.
- Coarse-to-fine: h = 8 mm (all 21 distinct load sets) -> trilinear prolongation -> h = 4 mm (the sets
  carrying >= 97 % of the weighted compliance, all re-checked at verification).
- Stress: p-norm (p = 8) von Mises over every factored load set is evaluated on the verified design;
  the stress constraint is enforced in an outer loop over the volume fraction (volume minimization subject
  to p-norm stress <= allowable, solved by interpolation over a volume-fraction sweep, per material). For a
  single linear isotropic material the stress field does not depend on E, so one sweep serves every material.
- Optional embedded 1D reinforcement (pultruded CF rods or continuous-fiber print paths) as bar elements
  on voxel nodes (``rods``), included in the SIMP stiffness and in the verification.

Verification
- The density field is up-sampled 2x (h = 2 mm), thresholded at 0.5, passive solids re-imposed, the largest
  connected body kept, and re-solved as an independent solid-voxel FE model for ALL 27 load sets
  (element-centre stresses, 99th-percentile von Mises excluding the clamp and load-patch elements).
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from huntkit.fea.materials_bridge import REPO_ROOT

from .fem import Grid, b_h8_center, density_filter, iso_D3, ke_h8, von_mises_3d
from .lugs import distribute
from .simp import _project

GEOMETRY = REPO_ROOT / "designs" / "pack_5200" / "geometry.yaml"
FRAME_YAML = REPO_ROOT / "designs" / "pack_5200" / "frame.yaml"
TORSOS = (15, 19, 23)

X_HALF = 152.0
Y_LO = -48.0           # ASSUMPTION: back-pad clearance (hip-pivot face y -48.1; back panel foam + mesh behind it)
Y_HI_GRID = 16.0
Z_TOP = 544.0
SLEEVE_BORE_R = 9.0    # crown leg OD 16 + 1 mm UHMWPE bushing wall
SLEEVE_WALL = 2.5      # printed sleeve wall (min wall FDM 2 mm, SLS 1.5 mm)
SLEEVE_Z0 = 160.0      # leg-end bushing reaches z 171 at the 15 in setting
NU = 0.35
PATCH_R = 12.0
MOMENT_PATCH_R = 50.0
PAD_R = 6.0


# ============================================================================= envelope
@dataclass
class Envelope:
    hp: dict
    bag_z: np.ndarray
    bag_y: np.ndarray
    crown_settings: list
    axis_slope: float            # dy/dz of the crown axis
    top_pt: np.ndarray           # stay-top crown socket (R)
    strap_z: dict

    def y_hi(self, z):
        return np.interp(z, self.bag_z, self.bag_y) - 1.0

    def sleeve_y(self, z):
        return self.top_pt[1] + self.axis_slope * (np.asarray(z, float) - self.top_pt[2])

    def leg_bottom_z(self, torso_in: float) -> float:
        cs = min(self.crown_settings, key=lambda c: abs(c["torso_in"] - torso_in))
        uz = 1.0 / np.sqrt(1 + self.axis_slope ** 2)
        return float(cs["crown_top_z"] - 430.0 * uz)


def load_envelope(path=GEOMETRY) -> Envelope:
    import yaml

    from huntkit.fea.pack5200 import strap_levels
    g = yaml.safe_load(Path(path).read_text())
    fr = g["frame"]
    st = np.array(g["bag"]["profile"]["stations"], float)
    bag_z, bag_y = st[:, 0], st[:, 2]
    bag_z = np.r_[0.0, bag_z]
    bag_y = np.r_[bag_y[0], bag_y]
    uy, uz = fr["members_topology"]["crown"]["axis_unit_vector_yz"]
    return Envelope(hp={k: np.asarray(v, float) for k, v in fr["hard_points"].items()},
                    bag_z=bag_z, bag_y=bag_y, crown_settings=fr["crown_settings"], axis_slope=uy / uz,
                    top_pt=np.asarray(fr["hard_points"]["stay_top_crown_socket_R"], float),
                    strap_z=strap_levels(fr))


def pad_points(env: Envelope) -> dict:
    """Hard points that become solid pads (right side listed; mirrored in build_domain)."""
    hp = env.hp
    pts = {}
    for k in ("bag_anchor_low_R", "bag_anchor_mid_R", "hip_stabilizer_anchor_R", "shoulder_strap_lower_anchor_R",
              "load_wing_lash_z80_R", "load_wing_lash_z250_R", "load_wing_lash_z420_R", "pulley_fixed_guide_C",
              "pulley_cam_buckle_R"):
        if k in hp:
            pts[k] = hp[k]
    for lvl, z in env.strap_z.items():                      # internal meat-strap anchors (rev B)
        pts[f"internal_{lvl}_R"] = np.array([115.0, env.y_hi(z) - 6.0, z])
    pts["stay_foot_R"] = np.array([115.0, -6.0, 6.0])
    return pts


# ============================================================================= domain
@dataclass
class Domain:
    grid: Grid
    env: Envelope
    passive_solid: np.ndarray
    passive_void: np.ndarray
    mirror: np.ndarray            # element index of the x-mirror element
    masks: dict = field(default_factory=dict)   # named element masks (sleeve_R, pivot, ...)

    @property
    def h(self):
        return self.grid.h

    def design(self):
        return ~(self.passive_solid | self.passive_void)


def build_domain(h: float = 4.0, env: Envelope | None = None, sleeve_wall: float = SLEEVE_WALL) -> Domain:
    env = env or load_envelope()
    nx = int(round(2 * X_HALF / h))
    ny = int(round((Y_HI_GRID - Y_LO) / h))
    nz = int(round(Z_TOP / h))
    g = Grid((nx, ny, nz), h, x0=np.array([-X_HALF, Y_LO, 0.0]))
    c = g.elem_centers()
    x, y, z = c.T
    void = (y > env.y_hi(z)) | (y < Y_LO)
    solid = np.zeros(g.ne, bool)
    masks = {}
    # crown sleeves (both sides) and bores
    half = max(h / 2, 0.5)
    for s, tag in ((1, "R"), (-1, "L")):
        dy = y - env.sleeve_y(z)
        dx = x - s * env.top_pt[0]
        r = np.hypot(dx, dy)
        inz = (z >= SLEEVE_Z0) & (z <= Z_TOP)
        bore = inz & (r < SLEEVE_BORE_R)
        wall = inz & (r >= SLEEVE_BORE_R) & (r < SLEEVE_BORE_R + max(sleeve_wall, half))
        masks[f"bore_{tag}"] = bore
        masks[f"sleeve_{tag}"] = wall
        solid |= wall
        void |= bore
    # crown-spine channel (spine 30 x 3 + rack, travel 296..544) and the pawl housing around it
    ch = (np.abs(x) < 20.0) & (y > -34.0) & (y < -16.0) & (z > 296.0)
    pawl = (np.abs(x) < 25.0) & (y > -39.0) & (y < -11.0) & (z > 506.0) & (z < 536.0) & ~ch
    void |= ch
    solid |= pawl
    masks["spine_channel"] = ch
    masks["pawl"] = pawl
    # hip-pivot boss (Ti insert seat, axis along y)
    pv = env.hp["hipbelt_pivot"]
    piv = (np.hypot(x - pv[0], z - pv[2]) < 16.0) & (y > Y_LO - 1) & (y < pv[1] + 20.0)
    solid |= piv
    masks["pivot"] = piv
    # pads
    padm = np.zeros(g.ne, bool)
    for name, p in pad_points(env).items():
        for s in (1, -1):
            q = np.array([s * p[0], p[1], p[2]])
            q[1] = np.clip(q[1], Y_LO + PAD_R, env.y_hi(q[2]) - PAD_R * 0.5)
            m = np.linalg.norm(c - q, axis=1) < max(PAD_R, 1.01 * h)
            padm |= m
    solid |= padm
    masks["pads"] = padm
    void &= ~solid | np.isin(np.arange(g.ne), [])     # solids win over the envelope ...
    for tag in ("R", "L"):                                 # ... except the bores and the spine channel
        void |= masks[f"bore_{tag}"]
        solid &= ~masks[f"bore_{tag}"]
    void |= ch
    solid &= ~ch
    void |= (y > env.y_hi(z) + 6.0)                        # pads may not poke into the bag
    solid &= ~void
    # mirror map
    ijk = g.eijk.copy()
    ijk[:, 0] = nx - 1 - ijk[:, 0]
    mirror = np.ravel_multi_index(tuple(ijk.T), g.shape, order="F")
    return Domain(g, env, solid, void, mirror, masks)


# ============================================================================= loads from the beam model
@dataclass
class LoadSet:
    key: str
    case: str
    torso: float
    factor: float
    g: float
    kg: float
    items: list                  # (point(3), F6, side) side: "bag" | "body" | "point"
    bushings: list               # (side tag "L"/"R", z, F3)
    pawl: np.ndarray
    resid: float = 0.0


FIXED_PREFIX = ("S", "P", "MB", "UB", "HP")


def _is_fixed_node(nid: str) -> bool:
    if nid in ("SP150",) or nid.startswith("SP"):
        return False
    return nid.startswith(FIXED_PREFIX)


def beam_loadsets(torsos=TORSOS, frame_yaml=FRAME_YAML, cases=None, log=print) -> list[LoadSet]:
    """Interface loads on the fixed frame for every HA-LS-1 case x torso (beam model of frame.yaml)."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import TABLE, ls1_cases
    cases = cases or ls1_cases()
    out = []
    for t in torsos:
        fm = build_frame_from_yaml(frame_yaml, torso_in=float(t), extension_posts=False)
        fmp = None
        for c in cases:
            c = copy.copy(c)
            c.buckling = False
            m = fm
            if c.name == "tall_load_posts":
                fmp = fmp or build_frame_from_yaml(frame_yaml, torso_in=float(t), extension_posts=True)
                m = fmp
            res = c.run(m)
            out.append(_extract(res, m, c, t, TABLE))
        if log:
            log(f"  beam model: {len(cases)} cases at torso {t} in")
    return out


def _extract(res, model, case, torso, table) -> LoadSet:
    nodes = model["nodes"]
    items = []
    loads = res.model.get("loads") or {}
    fi = res.meta.get("inertia_forces")
    tot = np.zeros(3)
    for nid in nodes:
        if not _is_fixed_node(nid) or nid == "HP":
            continue
        p = np.asarray(nodes[nid], float)
        if nid in loads:
            v = np.zeros(6); v[: len(loads[nid])] = loads[nid]
            if np.any(v):
                items.append((p, v, "bag")); tot += v[:3]
        if nid in res.reactions and np.any(res.reactions[nid]):
            items.append((p, np.asarray(res.reactions[nid], float), "body")); tot += res.reactions[nid][:3]
        if fi is not None:
            i = res.node_ids.index(nid)
            v = fi[6 * i: 6 * i + 6]
            if np.any(v):
                items.append((p, np.asarray(v, float), "bag")); tot += v[:3]
    lf = res.meta.get("link_forces", {})
    bush, pawl = [], np.zeros(3)
    for ln in model.get("links", []):
        a, b = ln["nodes"]
        f = lf.get(ln["id"])
        if f is None:
            continue
        # huntkit.fea.frame stores k (u_b - u_a): the force the link exerts ON node a (the fixed-frame
        # node: stay / UB1); node b (crown) gets the opposite
        fa = np.asarray(f[:3], float)
        za = nodes[a][2]
        if ln["id"].startswith("bush"):
            bush.append(("L" if nodes[a][0] < 0 else "R", float(za), fa))
        elif ln["id"] == "pawl":
            pawl = pawl + fa
        tot += fa
    g, req, kg = table[case.name]
    return LoadSet(key=f"{case.name}|{torso:g}", case=case.name, torso=float(torso), factor=float(req),
                   g=float(g), kg=float(kg), items=items, bushings=bush, pawl=pawl,
                   resid=float(np.linalg.norm(tot)))


SHAPES_FOR_OPT = ("drop_2p5g", "side_hill_torsion", "single_stay_setdown", "meat_straps", "tall_load",
                  "tall_load_posts", "hipbelt_off_abuse")   # static_carry = drop shape x 2/3; overload ~ meat shape


def assemble_loads(dom: Domain, sets: list[LoadSet], solid_mask=None):
    """(F (ndof, n) factored, fixed dof mask). The hip-pivot boss is clamped."""
    g, env = dom.grid, dom.env
    nc = g.node_coords()
    act_e = ~dom.passive_void if solid_mask is None else solid_mask
    act_n = np.zeros(g.nn, bool)
    act_n[np.unique(g.enodes[act_e])] = True
    y_hi_n = env.y_hi(nc[:, 2])
    # node sets
    pv = env.hp["hipbelt_pivot"]
    clamp = act_n & (np.hypot(nc[:, 0] - pv[0], nc[:, 2] - pv[2]) <= 16.0 + 1e-6) & (nc[:, 1] <= pv[1] + 20.0 + 1e-6)
    fixed = np.zeros(g.ndof, bool)
    for d in range(3):
        fixed[3 * np.where(clamp)[0] + d] = True
    # face nodes: the most aft (bag side) / most forward (body side) active node in each (x, z) column
    face_bag = np.zeros(g.nn, bool)
    face_body = np.zeros(g.nn, bool)
    sh = g.nshape
    A = act_n.reshape(sh, order="F")
    yy = nc[:, 1].reshape(sh, order="F")
    big = np.where(A, yy, -1e9)
    small = np.where(A, yy, 1e9)
    jmax = big.argmax(axis=1)
    jmin = small.argmin(axis=1)
    has = A.any(axis=1)
    for arr, jj in ((face_bag, jmax), (face_body, jmin)):
        F3 = np.zeros(sh, bool)
        ii, kk = np.nonzero(has)
        F3[ii, jj[ii, kk], kk] = True
        arr[:] = F3.reshape(-1, order="F")
    sleeve_n = {}
    for tag in ("L", "R"):
        e = dom.masks[f"sleeve_{tag}"] & act_e
        m = np.zeros(g.nn, bool)
        m[np.unique(g.enodes[e])] = True
        sleeve_n[tag] = m
    pawl_n = np.zeros(g.nn, bool)
    pawl_n[np.unique(g.enodes[dom.masks["pawl"] & act_e])] = True
    free_n = act_n & ~clamp

    def nearest_patch(p, cand, r):
        d = np.linalg.norm(nc[:, [0, 2]] - p[[0, 2]], axis=1)
        idx = np.where(cand & (d <= r))[0]
        rr = r
        while idx.size < 3:
            rr *= 1.4
            idx = np.where(cand & (d <= rr))[0]
            if rr > 400:
                break
        return idx

    def point_patch(p, r):
        d = np.linalg.norm(nc - p, axis=1)
        idx = np.where(free_n & (d <= r))[0]
        rr = r
        while idx.size < 4:
            rr *= 1.4
            idx = np.where(free_n & (d <= rr))[0]
        return idx

    F = np.zeros((g.ndof, len(sets)))
    for k, ls in enumerate(sets):
        f = np.zeros((g.nn, 3))
        for p, v, side in ls.items:
            has_m = np.linalg.norm(v[3:]) > 1e-6
            r = MOMENT_PATCH_R if has_m else PATCH_R
            q = p.copy()
            if side == "body":
                idx = nearest_patch(q, face_body & free_n, r)
            elif q[2] < 4.0:                                   # stay feet (set-down impact)
                idx = point_patch(np.array([q[0], -6.0, 6.0]), 14.0)
            else:
                idx = nearest_patch(q, face_bag & free_n, r)
            if idx.size == 0:
                continue
            f[idx] += distribute(nc, idx, v, origin=p)
        for tag, z, F3 in ls.bushings:
            m = sleeve_n[tag] & free_n & (np.abs(nc[:, 2] - min(z, Z_TOP - 18.0)) <= 20.0)
            idx = np.where(m)[0]
            if idx.size:
                f[idx] += F3 / idx.size
        if np.any(ls.pawl):
            idx = np.where(pawl_n & free_n)[0]
            if idx.size == 0:
                idx = point_patch(np.array([0.0, -24.4, 520.0]), 20.0)
            f[idx] += ls.pawl / idx.size
        F[:, k] = ls.factor * f.reshape(-1)
    F[fixed] = 0.0
    return F, fixed


# ============================================================================= rods / fibers (1D bars)
@dataclass
class Rod:
    p0: np.ndarray
    p1: np.ndarray
    area: float                  # mm^2
    E_ratio: float               # E_rod / E_matrix (stiffness relative to the voxel material)
    name: str = "rod"
    density: float = 1550.0


def rod_matrix(g: Grid, rods: list[Rod], act_n=None) -> tuple[sp.csr_matrix, list]:
    """Bar elements along each rod, snapped to the voxel node grid (consecutive distinct nodes)."""
    rows, cols, vals, info = [], [], [], []
    nc = g.node_coords()
    for rd in rods:
        L = np.linalg.norm(rd.p1 - rd.p0)
        n = max(2, int(np.ceil(L / (0.5 * g.h))) + 1)
        pts = rd.p0 + np.linspace(0, 1, n)[:, None] * (rd.p1 - rd.p0)
        ijk = np.clip(np.round((pts - g.x0) / g.h).astype(int), 0, np.array(g.nshape) - 1)
        ids = np.ravel_multi_index(tuple(ijk.T), g.nshape, order="F")
        keep = np.r_[True, ids[1:] != ids[:-1]]
        ids = ids[keep]
        segs = []
        for a, b in zip(ids[:-1], ids[1:]):
            d = nc[b] - nc[a]
            l = np.linalg.norm(d)
            e = d / l
            k = rd.E_ratio * rd.area / l * np.outer(e, e)
            da, db = 3 * a + np.arange(3), 3 * b + np.arange(3)
            for (r_, c_, s_) in ((da, da, 1), (db, db, 1), (da, db, -1), (db, da, -1)):
                rows.append(np.repeat(r_, 3)); cols.append(np.tile(c_, 3)); vals.append((s_ * k).ravel())
            segs.append((a, b, l))
        info.append({"name": rd.name, "nodes": ids, "segs": segs, "rod": rd})
    if not rows:
        return sp.csr_matrix((g.ndof, g.ndof)), info
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(g.ndof, g.ndof))
    return K, info


def eliminate(K: sp.csr_matrix, fixed: np.ndarray) -> sp.csr_matrix:
    d = sp.diags((~fixed).astype(float))
    return (d @ K @ d).tocsr()


# ============================================================================= reduced direct solver
class ReducedSystem:
    """K assembled over ACTIVE elements only and reduced to the free DOFs they touch (void and clamped DOFs
    dropped, not just pinned), solved with a sparse direct solver (MKL PARDISO via pypardiso, SPD, multi-RHS;
    scipy SuperLU fallback). One factorization per optimization iteration serves all load cases."""

    def __init__(self, g: Grid, active: np.ndarray, fixed: np.ndarray, KE: np.ndarray, rods: list | None = None):
        self.g = g
        self.ae = np.where(active)[0]
        ed = g.edof[self.ae]
        used = np.zeros(g.ndof, bool)
        used[ed.ravel()] = True
        free = used & ~fixed
        self.free = np.where(free)[0]
        gmap = -np.ones(g.ndof, np.int64)
        gmap[self.free] = np.arange(self.free.size)
        self.gmap = gmap
        led = gmap[ed]                                     # (nae, 24) reduced ids or -1
        nd = led.shape[1]
        r = np.repeat(led, nd, axis=1)
        c = np.tile(led, (1, nd))
        keep = (r >= 0) & (c >= 0) & (c >= r)              # upper triangle (SPD storage)
        n = self.free.size
        key = (r[keep].astype(np.int64) * n + c[keep])
        uniq, inv = np.unique(key, return_inverse=True)
        self.inv = inv.astype(np.int64)
        self.keep = keep
        self.rows = (uniq // n).astype(np.int32)
        self.cols = (uniq % n).astype(np.int32)
        self.n = n
        indptr = np.zeros(n + 1, np.int64)
        np.add.at(indptr, self.rows.astype(np.int64) + 1, 1)
        self.indptr = np.cumsum(indptr)
        self.ke = KE.ravel()
        self.Kr = None
        if rods:
            Kg = rod_matrix(g, rods)[0].tocoo()
            ok = (gmap[Kg.row] >= 0) & (gmap[Kg.col] >= 0)
            rr, cc, vv = gmap[Kg.row[ok]], gmap[Kg.col[ok]], Kg.data[ok]
            up = cc >= rr
            self.Kr = sp.csr_matrix((vv[up], (rr[up], cc[up])), shape=(n, n))

    def assemble(self, w_active: np.ndarray) -> sp.csr_matrix:
        vals = (w_active[:, None] * self.ke[None, :])[self.keep]
        data = np.bincount(self.inv, weights=vals, minlength=self.rows.size)
        K = sp.csr_matrix((data, self.cols, self.indptr), shape=(self.n, self.n))
        if self.Kr is not None:
            K = (K + self.Kr).tocsr()
        return K

    def solve(self, Ku: sp.csr_matrix, F: np.ndarray) -> np.ndarray:
        """Ku: upper-triangular reduced K. F: (ndof, m) global. Returns U (ndof, m) global."""
        Fr = F[self.free]
        try:
            import pypardiso
            s = pypardiso.PyPardisoSolver(mtype=2)
            Ku.sort_indices()
            Ur = s.solve(Ku, np.ascontiguousarray(Fr))
            s.free_memory(everything=True)
        except ImportError:                    # pragma: no cover
            import scipy.sparse.linalg as spla
            Kf = (Ku + sp.triu(Ku, 1).T).tocsc()
            Ur = spla.splu(Kf).solve(Fr)
        Ur = Ur.reshape(Fr.shape)
        U = np.zeros((self.g.ndof,) + F.shape[1:])
        U[self.free] = Ur
        return U

    def full(self, Ku):
        return (Ku + sp.triu(Ku, 1).T).tocsr()


# ============================================================================= SIMP (whole frame)
@dataclass
class FrameOpt:
    h: float
    volfrac: float
    x: np.ndarray
    xPhys: np.ndarray
    history: list
    keys: list
    seconds: float
    dom: Domain | None = None


def _phys(H, Hs, x, beta, ps, pv):
    xt = H @ x / Hs
    xp, dxp = _project(xt, beta)
    return np.where(ps, 1.0, np.where(pv, 0.0, xp)), dxp


def simp_frame(dom: Domain, F: np.ndarray, fixed: np.ndarray, volfrac: float, iters: int = 40,
               rmin_vox: float = 1.5, x0=None, beta_schedule=(1, 2, 4), beta_every: int = 12, penal: float = 3.0,
               rods: list | None = None, move: float = 0.15, weights=None, log=None, tol=1e-6,
               hist_cb=None) -> FrameOpt:
    g = dom.grid
    t0 = time.time()
    KE = ke_h8(g.h, 1.0, NU)
    ps, pv = dom.passive_solid, dom.passive_void & ~dom.passive_solid
    rs = ReducedSystem(g, ~pv, fixed, KE, rods)
    H, Hs = density_filter(g, rmin_vox)
    design = ~(ps | pv)
    nd = design.sum()
    Fm = F.copy(); Fm[fixed] = 0.0
    Emin = 1e-6
    x = np.where(ps, 1.0, np.where(pv, 0.0, volfrac)) if x0 is None else np.where(ps, 1.0, np.where(pv, 0.0, x0))
    beta_i = 0
    beta = beta_schedule[0]
    xPhys, dproj = _phys(H, Hs, x, beta, ps, pv)
    U = None
    w = None if weights is None else np.asarray(weights, float)
    hist = []
    mir = dom.mirror
    for it in range(1, iters + 1):
        E = Emin + xPhys ** penal * (1 - Emin)
        K = rs.assemble(E[rs.ae])
        U = rs.solve(K, Fm)
        ce_c = np.zeros((g.ne, Fm.shape[1]))
        for c in range(Fm.shape[1]):
            Ue = U[g.edof[rs.ae], c]
            ce_c[rs.ae, c] = np.einsum("ij,jk,ik->i", Ue, KE, Ue)
        comps = np.einsum("ij,ij->j", Fm, U)
        if w is None:
            w = 1.0 / np.maximum(comps, 1e-30)
            w = w / w.sum()
        ce = ce_c @ w
        comp = float(comps @ w)
        dc = -penal * xPhys ** (penal - 1) * (1 - Emin) * ce
        dc = np.where(design, dc * dproj, 0.0)
        dv = np.where(design, dproj, 0.0)
        dc = H.T @ (dc / Hs)
        dv = H.T @ (dv / Hs)
        dc = 0.5 * (dc + dc[mir])                      # mirror symmetry
        dv = 0.5 * (dv + dv[mir])
        dc = np.minimum(dc, -1e-30)
        dv = np.maximum(dv, 1e-30)
        l1, l2 = 1e-12, 1e12
        xd = x[design]
        Be = np.sqrt(-dc[design] / dv[design])
        while (l2 - l1) / (l1 + l2) > 1e-4:
            lm = np.sqrt(l1 * l2)
            xn = x.copy()
            xn[design] = np.clip(xd * Be / np.sqrt(lm), np.maximum(0.0, xd - move), np.minimum(1.0, xd + move))
            xp, _ = _phys(H, Hs, xn, beta, ps, pv)
            if xp[design].sum() / nd > volfrac:
                l1 = lm
            else:
                l2 = lm
        xn = 0.5 * (xn + xn[mir])
        ch = float(np.abs(xn - x).max())
        x = xn
        xPhys, dproj = _phys(H, Hs, x, beta, ps, pv)
        vol = float(xPhys[design].mean())
        rec = {"it": it, "h": g.h, "compliance": comp, "volume": vol, "change": ch, "beta": beta,
               "ndof": int(rs.n), "comps": comps.tolist()}
        hist.append(rec)
        if hist_cb:
            hist_cb(it, xPhys, rec)
        if log:
            log(f"   h{g.h:g} vf{volfrac:.3f} it {it:3d} c={comp:.4g} vol={vol:.3f} ch={ch:.3f} beta={beta} "
                f"ndof={rs.n} t={time.time() - t0:.0f}s")
        if (it % beta_every == 0) and beta_i + 1 < len(beta_schedule):
            beta_i += 1
            beta = beta_schedule[beta_i]
            xPhys, dproj = _phys(H, Hs, x, beta, ps, pv)
    return FrameOpt(h=g.h, volfrac=volfrac, x=x, xPhys=xPhys, history=hist, keys=[], seconds=time.time() - t0,
                    dom=dom)


def prolong(dom_c: Domain, x_c: np.ndarray, dom_f: Domain) -> np.ndarray:
    """Trilinear interpolation of an element field from a coarse to a fine domain (same box)."""
    from scipy.interpolate import RegularGridInterpolator
    gc, gf = dom_c.grid, dom_f.grid
    ax = [gc.x0[d] + (np.arange(gc.shape[d]) + 0.5) * gc.h for d in range(3)]
    fi = RegularGridInterpolator(ax, gc.to_array(x_c), bounds_error=False, fill_value=None)
    return np.clip(fi(gf.elem_centers()), 0.0, 1.0)


# ============================================================================= verification
@dataclass
class Verified:
    h: float
    solid: np.ndarray            # element mask on the verification grid
    dom: Domain
    volume_mm3: float
    stress: dict                 # key -> dict(vm99, vm_max, pnorm, sn_x99, sn_y99, sn_z99)
    env_vm: np.ndarray           # per-element envelope von Mises over all sets (factored)
    env_s: np.ndarray            # per-element envelope |normal stress| per axis (3,) factored
    env_t: np.ndarray            # per-element envelope |shear| per plane pair (xy, yz, zx)
    keys: list
    disp: dict = field(default_factory=dict)
    stiff: dict = field(default_factory=dict)
    exclude: np.ndarray | None = None
    S: dict = field(default_factory=dict)    # key -> (ne_s, 6) stresses (kept for the governing sets only)


def threshold_up(dom_f: Domain, xPhys: np.ndarray, up: int = 2, level: float = 0.5, sleeve_wall=SLEEVE_WALL,
                 rods: list | None = None):
    """Up-sample the density 'up' times, threshold, re-impose passives and keep the body that is connected to
    the hip-pivot clamp (directly, or through embedded rods): islands that cannot carry load are dropped."""
    from scipy import ndimage
    dv = build_domain(dom_f.h / up, dom_f.env, sleeve_wall=sleeve_wall)
    x = prolong(dom_f, xPhys, dv)
    solid = (x >= level) | dv.passive_solid
    solid &= ~dv.passive_void
    lab3, n = ndimage.label(dv.grid.to_array(solid))
    lab = dv.grid.from_array(lab3)
    if n > 1:
        piv = np.unique(lab[dv.masks["pivot"] & solid])
        keep = set(int(v) for v in piv if v > 0)
        if not keep:
            sizes = ndimage.sum(np.ones_like(lab3), lab3, index=np.arange(1, n + 1))
            keep = {1 + int(np.argmax(sizes))}
        if rods:
            c = dv.grid.elem_centers()
            touched = []
            for r in rods:
                d = (r.p1 - r.p0) / np.linalg.norm(r.p1 - r.p0)
                v = c - r.p0
                t = np.clip(v @ d, 0, np.linalg.norm(r.p1 - r.p0))
                near = np.linalg.norm(v - t[:, None] * d, axis=1) < 1.5 * dv.h
                touched.append(set(int(q) for q in np.unique(lab[near & solid]) if q > 0))
            grew = True
            while grew:
                grew = False
                for tset in touched:
                    if tset & keep and not tset <= keep:
                        keep |= tset
                        grew = True
        solid = np.isin(lab, list(keep))
    return dv, solid


def solve_solid(dv: Domain, solid: np.ndarray, F: np.ndarray, fixed: np.ndarray, E: float = 1.0,
                rods: list | None = None, tol=1e-7, log=None):
    g = dv.grid
    KE = ke_h8(g.h, 1.0, NU)
    if rods:
        rods = [Rod(r.p0, r.p1, r.area, r.E_ratio, r.name, r.density) for r in rods]
    rs = ReducedSystem(g, solid, fixed, KE, rods)
    K = rs.assemble(np.full(rs.ae.size, 1.0))
    U = rs.solve(K, F) / E
    if log:
        log(f"   solid solve: {solid.sum()} elements, {rs.n} dof")
    return U, fixed


def element_stress(g: Grid, U: np.ndarray, solid: np.ndarray, E=1.0):
    D = iso_D3(E, NU)
    B = b_h8_center(g.h)
    idx = np.where(solid)[0]
    Ue = U[g.edof[idx]]
    return idx, (Ue @ B.T) @ D.T


def verify(dom_f: Domain, xPhys: np.ndarray, sets: list[LoadSet], up: int = 2, rods_fn=None, E_mat=1.0,
           log=None, keep_S=("drop_2p5g|19", "side_hill_torsion|15", "meat_straps|23", "hipbelt_off_abuse|19")):
    rods = rods_fn(dom_f) if rods_fn else None
    dv, solid = threshold_up(dom_f, xPhys, up, rods=rods)
    F, fixed = assemble_loads(dv, sets, solid_mask=solid)
    rods = rods_fn(dv) if rods_fn else None
    U, fx = solve_solid(dv, solid, F, fixed, E=E_mat, rods=rods, log=log)
    g = dv.grid
    # exclude the clamp elements and one voxel around load patches from the percentile statistics
    nc = g.node_coords()
    clamp_n = np.where(fixed[0::3])[0]
    loaded = np.where(np.abs(F).reshape(g.nn, 3, -1).sum(axis=(1, 2)) > 0)[0]
    bad_n = np.zeros(g.nn, bool); bad_n[clamp_n] = True; bad_n[loaded] = True
    excl = bad_n[g.enodes].any(axis=1)
    idx = np.where(solid)[0]
    ex = excl[idx]
    env_vm = np.zeros(idx.size)
    env_s = np.zeros((idx.size, 3))
    env_t = np.zeros((idx.size, 3))
    stress, S_keep = {}, {}
    for k, ls in enumerate(sets):
        _, S = element_stress(g, U[:, k], solid, E_mat)
        vm = von_mises_3d(S)
        env_vm = np.maximum(env_vm, vm)
        env_s = np.maximum(env_s, np.abs(S[:, :3]))
        env_t = np.maximum(env_t, np.abs(S[:, 3:]))
        v_ok = vm[~ex]
        p = 8.0
        stress[ls.key] = {"vm99": float(np.percentile(v_ok, 99)), "vm_max": float(v_ok.max()),
                          "pnorm": float((np.mean(v_ok ** p)) ** (1 / p) * (v_ok.size ** (1 / p))) if False else
                          float(np.mean(v_ok ** p) ** (1 / p)),
                          "sn99": [float(np.percentile(np.abs(S[~ex, d]), 99)) for d in range(3)],
                          "tau99": [float(np.percentile(np.abs(S[~ex, 3 + d]), 99)) for d in range(3)],
                          "factor": ls.factor}
        if ls.key in keep_S:
            S_keep[ls.key] = S.astype(np.float32)
    vol = float(solid.sum() * g.h ** 3)
    vr = Verified(h=g.h, solid=solid, dom=dv, volume_mm3=vol, stress=stress, env_vm=env_vm, env_s=env_s,
                  env_t=env_t, keys=[s.key for s in sets], exclude=ex, S=S_keep)
    vr.disp = {"U_drop19": U[:, [s.key for s in sets].index("drop_2p5g|19")].astype(np.float32)} \
        if "drop_2p5g|19" in vr.keys else {}
    vr.stiff = stiffness_tests(dv, solid, rods=rods, E=E_mat, sets=sets)
    return vr


# ============================================================================= stiffness tests
TORSION_F = 100.0           # N, +-y at the two stay-top sockets (x +-115, z 510-544)


def stiffness_tests(dv: Domain, solid: np.ndarray, rods=None, E=1.0, sets=None) -> dict:
    """(1) static carry 150 lb, 1.0 g (unfactored): aft (y) and vertical (z) deflection of the stay-top
    crown sockets relative to the clamped hip pivot; (2) frame torsion about z: +-100 N fore-aft at the
    two stay-top sockets, k = T / theta. Values for modulus E (MPa); scale by E_ref / E for another one."""
    g = dv.grid
    out = {}
    sc = [s for s in (sets or []) if s.case == "static_carry" and s.torso == 19.0]
    cols = []
    if sc:
        s0 = copy.copy(sc[0]); s0.factor = 1.0
        F1, fixed = assemble_loads(dv, [s0], solid_mask=solid)
        cols.append(F1[:, 0])
    else:
        _, fixed = assemble_loads(dv, [], solid_mask=solid)
    nc = g.node_coords()
    act = np.zeros(g.nn, bool); act[np.unique(g.enodes[solid])] = True
    top = {}
    Ft = np.zeros(g.ndof)
    for tag, s in (("R", 1), ("L", -1)):
        e = dv.masks[f"sleeve_{tag}"] & solid
        m = np.zeros(g.nn, bool); m[np.unique(g.enodes[e])] = True
        m &= (nc[:, 2] >= 510.0)
        top[tag] = np.where(m)[0]
        Ft[3 * top[tag] + 1] = s * TORSION_F / max(top[tag].size, 1)
    cols.append(Ft)
    U, fx = solve_solid(dv, solid, np.stack(cols, 1), fixed, E=E, rods=rods)
    if sc:
        u = U[:, 0].reshape(-1, 3)
        out["carry_dy_mm"] = float(np.mean([u[top[t], 1].mean() for t in "LR"]))
        out["carry_dz_mm"] = float(np.mean([u[top[t], 2].mean() for t in "LR"]))
    u = U[:, -1].reshape(-1, 3)
    dy = u[top["R"], 1].mean() - u[top["L"], 1].mean()
    theta = dy / (2 * 115.0)
    T = TORSION_F * 2 * 115.0 / 1000.0           # N m
    out["torsion_Nm_per_deg"] = float(T / np.degrees(theta)) if theta > 0 else float("inf")
    out["E_ref"] = float(E)
    return out


def tube_frame_stiffness(frame_yaml=FRAME_YAML, torso=19.0, sets=None) -> dict:
    """Same two tests on the v2 carbon-tube frame (beam model, hip pivot clamped)."""
    from huntkit.fea.frame import solve
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import ls1_cases
    fm = build_frame_from_yaml(frame_yaml, torso_in=float(torso), extension_posts=False)
    out = {}
    c = next(x for x in ls1_cases() if x.name == "static_carry")
    c.buckling = False
    res = c.run(fm)
    # same load set as the voxel test: every external load / reaction except the hip pivot's
    loads = {}
    for nid in fm["nodes"]:
        if nid == "HP":
            continue
        v = np.zeros(6)
        L = (res.model.get("loads") or {}).get(nid)
        if L is not None:
            v[: len(L)] += L
        if nid in res.reactions:
            v += res.reactions[nid]
        if np.any(v):
            loads[nid] = list(v)
    m = dict(fm); m["loads"] = loads; m["supports"] = {"HP": "fixed"}; m["inertia_relief"] = False
    r = solve(m, buckling=False)
    i = {n: r.node_ids.index(n) for n in ("SL530", "SR530")}
    out["carry_dy_mm"] = float(np.mean([r.u[6 * i[n] + 1] for n in i]))
    out["carry_dz_mm"] = float(np.mean([r.u[6 * i[n] + 2] for n in i]))
    m2 = dict(fm); m2["loads"] = {"SR530": [0, TORSION_F, 0, 0, 0, 0], "SL530": [0, -TORSION_F, 0, 0, 0, 0]}
    m2["supports"] = {"HP": "fixed"}; m2["inertia_relief"] = False
    r2 = solve(m2, buckling=False)
    dy = r2.u[6 * i["SR530"] + 1] - r2.u[6 * i["SL530"] + 1]
    theta = dy / (2 * 115.0)
    out["torsion_Nm_per_deg"] = float(TORSION_F * 0.230 / np.degrees(theta))
    return out


# ============================================================================= materials
@dataclass
class PrintMaterial:
    id: str
    label: str
    process: str
    rho: float                   # kg/m3
    E: float                     # MPa, in the layer plane (FDM) / isotropic
    Ez: float                    # MPa, normal to the layers
    s_xy: float                  # MPa tensile strength in the layer plane (dry, 23 C)
    s_z: float                   # MPa normal to the layers
    knock: float                 # environmental knockdown on strength (hot/wet, conditioned)
    E_hot: float                 # E(40 C, conditioned) / E(23 C dry)
    creep8h: float               # creep modulus ratio E_c(8 h)/E at 40 C under sustained load
    rupture: float               # sustained-stress limit (8 h, 40 C) / short-term strength
    fat: float                   # 1e5-cycle fatigue strength / static strength (R ~ 0.1)
    E_cold: float = 1.3          # E(-20 C)/E(23 C)
    impact_kj_m2: float = 0.0    # notched Charpy 23 C (as published)
    impact_cold_ratio: float = 0.7
    hdt_c: float = 0.0           # HDT at 0.45 MPa (C)
    tg_c: float = 0.0
    water_pct: float = 0.0
    cost_per_g: float = 0.0
    cost_basis: str = ""
    min_wall: float = 2.0
    anisotropic: bool = False
    ref: str = ""


def material_table() -> dict:
    """Printing materials (data/materials records; numbers + sources live there)."""
    from huntkit.fea.materials_bridge import get_material
    ids = ["pa6_cf_fdm_bambu", "pa12_cf_fdm_paht", "pa12_mjf_hp", "pa11_mjf_hp", "pa12_gb_mjf_hp",
           "pa12_cf_sls", "onyx_ccf_markforged", "alsi10mg_slm"]
    out = {}
    for i in ids:
        m = get_material(i)
        P = m.props if hasattr(m, "props") else {}
        g = m.get
        if i == "alsi10mg_slm":
            out[i] = PrintMaterial(i, "SLM AlSi10Mg (reference)", "SLM metal", g("density_kg_m3"), g("youngs_modulus_mpa"),
                                   g("youngs_modulus_mpa"), 184.0, 184.0, 1.0, 1.0, 1.0, 1.0,
                                   float(g("fatigue_limit_mpa", 60.0)) / 184.0, E_cold=1.0, hdt_c=500, tg_c=500,
                                   cost_per_g=float(g("print_cost_usd_per_g", 0.9)), cost_basis="service ASSUMPTION",
                                   min_wall=1.0, ref=i)
            continue
        out[i] = PrintMaterial(
            id=i, label=m.name, process=str(g("process", "")), rho=float(g("density_kg_m3")),
            E=float(g("youngs_modulus_xy_mpa", g("youngs_modulus_mpa"))),
            Ez=float(g("youngs_modulus_z_mpa", g("youngs_modulus_mpa"))),
            s_xy=float(g("tensile_strength_xy_mpa", g("tensile_strength_mpa", 0.0))),
            s_z=float(g("tensile_strength_z_mpa", g("tensile_strength_xy_mpa", g("tensile_strength_mpa", 0.0)))),
            knock=float(g("env_knockdown_ratio", 0.8)), E_hot=float(g("modulus_40c_wet_ratio", 0.6)),
            creep8h=float(g("creep_modulus_8h_40c_ratio", 0.7)), rupture=float(g("creep_rupture_8h_40c_ratio", 0.4)),
            fat=float(g("fatigue_1e5_ratio", 0.3)), E_cold=float(g("modulus_minus20c_ratio", 1.3)),
            impact_kj_m2=float(g("charpy_notched_kj_m2", 0.0)), impact_cold_ratio=float(g("impact_minus20c_ratio", 0.7)),
            hdt_c=float(g("heat_deflection_temp_c", 0.0)), tg_c=float(g("glass_transition_c", 0.0)),
            water_pct=float(g("water_absorption_pct", 0.0)), cost_per_g=float(g("print_cost_usd_per_g", 0.1)),
            cost_basis=str(g("print_cost_basis", "")), min_wall=float(g("min_wall_mm", 2.0)),
            anisotropic=bool(g("anisotropic", False)), ref=i)
    return out


# ============================================================================= orientation (FDM)
def layer_failure_index(env_s: np.ndarray, env_t: np.ndarray, normal_axis: int, s_xy: float, s_z: float,
                        knock: float) -> np.ndarray:
    """Per-element failure index for a layered (FDM) part with layer normal along ``normal_axis``:
    max( in-plane von-Mises-like / (knock s_xy), normal / (knock s_z), interlayer shear / (knock 0.6 s_z) )
    from the stress envelopes (conservative: envelopes of different cases combined). ASSUMPTION:
    interlayer shear strength 0.6 x Z tensile strength."""
    a = normal_axis
    ip = [d for d in range(3) if d != a]
    sn = env_s[:, a]
    s_ip = np.maximum(env_s[:, ip[0]], env_s[:, ip[1]])
    shear_idx = {0: (0, 2), 1: (0, 1), 2: (1, 2)}   # tau components touching the normal axis: xy(0), yz(1), zx(2)
    tl = np.maximum(env_t[:, shear_idx[a][0]], env_t[:, shear_idx[a][1]])
    tin = env_t[:, [k for k in range(3) if k not in shear_idx[a]][0]]
    vm_ip = np.sqrt(s_ip ** 2 + 3 * tin ** 2)
    return np.maximum.reduce([vm_ip / (knock * s_xy), sn / (knock * s_z), tl / (knock * 0.6 * s_z)])


# ============================================================================= mesh + segments
def solid_to_mesh(dv: Domain, solid: np.ndarray, smooth_iters: int = 10):
    from .surface import field_to_mesh
    f = dv.grid.to_array(solid.astype(float))
    return field_to_mesh(f, dv.h, dv.grid.x0, level=0.5, smooth_iters=smooth_iters, upsample=1)


def split_mesh(mesh, z_cut: float):
    """Cut the body at z = z_cut into two closed segments (manifold3d half-space trim)."""
    from .surface import _from_manifold, _to_manifold
    man = _to_manifold(mesh)
    lo = man.trim_by_plane((0.0, 0.0, -1.0), -z_cut)
    hi = man.trim_by_plane((0.0, 0.0, 1.0), z_cut)
    return _from_manifold(lo), _from_manifold(hi)


def section_resultants(dv: Domain, solid: np.ndarray, U_col: np.ndarray, z_cut: float, E=1.0) -> dict:
    """Internal force + moment transmitted across the plane z = z_cut, per side (x < 0 / x > 0), from the
    element stresses of the layer of elements just below the cut (sigma_zz, tau_zx, tau_yz)."""
    g = dv.grid
    c = g.elem_centers()
    lay = solid & (np.abs(c[:, 2] - (z_cut - g.h / 2)) < g.h / 2 + 1e-6)
    idx, S = element_stress(g, U_col, lay, E)
    A = g.h ** 2
    out = {}
    for tag, m in (("L", c[idx, 0] < 0), ("R", c[idx, 0] >= 0)):
        if not m.any():
            continue
        s = S[m]
        xc = c[idx][m]
        cen = xc.mean(0)
        Fz = s[:, 2].sum() * A
        Vx = s[:, 5].sum() * A
        Vy = s[:, 4].sum() * A
        My = (s[:, 2] * (xc[:, 0] - cen[0])).sum() * A
        Mx = (s[:, 2] * (xc[:, 1] - cen[1])).sum() * A
        out[tag] = {"N": float(Fz), "Vx": float(Vx), "Vy": float(Vy), "Mx": float(Mx), "My": float(My),
                    "area_mm2": float(m.sum() * A), "centroid": cen.tolist()}
    return out


def joint_check(res: dict, bolt_d=5.0, n_bolts=2, lap_mm=40.0, width_mm=None, tau_bond=6.0, bearing=60.0,
                bolt_shear=300.0, t_lap=6.0, lever=None) -> dict:
    """Bolted + bonded dovetail lap across the cut, per side. Bolts take the shear, bond takes the
    axial / moment couple (flange forces): F_flange = |N|/2 + |M| / lever.
    ASSUMPTIONS: tau_bond 6 MPa (MMA on flame/plasma-treated nylon, hot/wet), bolt M5 A2-70 shear
    300 MPa x root area, nylon bearing 60 MPa (knocked down)."""
    out = {}
    for tag, r in res.items():
        lev = lever or 30.0
        Ff = abs(r["N"]) / 2 + max(abs(r["Mx"]), abs(r["My"])) / lev
        w = width_mm or 30.0
        bond_cap = tau_bond * lap_mm * w
        V = np.hypot(r["Vx"], r["Vy"])
        Ab = 0.7854 * (0.85 * bolt_d) ** 2
        bolt_cap = n_bolts * bolt_shear * 0.6 * Ab
        bear_cap = n_bolts * bearing * bolt_d * t_lap
        out[tag] = {"flange_force_n": float(Ff), "bond_sf": float(bond_cap / max(Ff, 1e-9)),
                    "shear_n": float(V), "bolt_sf": float(min(bolt_cap, bear_cap) / max(V, 1e-9))}
    return out


# ============================================================================= fiber paths
def principal_streamlines(dv: Domain, solid: np.ndarray, S: np.ndarray, y_layer: float, n_seeds: int = 24,
                          step: float = 3.0, max_len: float = 900.0) -> list:
    """Trajectories of the major in-plane (x-z) principal stress on the layer y ~ y_layer of a flat-printed
    body (layer plane = frame x-z plane). Seeds where |sigma_1| is highest. Returns polylines (n, 3)."""
    g = dv.grid
    idx = np.where(solid)[0]
    c = g.elem_centers()[idx]
    sel = np.abs(c[:, 1] - y_layer) <= g.h * 0.75
    if sel.sum() < 10:
        return []
    cc = c[sel]
    s = S[sel]
    sxx, szz, txz = s[:, 0], s[:, 2], s[:, 5]
    ang = 0.5 * np.arctan2(2 * txz, sxx - szz)
    s1 = 0.5 * (sxx + szz) + np.sqrt((0.5 * (sxx - szz)) ** 2 + txz ** 2)
    s2 = 0.5 * (sxx + szz) - np.sqrt((0.5 * (sxx - szz)) ** 2 + txz ** 2)
    smax = np.where(np.abs(s1) >= np.abs(s2), s1, s2)
    ang = np.where(np.abs(s1) >= np.abs(s2), ang, ang + np.pi / 2)
    d = np.stack([np.cos(ang), np.sin(ang)], 1)           # (x, z) direction
    from scipy.spatial import cKDTree
    tree = cKDTree(cc[:, [0, 2]])
    order = np.argsort(-np.abs(smax))
    seeds, used = [], []
    for k in order:
        p = cc[k, [0, 2]]
        if all(np.linalg.norm(p - q) > 25.0 for q in seeds):
            seeds.append(p)
        if len(seeds) >= n_seeds:
            break
    lines = []
    for p0 in seeds:
        pts = [p0]
        for sgn in (1, -1):
            p = p0.copy()
            dprev = None
            seg = []
            L = 0.0
            while L < max_len / 2:
                dist, j = tree.query(p)
                if dist > 1.5 * g.h:
                    break
                v = d[j]
                if dprev is None:
                    v = sgn * v
                elif v @ dprev < 0:
                    v = -v
                p = p + step * v
                dprev = v
                seg.append(p.copy())
                L += step
            pts = (seg[::-1] + pts) if sgn == -1 else (pts + seg)
        if len(pts) > 10:
            P = np.array(pts)
            lines.append(np.c_[P[:, 0], np.full(len(P), y_layer), P[:, 1]])
    return lines


# ============================================================================= high level
def save_npz(path, **kw):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **kw)


def run_optimization(sets: list[LoadSet], volfrac: float, h_coarse=8.0, h_fine=4.0, it_coarse=45, it_fine=28,
                     rods_fn=None, log=None, rmin_vox=1.5, keep_frac=0.97, snap_every=None, snaps=None,
                     band_mm=16.0) -> dict:
    """Coarse (all distinct load shapes x 3 torsos) -> fine (governing sets, active band around the coarse
    structure: elements farther than ``band_mm`` from coarse material > 0.02 are void at the fine level)."""
    from scipy import ndimage
    env = load_envelope()
    opt_sets = [s for s in sets if s.case in SHAPES_FOR_OPT]
    dc = build_domain(h_coarse, env)
    Fc, fxc = assemble_loads(dc, opt_sets)
    rc = rods_fn(dc) if rods_fn else None

    def cb(it, xp, rec, tag="c"):
        if snaps is not None and snap_every and (it % snap_every == 0 or it == 1):
            snaps.append({"stage": tag, "it": it, "h": rec["h"], "x": xp.astype(np.float16), "rec": rec})
    oc = simp_frame(dc, Fc, fxc, volfrac, iters=it_coarse, rmin_vox=rmin_vox, rods=rc, log=log,
                    beta_schedule=(1, 2, 4), beta_every=15, hist_cb=cb)
    comps = np.array(oc.history[-1]["comps"])
    c0 = np.array(oc.history[0]["comps"])
    rel = comps / c0                                   # same normalization as the optimizer weights
    order = np.argsort(-rel)
    keep, acc = [], 0.0
    for k in order:
        keep.append(int(k)); acc += rel[k]
        if acc >= keep_frac * rel.sum() or len(keep) >= 10:
            break
    fine_sets = [opt_sets[k] for k in sorted(keep)]
    df = build_domain(h_fine, env)
    x0 = prolong(dc, oc.xPhys, df)
    near = df.grid.to_array(x0 > 0.02)
    band = ndimage.binary_dilation(near, iterations=max(1, int(round(band_mm / h_fine))))
    df.passive_void = df.passive_void | (~df.grid.from_array(band) & ~df.passive_solid)
    Ff, fxf = assemble_loads(df, fine_sets)
    rf = rods_fn(df) if rods_fn else None
    of = simp_frame(df, Ff, fxf, volfrac * (df.design().sum() and (build_domain(h_fine, env).design().sum() / df.design().sum())),
                    iters=it_fine, rmin_vox=rmin_vox, rods=rf, x0=prolong(dc, oc.x, df), log=log,
                    beta_schedule=(2, 4, 8), beta_every=10, hist_cb=lambda i, xp, r: cb(i, xp, r, "f"))
    full = build_domain(h_fine, env)
    return {"coarse": oc, "fine": of, "fine_keys": [s.key for s in fine_sets], "domain_f": df,
            "volfrac": volfrac, "design_volume_mm3": float(full.design().sum() * h_fine ** 3),
            "passive_volume_mm3": float(full.passive_solid.sum() * h_fine ** 3),
            "rel_compliance": dict(zip([s.key for s in opt_sets], rel.tolist()))}
