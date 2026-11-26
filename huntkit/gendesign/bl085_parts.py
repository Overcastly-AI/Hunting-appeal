"""BL-085 parts, mass and cost of the B85 tees (on the B81 frame), and the comparison bill (H1c, B81, B81-Lb, D83-L).

Printed (PAHT-CF, compression / bearing only, nothing under preload except the mid saddle's positioning band, which no
strength row credits): upper bar-end saddle plug, mid-tee saddle socket (bar side) and outer saddle half, stay-top
collar (B81 part on the 15 mm longer stay). Metal: stays 545 mm, upper-tee half-shells 100 mm from 1-1/4 x .120 6061
(Speedy p-4573, ID 1.010 in), 1 x 3/16 6061 backers (Speedy p-2233), 1/8 in spacer washers from the 1 x 1/8 flat.

Mass and cost are the BL-081 bill (``bl081.json``) with every changed line replaced and the source of each price
given. STL coordinates: frame axes (x lateral, y aft, z up), right-hand part.
"""
from __future__ import annotations

import json
import math

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ
from huntkit.gendesign import bl081_parts as BP
from huntkit.gendesign.bl085_tee import CFG85

OUTDIR = BQ.REPO / "designs" / "pack_5200" / "iter2" / "frame_b85"
PRINT = OUTDIR / "print"
FIT = BP.FIT
RHO = BQ.RHO_AL

# ----------------------------------------------------------------------------- cited prices (read 2026-11-25 unless noted)
SRC = {
    "t1000_065": "Speedy Metals p-4588 1 x .065 6061-T6 (12 in 5.24, 18 in 6.73, 24 in 7.85, 36 in 10.47; read 2026-11-25)",
    "t750_035": "Speedy Metals pc-4563 3/4 x .035 6061-T6 (12 in 8.32, 24 in 12.47; BL-082 read 2026-11-25)",
    "shell": "Speedy Metals p-4573 1-1/4 OD x 1.010 ID x .120 6061-T6, by the inch USD 1.49 (12 in 26.75; read 2026-11-25)",
    "flat14": "Speedy Metals p-2241 1/4 x 1 6061-T6511 flat (18 in 6.22, 24 in 7.26; read 2026-11-25)",
    "flat316": "Speedy Metals p-2233 3/16 x 1 6061-T6511 flat (18 in 5.65, 24 in 6.59; read 2026-11-25)",
    "flat18": "Speedy Metals p-2225 1/8 x 1 6061-T6511 flat (18 in 4.50; read 2026-11-25; BL-081 booked 3.25)",
    "sheet090": "Speedy Metals p-84 .090 6061-T6 sheet 12 x 12 in USD 22.05 (read 2026-11-25; no smaller size listed)",
    "angle": BQ.ANGLE_15["src"],
    "screws": "Zoro G5321942 M5-0.80 x 35 socket head cap screw, 316 (A4) stainless, 50-pk USD 6.79 = 0.14 each "
              "(search snippet 2026-11-25, secondary; A4-70 proof = A2-70 450 MPa, ISO 3506-1); other lengths booked at the "
              "same each price (ASSUMPTION SCREW-LEN); nut USD 0.10 (BL-077 line)",
    "band": "Zoro G208391365 9 mm stainless worm-drive clamp 20-32 mm, 10-pk USD 12.49 = 1.25 each (search snippet "
            "2026-11-25, secondary)",
    "ship": "FedEx Ground Economy 2026 list (eFulfillment Service table, read 2026-11-25, secondary): 10 lb at zone 8 "
            "USD 20.43 (zone 5 13.24); one 36 x 6 x 6 in box = 9.3 lb dimensional -> 10 lb; ASSUMPTION FUEL-20: +20 % "
            "fuel / residential. Speedy Metals publishes no rates (t-shipping.aspx: 'FedEx ... ask sales')",
}
SHIP_ZONE8, SHIP_ZONE5, FUEL = 20.43, 13.24, 1.20
SCREW_EACH, NUT_EACH = 0.14, 0.10
BAND_EACH, BAND_G = 1.25, 12.0
PAHT_USD_G = 0.08 * 1.10


