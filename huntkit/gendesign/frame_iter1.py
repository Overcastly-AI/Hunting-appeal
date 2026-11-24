"""BL-061 iteration 1, frame track: lighter-and-at-least-as-strong concepts for the H1 frame.

Every concept is built on the **exported H1 print** (``print/frame_h1/h1_assembled.stl``, locked to its md5) re-rastered
on the H1 2 mm grid (``bl058_frame.body_stl``), so the bag interfaces (hinge eyes, US lanes, fairleads, crown, hip boss,
spine channel) stay exactly where they are. Concepts (``CONCEPTS``):

- ``h1``      the baseline (the released print).
- ``graded``  (C) same STL, slicer-only: 4 mm wall shell, 15 % gyroid core where the baseline utilisation is low, 100 %
              infill modifiers at every hard point. No CAD change.
- ``box``     (A) topology refinement on the print: the buckling members (branches, mid bar) grown 2 mm and made
              closed boxes, low-utilisation thick zones hollowed into ribbed cavities, the cinch-cycled hot spot grown.
- ``cfstay``  (B) hybrid: two roll-wrapped carbon tubes as the stays (crown legs slide inside), three printed PAHT-CF
              parts slid on and bonded (lower node, branch X, top node); the z 234 bolted split is deleted.
- ``cfbox``   (D) ``cfstay`` with ``box``'s member and hollowing rules on its printed parts.

Check: the BL-055 / BL-058 whole-body check (``h1_buckling.full_check`` rules: FI99 layer rule, fatigue / creep from the
static-carry sets, the 4 bases incl. the cinch-cycled ``fine_sm8.cyc``, lane kit sets, real crown models, stays
sanded k 1.0416), extended for stiffness weights (``h1_sleeve.solve_fields_w``):
- gyroid core voxels: E x ``W_GYROID``; their FI is taken against the gyroid strength (stays in the FI99 population);
- carbon tube voxels: isotropic weight that matches the tube's EI; checked as CFRP (max-stress FI on the tube's own
  stress, knock-downs kept), left out of the printed FI99 population;
- member buckling: the record rule (team A: voxel area as a solid round, K 1, E x 0.6 x 0.7) AND a section rule
  (the cut's real weighted I_min about its centroid). The section rule is stricter on flat sections and credits boxes.

Run: ``python -m huntkit.gendesign.frame_iter1 [check <concept> | all | report]``.
Record: ``designs/pack_5200/iter1/frame/frame_iter1.{md,json}``. Tests: ``tests/test_frame_iter1.py``.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
STL = PACK / "print" / "frame_h1" / "h1_assembled.stl"
STL_MD5 = "7bd47cbdcc3b42c0f93d57ef041efc11"         # BL-060 lock (gauge_lines_bl060.json)
DESIGN_DIR = PACK / "iter1" / "frame"
OUT = REPO / "outputs" / "iter1_frame"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261124_iter1_frame_"
H = 2.0
RHO_PAHT = 1.06e-3                                   # g/mm3, pa12_cf_fdm_paht record
SAND_K = 1.0416                                      # h1_closeout.sand_factor (BL-055 / BL-058)
BASES = ("fine_sm8", "fine", "beam", "fine_sm8.cyc")
E_PAHT = 3860.0                                      # MPa, record (frame_comp_d paht_fdm)
E_BUCKLE = E_PAHT * 0.6 * 0.7                        # team A rule: hot 0.6 x creep 0.7

# ----------------------------------------------------------------------------------------------- material inputs
# Gyroid core (slicer infill). Gibson-Ashby (Cellular Solids, 2nd ed., ch. 5) bending-dominated cells:
# E*/E_s = C1 rho^2 (C1 ~ 1), sigma*/sigma_s = C2 rho^1.5 (C2 ~ 0.3). Sheet-gyroid FDM data sit at or above these
# (docs/research/frame_iter1.md section 4). ASSUMPTION GYROID: both apply to PAHT-CF gyroid at 15 %.
GYROID_RHO = 0.15
W_GYROID = GYROID_RHO ** 2                           # 0.0225
S_GYROID = 0.3 * GYROID_RHO ** 1.5                   # 0.0174 (strength ratio)
WALL_MM = 4.0                                        # shell: 2 voxel layers = 6 lines of 0.62 mm (0.6 nozzle) + gap
CORE_DEPTH = 6.0                                     # EDT depth (mm) of the third voxel layer: core = depth >= 6
U_CUT = 0.55                                         # graded / hollow only where the baseline max utilisation < U_CUT
DIAPHRAGM_PITCH = 40.0                               # box: a 2 mm solid diaphragm every 40 mm across each cavity

# Roll-wrapped carbon tube (data/materials/composites/cfrp_rollwrapped_tube.yaml): E 75 GPa, 650 / 450 MPa, G 12 GPa,
# shear 90 MPa, 1550 kg/m3. Size: 22 x 18 mm (ID = today's reamed 18.0 mm crown-leg bore), research section 3.
TUBE = {"od": 22.0, "id": 18.0, "E": 75000.0, "G": 12000.0, "Xt": 650.0, "Xc": 450.0, "S": 90.0, "rho": 1.55e-3,
        "x": 115.0, "y": -7.0, "z0": 30.0, "z1": 543.5, "hot_wet": 0.8, "impact_c": 0.65}
# printed parts on the tubes (cfstay): z ranges along the stay where a printed sleeve surrounds the tube. Between
# them the stay is bare tube. P1 lower node, P2 branch X (three sleeves), P3 top node.
SLEEVES = {"P1 lower node": (0.0, 190.0), "P2 lower-branch root": (196.0, 246.0), "P2 mid-bar knuckle": (312.0, 348.0),
           "P2 upper-branch root": (440.0, 466.0), "P3 top node": (472.0, 544.0)}
PART_GAPS = (193.0, 469.0)                           # one 2 mm layer cut through every printed voxel of the stay column
STAY_COL_R = 17.0                                    # stay column: printed voxels within this radius of the tube axis
SLEEVE_R_OUT = 14.0                                  # printed sleeve over the tube in a node (wall 3 mm)
# bond (MMA on sanded, flame-treated PAHT-CF): published PA12 best 5.0 MPa dry (Sedlacek 2025, light_frame_architectures
# section 2), x 0.8 hot/wet = 4.0 MPa. ASSUMPTION BOND-PA (frame_light2), settled by coupon T6p.
BOND_PA_MPA = 5.0
BOND_HOT_WET = 0.8
MMA_G_MPA = 300.0                                    # ASSUMPTION MMA-G: toughened MMA shear modulus (Plexus class)
MMA_T = 0.5                                          # bondline, adhesive_methacrylate_ma record
# P1 and P3 carry the whole pack into the tubes: 0.8 mm bondline (glass beads), as the rev C crown corners, which
# lowers the Volkersen peak by sqrt(0.5 / 0.8) (load_standard.md 4.2, T6 rev C coupons at 0.8 mm)
BONDLINE = {"P1 lower node": 0.8, "P3 top node": 0.8}
# bonded length where it differs from the sleeve: P1 is bonded in two 40 mm bands (z 40-80 at the hinge eyes and
# z 150-190 under the strut / lug roots); the rest of its bore is a 0.2 mm slip fit (ASSUMPTION P1-BANDS)
BOND_L = {"P1 lower node": 80.0}
CROSS_PIN_D = 4.0                                    # fail-safe Ti M4 cross bolt through P1 and P3 sleeves
TUBE_BEARING_MPA = 250.0                             # ASSUMPTION TUBE-BEARING: pin bearing of a roll-wrapped tube


# ================================================================================================ geometry
def stl_md5(path: Path = STL) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _base():
    from . import frame_h1 as H1
    return H1.base()


def baseline_solid(refresh: bool = False) -> np.ndarray:
    """The current print re-rastered on the 2 mm grid (bl058_frame.body_stl), cached against the STL md5."""
    OUT.mkdir(parents=True, exist_ok=True)
    md5 = stl_md5()
    if md5 != STL_MD5:
        raise RuntimeError(f"h1_assembled.stl md5 {md5} is not the locked {STL_MD5}: re-baseline BL-061")
    p = OUT / f"baseline_{md5}.npz"
    if p.exists() and not refresh:
        return np.load(p)["solid"]
    from . import bl058_frame as BF
    solid, info = BF.body_stl()
    np.savez_compressed(p, solid=solid)
    (OUT / f"baseline_{md5}.json").write_text(json.dumps(info, default=float))
    return solid


def depth_mm(solid: np.ndarray) -> np.ndarray:
    """Euclidean distance (mm) from each solid voxel centre to the nearest empty voxel centre (surface voxel = 2)."""
    from scipy import ndimage
    g = _base()["dom"].grid
    return g.from_array(ndimage.distance_transform_edt(g.to_array(solid)) * g.h)


def _dilate(mask: np.ndarray, it: int = 1, structure=None) -> np.ndarray:
    from scipy import ndimage
    g = _base()["dom"].grid
    return g.from_array(ndimage.binary_dilation(g.to_array(mask), iterations=it, structure=structure))


def protected(solid: np.ndarray) -> np.ndarray:
    """Hard points that stay 100 % solid in every concept: load pads, fairlead field, hip boss with its 8 insert
    pilots, pawl housing, spine-channel ring, z 234 joint bosses and holes, stay feet, outboard lug blocks (|x| > 125),
    each dilated 6 mm."""
    from .bag_attach import attachment_field
    from .spreader import SCALE
    from .h1_spine_channel import housing_ring_mask
    from . import frame_h1 as H1
    c = _base()
    dom, cen = c["dom"], c["cen"]
    m = np.asarray(dom.masks["pads"], bool) | np.asarray(dom.masks["pivot"], bool) | np.asarray(dom.masks["pawl"], bool)
    m |= c["holes"] | (H1.boss_sdf(cen) <= 0.0) | housing_ring_mask(cen)
    m |= (attachment_field(cen, SCALE) <= 0.0)
    m |= (np.hypot(cen[:, 0], cen[:, 2] - 120.0) < 27.0) & (cen[:, 1] < -25.0)      # boss + insert pilots (r 19 + 8)
    m = _dilate(m, 3)
    m |= (cen[:, 2] < 40.0) | (np.abs(cen[:, 0]) > 125.0)
    return m & solid


def hard_points(solid: np.ndarray, dil: int = 1) -> np.ndarray:
    """Load pads and the fairlead field only (no lug-block or foot rule), dilated ``dil`` voxels: what a bare carbon
    span must keep as a printed clip."""
    from .bag_attach import attachment_field
    from .spreader import SCALE
    c = _base()
    dom, cen = c["dom"], c["cen"]
    m = np.asarray(dom.masks["pads"], bool) | (attachment_field(cen, SCALE) <= 0.0)
    return _dilate(m, dil) & solid if dil else m & solid


def tube_axis_r(cen: np.ndarray) -> np.ndarray:
    return np.hypot(np.abs(cen[:, 0]) - TUBE["x"], cen[:, 1] - TUBE["y"])


def member_mask(solid: np.ndarray) -> np.ndarray:
    """Branches and mid bar (team A groups 'branch', 'mid')."""
    from . import frame_comp_A as A
    grp = _base()["grp"]
    return solid & ((grp == A.GROUPS.index("branch")) | (grp == A.GROUPS.index("mid")))


def diaphragms(cen: np.ndarray, pitch: float = DIAPHRAGM_PITCH) -> np.ndarray:
    """One voxel layer every ``pitch`` mm across z and across x (kept solid inside cavities)."""
    on = lambda v: np.abs(((v + pitch / 2) % pitch) - pitch / 2) < H / 2 + 1e-6
    return on(cen[:, 2]) | on(cen[:, 0])


def util_of(name: str, cyc: bool = False) -> np.ndarray | None:
    """Max utilisation per element of a checked concept (static bases, or the cinch-cycled basis)."""
    p = OUT / f"util_{name}{'_cyc' if cyc else ''}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    u = np.zeros(_base()["dom"].grid.ne, np.float32)
    u[z["idx"]] = z["util"]
    return u


def util_ref() -> np.ndarray | None:
    p = OUT / "util_h1.npz"
    if not p.exists():
        return None
    z = np.load(p)
    u = np.zeros(_base()["dom"].grid.ne, np.float32)
    u[z["idx"]] = z["util"]
    return u


def util_cyc_ref() -> np.ndarray | None:
    p = OUT / "util_h1_cyc.npz"
    if not p.exists():
        return None
    z = np.load(p)
    u = np.zeros(_base()["dom"].grid.ne, np.float32)
    u[z["idx"]] = z["util"]
    return u


def core_mask(solid: np.ndarray, u_cut: float = U_CUT, util: np.ndarray | None = None) -> np.ndarray:
    """Voxels a shell + core print can put in the core: depth >= CORE_DEPTH, outside the hard points, where the
    reference max utilisation over every basis (default: H1's, util_h1.npz) is below ``u_cut``."""
    u = util_ref() if util is None else util
    if u is None:
        raise RuntimeError("run the baseline check first (util_h1.npz)")
    return solid & (depth_mm(solid) >= CORE_DEPTH - 1e-6) & ~protected(solid) & (u < u_cut)


def grow_members_y(solid: np.ndarray) -> np.ndarray:
    """Members deepened 2 mm on each face in frame y only (the out-of-plane, I_min direction of these sections), same
    limits as grow_members."""
    c = _base()
    dom, cen = c["dom"], c["cen"]
    mem = member_mask(solid)
    st = np.zeros((3, 3, 3), bool)
    st[1, :, 1] = True                                       # grid axis 1 = frame y
    grown = _dilate(mem, 1, structure=st) & ~solid
    ok = dom.design() & ~dom.passive_void & (cen[:, 1] >= -23.0) & (cen[:, 1] <= 9.0) & (cen[:, 2] > 165.0)
    ok &= ~np.asarray(dom.masks["bore_R"], bool) & ~np.asarray(dom.masks["bore_L"], bool) & ~c["holes"]
    return solid | (grown & ok)


def grow_members(solid: np.ndarray) -> np.ndarray:
    """Box members: branches and mid bar grown one voxel (2 mm) in every direction, inside the design domain, out of
    the passive voids, and in y only inside the stay's y span (sleeve masks, y -23..9: the members never reach the
    spreader or the back rails, ASSUMPTION BOX-ENVELOPE)."""
    c = _base()
    dom, cen = c["dom"], c["cen"]
    mem = member_mask(solid)
    grown = _dilate(mem, 1) & ~solid
    ok = dom.design() & ~dom.passive_void & (cen[:, 1] >= -23.0) & (cen[:, 1] <= 9.0) & (cen[:, 2] > 165.0)
    ok &= ~np.asarray(dom.masks["bore_R"], bool) & ~np.asarray(dom.masks["bore_L"], bool) & ~c["holes"]
    return solid | (grown & ok)


def grow_hotspot(solid: np.ndarray, frac: float = 0.80) -> np.ndarray:
    """One voxel of growth around the cinch-cycled hot spot: solid voxels whose baseline cinch-cycled fatigue
    utilisation (util_h1_cyc.npz) is >= ``frac`` x its max, dilated one voxel into the design domain."""
    c = _base()
    dom = c["dom"]
    u = util_cyc_ref()
    if u is None:
        raise RuntimeError("run the baseline check first (util_h1_cyc.npz)")
    hot = solid & (u >= frac * float(u[solid].max()))
    add = _dilate(hot, 1) & ~solid & dom.design() & ~dom.passive_void & ~c["holes"]
    for k in ("bore_R", "bore_L", "pivot"):
        add &= ~np.asarray(dom.masks[k], bool)
    return solid | add


def bond_sleeve_mask() -> np.ndarray:
    """Printed sleeve ring r 11..14 mm round each tube over every bonded length (P1 bands, P2 and P3 sleeves)."""
    c = _base()
    cen = c["cen"]
    r = tube_axis_r(cen)
    ring = (r >= TUBE["od"] / 2 - 1e-6) & (r < SLEEVE_R_OUT) & (np.abs(cen[:, 0]) > 95.0)
    zz = np.zeros(len(cen), bool)
    for k, (z0, z1) in SLEEVES.items():
        if k == "P1 lower node":
            zz |= ((cen[:, 2] >= 40.0) & (cen[:, 2] <= 80.0)) | ((cen[:, 2] >= 150.0) & (cen[:, 2] <= 190.0))
        else:
            zz |= (cen[:, 2] >= z0) & (cen[:, 2] <= z1)
    return ring & zz & c["dom"].design() & ~c["dom"].passive_void


def tube_masks() -> dict:
    """Carbon tube voxels (ring r 9..11 about the stay axis, z0..z1), the tube bore (r < 9) and per-side tube."""
    c = _base()
    cen = c["cen"]
    r = tube_axis_r(cen)
    zr = (cen[:, 2] >= TUBE["z0"]) & (cen[:, 2] <= TUBE["z1"])
    ring = zr & (r >= TUBE["id"] / 2 - 1e-6) & (r < TUBE["od"] / 2 + 1e-6)
    bore = zr & (r < TUBE["id"] / 2 - 1e-6)
    return {"ring": ring, "bore": bore, "R": ring & (cen[:, 0] > 0), "L": ring & (cen[:, 0] < 0)}


def tube_section() -> dict:
    """Real tube vs its voxel ring: A, I and the isotropic weight that matches EI (bending governs the stays)."""
    c = _base()
    cen = c["cen"]
    tm = tube_masks()
    z = 301.0
    m = tm["R"] & np.isclose(cen[:, 2], z)
    P = cen[m]
    dx, dy = P[:, 0] - TUBE["x"], P[:, 1] - TUBE["y"]
    A_vox = len(P) * H * H
    I_vox = float(((dy ** 2).sum() + (len(P) * H * H / 12.0)) * H * H)
    Ix_vox = float((dx ** 2).sum() * H * H + len(P) * H ** 4 / 12.0)
    ro, ri = TUBE["od"] / 2, TUBE["id"] / 2
    A_t = math.pi * (ro ** 2 - ri ** 2)
    I_t = math.pi / 4 * (ro ** 4 - ri ** 4)
    I_vox = min(I_vox, Ix_vox) if False else 0.5 * (I_vox + Ix_vox)
    w = TUBE["E"] * I_t / (E_PAHT * I_vox)
    return {"A_tube_mm2": A_t, "I_tube_mm4": I_t, "A_vox_mm2": A_vox, "I_vox_mm4": I_vox, "weight": w,
            "EA_ratio_vox_over_tube": w * E_PAHT * A_vox / (TUBE["E"] * A_t),
            "GJ_ratio_vox_over_tube": (w * E_PAHT / 2.7) * 2 * I_vox / (TUBE["G"] * 2 * I_t),
            "g_per_mm": A_t * TUBE["rho"]}


# ================================================================================================ concepts
CONCEPTS = ("h1", "graded", "box", "cfstay", "cfbox", "cflite")
CFLITE_UCUT = 0.60        # cflite: hollow where CF-STAY's own utilisation (static max and cinch-cycled) is below this
LABEL = {"h1": "H1 today (released print)", "graded": "C  GRADED: same STL, shell + 15 % gyroid core",
         "box": "A  BOX: closed-box members + ribbed cavities", "cfstay": "B  CF-STAY: carbon-tube stays + 3 printed nodes",
         "cfbox": "D  CF-BOX: CF-STAY + box members + ribbed node cavities",
         "cflite": "E  CF-LITE: CF-STAY + box members + cavities sized on CF-STAY's own utilisation"}


def build(name: str) -> dict:
    """Concept -> {solid, weight (ne float), core, cf, printed, joint (bool: z 234 split present), info}."""
    c = _base()
    cen, dom = c["cen"], c["dom"]
    ne = dom.grid.ne
    s0 = baseline_solid()
    w = np.ones(ne, np.float32)
    zero = np.zeros(ne, bool)
    info = {}
    if name == "h1":
        solid, core, cf, joint = s0.copy(), zero, zero, True
    elif name == "graded":
        solid = s0.copy()
        core = core_mask(solid)
        cf, joint = zero, True
        w[core] = W_GYROID
    elif name == "box":
        solid = grow_hotspot(grow_members(s0))
        mem = member_mask(solid)
        dep = depth_mm(solid)
        cav = (core_mask(solid) | (mem & (dep >= CORE_DEPTH - 1e-6))) & ~diaphragms(cen)
        info["cavity_voxels"] = int(cav.sum())
        solid = solid & ~cav
        core, cf, joint = zero, zero, True
    elif name in ("cfstay", "cfbox", "cflite"):
        tm = tube_masks()
        r = tube_axis_r(cen)
        col = (r < STAY_COL_R) & (np.abs(cen[:, 0]) > 95.0)
        in_sleeve = np.zeros(ne, bool)
        for z0, z1 in SLEEVES.values():
            in_sleeve |= (cen[:, 2] >= z0) & (cen[:, 2] <= z1)
        solid = s0.copy()
        # bare spans: the printed stay goes, except the pads (spreader-clip seats, fairleads) and the bag hard points
        hp = hard_points(s0)
        from . import frame_comp_A as A
        stay_grp = np.isin(c["grp"], [A.GROUPS.index(g_) for g_ in ("sleeve", "low", "top", "foot")])
        bare = col & ~in_sleeve & ~hp & (stay_grp | (r < TUBE["od"] / 2 + 1e-6))
        solid &= ~bare
        # in the P2 sleeves the printed stay wall is cut to SLEEVE_R_OUT (stay groups only: the branch and mid-bar
        # roots that enter the column stay whole; the P1 lower node and the P3 top node keep their print)
        solid &= ~(col & in_sleeve & stay_grp & (r >= SLEEVE_R_OUT) & ~hp & ~protected(s0)
                   & (cen[:, 2] > 195.0) & (cen[:, 2] < 470.0))
        # the parts are separate: one empty layer through the stay column at each part boundary
        for zg in PART_GAPS:
            solid &= ~(col & (np.abs(cen[:, 2] - zg) < H / 2 + 1e-6) & (r >= TUBE["od"] / 2))
        solid &= ~tm["bore"]
        solid |= tm["ring"]
        # a full printed sleeve (r 11..14, 3 mm) wherever the tube is bonded: H1's stay was narrower than 28 mm in
        # places (the lower legs), which would leave windows in the bond bands
        solid |= bond_sleeve_mask()
        # z 234 split deleted: its bosses / holes are no longer needed; fill the holes inside the remaining print
        solid &= ~((c["holes"] | (__import__("huntkit.gendesign.frame_h1", fromlist=["x"]).boss_sdf(cen) <= 0.0))
                   & ~tm["ring"] & col & (r >= SLEEVE_R_OUT))
        cf = tm["ring"].copy()
        ts = tube_section()
        w[cf] = ts["weight"]
        info["tube"] = ts
        core, joint = zero, False
        if name == "cfbox":
            pr = solid & ~cf
            pr2 = grow_hotspot(grow_members(pr))
            solid = solid | pr2
            mem = member_mask(solid & ~cf)
            dep = depth_mm(solid & ~cf)
            cav = ((core_mask(solid & ~cf)) | (mem & (dep >= CORE_DEPTH - 1e-6))) & ~diaphragms(cen) & ~cf
            info["cavity_voxels"] = int(cav.sum())
            solid &= ~cav
        if name == "cflite":
            uu = util_of("cfstay")
            uc = util_of("cfstay", cyc=True)
            if uu is None or uc is None:
                raise RuntimeError("check cfstay first (util_cfstay*.npz)")
            u = np.maximum(uu, uc)
            # the tube carries the stay: every printed stay voxel outside the 14 mm sleeve goes (P1 and P3 too),
            # except the hard points (pads, fairleads, 4 mm round them), the lug arms (|x| > 126 below z 175) and
            # any voxel CF-STAY used above 0.4
            keep = hard_points(s0, 2) | ((np.abs(cen[:, 0]) > 126.0) & (cen[:, 2] < 175.0)) | (u >= 0.4)
            keep |= cen[:, 2] > 466.0      # v1 trimmed P3 too: strength fell to 1.50 at the top bushing (check_cflite_v1)
            solid &= ~(col & stay_grp & (r >= SLEEVE_R_OUT) & ~keep & ~cf)
            solid = _connected(solid)
            pr = solid & ~cf
            # v1 deepened the members in y only: upper branch R buckling 0.91 (1067 N, side-hill); full box as CF-BOX
            solid = solid | grow_members(pr)
            pr = solid & ~cf
            mem = member_mask(pr)
            dep = depth_mm(pr)
            cav = (core_mask(pr, CFLITE_UCUT, util=u) | (mem & (dep >= CORE_DEPTH - 1e-6))) & ~diaphragms(cen) & ~cf
            # no cavity in the upper bar / pawl housing (BOX and CF-BOX lost strength there: hipbelt-off abuse)
            cav &= ~(cen[:, 2] > 470.0)
            info["cavity_voxels"] = int(cav.sum())
            solid &= ~cav
    else:
        raise KeyError(name)
    solid = _connected(solid)
    core &= solid
    cf &= solid
    w[~solid] = 1.0
    return {"name": name, "solid": solid, "weight": w, "core": core, "cf": cf, "printed": solid & ~cf,
            "joint": joint, "info": info}


def _connected(solid: np.ndarray) -> np.ndarray:
    """Largest 6-connected part (the voxel FE needs one body; drops floating voxels left by the cuts)."""
    from scipy import ndimage
    g = _base()["dom"].grid
    lab, n = ndimage.label(g.to_array(solid))
    if n <= 1:
        return solid
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    keep = 1 + int(np.argmax(sizes))
    return g.from_array(lab == keep)


# ================================================================================================ mass
def mass(con: dict) -> dict:
    """Ledger-style mass of the concept's variable part against H1: printed voxels (solid PAHT-CF + gyroid at
    GYROID_RHO), carbon tubes, bond, fail-safe pins, the z 234 joint hardware; applied as deltas to the 1069.32 g
    print (bl058.json stl) so the voxel/STL raster difference cancels."""
    s0 = baseline_solid()
    v = H ** 3
    pr = con["printed"]
    g_solid0 = float(s0.sum()) * v * RHO_PAHT
    g_print = float((pr & ~con["core"]).sum()) * v * RHO_PAHT + float(con["core"].sum()) * v * RHO_PAHT * GYROID_RHO
    stl_g = json.loads((PACK / "analysis" / "bl058.json").read_text())["stl"]["h1_assembled"]["g"]
    rows = {"print (released STL, bl058.json stl)": stl_g,
            "printed voxel delta (2 mm raster)": round(g_print - g_solid0, 1)}
    if con["name"].startswith("cf"):
        ts = tube_section()
        L = TUBE["z1"] - TUBE["z0"]
        rows["2 carbon tubes 22 x 18 x %.0f mm (record density)" % L] = round(2 * ts["g_per_mm"] * L, 1)
        bond_v = sum(math.pi * TUBE["od"] * BOND_L.get(k, z1 - max(z0, TUBE["z0"])) * BONDLINE.get(k, MMA_T)
                     for k, (z0, z1) in SLEEVES.items()) * 2
        rows["MMA bond, 0.8 mm in P1 (2 x 40 mm bands) / P3, 0.5 mm in P2 (record density 0.98)"] = round(bond_v * 0.98e-3, 1)
        pin = math.pi / 4 * CROSS_PIN_D ** 2 * 30.0 * 4.43e-3 + 0.8        # Ti M4 x 30 shank + head/nut (ASSUMPTION)
        rows["4 fail-safe Ti M4 x 30 cross bolts (P1, P3)"] = round(4 * pin, 1)
        j = json.loads((PACK / "analysis" / "frame_mass_h1.json").read_text())["h1"]["joint_hardware_g"]
        rows["z 234 joint hardware deleted (frame_mass_h1.json)"] = -round(sum(j.values()), 1)
    total = round(sum(rows.values()), 1)
    return {"rows": rows, "frame_print_g": total, "delta_g": round(total - stl_g, 1),
            "raster_printed_g": round(g_print, 1), "raster_h1_g": round(g_solid0, 1)}


# ================================================================================================ check
def _ctx():
    """Context: lane kit sets + the real crown models / caches, exactly as h1_closeout.body ran BL-058."""
    import contextlib
    from . import h1_lanes as LN
    from . import h1_sleeve as S
    from . import h1_spine_channel as SC

    @contextlib.contextmanager
    def cm():
        orig = S.kit_sets
        with SC.real_crown_models(), SC._real_caches():
            S.kit_sets = LN.lane_kit_sets(orig)
            try:
                yield
            finally:
                S.kit_sets = orig
    return cm()


def section_props(u: np.ndarray, v: np.ndarray, w: np.ndarray, h: float = H) -> dict:
    """Weighted voxel section (cells h x h at (u, v), stiffness weight w): A_eff, centroid, I_u, I_v, I_uv and the
    minimum principal I_min (each cell's own h^4/12 included, so a voxelised rectangle gives b d^3 / 12 exactly)."""
    w = np.asarray(w, float)
    a = h * h
    uc, vc = float((w * u).sum() / w.sum()), float((w * v).sum() / w.sum())
    own = a * a / 12.0
    Iu = float((w * ((v - vc) ** 2 * a + own)).sum())
    Iv = float((w * ((u - uc) ** 2 * a + own)).sum())
    Iuv = float((w * (u - uc) * (v - vc) * a).sum())
    Imin = (Iu + Iv) / 2 - math.sqrt(((Iu - Iv) / 2) ** 2 + Iuv ** 2)
    return {"A": float(w.sum() * a), "uc": uc, "vc": vc, "Iu": Iu, "Iv": Iv, "Iuv": Iuv, "Imin": Imin}


def euler_pcr(E: float, I: float, L: float, K: float = 1.0) -> float:
    return math.pi ** 2 * E * I / (K * L) ** 2


def section_buckling(cen, solid_idx_mask_fn, stress, meta, wloc) -> dict:
    """Record rule and section rule for the three team A cuts (per side)."""
    from . import frame_comp_A as A
    c = _base()
    out = {}
    grp_all = c["grp"]
    for name, (gname, ax, cc, L) in A.BUCKLE_CUTS.items():
        lay = solid_idx_mask_fn(grp_all == A.GROUPS.index(gname)) & (np.abs(cen[:, ax] - (cc + H / 2)) <= H / 2 + 1e-6)
        sides = {"all": lay} if ax == 0 else {"L": lay & (cen[:, 0] < 0), "R": lay & (cen[:, 0] > 0)}
        for sd, msk in sides.items():
            P = cen[msk]
            ww = wloc[msk].astype(float)
            if len(P) == 0:
                continue
            o = [i for i in range(3) if i != ax]
            sp = section_props(P[:, o[0]], P[:, o[1]], ww)
            a = H * H
            Aeff, Imin = sp["A"], sp["Imin"]
            pcr_rec = euler_pcr(E_BUCKLE, Aeff ** 2 / (4 * math.pi), L)
            pcr_sec = euler_pcr(E_BUCKLE, Imin, L)
            N = np.array([float((S[msk, ax].astype(float)).sum() * a) for S in stress])
            k = int(np.argmin(N))
            Pc = -float(N[k])
            out[f"{name} {sd}"] = {"A_eff_mm2": round(Aeff, 1), "I_min_mm4": round(Imin), "I_round_mm4": round(Aeff ** 2 / (4 * math.pi)),
                                   "L_mm": L, "P_factored_n": round(Pc, 1), "set": meta[k]["set"],
                                   "Pcr_record_n": round(pcr_rec, 1), "Pcr_section_n": round(pcr_sec, 1),
                                   "margin_record": round(pcr_rec / (1.5 * Pc), 3) if Pc > 0 else None,
                                   "margin_section": round(pcr_sec / (1.5 * Pc), 3) if Pc > 0 else None}
    return out


def tube_checks(f: dict, cf_loc: np.ndarray, meta: list) -> dict:
    """CFRP tube: stress = unit strain field x E_tube (same strain as the voxel ring). Max-stress FI with the
    knock-downs kept (tension Xt x 0.8; compression Xc x 0.8 x 0.65; shear S x 0.8), worst p99 and max over the tube
    voxels outside the load patches; fatigue: FI at 1.6 g on the static-carry sets <= 0.5 (HA-LS-1)."""
    scale = TUBE["E"] / E_PAHT
    Xt = TUBE["Xt"] * TUBE["hot_wet"]
    Xc = TUBE["Xc"] * TUBE["hot_wet"] * TUBE["impact_c"]
    Ss = TUBE["S"] * TUBE["hot_wet"]
    worst = {"strength": (9e9, ""), "strength_max": (9e9, ""), "fatigue": (9e9, "")}
    for S, mt in zip(f["stress"], meta):
        ex = f["ex"][mt["scenario"]]
        m = cf_loc & ~ex
        if m.sum() == 0:
            continue
        s = S[m].astype(float) * scale
        szz = s[:, 2]
        tau = np.hypot(s[:, 4], s[:, 5])
        fi = np.where(szz >= 0, szz / Xt, -szz / Xc) + (tau / Ss) ** 2
        p99, mx = float(np.percentile(fi, 99)), float(fi.max())
        if 1 / p99 < worst["strength"][0]:
            worst["strength"] = (1 / p99, mt["set"])
        if 1 / mx < worst["strength_max"][0]:
            worst["strength_max"] = (1 / mx, mt["set"])
        if mt["case"] == "static_carry":
            fi16 = p99 * 1.6 / mt["factor"]
            if 0.5 / fi16 < worst["fatigue"][0]:
                worst["fatigue"] = (0.5 / fi16, mt["set"])
    return {k: {"margin": round(v[0], 3), "set": v[1]} for k, v in worst.items()}


TUBE_CUTS = (100.0, 192.0, 250.0, 306.0, 354.0, 436.0, 468.0, 520.0)   # bare-tube cuts between the sleeves


def tube_resultants(f: dict, cf_loc: np.ndarray, meta: list) -> dict:
    """Tube section resultants (real tube stresses) at z cuts, per side and set: N (N), Mx, My (N mm about the tube
    axis), Vx, Vy (N), T (N mm; the voxel ring is about 2.3x too stiff in torsion, tube_section, so T is an upper
    bound on what the tube attracts)."""
    scale = TUBE["E"] / E_PAHT
    cen = f["cen"]
    out = {}
    a = H * H
    for sd, sg in (("R", 1.0), ("L", -1.0)):
        for zc in TUBE_CUTS:
            m = cf_loc & (np.sign(cen[:, 0]) == sg) & (np.abs(cen[:, 2] - (zc + 1.0)) < H / 2 + 1e-6)
            if m.sum() == 0:
                continue
            dx = cen[m, 0] - sg * TUBE["x"]
            dy = cen[m, 1] - TUBE["y"]
            rows = []
            for S in f["stress"]:
                s = S[m].astype(float) * scale
                rows.append([float(s[:, 2].sum() * a), float((s[:, 2] * dy).sum() * a), float((s[:, 2] * dx).sum() * a),
                             float(s[:, 5].sum() * a), float(s[:, 4].sum() * a),
                             float((dx * s[:, 4] - dy * s[:, 5]).sum() * a)])
            out[f"{sd}|{zc:g}"] = np.array(rows)
    return out


# sleeve -> (cut below, cut above) on the bare tube; None = the tube's free end (resultant 0)
SLEEVE_CUTS = {"P1 lower node": (None, 192.0), "P2 lower-branch root": (192.0, 250.0),
               "P2 mid-bar knuckle": (306.0, 354.0), "P2 upper-branch root": (436.0, 468.0),
               "P3 top node": (468.0, None)}
BEARING_PAHT = 47.0 * 0.8           # MPa: Z tensile strength x 0.8 as a bearing floor (ASSUMPTION SLEEVE-BEARING)


def bonds(name: str, bases=BASES) -> dict:
    """Tube-to-sleeve joints of a carbon-stay concept, from the tube resultants of every set: transferred axial
    force dN and moment dM over each sleeve (difference of the bare-tube cuts that bound it).
    - shear: dN / (2 pi r) line load over the sleeve length, Volkersen peak with the PAHT-CF sleeve (3 mm) as the soft
      adherend; average >= 1 at the factored load, peak >= 1 at limit (factored / case factor), fatigue: 1.6 g
      static-carry average <= 0.3 x the dry allowable (HA-LS-1 as frame_light2 applies it). Allowable 5.0 x 0.8 = 4.0 MPa (ASSUMPTION BOND-PA);
    - moment: by bearing of the tube on the sleeve over its length, p = 6 dM / (d L^2) against BEARING_PAHT;
    - fail-safe: one Ti M4 cross bolt in P1 and P3 carries dN and the torque alone at the limit load (factor 1.0
      on limit), bearing in the tube's two walls against TUBE_BEARING_MPA (ASSUMPTION TUBE-BEARING)."""
    from huntkit.fea.joints import volkersen_factor
    r = TUBE["od"] / 2
    t = (TUBE["od"] - TUBE["id"]) / 2
    allow = BOND_PA_MPA * BOND_HOT_WET
    E1t, E2t = TUBE["E"] * t, E_PAHT * 3.0
    out = {}
    for sl, (lo, hi) in SLEEVE_CUTS.items():
        z0, z1 = SLEEVES[sl]
        L = BOND_L.get(sl, z1 - max(z0, TUBE["z0"]))
        if sl in BOND_L:
            L = L / 2              # two bands: checked as if the nearer band took the whole transfer (conservative)
        om = math.sqrt(MMA_G_MPA / BONDLINE.get(sl, MMA_T) * (1 / E1t + 1 / E2t))
        k = volkersen_factor(om * L, min(E1t, E2t) / max(E1t, E2t))
        w = {"avg": (9e9, ""), "peak": (9e9, ""), "peak_ultimate_info": (9e9, ""), "fatigue": (9e9, ""),
             "bearing": (9e9, ""), "pin": (9e9, "")}
        for b in bases:
            p = OUT / f"tube_{name}_{b}.npz"
            if not p.exists():
                continue
            z = np.load(p)
            meta = [json.loads(m) for m in z["meta"]]
            for sd in ("R", "L"):
                A = z[f"{sd}_{lo:g}"] if lo is not None else 0.0
                B = z[f"{sd}_{hi:g}"] if hi is not None else 0.0
                d = np.asarray(B) - np.asarray(A) if not (np.isscalar(A) and np.isscalar(B)) else None
                if d is None:
                    continue
                if d.ndim == 1:
                    d = d[None, :]
                for i, mt in enumerate(meta):
                    dN = abs(float(d[i, 0]))
                    dM = float(np.hypot(d[i, 1], d[i, 2]))
                    dT = abs(float(d[i, 5])) if d.shape[1] > 5 else 0.0
                    tau = math.hypot(dN / (2 * math.pi * r), dT / (2 * math.pi * r * r)) / L
                    pb = 6 * dM / (TUBE["od"] * L ** 2)
                    tag = f"{b}|{sd}|{mt['set']}"
                    # HA-LS-1 4: Volkersen peak >= 1 at LIMIT load (limit cases, factor > 1); the ultimate cases
                    # C7 / C8 (factor 1.0) are judged on the average (toughened MMA yields and redistributes); their
                    # peak is kept as information ("peak_ultimate_info")
                    pk = allow / max(k * tau / mt["factor"], 1e-9)
                    for key, val in (("avg", allow / max(tau, 1e-9)),
                                     ("peak" if mt["factor"] > 1.0 else "peak_ultimate_info", pk),
                                     ("bearing", BEARING_PAHT / max(pb, 1e-9))):
                        if val < w[key][0]:
                            w[key] = (val, tag)
                    if mt["case"] == "static_carry":       # HA-LS-1 / frame_light2: average shear <= 0.3 x dry
                        v = 0.3 * BOND_PA_MPA / max(tau * 1.6 / mt["factor"], 1e-9)
                        if v < w["fatigue"][0]:
                            w["fatigue"] = (v, tag)
                    if sl in ("P1 lower node", "P3 top node"):
                        # each tube wall bears half the axial force plus the torque couple T / OD
                        Fw = math.hypot(dN / 2, dT / TUBE["od"]) / mt["factor"]
                        v = TUBE_BEARING_MPA / max(Fw / (CROSS_PIN_D * t), 1e-9)
                        if v < w["pin"][0]:
                            w["pin"] = (v, tag)
        out[sl] = {"L_mm": L, "volkersen_k": round(k, 2),
                   **{kk: {"margin": round(float(v[0]), 2) if v[0] < 9e8 else None, "where": v[1]} for kk, v in w.items()}}
    return out


def check(name: str, bases=BASES, log=print, refresh: bool = False, con: dict | None = None) -> dict:
    """The BL-058 whole-body check on a concept (sanded stays, 4 bases). Cached OUT/check_<name>.json. ``con``: a
    prebuilt concept dict (as ``build`` returns) for bodies defined outside CONCEPTS (BL-065 fix)."""
    from . import frame_comp_d as D
    from . import frame_h1 as H1
    from . import h1_closeout as C
    from . import h1_sleeve as S
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"check_{name}.json"
    res = json.loads(p.read_text()) if (p.exists() and not refresh) else {"name": name}
    todo = [b for b in bases if b not in res]
    if not todo:
        return res
    con = build(name) if con is None else con
    c = _base()
    res["mass"] = mass(con)
    res["info"] = {k: v for k, v in con["info"].items()}
    utils = {}
    with _ctx():
        for b in todo:
            t0 = time.time()
            basis, cyc = b.split(".")[0], b.endswith(".cyc")
            sets = S.kit_sets(basis, cycled=cyc)
            f = S.solve_fields_w(c["dom"], con["solid"], sets, con["weight"] if (con["weight"] != 1).any() else None)
            idx = f["idx"]
            wl = con["weight"][idx].astype(np.float32)
            core_l, cf_l = con["core"][idx], con["cf"][idx]
            stay = C.stay_mask(f["cen"]) & ~cf_l
            phys = []
            for st in f["stress"]:
                st *= wl[:, None]                       # physical stress (unit-modulus strain x relative modulus)
                st[stay] *= np.float32(SAND_K)          # sanded stays (BL-055 rule)
                phys.append(st)
            sb = section_buckling(f["cen"], lambda m: m[idx], phys, f["meta"], wl)
            tc = tube_checks({**f, "stress": [s / wl[:, None] for s in phys]}, cf_l, f["meta"]) if cf_l.any() else None
            tr = tube_resultants({**f, "stress": [s / wl[:, None] for s in phys]}, cf_l, f["meta"]) if cf_l.any() else None
            jc = H1.joint_check({**f, "stress": phys}) if con["joint"] else None
            # FI population: printed voxels; gyroid core against its own strength; tubes out
            fi_stress = []
            for st in phys:
                q = st.copy()
                if core_l.any():
                    q[core_l] /= np.float32(S_GYROID)
                fi_stress.append(q)
            ff = {**f, "stress": fi_stress}
            r = S.evaluate(ff, cf_l if cf_l.any() else None)
            utils[b] = (np.asarray(r["util"], np.float32), idx)
            res[b] = {"min": r["min"], "per_tag": r["per_tag"], "governing_tag": r["governing_tag"],
                      "top_regions": r["top_regions"], "buckling": sb,
                      "buckling_record_min": min(v["margin_record"] for v in sb.values() if v["margin_record"]),
                      "buckling_section_min": min(v["margin_section"] for v in sb.values() if v["margin_section"]),
                      "joint_strength": float(jc["min_strength"]) if jc else None,
                      "joint_fatigue": float(jc["min_fatigue"]) if jc else None,
                      "tube": tc, "seconds": round(time.time() - t0)}
            if tr is not None:
                np.savez_compressed(OUT / f"tube_{name}_{b}.npz", **{k.replace("|", "_"): v for k, v in tr.items()},
                                    meta=np.array([json.dumps(m) for m in f["meta"]]))
            # gyroid core: own check (peak core FI against the gyroid strength), reported
            if core_l.any():
                worst = 9e9
                for st, mt in zip(fi_stress, f["meta"]):
                    ex = f["ex"][mt["scenario"]]
                    fi = D.fi_material(st[core_l & ~ex].astype(float), D.MATERIALS[H1.MAT])
                    worst = min(worst, 1 / max(float(np.percentile(fi, 99)), 1e-9))
                res[b]["core_p99_strength"] = round(worst, 3)
            res["raster_g"] = D.mass_g(con["solid"], H, 1060.0)
            p.write_text(json.dumps(res, default=_jd))
            if log:
                log(f"[{time.strftime('%H:%M:%S')}] {name} {b}: {json.dumps(r['min'], default=float)} buckling rec "
                    f"{res[b]['buckling_record_min']:.3f} sec {res[b]['buckling_section_min']:.3f} "
                    f"joint {res[b]['joint_strength']} tube {json.dumps(tc)} ({res[b]['seconds']} s)")
            del f, phys, fi_stress, ff
    # utilisation fields: max over the static bases, and the cyc basis on its own
    st = [utils[b] for b in utils if not b.endswith(".cyc")]
    if st:
        _merge_util(OUT / f"util_{name}.npz", st)
    if "fine_sm8.cyc" in utils:
        _merge_util(OUT / f"util_{name}_cyc.npz", [utils["fine_sm8.cyc"]], replace=True)
    return res


def _merge_util(path: Path, items: list, replace: bool = False):
    idx = items[0][1]
    u = np.max(np.vstack([it[0] for it in items]), axis=0)
    if path.exists() and not replace:
        z = np.load(path)
        if np.array_equal(z["idx"], idx):
            u = np.maximum(u, z["util"])
    np.savez_compressed(path, util=u, idx=idx)


def _jd(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def summary(res: dict) -> dict | None:
    """Governing margins as BL-058 reports them: static-cinch = min over fine_sm8 / fine / beam, cinch-cycled =
    fine_sm8.cyc."""
    if not all(b in res for b in BASES):
        return None
    st = [b for b in BASES if not b.endswith(".cyc")]
    key = ("strength", "fatigue", "creep")
    out = {"static_cinch": {k: round(min(res[b]["min"][k] for b in st), 3) for k in key},
           "cinch_cycled": {k: round(res["fine_sm8.cyc"]["min"][k], 3) for k in key}}
    for nm, bs in (("static_cinch", st), ("cinch_cycled", ["fine_sm8.cyc"])):
        out[nm]["buckling_record"] = round(min(res[b]["buckling_record_min"] for b in bs), 3)
        out[nm]["buckling_section"] = round(min(res[b]["buckling_section_min"] for b in bs), 3)
        js = [res[b]["joint_strength"] for b in bs if res[b]["joint_strength"] is not None]
        jf = [res[b]["joint_fatigue"] for b in bs if res[b]["joint_fatigue"] is not None]
        out[nm]["joint_strength"] = round(min(js), 3) if js else None
        out[nm]["joint_fatigue"] = round(min(jf), 3) if jf else None
        tb = [res[b]["tube"] for b in bs if res[b].get("tube")]
        if tb:
            out[nm]["tube_strength"] = round(min(t["strength"]["margin"] for t in tb), 3)
            out[nm]["tube_fatigue"] = round(min(t["fatigue"]["margin"] for t in tb), 3)
        co = [res[b]["core_p99_strength"] for b in bs if "core_p99_strength" in res[b]]
        if co:
            out[nm]["gyroid_core"] = round(min(co), 3)
    return out


def main(argv=None) -> int:  # pragma: no cover
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    if a and a[0] == "check":
        for n in a[1:]:
            check(n)
        return 0
    if a and a[0] == "all":
        for n in CONCEPTS:
            check(n)
        return 0
    from . import frame_iter1_report as R
    R.report()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
