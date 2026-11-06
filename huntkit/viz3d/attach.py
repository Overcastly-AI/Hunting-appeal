"""Pack 5200 bag-to-frame joint, spreader and back panel for the 3D model (design state 2026-11-06).

Every dimension comes from a record; nothing here is redrawn by eye:

- **Spreader BP-06 rev C (Sandwich v2):** outline, fairlead notches, clip slots, pucks, stand-off pads, edge tubes and
  the PA12 clip profile from :mod:`huntkit.gendesign.spreader` (the same functions write ``cut/spreader/*.dxf``);
  thickness and size from ``panels.yaml`` BP-06. The board is FLAT, parallel to the stay axis and bears on the stay
  crowns at the z 260 clip (``cut/spreader/README.md`` section 3: pad height = stay radius at z 260 minus at z 119).
- **Back panel:** :func:`huntkit.gendesign.back_rail.back_panel_pieces` (BP-01 mesh, BP-02 XLPE rails, BP-05 sleeve
  width, BP-08 carbon backers), rail z span ``spreader.RAIL_Z``.
- **Fairleads:** :mod:`huntkit.gendesign.bag_attach` (stations, cleat SDF, pin, hole, throat), the stay line of
  :mod:`huntkit.gendesign.frame_branch`. B-01 swells from ``designs/pack_5200/patterns_v31.py`` (B-13..B-15).
- **Joint:** :mod:`huntkit.gendesign.attach_system` (HOOD, LADDER, GUY, PIN, HOOK_RATED_N, WRAP, HOOD_TOP_MM,
  HOOD_FRONT_MM), ``panels.yaml`` B-11/B-17..B-23 sizes, placements from ``analysis/bag_attachment.md`` section 5.
- **Between mode:** ``analysis/meat_haul_modes.json`` ``between.angle_deg`` (250 mm at IM3 = 28.5 deg about z 60).
- **Cradle:** :mod:`huntkit.gendesign.meat_haul` US1_Z / US2_Z / BELLY_MM.

Visual-only choices that no record fixes are marked ``ASSUMPTION (visual)``.
Units mm, frame coordinates (x wearer's right, y aft toward the bag, z up from the stay feet).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from functools import lru_cache

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import geom as G
from .params import REPO

PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
ALL = ("pack", "pack_haul", "frame", "frame_haul")
BAGM = ("pack", "pack_haul")
BE = (0.0, 260.0, 0.0)            # bag explode offset (bag_v3)


# ============================================================================ records
def _S():
    from huntkit.gendesign import spreader
    return spreader


def _BA():
    from huntkit.gendesign import bag_attach
    return bag_attach


def _AS():
    from huntkit.gendesign import attach_system
    return attach_system


@lru_cache(maxsize=1)
def panels() -> dict:
    import yaml
    d = yaml.safe_load((PACK / "panels.yaml").read_text())
    return {r["id"]: r for r in d["panels"] if isinstance(r, dict) and "id" in r}


def panel_size(pid: str) -> tuple[float, float]:
    w, h = panels()[pid]["approx_size_mm"]
    return float(w), float(h)


@lru_cache(maxsize=1)
def patterns_v31():
    """designs/pack_5200/patterns_v31.py constants (swells B-13..B-15)."""
    name = "pack5200_patterns_v31"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, PACK / "patterns_v31.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def stay_y(z):
    from huntkit.gendesign.frame_branch import _sleeve_y
    return np.asarray(_sleeve_y(np.asarray(z, float)), float)


def stay_r(z):
    from huntkit.gendesign.frame_branch import stay_radius
    return np.asarray(stay_radius(np.asarray(z, float), _BA().SCALE), float)


def pin_y(z) -> float:
    """Pin axis y at a fairlead: hole centre HOLE_PROUD above the stay surface (bag_attach.fairlead_local)."""
    return float(stay_y(z) + stay_r(z) + _BA().HOLE_PROUD)


def board_t() -> float:
    return float(panels()["BP-06"]["thickness_mm"])


def board_wearer_y(z):
    """Wearer face of the flat spreader: parallel to the stay axis, on the stay crowns at the z 260 clip."""
    S = _S()
    return stay_y(z) + float(stay_r(S.CLIP_Z[1]))


def board_bag_y(z):
    return board_wearer_y(z) + board_t()


@lru_cache(maxsize=1)
def board_shape():
    return _S().part_shape()


def hinge() -> dict:
    """Hinge-pin axis (x through the z 60 pins) and the between-mode opening angle."""
    st = next(s for s in _BA().stations() if s["name"] == "hinge")
    mh = json.loads((ANALYSIS / "meat_haul_modes.json").read_text())["between"]
    return {"y": pin_y(st["z"]), "z": float(st["z"]), "angle_deg": float(mh["angle_deg"]),
            "opening_mm": {k: float(v) for k, v in mh["opening_mm"].items()},
            "source": "analysis/meat_haul_modes.json between (bag swung open about the z 60 pins)"}


class Swing:
    """Rotation of the bag about the hinge-pin axis (x) by the between-mode angle: the top goes aft."""

    def __init__(self, h: dict):
        self.yc, self.zc = h["y"], h["z"]
        a = np.radians(h["angle_deg"])
        self.c, self.s = np.cos(a), np.sin(a)

    def __call__(self, P, direction=False):
        P = np.array(P, float, copy=True)
        oy, oz = (0.0, 0.0) if direction else (self.yc, self.zc)
        y, z = P[..., 1] - oy, P[..., 2] - oz
        P[..., 1] = oy + y * self.c + z * self.s
        P[..., 2] = oz + z * self.c - y * self.s
        return P


# ============================================================================ small mesh helpers
def _uv(m, tile=40.0):
    v = np.asarray(m.vertices)
    m.metadata["uv"] = np.c_[v[:, 0] / tile, v[:, 2] / tile]
    return m


def _slab(shape, y_lo, t, tile=40.0):
    """Extrude a shapely outline in the frame (x, z) plane through y_lo(z) .. y_lo(z) + t (t may be negative)."""
    m = trimesh.creation.extrude_polygon(shape, abs(t))
    v = np.asarray(m.vertices, float).copy()
    x, z, h = v[:, 0], v[:, 1], v[:, 2]
    y = np.asarray(y_lo(z), float) + (h if t > 0 else -h)
    V = np.c_[x, y, z]
    F = m.faces
    idx = F.reshape(-1)
    uv = np.c_[x, z] / tile
    return G._mesh(V[idx], np.arange(len(idx)).reshape(-1, 3), uv[idx])


def _cyl(a, b, r, n=20):
    return G.tube([np.asarray(a, float), np.asarray(b, float)], r, n=n, tile=40.0)


def _loop_rod(c, ea, eb, A, B, r, n=56):
    """Closed rounded-rectangle rod (hook / ring), A along ea, B along eb."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    P = (np.asarray(c, float) + np.outer(np.sign(ct) * np.abs(ct) ** 0.45 * (A / 2 - r), ea)
         + np.outer(np.sign(st) * np.abs(st) ** 0.45 * (B / 2 - r), eb))
    P = np.vstack([P, P[:1]])
    return G.tube(P, r, n=12, tile=40.0)


