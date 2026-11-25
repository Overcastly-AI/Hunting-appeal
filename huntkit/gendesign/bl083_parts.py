"""BL-083 parts for concept D83 and the B81 lever row: the hip-pan flat patterns (DXF with bend lines, SendCutSend),
the pan / spine solids (STL, for renders and fit), the printed parts carried from BL-081 (re-exported for D), the D
stay drill jig, the cut list, mass and cost bills.

Flat pattern (``flat_tray`` / ``flat_spine``): outside-mould-line (OML) dimensions from the frame geometry, flat
lengths by the bend-allowance rule BA = pi / 2 (r + K t), segment flat length = OML length - (r + t) per bent end.
ASSUMPTION SCS-RADIUS: inside radius r = 1 t (SendCutSend 5052 page: "as low as 1x material thickness in many cases"),
K 0.42 (a typical air-bend value; SendCutSend fixes r and K per thickness, so the DXF is re-checked in their bending
calculator at order). Layers: CUT (outline + holes), BEND (bend centre lines, dashed), NOTE (labels).
"""
from __future__ import annotations

import math

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_parts as BP
from huntkit.gendesign import bl083_concept_d as D

PRINT = D.OUTDIR / "print"
JIGS = D.OUTDIR / "jigs"
CUT = D.OUTDIR / "cut"
K_FACTOR = 0.42
HOLE = BQ.HOLE_D
PIN_BORE = 10.5
SPINE_SCREW_Z = (62.0, 178.0)          # spine-to-face screws near the flanges (>= 1/2 die width from the bends)
SPINE_SCREW_X = (-8.0, 8.0)


def bend(t):
    r = t
    ba = math.pi / 2 * (r + K_FACTOR * t)
    return {"r": r, "ba": ba, "setback": r + t, "bd": 2 * (r + t) - ba}


# ============================================================================ tray geometry (OML, frame axes)
def tray_dims(cfg) -> dict:
    g = D.geom(cfg)
    t = g["t"]
    W = 2 * (g["x_w"] + t / 2)                         # outside of the walls = the stays' inboard faces
    z0, z1 = cfg["face_z"]
    y_front = g["y_seat"]                              # face body-side surface
    y_stay = g["yline"](120.0)
    D_full = (y_stay + cfg["wall_aft"]) - y_front      # wall depth beside the stay (z 78-170)
    D_front = (y_stay - BQ.STOCK[cfg["stay"]]["od"] / 2 - 2.0) - y_front   # front part, clear of the stay / IM1 loop
    return {"t": t, "W": W, "H": z1 - z0, "z0": z0, "z1": z1, "D_full": D_full, "D_front": D_front,
            "wz": cfg["wall_z"], "ft": cfg["flange_top"], "fb": cfg["flange_bot"], "y_front": y_front}


