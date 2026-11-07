"""Pack 5200: the WIDER set of main-bag concepts (owner 2026-11-07: "give me multiple to choose from ... look at other
bags"). Study only; the released SPINE is untouched. Research: docs/research/bag_body_architectures.md section 6.

Eight more concepts, numbered after the first five (1 SPINE, 2 SLAB, 3 TWIN, 4 WRAP, 5 HATCH):

    6  SPIRE   tall slim torpedo top-loader, round section, one short straight front zip
    7  CRADLE  harness bag (the frame-side panel + side wings) holding four roll-top drybags; meat swaps in for a drybag
    8  DUO     two-zone: lower compartment with its own horizontal zip and a removable divider, main above
    9  GULP    big front stretch shove-it pocket over the whole aft face, side zip into the main bag
    10 MAW     clamshell duffel hauler: zip up both aft corners and across the top, the aft face drops open; no roll-top
    11 CAIRN   roll-top with an integrated 6 L lid that converts to a summit pack
    12 WISP    minimalist ultralight: roll-top only, no lid, no zip, no pockets on the body
    13 MANTLE  expedition hauler: box body with two full-height side compression wings (tripod, pads, antlers)

Every concept keeps the frame interface (B-01 with hinge eyes / B-18, IM1-IM3 ports, B-17 / B-23, B-20 ladders, 8 swells,
under-strap channels, B-24 float links via T3) unless its ``interface_changes`` says what moves; 85.2 L +/- 3; 15.5 in
width; quiet (coil zips, no hook-and-loop); solid body with camo accents; fly in its base pocket and bow riser carry are
common. Metrics use exactly the same code as the first five (bag_concepts.metrics).
"""
from __future__ import annotations

import math

import numpy as np

import bag_concepts as BC
from bag_concepts import (A_MAX, COLLAR_TOP, IN, L_CUIN, SA_BODY, SA_FLAT, TARGET_L, Z0, Z_SB, Z_SH, Build, Concept,
                          _accent_rect, _chevron, _line, _seam, boxed_swell, collar_set, frame_collar, frame_panel,
                          y_frame)
from huntkit import materials as MAT
from huntkit.patterns import Piece, Seam, rect_panel, tapered_panel

G_HOOK_G = 4.0          # ASSUMPTION (as the haul wraps, DESIGN.md 4.5)
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")          # 18 g/m
SR25 = MAT.load("buckle_side_release_25mm").require("mass_g")      # 9 g
LADDER = MAT.load("ladder_lock_25mm").require("mass_g")            # 4 g
ROLLTOP_HW_G = 48.5     # geometry.yaml weight row 'roll-top: HDPE strip, 2 x 25 mm SR, 2 x 0.35 m webbing' (common item)

WIDE = {
    "spire": dict(name="SPIRE", kind="d", n=2.5, a_bot=136.0, d_bot=175.0, d_nom=290.0,
                  tagline="Tall slim torpedo top-loader: round section, short straight front zip",
                  access="roll-top + 440 mm straight #10 zip down the centre of the aft face, z 120-560",
                  pitch="Tallest, slimmest, roundest: a torpedo that slips through timber"),
    "cradle": dict(name="CRADLE", kind="box",
                   tagline="Harness bag holding four roll-top drybags; meat swaps in for a drybag",
                   access="lift out any drybag; IM1-IM3 run across the drybags or the meat",
                   pitch="Modular: four waterproof drybags in an open harness, swap one for meat"),
    "duo": dict(name="DUO", kind="d", n=4.0,
                tagline="Two-zone: lower compartment (own zip, removable divider) + main above",
                access="roll-top for the main zone; 600 mm horizontal #10 zip into the lower zone at z 330",
                pitch="Sleep kit low and dry with its own door; divider unhooks for meat"),
    "gulp": dict(name="GULP", kind="d", n=3.0,
                 tagline="Big front stretch shove-it pocket over the aft face + side zip",
                 access="roll-top + 450 mm straight #10 zip in the right side, z 150-600; 9 L stretch pocket",
                 pitch="Stuff a wet layer, a bow cam or a game bag in the giant stretch pocket"),
    "maw": dict(name="MAW", kind="box", dome_h=0.0,
                tagline="Clamshell duffel hauler: aft face drops open, closed top, no roll-top",
                access="#10 zip up both aft corners and across the top: the whole aft face opens like a duffel",
                pitch="Open it like a duffel on the ground: everything in view, IM straps reachable"),
    "cairn": dict(name="CAIRN", kind="d", n=3.5,
                  tagline="Roll-top with an integrated 6 L lid that converts to a summit pack",
                  access="roll-top + 450 mm straight #10 zip in the left side; lid 600 mm zip",
                  pitch="The lid comes off with straps as a summit / stalk pack"),
    "wisp": dict(name="WISP", kind="d", n=3.0, d_bot=180.0,
                 tagline="Minimalist ultralight: roll-top only, no lid, no zip, no body pockets",
                 access="roll-top only (A2: armpit-deep to reach IM1)",
                 pitch="The lightest and quickest to sew; everything through the top"),
    "mantle": dict(name="MANTLE", kind="box",
                   tagline="Expedition hauler: box body with two full-height side compression wings",
                   access="roll-top + 520 mm straight centre #10 zip (as SLAB)",
                   pitch="Wings wrap tripod, pads or antlers to the sides and squeeze small loads"),
}
NUM = {"spire": 6, "cradle": 7, "duo": 8, "gulp": 9, "maw": 10, "cairn": 11, "wisp": 12, "mantle": 13}