def _eye_loop(pin, end, width, thick=2.4, r_in=3.6):
    """Webbing eye: a stadium loop round the pin, out to ``end`` (strap face normals point out of the loop)."""
    pin, end = np.asarray(pin, float), np.asarray(end, float)
    d = end - pin
    L = np.linalg.norm(d)
    d /= L
    e = np.array([0.0, -d[2], d[1]])
    ro = r_in + thick / 2
    pts, nrm = [], []
    for ph in np.linspace(np.pi / 2, 3 * np.pi / 2, 14):        # round the pin
        n_ = np.cos(ph) * d + np.sin(ph) * e
        pts.append(pin + ro * n_); nrm.append(n_)
    for ph in np.linspace(-np.pi / 2, np.pi / 2, 14):           # round the far end
        n_ = np.cos(ph) * d + np.sin(ph) * e
        pts.append(end + ro * n_); nrm.append(n_)
    pts.append(pts[0]); nrm.append(nrm[0])
    return G.ribbon(np.array(pts), width, thick, np.array(nrm), step=2.0)


# ============================================================================ drape (B-01 conforms + swells)
class Drape:
    """Frame face of the bag: the sewn swells over the fairleads (patterns_v31 SWELLS, cos^2 crest 16 x 50 mm, cones to
    the tips) plus the fabric pushed aft over the hard parts between bag and frame (spreader, edge tubes, clips, eyes,
    hooks). Applied as y := max(y + swell, cone-dilated obstacle height) to points on the frame half of the bag."""

    X0, X1, Z0, Z1, H = -170.0, 170.0, -20.0, 720.0, 2.0
    SLOPE, REACH = 0.6, 26.0          # ASSUMPTION (visual): fabric tents off a hard edge at about 1 in 1.7

    def __init__(self, face_y):
        self.face_y = face_y          # z -> drafted frame-face y (bag profile yf), selects the frame half
        self.xs = np.arange(self.X0, self.X1 + 1e-6, self.H)
        self.zs = np.arange(self.Z0, self.Z1 + 1e-6, self.H)
        self.F = np.full((len(self.xs), len(self.zs)), -1e3)
        self.Gd = None
        P = patterns_v31()
        self.swells = [(sx * P.STAY_X, zc, lo, up) for zc, lo, up in P.SWELLS.values() for sx in (-1.0, 1.0)]
        self.swell_h, self.swell_w = float(P.SWELL_H), float(P.SWELL_W)

    def _ij(self, x0, x1, z0, z1):
        i = (self.xs >= x0) & (self.xs <= x1)
        j = (self.zs >= z0) & (self.zs <= z1)
        return np.ix_(i, j)

    def box(self, x0, x1, z0, z1, y):
        ij = self._ij(x0, x1, z0, z1)
        Z = np.broadcast_to(self.zs[None, :], self.F.shape)[ij]
        yy = y(Z) if callable(y) else np.full(Z.shape, float(y))
        self.F[ij] = np.maximum(self.F[ij], yy)

    def poly(self, shape, y):
        import shapely
        X, Z = np.meshgrid(self.xs, self.zs, indexing="ij")
        m = shapely.contains_xy(shape, X, Z)
        yy = y(Z) if callable(y) else np.full(Z.shape, float(y))
        self.F[m] = np.maximum(self.F[m], yy[m])

    def points(self, P, pad=0.8):
        """Register the y-extent of a hard part (point cloud) column by column."""
        P = np.asarray(P, float)
        i = np.clip(np.round((P[:, 0] - self.X0) / self.H).astype(int), 0, len(self.xs) - 1)
        j = np.clip(np.round((P[:, 2] - self.Z0) / self.H).astype(int), 0, len(self.zs) - 1)
        np.maximum.at(self.F, (i, j), P[:, 1] + pad)

    def finish(self):
        from scipy.ndimage import grey_dilation
        r = int(self.REACH / self.H)
        k = np.arange(-r, r + 1) * self.H
        D = np.hypot(k[:, None], k[None, :])
        st = np.where(D <= self.REACH, -self.SLOPE * D, -1e3)
        self.Gd = grey_dilation(self.F, structure=st, mode="constant", cval=-1e3)
        return self

    def swell(self, x, z):
        out = np.zeros(np.shape(x))
        for xs, zc, lo, up in self.swells:
            dz = z - zc
            L = np.where(dz < 0, lo, up)
            f = np.clip(1.0 - np.abs(dz) / L, 0.0, 1.0)
            w = self.swell_w * np.maximum(f, 1e-6)
            u = np.clip((x - xs) / w, -0.5, 0.5)
            out = np.maximum(out, self.swell_h * f * np.cos(np.pi * u) ** 2 * (np.abs(x - xs) <= w / 2))
        return out

    def __call__(self, P):
        from scipy.ndimage import map_coordinates
        P = np.array(P, float, copy=True)
        if P.size == 0:
            return P
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        frame_half = y < self.face_y(z) + 60.0
        y2 = y + np.where(frame_half, self.swell(x, z), 0.0)
        if self.Gd is not None:
            hy = map_coordinates(self.Gd, [(x - self.X0) / self.H, (z - self.Z0) / self.H], order=1, mode="constant",
                                 cval=-1e3)
            y2 = np.where(frame_half, np.maximum(y2, hy), y2)
        P[:, 1] = y2
        return P


