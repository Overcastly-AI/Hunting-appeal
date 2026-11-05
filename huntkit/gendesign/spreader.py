"""Spreader (BP-06) v2: verify the 2.0 mm QI sheet on the real branch frame, pick a lighter part,
detail it for water-jet / CNC, and write the records.

The sheet is a plate on the bag face of the stays. It is modelled as an ACM Kirchhoff plate
(``huntkit.fea.plate_grid``) on the supports the branch frame really has:

- the stay crowns (rigid, unilateral; the sheet can lift off),
- the inboard branches and the z 330 bar (PAHT beams, hot/wet modulus, unilateral contact with the
  gap read from the frame's own distance field),
- clips (bilateral) where the part is clipped, and the M4 bolts of the old drawing where they land.

The frame sits on the XLPE rails. Skin pressure and the rail compression come from a 1-D
nonlinear Pasternak model of the rail (``rail_section``): rigid stay cylinder, aged foam with the
cited L200 compression curve, soft tissue in series. The rail compression and the tissue bulge
into the gutter set the real clearance between the sheet and the back.

Loads: HA-LS-1 rev B C5 (meat on the internal straps), walking 1.6 g and factored 2.0 g x 1.5,
the strap cinch preload, and a bone end (20 % of 68 kg on a 22 mm patch) at many positions.

Run: python -m huntkit.gendesign.spreader
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from huntkit.fea.composite import DEFAULT_KNOCKDOWN, Laminate, Ply
from huntkit.fea.materials_bridge import REPO_ROOT
from huntkit.fea.plate_grid import Beam, GridPlate, Spring, laminate_bending_fi
from huntkit.materials import load

DATE = "20261101"
TAG = "spreader2"
G = 9.80665
SCALE = 1.05                      # branch frame scale (generative_branch_results.json)
STAY_X = 115.0
Z_LO, Z_HI = 130.0, 430.0         # old sheet height on the frame
Z_LO_V2 = 112.0                   # v2 bottom edge: below the US2 cleat, so the bottom bay has a crown support
BONE_D = 22.0
BONE_SHARE = 0.20
KD = DEFAULT_KNOCKDOWN            # hot/wet 0.8, impact 0.65 on compression
PAHT_HOT_WET = 0.6                # modulus_40c_wet_ratio, pa12_cf_fdm_paht
FAIRLEADS_Z = (60.0, 95.0, 142.0, 190.0, 330.0, 520.0)   # bag_attach.stations()
FAIRLEAD_HALF_X = 17.0            # throat 18 / 2 + cheek 8
FAIRLEAD_HALF_Z = 9.0
NOTCH_CLEAR = 6.0                 # air around a cleat: 4.5 mm root blend (frame_sdf smin) + 1.5 mm
RAIL_W, RAIL_L, RAIL_T = 100.0, 420.0, 10.0
RAIL_Z = (50.0, 470.0)
GUTTER_HALF = STAY_X - RAIL_W / 2.0                       # 65 mm: rail inner edge
# Torso lateral radius at the shoulder blades. ASSUMPTION: an ellipse with ANSUR II-class chest
# breadth ~320 mm and depth ~240 mm has a radius a^2/b ~ 230 mm at the spine. 150 mm is the
# sensitivity (lean, curved back).
R_TORSO = 230.0
R_TORSO_LO = 150.0
# Soft tissue under the rail. Effective indentation moduli 10-90 kPa (umbilicus 11-13 kPa,
# lower limb 10.4-89.2 kPa; research doc). ASSUMPTION: 25 mm column, 60 kPa design value
# (stiff end = less spreading = higher peak), 20 kPa soft sensitivity.
TISSUE_H = 25.0
TISSUE_E_KPA = 60.0
TISSUE_E_SOFT_KPA = 20.0
PEAK_KPA = 14.0                   # Golriz et al. 2017 (back_comfort.md)
# ASSUMPTION: the spacer mesh over the gutter lies on the skin and is 3 mm thick. At the 1.6 g walking
# peak the sheet must stay 3 mm off the skin (it never presses the mesh). At the factored 3.0 g case it
# must not touch the skin at all (clearance >= 0) on the design torso (R 230 mm).
MESH_T = 3.0
FAT_FI = 0.5                      # HA-LS-1: CFRP FI <= 0.5 at the 1.6 g walking peak
SCREENS = REPO_ROOT / "outputs" / "screens"
DOC_SCREENS = REPO_ROOT / "docs" / "screens"
ANALYSIS = REPO_ROOT / "designs" / "pack_5200" / "analysis"
OUT = REPO_ROOT / "outputs" / "spreader"
CUT = REPO_ROOT / "designs" / "pack_5200" / "cut" / "spreader"
PRINT = REPO_ROOT / "designs" / "pack_5200" / "print" / "frame"


# ============================================================================ loads
def meat_normal_n(g_level: float = 1.6) -> float:
    from .frame_smooth import meat_normal_n as mn
    return mn(g_level)


def bone_n(kind: str) -> float:
    m = BONE_SHARE * 68.0 * G
    return {"walk": m * 1.6, "factored": m * 2.0 * 1.5, "static": m}[kind]


CINCH_N_PER_ANCHOR = 150.0        # HA-LS-1 4.1, six anchors (IM1-IM3, both sides)
FACE_W = 2.0 * STAY_X             # meat contact width on the frame face


def meat_pressure(z: np.ndarray, kind: str, less_n: float = 0.0) -> np.ndarray:
    """Face pressure on the sheet, MPa. Rev B: overturning triangular z 60-330 (peak at the
    bottom) plus the strap cinch spread uniformly over z 60-560.

    ``less_n``: a bone end is part of the meat, not extra meat. Its force is taken out of the
    overturning resultant so the total normal force on the back stays the rev B couple
    (ASSUMPTION; the v1 study added it on top)."""
    g, f_over, f_cinch = {"walk": (1.6, 1.0, 1.0), "factored": (2.0, 1.5, 1.5)}[kind]
    H = max(meat_normal_n(g) * f_over - less_n, 0.0)
    p0 = 2.0 * H / (270.0 * FACE_W)
    tri = p0 * np.clip((330.0 - z) / 270.0, 0.0, None)
    cinch = 6.0 * CINCH_N_PER_ANCHOR * f_cinch / (500.0 * FACE_W)
    return tri + cinch


# ============================================================================ laminates
def _t700():
    return Ply.from_material("cfrp_t700_ud_epoxy_ply")


def _twill(t=0.22):
    return Ply.from_material("cfrp_t300_3k_woven_epoxy_ply", t)


def _glass():
    return Ply.from_material("gfrp_eglass_ud_epoxy_ply")


def core_ply(mid: str, t: float) -> Ply:
    m = load(mid)
    E = float(m.require("tensile_modulus_mpa"))
    nu = float(m.get("poisson", 0.3))
    Gc = float(m.require("shear_modulus_mpa"))
    return Ply(E1=E, E2=E, G12=E / (2 * (1 + nu)), nu12=nu, Xt=float(m.require("tensile_strength_mpa")),
               Xc=float(m.require("compressive_strength_mpa")), Yt=float(m.require("tensile_strength_mpa")),
               Yc=float(m.require("compressive_strength_mpa")), S=float(m.require("shear_strength_mpa")),
               t=t, density_kg_m3=float(m.require("density_kg_m3")), name=mid)


def lam_from(plies_angles) -> Laminate:
    plies = [p for p, _ in plies_angles]
    ang = [a for _, a in plies_angles]
    return Laminate(plies, ang)


def qi_lam(t: float, ply=None) -> Laminate:
    """[0/45/90/-45]ns (0 along the span, frame x). 1.5 mm uses [0/60/-60]2s."""
    p = ply or _t700()
    n_ply = int(round(t / p.t))
    if n_ply % 8 == 0:
        half = [0, 45, 90, -45] * (n_ply // 8)
    elif n_ply % 6 == 0:
        half = [0, 60, -60] * (n_ply // 6)
    else:
        raise ValueError(f"no QI stack for {t} mm")
    ang = half + half[::-1]
    return Laminate([p] * len(ang), ang)


def sandwich_lam(core_id: str, core_t: float, skin=("twill", 1)) -> Laminate:
    kind, n = skin
    if kind == "twill":
        sk = [(_twill(), 0.0)] * n
    else:
        sk = [(_t700(), 0.0), (_t700(), 90.0)][:n]
    return lam_from(sk + [(core_ply(core_id, core_t), 0.0)] + sk[::-1])


DOUBLER_X = 76.0                  # doubler zone: |x| >= 76 mm (notch roots at 92, tabs, clip slots)
DOUBLER_DZ = 14.0                 # and within notch half-height + 14 mm of each cleat station


def doubler_mask(exy: np.ndarray) -> np.ndarray:
    m = np.zeros(exy.shape[:2], bool)
    hz = FAIRLEAD_HALF_Z + NOTCH_CLEAR
    for zf in (142.0, 190.0, 330.0):
        m |= (np.abs(exy[..., 0]) >= DOUBLER_X) & (np.abs(exy[..., 1] - zf) <= hz + DOUBLER_DZ)
    return m


def doubler_zone():
    """Doubler patches as shapely geometry, clipped to the part (for mass and the drawing)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    hz = FAIRLEAD_HALF_Z + NOTCH_CLEAR
    bs = [box(min(s * DOUBLER_X, s * 130.0), zf - hz - DOUBLER_DZ, max(s * DOUBLER_X, s * 130.0), zf + hz + DOUBLER_DZ)
          for s in (1.0, -1.0) for zf in (142.0, 190.0, 330.0)]
    return unary_union(bs).intersection(outline_v2())


def doubler_lam(opt: "Option") -> Laminate:
    """Skins become [0 / 45] twill in the doubler zone (one 45 deg ply added on the core side)."""
    if not opt.core:
        return opt.lam
    sk = [(_twill(), 0.0), (_twill(), 45.0)]
    return lam_from(sk + [(core_ply(opt.core, opt.core_t), 0.0)] + sk[::-1])


RESIN_SANDWICH_KG_M2 = 0.06       # ASSUMPTION: extra resin to wet the cut core cells, both faces


