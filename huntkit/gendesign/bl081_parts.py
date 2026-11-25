"""BL-081 parts for concept B81: printed PAHT-CF nodes and PLA drill jigs (STL), the tube / metal cut list, mass and
cost bill, and the coupon / proof list.

Printed nodes are designed so PAHT sees only bolt preload and contact in compression or pin bearing: every load path
between tubes is a 6061 part or a bolt (``bl081_concept_b`` module docstring). Print orientation is chosen so the
compression acts across the layers (layer normal = the bolt / clamp axis).

Coordinates of the STL: frame axes (x lateral, y aft, z up, mm) for the right-hand (R) part; the L part is the mirror
in x. ``print/`` holds one file per part as placed on the bed (largest flat face down).
"""
from __future__ import annotations

import math

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ

PRINT = BQ.OUTDIR / "print"
JIGS = BQ.OUTDIR / "jigs"
FIT = 0.15                  # printed bore over the tube OD, radial (ASSUMPTION FIT-PRINT, settled on the fit-up trial)
CLR = 5.6                   # bolt clearance through printed parts (oversize: the bolt bears on metal first)
SEG = 72


def _M():
    from manifold3d import Manifold
    return Manifold


def box(x0, x1, y0, y1, z0, z1):
    M = _M()
    return M.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl(axis, c, r, h0, h1, seg=SEG):
    """Cylinder radius r along ``axis`` ('x'|'y'|'z') from h0 to h1, centre c = (a, b) in the other two axes."""
    M = _M()
    m = M.cylinder(h1 - h0, r, r, seg).translate((0, 0, h0))
    if axis == "x":
        m = m.rotate((0, 90, 0))           # z -> x (z -> -x? rotate +90 about y maps z to x)
        return m.translate((0, c[0], c[1]))
    if axis == "y":
        m = m.rotate((-90, 0, 0))          # z -> y
        return m.translate((c[0], 0, c[1]))
    return m.translate((c[0], c[1], 0))


def to_trimesh(m):
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


# ============================================================================ geometry helpers
def yc(z):
    return -10.0 * z / 530.0


def stay_r(cfg):
    return BQ.STOCK[cfg["stay"]]["od"] / 2


# ============================================================================ printed nodes (right-hand)
def foot_cup(cfg):
    """Cup round the stay foot: 38 x 38 6061 foot-plate pocket, 3 mm floor, sleeve to z 75, outboard cheek column
    (12 mm) standing on the base so the hinge-pin load reaches the ground side in compression; pin hole z 60 along x."""
    R = stay_r(cfg)
    x0 = 115.0
    floor, plate = 3.0, 0.125 * BQ.IN
    zb = -plate - floor
    base = box(x0 - 23, x0 + R + 18 + 12, -23, 23, zb, 6)
    sleeve = cyl("z", (x0, 0.0), R + 3.2, zb, 75)
    cheek = box(x0 + R + 18, x0 + R + 18 + 12, -10, 10, zb, 72)
    body = base + sleeve + cheek
    body = body - cyl("z", (x0, 0.0), R + FIT, 0.0, 80)
    body = body - box(x0 - 19.2, x0 + 19.2, -19.2, 19.2, -plate - 0.1, 0.01)
    body = body - cyl("x", (0.0, 60.0), 2.65, x0 - R - 6, x0 + R + 18 + 13)
    # eye window between the stay and the cheek
    body = body - box(x0 + R + 3.2, x0 + R + 18, -12, 12, 40, 80)
    return body


def lumbar_filler(cfg):
    """Filler between the front and back 6061 L-gussets: an L slab 2 (R + 1) thick minus both tubes (bore + FIT),
    bolt clearance holes; top face z 165 is the IM1 loop seat. Printed lying on a face: preload across the layers."""
    R = stay_r(cfg)
    ycen = yc(120.0)
    th = R + 1.0
    w = cfg["gusset_w"] / 2
    z1, z2 = cfg["stay_bolt_z"]
    xb1, xb2 = cfg["ct_bolt_x"]
    v = box(115 - w, 115 + w, ycen - th, ycen + th, z1 - 15, z2 + 10)
    hz = box(min(xb2, xb1) - 12, 115, ycen - th, ycen + th, 120 - w, 120 + w)
    body = v + hz
    body = body - cyl("z", (115.0, ycen), R + FIT, z1 - 20, z2 + 20)
    body = body - cyl("x", (ycen, 120.0), R + FIT, min(xb2, xb1) - 20, 115.0)
    for z in (z1, z2):
        body = body - cyl("y", (115.0, z), CLR / 2, ycen - th - 1, ycen + th + 1)
    for x in (xb1, xb2):
        body = body - cyl("y", (x, 120.0), CLR / 2, ycen - th - 1, ycen + th + 1)
    return body