def flat_tray(cfg) -> dict:
    """Flat pattern of the tray: polylines (closed) and holes (x, y, d) in a 2D frame u (across, = frame x) / v (up,
    = frame z, v 0 at the face bottom OML), bend lines as segments."""
    d = tray_dims(cfg)
    t, b = d["t"], bend(d["t"])
    sb, ba = b["setback"], b["ba"]
    fw = d["W"] - 2 * sb                     # face flat width
    fh = d["H"] - 2 * sb                     # face flat height (flanges top and bottom)
    wl_full = d["D_full"] - sb               # wall flat lengths outward from its bend
    wl_front = d["D_front"] - sb
    ft, fb = d["ft"] - sb, d["fb"] - sb
    # face from u -fw/2..fw/2, v 0..fh (v measured from the bottom bend line's tangent)
    u1 = fw / 2
    xb = u1 + ba                              # wall flat starts here
    # wall: full depth over z wall_z[0]..170 (beside the stay), front depth elsewhere (z 50 .. 190)
    zf = lambda z: z - d["z0"] - sb           # noqa: E731  frame z -> v
    v_lo, v_hi = 0.0, fh
    vs0, vs1 = zf(d["wz"][0]), zf(D.WALL_STAY_TOP)
    wall_R = [(xb, v_lo), (xb + wl_front, v_lo), (xb + wl_front, vs0), (xb + wl_full, vs0), (xb + wl_full, vs1),
              (xb + wl_front, vs1), (xb + wl_front, v_hi), (xb, v_hi)]
    # outline: bottom flange, right wall, top flange, left wall (corner reliefs = the bend-zone squares left open)
    rel = 1.0                                 # relief beyond the bend zone (mm)
    pts = [(-u1, -ba - fb), (u1, -ba - fb), (u1, -rel), (u1 + ba + rel, -rel)]
    pts += [(x, y) for x, y in wall_R]
    pts += [(u1 + ba + rel, fh + rel), (u1, fh + rel), (u1, fh + ba + ft), (-u1, fh + ba + ft), (-u1, fh + rel),
            (-u1 - ba - rel, fh + rel)]
    pts += [(-x, y) for x, y in reversed(wall_R)]
    pts += [(-u1 - ba - rel, -rel), (-u1, -rel)]
    # holes: Ti mount (8 x D5.8 = hip_mount.HOLE_D) + pin bore at (0, z 120); wall bolts at z 85 / 155 on the stay axis
    from huntkit.gendesign import hip_mount as HMNT
    holes = [(x, zf(z), HMNT.HOLE_D) for x, z in HMNT.pattern()["positions_xz"]]
    holes.append((0.0, zf(120.0), PIN_BORE))
    y_axis = D.geom(cfg)["yline"]
    for z in cfg["pan_bolt_z"]:
        s = (y_axis(z) - d["y_front"]) - sb        # along the wall from its bend line
        for sx in (-1, 1):
            holes.append((sx * (xb + s), zf(z), HOLE))
    # spine end screws through the face near the flanges
    for z in SPINE_SCREW_Z:
        for x in SPINE_SCREW_X:
            holes.append((x, zf(z), HOLE))
    bends = [((-u1, 0.0 - ba / 2), (u1, -ba / 2), "bottom flange 90 deg up (aft)"),
             ((-u1, fh + ba / 2), (u1, fh + ba / 2), "top flange 90 deg up (aft)"),
             ((u1 + ba / 2, 0.0), (u1 + ba / 2, fh), "right wall 90 deg up (aft)"),
             ((-u1 - ba / 2, 0.0), (-u1 - ba / 2, fh), "left wall 90 deg up (aft)")]
    # cut features >= 1/2 die width from each bend centre line (SCS bending page): nearest hole to a bend
    minclr = min(_hole_to_bend(h, bends) for h in holes)
    xs, ys = zip(*pts)
    return {"outline": pts, "holes": holes, "bends": bends, "bbox": (max(xs) - min(xs), max(ys) - min(ys)),
            "area_mm2": _poly_area(pts) - sum(math.pi * h[2] ** 2 / 4 for h in holes), "dims": d, "bend": b,
            "hole_to_bend_min_mm": round(minclr, 1), "n_bends": 4}


def flat_spine(cfg) -> dict:
    """Spine channel: web w (OML) x height between the flanges, two legs (2 bends)."""
    t = D.SHEET_T[cfg["spine_t"]]
    b = bend(t)
    sb, ba = b["setback"], b["ba"]
    d = tray_dims(cfg)
    h = d["H"] - 2 * d["t"] - 1.0                 # between the flanges' inner faces, 0.5 clearance each end
    w = cfg["spine_w"] - 2 * sb
    leg = cfg["spine_leg"] - sb
    u1 = w / 2
    pts = [(-u1 - ba - leg, 0.0), (u1 + ba + leg, 0.0), (u1 + ba + leg, h), (-u1 - ba - leg, h)]
    from huntkit.gendesign import hip_mount as HMNT
    z_base = d["z0"] + d["t"] + 0.5
    holes = [(x, z - z_base, HMNT.HOLE_D) for x, z in HMNT.pattern()["positions_xz"]]
    holes.append((0.0, 120.0 - z_base, PIN_BORE))
    for z in SPINE_SCREW_Z:
        for x in SPINE_SCREW_X:
            holes.append((x, z - z_base, HOLE))
    bends = [((u1 + ba / 2, 0.0), (u1 + ba / 2, h), "leg 90 deg (aft)"), ((-u1 - ba / 2, 0.0), (-u1 - ba / 2, h), "leg 90 deg (aft)")]
    return {"outline": pts, "holes": holes, "bends": bends, "bbox": (2 * (u1 + ba + leg), h),
            "hole_to_bend_min_mm": round(min(_hole_to_bend(q, bends) for q in holes), 1),
            "area_mm2": _poly_area(pts) - sum(math.pi * q[2] ** 2 / 4 for q in holes), "n_bends": 2, "t": t}