# ============================================================================ frame side
def frame_side(p: dict, g: dict, Part, block, face_y) -> dict:
    """Spreader, back panel, fairlead cleats, pins and captive eyes (all on the frame). Returns parts, the drape,
    and the anchor points the bag side needs (eye ends, hook centres, pins)."""
    S, BA, AS = _S(), _BA(), _AS()
    parts = []
    dr = Drape(face_y)
    t = board_t()

    # ---------------------------------------------------------------- spreader BP-06 rev C
    shape = board_shape()
    parts.append(Part("spreader_board", _slab(shape, board_wearer_y, t), "carbon_matte", "frame",
                      label=f"Spreader BP-06 rev C, Sandwich v2: twill / 7 mm ROHACELL 110 / twill, flat "
                            f"{panel_size('BP-06')[0]:.0f} x {panel_size('BP-06')[1]:.0f} x {t:.2f} mm, notched at "
                            "the cleats, 6 clip slots"))
    dr.poly(shape, lambda z: board_bag_y(z) + 0.8)
    tubes = []
    TUBE_L = 236.0                # cut/spreader/README.md section 3 (edge tubes 236 mm long); spreader_report.tube_meshes
    for zt, od, _idd in S.EDGE_TUBES:
        yc = float(board_bag_y(zt)) + od / 2
        tubes.append(_cyl([-TUBE_L / 2, yc, zt], [TUBE_L / 2, yc, zt], od / 2, n=24))
        dr.box(-TUBE_L / 2 - 2, TUBE_L / 2 + 2, zt - od / 2, zt + od / 2, yc + od / 2 + 0.8)
    parts.append(Part("spreader_tubes", G.concat(tubes), "carbon", "frame",
                      label="Pultruded carbon edge tubes 10/8 mm on the bag face (z 118.5, z 424)"))
    fit = []
    for row in S.puck_table():                       # bonded PAHT-CF pucks, wearer face, height = gap - 0.3
        x, z, h = row["x"], row["z"], max(row["height_mm"], 0.4)
        yw = float(board_wearer_y(z))
        fit.append(_cyl([x, yw - h, z], [x, yw + 0.2, z], S.PUCK_D / 2, n=20))
    for zp in S.PAD_Z:                               # stand-off pads under the bottom tab (README: 16 x 10 x 4.9)
        h = float(board_wearer_y(zp) - (stay_y(zp) + stay_r(zp)))
        for s in (-1, 1):
            fit.append(block([s * S.STAY_X, float(board_wearer_y(zp)) - h / 2 + 0.1, zp], (16.0, h + 0.2, S.CLIP_W), e=0.2))
    parts.append(Part("spreader_pucks", G.concat(fit), "printed_cf", "frame",
                      label="PAHT-CF pucks (11) and stand-off pads (2) on the wearer face"))
    clips = []
    for zc in S.CLIP_Z:
        r = float(stay_r(zc))
        so = float(board_wearer_y(zc) - (stay_y(zc) + r))
        prof = S.clip_profile(r, t, standoff=max(so, 0.0))
        for s in (-1, 1):
            m = G.plate(prof, [s * S.STAY_X, float(stay_y(zc)), zc], [s, 0, 0], [0, 1, 0], S.CLIP_W, tile=40.0)
            clips.append(m)
            dr.points(np.asarray(m.vertices))
    parts.append(Part("spreader_clips", G.concat(clips), "hardware", "frame",
                      label="MJF PA12 snap clips (6) at z 166 / 260 / 400"))

    # ---------------------------------------------------------------- fairlead cleats, pins, captive eyes
    from skimage.measure import marching_cubes
    cleats, cradle_cl = [], []
    hcell = 0.9
    pins_fixed, pins_hinge, eyes, eye_ends, hooks_at, pin_at = [], [], [], {}, {}, {}
    PIN_L, PIN_D = AS.PIN["L"], AS.PIN["d"]
    for st in BA.stations():
        z0, x0, s = st["z"], st["x"], st["sign"]
        r = float(stay_r(z0))
        y0 = float(stay_y(z0))
        hx = BA.THROAT / 2 + BA.CHEEK + 2.0
        ylo, yhi = r - BA.EMBED - 2.0, r + BA.HOLE_PROUD + BA.HOLE_D / 2 + BA.WALL_FRONT + 2.0
        xs = np.arange(-hx, hx + 1e-6, hcell)
        ys = np.arange(ylo, yhi + 1e-6, hcell)
        zs = np.arange(-BA.HALF_Z - 2.0, BA.HALF_Z + 2.0 + 1e-6, hcell)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        sdf = BA.fairlead_local(np.c_[X.ravel(), Y.ravel(), Z.ravel()], r).reshape(X.shape)
        v, f, _, _ = marching_cubes(sdf, level=0.12, spacing=(hcell, hcell, hcell))   # 0.12 mm proud of the print
        v = v + [xs[0], ys[0], zs[0]]
        V = np.c_[v[:, 0] + x0, v[:, 1] + y0, v[:, 2] + z0]
        try:                                       # the cleat is a few cm: a quarter of the marching-cube faces is plenty
            d = trimesh.Trimesh(V, f, process=False).simplify_quadric_decimation(face_count=max(len(f) // 4, 500))
            d = max(d.split(only_watertight=False), key=lambda c: len(c.faces))   # drop decimation slivers
            V, f = np.asarray(d.vertices), np.asarray(d.faces)
        except Exception:  # noqa: BLE001  (fast_simplification not installed: keep the full mesh)
            pass
        m = G._mesh(V, f, np.c_[V[:, 0], V[:, 2]] / 40.0)
        (cleats if st["name"] in ("hinge", "im1", "im2", "im3") else cradle_cl).append(m)
        py = pin_y(z0)
        pin_at[st["id"]] = np.array([x0, py, z0])
        pin = _cyl([x0 - PIN_L / 2, py, z0], [x0 + PIN_L / 2, py, z0], PIN_D / 2, n=16)
        if st["name"] == "hinge":
            ring = [np.array([x0 + s * (PIN_L / 2 + 6), py + 9 * np.cos(a), z0 + 9 * np.sin(a)])
                    for a in np.linspace(0, 2 * np.pi, 25)]
            pins_hinge += [pin, G.tube(np.array(ring), 1.5, n=8, tile=40.0)]     # Dyneema cord pull loop
        else:
            pins_fixed.append(pin)
        if st["name"].startswith("im"):
            ze = z0 - 18.0                                                     # ASSUMPTION (visual): eye 18 mm long
            ye = py
            if shape.intersects(box(x0 - 20, ze - 32, x0 + 20, ze)):          # IM1 / IM2: hang aft of the board
                ye = max(py, float(board_bag_y(ze)) + 3.4)
            end = np.array([x0, ye, ze])
            eye = _eye_loop(pin_at[st["id"]], end, BA.THROAT)
            eyes.append(eye)
            dr.points(np.asarray(eye.vertices))
            eye_ends[st["id"]] = end
            if st["bag_clip"]:
                hooks_at[st["id"]] = end + np.array([0, 0, -15.0])
                dr.box(x0 - 21, x0 + 21, ze - 31, ze + 1, ye + 2.6 + 0.8)
    parts.append(Part("fairlead_cleats", G.concat(cleats), "printed_cf", "frame",
                      label="Branch fairleads (8): printed cleats at the hinge z 60 and IM1-IM3 z 190 / 330 / 520"))
    parts.append(Part("cradle_fairleads", G.concat(cradle_cl), "printed_cf", "frame",
                      label="Cradle fairleads (4): under-strap anchors US1 z 95 / US2 z 142"))
    parts.append(Part("fairlead_pins", G.concat(pins_fixed), "aluminium", "frame",
                      label="7075 pins 5 mm in UHMWPE sleeves (US1/US2, IM1-IM3)"))
    parts.append(Part("hinge_pins", G.concat(pins_hinge), "aluminium", "frame", modes=BAGM,
                      label="Hinge pins z 60: tethered 5 mm 7075 pull-pins, Dyneema pull loops (come off with the bag)"))
    parts.append(Part("captive_eyes", G.concat(eyes), "webbing", "frame",
                      label="Captive webbing eyes on the IM1-IM3 pins (bag hooks and meat straps clip here)"))
    for st in BA.stations():                     # cradle cleat tips are not under a swell: the cloth drapes them
        if st["name"] in ("us1", "us2"):
            y_tip = float(stay_y(st["z"]) + stay_r(st["z"]) + BA.HOLE_PROUD + BA.HOLE_D / 2 + BA.WALL_FRONT)
            dr.box(st["x"] - 17, st["x"] + 17, st["z"] - 9, st["z"] + 9, y_tip + 1.5)

    # ---------------------------------------------------------------- back panel (released rails r120_b80)
    from huntkit.gendesign.back_rail import back_panel_pieces
    bp = back_panel_pieces()
    z_lo, z_hi = (float(v) for v in S.RAIL_Z)
    zz = np.linspace(z_lo, z_hi, 200)
    r_max = float(np.max(stay_r(zz)))

    def y_backer(z):                                   # bag-side face of the backers = the stays' wearer crowns
        return stay_y(z) - r_max
    bk, foam = [], []
    for s in (-1, 1):
        xc = s * S.STAY_X
        bshape = box(xc - bp["backer_w"] / 2, z_lo, xc + bp["backer_w"] / 2, z_hi).buffer(-10).buffer(10, quad_segs=8)
        bk.append(_slab(bshape, y_backer, -bp["backer_t"]))
        fshape = box(xc - bp["rail_w"] / 2, z_lo, xc + bp["rail_w"] / 2, z_hi).buffer(-6).buffer(6, quad_segs=8)
        foam.append(_slab(fshape, lambda z: y_backer(z) - bp["backer_t"], -bp["rail_t"]))
    zc_mesh = (z_lo + z_hi) / 2
    mz0, mz1 = zc_mesh - bp["mesh_h"] / 2, zc_mesh + bp["mesh_h"] / 2
    x_in = S.STAY_X - bp["rail_w"] / 2                 # rail inner edge: half the air gutter
    x_st_in = S.STAY_X - bp["sleeve_w"] / 2            # sleeve stitch line (stay CL - 70)
    x_out, x_st_out = S.STAY_X + bp["rail_w"] / 2, bp["mesh_w"] / 2
    sleeve_t, mesh_t = 0.6, float(S.MESH_T)            # sleeve ripstop ASSUMPTION (visual); mesh MESH_T

    def rise(ax):
        a = np.abs(ax)
        up = np.clip((a - x_st_in) / (x_in - x_st_in), 0, 1)
        dn = np.clip((x_st_out - a) / (x_st_out - x_out), 0, 1)
        return (np.sin(np.pi / 2 * np.minimum(up, dn))) ** 2

    def mesh_y(x, z):
        zc_ = np.clip(z, z_lo, z_hi)
        over = rise(x) * (np.abs(z - zc_) < 1e-9)       # rails stop at RAIL_Z; the mesh lies flat beyond them
        return y_backer(z) - bp["backer_t"] - sleeve_t - (bp["rail_t"]) * over

    def m_surf(u, v):
        return np.stack([u, mesh_y(u, v), v], -1)

    def m_nrm(u, v):
        return np.broadcast_to(np.array([0.0, -1.0, 0.0]), np.shape(u) + (3,))
    mesh = G.patch_shell(m_surf, m_nrm, (-x_st_out, x_st_out), (mz0, mz1), lambda s_, t_: np.full(np.shape(s_), mesh_t),
                         inset=0.0, nu=124, nv=24, tile=G.TILE_MM)
    parts.append(Part("back_panel", mesh, "spacer", "backpanel", explode=(0, -150.0, 0), xray=True,
                      label=f"BP-01 back panel spacer mesh {bp['mesh_w']:.0f} x {bp['mesh_h']:.0f} over the BP-05 "
                            f"rail sleeves and the {2 * x_in:.0f} mm air gutter"))
    parts.append(Part("rail_foam", G.concat(foam), "xlpe", "backpanel", explode=(0, -95.0, 0), xray=True,
                      label=f"BP-02 stay rails: {bp['rail_w']:.0f} x {bp['rail_l']:.0f} x {bp['rail_t']:.0f} mm "
                            "XLPE (Minicel L200 class)"))
    parts.append(Part("rail_backers", G.concat(bk), "carbon", "backpanel", explode=(0, -45.0, 0),
                      label=f"BP-08 rail backers: {bp['backer_w']:.0f} x {bp['backer_l']:.0f} x {bp['backer_t']:.2f} mm "
                            "2x2 twill carbon on the stays"))

    dr.finish()
    return {"parts": parts, "drape": dr, "eye_ends": eye_ends, "hooks_at": hooks_at, "pin_at": pin_at,
            "back_panel": dict(bp, gutter_mm=2 * x_in, rail_z=[z_lo, z_hi], mesh_z=[mz0, mz1]),
            "spreader": {"size_mm": [float(shape.bounds[2] - shape.bounds[0]), float(shape.bounds[3] - shape.bounds[1])],
                         "t_mm": t, "z": [float(shape.bounds[1]), float(shape.bounds[3])], "pucks": len(S.puck_table()),
                         "clips": 2 * len(S.CLIP_Z), "edge_tubes": len(S.EDGE_TUBES)}}


# ============================================================================ bag side
def u_at_x(S, x, z, half="frame", n=500):
    """Arc position u on the bag surface S at height z where the skin passes lateral x (outer or frame half)."""
    Lo, P = float(S.outer_half(z)), float(S.perim(z))
    sg = 1.0 if x >= 0 else -1.0
    us = sg * (np.linspace(0, Lo / 2, n) if half == "outer" else np.linspace(Lo / 2, P / 2, n))
    xs = np.abs(S.pt(us, np.full(n, float(z)))[:, 0])
    o = np.argsort(xs)
    return float(np.interp(abs(x), xs[o], us[o]))


def face_pt(S, x, z, lift=0.0, half="frame"):
    u = u_at_x(S, x, z, half)
    P = S.pt(np.array([u]), np.array([float(z)]))[0]
    N = S.nrm(np.array([u]), np.array([float(z)]))[0]
    return P + N * lift, N


def frame_shard(S, poly_sz, thick, lift=0.5, max_edge=14.0):
    """Conformal plate on the bag's FRAME face, laid out in (s, z): s = arc distance from the frame-face centre line
    (s ~ x on the flat panel). The arc position u = perim(z)/2 - s keeps a tall strip straight although the
    perimeter (so the u of the centre line) changes with z."""
    def surf(s_, z_):
        return S.pt(S.perim(z_) / 2 - s_, z_)

    def nrm(s_, z_):
        return S.nrm(S.perim(z_) / 2 - s_, z_)
    return G.conformal_plate(poly_sz, surf, nrm, thick=thick, lift=lift, max_edge=max_edge)


def s_at_x(S, x, z):
    return float(S.perim(z)) / 2 - u_at_x(S, x, z, "frame")


def _tab(S, x, z, w, h, thick=1.2, lift=0.5, r=6.0, half="frame", holes=()):
    from .bag_v3 import _shard
    c = s_at_x(S, x, z) if half == "frame" else u_at_x(S, x, z, half)
    poly = box(c - w / 2, z - h / 2, c + w / 2, z + h / 2)
    if r:
        poly = poly.buffer(-r).buffer(r, quad_segs=6)
    for hb in holes:
        poly = poly.difference(hb(c))
    if half == "frame":
        return frame_shard(S, poly, thick, lift=lift)
    return _shard(S, poly, thick, lift=lift, max_edge=14)


def _on_face_path(S, x0, z0, x1, z1, lift, half0="frame", half1="frame", n=60, xform=None):
    """Points on the skin from (x0, z0) to (x1, z1), straight in (u, z)."""
    u0, u1 = u_at_x(S, x0, z0, half0), u_at_x(S, x1, z1, half1)
    us, zs = np.linspace(u0, u1, n), np.linspace(z0, z1, n)
    P = S.pt(us, zs)
    N = S.nrm(us, zs)
    P = P + N * lift
    if xform is not None:
        P, N = xform(P), xform(N, direction=True)
    return P, N


def _hood_mesh(yc, zc, ybag, AS):
    """Crown hood B-19 on the bar centred (yc, zc): back ply + crown full width (x +/-width/2), J-lip and curl only
    over x +/-lip_half (relieved at the corner wraps), ears for the guys, XLPE lining B-19L under the crown."""
    H = AS.HOOD
    rb = AS.BAR_OD / 2
    t = 1.0                                                 # Hypalon ply (HOOD_FRONT_MM: one ply)
    z_cr = zc + rb + AS.HOOD_TOP_MM - t / 2                 # crown ply centre: bar + lining + ply
    zb_lo = z_cr - H["back"]
    zs = np.linspace(zb_lo, z_cr, 12)
    yb = np.minimum(yc + rb + H["depth"], ybag(zs) - 2.5) - t / 2   # back ply on (not inside) the bag face
    back = [(float(y), float(z)) for y, z in zip(yb, zs)]
    y_lip = yc - rb - AS.HOOD_FRONT_MM + t / 2
    crown = back + [(y_lip, z_cr)]
    lip = [(y_lip, z_cr), (y_lip, z_cr - H["lip"]), (y_lip + 1.5, z_cr - H["lip"] - 6), (yc - 4, z_cr - H["lip"] - H["curl"])]
    poly_c = LineString(crown).buffer(t / 2, cap_style="flat", join_style="mitre")
    poly_l = LineString(lip).buffer(t / 2, cap_style="flat", join_style="mitre")
    m = [G.plate(poly_c, [0, 0, 0], [0, 1, 0], [0, 0, 1], H["width"], tile=40.0),
         G.plate(poly_l, [0, 0, 0], [0, 1, 0], [0, 0, 1], 2 * H["lip_half"], tile=40.0)]
    ze = zb_lo + H["back"] * 0.45
    ye = float(np.interp(ze, zs, yb))
    ears = []
    for s in (-1, 1):
        ep = box(H["width"] / 2 - 4, ze - H["ear_h"] / 2, H["width"] / 2 + H["ear_w"], ze + H["ear_h"] / 2)
        ep = ep.buffer(-5).buffer(5, quad_segs=6)
        if s < 0:
            ep = Polygon([(-x, y) for x, y in ep.exterior.coords])
        m.append(G.plate(ep, [0, ye, 0], [1, 0, 0], [0, 0, 1], t, tile=40.0))
        ears.append(np.array([s * (H["width"] / 2 + H["ear_w"] / 2), ye, ze]))
    lw, ld, lt = H["lining"]
    lining = G.plate(box(-lw / 2, yc - rb, lw / 2, yc - rb + min(ld, yb[-1] - yc + rb)), [0, 0, zc + rb + lt / 2],
                     [1, 0, 0], [0, 1, 0], lt, tile=40.0)
    return G.concat(m), lining, ears, float(yb[0]), zb_lo


def bag_side(p, g, Part, block, crown_info, bx, fs, metrics) -> list:
    """Sewn and hardware parts on the bag, the crown hood + guys, under-straps and the bow riser carry."""
    AS, BA = _AS(), _BA()
    full, roll = bx["full"], bx["roll"]
    parts = []
    sw = Swing(hinge())
    STAY_X = _S().STAY_X
    z0 = float(bx["z0"])

    # ---------------------------------------------------------------- reinforcements on B-01
    w17, h17 = panel_size("B-17")
    w18, h18 = panel_size("B-18")
    w23, h23 = panel_size("B-23")
    Z17, Z23 = 450.0, 260.0              # bag_attachment.md section 5: B-17 / T3 box z 450, B-23 / T2 box z 260
    tabs_out, tabs_in = [], []
    for s in (-1, 1):
        x = s * STAY_X
        tabs_out.append(_tab(full, x, Z17, w17, h17))
        tabs_in.append(_tab(full, x, z0 + h18 / 2, w18, h18, lift=-2.2))   # INSIDE B-01, lower edge in the seam
        tabs_in.append(_tab(full, x, Z23, w23, h23, lift=-2.2))            # INSIDE B-01 under the T2 box
    parts.append(Part("tab_b17", G.concat(tabs_out), "hypalon", "bag", modes=BAGM, explode=BE, swing=True,
                      label=f"B-17 IM3 bag-hook tabs (Hypalon {w17:.0f} x {h17:.0f}, outside B-01)"))
    parts.append(Part("doublers_b18_b23", G.concat(tabs_in), "hypalon", "bag", modes=BAGM, explode=(0, 120, 0), swing=True,
                      label=f"B-18 hinge-eye doublers {w18:.0f} x {h18:.0f} + B-23 IM2 backings {w23:.0f} x {h23:.0f} "
                            "(INSIDE B-01; pulled out in the exploded view)"))

    # ---------------------------------------------------------------- hinge eyes HE, tongues T2/T3, bag hooks
    he, tg, hk = [], [], []
    for s in (-1, 1):
        x = s * STAY_X
        pin = fs["pin_at"][f"hinge_{'R' if s > 0 else 'L'}"]
        tgt, _ = face_pt(full, x, pin[2] - 16, lift=1.6)
        d = (tgt - pin) / np.linalg.norm(tgt - pin)
        end = pin + d * 16.0
        he.append(_eye_loop(pin, end, 18.0))                   # necked to the 18 mm throat (HE fold)
        zz = np.linspace(end[2], z0 + 8, 10)
        P = np.array([face_pt(full, x, z_, lift=1.6)[0] for z_ in zz])
        N = np.array([face_pt(full, x, z_)[1] for z_ in zz])
        he.append(G.ribbon(np.vstack([end, P]), 38.0, 2.0, np.vstack([N[:1], N]), step=4.0))
        for im, zbox in (("im2", Z23), ("im3", Z17)):
            hc = fs["hooks_at"][f"{im}_{'R' if s > 0 else 'L'}"]
            hk.append(_loop_rod(hc, [1, 0, 0], [0, 0, 1], 40.0, 30.0, 2.6))
            lift = 2.4 if im == "im3" else 1.6                 # T3 lies on B-17
            top = hc + np.array([0, 0, -13.0])
            zz = np.linspace(top[2] - 12, zbox, 8)
            P = np.array([face_pt(full, x, z_, lift=lift)[0] for z_ in zz])
            N = np.array([face_pt(full, x, z_)[1] for z_ in zz])
            tg.append(G.ribbon(np.vstack([top, P]), 38.0, 2.0, np.vstack([[0, -1, 0], N]), step=4.0))
    parts.append(Part("hinge_eyes", G.concat(he), "webbing", "bag", modes=BAGM, explode=BE, swing=True,
                      label="HE hinge eyes on the z 60 pins (38 mm, necked to the 18 mm throat), tails into the B-01|B-05 seam"))
    parts.append(Part("hook_tongues", G.concat(tg), "webbing", "bag", modes=BAGM, explode=BE, swing=True,
                      label="T2 (z 260, on B-23) and T3 (z 450, on B-17) bag-hook tongues, 38 mm"))
    parts.append(Part("bag_hooks", G.concat(hk), "aluminium", "bag", modes=BAGM, explode=BE, swing=True,
                      label=f"Bag hooks (4), 38 mm sliding gate, rated >= {AS.HOOK_RATED_N:.0f} N, at IM2 / IM3"))

    # ---------------------------------------------------------------- B-20 ladders (one rung per crown setting)
    L = AS.LADDER
    lw, lh = L["w"], L["h"]
    sl_w, sl_h = L["slot"]
    lad = []
    for s in (-1, 1):
        zc_ = L["z_lo"] + lh / 2
        holes = [lambda uc, k=k: box(uc - sl_w / 2, L["slot0_z"] + k * L["pitch"] - sl_h / 2,
                                     uc + sl_w / 2, L["slot0_z"] + k * L["pitch"] + sl_h / 2) for k in range(L["rungs"])]
        lad.append(_tab(full, s * L["x"], zc_, lw, lh, thick=1.2, lift=0.4, r=4.0, holes=holes))
    parts.append(Part("hood_ladders", G.concat(lad), "hypalon", "bag", modes=BAGM, explode=BE, swing=True,
                      label=f"B-20 hood ladders x {L['x']:.0f}, z {L['z_lo']:.0f}-{L['z_lo'] + lh:.0f}: "
                            f"{L['rungs']} slots, one rung per crown setting"))

    # ---------------------------------------------------------------- crown hood, tongues, guys, B-22 corner tabs
    gx, gz = AS.GUY["bag_xz"]
    w22, h22 = panel_size("B-22")
    guy_len = {}
    for var, S in (("rolled", roll), ("full", full)):
        b22 = []
        for s in (-1, 1):
            b22.append(_tab(S, s * gx, gz, w22, h22, half="outer"))
            c, n_ = face_pt(S, s * gx, gz, lift=1.7, half="outer")
            b22.append(block(c + n_ * 4.0 + [0, 0, -8], (30, 9, 14), e=0.35))        # ladder lock
            b22.append(block(c + n_ * 3.0 + [0, 0, -26], (30, 5, 9), e=0.3))         # tri-glide keeper
        parts.append(Part("guy_tabs_b22" + ("" if var == "rolled" else "_full"), G.concat(b22), "hypalon", "bag",
                          modes=BAGM, explode=BE, swing=True, variant=var,
                          label=f"B-22 guy corner tabs {w22:.0f} x {h22:.0f} + 25 mm ladder locks, x +/-{gx:.0f}, z {gz:.0f}"))

    def ybag(z):
        return np.array([face_pt(full, 0.0, float(zz_))[0][1] for zz_ in np.atleast_1d(z)])

    TG_W = 25.0                                    # poly_webbing_25mm (TG, HT)
    for tin, cs in crown_info.items():
        tag = f"@t{tin:g}"
        yc, zc = float(cs["top_bar_centre"][1]), float(cs["top_bar_centre"][2])
        k = int(cs.get("index", round((tin - 15.0) * 2)))
        hood, lining, ears, yb0, zb_lo = _hood_mesh(yc, zc, ybag, AS)
        z_slot = L["slot0_z"] + k * L["pitch"]
        ht = []
        for s in (-1, 1):                           # hood tongues: back ply x +/-60 -> woven at rung k, toggle at k+1
            P0 = np.array([s * L["x"], yb0 + 0.6, zb_lo + 12])
            P1, N1 = face_pt(full, s * L["x"], z_slot, lift=2.6)
            ht.append(G.ribbon(np.array([P0, P0 + [0, 0.5, -6], P1]), TG_W, 1.6, np.array([[0, 1, 0], [0, 1, 0], -N1]),
                               step=3.0))
            P2, N2 = face_pt(full, s * L["x"], z_slot + L["pitch"], lift=4.6)
            ht.append(block(P2, (30, 5, 8), e=0.35))
        parts.append(Part(f"crown_hood{tag}", G.concat([hood] + ht), "hypalon", "attach", torso=tin, modes=("pack",),
                          explode=(0, 130, 150),
                          label=f"B-19 crown hood on the top bar (z {zc:.0f}): {AS.HOOD['width']:.0f} mm shell, J-lip "
                                f"relieved to x +/-{AS.HOOD['lip_half']:.0f}, tongues on rung {k}"))
        parts.append(Part(f"hood_lining{tag}", lining, "xlpe", "attach", torso=tin, modes=("pack",), explode=(0, 130, 150),
                          label="B-19L XLPE lining (quiet on the bar)"))
        # between mode: the hood is lifted off the bar and lies flat on B-01 over the ladder (rides with the bag)
        flen = _AS().hood_flat()["length"]
        Wh = AS.HOOD["width"]
        hp_ = box(-Wh / 2, z_slot - 6, Wh / 2, z_slot - 6 + flen).buffer(-4).buffer(4, quad_segs=6)
        ear_z = z_slot - 6 + AS.HOOD["back"] * 0.45
        ew, eh = AS.HOOD["ear_w"], AS.HOOD["ear_h"]
        hp_ = unary_union([hp_, box(-Wh / 2 - ew, ear_z - eh / 2, -Wh / 2 + 4, ear_z + eh / 2),
                           box(Wh / 2 - 4, ear_z - eh / 2, Wh / 2 + ew, ear_z + eh / 2)])
        flat = frame_shard(full, hp_, 1.4, lift=1.8, max_edge=10)
        parts.append(Part(f"crown_hood_open{tag}", flat, "hypalon", "attach", torso=tin, modes=("pack_haul",), swing=True,
                          label="Crown hood lifted off the bar, lying flat on B-01 (between mode)"))
        ears_open = [face_pt(full, s * (Wh / 2 + AS.HOOD["ear_w"] / 2), ear_z, lift=3.0)[0] for s in (-1, 1)]
        for var, S in (("rolled", roll), ("full", full)):
            for mode, ear_pts in (("pack", ears), ("pack_haul", ears_open)):
                gm, ln = [], []
                for s, ep in zip((-1, 1), ear_pts):
                    x_e = s * (Wh / 2 + AS.HOOD["ear_w"] + 4)
                    P, N = _on_face_path(S, x_e, float(ep[2]), s * gx, gz, 2.6, "frame", "outer", n=70)
                    P = np.vstack([ep + [0, 1.5, 0], P])
                    N = np.vstack([[0, 1, 0], N])
                    gm.append(G.ribbon(P, TG_W, 1.8, N, step=5.0))
                    ln.append(float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))))
                if mode == "pack":
                    guy_len[(tin, var)] = float(np.mean(ln))
                nm = "top_guys" + ("_open" if mode == "pack_haul" else "") + ("" if var == "rolled" else "_full") + tag
                parts.append(Part(nm, G.concat(gm), "webbing", "attach", torso=tin, modes=(mode,), variant=var,
                                  swing=(mode == "pack_haul"), explode=BE,
                                  label=f"TG top side guys: hood ears -> B-22 at x +/-{gx:.0f}, z {gz:.0f} "
                                        f"(fixed length, set once; record free length {AS.GUY['free_mm']:.0f} mm)"))
    metrics["attach"] = {"hook_rated_n": float(AS.HOOK_RATED_N), "hood_width_mm": float(AS.HOOD["width"]),
                         "hood_lip_half_mm": float(AS.HOOD["lip_half"]), "ladder_rungs": int(L["rungs"]),
                         "ladder_z": [float(L["z_lo"]), float(L["z_lo"] + lh)], "guy_xz": [float(gx), float(gz)],
                         "guy_free_mm_record": float(AS.GUY["free_mm"]),
                         "guy_model_mm": {f"{t:g}_{v}": round(l_, 1) for (t, v), l_ in guy_len.items()},
                         "source": "huntkit.gendesign.attach_system + panels.yaml B-17..B-23"}

    # ---------------------------------------------------------------- bow riser carry (D-30, right side)
    # Two 25 mm loops through B-11 lash tabs + one 25 mm G-hook strap over the riser (DESIGN.md 4.11, owner freeze
    # 2026-11-05). ASSUMPTION (visual, no record places them): the two bow tabs on the right gore line at z 475 and
    # z 555, between the floating pocket (top z 450) and the rolled roll-top clip (z ~590); the strap at z 515.
    from .bag_v3 import _shard
    w11, h11 = panel_size("B-11")
    bow = []
    zl = (475.0, 555.0)
    for zt in zl:
        uc = float(full.outer_half(zt)) / 2
        bow.append(_shard(full, box(uc - w11 / 2, zt - h11 / 2, uc + w11 / 2, zt + h11 / 2), 2.2, max_edge=8))
        us = np.linspace(uc - 30, uc + 30, 25)
        bulge = 20.0 * np.sin(np.pi * (us - us[0]) / (us[-1] - us[0])) ** 0.8 + 3.0
        P = full.pt(us, np.full(25, zt)) + full.nrm(us, np.full(25, zt)) * bulge[:, None]
        N = full.nrm(us, np.full(25, zt))
        bow.append(G.ribbon(P, 25.0, 1.8, N, step=3.0))
    zs_ = 515.0
    uc = float(full.outer_half(zs_)) / 2
    us = np.linspace(uc - 75, uc + 55, 40)
    P = full.pt(us, np.full(40, zs_)) + full.nrm(us, np.full(40, zs_)) * 2.4
    N = full.nrm(us, np.full(40, zs_))
    bow.append(G.ribbon(P, 25.0, 1.8, N, step=4.0))
    bow_hw = [block(P[-1] + N[-1] * 2.5, (8, 14, 30), e=0.6)]
    parts.append(Part("bow_carry", G.concat(bow), "webbing", "bag", modes=BAGM, explode=BE, swing=True,
                      label="Bow riser carry (right side): 2 x 25 mm loops through B-11 lash tabs + G-hook strap"))
    parts.append(Part("bow_carry_hook", G.concat(bow_hw), "aluminium", "bag", modes=BAGM, explode=BE, swing=True,
                      label="Bow strap G-hook (HAUL family)"))
    return parts


