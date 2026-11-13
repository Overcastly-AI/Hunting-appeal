"""BL-050 Part A: the H1 lower half on the H2S bed with the US2 lane, the bolt-on US2 outer clevis, and the A-items.

    python -m huntkit.gendesign.h1_bedfit --probe 147   # option (c): print with US2 at x 147, bed fit + strap route
    python -m huntkit.gendesign.h1_bedfit --fea         # I-section lug arms (h1_lanes.lug_fea), one lug at a time
    python -m huntkit.gendesign.h1_bedfit --export      # print files (h1_buckling.export_print) + clevis pieces
    python -m huntkit.gendesign.h1_bedfit               # joint check, bed fit, figures, md / json from the caches

Ticket docs/backlog/BL-050-bed-fit-and-bag-lanes.md, Part A. BL-049 left the lower half 367.5 mm wide (US2 lugs at
x +/-165), 343 x 323 at its best rotation against the Bambu H2S's 340 x 320, before the 8 mm brim.

1. **Option (c), US2 in.** The largest US2 x whose lower half fits the bed with the brim is found on the real print
   (``probe``: h1_buckling.export_print with ``h1_lanes.US2_X`` moved, into ``outputs/h1_bedfit/probe_<x>``), and the
   strap route (``designs/pack_5200/us_route.py`` run_layout 'print_lanes') is run on that STL. It fails (the strap
   hits the hinge fairlead), so:
2. **Option (a), bolt-on US2 outer clevis.** US2 stays at x +/-165. The US2 fairlead is split at |x| ``SPLIT_X`` (in
   the throat floor, 8 mm outboard of the inner cheek): the body keeps the lug arm, the inner cheek and the inner part
   of the floor; the outer floor and the outer cheek are a separate printed piece (``us2_clevis_R`` / ``_L``) held by
   two Ti M5 through-bolts along x (the z 234 joint's hardware) in a dry butt joint. Below the throat floor both sides
   get a joint block (z +/-14.5) for the bolts; the nuts sit in side-access traps opening to the wearer face. The
   lower half then fits; the flat halves are written already rotated to the angle that fits the bed (``orient_on_bed``).
3. Joint check (``joint_check``): rigid dry face with tension-only bolts (frame_h1.contact_solve), every US2 lug load
   (h1_lanes.lug_loads: bag-off cradle 720 N, bag-on 296 N, +/-10 deg fleet), the outer cheek's share of the pin
   load; bolt tension / fatigue / shear, washer bearing, plug shear-out, hole bearing, contact, and the body block's
   net section through the nut traps.

Units mm, N, MPa, g. Frame coordinates: x lateral (R side +), y towards the bag, z up from the stay feet.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
RESULTS = ANALYSIS / "h1_bedfit.json"
DOC = ANALYSIS / "h1_bedfit.md"
OUT = REPO / "outputs" / "h1_bedfit"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL050_"
RHO_G_MM3 = 1.06e-3                # pa12_cf_fdm_paht print density (h1_lanes.RHO_G_MM3)

# ---------------------------------------------------------------------------------------------------- option (c)
PROBE_X = 147.0                    # largest US2 x found with the brim (footprint sweep 149 over by 0.7 mm, 147 fits)

# ---------------------------------------------------------------------------------------------------- option (a)
SPLIT_X = 163.0                    # |x| of the joint face: in the US2 throat floor (throat 155-175), 2 mm in of the pin
BLOCK_DY_LO = -9.8                 # joint blocks' wearer face, from the stay centre yc (-12.5 at US2; arm tip -10.7)
BLOCK_HALF_Z = 14.5                # joint blocks' half height about the pin (fairlead +/-9); below the throat floor only
BODY_BLOCK_X0 = 141.0              # body block from |x| 141 (covers the bolt tail, 1.5 mm wall) to SPLIT_X
BLOCK_EDGE_R = 1.5                 # rounded block edges


@dataclass
class ClevisJoint:
    """Dry butt joint at |x| SPLIT_X, per side: two Ti M5 through-bolts along x at (yc + dy, z_pin +/- dz). BL-051:
    the head sits in a counterbore (cbore_d, head_recess deep) in the clevis's outer face (|x| outer_face) and bears
    on the PAHT at |x| head_face with no washer, so nothing stands proud of the face (the free bag drapes reached
    the BL-050 heads, -1.1 mm); washer + nut in a side-access trap in the body block that opens to the wearer face
    (as the z 234 joint's inboard trap). Holes printed 4.8, reamed 5.1 (fitted bolts take the shear, as at z 234)."""
    dy: float = -2.8               # bolt axis from the stay centre yc (y -5.47 at US2; BL-050 -4.3): BL-051 moved it
    #                                1.5 mm up so the head counterbore keeps a 2.5 mm wall to the block's wearer face
    dz: float = 7.0                # bolt axes at z_pin +/- 7 (BL-053, fifth review M-2: was 8, which left the washer
    #                                slot 1.1-1.3 mm from the block's z faces; 7 gives 2.3 mm at the washer, 3.4 mm at
    #                                the nut's hex slot, 3.6 mm between the two washer slots)
    hole_d: float = 5.1            # reamed (printed 4.8)
    hole_print_d: float = 4.8
    washer_od: float = 10.0        # DIN 433 5.3 x 10 x 1 (z room: 8 + 5 = 13 < 14.5)
    washer_t: float = 1.0
    nut_af: float = 8.0            # ISO 4032 M5
    nut_t: float = 4.0
    nut_face: float = 151.0        # |x| where the nut washer bears (body plug 151 -> 163 = 12 mm: hole bearing at
    #                                share 1.0 governs the fatigue; 8 mm gave 0.79 there)
    trap_x0: float = 145.8         # |x| inboard end of the trap (washer 1 + nut 4 + 0.2 play)
    hex_trap: bool = True          # BL-053 (M-2): two-step trap as at z 234: washer slot (slot_w, washer_t + 0.2 long
    #                                at the nut face), then an AF + 0.2 hex slot that holds the nut by its flats
    nut_play: float = 0.2          # hex slot AF play
    outer_face: float = 183.0      # |x| clevis outer face (outer cheek's outer face, h1 US2 x 165 + 18)
    head_recess: float = 4.0       # BL-051: counterbore depth (head 3.5 + 0.5 below the face)
    cbore_d: float = 9.0           # BL-051: head 8.5 + 0.5 (printed; the head bears on its floor, no washer)
    head_h: float = 3.5            # DIN 7984 low head
    head_d: float = 8.5
    head_washer: bool = False      # BL-051: no washer under the head (BL-050 had one, on the face)
    bolt_len: float = 35.0         # grip 28 + nut washer 1 + nut 4 + 1 = 34: M5 x 35 Ti gr5 DIN 7984 (BL-050: x 40)
    tail_x: float = 143.5          # |x| bolt tail clearance end (head_face - bolt_len - 0.5)

    @property
    def head_face(self):           # |x| where the head bears (counterbore floor)
        return self.outer_face - self.head_recess

    @property
    def head_x(self):              # |x| span of the head (frame), for clearance checks (us_route.head_clearance)
        x0 = self.head_face + (self.washer_t if self.head_washer else 0.0)
        return x0, x0 + self.head_h

    @property
    def n_washers(self):           # per bolt
        return 2 if self.head_washer else 1

    @property
    def slot_w(self):
        return self.washer_od + 0.4

    @property
    def L_body(self):              # body plug, nut face -> joint face
        return SPLIT_X - self.nut_face

    @property
    def L_clevis(self):            # clevis plug, joint face -> head face
        return self.head_face - SPLIT_X


JOINT = ClevisJoint()
CHEEK_SHARE = 0.6                  # ASSUMPTION CLEVIS-SHARE: outer cheek's share of the pin's y-z load (eye 18-19 in a
#   20 throat; centred = 0.5); the whole x (fleet) load also goes to the cheek the eye bears on. 1.0 is the sensitivity.


# ======================================================================================= geometry
def us2_stations() -> list:
    from . import h1_fairleads as HF
    return [p for p in HF.placed() if p["name"] == "us2"]


def _box(x0, x1, y0, y1, z0, z1, r: float = 0.0):
    import manifold3d as m3d
    lo, hi = np.array([x0, y0, z0], float), np.array([x1, y1, z1], float)
    if r <= 0.0:
        return m3d.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
    cyl = []
    for xx in (x0 + r, x1 - r):
        for yy in (y0 + r, y1 - r):
            cyl.append(m3d.Manifold.cylinder(z1 - z0, r, r, 24).translate((xx, yy, z0)))
    return m3d.Manifold.batch_hull(cyl)


def _sx(p, a, b):
    """|x| interval [a, b] on station p's side -> (lo, hi) in frame x."""
    s = p["sign"]
    return (min(s * a, s * b), max(s * a, s * b))


def block_boxes(p: dict) -> dict:
    """The two joint blocks (frame coordinates) of station ``p``: 'body' |x| 145 -> SPLIT_X, 'clevis' SPLIT_X -> the
    outer face; y from yc + BLOCK_DY_LO to the throat floor, z pin +/- BLOCK_HALF_Z."""
    # small offsets off the fairlead's own planes (floor, outer face): coplanar booleans leave slivers that an STL
    # round trip turns into non-manifold edges (as h1_fairleads' grid offsets)
    y0, y1 = p["yc"] + BLOCK_DY_LO, p["y_floor"] - 0.0371
    z0, z1 = p["z"] - BLOCK_HALF_Z, p["z"] + BLOCK_HALF_Z
    return {"body": (*_sx(p, BODY_BLOCK_X0, SPLIT_X + 1.0), y0, y1, z0, z1),
            "clevis": (*_sx(p, SPLIT_X - 1.0, JOINT.outer_face - 0.0413), y0, y1, z0, z1)}


def bolt_axes(p: dict, j: ClevisJoint = JOINT) -> list:
    """(y, z) of the two bolt axes of station p."""
    return [(p["yc"] + j.dy, p["z"] + s * j.dz) for s in (-1.0, 1.0)]


def _cyl_x(xa, xb, y, z, d, seg=48):
    import manifold3d as m3d
    lo, hi = min(xa, xb), max(xa, xb)
    c = m3d.Manifold.cylinder(hi - lo, d / 2.0, d / 2.0, seg)          # along +z from 0
    return c.rotate((0.0, 90.0, 0.0)).translate((lo, y, z))             # -> along +x


def cuts(p: dict, j: ClevisJoint = JOINT):
    """Bolt holes (printed size) from the tail end to the outer face, and the nut + washer traps open to the wearer
    face (y down to below the block)."""
    out = None
    yb = p["yc"] + BLOCK_DY_LO
    for (y, z) in bolt_axes(p, j):
        h = _cyl_x(p["sign"] * j.tail_x, p["sign"] * (j.outer_face + 1.0), y, z, j.hole_print_d)
        if j.head_recess > 0.0:        # BL-051: head counterbore from the outer face
            h = h + _cyl_x(p["sign"] * j.head_face, p["sign"] * (j.outer_face + 1.0), y, z, j.cbore_d, seg=64)
        if j.hex_trap:
            t = trap_solid(p, y, z, j)
        else:
            t = _box(*_sx(p, j.trap_x0, j.nut_face), yb - 1.0, y + j.slot_w / 2.0, z - j.slot_w / 2.0,
                     z + j.slot_w / 2.0)
        out = h + t if out is None else out + h + t
    return out


def trap_solid(p: dict, y: float, z: float, j: ClevisJoint = JOINT):
    """BL-053 (M-2): the nut + washer trap of one bolt, as the z 234 joint's: a washer slot slot_w wide (round top, box
    to the wearer face) over |x| nut_face - washer_t - 0.2 .. nut_face, then the nut's hex pocket (AF + play across z,
    flats facing +/- z so the nut cannot turn, corners towards y) with an AF + play slot down to the wearer face, over
    |x| trap_x0 .. the washer slot."""
    import manifold3d as m3d
    yb = p["yc"] + BLOCK_DY_LO
    w_lo = j.nut_face - j.washer_t - 0.2
    ws = _cyl_x(p["sign"] * w_lo, p["sign"] * j.nut_face, y, z, j.slot_w, seg=48) + \
        _box(*_sx(p, w_lo, j.nut_face), yb - 1.0, y, z - j.slot_w / 2.0, z + j.slot_w / 2.0)
    af = j.nut_af + j.nut_play
    rc = af / math.sqrt(3.0)                          # circumradius of the hex slot
    hx = m3d.Manifold.cylinder(w_lo - j.trap_x0, rc, rc, 6)        # along +z, vertices at angle 0 (+x local)
    # local z -> frame x; local x -> frame y (a vertex points along y: flats face +/- z)
    hx = hx.rotate((0.0, 0.0, 90.0)).rotate((0.0, 90.0, 0.0)).translate((min(p["sign"] * j.trap_x0, p["sign"] * w_lo), y, z))
    ns = _box(*_sx(p, j.trap_x0, w_lo), yb - 1.0, y, z - af / 2.0, z + af / 2.0)
    return ws + hx + ns


def trap_walls(p: dict | None = None, j: ClevisJoint = JOINT) -> dict:
    """Wall (mm) between each trap step and the block's z faces, and between the two traps (M-2 rule >= 2 mm)."""
    p = p or next(q for q in us2_stations() if q["side"] == "R")
    af = j.nut_af + j.nut_play
    out = {}
    for lab, w in (("washer_slot", j.slot_w), ("hex_slot", af)):
        out[lab] = {"outer_wall_mm": round(BLOCK_HALF_Z - (j.dz + w / 2.0), 2),
                    "between_traps_mm": round(2 * j.dz - w, 2)}
    out["min_wall_mm"] = min(min(v.values()) for v in out.values())
    out["pass_2mm"] = bool(out["min_wall_mm"] >= 2.0)
    out["nut_held_by_flats"] = bool(j.hex_trap and af < j.nut_af / math.cos(math.radians(30)) - 0.2)
    return out


LIP_R = 3.0                        # BL-053 (M-6): the US2 blocks' lower aft edge (the bag-on strap wraps it)


def lip_round_cut(p: dict, r: float = LIP_R):
    """Material to take off the lower aft edge of both joint blocks of station p (edge along x at y = y_floor,
    z = pin - BLOCK_HALF_Z): the corner square less a quarter cylinder of radius r."""
    y1, z0 = p["y_floor"], p["z"] - BLOCK_HALF_Z
    xa, xb = _sx(p, BODY_BLOCK_X0 - 1.0, JOINT.outer_face + 1.0)
    sq = _box(xa, xb, y1 - r, y1 + 0.5, z0 - 0.5, z0 + r)
    return sq - _cyl_x(xa - 0.5, xb + 0.5, y1 - r, z0 + r, 2 * r, seg=64)


def split_box(p: dict):
    """Everything of the US2 lug outboard of the joint face (frame coordinates)."""
    return _box(*_sx(p, SPLIT_X + 0.0187, SPLIT_X + 40.0), p["yc"] - 30.0, p["yc"] + 45.0, p["z"] - 30.0, p["z"] + 30.0)


def split_us2(mesh, log=print) -> tuple:
    """Assembled print mesh (frame coordinates) -> (assembled with the joint blocks and cuts, body, {piece: mesh},
    stats). The body is what prints in the halves; each clevis prints on its own."""
    from .h1_buckling import clean_shell
    from .surface import _from_manifold, _to_manifold
    man = _to_manifold(mesh)
    v0 = man.volume()
    for p in us2_stations():
        for b in block_boxes(p).values():
            man = man + _box(*b, r=BLOCK_EDGE_R)
    v1 = man.volume()
    for p in us2_stations():
        man = man - cuts(p)
        if LIP_R > 0.0:                # BL-053 (M-6): r 3 lip on the blocks' lower aft edge
            man = man - lip_round_cut(p)
    v2 = man.volume()
    body = man
    pieces = {}
    for p in us2_stations():
        sb = split_box(p)
        pieces[f"us2_clevis_{p['side']}"] = man ^ sb
        body = body - sb
    asm = _from_manifold(man)
    body_m, drop = clean_shell(_from_manifold(body))
    pcs = {}
    for k, v in pieces.items():
        pm, d = clean_shell(_from_manifold(v))
        pcs[k] = pm
        drop = drop + d
    stats = {"blocks_g": round((v1 - v0) * RHO_G_MM3, 2), "cuts_g": round((v1 - v2) * RHO_G_MM3, 2),
             "net_g": round((v2 - v0) * RHO_G_MM3, 2),
             "pieces_g": {k: round(float(v.volume) * RHO_G_MM3, 2) for k, v in pcs.items()},
             "body_g": round(float(body_m.volume) * RHO_G_MM3, 1), "assembled_g": round(float(asm.volume) * RHO_G_MM3, 1),
             "dropped": drop}
    if log:
        log(f"  US2 clevis (BL-050): blocks +{stats['blocks_g']} g, cuts -{stats['cuts_g']} g, pieces "
            f"{stats['pieces_g']}")
    return asm, body_m, pcs, stats


# ======================================================================================= bed
def footprint_fit(P2: np.ndarray, bed=None, brim: float | None = None, step: float = 0.25) -> dict:
    """Smallest bounding rectangle of a 2D footprint over rotations (``step`` deg), with the brim, against the bed:
    {'deg', 'w_mm', 'h_mm', 'over_mm' (incl. brim; <= 0 fits), 'fits_with_brim'}."""
    from scipy.spatial import ConvexHull
    from .h1_lanes import BED_MM, BRIM_MM
    bed = bed or BED_MM
    brim = BRIM_MM if brim is None else brim
    H = P2[ConvexHull(P2).vertices]
    best = None
    for deg in np.arange(0.0, 180.0, step):
        th = math.radians(deg)
        R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        Q = H @ R.T
        w, h = float(np.ptp(Q[:, 0])), float(np.ptp(Q[:, 1]))
        swap = h > w
        w, h = max(w, h), min(w, h)
        over = max(w + 2 * brim - bed[0], h + 2 * brim - bed[1])
        if best is None or over < best["over_mm"] - 1e-9:
            best = {"deg": float(deg), "swap": bool(swap), "w_mm": round(w, 2), "h_mm": round(h, 2),
                    "over_mm": round(over, 2)}
    best["fits_with_brim"] = bool(best["over_mm"] <= 0.0)
    return best


def orient_on_bed(mesh, bed=None, brim: float | None = None):
    """Rotate a flat half about the print z so its axis-aligned footprint (+ brim) fits the bed, long side along the
    bed's 340 mm axis; keep 0 deg when that already fits. Returns (mesh, info). The rotation is what the slicer plate
    shows: the STL needs no turning on the plate."""
    from .h1_lanes import BED_MM, BRIM_MM
    bed = bed or BED_MM
    brim = BRIM_MM if brim is None else brim
    m = mesh.copy()
    e = m.extents
    w, h = max(e[0], e[1]), min(e[0], e[1])
    if w + 2 * brim <= bed[0] and h + 2 * brim <= bed[1]:
        deg = 0.0 if e[0] >= e[1] else 90.0
    else:
        deg = footprint_fit(m.vertices[:, :2], bed, brim)["deg"]
    T = np.eye(4)
    th = math.radians(deg)
    T[:2, :2] = [[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]
    m.apply_transform(T)
    if m.extents[1] > m.extents[0]:                     # long side along the bed x (340)
        T = np.eye(4)
        T[:2, :2] = [[0.0, -1.0], [1.0, 0.0]]
        m.apply_transform(T)
        deg += 90.0
    m.apply_translation(-m.bounds[0])
    ex = [round(float(v), 2) for v in m.extents]
    return m, {"rot_deg": round(deg % 360.0, 2), "extents_mm": ex,
               "fits": bool(ex[0] <= bed[0] and ex[1] <= bed[1]),
               "fits_with_brim": bool(ex[0] + 2 * brim <= bed[0] and ex[1] + 2 * brim <= bed[1]),
               "spare_mm": [round(bed[0] - 2 * brim - ex[0], 2), round(bed[1] - 2 * brim - ex[1], 2)]}


def bed_check(path: Path) -> dict:
    """The file as written: axis-aligned extents against the bed with the brim (no rotation), and the best rotation."""
    import trimesh
    from .h1_lanes import BED_MM, BRIM_MM
    m = trimesh.load(path)
    ex = [round(float(v), 2) for v in m.extents]
    return {"extents_mm": ex, "fits": bool(ex[0] <= BED_MM[0] and ex[1] <= BED_MM[1]),
            "fits_with_brim": bool(ex[0] + 2 * BRIM_MM <= BED_MM[0] and ex[1] + 2 * BRIM_MM <= BED_MM[1]),
            "spare_mm": [round(BED_MM[0] - 2 * BRIM_MM - ex[0], 2), round(BED_MM[1] - 2 * BRIM_MM - ex[1], 2)],
            "best_rotation": footprint_fit(m.vertices[:, :2])}


# ======================================================================================= option (c) probe
def probe(x2: float = PROBE_X, log=print) -> dict:
    """Export the print with US2 at |x| ``x2`` (no clevis) into outputs/h1_bedfit/probe_<x2>, fit the halves on the
    bed, run the strap route on it (us_route 'print_lanes': channel ends at the lane x). Cached as probe_<x2>.json."""
    import importlib
    import sys
    import trimesh
    from . import frame_h1 as H1
    from . import h1_buckling as B
    from . import h1_fairleads as HF
    from . import h1_lanes as LN
    d = OUT / f"probe_{x2:g}"
    cache = OUT / f"probe_{x2:g}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    d.mkdir(parents=True, exist_ok=True)
    keep = (LN.US2_X, dict(LN.LANE_X), dict(LN.CHANNEL_ENTRY_X), H1.PRINT_DIR, B.OUT, HF.PRINT_DIR, B.US2_CLEVIS)
    try:
        LN.US2_X = x2
        LN.LANE_X["us2"] = x2
        LN.CHANNEL_ENTRY_X["us2"] = x2
        H1.PRINT_DIR, B.OUT, HF.PRINT_DIR, B.US2_CLEVIS = d, d, d, False
        info = B.export_print(*B.CHOSEN, log=None)
        for p in (str(PACK), str(PACK / "concepts")):
            if p not in sys.path:
                sys.path.insert(0, p)
        U = importlib.import_module("us_route")
        mesh = trimesh.load(d / "h1_assembled.stl")
        F = U._F()
        drapes = {t: F.drape(U.RUN.format(t=t), U.CASE) for t in U.TORSOS}
        r = U.run_layout("print_lanes", mesh, drapes, U.tensions())
    finally:
        LN.US2_X, H1.PRINT_DIR, B.OUT, HF.PRINT_DIR, B.US2_CLEVIS = keep[0], keep[3], keep[4], keep[5], keep[6]
        LN.LANE_X.update(keep[1])
        LN.CHANNEL_ENTRY_X.update(keep[2])
    bed = {nm: bed_check(d / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")}
    rows = [{"torso": q["torso"], "side": q["side"], "strap": q["strap"], "clear_mm": q["clear_mm"],
             "min_clear_mm": q["min_clear_mm"], "pass": q["pass"]} for q in r["rows"]]
    res = {"us2_x": x2, "lower_g": info["lower"]["g"], "bed": bed, "route": {"layout": r["layout"],
           "worst_clear_mm": r["worst_clear_mm"], "pass": r["pass"], "rows": rows}}
    cache.write_text(json.dumps(res, indent=1, default=float))
    if log:
        log(f"  probe US2 x {x2}: bed {bed['lower']['best_rotation']}, route {r['worst_clear_mm']} pass {r['pass']}")
    return res


def sweep_x(xs=(165, 161, 157, 153, 151, 149, 148, 147, 145, 141)) -> list:
    """Footprint sweep on the BL-049 lower half: the US2 lug + fairlead (|x| > 138 at z 120-165) moved in to x, best
    rotation with the brim. Cheap screen for ``probe`` (which exports the real print)."""
    import trimesh
    from . import h1_fairleads as HF
    f = HF.PRINT_DIR / "h1_lower_flat.stl"
    src = OUT / "bl049_lower_flat.stl"
    if not src.exists():                                  # BL-049's lower half (git HEAD), before this ticket
        import subprocess
        OUT.mkdir(parents=True, exist_ok=True)
        src.write_bytes(subprocess.run(["git", "-C", str(REPO), "show",
                                        "3b3e681:designs/pack_5200/print/frame_h1/h1_lower_flat.stl"],
                                       check=True, capture_output=True).stdout)
    m = trimesh.load(src if src.exists() else f)
    P = m.vertices[:, :2].copy()
    P[:, 0] -= 0.5 * (P[:, 0].min() + P[:, 0].max())
    sel = np.abs(P[:, 0]) > 138.0
    out = []
    for x in xs:
        Q = P.copy()
        Q[sel, 0] -= np.sign(Q[sel, 0]) * (165.0 - x)
        out.append({"us2_x": float(x), **footprint_fit(Q)})
    return out


# ======================================================================================= joint check
def _face_grid(p: dict, h: float = 0.5, j: ClevisJoint = JOINT):
    """Contact face at |x| SPLIT_X (local u = y - yc - j.dy, v = z - z_pin about the bolt-group centre): the block
    rectangle less the two holes (reamed size)."""
    y0, y1 = p["yc"] + BLOCK_DY_LO, p["y_floor"]
    yb = p["yc"] + j.dy
    u = np.arange(y0 - yb + h / 2, y1 - yb, h)
    v = np.arange(-BLOCK_HALF_Z + h / 2, BLOCK_HALF_Z, h)
    U, V = np.meshgrid(u, v, indexing="ij")
    U, V = U.ravel(), V.ravel()
    keep = np.ones(U.size, bool)
    for s in (-1.0, 1.0):
        keep &= np.hypot(U, V - s * j.dz) > j.hole_d / 2.0
    return U[keep], V[keep], h * h


def net_section(p: dict, j: ClevisJoint = JOINT, h: float = 0.25) -> dict:
    """Body block section through the nut traps (|x| trap_x0..nut_face): block rectangle less the two traps (open to
    the wearer face) and the hole. Section properties about its centroid (u along y, v along z)."""
    y0, y1 = p["yc"] + BLOCK_DY_LO, p["y_floor"]
    u = np.arange(y0 + h / 2, y1, h)
    v = np.arange(p["z"] - BLOCK_HALF_Z + h / 2, p["z"] + BLOCK_HALF_Z, h)
    Y, Z = np.meshgrid(u, v, indexing="ij")
    keep = np.ones(Y.shape, bool)
    for (yb, zb) in bolt_axes(p, j):
        keep &= ~((Y <= yb + j.slot_w / 2.0) & (np.abs(Z - zb) <= j.slot_w / 2.0))
    Y, Z = Y[keep], Z[keep]
    A = Y.size * h * h
    yc, zc = Y.mean(), Z.mean()
    Iy = ((Z - zc) ** 2).sum() * h * h          # about the y axis (bending from z loads)
    Iz = ((Y - yc) ** 2).sum() * h * h          # about the z axis (bending from y loads)
    Iyz = ((Y - yc) * (Z - zc)).sum() * h * h
    return {"A": A, "yc": yc, "zc": zc, "Iy": Iy, "Iz": Iz, "Iyz": Iyz, "pts": (Y, Z)}


def joint_loads(name: str = "us2") -> dict:
    """h1_lanes.lug_loads rows (R side, x + outboard) -> the force on the outer clevis: CHEEK_SHARE of the y-z part;
    the x part in full when it pushes outboard (the eye bears on the outer cheek), else 0."""
    from . import h1_lanes as LN
    return LN.lug_loads(name)


def joint_check(share: float = CHEEK_SHARE, j: ClevisJoint = JOINT, loads: dict | None = None) -> dict:
    """Per load row: bolt forces from the dry-face contact solve (tension-only bolts, no preload credited, as the
    z 234 joint), bolt shear from the direct shear and the torsion, PAHT checks; static at the factored row, fatigue
    at 1.6 g (row x 1.6 / g_times_req). Body block net section through the nut traps (layer rule, layer normal y)."""
    from . import frame_h1 as H1
    from .frame_topopt import layer_failure_index
    p = next(q for q in us2_stations() if q["side"] == "R")
    U, V, a = _face_grid(p, j=j)
    bolts = [(0.0, -j.dz), (0.0, j.dz)]
    TI, PA = H1.TI, H1.PAHT
    kb = TI["E"] * TI["As"] / (j.head_face - j.nut_face + j.n_washers * j.washer_t)
    kc = PA["E"] * PA["E_hot"] / H1.L_CONTACT
    k = PA["knock"]
    # BL-051: the bearing ring and the shear-out width of each end (nut washer in the body; head, or its washer, in the
    # clevis): the weaker end governs
    bear_d = {"body": j.washer_od, "clevis": j.washer_od if j.head_washer else j.head_d}
    ring = min(math.pi / 4 * (d ** 2 - j.hole_d ** 2) for d in bear_d.values())
    shear_lw = min(j.L_body * bear_d["body"], j.L_clevis * bear_d["clevis"])
    cap = {"washer_bearing_n": ring * k * PA["s_xy"],
           "plug_shear_out_n": 2 * shear_lw * 0.6 * k * PA["s_z"],
           "bolt_tension_n": 0.7 * TI["uts"] * TI["As"], "bolt_fatigue_n": 0.25 * TI["uts"] * TI["As"],
           # fitted bolt bearing in the body plug, load across the layers in part: interlayer strength (conservative)
           "hole_bearing_n": j.hole_d * j.L_body * k * PA["s_z"],
           "bolt_shear_n": 0.6 * TI["uts"] * math.pi / 4 * TI["d_minor"] ** 2, "contact_mpa": k * PA["s_xy"]}
    pin = np.array([p["x"] + p["geom"].throat / 2 + p["geom"].cheek / 2, p["y_pin"], p["z"]])   # outer cheek centre
    c0 = np.array([SPLIT_X, p["yc"] + j.dy, p["z"]])                                            # bolt-group centre
    ns = net_section(p, j)
    xs_ns = 0.5 * (j.trap_x0 + j.nut_face)
    rows = {}
    for nm, L in (loads if loads is not None else joint_loads()).items():
        F = np.asarray(L["vec"], float)
        if L.get("direct"):            # BL-053: a force already on the clevis (e.g. the strap's wrap on the block lip)
            Fc = F.copy()
        else:
            Fc = np.array([max(F[0], 0.0), share * F[1], share * F[2]])
        gr = L["g_times_req"]
        r = (np.asarray(L["at"], float) if L.get("at") is not None else pin) - c0
        M = np.cross(r, Fc)
        # face equilibrium (see module notes): sum f = Fx, sum f v = M_y, sum f u = -M_z (u = y, v = z local)
        cs = H1.contact_solve(U, V, a, Fc[0], M[1], -M[2], bolts, kb, kc)
        T = cs["bolt_n"]
        V_dir = np.array([Fc[1], Fc[2]]) / 2.0
        tors = M[0] / (2 * j.dz)                           # torsion about x: couple of the two bolts (along y)
        shear = [float(np.hypot(V_dir[0] + s * tors, V_dir[1])) for s in (-1.0, 1.0)]
        # body block net section through the traps: N = Fx, moments of Fc about the section centroid
        rn = pin - np.array([p["sign"] * xs_ns, ns["yc"], ns["zc"]])
        Mn = np.cross(rn, Fc)
        Y, Z = ns["pts"]
        # sigma_x = N/A + (My z' ... ) : general biaxial bending (unsymmetric section)
        dy_, dz_ = Y - ns["yc"], Z - ns["zc"]
        Mz_, My_ = Mn[2], Mn[1]
        D = ns["Iy"] * ns["Iz"] - ns["Iyz"] ** 2
        # (axial and bending magnitudes added: conservative on the sign conventions)
        sig = abs(Fc[0]) / ns["A"] + np.abs((-(Mz_ * ns["Iy"] + My_ * ns["Iyz"]) * dy_
                                             + (My_ * ns["Iz"] + Mz_ * ns["Iyz"]) * dz_) / D)
        tau = abs(Mn[0]) / (0.25 * (BLOCK_HALF_Z * 2) * (p["y_floor"] - p["yc"] - BLOCK_DY_LO) ** 2) \
            + float(np.hypot(Fc[1], Fc[2])) / ns["A"] * 1.5
        S = np.zeros((1, 3))
        S[0, 0] = float(np.abs(sig).max())
        Tt = np.zeros((1, 3))
        Tt[0, 0] = tau                                     # tau_xy: touches the layer normal (y): interlayer
        fi_ns = float(layer_failure_index(S, Tt, 1, PA["s_xy"], PA["s_z"], PA["knock"])[0])
        tmax = float(T.max())
        sf = {"bolt_tension": cap["bolt_tension_n"] / max(tmax, 1e-9),
              "washer_bearing": cap["washer_bearing_n"] / max(tmax, 1e-9),
              "plug_shear_out": cap["plug_shear_out_n"] / max(tmax, 1e-9),
              "bolt_shear": cap["bolt_shear_n"] / max(max(shear), 1e-9),
              "hole_bearing": cap["hole_bearing_n"] / max(max(shear), 1e-9),
              "contact": cap["contact_mpa"] / max(cs["contact_mpa"], 1e-9),
              "net_section": 1.0 / max(fi_ns, 1e-9)}
        fw = 1.6 / gr
        fat = {"bolt": cap["bolt_fatigue_n"] / max(tmax * fw, 1e-9),
               "plug_paht": PA["fat"] * cap["plug_shear_out_n"] / max(tmax * fw, 1e-9),
               "washer_paht": PA["fat"] * cap["washer_bearing_n"] / max(tmax * fw, 1e-9),
               "hole_paht": PA["fat"] * cap["hole_bearing_n"] / max(max(shear) * fw, 1e-9),
               "net_section_paht": PA["fat"] / max(fi_ns * fw, 1e-9)}
        rows[nm] = {"g_times_req": gr, "force_on_clevis_n": [round(float(v), 1) for v in Fc],
                    "moment_nmm": [round(float(v), 0) for v in M], "bolt_tension_n": [round(float(t), 1) for t in T],
                    "bolt_shear_n": [round(s, 1) for s in shear], "contact_mpa": round(cs["contact_mpa"], 2),
                    "resid_n": round(cs["resid_n"], 4), "net_section_fi": round(fi_ns, 3),
                    "net_section_sigma_mpa": round(float(np.abs(sig).max()), 2),
                    "sf": {kk: round(v, 2) for kk, v in sf.items()}, "fatigue": {kk: round(v, 2) for kk, v in fat.items()},
                    "min_sf": round(min(sf.values()), 2), "min_fatigue": round(min(fat.values()), 2)}
    ws = min(rows, key=lambda r: rows[r]["min_sf"])
    wf = min(rows, key=lambda r: rows[r]["min_fatigue"])
    return {"share": share, "joint": dataclasses.asdict(j), "capacities_n": {kk: round(v, 1) for kk, v in cap.items()},
            "net_section": {kk: round(float(ns[kk]), 2) for kk in ("A", "yc", "zc", "Iy", "Iz", "Iyz")},
            "rows": rows, "worst_strength": {"load": ws, "sf": rows[ws]["min_sf"],
                                             "check": min(rows[ws]["sf"], key=rows[ws]["sf"].get)},
            "worst_fatigue": {"load": wf, "fatigue": rows[wf]["min_fatigue"],
                              "check": min(rows[wf]["fatigue"], key=rows[wf]["fatigue"].get)}}


def hardware_g(j: ClevisJoint = JOINT) -> dict:
    """Two bolts, two nuts, two (BL-050: four) washers per side (x 2 sides)."""
    from .frame_comp_B import bolt_mass_g
    nut = (3 * math.sqrt(3) / 2 * (j.nut_af / math.sqrt(3)) ** 2 - math.pi / 4 * 5.0 ** 2) * j.nut_t * 7.9e-3
    washer = math.pi / 4 * (j.washer_od ** 2 - 5.3 ** 2) * j.washer_t * 7.9e-3
    return {f"4 Ti gr5 M5 x {j.bolt_len:.0f} DIN 7984": round(4 * bolt_mass_g(j.bolt_len), 2),
            "4 A2 M5 hex nuts ISO 4032": round(4 * nut, 2),
            f"{4 * j.n_washers} A2 M5 x 10 x 1 washers DIN 433": round(4 * j.n_washers * washer, 2)}


# ======================================================================================= arm sections (A2)
ISECT_VARIANTS = (("I", 3.0, 3.0), ("box", 3.0, 3.0), ("box", 4.0, 4.0), ("box", 5.0, 5.0))


def isect_study(log=None) -> dict:
    """BL-049's proposal: the lug arms pocketed outboard of the root (h1_lanes.ISECT). Each variant through the same
    lug FEA as the solid arm (h1_lanes.lug_study, cached per variant); per lug the governing strength / fatigue and
    each region's lowest fatigue, and the mass the pockets take out (print geometry, both sides)."""
    from . import h1_fairleads as HF
    from . import h1_lanes as LN

    def summ(r):
        return {n: {"strength": r[n]["worst_strength"]["sf"], "fatigue": r[n]["worst_fatigue"]["fatigue"],
                    "fatigue_load": r[n]["worst_fatigue"]["load"],
                    "region_fatigue": {rg: min(row["regions"][rg]["fatigue"] for row in r[n]["rows"].values()
                                               if rg in row["regions"]) for rg in ("fairlead", "arm", "root")}}
                for n in r}
    base = summ(LN.lug_study(log=log, arms={n: dict(LN.ARM[n]) for n in LN.LANE_X}))
    out = {"solid": {"lugs": base, "saved_g": 0.0}}
    for kind, web, fl in ISECT_VARIANTS:
        q = {**LN.ISECT, "kind": kind, "web": web, "flange": fl}
        arms = {n: {**LN.ARM[n], "isect": q} for n in LN.LANE_X}
        r = summ(LN.lug_study(log=log, arms=arms))
        g = 0.0
        for p in HF.placed():
            if p.get("lane"):
                a = LN.arm_solid(p)
                g += (a.volume() - (a - LN.pocket_solid(p, arms[p["name"]])).volume()) * LN.RHO_G_MM3
        holds = all(r[n]["strength"] >= base[n]["strength"] - 0.02 and
                    all(r[n]["region_fatigue"][rg] >= base[n]["region_fatigue"][rg] - 0.02 for rg in base[n]["region_fatigue"])
                    for n in r)
        out[f"{kind}_w{web:g}_f{fl:g}"] = {"kind": kind, "web": web, "flange": fl, "lugs": r, "saved_g": round(g, 2),
                                         "every_margin_holds": bool(holds)}
    out["adopted"] = [k for k, v in out.items() if k != "solid" and v["every_margin_holds"]]
    return out


# ======================================================================================= record
def joint_slices(path: Path | None = None) -> dict:
    """Slice the assembled print across the US2 joint (R and L): at |x| 170 (clevis, under the throat) the two bolt
    holes must be there at the printed size and on their axes; at the trap plane (body) the traps must
    open to the wearer face and leave the block top whole; the joint face |x| SPLIT_X must be a closed section."""
    import trimesh
    from shapely.geometry import Polygon
    from . import h1_fairleads as HF
    m = trimesh.load(path or HF.PRINT_DIR / "h1_assembled.stl")
    out = {}
    for p in us2_stations():
        rows = {}
        for lab, ax in (("clevis_170", 170.0), ("body_trap", 0.5 * (JOINT.trap_x0 + JOINT.nut_face)),
                        ("face", SPLIT_X - 0.5)):
            sec = m.section(plane_origin=[p["sign"] * ax, 0.0, 0.0], plane_normal=[1.0, 0.0, 0.0])
            loops = [Polygon(L[:, 1:]) for L in sec.discrete if len(L) > 3]
            loops = [L for L in loops if L.is_valid and L.area > 0.5]
            # only the loops round the US2 station (|z - z_pin| < 30)
            loops = [L for L in loops if abs(L.centroid.y - p["z"]) < 30.0]
            loops.sort(key=lambda L: -L.area)
            outer = loops[0] if loops else None
            holes = [L for L in loops[1:] if outer is not None and outer.contains(L)]
            r = {"outer_area_mm2": round(outer.area, 1) if outer is not None else 0.0,
                 "holes": [{"d_eq_mm": round(2 * math.sqrt(h.area / math.pi), 2),
                            "y": round(h.centroid.x, 2), "z": round(h.centroid.y, 2)} for h in holes]}
            if outer is not None:
                b = outer.bounds
                r["bounds_yz"] = [round(v, 2) for v in b]
            rows[lab] = r
        ax_ = bolt_axes(p)
        cl = rows["clevis_170"]["holes"]
        ok_cl = len(cl) == 2 and all(any(abs(h["y"] - y) < 0.3 and abs(h["z"] - z) < 0.3 and
                                         abs(h["d_eq_mm"] - JOINT.hole_print_d) < 0.25 for h in cl) for y, z in ax_)
        bt = rows["body_trap"].get("bounds_yz", [0, 0, 0, 0])
        near = [h for h in rows["body_trap"]["holes"] if any(math.hypot(h["y"] - y, h["z"] - z) < 6.0 for y, z in ax_)]
        ok_body = not near and bt[2] >= p["y_floor"] - 0.3     # traps open to the wearer face (no closed loop), top whole
        rows["pass"] = bool(ok_cl and ok_body and rows["face"]["outer_area_mm2"] > 300.0)
        out[p["side"]] = rows
    out["pass"] = all(v["pass"] for k, v in out.items() if k in ("R", "L"))
    return out


def mass_rows() -> dict:
    """Grams against BL-049: the print (assembled, clevises included) from the export, the joint hardware, and the
    attachment pins / sleeves booked for 8 stations against the 12 that bag_attach.stations() places."""
    from huntkit.mass import ledger as LG
    from . import bag_attach as BA
    ex = json.loads((REPO / "outputs" / "h1_lanes" / "export_info.json").read_text())
    b49 = json.loads((ANALYSIS / "h1_lanes.json").read_text())["mass"]
    led = {r["name"]: r["g"] for r in LG._parts("corrie_b2_h1", "M")}
    n_st = len(BA.stations())
    # BL-051: the attachment rows book 8 stations and meat_haul.cradle_parts_g books the 4 US1 / US2 pins + sleeves
    # ('under-straps US1/US2: 7075 pins (4)'), so all 12 are booked; BL-050's 'booked short' delta was a double count
    n_at = len(BA._pins_booked_here())
    n_bk = n_at + sum(1 for s_ in BA.stations() if s_["name"] in BA.CRADLE_PIN_STATIONS)
    pin8 = led[f"attachment: 7075 pins ({n_at})"] * 8.0 / n_at
    sl8 = led[f"attachment: UHMWPE sleeves ({n_at})"] * 8.0 / n_at
    hw = hardware_g()
    st = ex["fairleads_bl042"].get("us2_clevis_bl050", {})
    m = {"assembled_g": ex["assembled"]["g"], "assembled_bl049_g": b49["assembled_g"],
         "print_delta_g": round(ex["assembled"]["g"] - b49["assembled_g"], 1),
         "joint_blocks_g": st.get("blocks_g"), "joint_cuts_g": st.get("cuts_g"),
         "lower_g": ex["lower"]["g"], "upper_g": ex["upper"]["g"],
         "clevis_g": {k: ex[k]["g"] for k in ("us2_clevis_R", "us2_clevis_L") if k in ex},
         "hardware": hw, "hardware_g": round(sum(hw.values()), 2),
         "stations": n_st, "pins_booked": n_bk, "pin_g": round(pin8 / 8.0, 3), "sleeve_g": round(sl8 / 8.0, 3),
         "pins_sleeves_delta_g": round((n_st - n_bk) * (pin8 + sl8) / 8.0, 2)}
    m["frame_delta_g"] = round(m["print_delta_g"] + m["hardware_g"], 2)
    return m


def compute(log=print) -> dict:
    from . import h1_fairleads as HF
    from . import h1_lanes as LN
    from . import spreader as SP
    ex = json.loads((REPO / "outputs" / "h1_lanes" / "export_info.json").read_text())
    ur = json.loads((ANALYSIS / "us_route.json").read_text())
    pl = ur["layouts"]["print_lanes"]
    pc = OUT / f"probe_{PROBE_X:g}.json"
    sc = OUT / "slice_checks.json"
    res = {"date": "2026-11-13", "ticket": "BL-050 Part A",
           "published": {"US1_X": LN.US1_X, "US1_Z": LN.US1_Z, "US2_X": LN.US2_X, "US2_Z": LN.US2_Z,
                         "STAY_X": LN.STAY_X, "CHANNEL_ENTRY_X": LN.CHANNEL_ENTRY_X, "US2_SPLIT_X": SPLIT_X,
                         "US2_BOLT_ON": True, "ARM_ISECT": dict(LN.ARM_ISECT)},
           "bed_mm": list(LN.BED_MM), "brim_mm": LN.BRIM_MM,
           "option_c": {"sweep": sweep_x(), "probe": json.loads(pc.read_text()) if pc.exists() else None},
           "bed": {nm: bed_check(HF.PRINT_DIR / f"h1_{nm}_flat.stl") for nm in ("lower", "upper")},
           "pieces": {k: {kk: ex[k][kk] for kk in ("g", "footprint_mm", "watertight", "shells")}
                      for k in ("us2_clevis_R", "us2_clevis_L") if k in ex},
           "export": {k: {kk: ex[k].get(kk) for kk in ("g", "watertight", "shells", "footprint_mm", "bed_bl050")}
                      for k in ("assembled", "lower", "upper")},
           "joint": joint_check(), "joint_share_1": joint_check(share=1.0),
           "joint_slices": joint_slices(),
           "lug_us2_bl049": {k: v for k, v in LN.lug_study(log=None)["us2"].items() if k != "rows"},
           "isect": isect_study(),
           "us_route": {"print_lanes": {"worst_clear_mm": pl["worst_clear_mm"], "pass": pl["pass"],
                                        "rows": [{"torso": r["torso"], "side": r["side"], "strap": r["strap"],
                                                  "min_clear_mm": r["min_clear_mm"], "pass": r["pass"]}
                                                 for r in pl["rows"]]},
                        "station_move": ur.get("station_move"), "test_piece": ur.get("test_piece")},
           "slice_checks": json.loads(sc.read_text()) if sc.exists() else None,
           "spreader_us2_notch": {k: v for k, v in SP.us2_notch_check().items() if k != "rows"},
           "mass": mass_rows()}
    RESULTS.write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))
    if log:
        log(f"  wrote {RESULTS.relative_to(REPO)}")
    return res


# ======================================================================================= figures
def _save(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    if path.stat().st_size > 1.5e6:
        from PIL import Image
        im = Image.open(path)
        im.thumbnail((1400, 1400))
        im.save(path, optimize=True)
    return str(path)


def plot_bed(res: dict, path: Path) -> str:
    """The flat halves as written on the H2S plate (brim band shaded), and the clevis piece."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Rectangle
    from scipy.spatial import ConvexHull
    from . import h1_fairleads as HF
    from .h1_lanes import BED_MM, BRIM_MM
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.6), gridspec_kw={"width_ratios": [1, 1, 0.55]})
    for ax, nm in zip(axs[:2], ("lower", "upper")):
        m = trimesh.load(HF.PRINT_DIR / f"h1_{nm}_flat.stl")
        P = m.vertices[:, :2]
        ax.add_patch(Rectangle((0, 0), BED_MM[0], BED_MM[1], fc="#eef2f6", ec="#1d1d1f", lw=1.2))
        ax.add_patch(Rectangle((BRIM_MM, BRIM_MM), BED_MM[0] - 2 * BRIM_MM, BED_MM[1] - 2 * BRIM_MM, fc="white",
                               ec="#888", lw=0.8, ls="--"))
        off = np.array([BRIM_MM, BRIM_MM])
        idx = np.random.default_rng(0).choice(len(P), min(len(P), 60000), replace=False)
        ax.plot(P[idx, 0] + off[0], P[idx, 1] + off[1], ",", color="#3b6e8f", alpha=0.6)
        H = P[ConvexHull(P).vertices] + off
        ax.fill(H[:, 0], H[:, 1], fc="none", ec="#c0392b", lw=0.8)
        b = res["bed"][nm]
        ax.set_title(f"{nm} half as written: {b['extents_mm'][0]:.1f} x {b['extents_mm'][1]:.1f} mm\n"
                     f"+ 8 mm brim: spare {b['spare_mm'][0]:.1f} / {b['spare_mm'][1]:.1f} mm "
                     f"({'fits' if b['fits_with_brim'] else 'DOES NOT FIT'})", fontsize=10)
        ax.set_xlim(-10, BED_MM[0] + 10)
        ax.set_ylim(-10, BED_MM[1] + 10)
        ax.set_aspect("equal")
        ax.set_xlabel("bed x, mm")
    m = trimesh.load(HF.PRINT_DIR / "us2_clevis_R.stl")
    for zz, col in ((0.5, "#8e44ad"), (0.6 * m.extents[2], "#c39bd3")):
        sec = m.section(plane_origin=[0, 0, zz], plane_normal=[0, 0, 1.0])
        if sec is not None:
            for L in sec.discrete:
                axs[2].plot(L[:, 0], L[:, 1], color=col, lw=1.2)
    axs[2].plot([], [], color="#8e44ad", label="section 0.5 mm off the plate")
    axs[2].plot([], [], color="#c39bd3", label="section at 60 % height (cheek)")
    axs[2].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    axs[2].set_aspect("equal")
    pg = res["pieces"].get("us2_clevis_R", {})
    axs[2].set_title(f"us2_clevis_R (x2 mirrored)\n{pg.get('g', 0):.1f} g, "
                     f"{' x '.join(f'{v:.0f}' for v in pg.get('footprint_mm', []))} mm", fontsize=10)
    fig.suptitle("BL-050 A: H1 halves on the Bambu H2S plate (340 x 320) with the US2 outer clevis bolted on",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, path)


def plot_joint(res: dict, path: Path) -> str:
    """US2 R joint: plan section at the pin height (body / clevis / bolts / traps), the joint face with the bolts,
    and the check utilizations (1 / SF) at the governing cradle row."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from matplotlib.patches import Circle, Rectangle
    from . import h1_fairleads as HF
    m = trimesh.load(HF.PRINT_DIR / "h1_assembled.stl")
    p = next(q for q in us2_stations() if q["side"] == "R")
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw={"width_ratios": [1.25, 0.8, 1.0]})
    ax = axs[0]
    for zz, col, lab in ((p["z"] + JOINT.dz, "#1d1d1f", f"section z {p['z'] + JOINT.dz:.0f} (bolt axis)"),
                         (p["z"], "#2c7fb8", f"section z {p['z']:.0f} (pin)")):
        sec = m.section(plane_origin=[0, 0, zz], plane_normal=[0, 0, 1.0])
        for L in sec.discrete:
            if L[:, 0].max() > 120 and L[:, 0].min() < 200:
                ax.plot(L[:, 0], L[:, 1], color=col, lw=0.9)
        ax.plot([], [], color=col, label=lab)
    ax.axvline(SPLIT_X, color="#c0392b", ls="--", lw=1.2, label=f"joint face |x| {SPLIT_X:.0f}")
    yb = p["yc"] + JOINT.dy
    ax.plot([JOINT.tail_x, JOINT.head_face + JOINT.head_h + 1], [yb, yb], color="#8e44ad", lw=3, alpha=0.6,
            label=f"Ti M5 x {JOINT.bolt_len:.0f} bolt axis")
    ax.add_patch(Rectangle((JOINT.trap_x0, p["yc"] + BLOCK_DY_LO - 1), JOINT.nut_face - JOINT.trap_x0,
                           yb + JOINT.slot_w / 2 - (p["yc"] + BLOCK_DY_LO - 1), fc="#f39c12", alpha=0.35,
                           label="nut + washer trap (opens to wearer face)"))
    ax.add_patch(Circle((p["x"], p["y_pin"]), 2.5, fc="#555", label="5 mm pin"))
    ax.set_xlim(120, 195)
    ax.set_ylim(-20, 32)
    ax.set_aspect("equal")
    ax.set_xlabel("frame x, mm (R side)")
    ax.set_ylabel("frame y (bag +), mm")
    ax.text(150, 27, "BODY (prints in the lower half)", ha="center", fontsize=9)
    ax.text(177, 27, "CLEVIS (own print)", ha="center", fontsize=9, color="#8e44ad")
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("US2 R lug: split in the throat floor, 2 bolts along x", fontsize=10)
    ax = axs[1]
    sec = m.section(plane_origin=[SPLIT_X - 0.5, 0, 0], plane_normal=[1.0, 0, 0])
    for L in sec.discrete:
        if abs(L[:, 2].mean() - p["z"]) < 30 and L[:, 1].min() > -30:
            ax.plot(L[:, 1], L[:, 2], color="#1d1d1f", lw=1.0)
    for (y, z) in bolt_axes(p):
        ax.add_patch(Circle((y, z), JOINT.washer_od / 2, fc="none", ec="#8e44ad", ls="--"))
    ax.set_aspect("equal")
    ax.set_xlabel("frame y, mm")
    ax.set_ylabel("frame z, mm")
    ax.set_title(f"joint face |x| {SPLIT_X:.0f}: block {2 * BLOCK_HALF_Z:.0f} mm tall,\nbolts at z +/-{JOINT.dz:.0f} "
                 f"(washer OD {JOINT.washer_od:.0f} dashed)", fontsize=10)
    ax = axs[2]
    j = res["joint"]
    row = j["rows"][j["worst_strength"]["load"]]
    keys = list(row["sf"])
    u_s = [1.0 / row["sf"][k] for k in keys]
    fk = list(row["fatigue"])
    u_f = [1.0 / row["fatigue"][k] for k in fk]
    yy = np.arange(len(keys))
    ax.barh(yy, u_s, color="#2c7fb8", label="strength (factored row)")
    ax.barh(np.arange(len(fk)) + len(keys) + 0.5, u_f, color="#e67e22", label="fatigue (1.6 g)")
    ax.set_yticks(list(yy) + list(np.arange(len(fk)) + len(keys) + 0.5))
    ax.set_yticklabels(keys + fk, fontsize=8)
    ax.axvline(1.0, color="#c0392b", lw=1.2)
    ax.axvline(1.0 / 1.15, color="#c0392b", lw=0.8, ls=":")
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("utilization = 1 / SF (red line = limit; dotted = fatigue goal 1.15)")
    ax.set_title(f"joint checks, governing row '{j['worst_strength']['load']}'\nmin SF {j['worst_strength']['sf']}, "
                 f"min fatigue {j['worst_fatigue']['fatigue']} (outer cheek share {j['share']})", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    fig.suptitle("BL-050 A: bolt-on US2 outer clevis (x +/-165 kept; the strap still clears by >= 10 mm)", x=0.02,
                 ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, path)


def plot_options(res: dict, path: Path) -> str:
    """Left: worst strap clearance per torso and side, US2 at 147 (option c, fits the bed) and 165 (as printed with
    the clevis); right: lug FEA, governing fatigue per region, solid arm vs the pocketed variants."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.4))
    ax = axs[0]
    pr = (res["option_c"].get("probe") or {}).get("route", {}).get("rows", [])
    now = res["us_route"]["print_lanes"]["rows"]
    labs = [f"{r['torso']} in {r['side']}" for r in now if r["strap"] == "us2"]
    a = [r["min_clear_mm"] for r in pr if r["strap"] == "us2"]
    b = [r["min_clear_mm"] for r in now if r["strap"] == "us2"]
    x = np.arange(len(labs))
    if a:
        ax.bar(x - 0.2, a, 0.4, color="#c0392b", label=f"US2 at x {PROBE_X:g} (option c, fits the bed)")
    ax.bar(x + 0.2, b, 0.4, color="#27ae60", label="US2 at x 165 (option a, bolt-on clevis)")
    ax.axhline(10.0, color="#1d1d1f", ls="--", lw=1, label="required 10 mm")
    ax.axhline(0.0, color="#888", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labs)
    ax.set_ylabel("US2 strap: least clearance to hinge fairlead / HE / US1, mm")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
    ax.set_title("strap route on the sliced print (15 / 19 / 23 in meat drapes)", fontsize=10)
    ax = axs[1]
    iv = res["isect"]
    names = ["solid"] + [k for k in iv if k not in ("solid", "adopted")]
    regs = ("fairlead", "arm", "root")
    w = 0.8 / len(names)
    for i, nm in enumerate(names):
        vals = [iv[nm]["lugs"][lug]["region_fatigue"][rg] for lug in ("us1", "us2") for rg in regs]
        lab = nm if nm == "solid" else f"{nm} (-{iv[nm]['saved_g']:.1f} g)"
        ax.bar(np.arange(6) + (i - len(names) / 2 + 0.5) * w, vals, w, label=lab)
    ax.axhline(1.0, color="#c0392b", lw=1)
    ax.set_xticks(np.arange(6))
    ax.set_xticklabels([f"{lug} {rg}" for lug in ("us1", "us2") for rg in regs], fontsize=8)
    ax.set_ylabel("lowest fatigue SF over the lug loads")
    ax.legend(fontsize=7.5)
    ax.set_title("lug arms: pocketing outboard of the root lowers every governing margin -> kept solid", fontsize=10)
    fig.suptitle("BL-050 A: why US2 is not moved in, and why the arms stay solid", x=0.02, ha="left", fontsize=12,
                 fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return _save(fig, path)


def plot_isect_field(path: Path) -> str:
    """Lug FEA (h1_lanes.lug_fea) of the US2 lug under its governing row (cradle, fleet in): failure index on the
    element layer at the pin height, solid arm vs the I-section, with the deformed outline (x 300)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import h1_lanes as LN
    gi = LN.lug_geom_inputs("us2")
    p = gi["p"]
    L = LN.lug_loads("us2")
    loads = {"cradle|fleet_in": L["cradle|fleet_in"]["vec"]}
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.2), sharey=True)
    for ax, (lab, arm) in zip(axs, (("solid arm (built)", dict(LN.ARM["us2"])),
                                    ("I-section (rejected)", {**LN.ARM["us2"], "isect": dict(LN.ISECT)}))):
        f = LN.lug_fea(p["geom"], p["stay_r"], gi["xoff"], arm, loads, h=1.0, field="cradle|fleet_in")
        fd = f["loads"]["_field"]
        c, fi = fd["cen"], fd["fi"]
        sel = np.abs(c[:, 2] - 4.5) < 0.6                     # the element layer at pin z + 4.5 (arm's upper half)
        sc = ax.scatter(c[sel, 0] + LN.STAY_X, c[sel, 1], c=fi[sel] * 1.6 / 2.4 / 0.3, s=9, marker="s",
                        cmap="inferno", vmin=0, vmax=1.5)
        ax.set_aspect("equal")
        ax.set_xlabel("frame x, mm")
        r = f["loads"]["cradle|fleet_in"]
        ax.set_title(f"{lab}: FI99 arm {r.get('arm', {}).get('fi99', float('nan')):.3f}, root "
                     f"{r.get('root', {}).get('fi99', float('nan')):.3f}", fontsize=10)
    axs[0].set_ylabel("frame y, mm")
    cb = fig.colorbar(sc, ax=axs, shrink=0.85)
    cb.set_label("fatigue utilization at 1.6 g (FI x 1.6/2.4 / 0.30); > 1 fails")
    fig.suptitle("BL-050 A: US2 lug FEA, bag-off cradle 720 N + 10 deg fleet, element layer at pin z + 4.5: "
                 "the open section lets the arm twist",
                 x=0.02, ha="left", fontsize=12, fontweight="bold")
    return _save(fig, path)


ASSUMPTIONS = [
    ("CLEVIS-SHARE", "The outer cheek (the bolt-on clevis) takes 0.6 of the pin's y-z load and the whole fleet x load "
     "when it pushes outboard (eye 18-19 mm in a 20 mm throat; centred = 0.5); the whole load on the clevis (1.0) is "
     "the sensitivity (json joint_share_1, section 2).", "US2 clevis joint pull on the CA-1 rig: us_route_stay_R + us2_clevis_R bolted, 720 N cradle "
     "direction, eye off-centre against the outer cheek, then 1e5 cycles at 480 N."),
    ("CLEVIS-DRY", "Dry butt joint, no preload credited (snug, as the z 234 joint), fitted bolts take the shear; no "
     "friction credited; the lug FEA (BL-049 stub, monolithic) stands for the cheeks and arm because the joint face "
     "sits under the throat floor, away from the cheek roots.", "Same pull test: no joint opening at 720 N (feeler "
     "0.05 mm), strain gauge at the arm root as STAY-STUB."),
    ("CLEVIS-PRINT", "The clevis prints in the body's orientation (wearer face on the plate, layer normal frame y), so "
     "its cheek is the cheek the BL-049 lug FEA checked; holes printed 4.8 and reamed 5.1 like every other bolt hole.",
     "First article: ream fit, slicer preview of the clevis."),
    ("SEAM-FLOOR", "The joint line crosses the US2 throat floor 8 mm from the inner cheek; the eye sits 5.5 mm above "
     "the floor (gap under the pin) and does not ride on it.", "FIT-US / HE-FIT step 0: slide the US eye across the "
     "seam under load; chamfer 0.3 mm both edges if it catches."),
    ("HEAD-PROUD", "The bolt heads stand 4.5 mm proud of the clevis's outer face (x +/-187.5 at z 134 / 150), inside "
     "the 394 mm pack width; the bag's side panel is outboard.", "FIT-US on P1: nothing rubs the heads."),
    ("BED-ROT", "The flat halves are written turned on the plate (lower 163.5 deg) so the slicer needs no rotation; the "
     "8 mm brim is from print/frame_h1/README.md.", "Slicer plate preview on the H2S profile, first article."),
    ("ROOT-AIR", "The spreader sheet rests on the stay crowns each side of the z 142 notch; the US2 arm root under it "
     "is >= 1.5 mm below that line (spreader.us2_notch_check).", "Spreader dry fit on the first article: 1.5 mm "
     "feeler between sheet and root."),
    ("PROBE-X", "Option (c) used US2 x 147 (largest x with the brim on the real export; the footprint sweep puts 149 "
     "0.7 mm over).", "Not needed: the strap fails by 13 mm at 147."),
]


BL051_NOTE = ("> **BL-051 (2026-11-13):** the print described here had the stay crown cut 2 mm low over z 86-104 and z 131-152 (`h1_lanes.strip_old_us`); it is restored and re-exported, see `h1_crown.md` for the current print masses (assembled 996.6 g), slice checks, US2 lug (real stay section) and the z 142 notch, whose 'root air' below was the cut-away crown (rule now: nothing proud of the support line). The clevis screw heads are counterbored (ASSUMPTION HEAD-PROUD retired; M5 x 35, no head washer, bolt axes at yc - 2.8) and the lug and joint carry the lane cradle rows (US2 860 N at a 50 mm belly). The ledger's pins / sleeves row (A4) is retired: the US1 / US2 pins + sleeves were already booked by `meat_haul.cradle_parts_g` (a double count, -10.8 g).\n")


def write_md(res: dict, shots: list) -> str:
    j, j1 = res["joint"], res["joint_share_1"]
    pr = res["option_c"]["probe"] or {}
    m = res["mass"]
    bl, bu = res["bed"]["lower"], res["bed"]["upper"]
    ur = res["us_route"]["print_lanes"]
    lg = res["lug_us2_bl049"]
    sp = res["spreader_us2_notch"]
    iv = res["isect"]
    w = []
    a = w.append
    a("# H1 print-bed fit with the US2 lanes: bolt-on US2 outer clevis (BL-050 Part A)")
    a(BL051_NOTE)
    a("")
    a("structural-fea-engineer, 2026-11-13. Ticket `docs/backlog/BL-050-bed-fit-and-bag-lanes.md` Part A. Code "
      "`huntkit/gendesign/h1_bedfit.py` (`python -m huntkit.gendesign.h1_bedfit --probe 147 | --joint`; the report "
      "with no flag), hooked into `h1_buckling.export_print` (`US2_CLEVIS`); I-section option in `h1_lanes` "
      "(`ISECT`, `ARM_ISECT`); spreader check `spreader.us2_notch_check`; tests `tests/test_h1_bedfit.py`. Results "
      "`h1_bedfit.json`. Units mm, N, g (imperial in brackets).")
    a("")
    a("## Summary")
    a("")
    a(f"- **Option (c) fails.** The largest US2 x whose lower half fits the H2S with the 8 mm brim is about "
      f"{PROBE_X:g} mm (real export: {pr.get('bed', {}).get('lower', {}).get('best_rotation', {}).get('w_mm', '?')} x "
      f"{pr.get('bed', {}).get('lower', {}).get('best_rotation', {}).get('h_mm', '?')} mm at its best rotation). "
      f"There the US2 strap hits the hinge fairlead: worst clearance "
      f"**{pr.get('route', {}).get('worst_clear_mm', {}).get('us2', '?')} mm** against >= 10 (23 in R); "
      f"every torso and side is below 10 mm.")
    a(f"- **Option (a) adopted: bolt-on US2 outer clevis.** US2 stays at x +/-165 (z 142). The US2 fairlead is split at "
      f"|x| {SPLIT_X:g} in the throat floor; the outer floor + outer cheek print as `us2_clevis_R` / `_L` "
      f"({m['clevis_g'].get('us2_clevis_R', 0):.1f} g each) and bolt to the body with two Ti M5 x {j['joint']['bolt_len']:g} "
      f"along x (the z 234 joint's screw type), nuts in side traps. Joint (outer cheek share {j['share']}): strength "
      f"**{j['worst_strength']['sf']}** ({j['worst_strength']['check']}, {j['worst_strength']['load']}), fatigue "
      f"**{j['worst_fatigue']['fatigue']}** ({j['worst_fatigue']['check']}); at share 1.0 {j1['worst_strength']['sf']}"
      f" / {j1['worst_fatigue']['fatigue']}.")
    a(f"- **Bed:** lower half as written **{bl['extents_mm'][0]:.1f} x {bl['extents_mm'][1]:.1f} mm** "
      f"(turned {res['export']['lower']['bed_bl050']['rot_deg']:g} deg on the plate), + 8 mm brim: "
      f"{bl['spare_mm'][0]:.1f} / {bl['spare_mm'][1]:.1f} mm spare; upper {bu['extents_mm'][0]:.1f} x "
      f"{bu['extents_mm'][1]:.1f} ({bu['spare_mm'][0]:.1f} / {bu['spare_mm'][1]:.1f} spare). "
      "`test_print_halves_fit_the_h2s_bed` passes (xfail removed).")
    a(f"- **Strap route on the new STL** (`us_route.py`, 'print_lanes'): worst US1 {ur['worst_clear_mm']['us1']} / "
      f"US2 {ur['worst_clear_mm']['us2']} mm, every torso and side >= 10: pass {ur['pass']}. US2 lug (BL-049 lug "
      f"FEA, geometry unchanged at x 165): strength {lg['worst_strength']['sf']}, fatigue "
      f"{lg['worst_fatigue']['fatigue']} ({lg['worst_fatigue']['load']}, root).")
    a(f"- **Lug arms (A2): kept solid.** I-section (3 mm web / flanges, about -{iv['I_w3_f3']['saved_g']:.0f} g) drops "
      f"the US1 arm fatigue {iv['solid']['lugs']['us1']['region_fatigue']['arm']} -> "
      f"{iv['I_w3_f3']['lugs']['us1']['region_fatigue']['arm']} and the roots too (open section, the arm twists); "
      "closed box variants also lower the roots. No variant holds every margin.")
    a(f"- **Spreader (A3):** the z 142 notch is 0 mm from the US2 arm root in plan (by construction), but the root "
      f"lies under the sheet: measured air **{sp['air_mm']} mm** below the crown line the sheet bears on (>= "
      f"{sp['air_req_mm']}): pass. Clearance rule fixed (3D, `spreader.us2_notch_check`); the sheet is not re-cut.")
    a(f"- **Ledger (A4):** pins + sleeves booked for 8 stations, 12 placed: +{m['pins_sleeves_delta_g']:.2f} g "
      f"(every config). Print +{m['print_delta_g']:.1f} g (joint blocks), joint hardware +{m['hardware_g']:.1f} g: "
      f"frame **+{m['frame_delta_g']:.1f} g (+{m['frame_delta_g'] / 28.3495:.2f} oz)** against BL-049. Rows BL050.")
    a("")
    a("## 1. Option (c): bring US2 in")
    a("")
    a("Footprint sweep on the BL-049 lower half (the US2 lug and fairlead moved in rigidly), best rotation, 8 mm brim:")
    a("")
    a("| US2 x | best rotation deg | footprint mm | over the bed with brim, mm |")
    a("|---:|---:|---|---:|")
    for r in res["option_c"]["sweep"]:
        a(f"| {r['us2_x']:g} | {r['deg']:g} | {r['w_mm']:.1f} x {r['h_mm']:.1f} | {r['over_mm']:+.1f} |")
    a("")
    if pr:
        bp = pr["bed"]["lower"]
        a(f"Real export with US2 at x {pr['us2_x']:g} (`probe`, outputs/h1_bedfit/probe_{pr['us2_x']:g}): lower half "
          f"{bp['extents_mm'][0]} x {bp['extents_mm'][1]} mm as laid flat, best rotation "
          f"{bp['best_rotation']['w_mm']} x {bp['best_rotation']['h_mm']} at {bp['best_rotation']['deg']:g} deg, over "
          f"{bp['best_rotation']['over_mm']:+.1f} mm with the brim: fits. Strap route on that STL:")
        a("")
        a("| torso | side | US2 least clearance mm (hinge / HE / US1) | pass |")
        a("|---:|---|---:|---|")
        for r in pr["route"]["rows"]:
            if r["strap"] == "us2":
                a(f"| {r['torso']} | {r['side']} | {r['min_clear_mm']} | {r['pass']} |")
        a("")
        a("The strap's 25 mm ribbon comes off a pin 32 mm outboard of the stay and runs past the hinge fairlead's "
          "outer cheek (x 135): the BL-048 lane offset (throat / 2 + cheek + 10 + strap / 2 = 42.5 mm, 157.5) is "
          "already more than the bed allows. Option (c) is out.")
    a("")
    a("## 2. Option (a): bolt-on US2 outer clevis")
    a("")
    jt = j["joint"]
    a(f"- Split plane |x| {SPLIT_X:g}: in the US2 throat floor (throat 155-175), so the body prints the arm, the "
      f"inner cheek and 8 mm of floor; the clevis is the outer 12 mm of floor and the outer cheek (175-183).")
    a(f"- Joint blocks under the throat floor: y {BLOCK_DY_LO:+g} from the stay centre (y -12.5) to the floor "
      f"(y 8.4), z +/-{BLOCK_HALF_Z:g} about the pin; body block |x| {BODY_BLOCK_X0:g}-{SPLIT_X:g}, clevis "
      f"{SPLIT_X:g}-{jt['head_face']:g}. Above the floor nothing changes (throat, cheeks, pin, eye envelope).")
    a(f"- Two Ti gr5 M5 x {jt['bolt_len']:g} DIN 7984 along x at y {jt['dy']:+g} from the stay centre, z +/-{jt['dz']:g}"
      f"; DIN 433 washers (OD {jt['washer_od']:g}); head on the clevis's outer face, nut + washer in a side trap in "
      f"the body (|x| {jt['trap_x0']:g}-{jt['nut_face']:g}) that opens to the wearer face. Holes printed "
      f"{jt['hole_print_d']:g}, reamed {jt['hole_d']:g}. Plugs: body {SPLIT_X - jt['nut_face']:g} mm, clevis "
      f"{jt['head_face'] - SPLIT_X:g} mm.")
    a("- Loads: every US2 row of `h1_lanes.lug_loads` (bag-off cradle 720 N at 2.4, bag-on 296 N at 3.0, +/-10 deg "
      "fleet); fatigue at 1.6 g (row x 1.6 / basis). The clevis gets the outer cheek's share (CLEVIS-SHARE) at the "
      "outer cheek centre on the pin line. Face: rigid dry contact, tension-only bolts, no preload "
      "(`frame_h1.contact_solve`, as the z 234 joint); bolt shear = direct + the torsion couple; capacities by the "
      "z 234 joint's rules (`frame_h1.joint_capacities`; hole bearing on the interlayer strength, conservative). "
      "Body net section through the traps: biaxial bending + axial (magnitudes added), torsion and shear, layer rule.")
    a("")
    a("| load | on clevis N (x, y, z) | bolt T N | bolt V N | contact MPa | net-section FI | min SF | min fatigue |")
    a("|---|---|---|---|---:|---:|---:|---:|")
    for k, r in j["rows"].items():
        a(f"| {k} | {', '.join(f'{v:.0f}' for v in r['force_on_clevis_n'])} | "
          f"{' / '.join(f'{v:.0f}' for v in r['bolt_tension_n'])} | {' / '.join(f'{v:.0f}' for v in r['bolt_shear_n'])}"
          f" | {r['contact_mpa']} | {r['net_section_fi']} | {r['min_sf']} | {r['min_fatigue']} |")
    a("")
    a("Capacities (N): " + ", ".join(f"{k} {v:g}" for k, v in j["capacities_n"].items()) + ".")
    a("")
    a(f"Governing: strength {j['worst_strength']['sf']} ({j['worst_strength']['check']}), fatigue "
      f"{j['worst_fatigue']['fatigue']} ({j['worst_fatigue']['check']}), both on the cradle row. With the whole "
      f"pin load on the clevis (share 1.0): {j1['worst_strength']['sf']} / {j1['worst_fatigue']['fatigue']}. The "
      f"Ti bolts are far from their limits (tension SF >= {min(r['sf']['bolt_tension'] for r in j['rows'].values()):.0f}"
      f"); the PAHT round the fitted holes governs.")
    a("")
    js = res["joint_slices"]
    a(f"**Slice check of the joint on the print** (`joint_slices`, both sides pass {js['pass']}): at |x| 170 the clevis "
      f"section has two holes of d_eq "
      f"{', '.join(str(h['d_eq_mm']) for h in js['R']['clevis_170']['holes'])} mm on the bolt axes; at the trap plane the "
      f"traps open to the wearer face and the block top is whole; the joint face is a closed "
      f"{js['R']['face']['outer_area_mm2']:.0f} mm2 section.")
    a("")
    a("## 3. Print files and checks")
    a("")
    a("| file | g | watertight | shells | as written mm | + 8 mm brim on 340 x 320 |")
    a("|---|---:|---|---:|---|---|")
    ex = res["export"]
    a(f"| h1_assembled.stl (body + clevises, frame coordinates) | {ex['assembled']['g']} | "
      f"{ex['assembled']['watertight']} | {ex['assembled']['shells']} | | |")
    for nm in ("lower", "upper"):
        b = res["bed"][nm]
        a(f"| h1_{nm}_flat.stl | {ex[nm]['g']} | {ex[nm]['watertight']} | {ex[nm]['shells']} | "
          f"{b['extents_mm'][0]:.1f} x {b['extents_mm'][1]:.1f} x {b['extents_mm'][2]:.1f} | fits {b['fits_with_brim']}"
          f", spare {b['spare_mm'][0]:.1f} / {b['spare_mm'][1]:.1f} |")
    for k, v in res["pieces"].items():
        a(f"| {k}.stl | {v['g']} | {v['watertight']} | {v['shells']} | "
          f"{' x '.join(f'{x:.1f}' for x in v['footprint_mm'])} | fits |")
    a("")
    sc = res["slice_checks"] or {}
    if sc:
        a(f"Slice checks on `h1_assembled.stl` (`h1_lanes.slice_checks`): fairleads 12 / 12 pass "
          f"{sc['fairleads_pass']} (eye stacks included; US2 R/L gap under pin "
          f"{sc['fairleads']['us2_R']['gap_under_pin']} / {sc['fairleads']['us2_L']['gap_under_pin']}, cheeks "
          f"{sc['fairleads']['us2_R']['cheek_mm']}); spine channel pass {sc['channel']['pass']} (clear "
          f"{sc['channel']['min']['clear_mm']} mm); pawl pass {sc['pawl']['pass']}; test pieces pass "
          f"{sc['pieces_pass']} ({', '.join(sc['pieces'])}).")
    tp = res["us_route"]["test_piece"] or {}
    a("")
    a(f"Test piece `print/frame_h1/test_pieces/us_route_stay_R.stl` re-cut: {tp.get('g')} g as printed (the US2 "
      f"outer clevis is not in it: bolt `us2_clevis_R` from the frame folder onto it, {tp.get('g_as_assembled')} g "
      "assembled); the `_frame_coords` copy is the piece as assembled (the slice checks read it).")
    a("")
    a("**Strap route on the new STL** (`designs/pack_5200/us_route.py`, 'print_lanes', channel ends at the lane x):")
    a("")
    a("| torso | side | US1 mm | US2 mm |")
    a("|---:|---|---:|---:|")
    for t in (15, 19, 23):
        for sd in ("R", "L"):
            v = {r["strap"]: r["min_clear_mm"] for r in ur["rows"] if r["torso"] == t and r["side"] == sd}
            a(f"| {t} | {sd} | {v.get('us1')} | {v.get('us2')} |")
    a("")
    a("## 4. Lug arms as I-sections (A2)")
    a("")
    a("Same lug FEA as BL-049 (`h1_lanes.lug_fea`, stay stub, 1 mm voxels, every US load), arm pocketed from |x - "
      "stay| = stay radius + 6 mm to 2 mm short of the fairlead. Lowest fatigue per region over the loads "
      "(strength in brackets):")
    a("")
    a("| arm | g saved (4 arms) | US1 fairlead / arm / root | US2 fairlead / arm / root | every margin holds |")
    a("|---|---:|---|---|---|")
    for k, v in iv.items():
        if k == "adopted":
            continue
        u1, u2 = v["lugs"]["us1"], v["lugs"]["us2"]
        a(f"| {k} | {v['saved_g']:.1f} | {u1['region_fatigue']['fairlead']} / {u1['region_fatigue']['arm']} / "
          f"{u1['region_fatigue']['root']} ({u1['strength']}) | {u2['region_fatigue']['fairlead']} / "
          f"{u2['region_fatigue']['arm']} / {u2['region_fatigue']['root']} ({u2['strength']}) | "
          f"{v.get('every_margin_holds', '-')} |")
    a("")
    a("The cradle pulls the pin aft and down 17-23 mm above the arm's centre line, so the arm carries torsion as well "
      "as bending; an open I-section has a small fraction of the solid arm's torsion stiffness, the arm twists and "
      "the stress moves into the web and the root. A closed box keeps the torsion but the thin walls still raise "
      "the root (US1 0.80 -> 0.76-0.78). **Arms stay solid** (`h1_lanes.ARM_ISECT` all False); the -15 g is not "
      "available at these margins.")
    a("")
    a("## 5. Spreader US2 notch (A3)")
    a("")
    a(f"In plan the notch (z {sp['notch_z'][0]:g}-{sp['notch_z'][1]:g}) and the US2 arm root (z {sp['root_z'][0]:g}-"
      f"{sp['root_z'][1]:g}) coincide: plan clearance {abs(sp['plan_clear_mm']):g} mm. The notch cannot grow (z 121 "
      "would cut the z 119 clip tab and the z 118.5 bottom edge tube) and the root cannot shrink (it governs the "
      "US2 lug). But NOTCH_CLEAR is the air round a cleat that stands up through the sheet, and the arm root does "
      "not: its top is the stay crown line, and on the print it sits under it. Measured on `h1_assembled.stl` "
      f"(`spreader.us2_notch_check`): the sheet's support (stay crown) is y {sp['support_bands']['below']['y']} at z "
      f"{sp['support_bands']['below']['z']:g} and y {sp['support_bands']['above']['y']} at z "
      f"{sp['support_bands']['above']['z']:g}; the highest print inside the notch footprint is **{sp['air_mm']} mm** "
      f"below that line (required {sp['air_req_mm']}): pass. The rule is now the 3D one; the sheet is not re-cut. "
      "Owner option: close the z 142 notch (no cleat there any more), which needs the spreader re-run.")
    a("")
    a("## 6. Mass")
    a("")
    a("| item | g | oz |")
    a("|---|---:|---:|")
    a(f"| print: joint blocks + bolt / trap cuts (assembled BL-050 {m['assembled_g']} - BL-049 "
      f"{m['assembled_bl049_g']}) | {m['print_delta_g']:+.1f} | {m['print_delta_g'] / 28.3495:+.2f} |")
    for k, v in m["hardware"].items():
        a(f"| {k} | {v:+.2f} | {v / 28.3495:+.3f} |")
    a(f"| **frame, net (BL050 H1 rows)** | **{m['frame_delta_g']:+.1f}** | **{m['frame_delta_g'] / 28.3495:+.2f}** |")
    a(f"| attachment: 7075 pins ({m['pin_g']} g) + UHMWPE sleeves ({m['sleeve_g']} g) for {m['stations'] - 8} more "
      f"stations | {m['pins_sleeves_delta_g']:+.2f} | {m['pins_sleeves_delta_g'] / 28.3495:+.3f} |")
    a("")
    a(f"Printed: lower {m['lower_g']} g, upper {m['upper_g']} g, clevises "
      f"{sum(m['clevis_g'].values()):.1f} g ({m['assembled_g']} g, {m['assembled_g'] / 453.59:.2f} lb). Ledger rows "
      "BL050 (`huntkit/mass/ledger.py`, from this json).")
    a("")
    a("**Mass reductions that keep the SF (not applied):** (1) the joint blocks are sized by the M5 washer and the "
      "trap: the clevis block outboard of the outer cheek root could be chamfered under the cheek (about -2 g, needs "
      "the net-section re-check only); (2) the US1 arm onto the lower branch it touches (BL-049 proposal 2) - it "
      "would also lift the US1 root (fatigue 0.80 on the stub model), which is what blocks every lighter arm.")
    a("")
    a("## 7. Assumptions")
    a("")
    for k, t, s_ in ASSUMPTIONS:
        a(f"- ASSUMPTION {k}: {t} Settled by: {s_}")
    a("- Carried: HINGE-ROW, FI99-RULE, STAY-STUB, LANE-MOMENT, PIN-KS, PIN-L, SUPPORTS, SHEET-CLEAR (now ROOT-AIR) "
      "(h1_lanes.md 6); US-FLEET, US-TOPO, DRAPE-US (us_route.json); the z 234 joint rules (frame_h1).")
    a("")
    a("## 8. Screenshots")
    a("")
    for s_ in shots:
        a(f"- `{Path(s_).relative_to(REPO)}`")
    DOC.write_text("\n".join(w) + "\n")
    return str(DOC)


def report(log=print) -> dict:
    res = compute(log=log)
    shots = [plot_bed(res, SCREENS / f"{SHOT}1.png"), plot_joint(res, SCREENS / f"{SHOT}2.png"),
             plot_options(res, SCREENS / f"{SHOT}3.png"), plot_isect_field(SCREENS / f"{SHOT}4.png")]
    for s_ in (SCREENS / "20261113_BL050_us_1.png", SCREENS / "20261113_BL050_us_2.png"):
        if s_.exists():
            shots.append(str(s_))
    write_md(res, shots)
    if log:
        log(f"  wrote {DOC.relative_to(REPO)}; screens {shots}")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--probe", type=float, default=None)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--joint", action="store_true")
    a = ap.parse_args(argv)
    if a.sweep:
        for r in sweep_x():
            print(r)
    if a.probe is not None:
        print(json.dumps(probe(a.probe), indent=1, default=float)[:3000])
    if not (a.sweep or a.probe is not None or a.joint):
        report()
    if a.joint:
        r = joint_check()
        print(json.dumps({k: r[k] for k in ("capacities_n", "worst_strength", "worst_fatigue", "net_section")},
                         indent=1))
        for k, v in r["rows"].items():
            print(k, v["bolt_tension_n"], v["bolt_shear_n"], v["min_sf"], v["min_fatigue"], v["net_section_fi"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