def _hole_to_bend(h, bends) -> float:
    """Clear distance from a hole edge to the nearest bend centre line (vertical or horizontal bend lines)."""
    hx, hy, hd = h
    ds = []
    for (a, b, _) in bends:
        if abs(a[0] - b[0]) < 1e-9:
            ds.append(abs(hx - a[0]))
        else:
            ds.append(abs(hy - a[1]))
    return min(ds) - hd / 2


def _poly_area(pts):
    x, y = np.array(pts).T
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def write_dxf(fp: dict, path, title: str) -> str:
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, col in (("CUT", 7), ("BEND", 1), ("NOTE", 3)):
        doc.layers.add(name, color=col)
    doc.layers.get("BEND").dxf.linetype = "DASHED"
    msp = doc.modelspace()
    msp.add_lwpolyline(fp["outline"], close=True, dxfattribs={"layer": "CUT"})
    for x, y, d in fp["holes"]:
        msp.add_circle((x, y), d / 2, dxfattribs={"layer": "CUT"})
    for a, b, lab in fp["bends"]:
        msp.add_line(a, b, dxfattribs={"layer": "BEND", "linetype": "DASHED"})
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        msp.add_text(lab, height=3.0, dxfattribs={"layer": "NOTE"}).set_placement((mx + 2, my + 2))
    xs, ys = zip(*fp["outline"])
    msp.add_text(title, height=4.0, dxfattribs={"layer": "NOTE"}).set_placement((min(xs), min(ys) - 10))
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(path)
    try:
        return str(path.relative_to(BQ.REPO))
    except ValueError:
        return str(path)


# ============================================================================ 3D solids (STL)
def tray_solid(cfg):
    """Formed tray as a solid (frame axes, mm): face + walls + flanges (sharp corners; the bend radii are cosmetic)."""
    d = tray_dims(cfg)
    t = d["t"]
    yf = d["y_front"]
    xw = d["W"] / 2
    z0, z1 = d["z0"], d["z1"]
    box = BP.box
    face = box(-xw, xw, yf, yf + t, z0, z1)
    fb = box(-xw, xw, yf, yf + d["fb"], z0, z0 + t)
    ft = box(-xw, xw, yf, yf + d["ft"], z1 - t, z1)
    parts = face + fb + ft
    for sx in (-1, 1):
        xa, xb_ = (xw - t, xw) if sx > 0 else (-xw, -xw + t)
        parts = parts + box(xa, xb_, yf, yf + d["D_front"], z0, z1)
        parts = parts + box(xa, xb_, yf, yf + d["D_full"], d["wz"][0], D.WALL_STAY_TOP)
    from huntkit.gendesign import hip_mount as HMNT
    for x, z in HMNT.pattern()["positions_xz"]:
        parts = parts - BP.cyl("y", (x, z), HMNT.HOLE_D / 2, yf - 1, yf + t + 1)
    parts = parts - BP.cyl("y", (0.0, 120.0), PIN_BORE / 2, yf - 1, yf + t + 1)
    yl = D.geom(cfg)["yline"]
    for z in cfg["pan_bolt_z"]:
        parts = parts - BP.cyl("x", (yl(z), z), HOLE / 2, -xw - 1, xw + 1)
    return parts


def spine_solid(cfg):
    d = tray_dims(cfg)
    t = D.SHEET_T[cfg["spine_t"]]
    yb = d["y_front"] + d["t"]
    w, f = cfg["spine_w"] / 2, cfg["spine_leg"]
    z0, z1 = d["z0"] + d["t"] + 0.5, d["z1"] - d["t"] - 0.5
    s = BP.box(-w, w, yb, yb + t, z0, z1) + BP.box(-w, -w + t, yb, yb + f, z0, z1) + BP.box(w - t, w, yb, yb + f, z0, z1)
    return s


def strut_solid(cfg):
    d = tray_dims(cfg)
    yl = D.geom(cfg)["yline"]
    sp = BQ.STOCK["t750_035"]
    out = None
    for z in cfg["strut_z"]:
        L = d["W"] / 2 - d["t"]
        s = BP.cyl("x", (yl(z), z), sp["od"] / 2, -L, L) - BP.cyl("x", (yl(z), z), sp["od"] / 2 - sp["t"], -L - 1, L + 1)
        out = s if out is None else out + s
    return out


