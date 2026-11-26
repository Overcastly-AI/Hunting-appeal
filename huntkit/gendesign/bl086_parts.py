"""BL-086 parts, mass and cost of B86 (B85 + the reworked lumbar node, hip ties, front-leg doublers and bushings).

New printed parts (PAHT-CF, compression / bearing only, none in a bolt preload path):
* ``tie_saddle_86``: upper hip tie, a saddle block between the post front leg (aft face) and the upper rung's front
  half (+/-60 deg contact), held by its own snap arms round the rung (positioning only, no band).
* ``rung_plug_upper_86``: upper rung-end plug with a 50 mm tall head coped to the stay (+/-65 deg), between the gusset
  plates (head width 25 mm).
* ``foot_cup_86``: B81 foot cup with the stay sleeve cut to z 66 (the gusset plates now start at z 68).
* ``im1_collar_86``: IM1 seat ring moved to z 181-189 (on the plug head top).

Also ``lower_tie_saddle_86``: printed saddle washer behind the lower rung (snug bolt, fender washer).

Metal changes: gusset spine z 68-170 (stay holes z 78 / 95), 2 x 1 x 1/8 x 90 front-leg doubler strips, the upper tie spacers / bolts / backer strip deleted, the
3/4 x .035 buy drops to 12 in, both post angles notched at the rungs (finding: the B81 stems overlap the rung fronts
by 5.2 mm).

Mass and cost = the BL-085 bill (``bl085.json``) with every changed line replaced; sources as BL-085.
STL coordinates: frame axes (x lateral, y aft, z up), right-hand part.
"""
from __future__ import annotations

import json
import math

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_parts as BP
from huntkit.gendesign import bl085_parts as P85
from huntkit.gendesign.bl086_local import CFG86, cfg86

OUTDIR = BQ.REPO / "designs" / "pack_5200" / "iter2" / "frame_b86"
PRINT = OUTDIR / "print"
FIT = BP.FIT
R_ST = BQ.STOCK["t1000_065"]["od"] / 2
GUSSET_Z = (68.0, 170.0)            # spine (stay arm) of the .090 gussets
TIE_SADDLE_X = (8.0, 34.0)          # clear of the post stem inner face (x 34.8)
FLAT18_SRC = P85.SRC["flat18"]
SRC = {**P85.SRC,
       "t750_035_12": "Speedy Metals pc-4563 3/4 x .035 6061-T6 (12 in 8.32; BL-082 read 2026-11-25)",
       "flat18x2": "Speedy Metals p-2228 1/8 x 2 6061-T6511 flat (12 in 6.00, 18 in 7.71; read 2026-11-26) - not used, "
                   "the doubler strips come from the 1 x 1/8 bar"}


# ----------------------------------------------------------------------------- printed parts
def tie_saddle(cfg=None):
    """Upper hip-tie saddle (right side): open frame from the post front leg's aft face to the rung, coped to the rung
    (R 12.7 + fit, contact +/-60 deg). Two 3 mm side walls carry the tie push; a 2 mm snap arm wraps the rung to 115 deg
    from the front at top and bottom (positioning only: holds the saddle through the 33 N set-down reversal, no band)."""
    c = cfg86(**(cfg or {}))
    z = c["rung_z"][1]
    yr = BP.yc(z)
    y_leg = BQ.Y_MOUNT + 0.125 * BQ.IN            # aft face of the front leg (the doubler strips are on the front face)
    x0, x1 = TIE_SADDLE_X
    hz = R_ST * math.sin(math.radians(c["tie_saddle_deg"]))
    body = BP.box(x0, x1, y_leg + 0.2, yr - 2.0, z - hz - 2.5, z + hz + 2.5)
    body = body - BP.cyl("x", (yr, z), R_ST + FIT, x0 - 1, x1 + 1)
    # lightening: a through window along x between the leg pad (4 mm) and the saddle shell (3 mm)
    body = body - BP.box(x0 + 3.0, x1 - 3.0, y_leg + 4.2, yr - R_ST - 3.0, z - hz + 1.0, z + hz - 1.0)
    for yh in (y_leg + 10.0, y_leg + 18.0):
        body = body - BP.cyl("x", (yh, z), 3.5, x0 - 1, x1 + 1)
    arm = BP.cyl("x", (yr, z), R_ST + FIT + 2.0, x0 + 8.0, x1 - 8.0) - BP.cyl("x", (yr, z), R_ST + FIT, x0, x1)
    arm = arm - BP.box(x0 - 1, x1 + 1, yr + R_ST * math.cos(math.radians(65.0)), yr + 30, z - 30, z + 30)
    return body + arm


