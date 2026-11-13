"""Pack 5200: alternative MAIN-BAG BODY concepts, measured against the released v3.1 "SPINE".

Owner: pack-designer. Study only: nothing here changes the released SPINE geometry, patterns or YAML
(`geometry.yaml`, `panels.yaml`, `patterns_v31.py` are only READ). Write-up:
`designs/pack_5200/analysis/bag_alternatives.md`; research: `docs/research/bag_body_architectures.md`.

Concepts (all keep the frame interface: B-01 frame-side panel with the hinge eyes / B-18, IM1-IM3 ports, B-17 / B-23
hook tabs, B-20 hood ladders, B-22 guy tabs, under-strap channels; same 30 mm head setback at z 560 -> 631.2):

* ``slab``  "SLAB"  beginner build: tapered flat-panel box, roll-top, ONE straight centre front zip. 0 curved seams.
* ``twin``  "TWIN"  SLAB body, the zips moved INTO the two front corner seams (one each side), the front face stays
                    one piece and carries a flat stretch overload pocket (bow cam cup, poles).
* ``wrap``  "WRAP"  SPINE-lite: one developed wrap panel (front + both sides) on a flat frame panel, D section,
                    keeps the diagonal zip + stretch band. 1 curved seam (the bottom).
* ``hatch`` "HATCH" panel loader: SLAB body with a horseshoe (U) zip door in the front face under the roll-top.

Every number traces to geometry.yaml / panels.yaml / a material record in data/materials, a calculation below,
or a line marked ``ASSUMPTION``. Units mm, g, L.

Volume rule (same as R-01): main bag to the roll-top fill line, 3 rolls closed (150 mm of collar = closure),
collar / pockets / lid / band pocket NOT counted. Below the collar seam the sewn body is exact; above it the stuffed
collar forms a dome to the fill line by the SPINE dome law (``dome_section``), calibrated on SPINE itself
(``spine_dome_check``).
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "designs" / "pack_5200"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import build_geometry as BG  # noqa: E402  (stay line, frame gap, head setback, D_TOP)
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import Piece, Seam, check_seams, develop_region  # noqa: E402

GEOM = yaml.safe_load((HERE / "geometry.yaml").read_text())
_PROF = GEOM["bag"]["profile"]
SPINE_ST = np.asarray(_PROF["stations"], float)          # [z, half_width, y_frame, depth] (85.2 L full state)
N_OUT, N_FRM = float(_PROF["n_out"]), float(_PROF["n_frm"])  # 2.5 / 5.0

# ------------------------------------------------------------------ shared frame interface + envelope
Z0 = float(SPINE_ST[0, 0])                                  # 35: bag bottom (hinge eyes at z 60 above it)
Z_SB = float(BG.HEAD_SB_Z[0])                               # 560: SETBACK crease / seam
Z_SH = float(GEOM["bag"]["diagonal"]["zip_end_left"][2])    # 631.2: SHOULDER crease / seam (= SPINE zip end)
SETBACK = float(BG.HEAD_SETBACK)                            # 30 mm (D-21, head clearance R-28)
FRAME_GAP = float(BG.FRAME_GAP)                             # 20 mm aft of the stay centre line
Z_COLLAR_SPINE = float(_PROF["z_collar_seam"])              # 781.2
Z_FILL_SPINE = float(_PROF["z_fill_line"])                  # 1101
DOME_H = Z_FILL_SPINE - Z_COLLAR_SPINE                      # 319.8: stuffed collar to the fill line (SPINE)
D_TOP = float(BG.D_TOP)                                     # 62: closed roll thickness at the fill line
A_BOT, D_BOT = float(SPINE_ST[0, 1]), float(SPINE_ST[0, 3])  # 136.18 / 190: SPINE bottom (10.7 x 7.5 in)
A_MAX = float(SPINE_ST[:, 1].max())                          # 197: 15.5 in at the shoulder blades (owner freeze)
D_MAX = float(BG.D_PEAK)                                     # 302 nominal (11.9 in)
TARGET_L = float(BG.TARGET_L)                                # 85.2 L = 5200 cu in
COLLAR_H = float(GEOM["bag"]["rolltop"]["collar"]["fabric_height_mm"])   # 494.8 (B-06 fabric height)
HEM_H = 70.0          # B-07 hem strip height (panels.yaml B-07: 1170 x 70 area 81.9e3 mm2 cut) -> same rule
HDPE_T, HDPE_W = 0.8, 20.0   # roll-top stiffener 0.8 x 20 mm (geometry.yaml weight row 'roll-top')
SA_BODY, SA_ZIP, SA_FLAT = 12.0, 10.0, 8.0   # patterns_v31: bound body seams 12, zip 10, flat-work turn 8
IN, L_CUIN = 25.4, 16.387064
PACK_TOTAL_G = float(GEOM["weight"]["total_g"])             # 3495.6 g production pack (geometry.yaml)

# frame-interface stations (attachment.yaml / bag_attachment.md), drawn on every concept's B-01
STATIONS = {"hinge": 60.0, "im1": 190.0, "im2": 330.0, "im3": 520.0}
STAY_X = 115.0


def stay_y(z):
    return np.asarray([BG.y_on_axis(float(zz)) for zz in np.atleast_1d(z)])


def setback(z):
    """30 mm head setback taken as two straight creases (z 560 / 631.2), linear between: on a flat panel a Z-fold."""
    z = np.atleast_1d(np.asarray(z, float))
    return SETBACK * np.clip((z - Z_SB) / (Z_SH - Z_SB), 0, 1)


def y_frame(z):
    return stay_y(z) + FRAME_GAP + setback(z)


def _F(n):
    return math.gamma(1 + 1 / n) ** 2 / math.gamma(1 + 2 / n)


K_SPINE = 0.5 * (_F(N_OUT) + _F(N_FRM))    # SPINE ring area / bounding box (2a x d) = 0.898


# ============================================================================ sections
def section_ring(a, d, yf, kind, n=None, M=240):
    """Closed ring polygon (M x 2, x/y) in the order frame face (-x -> +x), then outer part (+x side, back over the
    aft face, to -x). Returns (pts, n_frame) where pts[:n_frame] is the frame face.
    kind 'spine': SPINE mixed superellipse (centre yf + d/2); 'box': rectangle; 'd': flat frame face + half
    superellipse of exponent n (semi-axes a, d) aft of it."""
    if kind == "spine":
        # theta pi -> 2 pi is the frame half (-x -> +x along the frame face), 2 pi -> 3 pi the aft half (+x -> -x)
        th = np.linspace(np.pi, 3 * np.pi, 4 * M, endpoint=False)
        c, s = np.cos(th), np.sin(th)
        nn = np.where(s >= 0, N_OUT, N_FRM)
        x = a * np.sign(c) * np.abs(c) ** (2 / nn)
        y = yf + d / 2 + d / 2 * np.sign(s) * np.abs(s) ** (2 / nn)
        return _resample(np.column_stack([x, y]), M), M // 4
    nf = M // 4
    xf = np.linspace(-a, a, nf, endpoint=False)
    frame = np.column_stack([xf, np.full(nf, yf)])
    if kind == "box":
        per = 2 * d + 2 * a
        m = M - nf
        s = np.linspace(0, per, m, endpoint=False)
        pts = []
        for si in s:
            if si < d:
                pts.append((a, yf + si))
            elif si < d + 2 * a:
                pts.append((a - (si - d), yf + d))
            else:
                pts.append((-a, yf + d - (si - d - 2 * a)))
        return np.vstack([frame, np.array(pts)]), nf
    th = np.linspace(0, np.pi, 2000)
    c, s = np.cos(th), np.sin(th)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = yf + d * np.abs(s) ** (2 / n)
    outer = _resample_open(np.column_stack([x, y]), M - nf)
    return np.vstack([frame, outer[:-1] if len(outer) > M - nf else outer]), nf


def _resample_open(P, m):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, s[-1], m)
    return np.column_stack([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])])


def _resample(P, m):
    Pc = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(Pc, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, s[-1], m, endpoint=False)
    return np.column_stack([np.interp(t, s, Pc[:, 0]), np.interp(t, s, Pc[:, 1])])


def poly_area_centroid(P):
    x, y = P[:, 0], P[:, 1]
    xr, yr = np.roll(x, -1), np.roll(y, -1)
    cr = x * yr - xr * y
    A = 0.5 * cr.sum()
    return abs(A), ((y + yr) * cr).sum() / (6 * A)


def section_area(a, d, kind, n=None):
    """Exact area of a section (mm2)."""
    if kind == "spine":
        return a * d * (_F(N_OUT) + _F(N_FRM))
    if kind == "box":
        return 2 * a * d
    return 2 * a * d * _F(n)


def section_k(kind, n=None):
    return section_area(1.0, 1.0, kind, n) / 2.0


# ============================================================================ dome (stuffed collar) law
RW_SPINE = float(SPINE_ST[-1, 1] / np.interp(Z_COLLAR_SPINE, SPINE_ST[:, 0], SPINE_ST[:, 1]))  # a_fill / a_collar


def dome_section(u, a_c, d_c, k_c):
    """Section at fraction u (0 at the collar seam, 1 at the fill line) of the stuffed collar.
    ASSUMPTION (SPINE dome law, build_geometry.depth above T_PEAK): depth = D_TOP + (d_c - D_TOP) sqrt(1 - u^2);
    half-width = a_c (1 - (1 - RW) u^2) with RW = SPINE a_fill / a_collar (0.816); the shape factor blends linearly
    from the body section k_c to the SPINE section k at the roll (every collar pinches to the same flat roll)."""
    u = np.clip(u, 0, 1)
    d = D_TOP + (d_c - D_TOP) * np.sqrt(np.clip(1 - u ** 2, 0, None))
    a = a_c * (1 - (1 - RW_SPINE) * u ** 2)
    k = k_c + (K_SPINE - k_c) * u
    return a, d, k


def spine_dome_check(cal: float | None = None) -> dict:
    """Calibrate the dome law on SPINE: true SPINE volume above the collar seam vs the law applied to SPINE's own
    collar-seam section. The raw law over-predicts SPINE by ~1.1 L (4.4 % of the dome, 1.3 % of the bag); DOME_CAL
    scales every concept's dome area so the law reproduces SPINE exactly. The raw error is the stated uncertainty."""
    z = SPINE_ST[:, 0]
    A = SPINE_ST[:, 1] * SPINE_ST[:, 3] * (_F(N_OUT) + _F(N_FRM))
    zz = np.linspace(Z_COLLAR_SPINE, Z_FILL_SPINE, 400)
    true = float(np.trapezoid(np.interp(zz, z, A), zz)) / 1e6
    a_c = float(np.interp(Z_COLLAR_SPINE, z, SPINE_ST[:, 1]))
    d_c = float(np.interp(Z_COLLAR_SPINE, z, SPINE_ST[:, 3]))
    u = (zz - Z_COLLAR_SPINE) / DOME_H
    a, d, k = dome_section(u, a_c, d_c, K_SPINE)
    model = float(np.trapezoid(2 * a * d * k, zz)) / 1e6 * (1.0 if cal is None else cal)
    return {"true_L": true, "model_L": model, "err_L": model - true, "err_pct_of_bag": 100 * (model - true) / TARGET_L}