def stock_shell() -> dict:
    return {"od": 1.25 * BQ.IN, "t": 0.120 * BQ.IN, "id": 1.010 * BQ.IN}


# ----------------------------------------------------------------------------- printed parts
def bar_saddle_plug(cfg=None):
    """Upper bar end: plug 20 mm into the bar bore + a head coped to the shell OD (bears on the shells, compression).
    Clearance holes for the two bar bolts (the crush sleeves sit in the bar, not in the plug: the plug is split by the
    bolt holes and only fills the end)."""
    sh = stock_shell()
    ub = BQ.STOCK[BQ.CFG0["ubar"]]
    rs = sh["od"] / 2
    y0 = BP.yc(520.0)
    x_cope = 115.0 - rs                      # bar end touches the shell OD here
    ri = ub["od"] / 2 - ub["t"] - 0.15
    plug = BP.cyl("x", (y0, 520.0), ri, x_cope - 26.0, x_cope - 6.0)
    head = BP.cyl("x", (y0, 520.0), ub["od"] / 2, x_cope - 6.0, x_cope + 4.0)
    body = (plug + head) - BP.cyl("z", (115.0, y0), rs + FIT, 480.0, 560.0)
    for xb in (x_cope - CFG85["bar_bolt_edge"], x_cope - CFG85["bar_bolt_edge"] - CFG85["bar_bolt_pitch"]):
        body = body - BP.cyl("y", (xb, 520.0), 4.3, y0 - 20, y0 + 20)
    return body


def mid_saddle(cfg=None, half="socket"):
    """Mid tee: split PAHT sleeve round the stay (bore = stay OD + fit, wall 1.5 mm, 40 mm long, split on the y-z plane
    through the stay axis); the inboard half carries the 3/4 in bar socket (20 mm deep, 3 mm wall, M5 cross bolt);
    a 9 mm band groove (0.5 mm deep) in the middle of both halves."""
    R = BQ.STOCK[BQ.CFG0["stay"]]["od"] / 2
    rb = BQ.STOCK[BQ.CFG0["bar"]]["od"] / 2
    w = CFG85["saddle_wall"]
    Ls = CFG85["saddle_len"]
    z, y0 = 330.0, BP.yc(330.0)
    ring = BP.cyl("z", (115.0, y0), R + FIT + w, z - Ls / 2, z + Ls / 2) - BP.cyl("z", (115.0, y0), R + FIT, z - 30, z + 30)
    groove = BP.cyl("z", (115.0, y0), R + 10, z - 4.5, z + 4.5) - BP.cyl("z", (115.0, y0), R + FIT + w - 0.5, z - 5, z + 5)
    ring = ring - groove
    if half == "socket":
        body = ring - BP.box(115.0, 160.0, y0 - 30, y0 + 30, z - 30, z + 30)
        sock = BP.cyl("x", (y0, z), rb + FIT + 3.0, 115.0 - R - 24.0, 115.0 - R + 1.0) - \
            BP.cyl("x", (y0, z), rb + FIT, 115.0 - R - 25.0, 115.0 - R - 2.0)
        sock = sock - BP.cyl("z", (115.0, y0), R + FIT, z - 30, z + 30)
        body = body + sock
        body = body - BP.cyl("y", (115.0 - R - 12.0, z), BP.CLR / 2, y0 - 20, y0 + 20)
        return body
    return ring - BP.box(70.0, 115.0, y0 - 30, y0 + 30, z - 30, z + 30)


def stay_top_collar_85(cfg=None):
    """B81 stay-top collar on the 545 mm stay (rim z 545): sleeve z 535-548, 5 mm clear of the shell top (z 530):
    the 15 mm of bare tube above the shells carries 10 mm of collar and a 5 mm gap."""
    R = BQ.STOCK[BQ.CFG0["stay"]]["od"] / 2
    y0 = BP.yc(545.0)
    top = CFG85["stay_len"]
    ring = BP.cyl("z", (115.0, y0), R + 3.0, top - 10.0, top + 3.0) - BP.cyl("z", (115.0, y0), R + FIT, top - 11.0, top)
    return ring - BP.cyl("z", (115.0, y0), 9.8, top - 1.0, top + 4.0)


