"""Pack 5200 v3.1 "Spine": production pattern set for the bag and all soft goods.

Owner: pattern-maker. Run from the repo root::

    python designs/pack_5200/patterns_v31.py            # build, check, export everything
    python designs/pack_5200/patterns_v31.py --check    # build + checks only (no files)

Out of scope (printed / cut parts owned by other agents): the frame, the fairleads and the
carbon spreader (BP-06). Only their interfaces are drawn here: fairlead swells and ports in
B-01, hinge-eye and bag-hook bartacks, under-strap channels, hipbelt pivot, lumbar pad,
back-panel mesh and stay-rail sleeves.

How the body is drafted
-----------------------
* Master surface = the v3.1 loft of ``build_geometry.py`` (mixed-superellipse rings,
  width scale 1.0639, fill height 1066 mm; geometry.yaml ``bag``), with one pattern decision:
  the 30 mm head setback (smooth step z 560 -> 640, radius ~36 mm) is taken by two ring seams.
  Between the SETBACK seam (z 560 = HEAD_SB_Z[0]) and the SHOULDER seam (z 631.2 = the zip's
  upper end, 0.8 mm under the T_PEAK depth kink at z 632) the surface is ruled ring-to-ring.
  Drafted on the smooth step the frame panel needs 10 % stretch and the face 8 %; with the two
  seams every piece is under 2 % (area-weighted 99th percentile principal strain).
* Each panel is a region in the (q, z) parameter plane (q = ring arc fraction: outer half
  0..1 from the wearer's right, frame half 1..2), meshed and flattened by least squares
  (``huntkit.patterns.develop_region``). Seam edges keep their 3D length, so joined edges
  match to a fraction of a millimetre.
* Ruled parts (stretch band, swell cones, rifle-boot cone) use ``develop_ruled_surface``.

Every number traces to geometry.yaml / panels.yaml / attachment.yaml / a material record, or is
marked ``ASSUMPTION`` below. Units mm.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from shapely.geometry import LineString, Point as SPoint, Polygon
from shapely.ops import split as sh_split

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import build_geometry as BG  # noqa: E402  (pack-designer's geometry, the source of the shape)
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import (Piece, Seam, check_seams, develop_region,  # noqa: E402
                              develop_ruled_surface, grade, rect_panel, tapered_panel)
from huntkit.patterns import curves as CV  # noqa: E402

GEOM = yaml.safe_load((HERE / "geometry.yaml").read_text())
ATTACH = yaml.safe_load((HERE / "attachment.yaml").read_text())
PANELS = yaml.safe_load((HERE / "panels.yaml").read_text())

# ------------------------------------------------------------------ shape (geometry.yaml)
W_SCALE = float(GEOM["bag"]["width_scale_solved"])          # 1.0639
HF = float(GEOM["bag"]["height_z"])                         # 1066 mm, bag bottom -> fill line
Z0 = float(GEOM["bag"]["origin_carry_mode"]["z_bottom"])    # 35
Z_COLLAR = float(GEOM["bag"]["rolltop"]["collar"]["z_seam"])  # 781.2
Z_FILL = float(GEOM["bag"]["profile"]["z_fill_line"])      # 1101
Z_SB = float(BG.HEAD_SB_Z[0])                                # 560: setback seam
Z_SH = float(GEOM["bag"]["diagonal"]["zip_end_left"][2])     # 631.2: shoulder seam = zip end
Z_PEAK = BG.BAG_Z0 + BG.T_PEAK * HF                          # 632: depth-slope kink (T_PEAK)
Q_FACE_R, Q_FACE_L = BG.F_SIDE_OUT, 1 - BG.F_SIDE_OUT         # 0.17 / 0.83 of the outer half
Q_FRM_L, Q_FRM_R = 1 + BG.F_SIDE_FRM, 2 - BG.F_SIDE_FRM       # 1.12 / 1.88 (frame half)
US = 600.0     # parameter scale: U = q * 600 mm (keeps the (U, z) mesh near isotropic)

# ------------------------------------------------------------------ seam allowances
SA_BODY = 12.0     # bound pack seams (panels.yaml B-01..B-05: 12 mm, 301 + binding)
SA_ZIP = 10.0      # zip insertion, 301 (panels.yaml note "zip SA 10 mm")
SA_301 = 10.0      # standard 301 lockstitch seam
SA_SWELL = 8.0     # ASSUMPTION: small set-in swell seams (tight curve, 2.5 mm stitch, taped)
SA_TURN = 8.0      # shard edge turn-under (panels.yaml shards: 8 mm)
SA_LASER = 0.0     # Hypalon, foam, HDPE, laser/die-cut raw edges
NOTCH_PITCH = 50.0  # BUILD_PLAN.md: match notches every 50 mm of centre-line length

# ------------------------------------------------------------------ frame interfaces
STAY_X = 115.0                                    # bag_attach.stations(): x = +/-115
STATIONS = {k: float(v) for k, v in ATTACH["stations_mm"].items()}
SWELL_H = float(ATTACH["swell_mm"])               # 16 mm (accepted, owner 2026-11-01)
SWELL_LEN = 90.0                                  # analysis/bag_attachment.md: 90 mm long
SWELL_W = 50.0    # ASSUMPTION: fairlead 34 mm wide (throat 18 + 2 x cheek 8) + 8 mm each side
# (crest z, lower length, upper length): 90 mm each. Hinge is pushed up so its lower tip sits
# 5 mm above the bottom seam; IM3 is shortened on top so its tip stays 8 mm under the setback
# seam (press that seam allowance UP). IM1/IM2 symmetric.
SWELLS = {"hinge": (62.0, 22.0, 68.0), "im1": (STATIONS["im1"], 45.0, 45.0),
          "im2": (STATIONS["im2"], 45.0, 45.0), "im3": (STATIONS["im3"], 58.0, 32.0)}
PORT_LEN = 45.0          # geometry.yaml meat_harness.anchor_stub.port: slot 45 x 6
HOOK_STRAP_DZ = 70.0     # ASSUMPTION: bag-hook strap bartack 70 mm below the IM2/IM3 crest
HYD_W, HYD_H = 176.0, 430.0   # B-09: panels.yaml 250 wide narrowed to clear the IM swells (x +/-88)
CHANNEL_Y = (0.30, 0.65)      # ASSUMPTION: under-strap channels at 30 % / 65 % of floor depth
CHANNEL_W = 50.0              # 38 mm webbing + 12 mm play (attachment: 38 mm under-straps)

MATERIAL_FACE = {  # cutting face + direction notes per material (cutting instructions)
    "challenge_ultra_200": ("laminate (film) side DOWN = inside of bag", "non-directional, keep grain"),
    "cordura_330d_nylon66": ("PU coat DOWN (inside)", "solid colour: two-way lay allowed"),
    "cordura_500d_nylon66": ("PU coat DOWN (inside)", "solid colour: two-way lay allowed"),
    "robic_100d_ripstop": ("coated side DOWN (inside)", "two-way lay allowed"),
    "robic_210d_ripstop": ("coated side DOWN (inside)", "two-way lay allowed"),
    "silicone_coated_poly_ripstop_40d": ("either", "two-way; weigh plies down, it slides"),
    "ultragrid_210d_uhmwpe_ripstop": ("grid face UP", "two-way lay allowed"),
    "hypalon_coated_nylon": ("coated face UP", "laser-cut, any rotation"),
    "spacer_mesh_3d": ("open mesh face UP (wearer side)", "ONE-WAY: rib direction along the grain"),
    "poly_spandex_stretch_woven_printable": ("print UP", "ONE-WAY print; stretch across the band"),
    "polyester_ht_630d_printable": ("print UP", "ONE-WAY camo print (all shards same direction)"),
    "tpu_coated_nylon_840d": ("TPU DOWN (inside)", "two-way"),
    "eva_foam_45c": ("-", "die-cut sheet, any rotation"), "eva_foam_30c": ("-", "die-cut sheet"),
    "eva_foam_perforated": ("-", "die-cut sheet"), "xlpe_foam": ("-", "die-cut sheet"),
    "hdpe_sheet": ("-", "CNC router / waterjet, any rotation"),
}
FREE_ROTATION = {"hypalon_coated_nylon", "eva_foam_45c", "eva_foam_30c", "eva_foam_perforated",
                 "xlpe_foam", "hdpe_sheet"}
ONE_WAY = {"spacer_mesh_3d", "poly_spandex_stretch_woven_printable", "polyester_ht_630d_printable"}
KNIFE = "CW from the grain-arrow head; cut inside windows/slots first"

HIPBELT_SIZES = ["S", "M", "L", "XL"]
WING_LEN = {k: float(v) for k, v in GEOM["hipbelt"]["wing_length_mm"].items()}   # 186/223/259/296
STRAP_SIZES = ["J", "S"]


# ============================================================================ master surface
class MasterSurface:
    """(U, z) -> xyz on the v3.1 loft, with the setback band ruled between Z_SB and Z_SH.
    ``scale`` > 1 inflates every ring about its centre (used for the rain fly)."""

    def __init__(self, scale: float = 1.0, dz: float = 2.0, m: int = 1440, ruled_band: bool = True,
                 setback: bool = True):
        BG.set_width_scale(W_SCALE)
        self.scale, self.ruled = scale, ruled_band and setback
        sb_keep = BG.HEAD_SETBACK
        if not setback:
            BG.HEAD_SETBACK = 0.0
        zs = list(np.arange(Z0, Z_COLLAR, dz)) + [Z_COLLAR]
        for z in (Z_SB, Z_SH):
            if z not in zs:
                zs.append(z)
        self.zs = np.array(sorted(zs))
        self.R, self.S, self.Lo, self.Lb = [], [], [], []
        for z in self.zs:
            P, _ = BG.ring_xy((z - Z0) / HF, HF, m)
            if scale != 1.0:
                c = np.array([0.0, 0.5 * (P[:, 1].max() + P[:, 1].min()), 0.0])
                P = c + (P - c) * np.array([scale, scale, 1.0])
            sm = BG.ring_seams(P)
            self.R.append(np.vstack([P, P[:1]]))
            self.S.append(sm["s"])
            self.Lo.append(sm["Lo"])
            self.Lb.append(sm["Lb"])
        BG.HEAD_SETBACK = sb_keep

    def _ring(self, j, q):
        q = np.mod(q, 2.0)
        arc = np.where(q <= 1, q * self.Lo[j], self.Lo[j] + (q - 1) * self.Lb[j])
        return np.stack([np.interp(arc, self.S[j], self.R[j][:, k]) for k in range(3)], -1)

    def _smooth(self, q, z):
        z = np.clip(z, self.zs[0], self.zs[-1])
        j = np.clip(np.searchsorted(self.zs, z, side="right") - 1, 0, len(self.zs) - 2)
        out = np.zeros((len(q), 3))
        for jj in np.unique(j):
            m = j == jj
            w = ((z[m] - self.zs[jj]) / (self.zs[jj + 1] - self.zs[jj]))[:, None]
            out[m] = (1 - w) * self._ring(jj, q[m]) + w * self._ring(jj + 1, q[m])
        return out

    def __call__(self, uv):
        uv = np.atleast_2d(np.asarray(uv, float))
        q, z = uv[:, 0] / US, uv[:, 1]
        out = self._smooth(q, z)
        if self.ruled:
            m = (z > Z_SB) & (z < Z_SH)
            if m.any():
                w = ((z[m] - Z_SB) / (Z_SH - Z_SB))[:, None]
                a = self._smooth(q[m], np.full(m.sum(), Z_SB))
                b = self._smooth(q[m], np.full(m.sum(), Z_SH))
                out[m] = (1 - w) * a + w * b
        return out

    def q_of_x_frame(self, x: float, z: float) -> float:
        """q on the FRAME half of ring z where the surface has lateral coordinate x."""
        qs = np.linspace(1.0, 2.0, 2001)
        P = self(np.column_stack([qs * US, np.full_like(qs, z)]))
        return float(np.interp(x, P[:, 0], qs))

    def q_of_point(self, p) -> float:
        j = int(np.argmin(np.abs(self.zs - p[2])))
        R = self.R[j][:-1]
        k = int(np.argmin(np.linalg.norm(R - np.asarray(p), axis=1)))
        arc = self.S[j][k]
        return arc / self.Lo[j] if arc <= self.Lo[j] else 1 + (arc - self.Lo[j]) / self.Lb[j]

    def ring_perimeter(self, z: float, n: int = 1441) -> float:
        qs = np.linspace(0, 2, n)
        P = self(np.column_stack([qs * US, np.full(n, z)]))
        return float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())


def _line(a, b, step=4.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
    return [tuple(a + (b - a) * i / n) for i in range(n + 1)]


def _dense(pts, step=4.0):
    out = [tuple(pts[0])]
    for a, b in zip(pts[:-1], pts[1:]):
        out.extend(_line(a, b, step)[1:])
    return out


def _len(pts) -> float:
    p = np.asarray(pts, float)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


# ============================================================================ developed pieces
@dataclass
class DevPiece:
    """A piece developed from the master surface: named parameter-space edges + flat mesh."""
    piece: Piece
    mesh: object
    edges_uv: dict
    surface: object
    region: Polygon

    def to_flat(self, pts_uv) -> np.ndarray:
        return self.mesh.map_uv(pts_uv)


def develop_piece(surface, edges_uv: list, *, spacing=12.0, **piece_kw) -> DevPiece:
    """``edges_uv`` = ordered [(name, polyline_uv)], CCW in (U, z) seen from outside."""
    ring = []
    for _, pts in edges_uv:
        ring.extend([tuple(p) for p in pts[:-1]])
    region = Polygon(ring)
    if not region.is_valid:
        region = region.buffer(0)
    fm = develop_region(surface, region, spacing=spacing, boundary_spacing=4.0,
                        boundary_weight=100.0)
    flat_edges = [(nm, [tuple(p) for p in fm.map_uv(np.asarray(pts))]) for nm, pts in edges_uv]
    p = Piece.from_edges(piece_kw.pop("name"), flat_edges, **piece_kw)
    return DevPiece(p, fm, dict(edges_uv), surface, region)


def uv_rect_edges(q0, q1, z0, z1, names=("bottom", "right", "top", "left"), step=4.0):
    a, b, c, d = (q0 * US, z0), (q1 * US, z0), (q1 * US, z1), (q0 * US, z1)
    return [(names[0], _line(a, b, step)), (names[1], _line(b, c, step)),
            (names[2], _line(c, d, step)), (names[3], _line(d, a, step))]


# ============================================================================ the pattern set
@dataclass
class PatternSet:
    pieces: dict = field(default_factory=dict)        # id -> Piece (base size)
    graded: dict = field(default_factory=dict)        # id -> {size: Piece}
    dev: dict = field(default_factory=dict)           # id -> DevPiece
    seams: list = field(default_factory=list)
    graded_seams: dict = field(default_factory=dict)  # size -> [Seam]
    virtual: dict = field(default_factory=dict)       # placement outlines used only in seams
    strain: dict = field(default_factory=dict)        # id -> stats
    meta: dict = field(default_factory=dict)          # id -> {sub, zone, notes, kit}
    webbing: list = field(default_factory=list)
    hardware: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def add(self, p: Piece, sub: str, notes: str = "", kit: str = "base", **kw):
        p.knife_direction = p.knife_direction or KNIFE
        self.pieces[p.piece_id] = p
        self.meta[p.piece_id] = {"sub": sub, "notes": notes, "kit": kit, **kw}
        return p

    def all_pieces(self, kit=None, sizes=None):
        """Every piece to cut (graded pieces expanded to their sizes)."""
        out = []
        for pid, p in self.pieces.items():
            if kit and self.meta[pid]["kit"] not in kit:
                continue
            if pid in self.graded:
                for s, g in self.graded[pid].items():
                    if sizes is None or s in sizes:
                        out.append(g)
            else:
                out.append(p)
        return out


def _notch_along(dps: list, curve_uv, pitch=NOTCH_PITCH, label="", ends=False, kind="slit"):
    """Notch every ``pitch`` mm of 3D arc length along a shared parameter curve, on every
    developed piece in ``dps`` (each maps the same 3D points onto its own pattern)."""
    curve_uv = np.asarray(curve_uv, float)
    P3 = dps[0].surface(curve_uv)
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P3, axis=0), axis=1))]
    L = s[-1]
    ts = list(np.arange(pitch, L - pitch * 0.4, pitch))
    if ends:
        ts = [0.0] + ts + [L]
    pts = np.column_stack([np.interp(ts, s, curve_uv[:, 0]), np.interp(ts, s, curve_uv[:, 1])])
    for dp in dps:
        for xy in dp.to_flat(pts):
            dp.piece.add_notch(float(xy[0]), float(xy[1]), kind, label)
    return len(ts)


def _place(dp: DevPiece, pts_uv, kind="placement", label="", closed=False):
    xy = dp.to_flat(np.asarray(pts_uv, float))
    dp.piece.add_internal_line([tuple(p) for p in xy], kind, label, closed)
    return xy


def _drill(dp: DevPiece, pts_uv, label=""):
    for xy in dp.to_flat(np.atleast_2d(pts_uv)):
        dp.piece.add_drill_hole(float(xy[0]), float(xy[1]), 3.0, label)


def _virtual(name, edges):
    return Piece.from_edges(name, edges, seam_allowance_mm=0.0)


# ---------------------------------------------------------------------------- body
def build_body(ps: PatternSet, S: MasterSurface, spacing=12.0):
    diag = BG.diagonal(HF)
    zip_uv = np.array([(S.q_of_point(p) * US, p[2]) for p in diag["zip3"]])
    zip_uv[0] = (Q_FACE_R * US, zip_uv[0, 1])       # snap ends onto the face seams
    zip_uv[-1] = (Q_FACE_L * US, Z_SH)
    zz = LineString(zip_uv)
    xing = zz.intersection(LineString([(0, Z_SB), (2 * US, Z_SB)]))
    q_c = float(xing.x)                              # zip crosses the setback seam here (U)
    i_c = int(np.searchsorted(zip_uv[:, 1], Z_SB))
    zip_lo = np.vstack([zip_uv[:i_c], [(q_c, Z_SB)]])          # z 248 -> 560
    zip_hi = np.vstack([[(q_c, Z_SB)], zip_uv[i_c:]])          # z 560 -> 631.2
    zip_lo_d, zip_hi_d = np.array(_dense(zip_lo)), np.array(_dense(zip_hi))
    ps.meta_zip = {"zip_uv": zip_uv, "q_c": q_c, "zip3": diag["zip3"], "band3": diag["band3"]}
    fR, fL, mL, mR = Q_FACE_R * US, Q_FACE_L * US, Q_FRM_L * US, Q_FRM_R * US
    z_lo = float(zip_uv[0, 1])
    kw = dict(grain=90.0, mirror=False, quantity=1)

    def dev(pid, name, edges, mat, sa, q=1, mirror=False, sub="main bag", notes="", zone=""):
        dp = develop_piece(S, edges, spacing=spacing, name=name, piece_id=pid, material_id=mat,
                           seam_allowance_mm=sa, grain=90.0, quantity=q, mirror=mirror)
        ps.dev[pid] = dp
        ps.strain[pid] = {**dp.mesh.strain_stats(), "folded": dp.mesh.folded()}
        ps.add(dp.piece, sub, notes, zone=zone)
        return dp

    sa12 = {"default": SA_BODY}
    # frame side: three tiers
    b01 = dev("B-01", "frame-side panel, lower", uv_rect_edges(1.12, 1.88, Z0, Z_SB), "challenge_ultra_200",
              sa12, notes="meat-contact laminate; 8 fairlead swells, 6 ports, hook-strap bartacks, hydration sleeve",
              zone="frame side")
    b01b = dev("B-01b", "frame-side setback band", uv_rect_edges(1.12, 1.88, Z_SB, Z_SH), "challenge_ultra_200",
               sa12, notes="30 mm head setback taken between the setback and shoulder seams (ruled band)")
    b01u = dev("B-01u", "frame-side panel, upper", uv_rect_edges(1.12, 1.88, Z_SH, Z_COLLAR), "challenge_ultra_200",
               sa12, notes="top edge into the collar seam with the hydration-sleeve top")
    # side gore (R drafted; L is the mirror)
    b03 = dev("B-03", "side gore", uv_rect_edges(1.88, 2.17, Z0, Z_COLLAR, ("bottom", "face", "top", "frm")),
              "cordura_330d_nylon66", sa12, q=2, mirror=True,
              notes="floating pocket back caught in the frame seam, roll clip, keepers, lash tabs; continuous (crease at z 560/631)")
    # outer face
    e_a = [("zip", [tuple(p) for p in zip_lo_d]), ("top", _line((q_c, Z_SB), (fR, Z_SB))),
           ("right", _line((fR, Z_SB), (fR, z_lo)))]
    b02a = dev("B-02a", "outer face, right (above zip, below setback seam)", e_a, "cordura_330d_nylon66",
               {"default": SA_BODY, "zip": SA_ZIP})
    e_c = [("bottom", _line((fR, Z_SB), (q_c, Z_SB))), ("zip", [tuple(p) for p in zip_hi_d]),
           ("top", _line((fL, Z_SH), (fR, Z_SH))), ("right", _line((fR, Z_SH), (fR, Z_SB)))]
    b02c = dev("B-02c", "outer face setback band (above zip)", e_c, "cordura_330d_nylon66",
               {"default": SA_BODY, "zip": SA_ZIP})
    zip_all = np.vstack([zip_lo_d, zip_hi_d[1:]])
    e_b = [("bottom", _line((fR, Z0), (fL, Z0))), ("left", _line((fL, Z0), (fL, Z_SH))),
           ("zip", [tuple(p) for p in zip_all[::-1]]), ("right", _line((fR, z_lo), (fR, Z0)))]
    b02b = dev("B-02b", "outer face, lower-left (below zip; band + cam-cup shard)", e_b,
               "cordura_330d_nylon66", {"default": SA_BODY, "zip": SA_ZIP},
               notes="continuous through z 560 (crease); stretch band D-01 sewn flat first")
    # upper face with two darts from the collar seam (ASSUMPTION positions: thirds of the face)
    dq = [0.17 + 0.66 * f for f in (1 / 3, 2 / 3)]
    DL, DM = 110.0, 1.0
    top = []
    xs = [fL] + [x for q in dq[::-1] for x in (q * US + DM / 2, q * US - DM / 2)] + [fR]
    e_d = [("bottom", _line((fR, Z_SH), (fL, Z_SH))), ("left", _line((fL, Z_SH), (fL, Z_COLLAR)))]
    ti = 0
    for k, q in enumerate(dq[::-1]):
        x0 = xs[2 * k]
        e_d.append((f"top_{ti}", _line((x0, Z_COLLAR), (q * US + DM / 2, Z_COLLAR))))
        ti += 1
        e_d.append((f"dart{k}_a", _line((q * US + DM / 2, Z_COLLAR), (q * US, Z_COLLAR - DL), 3.0)))
        e_d.append((f"dart{k}_b", _line((q * US, Z_COLLAR - DL), (q * US - DM / 2, Z_COLLAR), 3.0)))
    e_d.append((f"top_{ti}", _line((dq[0] * US - DM / 2, Z_COLLAR), (fR, Z_COLLAR))))
    e_d.append(("right", _line((fR, Z_COLLAR), (fR, Z_SH))))
    b02d = dev("B-02d", "outer face, upper (2 darts)", e_d, "cordura_330d_nylon66", sa12,
               notes="darts 110 mm from the collar seam take the dome above the shoulder seam")
    for k in range(2):
        b02d.piece.add_drill_hole(*b02d.to_flat([(dq[::-1][k] * US, Z_COLLAR - DL + 3)])[0], 3.0, f"dart{k} apex")

    # ---- bottom: the z 35 ring, flat (seen from outside = from below: mirror x)
    def ring_pts(q0, q1, z, n):
        qs = np.linspace(q0, q1, n)
        return S(np.column_stack([qs * US, np.full(n, z)]))
    segs = [("face", Q_FACE_R, Q_FACE_L), ("gore_L", Q_FACE_L, Q_FRM_L), ("frm", Q_FRM_L, Q_FRM_R),
            ("gore_R", Q_FRM_R, 2 + Q_FACE_R)]
    edges = []
    for nm, a, b in segs:
        P = ring_pts(a, b, Z0, max(8, int((b - a) * 300)))
        edges.append((nm, [(-float(x), float(y)) for x, y, _ in P]))
    b05 = Piece.from_edges("bag bottom", edges, seam_allowance_mm=SA_BODY, material_id="cordura_500d_nylon66",
                           piece_id="B-05", grain=90.0)
    ps.add(b05, "main bag", "flat ring at z 35; drain grommets, hinge-eye bartacks, fly pocket")
    ps.b05_map = lambda pts_uv: np.array([(-p[0], p[1]) for p in S(np.atleast_2d(pts_uv))])

    # ---- collar: straight tube = sum of the panel top lengths (seam matches by construction)
    tops = [b01u.piece.edge_length("top"), b03.piece.edge_length("top"),
            sum(b02d.piece.edge_length(f"top_{i}") for i in range(3)), b03.piece.edge_length("top")]
    perim = sum(tops)
    collar_h = (Z_FILL - Z_COLLAR) + BG.CLOSURE_MM + BG.COLLAR_HEM     # 319.8 + 150 + 25
    b06 = rect_panel("roll-top collar", perim, collar_h, 0.0, piece_id="B-06",
                     material_id="robic_100d_ripstop", seam_allowance_mm={"default": SA_BODY, "top": SA_301})
    b06.add_internal_line([(0, Z_FILL - Z_COLLAR), (perim, Z_FILL - Z_COLLAR)], "fold", "FILL LINE (85.2 L)")
    for k in range(1, 4):
        y = Z_FILL - Z_COLLAR + 50 * k
        b06.add_internal_line([(0, y), (perim, y)], "fold", f"ROLL {k}")
    ps.add(b06, "main bag", "one back seam at the frame-side centre; fill line 150 mm below the hem")
    b07 = rect_panel("roll-top stiffener hem", perim, 2 * BG.COLLAR_HEM + 20, 0.0, piece_id="B-07",
                     material_id="cordura_330d_nylon66", seam_allowance_mm=SA_301)
    b07.add_internal_line([(0, BG.COLLAR_HEM + 10), (perim, BG.COLLAR_HEM + 10)], "fold", "FOLD")
    ps.add(b07, "main bag", "folded hem, houses 2 HDPE strips B-07s; camo SH-03 on the outer half")
    b07s = rect_panel("roll-top HDPE strip", perim / 2 - 40, 20.0, 10.0, piece_id="B-07s",
                      material_id="hdpe_sheet", seam_allowance_mm=SA_LASER, quantity=2, grain=0.0)
    ps.add(b07s, "main bag", "0.8 x 20 mm HDPE (panels.yaml B-07), one per half, 20 mm clear of the back seam and the clips")

    # ---- seams: body
    E = lambda p, e: p.piece.edge(e) if isinstance(p, DevPiece) else p.edge(e)  # noqa: E731
    sm = ps.seams
    # B-03 frame edge spans the three B-01 tiers; its face edge spans B-02b / B-02a / B-02c / B-02d
    for side in ("R", "L"):
        f01 = "right" if side == "R" else "left"
        sm.append(Seam([E(b01, f01), E(b01b, f01), E(b01u, f01)], [E(b03, "frm")],
                       name=f"B-01 tiers | B-03{side} frame seam", stitch="301"))
    sm.append(Seam([E(b02b, "right"), E(b02a, "right"), E(b02c, "right"), E(b02d, "right")], [E(b03, "face")],
                   name="B-02 R edge | B-03R face seam", stitch="301"))
    sm.append(Seam([E(b02b, "left"), E(b02d, "left")], [E(b03, "face")],
                   name="B-02 L edge | B-03L face seam", stitch="301"))
    sm.append(Seam(E(b01, "top"), E(b01b, "bottom"), name="B-01 | B-01b setback seam", stitch="301"))
    sm.append(Seam(E(b01b, "top"), E(b01u, "bottom"), name="B-01b | B-01u shoulder seam", stitch="301"))
    sm.append(Seam(E(b02a, "top"), E(b02c, "bottom"), name="B-02a | B-02c setback seam", stitch="301"))
    sm.append(Seam(E(b02c, "top"), E(b02d, "bottom"), name="B-02c | B-02d shoulder seam", stitch="301"))
    sm.append(Seam([E(b02a, "zip"), E(b02c, "zip")], E(b02b, "zip"), name="diagonal zip B-02a/c | B-02b",
                   stitch="301", notes="#10 coil, both sides sewn to the tape"))
    for k in range(2):
        sm.append(Seam(E(b02d, f"dart{k}_a"), E(b02d, f"dart{k}_b"), name=f"B-02d dart {k}", stitch="301"))
    sm.append(Seam(b05.edge("frm"), E(b01, "bottom"), name="B-05 | B-01 bottom seam", stitch="301"))
    sm.append(Seam(b05.edge("gore_R"), E(b03, "bottom"), name="B-05 | B-03R bottom seam", stitch="301"))
    sm.append(Seam(b05.edge("gore_L"), E(b03, "bottom"), name="B-05 | B-03L bottom seam", stitch="301"))
    sm.append(Seam(b05.edge("face"), E(b02b, "bottom"), name="B-05 | B-02b bottom seam", stitch="301"))
    sm.append(Seam(b06.edge("bottom"), [E(b01u, "top"), E(b03, "top"), E(b02d, "top_0"), E(b02d, "top_1"),
                                        E(b02d, "top_2"), E(b03, "top")], name="B-06 collar | body tops", stitch="301"))
    sm.append(Seam(b06.edge("right"), b06.edge("left"), name="B-06 collar back seam", stitch="301"))
    sm.append(Seam(b07.edge("bottom"), b06.edge("top"), name="B-07 hem | B-06 collar top", stitch="301"))
    sm.append(Seam(b07.edge("right"), b07.edge("left"), name="B-07 hem back seam", stitch="301"))

    # ---- notches: every 50 mm on every long seam (same 3D points on both sides)
    _notch_along([b01, b03], _dense([(mR, Z0), (mR, Z_COLLAR)]), label="frame seam")
    _notch_along([b01, b01b, b01u], _dense([(mL, Z0), (mL, Z_COLLAR)]), label="frame seam L")
    _notch_along([b02b, b02a, b02c, b02d, b03], _dense([(fR, Z0), (fR, Z_COLLAR)]), label="face seam R")
    _notch_along([b02b, b02d], _dense([(fL, Z0), (fL, Z_COLLAR)]), label="face seam L")
    _notch_along([b02a, b02c, b02b], zip_all, label="zip", ends=False)
    for a, b, z in ((b01, b01b, Z_SB), (b01b, b01u, Z_SH)):
        _notch_along([a, b], _dense([(mL, z), (mR, z)]), label="tier seam")
    _notch_along([b02a, b02c], _dense([(fR, Z_SB), (q_c, Z_SB)]), label="setback seam")
    _notch_along([b02c, b02d], _dense([(fR, Z_SH), (fL, Z_SH)]), label="shoulder seam")
    # bottom ring notches: on panels and on B-05 (B-05 is the flat 3D ring itself)
    for nm, a, b in segs:
        curve = _dense([(a * US, Z0), (b * US, Z0)])
        P3 = S(np.asarray(curve))
        s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P3, axis=0), axis=1))]
        ts = np.arange(NOTCH_PITCH, s[-1] - 20, NOTCH_PITCH)
        uvs = np.column_stack([np.interp(ts, s, np.asarray(curve)[:, 0]), np.full(len(ts), Z0)])
        host = {"face": b02b, "gore_L": b03, "frm": b01, "gore_R": b03}[nm]
        if nm != "gore_L":
            for xy in host.to_flat(uvs):
                host.piece.add_notch(float(xy[0]), float(xy[1]), "slit", "bottom")
        for xy in ps.b05_map(uvs):
            b05.add_notch(float(xy[0]), float(xy[1]), "slit", "bottom")
        b05.add_notch(*ps.b05_map([(a * US, Z0)])[0], kind="v", label=f"seam {nm}")
    # collar notches: panel seam positions from the back seam (B-01 centre) + every 50 mm
    acc = 0.0
    order = [("b01u_R", b01u, 1.5, 1.88), ("b03R", b03, 1.88, 2.17), ("face", b02d, 0.17, 0.83),
             ("b03L", None, 0.83, 1.12), ("b01u_L", b01u, 1.12, 1.5)]
    for nm, dp, a, b in order:
        curve = np.asarray(_dense([(a * US, Z_COLLAR), (b * US, Z_COLLAR)]))
        L3 = _len(S(curve))
        b06.add_notch(acc, 0.0, "v" if nm != "b01u_R" else "slit", f"collar {nm} start")
        if dp is not None:
            _notch_along([dp], curve, pitch=100.0, label="collar")
        for t in np.arange(100.0, L3 - 30, 100.0):
            b06.add_notch(acc + t, 0.0, "slit", "collar")
        acc += L3
    b06.labels["back seam"] = "at the B-01 centre (frame side)"
    for p in (b06, b07):
        for f in (0.25, 0.5, 0.75):
            p.add_notch_on_edge("top", f, label="quarter")
    b07.add_notch_on_edge("bottom", 0.5, label="quarter")
    ps.body = {"b01": b01, "b01b": b01b, "b01u": b01u, "b03": b03, "b02a": b02a, "b02b": b02b,
               "b02c": b02c, "b02d": b02d, "b05": b05, "b06": b06, "b07": b07}
    return ps.body


# ---------------------------------------------------------------------------- swells + ports
def swell_cap_half(name, pid, L, qty):
    """One half of a fairlead swell: a cone from the window tip to the crest arc
    (h = 16 cos^2(pi x / 50), x = -25..25). Exactly developable; strain from the ruled unfold."""
    n = 41
    xs = np.linspace(-SWELL_W / 2, SWELL_W / 2, n)
    crest = np.column_stack([xs, SWELL_H * np.cos(np.pi * xs / SWELL_W) ** 2, np.zeros(n)])
    apex = np.tile([0.0, 0.0, -L], (n, 1))
    dev = develop_ruled_surface(apex, crest, resample=False)
    a2, b2 = dev.edge_a, dev.edge_b
    ap = tuple(map(float, a2[0]))
    cr = [tuple(map(float, p)) for p in b2]
    p = Piece.from_edges(name, [("side_a", [ap, cr[0]]), ("crest", cr), ("side_b", [cr[-1], ap])],
                         seam_allowance_mm=SA_SWELL, material_id="challenge_ultra_200", piece_id=pid,
                         quantity=qty, grain=90.0)
    crest_len = p.edge_length("crest")
    for s_ in (crest_len / 2 - PORT_LEN / 2, crest_len / 2, crest_len / 2 + PORT_LEN / 2):
        (x, y), _ = CV.point_at_length(p.edge_points("crest"), s_)
        p.add_notch(x, y, "slit", "port end / crest CL")
    p.add_notch_on_edge("side_a", 0.5, label="side mid")
    p.add_notch_on_edge("side_b", 0.5, label="side mid")
    # grain along the cone axis: apex -> crest centre
    (cx, cy), _ = CV.point_at_length(p.edge_points("crest"), crest_len / 2)
    p.grain_line = (ap, (cx, cy))
    p.grain = math.degrees(math.atan2(cy - ap[1], cx - ap[0]))
    return p, float(dev.max_strain)


def build_swells(ps: PatternSet, S: MasterSurface):
    b01 = ps.body["b01"]
    halves = {}
    for key, (zc, llo, lup) in SWELLS.items():
        for L in (llo, lup):
            if L not in halves:
                halves[L] = None
    ids = {45.0: ("B-13", "swell cap half, IM1/IM2 (45 mm)", 8), 22.0: ("B-14a", "hinge swell cap, lower (22 mm)", 2),
           68.0: ("B-14b", "hinge swell cap, upper (68 mm)", 2), 58.0: ("B-15a", "IM3 swell cap, lower (58 mm)", 2),
           32.0: ("B-15b", "IM3 swell cap, upper (32 mm)", 2)}
    caps = {}
    for L, (pid, nm, q) in ids.items():
        p, st = swell_cap_half(nm, pid, L, q)
        ps.strain[pid] = {"max_pct": 100 * st, "p99_pct": 100 * st, "p95_pct": 100 * st, "mean_pct": 100 * st,
                          "folded": 0, "method": "develop_ruled_surface (cone)"}
        ps.add(p, "main bag: fairlead swells", "set into the B-01 window; crest seam open 45 mm in the middle = meat-strap port (IM1-IM3)")
        caps[L] = p
    ps.swell_windows = []
    for key, (zc, llo, lup) in SWELLS.items():
        for side, sx in (("L", -1.0), ("R", 1.0)):
            q = S.q_of_x_frame(sx * STAY_X, zc)
            c2 = b01.to_flat([(q * US, zc)])[0]
            up = b01.to_flat([(q * US, zc + 10.0)])[0] - c2
            et = up / np.linalg.norm(up)
            eu = np.array([et[1], -et[0]])
            if np.dot(b01.to_flat([((q + 0.01) * US, zc)])[0] - c2, eu) < 0:
                eu = -eu
            tl, tu = c2 - et * llo, c2 + et * lup
            cR, cL = c2 + eu * SWELL_W / 2, c2 - eu * SWELL_W / 2
            rh = [tuple(tl), tuple(cR), tuple(tu), tuple(cL)]
            b01.piece.add_internal_line(rh, "stitch", f"swell {key}{side} seam", closed=True)
            cut = Polygon(rh).buffer(-SA_SWELL, join_style="mitre", mitre_limit=5.0)
            b01.piece.add_internal_line(list(cut.exterior.coords)[:-1], "cut_inside", f"swell {key}{side} window", closed=True)
            for pt in (tl, tu, cR, cL):
                b01.piece.add_drill_hole(*(np.asarray(pt) + (c2 - np.asarray(pt)) / np.linalg.norm(c2 - np.asarray(pt)) * 3.0), 2.0,
                                         f"swell {key}{side} corner")
            win = _virtual(f"B-01 window {key}{side}",
                           [("lo_r", [tuple(tl), tuple(cR)]), ("up_r", [tuple(cR), tuple(tu)]),
                            ("up_l", [tuple(tu), tuple(cL)]), ("lo_l", [tuple(cL), tuple(tl)])])
            for e in win.edge_names:
                win.add_notch_on_edge(e, 0.5, label="side mid")
            ps.virtual[win.name] = win
            lo, upp = caps[llo], caps[lup]
            ps.seams.append(Seam([lo.edge("side_a"), lo.edge("side_b")], [win.edge("lo_l"), win.edge("lo_r")],
                                 name=f"swell {key}{side} lower cap | window", stitch="301"))
            ps.seams.append(Seam([upp.edge("side_a"), upp.edge("side_b")], [win.edge("up_r"), win.edge("up_l")],
                                 name=f"swell {key}{side} upper cap | window", stitch="301"))
            ps.seams.append(Seam(lo.edge("crest"), upp.edge("crest"), name=f"swell {key}{side} crest seam",
                                 stitch="301", notes="IM1-IM3: open 45 mm in the middle (port), bartack both ends"
                                 if key != "hinge" else "closed"))
            ps.swell_windows.append({"station": key, "side": side, "z": zc, "q": q, "lower": llo, "upper": lup,
                                     "height": SWELL_H, "length": llo + lup, "width": SWELL_W,
                                     "centre_flat": c2.tolist()})
            # bag-hook strap bartack (IM2, IM3) on the outside of B-01, below the window
            if key in ("im2", "im3"):
                zb = zc - llo - 25.0
                for dx, dz in ((-19, -15), (19, -15), (19, 15), (-19, 15)):
                    qq = S.q_of_x_frame(sx * STAY_X + dx, zb + dz)
                    _drill(b01, [(qq * US, zb + dz)], f"{key}{side} bag-hook strap box-X")
    # port frames B-12 (Hypalon, laser-cut slot 45 x 6) over the open crest on IM1-IM3
    b12 = rect_panel("meat-strap port frame", 70.0, 24.0, 6.0, piece_id="B-12", material_id="hypalon_coated_nylon",
                     seam_allowance_mm=SA_LASER, quantity=6, grain=0.0)
    slot = [(35 - 22.5, 9.0), (35 + 22.5, 9.0), (35 + 22.5, 15.0), (35 - 22.5, 15.0)]
    b12.add_internal_line(slot, "cut_inside", "slot 45 x 6 (laser)", closed=True)
    b12.add_internal_line([(4, 12), (66, 12)], "placement", "crest seam line")
    ps.add(b12, "main bag: fairlead swells", "inside the bag, centred on the open crest of IM1-IM3 swells; edge-stitch 3 mm")
    ps.caps = caps


# ---------------------------------------------------------------------------- B-01 features
def build_frame_side_features(ps: PatternSet, S: MasterSurface):
    b = ps.body
    # hydration sleeve: x +/- 88 on the frame face, from the collar seam down 430 mm
    z_bot = Z_COLLAR - HYD_H
    tiers = [(b["b01"], Z0, Z_SB), (b["b01b"], Z_SB, Z_SH), (b["b01u"], Z_SH, Z_COLLAR)]
    side_len = {"L": 0.0, "R": 0.0}
    for dp, za, zb in tiers:
        lo, hi = max(za, z_bot), zb
        if hi <= lo:
            continue
        for side, x in (("L", -HYD_W / 2), ("R", HYD_W / 2)):
            zs = np.linspace(lo, hi, 25)
            uv = np.array([(S.q_of_x_frame(x, z) * US, z) for z in zs])
            _place(dp, uv, "stitch", f"B-09 hydration sleeve {side} edge")
            side_len[side] += _len(S(uv))
        if za <= z_bot < zb:
            xs = np.linspace(-HYD_W / 2, HYD_W / 2, 25)
            uv = np.array([(S.q_of_x_frame(x, z_bot) * US, z_bot) for x in xs])
            _place(dp, uv, "stitch", "B-09 hydration sleeve bottom")
            _drill(dp, uv[[0, -1]] + np.array([[0, 3.0], [0, 3.0]]), "B-09 sleeve corner")
            bottom_len = _len(S(uv))
    b09 = rect_panel("hydration sleeve", HYD_W, side_len["L"], 0.0, piece_id="B-09", material_id="robic_100d_ripstop",
                     seam_allowance_mm={"default": SA_301, "top": SA_BODY})
    ps.add(b09, "main bag", "sides + bottom on B-01 (flat, after the tiers are joined); top caught in the collar seam; "
                            "fits a flat bladder <= 160 mm wide (ASSUMPTION)")
    vs = _virtual("B-01 hydration placement", [("bottom", [(0, 0), (bottom_len, 0)]),
                                               ("right", [(bottom_len, 0), (bottom_len, side_len["R"])]),
                                               ("top", [(bottom_len, side_len["R"]), (0, side_len["L"])]),
                                               ("left", [(0, side_len["L"]), (0, 0)])])
    ps.virtual[vs.name] = vs
    ps.seams += [Seam(b09.edge("left"), vs.edge("left"), name="B-09 sleeve L | B-01 placement"),
                 Seam(b09.edge("right"), vs.edge("right"), name="B-09 sleeve R | B-01 placement"),
                 Seam(b09.edge("bottom"), vs.edge("bottom"), name="B-09 sleeve bottom | B-01 placement")]
    for e in ("left", "right"):
        b09.add_notch_on_edge(e, 0.5, label="mid")
    # hinge eye: 38 mm webbing caught in the B-01/B-05 seam at x +/-115, box-X through B-05
    b05 = b["b05"]
    for sx in (-1, 1):
        q = S.q_of_x_frame(sx * STAY_X, Z0)
        c = ps.b05_map([(q * US, Z0)])[0]
        for dx, dy in ((-19, 6), (19, 6), (19, 30), (-19, 30)):
            b05.add_drill_hole(c[0] + dx, c[1] + dy, 3.0, "hinge eye box-X (38 mm)")
        b05.add_notch(c[0], c[1], "v", "hinge eye CL")
        xy = b["b01"].to_flat([(q * US, Z0)])[0]
        b["b01"].piece.add_notch(float(xy[0]), float(xy[1]), "v", "hinge eye CL")
    # drain grommets (8 mm) at the frame-side corners of the floor
    for sx in (-1, 1):
        q = S.q_of_x_frame(sx * 80.0, Z0)
        c = ps.b05_map([(q * US, Z0)])[0]
        b05.add_drill_hole(c[0], c[1] + 25.0, 8.0, "drain grommet 8 mm")


# ---------------------------------------------------------------------------- band + accents
def build_band_and_accents(ps: PatternSet, S: MasterSurface):
    b = ps.body
    zip3, band3 = ps.meta_zip["zip3"], ps.meta_zip["band3"]
    dev = develop_ruled_surface(zip3, band3, n=60)
    raw = dev.to_piece("x")
    # cut 6 % short across (panels.yaml D-01: stretch 40 %, hugs flat when empty)
    A = np.asarray(raw.edge_points("a"))
    ch = (A[-1] - A[0]) / np.linalg.norm(A[-1] - A[0])
    nrm = np.array([-ch[1], ch[0]])

    def shrink(pts):
        P = np.asarray(pts, float) - A[0]
        along, across = P @ ch, P @ nrm
        return [tuple(A[0] + ch * a + nrm * c * 0.94) for a, c in zip(along, across)]
    d01 = Piece.from_edges("diagonal stretch band", [(e, shrink(raw.edge_points(e))) for e in raw.edge_names],
                           seam_allowance_mm={"default": SA_301, "a": 0.0}, material_id="poly_spandex_stretch_woven_printable",
                           piece_id="D-01", grain=0.0)
    ps.strain["D-01"] = {"max_pct": 100 * dev.max_strain, "p99_pct": 100 * dev.max_strain, "p95_pct": 0.0,
                         "mean_pct": 0.0, "folded": 0, "method": "develop_ruled_surface"}
    for e in ("a", "b"):
        for f in (0.25, 0.5, 0.75):
            d01.add_notch_on_edge(e, f, label="band quarter")
    ps.add(d01, "main bag", "mouth (edge a) bound with SH-02, lies over the zip as the storm flap; edge b + ends on B-02b")
    # band lower edge + ends as placement lines on B-02b
    b02b = b["b02b"]
    band_uv = np.array([(S.q_of_point(p) * US, p[2]) for p in band3])
    xy = _place(b02b, band_uv, "stitch", "D-01 band lower edge")
    for f in (0.25, 0.5, 0.75):
        (x, y), _ = CV.point_at_length([tuple(p) for p in xy], f * _len(xy))
        b02b.piece.add_drill_hole(x, y + 3.0, 2.0, "band quarter")
    vb = _virtual("B-02b band placement", [("b", [tuple(p) for p in xy[::-1]]), ("x", [tuple(xy[0]), tuple(xy[-1])])])
    ps.virtual[vb.name] = vb
    ease = d01.edge_length("b") - vb.edge_length("b")
    ps.seams.append(Seam(d01.edge("b"), vb.edge("b"), ease_mm=round(ease, 2), stitch="301",
                         name="D-01 band lower edge | B-02b placement", notes="ease = the 6 % across-shrink, stretched on"))
    # zip-end drill holes + zip storm strip
    for dp in (b["b02a"], b["b02b"]):
        z = ps.meta_zip["zip_uv"]
        _drill(dp, [z[0] + (8.0, 6.0)], "zip end (stop)")
    _drill(b["b02c"], [ps.meta_zip["zip_uv"][-1] + (-8.0, -6.0)], "zip end (stop)")
    zip_len = b["b02b"].piece.edge_length("zip")
    b08 = rect_panel("diagonal zip storm strip", 30.0, zip_len + 40, 0.0, piece_id="B-08",
                     material_id="cordura_330d_nylon66", seam_allowance_mm=8.0)
    for f in (0.25, 0.5, 0.75):
        b08.add_notch_on_edge("left", f, label="quarter")
    ps.add(b08, "main bag", "under-zip backing, 20 mm past each zip end")
    ps.seams.append(Seam(b08.edge("left"), b["b02b"].piece.edge("zip"), ease_mm=40.0, stitch="301",
                         name="B-08 strip | zip seam (20 mm overhang each end)"))
    # camo accents (owner base camo on 630D printable)
    shard = "polyester_ht_630d_printable"
    sh02 = rect_panel("band mouth binding (camo)", 32.0, d01.edge_length("a") + 40, 0.0, piece_id="SH-02",
                      material_id=shard, seam_allowance_mm=0.0, grain=45.0)
    sh02.add_internal_line([(16, 0), (16, sh02.edge_length("left"))], "fold", "FOLD to 16 mm")
    ps.add(sh02, "accents", "bias-cut binding; it is the storm flap edge")
    ps.seams.append(Seam(sh02.edge("left"), d01.edge("a"), ease_mm=40.0, name="SH-02 binding | D-01 mouth (20 mm ends)"))
    sh03 = rect_panel("roll-top band (camo)", b["b07"].edge_length("bottom") / 2, 60.0, 0.0, piece_id="SH-03",
                      material_id=shard, seam_allowance_mm=0.0, grain=0.0)
    ps.add(sh03, "accents", "overlay on B-07, outer-face half; laser-cut raw edge, edge-stitched")
    # SH-01: lower-corner shard = bottom of B-03 under an angular line (caught in 3 seams)
    b03 = b["b03"].piece
    poly = b03.seam_polygon()
    x0, y0, x1, y1 = poly.bounds
    cutter = Polygon([(x0 - 50, y0 - 50), (x1 + 50, y0 - 50), (x1 + 50, y0 + 70), (0.5 * (x0 + x1), y0 + 150),
                      (x0 - 50, y0 + 110)])
    sh01 = Piece("lower-corner shard", list(poly.intersection(cutter).exterior.coords)[:-1], grain=90.0,
                 seam_allowance_mm=SA_BODY, material_id=shard, piece_id="SH-01", quantity=2, mirror=True)
    sh01.labels["free edge"] = "turn under 8 mm + topstitch; others basted in the gore seams"
    ps.add(sh01, "accents", "overlay on B-03 bottom; cut line = gore cut line on the caught edges")
    # SH-04 cam-cup shard: bottom-right corner of B-02b
    pb = b["b02b"].piece.seam_polygon()
    bx0, by0, bx1, by1 = pb.bounds
    cut4 = Polygon([(bx0 - 50, by0 - 50), (bx0 + 170, by0 - 50), (bx0 + 150, by0 + 90), (bx0 + 60, by0 + 150),
                    (bx0 - 50, by0 + 130)])
    # B-02b right edge (wearer's right) is the flat LEFT (u = q increasing to the right); cam cup sits there
    sh04 = Piece("cam-cup shard", list(pb.intersection(cut4).exterior.coords)[:-1], grain=90.0, seam_allowance_mm=SA_BODY,
                 material_id=shard, piece_id="SH-04")
    ps.add(sh04, "accents", "overlay on B-02b lower corner at the band's low end (bow cam, rifle butt)")
    # lash tabs B-11: 2 per gore (muzzle keepers / antler) + 4 on the upper face
    b11 = rect_panel("lash tab", 30.0, 50.0, 4.0, piece_id="B-11", material_id="hypalon_coated_nylon",
                     seam_allowance_mm=SA_LASER, quantity=8)
    b11.add_internal_line([(2.5, 10), (27.5, 10), (27.5, 15), (2.5, 15)], "cut_inside", "slot 25 x 5", closed=True)
    ps.add(b11, "main bag", "laser-cut; box-stitch the upper 25 mm")
    qg = (Q_FRM_R + 2 + Q_FACE_R) / 2
    for z in (660.0, 740.0):
        _drill(b["b03"], [(qg * US, z)], "lash tab B-11 centre")
    for q in (0.30, 0.70):
        for z in (680.0, 750.0):
            _drill(b["b02d"], [(q * US, z)], "lash tab B-11 centre")
    # haul-wrap keepers (25 mm, 80 mm) on the gores (ASSUMPTION: z 200/400/600 at gore centre)
    for z in (200.0, 400.0, 600.0):
        for dz in (-12.0, 12.0):
            _drill(b["b03"], [(qg * US, z + dz)], "wrap keeper bartack")
    # roll-top clip strap anchor (25 mm) on the gore at z 700
    for dz in (-10, 10):
        _drill(b["b03"], [(qg * US, 700.0 + dz)], "roll-clip strap bartack")
    # hose port on the gore top (both sides), 40 mm below the collar seam
    _drill(b["b03"], [(qg * US, Z_COLLAR - 40)], "hose port (12 mm bound eyelet)")


# ---------------------------------------------------------------------------- pockets
def build_pockets(ps: PatternSet, S: MasterSurface):
    b03 = ps.body["b03"]
    # P-03 floating back: frame-side edge caught in the B-01/B-03 seam from z 90 to 450
    zb, zt = float(GEOM["side_pockets"]["position"]["z_bottom"]), \
        float(GEOM["side_pockets"]["position"]["z_bottom"]) + float(GEOM["side_pockets"]["height"])
    wb, wt = float(GEOM["side_pockets"]["face_bottom_w"]), float(GEOM["side_pockets"]["face_top_w"])
    edge_uv = np.asarray(_dense([(Q_FRM_R * US, zb), (Q_FRM_R * US, zt)]))
    fe = b03.to_flat(edge_uv)
    d = (fe[-1] - fe[0]) / np.linalg.norm(fe[-1] - fe[0])
    n = np.array([d[1], -d[0]])
    if np.dot(b03.to_flat([((Q_FRM_R + 0.05) * US, zb)])[0] - fe[0], n) < 0:
        n = -n
    frm = [tuple(p) for p in fe]
    br = tuple(fe[0] + n * wb)
    tr = tuple(fe[-1] + n * wt)
    edges = [("frm", frm), ("top", [frm[-1], tr]), ("face", [tr, br]), ("bottom", [br, frm[0]])]
    p03 = Piece.from_edges("side pocket floating back", edges, seam_allowance_mm={"default": SA_301, "frm": SA_BODY},
                           material_id="robic_100d_ripstop", piece_id="P-03", quantity=2, mirror=True, grain=90.0,
                           grain_line=(tuple(fe[0] + n * 40 + d * 60), tuple(fe[0] + n * 40 + d * 300)))
    p01 = Piece.from_edges("side pocket face", edges, seam_allowance_mm={"default": SA_301, "frm": SA_BODY, "top": 20.0},
                           material_id="ultragrid_210d_uhmwpe_ripstop", piece_id="P-01", quantity=2, mirror=True,
                           grain=90.0, grain_line=p03.grain_line)
    p01.add_internal_line([tr, tuple(np.asarray(frm[-1]))], "fold", "HEM FOLD (3 mm shock cord)")
    p01.add_drill_hole(*(np.asarray(br) + (np.asarray(frm[0]) - np.asarray(br)) * 0.5 + d * 10), 5.0, "drain eyelet")
    ps.add(p03, "pockets", "frame-side edge basted onto the B-03 frame edge (z 90-450) and sewn in that seam; bottom tacked across the gore")
    ps.add(p01, "pockets", "3 mm shock-cord hem; drain eyelet")
    g_len = p01.edge_length("bottom") + p01.edge_length("face") + p01.edge_length("top")
    p02 = rect_panel("side pocket gusset", g_len, float(GEOM["side_pockets"]["bellows"]), 0.0, piece_id="P-02",
                     material_id="ultragrid_210d_uhmwpe_ripstop", seam_allowance_mm=SA_301, quantity=2, grain=0.0)
    a = p01.edge_length("top")
    for x in (a, a + p01.edge_length("face")):
        p02.add_notch(x, 0.0, "v", "corner")
        p02.add_notch(x, p02.edge_length("right"), "v", "corner")
    ps.add(p02, "pockets", "U-strip; bellows 50 mm")
    ps.seams += [Seam(p02.edge("bottom"), [p01.edge("top"), p01.edge("face"), p01.edge("bottom")],
                      name="P-02 gusset | P-01 face"),
                 Seam(p02.edge("top"), [p03.edge("top"), p03.edge("face"), p03.edge("bottom")],
                      name="P-02 gusset | P-03 back"),
                 Seam(p03.edge("frm"), b03.piece.edge("frm"), ease_mm=p03.edge_length("frm") - b03.piece.edge_length("frm"),
                      name="P-03 frame edge | B-03 frame edge (z 90-450 of it)", notes="partial-edge placement")]
    # notch the pocket ends on the gore frame edge
    for xy in b03.to_flat([(Q_FRM_R * US, zb), (Q_FRM_R * US, zt)]):
        b03.piece.add_notch(float(xy[0]), float(xy[1]), "v", "P-03 end")
        p03.add_notch(float(xy[0]), float(xy[1]), "v", "P-03 end")
        p01.add_notch(float(xy[0]), float(xy[1]), "v", "P-01 end")
    # fly pocket + under-strap channels (bottom)
    f02 = rect_panel("fly pocket", 230.0, 150.0, 20.0, piece_id="F-02", material_id="cordura_330d_nylon66",
                     seam_allowance_mm={"default": SA_301, "top": SA_ZIP})
    d_floor = 190.0
    for k, f in enumerate(CHANNEL_Y):
        yc = 150.0 - (f * d_floor - 12.0)   # pocket y=150 is the frame-side edge (pocket aft edge = zip)
        f02.add_internal_line([(20, yc - CHANNEL_W / 2), (210, yc - CHANNEL_W / 2)], "stitch", f"B-16 channel {k + 1} edge")
        f02.add_internal_line([(20, yc + CHANNEL_W / 2), (210, yc + CHANNEL_W / 2)], "stitch", f"B-16 channel {k + 1} edge")
    for f in (0.25, 0.5, 0.75):
        f02.add_notch_on_edge("bottom", f, label="quarter")
    ps.add(f02, "fly", "BASE pocket under B-05, #5 coil zip along the floor's aft edge; holds the fly; "
                       "carries the two under-strap channels on its face")
    b16 = rect_panel("under-strap floor channel", 190.0, CHANNEL_W, 0.0, piece_id="B-16",
                     material_id="cordura_500d_nylon66", seam_allowance_mm={"default": SA_301, "left": 15.0, "right": 15.0},
                     quantity=2, grain=0.0)
    b16.labels["ends"] = "turn 15 mm, ends OPEN (strap passes through)"
    ps.add(b16, "main bag", "open channel for the 38 mm under-strap (US1/US2); topstitched on F-02 face (ASSUMPTION position)")
    for k in (1, 2):
        vc = _virtual(f"F-02 channel {k}", [("a", [(0, 0), (190, 0)]), ("b", [(190, 0), (190, 1)]),
                                             ("c", [(190, 1), (0, 1)]), ("d", [(0, 1), (0, 0)])])
        ps.virtual[vc.name] = vc
        ps.seams.append(Seam(b16.edge("bottom"), vc.edge("a"), name=f"B-16 channel {k} | F-02 placement"))


# ---------------------------------------------------------------------------- rain fly
def build_fly(ps: PatternSet, spacing=16.0):
    # ASSUMPTION: 10 % ring ease over pockets + wraps (panels.yaml F-01 used x1.12 area). The fly drapes
    # over the setback, so its hull is the loft without the 30 mm step (no creases); it is split at the
    # T_PEAK depth kink (z 632 ~ the shoulder seam) like the bag face.
    SF = MasterSurface(scale=1.10, setback=False)
    mat = "silicone_coated_poly_ripstop_40d"
    q0s, q1s = Q_FACE_L, 1.0 + 0.20      # side: whole gore + 0.08 of the frame half (wrap onto the frame side)
    out = {}
    for pid, nm, edges, q, mir in (
            ("F-01a", "rain fly face, lower", uv_rect_edges(Q_FACE_R, Q_FACE_L, Z0, Z_PEAK), 1, False),
            ("F-01c", "rain fly face, upper", uv_rect_edges(Q_FACE_R, Q_FACE_L, Z_PEAK, Z_COLLAR), 1, False),
            ("F-01b", "rain fly side", uv_rect_edges(q0s, q1s, Z0, Z_COLLAR, ("bottom", "frm", "top", "face")), 2, True)):
        if pid == "F-01b":
            edges = [(n, p) for n, p in edges]
            edges = [edges[0], ("face_far", edges[1][1]), edges[2], ("face", edges[3][1])]
            edges = [("bottom", edges[0][1]), ("frm", edges[1][1]), ("top", edges[2][1]), ("face", edges[3][1])]
        dp = develop_piece(SF, edges, spacing=spacing, name=nm, piece_id=pid, material_id=mat,
                           seam_allowance_mm={"default": SA_301, "bottom": 20.0, "top": 20.0, "frm": 20.0} if pid == "F-01b"
                           else {"default": SA_301, "bottom": 20.0, "top": 20.0},
                           grain=90.0, quantity=q, mirror=mir)
        ps.dev[pid] = dp
        ps.strain[pid] = {**dp.mesh.strain_stats(), "folded": dp.mesh.folded()}
        out[pid] = dp
    fa, fc, fb = out["F-01a"], out["F-01c"], out["F-01b"]
    for dp, note in ((fa, "elastic channel hem along the bottom"), (fc, "top hem 20 mm: drawcord gathers over the roll"),
                     (fb, "20 mm channel hems with 6 mm elastic on bottom/top/frame edge")):
        ps.add(dp.piece, "fly", note)
    ps.seams += [Seam([fa.piece.edge("right"), fc.piece.edge("right")], fb.piece.edge("face"), name="F-01 face R | F-01b side"),
                 Seam([fa.piece.edge("left"), fc.piece.edge("left")], fb.piece.edge("face"), name="F-01 face L | F-01b side"),
                 Seam(fa.piece.edge("top"), fc.piece.edge("bottom"), name="F-01a | F-01c shoulder seam")]
    _notch_along([fa, fc, fb], _dense([(Q_FACE_L * US, Z0), (Q_FACE_L * US, Z_COLLAR)]), pitch=100.0, label="fly seam")
    _notch_along([fa, fc], _dense([(Q_FACE_R * US, Z0), (Q_FACE_R * US, Z_COLLAR)]), pitch=100.0, label="fly seam R")
    _notch_along([fa, fc], _dense([(Q_FACE_R * US, Z_PEAK), (Q_FACE_L * US, Z_PEAK)]), pitch=100.0, label="shoulder")
    fa.piece.add_drill_hole(*fa.to_flat([(0.5 * US, Z0 + 30)])[0], 5.0, "tether grommet")


# ---------------------------------------------------------------------------- hipbelt (graded)
def wing_piece(name, pid, L, mat, inset=0.0, sa=SA_301, kind="fabric"):
    """Hipbelt wing: root (x=0) 140 tall, tip (x=L) 95 tall, symmetric taper, tip corners r 20.
    Grade points ``ta``/``ba`` (start of the tip arcs) and the tip vertices move with size."""
    H0, H1, R = 140.0 - 2 * inset, 95.0 - 2 * inset, max(20.0 - inset, 4.0)
    L = L - inset
    y_top = lambda x: 140.0 - inset - (22.5 * x / L)          # noqa: E731
    y_bot = lambda x: inset + (22.5 * x / L)                  # noqa: E731
    rb, rt = (inset, y_bot(inset)), (inset, y_top(inset))
    c_t, c_b = (L - R, y_top(L - R) - R), (L - R, y_bot(L - R) + R)
    tipt = [(c_t[0] + R * math.cos(math.radians(a)), c_t[1] + R * math.sin(math.radians(a))) for a in np.linspace(90, 0, 6)]
    tipb = [(c_b[0] + R * math.cos(math.radians(a)), c_b[1] + R * math.sin(math.radians(a))) for a in np.linspace(0, -90, 6)]
    edges = [("root", [rt, rb]), ("bottom", [rb, tipb[-1]]), ("tip", list(tipb[::-1]) + list(tipt[::-1])),
             ("top", [tipt[0], rt])]
    pts = {"rt": rt, "rb": rb}
    for i, p in enumerate(tipb[::-1]):
        pts[f"tb{i}"] = p
    for i, p in enumerate(tipt[::-1]):
        pts[f"tt{i}"] = p
    p = Piece.from_edges(name, edges, seam_allowance_mm=sa, material_id=mat, piece_id=pid, quantity=2,
                         mirror=True, grain=0.0, points=pts)
    return p


def wing_rules(p: Piece):
    pts = {k: {s: (WING_LEN[s] - WING_LEN["M"], 0.0) for s in HIPBELT_SIZES if s != "M"}
           for k in p.points if k.startswith(("tb", "tt"))}
    pts.update({k: {s: (0.0, 0.0) for s in HIPBELT_SIZES if s != "M"} for k in ("rt", "rb")})
    return {"sizes": HIPBELT_SIZES, "base": "M", "points": pts, "default": "interpolate"}


HP_DX = {"S": -37.0, "L": 30.0, "XL": 30.0}   # pocket width grade: wing - 70 mm, capped at 180 (ASSUMPTION)


def build_hipbelt(ps: PatternSet):
    L = WING_LEN["M"]
    specs = [("H-01", "hipbelt wing outer shell", "cordura_330d_nylon66", 0.0, SA_301),
             ("H-02", "hipbelt wing body face", "spacer_mesh_3d", 0.0, SA_301),
             ("H-03", "hipbelt wing load foam", "eva_foam_45c", 8.0, SA_LASER),
             ("H-04", "hipbelt wing comfort foam", "eva_foam_30c", 6.0, SA_LASER),
             ("H-05", "hipbelt wing stiffener", "hdpe_sheet", 12.0, SA_LASER)]
    base = {}
    for pid, nm, mat, inset, sa in specs:
        p = wing_piece(nm, pid, L, mat, inset, sa)
        base[pid] = p
        notes = {"H-01": "binding on top/bottom/tip; pocket + rifle tabs + shard sewn flat first",
                 "H-03": "die-cut, inset 8 mm", "H-04": "die-cut, inset 6 mm",
                 "H-05": "1.0 mm HDPE, routed, carries load to the iliac crest"}.get(pid, "")
        ps.add(p, "hipbelt", notes)
    h01 = base["H-01"]
    # marks on the shell (M), graded with the piece
    h01.add_drill_hole(L - 35, 70 - 25 + 4, 3.0, "50 mm hipbelt strap box-X")
    h01.add_drill_hole(L - 35, 70 + 25 - 4, 3.0, "50 mm hipbelt strap box-X")
    h01.add_drill_hole(L - 75, 70 - 25 + 4, 3.0, "50 mm hipbelt strap box-X")
    h01.add_drill_hole(L - 75, 70 + 25 - 4, 3.0, "50 mm hipbelt strap box-X")
    h01.add_drill_hole(25, 125, 3.0, "hip stabilizer 25 mm")
    for x in (30.0, 90.0):
        h01.add_drill_hole(x, 8.0, 3.0, "R-03 rifle-boot tab")
    h01.add_notch_on_edge("root", 0.5, label="root CL")
    for e in ("top", "bottom"):
        h01.add_notch_on_edge(e, 0.5, label="mid")
    base["H-02"].add_notch_on_edge("root", 0.5, label="root CL")
    for e in ("top", "bottom"):
        base["H-02"].add_notch_on_edge(e, 0.5, label="mid")
    for pid, p in base.items():
        ps.graded[pid] = grade(p, wing_rules(p))
    # pocket on the wing (graded width), shard at the tip (one size)
    hp_w = 150.0
    hpf = tapered_panel("hipbelt pocket face", hp_w, hp_w - 30, 95.0, align="left", material_id="cordura_330d_nylon66",
                        piece_id="HP-01", quantity=2, mirror=True, seam_allowance_mm={"default": 8.0, "top": SA_ZIP})
    hpf.add_notch_on_edge("bottom", 0.5, label="mid")
    ps.add(hpf, "hipbelt", "#8 coil zip along the top; graded with the wing (S 113, M 150, L/XL 180 wide)")
    hp_rules = {"sizes": HIPBELT_SIZES, "base": "M", "default": "interpolate",
                "points": {"br": {s: (d, 0.0) for s, d in HP_DX.items()}, "tr": {s: (d, 0.0) for s, d in HP_DX.items()},
                           "bl": {s: (0.0, 0.0) for s in HP_DX}, "tl": {s: (0.0, 0.0) for s in HP_DX}}}
    ps.graded["HP-01"] = grade(hpf, hp_rules)
    g = hpf.edge_length("left") + hpf.edge_length("bottom") + hpf.edge_length("right")
    hpg = rect_panel("hipbelt pocket gusset", g, 40.0, 0.0, material_id="cordura_330d_nylon66", piece_id="HP-02",
                     quantity=2, seam_allowance_mm=8.0, grain=0.0)
    ps.add(hpg, "hipbelt", "U gusset, 40 mm deep")
    ps.graded["HP-02"] = grade(hpg, {"sizes": HIPBELT_SIZES, "base": "M", "default": "interpolate",
                                     "points": {"br": {s: (d, 0.0) for s, d in HP_DX.items()},
                                                "tr": {s: (d, 0.0) for s, d in HP_DX.items()},
                                                "bl": {s: (0.0, 0.0) for s in HP_DX}, "tl": {s: (0.0, 0.0) for s in HP_DX}}})
    sh05 = Piece.from_edges("hipbelt wing-tip shard", [(e, h01.edge_points(e)) for e in h01.edge_names],
                            seam_allowance_mm=SA_301)
    poly = sh05.seam_polygon().intersection(Polygon([(L - 60, -10), (L + 30, -10), (L + 30, 150), (L - 75, 150)]))
    sh05 = Piece("hipbelt wing-tip shard", list(poly.exterior.coords)[:-1], grain=0.0, seam_allowance_mm=SA_301,
                 material_id="polyester_ht_630d_printable", piece_id="SH-05", quantity=2, mirror=True)
    sh05.labels["note"] = "same all sizes; tip edges caught in the binding, inner edge turned 8 mm"
    ps.add(sh05, "accents", "overlay on H-01 tip, same shape every size (tip moves rigidly in the grade)")
    r03 = rect_panel("rifle-boot mount tab", 40.0, 60.0, 4.0, piece_id="R-03", material_id="hypalon_coated_nylon",
                     seam_allowance_mm=SA_LASER, quantity=4)
    r03.add_internal_line([(7.5, 40), (32.5, 40), (32.5, 45), (7.5, 45)], "cut_inside", "slot 25 x 5", closed=True)
    ps.add(r03, "hipbelt", "2 per wing, caught in the bottom binding")
    # lumbar centre (one size): square corners where the wings join
    for pid, nm, mat, kind in (("H-06", "lumbar pad shell", "cordura_330d_nylon66", "f"),
                               ("H-07", "lumbar pad face (grippy)", "spacer_mesh_3d", "f")):
        p = rect_panel(nm, float(GEOM["hipbelt"]["lumbar_centre_w"]) + 20.0, 140.0, 0.0, material_id=mat, piece_id=pid,
                       seam_allowance_mm=SA_301)
        p.add_notch_on_edge("left", 0.5, label="wing root CL")
        p.add_notch_on_edge("right", 0.5, label="wing root CL")
        p.add_notch_on_edge("top", 0.5, label="CB")
        p.add_notch_on_edge("bottom", 0.5, label="CB")
        if pid == "H-06":
            p.add_drill_hole(80.0, 70.0, 6.0, "Ti hip-pivot CL (geometry.yaml hipbelt_pivot)")
            for dx, dy in ((-35, -25), (35, -25), (35, 25), (-35, 25)):
                p.add_drill_hole(80 + dx, 70 + dy, 3.0, "centre-plate bolt (ASSUMPTION 70 x 50)")
            p.add_internal_line([(15, 15), (145, 15), (145, 115), (15, 115)], "stitch", "H-10 wedge sleeve (3 sides)")
        ps.add(p, "hipbelt", "wings sew to both side edges; pivot at the centre")
    h08 = rect_panel("lumbar pad foam, stage 1", 148.0, 128.0, 20.0, material_id="eva_foam_45c", piece_id="H-08",
                     seam_allowance_mm=SA_LASER)
    h09 = rect_panel("lumbar stage-2 wedge insert (removable)", 130.0, 90.0, 25.0, material_id="eva_foam_45c", piece_id="H-09",
                     seam_allowance_mm=SA_LASER)
    h10 = rect_panel("lumbar wedge sleeve", 130.0, 100.0, 0.0, material_id="robic_210d_ripstop", piece_id="H-10",
                     seam_allowance_mm={"default": SA_301, "top": 15.0})
    ps.add(h08, "hipbelt", "8 mm EVA 45C, die-cut")
    ps.add(h09, "hipbelt", "8 mm EVA 45C wedge, slides into H-10 for > 65 lb loads")
    ps.add(h10, "hipbelt", "sewn to the inside of H-06 on 3 sides, top open (hemmed)")
    vsl = _virtual("H-06 wedge sleeve placement", [("bottom", [(15, 15), (145, 15)]), ("right", [(145, 15), (145, 115)]),
                                                   ("top", [(145, 115), (15, 115)]), ("left", [(15, 115), (15, 15)])])
    ps.virtual[vsl.name] = vsl
    ps.seams += [Seam([h10.edge("left"), h10.edge("bottom"), h10.edge("right")],
                      [vsl.edge("left"), vsl.edge("bottom"), vsl.edge("right")], name="H-10 sleeve | H-06 placement")]
    # graded seam sets
    for s in HIPBELT_SIZES:
        g1, g2 = ps.graded["H-01"][s], ps.graded["H-02"][s]
        hp, hg = ps.graded["HP-01"][s], ps.graded["HP-02"][s]
        lum, lumf = ps.pieces["H-06"], ps.pieces["H-07"]
        ps.graded_seams[s] = [
            Seam([g1.edge("top"), g1.edge("tip"), g1.edge("bottom")], [g2.edge("top"), g2.edge("tip"), g2.edge("bottom")],
                 name=f"H-01 | H-02 wing perimeter [{s}]", stitch="301", notes="then bound"),
            Seam(g1.edge("root"), lum.edge("right"), name=f"H-01 root | H-06 side [{s}]"),
            Seam(g2.edge("root"), lumf.edge("right"), name=f"H-02 root | H-07 side [{s}]"),
            Seam(hg.edge("bottom"), [hp.edge("left"), hp.edge("bottom"), hp.edge("right")], name=f"HP-02 | HP-01 [{s}]")]
    ps.seams += [Seam(ps.pieces["H-06"].edge(e), ps.pieces["H-07"].edge(e), name=f"H-06 | H-07 {e}")
                 for e in ("top", "bottom")]


# ---------------------------------------------------------------------------- harness (J/S)
def strap_piece(name, pid, mat, inset=0.0, sa=SA_301):
    """Shoulder strap, drafted as the J strap (graded to S by point rules)."""
    L, wt, wb, n = float(GEOM["harness"]["padded_length"]), float(GEOM["harness"]["width_top"]), \
        float(GEOM["harness"]["width_bottom"]), 12
    left, right, pts = [], [], {}
    for i in range(n + 1):
        z = inset + (L - 2 * inset) * i / n
        w = (wt + (wb - wt) * i / n) - 2 * inset
        off = 18.0 * math.sin(math.pi * i / n * 0.5)
        y = L - z
        left.append((off - w / 2, y))
        right.append((off + w / 2, y))
    for i, (l, r) in enumerate(zip(left, right)):
        pts[f"l{i}"], pts[f"r{i}"] = l, r
    edges = [("outer", left), ("bottom", [left[-1], right[-1]]), ("inner", right[::-1]), ("top", [right[0], left[0]])]
    p = Piece.from_edges(name, edges, seam_allowance_mm=sa, material_id=mat, piece_id=pid, quantity=2, mirror=True,
                         grain=90.0, points=pts)
    return p


def strap_rules(p: Piece):
    n = 12
    pts = {}
    for i in range(n + 1):
        d = 35.0 * math.sin(math.pi * i / n) - 18.0 * math.sin(math.pi * i / n * 0.5)   # panels.yaml S vs J offsets
        pts[f"l{i}"] = {"S": (d, 0.0)}
        pts[f"r{i}"] = {"S": (d, 0.0)}
    return {"sizes": STRAP_SIZES, "base": "J", "points": pts}


def build_harness(ps: PatternSet):
    specs = [("HS-1", "shoulder strap shell", "cordura_330d_nylon66", 0.0, SA_301),
             ("HS-2", "shoulder strap face", "spacer_mesh_3d", 0.0, SA_301),
             ("HS-3", "shoulder strap load foam", "eva_foam_45c", 4.0, SA_LASER),
             ("HS-4", "shoulder strap comfort foam", "eva_foam_perforated", 4.0, SA_LASER)]
    for pid, nm, mat, inset, sa in specs:
        p = strap_piece(nm, pid, mat, inset, sa)
        if pid in ("HS-1", "HS-2"):
            p.add_notch_on_edge("top", 0.5, label="CL")
            p.add_notch_on_edge("bottom", 0.5, label="CL")
            for f in (0.25, 0.5, 0.75):
                p.add_notch_on_edge("inner", f, label="inner")
                p.add_notch_on_edge("outer", f, label="outer")
        if pid == "HS-1":
            for dx, dy in ((-12, 400), (12, 400), (-12, 420), (12, 420)):
                p.add_drill_hole(dx, dy, 3.0, "load-lifter 25 mm box-X")
            pr = p.edge_points("inner")
            p.add_internal_line([(x - 6, y) for x, y in pr if 160 <= y <= 280], "placement", "POM sternum rail (120 travel)")
            for dx in (-12, 12):
                p.add_drill_hole(dx + 14, 15, 3.0, "25 mm lower webbing bartack")
        ps.add(p, "harness", "J (default) and S graded; L/R pair", )
        g = grade(p, strap_rules(p))
        for s, gp in g.items():
            gp.piece_id = pid.replace("HS-", f"HS-{s}")
        ps.graded[pid] = g
    for s in STRAP_SIZES:
        a, b = ps.graded["HS-1"][s], ps.graded["HS-2"][s]
        ps.graded_seams.setdefault(f"strap-{s}", []).append(
            Seam([a.edge(e) for e in ("outer", "bottom", "inner", "top")], [b.edge(e) for e in ("outer", "bottom", "inner", "top")],
                 name=f"HS shell | face perimeter [{s}]", stitch="301", notes="then bound"))
    hs05 = rect_panel("yoke cover", 260.0, 120.0, 30.0, material_id="cordura_330d_nylon66", piece_id="HS-05", quantity=2,
                      seam_allowance_mm=SA_301)
    for f in (0.25, 0.5, 0.75):
        hs05.add_notch_on_edge("top", f, label="quarter")
        hs05.add_notch_on_edge("bottom", f, label="quarter")
    ps.add(hs05, "harness", "sandwich over the yoke plate (yoke redesign pending: RESUME.md next #1)")
    ps.seams.append(Seam([hs05.edge(e) for e in hs05.edge_names], [hs05.edge(e) for e in hs05.edge_names],
                         name="HS-05 yoke cover pair perimeter"))


# ---------------------------------------------------------------------------- back panel
def build_back_panel(ps: PatternSet):
    W, H = 350.0, 440.0        # covers both stay rails (x +/-115, 100 wide) + the window
    bp01 = rect_panel("back panel mesh", W, H, 30.0, material_id="spacer_mesh_3d", piece_id="BP-01", seam_allowance_mm=SA_301)
    cx = W / 2
    for sx in (-1, 1):
        x0 = cx + sx * STAY_X - 60
        bp01.add_internal_line([(x0, 10), (x0 + 120, 10), (x0 + 120, 430), (x0, 430)], "stitch",
                               "BP-05 rail sleeve (3 sides, top open)", closed=False)
        bp01.add_internal_line([(cx + sx * STAY_X, 20), (cx + sx * STAY_X, 420)], "placement", "stay CL")
    for x, y in ((20, 20), (W - 20, 20), (W - 20, H - 20), (20, H - 20)):
        bp01.add_drill_hole(x, y, 3.0, "stay-clip loop tab (ASSUMPTION)")
    for f in (0.25, 0.5, 0.75):
        bp01.add_notch_on_edge("top", f, label="quarter")
        bp01.add_notch_on_edge("bottom", f, label="quarter")
    ps.add(bp01, "back panel", "open spacer mesh over the rails and the window air gap (analysis/back_comfort.md); bound edge")
    bp05 = rect_panel("stay-rail sleeve back", 120.0, 420.0, 0.0, material_id="robic_210d_ripstop", piece_id="BP-05",
                      quantity=2, seam_allowance_mm={"default": SA_301, "top": 15.0})
    ps.add(bp05, "back panel", "pocket for the 10 mm XLPE rail; rail drops in from the top")
    v = _virtual("BP-01 rail sleeve placement", [("bottom", [(0, 0), (120, 0)]), ("right", [(120, 0), (120, 420)]),
                                                 ("top", [(120, 420), (0, 420)]), ("left", [(0, 420), (0, 0)])])
    ps.virtual[v.name] = v
    ps.seams.append(Seam([bp05.edge("left"), bp05.edge("bottom"), bp05.edge("right")],
                         [v.edge("left"), v.edge("bottom"), v.edge("right")], name="BP-05 sleeve | BP-01 placement"))
    bp02 = rect_panel("stay-rail foam", 100.0, 420.0, 30.0, material_id="xlpe_foam", piece_id="BP-02", quantity=2,
                      seam_allowance_mm=SA_LASER)
    ps.add(bp02, "back panel", "10 mm XLPE, die-cut (analysis/back_comfort.md: 100 x 420 x 10)")
    bp03 = rect_panel("upper back pad face (crown)", 210.0, 180.0, 30.0, material_id="spacer_mesh_3d", piece_id="BP-03",
                      seam_allowance_mm=SA_301)
    bp07 = rect_panel("upper back pad back", 210.0, 180.0, 30.0, material_id="robic_210d_ripstop", piece_id="BP-07",
                      seam_allowance_mm=SA_301)
    bp04 = rect_panel("upper back pad foam", 190.0, 160.0, 20.0, material_id="xlpe_foam", piece_id="BP-04",
                      seam_allowance_mm=SA_LASER)
    for p in (bp03, bp07):
        for e in p.edge_names:
            p.add_notch_on_edge(e, 0.5, label="CL")
    ps.add(bp03, "back panel", "on the crown, above the frame window")
    ps.add(bp07, "back panel", "back of the crown pad (new: panels.yaml had none)")
    ps.add(bp04, "back panel", "6 mm XLPE")
    ps.seams.append(Seam([bp03.edge(e) for e in bp03.edge_names], [bp07.edge(e) for e in bp07.edge_names],
                         name="BP-03 | BP-07 perimeter"))


# ---------------------------------------------------------------------------- rifle boot + lid
def build_accessories(ps: PatternSet):
    # rifle boot: truncated oval cone, bottom = R-02 seam line, top 1.3 x (ASSUMPTION), 200 tall
    r02 = rect_panel("rifle boot bottom", 100.0, 60.0, 30.0, material_id="tpu_coated_nylon_840d", piece_id="R-02",
                     seam_allowance_mm=SA_301, split_corners=False)
    ring = np.asarray(r02.outline + [r02.outline[0]])
    ring = np.asarray(_dense([tuple(p) for p in ring], 3.0))
    c = ring[:-1].mean(0)
    A = np.column_stack([ring - c, np.zeros(len(ring))])
    B = np.column_stack([(ring - c) * 1.30, np.full(len(ring), 200.0)])
    dev = develop_ruled_surface(A, B, resample=False)
    a2, b2 = dev.edge_a, dev.edge_b
    r01 = Piece.from_edges("rifle butt boot body", [("bottom", [tuple(p) for p in a2]), ("seam_b", [tuple(a2[-1]), tuple(b2[-1])]),
                                                    ("top", [tuple(p) for p in b2[::-1]]), ("seam_a", [tuple(b2[0]), tuple(a2[0])])],
                           seam_allowance_mm={"default": SA_301, "top": 20.0}, material_id="cordura_500d_nylon66",
                           piece_id="R-01", grain=0.0)
    ps.strain["R-01"] = {"max_pct": 100 * dev.max_strain, "p99_pct": 100 * dev.max_strain, "p95_pct": 0.0, "mean_pct": 0.0,
                         "folded": 0, "method": "develop_ruled_surface (cone)"}
    for f in (0.25, 0.5, 0.75):
        r01.add_notch_on_edge("bottom", f, label="quarter")
        r02.add_notch_on_edge("bottom" if f == 0.5 else "top", 0.5, label="quarter")
    r02.add_drill_hole(50, 30, 6.0, "drain eyelet")
    ps.add(r01, "carry", "developed cone; clips to either hipbelt wing", kit="accessory")
    ps.add(r02, "carry", "drain eyelet", kit="accessory")
    ps.seams += [Seam(r01.edge("bottom"), [r02.edge(e) for e in r02.edge_names], name="R-01 cone | R-02 bottom"),
                 Seam(r01.edge("seam_a"), r01.edge("seam_b"), name="R-01 cone back seam")]
    # lid (optional accessory)
    l01 = rect_panel("lid top", 300.0, 240.0, 50.0, seam_allowance_mm=SA_301, material_id="robic_210d_ripstop", piece_id="L-01")
    l02 = rect_panel("lid underside", 300.0, 240.0, 50.0, seam_allowance_mm=SA_301, material_id="cordura_330d_nylon66", piece_id="L-02")
    per = sum(l01.edge_length(e) for e in l01.edge_names)
    l03 = rect_panel("lid gusset", per, 70.0, 0.0, seam_allowance_mm=SA_301, material_id="cordura_330d_nylon66", piece_id="L-03",
                     grain=0.0)
    acc = 0.0
    for e in l01.edge_names:
        l03.add_notch(acc, 0.0, "v", f"lid {e}")
        l03.add_notch(acc, 70.0, "v", f"lid {e}")
        acc += l01.edge_length(e)
    for p in (l01, l02):
        for e in p.edge_names:
            p.add_notch_on_edge(e, 0.0, kind="v", label="corner")
        ps.add(p, "lid", "optional 4.9 L lid / hip pack", kit="accessory")
    ps.add(l03, "lid", "#8 AquaGuard zip across the front 260 mm", kit="accessory")
    ps.seams += [Seam(l03.edge("bottom"), [l01.edge(e) for e in l01.edge_names], name="L-03 | L-01"),
                 Seam(l03.edge("top"), [l02.edge(e) for e in l02.edge_names], name="L-03 | L-02"),
                 Seam(l03.edge("left"), l03.edge("right"), name="L-03 gusset end seam")]


# ---------------------------------------------------------------------------- webbing + hardware
def build_cut_lists(ps: PatternSet):
    keep = {"haul wrap W1", "haul wrap W2", "haul wrap W3", "hipbelt strap", "load lifters", "internal meat strap IM1",
            "internal meat strap IM2", "internal meat strap IM3", "roll-top clips", "haul-wrap keeper loops",
            "hip stabilizers", "sternum", "crown 3:1 pulley"}
    for w in PANELS["webbing_cut_list"]:
        if any(w["use"].startswith(k) for k in keep):
            ps.webbing.append({**w, "source": "panels.yaml webbing_cut_list"})
    # v3.1 attachment (analysis/bag_attachment.md, meat_haul_modes.md): stubs + LINK toggles removed
    ps.webbing += [
        {"use": "fairlead captive eyes (8: hinge, IM1-IM3, both sides)", "material_id": "poly_webbing_38mm",
         "length_mm": 120, "qty": 8, "source": "bag_attach._mass_budget loops 0.12 m"},
        {"use": "bag-hook straps IM2/IM3 (hook + TPU sleeve)", "material_id": "poly_webbing_38mm", "length_mm": 160,
         "qty": 4, "source": "bag_attach._mass_budget bag_straps 0.16 m"},
        {"use": "hinge eyes (sewn eye on the tethered pin, caught in B-01/B-05 seam)", "material_id": "poly_webbing_38mm",
         "length_mm": 150, "qty": 2, "source": "ASSUMPTION 150 mm (25 mm rise + 2 x 50 mm eye + tails)"},
        {"use": "under-straps US1/US2 (eye L, cam + tri-glide R, 70 mm belly)", "material_id": "poly_webbing_38mm",
         "length_mm": 550, "qty": 2, "source": "meat_haul_modes.md: 38 mm webbing 1.10 m for two"},
        {"use": "lifter tri-glide keepers tails", "material_id": "poly_webbing_25mm", "length_mm": 60, "qty": 2,
         "source": "bag_attachment.md lifter keeper (ASSUMPTION length)"},
    ]
    # binding (bound edges), lengths from the pieces
    def per(pid, size=None):
        p = ps.graded[pid][size] if size else ps.pieces[pid]
        return p.seam_perimeter_mm
    bind = [("hipbelt wings (top+tip+bottom) x2, size M", 2 * (per("H-01", "M") - 140)),
            ("lumbar pad top+bottom", 2 * 160),
            ("shoulder straps x2 (J)", 2 * per("HS-1", "J")),
            ("back panel mesh perimeter", per("BP-01")),
            ("main-bag inside seams (B-01/B-03 x2, B-03/B-02 x2, bottom ring)", 4 * 765 + ps.pieces["B-05"].seam_perimeter_mm)]
    for use, L in bind:
        ps.webbing.append({"use": f"binding: {use}", "material_id": "grosgrain_binding_20mm (no record: ASSUMPTION)",
                           "length_mm": round(L + 100), "qty": 1, "source": "piece perimeters + 100 mm"})
    zl = ps.pieces["B-02b"].edge_length("zip")
    ps.hardware += [
        {"item": "#10 coil zip, 2 sliders (diagonal)", "material_id": "coil_zipper_10", "length_mm": round(zl + 40), "qty": 1},
        {"item": "#5 coil zip (fly pocket)", "material_id": "coil_zipper_5", "length_mm": 230, "qty": 1},
        {"item": "#8 coil zip (hipbelt pockets, size M)", "material_id": "coil_zipper_8", "length_mm": 150, "qty": 2},
        {"item": "#8 AquaGuard (lid)", "material_id": "aquaguard_zipper_8", "length_mm": 260, "qty": 1},
        {"item": "8 mm drain grommets", "material_id": "-", "length_mm": None, "qty": 2},
    ]


# ============================================================================ build + checks
def build(spacing: float = 12.0) -> PatternSet:
    ps = PatternSet()
    S = MasterSurface()
    ps.surface = S
    build_body(ps, S, spacing)
    build_swells(ps, S)
    build_frame_side_features(ps, S)
    build_band_and_accents(ps, S)
    build_pockets(ps, S)
    build_fly(ps, spacing=max(spacing, 16.0))
    build_hipbelt(ps)
    build_harness(ps)
    build_back_panel(ps)
    build_accessories(ps)
    build_cut_lists(ps)
    ps.notes += [
        "pack-designer: the 30 mm head setback is not sewable as a smooth step (10.5 % stretch on B-01, 8.5 % on the "
        "face). The pattern takes it with a SETBACK seam at z 560 and a SHOULDER seam at z 631.2 (zip end), ruled "
        "between. Volume is unchanged (85.02 L rebuilt vs 85.16 L design). geometry.yaml should adopt the two seams.",
        "pack-designer / structural: the under-strap cleat US2 (z 142, cheek z 133-151) is not under a swell (hinge swell "
        "ends z 130, IM1 swell starts z 145). US1 (z 95) sits under the hinge swell (8 mm of rise there). Only the eight "
        "accepted swells are drawn.",
        "pack-designer: B-10 frame-link tabs and the 6 girth-hitched stubs are retired (bag_attachment.md: LINK hardware "
        "removed). The meat-strap ports now sit in the swell crests over the fairlead eyes (x +/-115), not at x +/-100.",
        "pack-designer: under-strap channel positions (30 % / 65 % of floor depth, on the fly-pocket face) are an "
        "ASSUMPTION; meat_haul_modes.md gives no position.",
        "pack-designer: hydration sleeve narrowed 250 -> 176 mm to clear the IM2/IM3 swells (x +/-88).",
        "pack-designer: back panel mesh resized to 350 x 440 to cover both 100 x 420 stay rails (panels.yaml had 230 x 300, "
        "smaller than the rails); rail sleeves BP-05 x2 and a crown-pad back BP-07 added.",
        "pack-designer: hipbelt pocket width graded with the wing (S 113 / M 150 / L, XL 180) so pocket + tip shard fit "
        "the S wing; the S pocket will not take a rangefinder lying flat.",
        "materials-engineer: roll widths for cordura_330d, ultragrid, hypalon, spacer mesh, printables, TPU 840D and the "
        "sheet goods are ASSUMPTIONs in the records; confirm before a production buy. No grosgrain binding record.",
        "yoke cover HS-05 is the v3.1 placeholder; the torso-adjust yoke (RESUME next #1) will change it.",
    ]
    for pid, p in ps.pieces.items():
        p.labels.setdefault("pack", "5200 v3.1")
        p.face = "up"
    return ps


def seam_report(ps: PatternSet, tol=1.0):
    rep = check_seams(ps.seams, tol_mm=tol)
    graded = {s: check_seams(v, tol_mm=tol) for s, v in ps.graded_seams.items()}
    return rep, graded


def volume_check(ps: PatternSet) -> dict:
    """Re-assemble the flattened seam lines into rings and integrate the volume.

    For each z level the ring is rebuilt from the FLAT pattern: its perimeter is the sum of
    the flat lengths of that ring line across every body piece (mapped through each piece's
    flat mesh), and its height step is the flat length of the B-01 | B-03 seam between levels
    times the 3D dz/ds of that seam. The ring shape (aspect) is the master ring scaled to that
    perimeter: A_flat = A_3d (P_flat / P_3d)^2. Above the collar seam the collar is a straight
    tube (perimeter = pattern width) and the design dome to the fill line is checked to fit in
    it. Swells (inward) are subtracted."""
    S = ps.surface
    b = ps.body
    zs = np.r_[np.linspace(Z0, Z_SB, 50)[:-1], np.linspace(Z_SB, Z_SH, 10)[:-1], np.linspace(Z_SH, Z_COLLAR, 20)]
    zs = np.unique(np.round(zs, 4))
    face = [b["b02b"], b["b02a"], b["b02c"], b["b02d"]]

    def host_for(dp_list, uv):
        for dp in dp_list:
            if dp.region.buffer(0.5).contains(SPoint(*uv)):
                return dp
        return min(dp_list, key=lambda d: d.region.distance(SPoint(*uv)))

    def flat_len(z, q0, q1, hosts, n):
        """Flat length of the ring line z between q0 and q1, clipped to each host region
        (so dart mouths and zip gaps are not counted)."""
        line = LineString([(q0 * US, z), (q1 * US, z)])
        tot = 0.0
        covered = None
        for dp in hosts:
            part = line.intersection(dp.region.buffer(1e-6))
            if covered is not None:
                part = part.difference(covered)     # a ring on a tier seam belongs to one tier only
            covered = part if covered is None else covered.union(part)
            for g in getattr(part, "geoms", [part]):
                if g.is_empty or g.geom_type != "LineString" or g.length < 1e-6:
                    continue
                pts = np.asarray(_dense(list(g.coords), 3.0))
                tot += _len(dp.to_flat(pts))
        return tot

    A3, Af, P3s, Pfs = [], [], [], []
    frame = [b["b01"], b["b01b"], b["b01u"]]
    for z in zs:
        qs = np.linspace(0, 2, 801)
        P3 = S(np.column_stack([qs * US, np.full(len(qs), z)]))
        x, y = P3[:, 0], P3[:, 1]
        a3 = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(y[:-1], x[1:]))
        p3 = float(np.linalg.norm(np.diff(P3, axis=0), axis=1).sum())
        pf = (flat_len(z, Q_FRM_L, Q_FRM_R, frame, 61) + flat_len(z, Q_FACE_R, Q_FACE_L, face, 61)
              + 2 * flat_len(z, Q_FRM_R, 2 + Q_FACE_R, [b["b03"]], 25))     # L gore = mirror of R
        A3.append(a3)
        P3s.append(p3)
        Pfs.append(pf)
        Af.append(a3 * (pf / p3) ** 2)
    A3, Af = np.array(A3), np.array(Af)
    # height from the flat B-01 | B-03 seam (right edge of the B-01 tiers)
    seam_uv = np.column_stack([np.full(len(zs), Q_FRM_R * US), zs])
    S3 = S(seam_uv)
    ds3 = np.linalg.norm(np.diff(S3, axis=0), axis=1)
    dz3 = np.diff(S3[:, 2])
    dsf = []
    for (u0, z0_), (u1, z1_) in zip(seam_uv[:-1], seam_uv[1:]):
        dp = b["b01"] if z1_ <= Z_SB + 1e-6 else (b["b01b"] if z1_ <= Z_SH + 1e-6 else b["b01u"])
        f = dp.to_flat([(u0, z0_), (u1, z1_)])
        dsf.append(float(np.linalg.norm(f[1] - f[0])))
    dzf = np.array(dsf) * dz3 / ds3
    V_body_3d = float(np.sum(0.5 * (A3[1:] + A3[:-1]) * dz3))
    V_body_flat = float(np.sum(0.5 * (Af[1:] + Af[:-1]) * dzf))
    # collar region: design rings from the collar seam to the fill line
    BG.set_width_scale(W_SCALE)
    t = np.linspace(BG.T_COLLAR, 1.0, 400)
    V_top = float(np.trapezoid(BG.ring_area(t), t * HF))
    perim_needed = max(BG.ring_seams(BG.ring_xy(tt, HF)[0])["Ltot"] for tt in np.linspace(BG.T_COLLAR, 1.0, 30))
    collar_w = ps.pieces["B-06"].edge_length("bottom")
    # swells: two cones of A_crest = 16 * 25 (cos^2 mean x width)
    v_sw = 0.0
    for w in ps.swell_windows:
        a_cr = SWELL_H * SWELL_W / 2
        v_sw += a_cr * (w["lower"] + w["upper"]) / 3
    V_design = float(BG.bag_volume_mm3(HF))
    tot = (V_body_flat + V_top - v_sw) / 1e6
    return {"design_L": V_design / 1e6, "master_surface_body_L": V_body_3d / 1e6, "pattern_body_L": V_body_flat / 1e6,
            "collar_to_fill_L": V_top / 1e6, "swells_L": v_sw / 1e6, "pattern_total_L": tot,
            "pattern_total_cu_in": tot * 1e6 / 16387.064, "delta_vs_design_L": tot - V_design / 1e6,
            "collar_perimeter_mm": collar_w, "max_ring_perimeter_above_collar_mm": float(perim_needed),
            "collar_fits": bool(collar_w >= 0.995 * perim_needed),
            "perimeter_err_max_mm": float(np.max(np.abs(np.array(Pfs) - np.array(P3s)))),
            "height_flat_mm": float(np.sum(dzf)), "height_3d_mm": float(np.sum(dz3))}


def summary(ps: PatternSet) -> dict:
    rep, graded = seam_report(ps)
    cut = ps.all_pieces()
    n_cut = sum(p.quantity for p in ps.all_pieces(kit={"base"}, sizes={"M", "J"}))
    return {"piece_types": len(ps.pieces), "cut_pieces_per_pack_base": n_cut, "seams": len(rep.results),
            "mismatches": len(rep.mismatches), "graded_mismatches": {s: len(g.mismatches) for s, g in graded.items()},
            "max_p99_strain_pct": max(v["p99_pct"] for v in ps.strain.values()),
            "graded_piece_files": len(cut)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    ps = build()
    rep, graded = seam_report(ps)
    print(rep if rep.mismatches else f"seams OK: {len(rep.results)}")
    for s, g in graded.items():
        print(s, "OK" if g.ok else g)
    for k, v in ps.strain.items():
        print(f"{k:7s} p99 {v['p99_pct']:.2f} %  max {v['max_pct']:.2f} %")
    print(json.dumps(volume_check(ps), indent=1))
    if not a.check:
        from patterns_v31_export import export_all  # noqa: E402
        export_all(ps)