_raw = spine_dome_check()
DOME_CAL = _raw["true_L"] / _raw["model_L"]     # 0.957: calibration of the dome law on SPINE (see above)


# ============================================================================ concepts
@dataclass
class Concept:
    key: str
    name: str
    tagline: str
    kind: str                    # 'box' | 'd' | 'spine'
    n: float | None = None       # outer exponent for kind 'd'
    access: str = ""
    zips: list = field(default_factory=list)      # dicts: name, z_lo, z_hi, length_mm, corners, where
    notes: list = field(default_factory=list)
    z_c: float = 0.0             # collar seam (solved)
    # envelope (defaults = the first four concepts; the wider set overrides them, bag_concepts_wide.py)
    a_bot: float = A_BOT         # half-width at the bottom (SPINE 136)
    d_bot: float = D_BOT         # depth at the bottom (SPINE 190)
    d_nom: float = D_MAX         # nominal depth at the shoulder crease, from the face without setback (302)
    dome_h: float = DOME_H       # stuffed collar to the fill line; 0 = closed (zip) top, no roll-top

    # ---------------------------------------------------------------- body envelope (below the collar seam)
    def a(self, z):
        """Half-width: SPINE bottom (136) linearly to 15.5 in (197) at the shoulder crease, then constant."""
        z = np.atleast_1d(np.asarray(z, float))
        return np.interp(z, [Z0, Z_SH], [self.a_bot, A_MAX])

    def y_front(self, z):
        """Aft face: one plane from the SPINE bottom depth (190) to the 302 mm nominal depth at the shoulder crease
        measured from the face WITHOUT the setback, then parallel to the frame face. So the aft face has no setback jog
        (one crease only) and the depth above the setback is 302 - 30 = 272 mm (10.7 in). DECISION (concepts):
        a jog in the aft face would add 2 creases to the face / wrap for no volume."""
        z = np.atleast_1d(np.asarray(z, float))
        y_nom = stay_y(z) + FRAME_GAP
        y0 = float(stay_y([Z0])[0]) + FRAME_GAP + self.d_bot
        y1 = float(stay_y([Z_SH])[0]) + FRAME_GAP + self.d_nom
        low = y0 + (y1 - y0) * (z - Z0) / (Z_SH - Z0)
        high = y_nom + self.d_nom
        return np.where(z <= Z_SH, low, high)

    def depth(self, z):
        return self.y_front(z) - y_frame(z)

    @property
    def k(self):
        return section_k(self.kind, self.n)

    # ---------------------------------------------------------------- full state (with the dome)
    def profile(self, z_c=None, n_body=240, n_dome=80):
        """Stations [z, a, y_frame, d, k] from the bottom to the fill line."""
        z_c = self.z_c if z_c is None else z_c
        zb = np.unique(np.r_[np.linspace(Z0, z_c, n_body), Z_SB, Z_SH])
        zb = zb[zb <= z_c]
        rows = [np.column_stack([zb, self.a(zb), y_frame(zb), self.depth(zb), np.full(len(zb), self.k)])]
        if self.dome_h <= 0:
            return rows[0]
        a_c, d_c = float(self.a([z_c])[0]), float(self.depth([z_c])[0])
        zd = np.linspace(z_c, z_c + self.dome_h, n_dome)[1:]
        a, d, k = dome_section((zd - z_c) / self.dome_h, a_c, d_c, self.k)
        rows.append(np.column_stack([zd, a, y_frame(zd), d, k * DOME_CAL]))
        return np.vstack(rows)

    def volume_L(self, z_c=None, upto=None):
        st = self.profile(z_c)
        if upto is not None:
            st = st[st[:, 0] <= upto]
        A = 2 * st[:, 1] * st[:, 3] * st[:, 4]
        return float(np.trapezoid(A, st[:, 0])) / 1e6

    def solve(self):
        """Collar-seam height such that the main bag holds exactly TARGET_L (bisection)."""
        lo, hi = Z_SH + 1.0, 1600.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if self.volume_L(mid) < TARGET_L else (lo, mid)
        self.z_c = round(0.5 * (lo + hi), 1)
        return self.z_c

    @property
    def z_fill(self):
        return self.z_c + self.dome_h

    def ring(self, z, M=240, state=None):
        """3D ring at z (full state). Dome rings keep the concept's section shape (render only)."""
        st = self.profile()
        a = float(np.interp(z, st[:, 0], st[:, 1]))
        yf = float(np.interp(z, st[:, 0], st[:, 2]))
        d = float(np.interp(z, st[:, 0], st[:, 3]))
        P, nf = section_ring(a, d, yf, self.kind, self.n, M)
        return np.column_stack([P, np.full(len(P), z)]), nf

    def cg(self, n=161, M=360):
        """Uniform-fill centroid (FCS y, z), as build_geometry.bag_cg (SPINE: y 148.2, z 592.5)."""
        st = self.profile()
        zs = np.linspace(st[0, 0], st[-1, 0], n)
        V = Sy = Sz = 0.0
        for z in zs:
            a = float(np.interp(z, st[:, 0], st[:, 1]))
            yf = float(np.interp(z, st[:, 0], st[:, 2]))
            d = float(np.interp(z, st[:, 0], st[:, 3]))
            kk = float(np.interp(z, st[:, 0], st[:, 4]))
            P, _ = section_ring(a, d, yf, self.kind, self.n, M)
            A, cy = poly_area_centroid(P)
            A *= kk / self.k        # dome blend
            V += A
            Sy += A * cy
            Sz += A * z
        return Sy / V, Sz / V


def spine_volume_check() -> dict:
    """The integrator on SPINE's own stations (geometry.yaml): must reproduce 85.14 L and CG y 148.2 / z 592.5."""
    z = SPINE_ST[:, 0]
    A = SPINE_ST[:, 1] * SPINE_ST[:, 3] * (_F(N_OUT) + _F(N_FRM))
    V = float(np.trapezoid(A, z)) / 1e6
    zs = np.linspace(z[0], z[-1], 161)
    Vs = Sy = Sz = 0.0
    for zz in zs:
        a, yf, d = (float(np.interp(zz, z, SPINE_ST[:, j])) for j in (1, 2, 3))
        P, _ = section_ring(a, d, yf, "spine", M=360)
        Ai, cy = poly_area_centroid(P)
        Vs += Ai
        Sy += Ai * cy
        Sz += Ai * zz
    return {"volume_L": V, "cg_y": Sy / Vs, "cg_z": Sz / Vs, "fill_mm": float(z[-1] - z[0]),
            "max_depth": float(SPINE_ST[:, 3].max()), "width_max": 2 * A_MAX}