PARTS85 = {
    "bar_saddle_plug_upper": (bar_saddle_plug, 2),
    "mid_saddle_socket": (lambda c: mid_saddle(c, "socket"), 2),
    "mid_saddle_outer": (lambda c: mid_saddle(c, "outer"), 2),
    "stay_top_collar_85": (stay_top_collar_85, 2),
}


def metal_parts(cfg=None) -> dict:
    """Metal solids of one (right-hand) upper tee and mid tee for the render and the interference check."""
    c = {**CFG85, **(cfg or {})}
    sh = stock_shell()
    R = BQ.STOCK[BQ.CFG0["stay"]]["od"] / 2
    y0 = BP.yc(520.0)
    z0, z1 = c["shell_top_z"] - c["shell_len"], c["shell_top_z"]
    stay = BP.cyl("z", (115.0, y0), R, 400.0, c["stay_len"]) - BP.cyl("z", (115.0, y0), R - 1.651, 399.0, c["stay_len"] + 1)
    shell = BP.cyl("z", (115.0, y0), sh["od"] / 2, z0, z1) - BP.cyl("z", (115.0, y0), sh["id"] / 2, z0 - 1, z1 + 1)
    shell = shell - BP.box(115.0 - 20, 115.0 + 20, y0 - 0.75, y0 + 0.75, z0 - 1, z1 + 1)    # saw kerf on the x-z plane
    rs = sh["od"] / 2
    tb = c["backer_t"]
    bk = []
    for (za, zb_, Lb) in ((z0, z0 + c["backer_w"], c["backer_len_lower"]), (z1 - c["backer_w"], z1, c["backer_len_upper"])):
        x_out = 115.0 + 18.9 + 8.0
        for s in (-1, 1):
            yb = y0 + s * (rs + tb / 2)
            bk.append(BP.box(x_out - Lb, x_out, yb - tb / 2, yb + tb / 2, za, zb_))
    ub = BQ.STOCK[BQ.CFG0["ubar"]]
    bar = BP.cyl("x", (y0, 520.0), ub["od"] / 2, 20.0, 115.0 - rs) - BP.cyl("x", (y0, 520.0), ub["od"] / 2 - ub["t"], 19.0, 116.0 - rs)
    bolts = []
    for zb in (z0 + c["backer_w"] / 2, z1 - c["backer_w"] / 2):
        for xb in (115.0 - 18.9, 115.0 + 18.9):
            bolts.append(BP.cyl("y", (xb, zb), 2.5, y0 - rs - tb - 4, y0 + rs + tb + 4))
    xc = 115.0 - rs
    for xb in (xc - c["bar_bolt_edge"], xc - c["bar_bolt_edge"] - c["bar_bolt_pitch"]):
        bolts.append(BP.cyl("y", (xb, 520.0), 2.5, y0 - rs - tb - 4, y0 + rs + tb + 4))
    return {"stay": stay, "shells": shell, "backers": bk, "bar": bar, "bolts": bolts}


def interference_check(cfg=None) -> dict:
    """Volumes of overlap between the parts that must not collide (review 9 B1: shell vs stay-top collar)."""
    c = {**CFG85, **(cfg or {})}
    mp = metal_parts(c)
    col = stay_top_collar_85(c)
    plug = bar_saddle_plug(c)
    out = {"shell_vs_collar_mm3": float((mp["shells"] ^ col).volume()),
           "plug_vs_shell_mm3": float((plug ^ mp["shells"]).volume()),
           "backer_vs_collar_mm3": float(sum((b ^ col).volume() for b in mp["backers"])),
           "tube_above_shell_mm": c["stay_len"] - c["shell_top_z"],
           "gap_shell_to_collar_mm": (c["stay_len"] - 10.0) - c["shell_top_z"]}
    out["ok"] = out["shell_vs_collar_mm3"] < 1e-6 and out["backer_vs_collar_mm3"] < 1e-6 and out["plug_vs_shell_mm3"] < 1.0
    return out


