"""BL-058: frame / hardware findings of review 6 (M-1 nut, M-2 pin retention, M-3 US2 pin head, M-5 real-geometry
checks; m-2 hip screws, m-3 hex key and hip holes, m-8 us_route.json).

    python -m huntkit.gendesign.bl058_frame --heavy     # US2 lug submodel + whole body on the exported print (long)
    python -m huntkit.gendesign.bl058_frame             # checks, analysis/bl058.json, screenshots, insert guide STL

1. **M-1 nut** (``nut_check``): the hex pockets of the US2 clevis traps (both sides) and the z 234 traps (4 bolts)
   measured on ``print/frame_h1/h1_assembled.stl`` by probe lines through the section polygons (no model numbers):
   pocket length, washer-slot length, nut face; a nut of thickness m seats when nut_face - washer - m >= the pocket's
   inner end. DIN 934 M5 (m 3.7-4.0) against ISO 4032 M5 (m 4.4-4.7); screw tip protrusion past the nut and the tail
   clearance with the length tolerance.
2. **M-2 retainers** (``RETAINERS``, ``envelopes``, ``retainer_checks``): a named commercial retainer per station with
   its cited dimensions and orientation, as solids in frame coordinates; checked against the print (clash, with a
   0.5 mm gap), the B-01 plane (the bag rests on the cheek-tip plane: >= 1 mm under it), the US strap ribbons
   (us_route 'now' paths) and the hinge eye (us_route.he_shapes). US2: groove + DIN 6799 E-clip (``groove_check``:
   pin bending at the groove, Ti and 7075), tether from a tail hole.
3. **M-3** (``h1_bedfit.pin_cbore_cut``): the US2 pin head in a D9 x 2 counterbore of the clevis (clevis reprint
   only); the head, retainer and tether in ``us_route.head_clearance`` (re-run on every drape).
4. **M-5** (``heavy``): the US2 lug submodel (h1_rev5.lug_check) and the whole body (h1_closeout.body) on the
   exported print: the body is the assembled STL re-rastered on the H1 2 mm grid (``body_stl``), so the D50 hip boss,
   the BL-056 blocks and every fairlead inside the domain are in it (BOSS-LOCAL).
5. **m-2 / m-3** (``hip_screws``, ``hip_holes``, ``insert_guide``): M5 x 12 engagement, the 3 mm key, D5.8 holes
   against the insert position scatter, a printed insert-setting guide.

Units mm, N, MPa, g. Frame coordinates: x lateral (+ = R), y towards the bag, z up.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
PRINT = PACK / "print" / "frame_h1"
PIECES = PRINT / "test_pieces"
RESULTS = ANALYSIS / "bl058.json"
OUT = ROOT / "outputs" / "bl058"
BEFORE = OUT / "before"               # the 6b0cde1 print files, copied before the BL-058 re-export
SCREENS = ROOT / "outputs" / "screens"
SHOT = "20261121_BL058_"
DATE = "2026-11-21"
RHO_PAHT = 1.06e-3                    # g/mm3, as the print export books it (h1_buckling.export_print)
BODY_STL = "m1_u2.5_im3_bl058_stl"            # h1_buckling.full_check cache: the exported print re-rastered
BODY_STL_SANDED = "m1_u2.5_im3_bl058_stl_sanded"

# ============================================================================================ sources
SRC = {
    "din934": "https://aspenfasteners.com/m5-0-8-din-934-iso-4032-metric-hex-finished-nuts-class-10-steel-plain "
              "(DIN 934 M5: s 8 (7.78-8), height 4 basic, 3.7 min, 4 max); "
              "https://accu-components.com/us/hexagon-nuts/7891-HPN-M5-A2 (A2 DIN 934 M5: 4 mm +0/-0.3)",
    "iso4032": "https://fasten.it/norms/norm/din_en_iso_4032 (DIN EN ISO 4032 M5: m max 4.70, m min 4.40, s 8, "
               "e min 8.79)",
    "din7984": "https://www.westfieldfasteners.co.uk/A4_ScrewBolt_SHCapLow_M5.html (DIN 7984 M5: s 3, t 2.7) and "
               "https://westfieldfasteners.co.uk/Standards/ScrewBolt-SHCapLow-M.html (dk 8.5 max, k 3.5 max); "
               "https://eshop-pl.boellhoff.com/out/media/pdf/DIN_7984_Stahl_08.8___en.pdf (M5 SW 3)",
    "din6799": "https://www.mcmaster.com/din-6799-retaining-rings (DIN 6799, 1.4122 stainless, for OD 5-7 mm: "
               "groove dia 4, groove width 0.74, ring OD 8.85 uninstalled, thickness 0.7, thrust load 210 lbf)",
    "hairpin": "https://www.mcmaster.com/hitch-pin-clips (hairpin clips, 18-8 stainless: 90153A214 for 3/16 in "
               "shaft, wire 1/32 in, length 1/2 in, pin opening 9/64 in; 90153A216 for 1/4 in, 1/32 in, 5/8 in, 7/32 in)",
    "din11024": "https://fasten.it/norms/norm/din_11024 (DIN 11024 spring cotters start at 2.5 mm wire for 9-11.2 mm "
                "pins: no DIN R-clip exists for a 5 mm pin)",
    "iso273": "https://www.iso.org/standard/4183.html (ISO 273 clearance holes, fine / medium / coarse; M5 5.3 / 5.5 / "
              "5.8: secondary, the table is behind the paywall)",
    "fdm_tol": "https://www.hubs.com/3d-printing/dimensional-accuracy/ and "
               "https://formlabs.com/blog/understanding-accuracy-precision-tolerance-in-3d-printing/ (FDM prototyping "
               "+/-0.5 % with a +/-0.5 mm lower limit)",
}

# ============================================================================================ 1. nuts (M-1)
NUTS = {
    "DIN 934": {"m_max": 4.0, "m_min": 3.7, "s": 8.0, "e_sharp": 8.0 / math.cos(math.radians(30)),
                "source": SRC["din934"]},
    "ISO 4032": {"m_max": 4.7, "m_min": 4.4, "s": 8.0, "e_min": 8.79, "e_sharp": 8.0 / math.cos(math.radians(30)),
                 "source": SRC["iso4032"]},
}
BOLT_LEN_TOL = 0.5                    # ASSUMPTION BOLT-LEN: ISO 4759-1 grade A length js15 for 30-50 mm (+/-0.5);
#                                       settled by a caliper on every M5 x 35 / x 45 before assembly
PITCH = 0.8


def _mesh(path: Path | None = None):
    import trimesh
    return trimesh.load(path or PRINT / "h1_assembled.stl", force="mesh")


def probe(mesh, p0, u, n, t0: float, t1: float) -> list:
    """Solid intervals [(ta, tb)] of the line p0 + t u (t in [t0, t1]) through the mesh, from the section of the mesh
    by the plane through the line with normal n (n perpendicular to u): exact polygon edges, even-odd."""
    from shapely.geometry import LineString, Polygon
    p0, u, n = (np.asarray(v, float) for v in (p0, u, n))
    u = u / np.linalg.norm(u)
    n = n - (n @ u) * u
    n = n / np.linalg.norm(n)
    w = np.cross(n, u)
    s = mesh.section(plane_origin=p0, plane_normal=n)
    if s is None:
        return []
    area = None
    for L in s.discrete:
        Q = np.asarray(L) - p0
        P = Polygon(np.c_[Q @ u, Q @ w]).buffer(0)
        area = P if area is None else area.symmetric_difference(P)
    seg = LineString([(t0, 0.0), (t1, 0.0)]).intersection(area)
    parts = [seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))
    out = []
    for g in parts:
        if g.length > 1e-6:
            xs = [c[0] for c in g.coords]
            out.append((min(xs), max(xs)))
    return sorted(out)


def voids(solid: list, t0: float, t1: float) -> list:
    """Complement of the solid intervals in [t0, t1]."""
    out, a = [], t0
    for s0, s1 in solid:
        if s0 > a + 1e-6:
            out.append((a, s0))
        a = max(a, s1)
    if t1 > a + 1e-6:
        out.append((a, t1))
    return out


def _seat(nut_face: float, pocket_end: float, washer_t: float, m: float) -> float:
    """Room left for a nut of thickness m (> 0 seats): the pocket's inner end measured along the axis from the nut
    face, against washer + nut."""
    return round((nut_face - pocket_end) - washer_t - m, 3)


def nut_check(mesh=None) -> dict:
    """US2 traps (both sides, both bolts) and the z 234 traps (4 bolts) measured on the STL."""
    from . import frame_h1 as H1
    from . import h1_bedfit as BF
    m = mesh if mesh is not None else _mesh()
    j = BF.JOINT
    rows = []
    # ---- US2: bolt axes along x. Probe lines parallel to the axis at z +3.3 (inside the hex flats, af/2 4.1, outside
    # the 2.4 hole) and z +4.7 (washer slot only, radius 5.2), in the plane normal to y through the axis; |x| measured
    for p in BF.us2_stations():
        s = p["sign"]
        for k, (yb, zb) in enumerate(BF.bolt_axes(p, j)):
            meas = {}
            for lab, dz in (("hex", 3.3), ("washer", 4.7), ("cbore", 4.0), ("axis", 0.0)):
                z = zb + (dz if zb > p["z"] else -dz)       # probe away from the other bolt
                if lab == "cbore":
                    z = zb + (4.0 if zb > p["z"] else -4.0)
                sol = probe(m, (s * 130.0, yb, z), (s, 0.0, 0.0), (0.0, 1.0, 0.0), 0.0, 60.0)
                meas[lab] = [(round(130.0 + a, 3), round(130.0 + b, 3)) for a, b in voids(sol, 0.0, 60.0)]
            # the hex pocket: the void run at the hex probe that contains |x| 147; washer slot: at the washer probe
            hexv = next(v for v in meas["hex"] if v[0] < 147.0 < v[1])
            wsv = next(v for v in meas["washer"] if v[0] < 149.5 < v[1])
            cb = next(v for v in meas["cbore"] if v[1] > j.outer_face - 1.0)
            ax = [v for v in meas["axis"] if v[0] < 146.0]
            tail_end = min(v[0] for v in ax) if ax else None
            nut_face, pocket_end = wsv[1], hexv[0]
            head_face = cb[0]
            tip = head_face - 35.0                              # M5 x 35 DIN 7984 (head bears on the cbore floor)
            r = {"joint": "US2 clevis", "side": p["side"], "bolt_no": k, "pocket_inner_end_abs_x": pocket_end,
                 "washer_slot_abs_x": wsv, "nut_face_abs_x": nut_face, "hex_pocket_mm": round(wsv[0] - pocket_end, 3),
                 "slot_to_nut_face_mm": round(nut_face - pocket_end, 3), "head_face_abs_x": head_face,
                 "tail_hole_end_abs_x": tail_end, "bolt": "M5 x 35 DIN 7984", "bolt_tip_abs_x": round(tip, 3),
                 "model": {"trap_x0": j.trap_x0, "nut_face": j.nut_face, "head_face": j.head_face}}
            rows.append(_nut_rows(r, j.washer_t, tip, tail_end, nut_face, inward=True))
    # ---- z 234: bolt axes parallel to the stay axis. Probe opposite to the trap opening at r 3.3 (hex) / 5.6 (washer)
    for sx, k, base, ax in H1.bolt_axes(H1.JOINT):
        jz = H1.JOINT
        ax = np.asarray(ax, float) / np.linalg.norm(ax)
        td = jz.trap_dir(k)
        d = np.array([-sx * td[0], -td[1], 0.0])
        d = d - (d @ ax) * ax
        d /= np.linalg.norm(d)
        nrm = np.cross(ax, d)
        meas = {}
        for lab, r_ in (("hex", 3.3), ("washer", 5.6), ("axis", 0.0)):
            p0 = np.asarray(base, float) + r_ * d - 45.0 * ax          # base is the axis at z 234
            sol = probe(m, p0, ax, nrm, 0.0, 90.0)
            meas[lab] = [(round(float(p0[2] + a * ax[2]), 3), round(float(p0[2] + b * ax[2]), 3))
                         for a, b in voids(sol, 0.0, 90.0)]
        hexv = next(v for v in meas["hex"] if v[0] < jz.nut_face - 3.0 < v[1])
        wsv = next(v for v in meas["washer"] if v[0] < jz.nut_face - 0.5 < v[1])
        axv = next(v for v in meas["axis"] if v[0] < jz.z < v[1])
        nut_face, pocket_end = wsv[1], hexv[0]
        tip = jz.head_face + jz.washer_t - jz.bolt_len         # head washer on the counterbore floor (frame_h1.Joint)
        r = {"joint": "z 234", "side": "R" if sx > 0 else "L", "bolt_no": k, "pocket_inner_end_z": pocket_end,
             "washer_slot_z": wsv, "nut_face_z": nut_face, "hex_pocket_mm": round(wsv[0] - pocket_end, 3),
             "slot_to_nut_face_mm": round(nut_face - pocket_end, 3), "tail_hole_end_z": axv[0],
             "bolt": f"M5 x {jz.bolt_len:g} DIN 7984", "bolt_tip_z": round(tip, 3),
             "model": {"n_lo": jz.nut_face - jz.washer_t - 0.2 - jz.nut_t - 0.4, "nut_face": jz.nut_face,
                       "tail_z": jz.tail_z}}
        rows.append(_nut_rows(r, jz.washer_t, tip, axv[0], nut_face, inward=True))
    out = {"rows": rows, "nuts": NUTS, "bolt_len_tol_mm": BOLT_LEN_TOL, "pitch_mm": PITCH}
    for std in NUTS:
        out[f"{std}_seats_everywhere_at_m_max"] = all(r["seat"][std]["at_m_max_mm"] > 0.0 for r in rows)
        out[f"{std}_seats_everywhere_at_m_min"] = all(r["seat"][std]["at_m_min_mm"] > 0.0 for r in rows)
    out["din934_tip_through_nut_everywhere"] = all(r["seat"]["DIN 934"]["tip_past_nut_short_bolt_mm"] > 0.0
                                                   for r in rows)
    out["verdict"] = ("DIN 934 seats in every trap (US2 and z 234) with the screw tip through the nut; ISO 4032 does "
                      "not seat at US2 at any thickness in its range, and at z 234 only below m "
                      f"{min(r['slot_to_nut_face_mm'] - 1.0 for r in rows if r['joint'] == 'z 234'):.2f}: the "
                      "caliper check (m <= 4.1) matters")
    return out


def _nut_rows(r: dict, washer_t: float, tip: float, tail_end, nut_face: float, inward: bool) -> dict:
    """Seat room, tip protrusion past the nut's far face and tail clearance for each nut standard. Coordinates run
    from the nut face towards the tail (|x| or z decreasing)."""
    r["seat"] = {}
    for std, d in NUTS.items():
        far_max = nut_face - washer_t - d["m_max"]             # nut's far face, thickest nut
        far_min = nut_face - washer_t - d["m_min"]
        r["seat"][std] = {"at_m_max_mm": _seat(nut_face, r.get("pocket_inner_end_abs_x", r.get("pocket_inner_end_z")),
                                               washer_t, d["m_max"]),
                          "at_m_min_mm": _seat(nut_face, r.get("pocket_inner_end_abs_x", r.get("pocket_inner_end_z")),
                                               washer_t, d["m_min"]),
                          "m_that_just_seats_mm": round(r["slot_to_nut_face_mm"] - washer_t, 3),
                          "tip_past_nut_nominal_mm": round(far_max - tip, 3),
                          "tip_past_nut_short_bolt_mm": round(far_max - (tip + BOLT_LEN_TOL), 3),
                          "tip_past_nut_pitches": round((far_max - tip) / PITCH, 2)}
    if tail_end is not None:
        r["tail_clear_nominal_mm"] = round(tip - tail_end, 3)
        r["tail_clear_long_bolt_mm"] = round(tip - BOLT_LEN_TOL - tail_end, 3)
    return r


# ============================================================================================ 2. retainers (M-2)
HAIRPIN = {
    "id": "HW-PIN-RET-H", "part": "McMaster-Carr 90153A214: hairpin (R-) clip, 18-8 stainless, for 3/16 in (4.76 mm) "
    "shaft, wire 1/32 in (0.79 mm), length 1/2 in (12.7 mm), pin opening 9/64 in (3.57 mm)",
    "source": SRC["hairpin"], "wire_d": 0.79, "length": 12.7, "pin_opening": 3.57,
    "mass_g": round(math.pi / 4 * 0.79 ** 2 * (2 * 12.7 + 6.0) * 7.9e-3, 3),   # ASSUMPTION CLIP-MASS: 2 legs + bend
    "fallback": "90153A216 (1/4 in shaft, 5/8 in long) if the 3/16 in clip will not spring over the 5.0 mm pin",
    "note": "DIN 11024 spring cotters start at 2.5 mm wire for 9-11.2 mm pins (" + SRC["din11024"] + "): there is no "
            "DIN R-clip for a 5 mm pin, so the clip is a catalogue hairpin clip",
}
ECLIP = {
    "id": "HW-PIN-RET-E", "part": "DIN 6799 RS 4 retaining washer (E-clip), 1.4122 stainless, for 5-7 mm shafts: groove "
    "D4.0 x 0.74 wide, ring OD 8.85 (uninstalled), 0.7 thick, thrust load 210 lbf (934 N)",
    "source": SRC["din6799"], "groove_d": 4.0, "groove_w": 0.74, "od": 8.85, "t": 0.7, "thrust_n": 934.0,
    "mass_g": round(0.75 * math.pi / 4 * (8.85 ** 2 - 4.0 ** 2) * 0.7 * 7.7e-3, 3),   # ASSUMPTION ECLIP-MASS: 75 % of
    #                                                                                  the annulus (opening, lugs)
    "tool": "fit by pushing it radially onto the groove with flat pliers; remove with a small flat screwdriver in the "
            "opening (the pin comes out only at the bench, bag off)",
}
CROSS_HOLE_D = 1.5                    # orchestrator call: 1.5-1.6 mm if kept (0.79 wire: 0.7 mm play, takes the 1.2 mm
#                                       wire spare clips too)
CLIP_EDGE = 2.5                       # cross-hole centre beyond the far cheek's outer face (h1_rev5.CLIP_EDGE)
TAIL_BEYOND_HOLE = 2.0                # h1_rev5.TAIL_BEYOND_HOLE
TAIL_HAIRPIN = CLIP_EDGE + 1.3 / 2.0 + TAIL_BEYOND_HOLE   # BL-053's tail (1.3 hole): 5.15 mm; with the D1.5 hole the
#                                       end wall past the hole is 1.9 mm (was 2.0) and the shanks (45.1 / 41.1) stay
CLIP_TIP_PAST_PIN = 3.0               # ASSUMPTION CLIP-ENV: the hairpin's straight-leg tip stands <= 3 mm past the pin
#                                       surface on the side opposite the clip body (catalogue gives the overall length
#                                       only); settled by a caliper on one clip seated on a pin (PIN-RET a)
ECLIP_PLAY = 0.3                      # groove's near edge beyond the far cheek face (axial play; sleeve flush)
GROOVE_LAND = 1.5                     # groove to the tether hole edge (3 x the 0.5 mm groove depth, ASSUMPTION GROOVE-LAND)
TETHER_HOLE_D = 1.6                   # h1_rev5.TETHER_HOLE_D (1.5 mm Dyneema)
TETHER_END_WALL = 1.0                 # tether hole edge to the pin's tail end
TETHER_G = 0.2                        # h1_rev5.RETAINER tether_g (1.5 mm Dyneema, 120 mm)
HEAD_D, HEAD_T = 8.0, 1.5             # h1_rev5.HEAD_D / HEAD_T
US2_HEAD_T = 1.0                      # BL-058 follow-up (orchestrator): the US2 pin head 1.0 mm in a 1.5 mm counterbore, so the
#                                       outer cheek bears over 6.5 mm (sleeve SF >= 1 at the dy 95 / share 1.0 corner)


def head_t(name: str) -> float:
    return US2_HEAD_T if name == "us2" else HEAD_T
KNOT = {"d": 4.0, "l": 3.0}           # ASSUMPTION KNOT: the tether's stopper knot at a head hole, D4 x 3 mm
B01_RULE = 1.0                        # retainer >= 1 mm under the cheek-tip plane (B-01 rests on the tips)
FRAME_GAP = 0.5                       # retainer >= 0.5 mm off the print (except the E-clip's thrust face)

STATION_RET = {
    "hinge": {"retainer": "hairpin", "points": "fore (-y, towards the wearer: 60+ mm free at the far face)",
              "why": "the hinge pin comes out at every bag-off: a gloved, tool-free clip"},
    "us1": {"retainer": "hairpin", "points": "fore (-y, inside the buttress's 12 mm slot: 24 mm free)",
            "why": "fore room 24.2 mm (STL) for a 13.5 mm clip body"},
    "us2": {"retainer": "eclip", "points": "a ring round the pin (no leg): 4.4 mm radius inside the 12 mm slot",
            "why": "fore room 8.0 mm (STL) is shorter than any clip body; aft is B-01 and the meat (review 6 M-2)"},
    "im1": {"retainer": "hairpin", "points": "fore (-y: 60+ mm free)", "why": "as the hinge"},
    "im2": {"retainer": "hairpin", "points": "fore (-y: 18.2 mm free, STL)", "why": "18.2 mm fore room > 13.5 mm"},
    "im3": {"retainer": "hairpin", "points": "fore (-y: 22.7 mm free, STL)", "why": "22.7 mm fore room > 13.5 mm"},
}


def stations_R() -> dict:
    from . import h1_fairleads as HF
    return {p["name"]: p for p in HF.placed() if p["side"] == "R"}


def faces(p: dict) -> dict:
    """|x| of the near (head) and far (retainer) cheek outer faces, R side. The head is outboard (larger |x|) at every
    station (h1_rev5.pins); at US2 it bears on the counterbore floor."""
    from . import h1_bedfit as BF
    g = p["geom"]
    span = g.throat + 2 * g.cheek
    near, far = abs(p["x"]) + span / 2, abs(p["x"]) - span / 2
    head_seat = near - BF.PIN_CBORE_DEPTH if p["name"] == "us2" else near
    return {"near": near, "far": far, "head_seat": head_seat, "span": span}


def pin_row(name: str) -> dict:
    """The BL-058 pin of a station: shank (head seat -> tail end), features from the head, retainer, tether."""
    p = stations_R()[name]
    f = faces(p)
    ret = STATION_RET[name]["retainer"]
    shank_in = f["head_seat"] - f["far"]                 # head seat to far cheek face
    if ret == "hairpin":
        tail = TAIL_HAIRPIN                              # BL-053's tail kept: the shank lengths do not change
        feats = {"cross_hole": {"d_mm": CROSS_HOLE_D, "from_far_cheek_face_mm": CLIP_EDGE,
                                "axis": "frame y (the clip lies in the y-z plane, body fore)"},
                 "tether_hole": {"d_mm": TETHER_HOLE_D, "where": "in the head (as BL-053)"}}
        part = HAIRPIN
    else:
        g0 = ECLIP_PLAY
        g1 = g0 + ECLIP["groove_w"]
        th = g1 + GROOVE_LAND + TETHER_HOLE_D / 2.0
        tail = th + TETHER_HOLE_D / 2.0 + TETHER_END_WALL
        feats = {"groove": {"d_mm": ECLIP["groove_d"], "w_mm": ECLIP["groove_w"], "tol": "d h11 / w H13 (DIN 6799)",
                            "from_far_cheek_face_mm": [round(g0, 2), round(g1, 2)]},
                 "tether_hole": {"d_mm": TETHER_HOLE_D, "from_far_cheek_face_mm": round(th, 2),
                                 "axis": "frame z (cord exits along the slot)", "where": "in the tail, past the groove"},
                 "head": "plain (no tether hole), D8 x 1.0: the head sits in the clevis counterbore D9 x 1.5"}
        part = ECLIP
    L = shank_in + tail
    return {"station": name, "head_seat_abs_x": round(f["head_seat"], 2), "far_face_abs_x": round(f["far"], 2),
            "shank_mm": round(L, 2), "tail_past_far_face_mm": round(tail, 2), "head_mm": [HEAD_D, head_t(name)],
            "retainer": ret, "retainer_part": part["part"], "retainer_id": part["id"], "retainer_source": part["source"],
            "orientation": STATION_RET[name]["points"], "why": STATION_RET[name]["why"], "features": feats,
            "tether": tether_route(name)}


TETHER_ARM_X = 132.0                 # |x| where the US2 tether larks-heads round the lug arm (between the stay's root
#                                      flare and the inner cheek's buttress)


@functools.lru_cache(maxsize=None)
def arm_section(x: float = TETHER_ARM_X) -> dict:
    """y-z bounds of the US2 lug arm cut at |x| = x on the print (R side): the loop the tether wraps."""
    from shapely.geometry import Point, Polygon
    p = stations_R()["us2"]
    m = _mesh()
    sec = m.section(plane_origin=[x, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    A = None
    for L in sec.discrete:
        P = Polygon(np.asarray(L)[:, 1:3]).buffer(0)
        A = P if A is None else A.symmetric_difference(P)
    parts = getattr(A, "geoms", [A])
    arm = next(g for g in parts if g.contains(Point(0.0, p["z"])))
    y0, z0, y1, z1 = arm.bounds
    return {"x": x, "y": [round(y0, 2), round(y1, 2)], "z": [round(z0, 2), round(z1, 2)],
            "perimeter_mm": round(arm.exterior.length, 1)}


def cord_len(name: str) -> float:
    """Tether cord length: BL-053's 120 mm, or (US2) the route + 20 mm of knots, up to the next 10 mm."""
    if name != "us2":
        return 120.0
    return float(math.ceil((tether_route(name)["cord_needed_mm"] + 20.0) / 10.0) * 10.0)