def stay_jig(cfg):
    """V-cradle drill jig for the D stay (foot end stop): z 60 hinge pin and z 85 / 155 pan bolts, all along x (the
    jig's vertical axis: drill down)."""
    st = BQ.STOCK[cfg["stay"]]
    return BP.tube_jig(st["od"], 170.0, [(60.0, "z")] + [(z, "z") for z in cfg["pan_bolt_z"]])


def export(cfg, log=print) -> dict:
    """Printed parts (B81 builders re-used, minus the saddle plugs), D jigs, tray / spine STL and DXF."""
    PRINT.mkdir(parents=True, exist_ok=True)
    JIGS.mkdir(parents=True, exist_ok=True)
    CUT.mkdir(parents=True, exist_ok=True)
    out = {"printed": {}, "jigs": {}, "metal_stl": {}, "dxf": {}}
    parts = {k: v for k, v in BP.PARTS.items() if k != "rung_saddle_plug"}
    for name, (fn, n, mir) in parts.items():
        tm = BP.to_trimesh(fn(cfg))
        p = PRINT / f"{name}_R.stl"
        tm.export(p)
        tl = tm.copy()
        tl.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
        tl.invert()
        tl.export(PRINT / f"{name}_L.stl")
        vol = float(abs(tm.volume))
        out["printed"][name] = {"file": str(p.relative_to(BQ.REPO)), "count": n, "volume_mm3": round(vol, 1),
                                "mass_g_each": round(vol * BQ.RHO_PAHT, 1), "watertight": bool(tm.is_watertight)}
    jigs = {"jig_stay_d83": stay_jig(cfg), "jig_upper_bar_half": BP.jig_set(cfg)["jig_upper_bar_half"]}
    for name, m in jigs.items():
        tm = BP.to_trimesh(m)
        p = JIGS / f"{name}.stl"
        tm.export(p)
        out["jigs"][name] = {"file": str(p.relative_to(BQ.REPO)), "pla_g": round(float(abs(tm.volume)) * 1.24e-3, 1),
                             "watertight": bool(tm.is_watertight)}
    for name, fn in (("hip_pan_tray", tray_solid), ("hip_pan_spine", spine_solid), ("lumbar_strut", strut_solid)):
        tm = BP.to_trimesh(fn(cfg))
        p = CUT / f"{name}.stl"
        tm.export(p)
        out["metal_stl"][name] = {"file": str(p.relative_to(BQ.REPO)), "watertight": bool(tm.is_watertight),
                                  "volume_mm3": round(float(abs(tm.volume)), 1)}
    ft, fs = flat_tray(cfg), flat_spine(cfg)
    out["dxf"]["hip_pan_tray"] = write_dxf(ft, CUT / "hip_pan_tray_5052_flat.dxf",
                                           f"D83 hip pan tray, 5052-H32 {cfg['pan_t']} in, 4 bends 90 deg (r = t ASSUMPTION), qty 1 per frame")
    out["dxf"]["hip_pan_spine"] = write_dxf(fs, CUT / "hip_pan_spine_5052_flat.dxf",
                                            f"D83 mount spine, 5052-H32 {cfg['spine_t']} in, 2 bends 90 deg, qty 1 per frame")
    log(f"  tray flat {ft['bbox'][0]:.0f} x {ft['bbox'][1]:.0f} mm, spine {fs['bbox'][0]:.0f} x {fs['bbox'][1]:.0f}")
    return out