def tee_half(cfg, z, bar_key, front=True):
    """One half of a clamp tee (split on the stay plane): stay jaw 40 mm, bar socket 30 mm, two clamp-bolt bosses
    beside the stay (x 115 +/- (R + 3.5)), bar bolt at x 80; 3.3 mm recess for the 1 x 1/8 backer. Printed split face
    down (layer normal y): the clamp pressure acts across the layers."""
    R = stay_r(cfg)
    rb = BQ.STOCK[bar_key]["od"] / 2
    Lc = cfg["clamp_len"]
    y0 = yc(z)
    s = -1.0 if front else 1.0
    depth = R + 4.0
    ya, yb = (y0 - depth, y0) if front else (y0, y0 + depth)
    jaw = box(115 - R - 9, 115 + R + 9, ya, yb, z - Lc / 2, z + Lc / 2)
    sock = box(115 - R - 40, 115 - R + 1, ya, yb, z - rb - 4, z + rb + 4)
    body = jaw + sock
    body = body - cyl("z", (115.0, y0), R + FIT, z - Lc, z + Lc)
    body = body - cyl("x", (y0, z), rb + FIT, 115 - R - 41, 115 - R + 2)
    for x in (115 - R - 3.5, 115 + R + 3.5):
        body = body - cyl("y", (x, z), CLR / 2, y0 - depth - 1, y0 + depth + 1)
    body = body - cyl("y", (80.0, z), CLR / 2, y0 - depth - 1, y0 + depth + 1)
    # backer recess on the outer face (25.6 wide, 3.3 deep)
    yr0, yr1 = ((y0 - depth - 0.1, y0 - depth + 3.3) if front else (y0 + depth - 3.3, y0 + depth + 0.1))
    body = body - box(78 - 8, 115 + R + 9.1, yr0, yr1, z - 12.8, z + 12.8)
    # 1 mm split gap so the halves close on the tube
    gap = box(70, 150, y0 - 0.5, y0 + 0.5, z - Lc, z + Lc)
    return body - gap


def stay_top_collar(cfg):
    """Cap on the stay top end: rests on the rim (compression), holds the top bushing flange; bore for the leg."""
    R = stay_r(cfg)
    y0 = yc(530.0)
    ring = cyl("z", (115.0, y0), R + 3.0, 515.0, 533.0) - cyl("z", (115.0, y0), R + FIT, 514.0, 530.0)
    return ring - cyl("z", (115.0, y0), 9.8, 529.0, 534.0)


def hip_saddle(cfg):
    """1 mm-min saddle shim between the cross tube and the front / back angle legs (x2 per frame)."""
    R = BQ.STOCK[cfg["ctube"]]["od"] / 2
    L = cfg["bracket_len"]
    ycen = yc(120.0)
    blk = box(-L / 2, L / 2, ycen - R - 4.0, ycen - R + 4.0, 120 - 12, 120 + 12)
    blk = blk - cyl("x", (ycen, 120.0), R + FIT, -L, L)
    for k in cfg["key_x"]:
        for x in (-k, k):
            blk = blk - cyl("y", (x, 120.0), CLR / 2, ycen - R - 5, ycen + R + 5)
    return blk


def saddle_plug(cfg):
    """Plug in each cross-tube end (25 mm in the bore) with a 140 deg saddle that bears on the stay side: the lumbar
    node's fore-aft and x loads in compression / bearing. Printed lying on its side: the plug axis lies in the layer
    plane, so its body shear is in-plane. The x 90 gusset bolt passes through a clearance hole (no bearing on PAHT)."""
    ct = BQ.STOCK[cfg["ctube"]]
    st = BQ.STOCK[cfg["stay"]]
    ycen = yc(120.0)
    x_end = 115.0 - st["od"] / 2 - 1.0
    ri = ct["od"] / 2 - ct["t"] - 0.15
    plug = cyl("x", (ycen, 120.0), ri, x_end - 25.0, x_end)
    head = cyl("x", (ycen, 120.0), ct["od"] / 2, x_end, 115.0 - st["od"] / 2 * 0.35)
    body = plug + head
    body = body - cyl("z", (115.0, ycen), st["od"] / 2 + FIT, 90.0, 150.0)
    body = body - cyl("y", (cfg["ct_bolt_x"][0], 120.0), CLR / 2 + 0.2, ycen - 20, ycen + 20)
    return body