# ============================================================================ under-straps, quarters, meat harness
def _strap_pack_path(full, fs, z_s, y_ch, z0, sw=None):
    """US strap with the bag on: L pin -> down the B-01 face -> under the floor to the channel -> across -> back."""
    from huntkit.gendesign import spreader as S
    pts, nrm = [], []
    for s in (-1, 1):
        x = s * S.STAY_X
        pin = fs["pin_at"][f"{'us1' if z_s < 120 else 'us2'}_{'R' if s > 0 else 'L'}"]
        leg, legn = [pin + [0, 4.0, -3.0]], [[0, -1.0, 0]]
        for zz in np.linspace(pin[2] - 12, z0 + 26, 7):
            P, N = face_pt(full, x, zz, lift=3.2)
            leg.append(P); legn.append(N)
        yf0 = float(full.yf[0])
        r_b = 25.0                                       # bag_v3 body_mesh rounded bottom edge
        for q, n_ in (([x, yf0 + r_b * (1 - np.cos(np.pi / 4)) - 2.3, z0 + r_b * (1 - np.sin(np.pi / 4)) - 2.3],
                       [0, -0.7, -0.7]),
                      ([x, yf0 + r_b, z0 - 3.2], [0, 0, -1.0]), ([x, y_ch, z0 - 3.2], [0, 0, -1.0])):
            leg.append(np.array(q, float)); legn.append(np.array(n_, float))
        if sw is not None:
            leg = [leg[0]] + [sw(q) for q in leg[1:]]
            legn = [legn[0]] + [sw(np.asarray(n_, float), direction=True) for n_ in legn[1:]]
        if s < 0:
            pts += leg; nrm += legn
        else:
            pts += leg[::-1]; nrm += legn[::-1]
    return np.array(pts), np.array(nrm, float)