CONCEPTS = {
    "slab": dict(name="SLAB", kind="box",
                 tagline="Beginner build: tapered flat-panel box, roll-top, one straight centre zip",
                 access="roll-top + straight #10 centre front zip, z 140-660 (2 sliders)"),
    "twin": dict(name="TWIN", kind="box",
                 tagline="SLAB body, a straight zip in each front corner seam + flat stretch overload pocket",
                 access="roll-top + two straight #10 zips in the front corner seams, z 120-700"),
    "wrap": dict(name="WRAP", kind="d", n=4.0,   # n 4: 42.4 in fill (n 3: 43.9 in), wrap strain p99 <= 0.9 %
                 tagline="SPINE-lite: one wrap panel round a flat frame panel, diagonal zip + band kept",
                 access="roll-top + diagonal #10 zip (as SPINE), straight on the flat pattern"),
    "hatch": dict(name="HATCH", kind="box",
                  tagline="Panel loader: SLAB body with a horseshoe-zip door under the roll-top",
                  access="roll-top + horseshoe #10 zip door, z 100-720, R 60 corners"),
}


def make(key: str) -> Concept:
    c = Concept(key=key, **CONCEPTS[key])
    c.solve()
    return c


# ============================================================================ flat patterns
def unroll(zs, ys):
    """Arc length of the polyline (y(z), z): exact unfold of a creased planar-facet face."""
    seg = np.hypot(np.diff(ys), np.diff(zs))
    return np.r_[0, np.cumsum(seg)]


def unroll_xz(zs, xs):
    seg = np.hypot(np.diff(xs), np.diff(zs))
    return np.r_[0, np.cumsum(seg)]


def _kinks(c: Concept):
    return np.array(sorted({Z0, Z_SB, Z_SH, c.z_c}))


def frame_panel(c: Concept, name="frame-side panel (flat, Z-fold setback)", pid="B-01"):
    """B-01: one flat piece. Facets are planar (straight stays) and contain the x direction, so the unfold is exact:
    flat (x, s) with s = arc length of the frame-face profile y_frame(z)."""
    zk = _kinks(c)
    s = unroll(zk, y_frame(zk))
    a = c.a(zk)
    right = [(float(a[i]), float(s[i])) for i in range(len(zk))]
    left = [(-float(a[i]), float(s[i])) for i in range(len(zk))][::-1]
    edges = [("bottom", [(-a[0], 0.0), (a[0], 0.0)]), ("right", right), ("top", [right[-1], left[0]]), ("left", left)]
    p = Piece.from_edges(name, edges, seam_allowance_mm=SA_BODY, material_id="challenge_ultra_200", piece_id=pid)
    p.creases = [float(v) for v in s[1:-1]]
    return p


def front_face_profile(c: Concept):
    zk = np.array(sorted({Z0, Z_SH, c.z_c}))
    s = unroll(zk, c.y_front(zk))
    return zk, s, c.a(zk)


def front_face(c: Concept, split_x=None, name="aft face", pid="B-02", mat="cordura_330d_nylon66"):
    zk, s, a = front_face_profile(c)
    right = [(float(a[i]), float(s[i])) for i in range(len(zk))]
    left = [(-float(a[i]), float(s[i])) for i in range(len(zk))][::-1]
    if split_x is None:
        edges = [("bottom", [(-a[0], 0.0), (a[0], 0.0)]), ("right", right), ("top", [right[-1], left[0]]),
                 ("left", left)]
        return [Piece.from_edges(name, edges, seam_allowance_mm=SA_BODY, material_id=mat, piece_id=pid)]
    out = []
    for side, sgn in (("R", 1), ("L", -1)):
        outer = right if sgn > 0 else left[::-1]
        cen = [(0.0, 0.0), (0.0, float(s[-1]))]
        if sgn > 0:
            edges = [("bottom", [(0.0, 0.0), (a[0], 0.0)]), ("outer", outer), ("top", [outer[-1], (0.0, s[-1])]),
                     ("centre", cen[::-1])]
        else:
            edges = [("bottom", [(-a[0], 0.0), (0.0, 0.0)]), ("centre", cen), ("top", [(0.0, s[-1]), outer[-1]]),
                     ("outer", outer[::-1])]
        sa = {"default": SA_BODY, "centre": SA_ZIP}
        out.append(Piece.from_edges(f"{name} {side}", edges, seam_allowance_mm=sa, material_id=mat,
                                    piece_id=f"{pid}{side.lower()}"))
    return out


def gusset(c: Concept, name="side gusset", pid="B-03"):
    """Side gusset (box concepts): facets contain the y direction; flat coords (y - y_ref, sigma) with sigma the arc
    length of (a(z), z). Frame edge = y_frame (2 creases), aft edge = y_front (1 crease). Cut 2 (mirror)."""
    zk = _kinks(c)
    sig = unroll_xz(zk, c.a(zk))
    yr = float(y_frame([Z0])[0])
    fr = [(float(y_frame([z])[0] - yr), float(sg)) for z, sg in zip(zk, sig)]
    af = [(float(c.y_front([z])[0] - yr), float(sg)) for z, sg in zip(zk, sig)]
    edges = [("bottom", [fr[0], af[0]]), ("aft", af), ("top", [af[-1], fr[-1]]), ("frame", fr[::-1])]
    return Piece.from_edges(name, edges, seam_allowance_mm=SA_BODY, material_id="cordura_330d_nylon66",
                            quantity=2, mirror=True, piece_id=pid)


def box_bottom(c: Concept):
    w, d = 2 * A_BOT, float(c.depth([Z0])[0])
    from huntkit.patterns import rect_panel
    return rect_panel("bottom", w, d, 0.0, seam_allowance_mm=SA_BODY, material_id="cordura_500d_nylon66",
                      piece_id="B-05")


def ring_perimeter(c: Concept, z):
    P, _ = c.ring(z, M=720)
    return float(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1).sum())


COLLAR_TOP = float(GEOM["bag"]["rolltop"]["collar"]["perimeter_mm"])   # 1171.6: SPINE collar (roll width)


def collar_set(c: Concept):
    """Roll-top collar: a straight-seam tapered tube. Bottom = the body ring at the collar seam; top (hem) = the SPINE
    collar perimeter 1171.6 mm, so every concept rolls to the same roll width (a box ring is ~14 % longer than the
    SPINE ring; rolled flat its collar would stick out ~80 mm further each side). DECISION (concepts)."""
    from huntkit.patterns import tapered_panel, rect_panel
    per = ring_perimeter(c, c.z_c)
    top = min(per, COLLAR_TOP)
    col = tapered_panel("roll-top collar", per, top, COLLAR_H, seam_allowance_mm=SA_BODY,
                        material_id="robic_100d_ripstop", piece_id="B-06")
    hem = rect_panel("roll-top hem", top, HEM_H, 0.0, seam_allowance_mm=SA_BODY,
                     material_id="cordura_330d_nylon66", piece_id="B-07")
    hd = rect_panel("roll-top HDPE strip", 0.5 * top - 40, HDPE_W, 0.0, seam_allowance_mm=0.0,
                    material_id="hdpe_sheet", quantity=2, piece_id="B-07s")
    hd.thickness_mm = HDPE_T
    return col, hem, hd, per


LADDER_TOP = 795.0   # B-20 hood ladders run z 545-795 on the frame side (bag_attachment.md section 10)


def frame_collar(c: Concept, col, per):
    """When the collar seam is below the top of the B-20 hood ladders (box concepts: z 736 < 795) the frame-side
    quarter of the collar is cut in ULTRA 200 (B-06f, same as B-01) so the top rungs sit on laminate, not on 100D.
    Splits the tapered collar into B-06f (frame width) + B-06 (rest); the two side seams replace the back seam."""
    from huntkit.patterns import tapered_panel
    top = col.edge_length("top")
    wf = 2 * float(c.a([c.z_c])[0])
    dl = (per - top) / 4.0      # equal side shift on all four side edges, so the two side seams match exactly
    f = tapered_panel("roll-top collar, frame side (ULTRA)", wf, wf - 2 * dl, COLLAR_H, seam_allowance_mm=SA_BODY,
                      material_id="challenge_ultra_200", piece_id="B-06f")
    r = tapered_panel("roll-top collar", per - wf, per - wf - 2 * dl, COLLAR_H, seam_allowance_mm=SA_BODY,
                      material_id="robic_100d_ripstop", piece_id="B-06")
    return f, r