INTERFACE_CHANGES = {
    "spire": "none (B-01 2.5 in narrower at the bottom: 252 mm; hinge eyes x +/-115 still inside it)",
    "cradle": "B-01 becomes the harness back and runs to z 1175; B-22 guy tabs move to the wing aft edges at z 752",
    "duo": "none",
    "gulp": "none",
    "maw": "no roll-top: collar, hem, HDPE and the ROLL buckles go (-48.5 g common); B-20 ladder top on B-01 (z_c 790)",
    "cairn": "lid rear straps to the frame-side hem (as the current optional lid); B-22 unchanged",
    "wisp": "none",
    "mantle": "wing roots sewn in the B-01 | gusset seams; wings run outside W1-W3, wraps pass over them",
}

JUDGED_WIDE = {   # access, durability / quiet, look (1-5); reasons in analysis/bag_alternatives.md section 6
    "spire": {"access": 3.0, "durability": 4.0, "look": 4.5},
    "cradle": {"access": 4.0, "durability": 3.0, "look": 3.5},
    "duo": {"access": 4.0, "durability": 3.5, "look": 4.0},
    "gulp": {"access": 4.0, "durability": 3.0, "look": 4.0},
    "maw": {"access": 5.0, "durability": 2.0, "look": 3.0},
    "cairn": {"access": 3.5, "durability": 4.0, "look": 4.0},
    "wisp": {"access": 1.5, "durability": 4.5, "look": 4.0},
    "mantle": {"access": 3.5, "durability": 4.0, "look": 3.5},
}
BC.JUDGED.update(JUDGED_WIDE)


# ============================================================================ helpers
def vseam(name, L, sag=0.0, *tags):
    """A seam of length L (and sagitta sag, mm) that has no partner piece in this study (flat-work, slit zips)."""
    if sag > 0:
        R = (L ** 2 / (8 * sag) + sag / 2) if sag < L / 2 else L / 2
        th = L / R
        t = np.linspace(-th / 2, th / 2, 60)
        pts = [(R * math.sin(a), R * math.cos(a) - R * math.cos(th / 2)) for a in t]
    else:
        pts = [(0.0, 0.0), (L / 2, 0.0), (L, 0.0)]
    p = Piece.from_edges(name, [("e", pts), ("c", [pts[-1], (pts[-1][0], -5.0), (pts[0][0], -5.0), pts[0]])],
                         seam_allowance_mm=0.0)
    return (Seam(p.edge("e"), p.edge("e"), name=name), set(tags))


def slit_zip(b: Build, name, L, z, path3d, curved_sag=0.0, storm=True):
    """A zip set into a slit cut in a panel: both tapes sewn (2 x L), a 30 mm storm strip, two bartacks."""
    b.zips.append({"name": name, "length_mm": float(L), "corners": 0, "z": z, "where": "slit"})
    b.seams.append(vseam(f"{name}: tape 1", L, curved_sag, "zip"))
    b.seams.append(vseam(f"{name}: tape 2", L, curved_sag, "zip"))
    if storm:
        st = rect_panel(f"{name} storm strip", 30.0, L + 40, 0.0, seam_allowance_mm=SA_FLAT,
                        material_id="cordura_330d_nylon66", piece_id="B-08")
        b.pieces.append((st, "flat"))
        b.seams.append(vseam(f"{name} storm strip", L + 40, 0.0, "flat"))
    b.extra.setdefault("zip3d", []).append(np.asarray(path3d))
    b.extra["bartacks"] = b.extra.get("bartacks", 0) + 2