# ============================================================================ cut list, mass, cost
def cut_list(cfg) -> list[dict]:
    half = 115 - 12.7 - 1.0
    dd = tray_dims(cfg)
    strut_L = round(dd["W"] - 2 * dd["t"], 1)
    rows = [
        {"part": "stay", "stock": cfg["stay"], "qty": 2, "length_mm": 530.0,
         "holes": f"z 60 / {cfg['pan_bolt_z'][0]:g} / {cfg['pan_bolt_z'][1]:g} all along x (lateral: on the neutral axis of "
                  "fore-aft bending), crush sleeves at the pan rows; no hole above z 160", "jig": "jig_stay_d83"},
        {"part": "upper bar", "stock": cfg["ubar"], "qty": 1, "length_mm": round(2 * half, 1),
         "holes": "along y at x +/-15 (pawl housing, crush sleeves), 12 mm from each end (bar-socket bolt)", "jig": "jig_upper_bar_half"},
        {"part": "mid bar", "stock": cfg["bar"], "qty": 1, "length_mm": round(2 * half, 1),
         "holes": "along y 12 mm from each end (bar-socket bolt)", "jig": "jig_upper_bar_half (shim to 3/4 in)"},
        {"part": f"lumbar strut (spacer between the pan walls on the z {cfg['strut_z'][0]:g} M5 rod)", "stock": "t750_035",
         "qty": len(cfg["strut_z"]), "length_mm": strut_L, "holes": "none (rod inside), ends faced square", "jig": "-"},
        {"part": "crush sleeve (cut to the stay bore)", "stock": "sleeve_5_16", "qty": 4 + 2,
         "length_mm": round(BQ.STOCK[cfg["stay"]]["od"] - 2 * BQ.STOCK[cfg["stay"]]["t"], 1), "holes": "-", "jig": "-"},
        {"part": "hip pan tray (SendCutSend, formed)", "stock": f"5052-H32 {cfg['pan_t']}", "qty": 1, "length_mm": None,
         "holes": "8 x D5.8 mount + D10.5 pin + 4 x D5.3 wall bolts + 4 x D5.3 spine screws (all in the DXF)",
         "jig": "none (laser cut)"},
        {"part": "mount spine channel (SendCutSend, formed)", "stock": f"5052-H32 {cfg['spine_t']}", "qty": 1, "length_mm": None,
         "holes": "8 x D5.8 + D10.5 + 4 x D5.3 (match the tray)", "jig": "none (laser cut)"},
        {"part": "foot plate (one leg sawn off a 38.1 mm angle piece)", "stock": "angle_15", "qty": 2, "length_mm": 38.1,
         "holes": "none", "jig": "-"},
    ]
    if cfg.get("tees") == "bands":
        rows.append({"part": "clamp half-shell (50 mm ring sawn in half), 2 hose bands each tee", "stock": cfg["shell"],
                     "qty": 4, "length_mm": cfg["clamp_len"], "holes": "none", "jig": "printed saw guide (V-block)"})
    else:
        rows += [{"part": "clamp half-shell (50 mm ring sawn in half along the axis, 1.5 mm kerf)", "stock": cfg["shell"],
                  "qty": 4, "length_mm": cfg["clamp_len"], "holes": "none", "jig": "printed saw guide (V-block)"},
                 {"part": "tee backer (1 x 1/4 flat)", "stock": "flat_1x14", "qty": 8, "length_mm": cfg["backer_len"],
                  "holes": "2 x D5.3 at 37.8 mm", "jig": "bar socket as template"}]
    return rows


def bolts(cfg) -> list[tuple]:
    out = [(2 * (2 - len(cfg["strut_z"])), 5, 40, "pan wall bolts through the stays (lateral, crush sleeves)"),
           (4, 5, 12, "spine to the face near the flanges"),
           (4, 5, 40, "bar-socket bolts (bar end)"),
           (2, 5, 40, "pawl housing through the upper bar, crush sleeves")]
    if cfg.get("tees") != "bands":
        out.append((8, 5, 45, "tee clamp bolts (4 tees x 2, beside the stay)"))
    return out


ROD_G_PER_MM = 7.93e-3 * math.pi / 4 * 4.48 ** 2     # M5 A2 threaded rod, pitch-diameter area (ISO 724 d2 4.48)
HIP_FIX = (8, 5, 16, "Ti mount to the pan face + spine (all 8 BL-055 positions)")