PARTS = {   # name: (builder, count per frame, mirror pair?)
    "foot_cup": (foot_cup, 2, True),
    "lumbar_filler": (lumbar_filler, 2, True),
    "tee_mid_front": (lambda c: tee_half(c, 330.0, c["bar"], True), 2, True),
    "tee_mid_back": (lambda c: tee_half(c, 330.0, c["bar"], False), 2, True),
    "tee_upper_front": (lambda c: tee_half(c, 520.0, c["ubar"], True), 2, True),
    "tee_upper_back": (lambda c: tee_half(c, 520.0, c["ubar"], False), 2, True),
    "stay_top_collar": (stay_top_collar, 2, True),
    "hip_saddle": (hip_saddle, 2, False),
    "saddle_plug": (saddle_plug, 2, True),
}
# kept from BL-080 (not redesigned here): pawl housing + spine guide 30 g (now clamped to the 1 in bar by the 2 pawl
# bolts), lash clips 4 x 6 g, US2 clevises 2 x 15.7 g (BL-050 part)
CARRIED_PRINTED_G = {"pawl housing + spine guide (BL-080 estimate)": 30.0, "lash clips z 250 / 420 x 4": 24.0,
                     "US2 clevis x 2 (BL-050 part)": 31.4}


# ============================================================================ jigs (PLA, not frame mass)
def tube_jig(od, length, holes, end_stop=True, name=""):
    """V-cradle drill jig for a round tube: holes = [(s along the tube from the stop face, axis 'y'|'x')], guide
    bushing D5.2 (drill) through the cradle wall, end stop at s 0."""
    R = od / 2
    w = od + 16
    body = box(-6 if end_stop else 0, length, -w / 2, w / 2, -R - 6, R * 0.55)
    body = body - cyl("x", (0.0, 0.0), R + 0.2, 0, length + 1)
    for s, ax in holes:
        if ax == "y":       # drill along the jig's y (horizontal, through the side walls)
            body = body - cyl("y", (s, 0.0), 2.6, -w, w)
        else:               # drill down through the floor (vertical)
            body = body - cyl("z", (s, 0.0), 2.6, -R - 10, R)
    return body


def gusset_template(cfg):
    """2 mm PLA template of the .090 L-gusset (stay arm z 70-170, cross arm to x 50), guide holes D5.2; scribe and
    drill four plates (flip for L / R)."""
    w = cfg["gusset_w"]
    z1, z2 = cfg["stay_bolt_z"]
    xb1, xb2 = cfg["ct_bolt_x"]
    v = box(115 - w / 2, 115 + w / 2, 0, 2, z1 - 15, z2 + 10)
    hz = box(min(xb1, xb2) - 12, 115, 0, 2, 120 - w / 2, 120 + w / 2)
    t = v + hz
    for z in (z1, z2):
        t = t - cyl("y", (115.0, z), 2.6, -1, 3)
    for x in (xb1, xb2):
        t = t - cyl("y", (x, 120.0), 2.6, -1, 3)
    return t


def angle_jig(cfg):
    """Drill template for the two bracket angles: the Ti-mount 6 positions + key bolts on the front leg, web-lap holes."""
    L = cfg["bracket_len"]
    t = box(-L / 2 - 6, L / 2 + 6, 0, 3, 100, 146)
    for x, z in BQ.MOUNT_POS:
        t = t - cyl("y", (x, z), 2.6, -1, 4)
    t = t - cyl("y", (0.0, 120.0), 5.4, -1, 4)                 # pin bore D10 + 0.8
    for k in cfg["key_x"]:
        for x in (-k, k):
            t = t - cyl("y", (x, 120.0), 2.6, -1, 4)
    return t