@dataclass
class Option:
    key: str
    name: str
    family: str
    lam: Laminate
    note: str = ""
    beads: dict | None = None      # {"pitch", "width", "depth"} along the span (x)
    perforated: bool = False
    core: str | None = None        # sandwich core material id
    core_t: float = 0.0
    skin_t: float = 0.0
    extra_kg_m2: float = 0.0
    buy: str = ""
    usd_m2: float = 0.0            # material cost for the cost table
    tubes: bool | tuple = True     # bonded edge tubes: True = EDGE_TUBES, False = none, or ((z, OD, ID), ...)
    pucks: bool = True             # bonded pucks onto the branches and the bar (v2 outline)
    edge_seal: bool = False        # sandwich: sealed core edge (brushed epoxy)
    doubler: bool = False          # sandwich: one extra 45 deg twill ply per skin around the cleat notches
    results: dict = field(default_factory=dict)

    @property
    def t(self) -> float:
        return self.lam.thickness + (self.beads or {}).get("depth", 0.0) * 0.0

    def areal_kg_m2(self) -> float:
        a = self.lam.areal_mass_kg_m2() + self.extra_kg_m2
        if self.beads:
            b = self.beads
            # developed length of a shallow circular bead: chord w, rise d -> w (1 + 8/3 (d/w)^2)
            stretch = 1.0 + (8.0 / 3.0) * (b["depth"] / b["width"]) ** 2
            a *= 1.0 + (stretch - 1.0) * b["width"] / b["pitch"]
        return a


def options() -> list[Option]:
    """Candidates on the v2 outline. All carry the two bonded edge tubes and the pucks unless noted."""
    def sw(key, name, core, ct, doubler=False, note=""):
        return Option(key, name, "sandwich", sandwich_lam(core, ct), note, core=core, core_t=ct, skin_t=0.22,
                      extra_kg_m2=RESIN_SANDWICH_KG_M2, edge_seal=True, doubler=doubler,
                      buy="vacuum-bagged in-house (twill + PMI), CNC-routed")
    return [
        Option("qi20", "QI carbon 2.0 mm (current material)", "monolithic", qi_lam(2.0),
               "the 193 g sheet's laminate on the new outline", buy="bought plate, water-jet"),
        Option("qi15", "QI carbon 1.5 mm", "monolithic", qi_lam(1.5), buy="bought plate, water-jet"),
        Option("qi10", "QI carbon 1.0 mm", "monolithic", qi_lam(1.0), buy="bought plate, water-jet"),
        Option("b10", "Span-biased carbon 1.0 mm [0/90/0/0]s", "monolithic",
               Laminate([_t700()] * 8, [0, 90, 0, 0, 0, 0, 90, 0]), "custom press-cured layup"),
        Option("tw10", "Twill carbon 1.0 mm (4 x 200 g 2x2 twill)", "monolithic",
               Laminate([_twill(0.25)] * 4, [0, 45, 45, 0]), "SendCutSend-class stock sheet, 1.02 mm",
               buy="SendCutSend 0.040 in carbon, water-jet"),
        Option("bd10", "QI carbon 1.0 mm + 3 span beads (5 mm)", "beaded", qi_lam(1.0),
               "needs a matched press tool", beads={"pitch": 75.0, "width": 24.0, "depth": 5.0}),
        sw("sw71c5", "Sandwich: 200 g twill skins on 5 mm ROHACELL 71", "rohacell_71_igf", 5.0),
        sw("sw110c5", "Sandwich: 200 g twill skins on 5 mm ROHACELL 110", "rohacell_110_igf", 5.0),
        sw("sw110c3d", "Sandwich: twill / 3 mm ROHACELL 110, notch doublers", "rohacell_110_igf", 3.0, True),
        sw("sw110c4d", "Sandwich: twill / 4 mm ROHACELL 110, notch doublers", "rohacell_110_igf", 4.0, True),
        sw("sw110c5d", "Sandwich: twill / 5 mm ROHACELL 110, notch doublers", "rohacell_110_igf", 5.0, True),
        sw("sw110c6d", "Sandwich: twill / 6 mm ROHACELL 110, notch doublers", "rohacell_110_igf", 6.0, True),
        Option("g20", "Glass (G10-class) QI 2.0 mm", "monolithic", qi_lam(2.0, _glass()), "cost variant",
               buy="bought G10 sheet, water-jet"),
        Option("g30", "Glass (G10-class) QI 3.0 mm", "monolithic", qi_lam(3.0, _glass()), "cost variant",
               buy="bought G10 sheet, water-jet"),
    ]


# ============================================================================ geometry
def sleeve_y(z):
    from .frame_branch import _sleeve_y
    return np.asarray(_sleeve_y(np.asarray(z, float)), float)


def stay_r(z):
    from .frame_branch import stay_radius
    return np.asarray(stay_radius(np.asarray(z, float), SCALE), float)


def branch_x(z):
    """Inboard branch centreline |x| (frame_branch.frame_sdf)."""
    t = np.clip((np.asarray(z, float) - 165.0) / 320.0, 0.0, 1.0)
    return 115.0 - 46.0 * np.sin(np.pi * t)


NOTCH_ROOT_R = 6.0                # notch root corner radius (>= 3 t, and the water-jet inside-corner rule)
BOTTOM_CORNER_R = 8.0             # bottom corners: the z 119 clip tab sits 7 mm above the edge


def outline_v2(half_w: float = 121.0, corner_r: float = 20.0, z_lo: float = Z_LO_V2):
    """New outline: edges land on the stay crowns, U-notches at the cleats, round corners."""
    from shapely.geometry import Point, box
    from shapely.ops import unary_union
    body = box(-half_w, z_lo, half_w, Z_HI)
    hz = FAIRLEAD_HALF_Z + NOTCH_CLEAR                     # 12 mm half-height
    x_in = STAY_X - FAIRLEAD_HALF_X - NOTCH_CLEAR         # 95 mm: notch bottom
    cuts = []
    for s in (1.0, -1.0):
        for zf in FAIRLEADS_Z:
            if zf + hz < z_lo or zf - hz > Z_HI:
                continue
            # U-notch, straight sides, NOTCH_ROOT_R root corners: clears the cleat footprint by
            # NOTCH_CLEAR on all three sides (bag_attachment.md stations)
            rect = box(min(s * x_in, s * 150.0), zf - hz, max(s * x_in, s * 150.0), zf + hz)
            cuts.append(rect.buffer(-NOTCH_ROOT_R, join_style=2).buffer(NOTCH_ROOT_R, 32))
    shape = body.difference(unary_union(cuts))
    # outside corners round, inside corners filleted (R5): open then close
    shape = shape.buffer(-5.0, join_style=1).buffer(5.0, join_style=1)
    # big top corners
    tl = box(-half_w, Z_HI - corner_r, -half_w + corner_r, Z_HI).difference(
        Point(-half_w + corner_r, Z_HI - corner_r).buffer(corner_r, 64))
    tr = box(half_w - corner_r, Z_HI - corner_r, half_w, Z_HI).difference(
        Point(half_w - corner_r, Z_HI - corner_r).buffer(corner_r, 64))
    shape = shape.difference(tl).difference(tr)
    rb = BOTTOM_CORNER_R
    bl = box(-half_w, z_lo, -half_w + rb, z_lo + rb).difference(Point(-half_w + rb, z_lo + rb).buffer(rb, 48))
    br = box(half_w - rb, z_lo, half_w, z_lo + rb).difference(Point(half_w - rb, z_lo + rb).buffer(rb, 48))
    shape = shape.difference(bl).difference(br)
    return shape.simplify(0.05)