def boxed_swell(qty=8):
    """Boxed swell (concepts): the SPINE 16 mm fairlead swell (attachment.yaml swell_mm, 90 x 50 window, patterns_v31
    SWELL_LEN / SWELL_W) made from ONE rectangle with four boxed corners: (90 + 2 x 16) x (50 + 2 x 16), straight seams
    only. Sewn INSIDE B-01 over a 90 x 50 window. ASSUMPTION: same cleat clearance as the cone caps (2 mm air)."""
    from huntkit.patterns import rect_panel
    p = rect_panel("boxed fairlead swell", 90 + 32, 50 + 32, 0.0, seam_allowance_mm=SA_FLAT,
                   material_id="challenge_ultra_200", quantity=qty, piece_id="B-13x")
    return p


# ---------------------------------------------------------------------------- wrap surface (WRAP concept)
US = 600.0


class WrapSurface:
    """(U, z) -> xyz on the WRAP outer half (U = q * 600, q 0 at the RIGHT frame corner, 1 at the LEFT, over the
    aft face), body below the collar seam. Same convention as patterns_v31.MasterSurface."""

    def __init__(self, c: Concept, dz=4.0, m=600):
        self.c = c
        self.zs = np.unique(np.r_[np.arange(Z0, c.z_c, dz), Z_SB, Z_SH, c.z_c])
        self.R = []
        th = np.linspace(0, np.pi, 3000)
        cs, sn = np.cos(th), np.sin(th)
        for z in self.zs:
            a, d, yf = float(c.a([z])[0]), float(c.depth([z])[0]), float(y_frame([z])[0])
            x = a * np.sign(cs) * np.abs(cs) ** (2 / c.n)
            y = yf + d * np.abs(sn) ** (2 / c.n)
            self.R.append(_resample_open(np.column_stack([x, y]), m))
        self.R = np.array(self.R)
        self.m = m

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        q = np.clip(uv[:, 0] / US, 0, 1)
        z = np.clip(uv[:, 1], self.zs[0], self.zs[-1])
        j = np.clip(np.searchsorted(self.zs, z, side="right") - 1, 0, len(self.zs) - 2)
        w = (z - self.zs[j]) / (self.zs[j + 1] - self.zs[j])
        f = q * (self.m - 1)
        i = np.clip(np.floor(f).astype(int), 0, self.m - 2)
        t = f - i
        out = np.zeros((len(q), 3))
        for jj, ww in ((j, 1 - w), (j + 1, w)):
            P = (1 - t)[:, None] * self.R[jj, i] + t[:, None] * self.R[jj, i + 1]
            out[:, :2] += ww[:, None] * P
        out[:, 2] = z
        return out