def haul_parts(p, g, Part, block, crown_info, bx, fs, metrics, ribbon_on) -> list:
    """Between mode (bag swung open on the hinge pins, quarter in the wedge) and bag-off (quarter in the cradle),
    plus the under-straps in every mode."""
    from huntkit.gendesign import meat_haul as MH
    S = _S()
    full, roll = bx["full"], bx["roll"]
    h = hinge()
    sw = Swing(h)
    parts = []
    z0 = float(bx["z0"])
    c0 = full.center(z0)
    d0 = float(full.d[0])
    # ASSUMPTION (visual): floor channels, US1 rear at 0.62 of the floor depth, US2 front at 0.30
    chans = {MH.US1_Z: float(full.yf[0]) + 0.62 * d0, MH.US2_Z: float(full.yf[0]) + 0.30 * d0}

    # ---------------------------------------------------------------- under-straps: bag on / between / frame only
    for mode, xf in (("pack", None), ("pack_haul", sw)):
        straps, cams = [], []
        for z_s, y_ch in chans.items():
            P, N = _strap_pack_path(full, fs, z_s, y_ch, z0, sw=xf)
            straps.append(G.ribbon(P, 38.0, 2.0, N, step=4.0))
            cams.append(block(P[-2] + [0, 2, 0], (40, 10, 24), e=0.35))
        parts.append(Part("under_straps" + ("" if mode == "pack" else "_open"), G.concat(straps + cams), "webbing", "frame",
                          modes=(mode,), label="Under-straps US1 (z 95) / US2 (z 142), 38 mm, cammed under the bag floor "
                                               "channels (eye on the left pin, cam on the right)"))
    slack = []
    for z_s in chans:
        pr = fs["pin_at"][f"{'us1' if z_s < 120 else 'us2'}_R"]
        # ASSUMPTION (visual): hanging slack, the belly a little aft of the pins, strap face up and aft
        P = np.array([[-pr[0], pr[1] + 2, z_s - 4], [-pr[0] + 30, pr[1] + 6, z_s - MH.BELLY_MM * 0.75],
                      [0, pr[1] + 8, z_s - MH.BELLY_MM], [pr[0] - 30, pr[1] + 6, z_s - MH.BELLY_MM * 0.75],
                      [pr[0], pr[1] + 2, z_s - 4]])
        Ns = np.array([[0, 1, 0], [0, 0.7, 0.7], [0, 0, 1], [0, 0.7, 0.7], [0, 1, 0]], float)
        slack.append(ribbon_on(P, Ns, 38.0, 2.0))
    parts.append(Part("under_straps_slack", G.concat(slack), "webbing", "frame", modes=("frame",),
                      label=f"Under-straps hanging as the cradle (belly {MH.BELLY_MM:.0f} mm)"))

    # ---------------------------------------------------------------- quarters
    q = p["quarter"]
    W, D, Hq = q["width"], q["depth"], q["height"]

    def y_front(z):                                   # game bag on the spreader (bag face + 1), the line above it
        return board_bag_y(z) + 1.0

    def quarter(zq0, thick_high, wedge=None):
        rings, info = [], []
        for f in np.linspace(0, 1, 40):
            z = zq0 + Hq * f
            ff = (1 - f) if thick_high else f
            taper = 1 - 0.45 * ff ** 1.3
            bul = 1 + 0.10 * np.sin(np.pi * min(ff * 1.6, 1))
            rr = np.sqrt(max(1 - ((f - 0.5) / 0.5) ** 10, 0.05))
            a = max(W / 2 * taper * bul * rr, 18)
            b = max(D / 2 * (1 - 0.25 * ff) * bul * rr, 14)
            if wedge is not None:
                b = max(min(b, (wedge(z) - 8.0) / 2), 12)
            cy = float(y_front(z)) + b
            rings.append(G.superellipse_ring(a, b, 2.3, 3.4, M=64, cy=cy, z=z))
            info.append((z, a, b, cy))
        info = np.array(info)
        top = info[-1]
        bc = np.array([14, float(y_front(top[0])) + 26, top[0] - 30])
        bone = G.concat([G.capsule_between(bc, bc + [4, 4, 110], 20, 17),
                         G.superellipsoid(bc + [4, 4, 124], (28, 24, 22), 0.8, 0.8)])
        return G.loft(np.array(rings), cap_start=True, cap_end=True), bone, info

    # B-01 swung open: its frame-face line, rotated; the wedge is what is left between it and the spreader line
    zz = np.linspace(z0, 1000, 300)
    b01 = np.c_[np.zeros_like(zz), np.interp(zz, full.z, full.yf), zz]
    b01r = sw(b01)

    def wedge(z):
        return float(np.interp(z, b01r[:, 2], b01r[:, 1])) - float(y_front(z))
    ZQ_BETWEEN = 150.0     # ASSUMPTION (visual): hock just under the IM1 strap (bag_attachment.md 7: 'hock at IM1')
    qb, bb, qi_b = quarter(ZQ_BETWEEN, True, wedge)
    zq_off = MH.US1_Z - MH.BELLY_MM + 4.0              # bag off: the quarter sits in the US1 belly
    qo, bo, qi_o = quarter(zq_off, False)
    QE = (0.0, 120.0, 0.0)
    parts.append(Part("quarter_between", qb, "game_bag", "haul", modes=("pack_haul",),
                      label="Bone-in elk hindquarter in a game bag, thick end high in the wedge (between mode)"))
    parts.append(Part("quarter_bone_between", bb, "bone", "haul", modes=("pack_haul",)))
    parts.append(Part("quarter_proxy", qo, "game_bag", "haul", modes=("frame_haul",), explode=QE,
                      label="Bone-in elk hindquarter in a game bag, in the under-strap cradle (bag off)"))
    parts.append(Part("quarter_bone", bo, "bone", "haul", modes=("frame_haul",), explode=QE))

    def q_half_of(info):
        def f(z):
            return float(np.interp(z, info[:, 0], info[:, 1])) if info[0, 0] <= z <= info[-1, 0] else 0.0
        return f

    # ---------------------------------------------------------------- IM1-IM3 meat harness, eye to eye over the meat
    mh = g.get("meat_harness") or {}
    for mode, info, name in (("pack_haul", qi_b, "between"), ("frame_haul", qi_o, "bagoff")):
        ims, imh = [], []
        for st_ in mh.get("straps", []):
            zs_ = float(st_["z"])
            key = {190.0: "im1", 330.0: "im2", 520.0: "im3"}[zs_]
            eR, eL = fs["eye_ends"][f"{key}_R"], fs["eye_ends"][f"{key}_L"]
            zm = float(np.clip(zs_, info[0, 0] + 5, info[-1, 0] - 5))
            a_, b_, c_ = (float(np.interp(zm, info[:, 0], info[:, k])) for k in (1, 2, 3))
            th_ = np.linspace(0.0, np.pi, 50)
            cth, sth = np.cos(th_), np.sin(th_)
            qp = np.column_stack([(a_ + 3.5) * np.sign(cth) * np.abs(cth) ** (2 / 2.3),
                                  c_ + (b_ + 3.5) * np.abs(sth) ** (2 / 2.3), np.full(50, zs_ - 6)])
            qp = qp[qp[:, 1] > eR[1] + 8]
            Pq = np.vstack([[eR + [0, 4, -4]], qp, [eL + [0, 4, -4]]])
            nq = Pq - np.column_stack([np.zeros(len(Pq)), np.full(len(Pq), c_), Pq[:, 2]])
            ims.append(ribbon_on(Pq, nq, 38.0, 2.6, smooth=False))
            for e_ in (eR, eL):                                           # sliding-gate meat hooks on the eyes
                imh.append(_loop_rod(e_ + [0, 6, -6], [1, 0, 0], [0, 0.6, -0.8], 40.0, 26.0, 2.4))
            kq = int(len(qp) * 0.25)                                      # cam on the wearer's-right leg
            imh.append(block(qp[kq] + (qp[kq] - [0, c_, qp[kq][2]]) / max(np.linalg.norm(qp[kq][:2] - [0, c_]), 1) * 6,
                             (12, 18, 46), e=0.35))
        parts.append(Part(f"meat_straps_{name}" if name != "bagoff" else "meat_straps", G.concat(ims), "meat_strap", "haul",
                          modes=(mode,), label="Meat harness IM1-IM3 (38 mm, MEAT family): eye to eye over the quarter, cammed"))
        parts.append(Part(f"meat_hardware_{name}" if name != "bagoff" else "meat_hardware", G.concat(imh), "aluminium",
                          "haul", modes=(mode,), label="MEAT sliding-gate hooks + cams"))

    # bag off: the two under-straps are the cradle round the quarter's low end
    cr = []
    for z_s in chans:
        pr, pl = fs["pin_at"][f"{'us1' if z_s < 120 else 'us2'}_R"], fs["pin_at"][f"{'us1' if z_s < 120 else 'us2'}_L"]
        th_ = np.linspace(0.0, np.pi, 41)
        pts = []
        for t_ in th_:
            zb = z_s - MH.BELLY_MM * np.sin(t_)
            zq = float(np.clip(zb, qi_o[0, 0] + 6, qi_o[-1, 0]))
            a_, b_, c_ = (float(np.interp(zq, qi_o[:, 0], qi_o[:, k])) for k in (1, 2, 3))
            pts.append([(a_ + 4) * np.cos(t_), c_ + (b_ + 4) * np.sin(t_) ** 0.8, min(zb, zq) - (3 if zb < zq else 0)])
        pts = np.array(pts)
        pts = pts[pts[:, 1] > pr[1] + 6]
        P = np.vstack([[pr + [0, 3, -3]], pts, [pl + [0, 3, -3]]])
        cen = np.column_stack([np.zeros(len(P)), np.interp(P[:, 2], qi_o[:, 0], qi_o[:, 3]), P[:, 2] + 30])
        cr.append(ribbon_on(P, P - cen, 38.0, 2.4, smooth=False))
    parts.append(Part("cradle_straps", G.concat(cr), "webbing", "frame", modes=("frame_haul",),
                      label=f"Under-straps as the cradle: belly {MH.BELLY_MM:.0f} mm under the quarter"))

    # ---------------------------------------------------------------- haul wraps W1-W3 round the open bag and the meat
    wp, anchor_of = bx["wrap_path"], bx["anchor_of"]
    q_half_b = q_half_of(qi_b)
    wr = []
    for w in bx["fixed_wraps"]:
        (ayR, zR), (ayL, zL) = anchor_of(w, "R"), anchor_of(w, "L")
        P, Nn = wp(roll, zR, zL, ayR, ayL, meat=True, xform=sw, q_half=q_half_b)
        wr.append(G.ribbon(P, 25.0, 2.4, Nn, step=8))
    parts.append(Part("haul_wraps_meat", G.concat(wr), "webbing", "haul", modes=("pack_haul",),
                      label="W1/W2 close round the swung bag and the meat (frame anchors)"))
    for tin, cs in crown_info.items():
        for w in bx["crown_wraps"]:
            z = float(cs["crown_top_z"])
            ay = float(cs["lifter_anchor_R"][1])
            for var, Sx in (("rolled", roll), ("full", full)):
                P, Nn = wp(Sx, z, z, ay, ay, meat=True, xform=sw, q_half=q_half_b)
                parts.append(Part(f"crown_wrap_meat{'' if var == 'rolled' else '_full'}@t{tin:g}",
                                  G.concat([G.ribbon(P, 25.0, 2.4, Nn, step=8)] + bx["wrap_hooks"](z, z, ay, ay)),
                                  "webbing", "haul", torso=tin, modes=("pack_haul",), variant=var,
                                  label="W3 from the crown top bar round the swung bag"))
    metrics["hinge"] = {k: v for k, v in h.items()}
    metrics["between_wedge_mm"] = {str(int(z)): round(wedge(z), 1) for z in (190.0, 330.0, 520.0)}
    return parts