def mass_table(cfg, printed: dict) -> dict:
    rows = {}
    st = BQ.STOCK
    for r in cut_list(cfg):
        k = r["stock"]
        if k in st and k != cfg["shell"] and r["length_mm"]:
            rows[f"{r['part']} x {r['qty']} ({st[k]['desc']}, {r['length_mm']} mm)"] = r["qty"] * r["length_mm"] * BQ.area(k) * BQ.RHO_AL
    ft, fs = flat_tray(cfg), flat_spine(cfg)
    P = D.pan_material(cfg)
    rows[f"hip pan tray (5052-H32 {cfg['pan_t']}, flat {ft['area_mm2'] / 1e3:.1f} cm2 x 10)"] = ft["area_mm2"] * ft["dims"]["t"] * P["rho"]
    rows[f"mount spine channel (5052-H32 {cfg['spine_t']})"] = fs["area_mm2"] * fs["t"] * P["rho"]
    rows["foot plates x 2 (38.1 x 38.1 x 1/8)"] = 2 * 38.1 ** 2 * BQ.ANGLE_15["t"] * BQ.RHO_AL
    sw = BQ.STOCK[cfg["shell"]]
    rows[f"clamp half-shells, 4 tees (1-1/4 x .125, {cfg['clamp_len']:g} mm less kerf)"] = \
        4 * cfg["clamp_len"] * BQ.area(cfg["shell"]) * BQ.RHO_AL * (1 - 2 * 1.5 / (math.pi * (sw["od"] - sw["t"])))
    if cfg.get("tees") == "bands":
        rows["hose bands x 8 (9 mm W4, ASSUMPTION BAND 12 g)"] = 8 * D.BAND["mass_g"]
    else:
        rows[f"tee backers x 8 (1 x 1/4 x {cfg['backer_len']:g})"] = 8 * cfg["backer_len"] * BQ.IN * cfg["backer_t"] * BQ.RHO_AL
    stay = BQ.STOCK[cfg["stay"]]
    rows["crush sleeves x 6 (5/16 x .035 6061)"] = 6 * (stay["od"] - 2 * stay["t"]) * math.pi / 4 * (7.94 ** 2 - 6.16 ** 2) * BQ.RHO_AL
    for name, v in printed.items():
        rows[f"printed: {name} x {v['count']}"] = v["count"] * v["mass_g_each"]
    for k, v in BP.CARRIED_PRINTED_G.items():
        rows[f"printed: {k}"] = v
    bore = stay["od"] - 2 * stay["t"]
    rows[f"crown bushing growth (4 x 70 mm UHMWPE, bore 18 -> {bore:.1f})"] = \
        4 * 70.0 * math.pi / 4 * ((bore ** 2 - 16.0 ** 2) - (18.0 ** 2 - 16.0 ** 2)) * 0.935e-3
    L_rod = tray_dims(cfg)["W"] + 2 * stay["od"] + 16.0
    rows[f"M5 A2 threaded rod x {len(cfg['strut_z'])} ({L_rod:.0f} mm) + 2 nuts + 2 washers"] = \
        len(cfg["strut_z"]) * (L_rod * ROD_G_PER_MM + 2 * 1.2 + 2 * 1.0)
    rows["M5 A2 screws + nuts (joints)"] = sum(n * BP.B80_bolt(d, L) for n, d, L, _ in bolts(cfg))
    rows["TPU foot pads x 2 (6 mm, ASSUMPTION PAD)"] = 2 * 38.1 ** 2 * 6.0 * 1.2e-3
    body = sum(rows.values())
    from huntkit.gendesign.bl080_metal_frame import H1, H1C
    hip = HIP_FIX[0] * BP.B80_bolt(HIP_FIX[1], HIP_FIX[2])
    pan_keys = [k for k in rows if k.startswith(("hip pan", "mount spine", "lumbar strut", "M5 A2 threaded"))]
    return {"rows": {k: round(float(v), 1) for k, v in rows.items()}, "body_g": round(body, 1),
            "printed_g": round(sum(v for k, v in rows.items() if k.startswith("printed")), 1),
            "lumbar_g": round(sum(rows[k] for k in pan_keys), 1), "hip_hw_g": round(hip, 1),
            "vs_h1c_g": round(body - H1C["body_g"], 1), "vs_h1_g": round(body - H1["body_g"], 1)}