def _line(a, b, step=4.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
    return [tuple(a + (b - a) * i / n) for i in range(n + 1)]


WRAP_ZIP = {"q_lo": 0.15, "z_lo": 248.0, "q_hi": 0.85, "z_hi": Z_SH}   # SPINE: z 248 (right hip) -> 631.2 (left)


def develop(surface, edges_uv, spacing=14.0, **kw):
    ring = []
    for _, pts in edges_uv:
        ring.extend([tuple(p) for p in pts[:-1]])
    region = Polygon(ring)
    if not region.is_valid:
        region = region.buffer(0)
    fm = develop_region(surface, region, spacing=spacing, boundary_spacing=5.0, boundary_weight=100.0)
    flat_edges = [(nm, [tuple(p) for p in fm.map_uv(np.asarray(pts))]) for nm, pts in edges_uv]
    p = Piece.from_edges(kw.pop("name"), flat_edges, **kw)
    return p, fm


def inverse_map(fm, pts2):
    """Parameter-space (uv) points whose flat image is pts2 (barycentric in the flat triangles)."""
    out = []
    A, B, C = (fm.V2[fm.tris[:, j]] for j in range(3))
    for p in np.atleast_2d(pts2):
        v0, v1, v2 = B - A, C - A, p - A
        den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
        den = np.where(np.abs(den) < 1e-12, 1e-12, den)
        l1 = (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / den
        l2 = (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / den
        bary = np.stack([1 - l1 - l2, l1, l2], 1)
        j = int(np.argmin(np.clip(-bary, 0, None).sum(1)))
        bb = np.clip(bary[j], 0, None)
        out.append(bb / bb.sum() @ fm.uv[fm.tris[j]])
    return np.array(out)


def wrap_split_uv(S, spacing=14.0):
    """Zip line STRAIGHT ON THE FLAT pattern (the easiest zip to sew): develop the whole tapered wrap (z 35 -> 631.2),
    draw the chord between the flat images of the zip ends (q 0.15, z 248) and (q 0.85, z 631.2), carry it back to
    (U, z). The line is extended straight (on the flat) to the right frame-corner seam; at its upper end it meets the
    SHOULDER seam (z 631.2), as on SPINE."""
    full = [("b", _line((0, Z0), (US, Z0))), ("l", _line((US, Z0), (US, Z_SH))),
            ("t", _line((US, Z_SH), (0, Z_SH))), ("r", _line((0, Z_SH), (0, Z0)))]
    _, fm = develop(S, full, spacing, name="tmp", seam_allowance_mm=0.0)
    e_lo = fm.map_uv([(WRAP_ZIP["q_lo"] * US, WRAP_ZIP["z_lo"])])[0]
    e_hi = fm.map_uv([(WRAP_ZIP["q_hi"] * US, WRAP_ZIP["z_hi"] - 0.5)])[0]
    # extend downward (on the flat) to the flat image of the right frame-corner edge (q = 0)
    from shapely.geometry import LineString
    edge2 = fm.map_uv(np.asarray(_line((0, Z0), (0, Z_SH), 4.0)))
    ray = LineString([e_hi, e_hi + 3.0 * (e_lo - e_hi)])
    x = ray.intersection(LineString(edge2))
    if x.geom_type != "Point":
        x = min(getattr(x, "geoms", [x]), key=lambda g: g.distance(LineString([e_hi, e_lo])))
    start = np.array([x.x, x.y])
    t = np.linspace(0.0, 1.0, 300)
    line2 = start[None] + t[:, None] * (e_hi - start)[None]
    uv = inverse_map(fm, line2)
    uv[0, 0] = 0.0
    uv[-1] = (WRAP_ZIP["q_hi"] * US, Z_SH)
    return uv, fm


def wrap_pieces(c: Concept, spacing=14.0):
    """WRAP outer panel = 3 pieces: lower (below the zip), mid (above the zip, below the shoulder seam) and the
    shoulder band (z 631.2 -> collar seam, a developable prism). One flat piece over the taper/prism kink is not
    developable (p99 6.5 % strain, checked 2026-11-07), so the shoulder seam stays, as on SPINE."""
    S = WrapSurface(c)
    split, fm = wrap_split_uv(S, spacing)
    z_a = float(split[0, 1])
    qh = WRAP_ZIP["q_hi"] * US
    split = [tuple(p) for p in split]
    lo = [("bottom", _line((0, Z0), (US, Z0))), ("left_frame", _line((US, Z0), (US, Z_SH))),
          ("shoulder", _line((US, Z_SH), (qh, Z_SH))), ("split", split[::-1]),
          ("right_frame", _line((0, z_a), (0, Z0)))]
    mid = [("split", split), ("shoulder", _line((qh, Z_SH), (0, Z_SH))), ("right_frame", _line((0, Z_SH), (0, z_a)))]
    top = [("shoulder", _line((0, Z_SH), (US, Z_SH))), ("left_frame", _line((US, Z_SH), (US, c.z_c))),
           ("top", _line((US, c.z_c), (0, c.z_c))), ("right_frame", _line((0, c.z_c), (0, Z_SH)))]
    sa = {"default": SA_BODY, "split": SA_ZIP}

    def cut_from(fm_, edges_uv, **kw):
        """Lower and mid pieces are CUT from one flat development of the tapered wrap (as a pattern-maker cuts a
        drafted panel along a line), so the zip edges match exactly and are straight."""
        return Piece.from_edges(kw.pop("name"), [(nm, [tuple(q) for q in fm_.map_uv(np.asarray(pts))])
                                                 for nm, pts in edges_uv], **kw)

    p_lo = cut_from(fm, lo, name="wrap panel, lower (below the zip)", seam_allowance_mm=sa,
                    material_id="cordura_330d_nylon66", piece_id="W-02b")
    p_mid = cut_from(fm, mid, name="wrap panel, above the zip", seam_allowance_mm=sa,
                     material_id="cordura_330d_nylon66", piece_id="W-02a")
    p_top, f_top = develop(S, top, spacing, name="wrap shoulder band", seam_allowance_mm=SA_BODY,
                           material_id="cordura_330d_nylon66", piece_id="W-02c")
    strain = {"W-02a+b (one development)": fm.strain_stats(), "W-02c": f_top.strain_stats()}
    zl = [p for p in split if p[0] >= WRAP_ZIP["q_lo"] * US - 1e-6]
    zip3 = S(np.asarray(zl))
    zip_len = float(np.linalg.norm(np.diff(zip3, axis=0), axis=1).sum())
    return p_lo, p_mid, p_top, strain, zip_len, S, split


def d_bottom(c: Concept):
    """WRAP bottom: the D section at z 35 (flat): straight frame edge + one curved edge."""
    a, d, yf = A_BOT, float(c.depth([Z0])[0]), float(y_frame([Z0])[0])
    th = np.linspace(0, np.pi, 200)
    cs, sn = np.cos(th), np.sin(th)
    x = a * np.sign(cs) * np.abs(cs) ** (2 / c.n)
    y = d * np.abs(sn) ** (2 / c.n)
    curve = [(float(xx), float(yy)) for xx, yy in zip(x, y)]
    edges = [("frame", [(-a, 0.0), (a, 0.0)]), ("aft", curve)]
    return Piece.from_edges("bottom (D)", edges, seam_allowance_mm=SA_BODY, material_id="cordura_500d_nylon66",
                            piece_id="B-05")


# ---------------------------------------------------------------------------- HATCH face
HATCH = {"inset": 40.0, "z_lo": 100.0, "z_hinge": 720.0, "r": 60.0}   # ASSUMPTION: door geometry


def hatch_face(c: Concept, H: dict | None = None):
    """Face of HATCH: U-surround (one piece, inner R60 corners), door (rounded bottom corners), hinge band above.
    Face flat coords (x, s) with s the unrolled aft-face length (exact: planar facets containing x).
    ``H`` overrides the door geometry (default HATCH)."""
    HATCH_ = HATCH if H is None else H
    zk, s, a = front_face_profile(c)
    S = lambda z: float(np.interp(z, zk, s))           # noqa: E731
    A = lambda z: float(np.interp(z, zk, a))           # noqa: E731
    ins, r = HATCH_["inset"], HATCH_["r"]
    s0, s1 = S(HATCH_["z_lo"]), S(HATCH_["z_hinge"])
    zz = np.linspace(HATCH_["z_lo"] + r, HATCH_["z_hinge"], 30)
    right_in = [(A(z) - ins, S(z)) for z in zz]
    xr0 = A(HATCH_["z_lo"] + r) - ins
    arc_r = [(xr0 - r + r * math.cos(t), s0 + r - r * math.sin(t)) for t in np.linspace(0, math.pi / 2, 12)]
    arc_r = arc_r[::-1]   # from the bottom (x = xr0 - r, s0) up to (xr0, s0 + r)
    arc_l = [(-x, y) for x, y in arc_r][::-1]
    u_right = arc_r + right_in[1:]           # bottom -> hinge, right side
    u_left = [(-x, y) for x, y in u_right]   # bottom -> hinge, left side
    # door: CCW: bottom (left -> right), right up, top (hinge) right -> left, left down
    door_edges = [("zip", _door_u(u_left, u_right)),
                  ("hinge", [u_right[-1], u_left[-1]])]
    door = Piece.from_edges("horseshoe door", door_edges, seam_allowance_mm={"default": SA_ZIP, "hinge": SA_BODY},
                            material_id="cordura_330d_nylon66", piece_id="B-02door")
    # surround: outer bottom, outer right up to hinge, top-right short edge, inner U (reversed), top-left, outer left
    oz = [z for z in zk if z <= HATCH_["z_hinge"]] + [HATCH_["z_hinge"]]
    out_r = [(A(z), S(z)) for z in oz]
    out_l = [(-A(z), S(z)) for z in oz]
    sur_edges = [("bottom", [out_l[0], out_r[0]]), ("outer_right", out_r),
                 ("top_right", [out_r[-1], u_right[-1]]), ("zip", _door_u(u_left, u_right)[::-1]),
                 ("top_left", [u_left[-1], out_l[-1]]), ("outer_left", out_l[::-1])]
    sur = Piece.from_edges("U-surround", sur_edges, seam_allowance_mm={"default": SA_BODY, "zip": SA_ZIP},
                           material_id="cordura_330d_nylon66", piece_id="B-02u")
    hz = [HATCH_["z_hinge"]] + [z for z in zk if z > HATCH_["z_hinge"]]
    br = [(A(z), S(z)) for z in hz]
    bl = [(-A(z), S(z)) for z in hz]
    band_edges = [("bottom", [bl[0], br[0]]), ("right", br), ("top", [br[-1], bl[-1]]), ("left", bl[::-1])]
    band = Piece.from_edges("hinge band", band_edges, seam_allowance_mm=SA_BODY, material_id="cordura_330d_nylon66",
                            piece_id="B-02h")
    zip_len = Piece.from_edges("tmp", [("u", _door_u(u_left, u_right)), ("c", [u_right[-1], u_left[-1]])],
                               seam_allowance_mm=0).edge_length("u")
    return sur, door, band, zip_len


def _door_u(u_left, u_right):
    """Door U edge, CCW on the door: down the left side, across the bottom (the chord between the two arcs), up the
    right side."""
    return list(reversed(u_left)) + list(u_right)


# ============================================================================ bills of pieces + seams
@dataclass
class Build:
    concept: Concept
    pieces: list                  # [(Piece, group)] group: shell | collar | swell | accent | flat
    seams: list                   # [(Seam, tags)] tags: set of 'ring', 'zip', 'flat', 'bound'
    zips: list                    # dicts: name, length_mm, corners
    swells: dict                  # {'kind': 'boxed'|'cone', 'n': 8}
    appliques: list               # [(Piece)] camo pieces whose edge is turned and topstitched
    darts: int = 0
    strain: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


def _seam(a, b, name, *tags):
    return (Seam(a, b, name=name), set(tags))


def _accent_rect(name, w, h, pid, qty=1):
    from huntkit.patterns import rect_panel
    return rect_panel(name, w, h, 0.0, seam_allowance_mm=SA_FLAT, material_id="polyester_ht_630d_printable",
                      quantity=qty, piece_id=pid)


def _chevron(name, w, h_side, h_peak, pid, qty=1):
    """Kick plate with an angular (chevron) top edge: functional edge line, straight seams only."""
    edges = [("bottom", [(0, 0), (w, 0)]), ("right", [(w, 0), (w, h_side)]),
             ("top", [(w, h_side), (w / 2, h_peak), (0, h_side)]), ("left", [(0, h_side), (0, 0)])]
    return Piece.from_edges(name, edges, seam_allowance_mm=SA_FLAT, material_id="polyester_ht_630d_printable",
                            quantity=qty, piece_id=pid)


def build_concept(c: Concept) -> Build:
    if c.key in ("slab", "twin", "hatch"):
        return _build_box(c)
    if c.key == "wrap":
        return _build_wrap(c)
    raise KeyError(c.key)


def _collar_seams(top_edges, col, hem):
    s = [_seam(top_edges, col.edge("bottom"), "collar | body tops (ring)", "ring", "bound"),
         _seam(col.edge("left"), col.edge("right").reversed(), "collar back seam", "bound"),
         _seam(hem.edge("bottom"), col.edge("top"), "hem | collar top (ring)", "ring"),
         _seam(hem.edge("left"), hem.edge("right").reversed(), "hem back seam")]
    return s


def _build_box(c: Concept) -> Build:
    B1 = frame_panel(c)
    G = gusset(c)
    BOT = box_bottom(c)
    col0, hem, hd, per = collar_set(c)
    colf, col = frame_collar(c, col0, per)
    pieces = [(B1, "shell"), (G, "shell"), (BOT, "shell"), (colf, "collar"), (col, "collar"), (hem, "collar"),
              (hd, "collar")]
    seams, zips, apps = [], [], []
    w_face_bot = 2 * A_BOT
    if c.key == "slab":
        FR, FL = front_face(c, split_x=0.0)
        pieces += [(FR, "shell"), (FL, "shell")]
        faces_r, faces_l = [FR.edge("outer")], [FL.edge("outer").reversed()]
        face_bottom = [FL.edge("bottom"), FR.edge("bottom")]
        face_top = [FR.edge("top"), FL.edge("top")]
        seams.append(_seam(FR.edge("centre"), FL.edge("centre").reversed(), "centre seam (zip z 140-660 in it)",
                           "zip", "bound"))
        L = 520.0
        zips.append({"name": "centre zip", "length_mm": L, "corners": 0, "z": (140, 660), "where": "centre seam"})
        flap = _accent_rect("zip storm flap (camo)", 50, L + 40, "SH-02")
        apps.append(flap)
        pieces.append((flap, "accent"))
        seams.append((Seam(flap.edge("right"), flap.edge("right"), name="storm flap | face R (topstitch)"), {"flat"}))
        cup = Piece.from_edges("bow cam cup (stretch)", [("bottom", [(0, 0), (160, 0)]), ("right", [(160, 0), (160, 200)]),
                                                         ("top", [(160, 200), (0, 200)]), ("left", [(0, 200), (0, 0)])],
                               seam_allowance_mm=SA_FLAT, material_id="poly_spandex_stretch_woven_printable",
                               piece_id="SH-04")
        pieces.append((cup, "flat"))
        seams.append((Seam([cup.edge("left"), cup.edge("bottom"), cup.edge("right")],
                           [cup.edge("left"), cup.edge("bottom"), cup.edge("right")], name="cam cup | face R"), {"flat"}))
    elif c.key == "twin":
        (F,) = front_face(c)
        pieces.append((F, "shell"))
        faces_r, faces_l = [F.edge("right")], [F.edge("left").reversed()]
        face_bottom = [F.edge("bottom")]
        face_top = [F.edge("top")]
        L = 580.0
        for side in ("R", "L"):
            zips.append({"name": f"corner zip {side}", "length_mm": L, "corners": 0, "z": (120, 700),
                         "where": f"aft face | gusset {side} seam"})
        # stretch overload pocket on the face: z 60 -> 420, 40 mm inside each corner zip
        w_p = 2 * float(c.a([240])[0]) - 2 * 40
        pk = Piece.from_edges("stretch overload pocket", [("bottom", [(0, 0), (w_p, 0)]), ("right", [(w_p, 0), (w_p, 360)]),
                                                          ("top", [(w_p, 360), (0, 360)]), ("left", [(0, 360), (0, 0)])],
                              seam_allowance_mm=SA_FLAT, material_id="poly_spandex_stretch_woven_printable",
                              piece_id="D-01t")
        pieces.append((pk, "flat"))
        seams.append((Seam([pk.edge("left"), pk.edge("bottom"), pk.edge("right")],
                           [pk.edge("left"), pk.edge("bottom"), pk.edge("right")], name="pocket | face (3 sides)"), {"flat"}))
        bind = _accent_rect("pocket mouth binding (camo)", 32, w_p + 20, "SH-02")
        pieces.append((bind, "accent"))
        seams.append((Seam(bind.edge("right"), bind.edge("right"), name="binding | pocket mouth"), {"flat"}))
    else:  # hatch
        sur, door, band, L = hatch_face(c)
        pieces += [(sur, "shell"), (door, "shell"), (band, "shell")]
        faces_r = [sur.edge("outer_right"), band.edge("right")]
        faces_l = [sur.edge("outer_left").reversed(), band.edge("left").reversed()]
        face_bottom = [sur.edge("bottom")]
        face_top = [band.edge("top")]
        seams.append(_seam(door.edge("zip"), sur.edge("zip").reversed(), "horseshoe zip door | surround", "zip"))
        seams.append(_seam([sur.edge("top_left").reversed(), door.edge("hinge").reversed(),
                            sur.edge("top_right").reversed()], band.edge("bottom"),
                           "surround tops + door hinge | hinge band", "bound"))
        zips.append({"name": "horseshoe zip", "length_mm": L, "corners": 2, "z": (HATCH["z_lo"], HATCH["z_hinge"]),
                     "where": "door | U-surround"})
        flap = _accent_rect("door pull tab + cam cup (camo)", 160, 200, "SH-04")
        apps.append(flap)
        pieces.append((flap, "accent"))
    # body seams (box)
    seams += [
        _seam(B1.edge("right"), G.edge("frame").reversed(), "B-01 | gusset R", "bound"),
        _seam(B1.edge("left").reversed(), G.edge("frame").reversed(), "B-01 | gusset L", "bound"),
        _seam(faces_r, G.edge("aft"), "aft face | gusset R" + (" (corner zip z 120-700)" if c.key == "twin" else ""),
              *(("zip", "bound") if c.key == "twin" else ("bound",))),
        _seam(faces_l, G.edge("aft"), "aft face | gusset L" + (" (corner zip z 120-700)" if c.key == "twin" else ""),
              *(("zip", "bound") if c.key == "twin" else ("bound",))),
        _seam(B1.edge("bottom"), BOT.edge("bottom"), "bottom | B-01", "ring", "bound"),
        _seam(face_bottom, BOT.edge("top").reversed(), "bottom | aft face", "bound"),
        _seam(G.edge("bottom"), BOT.edge("right"), "bottom | gusset R", "bound"),
        _seam(G.edge("bottom"), BOT.edge("left").reversed(), "bottom | gusset L", "bound"),
    ]
    seams += [_seam([B1.edge("top"), G.edge("top"), *face_top, G.edge("top")],
                    [colf.edge("bottom"), col.edge("bottom")], "collar | body tops (ring)", "ring", "bound"),
              _seam(colf.edge("right"), col.edge("left").reversed(), "collar frame side | collar R", "bound"),
              _seam(colf.edge("left"), col.edge("right").reversed(), "collar frame side | collar L", "bound"),
              _seam(hem.edge("bottom"), [colf.edge("top"), col.edge("top")], "hem | collar top (ring)", "ring"),
              _seam(hem.edge("left"), hem.edge("right").reversed(), "hem back seam")]
    # camo: chevron kick plate across the aft face + both gussets (3 appliques), roll-top hem band (SH-03 as SPINE)
    d0 = float(c.depth([Z0])[0])
    kp_face = _chevron("kick plate, aft face (camo)", w_face_bot, 70, 140, "SH-01a")
    kp_side = _chevron("kick plate, gusset (camo)", d0, 70, 70, "SH-01b", qty=2)
    hemband = _accent_rect("roll-top hem band (camo)", min(per, COLLAR_TOP), 30, "SH-03")
    for p in (kp_face, kp_side, hemband):
        pieces.append((p, "accent"))
        apps.append(p)
    sw = boxed_swell()
    pieces.append((sw, "swell"))
    return Build(c, pieces, seams, zips, {"kind": "boxed", "n": 8}, apps,
                 extra={"collar_perimeter_mm": per})


def _build_wrap(c: Concept) -> Build:
    B1 = frame_panel(c)
    lo, mid, top, strain, zip_len, S, split = wrap_pieces(c)
    BOT = d_bottom(c)
    col, hem, hd, per = collar_set(c)
    pieces = [(B1, "shell"), (lo, "shell"), (mid, "shell"), (top, "shell"), (BOT, "shell"), (col, "collar"),
              (hem, "collar"), (hd, "collar")]
    hi = top
    seams = [
        _seam(B1.edge("right"), [lo.edge("right_frame").reversed(), mid.edge("right_frame").reversed(),
                                 top.edge("right_frame").reversed()], "B-01 | wrap R", "bound"),
        _seam(B1.edge("left").reversed(), [lo.edge("left_frame"), top.edge("left_frame")], "B-01 | wrap L", "bound"),
        _seam(lo.edge("split"), mid.edge("split").reversed(), "diagonal split (zip from q 0.15)", "zip"),
        _seam(top.edge("shoulder"), [mid.edge("shoulder").reversed(), lo.edge("shoulder").reversed()],
              "shoulder seam (ring, z 631.2)", "bound"),
        _seam(B1.edge("bottom"), BOT.edge("frame"), "bottom | B-01", "ring", "bound"),
        _seam(lo.edge("bottom"), BOT.edge("aft").reversed(), "bottom (D) | wrap", "bound"),
    ]
    seams += _collar_seams([B1.edge("top"), hi.edge("top")], col, hem)
    # band + storm strip + accents: SPINE pieces scaled to this zip (panels / patterns_v31 areas)
    from huntkit.patterns import rect_panel
    band_w = 51.4e3 / 509.0        # SPINE D-01 seam area / SPINE zip length (patterns_v31 D-01, geometry zip 509 mm)
    band = rect_panel("diagonal stretch band", zip_len, band_w, 0.0, seam_allowance_mm=SA_FLAT,
                      material_id="poly_spandex_stretch_woven_printable", piece_id="D-01")
    storm = rect_panel("zip storm strip", 30.0, zip_len + 40, 0.0, seam_allowance_mm=SA_FLAT,
                       material_id="cordura_330d_nylon66", piece_id="B-08")
    mouth = _accent_rect("band mouth binding (camo)", 32, zip_len + 40, "SH-02")
    pieces += [(band, "flat"), (storm, "flat"), (mouth, "accent")]
    seams += [(Seam(band.edge("bottom"), band.edge("bottom"), name="band lower edge | wrap lower"), {"flat"}),
              (Seam(storm.edge("right"), storm.edge("right"), name="storm strip | zip"), {"flat"}),
              (Seam(mouth.edge("right"), mouth.edge("right"), name="binding | band mouth"), {"flat"})]
    corner = Piece.from_edges("lower-corner shard (camo)", [("a", [(0, 0), (160, 0)]), ("b", [(160, 0), (160, 50)]),
                                                            ("c", [(160, 50), (0, 150)]), ("d", [(0, 150), (0, 0)])],
                              seam_allowance_mm=SA_FLAT, material_id="polyester_ht_630d_printable", quantity=2,
                              piece_id="SH-01")
    cam = _accent_rect("cam-cup shard (camo)", 120, 140, "SH-04")
    hemband = _accent_rect("roll-top hem band (camo)", min(per, COLLAR_TOP), 30, "SH-03")
    apps = [corner, cam, hemband]
    pieces += [(p, "accent") for p in apps]
    pieces.append((boxed_swell(), "swell"))
    return Build(c, pieces, seams, [{"name": "diagonal zip", "length_mm": zip_len, "corners": 0,
                                     "z": (WRAP_ZIP["z_lo"], WRAP_ZIP["z_hi"]), "where": "wrap split line"}],
                 {"kind": "boxed", "n": 8}, apps, strain=strain,
                 extra={"collar_perimeter_mm": per, "surface": S, "split_uv": split})


# ============================================================================ metrics
# ASSUMPTION (beginner sewing time, home walking-foot machine, includes marking, clipping, test-fitting and some
# unpicking). Not calibrated on a real build: on SPINE it gives ~35 h for the main-bag body, more than the BUILD_PLAN
# step 9 guess of "2-3 weekends" (16-24 h at 8 h per weekend). Use it to RANK the concepts, not to plan evenings.
HOURS = {
    "cut_piece": 0.12,        # trace + cut + notch one piece
    "straight_m": 0.6,        # per m of straight seam incl. binding the allowance
    "curved_m": 1.8,          # per m of curved seam: notch match every 50 mm, ease, clip, bind a curve (3x straight)
    "pivot": 0.05,            # per corner pivot inside a seam line
    "zip_fixed": 0.5,         # per zip: baste tape, set stops, sliders
    "zip_m": 1.0,             # per m of zip
    "zip_corner": 0.4,        # per curved zip corner (horseshoe)
    "ring": 0.5,              # per closed 3D ring seam (handling a tube through the machine)
    "swell_cone": 1.2,        # SPINE fairlead swell: rhombus window + 2 cone caps + crest seam, 8 mm SA
    "swell_boxed": 0.5,       # boxed swell: rectangle, 4 boxed corners, set into a straight window
    "applique_m": 0.8,        # per m of turned + topstitched camo edge
    "dart": 0.25,
    "bartack": 0.1,           # per webbing / hardware termination added by a concept feature
}
CURVE_SAGITTA = 5.0   # ASSUMPTION: a seam segment whose flat edge bows > 5 mm off its chord is sewn as a curve
PIVOT_DEG = 12.0      # a turn > 12 deg at one vertex is a pivot (straight-to-straight), not a curve
PIVOT_MIN_DEG, PIVOT_SEG_MM = 2.0, 12.0   # ... and so is a > 2 deg turn between two straight runs > 12 mm (a crease
                                           # kink); a developed curve is sampled every 4-5 mm and never qualifies


def edge_shape(pts):
    """(max sagitta of the pivot-free segments, number of pivots) of a flat polyline."""
    P = np.asarray(pts, float)
    if len(P) < 3:
        return 0.0, 0
    d = np.diff(P, axis=0)
    keep = np.linalg.norm(d, axis=1) > 1e-6
    d = d[keep]
    P = np.vstack([P[:1], P[1:][keep]])
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0]))
    turn = np.abs((np.diff(ang) + 180) % 360 - 180)
    # a pivot is a sharp turn at ONE vertex; gentle turns spread over many vertices are curvature
    seg_len = np.linalg.norm(d, axis=1)
    piv = [i + 1 for i, t in enumerate(turn)
           if t > PIVOT_DEG or (t > PIVOT_MIN_DEG and min(seg_len[i], seg_len[i + 1]) > PIVOT_SEG_MM)]
    cuts = [0] + piv + [len(P) - 1]
    sag = 0.0
    for i0, i1 in zip(cuts[:-1], cuts[1:]):
        seg = P[i0:i1 + 1]
        if len(seg) < 3:
            continue
        a, b = seg[0], seg[-1]
        ch = b - a
        L = np.linalg.norm(ch)
        if L < 1e-9:
            continue
        dev = np.abs(ch[0] * (seg[:, 1] - a[1]) - ch[1] * (seg[:, 0] - a[0])) / L
        sag = max(sag, float(dev.max()))
    return sag, len(piv)