def pin_mass_g(row: dict, material: str) -> float:
    """Pin mass from the record density: shank D5 x shank_mm + head D8 x 1.5, less the groove and the cross holes."""
    from huntkit.materials import load
    rho = float(load(material).require("density_kg_m3")) * 1e-6
    d = 5.0
    v = math.pi / 4 * d ** 2 * row["shank_mm"] + math.pi / 4 * HEAD_D ** 2 * row["head_mm"][1]
    f = row["features"]
    if "groove" in f:
        v -= math.pi / 4 * (d ** 2 - f["groove"]["d_mm"] ** 2) * f["groove"]["w_mm"]
    return v * rho                                       # cross / tether holes not deducted (as h1_rev5.pins)


def tether_g(name: str) -> float:
    return round(TETHER_G * cord_len(name) / 120.0, 3)       # 1.5 mm Dyneema, h1_rev5 RETAINER tether_g per 120 mm


def pin_overlay(name: str, material: str) -> dict:
    """The keys h1_closeout.pins takes from BL-058 for station ``name``: shank, cross hole (US2: the tether hole, the
    E-clip groove), retainer, head seat, masses."""
    r = pin_row(name)
    part = HAIRPIN if r["retainer"] == "hairpin" else ECLIP
    pg = pin_mass_g(r, material)
    f = r["features"]
    if r["retainer"] == "hairpin":
        ch = {"d_mm": f["cross_hole"]["d_mm"], "from_far_cheek_face_mm": f["cross_hole"]["from_far_cheek_face_mm"],
              "use": "hairpin clip (axis along frame y)"}
        side = "inboard (far cheek), clip body pointing fore (-y)"
    else:
        ch = {"d_mm": f["tether_hole"]["d_mm"], "from_far_cheek_face_mm": f["tether_hole"]["from_far_cheek_face_mm"],
              "use": "tether (axis along frame z)"}
        side = "inboard (far cheek): DIN 6799 E-clip in the groove"
    out = {"shank_mm": round(r["shank_mm"], 1), "cross_hole": ch, "clip_side": side, "retainer": r["retainer"],
           "retainer_part": part["part"], "head_mm": r["head_mm"], "head_seat": ("clevis counterbore D9 x 1.5, head D8 x 1.0, 0.5 below the face"
                                                        if name == "us2" else "on the near cheek face"),
           "pin_g": round(pg, 2), "set_g": round(pg + part["mass_g"] + tether_g(name), 2),
           "tether": {"cord_mm": cord_len(name), **{k: v for k, v in tether_route(name).items()
                                                     if k in ("route", "never")}}}
    if "groove" in f:
        out["groove"] = f["groove"]
        out["tether_hole"] = f["tether_hole"]
        out["sleeve_note"] = "the outer cheek's UHMWPE sleeve is cut to 6.5 mm (flush with the counterbore floor)"
    return out