def cost_table(cfg, mass: dict, local_metal: bool = False) -> dict:
    lines = []
    pieces = {}
    for r in cut_list(cfg):
        if r["stock"] in BQ.PRICE and r["stock"] != cfg["shell"] and r["length_mm"]:
            pieces.setdefault(r["stock"], []).extend([r["length_mm"]] * r["qty"])
    for k, pcs in pieces.items():
        usd, how = BP._buy_tube(k, pcs)
        lines.append((f"{BQ.STOCK[k]['desc']}: {', '.join(f'{p:g}' for p in pcs)} mm, buy {how}", usd, BQ.STOCK[k]["src"]))
    ft, fs = flat_tray(cfg), flat_spine(cfg)
    a_t = ft["bbox"][0] * ft["bbox"][1] / 645.16
    a_s = fs["bbox"][0] * fs["bbox"][1] / 645.16
    p_t = D.scs_price(a_t, len(ft["holes"]), ft["n_bends"])
    p_s = D.scs_price(a_s, len(fs["holes"]), fs["n_bends"])
    lines.append((f"SendCutSend hip pan tray 5052 {cfg['pan_t']}, {a_t:.0f} in2 bbox, {len(ft['holes'])} holes, 4 bends", p_t,
                  "ASSUMPTION SCS-PRICE (method: bl083_concept_d.scs_price on the cited example, " + D.SCS["pricing"] + ")"))
    lines.append((f"SendCutSend mount spine 5052 {cfg['spine_t']}, {a_s:.0f} in2 bbox, 2 bends", p_s, "ASSUMPTION SCS-PRICE"))
    lines.append(("SendCutSend shipping", 0.0 if p_t + p_s >= D.SCS["free_ship_usd"] else 8.0,
                  "free US shipping on orders >= USD 39 (SCS pricing page)"))
    lines.append((BQ.ANGLE_15["desc"] + " (2 foot plates 38)", BQ.ANGLE_15["usd"], BQ.ANGLE_15["src"]))
    if cfg.get("tees") == "bands":
        lines.append(("hose bands 9 mm W4 x 8", 8 * D.BAND["usd"], "ASSUMPTION BAND (price not read)"))
    else:
        lines.append(("6061 1 x 1/4 flat, 18 in (8 tee backers x 55)", 6.00, "ASSUMPTION FLAT14-PRICE (BL-081)"))
    lines.append((BQ.STOCK[cfg["shell"]]["desc"] + ", 12 in (4 tees of half-shells)", BQ.STOCK[cfg["shell"]]["usd"],
                  BQ.STOCK[cfg["shell"]]["src"]))
    lines.append(("5/16 x .035 tube for 6 crush sleeves", 3.00, BQ.CRUSH_SLEEVE["src"]))
    pr = mass["printed_g"] * 1.10 * 0.08
    lines.append((f"PAHT-CF filament {mass['printed_g']:.0f} g x 1.10 support", pr, "record USD 80/kg; BL-053 support x1.10"))
    nb = sum(n for n, *_ in bolts(cfg)) + HIP_FIX[0]
    lines.append((f"A2 M5 screws + nuts ({nb})", nb * (0.84 + 0.10), "Zoro A2 M5 x 35 50-pk USD 41.79 + nut (BL-077 lines)"))
    lines.append((f"M5 A2 threaded rod 1 m (share) + 2 nuts per strut x {len(cfg['strut_z'])}", 3.0 * len(cfg["strut_z"]),
                  "ASSUMPTION ROD-PRICE (shop-class, not read)"))
    lines.append(("threadlocker share", 0.90, "BL-077 LOC-SHARE"))
    ship = 0.0 if local_metal else BQ.tube_props()["ship_base"]
    lines.append(("metal shipping (Speedy order)" if not local_metal else "metal bought locally: no shipping (ASSUMPTION LOCAL-METAL: same list price)",
                  ship, "BL-082 ship_ground_base_estimate_usd (ASSUMPTION SHIP-BASE)"))
    tot = sum(v for _, v, _ in lines)
    return {"lines": [{"item": a, "usd": round(float(b), 2), "source": s} for a, b, s in lines],
            "per_frame_usd": round(tot, 2), "within_cap": bool(tot <= 150.0),
            "pan_usd": round(p_t + p_s, 2),
            "pan_band_usd": [round(D.scs_price(a_t, len(ft["holes"]), 0) + D.scs_price(a_s, len(fs["holes"]), 0) + 2 * 6 * 3, 2),
                             round(p_t + p_s, 2)]}


def proving(cfg) -> dict:
    lines = [
        ("1 x .065 6061 tube 24 in: BB-D, KF-D coupons and the fit-up trial", 7.85, "Speedy p-4588 24 in"),
        ("SendCutSend coupon strips 5052 (bearing BB-D, bend FB-1) in the pan order", 8.00, "ASSUMPTION SCS-PRICE (small parts)"),
        ("PAHT for coupon cups (CF-1), 60 g", 60 * 0.08 * 1.1, "record"),
        ("PLA for the jigs (~150 g) at USD 20/kg", 3.0, "ASSUMPTION PLA-PRICE"),
        ("tubing cutter to 1-1/8 in (new tool)", 15.0, "BL-080 ASSUMPTION TOOL-PRICE"),
        ("deburr tool + 5.2 / 5.3 mm cobalt bits (new tools)", 14.0, "BL-080 ASSUMPTION TOOL-PRICE"),
        ("spare M5 A2 screws for the coupons (10)", 9.4, "Zoro A2 M5 (BL-077)"),
    ]
    return {"lines": [{"item": a, "usd": round(b, 2), "source": s} for a, b, s in lines],
            "total_usd": round(sum(b for _, b, _ in lines), 2)}