def seam_shape(seam: Seam):
    sag, piv = 0.0, 0
    for side in (seam.a, seam.b):
        pts = []
        for e in side:
            p = e.points
            pts.extend(p if not pts else p[1:])
        s, n = edge_shape(pts)
        sag = max(sag, s)
        piv = max(piv, n)
    return sag, piv


def metrics(build: Build) -> dict:
    """Uniform metrics for any Build (concepts and the SPINE baseline adapter)."""
    c = build.concept
    n_cut = sum(p.quantity for p, _ in build.pieces)
    by_group = {}
    for p, g in build.pieces:
        by_group[g] = by_group.get(g, 0) + p.quantity
    seam_rows, L_str, L_cur, n_curved, n_piv, n_ring = [], 0.0, 0.0, 0, 0, 0
    for s, tags in build.seams:
        L = s.length_a
        sag, piv = seam_shape(s)
        curved = sag > CURVE_SAGITTA
        n_curved += int(curved)
        n_piv += piv
        n_ring += int("ring" in tags)
        if curved:
            L_cur += L
        else:
            L_str += L
        seam_rows.append({"name": s.name, "length_mm": round(L, 1), "sagitta_mm": round(sag, 1), "pivots": piv,
                          "curved": curved, "tags": sorted(tags), "error_mm": round(s.error_mm, 2)})
    app_m = sum(_perim(p) * p.quantity for p in build.appliques) / 1000
    zip_m = sum(z["length_mm"] for z in build.zips) / 1000
    zip_corners = sum(z["corners"] for z in build.zips)
    H = HOURS
    sw_rate = H["swell_cone"] if build.swells["kind"] == "cone" else H["swell_boxed"]
    hours = {
        "cutting": n_cut * H["cut_piece"],
        "straight seams": L_str / 1000 * H["straight_m"],
        "curved seams": L_cur / 1000 * H["curved_m"],
        "pivots": n_piv * H["pivot"],
        "ring seams": n_ring * H["ring"],
        "zips": len(build.zips) * H["zip_fixed"] + zip_m * H["zip_m"] + zip_corners * H["zip_corner"],
        "swells": build.swells["n"] * sw_rate,
        "camo applique": app_m * H["applique_m"],
        "darts": build.darts * H["dart"],
        "hardware bartacks": build.extra.get("bartacks", 0) * H["bartack"],
    }
    mass = mass_breakdown(build)
    out = {"key": c.key, "name": c.name, "cut_pieces": n_cut, "pieces_by_group": by_group,
           "piece_types": len(build.pieces), "seams": len(build.seams), "seam_length_m": round((L_str + L_cur) / 1000, 2),
           "curved_seams": n_curved, "curved_seam_length_m": round(L_cur / 1000, 2), "pivots": n_piv,
           "ring_seams": n_ring, "zips": len(build.zips), "zip_length_m": round(zip_m, 3), "zip_list": build.zips,
           "swells": build.swells, "applique_edge_m": round(app_m, 2), "hours": {k: round(v, 2) for k, v in hours.items()},
           "hours_total": round(sum(hours.values()), 1), "mass_g": mass, "seam_rows": seam_rows,
           "seam_check_max_err_mm": max((abs(r["error_mm"]) for r in seam_rows if "flat" not in r["tags"]), default=0.0),
           "strain": build.strain}
    return out