def add_hw(b: Build, name, g, n_tacks=1):
    b.extra.setdefault("hardware", []).append((name, float(g)))
    b.extra["bartacks"] = b.extra.get("bartacks", 0) + n_tacks


def accents_common(b: Build, c: Concept, per, kick="chevron"):
    """Camo placed where the leaders put wear panels: a kick plate on the bottom wear line and the roll-top hem band."""
    w = 2 * BC.A_BOT if c.kind == "box" else 2 * c.a_bot
    d0 = float(c.depth([Z0])[0])
    if kick == "chevron":
        ps = [_chevron("kick plate, aft (camo)", w, 70, 140, "SH-01a"), _chevron("kick plate, side (camo)", d0, 70, 70,
                                                                                 "SH-01b", qty=2)]
    else:
        ps = [_accent_rect("kick band (camo)", w + 2 * d0, 80, "SH-01")]
    if c.dome_h > 0:
        ps.append(_accent_rect("roll-top hem band (camo)", min(per, COLLAR_TOP), 30, "SH-03"))
    for p in ps:
        b.pieces.append((p, "accent"))
        b.appliques.append(p)


# ============================================================================ bodies
def d_body(c: Concept, spacing=14.0):
    """D-section body: flat B-01 + ONE developed lower wrap (z 35 -> 631.2) + shoulder band + D bottom + collar."""
    S = BC.WrapSurface(c)
    US = BC.US
    lo = [("bottom", _line((0, Z0), (US, Z0))), ("left_frame", _line((US, Z0), (US, Z_SH))),
          ("shoulder", _line((US, Z_SH), (0, Z_SH))), ("right_frame", _line((0, Z_SH), (0, Z0)))]
    top = [("shoulder", _line((0, Z_SH), (US, Z_SH))), ("left_frame", _line((US, Z_SH), (US, c.z_c))),
           ("top", _line((US, c.z_c), (0, c.z_c))), ("right_frame", _line((0, c.z_c), (0, Z_SH)))]
    p_lo, f_lo = BC.develop(S, lo, spacing, name="wrap panel (one piece, z 35-631)", seam_allowance_mm=SA_BODY,
                            material_id="cordura_330d_nylon66", piece_id="W-02")
    p_top, f_top = BC.develop(S, top, spacing, name="wrap shoulder band", seam_allowance_mm=SA_BODY,
                              material_id="cordura_330d_nylon66", piece_id="W-02c")
    B1 = frame_panel(c)
    BOT = BC.d_bottom(c)
    pieces = [(B1, "shell"), (p_lo, "shell"), (p_top, "shell"), (BOT, "shell")]
    seams = [
        _seam(B1.edge("right"), [p_lo.edge("right_frame").reversed(), p_top.edge("right_frame").reversed()],
              "B-01 | wrap R", "bound"),
        _seam(B1.edge("left").reversed(), [p_lo.edge("left_frame"), p_top.edge("left_frame")], "B-01 | wrap L", "bound"),
        _seam(p_top.edge("shoulder"), p_lo.edge("shoulder").reversed(), "shoulder seam (ring, z 631.2)", "bound"),
        _seam(B1.edge("bottom"), BOT.edge("frame"), "bottom | B-01", "ring", "bound"),
        _seam(p_lo.edge("bottom"), BOT.edge("aft").reversed(), "bottom (D) | wrap", "bound"),
    ]
    b = Build(c, pieces, seams, [], {"kind": "boxed", "n": 8}, [], strain={"W-02": f_lo.strain_stats(),
                                                                           "W-02c": f_top.strain_stats()},
              extra={"surface": S, "fm": f_lo})
    tops = [B1.edge("top"), p_top.edge("top")]
    per = _add_collar(b, c, tops)
    b.pieces.append((boxed_swell(), "swell"))
    return b, per


def _add_collar(b, c, top_edges):
    col0, hem, hd, per = collar_set(c)
    if c.z_c < BC.LADDER_TOP - 15.0:
        colf, col = frame_collar(c, col0, per)
        b.pieces += [(colf, "collar"), (col, "collar"), (hem, "collar"), (hd, "collar")]
        b.seams += [_seam(top_edges, [colf.edge("bottom"), col.edge("bottom")], "collar | body tops (ring)", "ring",
                          "bound"),
                    _seam(colf.edge("right"), col.edge("left").reversed(), "collar frame side | collar R", "bound"),
                    _seam(colf.edge("left"), col.edge("right").reversed(), "collar frame side | collar L", "bound"),
                    _seam(hem.edge("bottom"), [colf.edge("top"), col.edge("top")], "hem | collar top (ring)", "ring"),
                    _seam(hem.edge("left"), hem.edge("right").reversed(), "hem back seam")]
    else:
        b.pieces += [(col0, "collar"), (hem, "collar"), (hd, "collar")]
        b.seams += BC._collar_seams(top_edges, col0, hem)
    b.extra["collar_perimeter_mm"] = per
    return per