def jig_set(cfg):
    st = BQ.STOCK[cfg["stay"]]
    ct = BQ.STOCK[cfg["ctube"]]
    ub = BQ.STOCK[cfg["ubar"]]
    z1, z2 = cfg["stay_bolt_z"]
    xb1, xb2 = cfg["ct_bolt_x"]
    half_ct = 115 - 12.7 - 1.0
    return {
        "jig_stay_foot": tube_jig(st["od"], 170.0, [(60.0, "y"), (z1, "z"), (z2, "z")]),
        "jig_cross_tube_half": tube_jig(ct["od"], half_ct + 2, [(half_ct - xb1, "z"), (half_ct - xb2, "z")]
                                        + [(half_ct - k, "z") for k in cfg["key_x"]]),
        "jig_upper_bar_half": tube_jig(ub["od"], half_ct + 2, [(half_ct - 15.0, "z"), (half_ct - (115 - 12.7 - 80), "z")]),
        "jig_gusset_template": gusset_template(cfg),
        "jig_angle_template": angle_jig(cfg),
    }


# ============================================================================ export
def export(cfg=None, log=print) -> dict:
    cfg = {**BQ.CFG0, **(cfg or {})}
    PRINT.mkdir(parents=True, exist_ok=True)
    JIGS.mkdir(parents=True, exist_ok=True)
    out = {"printed": {}, "jigs": {}}
    for name, (fn, n, _mir) in PARTS.items():
        m = fn(cfg)
        tm = to_trimesh(m)
        p = PRINT / f"{name}_R.stl" if _mir else PRINT / f"{name}.stl"
        tm.export(p)
        if _mir:
            tl = tm.copy()
            tl.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
            tl.invert()
            tl.export(PRINT / f"{name}_L.stl")
        vol = float(abs(tm.volume))
        out["printed"][name] = {"file": str(p.relative_to(BQ.REPO)), "count": n, "volume_mm3": round(vol, 1),
                                "mass_g_each": round(vol * BQ.RHO_PAHT, 1), "watertight": bool(tm.is_watertight),
                                "bbox_mm": np.round(tm.extents, 1).tolist()}
        log(f"  {name}: {vol * BQ.RHO_PAHT:.1f} g x {n}, watertight {tm.is_watertight}")
    for name, m in jig_set(cfg).items():
        tm = to_trimesh(m)
        p = JIGS / f"{name}.stl"
        tm.export(p)
        out["jigs"][name] = {"file": str(p.relative_to(BQ.REPO)), "volume_mm3": round(float(abs(tm.volume)), 1),
                             "pla_g": round(float(abs(tm.volume)) * 1.24e-3, 1), "watertight": bool(tm.is_watertight)}
    return out


# ============================================================================ cut list, mass, cost
KERF = 3.0          # tubing cutter / hacksaw kerf + facing per cut (mm)


def cut_list(cfg) -> list[dict]:
    half = 115 - 12.7 - 1.0
    st, ct, ub, mb = cfg["stay"], cfg["ctube"], cfg["ubar"], cfg["bar"]
    rows = [
        {"part": "stay", "stock": st, "qty": 2, "length_mm": 530.0, "holes": "z 60 along x (hinge pin, 5.2 then 5.3); "
         f"z {cfg['stay_bolt_z'][0]:g} / {cfg['stay_bolt_z'][1]:g} along y (gusset bolts); no hole above z 160",
         "jig": "jig_stay_foot (stop on the foot end)"},
        {"part": "lumbar cross tube", "stock": ct, "qty": 1, "length_mm": round(2 * half, 1),
         "holes": f"along y at x +/-{cfg['ct_bolt_x'][0]:g}, +/-{cfg['ct_bolt_x'][1]:g} (gussets), "
                  + ", ".join(f"+/-{k:g}" for k in cfg["key_x"]) + " (hip key bolts); printed saddle plug in each end",
         "jig": "jig_cross_tube_half (stop on each end in turn)"},
        {"part": "upper bar", "stock": ub, "qty": 1, "length_mm": round(2 * half, 1),
         "holes": "along y at x +/-15 (pawl housing), +/-80 (tee bar bolts)", "jig": "jig_upper_bar_half"},
        {"part": "mid bar", "stock": mb, "qty": 1, "length_mm": round(2 * half, 1), "holes": "along y at x +/-80",
         "jig": "jig_upper_bar_half (3/4 in insert: print the 19.05 variant or shim)"},
        {"part": "key-bolt spacer", "stock": "t750_035", "qty": 2 * len(cfg["key_x"]), "length_mm": 31.0, "holes": "none (M5 passes inside)",
         "jig": "-"},
        {"part": "hip bracket angle (front / back)", "stock": "angle_15", "qty": 2, "length_mm": cfg["bracket_len"],
         "holes": f"front: 6 mount + {2 * len(cfg['key_x'])} key + D10.5 pin; back: {2 * len(cfg['key_x'])} key; webs: 2 lap",
         "jig": "jig_angle_template"},
        {"part": "foot plate (one leg sawn off a 38.1 mm angle piece)", "stock": "angle_15", "qty": 2, "length_mm": 38.1,
         "holes": "none", "jig": "-"},
        {"part": "tee backer", "stock": "flat_1x18", "qty": 8, "length_mm": 70.0,
         "holes": "3 x D5.3 at x 80, 115 +/- 16.2 (from the tee half)", "jig": "tee half as template"},
        {"part": "lumbar L-gusset", "stock": "sheet_090", "qty": 4, "length_mm": None,
         "holes": "4 x D5.3", "jig": "jig_gusset_template"},
    ]
    return rows