def retainer_record(base: dict) -> dict:
    """h1_rev5.RETAINER's shape (part, source, mass_g, tether, tether_g) with the BL-058 parts, so the kit and the
    build guide keep reading ``pins.retainer``."""
    return {**base, "part": f"{HAIRPIN['part']} (hinge, US1, IM1-IM3); US2: {ECLIP['part']}",
            "source": f"{HAIRPIN['source']}; {ECLIP['source']}", "mass_g": HAIRPIN["mass_g"],
            "mass_eclip_g": ECLIP["mass_g"],
            "tether": "1.5 mm Dyneema (UHMWPE): 120 mm through the head hole and the clip's bend, larks-head round the "
                      f"stay (hairpin stations); US2: {cord_len('us2'):.0f} mm from the pin's tail hole along the "
                      "buttress slot, larks-head round the lug arm at |x| 132",
            "tether_g": TETHER_G, "tether_us2_g": tether_g("us2")}


def clip_double_shear_n() -> float:
    """Hairpin wire (0.79 mm, 18-8) in double shear against a walking pin, on the h1_rev5 basis (0.6 x UTS)."""
    from huntkit.materials import load
    try:
        su = float(load("ss_304").require("ultimate_strength_mpa"))
    except Exception:
        su = 515.0                 # ASSUMPTION CLIP-UTS (h1_rev5): ASTM A240 304 minimum
    return round(2 * math.pi / 4 * HAIRPIN["wire_d"] ** 2 * 0.6 * su, 0)


def retainer_summary() -> dict:
    return {"hairpin": {k: HAIRPIN[k] for k in ("id", "part", "source", "mass_g", "fallback", "note")},
            "eclip": {k: ECLIP[k] for k in ("id", "part", "source", "mass_g", "tool")},
            "stations": {n: {"retainer": v["retainer"], "points": v["points"]} for n, v in STATION_RET.items()},
            "cross_hole_d_mm": CROSS_HOLE_D}


def tether_route(name: str) -> dict:
    p = stations_R()[name]
    f = faces(p)
    if name == "us2":
        a = arm_section()
        xh = f["far"] - pin_row_tail_hole(name)
        top = a["y"][1] + 1.0
        free = [[xh, p["y_pin"], p["z"]], [a["x"] + 2.0, top, p["z"]]]
        loop = [[a["x"], top, p["z"]], [a["x"], top, a["z"][0] - 1.0], [a["x"], a["y"][0] - 1.0, a["z"][0] - 1.0],
                [a["x"], a["y"][0] - 1.0, a["z"][1] + 1.0], [a["x"], top, a["z"][1] + 1.0], [a["x"], top, p["z"]]]
        need = math.dist(*free) + a["perimeter_mm"] + 25.0
        return {"cord": "1.5 mm Dyneema (UHMWPE)", "route": [
            f"through the pin's tail hole at |x| {xh:.1f} (y {p['y_pin']:.1f}, z {p['z']:.0f}), the hole axis along z",
            f"inboard {math.dist(*free):.0f} mm along the buttress slot (z {p['z'] - 6:.0f}-{p['z'] + 6:.0f}), onto the "
            f"lug arm's bag face (y {a['y'][1]:.1f})",
            f"larks-head round the lug arm at |x| {a['x']:.0f} (section y {a['y'][0]:.0f}..{a['y'][1]:.0f}, z "
            f"{a['z'][0]:.0f}..{a['z'][1]:.0f}, perimeter {a['perimeter_mm']:.0f} mm), knot on the bag face"],
            "polyline_free_R": free, "loop_R": loop, "arm_section": a, "cord_needed_mm": round(need, 0),
            "never": "outboard of the clevis face, aft of the cheek-tip plane, or across the US2 throat"}
    return {"cord": "1.5 mm Dyneema (UHMWPE), 120 mm", "route": ["head hole (as BL-053) to a larks-head round the "
                                                                 "stay beside the fairlead"], "polyline_free_R": None}


def pin_row_tail_hole(name: str) -> float:
    return ECLIP_PLAY + ECLIP["groove_w"] + GROOVE_LAND + TETHER_HOLE_D / 2.0


def _cyl_x(xa, xb, y, z, r, seg=48):
    import manifold3d as m3d
    lo, hi = min(xa, xb), max(xa, xb)
    return m3d.Manifold.cylinder(hi - lo, r, r, seg).rotate((0.0, 90.0, 0.0)).translate((lo, y, z))


def _box(lo, hi):
    import manifold3d as m3d
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3d.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def _capsule(a, b, r, seg=24):
    import manifold3d as m3d
    return m3d.Manifold.batch_hull([m3d.Manifold.sphere(r, seg).translate(tuple(map(float, a))),
                                    m3d.Manifold.sphere(r, seg).translate(tuple(map(float, b)))])


def envelopes(name: str, gap: float = 0.0) -> dict:
    """Solids (manifold3d, frame, R side) of the retainer, the head (+ knot) and the tether near the pin of station
    ``name``, grown by ``gap``. 'retainer': the hairpin body in the y-z plane at the cross hole (body fore, the
    straight-leg tip CLIP_TIP_PAST_PIN past the pin aft), or the E-clip ring; 'head': head D8 x 1.5 (+ the knot where the
    tether is at the head); 'tether': the US2 cord as a capsule chain (r 0.75)."""
    p = stations_R()[name]
    f = faces(p)
    yp, zp, r_pin = p["y_pin"], p["z"], p["geom"].pin_d / 2.0
    out = {}
    if STATION_RET[name]["retainer"] == "hairpin":
        w = HAIRPIN["wire_d"]
        xc = f["far"] - CLIP_EDGE
        y_aft = yp + r_pin + CLIP_TIP_PAST_PIN
        y_fore = yp - (HAIRPIN["length"] + w)
        zh = r_pin + w + 0.5
        out["retainer"] = _box((xc - w - gap, y_fore - gap, zp - zh - gap), (xc + w + gap, y_aft + gap, zp + zh + gap))
        hx = (f["near"], f["near"] + HEAD_T + KNOT["l"])
        out["head"] = _cyl_x(hx[0] + 0.05, hx[1] + gap, yp, zp, HEAD_D / 2 + gap)
    else:
        x1 = f["far"] - ECLIP_PLAY
        x0 = x1 - ECLIP["t"]
        out["retainer"] = _cyl_x(x0 - gap, x1 - 0.05, yp, zp, ECLIP["od"] / 2 + 0.3 + gap)   # +0.3: installed spread
        out["tail"] = _cyl_x(f["far"] - faces_tail(name), f["far"] - 0.05, yp, zp, r_pin + gap)
        hx = (f["head_seat"], f["head_seat"] + head_t(name))
        out["head"] = _cyl_x(hx[0] + 0.02, hx[1] + gap, yp, zp, HEAD_D / 2 + gap)
        tr = tether_route(name)
        out["tether"] = _capsule(tr["polyline_free_R"][0], tr["polyline_free_R"][1], 0.75 + gap)
        cap = None
        for a, b in zip(tr["loop_R"][:-1], tr["loop_R"][1:]):
            c = _capsule(a, b, 0.75 + gap)
            cap = c if cap is None else cap + c
        out["tether_loop"] = cap          # lies on the arm by design: not in the clash check
    return out


def faces_tail(name: str) -> float:
    return pin_row(name)["tail_past_far_face_mm"]


def _bounds(man) -> tuple:
    b = man.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


def retainer_checks(mesh=None, us_route: dict | None = None) -> dict:
    """Per station: clash of each envelope (grown FRAME_GAP) with the print, the envelope's highest y against the
    cheek-tip plane (B01_RULE), US1 / US2 strap ribbons, the hinge eye. US2 also the drape (us_route.head_clearance)."""
    from .surface import _to_manifold
    m = mesh if mesh is not None else _mesh()
    fm = _to_manifold(m)
    st = stations_R()
    usr = us_route if us_route is not None else json.loads((ANALYSIS / "us_route.json").read_text())
    rows = {}
    for name in STATION_RET:
        p = st[name]
        env0 = envelopes(name, 0.0)
        envg = envelopes(name, FRAME_GAP)
        r = {"retainer": STATION_RET[name]["retainer"], "orientation": STATION_RET[name]["points"]}
        for k, e in envg.items():
            if k in ("tail", "tether_loop"):   # the pin's own tail runs out of the cheek's hole; the loop wraps the arm
                continue
            v = (fm ^ e).volume()
            r[f"{k}_clash_mm3_at_{FRAME_GAP:g}mm"] = round(v, 3)
        ys = max(_bounds(e)[1][1] for e in env0.values())
        r["y_max"] = round(float(ys), 2)
        r["y_tip"] = round(p["y_tip"], 2)
        r["below_b01_plane_mm"] = round(p["y_tip"] - ys, 2)
        lo, hi = _bounds(env0["retainer"])
        r["retainer_box"] = {"lo": np.round(lo, 2).tolist(), "hi": np.round(hi, 2).tolist()}
        r["fore_room_needed_mm"] = round(p["y_pin"] - lo[1], 2)
        if name in ("us1", "us2"):
            r["strap_mm"] = strap_distance(name, env0, usr)
        if name == "hinge":
            r["he"] = he_distance(env0)
        r["pass"] = bool(all(v < 0.05 for k, v in r.items() if k.endswith("mm3_at_0.5mm"))
                         and r["below_b01_plane_mm"] >= B01_RULE
                         and (r.get("strap_mm", {}).get("min_mm", 99.0) >= 10.0 or name not in ("us1", "us2"))
                         and (r.get("he", {}).get("min_mm", 99.0) >= 1.0))
        rows[name] = r
    return {"rows": rows, "rules": {"frame_gap_mm": FRAME_GAP, "b01_plane_mm": B01_RULE,
                                    "strap_mm": "us_route.CLEAR_REQ 10 (the strap's own rule)", "he_mm": 1.0},
            "pass": all(r["pass"] for r in rows.values())}


def _env_points(env: dict, n: int = 14) -> np.ndarray:
    """Points on the envelopes' bounding boxes (corners, edges, faces), for distances to strap / eye."""
    P = []
    for e in env.values():
        lo, hi = _bounds(e)
        g = [np.linspace(lo[i], hi[i], n) for i in range(3)]
        X, Y, Z = np.meshgrid(*g, indexing="ij")
        Q = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
        on = np.zeros(len(Q), bool)
        for i in range(3):
            on |= np.isclose(Q[:, i], lo[i]) | np.isclose(Q[:, i], hi[i])
        P.append(Q[on])
    return np.vstack(P)


def strap_distance(name: str, env: dict, usr: dict) -> dict:
    """Distance from the envelopes to the 25 mm strap ribbon (width along frame x, as us_route.ribbon lays it on B-01)
    on every 'now' row of us_route.json for this strap, both sides (mirrored to R). The strap's run from its own pin
    down to the joint blocks' lip (z > pin - 14.5 - 1) is inside the throat, walled off by the cheeks: it is reported as
    the cheek wall between (``in_throat``), not as a clearance."""
    from . import h1_bedfit as BF
    p = stations_R()[name]
    Q = _env_points(env)
    d = []
    z_lip = p["z"] - BF.BLOCK_HALF_Z - 1.0
    for r in usr["layouts"]["now"]["rows"]:
        if r["strap"] != name:
            continue
        P = np.asarray(r["path"], float)
        P[:, 0] *= 1.0 if r["side"] == "R" else -1.0
        S = np.vstack([np.linspace(a, b, 30) for a, b in zip(P[:-1], P[1:])])
        S = S[S[:, 2] < z_lip]
        W = np.vstack([S + np.array([k, 0.0, 0.0]) for k in np.linspace(-12.5, 12.5, 11)])
        dd = np.min(np.linalg.norm(Q[:, None, :] - W[None, :, :], axis=2))
        d.append({"torso": r["torso"], "side": r["side"], "mm": round(float(dd), 1)})
    g = p["geom"]
    return {"rows": d, "min_mm": min(x["mm"] for x in d) if d else None,
            "in_throat": {"cheek_wall_mm": g.cheek, "note": "from the pin to the lip the strap runs between the cheeks; "
                          "the head and the retainer sit outside them"},
            "note": "envelope box surface points to the ribbon (25 mm wide along x, 11 lines), below the lip"}