def _perim(p: Piece) -> float:
    return float(sum(p.edge_length(n) for n in p.edge_names))


def piece_mass_g(p: Piece) -> float:
    m = MAT.load(p.material_id)
    a = p.area_mm2 / 1e6
    if getattr(p, "thickness_mm", None):
        return a * p.thickness_mm / 1000 * m.require("density_kg_m3") * 1000 * p.quantity
    if p.material_id == "hdpe_sheet":
        return a * HDPE_T / 1000 * m.require("density_kg_m3") * 1000 * p.quantity
    return a * m.require("areal_density_gsm") * p.quantity


SLIDER_G = float(MAT.load("slider_10").require("mass_g"))   # 19.0 g: slider_10 record (YKK #10 CN, metal pull; BL-034,
#                                                               was 6 g ASSUMPTION from the build_geometry zip row)


def zip_mass_g(z) -> float:
    """build_geometry rule: coil_zipper_10 g/m x (length + 60 mm) + 2 sliders x 6 g (``mass_g`` in the dict overrides)."""
    if "mass_g" in z:
        return float(z["mass_g"])
    return MAT.load("coil_zipper_10").require("mass_g_m") * (z["length_mm"] + 60) / 1000 + 2 * SLIDER_G


def mass_breakdown(build: Build) -> dict:
    g = {}
    for p, grp in build.pieces:
        g[grp] = g.get(grp, 0.0) + piece_mass_g(p)
    g["zips"] = sum(zip_mass_g(z) for z in build.zips)
    if build.extra.get("hardware"):
        g["hardware"] = sum(m for _, m in build.extra["hardware"])
    if build.extra.get("common_delta_g"):
        g["common items delta"] = float(build.extra["common_delta_g"])
    g = {k: round(v, 1) for k, v in g.items()}
    g["total"] = round(sum(v for k, v in g.items()), 1)
    return g