def box_body(c: Concept, closed=False):
    B1 = frame_panel(c)
    G = BC.gusset(c)
    BOT = BC.box_bottom(c)
    (F,) = BC.front_face(c)
    pieces = [(B1, "shell"), (G, "shell"), (BOT, "shell"), (F, "shell")]
    seams = [
        _seam(B1.edge("right"), G.edge("frame").reversed(), "B-01 | gusset R", "bound"),
        _seam(B1.edge("left").reversed(), G.edge("frame").reversed(), "B-01 | gusset L", "bound"),
        _seam(F.edge("right"), G.edge("aft"), "aft face | gusset R", "bound"),
        _seam(F.edge("left").reversed(), G.edge("aft"), "aft face | gusset L", "bound"),
        _seam(B1.edge("bottom"), BOT.edge("bottom"), "bottom | B-01", "ring", "bound"),
        _seam(F.edge("bottom"), BOT.edge("top").reversed(), "bottom | aft face", "bound"),
        _seam(G.edge("bottom"), BOT.edge("right"), "bottom | gusset R", "bound"),
        _seam(G.edge("bottom"), BOT.edge("left").reversed(), "bottom | gusset L", "bound"),
    ]
    b = Build(c, pieces, seams, [], {"kind": "boxed", "n": 8}, [], extra={})
    tops = [B1.edge("top"), G.edge("top"), F.edge("top"), G.edge("top")]
    if closed:
        a, d = float(c.a([c.z_c])[0]), float(c.depth([c.z_c])[0])
        T = rect_panel("top panel", 2 * a, d, 0.0, seam_allowance_mm=SA_BODY, material_id="cordura_500d_nylon66",
                       piece_id="B-04")
        b.pieces.append((T, "shell"))
        b.seams.append(_seam([B1.edge("top"), G.edge("top")], [T.edge("bottom"), T.edge("right")],
                             "top | B-01 + gusset R", "ring", "bound"))
        b.seams.append(_seam(G.edge("top"), T.edge("left"), "top | gusset L", "bound"))
        per = 0.0
    else:
        per = _add_collar(b, c, tops)
    b.pieces.append((boxed_swell(), "swell"))
    return b, per


def _wrap_path(S, q0, q1, z0, z1, n=80):
    return S(np.column_stack([np.linspace(q0, q1, n) * BC.US, np.linspace(z0, z1, n)]))


def _flat_len_sag(fm, uv):
    P = fm.map_uv(np.asarray(uv))
    L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    sag, _ = BC.edge_shape(P)
    return L, sag


# ============================================================================ concept builders
def build_spire(c):
    b, per = d_body(c)
    S = b.extra["surface"]
    path = _wrap_path(S, 0.5, 0.5, 120, 560)
    slit_zip(b, "centre zip", float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()), (120, 560), path)
    flap = _accent_rect("zip storm flap (camo)", 40, 480, "SH-02")
    b.pieces.append((flap, "accent"))
    b.appliques.append(flap)
    accents_common(b, c, per, kick="band")
    return b


def build_duo(c):
    b, per = d_body(c)
    S, fm = b.extra["surface"], b.extra["fm"]
    uv = np.column_stack([np.linspace(0.15, 0.85, 80) * BC.US, np.full(80, 330.0)])
    L, sag = _flat_len_sag(fm, uv)
    slit_zip(b, "lower-zone zip", L, (330, 330), S(uv), curved_sag=sag)
    # removable divider: the D section at z 330 in 100D, sewn to B-01 across the frame face, hooked at 3 tabs
    a, d = float(c.a([330])[0]), float(c.depth([330])[0])
    th = np.linspace(0, np.pi, 120)
    x = a * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / c.n)
    y = d * np.abs(np.sin(th)) ** (2 / c.n)
    div = Piece.from_edges("removable divider", [("frame", [(-a, 0.0), (a, 0.0)]),
                                                 ("aft", [(float(u), float(v)) for u, v in zip(x, y)])],
                           seam_allowance_mm=SA_FLAT, material_id="robic_100d_ripstop", piece_id="B-09d")
    b.pieces.append((div, "flat"))
    b.seams.append(_seam(div.edge("frame"), div.edge("frame"), "divider | B-01 (sewn)", "flat"))
    b.seams.append(_seam(div.edge("aft"), div.edge("aft"), "divider edge binding", "flat"))
    for i in range(3):
        add_hw(b, f"divider tab {i + 1}: 25 mm webbing 0.12 m + G-hook", 0.12 * WEB25 + G_HOOK_G, 2)
    accents_common(b, c, per)
    lip = _accent_rect("lower-zone zip garage (camo)", 40, L + 40, "SH-02")
    b.pieces.append((lip, "accent"))
    b.appliques.append(lip)
    return b