def he_distance(env: dict) -> dict:
    """Hinge: the hairpin envelope against the HE (eye + legs, box) of us_route.he_shapes: lateral gap where the y-z
    shapes overlap, else the y-z distance."""
    sys.path.insert(0, str(PACK))
    import us_route as U
    from shapely.geometry import box as sbox
    he = U.he_shapes()
    lo, hi = _bounds(env["retainer"])
    R = sbox(lo[1], lo[2], hi[1], hi[2])
    out = {}
    for k in ("eye_legs", "box"):
        poly, half = he[k]
        lat = (he["x"] - half) - hi[0]
        yz = R.distance(poly)
        out[k] = {"lateral_gap_mm": round(float(lat), 2), "yz_gap_mm": round(float(yz), 2),
                  "gap_mm": round(float(max(lat, yz)), 2)}
    out["min_mm"] = min(v["gap_mm"] for v in out.values())
    return out


# ---------------------------------------------------------------------------------------------- groove (US2)
KT_GROOVE = 2.5                       # ASSUMPTION KT-GROOVE: Peterson, bending of a shaft with a flat-bottom groove,
#                                       d/D 0.8, r/d about 0.03 (DIN 6799 groove corners r <= 0.1): Kt 2.4-2.6


def pin_moment(F: float, p: dict, eye_offset: float = 0.0, neck: float = 18.0, n: int = 4001) -> dict:
    """Bending moment along the US2 pin (|x|) under the eye's y-z force F: uniform over the neck, its centre
    ``eye_offset`` mm outboard of the throat centre (the 18 mm neck slides +/-1 mm in the 20 mm throat), reacted
    uniformly over each cheek's bearing (inner 8 mm; outer 6.5 mm under the D9 x 1.5 counterbore) with the reactions from
    statics (lever rule on the bearing centroids). Integrated from the free inboard end: M is zero outboard of the
    bearings."""
    from . import h1_bedfit as BF
    g = p["geom"]
    xc = abs(p["x"]) + eye_offset
    f = faces(p)
    inner = (f["far"], f["far"] + g.cheek)
    outer = (abs(p["x"]) + g.throat / 2.0, f["near"] - BF.PIN_CBORE_DEPTH)
    ci, co = 0.5 * sum(inner), 0.5 * sum(outer)
    share = (xc - ci) / (co - ci)                            # outer cheek's share by statics
    eye = (xc - neck / 2.0, xc + neck / 2.0)
    x = np.linspace(f["far"] - 8.0, f["near"] + 1.0, n)
    w = np.zeros_like(x)                                     # distributed load per mm (+ = eye direction)
    w[(x >= eye[0]) & (x <= eye[1])] += F / neck
    w[(x >= inner[0]) & (x <= inner[1])] -= (1.0 - share) * F / (inner[1] - inner[0])
    w[(x >= outer[0]) & (x <= outer[1])] -= share * F / (outer[1] - outer[0])
    dx = x[1] - x[0]
    V = np.cumsum(w) * dx
    M = np.cumsum(V) * dx
    return {"x": x, "M": M, "inner": inner, "outer": outer, "eye": eye, "share_outer": share,
            "R_inner": (1.0 - share) * F}


def groove_check() -> dict:
    """US2: bending at the E-clip groove (|x| far face - 0.3 .. - 1.04, d 4.0) for Ti-6Al-4V and 7075-T6 on the design
    and dy 95 rows (h1_closeout.json pins.us2 bending: y-z force), eye centred and slid 1 mm either way: M at the groove
    is zero (outboard of every bearing), so the pin's SF is its mid-span value: pin_check (the record) and this
    integration with the counterbore's 6 mm outer bearing. Sensitivity: the groove cut 1 mm INSIDE the cheek face by
    mistake: M = R_in x 1^2 / (2 x 8), stress x KT_GROOVE on d 4. The CLEVIS-SHARE 0.6 / 1.0 splits come from cheek
    compliance, not this rigid statics; the groove moment is zero for any split."""
    from huntkit.materials import load
    from . import h1_lanes as LN
    from . import h1_rev5 as R5
    p = stations_R()["us2"]
    g = p["geom"]
    f = faces(p)
    co = json.loads((ANALYSIS / "h1_closeout.json").read_text())["pins"]["stations"]["us2"]["bending"]
    gx = (f["far"] - ECLIP_PLAY - ECLIP["groove_w"], f["far"] - ECLIP_PLAY)
    out = {"groove_abs_x": [round(v, 2) for v in gx], "kt": KT_GROOVE, "rows": {}}
    Zg = math.pi * ECLIP["groove_d"] ** 3 / 32.0
    Zp = math.pi * g.pin_d ** 3 / 32.0
    for mat in ("alu_7075_t6", "ti_6al_4v"):
        m = load(mat)
        sy = float(m.get("yield_strength_sbasis_mpa") or m.require("yield_strength_mpa"))
        su = float(m.require("ultimate_strength_mpa"))
        se = float(m.require("fatigue_limit_mpa")) * 0.9
        smax = 2.0 / (1.0 / se + 1.0 / su)
        for row, F in (("design", co["design_yz_n"]), ("dy95", co["dy95_yz_n"])):
            pc = LN.pin_check(F, g.throat, g.cheek, g.pin_d, mat, R5.G_CRADLE)
            for off in (-1.0, 0.0, 1.0):
                pm = pin_moment(F, p, off)
                sel = (pm["x"] >= gx[0]) & (pm["x"] <= gx[1])
                Mg = float(np.max(np.abs(pm["M"][sel])))
                Mpk = float(np.max(np.abs(pm["M"])))
                s_pk = Mpk / Zp
                Mmis = pm["R_inner"] * 1.0 ** 2 / (2.0 * g.cheek)
                s_mis = KT_GROOVE * Mmis / Zg
                out["rows"][f"{mat}|{row}|eye{off:+g}"] = {
                    "F_yz_n": F, "share_outer": round(pm["share_outer"], 3), "M_at_groove_nmm": round(Mg, 4),
                    "M_peak_nmm": round(Mpk, 1), "M_peak_pin_check_nmm": round(pc["M_nmm"], 1),
                    "sf_yield_peak": round(sy / s_pk, 2), "sf_fatigue_peak": round(smax / (s_pk * 1.6 / R5.G_CRADLE), 2),
                    "sf_yield_pin_check": round(pc["sf_yield"], 2), "sf_fatigue_pin_check": round(pc["sf_fatigue"], 2),
                    "misplaced_1mm": {"M_nmm": round(Mmis, 1), "sigma_kt_mpa": round(s_mis, 1),
                                      "sf_yield": round(sy / s_mis, 2),
                                      "sf_fatigue": round(smax / (s_mis * 1.6 / R5.G_CRADLE), 2)}}
    out["verdict"] = ("the groove sits 0.3-1.04 mm outboard of the inner cheek's face, outboard of every bearing: its "
                      "bending moment and shear are zero, so the groove costs the pin nothing; the pin's peak is at "
                      "mid-span, where the counterbore's shorter outer bearing moves the outer reaction inboard and "
                      "lowers it against pin_check. Cut 1 mm inside the cheek by mistake, the groove would read the "
                      "'misplaced' SFs; the machinist's drawing dimensions it from the head seat.")
    Fw = 0.2 * co["dy95_yz_n"]
    out["thrust"] = {"walk_force_n": round(Fw, 1), "ring_thrust_n": ECLIP["thrust_n"],
                     "sf": round(ECLIP["thrust_n"] / Fw, 2),
                     "land_shear_mpa": round(Fw / (math.pi * ECLIP["groove_d"] * GROOVE_LAND), 2),
                     "basis": "ASSUMPTION WALK-MU: 0.2 x the dy95 y-z force; vendor ring thrust (McMaster DIN 6799)"}
    return out


# ============================================================================================ 5. hip (m-2, m-3)
INSERT_SET_TOL = 0.2                  # ASSUMPTION INSERT-SET: an insert is set flush to 0.2 mm below the boss face (it
#                                       may not stand proud: the base must seat); settled by a straight-edge + feeler
#                                       on every insert before the mount goes on (HB-6b setup)
MOUNT_POS_T = 0.2                     # ASSUMPTION SLM-POS: SLM hole-pattern position tolerance, 0.2 mm diametral (+/-0.1)
SCATTER = {"guided": 0.2, "freehand": 0.4}   # ASSUMPTION INSERT-SCATTER: radial position error of a set insert's axis
#   at the boss face. Guided (printed guide, insert_guide): 0.075 bore play + 0.1 guide hole pattern + 1 deg tilt x 1.5 mm.
#   Freehand: the insert re-centres in its own softened pilot, which is only as good as the print's hole position
#   (FDM prototyping +/-0.5 mm general tolerance, SRC fdm_tol) plus tilt; no published figure for hand-set inserts was
#   found. Settled by the first-article: all 8 M5 x 12 start by hand through the mount, and a 5.0 pin gauge per insert.
GUIDE = {"bore_d": 7.25, "block_h": 6.0, "skirt_depth": 2.5, "skirt_clear": 0.15, "wall": 3.0, "window_d": 20.0}


def hip_screws() -> dict:
    """m-2: M5 x 12 in the 9.5 mm insert under the 3 mm Ti base: engagement, tip to the insert end and to the pilot
    floor (measured on the print: hip_mount.frame_fit), against the old M5 x 14."""
    from . import h1_closeout as C
    from . import hip_mount as HM
    from .frame_comp_B import bolt_mass_g
    ins = C.insert_record()
    f = HM.frame_fit()
    pil = f["pilot_depth_measured_mm"]
    out = {"screw": f"Ti gr5 M5 x {C.HIP_SCREW_L:g} DIN 7984", "was": f"M5 x {C.HIP_SCREW_L_BOOKED:g}",
           "insert_len_mm": ins["length"], "base_t_mm": HM.BASE_T, "pilot_depth_measured_mm": pil, "rows": {}}
    for L in (C.HIP_SCREW_L_BOOKED, C.HIP_SCREW_L):
        tip = L - HM.BASE_T
        out["rows"][f"x{L:g}"] = {
            "tip_depth_below_face_mm": tip,
            "engagement_mm": {"insert_flush": round(min(tip, ins["length"]), 2),
                              "insert_0.2_low": round(min(tip - INSERT_SET_TOL, ins["length"]), 2)},
            "engagement_d": round(min(tip - INSERT_SET_TOL, ins["length"]) / 5.0, 2),
            "tip_past_insert_end_mm": round(tip - ins["length"], 2),
            "tip_to_pilot_floor_mm": round(pil - tip, 2),
            "tip_in_melt_reservoir": bool(tip > ins["length"]),
            "mass_g": round(bolt_mass_g(L), 3)}
    r12 = out["rows"][f"x{C.HIP_SCREW_L:g}"]
    out["pass"] = bool(r12["engagement_d"] >= 1.5 and not r12["tip_in_melt_reservoir"] and r12["tip_to_pilot_floor_mm"] >= 2.0)
    out["rule"] = ">= 1.5 d of thread in the insert (8.8-9.0 of its 9.5 mm), tip inside the insert, >= 2 mm above the floor"
    out["key"] = {"socket_s_mm": 3.0, "source": SRC["din7984"], "tool": "3 mm hex screwdriver (blade >= 60 mm); the "
                  "socket depth t 2.7 mm", "envelope_d_mm": HM.KEY_D, "was": "4 mm key, D5 envelope (BL-056)",
                  "driver_access_ok": HM.geometry_check()["driver_access_ok"],
                  "frame_key_clash_mm3": max(s_["key_in_frame_mm3"] for s_ in f["screws"])}
    return out


def hip_holes() -> dict:
    """m-3: D5.5 (ISO 273 medium) against D5.8 (coarse) for the Ti base: the fixed-fastener budget H - F = T_mount +
    T_inserts (diametral) against the insert scatter, guided and freehand."""
    F = 5.0
    out = {"source": SRC["iso273"], "mount_pos_T_mm": MOUNT_POS_T, "scatter_radial_mm": SCATTER, "rows": {}}
    for H in (5.5, 5.8):
        t_ins = (H - F) - MOUNT_POS_T                    # diametral room left for the inserts
        out["rows"][f"D{H:g}"] = {"H_minus_F_mm": round(H - F, 2), "inserts_radial_allowed_mm": round(t_ins / 2, 3),
                                  **{f"{k}_pass": bool(v <= t_ins / 2 + 1e-9) for k, v in SCATTER.items()}}
    out["choice"] = {"hole_d_mm": 5.8, "guide": True,
                     "why": "guided scatter 0.2 mm fits D5.8's 0.3 mm (and not D5.5's 0.15); freehand 0.4 mm fits "
                            "neither: print the insert-setting guide (test_pieces/hip_insert_guide)"}
    out["head_to_head_worst_mm"] = round(0.69 - 2 * SCATTER["guided"], 2)
    return out