def volumes(c: Concept) -> dict:
    yc, zc = c.cg()
    d = c.depth(np.linspace(Z0, c.z_c, 200))
    return {"volume_L": round(c.volume_L(), 2), "volume_cu_in": round(c.volume_L() * 1e6 / L_CUIN / 1e3, 0),
            "body_to_collar_L": round(c.volume_L(upto=c.z_c), 2), "z_collar": c.z_c, "z_fill": round(c.z_fill, 1),
            "fill_height_mm": round(c.z_fill - Z0, 1), "fill_height_in": round((c.z_fill - Z0) / IN, 1),
            "max_depth_mm": round(float(d.max()), 1), "max_depth_in": round(float(d.max()) / IN, 2),
            "depth_top_mm": round(float(c.depth([c.z_c])[0]), 1), "width_max_mm": round(2 * A_MAX, 1),
            "width_max_in": round(2 * A_MAX / IN, 2), "cg_y": round(yc, 1), "cg_z": round(zc, 1),
            "section_k": round(c.k, 4)}


def all_concepts():
    return [make(k) for k in CONCEPTS]


if __name__ == "__main__":
    import json
    print(json.dumps(spine_volume_check(), indent=1))
    print(json.dumps(spine_dome_check(), indent=1))
    for c in all_concepts():
        b = build_concept(c)
        m = metrics(b)
        print(c.name, volumes(c), {k: m[k] for k in ("cut_pieces", "seam_length_m", "curved_seams", "zips",
                                                       "zip_length_m", "hours_total", "seam_check_max_err_mm")},
              m["mass_g"], m["strain"] and {k: round(v["p99_pct"], 2) for k, v in m["strain"].items()})
        rep = check_seams([s for s, t in b.seams if "flat" not in t], tol_mm=1.0)
        if not rep.ok:
            print(rep)


# ============================================================================ SPINE baseline (released v3.1 cut set)
SPINE_GROUPS = {  # patterns_v31 piece id -> group (same groups as the concepts)
    "B-01": "shell", "B-01b": "shell", "B-01u": "shell", "B-02a": "shell", "B-02b": "shell", "B-02c": "shell",
    "B-02d": "shell", "B-03": "shell", "B-05": "shell", "B-06": "collar", "B-07": "collar", "B-07s": "collar",
    "B-13": "swell", "B-14a": "swell", "B-14b": "swell", "B-15a": "swell", "B-15b": "swell",
    "D-01": "flat", "B-08": "flat", "SH-01": "accent", "SH-02": "accent", "SH-03": "accent", "SH-04": "accent"}
SPINE_SEAM_KEYS = ("B-01 tiers", "B-02 R edge", "B-02 L edge", "B-01 | B-01b", "B-01b | B-01u", "B-02a | B-02c",
                   "B-02c | B-02d", "diagonal zip", "B-02d dart", "B-05 |", "B-06 collar", "B-07 hem", "D-01 band",
                   "B-08 strip", "SH-02 binding")


def spine_build(ps) -> Build:
    """Adapter: the released v3.1 pattern set (patterns_v31.build()) as a Build, so SPINE is measured with exactly
    the same metric code as the concepts. Swell seams are left out of the seam list because the swell hour rate
    covers them (as for the concepts' boxed swells); their length is reported in ``extra``."""
    c = Concept(key="spine", name="SPINE", kind="spine",
                tagline="v3.1 released: teardrop, 3-tier frame panel, gores, 8 cone swells, diagonal zip + band",
                access="roll-top + diagonal #10 zip z 248-631 (right hip -> left shoulder) under the stretch band")
    c.z_c = Z_COLLAR_SPINE
    pieces = [(p, SPINE_GROUPS[pid]) for pid, p in ps.pieces.items() if pid in SPINE_GROUPS]
    seams, swell_len = [], 0.0
    for s in ps.seams:
        if s.name.startswith("swell"):
            swell_len += s.length_a
            continue
        if not s.name.startswith(SPINE_SEAM_KEYS):
            continue
        tags = {"bound"}
        if s.name.startswith(("B-05 | B-01", "B-06 collar | body", "B-07 hem | B-06")):
            tags.add("ring")
        if s.name.startswith("diagonal zip"):
            tags = {"zip"}
        if s.name.startswith(("D-01", "B-08", "SH-02")):
            tags = {"flat"}
        seams.append((s, tags))
    zl = float(GEOM["bag"]["diagonal"]["zip_length_mm"])
    apps = [ps.pieces[k] for k in ("SH-01", "SH-03", "SH-04")]
    n_dart = sum(1 for s in ps.seams if "dart" in s.name)
    return Build(c, pieces, seams, [{"name": "diagonal zip", "length_mm": zl, "corners": 0, "z": (248.0, Z_SH),
                                     "where": "B-02a/c | B-02b"}],
                 {"kind": "cone", "n": 8}, apps, darts=0,
                 extra={"swell_seam_length_m": round(swell_len / 1000, 2), "darts_in_seams": n_dart})


def spine_volumes() -> dict:
    v = GEOM["volumes"]
    cg = GEOM["bag"]["cg_uniform_fill"]
    return {"volume_L": float(v["main_bag_L"]), "volume_cu_in": float(v["main_bag_cu_in"]),
            "body_to_collar_L": float(v["body_to_collar_seam_L"]), "z_collar": Z_COLLAR_SPINE, "z_fill": Z_FILL_SPINE,
            "fill_height_mm": Z_FILL_SPINE - Z0, "fill_height_in": round((Z_FILL_SPINE - Z0) / IN, 1),
            "max_depth_mm": D_MAX, "max_depth_in": round(D_MAX / IN, 2),
            "depth_top_mm": float(np.interp(Z_COLLAR_SPINE, SPINE_ST[:, 0], SPINE_ST[:, 3])),
            "width_max_mm": round(2 * A_MAX, 1), "width_max_in": round(2 * A_MAX / IN, 2),
            "cg_y": float(cg["y"]), "cg_z": float(cg["z"]), "section_k": round(K_SPINE, 4)}


# ============================================================================ scoring
WEIGHTS = {"build": 0.35, "mass": 0.15, "access": 0.15, "carry": 0.15, "durability": 0.10, "look": 0.10}
# Judgement scores (1-5), reasons in analysis/bag_alternatives.md section 4. Research refs: docs/research/
# bag_body_architectures.md (A1..A6). DECISIONS 2026-11-01: the first bag was REJECTED by the owner as "too boxy/dated".
JUDGED = {
    "spine": {"access": 3.5, "durability": 4.0, "look": 5.0},
    "slab": {"access": 3.5, "durability": 4.0, "look": 2.0},
    "twin": {"access": 4.5, "durability": 3.0, "look": 2.5},
    "wrap": {"access": 3.5, "durability": 4.0, "look": 4.0},
    "hatch": {"access": 5.0, "durability": 2.5, "look": 2.5},
}


def score(rows: dict) -> dict:
    """rows: key -> {'metrics': ..., 'volumes': ...}. Computed criteria use absolute scales (not min-max), so a
    small difference stays a small difference:
    build  = mean of (5 - (hours - best) / 2 h) and (5 - 0.5 x curved seams), clipped 1..5
    mass   = 5 - (bag-body group g - best) / 20 g
    carry  = 5 - (CG y - best) / 5 mm - (CG z - best) / 40 mm   (closer and lower is better; HA-LS-1 rev C)."""
    h_best = min(r["metrics"]["hours_total"] for r in rows.values())
    m_best = min(r["metrics"]["mass_g"]["total"] for r in rows.values())
    y_best = min(r["volumes"]["cg_y"] for r in rows.values())
    z_best = min(r["volumes"]["cg_z"] for r in rows.values())
    clip = lambda v: float(min(5.0, max(1.0, v)))   # noqa: E731
    out = {}
    for k, r in rows.items():
        m, v = r["metrics"], r["volumes"]
        s = {"build": clip(0.5 * (5 - (m["hours_total"] - h_best) / 2.0) + 0.5 * (5 - 0.5 * m["curved_seams"])),
             "mass": clip(5 - (m["mass_g"]["total"] - m_best) / 20.0),
             "carry": clip(5 - (v["cg_y"] - y_best) / 5.0 - (v["cg_z"] - z_best) / 40.0),
             **JUDGED[k]}
        s = {kk: round(vv, 2) for kk, vv in s.items()}
        s["weighted"] = round(sum(WEIGHTS[kk] * s[kk] for kk in WEIGHTS), 2)
        out[k] = s
    return out