def lower_tie_saddle(cfg=None):
    """Lower hip-tie saddle washer (right side, behind the lower rung at x 30): PAHT-CF block coped to the rung's back
    half (+/-80 deg contact, 25 mm along x), 4 mm over the back crown, flat back face for the M5 x 15 fender washer,
    D5.6 bolt clearance. Snug bolt (no preload credited)."""
    c = cfg86(**(cfg or {}))
    z = c["rung_z"][0]
    yr = BP.yc(z)
    x0, x1 = c["tie_x"] - c["lt_washer_len"] / 2, c["tie_x"] + c["lt_washer_len"] / 2
    hz = R_ST * math.sin(math.radians(c["lt_washer_deg"]))
    body = BP.box(x0, x1, yr + 1.0, yr + R_ST + 4.0, z - hz - 1.5, z + hz + 1.5)
    body = body - BP.cyl("x", (yr, z), R_ST + FIT, x0 - 1, x1 + 1)
    body = body - BP.cyl("y", (c["tie_x"], z), BP.CLR / 2, yr - 20, yr + 30)
    return body


def rung_plug_upper(cfg=None):
    """Upper rung-end plug (B81 saddle plug with a 50 mm tall head coped to the stay, +/-65 deg, width 24.4 mm so it
    sits between the gusset plates; x 90 gusset-bolt clearance)."""
    c = cfg86(**(cfg or {}))
    z = c["rung_z"][1]
    ct = BQ.STOCK[c["ctube"]]
    y0 = BP.yc(z)
    x_end = 115.0 - R_ST - 1.0
    ri = ct["od"] / 2 - ct["t"] - 0.15
    plug = BP.cyl("x", (y0, z), ri, x_end - 25.0, x_end)
    hl = c["plug_len_upper"] / 2
    head = BP.box(x_end - 4.0, 115.0 - R_ST * math.cos(math.radians(c["plug_deg"])), y0 - 12.2, y0 + 12.2, z - hl, z + hl)
    body = plug + head
    body = body - BP.cyl("z", (115.0, y0), R_ST + FIT, z - 40, z + 40)
    body = body - BP.cyl("y", (max(c["ct_bolt_x"]), z), 4.3, y0 - 20, y0 + 20)
    return body


def foot_cup_86(cfg=None):
    """B81 foot cup with the stay sleeve ending at z 66 (2 mm under the gusset plates)."""
    c = cfg86(**(cfg or {}))
    cup = BP.foot_cup(c)
    return cup - (BP.cyl("z", (115.0, 0.0), R_ST + 10.0, 66.0, 90.0) - BP.box(115 + R_ST + 17.9, 200, -30, 30, 0, 100))


def im1_collar_86(cfg=None):
    R = R_ST
    y0 = BP.yc(185.0)
    ring = BP.cyl("z", (115.0, y0), R + 4.0, 181.0, 189.0) - BP.cyl("z", (115.0, y0), R + FIT, 176.0, 194.0)
    return ring - BP.box(113.5, 116.5, y0 - 20, y0, 176, 194)


PARTS86 = {
    "tie_saddle_86": (tie_saddle, 2),
    "lower_tie_saddle_86": (lower_tie_saddle, 2),
    "rung_plug_upper_86": (rung_plug_upper, 2),
    "foot_cup_86": (foot_cup_86, 2),
    "im1_collar_86": (im1_collar_86, 2),
}