def insert_guide_mesh():
    """The insert-setting guide (local: z up away from the boss face, origin on the boss axis at the face): a D56 block
    GUIDE.block_h thick with 8 bores (insert OD 7.1 + 0.15) on the BL-055 pattern, a skirt over the boss OD (+0.15 a side,
    2.5 deep), a D20 sight window."""
    import manifold3d as m3d
    from . import h1_closeout as C
    from .surface import _from_manifold
    pat = json.loads((ANALYSIS / "h1_closeout.json").read_text())["hip"]["chosen"]["pattern"]
    D = pat["boss_d"]
    ri = D / 2 + GUIDE["skirt_clear"]
    ro = ri + GUIDE["wall"]
    blk = m3d.Manifold.cylinder(GUIDE["block_h"], ro, ro, 180)
    skirt = m3d.Manifold.cylinder(GUIDE["skirt_depth"], ro, ro, 180) - m3d.Manifold.cylinder(
        GUIDE["skirt_depth"] + 0.2, ri, ri, 180).translate((0.0, 0.0, -0.1))
    man = blk + skirt.translate((0.0, 0.0, -GUIDE["skirt_depth"]))
    for x, z in pat["positions_xz"]:
        u, v = x - C.HIP_C[0], z - C.HIP_C[1]
        man = man - m3d.Manifold.cylinder(GUIDE["block_h"] + 2.0, GUIDE["bore_d"] / 2, GUIDE["bore_d"] / 2, 64).translate(
            (u, v, -1.0))
    man = man - m3d.Manifold.cylinder(GUIDE["block_h"] + 2.0, GUIDE["window_d"] / 2, GUIDE["window_d"] / 2, 96).translate(
        (0.0, 0.0, -1.0))
    return _from_manifold(man), pat


def insert_guide(write: bool = True) -> dict:
    """Export the guide (STL / 3MF, test_pieces/hip_insert_guide), slice-check it (bores on the pattern, one closed
    shell, bed fit with brim) and place it on the frame print (no clash, bores over the pilots)."""
    import manifold3d as m3d
    import trimesh
    from shapely.geometry import Polygon
    from . import h1_closeout as C
    from . import hip_mount as HM
    from .surface import _to_manifold, export as ex
    g, pat = insert_guide_mesh()
    files = ex(g, PIECES / "hip_insert_guide") if write else []
    out = {"files": [str(Path(f).relative_to(ROOT)) for f in files], "watertight": bool(g.is_watertight),
           "shells": len(g.split(only_watertight=False)), "extents_mm": [round(v, 2) for v in g.extents],
           "g_paht": round(g.volume * RHO_PAHT, 1), "params": GUIDE}
    s = g.section(plane_origin=[0.0, 0.0, GUIDE["block_h"] / 2], plane_normal=[0.0, 0.0, 1.0])
    holes = [Polygon(np.asarray(L)[:, :2]).buffer(0) for L in s.discrete]
    small = [h for h in holes if 30.0 < h.area < 60.0]
    want = np.asarray(pat["positions_xz"]) - np.asarray(C.HIP_C)
    got = np.array([h.centroid.coords[0] for h in small])
    out["bores"] = len(small)
    out["bore_d_eq_mm"] = sorted({round(2 * math.sqrt(h.area / math.pi), 2) for h in small})
    out["bore_pos_err_mm"] = round(float(max(np.min(np.linalg.norm(got - w, axis=1)) for w in want)), 3)
    from .h1_lanes import BED_MM, BRIM_MM
    out["bed_fit_with_brim"] = bool(max(g.extents[:2]) + 2 * BRIM_MM <= min(BED_MM))
    # on the frame: local z -> frame -y from the boss face, local (x, y) -> frame (x, z - 120)
    T = np.eye(4)
    T[:3, :3] = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
    T[:3, 3] = [C.HIP_C[0], HM.FACE_Y - 0.02, C.HIP_C[1]]
    gf = g.copy()
    gf.apply_transform(T)
    fr = _to_manifold(_mesh())
    out["frame_clash_mm3"] = round((fr ^ _to_manifold(gf)).volume(), 3)
    out["material"] = ("PAHT-CF as the frame (ASSUMPTION GUIDE-HEAT: the iron tip works inside the insert; replace the "
                       "guide when a bore reads > 7.4 mm)")
    out["print"] = "block face down, skirt up (no supports: the bores and the window are vertical)"
    out["procedure"] = [
        "1. Guide on the boss, skirt over the D50 rim, pressed flat on the face.",
        f"2. START each insert through its bore: iron at the vendor temperature, push until the insert's top is level "
        f"with the guide's top face ({GUIDE['block_h']:g} mm above the boss face; the insert is then "
        f"{9.5 - GUIDE['block_h']:.1f} mm into the pilot with {GUIDE['block_h']:g} mm held straight in the bore).",
        "3. After insert 1: M5 x 12 + a 10 mm washer on the guide top, into insert 1, snug: the guide cannot turn; "
        "start inserts 2-8 the same way, let them cool 30 s each.",
        f"4. Unscrew, lift the guide off. FINISH each insert with a flat-faced tip: press it straight down the last "
        f"{GUIDE['block_h']:g} mm until flush with the boss face (the started axis guides it).",
        "5. Straight-edge + 0.2 mm feeler: no insert proud, none more than 0.2 mm low (INSERT-SET).",
        "6. Ti mount on: all 8 x M5 x 12 must start by hand through the D5.8 holes (first-article check of the scatter)."]
    out["pass"] = bool(out["watertight"] and out["shells"] == 1 and out["bores"] == 8 and out["bore_pos_err_mm"] < 0.05
                       and out["frame_clash_mm3"] < 0.5 and out["bed_fit_with_brim"])
    return out


def hip_mount_record() -> dict:
    """The redrawn mount with D5.8 holes (hip_mount, re-exported) checked as BL-056 checked it; FE cached."""
    from . import hip_mount as HM
    fe_p = OUT / "hip_fe.json"
    fe = json.loads(fe_p.read_text()) if fe_p.exists() else None
    if fe is None:
        fe = HM.part_fe()
        OUT.mkdir(parents=True, exist_ok=True)
        fe_p.write_text(json.dumps(fe, default=float))
    b56 = json.loads((ANALYSIS / "hip_mount_bl056.json").read_text())
    g = HM.geometry_check()
    f = HM.frame_fit()
    m = HM.mass()
    return {"stl": str(HM.OUT_STEM.with_suffix(".stl").relative_to(ROOT)), "hole_d_mm": HM.HOLE_D,
            "geometry": {k: g[k] for k in ("watertight", "shells", "base", "head_to_leg_mm", "head_to_head_mm",
                                           "driver_access_ok", "hole_edge_to_rim_mm", "hole_to_pin_hole_mm")},
            "frame_fit": {k: f[k] for k in ("clash_mm3", "tip_to_pilot_floor_mm", "thread_engagement_in_insert_mm",
                                            "boss_contact_mm2", "base_area_mm2", "pass")},
            "strip": HM.strip_check(), "fe_min_sf_over_goal": fe["min_sf_over_goal"],
            "fe_rows": {k: v["min_sf_all"] for k, v in fe["rows"].items()},
            "bl056_fe_min_sf_over_goal": b56["fe"]["min_sf_over_goal"],
            "mass_g": float(m["redraw_g"]), "bl056_g": float(b56["mass"]["redraw_g"]),
            "delta_g": round(float(m["redraw_g"]) - float(b56["mass"]["redraw_g"]), 2)}


# ============================================================================================ 4. heavy (M-5)
def body_stl(mesh=None) -> tuple:
    """The exported assembled print re-rastered on the H1 2 mm grid (element centres inside the section loops of
    every voxel layer, even-odd), plus the passive pad voxels the BL-053 body had (load pads), less the z 234 joint
    holes. Returns (solid, info) with the voxel differences against the BL-053 body."""
    from matplotlib.path import Path as MPath
    from . import frame_h1 as H1
    from . import h1_closeout as C
    m = mesh if mesh is not None else _mesh()
    c = H1.base()
    cen, dom = c["cen"], c["dom"]
    solid = np.zeros(len(cen), bool)
    zs = np.unique(np.round(cen[:, 2], 4))
    for z in zs:
        sel = np.where(np.isclose(cen[:, 2], z))[0]
        s = m.section(plane_origin=[0.0, 0.0, float(z) + 1e-4], plane_normal=[0.0, 0.0, 1.0])
        if s is None:
            continue
        k = np.zeros(sel.size, int)
        P = cen[sel, :2]
        for d in s.discrete:
            k += MPath(np.asarray(d)[:, :2]).contains_points(P)
        solid[sel] = (k % 2) == 1
    raster = solid.copy()
    old, _ = C.body_solid_bl053()
    solid |= old & dom.passive_solid
    solid &= ~c["holes"]
    boss = (np.hypot(cen[:, 0] - C.HIP_C[0], cen[:, 2] - C.HIP_C[1]) < 25.0) & (cen[:, 1] < -30.0)
    info = {"source": "print/frame_h1/h1_assembled.stl (BL-058 export), 2 mm element-centre raster",
            "stl_voxels": int(raster.sum()), "run_voxels": int(solid.sum()), "bl053_body_voxels": int(old.sum()),
            "in_both": int((solid & old).sum()), "stl_only": int((solid & ~old).sum()),
            "bl053_only": int((old & ~solid).sum()), "stl_only_outside_envelope": int((solid & ~old & dom.passive_void).sum()),
            "pads_added": int((old & dom.passive_solid & ~raster).sum()),
            "boss_voxels": {"run": int((solid & boss).sum()), "bl053": int((old & boss).sum())},
            "raster_g": round(float(solid.sum()) * H1.H ** 3 * RHO_PAHT, 1),
            "bl053_raster_g": round(float(old.sum()) * H1.H ** 3 * RHO_PAHT, 1)}
    return solid, info


def heavy(log=print) -> dict:
    """M-5: the US2 lug submodel on the exported print, then the whole body (nominal + sanded) on it. Cached."""
    from . import h1_closeout as C
    from . import h1_rev5 as R5
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "lug_us2.json"
    if not p.exists():
        t0 = time.time()
        r = R5.lug_check("us2", mesh=_mesh(), tag="bl058_print")
        r.pop("_field", None)
        r["seconds"] = round(time.time() - t0)
        p.write_text(json.dumps(r, indent=1, default=float))
        log(f"lug us2 done {r['design_min']} ({r['seconds']} s)")
    solid, info = body_stl()
    log(f"body raster {json.dumps(info)}")
    res = C.body(log=log, solid=solid, info=info, names=(BODY_STL, BODY_STL_SANDED), out=OUT / "body")
    (OUT / "body_done.json").write_text(json.dumps({"done": True, "voxels": info}, default=float))
    return res