def _buy_tube(key, pieces):
    table = BQ.PRICE.get(key)
    import itertools
    best = None
    for n in (1, 2):
        for combo in itertools.combinations_with_replacement(sorted(table), n):
            free = sorted([l * BQ.IN for l in combo], reverse=True)
            ok = True
            for pc in sorted(pieces, reverse=True):
                for i, f in enumerate(free):
                    if f >= pc + KERF:
                        free[i] -= pc + KERF
                        break
                else:
                    ok = False
                    break
            if ok:
                usd = sum(table[l] for l in combo)
                if best is None or usd < best[0]:
                    best = (usd, " + ".join(f"{l} in" for l in combo))
    return best


def gusset_area(cfg):
    w = cfg["gusset_w"]
    z1, z2 = cfg["stay_bolt_z"]
    xb = min(cfg["ct_bolt_x"])
    return w * ((z2 + 10) - (z1 - 15)) + (115 - w / 2 - (xb - 12)) * w


def bolt_g(d, L):
    return B80_bolt(d, L)


def B80_bolt(d, L):
    from huntkit.gendesign.bl080_metal_frame import _bolt_g
    return _bolt_g(d, L)


BOLTS = [   # (count, d, L, where)
    (8, 5, 40, "lumbar gusset through-bolts"),
    (4, 5, 70, "hip key bolts (through the spacer and cross tube)"),
    (2, 5, 12, "bracket web lap"),
    (12, 5, 45, "tee clamp + bar bolts (4 tees x 3)"),
    (2, 5, 40, "pawl housing through the upper bar"),
]
HIP_FIX = (6, 5, 16, "Ti mount to the front angle (6 of 8 positions)")


def mass_table(cfg, printed: dict) -> dict:
    rows = {}
    for r in cut_list(cfg):
        k = r["stock"]
        if k in BQ.STOCK:
            rows[f"{r['part']} x {r['qty']} ({BQ.STOCK[k]['desc']}, {r['length_mm']} mm)"] = \
                r["qty"] * r["length_mm"] * BQ.area(k) * BQ.RHO_AL
    a15 = (2 * BQ.ANGLE_15["leg"] - BQ.ANGLE_15["t"]) * BQ.ANGLE_15["t"]
    rows["hip bracket angles x 2 (1-1/2 x 1/8, 80 mm), 15 % trimmed (ASSUMPTION TRIM)"] = \
        2 * cfg["bracket_len"] * a15 * BQ.RHO_AL * 0.85
    rows["foot plates x 2 (38.1 x 38.1 x 1/8)"] = 2 * 38.1 ** 2 * BQ.ANGLE_15["t"] * BQ.RHO_AL
    rows["tee backers x 8 (1 x 1/8 x 70)"] = 8 * 70.0 * BQ.IN * 0.125 * BQ.IN * BQ.RHO_AL
    rows[f"lumbar L-gussets x 4 (.090 6061)"] = 4 * gusset_area(cfg) * cfg["gusset_t"] * BQ.RHO_AL
    for name, v in printed.items():
        rows[f"printed: {name} x {v['count']}"] = v["count"] * v["mass_g_each"]
    for k, v in CARRIED_PRINTED_G.items():
        rows[f"printed: {k}"] = v
    rows["crown bushing growth (BL-080 booking, bore 22.9)"] = 41.3
    rows["M5 A2 screws + nuts (joints)"] = sum(n * B80_bolt(d, L) for n, d, L, _ in BOLTS)
    rows["TPU foot pads x 2 (6 mm, ASSUMPTION PAD)"] = 2 * 38.1 ** 2 * 6.0 * 1.2e-3
    body = sum(rows.values())
    printed_g = sum(v for k, v in rows.items() if k.startswith("printed"))
    hip = HIP_FIX[0] * B80_bolt(HIP_FIX[1], HIP_FIX[2])
    from huntkit.gendesign.bl080_metal_frame import H1, H1C
    return {"rows": {k: round(float(v), 1) for k, v in rows.items()}, "body_g": round(body, 1),
            "printed_g": round(printed_g, 1), "hip_hw_g": round(hip, 1),
            "vs_bl080_b_g": round(body - 1013.3, 1),
            "frame_delta_vs_h1_g": round(body + hip - H1["body_g"] - H1["hip_hw_g"], 1),
            "frame_delta_vs_h1c_g": round(body + hip - H1C["body_g"] - H1C["hip_hw_g"], 1)}