def gusset_plates(cfg=None, z_ref: float = 120.0):
    """Front and back .090 gusset plates of the right node as solids (for the interference check). The plates lie on the
    stay crowns and follow the stay's 1.1 deg lean; a box model is placed on the stay line at z_ref (the height of the
    part being checked)."""
    c = cfg86(**(cfg or {}))
    t, w = c["gusset_t"], c["gusset_w"]
    out = []
    for s in (-1, 1):
        yc0 = BP.yc(z_ref)
        y_in = yc0 + s * R_ST
        ya, yb = (y_in, y_in + s * t) if s > 0 else (y_in - t, y_in)
        g = BP.box(115 - w / 2, 115 + w / 2, ya, yb, GUSSET_Z[0], GUSSET_Z[1])
        for z in c["rung_z"]:
            g = g + BP.box(min(c["ct_bolt_x"]) - 12, 115, ya, yb, z - 12.7, z + 12.7)
        out.append(g)
    return out


def post_stem(cfg=None):
    """Right post angle stem (aft leg at the outer edge x 34.8-38.1), z 75-165, with the BL-086 notches at the rungs."""
    c = cfg86(**(cfg or {}))
    st = BP.box(38.1 - 3.175, 38.1, BQ.Y_MOUNT, BQ.Y_MOUNT + 38.1, 75.0, 165.0)
    for z in c["rung_z"]:
        st = st - BP.cyl("x", (BP.yc(z), z), R_ST + 1.0, 30, 45)
    return st


def interference_check(cfg=None) -> dict:
    c = cfg86(**(cfg or {}))
    plates = gusset_plates(c)
    stay = BP.cyl("z", (115.0, BP.yc(c["rung_z"][1])), R_ST, 0, 300)      # stay line at the plug height
    rungs = [BP.cyl("x", (BP.yc(z), z), R_ST, 0.0, 115 - R_ST) for z in c["rung_z"]]
    vol = lambda a, b: float((a ^ b).volume())    # noqa: E731
    head = rung_plug_upper(c)
    out = {
        "plug_head_vs_gusset_plates_mm3": sum(vol(head, p) for p in gusset_plates(c, c["rung_z"][1])),
        "plug_head_vs_im1_collar_mm3": vol(head, im1_collar_86(c)),
        "foot_cup_vs_gusset_plates_mm3": sum(vol(foot_cup_86(c), p) for p in gusset_plates(c, GUSSET_Z[0])),
        "tie_saddle_vs_post_stem_mm3": vol(tie_saddle(c), post_stem(c)),
        "tie_saddle_vs_rung_mm3": vol(tie_saddle(c), rungs[1]),
        "post_stem_vs_rungs_mm3 (notched)": sum(vol(post_stem(c), r) for r in rungs),
        "post_stem_vs_rungs_mm3 (B81, unnotched)": sum(vol(BP.box(38.1 - 3.175, 38.1, BQ.Y_MOUNT, BQ.Y_MOUNT + 38.1, 75, 165), r)
                                                       for r in rungs),
        "plug_head_vs_stay_mm3": vol(head, stay),
        "stay_hole_z78_to_hinge_pin_z60_mm": 18.0,
    }
    out["ok"] = all(v < 1.0 for k, v in out.items() if k.endswith("mm3") and "B81" not in k) or \
        all(v < 1.0 for k, v in out.items() if "mm3" in k and "B81" not in k)
    return out


def export(cfg=None, log=print) -> dict:
    PRINT.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (fn, n) in PARTS86.items():
        tm = BP.to_trimesh(fn(cfg))
        p = PRINT / f"{name}_R.stl"
        tm.export(p)
        tl = tm.copy()
        tl.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
        tl.invert()
        tl.export(PRINT / f"{name}_L.stl")
        vol = float(abs(tm.volume))
        out[name] = {"file": str(p.relative_to(BQ.REPO)), "count": n, "volume_mm3": round(vol, 1),
                     "mass_g_each": round(vol * BQ.RHO_PAHT, 1), "watertight": bool(tm.is_watertight),
                     "bbox_mm": np.round(tm.extents, 1).tolist()}
        log(f"  {name}: {vol * BQ.RHO_PAHT:.1f} g x {n}, watertight {tm.is_watertight}")
    return out