# ============================================================================================ record
def body_record() -> dict | None:
    """Per basis: the BL-053 voxel body (BL-055 record), the exported print re-rastered (BL-058), nominal and sanded;
    margins against R1; member buckling (the worst members); the US2 lug submodel before / after."""
    from . import h1_buckling as B
    from . import h1_closeout as C
    p = {k: B.OUT / f"check_{n}.json" for k, n in (("bl053", C.BODY_CHECK), ("bl053_sanded", C.BODY_SANDED),
                                                    ("bl058", BODY_STL), ("bl058_sanded", BODY_STL_SANDED))}
    if not p["bl058"].exists():
        return None
    d = {k: json.loads(v.read_text()) for k, v in p.items() if v.exists()}

    def row(r):
        return {"strength": round(r["min"]["strength"], 3), "fatigue": round(r["min"]["fatigue"], 3),
                "creep": round(r["min"]["creep"], 3), "buckling": round(r["buckling_min"], 3),
                "joint_strength": round(r["joint_strength"], 3), "joint_fatigue": round(r["joint_fatigue"], 3),
                "governing_tag": r.get("governing_tag")}
    out = {"bases": {}, "voxels": json.loads((OUT / "body" / "body_solid.json").read_text())
           if (OUT / "body" / "body_solid.json").exists() else None}
    for b in B.BASES_CHECK:
        out["bases"][b] = {k: row(v[b]) for k, v in d.items() if b in v}
    static = [b for b in B.BASES_CHECK if not b.endswith(".cyc")]
    gov = "bl058_sanded" if "bl058_sanded" in d and all(b in d["bl058_sanded"] for b in B.BASES_CHECK) else "bl058"
    out["governing_run"] = gov
    out["min"] = {"static_cinch": {k: min(out["bases"][b][gov][k] for b in static)
                                   for k in ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")},
                  "cinch_cycled": {k: out["bases"]["fine_sm8.cyc"][gov][k]
                                   for k in ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")}
                  if "fine_sm8.cyc" in out["bases"] and gov in out["bases"]["fine_sm8.cyc"] else None}
    out["min_bl055"] = {"static_cinch": {k: min(out["bases"][b]["bl053_sanded"][k] for b in static)
                                         for k in ("strength", "fatigue", "creep", "buckling")},
                        "cinch_cycled": {k: out["bases"]["fine_sm8.cyc"]["bl053_sanded"][k]
                                         for k in ("strength", "fatigue", "creep", "buckling")}}
    bk_new, bk_old = d["bl058"]["fine_sm8"]["buckling"], d["bl053"]["fine_sm8"]["buckling"]
    out["members_fine_sm8"] = {k: {"A_mm2": v["A_mm2"], "A_bl053_mm2": bk_old[k]["A_mm2"], "Pcr_n": round(v["Pcr_n"], 1),
                                   "P_factored_n": round(v["P_factored_n"], 1), "margin": v["margin"],
                                   "margin_bl053": bk_old[k]["margin"]} for k, v in bk_new.items()}
    out["governing_region"] = d["bl058"].get("governing_region")
    out["top_regions_fine_sm8"] = d["bl058"]["fine_sm8"].get("top_regions")
    out["keepouts"] = d["bl058"].get("keepouts")
    out["raster_g"] = {"bl053": round(d["bl053"]["raster_g"], 1), "bl058_stl": round(d["bl058"]["raster_g"], 1)}
    out["R1"] = "SF / requirement >= 1 on every basis (load_standard rev C); the cinch-cycled basis is held below R1 " \
                "for MT-1 since BL-024 (h1_closeout.md)"
    lug = json.loads((OUT / "lug_us2.json").read_text()) if (OUT / "lug_us2.json").exists() else None
    r5 = json.loads((ANALYSIS / "h1_rev5.json").read_text())["lugs"]["us2"]["print"]
    if lug:
        out["us2_lug"] = {"bl058": lug["design_min"], "bl053": r5["design_min"],
                          "families_bl058": {k: {kk: v[kk] for kk in ("strength", "fatigue", "region")}
                                             for k, v in lug["families"].items()},
                          "families_bl053": {k: {kk: v[kk] for kk in ("strength", "fatigue", "region")}
                                             for k, v in r5["families"].items()}}
    return out


def p_us2_bearing() -> float:
    """US2 outer cheek's pin bearing length under the counterbore (mm)."""
    from . import h1_bedfit as BF
    return stations_R()["us2"]["geom"].cheek - BF.PIN_CBORE_DEPTH


SLEEVE_GOAL = 1.0                     # the pin rows are factored (2.4 = 1.6 g x 1.5): SF on yield >= 1 (as bag_attach.pin_check)


def sleeve_bearing() -> dict:
    """The US2 outer cheek's UHMWPE sleeve under the counterbore (6.5 of 8 mm since the BL-058 follow-up; 6 with the
    first 2 mm counterbore). Projected bearing F_share / (d_pin x L) on the pin rows' y-z forces (h1_closeout.json
    pins.us2 bending: factored), against the uhmwpe_sheet yield; goal SLEEVE_GOAL on every row incl. dy 95 / share 1."""
    from huntkit.materials import load
    sy = float(load("uhmwpe_sheet").require("yield_strength_mpa"))
    co = json.loads((ANALYSIS / "h1_closeout.json").read_text())["pins"]["stations"]["us2"]["bending"]
    Lnow = p_us2_bearing()
    rows = {}
    for row, F in (("design", co["design_yz_n"]), ("dy95", co["dy95_yz_n"])):
        for sh in (0.6, 1.0):
            for L in sorted({8.0, 6.0, Lnow}):
                s_ = sh * F / (5.0 * L)
                rows[f"{row}|share{sh:g}|L{L:g}"] = {"sigma_mpa": round(s_, 2), "sf_yield": round(sy / s_, 3)}
    now = {k: v for k, v in rows.items() if k.endswith(f"|L{Lnow:g}")}
    return {"yield_mpa": sy, "bearing_now_mm": Lnow, "goal": SLEEVE_GOAL, "rows": rows,
            "min_now": min(v["sf_yield"] for v in now.values()),
            "min_design_now": min(v["sf_yield"] for k, v in now.items() if k.startswith("design")),
            "pass": bool(min(v["sf_yield"] for v in now.values()) >= SLEEVE_GOAL),
            "note": "factored rows (2.4 basis); the 1 mm liner is backed by the PAHT cheek (confined): uniaxial yield "
                    "is a lower bound. L6 = the first counterbore (2 mm), L8 = no counterbore."}


def head_check() -> dict:
    """The thinner US2 pin head (D8 x 1.0, 7075-T6 as the US2 pins; Ti-6Al-4V for reference) under the axial loads it
    can see: PIN-RET (a) 50 N push and a walking pin (WALK-MU 0.2 x the dy 95 y-z force), the larger x 1.5 as a proof
    margin row. Checks: head shear-off at the shank root (tau = F / (pi d t)); head flange bending as an annular strip
    fixed at the shank (r 2.5) loaded by uniform bearing out to r 4 (sigma = 3 p (b - a)^2 / t^2, conservative against
    the annular-plate value); pull-through bearing on the counterbore floor annulus (sleeve end + PAHT, r 2.6-4.0)
    against the PAHT-CF xy strength with its knock-down (bag_attach._paht)."""
    from huntkit.materials import load
    from . import bag_attach as BA
    co = json.loads((ANALYSIS / "h1_closeout.json").read_text())["pins"]["stations"]["us2"]["bending"]
    loads = {"PIN-RET (a) push": 50.0, "walk (0.2 x dy95)": round(0.2 * co["dy95_yz_n"], 1)}
    loads["proof (1.5 x max)"] = round(1.5 * max(loads.values()), 1)
    t, a_, b_ = US2_HEAD_T, 2.5, HEAD_D / 2
    A_bear = math.pi * (b_ ** 2 - 2.6 ** 2)
    pa = BA._paht()
    s_paht = pa["s_xy"] * pa["knock"]
    out = {"head_mm": [HEAD_D, t], "loads_n": loads, "bearing_area_mm2": round(A_bear, 1), "paht_allow_mpa":
           round(s_paht, 1), "rows": {}}
    for mat in ("alu_7075_t6", "ti_6al_4v"):
        m = load(mat)
        sy = float(m.get("yield_strength_sbasis_mpa") or m.require("yield_strength_mpa"))
        for lab, F in loads.items():
            tau = F / (math.pi * 5.0 * t)
            p_ = F / A_bear
            sig = 3.0 * p_ * (b_ - a_) ** 2 / t ** 2
            out["rows"][f"{mat}|{lab}"] = {"tau_mpa": round(tau, 2), "sf_shear": round(0.577 * sy / tau, 1),
                                           "sigma_flange_mpa": round(sig, 2), "sf_flange": round(sy / sig, 1),
                                           "bearing_mpa": round(p_, 2), "sf_pull_through": round(s_paht / p_, 1)}
    out["min_sf"] = min(min(v["sf_shear"], v["sf_flange"], v["sf_pull_through"]) for v in out["rows"].values())
    out["pass"] = bool(out["min_sf"] >= 2.0)
    out["note"] = "the US2 pins are 7075-T6 (not Ti); Ti rows for reference"
    return out


def BF_CB() -> float:
    from . import h1_bedfit as BF
    return BF.PIN_CBORE_DEPTH


def mass_rows(res: dict) -> dict:
    """BL058 ledger deltas, every one from a file or a record: the print (assembled now - the 6b0cde1 copy), the hip
    mount (STL now - hip_mount_bl056.json redraw_g), the 6 hip screws BL-055 booked (x 12 - x 14), the 12 pins and
    their retainers + tethers (h1_closeout.pins with and without the BL-058 overlay), the US2 outer sleeves (8 -> 6.5)."""
    import trimesh
    from . import bag_attach as BA
    from . import h1_closeout as C
    from huntkit.materials import load
    a = trimesh.load(PRINT / "h1_assembled.stl", force="mesh").volume
    b = trimesh.load(BEFORE / "h1_assembled.stl", force="mesh").volume if (BEFORE / "h1_assembled.stl").exists() \
        else None
    pr_new, pr_old = C.pins(bl058=True), C.pins(bl058=False)
    hs = res["hip_screws"]["rows"]
    n_scr = C.HIP_CHOSEN[0] - C.HIP_INSERTS_BOOKED
    rho_pe = float(load("uhmwpe_sheet").require("density_kg_m3")) * 1e-6
    sleeve_mm3_per_mm = math.pi * ((BA.HOLE_D / 2) ** 2 - (BA.PIN_D / 2 + 0.1) ** 2)
    prev = json.loads(RESULTS.read_text())["mass"]["print_delta_g"] if b is None and RESULTS.exists() else None
    out = {"print_delta_g": round((a - b) * RHO_PAHT, 3) if b is not None else prev,   # no copy: keep the published
           "print_basis": "assembled print mesh BL-058 - the 6b0cde1 copy (outputs/bl058/before) x 1.06 g/cm3",
           "mount_delta_g": res["hip_mount"]["delta_g"],
           "hip_screws_delta_g": round(n_scr * (hs[f"x{C.HIP_SCREW_L:g}"]["mass_g"] - hs[f"x{C.HIP_SCREW_L_BOOKED:g}"]["mass_g"]), 3),
           "hip_screws_n": n_scr,
           "pins_delta_g": round(pr_new["mass_bl058"]["pins_g"] - pr_old["mass"]["pins_g"], 3),
           "retainers_delta_g": round(pr_new["mass_bl058"]["retainers_tethers_g"] - pr_old["mass"]["clips_tethers_g"], 3),
           "sleeves_delta_g": round(-2 * BF_CB() * sleeve_mm3_per_mm * rho_pe, 3),
           "pins_bl058_g": pr_new["mass_bl058"]["pins_g"], "retainers_bl058_g": pr_new["mass_bl058"]["retainers_tethers_g"],
           "pins_bl055_g": pr_old["mass"]["pins_g"], "retainers_bl055_g": pr_old["mass"]["clips_tethers_g"]}
    out["frame_delta_g"] = round(sum(out[k] or 0.0 for k in ("print_delta_g", "mount_delta_g", "hip_screws_delta_g")), 3)
    out["attachment_delta_g"] = round(sum(out[k] for k in ("pins_delta_g", "retainers_delta_g", "sleeves_delta_g")), 3)
    return out


def kit_rows(res: dict) -> dict:
    """What the BL-057 wiring pass needs for the kit and BUILD_H1: PIN-RET (d), the FIT-US colour marks, the nut and
    screw lines, the hip guide, the pin BOM."""
    hc = res.get("us_route_heads") or {}
    return {
        "PIN-RET_d": {"id": "PIN-RET", "step": "(d)", "what": "bag on, loaded (the FIT-US 20 kg stand-in quarter in the "
                      "cradle, US straps cam-tight), 10 min, then bag off",
                      "pass": "no retainer, tether or pin-head marks on B-01 or the bag's side panel (chalk / lipstick "
                              "on every hairpin clip, the two US2 E-clips, the US2 tethers and pin heads before; look for "
                              "colour on the cloth)", "settles": ["CLIP-ENV", "TETHER-US2", "PIN-HEAD"]},
        "FIT-US_marks": ["US2 clevis bolt heads (2 per side)", "US2 pin head in its counterbore (1 per side)",
                         "US2 clevis outer face edges", "US2 E-clip (inboard, 1 per side)",
                         "US2 tether strand on the lug arm's bag face (1 per side)",
                         "US1 hairpin clip body (inboard, fore of the pin)"],
        "FIT-US_pass": f"no colour on the bag from any mark; pin head recess {hc.get('pin_head_recess_mm')} mm below the "
                       "clevis face (0.5 mm feeler across the head)",
        "nut": {"spec": "M5 hex nut A2 DIN 934, m = 4.0 mm (3.7-4.0), 8 AF",
                "caliper": "m <= 4.1 mm on every nut before assembly (ISO 4032 M5 is 4.4-4.7 and does not seat at US2)",
                "bolt_caliper": "M5 x 35 (US2) length 34.7-35.3 mm: longer bottoms in the tail hole (0.5 mm room), "
                                "shorter leaves < 0.6 pitch past the nut"},
        "hip_screw": {"spec": "Ti gr5 M5 x 12 DIN 7984 (8)", "key": "3 mm hex screwdriver", "was": "M5 x 14, 4 mm key"},
        "hip_guide": {"file": "designs/pack_5200/print/frame_h1/test_pieces/hip_insert_guide.stl",
                      "procedure": res["insert_guide"]["procedure"]},
        "pins_bom": res["pins"]["bom"],
    }


def compute(log=print) -> dict:
    from . import h1_bedfit as BF
    from . import h1_closeout as C
    res = {"ticket": "BL-058", "date": DATE, "review": "designs/pack_5200/analysis/review_20261121_sixth.md",
           "sources": SRC}
    m = _mesh()
    res["nut_check"] = nut_check(m)
    res["retainers"] = retainer_checks(m, json.loads((ANALYSIS / "us_route.json").read_text()))
    res["pin_rows"] = {n: pin_row(n) for n in STATION_RET}
    res["pins"] = {k: v for k, v in C.pins().items() if k in ("scheme", "retainer", "stations", "bom", "mass_bl058")}
    res["groove"] = groove_check()
    res["sleeve_bearing"] = sleeve_bearing()
    res["head_check"] = head_check()
    res["cbore"] = {"d_mm": BF.PIN_CBORE_D, "depth_mm": BF.PIN_CBORE_DEPTH, "head_mm": [HEAD_D, US2_HEAD_T],
                    "recess_mm": round(BF.PIN_CBORE_DEPTH - US2_HEAD_T, 2), "wall_to_cheek_tip_mm":
                    round(stations_R()["us2"]["y_tip"] - stations_R()["us2"]["y_pin"] - BF.PIN_CBORE_D / 2, 2),
                    "outer_cheek_bearing_mm": stations_R()["us2"]["geom"].cheek - BF.PIN_CBORE_DEPTH}
    usr = json.loads((ANALYSIS / "us_route.json").read_text())
    res["us_route_heads"] = {k: v for k, v in usr["clevis_heads"].items() if k not in ("method",)}
    res["us_route_layout"] = {"worst_clear_mm": usr["layouts"]["now"]["worst_clear_mm"],
                              "pass": usr["layouts"]["now"]["pass"], "md5": usr["print"]["md5"]}
    res["body"] = body_record()
    res["hip_screws"] = hip_screws()
    res["hip_holes"] = hip_holes()
    res["insert_guide"] = insert_guide()
    res["hip_mount"] = hip_mount_record()
    res["stl"] = stl_record()
    res["mass"] = mass_rows(res)
    res["kit"] = kit_rows(res)
    res["assumptions"] = [{"id": a, "text": t, "settled_by": s_} for a, t, s_ in ASSUMPTIONS]
    return res


def stl_record() -> dict:
    """Closed single shells and bed fit of every re-exported file; the halves' volumes against the 6b0cde1 copies."""
    import trimesh
    from . import h1_bedfit as BF
    out = {}
    for f in ("h1_assembled", "h1_lower_flat", "h1_upper_flat", "us2_clevis_L", "us2_clevis_R"):
        a = trimesh.load(PRINT / f"{f}.stl", force="mesh")
        r = {"watertight": bool(a.is_watertight), "shells": len(a.split(only_watertight=False)),
             "g": round(a.volume * RHO_PAHT, 2), "has_3mf": (PRINT / f"{f}.3mf").exists() or f == "h1_assembled"}
        if (BEFORE / f"{f}.stl").exists():
            b = trimesh.load(BEFORE / f"{f}.stl", force="mesh")
            r["delta_g"] = round((a.volume - b.volume) * RHO_PAHT, 3)
        out[f] = r
    out["bed"] = {nm: BF.bed_check(PRINT / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    from .h1_lanes import BED_MM, BRIM_MM
    for nm in ("us2_clevis_L", "us2_clevis_R"):
        e = trimesh.load(PRINT / f"{nm}.stl", force="mesh").extents
        out[nm]["bed_fit_with_brim"] = bool(sorted(e)[-1] + 2 * BRIM_MM <= min(BED_MM))
    for f in ("us_route_stay_R", "us_route_stay_R_frame_coords", "hip_insert_guide"):
        a = trimesh.load(PIECES / f"{f}.stl", force="mesh")
        out[f] = {"watertight": bool(a.is_watertight), "shells": len(a.split(only_watertight=False)),
                  "g": round(a.volume * RHO_PAHT, 2)}
    return out


ASSUMPTIONS = [
    ("BOLT-LEN", "M5 x 35 / x 45 length within +/-0.5 mm (ISO 4759-1 grade A js15).",
     "Caliper every bolt: US2 M5 x 35 must read 34.7-35.3 (tail room 0.5 mm, tip past the nut 1.0 mm nominal)."),
    ("CLIP-FIT", "McMaster 90153A214 (for a 3/16 in = 4.76 mm shaft) springs over the 5.0 mm pin and holds.",
     "PIN-RET (a): 50 N push on the tail moves the pin < 0.5 mm; fallback 90153A216."),
    ("CLIP-ENV", f"The hairpin clip's straight leg stands <= {CLIP_TIP_PAST_PIN:g} mm past the pin aft; the clip body "
     f"(<= {HAIRPIN['length'] + HAIRPIN['wire_d']:.1f} mm) lies fore, within +/-{5.0 / 2 + HAIRPIN['wire_d'] + 0.5:.1f} mm "
     "of the pin axis in z.", "Caliper one clip seated on a pin; PIN-RET (d)."),
    ("CLIP-MASS", f"Hairpin clip {HAIRPIN['mass_g']:g} g (wire volume), E-clip {ECLIP['mass_g']:g} g (75 % of the "
     "annulus).", "Weigh 10 of each on receipt."),
    ("GROOVE-LAND", f"{GROOVE_LAND:g} mm from the E-clip groove to the tether hole (3 x the 0.5 mm groove depth).",
     "PIN-RET (a) on the US2 pin: 50 N push, the ring stays seated."),
    ("WALK-MU", "A walking pin pushes on its retainer with <= 0.2 x the largest y-z pin force (the eye's pull along the "
     "pin bears on the cheek).", "PIN-RET (b): every retainer seated after the T9 walk and the cycle tests."),
    ("KT-GROOVE", f"Kt {KT_GROOVE:g} for the groove in bending (only used for the misplaced-groove sensitivity).",
     "Not needed while the groove is outboard of the cheek (M = 0 there); PIN-RET (a) measures its position."),
    ("TETHER-US2", "The US2 tether's strand across the lug arm's bag face (1.5 mm cord) leaves no mark on B-01; the free "
     "drapes reach it (-0.6 mm, the bag rests on the arm there).", "PIN-RET (d) and FIT-US marks."),
    ("INSERT-SET", f"Inserts set flush to {INSERT_SET_TOL:g} mm low.", "Straight-edge + feeler before the mount goes on."),
    ("SLM-POS", f"SLM hole-pattern position {MOUNT_POS_T:g} mm diametral.", "Vendor CMM report or a pin-gauge plate."),
    ("INSERT-SCATTER", f"Set-insert position error {SCATTER['guided']:g} mm radial with the guide, "
     f"{SCATTER['freehand']:g} mm freehand (no published figure found).",
     "First article: all 8 M5 x 12 start by hand through the D5.8 mount; pin gauge per insert."),
    ("GUIDE-HEAT", "The PAHT-CF guide's bores survive 8 insert starts (the iron tip works inside the insert).",
     "Bore <= 7.4 mm after use (caliper)."),
    ("KEY-D", "A 3 mm hex screwdriver blade sweeps a D4 envelope (3.46 across corners + 0.5).", "First-article assembly."),
    ("RASTER-2MM", "The whole-body check on the print uses the assembled STL rastered on the 2 mm H1 grid: member "
     "sections read 3-8 % below the BL-053 voxel body (the print surface is smoother; the STL slice of the upper branch "
     "is 144-147 mm2 against 152-160 voxel mm2), so the member buckling margins drop.", "CA-5 / BU-1 member tests."),
]


def report(log=print) -> dict:
    res = compute(log=log)
    try:
        res["screenshots"] = figures(res)
    except Exception as e:  # pragma: no cover
        log(f"figures failed: {e}")
        res["screenshots"] = []
    RESULTS.write_text(json.dumps(res, indent=1, default=_jd))
    return res


def _jd(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


# ============================================================================================ figures
def _save(fig, name: str) -> str:
    import matplotlib.pyplot as plt
    SCREENS.mkdir(parents=True, exist_ok=True)
    path = SCREENS / name
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    if path.stat().st_size > 1.5e6:          # phone rule
        from PIL import Image
        im = Image.open(path)
        im = im.resize((int(im.width * 0.75), int(im.height * 0.75)))
        im.save(path, optimize=True)
    return str(path.relative_to(ROOT))


def _sec_x(mesh, x):
    from shapely.geometry import Polygon
    s = mesh.section(plane_origin=[x, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
    A = None
    for L in ([] if s is None else s.discrete):
        P = Polygon(np.asarray(L)[:, 1:3]).buffer(0)
        A = P if A is None else A.symmetric_difference(P)
    return A


def _sec_z(mesh, z):
    from shapely.geometry import Polygon
    s = mesh.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    A = None
    for L in ([] if s is None else s.discrete):
        P = Polygon(np.asarray(L)[:, :2]).buffer(0)
        A = P if A is None else A.symmetric_difference(P)
    return A


def _fill(ax, A, **kw):
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    if A is None:
        return
    for g in getattr(A, "geoms", [A]):
        verts, codes = [], []
        for ring in [g.exterior] + list(g.interiors):
            c = np.asarray(ring.coords)
            verts += c.tolist()
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))


def plot_retainers(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    m = _mesh()
    st = stations_R()
    fig, axs = plt.subplots(2, 4, figsize=(17, 9.2))
    rr = res["retainers"]["rows"]
    for ax, name in zip(axs.ravel()[:6], ("hinge", "us1", "us2", "im1", "im2", "im3")):
        p = st[name]
        r = rr[name]
        lo, hi = r["retainer_box"]["lo"], r["retainer_box"]["hi"]
        xs = 0.5 * (lo[0] + hi[0])
        _fill(ax, _sec_x(m, xs), fc="#c9c3b8", ec="#5d5a54", lw=0.8)
        ax.add_patch(Circle((p["y_pin"], p["z"]), 2.5, fc="#888", ec="k", lw=0.8, zorder=3))
        col = "#c0392b" if r["retainer"] == "hairpin" else "#1f6fb4"
        if r["retainer"] == "hairpin":
            ax.add_patch(Rectangle((lo[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], fc=col, alpha=0.35, ec=col, lw=1.2,
                                   zorder=4, label="hairpin clip envelope"))
        else:
            ax.add_patch(Circle((p["y_pin"], p["z"]), (hi[1] - lo[1]) / 2, fc=col, alpha=0.35, ec=col, lw=1.2,
                                zorder=4, label="E-clip DIN 6799 RS 4"))
        ax.axvline(p["y_tip"], color="#8e44ad", lw=1.5, ls="--", label="cheek-tip plane (B-01)")
        ax.axvline(p["y_tip"] - B01_RULE, color="#8e44ad", lw=0.7, ls=":")
        ax.set_xlim(p["y_pin"] - 30, p["y_pin"] + 14)
        ax.set_ylim(p["z"] - 18, p["z"] + 18)
        ax.set_aspect("equal")
        ax.set_xlabel("frame y (mm, + to the bag)", fontsize=8)
        ax.set_ylabel("frame z (mm)", fontsize=8)
        extra = ""
        if "strap_mm" in r:
            extra = f"; strap {r['strap_mm']['min_mm']:.1f} mm"
        if "he" in r:
            extra = f"; hinge eye {r['he']['min_mm']:.1f} mm"
        ax.set_title(f"{name.upper()} far side |x| {xs:.1f}: {r['retainer']}\nB-01 plane {r['below_b01_plane_mm']:.1f} mm "
                     f"above it, print clash {max(v for k, v in r.items() if k.endswith('_mm3_at_0.5mm')):.2f} mm3"
                     f"{extra}", fontsize=8.5, loc="left")
        ax.legend(fontsize=6.5, loc="lower left")
    # US2 plan at the pin height
    ax = axs[1, 2]
    p = st["us2"]
    _fill(ax, _sec_z(m, p["z"]), fc="#c9c3b8", ec="#5d5a54", lw=0.8)
    pr = res["pin_rows"]["us2"]
    xh = pr["head_seat_abs_x"]
    ax.add_patch(Rectangle((pr["far_face_abs_x"] - pr["tail_past_far_face_mm"], p["y_pin"] - 2.5),
                           xh - pr["far_face_abs_x"] + pr["tail_past_far_face_mm"], 5.0, fc="#888", ec="k", lw=0.6))
    ax.add_patch(Rectangle((xh, p["y_pin"] - 4.0), US2_HEAD_T, 8.0, fc="#555", ec="k", lw=0.6, label="pin head D8 x 1.0"))
    ex = rr["us2"]["retainer_box"]
    ax.add_patch(Rectangle((ex["lo"][0], ex["lo"][1]), ex["hi"][0] - ex["lo"][0], ex["hi"][1] - ex["lo"][1], fc="#1f6fb4",
                           alpha=0.6, label="E-clip"))
    tr = tether_route("us2")
    P = np.asarray(tr["polyline_free_R"])
    ax.plot(P[:, 0], P[:, 1], color="#e67e22", lw=2.0, label="tether (free run)")
    ax.plot([tr["arm_section"]["x"]] * 2, tr["arm_section"]["y"], color="#e67e22", lw=2.0, ls="--",
            label="tether loop round the arm")
    ax.axhline(p["y_tip"], color="#8e44ad", lw=1.2, ls="--")
    ax.axvline(183.0, color="k", lw=0.6, ls=":")
    ax.set_xlim(120, 190)
    ax.set_ylim(-16, 30)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)", fontsize=8)
    ax.set_ylabel("frame y (mm)", fontsize=8)
    ax.set_title(f"US2 plan at z {p['z']:.0f}: head {res['cbore']['recess_mm']:.1f} mm below the clevis\nface (D9 x 1.5 "
                 f"cbore); E-clip groove {pr['features']['groove']['from_far_cheek_face_mm']} mm\npast the inner "
                 f"cheek; tether cord {cord_len('us2'):.0f} mm", fontsize=8.5, loc="left")
    ax.legend(fontsize=6.5, loc="lower left")
    ax = axs[1, 3]
    ax.axis("off")
    lines = ["Retainer per station (R side; L mirrors)", ""]
    for n, r in res["pin_rows"].items():
        lines.append(f"{n.upper():6s} {r['retainer']:8s} shank {r['shank_mm']:.1f} mm, tail {r['tail_past_far_face_mm']:.2f}")
    lines += ["", "hairpin: McMaster 90153A214, 18-8, 0.79 wire,", "  12.7 long; cross hole D1.5, body fore (-y)",
              "US2: DIN 6799 RS 4 E-clip (1.4122),", "  groove D4.0 x 0.74; tether from a tail hole",
              "", f"nut: DIN 934 seats everywhere: {res['nut_check']['DIN 934_seats_everywhere_at_m_max']}",
              f"ISO 4032 seats everywhere: {res['nut_check']['ISO 4032_seats_everywhere_at_m_max']}"]
    ax.text(0.0, 1.0, "\n".join(lines), va="top", family="monospace", fontsize=8.5)
    fig.suptitle("BL-058 (review 6 M-2): pin retainers drawn per station on the exported print", fontsize=11, x=0.01,
                 ha="left")
    fig.tight_layout()
    return _save(fig, f"{SHOT}1.png")


def plot_head(res: dict) -> str:
    """US2 pin head: the clevis section through the pin (z 142), 6b0cde1 (head proud) against BL-058 (counterbore), with
    the cloth of the 19 / 23 in fill drapes near the head (both sides, mirrored to R) and the clearance bars."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import trimesh
    sys.path.insert(0, str(PACK))
    import us_route as U
    F = U._F()
    p = stations_R()["us2"]
    hc = res["us_route_heads"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.25, 1.0]})
    for path, col, lab, lw in ((BEFORE / "h1_assembled.stl", "#999", "6b0cde1 (review 6)", 2.4),
                               (PRINT / "h1_assembled.stl", "#1f6fb4", "BL-058", 1.2)):
        if not path.exists():
            continue
        A = _sec_z(trimesh.load(path, force="mesh"), p["z"])
        for g in getattr(A, "geoms", [A]):
            c = np.asarray(g.exterior.coords)
            a1.plot(c[:, 0], c[:, 1], color=col, lw=lw)
            for h in g.interiors:
                c = np.asarray(h.coords)
                a1.plot(c[:, 0], c[:, 1], color=col, lw=lw)
        a1.plot([], [], color=col, lw=lw, label=lab)
    a1.add_patch(Rectangle((183.0, p["y_pin"] - 4.0), 1.5, 8.0, fc="#e74c3c", alpha=0.5, label="head before: proud 1.5"))
    a1.add_patch(Rectangle((hc["pin_head_x_mm"][0], p["y_pin"] - 4.0), 1.5, 8.0, fc="#2c3e50", alpha=0.8,
                           label=f"head now: {hc['pin_head_recess_mm']} below the face"))
    cols = {19: "#27ae60", 23: "#e67e22"}
    m = None
    for t in (19, 23):
        m = F.fine_mesh(t)
        X = F.drape(U.RUN.format(t=t), "fill")
        if X is None:
            continue
        S = F.ClothSurface(X, m["tris"]).S
        for side, sx, mk in (("R", 1.0, "o"), ("L", -1.0, "^")):
            Q = S.copy()
            Q[:, 0] *= sx
            sel = (np.abs(Q[:, 2] - p["z"]) < 2.0) & (Q[:, 0] > 170) & (Q[:, 0] < 200) & (Q[:, 1] > -5) & (Q[:, 1] < 35)
            a1.plot(Q[sel, 0], Q[sel, 1], mk, ms=2.2, color=cols[t], alpha=0.6, label=f"{t} in fill {side} cloth (z +/-2)")
    a1.set_xlim(170, 198)
    a1.set_ylim(-2, 32)
    a1.set_aspect("equal")
    a1.set_xlabel("frame x (mm)")
    a1.set_ylabel("frame y (mm)")
    a1.legend(fontsize=6.5, loc="lower left", ncol=1)
    a1.set_title("US2 clevis at the pin (z 142): D9 x 1.5 counterbore, head 1.0; the free drape passes through the clevis\n(no "
                 "frame outboard of the stays in the sim): the real cloth tents over the face", fontsize=9, loc="left")
    rows = [r for r in hc["pin_rows"] if r["case"] == "fill" and r["torso"] in (19, 23)]
    labs = [f"{r['torso']} in {r['side']}" for r in rows]
    rev = {("23", "R"): -0.6, ("19", "R"): -0.3, ("23", "L"): 0.9}
    yy = np.arange(len(rows))
    a2.barh(yy + 0.2, [r.get("pin_head_outside_clevis_mm", np.nan) for r in rows], height=0.38, color="#1f6fb4",
            label="BL-058: head to the cloth that can be there")
    a2.barh(yy - 0.2, [rev.get((str(r["torso"]), r["side"]), np.nan) for r in rows], height=0.38, color="#e74c3c",
            label="review 6 (head proud, its numbers)")
    a2.axvline(hc["bolt_head_rule_recess_mm"], color="k", lw=1, ls="--", label="bolt-head rule 0.5 mm")
    a2.set_yticks(yy, labs)
    for i, r in enumerate(rows):
        v = r.get("pin_head_outside_clevis_mm")
        a2.text((v or 0) + 0.1, i + 0.2, f"{v:+.1f}", va="center", fontsize=8)
    a2.set_xlabel("cloth clearance to the pin head (mm)")
    a2.legend(fontsize=7, loc="lower right")
    a2.set_title(f"19 / 23 in fill drapes, both sides: min {hc['pin_head_outside_clevis_min_mm']:+.1f} mm (all drapes);"
                 f"\nE-clip {hc['eclip_cloth_min_mm']:+.1f}, tether {hc['tether_cloth_min_mm']:+.1f} (on the arm)",
                 fontsize=9, loc="left")
    fig.tight_layout()
    return _save(fig, f"{SHOT}2.png")


def plot_body(res: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import frame_h1 as H1
    from . import h1_closeout as C
    b = res["body"]
    fig, axs = plt.subplots(1, 3, figsize=(18, 8.0), gridspec_kw={"width_ratios": [1.15, 1.0, 0.9]})
    ax = axs[0]
    keys = ("strength", "fatigue", "creep", "buckling", "joint_strength", "joint_fatigue")
    labs, old, new = [], [], []
    for bs in b["bases"]:
        for k in keys:
            labs.append(f"{bs}  {k.replace('_', ' ')}")
            old.append(b["bases"][bs].get("bl053_sanded", {}).get(k, np.nan))
            new.append(b["bases"][bs].get("bl058_sanded", {}).get(k, np.nan))
    yy = np.arange(len(labs))[::-1]
    ax.barh(yy + 0.2, old, height=0.38, color="#bbb", label="BL-055 record (voxel body, sanded)")
    ax.barh(yy - 0.2, new, height=0.38, color="#1f6fb4", label="BL-058: exported print re-rastered, sanded")
    for y_, v in zip(yy, new):
        ax.text(v + 0.03, y_ - 0.2, f"{v:.2f}", va="center", fontsize=6.5)
    ax.axvline(1.0, color="k", lw=1)
    ax.set_yticks(yy, labs, fontsize=7)
    ax.set_xlabel("SF / requirement (R1: >= 1)")
    ax.set_xlim(0, 3.1)
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title("Whole body on every basis, the print as exported (boss, BL-056 blocks in).\nfine_sm8.cyc = cinch-"
                 "cycled basis (held below R1 for MT-1 since BL-024)", fontsize=9, loc="left")
    ax = axs[1]
    mem = b["members_fine_sm8"]
    names = list(mem)
    yy = np.arange(len(names))
    ax.barh(yy + 0.2, [mem[n]["margin_bl053"] for n in names], height=0.38, color="#bbb", label="BL-053 voxel body")
    ax.barh(yy - 0.2, [mem[n]["margin"] for n in names], height=0.38, color="#1f6fb4", label="print STL raster")
    for i, n in enumerate(names):
        v = mem[n]["margin"]
        ax.text(min(v, 2.3) + 0.03, i - 0.2, f"{v:.2f}  (A {mem[n]['A_mm2']:g} vs {mem[n]['A_bl053_mm2']:g} mm2)",
                va="center", fontsize=7)
    ax.axvline(1.0, color="k", lw=1)
    ax.set_yticks(yy, [n.replace(" (", "\n(") for n in names], fontsize=7)
    ax.set_xlim(0, 3.3)
    ax.set_xlabel("member buckling margin, fine_sm8 (bars clipped at 3.3)")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title("Member buckling: the print's members are 3-8 % thinner\nthan the voxel body (STL slice 144-147 mm2 "
                 "at the upper branch)", fontsize=9, loc="left")
    ax = axs[2]
    cen = H1.base()["cen"]
    new_s = np.load(OUT / "body" / "body_solid.npz")["solid"]
    old_s, _ = C.body_solid_bl053()
    for msk, col, lab, sz in ((new_s & old_s, "#d5d0c8", "in both", 1.0), (new_s & ~old_s, "#1f6fb4", "print only", 2.0),
                              (old_s & ~new_s, "#e67e22", "voxel body only", 2.0)):
        P = cen[msk]
        ax.scatter(P[:, 0], P[:, 2], s=sz, c=col, label=f"{lab} ({msk.sum()})", lw=0)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)")
    ax.set_ylabel("frame z (mm)")
    ax.legend(fontsize=7, markerscale=4, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
    lug = b.get("us2_lug", {})
    ax.set_title(f"Voxels of the run (front): hip boss {b['voxels']['boss_voxels']['run']} (BL-053 body "
                 f"{b['voxels']['boss_voxels']['bl053']})\nUS2 lug on the print: SF {lug['bl058']['strength']} / fatigue "
                 f"{lug['bl058']['fatigue']} (was {lug['bl053']['strength']} / {lug['bl053']['fatigue']})", fontsize=9,
                 loc="left")
    fig.tight_layout()
    return _save(fig, f"{SHOT}3.png")


def plot_followup(res: dict) -> str:
    """BL-058 follow-up: the 1.0 mm US2 head in its 1.5 mm counterbore (section at the pin), the outer sleeve's bearing
    SF for 8 / 6 / 6.5 mm on every row, the head's own checks and the pin-head cloth clearance on the 19 / 23 in fill
    drapes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from . import h1_bedfit as BF
    p = stations_R()["us2"]
    fig, axs = plt.subplots(1, 4, figsize=(19, 5.2), gridspec_kw={"width_ratios": [1.0, 1.25, 1.0, 1.0]})
    ax = axs[0]
    A = _sec_z(_mesh(), p["z"])
    _fill(ax, A, fc="#c9c3b8", ec="#5d5a54", lw=0.8)
    pr = res["pin_rows"]["us2"]
    xh, t = pr["head_seat_abs_x"], pr["head_mm"][1]
    ax.add_patch(Rectangle((150.0, p["y_pin"] - 2.5), xh - 150.0, 5.0, fc="#888", ec="k", lw=0.6))
    ax.add_patch(Rectangle((xh, p["y_pin"] - 4.0), t, 8.0, fc="#2c3e50", ec="k", lw=0.6, label=f"head D8 x {t:g}"))
    ax.axvline(BF.JOINT.outer_face, color="k", lw=0.8, ls=":")
    y0 = p["y_pin"] - 6.5
    ax.annotate("", xy=(175.0, y0), xytext=(xh, y0), arrowprops=dict(arrowstyle="<->", color="#c0392b"))
    ax.text(0.5 * (175.0 + xh), y0 - 1.6, f"bearing {p_us2_bearing():g} mm", ha="center", fontsize=8, color="#c0392b")
    ax.text(BF.JOINT.outer_face + 0.3, p["y_pin"] + 5.5, f"face; head {res['cbore']['recess_mm']:g} below", fontsize=7.5)
    ax.set_xlim(168, 190)
    ax.set_ylim(4, 28)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x (mm)")
    ax.set_ylabel("frame y (mm)")
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title(f"US2 clevis at the pin (z 142): D9 x {BF.PIN_CBORE_DEPTH:g} counterbore", fontsize=9, loc="left")
    ax = axs[1]
    sb = res["sleeve_bearing"]
    rows = ["design|share0.6", "design|share1", "dy95|share0.6", "dy95|share1"]
    yy = np.arange(len(rows))
    for i, (L, col) in enumerate(((8.0, "#bbb"), (6.0, "#e74c3c"), (sb["bearing_now_mm"], "#1f6fb4"))):
        v = [sb["rows"][f"{r}|L{L:g}"]["sf_yield"] for r in rows]
        ax.barh(yy + (1 - i) * 0.27, v, height=0.26, color=col, label=f"bearing {L:g} mm")
        for k, x in enumerate(v):
            ax.text(x + 0.03, k + (1 - i) * 0.27, f"{x:.2f}", va="center", fontsize=7)
    ax.axvline(sb["goal"], color="k", lw=1)
    ax.set_yticks(yy, [r.replace("|", ", ") for r in rows], fontsize=8)
    ax.set_xlabel("UHMWPE sleeve bearing SF on yield (factored rows; goal 1.0)")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title(f"Outer sleeve: {sb['bearing_now_mm']:g} mm reads {sb['min_now']:.2f} at dy 95 / share 1.0\n(6 mm: 0.98; "
                 "8 mm: 1.31)", fontsize=9, loc="left")
    ax = axs[2]
    hc = res["head_check"]
    labs = list(hc["rows"])
    sel = [k for k in labs if k.startswith("alu_7075_t6")]
    yy = np.arange(len(sel))
    for i, (key, col) in enumerate((("sf_shear", "#1f6fb4"), ("sf_flange", "#27ae60"), ("sf_pull_through", "#e67e22"))):
        v = [hc["rows"][k][key] for k in sel]
        ax.barh(yy + (1 - i) * 0.27, v, height=0.26, color=col, label=key.replace("sf_", ""))
    ax.axvline(2.0, color="k", lw=1)
    ax.set_xscale("log")
    ax.set_yticks(yy, [k.split("|")[1] for k in sel], fontsize=8)
    ax.set_xlabel("SF (log), 7075-T6 head D8 x 1.0")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title(f"Head under axial loads: min SF {hc['min_sf']:.1f}\n(Ti for reference is higher)", fontsize=9,
                 loc="left")
    ax = axs[3]
    h = res["us_route_heads"]
    pr_ = [r for r in h["pin_rows"] if r["case"] == "fill" and r["torso"] in (19, 23)]
    yy = np.arange(len(pr_))
    v = [r.get("pin_head_outside_clevis_mm", np.nan) for r in pr_]
    ax.barh(yy, v, color="#1f6fb4")
    for k, x in enumerate(v):
        ax.text(x + 0.1, k, f"{x:+.1f}", va="center", fontsize=8)
    ax.axvline(h["bolt_head_rule_recess_mm"], color="k", lw=1, ls="--", label="bolt-head rule 0.5 mm")
    ax.set_yticks(yy, [f"{r['torso']} in fill {r['side']}" for r in pr_])
    ax.set_xlabel("cloth clearance to the pin head (mm)")
    ax.legend(fontsize=7, loc="lower right")
    ax.set_title(f"Pin head vs the drapes: min {h['pin_head_outside_clevis_min_mm']:+.1f} mm over all 12\n(recess "
                 f"{h['pin_head_recess_mm']:g} mm)", fontsize=9, loc="left")
    fig.suptitle("BL-058 follow-up: US2 pin head 1.0 mm in a 1.5 mm counterbore", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    return _save(fig, f"{SHOT}4.png")


def figures(res: dict) -> list:
    out = [plot_retainers(res), plot_head(res), plot_followup(res)]
    if res.get("body"):
        out.insert(2, plot_body(res))
    return out


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--heavy", action="store_true")
    a = ap.parse_args(argv)
    if a.heavy:
        heavy(log=lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True))
        return 0
    report()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