def build_gulp(c):
    b, per = d_body(c)
    S, fm = b.extra["surface"], b.extra["fm"]
    # stretch pocket over the aft face: q 0.18-0.82, z 80 -> 650 (on the lower wrap + 19 mm onto the shoulder band)
    side_r = np.column_stack([np.full(40, 0.18 * BC.US), np.linspace(80, 630, 40)])
    side_l = np.column_stack([np.full(40, 0.82 * BC.US), np.linspace(80, 630, 40)])
    bot = np.column_stack([np.linspace(0.18, 0.82, 60) * BC.US, np.full(60, 80.0)])
    Ls, sag_s = _flat_len_sag(fm, side_r)
    Lb, sag_b = _flat_len_sag(fm, bot)
    w_mouth = _flat_len_sag(fm, np.column_stack([np.linspace(0.18, 0.82, 60) * BC.US, np.full(60, 630.0)]))[0]
    pk = tapered_panel("stretch shove-it pocket", Lb * 0.92, w_mouth * 0.92, Ls * 1.0, seam_allowance_mm=SA_FLAT,
                       material_id="poly_spandex_stretch_woven_printable", piece_id="D-01g")
    b.pieces.append((pk, "flat"))
    b.seams += [vseam("pocket side R | wrap", Ls, sag_s, "flat"), vseam("pocket side L | wrap", Ls, sag_s, "flat"),
                vseam("pocket bottom | wrap", Lb, sag_b, "flat")]
    mouth = _accent_rect("pocket mouth binding (camo)", 32, w_mouth + 20, "SH-02")
    b.pieces.append((mouth, "accent"))
    b.appliques.append(mouth)
    b.seams.append(vseam("binding | pocket mouth", w_mouth, 0.0, "flat"))
    path = _wrap_path(S, 0.03, 0.03, 150, 600)
    slit_zip(b, "right side zip", float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()), (150, 600), path)
    accents_common(b, c, per, kick="band")
    b.extra["pocket_L"] = 9.0     # ASSUMPTION: stretch pocket loft 25 mm mean x pocket area (not counted)
    return b


def build_cairn(c):
    b, per = d_body(c)
    S = b.extra["surface"]
    path = _wrap_path(S, 0.97, 0.97, 150, 600)
    slit_zip(b, "left side zip", float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum()), (150, 600), path)
    # integrated lid / summit pack: two super-ellipse panels 400 x 290 (n 3), 80 mm gusset, 600 mm zip
    a, bb = 200.0, 145.0
    th = np.linspace(0, 2 * np.pi, 160, endpoint=False)
    px = a * np.sign(np.cos(th)) * np.abs(np.cos(th)) ** (2 / 3)
    py = bb * np.sign(np.sin(th)) * np.abs(np.sin(th)) ** (2 / 3)
    outline = [(float(x), float(y)) for x, y in zip(px, py)]
    per_lid = float(np.linalg.norm(np.diff(np.vstack([outline, outline[:1]]), axis=0), axis=1).sum())
    top = Piece.from_edges("lid top (camo)", [("rim", outline[:80] + [outline[80]]), ("rim2", outline[80:] + [outline[0]])],
                           seam_allowance_mm=SA_FLAT, material_id="polyester_ht_630d_printable", piece_id="L-11")
    bot = Piece.from_edges("lid underside", [("rim", outline[:80] + [outline[80]]), ("rim2", outline[80:] + [outline[0]])],
                           seam_allowance_mm=SA_FLAT, material_id="cordura_330d_nylon66", piece_id="L-12")
    gus = rect_panel("lid gusset", per_lid, 80.0, 0.0, seam_allowance_mm=SA_FLAT, material_id="cordura_330d_nylon66",
                     piece_id="L-13")
    b.pieces += [(top, "lid"), (bot, "lid"), (gus, "lid")]
    b.seams += [_seam([top.edge("rim"), top.edge("rim2")], gus.edge("top"), "lid top | gusset (zip 600 mm in it)", "zip"),
                _seam([bot.edge("rim"), bot.edge("rim2")], gus.edge("bottom"), "lid underside | gusset"),
                _seam(gus.edge("left"), gus.edge("right").reversed(), "lid gusset end")]
    b.zips.append({"name": "lid zip (#8 class booked as #10)", "length_mm": 600.0, "corners": 2, "z": (0, 0),
                   "where": "lid top | gusset"})
    add_hw(b, "summit harness: 2 x 25 mm webbing 0.7 m + 2 ladder locks", 2 * (0.7 * WEB25 + LADDER), 4)
    add_hw(b, "lid rear straps + 2 front magnetic clips (current lid rule)", 2 * 0.15 * WEB25 + 2 * 15.0, 4)
    b.appliques.append(top)
    accents_common(b, c, per, kick="band")
    b.extra["lid_L"] = round(math.pi * a * bb * 0.88 * 80 / 1e6 * 1.0, 1)
    return b