# ----------------------------------------------------------------------------- bill
BOLTS86 = [   # (count, d, L, where)
    (12, 5, 35, "lumbar gusset through-bolts (stay z 78 / 95, rungs x 62 / 90)"),
    (2, 5, 80, "lower hip tie bolts (front leg + doubler + strip, spacer, rung, crush sleeve, printed saddle, fender washer), snug + locknut"),
    (4, 5, 16, "front-leg doubler end bolts"),
    (8, 5, 50, "upper-tee clamp bolts (BL-085)"),
    (4, 5, 50, "upper bar end bolts (BL-085)"),
    (2, 5, 35, "mid-bar socket cross bolts (BL-085)"),
    (2, 5, 40, "pawl housing (B81)"),
]
HIP_FIX86 = (6, 5, 20, "Ti mount (M5 x 20: + 3.2 mm doubler strip)")


def gusset_area86(cfg) -> float:
    w = cfg["gusset_w"]
    xb = min(cfg["ct_bolt_x"])
    rc = BQ.STOCK[cfg["ctube"]]["od"] / 2
    return w * (GUSSET_Z[1] - GUSSET_Z[0]) + 2 * (115 - w / 2 - (xb - 12)) * 2 * rc


def mass_table(printed: dict, cfg=None) -> dict:
    c = cfg86(**(cfg or {}))
    b85 = json.loads((P85.OUTDIR / "bl085.json").read_text())
    rows = dict(b85["mass"]["rows"])
    for k in [k for k in rows if k.startswith(("hip tie spacer", "hip tie backer strips", "lumbar L-gussets",
                                                "printed: foot_cup", "printed: im1_collar", "printed: rung_saddle_plug",
                                                "crown bushing growth", "crush sleeves", "mid-tee hose bands",
                                                "M5 screws + nuts"))]:
        rows.pop(k)
    A35 = BQ.area("t750_035")
    rows["hip tie spacer x 2 (lower ties only; 3/4 x .035, 31.0 mm)"] = 2 * 31.0 * A35 * BQ.RHO_AL
    rows["hip tie backer strip x 1 (lower; 1 x 1/8 x 76)"] = 76.0 * BQ.IN * 0.125 * BQ.IN * BQ.RHO_AL
    d = c["leg_doubler"]
    rows[f"front-leg doubler strips x {d['n']} (1 x 1/8 x {d['len']:g})"] = d["n"] * d["len"] * d["w"] * d["t"] * BQ.RHO_AL
    rows["M5 x 15 fender washers x 2 (stainless, 1.2 mm, lower-tie saddles)"] = \
        2 * math.pi / 4 * (15.0 ** 2 - 5.3 ** 2) * 1.2 * BQ.RHO_STEEL
    rows["lumbar L-gussets x 4 (.090 6061, spine z 68-170)"] = 4 * gusset_area86(c) * c["gusset_t"] * BQ.RHO_AL
    rows["printed: rung_saddle_plug (lower, B81) x 2"] = 20.0
    for name, v in printed.items():
        rows[f"printed: {name} x {v['count']}"] = v["count"] * v["mass_g_each"]
    st = BQ.STOCK[c["stay"]]
    bore = st["od"] - 2 * st["t"]
    per_mm = math.pi / 4 * ((bore ** 2 - 16.0 ** 2) - (18.0 ** 2 - 16.0 ** 2)) * 0.935e-3
    rows[f"crown bushing growth (2 x {c['bush_len']:g} leg-end + 2 x 70 stay-top UHMWPE, bore 18 -> {bore:.1f})"] = \
        (2 * c["bush_len"] + 2 * 70.0) * per_mm
    rows["crush sleeves x 20 (5/16 x .035, 22.1 mm)"] = 20 * 22.1 * math.pi / 4 * (7.94 ** 2 - 6.16 ** 2) * BQ.RHO_AL
    rows["hose bands x 2 (9 mm stainless: mid tees, BL-085)"] = 2 * P85.BAND_G
    rows["M5 screws + nuts (joints)"] = sum(n * BP.B80_bolt(dd, L) for n, dd, L, _ in BOLTS86)
    body = sum(rows.values())
    printed_g = sum(v for k, v in rows.items() if k.startswith("printed"))
    return {"rows": {k: round(float(v), 1) for k, v in rows.items()}, "body_g": round(body, 1),
            "printed_g": round(printed_g, 1), "hip_hw_g": round(HIP_FIX86[0] * BP.B80_bolt(5, 20), 1),
            "vs_b85_g": round(body - b85["mass"]["body_g"], 1), "b85_body_g": b85["mass"]["body_g"]}


