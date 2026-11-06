"""Spreader layout study (BP-06 rev C): change the frame behind the sheet so a thin, cheap sheet works.

Owner decision 2026-11-05: support the sheet the way the leaders do (Mystery Ranch 0.060 in HDPE,
Kifaru 1/16 in, Seek Outside removable cross stays) instead of making the sheet stiff. The sandwich v2
(154 g, $188, ``spreader.py``) is the fallback.

What this module does:

1. Layout options for the printed branch frame behind the sheet (``layouts()``): printed cross-ribs at
   2-4 levels, X ribs, a coarse grid, two removable carbon cross stays in printed sockets, and extended
   branches/edge ribs. Every printed rib is flush with the sheet plane (the stay-crown plane), so the sheet
   lands on it without bonded pucks (HDPE cannot be bonded).
2. A rib-layer SIMP on the window (``rib_simp``): a PAHT rib layer under the sheet, density-penalised
   bending stiffness, minimum compliance for the meat pressure plus a grid of bone ends. It shows where
   bone-end support is worth printing material.
3. The sheet check on each layout (``evaluate``): the sheet is thin and flexible, so it is solved with the
   von Karman large-deflection plate (``plate_grid.solve_von_karman``), on unilateral contact with the stays,
   branch lands, ribs and tubes (all beams, hot/wet PAHT or carbon). Loads are HA-LS-1 rev B C5 (walking
   1.6 g, factored 2.0 g x 1.5) plus a bone end (20 % of 68 kg on a 22 mm patch) at named positions
   (centre, edges, notch roots, bay centres between supports) and on a grid.
4. The frame check on each printed layout (``frame_check``): the ribs are merged into the frame distance
   field and every HA-LS-1 rev B case is re-run on the 2 mm voxel FEA (``frame_production.verify_solid``).

Run: python -m huntkit.gendesign.spreader_layout   (writes the record via spreader_layout_report)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from huntkit.fea.composite import DEFAULT_KNOCKDOWN, Laminate, Q_matrix, T_eps, tsai_wu_fi_vec
from huntkit.fea.plate_grid import (Beam, GridPlate, Spring, iso_A, iso_D, iso_surface_vm, solve_von_karman)
from huntkit.materials import load

from . import spreader as S

G = 9.80665
KD = DEFAULT_KNOCKDOWN
PAHT = "pa12_cf_fdm_paht"
LAND_FIT = 0.3                    # printed land / rib top to the sheet: print tolerance (mm)
# Flat sheet plane: through the stay crowns over z 165-430 (stay r 13.9 mm at the 1.05 scale).
R_PLANE = float(S.stay_r(300.0))


def plane_y(z):
    return S.sleeve_y(z) + R_PLANE


def branch_y(z):
    t = np.clip((np.asarray(z, float) - 165.0) / 320.0, 0.0, 1.0)
    return S.sleeve_y(z) + 6.0 * np.sin(np.pi * t)


# ============================================================================ materials
# HDPE fatigue: Djebli et al., ETASR 4(2) 2014, PE-100 uniaxial, R = 0, 2 Hz, Basquin (Ps 50 %):
# Smax = 32.46 N^-0.067 MPa -> 15.0 MPa at 1e5 cycles. HDPE yield falls about linearly with temperature
# (PE-100 pipe: 32 -> 9 MPa from -10 to 70 C, KFUPM study) -> ~0.78 at 40 C.
HDPE_FAT_1E5 = 32.46 * 1e5 ** -0.067
HOT_PE = 0.78


@dataclass
class Sheet:
    key: str
    name: str
    mid: str
    t: float
    kind: str = "iso"            # iso (thermoplastic) | lam (laminate)
    lam: Laminate | None = None
    usd: float = 0.0             # cut part, see cost table
    buy: str = ""

    @property
    def E(self):
        return float(load(self.mid).require("youngs_modulus_mpa"))

    @property
    def nu(self):
        return float(load(self.mid).get("poisson", 0.4))

    @property
    def rho(self):
        if self.lam is not None:
            return self.lam.areal_mass_kg_m2() / self.t * 1000.0
        return float(load(self.mid).require("density_kg_m3"))

    def D(self):
        return self.lam.D if self.lam is not None else iso_D(self.E, self.t, self.nu)

    def A(self):
        return self.lam.A if self.lam is not None else iso_A(self.E, self.t, self.nu)

    def yield_hot(self) -> float:
        return float(load(self.mid).require("yield_strength_mpa")) * HOT_PE

    def fat_allow(self) -> float:
        # ASSUMPTION: UHMWPE takes the HDPE Basquin curve scaled by the yield ratio
        sy = float(load(self.mid).require("yield_strength_mpa"))
        return HDPE_FAT_1E5 * sy / 26.0 * HOT_PE


def sheets() -> dict:
    g10 = S.qi_lam(1.0, S._glass())
    return {
        "hdpe15": Sheet("hdpe15", "HDPE 1.5 mm (0.060 in)", "hdpe_sheet", 1.5,
                        buy="HDPE framesheet stock, CNC / jigsaw + file"),
        "hdpe10": Sheet("hdpe10", "HDPE 1.0 mm (0.040 in)", "hdpe_sheet", 1.0),
        "uhmw15": Sheet("uhmw15", "UHMWPE 1.5 mm (1/16 in)", "uhmwpe_sheet", 1.5),
        "g10_10": Sheet("g10_10", "G10-class glass/epoxy 1.0 mm", "gfrp_eglass_ud_epoxy_ply", 1.0, "lam", g10,
                        buy="G10/FR4 sheet, water-jet"),
    }


def lam_fi_nm(lam: Laminate, N: np.ndarray, M: np.ndarray, kd=KD) -> np.ndarray:
    """Tsai-Wu FI (load-proportional, = 1/SF) for running loads N and moments M (..., 3), symmetric laminate."""
    shp = N.shape[:-1]
    Nf, Mf = N.reshape(-1, 3), M.reshape(-1, 3)
    e0 = np.linalg.solve(lam.A, Nf.T)
    k = np.linalg.solve(lam.D, Mf.T)
    best = np.zeros(len(Nf))
    for i, (p, a) in enumerate(zip(lam.plies, lam.angles)):
        pk = p.knocked_down(kd)
        for zz in (lam.z[i], lam.z[i + 1]):
            sig = (Q_matrix(p) @ T_eps(a) @ (e0 + zz * k)).T
            best = np.maximum(best, tsai_wu_fi_vec(sig, pk))
    return best.reshape(shp)


# ============================================================================ layouts
@dataclass
class Rib:
    pts: list                     # [(x, z), ...] polyline in the sheet plane
    b: float = 7.0                # width in the sheet plane
    d: float = 14.0               # depth from the sheet plane toward the wearer
    kind: str = "rib"             # rib (printed) | tube (removable carbon cross stay) | land
    ends: tuple = ("stay", "stay")   # stay | branch | free | socket
    od: float = 0.0
    idd: float = 0.0
    tag: str = ""
    lift: float = 0.0             # sheet plane raised above the stay crowns (mm), see Layout.lift

    def length(self) -> float:
        p = np.asarray(self.pts, float)
        return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


@dataclass
class Layout:
    key: str
    name: str
    family: str
    ribs: list = field(default_factory=list)
    note: str = ""
    sockets: int = 0              # printed socket pairs for removable tubes
    lift: float = 0.0             # sheet plane raised this far above the crown plane (clip saddles carry it)

    @property
    def tubes(self):
        return [r for r in self.ribs if r.kind == "tube"]

    @property
    def printed(self):
        return [r for r in self.ribs if r.kind != "tube"]


STAY_IN = 103.0                   # rib ends: inside the stay wall, clear of the 9 mm sleeve bore


def _bx(z):
    return float(S.branch_x(z))


def _hrib(z, b=7.0, d=14.0, tag="", to="stay"):
    """Horizontal rib at height z, stay-to-stay or branch-to-branch."""
    if to == "stay" or not (165.0 < z < 485.0):
        x = STAY_IN
        ends = ("stay", "stay")
    else:
        x = _bx(z) - 2.0
        ends = ("branch", "branch")
    return Rib([(-x, z), (x, z)], b, d, ends=ends, tag=tag or f"z{z:.0f}")


def lands() -> list:
    """Printed flat lands on top of the inboard branches and the z 330 bar, flush with the sheet plane.
    They replace the 11 bonded pucks of v2 (HDPE takes no bond)."""
    out = []
    zz = np.arange(168.0, 431.0, 6.0)
    for s in (1.0, -1.0):
        out.append(Rib([(s * _bx(z), float(z)) for z in zz], 8.0, 0.0, kind="land", ends=("free", "free"),
                       tag=f"branch land {'R' if s > 0 else 'L'}"))
    out.append(Rib([(-STAY_IN, 330.0), (STAY_IN, 330.0)], 8.0, 0.0, kind="land", tag="bar land"))
    return out


EDGE_LO, EDGE_HI = 121.0, 422.0   # edge ribs under the sheet's bottom and top edges (sheet z 112-430)


TUBE_OD, TUBE_ID = 12.0, 10.0
SHEET_LIFT = 6.0                  # d6L: sheet plane raised on the clip saddles
SADDLE_L = 10.0                   # saddle under the sheet = the clip width (clip_profile standoff)


def _tube(z, od=TUBE_OD, idd=TUBE_ID, lift=0.0):
    """Removable roll-wrapped carbon cross stay: stay-to-stay below the branches, branch-to-branch above."""
    x = STAY_IN if not (165.0 < z < 485.0) else _bx(z) - 2.0
    return Rib([(-x, z), (x, z)], kind="tube", ends=("socket", "socket"), od=od, idd=idd, tag=f"tube z{z:.0f}",
               lift=lift)


def layouts() -> list[Layout]:
    L = lands
    edges = lambda: [_hrib(EDGE_LO, tag="bottom edge"), _hrib(EDGE_HI, tag="top edge", to="branch")]
    out = [
        Layout("e_edges", "(e) branch lands + edge ribs (extended branches / struts to the free edges)", "e",
               L() + edges(), "no rib in the window; only the free edges and the branches carry the sheet"),
        Layout("a2", "(a) 2 cross-ribs: z 225, 385 + edge ribs", "a",
               L() + edges() + [_hrib(225.0, to="branch"), _hrib(385.0, to="branch")]),
        Layout("a3", "(a) 3 cross-ribs: z 210, 265, 385 + edge ribs", "a",
               L() + edges() + [_hrib(z, to="branch") for z in (210.0, 265.0, 385.0)]),
        Layout("a4", "(a) 4 cross-ribs: z 175, 225, 280, 385 + edge ribs", "a",
               L() + edges() + [_hrib(z, to="branch") for z in (175.0, 225.0, 280.0, 385.0)]),
        Layout("bX", "(b) X ribs in the two bays + edge ribs", "b",
               L() + edges() + [
                   Rib([(-_bx(172.0) + 2, 172.0), (_bx(322.0) - 2, 322.0)], ends=("branch", "branch"), tag="X1"),
                   Rib([(_bx(172.0) - 2, 172.0), (-_bx(322.0) + 2, 322.0)], ends=("branch", "branch"), tag="X2"),
                   Rib([(-_bx(338.0) + 2, 338.0), (_bx(415.0) - 2, 415.0)], ends=("branch", "branch"), tag="X3"),
                   Rib([(_bx(338.0) - 2, 338.0), (-_bx(415.0) + 2, 415.0)], ends=("branch", "branch"), tag="X4")]),
        Layout("cgrid", "(c) coarse grid: 3 cross-ribs + spine rib x 0 + edge ribs", "c",
               L() + edges() + [_hrib(z, to="branch") for z in (210.0, 265.0, 385.0)] +
               [Rib([(0.0, EDGE_LO), (0.0, EDGE_HI)], 6.0, 12.0, ends=("free", "free"), tag="spine")]),
        Layout("d_tubes", "(d) 2 removable carbon cross stays (12/10 mm roll-wrapped) in printed sockets + edge ribs",
               "d", L() + edges() + [_tube(225.0), _tube(385.0)],
               "Seek-Outside-like: the tubes pop out of printed sockets on the branches to wash the frame", sockets=2),
        Layout("d4_tubes", "(d+e) 4 removable carbon cross stays: both free edges + z 225, 385, in printed sockets",
               "d", L() + [_tube(124.0), _tube(225.0), _tube(385.0), _tube(420.0)],
               "the free edges sit on tubes too; no printed rib in the window", sockets=4),
        Layout("d6_tubes", "(d+e) 6 removable carbon cross stays at about 50 mm pitch (z 124, 165, 225, 280, 385, 420)",
               "d", L() + [_tube(z) for z in (124.0, 165.0, 225.0, 280.0, 385.0, 420.0)],
               "bays small enough that the meat pressure does not yield or bottom the HDPE", sockets=6),
        Layout("d6L_tubes", "(d+e) 6 removable carbon cross stays (14/12 at z 124, 165, 225; 12/10 at z 280, 385, 420), sheet raised 6 mm on the clip saddles",
               "d", [_tube(z, 14.0, 12.0, lift=SHEET_LIFT) for z in (124.0, 165.0, 225.0)] +
               [_tube(z, lift=SHEET_LIFT) for z in (280.0, 385.0, 420.0)],
               "the tubes sit 6 mm further from the back, so a leaning torso under the factored load still clears them",
               sockets=6, lift=SHEET_LIFT),
        Layout("d6n_tubes", "(d+e) 6 removable carbon cross stays, no branch/bar lands (mass cut of d6)",
               "d", [_tube(z) for z in (124.0, 165.0, 225.0, 280.0, 385.0, 420.0)],
               "the sheet bears on the tubes and the crowns; the branches and bar are left as printed", sockets=6),
    ]
    return out


def layout_by_key(key: str) -> Layout:
    return next(l for l in layouts() if l.key == key)


# ============================================================================ frame geometry
def _rib_sdf(pts: np.ndarray, rib: Rib) -> np.ndarray:
    """Rounded-rectangle cross-section b x d swept along the rib polyline. Top flush with the sheet plane."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    P = np.asarray(rib.pts, float)
    dn = np.full(len(pts), 1e9)
    for a, b in zip(P[:-1], P[1:]):
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (z - a[1]) * ab[1]) / (ab @ ab + 1e-12), 0.0, 1.0)
        dn = np.minimum(dn, np.hypot(x - (a[0] + t * ab[0]), z - (a[1] + t * ab[1])))
    yp = plane_y(z) + rib.lift
    if rib.kind == "land":
        # flat-topped land from the sheet plane down into the branch / bar
        bot = branch_y(z) if "branch" in rib.tag else S.sleeve_y(z)
        d = np.maximum(yp - LAND_FIT - bot, 1.0)
        top = yp - LAND_FIT
    elif rib.kind == "tube":
        # socket cup only: a short sleeve at each end, the tube itself is not printed
        return _socket_sdf(pts, rib)
    else:
        d = np.full(len(pts), rib.d)
        top = yp - LAND_FIT
    yc = top - d / 2.0
    hb, hd = rib.b / 2.0, d / 2.0
    r = np.minimum(0.45 * rib.b, hd * 0.9)
    qx = dn - (hb - r)
    qy = np.abs(y - yc) - (hd - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


SOCKET_L, SOCKET_WALL = 16.0, 2.5


def _socket_sdf(pts, rib: Rib) -> np.ndarray:
    """Printed open-top cup at each tube end: a 16 mm long sleeve, 2.5 mm wall, top cut open so the tube
    snaps in from the bag side (about a 220 deg wrap)."""
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    P = np.asarray(rib.pts, float)
    out = np.full(len(pts), 80.0)
    ro = rib.od / 2.0 + 0.15 + SOCKET_WALL
    for end, inward in ((P[0], P[1] - P[0]), (P[-1], P[-2] - P[-1])):
        u = inward / np.linalg.norm(inward)
        s = (x - end[0]) * u[0] + (z - end[1]) * u[1]          # along the tube, from the end inward
        yc = plane_y(z) + rib.lift - LAND_FIT - rib.od / 2.0
        n = np.hypot(-(x - end[0]) * u[1] + (z - end[1]) * u[0], y - yc)
        cyl = np.maximum(n - ro, np.maximum(-s - 2.0, s - SOCKET_L))
        bore = np.maximum(n - (rib.od / 2.0 + 0.15), np.maximum(-s, s - SOCKET_L - 1.0))
        cup = np.maximum(cyl, -bore)
        # open the top (bag side) above the tube axis + 0.35 r so it snaps in
        cup = np.maximum(cup, y - (yc + 0.35 * rib.od / 2.0))
        out = np.minimum(out, cup)
    return out


def frame_sdf_layout(pts: np.ndarray, layout: Layout | None, scale: float = S.SCALE) -> np.ndarray:
    from .frame_branch import _smin, frame_sdf
    sdf = frame_sdf(pts, scale=scale)
    if layout is None:
        return sdf
    for rib in layout.ribs:
        sdf = _smin(sdf, _rib_sdf(pts, rib), 3.0 if rib.kind != "tube" else 1.5)
    # keep the sleeve bores and the spine channel clear (the ribs end inside the stay wall)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    yc = S.sleeve_y(z)
    for s in (1.0, -1.0):
        r = np.hypot(x - s * 115.0, y - yc)
        tool = np.where((z > 160.0) & (z < 546.0), r - 9.0, 80.0)
        sdf = np.maximum(sdf, -tool)
    return sdf


def raster(layout: Layout | None, h: float = 2.0, scale: float = S.SCALE):
    from . import frame_topopt as ft
    dom = ft.build_domain(h, sleeve_wall=max(4.2 * scale, h))
    sdf = frame_sdf_layout(dom.grid.elem_centers(), layout, scale)
    solid = (sdf <= 0.0) | dom.passive_solid
    solid &= ~dom.passive_void
    return dom, solid


def frame_check(layout: Layout | None, h: float = 2.0) -> dict:
    """HA-LS-1 rev B on the 2 mm voxel body with the layout's ribs merged in."""
    from . import frame_production as prod
    from . import frame_topopt as ft
    from .frame_branch import solid_mass_g
    sets = ft.beam_loadsets(log=None)
    dom, solid = raster(layout, h)
    use = prod.verify_solid(dom, solid, sets)
    by = {}
    for c in use["cases"]:
        by[c["case"]] = min(by.get(c["case"], 99.0), c["sf"])
    return {"key": layout.key if layout else "base", "body_g": solid_mass_g(solid, h), "cases": by,
            "sf_min": use["sf_strength_min"], "sf_fatigue": use["sf_fatigue"], "sf_creep": use["sf_creep_rupture"],
            "governing": use["governing"], "torsion_rel": use["torsion_rel"], "h": h}


def frame_mesh(layout: Layout | None, h: float = 2.2, scale: float = S.SCALE):
    from skimage.measure import marching_cubes
    import trimesh
    x0 = np.array([-156.0, -64.0, -8.0])          # padded past the body on every side so the surface closes
    dims = np.array([312.0, 112.0, 562.0])
    n = np.maximum((dims / h).astype(int), 2)
    axes = [x0[i] + np.arange(n[i]) * h for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    sdf = frame_sdf_layout(np.c_[X.ravel(), Y.ravel(), Z.ravel()], layout, scale).reshape(X.shape)
    for ax in range(3):                            # force the domain boundary outside
        sl = [slice(None)] * 3
        for k in (0, -1):
            sl[ax] = k
            sdf[tuple(sl)] = np.maximum(sdf[tuple(sl)], 1.0)
    v, f, _, _ = marching_cubes(sdf, level=0.0, spacing=(h, h, h))
    m = trimesh.Trimesh(v + x0, f, process=False)
    trimesh.smoothing.filter_taubin(m, lamb=0.45, nu=-0.45, iterations=8)
    m.remove_unreferenced_vertices()
    return m


# ============================================================================ masses and costs
def rib_section_area(rib: Rib) -> float:
    r = min(0.45 * rib.b, rib.d / 2 * 0.9)
    return rib.b * rib.d - (4 - np.pi) * r * r


def tube_mass_g(rib: Rib) -> float:
    rho = float(load("cfrp_rollwrapped_tube").require("density_kg_m3"))
    return np.pi / 4 * (rib.od ** 2 - rib.idd ** 2) * (rib.length() + 2 * SOCKET_L) * rho / 1e6


def clips_g(t_sheet: float, lift: float = 0.0) -> float:
    """6 MJF PA12 clips; with a lift, each carries a saddle under the sheet (clip_profile standoff)."""
    r_mid = float(np.mean(S.stay_r(np.array(S.CLIP_Z))))
    return float(2 * len(S.CLIP_Z) * S.clip_mass_g(S.clip_profile(r_mid, t_sheet, lift), S.CLIP_W))


def sheet_shape():
    return S.part_shape()


def sheet_mass_g(sheet: Sheet) -> float:
    return float(sheet_shape().area * sheet.t * sheet.rho / 1e6)


# ============================================================================ plate model
def _beam_EI(rib: Rib) -> float:
    if rib.kind == "tube":
        E = float(load("cfrp_rollwrapped_tube").require("youngs_modulus_mpa"))
        return E * np.pi * (rib.od ** 4 - rib.idd ** 4) / 64.0
    E = float(load(PAHT).require("youngs_modulus_xy_mpa")) * S.PAHT_HOT_WET
    return E * rib.b * rib.d ** 3 / 12.0


def _sample(rib: Rib, h: float) -> np.ndarray:
    P = np.asarray(rib.pts, float)
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(int(np.ceil(np.linalg.norm(b - a) / h)), 1)
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def build_model(layout: Layout | None, sheet: Sheet, h: float = 4.0):
    """Sheet on the frame + layout. Returns (plate, info)."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    shape = S.outline_v2()
    minx, miny, maxx, maxy = shape.bounds
    x0 = np.floor(minx / h) * h
    nx = int(np.ceil((maxx - x0) / h))
    z_lo = np.floor(miny / h) * h
    ny = int(np.ceil((S.Z_HI - z_lo) / h))
    ps = prep(shape)
    pl = GridPlate(x0, z_lo, nx, ny, h, sheet.D())
    exy = pl.elem_xy()
    pl.active = np.array([[ps.contains(Point(*exy[i, j])) for j in range(ny)] for i in range(nx)])
    nxy = pl.node_xy()
    actn = pl.active_nodes()
    xs, zs, top = S.frame_top(h, x0, x0 + nx * h, z_lo)
    i = np.clip(np.round((nxy[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1)
    j = np.clip(np.round((nxy[:, 1] - zs[0]) / h).astype(int), 0, len(zs) - 1)
    topn = top[i, j]
    lift = layout.lift if layout is not None else 0.0
    plane = plane_y(nxy[:, 1]) + lift
    gap = np.maximum(plane - topn, 0.0)
    keep_out = np.zeros(pl.nn, bool)
    for zf in S.FAIRLEADS_Z:
        keep_out |= (np.abs(np.abs(nxy[:, 0]) - S.STAY_X) <= S.FAIRLEAD_HALF_X + S.NOTCH_CLEAR) & \
                    (np.abs(nxy[:, 1] - zf) <= S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR)
    E = float(load(PAHT).require("youngs_modulus_xy_mpa")) * S.PAHT_HOT_WET
    rb, rbar = 6.2 * S.SCALE, 6.5 * S.SCALE
    zb = np.arange(165.0, 485.0 + 1e-6, h)
    beams = {}
    for s in (1.0, -1.0):
        bm = pl.add_beam(Beam(np.c_[s * S.branch_x(zb), zb], E * np.pi * rb ** 4 / 4, tag=f"branch{'R' if s > 0 else 'L'}"))
        beams[bm.tag] = (bm, np.c_[s * S.branch_x(zb), zb])
    xbar = np.arange(-S.STAY_X, S.STAY_X + 1e-6, h)
    bar = pl.add_beam(Beam(np.c_[xbar, np.full_like(xbar, 330.0)], E * np.pi * rbar ** 4 / 4, tag="bar"))
    beams["bar"] = (bar, np.c_[xbar, np.full_like(xbar, 330.0)])
    for s, tag in ((1.0, "branchR"), (-1.0, "branchL")):
        bm, xy = beams[tag]
        kb = int(np.argmin(np.abs(xy[:, 1] - 330.0)))
        kx = int(np.argmin(np.abs(xbar - s * S.branch_x(330.0))))
        pl.add_tie(bm.dof0 + 2 * kb, bar.dof0 + 2 * kx)
    has_lands = layout is not None and any(r.kind == "land" for r in layout.ribs)
    # ribs and tubes as beams
    ribbeams = []
    for rib in (layout.printed + layout.tubes if layout else []):
        if rib.kind == "land":
            continue
        xy = _sample(rib, h)
        bm = Beam(xy, _beam_EI(rib), clamp_start=rib.ends[0] == "stay", clamp_end=rib.ends[1] == "stay",
                  pin_start=rib.ends[0] == "socket", pin_end=rib.ends[1] == "socket", tag=rib.tag)
        # a socket on a branch is pinned to the branch, not to ground
        for k_end, e in ((0, rib.ends[0]), (len(xy) - 1, rib.ends[1])):
            if e in ("branch", "socket") and 165.0 < xy[k_end, 1] < 485.0 and abs(xy[k_end, 0]) < 112.0:
                if e == "socket":
                    if k_end == 0:
                        bm.pin_start = False
                    else:
                        bm.pin_end = False
        pl.add_beam(bm)
        for k_end, e in ((0, rib.ends[0]), (len(xy) - 1, rib.ends[1])):
            if e in ("branch", "socket") and 165.0 < xy[k_end, 1] < 485.0 and abs(xy[k_end, 0]) < 112.0:
                tag = "branchR" if xy[k_end, 0] > 0 else "branchL"
                bb, bxy = beams[tag]
                kb = int(np.argmin(np.abs(bxy[:, 1] - xy[k_end, 1])))
                pl.add_tie(bm.dof0 + 2 * k_end, bb.dof0 + 2 * kb)
        # printed ribs fused where they cross a branch or the bar
        if rib.kind == "rib":
            for tag, (bb, bxy) in beams.items():
                dd = np.linalg.norm(xy[:, None, :] - bxy[None, :, :], axis=2)
                k, kb = np.unravel_index(np.argmin(dd), dd.shape)
                if dd[k, kb] < h * 0.75 and 0 < k < len(xy) - 1:
                    pl.add_tie(bm.dof0 + 2 * k, bb.dof0 + 2 * kb)
        ribbeams.append((rib, bm, xy))
    # rib-rib crossings
    for a in range(len(ribbeams)):
        for b in range(a + 1, len(ribbeams)):
            ra, ba, xa = ribbeams[a]
            rb_, bb, xb = ribbeams[b]
            if ra.kind != "rib" or rb_.kind != "rib":
                continue
            dd = np.linalg.norm(xa[:, None, :] - xb[None, :, :], axis=2)
            k, kb = np.unravel_index(np.argmin(dd), dd.shape)
            if dd[k, kb] < h * 0.75:
                pl.add_tie(ba.dof0 + 2 * k, bb.dof0 + 2 * kb)
    # contact springs
    kinds = np.full(pl.nn, "", dtype=object)
    on_rib = np.full(pl.nn, -1)
    rib_k = np.full(pl.nn, -1)
    for ir, (rib, bm, xy) in enumerate(ribbeams):
        d = np.linalg.norm(nxy[:, None, :] - xy[None, :, :], axis=2)
        k = np.argmin(d, axis=1)
        half = (rib.od if rib.kind == "tube" else rib.b) / 2.0
        sel = actn & ~keep_out & (d[np.arange(pl.nn), k] <= half + 1e-6)
        on_rib[sel] = ir
        rib_k[sel] = k[sel]
    for n in np.nonzero(actn & ~keep_out)[0]:
        x, z = nxy[n]
        if on_rib[n] >= 0:
            rib, bm, xy = ribbeams[on_rib[n]]
            pl.springs.append(Spring(int(n), 0.0, LAND_FIT, other=bm.dof0 + 2 * int(rib_k[n]), tag="rib"))
            kinds[n] = "rib"
            continue
        if not np.isfinite(topn[n]) or gap[n] >= 30.0:
            continue
        g = float(gap[n])
        xb = S.branch_x(z)
        if 165.0 < z < 485.0 and abs(abs(x) - xb) <= 8.0 and abs(x) < 103.0:
            if has_lands and z <= 431.0:
                g = LAND_FIT
            bm, xy = beams["branchR" if x > 0 else "branchL"]
            k = int(np.argmin(np.abs(xy[:, 1] - z)))
            pl.springs.append(Spring(int(n), 0.0, g, other=bm.dof0 + 2 * k, tag="branch"))
            kinds[n] = "branch"
        elif abs(z - 330.0) <= 8.0 and abs(x) <= 108.0:
            if has_lands:
                g = LAND_FIT
            k = int(np.argmin(np.abs(xbar - x)))
            pl.springs.append(Spring(int(n), 0.0, g, other=bar.dof0 + 2 * k, tag="bar"))
            kinds[n] = "bar"
        else:
            pl.springs.append(Spring(int(n), 0.0, g, tag="stay" if abs(x) >= 100.0 else "rigid"))
            kinds[n] = "stay" if abs(x) >= 100.0 else "rigid"
    clip_nodes = []
    for zc in S.CLIP_Z:
        sel = actn & (np.abs(nxy[:, 1] - zc) <= S.CLIP_W / 2 + 1e-6) & (np.abs(nxy[:, 0]) >= S.STAY_X - 4.0)
        for n in np.nonzero(sel)[0]:
            pl.springs.append(Spring(int(n), S.clip_k(S.CLIP_W) / max(int(sel.sum()), 1), 0.0, sense=-1.0, tag="clip"))
            clip_nodes.append(int(n))
        if lift > 0:          # the clip's saddle pad (SADDLE_L long) carries the raised sheet over the crown
            sad = actn & (np.abs(nxy[:, 1] - zc) <= SADDLE_L / 2 + 1e-6) & (np.abs(nxy[:, 0]) >= S.STAY_X - 8.0)
            for n in np.nonzero(sad)[0]:
                pl.springs.append(Spring(int(n), 0.0, LAND_FIT, tag="saddle"))
    info = {"shape": shape, "plane": plane, "kinds": kinds, "ribbeams": ribbeams, "beams": beams,
            "clip_nodes": np.array(clip_nodes, int), "layout": layout, "sheet": sheet, "h": h}
    return pl, info


def support_distance(pl: GridPlate, info: dict) -> np.ndarray:
    """Distance (mm) from each active node to the nearest support line (crown, land, rib, tube)."""
    from scipy import ndimage
    nxy = pl.node_xy()
    sup = np.zeros(pl.nn, bool)
    for s in pl.springs:
        if s.tag in ("rib", "branch", "bar") or (s.tag == "stay" and s.gap < 2.0):
            sup[s.node] = True
    grid = sup.reshape(pl.ny + 1, pl.nx + 1)
    d = ndimage.distance_transform_edt(~grid) * pl.h
    return d.ravel()


def bay_positions(pl: GridPlate, info: dict, n: int = 4) -> dict:
    """The points of the sheet furthest from any support (bay centres), at least 40 mm apart, inside the
    bone-patch inset outline."""
    from shapely.geometry import Point
    d = support_distance(pl, info)
    nxy = pl.node_xy()
    inset = info["shape"].buffer(-S.BONE_D / 2 + 1.0)
    order = np.argsort(d)[::-1]
    out = {}
    for k in order:
        x, z = nxy[k]
        if x < -1e-6 or not inset.contains(Point(x, z)):
            continue
        if any(np.hypot(x - a, z - b) < 40.0 for a, b in out.values()):
            continue
        out[f"bay centre {len(out) + 1}"] = (float(x), float(z))
        if len(out) >= n:
            break
    return out


def named_positions() -> dict:
    p = dict(S.named_positions("v2"))
    p["top corner"] = (100.0, 414.0)
    p["bottom corner"] = (100.0, 126.0)
    return p


# ============================================================================ one case
def run_case(pl, info, kind: str, bone_xy=None, u0=None) -> dict:
    sheet: Sheet = info["sheet"]
    exy = pl.elem_xy()
    P = S.bone_n(kind) if bone_xy is not None else 0.0
    q = S.meat_pressure(exy[..., 1], kind, less_n=P)
    if bone_xy is not None:
        q = q + pl.patch_pressure(bone_xy[0], bone_xy[1], S.BONE_D, P)
    f = pl.load_vector(q)
    sol = solve_von_karman(pl, f, sheet.A(), fix_uv_nodes=info["clip_nodes"], n_steps=3, tol=1e-5,
                           max_newton=30, max_dw=6.0)
    act = pl.active
    if sheet.kind == "iso":
        vm = iso_surface_vm(sol["N"], sol["M"], sheet.t).max(axis=2)
        vm[~act] = 0.0
        stress = vm
    else:
        fi = lam_fi_nm(sheet.lam, sol["N"], sol["M"]).max(axis=2)
        fi[~act] = 0.0
        stress = fi
    rib = rib_stress(pl, info, sol["u"])
    return {"sol": sol, "w": sol["w"], "stress": stress, "P": P, "rib": rib}


def rib_stress(pl, info, u) -> dict:
    """Max bending stress in the printed ribs / tubes and their max deflection."""
    out = {"sig": 0.0, "tag": "", "w_max": 0.0, "fi_paht": 0.0, "fi_tube": 0.0, "rib_w": {}}
    s_xy = float(load(PAHT).require("tensile_strength_xy_mpa")) * float(load(PAHT).get("env_knockdown_ratio", 0.8))
    tub = load("cfrp_rollwrapped_tube")
    s_t = min(float(tub.require("ultimate_strength_mpa")) * KD["hot_wet"],
              float(tub.require("compressive_strength_mpa")) * KD["hot_wet"] * KD["impact_comp"])
    for rib, bm, xy in info["ribbeams"]:
        n = len(xy)
        w = u[bm.dof0:bm.dof0 + 2 * n:2]
        th = u[bm.dof0 + 1:bm.dof0 + 2 * n:2]
        L = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        kap = np.abs(np.diff(th) / L)
        M = bm.EI * kap
        if rib.kind == "tube":
            I = np.pi * (rib.od ** 4 - rib.idd ** 4) / 64.0
            sig = float((M * rib.od / 2 / I).max(initial=0.0))
            out["fi_tube"] = max(out["fi_tube"], sig / s_t)
        else:
            sig = float((6.0 * M / (rib.b * rib.d ** 2)).max(initial=0.0))
            out["fi_paht"] = max(out["fi_paht"], sig / s_xy)
        out["rib_w"][rib.tag] = (xy, w)
        if sig > out["sig"]:
            out["sig"], out["tag"] = sig, rib.tag
        out["w_max"] = max(out["w_max"], float(np.abs(w).max(initial=0.0)))
    return out


# Lumbar pan: the upper lumbar struts run from the hip pivot (0, -42, 120) into each stay at z 155
# (frame_branch.frame_sdf, r 7.5 x 1.05). Below that line the back rests on the hipbelt lumbar pad over the pan,
# so the skin cannot come closer to the sheet than the strut's wearer face.
PIVOT_Y, PIVOT_Z, STRUT_R = -42.0, 120.0, 7.5 * S.SCALE
LUMBAR_BLEND = 60.0               # ASSUMPTION: the back leaves the pan over 60 mm of height above the strut line


def _strut(x):
    t = np.clip(np.abs(x) / S.STAY_X, 0.0, 1.0)
    zs = PIVOT_Z + t * (155.0 - PIVOT_Z)
    ys = PIVOT_Y + t * (float(S.sleeve_y(155.0)) - 4.0 - PIVOT_Y) - STRUT_R
    return zs, ys


def skin_ref(x, z, indent: float, r_torso: float, member: bool = False):
    """Frame-y of the surface the back-system part must stay above (mm).

    Gutter (|x| < 65): the unloaded skin bulging into the gutter (radius r_torso) while the frame sinks into the
    rails by ``indent`` (spreader.clearance_field), except near the lumbar pan, where the back rests on the pan:
    below the strut line the reference is the strut's wearer face, blended to the gutter skin over 60 mm.
    Over a rail (|x| >= 65): the rail's top face (the stay's wearer face) for frame members; the spreader skin
    model for the sheet (``member=False``)."""
    x = np.abs(np.asarray(x, float))
    z = np.asarray(z, float)
    h_rail = S.RAIL_T * (1 - float(load("xlpe_foam_l200").require("compression_set_pct")) / 100.0)
    y_wear = S.sleeve_y(z) - S.stay_r(z)
    bulge = np.where(x < S.GUTTER_HALF, (S.GUTTER_HALF ** 2 - x ** 2) / (2.0 * r_torso), 0.0)
    yg = y_wear - h_rail + indent + bulge
    zs, ys = _strut(x)
    t = np.clip((z - zs) / LUMBAR_BLEND, 0.0, 1.0)
    y_lum = np.where(ys < yg, ys * (1 - t) + yg * t, yg)
    gut = x < S.GUTTER_HALF
    out = np.where(gut, y_lum, y_wear if member else y_wear - h_rail + indent)
    return out


def clearance(pl, info, w, rib: dict, indent: float, r_torso: float) -> float:
    """Minimum air (mm) between the back-system parts and the surface they must stay off: the sheet
    (plane - w) and the rib / tube bottoms (plane - 0.3 - depth - w_member). See ``skin_ref``."""
    nxy = pl.node_xy()
    act = pl.active_nodes()
    cs = info["plane"] - w - skin_ref(nxy[:, 0], nxy[:, 1], indent, r_torso)
    c = float(np.min(cs[act]))
    for rib_o, bm, xy in info["ribbeams"]:
        xr, zr = xy[:, 0], xy[:, 1]
        _, wr = rib["rib_w"][rib_o.tag]
        depth = rib_o.od if rib_o.kind == "tube" else rib_o.d
        y_bot = plane_y(zr) + rib_o.lift - LAND_FIT - depth - wr
        c = min(c, float((y_bot - skin_ref(xr, zr, indent, r_torso, member=True)).min()))
    return c


def skin(P_bone: float, x_bone: float, kind: str) -> dict:
    """Bone reaction into the nearer stay by the lever rule between the stays (ASSUMPTION; the sheet and
    ribs carry it to the stays), plus the meat share, through spreader.skin_pressure."""
    side = P_bone * (0.5 + min(abs(x_bone), S.STAY_X) / (2 * S.STAY_X))
    return S.skin_pressure(side, kind, bone_total_n=P_bone)


# ============================================================================ evaluate
def evaluate(layout: Layout | None, sheet: Sheet, h: float = 4.0, step: float | None = 48.0,
             keep: tuple = ()) -> dict:
    pl, info = build_model(layout, sheet, h)
    pos = named_positions()
    pos.update(bay_positions(pl, info))
    if step:
        for k, xy in enumerate(S.bone_positions(info["shape"], step)):
            pos.setdefault(f"grid {k}", xy)
    rows = []
    fields = {}
    meat_w = run_case(pl, info, "walk")
    meat_f = run_case(pl, info, "factored")
    for name, xy in pos.items():
        rw = run_case(pl, info, "walk", xy)
        rf = run_case(pl, info, "factored", xy)
        sk = skin(rw["P"], xy[0], "walk")
        skf = skin(rf["P"], xy[0], "factored")
        row = {"name": name, "x": xy[0], "z": xy[1],
               "s_walk": float(rw["stress"].max()), "s_fact": float(rf["stress"].max()),
               "w_walk": float(rw["w"][pl.active_nodes()].max()), "w_fact": float(rf["w"][pl.active_nodes()].max()),
               "w_bone_walk": float(rw["w"][pl.node_at(*xy)]),
               "rib_fi_fact": max(rf["rib"]["fi_paht"], rf["rib"]["fi_tube"]),
               "rib_fi_paht_walk": rw["rib"]["fi_paht"], "rib_fi_tube_walk": rw["rib"]["fi_tube"],
               "rib_tag": rf["rib"]["tag"], "rib_w_fact": rf["rib"]["w_max"],
               "clear_walk": clearance(pl, info, rw["w"], rw["rib"], sk["indent_mm"], S.R_TORSO),
               "clear_fact": clearance(pl, info, rf["w"], rf["rib"], skf["indent_mm"], S.R_TORSO),
               "clear_fact_lean": clearance(pl, info, rf["w"], rf["rib"], skf["indent_mm"], S.R_TORSO_LO),
               "clear_walk_lean": clearance(pl, info, rw["w"], rw["rib"], sk["indent_mm"], S.R_TORSO_LO),
               "skin_kpa": sk["peak_kpa"],
               "clip_lift_n": float(-rf["sol"]["spring_force"][[s.tag == "clip" for s in pl.springs]].min(initial=0.0))}
        rows.append(row)
        if name in keep:
            fields[name] = {"w_fact": rf["w"], "s_fact": rf["stress"], "s_walk": rw["stress"], "w_walk": rw["w"]}
    res = summarize(layout, sheet, rows, meat_w, meat_f, pl)
    res["rows"] = rows
    if keep:
        res["_fields"] = fields
        res["_plate"] = (pl, info)
    return res


def summarize(layout, sheet: Sheet, rows, meat_w, meat_f, pl) -> dict:
    worst = lambda k, f=max: f(rows, key=lambda r: r[k])
    s_w = max(worst("s_walk")["s_walk"], float(meat_w["stress"].max()))
    s_f = max(worst("s_fact")["s_fact"], float(meat_f["stress"].max()))
    if sheet.kind == "iso":
        sf_yield = sheet.yield_hot() / s_f
        sf_fat = sheet.fat_allow() / s_w
        # same convention as the frame FEA (verify_solid): 99th percentile, so single contact-edge elements at
        # the clip saddles and tube ends do not govern
        meat_sf = sheet.yield_hot() / max(float(np.percentile(meat_f["stress"][pl.active], 99)), 1e-9)
    else:
        sf_yield = 1.0 / s_f
        sf_fat = S.FAT_FI / s_w
        meat_sf = 1.0 / max(float(np.percentile(meat_f["stress"][pl.active], 99)), 1e-9)
    rib_fi_f = max(r["rib_fi_fact"] for r in rows)
    rib_fi_w_p = max(r["rib_fi_paht_walk"] for r in rows)
    rib_fi_w_t = max(r["rib_fi_tube_walk"] for r in rows)
    fat_paht = float(load(PAHT).get("fatigue_1e5_ratio", 0.3))
    out = {
        "layout": layout.key if layout else "none", "layout_name": layout.name if layout else "no layout change",
        "sheet": sheet.key, "sheet_name": sheet.name, "n_positions": len(rows),
        "s_walk_max": s_w, "s_fact_max": s_f, "s_where": worst("s_fact")["name"],
        "sf_sheet_yield": sf_yield, "sf_sheet_fatigue": sf_fat, "sf_sheet_meat_only": meat_sf,
        "w_fact_max": worst("w_fact")["w_fact"], "w_where": worst("w_fact")["name"],
        "w_bone_walk_center": next(r["w_bone_walk"] for r in rows if r["name"] == "center"),
        "rib_sf_fact": 1.0 / max(rib_fi_f, 1e-9),
        "rib_sf_fatigue": min(fat_paht / max(rib_fi_w_p, 1e-9), (S.FAT_FI / max(rib_fi_w_t * 1.0, 1e-9))),
        "rib_where": max(rows, key=lambda r: r["rib_fi_fact"])["rib_tag"],
        "clear_walk_min": worst("clear_walk", min)["clear_walk"], "clear_fact_min": worst("clear_fact", min)["clear_fact"],
        "clear_fact_lean_min": worst("clear_fact_lean", min)["clear_fact_lean"],
        "clear_walk_lean_min": worst("clear_walk_lean", min)["clear_walk_lean"],
        "clear_where": worst("clear_fact_lean", min)["name"],
        "skin_peak_kpa": worst("skin_kpa")["skin_kpa"],
        "clip_lift_max_n": max(r["clip_lift_n"] for r in rows),
        "sheet_g": sheet_mass_g(sheet), "clips_g": clips_g(sheet.t, layout.lift if layout else 0.0),
        "tubes_g": float(sum(tube_mass_g(r) for r in (layout.tubes if layout else []))),
    }
    out["checks"] = {
        "sheet_strict_no_yield": out["sf_sheet_yield"] >= 1.0,
        "sheet_fatigue_strict": out["sf_sheet_fatigue"] >= 1.0,
        "sheet_meat_only": out["sf_sheet_meat_only"] >= 1.0,
        "ribs_strength": out["rib_sf_fact"] >= 1.0,
        "ribs_fatigue": out["rib_sf_fatigue"] >= 1.0,
        "no_bottoming": out["clear_walk_min"] >= S.MESH_T and out["clear_fact_min"] >= 0.0,
        "no_bottoming_lean": out["clear_fact_lean_min"] >= 0.0,
        "skin_pressure": out["skin_peak_kpa"] <= S.PEAK_KPA,
    }
    if sheet.kind == "iso":
        out["checks"]["sheet_no_puncture"] = ductile_strain(sheet, s_f) <= 0.5 * float(
            load(sheet.mid).require("elongation_pct")) / 100.0
        out["strain_fact_neuber"] = ductile_strain(sheet, s_f)
    strict = ("sheet_strict_no_yield", "sheet_fatigue_strict")
    out["passes_strict"] = all(out["checks"].values()) if sheet.kind == "lam" else all(out["checks"].values())
    out["passes_barrier"] = all(v for k, v in out["checks"].items() if k not in strict)
    return out


def ductile_strain(sheet: Sheet, s_elastic: float) -> float:
    """Local strain at the bone-patch rim from the elastic peak by Neuber's rule on an elastic-perfectly-
    plastic curve: eps = s_e^2 / (E s_y) (s_e > s_y). Used for the barrier (no-puncture) check only."""
    sy = sheet.yield_hot()
    if s_elastic <= sy:
        return s_elastic / sheet.E
    return s_elastic ** 2 / (sheet.E * sy)


# ============================================================================ rib-layer SIMP
def rib_simp(sheet: Sheet | None = None, h: float = 6.0, volfrac: float = 0.10, d_rib: float = 14.0,
             iters: int = 30, p: float = 3.0, rmin: float = 10.0, log=None) -> dict:
    """Topology optimisation of a PAHT rib layer under the sheet (in the gendesign SIMP form: OC update,
    density filter, p = 3). Element bending stiffness D = D_sheet + rho^p D_rib (smeared rib layer of depth
    d_rib). Loads: factored meat pressure plus a 48 mm grid of factored bone ends; supports are the real
    crowns, branches and bar (contact frozen at the solid design's active sets, linearised). Linear plate."""
    from scipy import ndimage
    from huntkit.fea.plate_grid import _Dvec
    sheet = sheet or sheets()["hdpe15"]
    pl, info = build_model(Layout("simp", "simp", "f", lands()), sheet, h)
    act = pl.active.copy()
    exy = pl.elem_xy()
    E = float(load(PAHT).require("youngs_modulus_xy_mpa")) * S.PAHT_HOT_WET
    Drib = iso_D(E, d_rib, 0.35)
    Ds = sheet.D()
    cases = [None] + S.bone_positions(info["shape"], 48.0)
    loads, sets = [], []
    pl.D = np.broadcast_to(Ds + Drib, (pl.nx, pl.ny, 3, 3)).copy()
    pl._K0 = None
    for xy in cases:
        q = S.meat_pressure(exy[..., 1], "factored")
        if xy is not None:
            q = q + pl.patch_pressure(xy[0], xy[1], S.BONE_D, S.bone_n("factored"))
        f = pl.load_vector(q)
        loads.append(f)
        sets.append(pl.solve(f)["active"])
    rho = np.where(act, volfrac, 0.0)
    r = int(np.ceil(rmin / h))
    di, dj = np.meshgrid(np.arange(-r, r + 1), np.arange(-r, r + 1), indexing="ij")
    wk = np.maximum(rmin / h - np.hypot(di, dj), 0.0)
    Kb = pl.el.Kb
    Dv_rib = _Dvec(np.broadcast_to(Drib, (pl.nx, pl.ny, 3, 3)))
    hist = []
    for it in range(iters):
        pl.D = (Ds[None, None] + (np.maximum(rho, 1e-3) ** p)[..., None, None] * Drib[None, None])
        pl._K0 = None
        dc = np.zeros_like(rho)
        comp = 0.0
        for f, a0 in zip(loads, sets):
            u = pl.solve(f, active0=a0, max_iter=1)["u"]
            ue = u[pl.edof]
            ce = np.einsum("ija,ijab,ijb->ij", ue, np.einsum("ijk,kab->ijab", Dv_rib, Kb), ue)
            comp += float(f @ u)
            dc += -p * np.maximum(rho, 1e-3) ** (p - 1) * ce
        dc = ndimage.convolve(dc * rho, wk, mode="constant") / np.maximum(
            ndimage.convolve(np.maximum(rho, 1e-3), wk, mode="constant"), 1e-9)
        l1, l2 = 1e-12, 1e12
        target = volfrac * act.sum()
        while (l2 - l1) / (l1 + l2) > 1e-4:
            lm = 0.5 * (l1 + l2)
            rn = np.clip(rho * np.sqrt(np.maximum(-dc, 0) / lm), np.maximum(rho - 0.15, 1e-3),
                         np.minimum(rho + 0.15, 1.0))
            rn[~act] = 0.0
            if rn[act].sum() > target:
                l1 = lm
            else:
                l2 = lm
        rho = rn
        hist.append(comp)
        if log:
            log(f"rib simp {it} compliance {comp:.0f}")
    return {"rho": rho, "plate": pl, "info": info, "hist": hist, "volfrac": volfrac, "d_rib": d_rib,
            "mass_g": float(volfrac * act.sum() * h * h * d_rib * float(load(PAHT).require("density_kg_m3")) / 1e6)}


if __name__ == "__main__":          # pragma: no cover
    from .spreader_layout_report import run
    run()


# ============================================================================ local bone stress vs support pitch
def pitch_study(sheet: Sheet, pitches=(40.0, 64.0, 96.0, 136.0), h: float = 4.0, L: float = 240.0) -> list[dict]:
    """A bone end at the centre of a square bay of a sheet resting on a rigid square grid of line supports
    at ``pitch`` (unilateral), held in-plane at the outer edge. Von Karman solve, walking and factored bone.
    Shows how much of the sheet stress the support layout can remove at all."""
    out = []
    for s in pitches:
        n = int(L / h)
        pl = GridPlate(-L / 2, -L / 2, n, n, h, sheet.D())
        xy = pl.node_xy()
        lines = np.arange(-s / 2 - 4 * s, s / 2 + 4 * s + 1, s)
        on = np.isin(np.round(xy[:, 0]), lines) | np.isin(np.round(xy[:, 1]), lines)
        for k in np.nonzero(on)[0]:
            pl.springs.append(Spring(int(k), 0.0, 0.0))
        bnd = np.nonzero((np.abs(xy[:, 0]) > L / 2 - 1e-6) | (np.abs(xy[:, 1]) > L / 2 - 1e-6))[0]
        row = {"pitch": float(s)}
        for kind in ("walk", "factored"):
            P = S.bone_n(kind)
            f = pl.load_vector(pl.patch_pressure(0.0, 0.0, S.BONE_D, P))
            sol = solve_von_karman(pl, f, sheet.A(), fix_uv_nodes=bnd, n_steps=4)
            if sheet.kind == "iso":
                st = float(iso_surface_vm(sol["N"], sol["M"], sheet.t).max())
            else:
                st = float(lam_fi_nm(sheet.lam, sol["N"], sol["M"]).max())
            row[f"s_{kind}"] = st
            row[f"w_{kind}"] = float(sol["w"].max())
        out.append(row)
    return out


def sandwich_recheck(step: float | None = 48.0, key: str = "sw110c6d") -> dict:
    """Spreader v2 (the sandwich fallback) re-run with the lumbar-pan skin reference (``skin_ref``) in place
    of the bulging gutter skin below the strut line. Everything else as spreader.evaluate. ``key``: the option
    (the 2026-11-05 record is sw110c6d; the rev C production part is sw110c7d). The meat load follows
    ``spreader.MEAT_CG_MM`` (rev C 190 mm; the 2026-11-05 record was 150)."""
    orig = S.clearance_field

    def cf(pl, info, w, indent_mm, r_torso=S.R_TORSO, h_rail=None):
        nxy = pl.node_xy()
        c = info["plane"] - w - skin_ref(nxy[:, 0], nxy[:, 1], indent_mm, r_torso)
        c[~pl.active_nodes()] = np.nan
        return c
    try:
        S.clearance_field = cf
        opt = {o.key: o for o in S.options()}[key]
        r = S.evaluate(opt, h=4.0, step=step)
    finally:
        S.clearance_field = orig
    return {k: r[k] for k in ("clear_walk_min", "clear_fact_min", "clear_fact_lean_min", "clear_where", "mass_g",
                              "sf_fpf", "sf_fatigue")}