def build_wisp(c):
    b, per = d_body(c)
    accents_common(b, c, per, kick="band")
    return b


def build_mantle(c):
    b, per = box_body(c)
    # centre zip as SLAB: split the face
    b.pieces = [(p, g) for p, g in b.pieces if p.piece_id != "B-02"]
    FR, FL = BC.front_face(c, split_x=0.0)
    b.pieces += [(FR, "shell"), (FL, "shell")]
    b.seams = [s for s in b.seams if not s[0].name.startswith(("aft face", "bottom | aft"))]
    G = next(p for p, _ in b.pieces if p.piece_id == "B-03")
    BOT = next(p for p, _ in b.pieces if p.piece_id == "B-05")
    b.seams += [_seam(FR.edge("outer"), G.edge("aft"), "aft face R | gusset R", "bound"),
                _seam(FL.edge("outer").reversed(), G.edge("aft"), "aft face L | gusset L", "bound"),
                _seam([FL.edge("bottom"), FR.edge("bottom")], BOT.edge("top").reversed(), "bottom | aft face", "bound"),
                _seam(FR.edge("centre"), FL.edge("centre").reversed(), "centre seam (zip z 140-660)", "zip", "bound")]
    b.zips.append({"name": "centre zip", "length_mm": 520.0, "corners": 0, "z": (140, 660), "where": "centre seam"})
    zz = np.linspace(140, 660, 60)
    b.extra["zip3d"] = [np.column_stack([np.zeros(60), c.y_front(zz), zz])]
    # wings: trapezoid 230 -> 250 wide x 700 tall (z 80-780), 330D, bound edges, 3 G-hook straps each
    for side in ("R", "L"):
        w = tapered_panel(f"side compression wing {side}", 230, 250, 700, seam_allowance_mm=SA_FLAT,
                          material_id="cordura_330d_nylon66", piece_id=f"M-0{1 if side == 'R' else 2}")
        b.pieces.append((w, "wing"))
        b.seams.append(_seam(w.edge("left"), w.edge("left"), f"wing {side} root | B-01 gusset seam", "bound"))
        bind = _accent_rect(f"wing {side} edge binding (camo)", 32, 700 + 250 + 230, "SH-06")
        b.pieces.append((bind, "accent"))
        b.appliques.append(bind)
        for i in range(3):
            add_hw(b, f"wing {side} strap {i + 1}: 25 mm 0.30 m + G-hook + ladder lock", 0.30 * WEB25 + G_HOOK_G + LADDER, 2)
    accents_common(b, c, per)
    flap = _accent_rect("zip storm flap (camo)", 50, 560, "SH-02")
    b.pieces.append((flap, "accent"))
    b.appliques.append(flap)
    return b