def export(cfg=None, log=print) -> dict:
    PRINT.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, (fn, n) in PARTS85.items():
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
BOLTS85 = [   # (count, d, L, where)
    (12, 5, 35, "lumbar gusset through-bolts (B81)"),
    (4, 5, 70, "hip tie bolts (B81)"),
    (8, 5, 50, "upper-tee clamp bolts (2 tees x 2 pairs), beside the stay"),
    (4, 5, 50, "upper bar end, double shear through backers + spacers + bar (crush sleeve)"),
    (2, 5, 35, "mid-bar socket cross bolts (PAHT bearing)"),
    (2, 5, 40, "pawl housing (B81)"),
]
HIP_FIX = (6, 5, 16, "Ti mount (B81)")


def cut_list(cfg=None) -> list[dict]:
    c = {**CFG85, **(cfg or {})}
    half = 115 - 12.7 - 1.0
    return [
        {"part": "stay", "stock": "t1000_065", "qty": 2, "length_mm": c["stay_len"],
         "holes": "z 60 along x (hinge pin); z 105 / 135 along y (gusset bolts, crush sleeve); NO hole above z 160",
         "note": "BL-085: 15 mm longer than B81 so 15 mm of bare tube stand above the upper-tee shells (B1)"},
        {"part": "lumbar rung", "stock": "t1000_065", "qty": 2, "length_mm": round(2 * half, 1), "holes": "B81", "note": ""},
        {"part": "upper bar", "stock": "t1000_065", "qty": 1, "length_mm": round(2 * (115 - math.sqrt((stock_shell()["od"] / 2) ** 2 - 12.7 ** 2)), 1),
         "holes": f"along y at x +/-15 (pawl), and at {c['bar_bolt_edge']:g} / {c['bar_bolt_edge'] + c['bar_bolt_pitch']:g} mm "
                  "from each end (bar bolts, crush sleeve each); ends coped R 15.9 to the shell OD",
         "note": "BL-085: bar runs to the shell OD (no printed socket in the load path)"},
        {"part": "mid bar", "stock": "t750_035", "qty": 1, "length_mm": round(2 * (115 - 12.7 - 1.5 - 2.0), 1),
         "holes": "along y 12 mm from each end (socket cross bolt)", "note": "pinned saddle tee"},
        {"part": "hip tie spacer", "stock": "t750_035", "qty": 4, "length_mm": 31.0, "holes": "B81", "note": ""},
        {"part": "upper-tee half-shell (100 mm ring sawn in half on the x-z plane, 1.5 mm kerf)", "stock": "shell_120",
         "qty": 2, "length_mm": c["shell_len"], "holes": "none", "note": "4 halves; Speedy p-4573 (ID 1.010 in, see SHELL-FIT)"},
        {"part": "upper-tee backer, upper pair (bar bolts + clamp bolts)", "stock": "flat_1x316", "qty": 4,
         "length_mm": c["backer_len_upper"], "holes": "2 clamp holes D5.3 at x 115 +/- 18.9, 2 bar-bolt holes", "note": ""},
        {"part": "upper-tee backer, lower pair (clamp only)", "stock": "flat_1x316", "qty": 4,
         "length_mm": c["backer_len_lower"], "holes": "2 x D5.3 at 37.8 mm", "note": ""},
        {"part": "bar-bolt spacer washer 1/8 x 1 x 14 (between backer and bar wall)", "stock": "flat_1x18", "qty": 8,
         "length_mm": 14.0, "holes": "D5.3 centre", "note": ""},
        {"part": "crush sleeve in the upper bar (bar bolts)", "stock": "sleeve_5_16", "qty": 4, "length_mm": 22.1,
         "holes": "-", "note": "added to B81's 18 (pawl 2 + lumbar 16)"},
        {"part": "B81 parts not listed here (gussets, hip post, foot plates, tie strips, crush sleeves)", "stock": "-",
         "qty": None, "length_mm": None, "holes": "B81 cut list", "note": "unchanged"},
    ]