def cost_table(cfg, mass: dict) -> dict:
    lines = []
    pieces = {}
    for r in cut_list(cfg):
        if r["stock"] in BQ.PRICE:
            pieces.setdefault(r["stock"], []).extend([r["length_mm"]] * r["qty"])
    for k, pcs in pieces.items():
        usd, how = _buy_tube(k, pcs)
        lines.append((f"{BQ.STOCK[k]['desc']}: {', '.join(f'{p:g}' for p in pcs)} mm, buy {how}", usd, BQ.STOCK[k]["src"]))
    lines.append((BQ.SHEET_090["desc"] + " (4 L-gussets)", BQ.SHEET_090["usd"], BQ.SHEET_090["src"]))
    lines.append((BQ.ANGLE_15["desc"] + " (2 bracket angles 80 + 2 foot plates 38)", BQ.ANGLE_15["usd"], BQ.ANGLE_15["src"]))
    lines.append(("6061 1 x 1/8 flat, 2 x 18 in (8 tee backers x 70)", 2 * BQ.FLAT_1x18["usd"], BQ.FLAT_1x18["src"]))
    pr = mass["printed_g"] * 1.10 * 0.08
    lines.append((f"PAHT-CF filament {mass['printed_g']:.0f} g x 1.10 support", pr, "record USD 80/kg; BL-053 support x1.10"))
    nb = sum(n for n, *_ in BOLTS) + HIP_FIX[0]
    lines.append((f"A2 M5 screws + nuts ({nb})", nb * (0.84 + 0.10), "Zoro A2 M5 x 35 50-pk USD 41.79 + nut (BL-077 lines)"))
    lines.append(("threadlocker share", 0.90, "BL-077 LOC-SHARE"))
    lines.append(("shipping (metal order), ASSUMPTION SHIP", 12.0, "BL-080 ASSUMPTION SHIP"))
    tot = sum(v for _, v, _ in lines)
    return {"lines": [{"item": a, "usd": round(float(b), 2), "source": s} for a, b, s in lines],
            "per_frame_usd": round(tot, 2), "within_cap": bool(tot <= 150.0)}


def proving(cfg, jigs: dict) -> dict:
    pla = sum(v["pla_g"] for v in jigs.values())
    lines = [
        ("1 x .049 6061 tube 24 in: CL-1, BB-1, OV-1 coupons and the fit-up trial", 21.60, "Speedy p-4586 24 in"),
        ("PAHT for coupon tees / cups (CL-1, CF-1), 120 g", 120 * 0.08 * 1.1, "record"),
        (f"PLA for the jigs ({pla:.0f} g) at USD 20/kg", pla * 0.02, "ASSUMPTION PLA-PRICE"),
        ("tubing cutter to 1-1/8 in (new tool)", 15.0, "BL-080 ASSUMPTION TOOL-PRICE"),
        ("deburr tool + 5.2 / 5.3 mm cobalt bits (new tools)", 14.0, "BL-080 ASSUMPTION TOOL-PRICE"),
        ("spare M5 A2 screws for the coupons (10)", 9.4, "Zoro A2 M5 (BL-077)"),
    ]
    return {"lines": [{"item": a, "usd": round(b, 2), "source": s} for a, b, s in lines],
            "total_usd": round(sum(b for _, b, _ in lines), 2),
            "note": "the BL-079 PAHT coupons (USD 59.01) are already booked and qualify the printed parts' Z basis"}