def build_maw(c):
    b, per = box_body(c, closed=True)
    a_t, zc = float(c.a([c.z_c])[0]), c.z_c
    L = 2 * (zc - 120.0) + 2 * a_t - 2 * 40 * (2 - math.pi / 2)    # 2 corner radii R40 at the top corners
    b.seams = [s if not s[0].name.startswith("aft face | gusset") else (s[0], {"zip", "bound"}) for s in b.seams]
    b.seams.append(vseam("top | aft face (zip across the top, R40 corners)", 2 * a_t, 12.0, "zip", "bound"))
    b.zips.append({"name": "clamshell zip", "length_mm": L, "corners": 2, "z": (120, zc), "where": "corners + top"})
    zz = np.linspace(120, zc, 60)
    xs = np.linspace(-a_t, a_t, 60)
    paths = [np.column_stack([sg * c.a(zz), c.y_front(zz), zz]) for sg in (1, -1)]
    paths.append(np.column_stack([xs, np.full(60, float(c.y_front([zc])[0])), np.full(60, zc)]))
    b.extra["zip3d"] = paths
    add_hw(b, "4 haul-wrap keepers moved to the gussets (none new)", 0.0, 0)
    b.extra["common_delta_g"] = -ROLLTOP_HW_G
    accents_common(b, c, per)
    cap = _accent_rect("top panel corner caps (camo)", 120, 90, "SH-03", qty=2)
    b.pieces.append((cap, "accent"))
    b.appliques.append(cap)
    return b


# ---------------------------------------------------------------------------- CRADLE (custom geometry)
CRADLE_D = [250.0, 290.0, 300.0, 300.0]     # drybag diameters bottom -> top (ASSUMPTION), <= 302 mm depth cap
CRADLE_L = 330.0                            # drybag body length (ASSUMPTION): 330 + ~60 mm rolled end <= 394 mm
CRADLE_GAP = 5.0                            # mm between stacked drybags (ASSUMPTION)