def mass_table(printed: dict, cfg=None) -> dict:
    """B81 bill with the tee lines replaced."""
    c = {**CFG85, **(cfg or {})}
    b81 = json.loads(BQ.REC_JSON.read_text())
    rows = dict(b81["mass"]["rows"])
    drop = [k for k in rows if k.startswith(("stay x 2", "upper bar x 1", "mid bar x 1", "tee backers", "clamp half-shells",
                                              "crush sleeves", "printed: bar_socket", "printed: stay_top_collar",
                                              "M5 A2 screws"))]
    for k in drop:
        rows.pop(k)
    A65, A35 = BQ.area("t1000_065"), BQ.area("t750_035")
    cl = {r["part"]: r for r in cut_list(c)}
    rows[f"stay x 2 (1 x .065, {c['stay_len']:g} mm)"] = 2 * c["stay_len"] * A65 * RHO
    rows["upper bar x 1 (1 x .065, to the shell OD)"] = cl["upper bar"]["length_mm"] * A65 * RHO
    rows["mid bar x 1 (3/4 x .035)"] = cl["mid bar"]["length_mm"] * A35 * RHO
    sh = stock_shell()
    a_sh = math.pi / 4 * (sh["od"] ** 2 - sh["id"] ** 2)
    rows[f"upper-tee half-shells, 2 tees (1-1/4 x .120, {c['shell_len']:g} mm less kerf)"] = \
        2 * c["shell_len"] * a_sh * RHO * (1 - 2 * 1.5 / (math.pi * (sh["od"] - (sh["od"] - sh["id"]) / 2)))
    rows["upper-tee backers x 8 (1 x 3/16; 4 x 80 + 4 x 55)"] = \
        (4 * c["backer_len_upper"] + 4 * c["backer_len_lower"]) * BQ.IN * c["backer_t"] * RHO
    rows["bar-bolt spacer washers x 8 (1/8 x 1 x 14)"] = 8 * 14.0 * BQ.IN * 0.125 * BQ.IN * RHO * 0.95
    rows["crush sleeves x 22 (5/16 x .035, 22.1 mm)"] = 22 * 22.1 * math.pi / 4 * (7.94 ** 2 - 6.16 ** 2) * RHO
    for name, v in printed.items():
        rows[f"printed: {name} x {v['count']}"] = v["count"] * v["mass_g_each"]
    rows["mid-tee hose bands x 2 (9 mm stainless)"] = 2 * BAND_G
    rows["M5 screws + nuts (joints)"] = sum(n * BP.B80_bolt(d, L) for n, d, L, _ in BOLTS85)
    body = sum(rows.values())
    printed_g = sum(v for k, v in rows.items() if k.startswith("printed"))
    return {"rows": {k: round(float(v), 1) for k, v in rows.items()}, "body_g": round(body, 1),
            "printed_g": round(printed_g, 1), "hip_hw_g": b81["mass"]["hip_hw_g"],
            "vs_b81_g": round(body - b81["mass"]["body_g"], 1)}


def _buy(table: dict, pieces: list) -> tuple:
    import itertools
    best = None
    for n in (1, 2, 3):
        for combo in itertools.combinations_with_replacement(sorted(k for k in table if k <= 36), n):
            free = sorted([l * BQ.IN for l in combo], reverse=True)
            ok = True
            for pc in sorted(pieces, reverse=True):
                for i, f in enumerate(free):
                    if f >= pc + BP.KERF:
                        free[i] -= pc + BP.KERF
                        break
                else:
                    ok = False
                    break
            if ok:
                usd = sum(table[l] for l in combo)
                if best is None or usd < best[0]:
                    best = (usd, " + ".join(f"{l} in" for l in combo))
    return best