# ============================================================================ B81 lever row (comparison only)
DOUBLER = {"stock": "t875_049", "len_mm": 70.0, "z": (90.0, 160.0),
           "src": "internal 7/8 x .049 6061 doubler (OD 22.2 in the 22.9 bore), bonded (ASSUMPTION DOUBLER-BOND: "
                  "3M DP420-class epoxy, pinned by the two gusset bolts) at z 90-160; Speedy p-4568 12 in USD 12.50"}


def b81_lever_bill(cfg_l: dict, b81_mass: dict, b81_cost: dict, thin_stays: bool = True) -> dict:
    """Mass / cost deltas of the B81 levers against the BL-081 bill: hose-band tees (no 1/4 backers, no 8 tee bolts),
    .049 stays + internal doubler, metal bought locally (no shipping)."""
    st65, st49 = BQ.STOCK["t1000_065"], BQ.STOCK["t1000_049"]
    d_rows = {}
    if thin_stays:
        d_rows["stays 1 x .065 -> 1 x .049 (2 x 530)"] = 2 * 530.0 * (BQ.area("t1000_049") - BQ.area("t1000_065")) * BQ.RHO_AL
        d_rows["internal doublers 2 x 70 mm 7/8 x .049 + adhesive (ASSUMPTION 2 g)"] = \
            2 * DOUBLER["len_mm"] * BQ.area("t875_049") * BQ.RHO_AL + 2.0
    d_rows["tee backers x 8 removed"] = -8 * cfg_l["backer_len"] * BQ.IN * cfg_l["backer_t"] * BQ.RHO_AL
    d_rows["tee clamp bolts x 8 removed"] = -8 * BP.B80_bolt(5, 45)
    d_rows["hose bands x 8 added"] = 8 * D.BAND["mass_g"]
    b65, b49 = st65["od"] - 2 * st65["t"], st49["od"] - 2 * st49["t"]
    if thin_stays:
        d_rows["crown bushing growth (bore 22.1 -> 22.9)"] = 4 * 70.0 * math.pi / 4 * (b49 ** 2 - b65 ** 2) * 0.935e-3
        d_rows["crush sleeves +0.8 mm longer (18)"] = 18 * (b49 - b65) * math.pi / 4 * (7.94 ** 2 - 6.16 ** 2) * BQ.RHO_AL
    dm = sum(d_rows.values())
    # cost
    c = []
    stay_pcs_065 = [530.0, 530.0, 202.6, 202.6, 202.6]
    old, _ = BP._buy_tube("t1000_065", stay_pcs_065)
    new65, how65 = BP._buy_tube("t1000_065", [202.6, 202.6, 202.6])
    new49, how49 = BP._buy_tube("t1000_049", [530.0, 530.0])
    if thin_stays:
        c.append(("1 x .065 tube now rungs + upper bar only (" + how65 + ")", new65 - old))
        c.append(("1 x .049 tube for the stays (" + how49 + ", Speedy p-4586)", new49))
        c.append(("7/8 x .049 12 in for the doublers (Speedy p-4568) + adhesive share (ASSUMPTION USD 2)", 12.50 + 2.0))
    c.append(("1/4 flat backers removed", -6.00))
    c.append(("8 tee bolts removed", -8 * 0.94))
    c.append(("8 hose bands (ASSUMPTION BAND)", 8 * D.BAND["usd"]))
    c.append(("metal bought locally: no shipping (ASSUMPTION LOCAL-METAL)", -BQ.tube_props()["ship_base"]))
    dc = sum(v for _, v in c)
    return {"mass_rows": {k: round(v, 1) for k, v in d_rows.items()}, "d_mass_g": round(dm, 1),
            "body_g": round(b81_mass["body_g"] + dm, 1), "cost_rows": [{"item": a, "usd": round(b, 2)} for a, b in c],
            "d_cost_usd": round(dc, 2), "per_frame_usd": round(b81_cost["per_frame_usd"] + dc, 2)}