class Cradle(Concept):
    """Four horizontal roll-top drybags stacked in a harness. Volume = sum of drybag bodies (the rolled ends are
    closure, as R-01). Frame-side panel B-01 = harness back."""

    def stack(self):
        z = Z0
        out = []
        for D in CRADLE_D:
            zc = z + D / 2
            out.append((D, zc))
            z += D + CRADLE_GAP
        return out

    def volume_L(self, z_c=None, upto=None):
        return sum(math.pi / 4 * D ** 2 * CRADLE_L for D, _ in self.stack()) / 1e6

    def solve(self):
        D, zc = self.stack()[-1]
        self.z_c = round(zc + D / 2, 1)
        return self.z_c

    @property
    def z_fill(self):
        return self.z_c

    def depth(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        out = np.zeros_like(z)
        for D, zc in self.stack():
            m = np.abs(z - zc) <= D / 2
            out[m] = D
        return np.maximum(out, 1.0)

    def cg(self, n=0, M=0):
        V = Sy = Sz = 0.0
        for D, zc in self.stack():
            v = math.pi / 4 * D ** 2
            V += v
            Sy += v * (float(y_frame([zc])[0]) + D / 2)
            Sz += v * zc
        return Sy / V, Sz / V


def make_cradle():
    c = Cradle(key="cradle", **{k: v for k, v in WIDE["cradle"].items() if k != "pitch"})
    c.solve()
    return c


def build_cradle(c):
    B1 = frame_panel(c, name="harness back = frame-side panel (flat, Z-fold setback)")
    H = c.z_c - Z0
    wings = tapered_panel("harness side wing", 130, 130, H - 60, seam_allowance_mm=SA_BODY,
                          material_id="cordura_330d_nylon66", quantity=2, piece_id="C-02")
    cup = rect_panel("harness bottom cup", 2 * BC.A_BOT, CRADLE_D[0] * 0.6, 0.0, seam_allowance_mm=SA_BODY,
                     material_id="cordura_500d_nylon66", piece_id="C-03")
    pieces = [(B1, "shell"), (wings, "shell"), (cup, "shell")]
    seams = [_seam(B1.edge("right"), B1.edge("right"), "wing R | B-01 edge", "bound"),
             _seam(B1.edge("left"), B1.edge("left"), "wing L | B-01 edge", "bound"),
             _seam(cup.edge("bottom"), B1.edge("bottom"), "cup | B-01 bottom", "bound"),
             _seam([cup.edge("left"), cup.edge("right")], [cup.edge("left"), cup.edge("right")], "cup sides | wings")]
    b = Build(c, pieces, seams, [], {"kind": "boxed", "n": 8}, [], extra={})
    for i, D in enumerate(CRADLE_D):
        circ = math.pi * D
        tube = rect_panel(f"drybag {i + 1} tube (D {D:.0f})", circ, CRADLE_L + 175.0, 0.0, seam_allowance_mm=SA_FLAT,
                          material_id="robic_100d_ripstop", piece_id=f"C-1{i}")
        th = np.linspace(0, 2 * np.pi, 120, endpoint=False)
        disk = Piece.from_edges(f"drybag {i + 1} end", [("rim", [(D / 2 * math.cos(t), D / 2 * math.sin(t)) for t in th[:60]]
                                                         + [(D / 2 * math.cos(th[60]), D / 2 * math.sin(th[60]))]),
                                                        ("rim2", [(D / 2 * math.cos(t), D / 2 * math.sin(t)) for t in th[60:]]
                                                         + [(D / 2, 0.0)])],
                                seam_allowance_mm=SA_FLAT, material_id="robic_100d_ripstop", piece_id=f"C-2{i}")
        hem = rect_panel(f"drybag {i + 1} roll hem (camo)", circ, 30.0, 0.0, seam_allowance_mm=SA_FLAT,
                         material_id="polyester_ht_630d_printable", piece_id=f"C-3{i}")
        hd = rect_panel(f"drybag {i + 1} HDPE strip", circ / 2 - 30, 20.0, 0.0, seam_allowance_mm=0.0,
                        material_id="hdpe_sheet", quantity=2, piece_id=f"C-4{i}")
        b.pieces += [(tube, "drybags"), (disk, "drybags"), (hem, "accent"), (hd, "drybags")]
        b.appliques.append(hem)
        b.seams += [_seam(tube.edge("left"), tube.edge("right").reversed(), f"drybag {i + 1} long seam"),
                    _seam(tube.edge("bottom"), [disk.edge("rim"), disk.edge("rim2")], f"drybag {i + 1} end (ring)",
                          "ring"),
                    _seam(tube.edge("top"), hem.edge("bottom"), f"drybag {i + 1} hem", "ring")]
        add_hw(b, f"drybag {i + 1} roll clip: 25 mm SR + 0.3 m webbing", SR25 + 0.3 * WEB25, 2)
    add_hw(b, "4th cinch strap round the top drybag: 25 mm 1.1 m + G-hook + ladder lock", 1.1 * WEB25 + G_HOOK_G + LADDER, 2)
    b.extra["common_delta_g"] = -ROLLTOP_HW_G       # no main roll-top: the drybags carry their own clips (booked above)
    kp = _accent_rect("harness cup kick band (camo)", 2 * BC.A_BOT + 2 * 130, 80, "SH-01")
    b.pieces.append((kp, "accent"))
    b.appliques.append(kp)
    b.pieces.append((boxed_swell(), "swell"))
    b.extra["zip3d"] = []
    return b


BUILDERS = {"spire": build_spire, "duo": build_duo, "gulp": build_gulp, "cairn": build_cairn, "wisp": build_wisp,
            "mantle": build_mantle, "maw": build_maw, "cradle": build_cradle}


def make(key) -> Concept:
    if key == "cradle":
        return make_cradle()
    kw = {k: v for k, v in WIDE[key].items() if k != "pitch"}
    c = Concept(key=key, **kw)
    c.solve()
    return c


def build(c) -> Build:
    return BUILDERS[c.key](c)


def volumes(c) -> dict:
    if c.key != "cradle":
        v = BC.volumes(c)
    else:
        yc, zc = c.cg()
        V = c.volume_L()
        v = {"volume_L": round(V, 2), "volume_cu_in": round(V * 1e6 / L_CUIN / 1e3, 0), "body_to_collar_L": round(V, 2),
             "z_collar": c.z_c, "z_fill": c.z_c, "fill_height_mm": round(c.z_c - Z0, 1),
             "fill_height_in": round((c.z_c - Z0) / IN, 1), "max_depth_mm": max(CRADLE_D),
             "max_depth_in": round(max(CRADLE_D) / IN, 2), "depth_top_mm": CRADLE_D[-1],
             "width_max_mm": round(2 * A_MAX, 1), "width_max_in": round(2 * A_MAX / IN, 2), "cg_y": round(yc, 1),
             "cg_z": round(zc, 1), "section_k": round(math.pi / 4, 4)}
    return v


def all_wide():
    return [make(k) for k in WIDE]


if __name__ == "__main__":
    for c in all_wide():
        b = build(c)
        m = BC.metrics(b)
        v = volumes(c)
        print(f"{c.name:7s} {v['volume_L']:6.2f} L fill {v['fill_height_in']:5.1f} in depth {v['max_depth_in']:5.2f} "
              f"CG {v['cg_y']:.0f}/{v['cg_z']:.0f} pcs {m['cut_pieces']} seams {m['seam_length_m']} curved "
              f"{m['curved_seams']} zips {m['zip_length_m']} h {m['hours_total']} g {m['mass_g']['total']} "
              f"err {m['seam_check_max_err_mm']} strain {({k: round(s['p99_pct'], 2) for k, s in m['strain'].items()})}")