def cost_table(mass: dict, cfg=None, ship_zone: int = 8) -> dict:
    c = {**CFG85, **(cfg or {})}
    cl = {r["part"]: r for r in cut_list(c)}
    lines = []
    p65 = [c["stay_len"]] * 2 + [cl["lumbar rung"]["length_mm"]] * 2 + [cl["upper bar"]["length_mm"]]
    usd, how = _buy(BQ.PRICE["t1000_065"], p65)
    lines.append((f"1 x .065 6061-T6 tube: {', '.join(f'{p:g}' for p in p65)} mm, buy {how}", usd, SRC["t1000_065"]))
    p35 = [cl["mid bar"]["length_mm"]] + [31.0] * 4
    usd, how = _buy({12: 8.32, 24: 12.47, 36: 16.63}, p35)
    lines.append((f"3/4 x .035 6061-T6 tube: {', '.join(f'{p:g}' for p in p35)} mm, buy {how}", usd, SRC["t750_035"]))
    lines.append((".090 6061-T6 sheet 12 x 12 in (4 L-gussets, B81)", 22.05, SRC["sheet090"]))
    lines.append(("1-1/2 x 1-1/2 x 1/8 6061 angle 18 in (post + foot plates, B81)", BQ.ANGLE_15["usd"], SRC["angle"]))
    lines.append(("1/8 x 1 6061 flat 18 in (2 tie strips 76 + 8 spacer washers 14)", 4.50, SRC["flat18"]))
    L14 = 4 * c["backer_len_upper"] + 4 * c["backer_len_lower"] + 8 * BP.KERF
    lines.append((f"3/16 x 1 6061 flat 24 in (8 backers, {L14:.0f} mm with kerfs)", 6.59 if L14 <= 24 * BQ.IN else 8.78,
                  SRC["flat316"]))
    L_sh = 2 * c["shell_len"] + 2 * BP.KERF
    n_in = math.ceil(L_sh / BQ.IN)
    lines.append((f"1-1/4 x .120 6061 tube by the inch, {n_in} in (2 tees of half-shells)", n_in * 1.49, SRC["shell"]))
    lines.append(("5/16 x .035 tube for 22 crush sleeves", 3.00, BQ.CRUSH_SLEEVE["src"]))
    pr = mass["printed_g"] * PAHT_USD_G
    lines.append((f"PAHT-CF filament {mass['printed_g']:.0f} g x 1.10 support", pr, "record USD 80/kg; BL-053 support x1.10"))
    nb = sum(n for n, *_ in BOLTS85) + HIP_FIX[0]
    lines.append((f"M5 A4 screws + nuts ({nb})", nb * (SCREW_EACH + NUT_EACH), SRC["screws"]))
    lines.append(("9 mm stainless hose bands x 2 (mid tee)", 2 * BAND_EACH, SRC["band"]))
    lines.append(("threadlocker share", 0.90, "BL-077 LOC-SHARE"))
    ship = (SHIP_ZONE8 if ship_zone == 8 else SHIP_ZONE5) * FUEL
    lines.append((f"shipping, one FedEx Ground box <= 36 in, zone {ship_zone} + fuel", ship, SRC["ship"]))
    tot = sum(v for _, v, _ in lines)
    return {"lines": [{"item": a, "usd": round(float(b), 2), "source": s} for a, b, s in lines],
            "per_frame_usd": round(tot, 2), "within_cap": bool(tot <= 150.0), "ship_zone": ship_zone}


def proving() -> dict:
    lines = [
        ("1 x .065 tube 36 in for KF-T / CL-T / OV-2 coupons (3 tee coupons + 1 mid-saddle coupon)", 10.47, SRC["t1000_065"]),
        ("1-1/4 x .120 tube by the inch, 15 in (3 coupon tees + CL-T)", 15 * 1.49, SRC["shell"]),
        ("3/16 x 1 flat 18 in (coupon backers)", 5.65, SRC["flat316"]),
        ("PAHT for coupon saddles / plugs, 60 g", 60 * PAHT_USD_G, "record"),
        ("screws for coupons (20)", 20 * (SCREW_EACH + NUT_EACH), SRC["screws"]),
        ("dye penetrant kit (KF-T crack check; BL-081 KF-1 already books it)", 0.0, "BL-081 proving"),
        ("tubing cutter to 1-3/8 in (review m5; shells are 1-1/4 in) - new tool", 15.0, "BL-080 ASSUMPTION TOOL-PRICE"),
        ("torque: hex key + 50 kg hanging scale on a marked 50 mm lever (30 N = 1.5 N m), no new tool", 0.0,
         "test kit (CL-1 hanging scale)"),
    ]
    return {"lines": [{"item": a, "usd": round(b, 2), "source": s} for a, b, s in lines],
            "total_usd": round(sum(b for _, b, _ in lines), 2)}