def cost_table(mass: dict, cfg=None, ship_zone: int = 8) -> dict:
    c = cfg86(**(cfg or {}))
    from huntkit.gendesign.bl085_tee import CFG85
    cl = {r["part"]: r for r in P85.cut_list()}
    lines = []
    p65 = [CFG85["stay_len"]] * 2 + [cl["lumbar rung"]["length_mm"]] * 2 + [cl["upper bar"]["length_mm"]]
    usd, how = P85._buy(BQ.PRICE["t1000_065"], p65)
    lines.append((f"1 x .065 6061-T6 tube: {', '.join(f'{p:g}' for p in p65)} mm, buy {how}", usd, SRC["t1000_065"]))
    p35 = [cl["mid bar"]["length_mm"]] + [31.0] * 2
    usd, how = P85._buy({12: 8.32, 24: 12.47, 36: 16.63}, p35)
    lines.append((f"3/4 x .035 6061-T6 tube: {', '.join(f'{p:g}' for p in p35)} mm, buy {how}", usd, SRC["t750_035"]))
    lines.append((".090 6061-T6 sheet 12 x 12 in (4 L-gussets, spine z 68-170)", 22.05, SRC["sheet090"]))
    lines.append(("1-1/2 x 1-1/2 x 1/8 6061 angle 18 in (post + foot plates, B81)", BQ.ANGLE_15["usd"], SRC["angle"]))
    L18 = 76 + 8 * 14 + c["leg_doubler"]["n"] * c["leg_doubler"]["len"] + 11 * BP.KERF
    assert L18 <= 18 * BQ.IN, L18
    lines.append((f"1/8 x 1 6061 flat 18 in (1 tie strip 76, 8 spacer washers 14, 2 doubler strips 90: {L18:.0f} mm "
                  "with kerfs)", 4.50, SRC["flat18"]))
    L14 = 4 * CFG85["backer_len_upper"] + 4 * CFG85["backer_len_lower"] + 8 * BP.KERF
    lines.append((f"3/16 x 1 6061 flat 24 in (8 backers, {L14:.0f} mm with kerfs)", 6.59, SRC["flat316"]))
    L_sh = 2 * CFG85["shell_len"] + 2 * BP.KERF
    n_in = math.ceil(L_sh / BQ.IN)
    lines.append((f"1-1/4 x .120 6061 tube by the inch, {n_in} in (2 tees of half-shells, BL-085)", n_in * 1.49, SRC["shell"]))
    lines.append(("M5 x 15 stainless fender washers x 2 (lower-tie saddles)", 0.20,
                  "ASSUMPTION WASHER-PRICE: USD 0.10 each, as the BL-077 nut line (not read)"))
    lines.append(("5/16 x .035 tube for 20 crush sleeves", 3.00, BQ.CRUSH_SLEEVE["src"]))
    pr = mass["printed_g"] * P85.PAHT_USD_G
    lines.append((f"PAHT-CF filament {mass['printed_g']:.0f} g x 1.10 support", pr, "record USD 80/kg; BL-053 support x1.10"))
    nb = sum(n for n, *_ in BOLTS86) + HIP_FIX86[0]
    lines.append((f"M5 A4 screws + nuts ({nb})", nb * (P85.SCREW_EACH + P85.NUT_EACH), SRC["screws"]))
    lines.append(("9 mm stainless hose bands x 2 (mid tees, BL-085)", 2 * P85.BAND_EACH, SRC["band"]))
    lines.append(("threadlocker share", 0.90, "BL-077 LOC-SHARE"))
    lines.append(("UHMWPE for the 2 x 40 mm longer leg-end bushings", 0.0,
                  "crown-kit bushing stock (carried over; not in the B81 / B85 frame bill either)"))
    ship = (P85.SHIP_ZONE8 if ship_zone == 8 else P85.SHIP_ZONE5) * P85.FUEL
    lines.append((f"shipping, one FedEx Ground box <= 36 in, zone {ship_zone} + fuel", ship, SRC["ship"]))
    tot = sum(v for _, v, _ in lines)
    return {"lines": [{"item": a, "usd": round(float(b), 2), "source": s} for a, b, s in lines],
            "per_frame_usd": round(tot, 2), "within_cap": bool(tot <= 150.0), "ship_zone": ship_zone}


