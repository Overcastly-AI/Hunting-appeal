"""CORRIE F rev 3 camo release: print files, placed layouts, colour spec, vendors/cost, previews.

Fixes review M-10 (designs/pack_5200/analysis/review_20261113_rev3_release.md): no camo print file,
colourway, repeat, vendor, MOQ, lead time or print cost was released for the 630D camo pieces
(B-02u, SH-07, SH-01b, FP-b, B-29f, A1-d), and nothing confirmed the camo is original.

    python -m designs.pack_5200.camo_corrie_f_rev3            # everything (about 3 min)
    python -m designs.pack_5200.camo_corrie_f_rev3 --fast     # 75 dpi print files (tests / quick look)

Writes outputs/release/pack5200_corrie_f_rev3/camo/ and outputs/screens/20261113_camo_<n>.png.
Read-only inputs: the release DXF of the 630D pieces, designs/apparel/camo/owner_base.yaml + source SVG,
data/materials/textiles/{polyester_ht_630d_printable,polyester_300d_printable}.yaml.

Which camo (traced 2026-11-13): the rev 3 renders use ``huntkit.viz3d`` ``studio.MATERIALS["camo"]`` ->
``cycles_render.owner_camo_png`` = the owner base SVG at ``camo_repeat_mm`` 380 (the accent scale of
owner_base.yaml), i.e. **Owner Base, accent 380 mm, the 4 owner inks**. Their solids come from
``viz3d.export.colorway({"colorway": "talus"})``; "talus" is not a primary pairing id, so the hard-coded
default applies: body #6E745B (= Krummholz Sage), trim #2D2B27 (Basalt Ink), harness #4A4B3C (Spruce Shadow).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw
from shapely.geometry import box

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from huntkit.camo import color, owner_base as ob, placed as P, vision  # noqa: E402
from huntkit.camo.export import MAX_PREVIEW_BYTES, _distance_rows, _font, save_png  # noqa: E402
from huntkit.materials import load as load_material  # noqa: E402

REL = REPO / "outputs" / "release" / "pack5200_corrie_f_rev3"
OUT = REL / "camo"
DXF = REL / "patterns" / "dxf" / "primary" / "polyester_ht_630d_printable.dxf"
MARKERS = REL / "patterns" / "markers" / "markers.json"
SCREENS = REPO / "outputs" / "screens"
DATE = "20261113"
SEED = 20261113
IN = 25.4
YD = 914.4
SQYD_M2 = 0.83612736

# rendered solids (see module docstring); primary pairings offered for comparison
RENDER_SOLIDS = {"body": ("Krummholz Sage (as rendered)", "#6E745B"), "trim": ("Basalt Ink", "#2D2B27")}
PAIRINGS = [("As rendered: Krummholz Sage body", "#6E745B", "#2D2B27"),
            ("Sidehill (primary): Sidehill Olive body", "#8B8148", "#313120"),
            ("Wallow (primary): Elk Wallow body", "#5E5A40", "#313120")]

# ----------------------------------------------------------------------------- bases (records)
def bases() -> dict:
    out = {}
    for key, mid, label in (("630d", "polyester_ht_630d_printable", "630D HT polyester, TPU back (primary)"),
                            ("hyperd300", "polyester_300d_printable", "HyperD 300, PU back (BL-037 G-2, gated AB-1)")):
        m = load_material(mid)
        out[key] = {"material_id": mid, "label": label, "roll_mm": float(m.get("roll_width_mm")),
                    "usable_mm": float(m.get("usable_width_mm")), "gsm": m.get("areal_density_gsm"),
                    "cost": getattr(m, "cost_usd", None) or {}}
    return out


# ----------------------------------------------------------------------------- spec
def spec() -> dict:
    s = yaml.safe_load(ob.SPEC_PATH.read_text(encoding="utf-8"))
    return s


def extras_common() -> list[P.Item]:
    return [P.Item("TEST", box(0, 0, 100, 100), (0.0,), {"kind": "test_square", "label": "100 mm test square"}),
            P.Item("QC", box(0, 0, 120, 34), (0.0,), {"kind": "qc_strip",
                                                     "label": "ink QC: Bench Grass | Sidehill Olive | Bleached Tine | Deadfall Shadow"})]


def ab1_extras() -> list[P.Item]:
    """BL-038 AB-1 specimens on the HyperD print (test_register.csv AB-1)."""
    return [P.Item("AB1-LAB", box(0, 0, 300, 300), (0.0,), {"camo": True, "phase": (40.0, 90.0),
                                                            "label": "AB-1 lab sample 300 x 300 (Martindale)"}),
            P.Item("AB1-LOOK", box(0, 0, 300, 300), (0.0,), {"camo": True, "phase": (200.0, 10.0),
                                                             "label": "AB-1 look sample 1 m / 10 m + spare"}),
            P.Item("AB1-BRUSH1", box(0, 0, 50, 300), (0.0,), {"camo": True, "phase": (120.0, 300.0),
                                                              "label": "brush"}),
            P.Item("AB1-BRUSH2", box(0, 0, 50, 300), (0.0,), {"camo": True, "phase": (300.0, 150.0),
                                                              "label": "brush"})]


def build_layouts(pieces, tile, bs) -> dict[str, P.Sheet]:
    hd, c6 = bs["hyperd300"], bs["630d"]
    hd_w = 58 * IN                                      # RBTR: 58 in printed (56 in guaranteed usable)
    hd_m = (hd_w - hd["usable_mm"]) / 2
    sheets = {}
    # 1 set, area-billed vendors (cut a custom-size print)
    sheets["corrie_f_rev3_camo_1set_tile"] = P.layout_sheet(
        "1 set tile", tile.width_mm + 20, 18 + tile.length_mm + 6 + 100 + 6, tile, 1, margin_mm=10,
        extras=extras_common())
    sheets["corrie_f_rev3_camo_hyperd300_1yd_3sets"] = P.layout_sheet(
        "HyperD 300, 1 yd, 3 sets", hd_w, YD, tile, 3, margin_mm=hd_m, extras=extras_common())
    sheets["corrie_f_rev3_camo_hyperd300_1yd_2sets_ab1"] = P.layout_sheet(
        "HyperD 300, 1 yd, 2 sets + AB-1", hd_w, YD, tile, 2, margin_mm=hd_m,
        extras=ab1_extras() + extras_common())
    c6_len = 18 + tile.length_mm + 6
    sheets["corrie_f_rev3_camo_630d_engineered_repeat_3sets"] = P.layout_sheet(
        "630D engineered repeat, 3 sets", c6["roll_mm"], c6_len, tile, 3,
        margin_mm=(c6["roll_mm"] - c6["usable_mm"]) / 2, extras=extras_common())
    return sheets


# ----------------------------------------------------------------------------- colour spec
def colour_rows(base, coverage_pieces: dict) -> list[dict]:
    rows = []
    for i, ink in enumerate(base.palette):
        lab = color.hex_to_lab(ink["hex"])
        deer = color.srgb_to_lab(color.simulate_dichromat(color.hex_to_srgb(ink["hex"])))
        dark = ink["role"] == "dark"
        rows.append({
            "ink": i + 1, "key": ink["key"], "name": ink["name"], "ha_code": ink["code"], "role": ink["role"],
            "hex": ink["hex"], "srgb": " ".join(str(v) for v in ink["srgb"]),
            "L": round(float(lab[0]), 1), "a": round(float(lab[1]), 1), "b": round(float(lab[2]), 1),
            "deer_sim_L": round(float(deer[0]), 1),
            "coverage_repeat_pct": round(100 * coverage_pieces["repeat"][i], 1),
            "coverage_on_pieces_pct": round(100 * coverage_pieces["pieces"][i], 1),
            "tol_production_dE00": 1.0,
            "tol_prototype_dE00": 3.0,
            "tol_dL": 0.7 if dark else 1.5,
            "notes": ("no OBA; check 365 nm UV; dark must not print NIR-black only if spec'd" if dark else
                      "no OBA; check 365 nm UV" + ("; hold chroma C* to the low side" if ink["role"] in ("field", "olive") else "")),
        })
    return rows


# ----------------------------------------------------------------------------- vendors / cost
VENDORS = [
    {"id": "rbtr_hyperd300", "vendor": "Ripstop by the Roll (Durham NC, USA) - Design Your Own Fabric",
     "base": "HyperD 300 (record polyester_300d_printable)", "process": "digital dye-sublimation (OutdoorINK line; DYO process not named on the product page)",
     "minimum": "1 linear yard (58 x 36 in); 8 x 8 in sample", "price": "$30.25 / linear yd; 2-5 yd = n x $30.25; sample $5.00",
     "file": "PNG/JPG/WebP/SVG, <= 50 MB, sRGB IEC61966-2.1, 8-bit, >= 150 dpi (OutdoorINK mandates 300 dpi)",
     "lead_time": "3-5 business days processing/printing (OutdoorINK page) + shipping; DYO lead time not published",
     "sources": "https://ripstopbytheroll.com/products/hyperd-300.json ; https://help.ripstopbytheroll.com/en-US/using-the-design-tool-for-custom-uploads-226767 ; https://ripstopbytheroll.com/pages/outdoorink-info",
     "accessed": "2026-11-13"},
    {"id": "contrado_poly_canvas", "vendor": "Contrado (print on demand, US/UK)",
     "base": "Polyester Canvas, 100 % woven polyester, ~260 gsm, uncoated (NOT a repo material record)",
     "process": "print on demand (page says UV inks and also water-based inks - conflicting)",
     "minimum": "none stated; <= 0.8 sq yd fixed price; test print $16.85",
     "price": "<=0.8 sq yd $37.46; 1-3 sq yd $49.95/sq yd; 3-10 $45.00; 10-20 $43.00",
     "file": "TIFF flattened or JPEG, 200 dpi at 100 %, sRGB; max print width 1.42 yd (1298 mm); trims ~0.2 in white",
     "lead_time": "1-2 days production + 1-2 days ship (US shipping $9.95)",
     "sources": "https://www.contrado.com/polyester-canvas-fabric", "accessed": "2026-11-13"},
    {"id": "mill_630d", "vendor": "Custom-print mill program, e.g. Wazoodle / Yarrington Mills (USA); Chinese oxford mills",
     "base": "630D HT polyester, TPU back (record polyester_ht_630d_printable) - print BEFORE coating, or prove the coat on a strike-off",
     "process": "disperse dye-sublimation/transfer on polyester (Wazoodle); rotary/digital at Asian mills",
     "minimum": "50 or 100 yd per print per fabric (Wazoodle); quote-only at oxford mills",
     "price": "strike-off $5 (6 x 6 in) or $50 (36 in x width); print price quoted separately; fabric $18/yd unprinted (record ESTIMATE)",
     "file": "TIFF >= 150 dpi at 100 %, seamless in length and width, CMYK not colour-managed (Wazoodle); tile <= 200 in",
     "lead_time": "artwork 3-5 business days; strike-off 2-4 wk; production 3-6 wk after strike-off approval (Wazoodle); 25-35 days (mh-chine 500D camo listing)",
     "sources": "https://help.wazoodle.com/article/819-custom-print-program-discovery ; https://www.mh-chine.com/products/500d-nylon-66-camouflage-pattern-cordura-material",
     "accessed": "2026-11-13"},
    {"id": "rockywoods_600d_blank", "vendor": "Rocky Woods (USA) - blank for a customer-supplied-fabric bureau",
     "base": "600D coated polyester, optic white prepared-for-print face, white PU back (not the TPU-backed record)",
     "process": "blank only; needs a sublimation bureau that accepts customer fabric (none with a published price found)",
     "minimum": "per 60 yd roll (listing); by the yard mentioned but not offered", "price": "$623.25 / roll (~$10.39/yd); sold out 2026-11-13",
     "file": "n/a", "lead_time": "3 business days processing (site)",
     "sources": "https://rockywoods.com/products/600d-coated-polyester-fabric-optic-white-sold-per-roll",
     "accessed": "2026-11-13"},
]

ASSUMPTIONS = {
    "SHIP": "ASSUMPTION SHIP: shipping $12 per order (RBTR rate not captured; Contrado US $9.95 cited).",
    "PRINT-ADDER": "ASSUMPTION PRINT-ADDER: mill print adder $8/yd over the $18/yd 630D record (no published price; replace with the strike-off quote).",
    "TOL-PROTO": "ASSUMPTION TOL-PROTO: print-on-demand prototypes accepted at dE00 <= 3.0 per ink (digital POD lots are not colour-held); production holds owner_base.yaml qc.ink_tolerance_dE00 = 1.0.",
    "UP": "ASSUMPTION UP: each piece's DXF +y is up on the bag (labels read upright). The placed print renders the camo upright in that frame.",
    "SH01B": "ASSUMPTION SH01B: BL-037 G-2 keeps the SH-01b kick bands on 630D. They are on the HyperD sheets for look only; cut them from 630D (printed or solid) for a structural build.",
}


def cost_rows(tile_sheet: P.Sheet, bs: dict) -> list[dict]:
    hd_price = 30.25
    ship = 12.0
    rows = []
    # A: HyperD 300 at RBTR, 3 sets per yard (placed); n bags -> ceil(n/3) yd
    for n in (1, 10):
        yd = math.ceil(n / 3)
        c = yd * hd_price + ship
        rows.append({"scenario": "A HyperD 300 placed print, RBTR", "bags": n, "order": f"{yd} yd ({3 * yd} sets)",
                     "fabric_print_usd": round(yd * hd_price, 2), "shipping_usd": ship, "total_usd": round(c, 2),
                     "per_bag_usd": round(c / n, 2), "lead_time": "3-5 business days + ship (about 1-2 wk)",
                     "status": "orderable now; base gated by AB-1 + print swatch (BL-037)",
                     "basis": "RBTR $30.25/yd, 1 yd min; ASSUMPTION SHIP"})
    rows.append({"scenario": "A' HyperD 300, 1 yd = 2 sets + AB-1 specimens", "bags": 1, "order": "1 yd",
                 "fabric_print_usd": hd_price, "shipping_usd": ship, "total_usd": hd_price + ship,
                 "per_bag_usd": hd_price + ship, "lead_time": "3-5 business days + ship",
                 "status": "RECOMMENDED first order: is also the BL-038 AB-1 HyperD print (already budgeted there)",
                 "basis": "same; replaces the AB-1 '1 yd HyperD printable' line, no extra spend"})
    # B: Contrado polyester canvas, area-billed
    a1 = tile_sheet.width_mm * tile_sheet.length_mm / 1e6 / SQYD_M2
    c1 = 37.46 if a1 <= 0.8 else 49.95 * a1
    rows.append({"scenario": "B Contrado polyester canvas 260 gsm (look/fit proto only)", "bags": 1,
                 "order": f"1 tile {tile_sheet.width_mm:.0f} x {tile_sheet.length_mm:.0f} mm = {a1:.2f} sq yd",
                 "fabric_print_usd": round(c1, 2), "shipping_usd": 9.95, "total_usd": round(c1 + 9.95, 2),
                 "per_bag_usd": round(c1 + 9.95, 2), "lead_time": "1-2 days + 1-2 days ship",
                 "status": "not a repo material (uncoated, no strength data): look/fit only", "basis": "Contrado tiers (cited)"})
    w10 = min(1298.0, 3 * 417.64 + 2 * 6 + 20)
    l10 = 18 + 4 * (738.05 + 6)
    a10 = w10 * l10 / 1e6 / SQYD_M2
    rate = 45.0 if a10 < 10 else 43.0
    rows.append({"scenario": "B Contrado polyester canvas 260 gsm (look/fit proto only)", "bags": 10,
                 "order": f"1 panel {w10:.0f} x {l10:.0f} mm = {a10:.2f} sq yd (12 sets)",
                 "fabric_print_usd": round(rate * a10, 2), "shipping_usd": 9.95,
                 "total_usd": round(rate * a10 + 9.95, 2), "per_bag_usd": round((rate * a10 + 9.95) / 10, 2),
                 "lead_time": "1-2 days + 1-2 days ship", "status": "look/fit only", "basis": "Contrado tiers (cited)"})
    # C: mill 630D at MOQ
    moq = 50
    unp = float(bs["630d"]["cost"].get("value", 18.0)) if isinstance(bs["630d"]["cost"], dict) else 18.0
    mill = moq * (unp + 8.0) + 50.0 + ship
    sets_per_yd = 3 * YD / (18 + 738.05 + 6)
    for n in (1, 10):
        rows.append({"scenario": "C 630D mill print at MOQ (primary base)", "bags": n,
                     "order": f"MOQ {moq} yd (~{int(moq * sets_per_yd)} sets) + $50 strike-off",
                     "fabric_print_usd": round(moq * (unp + 8.0), 2), "shipping_usd": ship,
                     "total_usd": round(mill, 2), "per_bag_usd": round(mill / n, 2),
                     "lead_time": "strike-off 2-4 wk + production 3-6 wk (~6-10 wk)",
                     "status": "only sensible from ~100+ bags; TPU coat vs transfer heat unproven",
                     "basis": "Wazoodle MOQ/strike-off (cited); record $18/yd ESTIMATE; ASSUMPTION PRINT-ADDER $8/yd"})
    rows.append({"scenario": "D solid 630D fallback (review M-10 option)", "bags": 1, "order": "0.81 yd unprinted (1-bag marker)",
                 "fabric_print_usd": round(0.81 * unp, 2), "shipping_usd": ship, "total_usd": round(0.81 * unp + ship, 2),
                 "per_bag_usd": round(0.81 * unp + ship, 2), "lead_time": "stock", "status": "no camo; fallback",
                 "basis": "BOM proto_qty 0.738 m; record $18/yd"})
    return rows


# ----------------------------------------------------------------------------- previews
BG = (246, 245, 241)


def _txt(im, xy, s, size=16, bold=False, fill=(25, 25, 25)):
    ImageDraw.Draw(im).text(xy, s, fill=fill, font=_font(size, bold))


def bag_mock(pieces, labels, repeat_mm, hexes, phases, body_hex, trim_hex, ppmm=1.0, bg=(246, 245, 241),
             pad_mm=(160, 120)) -> np.ndarray:
    """Flat aft-face schematic of the bag: B-02u blade U (engineered phase), body door panel inside the
    U with the #10 zip, crown lid with the B-29f camo corner caps and SH-07 on the right blade top.
    Schematic only (not the 3D shape)."""
    pg = {p.piece_id: p for p in pieces}
    b02 = pg["B-02u"]
    sew = b02.visible
    x0, y0, x1, y1 = sew.bounds
    lid_h = 150.0
    W = int((x1 - x0 + 2 * pad_mm[0]) * ppmm)
    H = int((y1 - y0 + lid_h + 2 * pad_mm[1]) * ppmm)
    img = Image.new("RGB", (W, H), bg)
    ox, oy = pad_mm[0] - x0, pad_mm[1] + lid_h + y1      # piece (x, y up) -> image px

    def to_px(poly):
        return [((x + ox) * ppmm, (oy - y) * ppmm) for x, y in poly.exterior.coords]

    d = ImageDraw.Draw(img)
    hull = sew.convex_hull
    door = hull.difference(sew)
    door = max(door.geoms, key=lambda g: g.area) if door.geom_type != "Polygon" else door
    d.polygon(to_px(door), fill=color.hex_to_rgb8(body_hex))
    crop, mask = P.sample_piece(labels, repeat_mm, sew, phases["B-02u#1"], ppmm)
    rgb = ob.labels_to_rgb(crop, hexes)
    tile = Image.fromarray(rgb)
    m = Image.fromarray((mask * 255).astype(np.uint8))
    img.paste(tile, (int((x0 + ox) * ppmm), int((oy - y1) * ppmm)), m)
    d.line(to_px(door.buffer(-3)), fill=color.hex_to_rgb8(trim_hex), width=max(2, int(5 * ppmm)))
    # lid
    lid = box(x0 - 6, y1, x1 + 6, y1 + lid_h)
    d.polygon(to_px(lid), fill=color.hex_to_rgb8(body_hex))
    for k, (cx, sgn) in enumerate(((x0 - 6, 1), (x1 + 6, -1))):
        cap = box(min(cx, cx + sgn * 90), y1 + 6, max(cx, cx + sgn * 90), y1 + 21)
        c, mk = P.sample_piece(labels, repeat_mm, cap, phases[f"B-29f#{k + 1}"], ppmm)
        img.paste(Image.fromarray(ob.labels_to_rgb(c, hexes)), (int((cap.bounds[0] + ox) * ppmm),
                                                                 int((oy - cap.bounds[3]) * ppmm)),
                  Image.fromarray((mk * 255).astype(np.uint8)))
    d.line([((x0 - 6 + ox) * ppmm, (oy - y1 - lid_h + 10) * ppmm), ((x1 + 6 + ox) * ppmm, (oy - y1 - lid_h + 10) * ppmm)],
           fill=color.hex_to_rgb8(trim_hex), width=max(2, int(6 * ppmm)))
    garage = box(x1 - 50, y1 - 70, x1 - 10, y1 - 10)
    c, mk = P.sample_piece(labels, repeat_mm, garage, phases["SH-07#1"], ppmm)
    img.paste(Image.fromarray(ob.labels_to_rgb(c, hexes)), (int((garage.bounds[0] + ox) * ppmm),
                                                             int((oy - garage.bounds[3]) * ppmm)),
              Image.fromarray((mk * 255).astype(np.uint8)))
    d.line(to_px(garage), fill=color.hex_to_rgb8(trim_hex), width=1)
    return np.asarray(img)


def screen_swatch(base, rows, tile_labels_1ppmm, repeat_mm, out: Path) -> Path:
    W, H = 1600, 1180
    im = Image.new("RGB", (W, H), BG)
    _txt(im, (24, 14), "CORRIE F rev 3 camo: Owner Base, accent repeat 380 x 380 mm (15 x 15 in), 4 flat inks", 26, True)
    _txt(im, (24, 50), "Seamless repeat (left, 1 repeat) and 2 x 2 tiling (right, red ticks = repeat joins). "
                       "Print files at 300 dpi; colour targets below.", 18)
    rgb = ob.labels_to_rgb(tile_labels_1ppmm, base.hexes)
    one = Image.fromarray(rgb).resize((560, 560), Image.Resampling.NEAREST)
    two = Image.fromarray(np.tile(rgb, (2, 2, 1))).resize((560, 560), Image.Resampling.NEAREST)
    im.paste(one, (24, 90))
    im.paste(two, (24 + 580, 90))
    d = ImageDraw.Draw(im)
    for k in (280,):
        d.line([(604 + k, 80), (604 + k, 90)], fill=(220, 0, 0), width=4)
        d.line([(594, 90 + k), (604, 90 + k)], fill=(220, 0, 0), width=4)
    # 100 mm scale bar under the single repeat
    px100 = 560 * 100 / repeat_mm
    d.rectangle([24, 660, 24 + px100, 668], fill=(30, 30, 30))
    _txt(im, (24, 674), "100 mm", 16)
    # deer view of one repeat
    sim = color.simulate_dichromat(rgb)
    im.paste(Image.fromarray(sim).resize((380, 380), Image.Resampling.NEAREST), (1200, 90))
    _txt(im, (1200, 476), "same repeat, deer (dichromat) simulation", 16)
    _txt(im, (1200, 500), "luminance carries the pattern;", 16)
    _txt(im, (1200, 522), "olive/tan merge in hue, not in L*", 16)
    y = 712
    _txt(im, (24, y), "Ink  name (HA code)          hex      sRGB          CIELAB D65 (L a b)   deer L*  cover  tol dE00 prod/proto", 18, True)
    for k, r in enumerate(rows):
        yy = y + 36 + k * 64
        d.rectangle([24, yy, 104, yy + 52], fill=color.hex_to_rgb8(r["hex"]), outline=(0, 0, 0))
        _txt(im, (120, yy + 2), f"{r['ink']}  {r['name']} ({r['ha_code']})", 20, True)
        _txt(im, (120, yy + 28), f"{r['hex']}   sRGB {r['srgb']:<12}   Lab {r['L']:5.1f} {r['a']:5.1f} {r['b']:5.1f}"
             f"    deer L* {r['deer_sim_L']:4.1f}    {r['coverage_on_pieces_pct']:4.1f} % on pieces    "
             f"{r['tol_production_dE00']} / {r['tol_prototype_dE00']}  |dL*| <= {r['tol_dL']}", 18)
    _txt(im, (24, y + 36 + 4 * 64 + 6), "Names and HA codes are our own identifiers (not Pantone). No optical brighteners; "
         "check every strike-off under a 365 nm lamp.", 17)
    _txt(im, (24, y + 36 + 4 * 64 + 32), "Original art supplied by the owner (DECISIONS 2026-11-01). Originality screen: "
         "originality_check.md in this folder.", 17)
    return save_png(im, out, limit=MAX_PREVIEW_BYTES)


def screen_distance(mock_rgb: np.ndarray, mock_bg_name: str, out: Path) -> Path:
    s, pad, top, left = 230, 10, 30, 230
    rows = _distance_rows(mock_rgb, 1.0, False, s)
    ncol = len(rows[0][1])
    im = Image.new("RGB", (left + ncol * (s + pad), 70 + len(rows) * (s + top + 10)), BG)
    _txt(im, (10, 8), "CORRIE F rev 3 aft face (flat schematic, true scale) on " + mock_bg_name +
         ": human vs deer at distance", 20, True)
    _txt(im, (10, 36), "Blur at the acuity limit + Nyquist resample (huntkit.camo.vision); deer 6 cpd ASSUMPTION; no haze.", 15)
    for r, (rt, cells) in enumerate(rows):
        y = 70 + r * (s + top + 10) + 20
        _txt(im, (10, y + s // 2 - 20), rt.replace(" (", "\n("), 16, True)
        for c, (ct, arr) in enumerate(cells):
            x = left + c * (s + pad)
            im.paste(Image.fromarray(arr), (x, y))
            _txt(im, (x, y - 20), ct, 14)
    return save_png(im, out, limit=MAX_PREVIEW_BYTES)


def screen_mocks(mocks: list[tuple[str, np.ndarray]], out: Path) -> Path:
    h = max(m.shape[0] for _, m in mocks)
    w = sum(m.shape[1] for _, m in mocks) + 20 * (len(mocks) + 1)
    sc = min(1.0, 1500 / w)
    im = Image.new("RGB", (int(w * sc), int(h * sc) + 120), BG)
    _txt(im, (16, 10), "CORRIE F rev 3 bag mock, aft face (flat schematic): engineered camo on the B-02u blade U, "
                       "B-29f lid corner caps, SH-07 garage", 19, True)
    _txt(im, (16, 40), "Body = door panel and lid. Left: solids as in the rev 3 renders. Middle/right: primary pairings "
                       "for comparison (owner decision).", 16)
    x = 20
    for t, m in mocks:
        mi = Image.fromarray(m)
        mi = mi.resize((int(m.shape[1] * sc), int(m.shape[0] * sc)), Image.Resampling.LANCZOS)
        im.paste(mi, (int(x * sc), 110))
        _txt(im, (int(x * sc), 80), t, 16, True)
        x += m.shape[1] + 20
    return save_png(im, out, limit=MAX_PREVIEW_BYTES)


def screen_layout(sheet: P.Sheet, labels_small, repeat_mm, hexes, phases, stats: list[str], out: Path) -> Path:
    prev = P.render_sheet(sheet, labels_small, repeat_mm, hexes, 25.4 * 0.95, phases,
                          title="HyperD 300, 1 yd (58 x 36 in): 3 CORRIE F rev 3 camo sets, placed print",
                          cutline_mm=1.2)
    W = prev.width + 40
    im = Image.new("RGB", (W, prev.height + 90 + 26 * len(stats)), BG)
    _txt(im, (20, 10), "Placed-layout sheet: every camo piece printed in its own on-bag frame; waste unprinted", 22, True)
    im.paste(prev, (20, 46))
    d = ImageDraw.Draw(im)
    d.rectangle([19, 45, 20 + prev.width, 46 + prev.height], outline=(120, 120, 120))
    for k, s in enumerate(stats):
        _txt(im, (20, prev.height + 60 + 26 * k), s, 17)
    return save_png(im, out, limit=MAX_PREVIEW_BYTES)


# ----------------------------------------------------------------------------- main
def run(dpi: float = 300.0, out: Path = OUT, screens: bool = True, verbose: bool = True) -> dict:
    t0 = time.time()
    log = print if verbose else (lambda *a, **k: None)
    warnings.simplefilter("ignore", ob.ProxyWarning)
    out = Path(out)
    (out / "print").mkdir(parents=True, exist_ok=True)
    (out / "previews").mkdir(parents=True, exist_ok=True)
    s = spec()
    rep = float(s["repeat_mm"]["accent"]["width"])
    full = float(s["repeat_mm"]["full"]["width"])
    base = ob.load_owner_base()
    if base.is_proxy:
        raise RuntimeError("owner SVG missing: refusing to release a PROXY print")
    hexes = base.hexes
    seam = base.check_seamless()
    bs = bases()
    pieces = P.read_dxf_pieces(DXF)
    tile = P.set_tile(pieces)
    lab1 = P.clean_hairlines(base.labels(int(rep)))    # 1 px/mm for phase engineering + previews
    phases = P.engineer_phases(pieces, lab1, rep, seed=SEED)
    sheets = build_layouts(pieces, tile, bs)
    log(f"layouts ready {time.time() - t0:.0f}s; tile {tile.width_mm:.1f} x {tile.length_mm:.1f} mm, util {tile.utilisation:.3f}")

    # --- uniform seamless repeats
    files = []
    n_rep = int(round(rep / IN * dpi))
    lab_hi = P.clean_hairlines(base.labels(n_rep))    # cairosvg 1-px seams removed
    rgb_hi = ob.labels_to_rgb(lab_hi, hexes)
    tag = f"{int(dpi)}dpi"
    p_tif = out / "print" / f"owner_base_accent_{int(rep)}mm_{tag}.tif"
    Image.fromarray(rgb_hi).save(p_tif, compression="tiff_lzw", dpi=(dpi, dpi))
    p_png = out / "print" / f"owner_base_accent_{int(rep)}mm_{tag}.png"
    Image.fromarray(rgb_hi).save(p_png, dpi=(dpi, dpi), optimize=True)
    files += [p_tif, p_png]
    n_full = int(round(full / IN * dpi))
    p_full = out / "print" / f"owner_base_full_{int(full)}mm_{tag}.tif"
    Image.fromarray(ob.labels_to_rgb(P.clean_hairlines(base.labels(n_full)), hexes)).save(p_full, compression="tiff_lzw", dpi=(dpi, dpi))
    files.append(p_full)
    log(f"repeats written {time.time() - t0:.0f}s")

    # --- placed sheets at print resolution (labels at the print dpi of one repeat)
    sheet_meta = {}
    for name, sh in sheets.items():
        img = P.render_sheet(sh, lab_hi, rep, hexes, dpi, phases,
                             title=f"HUNTING-APPEAL CORRIE F rev 3 camo | {sh.name} | Owner Base accent {int(rep)} mm | "
                                   f"{int(dpi)} dpi | {sh.width_mm:.0f} x {sh.length_mm:.0f} mm")
        fmt = "png" if "hyperd300" in name or "1set" in name else "tif"
        p = out / "print" / f"{name}_{tag}.{fmt}"
        if fmt == "png":
            img.save(p, dpi=(dpi, dpi), optimize=False, compress_level=9)
        else:
            img.save(p, compression="tiff_lzw", dpi=(dpi, dpi))
        files.append(p)
        sheet_meta[name] = {"file": p.name, "width_mm": round(sh.width_mm, 1), "length_mm": round(sh.length_mm, 1),
                            "px": list(img.size), "dpi": dpi, "sets": sh.n_sets,
                            "utilisation_usable": round(sh.utilisation, 3), "notes": sh.notes,
                            "bytes": p.stat().st_size}
        del img
        log(f"  {p.name} {sheet_meta[name]['bytes'] / 1e6:.1f} MB {time.time() - t0:.0f}s")

    # --- cut / placement data (for a contour cutter and for checking)
    with open(out / "placement.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet", "instance", "piece_id", "rotation_deg", "dx_mm", "dy_mm", "bbox_mm",
                    "phase_x_mm", "phase_y_mm"])
        for name, sh in sheets.items():
            for pl in sh.placed:
                if isinstance(pl.ref, P.PieceGeom):
                    ik = pl.key.split("@")[0]
                    ph = phases[ik]
                    w.writerow([name, pl.key, pl.ref.piece_id, pl.rotation, round(pl.dx, 2), round(pl.dy, 2),
                                " ".join(f"{v:.1f}" for v in pl.polygon.bounds), round(ph[0], 2), round(ph[1], 2)])
    _svg_cut(sheets, out / "print")

    # --- coverage and colour spec
    cov_rep = np.bincount(lab1.ravel(), minlength=4)[:4] / lab1.size
    vals = []
    for pg in pieces:
        for k in range(pg.quantity):
            c, m = P.sample_piece(lab1, rep, pg.visible, phases[f"{pg.piece_id}#{k + 1}"], 1.0)
            vals.append(c[m])
    v = np.concatenate(vals)
    cov_p = np.bincount(v, minlength=4)[:4] / v.size
    rows = colour_rows(base, {"repeat": cov_rep, "pieces": cov_p})
    _write_csv(out / "colour_spec.csv", rows)

    # --- vendors + cost
    _write_csv(out / "vendors.csv", VENDORS)
    costs = cost_rows(sheets["corrie_f_rev3_camo_1set_tile"], bs)
    _write_csv(out / "cost_1_and_10_bags.csv", costs)
    bom_line = [{"section": "fabric_print", "item": "camo print, Owner Base accent 380, placed (3 sets/yd)",
                 "material_id": "polyester_300d_printable", "qty_1bag": 1, "qty_10bag": 4, "unit": "yd",
                 "unit_cost_usd": 30.25, "cost_1bag_usd": 30.25, "cost_10bag_usd": 121.0,
                 "source": "RBTR HyperD 300 DYO $30.25/yd, 1 yd min (vendors.csv)",
                 "notes": "replaces the unprinted 630D row only if AB-1 passes; else 630D mill print (C) or solid (D)"}]
    _write_csv(out / "bom_print_line_proposed.csv", bom_line)

    # --- originality screen
    from huntkit.camo import originality as O
    desc = O.describe(ob.labels_to_rgb(P.clean_hairlines(base.labels(760)), hexes), 2.0)
    refs = O.compare_to_references(desc)
    calib = O.calibrate()
    orig = {"descriptor": desc, "references": refs, "calibration": calib,
            "thresholds": {"ncc_copy": O.NCC_COPY, "ncc_clear": O.NCC_CLEAR}}
    (out / "originality_metrics.json").write_text(json.dumps(orig, indent=1, default=str), encoding="utf-8")

    # --- markers comparison
    mk = json.loads(MARKERS.read_text())
    m1 = mk["primary_1bag"]["polyester_ht_630d_printable"]
    m10 = mk["primary_10bag"]["polyester_ht_630d_printable"]
    net = sum(p.cut.area * p.quantity for p in pieces) / 1e6
    hd_sheet = sheets["corrie_f_rev3_camo_hyperd300_1yd_3sets"]
    c6_sheet = sheets["corrie_f_rev3_camo_630d_engineered_repeat_3sets"]
    yield_tbl = {
        "net_piece_area_m2": round(net, 4),
        "release_1bag_marker": {"length_m": m1["length_mm"] / 1000, "efficiency": m1["efficiency"]},
        "release_10bag_marker": {"length_m": m10["length_mm"] / 1000, "efficiency": m10["efficiency"],
                                 "m_per_bag": m10["yield_m_per_unit"]},
        "placed_set_tile": {"w_mm": round(tile.width_mm, 1), "l_mm": round(tile.length_mm, 1),
                            "utilisation": round(tile.utilisation, 3)},
        "placed_630d_repeat": {"repeat_mm": round(c6_sheet.length_mm, 1), "sets": 3,
                               "m_per_bag": round(c6_sheet.length_mm / 3 / 1000, 4),
                               "utilisation_usable": round(c6_sheet.utilisation, 3),
                               "ten_bags_m": round(math.ceil(10 / 3) * c6_sheet.length_mm / 1000, 3),
                               "twelve_sets_same_length": True},
        "placed_hyperd_1yd": {"sets": 3, "utilisation_usable": round(hd_sheet.utilisation, 3)},
    }
    meta = {"pattern": "owner_base", "scale": "accent", "repeat_mm": rep, "full_option_mm": full,
            "inks": hexes, "seam_check": seam, "dpi": dpi, "phases_mm": {k: [round(a, 2), round(b, 2)] for k, (a, b) in phases.items()},
            "set_tile": {"width_mm": tile.width_mm, "length_mm": tile.length_mm, "utilisation": tile.utilisation,
                         "unplaced": tile.unplaced},
            "sheets": sheet_meta, "yield": yield_tbl, "bases": bs, "assumptions": ASSUMPTIONS,
            "render_solids": RENDER_SOLIDS, "pieces": [{"id": p.piece_id, "name": p.name, "qty": p.quantity,
                                                        "grain_deg": round(p.grain_deg, 1),
                                                        "cut_area_m2": round(p.cut.area / 1e6, 5)} for p in pieces]}
    (out / "camo_release.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    log(f"data written {time.time() - t0:.0f}s")

    # --- previews / screens
    shots = []
    if screens:
        prev = out / "previews"
        p1 = screen_swatch(base, rows, lab1, rep, prev / "camo_swatch.png")
        sage = color.hex_to_rgb8(color.BACKGROUNDS["sagebrush"])
        mock_s = bag_mock(pieces, lab1, rep, hexes, phases, RENDER_SOLIDS["body"][1], RENDER_SOLIDS["trim"][1], bg=sage)
        p2 = screen_distance(mock_s, "sagebrush (#878A76)", prev / "camo_distance.png")
        mocks = [(t, bag_mock(pieces, lab1, rep, hexes, phases, bh, th)) for t, bh, th in PAIRINGS]
        p3 = screen_mocks(mocks, prev / "camo_bag_mock.png")
        stats = [f"1 yd = 3 complete sets (B-02u + SH-07 + 2 SH-01b + 2 FP-b + 2 B-29f + A1-d); small pieces nest inside the B-02u U.",
                 f"Set tile {tile.width_mm:.0f} x {tile.length_mm:.0f} mm uses {tile.utilisation * 100:.0f} % of its area "
                 f"(release markers: 1 bag {m1['efficiency'] * 100:.0f} %, 10 bags {m10['efficiency'] * 100:.0f} %).",
                 f"630D engineered repeat {c6_sheet.length_mm:.0f} mm = 3 sets: 10 bags in {yield_tbl['placed_630d_repeat']['ten_bags_m']:.2f} m "
                 f"with 12 sets (release 10-bag marker {m10['length_mm'] / 1000:.2f} m, 10 sets).",
                 "Grey line = cut line, 3 mm camo bleed past it, piece ID inside the seam allowance; QC ink strip + 100 mm square in the waste."]
        p4 = screen_layout(hd_sheet, lab1, rep, hexes, phases, stats, prev / "camo_layout_sheet.png")
        for i, p in enumerate((p1, p2, p3, p4), 1):
            dst = SCREENS / f"{DATE}_camo_{i}.png"
            SCREENS.mkdir(parents=True, exist_ok=True)
            im = Image.open(p).convert("RGB")
            if im.width > 1600:
                im = im.resize((1600, int(im.height * 1600 / im.width)), Image.Resampling.LANCZOS)
            shots.append(save_png(im, dst, limit=MAX_PREVIEW_BYTES))
    log(f"done {time.time() - t0:.0f}s")
    return {"files": files, "sheets": sheet_meta, "screens": shots, "meta": meta, "costs": costs, "colours": rows}


def _svg_cut(sheets: dict, folder: Path):
    """Cut contours per sheet (mm, same frame as the image) for a contour cutter / overlay check."""
    for name, sh in sheets.items():
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sh.width_mm:.1f}mm" height="{sh.length_mm:.1f}mm" '
                 f'viewBox="0 0 {sh.width_mm:.2f} {sh.length_mm:.2f}">',
                 f'<g id="CUT" fill="none" stroke="#ff0000" stroke-width="0.25">']
        for pl in sh.placed:
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in pl.polygon.exterior.coords)
            parts.append(f'<polygon id="{pl.key}" points="{pts}"/>')
        parts.append("</g></svg>")
        (folder / f"{name}_cut.svg").write_text("\n".join(parts), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]):
    keys = list(rows[0].keys())
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fast", action="store_true", help="75 dpi print files, no screens")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    r = run(dpi=75.0 if a.fast else 300.0, out=Path(a.out), screens=not a.fast)
    print(json.dumps({"screens": [str(p) for p in r["screens"]], "sheets": r["sheets"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