def outline_v1():
    """Retired v1 drawing: 208 x 300, square corners, 22 mm notches (the v1 attachment note; v2 notches are 30 mm)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    body = box(-104.0, Z_LO, 104.0, Z_HI)
    cuts = [box(min(s * 96.0, s * 110.0), zf - 11.0, max(s * 96.0, s * 110.0), zf + 11.0)
            for s in (1.0, -1.0) for zf in (142.0, 190.0, 330.0)]
    return body.difference(unary_union(cuts))


CLIP_Z = (166.0, 260.0, 400.0)  # stay segments clear of cleats: 157-175, 205-315, 345-430
# z 119: the bottom tab (z 112-130) is too short for a slot. The stay is r 9 there, 4.5 mm below the
# sheet, so a bonded PAHT stand-off pad carries the tab instead of a clip.
PAD_Z = (119.0,)
CLIP_W_BY_Z: dict = {}
# z 119: the stay is r 9 there, 4.5 mm below the sheet. That clip carries a stand-off pad under the sheet.
CLIP_STANDOFF: tuple = ()
CLIP_W = 10.0
CLIP_MAT = "pa12_mjf_hp"          # MJF PA12 clips: 20 % elongation for the snap, bought printed


@lru_cache(maxsize=8)
def frame_top(h: float, x_lo: float = -124.0, x_hi: float = 124.0, z_lo: float = Z_LO):
    """Height (frame y) of the frame's bag-side surface under each plate node, from the frame SDF.

    Returns (xs, zs, top) with NaN where no frame material lies within reach (y > -40)."""
    from .frame_branch import frame_sdf
    xs = np.arange(x_lo, x_hi + 1e-6, h)
    zs = np.arange(z_lo, Z_HI + 1e-6, h)
    ys = np.arange(34.0, -40.0, -1.0)
    X, Z, Y = np.meshgrid(xs, zs, ys, indexing="ij")
    s = frame_sdf(np.c_[X.ravel(), Y.ravel(), Z.ravel()], scale=SCALE).reshape(X.shape)
    inside = s <= 0.0
    hit = inside.any(axis=2)
    k = np.argmax(inside, axis=2)
    hi = ys[np.maximum(k - 1, 0)]
    lo = ys[k]
    # bisection for 0.06 mm
    ii, jj = np.nonzero(hit)
    a, b = hi[ii, jj].copy(), lo[ii, jj].copy()
    for _ in range(4):
        m = (a + b) / 2
        sm = frame_sdf(np.c_[xs[ii], m, zs[jj]], scale=SCALE)
        a = np.where(sm > 0, m, a)
        b = np.where(sm > 0, b, m)
    top = np.full(hit.shape, np.nan)
    top[ii, jj] = (a + b) / 2
    return xs, zs, top


def clip_k(width: float = CLIP_W) -> float:
    """Lift-off stiffness of one clip bridge (N/mm): cantilever 10 mm long, 2.5 mm thick."""
    E = float(load(CLIP_MAT).require("youngs_modulus_mpa"))
    I = width * CLIP_T ** 3 / 12.0
    return 3.0 * E * I / CLIP_TONGUE ** 3


CLIP_T = 2.5
CLIP_TONGUE = 10.0
LAND_FIT = 0.3                    # mm: printed lands on the branch / bar tops, fit gap to the sheet


PUCK_D = 16.0
PUCK_BRANCH_Z = (240.0, 285.0, 365.0, 405.0)
PUCK_BAR_X = (-36.0, 0.0, 36.0)


def _pucks():
    return pucks()


def pucks() -> list[tuple[float, float]]:  # noqa: D401
    """Printed PAHT-CF pucks bonded to the wearer face of the sheet where it crosses a branch or the bar.
    Each is machined to the local gap minus LAND_FIT, so the sheet bears on the branch at once."""
    pts = [(s * float(branch_x(z)), z) for s in (1.0, -1.0) for z in PUCK_BRANCH_Z]
    pts += [(x, 330.0) for x in PUCK_BAR_X]
    return pts


def _near_puck(x: float, z: float) -> bool:
    return any(np.hypot(x - px, z - pz) <= PUCK_D / 2 + 1e-6 for px, pz in pucks())


def _member(x: float, z: float) -> str:
    if 165.0 < z < 485.0 and abs(abs(x) - branch_x(z)) <= 8.0 and abs(x) < 103.0:
        return "branch"
    if abs(z - 330.0) <= 8.0 and abs(x) <= 108.0:
        return "bar"
    return "other"


EDGE_TUBES = ((118.5, 10.0, 8.0), (424.0, 10.0, 8.0))   # (z, OD, ID): pultruded tubes on the bag face


def tube_EI(od: float, idd: float) -> float:
    E = float(load("cfrp_pultruded_rod_tube").require("E1_mpa"))
    return E * np.pi * (od ** 4 - idd ** 4) / 64.0


def tube_mass_g(od: float, idd: float, length: float) -> float:
    rho = float(load("cfrp_pultruded_rod_tube").require("density_kg_m3"))
    return np.pi / 4.0 * (od ** 2 - idd ** 2) * length * rho / 1e6


def build_plate(opt: Option, h: float = 4.0, shape=None, version: str = "v2", holes_mask=None,
                lands: bool = True, tubes=None):
    """Plate model on the branch frame. Returns (plate, info)."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    shape = shape or (outline_v2() if version == "v2" else outline_v1())
    minx, miny, maxx, maxy = shape.bounds
    x0 = np.floor(minx / h) * h
    nx = int(np.ceil((maxx - x0) / h))
    z_lo = np.floor(miny / h) * h
    ny = int(np.ceil((Z_HI - z_lo) / h))
    ps = prep(shape)
    pl = GridPlate(x0, z_lo, nx, ny, h, opt.lam.D)
    exy = pl.elem_xy()
    act = np.array([[ps.contains(Point(*exy[i, j])) for j in range(ny)] for i in range(nx)])
    if holes_mask is not None:
        act &= ~holes_mask
    pl.active = act
    D = np.broadcast_to(opt.lam.D, (nx, ny, 3, 3)).copy()
    bead = np.zeros((nx, ny), bool)
    if opt.beads:
        b = opt.beads
        zc = 225.0 + b["pitch"] * np.arange(-2, 3)
        zc = zc[(zc > miny + 30) & (zc < Z_HI - 30)]
        for z in zc:
            bead |= np.abs(exy[..., 1] - z) <= b["width"] / 2
        bead &= np.abs(exy[..., 0]) < 100.0
        t = opt.lam.thickness
        I_bead = t * b["depth"] ** 2 / 8.0 + t ** 3 / 12.0          # per width, shallow arc
        f = I_bead / (t ** 3 / 12.0)
        D[bead, 0, 0] *= f
    dbl = np.zeros((nx, ny), bool)
    if opt.doubler and version == "v2":
        dbl = doubler_mask(exy)
        D[dbl] = doubler_lam(opt).D
    pl.D = D
    info = {"shape": shape, "bead": bead, "h": h, "version": version, "doubler": dbl}
    xs, zs, top = frame_top(h, x0, x0 + nx * h, z_lo)
    nxy = pl.node_xy()
    i = np.clip(np.round((nxy[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1)
    j = np.clip(np.round((nxy[:, 1] - zs[0]) / h).astype(int), 0, len(zs) - 1)
    topn = top[i, j]
    actn = pl.active_nodes()
    # sheet plane: follow the crown line, then rest on the highest frame point under the sheet
    y_crown = sleeve_y(nxy[:, 1]) + stay_r(nxy[:, 1])
    rel = topn - y_crown
    keep_out = np.zeros(pl.nn, bool)
    for zf in FAIRLEADS_Z:
        keep_out |= (np.abs(np.abs(nxy[:, 0]) - STAY_X) <= FAIRLEAD_HALF_X + NOTCH_CLEAR) & (np.abs(nxy[:, 1] - zf) <= FAIRLEAD_HALF_Z + NOTCH_CLEAR)
    crown = actn & ~keep_out & (np.abs(np.abs(nxy[:, 0]) - STAY_X) <= 2.0 * h / 2 + 1e-6)
    if crown.any():
        lift = float(np.nanmedian(np.where(crown, rel, np.nan)))   # sheet clipped down onto the crowns
    else:
        lift = float(np.nanmax(np.where(actn & ~keep_out, rel, np.nan)))   # old sheet: rests where it lands
    # frame points above that plane inside the outline: bumps a rub strip must take up
    info["bump_mm"] = float(np.nanmax(np.where(actn & ~keep_out, rel - lift, np.nan)))
    plane = y_crown + lift
    gap = np.maximum(plane - topn, 0.0)
    info.update(plane=plane, gap=gap, lift=float(lift))
    # beams: the two inboard branches and the z 330 bar (hot/wet PAHT)
    E = float(load("pa12_cf_fdm_paht").require("youngs_modulus_xy_mpa")) * PAHT_HOT_WET
    rb = 6.2 * SCALE
    rbar = 6.5 * SCALE
    zb = np.arange(165.0, 485.0 + 1e-6, h)
    beams = {}
    for s in (1.0, -1.0):
        bm = pl.add_beam(Beam(np.c_[s * branch_x(zb), zb], E * np.pi * rb ** 4 / 4, tag=f"branch{'R' if s > 0 else 'L'}"))
        beams[bm.tag] = (bm, zb)
    xbar = np.arange(-STAY_X, STAY_X + 1e-6, h)
    bar = pl.add_beam(Beam(np.c_[xbar, np.full_like(xbar, 330.0)], E * np.pi * rbar ** 4 / 4, tag="bar"))
    for s, tag in ((1.0, "branchR"), (-1.0, "branchL")):
        bm, zz = beams[tag]
        kb = int(np.argmin(np.abs(zz - 330.0)))
        kx = int(np.argmin(np.abs(xbar - s * branch_x(330.0))))
        pl.add_tie(bm.dof0 + 2 * kb, bar.dof0 + 2 * kx)
    # contact springs
    kinds = np.full(pl.nn, "", dtype=object)
    for n in np.nonzero(actn & np.isfinite(topn) & (gap < 30.0) & ~keep_out)[0]:
        x, z = nxy[n]
        g = max(float(gap[n]), 0.0)
        xb = branch_x(z)
        if lands and version == "v2" and _near_puck(x, z):
            g = LAND_FIT
        if 165.0 < z < 485.0 and abs(abs(x) - xb) <= 8.0 and abs(x) < 103.0:
            bm, zz = beams["branchR" if x > 0 else "branchL"]
            k = int(np.argmin(np.abs(zz - z)))
            pl.springs.append(Spring(n, 0.0, g, other=bm.dof0 + 2 * k, tag="branch"))
            kinds[n] = "branch"
        elif abs(z - 330.0) <= 8.0 and abs(x) <= 108.0:
            k = int(np.argmin(np.abs(xbar - x)))
            pl.springs.append(Spring(n, 0.0, g, other=bar.dof0 + 2 * k, tag="bar"))
            kinds[n] = "bar"
        else:
            pl.springs.append(Spring(n, 0.0, g, tag="stay" if abs(x) >= 100.0 else "rigid"))
            kinds[n] = "stay" if abs(x) >= 100.0 else "rigid"
    # clips (v2) / bolts (v1)
    if version == "v2":
        for zc in CLIP_Z + PAD_Z:
            cw = CLIP_W_BY_Z.get(zc, CLIP_W)
            sel = actn & (np.abs(nxy[:, 1] - zc) <= cw / 2 + 1e-6) & (np.abs(nxy[:, 0]) >= STAY_X - 4.0)
            for n in np.nonzero(sel)[0]:
                if zc in CLIP_Z:
                    pl.springs.append(Spring(n, clip_k(cw) / max(int(sel.sum()), 1), 0.0, sense=-1.0, tag="clip"))
                if zc in PAD_Z:
                    pl.springs.append(Spring(n, 0.0, LAND_FIT, tag="stay"))
    else:
        for s in (1.0, -1.0):
            n = pl.node_at(s * 96.0, 330.0)
            k = int(np.argmin(np.abs(xbar - s * 96.0)))
            pl.springs.append(Spring(n, 0.0, 0.0, other=bar.dof0 + 2 * k, unilateral=False, tag="bolt"))
    # bonded edge tubes: beams with free ends, tied to the plate row they sit on
    tubes = EDGE_TUBES if (tubes is None and version == "v2") else (tubes or ())
    info["tubes"] = []
    for (zt, od, idd) in tubes:
        jrow = int(round((zt - pl.y0) / h))
        row = actn & (np.abs(nxy[:, 1] - (pl.y0 + jrow * h)) < 1e-6)
        nodes_t = np.nonzero(row)[0]
        nodes_t = nodes_t[np.argsort(nxy[nodes_t, 0])]
        if len(nodes_t) < 3:
            continue
        xt = nxy[nodes_t, 0]
        tb = pl.add_beam(Beam(np.c_[xt, np.full_like(xt, zt)], tube_EI(od, idd), clamp_start=False,
                              clamp_end=False, tag=f"tube{zt:.0f}"))
        for k, n in enumerate(nodes_t):
            pl.springs.append(Spring(int(n), 0.0, 0.0, other=tb.dof0 + 2 * k, unilateral=False, tag="tube_bond"))
        info["tubes"].append({"beam": tb, "z": zt, "od": od, "id": idd, "len": float(xt[-1] - xt[0]),
                              "mass_g": tube_mass_g(od, idd, float(xt[-1] - xt[0]) + h)})
    info["kinds"] = kinds
    info["beams"] = beams
    return pl, info


def tube_stress(pl: GridPlate, info: dict, u: np.ndarray) -> dict:
    """Max bending stress in the edge tubes (MPa) and the bond-line pull per mm."""
    out = {"sigma_mpa": 0.0, "sf": np.inf}
    E = float(load("cfrp_pultruded_rod_tube").require("E1_mpa"))
    Xc = float(load("cfrp_pultruded_rod_tube").require("Xc_mpa")) * KD["hot_wet"] * KD["impact_comp"]
    for t in info.get("tubes", []):
        b = t["beam"]
        n = len(b.xy)
        w = u[b.dof0:b.dof0 + 2 * n:2]
        L = np.diff(b.xy[:, 0])
        # curvature from the Hermite end slopes
        th = u[b.dof0 + 1:b.dof0 + 2 * n:2]
        kap = np.abs(np.diff(th) / L)
        I = np.pi * (t["od"] ** 4 - t["id"] ** 4) / 64.0
        sig = float((E * kap * t["od"] / 2.0).max()) if len(kap) else 0.0
        if sig > out["sigma_mpa"]:
            out = {"sigma_mpa": sig, "sf": Xc / max(sig, 1e-9), "z": t["z"], "w_mm": float(np.abs(w).max())}
    return out


# ============================================================================ rail model
def foam_curve(mid: str = "xlpe_foam_l200"):
    m = load(mid)
    pts = [(0.0, 0.0)]
    for e in (5, 10, 25, 50, 70, 80):
        v = m.get(f"compression_{e}pct_kpa")
        if v is not None:
            pts.append((e / 100.0, float(v) / 1000.0))
    pts.append((0.88, 5.0))                                   # wall: solid PE (ASSUMPTION)
    e, s = np.array(pts).T
    return e, s


def eva_curve():
    m = load("eva_foam_45c")
    s25 = float(m.require("compression_25pct_kpa")) / 1000.0
    # ASSUMPTION: same shape as the L200 curve, scaled to the EVA 25 % point
    e, s = foam_curve()
    return e, s * s25 / np.interp(0.25, e, s)


def rail_layers(kind: str = "xlpe10"):
    """Rail build-ups. Aged thickness = (1 - compression set) x new."""
    xl = load("xlpe_foam_l200")
    set_x = float(xl.require("compression_set_pct")) / 100.0
    G_x = float(xl.require("shear_modulus_kpa")) / 1000.0
    ev = load("eva_foam_45c")
    set_e = float(ev.require("compression_set_pct")) / 100.0
    if kind == "xlpe10":
        return [{"h": RAIL_T * (1 - set_x), "curve": foam_curve(), "G": G_x, "name": "10 mm XLPE (aged)"}]
    if kind == "eva4_xlpe6":
        e, s = eva_curve()
        return [{"h": 4.0 * (1 - set_e), "curve": (e, s), "G": G_x * s[3] / foam_curve()[1][3],
                 "name": "4 mm EVA 45C (aged)"},
                {"h": 6.0 * (1 - set_x), "curve": foam_curve(), "G": G_x, "name": "6 mm XLPE (aged)"}]
    raise KeyError(kind)


def rail_section(q_line: float, layers=None, tissue_kpa: float = TISSUE_E_KPA, r_stay: float = 13.9,
                 half: float = RAIL_W / 2.0, dx: float = 0.5) -> dict:
    """Lateral section of one rail under one stay. Rigid cylinder on a nonlinear Pasternak layer
    (foam layers in series with a Winkler tissue column; shear from the foam layers).

    q_line: N/mm along the stay. Returns peak skin pressure (kPa), total indentation (mm), foam
    compression (mm), and the pressure profile.
    """
    layers = layers or rail_layers()
    kt = tissue_kpa / 1000.0 / TISSUE_H
    Gp = sum(L["G"] * L["h"] for L in layers)
    # u(p) table: total surface displacement for a pressure p
    p_tab = np.concatenate([[0.0], np.geomspace(1e-5, 0.6, 400)])
    u_f = np.zeros_like(p_tab)
    for L in layers:
        e, s = L["curve"]
        u_f += L["h"] * np.interp(p_tab, s, e)
    u_tab = u_f + p_tab / kt
    x = np.arange(-half, half + 1e-9, dx)
    n = len(x)
    prof = np.where(np.abs(x) < r_stay, r_stay - np.sqrt(np.maximum(r_stay ** 2 - x ** 2, 0.0)), 1e9)
    # second-difference operator with free (zero-shear) ends
    main = np.full(n, 2.0); main[0] = main[-1] = 1.0
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    L2 = sp.diags([main, -np.ones(n - 1), -np.ones(n - 1)], [0, -1, 1]) * (Gp / dx ** 2)

    def solve(d0):
        u = np.clip(d0 - prof, 0.0, None)
        act = (d0 - prof) > 0
        for _ in range(60):
            ksec = np.interp(np.maximum(u, 1e-6), u_tab, p_tab) / np.maximum(u, 1e-6)
            A = (L2 + sp.diags(ksec)).tolil()
            b = np.zeros(n)
            for i in np.nonzero(act)[0]:
                A.rows[i] = [i]; A.data[i] = [1.0]; b[i] = d0 - prof[i]
            un = spsolve(A.tocsr(), b)
            un = np.maximum(un, 0.0)
            # contact pressure at active nodes must be compressive; free nodes must not penetrate
            p = np.interp(un, u_tab, p_tab)
            qc = (L2 @ un) + p
            new = act.copy()
            new[act & (qc < 0)] = False
            new[~act & (un > d0 - prof + 1e-9)] = True
            conv = np.allclose(un, u, atol=1e-5) and np.array_equal(new, act)
            u, act = un, new
            if conv:
                break
        p = np.interp(u, u_tab, p_tab)
        return u, p

    lo, hi = 0.0, 60.0
    for _ in range(50):
        d0 = (lo + hi) / 2
        u, p = solve(d0)
        if p.sum() * dx < q_line:
            lo = d0
        else:
            hi = d0
    u, p = solve((lo + hi) / 2)
    pk = float(p.max())
    foam_c = float(sum(L["h"] * np.interp(pk, L["curve"][1], L["curve"][0]) for L in layers))
    k_line = q_line / max(float(u.max()), 1e-6)
    return {"peak_kpa": pk * 1000.0, "indent_mm": float(u.max()), "foam_mm": foam_c,
            "tissue_mm": pk / kt, "k_line": k_line, "x": x, "p_kpa": p * 1000.0,
            "foam_h_mm": float(sum(L["h"] for L in layers)), "Gp": Gp}


def rail_backed(q_line: float, D_b: float, layers=None, tissue_kpa: float = TISSUE_E_KPA,
                half: float = RAIL_W / 2.0, n: int = 101, strip_w: float = 80.0) -> dict:
    """Rail with a stiff backer strip between the stay and the foam (strip bending stiffness D_b,
    N mm per mm of rail length). The stay line load lands at the strip centre. 1-D Hermite beam on
    the same nonlinear Pasternak foundation as ``rail_section``. Free strip ends."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    layers = layers or rail_layers()
    kt = tissue_kpa / 1000.0 / TISSUE_H
    Gp = sum(L["G"] * L["h"] for L in layers)
    p_tab = np.concatenate([[0.0], np.geomspace(1e-5, 0.6, 400)])
    u_f = np.zeros_like(p_tab)
    for L in layers:
        e, s_ = L["curve"]
        u_f += L["h"] * np.interp(p_tab, s_, e)
    u_tab = u_f + p_tab / kt
    x = np.linspace(-half, half, n)
    le = x[1] - x[0]
    kb = D_b / le ** 3 * np.array([[12, 6 * le, -12, 6 * le], [6 * le, 4 * le ** 2, -6 * le, 2 * le ** 2],
                                    [-12, -6 * le, 12, -6 * le], [6 * le, 2 * le ** 2, -6 * le, 4 * le ** 2]])
    # Pasternak shear and Winkler (consistent Hermite matrices)
    ks = Gp / (30 * le) * np.array([[36, 3 * le, -36, 3 * le], [3 * le, 4 * le ** 2, -3 * le, -le ** 2],
                                    [-36, -3 * le, 36, -3 * le], [3 * le, -le ** 2, -3 * le, 4 * le ** 2]])
    mw = le / 420 * np.array([[156, 22 * le, 54, -13 * le], [22 * le, 4 * le ** 2, 13 * le, -3 * le ** 2],
                              [54, 13 * le, 156, -22 * le], [-13 * le, -3 * le ** 2, -22 * le, 4 * le ** 2]])
    nd = 2 * n
    f = np.zeros(nd)
    f[2 * (n // 2)] = q_line
    u = np.zeros(nd)
    ksec = np.full(n - 1, 0.01)
    ed = 2 * np.arange(n - 1)[:, None] + np.arange(4)[None, :]
    rr = np.repeat(ed, 4, axis=1).ravel()
    cc = np.tile(ed, (1, 4)).ravel()
    xm = (x[:-1] + x[1:]) / 2
    fb = np.where(np.abs(xm) <= strip_w / 2, 1.0, 1e-6)
    for _ in range(80):
        ke = fb[:, None, None] * kb[None] + ks[None] + ksec[:, None, None] * mw[None]
        K = sp.coo_matrix((ke.ravel(), (rr, cc)), shape=(nd, nd)).tocsr()
        un = spsolve(K, f)
        w = un[0::2]
        wm = np.maximum((w[:-1] + w[1:]) / 2, 1e-6)
        kn = np.interp(wm, u_tab, p_tab) / wm
        if np.allclose(kn, ksec, rtol=1e-4):
            u = un
            break
        ksec = 0.5 * ksec + 0.5 * kn
        u = un
    w = np.maximum(u[0::2], 0.0)
    p = np.interp(w, u_tab, p_tab)
    pk = float(p.max())
    foam_c = float(sum(L["h"] * np.interp(pk, L["curve"][1], L["curve"][0]) for L in layers))
    return {"peak_kpa": pk * 1000.0, "indent_mm": float(w.max()), "foam_mm": foam_c, "tissue_mm": pk / kt,
            "k_line": q_line / max(float(w.max()), 1e-6), "x": x, "p_kpa": p * 1000.0,
            "foam_h_mm": float(sum(L["h"] for L in layers)), "Gp": Gp}


# Backer strips between the stay and the rail foam: (material id, thickness mm, width mm)
RAIL_BACKERS = {
    "none": None,
    "cf05_80": ("cfrp_plate_quasi_iso", 0.5, 80.0),
    "tw10_40": ("cfrp_t300_3k_woven_epoxy_ply", 1.02, 40.0),
    "tw10_50": ("cfrp_t300_3k_woven_epoxy_ply", 1.02, 50.0),
    "tw10_60": ("cfrp_t300_3k_woven_epoxy_ply", 1.02, 60.0),
    "hdpe15_80": ("hdpe_sheet", 1.5, 80.0),
}


def backer_D(kind: str) -> float:
    spec = RAIL_BACKERS[kind]
    if spec is None:
        return 0.0
    mid, t, _w = spec
    m = load(mid)
    E = float(m.get("youngs_modulus_mpa") or m.require("E1_mpa"))
    nu = float(m.get("poisson", 0.3)) if m.get("poisson") is not None else 0.1
    return E * t ** 3 / (12 * (1 - nu ** 2))


def backer_mass_g(kind: str) -> float:
    spec = RAIL_BACKERS[kind]
    if spec is None:
        return 0.0
    mid, t, w = spec
    return 2 * w * RAIL_L * t * float(load(mid).require("density_kg_m3")) / 1e6


RAIL_DESIGN = {"layers": "xlpe10", "backer": "tw10_60"}     # chosen rail build (see rail_options)


def rail_eval(q_line: float, rail=None, tissue_kpa: float = TISSUE_E_KPA) -> dict:
    rail = rail or RAIL_DESIGN
    layers = rail_layers(rail["layers"])
    D = backer_D(rail["backer"])
    if D > 0:
        return rail_backed(q_line, D, layers, tissue_kpa, strip_w=RAIL_BACKERS[rail["backer"]][2])
    return rail_section(q_line, layers, tissue_kpa)


def stay_EI() -> float:
    E = float(load("pa12_cf_fdm_paht").require("youngs_modulus_xy_mpa")) * PAHT_HOT_WET
    r = 13.4 * SCALE
    return E * np.pi * (r ** 4 - 9.0 ** 4) / 4.0


def skin_pressure(bone_side_n: float, kind: str = "walk", rail=None, tissue_kpa: float = TISSUE_E_KPA,
                  bone_total_n: float = 0.0) -> dict:
    rail = rail or RAIL_DESIGN
    key = (round(float(bone_side_n) / 2.0) * 2.0, kind, rail["layers"], rail["backer"], float(tissue_kpa),
           round(float(bone_total_n)))
    if key not in _SKIN_CACHE:
        _SKIN_CACHE[key] = _skin_pressure(key[0], kind, rail, tissue_kpa, key[5])
    return dict(_SKIN_CACHE[key])


_SKIN_CACHE: dict = {}


def _skin_pressure(bone_side_n: float, kind: str = "walk", rail=None, tissue_kpa: float = TISSUE_E_KPA,
                   bone_total_n: float = 0.0) -> dict:
    """Peak skin pressure under a rail: pack-level forward meat force over the two rails plus the
    bone reaction spread along the stay as a beam on the rail foundation (Hetenyi, peak P beta / 2).
    The bone is part of the meat: ``bone_total_n`` comes out of the uniform share first."""
    g = {"walk": 1.6, "factored": 3.0, "static": 1.0}[kind]
    H = max(meat_normal_n(g) - bone_total_n, 0.0)
    q0 = H / 2.0 / RAIL_L
    sec0 = rail_eval(q0, rail, tissue_kpa)
    beta = (sec0["k_line"] / (4.0 * stay_EI())) ** 0.25
    q = q0 + bone_side_n * beta / 2.0
    sec = rail_eval(q, rail, tissue_kpa)
    sec.update(q_meat=q0, q_line=q, beta_len_mm=1.0 / beta, uniform_kpa=q / RAIL_W * 1000.0)
    return sec


# ============================================================================ checks
def bone_positions(shape, step: float = 24.0) -> list[tuple[float, float]]:
    from shapely.geometry import Point
    pts = []
    for x in np.arange(0.0, 121.0, step):
        for z in np.arange(shape.bounds[1] + 12.0, Z_HI - 11.0, step):
            if shape.buffer(-BONE_D / 2 + 1.0).contains(Point(x, z)):
                pts.append((float(x), float(z)))
    return pts


def named_positions(version: str = "v2") -> dict:
    if version == "v1":
        return {"center": (0.0, 280.0), "bottom edge": (0.0, 142.0), "top edge": (0.0, 418.0),
                "near M4 hole (IM2)": (86.0, 330.0), "near M4 hole (IM1)": (86.0, 190.0),
                "between rails, low": (0.0, 200.0), "over the rail, mid": (88.0, 260.0)}
    return {"center": (0.0, 280.0), "bottom edge": (0.0, 142.0), "top edge": (0.0, 418.0),
            "IM1 notch root": (82.0, 190.0), "IM2 notch root": (82.0, 330.0),
            "US2 corner relief": (84.0, 160.0), "between rails, low": (0.0, 200.0),
            "over the rail, mid": (90.0, 260.0), "at a clip": (104.0, 255.0)}


def _fi_field(opt: Option, pl: GridPlate, info: dict, u: np.ndarray) -> np.ndarray:
    M = pl.moments(u)                                           # (nx, ny, 4, 3)
    if opt.beads:
        t = opt.lam.thickness
        b = opt.beads
        I_bead = t * b["depth"] ** 2 / 8.0 + t ** 3 / 12.0
        c = b["depth"] / 2.0 + t / 2.0
        red = (t ** 2 / 6.0) / (I_bead / c)                      # section modulus ratio
        M = M.copy()
        M[info["bead"], :, 0] *= red
    fi = laminate_bending_fi(opt.lam, M, KD).max(axis=2)
    dbl = info.get("doubler")
    if dbl is not None and dbl.any():
        fi[dbl] = laminate_bending_fi(doubler_lam(opt), M[dbl], KD).max(axis=1)
    if opt.perforated and info.get("hole_edge") is not None:
        fi = np.where(info["hole_edge"], fi * 1.8, fi)          # Kt bending at a circular hole (Savin)
    fi[~pl.active] = 0.0
    return fi


def sandwich_checks(opt: Option, pl: GridPlate, u: np.ndarray, sol: dict, P_bone: float) -> dict:
    """Core shear, core crush (bone patch and stay crown), face wrinkling. Factored inputs."""
    m = load(opt.core)
    tau_a = float(m.require("shear_strength_mpa")) * KD["hot_wet"]
    sc_a = float(m.require("compressive_strength_mpa")) * KD["hot_wet"]
    Ec = float(m.require("compressive_modulus_mpa"))
    Gc = float(m.require("shear_modulus_mpa"))
    Ef = float(load("cfrp_t300_3k_woven_epoxy_ply").require("E1_mpa"))
    d = opt.core_t + opt.skin_t
    M = pl.moments(u).mean(axis=2)
    Mx, My, Mxy = M[..., 0], M[..., 1], M[..., 2]
    h = pl.h
    Qx = np.gradient(Mx, h, axis=0) + np.gradient(Mxy, h, axis=1)
    Qy = np.gradient(Mxy, h, axis=0) + np.gradient(My, h, axis=1)
    inner = pl.active.copy()
    from scipy import ndimage
    inner = ndimage.binary_erosion(inner, iterations=1)
    # resolve the plate shear over the sandwich shear length, as for the crown line load below
    l_s0 = float(np.sqrt(opt.lam.D[0, 0] / (Gc * d ** 2 / opt.core_t)))
    k_sm = max(int(round(max(20.0, 2.0 * l_s0) / h)), 1)
    Qa = np.where(inner, np.hypot(Qx, Qy), 0.0)
    Qa = ndimage.uniform_filter(Qa, k_sm) / np.maximum(ndimage.uniform_filter(inner.astype(float), k_sm), 1e-9)
    Q_fe = float(Qa[inner].max())
    Q_patch = P_bone / (np.pi * BONE_D)
    # Stay crown line load. Penalty contact closes at single nodes, so the raw node force / h is a
    # mesh artefact. The crown carries a 1 mm EVA rub strip; ASSUMPTION: the line load is resolved
    # over 20 mm of stay length (sum of crown contact forces per z row, both sides separately,
    # 20 mm moving window).
    f = sol["spring_force"]
    tags = np.array([s.tag for s in pl.springs])
    nodes = np.array([s.node for s in pl.springs])
    nxy = pl.node_xy()
    crown = (tags == "stay") | (tags == "rigid")
    zrow = np.round((nxy[nodes, 1] - pl.y0) / h).astype(int)
    q_stay = 0.0
    # A sandwich spreads a concentrated reaction by its own core shear over about +-sqrt(D / S)
    # (Zenkert ch. 5; S = G_c d^2 / c). The Kirchhoff plate has no such length, so the window
    # is the larger of 20 mm and 2 sqrt(D / S).
    S_sh = Gc * d ** 2 / opt.core_t
    l_s = float(np.sqrt(opt.lam.D[0, 0] / S_sh))
    win = max(int(round(max(20.0, 2.0 * l_s) / h)), 1)
    for side in (1.0, -1.0):
        sel = crown & (np.sign(nxy[nodes, 0]) == side) & (np.abs(nxy[nodes, 0]) >= 95.0)
        prof = np.bincount(zrow[sel], weights=f[sel], minlength=pl.ny + 1)
        sm = np.convolve(prof, np.ones(win) / win, mode="same") / h
        q_stay = max(q_stay, float(sm.max(initial=0.0)))
    Q_sup = q_stay      # the outboard overhang past the crown is short: all the shear is on the inboard side
    # Plate shear away from the contacts, from the moment gradient on elements one row clear of a support
    Q = max(Q_fe, Q_patch, Q_sup)
    tau = Q / d
    crush_patch = P_bone / (np.pi * BONE_D ** 2 / 4.0)
    b_crown = 8.0      # ASSUMPTION: 1 mm EVA rub strip on the crown spreads the line to >= 8 mm
    crush_crown = q_stay / b_crown
    # bonded pucks: the force a puck takes from the branch / bar over its own area
    f_puck = 0.0
    land = (tags == "branch") | (tags == "bar")
    for px, pz in (pucks() if opt.pucks else []):
        sel = land & (np.hypot(nxy[nodes, 0] - px, nxy[nodes, 1] - pz) <= PUCK_D / 2 + 1e-6)
        f_puck = max(f_puck, float(f[sel].sum()))
    crush_puck = f_puck / (np.pi * PUCK_D ** 2 / 4.0)
    f_clip = float(np.abs(f[tags == "clip"]).sum()) / max(len(CLIP_Z) * 2, 1)
    crush_clip = f_clip / (CLIP_W * 10.0)
    Mmax = float(np.abs(np.c_[Mx[pl.active], My[pl.active]]).max())
    s_face = Mmax / (opt.skin_t * d)
    s_wr = 0.5 * (Ef * Ec * Gc) ** (1.0 / 3.0) * KD["hot_wet"]
    return {"core_shear_mpa": tau, "core_shear_sf": tau_a / tau,
            "Q_fe": Q_fe, "Q_patch": Q_patch, "Q_support": Q_sup,
            "crush_patch_mpa": crush_patch, "crush_patch_sf": sc_a / crush_patch,
            "crush_crown_mpa": crush_crown, "crush_crown_sf": sc_a / max(crush_crown, 1e-9),
            "crush_clip_sf": sc_a / max(crush_clip, 1e-9), "face_mpa": s_face,
            "puck_n": f_puck, "crush_puck_mpa": crush_puck, "crush_puck_sf": sc_a / max(crush_puck, 1e-9),
            "wrinkle_mpa": s_wr, "wrinkle_sf": s_wr / s_face,
            "shear_length_mm": l_s,
            "sf_min": min(tau_a / tau, sc_a / crush_patch, sc_a / max(crush_crown, 1e-9), s_wr / s_face,
                          sc_a / max(crush_puck, 1e-9))}


def shear_deflection(opt: Option, P: float) -> float:
    """Core-shear part of the bone-patch deflection (sandwich), circular plate of radius 100 mm:
    w_s = P / (2 pi S) ln(R / r0), S = G_c d^2 / c (Zenkert, An Introduction to Sandwich Construction)."""
    if not opt.core:
        return 0.0
    Gc = float(load(opt.core).require("shear_modulus_mpa"))
    d = opt.core_t + opt.skin_t
    S = Gc * d ** 2 / opt.core_t
    return P / (2.0 * np.pi * S) * np.log(100.0 / (BONE_D / 2.0))


def clearance_field(pl: GridPlate, info: dict, w: np.ndarray, indent_mm: float, r_torso: float = R_TORSO,
                    h_rail: float | None = None) -> np.ndarray:
    """Air between the sheet's wearer face and the skin, per node (mm). Negative = bottoming."""
    nxy = pl.node_xy()
    z = nxy[:, 1]
    x = np.abs(nxy[:, 0])
    h_rail = h_rail if h_rail is not None else RAIL_T * (1 - float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0)
    y_frame_wearer = sleeve_y(z) - stay_r(z)
    y_skin = y_frame_wearer - h_rail + indent_mm
    bulge = np.where(x < GUTTER_HALF, (GUTTER_HALF ** 2 - x ** 2) / (2.0 * r_torso), 0.0)
    c = info["plane"] - w - (y_skin + bulge)
    c[~pl.active_nodes()] = np.nan
    return c


def run_case(opt: Option, pl: GridPlate, info: dict, kind: str, bone_xy=None, bone_only=False, active0=None) -> dict:
    exy = pl.elem_xy()
    P = bone_n(kind) if bone_xy is not None else 0.0
    q = np.zeros((pl.nx, pl.ny)) if bone_only else meat_pressure(exy[..., 1], kind, less_n=P)
    if bone_xy is not None:
        q = q + pl.patch_pressure(bone_xy[0], bone_xy[1], BONE_D, P)
    f = pl.load_vector(q)
    if active0 is None:
        active0 = info.get("_act", {}).get((kind, bone_only))
    sol = pl.solve(f, active0=active0)
    info.setdefault("_act", {})[(kind, bone_only)] = sol["active"]
    w = sol["w"].copy()
    if bone_xy is not None and opt.core:
        # add the core-shear dimple under the patch
        nxy = pl.node_xy()
        r = np.hypot(nxy[:, 0] - bone_xy[0], nxy[:, 1] - bone_xy[1])
        ws = shear_deflection(opt, P)
        w = w + ws * np.clip(np.log(100.0 / np.maximum(r, BONE_D / 2)) / np.log(100.0 / (BONE_D / 2)), 0, 1)
    fi = _fi_field(opt, pl, info, sol["u"])
    tags = np.array([s.tag for s in pl.springs])
    fs = sol["spring_force"]
    nxy = pl.node_xy()
    nodes = np.array([s.node for s in pl.springs])
    side_R = float(fs[nxy[nodes, 0] > 0].sum())
    side_L = float(fs[nxy[nodes, 0] < 0].sum())
    out = {"sol": sol, "w": w, "fi": fi, "P": P, "force_by_tag": {t: float(fs[tags == t].sum()) for t in set(tags)},
           "side_R": side_R, "side_L": side_L, "clip_max_n": float(np.abs(fs[tags == "clip"]).max(initial=0.0)),
           "clip_lift_n": float(-fs[tags == "clip"].min(initial=0.0)),
           "bolt_n": float(np.abs(fs[tags == "bolt"]).max(initial=0.0)), "q_total_n": float(f[0:pl.ndof_plate:3].sum())}
    if opt.core and bone_xy is not None:
        out["sandwich"] = sandwich_checks(opt, pl, sol["u"], sol, P)
    return out


def evaluate(opt: Option, h: float = 4.0, version: str = "v2", step: float | None = 24.0, rail=None,
             holes_mask=None, shape=None, keep_fields: bool = False, info_extra=None) -> dict:
    """Full check of one option: meat-only, bone map (walking and factored), skin pressure, clearance."""
    pl, info = build_plate(opt, h, shape=shape, version=version, holes_mask=holes_mask,
                           tubes=None if opt.tubes is True else (opt.tubes or ()), lands=opt.pucks)
    if info_extra:
        info.update(info_extra)
    shape = info["shape"]
    area_mm2 = float(shape.area) - (0.0 if holes_mask is None else float(holes_mask.sum() * h * h))
    if holes_mask is not None and info.get("hole_area_mm2"):
        area_mm2 = float(shape.area) - info["hole_area_mm2"]
    mass_g = area_mm2 * opt.areal_kg_m2() / 1000.0
    # rail indentation for clearance: meat only, and with the worst bone side load
    meat_w = run_case(opt, pl, info, "walk")
    meat_f = run_case(opt, pl, info, "factored")
    pos = bone_positions(shape, step) if step else []
    named = named_positions(version)
    allpos = list(named.values()) + pos
    rows = []
    rail_w0 = skin_pressure(0.0, "walk", rail)
    rail_f0 = skin_pressure(0.0, "factored", rail)
    fields = {}
    for k, xy in enumerate(allpos):
        rw = run_case(opt, pl, info, "walk", xy)
        rf = run_case(opt, pl, info, "factored", xy)
        bw = run_case(opt, pl, info, "walk", xy, bone_only=True)
        side = max(bw["side_R"], bw["side_L"])
        side_f = side * bone_n("factored") / bone_n("walk")
        # bone reaction share into the stays rises the line load locally; take the side with more
        sk = skin_pressure(side, "walk", rail, bone_total_n=bone_n("walk"))
        skf = skin_pressure(side_f, "factored", rail, bone_total_n=bone_n("factored"))
        cw = clearance_field(pl, info, rw["w"], sk["indent_mm"])
        cf = clearance_field(pl, info, rf["w"], skf["indent_mm"])
        cf_lo = clearance_field(pl, info, rf["w"], skf["indent_mm"], R_TORSO_LO)
        name = next((n for n, v in named.items() if v == xy), None) if k < len(named) else None
        row = {"x": xy[0], "z": xy[1], "name": name,
               "w_walk": float(np.nanmax(rw["w"][pl.active_nodes()])),
               "w_fact": float(np.nanmax(rf["w"][pl.active_nodes()])),
               "w_bone_walk": float(rw["w"][pl.node_at(*xy)]),
               "fi_fact": float(rf["fi"].max()), "fi_walk": float(rw["fi"].max()),
               "clear_walk": float(np.nanmin(cw)), "clear_fact": float(np.nanmin(cf)),
               "clear_fact_lean": float(np.nanmin(cf_lo)),
               "skin_kpa": sk["peak_kpa"], "skin_fact_kpa": skf["peak_kpa"], "bone_side_n": side,
               "clip_lift_n": rf["clip_lift_n"], "bolt_n": rf["bolt_n"]}
        if "sandwich" in rf:
            row["sandwich_sf"] = rf["sandwich"]["sf_min"]
            row["sandwich"] = {k2: v for k2, v in rf["sandwich"].items()}
        rows.append(row)
        if keep_fields and name is not None:
            fields[name] = {"w_fact": rf["w"], "fi_fact": rf["fi"], "w_walk": rw["w"], "clear": cf,
                            "skin": sk}
    worst = {
        "fi_fact": max(rows, key=lambda r: r["fi_fact"]),
        "fi_walk": max(rows, key=lambda r: r["fi_walk"]),
        "clear_fact": min(rows, key=lambda r: r["clear_fact"]),
        "skin_kpa": max(rows, key=lambda r: r["skin_kpa"]),
        "w_fact": max(rows, key=lambda r: r["w_fact"]),
    }
    fi_meat = float(meat_f["fi"].max())
    fi_f = max(worst["fi_fact"]["fi_fact"], fi_meat)
    fi_w = max(worst["fi_walk"]["fi_walk"], float(meat_w["fi"].max()))
    res = {
        "key": opt.key, "name": opt.name, "family": opt.family, "t_mm": opt.lam.thickness,
        "laminate": opt.lam.describe(), "areal_kg_m2": opt.areal_kg_m2(), "area_mm2": area_mm2,
        "mass_g": mass_g, "n_positions": len(rows),
        "meat_walk_w": float(np.nanmax(meat_w["w"][pl.active_nodes()])),
        "meat_fact_w": float(np.nanmax(meat_f["w"][pl.active_nodes()])),
        "meat_force_walk_n": meat_w["q_total_n"], "meat_force_fact_n": meat_f["q_total_n"],
        "meat_force_by_tag": meat_w["force_by_tag"],
        "fi_meat_fact": fi_meat,
        "sf_fpf": 1.0 / fi_f, "sf_fpf_limit": 1.5 / fi_f, "fpf_where": _where(worst["fi_fact"]),
        "sf_fatigue": FAT_FI / fi_w,
        "clear_fact_min": worst["clear_fact"]["clear_fact"], "clear_where": _where(worst["clear_fact"]),
        "clear_walk_min": min(r["clear_walk"] for r in rows),
        "clear_fact_lean_min": min(r["clear_fact_lean"] for r in rows),
        "skin_peak_kpa": worst["skin_kpa"]["skin_kpa"], "skin_where": _where(worst["skin_kpa"]),
        "skin_meat_only_kpa": rail_w0["peak_kpa"], "skin_fact_meat_only_kpa": rail_f0["peak_kpa"],
        "w_fact_max": worst["w_fact"]["w_fact"], "w_where": _where(worst["w_fact"]),
        "w_bone_walk_center": next(r["w_bone_walk"] for r in rows if r["name"] == "center"),
        "rail_indent_walk_mm": rail_w0["indent_mm"], "rail_foam_walk_mm": rail_w0["foam_mm"],
        "clip_lift_max_n": max(r["clip_lift_n"] for r in rows), "bolt_max_n": max(r["bolt_n"] for r in rows),
        "rows": rows, "plane_lift_mm": info["lift"],
        "sheet_g": mass_g, "tubes_g": float(sum(t["mass_g"] for t in info.get("tubes", []))),
    }
    if opt.core:
        res["sandwich_sf_min"] = min(r["sandwich_sf"] for r in rows)
        res["sandwich_worst"] = min((r for r in rows), key=lambda r: r["sandwich_sf"])["sandwich"]
    if version == "v2":
        res["fittings_g"] = fittings_mass_g(opt.lam.thickness, pucks=opt.pucks)
        if opt.edge_seal:
            res["fittings_g"] += edge_seal_g(shape, opt.lam.thickness)
        if opt.doubler and opt.core:
            res["doubler_g"] = float(doubler_zone().area * 2 * _twill().t * _twill().density_kg_m3 / 1e6)
            res["fittings_g"] += res["doubler_g"]
    else:
        res["fittings_g"] = 4 * M4_SET_G
    res["mass_g"] = res["sheet_g"] + res["tubes_g"] + res["fittings_g"]
    res["checks"] = {
        "fpf": res["sf_fpf"] >= 1.0,
        "fatigue": res["sf_fatigue"] >= 1.0,
        "no_bottoming": res["clear_walk_min"] >= MESH_T and res["clear_fact_min"] >= 0.0,
        "skin_pressure": res["skin_peak_kpa"] <= PEAK_KPA,
    }
    if opt.core:
        res["checks"]["sandwich_local"] = res["sandwich_sf_min"] >= 1.0
    res["passes"] = all(res["checks"].values())
    res["passes_sheet"] = all(v for k, v in res["checks"].items() if k != "skin_pressure")
    if keep_fields:
        res["_fields"] = fields
        res["_plate"] = (pl, info)
    return res


M4_SET_G = 2.4                    # ASSUMPTION: M4 x 12 stainless button head + nyloc nut + washer


EDGE_COAT_KG_M3 = 1150.0          # brushed laminating epoxy
EDGE_COAT_T = 0.3                 # ASSUMPTION: two brushed coats, 0.3 mm, over the cut PMI edge


def edge_seal_g(shape, t: float) -> float:
    """Sealed sandwich edge: the cut PMI edge is brushed with epoxy (closed-cell core, so this is an
    abrasion and grime seal, not a structural closure)."""
    return float(shape.length) * t * EDGE_COAT_T * EDGE_COAT_KG_M3 / 1e6


def fittings_mass_g(t_sheet: float, pucks: bool = True) -> float:
    """Clips (MJF PA12) and bonded pucks (PAHT-CF) for the v2 part. Not the sheet or the tubes."""
    clips = 0.0
    r_mid = float(np.mean(stay_r(np.array([166.0, 260.0, 400.0]))))
    for zc in CLIP_Z:
        so = float(stay_r(260.0) - stay_r(119.0)) if zc in CLIP_STANDOFF else 0.0
        r = float(stay_r(zc)) if zc in CLIP_STANDOFF else r_mid
        clips += 2 * clip_mass_g(clip_profile(r, t_sheet, so), CLIP_W_BY_Z.get(zc, CLIP_W))
    rho = float(load("pa12_cf_fdm_paht").require("density_kg_m3"))
    pk = 0.0
    if pucks:
        hts = [p["height_mm"] for p in puck_table()]
        pk = float(np.pi / 4 * PUCK_D ** 2 * (np.sum(hts) + 1.0 * len(hts)) * rho / 1e6)   # +1 mm bond flange
    pads = 2 * len(PAD_Z) * CLIP_W * 16.0 * float(stay_r(260.0) - stay_r(119.0)) * rho / 1e6
    return float(clips + pk + pads)


def _where(r):
    return r["name"] or f"x {r['x']:.0f}, z {r['z']:.0f}"


# ============================================================================ hole / edge checks
def qi_inplane_shear_strength(lam: Laminate) -> float:
    """In-plane shear strength (MPa) of the laminate at first-ply failure, knocked down."""
    r = lam.first_ply_failure(N=(0, 0, 1.0), knockdown=KD)
    return float(r["sf"] / lam.thickness)


def bolt_check(lam: Laminate, F: float, d: float = 4.5, e: float = 8.0) -> dict:
    """M4 in the old sheet: bearing, shear-out, net tension (CMH-17 style, knocked-down)."""
    qi = load("cfrp_plate_quasi_iso")
    t = lam.thickness
    Fbr = float(qi.require("bearing_strength_mpa")) * KD["hot_wet"]
    Fsu = qi_inplane_shear_strength(lam)
    s_br = F / (d * t)
    s_so = F / (2.0 * (e - d / 2.0) * t)
    return {"F_n": F, "bearing_mpa": s_br, "bearing_sf": Fbr / max(s_br, 1e-9),
            "shearout_mpa": s_so, "shearout_sf": Fsu / max(s_so, 1e-9), "e_over_d": e / d,
            "e_over_d_ok": e / d >= 3.0}


# ============================================================================ SIMP cut-outs
MAX_HOLE_D = 20.0                 # a 22 mm bone end cannot pass a 20 mm hole
HOLE_PITCH = 30.0                 # hex pitch: ligament >= 10 mm (>= 2 t rule, water-jet)


def simp_density(opt: Option, h: float = 6.0, volfrac: float = 0.65, iters: int = 30, p: float = 3.0,
                 rmin: float = 9.0, log=None) -> dict:
    """Bending SIMP on the plate: D = rho^p D0, minimise the summed compliance of the meat case and
    a grid of bone cases, contact frozen at the solid design's active sets (linearised)."""
    pl, info = build_plate(opt, h)
    D0 = pl.D.copy()
    act = pl.active.copy()
    exy = pl.elem_xy()
    cases = [("factored", None)] + [("factored", xy) for xy in bone_positions(info["shape"], 48.0)]
    loads, active_sets = [], []
    for kind, xy in cases:
        q = meat_pressure(exy[..., 1], kind)
        if xy is not None:
            q = q + pl.patch_pressure(xy[0], xy[1], BONE_D, bone_n(kind))
        f = pl.load_vector(q)
        loads.append(f)
        active_sets.append(pl.solve(f)["active"])
    # keep-solid: support bands over the stays, clip zones, a 10 mm rim, notch surrounds
    from scipy import ndimage
    rim = act & ~ndimage.binary_erosion(act, iterations=max(int(round(10.0 / h)), 1))
    keep = rim | (np.abs(exy[..., 0]) > 92.0)
    rho = np.where(act, volfrac, 0.0)
    rho[keep] = 1.0
    # filter weights
    r = int(np.ceil(rmin / h))
    di, dj = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    wk = np.maximum(rmin / h - np.hypot(di, dj), 0.0)
    hist = []
    Kb = pl.el.Kb
    from huntkit.fea.plate_grid import _Dvec
    Dv0 = _Dvec(D0)
    for it in range(iters):
        pl.D = (np.maximum(rho, 1e-3) ** p)[..., None, None] * D0
        pl._K0 = None
        dc = np.zeros_like(rho)
        comp = 0.0
        for f, a0 in zip(loads, active_sets):
            sol = pl.solve(f, active0=a0, max_iter=1)
            u = sol["u"]
            ue = u[pl.edof]
            Ke0 = np.einsum("ijk,kab->ijab", Dv0, Kb)
            ce = np.einsum("ija,ijab,ijb->ij", ue, Ke0, ue)
            comp += float(f @ u)
            dc += -p * np.maximum(rho, 1e-3) ** (p - 1) * ce
        dc = ndimage.convolve(dc * rho, wk, mode="constant") / np.maximum(
            ndimage.convolve(np.maximum(rho, 1e-3), wk, mode="constant"), 1e-9)
        # optimality criteria
        l1, l2 = 1e-12, 1e12
        free = act & ~keep
        target = volfrac * free.sum()
        while (l2 - l1) / (l1 + l2) > 1e-4:
            lm = 0.5 * (l1 + l2)
            rn = np.clip(rho * np.sqrt(np.maximum(-dc, 0) / lm), np.maximum(rho - 0.15, 0.05),
                         np.minimum(rho + 0.15, 1.0))
            rn[~free] = rho[~free]
            if rn[free].sum() > target:
                l1 = lm
            else:
                l2 = lm
        rho = rn
        hist.append(comp)
        if log:
            log(f"simp {it} compliance {comp:.1f}")
    pl.D = D0
    return {"rho": rho, "plate": pl, "info": info, "hist": hist, "keep": keep}


def holes_from_density(simp: dict, h_fine: float = 2.0) -> dict:
    """Hex grid of round holes, diameter from the local SIMP density, capped at MAX_HOLE_D."""
    from shapely.geometry import Point
    rho = simp["rho"]
    pl = simp["plate"]
    shape = simp["info"]["shape"]
    exy = pl.elem_xy()
    holes = []
    inner = shape.buffer(-10.0)
    for k, z in enumerate(np.arange(shape.bounds[1] + 18.0, Z_HI - 12.0, HOLE_PITCH * np.sqrt(3) / 2)):
        off = (HOLE_PITCH / 2) if k % 2 else 0.0
        for x in np.arange(-90.0 + off, 90.1, HOLE_PITCH):
            if abs(x) > 82.0:
                continue
            i = int(np.clip((x - pl.x0) / pl.h, 0, pl.nx - 1))
            j = int(np.clip((z - pl.y0) / pl.h, 0, pl.ny - 1))
            r_loc = float(rho[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2].mean())
            d = MAX_HOLE_D * float(np.clip((0.85 - r_loc) / 0.55, 0.0, 1.0))
            if d < 8.0:
                continue
            c = Point(x, z).buffer(d / 2, 32)
            if inner.contains(c):
                holes.append((float(x), float(z), round(d, 1)))
    return {"holes": holes, "area_mm2": float(sum(np.pi * d * d / 4 for _, _, d in holes))}


def holes_mask(plate_like, holes) -> tuple[np.ndarray, np.ndarray]:
    exy = plate_like.elem_xy()
    m = np.zeros(exy.shape[:2], bool)
    edge = np.zeros_like(m)
    for x, z, d in holes:
        r = np.hypot(exy[..., 0] - x, exy[..., 1] - z)
        m |= r <= d / 2
        edge |= (r > d / 2) & (r <= d / 2 + 1.5 * plate_like.h)
    return m, edge


def evaluate_perforated(opt: Option, holes: list, h: float = 2.0, step: float = 30.0) -> dict:
    pl0, _ = build_plate(opt, h)
    m, edge = holes_mask(pl0, holes)
    area = float(sum(np.pi * d * d / 4 for _, _, d in holes))
    return evaluate(opt, h=h, step=step, holes_mask=m, info_extra={"hole_edge": edge, "hole_area_mm2": area})


# ============================================================================ detail: clips, DXF, drawing
CLIP_LEG_T = 2.5                  # clip leg / bridge thickness
SLOT_W, SLOT_L = 4.0, 16.0        # sheet slot for the inboard clip leg (full-round ends)


def clip_slots() -> list[tuple[float, float]]:
    out = []
    for zc in CLIP_Z:
        r = float(stay_r(zc))
        xs = STAY_X - (r + CLIP_LEG_T / 2.0 + 0.3)
        out += [(xs, zc), (-xs, zc)]
    return out


def part_shape(opt: Option | None = None):
    """Finished outline with the clip slots cut (shapely, frame x / z)."""
    from shapely.geometry import LineString
    shape = outline_v2()
    for x, z in clip_slots():
        slot = LineString([(x, z - (SLOT_L - SLOT_W) / 2), (x, z + (SLOT_L - SLOT_W) / 2)]).buffer(SLOT_W / 2, 16)
        shape = shape.difference(slot)
    return shape


def clip_profile(r_stay: float, t_sheet: float, standoff: float = 0.0):
    """2-D profile of one PA12 clip in the stay cross-section (x across the stay, y toward the bag).

    Two straight posts rise beside the stay (the inboard one passes the sheet through a slot, the
    outboard one passes outside the sheet edge), a bridge lies on the sheet, and the posts end in
    hooks that wrap 20 deg past the stay's equator. With a stand-off the clip carries a saddle under
    the sheet (the z 119 clip, where the stay is r 9 and sits 4.5 mm below the sheet)."""
    from shapely.geometry import Point, Polygon, box
    from shapely.ops import unary_union
    T = CLIP_LEG_T
    ri = r_stay + 0.15
    ring = Point(0, 0).buffer(ri + T, 96).difference(Point(0, 0).buffer(ri, 96))
    a = np.radians(20.0)
    hook = ring.intersection(box(-40, -np.sin(a) * (ri + T), 40, 0.0))
    y_sheet = r_stay + standoff
    y_top = y_sheet + t_sheet + 0.2
    posts = [box(-(ri + T), -0.5, -ri, y_top + T), box(ri, -0.5, ri + T, y_top + T)]
    bridge = box(-(ri + T), y_top, ri + T, y_top + T)
    parts = [hook, bridge] + posts
    if standoff > 0:
        sad = box(-ri, r_stay - 2.0, ri, y_sheet).difference(Point(0, 0).buffer(r_stay + 0.15, 96))
        parts.append(sad)
    prof = unary_union(parts).buffer(0.3).buffer(-0.3)
    return prof


def clip_mass_g(prof, width: float) -> float:
    return prof.area * width * float(load(CLIP_MAT).require("density_kg_m3")) / 1e6


@lru_cache(maxsize=1)
def _puck_table_cached():
    return tuple(tuple(sorted(d.items())) for d in puck_heights(None))


def puck_table() -> list[dict]:
    return [dict(t) for t in _puck_table_cached()]


def puck_heights(opt: Option | None = None, h: float = 2.0) -> list[dict]:
    """Height of each bonded puck = gap from the sheet's wearer face to the branch / bar top - LAND_FIT."""
    xs, zs, top = frame_top(h, -124.0, 124.0, Z_LO_V2)
    out = []
    for (x, z) in pucks():
        i = int(np.argmin(np.abs(xs - x)))
        j = int(np.argmin(np.abs(zs - z)))
        y_plane = float(sleeve_y(z) + stay_r(z))
        win = top[max(i - 3, 0):i + 4, max(j - 3, 0):j + 4]
        gap = y_plane - float(np.nanmax(win))
        out.append({"x": x, "z": z, "gap_mm": gap, "height_mm": max(gap - LAND_FIT, 0.0)})
    return out


def write_dxf(opt: Option, path) -> dict:
    """Water-jet / CNC cut file. Layers: CUT (outline and slots), MARK (etched bond lines for the
    tubes and pucks; do not cut), TEXT. Units mm, true scale, part origin = frame x, frame z."""
    import ezdxf
    shape = part_shape(opt)
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for ln, col in (("CUT", 1), ("MARK", 5), ("TEXT", 7)):
        doc.layers.add(ln, color=col)
    msp = doc.modelspace()
    geoms = [shape] if shape.geom_type == "Polygon" else list(shape.geoms)
    n_cut = 0
    for g in geoms:
        msp.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
        n_cut += 1
        for ring in g.interiors:
            msp.add_lwpolyline(list(ring.coords), close=True, dxfattribs={"layer": "CUT"})
            n_cut += 1
    for (zt, od, idd) in EDGE_TUBES:
        msp.add_line((-116.0, zt), (116.0, zt), dxfattribs={"layer": "MARK"})
    for (x, z) in pucks():
        msp.add_circle((x, z), PUCK_D / 2, dxfattribs={"layer": "MARK"})
    msp.add_text(f"BP-06 rev B SPREADER  {opt.name}  qty 1  bag face up",
                 dxfattribs={"layer": "TEXT", "height": 3.5}).set_placement((-118.0, Z_LO_V2 - 10.0))
    doc.saveas(path)
    return {"path": str(path), "n_cut_loops": n_cut, "area_mm2": float(shape.area)}


def write_clip_dxf(path, t_sheet: float) -> dict:
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=1)
    doc.layers.add("TEXT", color=7)
    msp = doc.modelspace()
    out = {}
    for k, (name, zc, so) in enumerate((("A", 260.0, 0.0), ("B", 119.0, float(stay_r(260.0) - stay_r(119.0))))):
        r = float(stay_r(zc)) if name == "B" else float(np.mean(stay_r(np.array([166.0, 260.0, 400.0]))))
        prof = clip_profile(r, t_sheet, so)
        ox = k * 50.0
        msp.add_lwpolyline([(x + ox, y) for x, y in prof.exterior.coords], close=True, dxfattribs={"layer": "CUT"})
        for ring in prof.interiors:
            msp.add_lwpolyline([(x + ox, y) for x, y in ring.coords], close=True, dxfattribs={"layer": "CUT"})
        qty = 2 if name == "B" else 2 * (len(CLIP_Z) - 1)
        msp.add_text(f"CLIP {name}  MJF PA12  extrude {CLIP_W_BY_Z.get(zc, CLIP_W):.0f} mm  qty {qty}",
                     dxfattribs={"layer": "TEXT", "height": 2.5}).set_placement((ox - 18.0, -26.0))
        out[name] = {"r_stay": r, "standoff": so, "area_mm2": prof.area, "qty": qty,
                     "mass_g": clip_mass_g(prof, CLIP_W_BY_Z.get(zc, CLIP_W)), "profile": prof}
    doc.saveas(path)
    return out


if __name__ == "__main__":       # pragma: no cover
    from .spreader_report import run
    run()