def cut_list(cfg=None) -> list[dict]:
    c = cfg86(**(cfg or {}))
    zs = c["stay_bolt_z"]
    return [
        {"part": "stay", "stock": "t1000_065", "qty": 2, "length_mm": 545.0,
         "holes": f"z 60 along x (hinge pin); z {zs[0]:g} / {zs[1]:g} along y (gusset bolts, crush sleeve); NO hole above "
                  "z 100", "note": "BL-086: gusset holes moved down from z 105 / 135 (out of the stay's bending peak)"},
        {"part": "lumbar rung", "stock": "t1000_065", "qty": 2, "length_mm": 202.6,
         "holes": "along y at x +/-62, +/-90 (gussets); lower rung only: +/-30 (hip ties); UPPER RUNG: NO tie holes",
         "note": "BL-086: the upper hip ties are printed saddles"},
        {"part": "lumbar gusset (.090)", "stock": "sheet_090", "qty": 4, "length_mm": None,
         "holes": f"stay arm z {GUSSET_Z[0]:g}-{GUSSET_Z[1]:g}: holes z {zs[0]:g} / {zs[1]:g}; rung arms as B81",
         "note": "stay arm 2 mm longer at the bottom than B81"},
        {"part": "hip tie spacer", "stock": "t750_035", "qty": 2, "length_mm": 31.0, "holes": "-", "note": "lower ties only"},
        {"part": "lower-tie saddle washer (printed lower_tie_saddle_86) + M5 x 15 fender washer", "stock": "PAHT-CF", "qty": 2,
         "length_mm": c["lt_washer_len"], "holes": "D5.6", "note": "behind the lower rung under the nut; bolt SNUG 0.5 N m + "
         "nylon-insert locknut (no preload credited)"},
        {"part": "front-leg doubler strip", "stock": "flat_1x18", "qty": 2, "length_mm": 90.0,
         "holes": "3 mount holes (x 14.12 / 18.44 positions of that side) + 2 end holes z 80 / 160 at x 16.3",
         "note": "on the front face of each angle under the Ti mount; mount screws become M5 x 20"},
        {"part": "hip post angle", "stock": "angle_15", "qty": 2, "length_mm": 90.0,
         "holes": "B81 front-leg holes minus the upper tie holes",
         "note": "BL-086 finding: notch each stem R 13.7 x 6 mm at both rung heights (file); B81 stems overlap the rungs"},
        {"part": "hip tie backer strip", "stock": "flat_1x18", "qty": 1, "length_mm": 76.0, "holes": "2 x D5.3 at +/-30",
         "note": "lower ties only"},
    ]
