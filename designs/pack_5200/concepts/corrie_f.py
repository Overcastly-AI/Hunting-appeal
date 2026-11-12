"""BL-011: CORRIE F, the merged bag (pack-designer, 2026-11-11).

    python designs/pack_5200/concepts/corrie_f.py                    # weight table (belt M) + build metrics
    python designs/pack_5200/concepts/corrie_f.py --json             # also write concepts/corrie_f_result.json

One bag concept from the bag competition (BL-002 verdict) and the adopted diets, on one ledger basis:

* **Shell** S15 (BL-009, adopted 2026-11-11): full-width 394 mm box, width taper to 360 mm at the collar seam, depth
  160 / 205 / 195 mm, collar seam z 745. Plus ONE BL-011 change for R-28 head clearance at the 23 in setting: the
  frame-side face above the shoulder crease steps aft by ``TOP_SETBACK_MM`` (a second Z-fold in B-01, z 631 -> 745),
  with the aft face unchanged, so the top of the bag tapers in depth (195 -> 195 - setback at the collar seam).
  Sized by cloth sim (``corrie_f_sim/``, section 5 of ``analysis/corrie_f_body.md``).
* **Fabrics** team B (FELL): ULTRAGrid body, 70D collar, ULTRA 200X floor, each with its gate from
  ``analysis/fabric_swap_evidence.md`` (``FABRIC_GATES``). ``fabrics="today"`` books the same pieces in CORRIE B.2's
  fabrics, in case the owner declines the swaps.
* **Straps** BL-003 REC (lighten in place at 25 mm, sewn loops on the IM eyes, wings deleted: W1-W3 are the only
  external set) through ``strap_arch.architectures()['rec']``; **attachment** BL-004 REC through
  ``attach_diet.mass_changes('REC')``; **hardware** BL-010 fixes (wiregate carabiners at the IM3 bag hooks, the IM3
  meat free end and B-24; rated G-hooks and heavy ladder locks on W1-W3; heavy ladder locks on the guys) priced from
  ``huntkit.gendesign.loadpath_check.hooks_table()`` and the records.
* **Doors**, two options to the same level: ``D1`` team C's full-face tailgate (floor-hinged lid, #10 zip legs in the
  aft corner seams, lid straps H1-H3 at the IM heights); ``D2`` team E's camo-blade door made for a square-corner box:
  a flat camo blade strip beside each aft corner seam carries the door zip, so panel line, camo break and zip are one
  line.
* **Access** team A's hip-reach pockets FP-L / FP-R (E-4, same part) on the gussets' lower front corners and the pole
  quiver (E-5); IMP-6 (the shoulder-strap phone pocket, a harness part, unchanged); the 2nd bottle in FP-R.
* **Add-ons** (outside base weight, BL-008 rule): scope pod (team B's glass pod, on the left gusset), top pouch (team B's lid pod), meat liner (team D's SWAP slab), float kit
  (B-24). The bottle holster IMP-3 is a belt part (ledger ``belt``), as-hunted. Tripod straps are dropped: W1-W3 are
  the only external strap set (owner, 2026-11-11) and carry the tripod (BL-010 S10).

Every mass is a ledger row (``huntkit.mass.ledger``, config ``corrie_b2_h1``) kept, removed or replaced; a replaced row
gets its mass from cut area x record gsm (``bag_concepts.piece_mass_g``), a record, or a named ASSUMPTION. No total is
typed. Ledger systems are BL-001's; the ``cfg`` tag (base / as_hunted / meat_trip) is BL-008's rule.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACK = ROOT / "designs" / "pack_5200"
for _p in (str(ROOT), str(HERE), str(PACK), str(PACK / "bag_comp")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
import corrie as CO  # noqa: E402
import shell_sweep as SS  # noqa: E402
from bag_concepts import SA_BODY, SA_FLAT, _seam  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import Piece, rect_panel  # noqa: E402

NAME = "CORRIE F"
LB, OZ, IN = 453.592, 28.3495, 25.4
CONFIG, SIZES = "corrie_b2_h1", tuple(CO.BELT_SIZES)
CFGS = ("base", "as_hunted", "meat_trip")
DOORS = ("D1", "D2")
DOOR_DEFAULT = "D2"          # DECISION (doc section 3): the headline numbers use D2; D1 is complete for the owner's pick
_YF0 = BC.y_frame            # the shared frame face (stay line + gap + 30 mm head setback), captured before any patch

# ---------------------------------------------------------------------------------------------------------- fabrics
UG = "ultragrid_210d_uhmwpe_ripstop"     # 132 gsm
R70 = "nylon_ripstop_70d"                # 92 gsm
U200 = "challenge_ultra_200"             # 133 gsm (ULTRA 200X)
CAMO = "polyester_ht_630d_printable"     # 290 gsm, owner camo accents (O-6: wear zones stay 630D)
C330, C500, ROBIC = "cordura_330d_nylon66", "cordura_500d_nylon66", "robic_100d_ripstop"
MESH = "power_mesh_nylon_spandex"
FABRICS = {   # role -> (B map, today's map)
    "body": (UG, C330),           # gussets, aft face, door / lid, hinge band, roll-top hem
    "collar": (R70, ROBIC),       # B-06 roll-top collar (aft three quarters)
    "floor": (U200, C500),        # B-05
}
FABRIC_GATES = {   # analysis/fabric_swap_evidence.md, written next to each swap (ticket)
    "body": "O-4 ULTRAGrid 210D: proceed after the owner sees a swatch (visible grid); abrasion gate met (Taber 1100 "
            "vs 330D 800). Lighter, not tougher: ~55-60 % of 500D abrasion",
    "collar": "O-3 70D ripstop: proceed (tear 51.6 / 37.4 N >= 35 N); weigh the stock before cutting",
    "floor": "O-5 ULTRA 200X: proceed after PT-3 plus a 50 mm strip test (strip >= 36.8 N/mm keeps SF 2.31; "
             ">= 23.9 N/mm for SF 1.5); film laminate, quietness 2/5 when set down",
}


def fab(role: str, fabrics: str = "B") -> str:
    return FABRICS[role][0 if fabrics == "B" else 1]


def _gsm(mid: str) -> float:
    return float(MAT.load(mid).require("areal_density_gsm"))


def _rec(mid: str, key: str) -> float:
    return float(MAT.load(mid).require(key))


WEB25 = _rec("poly_webbing_25mm", "mass_g_m")
LADDER_G = _rec("ladder_lock_25mm", "mass_g")
ZIP10_GM = _rec("coil_zipper_10", "mass_g_m")
CHAIN10 = _rec("coil_zipper_10", "chain_width_mm")
SHOCK_GM = _rec("shock_cord_3mm", "mass_g_m")
CORDLOCK_G = _rec("cord_lock_spring", "mass_g")
SLIDER10_G = BC.SLIDER_G           # 6 g ASSUMPTION (build_geometry rule)
CORD_PULL_G = CO.CORD_PULL_G       # 1.5 g ASSUMPTION
G_HOOK = CO.G_HOOK                 # 4 g ASSUMPTION (HAUL family; add-on straps only, never a load path)

# ---------------------------------------------------------------------------------------------------------- shell
S15 = SS.SHELLS["S15"]
# ---------------------------------------------------------------------------------------------------------- revisions
# rev 0 = BL-011 as released 2026-11-11 (30 mm top setback sized on the COARSE mesh; guys toggled round the bar ends at
# x +/-100; tripod held by W1/W2 only). rev 1 = BL-022 (doc section 13): setback re-sized on the FINE mesh, guys moved
# inboard to a bridle clear of the lifter lugs, a shock-cord tripod keeper on the right gusset. ``revision(0)`` gives
# rev 0 back exactly (tests).
REVS = {0: {"setback": 30.0, "guy_x": 100.0, "guy_bridle": False, "tripod_keeper": False},
        1: {"setback": 30.0, "guy_x": 52.0, "guy_bridle": True, "tripod_keeper": True}}
REVISION = 1
TOP_SETBACK_MM = REVS[REVISION]["setback"]   # DECISION (R-28, doc sections 5 / 13): sized by the corrie_f_sim R-28 runs
GUY_X = REVS[REVISION]["guy_x"]               # DECISION (BL-022 S6, doc section 13.3): guy bar-end centre, x +/- mm


@contextlib.contextmanager
def revision(n: int):
    """Temporarily switch the module to CORRIE F rev ``n`` (setback, guy x, rev-1 parts); restored after."""
    g = globals()
    old = (g["REVISION"], g["TOP_SETBACK_MM"], g["GUY_X"])
    g["REVISION"], g["TOP_SETBACK_MM"], g["GUY_X"] = n, REVS[n]["setback"], REVS[n]["guy_x"]
    try:
        yield REVS[n]
    finally:
        g["REVISION"], g["TOP_SETBACK_MM"], g["GUY_X"] = old


class ShellF(SS.Shell):
    """S15 with an optional second frame-face Z-fold: the frame face steps aft by ``setback`` from the shoulder crease
    (z 631.2) to the collar seam, the aft face stays where S15 has it, so the depth at the collar seam drops by the
    same amount (a top taper in depth). ``setback`` 0 is S15 exactly."""

    setback: float = 0.0

    def extra(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        zc = self.z_c if self.z_c else 1000.0
        return self.setback * np.clip((z - BC.Z_SH) / max(zc - BC.Z_SH, 1.0), 0.0, 1.0)

    def frame_y(self, z):
        return _YF0(z) + self.extra(z)

    def y_front(self, z):
        """S15's aft face, on the ORIGINAL frame face (so the setback does not move it)."""
        z = np.atleast_1d(np.asarray(z, float))
        p = self.p
        zc = self.z_c if self.z_c else 1000.0
        yf0, yfs, yfc = (float(_YF0([v])[0]) for v in (BC.Z0, BC.Z_SH, zc))
        y0, y1, y2 = yf0 + p.d_bot, yfs + p.d_sh, yfc + p.d_col
        low = y0 + (y1 - y0) * (z - BC.Z0) / (BC.Z_SH - BC.Z0)
        high = y1 + (y2 - y1) * np.clip((z - BC.Z_SH) / max(zc - BC.Z_SH, 1.0), 0, 1)
        return np.where(z <= BC.Z_SH, low, high)

    def depth(self, z):
        return self.y_front(z) - self.frame_y(z)


def make(setback: float | None = None) -> ShellF:
    c = ShellF(key="corrie", name=NAME, kind="box", d_bot=S15.d_bot, d_nom=S15.d_sh + BC.SETBACK, a_bot=S15.a_bot,
               tagline="S15 box, B fabrics, top setback, W1-W3 compression, two door options",
               access="roll-top + door (D1 tailgate / D2 camo-blade door)")
    c.p = S15
    c.z_c = float(S15.z_c)
    c.setback = TOP_SETBACK_MM if setback is None else float(setback)
    return c


@contextlib.contextmanager
def frame_face(c: ShellF):
    """bag_concepts builders (frame panel, gusset, profile, ring) read the module-level ``y_frame``: point it at this
    shell's frame face for the duration (restored after; nothing is edited)."""
    old = BC.y_frame
    BC.y_frame = c.frame_y
    try:
        yield c
    finally:
        BC.y_frame = old


def geometry(c: ShellF | None = None) -> dict:
    c = c or make()
    with frame_face(c):
        zs = np.linspace(BC.Z0, c.z_c, 200)
        cg = c.cg()
        v = c.volume_L()
        prof = c.profile()
    return {"z_c": float(c.z_c), "z_fill": float(c.z_fill), "fill_height_in": round((c.z_fill - BC.Z0) / IN, 1),
            "width_max_mm": round(2 * float(max(c.a(zs))), 1), "width_collar_mm": round(2 * float(c.a([c.z_c])[0]), 1),
            "depth_max_mm": round(float(max(c.depth(zs))), 1), "depth_collar_mm": round(float(c.depth([c.z_c])[0]), 1),
            "rule_L": round(v, 2), "rule_cg_y": round(float(cg[0]), 1), "rule_cg_z": round(float(cg[1]), 1),
            "setback_mm": c.setback, "profile": prof}


# ---------------------------------------------------------------------------------------------------------- doors
D1 = {"z_top": 650.0, "r": 60.0, "ease_mm": 6.0, "hoop_z": (190.0, 330.0, 520.0), "loop_in_mm": 15.0,
      "flap_w": 35.0}                       # team C TAILGATE (bag_comp/C/tailgate.py LID, HOOP_Z, LOOP_IN_MM, FLAP_W)
D2 = {"z_lo": 110.0, "z_hinge": 650.0, "r": 55.0, "blade_bot": 40.0, "blade_top": 25.0, "kick_h": 75.0}
# D2 DECISION: team E's door (CHERT: sill z 110, hinge z 650, R 55 corners, 75 mm kick strip) on S15's square corners.
# The blade is a FLAT camo strip on the aft face beside each corner seam, 40 mm wide at the floor to 25 mm at the collar
# seam (E's chamfer blade was 60 -> 32 mm across; a flat blade that wide would cost the door 40 mm of clear width, and
# the verdict asks for team A's door width, 294-334 mm at IM1-IM3).
STATIONS = {"IM1": BC.STATIONS["im1"], "IM2": BC.STATIONS["im2"], "IM3": BC.STATIONS["im3"]}


def blade_w(c, z):
    t = np.clip((np.asarray(z, float) - BC.Z0) / (c.z_c - BC.Z0), 0, 1)
    return D2["blade_bot"] + (D2["blade_top"] - D2["blade_bot"]) * t


def clear_width(c, door: str, z: float) -> float:
    """Clear opening width at height z, less the two #10 chains (record chain width), mm."""
    if door == "D1":
        return 2 * float(c.a([min(z, D1["z_top"] - D1["r"])])[0]) - 2 * CHAIN10
    if door == "D2":
        return 2 * (float(c.a([z])[0]) - float(blade_w(c, z))) - 2 * CHAIN10
    if door == "CORRIE":
        return CO.door_width(z) - 2 * CHAIN10
    raise KeyError(door)


def _poly_piece(name, pts, pid, mat, sa=SA_BODY, edge_names=None):
    pts = [tuple(map(float, p)) for p in pts]
    edges = [("outline", pts + [pts[0]])] if edge_names is None else edge_names
    return Piece.from_edges(name, edges, seam_allowance_mm=sa, material_id=mat, piece_id=pid)


def _face_xy(c):
    """Aft-face flat coords: zk (sorted kinks), s(z) unrolled, a(z)."""
    zk, s, a = BC.front_face_profile(c)
    S = lambda z: float(np.interp(z, zk, s))     # noqa: E731
    A = lambda z: float(np.interp(z, zk, a))     # noqa: E731
    return zk, S, A


def d2_pieces(c, fabrics="B"):
    """D2 aft face: blade U (camo: both blades + kick strip, one piece), door (body fabric), hinge band (body)."""
    zk, S, A = _face_xy(c)
    zl, zh, r = D2["z_lo"], D2["z_hinge"], D2["r"]
    zz = np.unique(np.r_[BC.Z0, zk, zl, zh, c.z_c])   # kinks only: every edge is piecewise straight (no false curve)
    inner = lambda z: A(z) - float(blade_w(c, z))     # noqa: E731
    # door outline (flat), CCW from the hinge-left point
    th = np.linspace(0, np.pi / 2, 14)
    legz = [z for z in zz[::-1] if zl + r < z <= zh] + [zl + r]
    legL = [(-inner(z), S(z)) for z in legz]
    xc = inner(zl + r)
    cornerL = [(-(xc - r + r * math.cos(t)), S(zl + r) - r * math.sin(t)) for t in th[1:]]
    cornerR = [((xc - r + r * math.cos(t)), S(zl + r) - r * math.sin(t)) for t in th[::-1][:-1]]
    legR = [(inner(z), S(z)) for z in legz[::-1]]
    zip_path = legL + cornerL + cornerR + legR
    door = Piece.from_edges("D2 door (whole aft face z 110-650, R 55 corners)",
                            [("zip", zip_path), ("hinge", [zip_path[-1], zip_path[0]])],
                            seam_allowance_mm={"default": BC.SA_ZIP, "hinge": SA_BODY}, material_id=fab("body", fabrics),
                            piece_id="B-02door")
    hz = [z for z in zz if z >= zh]
    band = Piece.from_edges("D2 hinge band (z 650 to the collar seam)",
                            [("bottom", [(-inner(zh), S(zh)), (inner(zh), S(zh))]),
                             ("right", [(inner(z), S(z)) for z in hz]),
                             ("top", [(inner(c.z_c), S(c.z_c)), (-inner(c.z_c), S(c.z_c))]),
                             ("left", [(-inner(z), S(z)) for z in hz[::-1]])],
                            seam_allowance_mm=SA_BODY, material_id=fab("body", fabrics), piece_id="B-02h")
    # blade U: outer edges at +/-a(z), inner edges: hinge-band sides above z 650, the door zip below, kick strip under
    outer_R = [(A(z), S(z)) for z in zz]
    top_R = [(A(c.z_c), S(c.z_c)), (inner(c.z_c), S(c.z_c))]
    inner_R_hi = [(inner(z), S(z)) for z in zz[::-1] if z >= zh]
    inner_L_hi = [(-inner(z), S(z)) for z in zz if z >= zh]
    u_inner = inner_R_hi + legR[::-1] + cornerR[::-1] + cornerL[::-1] + legL[::-1] + inner_L_hi
    top_L = [(-inner(c.z_c), S(c.z_c)), (-A(c.z_c), S(c.z_c))]
    outer_L = [(-A(z), S(z)) for z in zz[::-1]]
    blade = Piece.from_edges("D2 camo blade U (blades + 75 mm kick strip, one piece)",
                             [("bottom", [(-A(BC.Z0), 0.0), (A(BC.Z0), 0.0)]), ("outer_right", outer_R),
                              ("top_right", top_R), ("inner", u_inner), ("top_left", top_L), ("outer_left", outer_L)],
                             seam_allowance_mm={"default": SA_BODY, "inner": BC.SA_ZIP}, material_id=CAMO,
                             piece_id="B-02u")
    zip_len = float(np.sum(np.linalg.norm(np.diff(np.asarray(zip_path), axis=0), axis=1)))
    return {"door": door, "band": band, "blade": blade, "zip_mm": zip_len}


def d1_pieces(c, fabrics="B"):
    """D1 aft face: team C's lid (floor hinge, R 60 top corners, 3 mm ease a side) and hinge band with corner
    tongues, on this shell (tailgate.lid_face is concept-generic)."""
    import importlib
    TG = importlib.import_module("C.tailgate")
    lid, band, Lzip = TG.lid_face(c)
    lid.material_id = band.material_id = fab("body", fabrics)
    return {"lid": lid, "band": band, "zip_mm": float(Lzip), "TG": TG}


# ---------------------------------------------------------------------------------------------------------- body
HARD_Z = (420.0, 640.0)     # DECISION: 4 hard-point loops for the scope pod (left gusset corners), above FP-L (z 150-380)
LOOP_M = 0.08               # 25 mm loop caught in a corner seam (team B, fell.LOOP_M)


def build(c: ShellF | None = None, door: str = DOOR_DEFAULT, fabrics: str = "B") -> BC.Build:
    """The body group: shell, collar, aft face of the chosen door, camo accents, hard points, door hardware. Swells are
    built (the B-13x row stays the ledger's attachment row, unchanged) but booked by the ledger, not here."""
    c = c or make()
    if door not in DOORS:
        raise KeyError(door)
    with frame_face(c):
        B1 = BC.frame_panel(c)                                          # ULTRA 200, frame interface (D6)
        G = BC.gusset(c)
        G.material_id = fab("body", fabrics)
        a0, d0 = float(c.a([BC.Z0])[0]), float(c.depth([BC.Z0])[0])
        BOT = rect_panel("bottom (full S15 width)", 2 * a0, d0, 0.0, seam_allowance_mm=SA_BODY,
                         material_id=fab("floor", fabrics), piece_id="B-05")
        pieces = [(B1, "shell"), (G, "shell"), (BOT, "shell")]
        seams = [
            _seam(B1.edge("right"), G.edge("frame").reversed(), "B-01 | gusset R (FP-R edge, pole-grip tab)", "seared"),
            _seam(B1.edge("left").reversed(), G.edge("frame").reversed(), "B-01 | gusset L (2 hard-point loops, FP-L edge)",
                  "seared"),
            _seam(B1.edge("bottom"), BOT.edge("bottom"), "bottom | B-01 (hinge eyes in it)", "ring", "seared"),
            _seam(G.edge("bottom"), BOT.edge("right"), "bottom | gusset R", "seared"),
            _seam(G.edge("bottom"), BOT.edge("left").reversed(), "bottom | gusset L", "seared"),
        ]
        b = BC.Build(c, pieces, seams, [], {"kind": "boxed", "n": 8}, [], extra={"door": door, "fabrics": fabrics})
        if door == "D2":
            P = d2_pieces(c, fabrics)
            U, DR, HB = P["blade"], P["door"], P["band"]
            b.pieces += [(U, "shell"), (DR, "shell"), (HB, "shell")]
            b.seams += [
                _seam(U.edge("outer_right"), G.edge("aft"), "blade U | gusset R (aft corner)", "seared"),
                _seam(U.edge("outer_left").reversed(), G.edge("aft"), "blade U | gusset L (aft corner, 2 hard-point loops)",
                      "seared"),
                _seam(U.edge("bottom"), BOT.edge("top").reversed(), "bottom | blade U kick strip", "seared"),
                _seam(DR.edge("zip"), DR.edge("zip"), "door | blade U (#10 zip, R 55 corners): panel line = camo break "
                      "= zip", "zip"),
                _seam(HB.edge("bottom"), DR.edge("hinge"), "hinge band | door (door hinge, z 650)", "seared"),
                _seam(HB.edge("right"), HB.edge("right"), "hinge band | blade R (z 650 to collar)", "seared"),
                _seam(HB.edge("left"), HB.edge("left"), "hinge band | blade L (z 650 to collar)", "seared"),
            ]
            b.zips.append({"name": "D2 door zip #10 in the blade | door seam, 2 sliders", "length_mm": P["zip_mm"],
                           "corners": 2, "z": (D2["z_lo"], D2["z_hinge"]), "where": "blade | door seam"})
            W.add_hw(b, "door: 2 cord pulls (3 mm Dyneema + rubber sleeve)", 2 * CORD_PULL_G, 0)
            gar = rect_panel("slider garage, top of the right blade (camo)", 40, 60, 0.0, seam_allowance_mm=SA_FLAT,
                             material_id=CAMO, piece_id="SH-07")
            kick_side = rect_panel("kick band, gusset (camo)", d0, 70, 0.0, seam_allowance_mm=SA_FLAT, material_id=CAMO,
                                   quantity=2, piece_id="SH-01b")
            for p in (gar, kick_side):
                b.pieces.append((p, "accent"))
                b.appliques.append(p)
            tops = [B1.edge("top"), G.edge("top"), U.edge("top_right"), HB.edge("top"), U.edge("top_left"), G.edge("top")]
            b.extra["zip_door_mm"] = P["zip_mm"]
        else:
            P = d1_pieces(c, fabrics)
            LID, HB = P["lid"], P["band"]
            b.pieces += [(LID, "shell"), (HB, "shell")]
            b.seams += [
                _seam(LID.edge("hinge"), BOT.edge("top").reversed(), "lid hinge | floor (sewn, 2 rows)", "seared"),
                _seam(LID.edge("zip"), LID.edge("zip"), "lid | gussets + hinge band (#10 zip, inverted U, R 60)", "zip"),
                _seam(HB.edge("right"), HB.edge("right"), "hinge band R | gusset R (above the zip)", "seared"),
                _seam(HB.edge("left"), HB.edge("left"), "hinge band L | gusset L (above the zip)", "seared"),
            ]
            b.zips.append({"name": "D1 tailgate zip #10, inverted U, 2 sliders", "length_mm": P["zip_mm"], "corners": 2,
                           "z": (BC.Z0, D1["z_top"]), "where": "lid | gussets + hinge band"})
            W.add_hw(b, "lid zip: 2 cord pulls (3 mm Dyneema + rubber sleeve)", 2 * CORD_PULL_G, 0)
            zk, S, A = _face_xy(c)
            leg_len = S(D1["z_top"] - D1["r"])
            gar = rect_panel("slider garage, top-right corner (camo)", 50, 70, 0.0, seam_allowance_mm=SA_FLAT,
                             material_id=CAMO, piece_id="SH-07")
            boots = rect_panel("zip-foot boot", 40, 50, 0.0, seam_allowance_mm=SA_FLAT, material_id=fab("floor", fabrics),
                               quantity=2, piece_id="SH-10")
            flaps = BC._accent_rect("corner storm flap (camo, hot-cut): panel line = camo break = zip", D1["flap_w"],
                                    leg_len, "SH-09", qty=2)
            top_run = 2 * float(c.a([D1["z_top"]])[0]) - 2 * D1["r"]
            tflap = rect_panel("top-run storm flap", D1["flap_w"], top_run, 0.0, seam_allowance_mm=SA_FLAT,
                               material_id=fab("body", fabrics), piece_id="SH-11")
            kick = [BC._chevron("kick band, lid foot (camo, V-notch)", 2 * a0, 70, 45, "SH-01a"),
                    rect_panel("kick band, gusset (camo)", d0, 70, 0.0, seam_allowance_mm=SA_FLAT, material_id=CAMO,
                               quantity=2, piece_id="SH-01b")]
            b.pieces += [(gar, "accent"), (boots, "accent"), (flaps, "accent"), (tflap, "accent")] + [(k, "accent") for k in kick]
            b.appliques += [gar] + kick
            b.extra["zip_door_mm"] = P["zip_mm"]
            tops = [B1.edge("top"), G.edge("top"), HB.edge("top"), G.edge("top")]
            # gusset loops for the lid straps H1-H3 (6), in the storm-flap seam 15 mm forward of the zip legs
            W.add_hw(b, "6 gusset loops 25 mm x 0.10 m (lid straps H1-H3), caught in the flap seam + bartack",
                     6 * 0.10 * WEB25, 6)
            b.extra["lid_straps"] = lid_straps(c)
        W._add_collar(b, c, tops)
        for p, g in b.pieces:
            if p.piece_id == "B-06":
                p.material_id = fab("collar", fabrics)
            elif p.piece_id == "B-07":
                p.material_id = fab("body", fabrics)
        b.seams = [(s, (set(t) - {"bound"}) | {"seared"} if "bound" in t else t) for s, t in b.seams]   # B-1 rule
        b.pieces.append((BC.boxed_swell(), "swell"))
        W.add_hw(b, f"4 hard-point loops: 25 mm webbing {LOOP_M} m each, in the left gusset's corner seams at z "
                    f"{HARD_Z[0]:.0f} / {HARD_Z[1]:.0f} (scope pod)", 4 * LOOP_M * WEB25, 4)
        if c.setback > 0:
            b.extra["frame_z_folds"] = 2      # B-01: the 30 mm head setback Z-fold + the BL-011 top setback Z-fold
    return b


def lid_straps(c) -> list:
    """D1 lid straps H1-H3 at the IM heights: span + round the corners + 150 mm tail, G-hook (R) + ladder lock (L)
    (tailgate.build rule). Booked in straps_compression (they are straps)."""
    out = []
    for i, z in enumerate(D1["hoop_z"]):
        L = 2 * float(c.a([z])[0]) + 2 * D1["loop_in_mm"] + 2 * 30.0 + 150.0
        out.append((f"D1 lid strap H{i + 1}: 25 mm {L / 1000:.2f} m + G-hook + ladder lock (z {z:.0f})",
                    L / 1000 * WEB25 + G_HOOK + LADDER_G))
    return out


# ---------------------------------------------------------------------------------------------------------- pockets
def _A():
    import importlib
    return importlib.import_module("A.evolve")


def _B():
    import importlib
    return importlib.import_module("lean.fell")


def hip_reach_pockets() -> list:
    """Team A's E-4 hip-reach pockets FP-L / FP-R, the same part (evolve.FP) moved from the wings' lower front corners
    to the gussets' lower front corners (the wings are deleted), z 150-380 (A's write-up height; IMP-8 stays below on
    the right, z 35-150). Plus E-5, the pole quiver (boot in FP-R's front pleat, grip loop at the gusset's top hard
    point). Mass by A's recipe from the records."""
    E = _A()
    FP, POLE, H = E.FP, E.POLE, BC.HOURS
    mesh = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (FP["h"] + 2 * SA_FLAT) * 1e-6 * _gsm(MESH)
    cord = 2 * (FP["w"] + FP["pleat"] + 60) / 1000 * SHOCK_GM
    band = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (25.0 + 2 * SA_FLAT) * 1e-6 * _gsm(CAMO)
    fp_h = 2 * H["cut_piece"] + 2 * (2 * FP["h"] + FP["w"]) / 1000 * H["straight_m"] + 2 * 0.25 * H["straight_m"] \
        + 4 * H["bartack"] + 0.3
    pole_g = POLE["cord_m"] * SHOCK_GM + CORDLOCK_G + POLE["tab_m"] * WEB25
    pole_h = 0.25 * H["straight_m"] + 2 * H["bartack"] + 0.1
    return [
        {"id": "FP-L/R", "name": "hip-reach pockets FP-L / FP-R (team A E-4): power mesh 260 x 230, 2 box pleats, "
         "shock-cord top in a 25 mm camo mouth band, sewn to each gusset's lower front corner (z 150-380)",
         "mass_g": round(mesh + cord + band, 1), "hours": round(fp_h, 2), "pieces": 4, "seam_m": round(
             2 * (2 * FP["h"] + FP["w"] + 250) / 1000, 2), "z": (150.0, 380.0), "cap_L": FP["cap_L"], "env_mm": FP["env_mm"],
         "source": "evolve.FP + power_mesh_nylon_spandex, shock_cord_3mm, polyester_ht_630d_printable records (A's recipe, "
                   "cut + 8 mm SA)"},
        {"id": "E-5", "name": "pole quiver: 40 mm boot in FP-R's front pleat + 3 mm shock-cord grip loop and cord lock on "
         "a 25 mm tab caught in the right B-01 | gusset seam at z 640", "mass_g": round(pole_g, 1), "hours": round(pole_h, 2),
         "pieces": 0, "seam_m": 0.25, "cap_L": POLE["cap_L"], "env_mm": POLE["env_mm"],
         "source": "evolve.POLE + shock_cord_3mm, cord_lock_spring, poly_webbing_25mm records"},
    ]


def fixed_pockets(c=None, door: str = DOOR_DEFAULT, fabrics: str = "B") -> list:
    """Bag-mounted pockets in base: IMP-2 hydration sleeve (team B's 70D tube, or CORRIE's in today's fabrics), IMP-4
    kill-kit pocket (inside the D2 door / inside the D1 lid, team C), IMP-8 bow cam cup (unchanged, right gusset foot),
    and the hip-reach pockets + pole quiver. IMP-1 (scope sleeve) leaves base: it is the scope pod add-on."""
    c = c or make()
    with frame_face(c):
        bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    out = []
    if fabrics == "B":
        h = [d for d in _B().fixed_pockets(c) if d["id"] == "IMP-2L"][0]
        out.append({"id": "IMP-2", "name": h["name"], "mass_g": h["mass_g"], "hours": h.get("hours", bp["IMP-2"]["hours"]),
                    "pieces": sum(p.quantity for p in bp["IMP-2"]["pieces"]), "source": "lean.fell.fixed_pockets (70D tube)"})
    else:
        out.append({"id": "IMP-2", "name": bp["IMP-2"]["name"], "mass_g": bp["IMP-2"]["mass_g"],
                    "hours": bp["IMP-2"]["hours"], "pieces": sum(p.quantity for p in bp["IMP-2"]["pieces"]),
                    "source": "corrie.bag_pockets"})
    where = "inside the D2 door" if door == "D2" else "inside the D1 lid (team C)"
    out.append({"id": "IMP-4", "name": f"IMP-4 zipped kill-kit / first-aid pocket, {where}", "mass_g": bp["IMP-4"]["mass_g"],
                "hours": bp["IMP-4"]["hours"], "pieces": sum(p.quantity for p in bp["IMP-4"]["pieces"]),
                "source": "corrie.bag_pockets (same part)"})
    out.append({"id": "IMP-8", "name": "IMP-8 bow cam / limb cup, right gusset foot (z 35-150)", "mass_g": bp["IMP-8"]["mass_g"],
                "hours": bp["IMP-8"]["hours"], "pieces": sum(p.quantity for p in bp["IMP-8"]["pieces"]),
                "source": "corrie.bag_pockets (same part)"})
    for d in hip_reach_pockets():
        out.append({k: d[k] for k in ("id", "name", "mass_g", "hours", "pieces", "source")})
    return out


# ---------------------------------------------------------------------------------------------------------- add-ons
SCOPE_POD_Z = (400.0, 640.0)   # DECISION: the spotter hangs from the hard points at z 420 / 640 (above FP-L)


def addons() -> dict:
    """Add-ons outside base (BL-008 rule: clip / hook on and off by hand).
    * scope pod: team B's A1 glass pod (padded spotter sleeve on its own ULTRAGrid back panel) on the LEFT gusset hard
      points (owner 2026-11-11: the scope sleeve goes on the left gusset);
    * tripod straps: DROPPED (stated reason): the owner made W1-W3 the only external strap set (DECISIONS
      2026-11-11), and BL-010 row S10 passes W1/W2 for side carry of the tripod; team B's A2 pair (32 g) would be a
      second external set. The tripod rides under W1/W2 on the right gusset, feet on FP-R's top edge;
    * top pouch: team B's A3 lid pod (CORRIE B.2's 2.7 L pouch in ULTRAGrid / 70D); its 4 straps are booked in
      straps_compression (ledger rule), the rest in pouch;
    * meat liner: team D's SWAP slab (silpoly tube, 70D frame face + floor, HDPE roll), a meat-trip add-on.
    Float kit = B-24 (straps_meat, meat trip) and the bottle holster IMP-3 (belt, as hunted) are ledger rows."""
    ad = _B().addons()
    out = {}
    a1, a3 = ad["A1"], ad["A3"]
    a3_straps = 4 * (0.12 * WEB25 + G_HOOK)
    out["scope_pod"] = {"name": "scope pod (team B glass pod), left gusset", "system": "bag_pockets", "cfg": "as_hunted",
                        "mass_g": a1["mass_g"], "hours": a1["hours"], "pieces": sum(p.quantity for p in a1["pieces"]),
                        "source": "lean.fell.addons()['A1']"}
    out["top_pouch"] = {"name": "top pouch 2.7 L (team B lid pod), body", "system": "pouch", "cfg": "as_hunted",
                        "mass_g": round(a3["mass_g"] - a3_straps, 2), "hours": a3["hours"],
                        "pieces": sum(p.quantity for p in a3["pieces"]), "zip_mm": CO.POUCH_B2["L"] - 20.0,
                        "source": "lean.fell.addons()['A3'] minus its 4 straps"}
    out["top_pouch_straps"] = {"name": "top pouch: 4 x 25 mm 0.12 m straps + 4 G-hooks", "system": "straps_compression",
                               "cfg": "as_hunted", "mass_g": round(a3_straps, 2), "hours": 0.0, "pieces": 0,
                               "source": "poly_webbing_25mm record + G_HOOK ASSUMPTION (lean.fell A3 recipe)"}
    import importlib
    D = importlib.import_module("D.cache")
    sw = D.modules()[0]
    g = sum(BC.piece_mass_g(p) for p in sw["pieces"]) + sum(m for _, m in sw["hw"])
    H = BC.HOURS
    hrs = sum(p.quantity for p in sw["pieces"]) * H["cut_piece"] + sum(L for _, L in sw["seams"]) / 1000 * H["straight_m"] \
        + 4 * H["pivot"] + 2 * H["bartack"]
    out["meat_liner"] = {"name": "meat liner (team D SWAP slab, wipeable silpoly / 70D, 330 x 110 x 560)",
                         "system": "bag_pockets", "cfg": "meat_trip", "mass_g": round(g, 1), "hours": round(hrs, 2),
                         "pieces": sum(p.quantity for p in sw["pieces"]), "source": "D.cache.modules()[0] (pieces x gsm + hw)"}
    return out


# ---------------------------------------------------------------------------------------------------------- ledger
def _ledger_rows(size="M") -> list:
    from huntkit.mass import ledger as L
    return L.parts(CONFIG, size)


def _cfg_b2(r: dict, f02_g: float) -> str:
    """BL-008 rule on a CORRIE B.2 ledger row (weight_configs_proposal.md section 3)."""
    n, s = r["name"], r["system"]
    if s == "pouch" or (s == "straps_compression" and n.startswith("pouch")):
        return "as_hunted"
    if n.startswith("IMP-3"):
        return "as_hunted"
    if s == "straps_meat" and n.startswith("float-mode stand-off links B-24"):
        return "meat_trip"
    return "base"


SHELL_ROWS = ("B-01", "B-03", "B-05", "B-06f", "B-06", "B-07", "B-07s", "B-02u", "B-02door", "B-02h", "SH-07",
              "SH-01a", "SH-01b", "horseshoe door zip", "door: 2 cord pulls", "G-1")


def _is_shell_row(r) -> bool:
    return r["system"] == "bag_shell" and any(r["name"].startswith(k + " ") or r["name"].startswith(k + ":")
                                               or r["name"] == k for k in SHELL_ROWS)


def fly_rows(b: BC.Build, ledger_rows: list) -> list:
    """Rain fly: F-01 scaled to this shell's outer area (CORRIE's G-2 rule), F-02 base pocket (base: it stays sewn
    on), the ledger's hem / zip / tether row unchanged (ASSUMPTION: the hem length follows the outer perimeter within
    5 %; settled by cutting the first fly)."""
    pan = CO._panels()
    f01 = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-01"))
    f02 = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-02"))
    ids = ("B-03", "B-02u", "B-02door", "B-02h", "B-02L", "B-05")    # B-02L = the D1 lid
    a = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in ids) / 1e6
    hem = next(r for r in ledger_rows if r["system"] == "fly" and "elastic hem" in r["name"])
    return [("fly", "F-01 rain fly re-cut to CORRIE F's outer shell", f01 * a / CO.SPINE_OUTER_M2, "as_hunted",
             f"panels.yaml F-01 x outer area {a:.3f} / SPINE {CO.SPINE_OUTER_M2} m2 (G-2 rule)"),
            ("fly", "F-02 fly base pocket (stays on the bag)", f02, "base", "panels.yaml F-02"),
            ("fly", hem["name"], hem["g"], "as_hunted", "ledger row (unchanged)")]


def strap_rows() -> list:
    """BL-003 REC parts (strap_arch.architectures()['rec'], every mass from the ledger or a record) + BL-010 fixes."""
    import strap_arch as SA
    from huntkit.gendesign import loadpath_check as LP
    rows = [(p.system, f"{p.id}: {p.name}", p.g, p.cfg, f"strap_arch rec: {p.source}") for p in SA.architectures()["rec"]
            if p.id != "pouch-straps"]           # the pouch straps are booked with the top pouch add-on
    H = {h["where"]: h for h in LP.hooks_table()}
    hw = LP.hw()
    im3 = H["IM3 meat-strap free end (1)"]
    rows.append(("straps_meat", "BL-010 S2: IM3 free end G-hook -> wiregate carabiner", im3["rated_g"] - im3["booked_g"],
                 "base", "loadpath_check.hooks_table (carabiner_wiregate_22kn record)"))
    wh = H["W1-W3 haul-wrap hooks (3)"]
    rows.append(("straps_compression", "BL-010 S9: W1-W3 rated 25 mm G-hooks (3) and heavy ladder locks (3)",
                 3 * (wh["rated_g"] - wh["booked_g"]) + 3 * (hw["llh"]["g"] - hw["ll"]["g"]), "base",
                 "loadpath_check.hooks_table + ladder_lock_25mm_heavy record"))
    b24 = H["B-24 float-link hooks (2, meat-trip kit)"]
    rows.append(("straps_meat", "BL-010 S12: B-24 hooks -> wiregate carabiners (2)", 2 * (b24["rated_g"] - b24["booked_g"]),
                 "meat_trip", "loadpath_check.hooks_table"))
    return rows


def attachment_rows(ledger_rows: list) -> list:
    """Ledger attachment rows + BL-004 REC changes + BL-010 A1 (IM3 bag hooks -> carabiners; the 25 mm fairlead
    cheek is a frame part) + heavy guy ladder locks (A3 passes only on the heavy lock; BL-004 booked it as a
    sensitivity, 220.7 g)."""
    import attach_diet as AD
    from huntkit.gendesign import loadpath_check as LP
    rows = [("attachment", r["name"], r["g"], "base", "ledger") for r in ledger_rows if r["system"] == "attachment"]
    for n, g, src in AD.mass_changes("REC"):
        rows.append(("attachment", f"BL-004 REC: {n}", g, "base", f"attach_diet.mass_changes: {src}"))
    H = {h["where"]: h for h in LP.hooks_table()}
    im3 = H["IM3 bag hooks (2)"]
    rows.append(("attachment", "BL-010 A1: IM3 bag hooks -> wiregate carabiners (2)", 2 * (im3["rated_g"] - im3["booked_g"]),
                 "base", "loadpath_check.hooks_table (carabiner_wiregate_22kn record)"))
    hw = LP.hw()
    rows.append(("attachment", "BL-010 A3: guy ladder locks -> heavy (2)", 2 * (hw["llh"]["g"] - hw["ll"]["g"]), "base",
                 "ladder_lock_25mm_heavy / ladder_lock_25mm records"))
    return rows


def parts(size: str = "M", door: str = DOOR_DEFAULT, fabrics: str = "B", c: ShellF | None = None) -> list:
    """CORRIE F bag-side rows on the ledger basis: dicts {system, name, g, cfg, source}."""
    c = c or make()
    led = _ledger_rows(size)
    b = build(c, door, fabrics)
    out = []

    def add(system, name, g, cfg, source):
        out.append({"system": system, "name": name, "g": round(float(g), 2), "cfg": cfg, "source": source})

    # bag_shell: ledger rows that are not the corrie.build() shell (B-11 tabs, bow riser carry) + CORRIE F's body
    for r in led:
        if r["system"] == "bag_shell" and not _is_shell_row(r):
            add("bag_shell", r["name"], r["g"], "base", "ledger (unchanged)")
    for p, grp in b.pieces:
        if grp == "swell":
            continue                                   # B-13x stays the ledger's attachment row
        add("bag_shell", f"{p.piece_id} {p.name} ({p.material_id}{', x%d' % p.quantity if p.quantity > 1 else ''})",
            BC.piece_mass_g(p), "base", "corrie_f.build(): cut area x record gsm")
    for z in b.zips:
        add("bag_shell", z["name"], BC.zip_mass_g(z), "base", "coil_zipper_10 record x (L + 60 mm) + 2 sliders (ASSUMPTION)")
    for n, g in b.extra.get("hardware", []):
        add("bag_shell", n, g, "base", "records (webbing, cord pulls ASSUMPTION)")
    # bag_pockets
    for d in fixed_pockets(c, door, fabrics):
        add("bag_pockets", f"{d['id']} {d['name']}", d["mass_g"], "base", d["source"])
    # add-ons
    for k, d in addons().items():
        add(d["system"], f"add-on {k}: {d['name']}", d["mass_g"], d["cfg"], d["source"])
    # fly
    for s, n, g, cfg, src in fly_rows(b, led):
        add(s, n, g, cfg, src)
    # straps
    for s, n, g, cfg, src in strap_rows():
        add(s, n, g, cfg, src)
    if door == "D1":
        for n, g in b.extra["lid_straps"]:
            add("straps_compression", n, g, "base", "poly_webbing_25mm + ladder_lock_25mm records, G_HOOK ASSUMPTION "
                "(tailgate.build rule)")
    # attachment
    for s, n, g, cfg, src in attachment_rows(led):
        add(s, n, g, cfg, src)
    # BL-022 rev 1 parts
    for s, n, g, cfg, src in rev1_rows(c, door):
        add(s, n, g, cfg, src)
    return out


BAG_SIDE = ("bag_shell", "bag_pockets", "pouch", "fly", "straps_meat", "straps_compression", "attachment")
_INCL = {"base": ("base",), "as_hunted": ("base", "as_hunted"), "meat_trip": CFGS}


def _sum(rows, systems, cfg):
    return round(sum(r["g"] for r in rows if r["system"] in systems and r["cfg"] in _INCL[cfg]), 1)


def corrie_b2_rows(size: str = "M") -> list:
    """CORRIE B.2's bag-side ledger rows with BL-008 cfg tags (same rule)."""
    pan = CO._panels()
    f02 = sum(r["mass_g_total"] for k, r in pan.items() if k.startswith("F-02"))
    rows = []
    for r in _ledger_rows(size):
        if r["system"] not in BAG_SIDE and not r["name"].startswith("IMP-3"):
            continue
        cfg = _cfg_b2(r, f02)
        if r["system"] == "fly" and r["name"].startswith("rain fly: fly + fly pocket"):
            rows.append({"system": "fly", "name": "F-02 fly base pocket", "g": round(f02, 2), "cfg": "base", "source": "panels.yaml"})
            rows.append({"system": "fly", "name": "rain fly (F-01 part of the ledger row)", "g": round(r["g"] - f02, 2),
                         "cfg": "as_hunted", "source": "ledger row minus F-02"})
            continue
        if r["system"] == "fly":
            cfg = "as_hunted"
        rows.append({"system": r["system"], "name": r["name"], "g": r["g"], "cfg": cfg, "source": "ledger"})
    return rows


def weight_table(size: str = "M", config: str = "as_hunted", door: str = DOOR_DEFAULT, fabrics: str = "B") -> dict:
    """Bag side by ledger system for one weight configuration (base / as_hunted / meat_trip), CORRIE F against CORRIE
    B.2 on the same rule, and the pack on H1 (ledger total - CORRIE B.2 bag side + CORRIE F bag side; suspension and
    misc as the ledger books them today: BL-013 has not landed, see ``pack_with_adopted``)."""
    from huntkit.mass import ledger as L
    if config not in CFGS:
        raise KeyError(config)
    F = parts(size, door, fabrics)
    B = corrie_b2_rows(size)
    sysF = {s: _sum(F, (s,), config) for s in BAG_SIDE}
    sysB = {s: _sum([r for r in B if r["system"] in BAG_SIDE], (s,), config) for s in BAG_SIDE}
    bsF, bsB = round(sum(sysF.values()), 1), round(sum(sysB.values()), 1)
    tot = L.total(CONFIG, size)
    allB = round(sum(r["g"] for r in B if r["system"] in BAG_SIDE), 1)
    rest = tot - allB                                     # suspension + misc (ledger)
    imp3 = sum(r["g"] for r in B if r["name"].startswith("IMP-3"))
    rest_cfg = rest - (0.0 if config != "base" else imp3)   # IMP-3 holster: as hunted (belt)
    return {"size": size, "config": config, "door": door, "fabrics": fabrics,
            "bag_side_g": bsF, "corrie_b2_bag_side_g": bsB, "delta_g": round(bsF - bsB, 1),
            "by_system": sysF, "corrie_b2_by_system": sysB,
            "pack_h1_g": round(rest_cfg + bsF, 1), "corrie_b2_pack_h1_g": round(rest_cfg + bsB, 1),
            "bag_system_g": round(sum(sysF[s] for s in L.BAG_SYSTEM), 1)}


def pack_with_adopted(size: str = "M", door: str = DOOR_DEFAULT, fabrics: str = "B") -> dict:
    """The pack on H1 with CORRIE F and the adopted suspension packages that BL-013 has not yet rolled into the ledger,
    each read from its own code at belt M: hipbelt B diet (BL-006, ``hipbelt_diet._mass_delta`` over ``PACKAGE`` less
    item 'e', which only moves the holster to as-hunted: a config change, not a mass change) and the sandwich backer
    strip (BL-005, ``back_system2.mass_delta_g(RECOMMENDED)``). Gated items stay in (as adopted). The crown kits
    (BL-017, owner 2026-11-11) are left out: their mass waits for the OD 17 legs and CA-1."""
    import hipbelt_diet as HD
    from huntkit.gendesign import back_system2 as BS2
    belt = sum(HD._mass_delta(k, size) for k in HD.PACKAGE if k != "e")
    back = BS2.mass_delta_g(BS2._variant(BS2.RECOMMENDED))["total"]
    out = {"belt_BL006_g": round(belt, 1), "back_BL005_g": round(back, 1)}
    for cfg in CFGS:
        w = weight_table(size, cfg, door, fabrics)
        out[cfg] = {"ledger_g": w["pack_h1_g"], "with_adopted_g": round(w["pack_h1_g"] + belt + back, 1)}
    return out


# ---------------------------------------------------------------------------------------------------------- metrics
def build_metrics(door: str = DOOR_DEFAULT, fabrics: str = "B") -> dict:
    """Pieces, seam length, curved seams, zip length, beginner hours: bag_concepts.metrics on the body + the pockets'
    and add-ons' own counts (same HOURS model as bag_concepts / every competition entry)."""
    c = make()
    b = build(c, door, fabrics)
    m = BC.metrics(b)
    fx = fixed_pockets(c, door, fabrics)
    ad = addons()
    base_h = m["hours_total"] + sum(d["hours"] for d in fx) + 0.3          # +0.3 h F-02 fly pocket (ASSUMPTION)
    addon_h = sum(d["hours"] for d in ad.values()) + 1.0                     # +1.0 h the fly itself (ASSUMPTION)
    pieces = m["cut_pieces"] + sum(d["pieces"] for d in fx) + 1             # + F-02
    zip_mm = m["zip_length_m"] * 1000
    out = {"door": door, "fabrics": fabrics, "body": {k: m[k] for k in ("cut_pieces", "seams", "seam_length_m",
                                                                        "curved_seams", "curved_seam_length_m", "pivots",
                                                                        "ring_seams", "zip_length_m", "hours_total")},
           "body_hours": m["hours"], "pieces_base": pieces,
           "pieces_with_addons": pieces + sum(d["pieces"] for d in ad.values()) + 1,
           "curved_seams": m["curved_seams"], "seam_length_m": m["seam_length_m"],
           "zip_mm_base": round(zip_mm, 0), "zip_mm_with_pouch": round(zip_mm + ad["top_pouch"]["zip_mm"], 0),
           "door_zip_mm": round(b.extra["zip_door_mm"], 0),
           "beginner_hours_base": round(base_h, 1), "beginner_hours_with_addons": round(base_h + addon_h, 1),
           # CORRIE B.2's 35.6 h basis (lean.fell.corrie_bag_system: body incl. pouch + IMP-1/2/4/8, no fly)
           "beginner_hours_b2_basis": round(base_h - 0.3 + ad["top_pouch"]["hours"] + ad["scope_pod"]["hours"], 1),
           "pieces_b2_basis": pieces - 1 + ad["top_pouch"]["pieces"] + ad["scope_pod"]["pieces"],
           "seam_rows": m["seam_rows"]}
    out["clear_width_mm"] = {k: round(clear_width(c, door, z), 0) for k, z in STATIONS.items()}
    return out


def corrie_b2_metrics() -> dict:
    """CORRIE B.2 on the same model (body + IMP-1/2/4/8), for the comparison table (lean.fell.corrie_bag_system)."""
    cs = _B().corrie_bag_system()
    return {"pieces": cs["pieces"], "hours": cs["hours"], "zip_mm": cs["zip_mm"], "curved_seams": cs["curved_seams"],
            "clear_width_mm": {k: round(clear_width(None, "CORRIE", z), 0) for k, z in STATIONS.items()}}


# ---------------------------------------------------------------------------------------------------------- report
def summary(size: str = "M") -> dict:
    out = {"geometry": {k: v for k, v in geometry().items() if k != "profile"}, "doors": {}}
    for door in DOORS:
        d = {"metrics": {k: v for k, v in build_metrics(door).items() if k != "seam_rows"},
             "configs": {cfg: weight_table(size, cfg, door) for cfg in CFGS},
             "today_fabrics": {cfg: weight_table(size, cfg, door, "today") for cfg in CFGS}}
        mt = d["configs"]["meat_trip"]
        liner = addons()["meat_liner"]["mass_g"]
        d["goal"] = {"basis": "ledger bag_side, every configuration item booked (meat trip), CORRIE F without the meat "
                              "liner (a new add-on CORRIE B.2 does not have)",
                     "corrie_b2_g": mt["corrie_b2_bag_side_g"], "corrie_f_g": round(mt["bag_side_g"] - liner, 1),
                     "saving_g": round(mt["corrie_b2_bag_side_g"] - (mt["bag_side_g"] - liner), 1),
                     "with_liner_saving_g": round(-mt["delta_g"], 1), "target_g": 350.0}
        d["goal"]["met"] = d["goal"]["saving_g"] >= 350.0
        out["doors"][door] = d
    out["corrie_b2_metrics"] = corrie_b2_metrics()
    return out


def _j(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


# ---------------------------------------------------------------------------------------------------------- BL-022
# Crown-bar layout (all three BL-017 crown kits share H1's top bar: crown_diet.build changes only the legs, spine,
# rack and bushings, checked in guy_lifter_check()).
LIFTER_X = 105.0          # build_geometry.LIFTER_X: lifter lugs on the crown-corner wraps (owner-frozen, patent guardrail)
LIFTER_W = 25.0           # panels.yaml: load lifters poly_webbing_25mm
LEG_OD = 16.0             # frame.yaml / crown_diet leg_section: crown leg OD 16
WRAP_ON_BAR = 30.0        # frame.yaml wrap_overlap_mm (30 mm on each tube)
WRAP_SCARF = 8.0          # frame.yaml: wrap ends scarfed over 8 mm
BAR_OD = 18.0             # frame.yaml bar_section od
SPINE_OD = 20.0           # frame.yaml spine_section od
SPINE_CLAMP_HALF = 15.0   # ASSUMPTION: spine-to-bar clamp half-width (OD 20 + 5 mm collar a side); settled by the clamp drawing
GUY_W = 25.0              # guy bar loop / bridle webbing (poly_webbing_25mm)
GUY_X_REV0 = (92.0, 100.0)    # attachment_diet.md section 5: guy loops at x +/-(92-100) "beside the leg"
MIN_CLEAR_MM = 10.0       # ASSUMPTION: gloved toggle handling + +/-5 mm webbing wander; settled by the prototype crown fit
MU_WEB_BAR = 0.30         # ASSUMPTION: 25 mm poly webbing loop on clear-coated carbon (no record); settled by a pull test
BAR_WRAP_MM = math.pi * (BAR_OD + 2 * 1.2) + 15.0      # webbing (t 1.2 mm ASSUMPTION) round the bar + 15 mm bartack lap
SPINE_WRAP_MM = math.pi * (SPINE_OD + 2 * 1.2) + 15.0
BRIDLE_TAB_MM = 60.0      # ASSUMPTION: 25 mm tab folded 2 x 30 mm for the guy's toggle loop to pass through
TRIPOD_KEEPER_Z = 600.0   # ASSUMPTION: upper tripod legs (feet on FP-R's top edge z 380); settled by the right-gusset fit check
TRIPOD_D = 70.0           # ASSUMPTION: folded tripod leg bundle (3 x ~25 mm legs + head); settled by the same fit check
KEEPER_PRE = 0.80         # DECISION: shock cord cut to 80 % of the gusset span (snug with no tripod)
SEAM_CATCH = 15.0         # cord end caught in a seam, each end (same rule as the FP mouth cords)


def _bands(x0: float, w: float) -> tuple:
    return (x0 - w / 2.0, x0 + w / 2.0)


def guy_lifter_check() -> dict:
    """S6: guy bar loops against the lifter lugs on the crown top bar, for each BL-017 crown kit (recommended
    (a)+(d1)+(c17 bore 19) = specs acb_S / acb_M / acb_L) at both ends of its torso range. x bands on the bar (right
    half; the left mirrors it). The lifter webbing band is clipped by the leg's inner face."""
    from huntkit.gendesign import crown_diet as CD
    sp = CD.specs()
    kits = {}
    for size, (lo, hi) in CD.SIZES.items():
        rows = []
        for t in (lo, hi):
            m = CD.build(sp[f"acb_{size}"], t)
            n = m["nodes"]
            leg_x = float(n["CRtop"][0])
            bar_ok = all(abs(float(n[k][2]) - float(n["CRtop"][2])) < 1e-6 for k in ("TB0", "TB1", "TB2"))
            rows.append({"torso_in": t, "leg_x": leg_x, "bar_z": float(n["CRtop"][2]), "bar_straight": bar_ok})
        kits[size] = rows
    leg_x = {r["leg_x"] for rr in kits.values() for r in rr}
    assert len(leg_x) == 1, leg_x
    leg_x = leg_x.pop()
    leg_in = leg_x - LEG_OD / 2.0
    lift = (max(LIFTER_X - LIFTER_W / 2.0, 0.0), min(LIFTER_X + LIFTER_W / 2.0, leg_in))
    wrap = (leg_in - WRAP_ON_BAR - WRAP_SCARF, leg_in)
    clamp = (0.0, SPINE_CLAMP_HALF)

    def judge(x0):
        g = _bands(x0, GUY_W)
        return {"guy_band": [round(v, 1) for v in g], "overlap_lifter_mm": round(max(0.0, min(g[1], lift[1]) - max(g[0], lift[0])), 1),
                "clear_to_lifter_mm": round(lift[0] - g[1], 1), "clear_to_wrap_mm": round(wrap[0] - g[1], 1),
                "clear_to_clamp_mm": round(g[0] - clamp[1], 1)}
    rev0 = {f"x{x:.0f}": judge(x) for x in GUY_X_REV0}
    rev1 = judge(REVS[1]["guy_x"])
    return {"kits": kits, "leg_x": leg_x, "lifter_band": [round(v, 1) for v in lift], "wrap_band": [round(v, 1) for v in wrap],
            "clamp_band": list(clamp), "rev0": rev0, "rev1": rev1, "min_clear_mm": MIN_CLEAR_MM,
            "rev0_clash": any(v["overlap_lifter_mm"] > 0 for v in rev0.values()),
            "rev1_ok": rev1["overlap_lifter_mm"] == 0 and min(rev1["clear_to_lifter_mm"], rev1["clear_to_wrap_mm"],
                                                              rev1["clear_to_clamp_mm"]) >= 0
                       and rev1["clear_to_lifter_mm"] >= MIN_CLEAR_MM}


def _seg_dist(p1, p2, q1, q2, n=200) -> float:
    a = np.linspace(0, 1, n)[:, None]
    P = p1 + a * (p2 - p1)
    Q = q1 + a * (q2 - q1)
    return float(np.min(np.linalg.norm(P[:, None, :] - Q[None, :, :], axis=2)))


def guy_geometry(c: ShellF | None = None) -> dict:
    """Guy line from its bar end to the B-22 tab (x +/-149, z 695 on the aft face) at each torso: the outboard share
    of the guy tension (does a plain loop slide along the bar? it does when share > MU_WEB_BAR) and the 3D distance
    from the guy line to the lifter webbing (lug to shoulder-strap point, same x: ASSUMPTION lifter in a vertical
    plane). Bar-end y, z = the cloth sim's tie anchors (corrie_PR{t}.yaml: bar centre + 25 mm sweep + bar radius)."""
    from huntkit.clothsim.pack import load_scenario
    c = c or make()
    bg = _bg()
    out = {}
    for t in (15, 19, 23):
        sc = load_scenario(str(ROOT / "huntkit" / "clothsim" / "scenarios" / f"corrie_PR{t}c.yaml"))
        tie = next(q for q in sc["attachments"]["ties"]["list"] if q["id"] == "TG_R")
        _, ay, az = (float(v) for v in tie["anchor"])
        tab = np.array([149.0, float(c.y_front([695.0])[0]), 695.0])
        cs = min(bg.crown_settings(), key=lambda q: abs(q["torso_in"] - t))
        la = np.array(cs["lifter_anchor_R"], float)
        ang = math.radians(cs["lifter_angle_deg"])
        lend = la + 150.0 * np.array([0.0, -math.cos(ang), -math.sin(ang)])
        row = {}
        for k, x in (("rev0", 100.0), ("rev1", REVS[1]["guy_x"])):
            a = np.array([x, ay, az])
            d = tab - a
            row[k] = {"outboard_share": round(float(d[0] / np.linalg.norm(d)), 3),
                      "slides_without_bridle": bool(d[0] / np.linalg.norm(d) > MU_WEB_BAR),
                      "dist_to_lifter_mm": round(_seg_dist(a, tab, la, lend) - GUY_W / 2.0, 1)}
        out[t] = row
    return out


def _bg():
    from huntkit.gendesign import attach_system as AS
    return AS._bg()


def guy_bridle() -> dict:
    """B-25 guy bridle (rev 1): one 25 mm webbing piece sewn round the top bar at x +/-GUY_X (two sleeves), joined
    along the bar and round the spine below its clamp (so the spine locates it and the guys' outboard pulls cancel in
    the webbing), with a folded tab at each sleeve for the guy's toggle loop. Fitted on the bar before the crown corners
    are bonded (build step). Permanent: no handling in use."""
    x = REVS[1]["guy_x"]
    run = 2.0 * (x - GUY_W / 2.0 - SPINE_CLAMP_HALF)
    mm = 2 * BAR_WRAP_MM + run + SPINE_WRAP_MM + 2 * BRIDLE_TAB_MM
    return {"id": "B-25", "length_mm": round(mm, 1), "mass_g": round(mm * WEB25 / 1000.0, 2),
            "source": "poly_webbing_25mm record x length (BAR_WRAP_MM, SPINE_WRAP_MM, BRIDLE_TAB_MM ASSUMPTIONS)"}


def tripod_keeper(c: ShellF | None = None, door: str = DOOR_DEFAULT) -> dict:
    """B-26 tripod keeper (rev 1, S7): one 3 mm shock cord across the right gusset at TRIPOD_KEEPER_Z, ends caught in
    the B-01 | gusset R seam and the aft corner seam (D2: blade U | gusset R). D1's aft corner seam holds the zip leg,
    so its aft end goes in a 25 x 60 mm webbing tab on the gusset 20 mm forward of the zip. The tripod slides under
    it head first when packed; W1/W2 still compress it. Unhooking W1/W2 for the door does not touch it."""
    c = c or make()
    span = float(c.depth([TRIPOD_KEEPER_Z])[0])
    free = KEEPER_PRE * span
    cut = free + 2 * SEAM_CATCH
    path = span + (math.pi - 2.0) * TRIPOD_D / 2.0      # cord over a round bundle lying on the gusset
    strain = path / free - 1.0
    g = cut * SHOCK_GM / 1000.0
    tab = 60.0 * WEB25 / 1000.0 if door == "D1" else 0.0
    return {"id": "B-26", "span_mm": round(span, 1), "cut_mm": round(cut, 1), "strain_with_tripod": round(strain, 3),
            "mass_g": round(g + tab, 2), "tab_g": round(tab, 2),
            "glove_s_per_door_cycle": 0.0,
            "glove_s_per_packing": 6.0,          # ASSUMPTION: slide the tripod head-first under one cord; settled by FT-S2
            "compare": {"team B A2 tripod straps g": 32.2, "W-strap re-routing g": 0.0},
            "source": "shock_cord_3mm record (6 g/m) x cut length; D1 tab poly_webbing_25mm record"}


def rev1_rows(c: ShellF | None = None, door: str = DOOR_DEFAULT) -> list:
    """Bag-side rows rev 1 adds (none at rev 0)."""
    r = REVS[REVISION]
    rows = []
    if r["guy_bridle"]:
        b = guy_bridle()
        rows.append(("attachment", f"BL-022 rev 1: {b['id']} guy bridle on the top bar at x +/-{r['guy_x']:.0f}",
                     b["mass_g"], "base", b["source"]))
    if r["tripod_keeper"]:
        k = tripod_keeper(c, door)
        rows.append(("straps_compression", f"BL-022 rev 1: {k['id']} tripod keeper (3 mm shock cord, right gusset)",
                     k["mass_g"], "base", k["source"]))
    return rows


def top_bar_guy_moment(guy_n_factored: float) -> dict:
    """Bar bending from the two guy loads (fixed-fixed between the corner nodes, symmetric point loads at x +/-xg):
    end moment M = P a (L - a) / L, mid moment P a^2 / L, a = leg_x - xg. Rev 0 node x 95 (crown_diet split_top_bar)
    against rev 1 x GUY_X. Stress on the 18 mm bar tube section (frame.yaml bar_section through fea.sections)."""
    from huntkit.fea.sections import from_spec
    import yaml as _y
    fr = _y.safe_load((PACK / "frame.yaml").read_text())
    sec = None
    for k in ("bar_section",):
        for v in _walk(fr):
            if isinstance(v, dict) and k in v:
                sec = from_spec(v[k])
                break
    L = 230.0
    out = {}
    for k, xg in (("rev0_x95", 95.0), ("rev1", REVS[1]["guy_x"])):
        a = 115.0 - xg
        m_end = guy_n_factored * a * (L - a) / L
        m_mid = guy_n_factored * a * a / L
        row = {"a_mm": a, "m_end_nmm": round(m_end, 0), "m_mid_nmm": round(m_mid, 0)}
        if sec is not None:
            I = float(getattr(sec, "Iy", getattr(sec, "I", 0.0)) or 0.0)
            if I > 0:
                row["sigma_mpa"] = round(max(m_end, m_mid) * (BAR_OD / 2.0) / I, 1)
                row["I_mm4"] = round(I, 0)
        out[k] = row
    return out


def _walk(o):
    yield o
    if isinstance(o, dict):
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


# ---------------------------------------------------------------------------------------------------------- results
RESULT = HERE / "corrie_f_result.json"
SCREENS = ROOT / "outputs" / "screens"
PREFIX = "20261111_BL011_"


def _sim():
    sys.path.insert(0, str(HERE / "corrie_f_sim"))
    import corrie_f_sim as S
    return S


def sim_table() -> dict:
    """CG (mass-weighted with the add-ons, as simulated, and with the BL-002 rounding bias), volume, R-28 per torso."""
    S = _sim()
    out = {}
    for t in S.TORSOS:
        r = S.get("F", t)
        if not r:
            continue
        out[str(t)] = {cn: {k: r["cases"][cn][k] for k in ("converged", "rounding_mm", "closed_L", "cg_y", "cg_y_biased",
                                                             "cg_z", "seam", "seam_n_mm", "seam_sf", "loads_1g")}
                       for cn in ("fill", "meat") if cn in r["cases"]}
        out[str(t)]["r28"] = {cn: {k: r["r28"][cn][k] for k in ("worst_contact_deg", "as_coded_deg", "pass",
                                                                 "wall_toward_head_above_bar_mm")}
                              for cn in r.get("r28", {})}
    return out


FEATURES = [
    "Shell S15 (BL-009): 394 mm full-width box tapering to 360 mm at the collar seam, depth 160 / 205 mm, collar seam z 745; "
    "plus a 30 mm top setback (second Z-fold in B-01, z 631-745) that holds the bag top back for R-28 at 23 in",
    "Team B fabrics: ULTRAGrid body and hem, 70D collar, ULTRA 200X floor, ULTRA 200 frame panel; each swap carries its "
    "fabric_swap_evidence gate",
    "Two door options to the same level: D1 floor-hinged full-face tailgate (team C, lid straps H1-H3) and D2 camo-blade "
    "door (team E rule on S15's square corners: panel line = camo break = zip)",
    "Team A hip-reach pockets FP-L / FP-R on the gussets (snacks + GPS left, 2nd bottle right) and the pole quiver",
    "Straps BL-003 REC: IM1-IM3 and US1/US2 at 25 mm, sewn loops girth-hitched on the IM eyes; no wings: W1-W3 are the "
    "only external straps (compression, tripod, float wrap)",
    "Attachment BL-004 REC: no crown hood, no ladders, no IM2 bag hooks; guys toggled on (bright toggle + hang-tag: "
    "'guys on' is a carry rule); B-17 70 mm. Rev 1 (BL-022): the guys toggle through the B-25 bridle tabs at x +/-52 on "
    "the top bar, clear of the lifter lugs at x +/-105",
    "Rev 1 (BL-022): B-26 tripod keeper, one 3 mm shock cord across the right gusset, so opening the door (W1/W2 "
    "unhooked) never frees the tripod",
    "BL-010 hardware: 22 g wiregate carabiners at the IM3 bag hooks, IM3 meat free end and B-24; rated G-hooks and heavy "
    "ladder locks on W1-W3 and the guys",
    "Add-ons outside base: scope pod (left gusset), top pouch 2.7 L, rain fly (base pocket stays), meat liner (team D "
    "SWAP slab), float kit B-24; bottle holster is a belt add-on",
    "Quiet: no hook-and-loop, coil zips, solid colours with camo on the blades / flaps, kick bands and FP mouth bands",
]


def risks(s: dict) -> list:
    d2 = s["doors"]["D2"]["goal"]
    return [
        f"Mass goal missed: like-for-like saving {d2['saving_g']:.0f} g (D2) against the 350 g target; base-to-base "
        f"{-s['doors']['D2']['configs']['base']['delta_g']:.0f} g (section 2 of the write-up names each shortfall)",
        "Fabric gates: ULTRAGrid swatch (owner), ULTRA 200X PT-3 + 50 mm strip test, 70D stock weighed; with today's "
        "fabrics the saving drops by about 60 g",
        "Hip-reach pocket reach on S15 is an ASSUMPTION (team A's EV-3): the mouth sits on the gusset at x +/-197, outside "
        "A's 320 mm base; FP-R, the tripod under W1/W2 and the bow cam cup IMP-8 share the right gusset (fit check)",
        "S15 is 16-17 in wide loaded at hip and elbow height (BL-009 gate: elbow swing and rifle-sling check)",
        "R-28 at 23 in rests on the 30 mm top setback (sim) and the corrected method (attach_system design_face); "
        "protractor check on the first prototype at the L crown kit",
        "'Guys on' is a carry rule: without them the 15 in meat CG exceeds rev C (BL-004)",
        "D2: the zip runs beside a 630D camo blade on a square corner (no fold, unlike E's chamfer) - untested; D1: the lid "
        "drops to the ground and needs H1-H3 cinched before zipping (procedure)",
        "Coarse-mesh CG (h 40 mm); the closed door is modelled on CORRIE's cut lines for both options (ASSUMPTION DOOR-SIM)",
    ]


def result(write: bool = True, screenshots: list | None = None) -> dict:
    import corrie_f_loadout as CFL
    from huntkit.mass import ledger as L
    s = summary("M")
    door = DOOR_DEFAULT
    d = s["doors"][door]
    st = sim_table()
    lo = json.loads((ROOT / "outputs" / "loadout" / "corrie_f_loadout.json").read_text()) \
        if (ROOT / "outputs" / "loadout" / "corrie_f_loadout.json").exists() else None
    acc = {}
    if lo:
        for dk in DOORS:
            mm = lo[dk]["misses"]
            acc[dk] = {k: max(len(mm[sz][k]["hourly"]) for sz in mm) for k in CFL.LOADOUTS}
            acc[dk + "_all_M"] = {k: mm["M"][k]["all"] for k in CFL.LOADOUTS}
    vol = [st[t]["fill"]["closed_L"] for t in st if "fill" in st[t]]
    mt = d["configs"]["meat_trip"]
    out = {
        "team": "BL-011", "name": NAME,
        "one_line": "S15 box in team B's fabrics with A's hip-reach pockets, BL-003/004/010 straps and attachment, "
                    "a 30 mm top setback for R-28, and two door options (D1 tailgate, D2 camo-blade door).",
        "door_headline": door,
        "bag_system_g": d["configs"]["meat_trip"]["bag_system_g"],
        "bag_system_note": "ledger BAG_SYSTEM (bag_shell + bag_pockets + pouch + fly + straps_compression), every add-on "
                           "booked; CORRIE B.2 " + str(L.corrie_bag_system()),
        "bag_side_g": mt["bag_side_g"], "bag_side_g_base": d["configs"]["base"]["bag_side_g"],
        "bag_side_g_as_hunted": d["configs"]["as_hunted"]["bag_side_g"],
        "corrie_b2_bag_side_g": {c: d["configs"][c]["corrie_b2_bag_side_g"] for c in CFGS},
        "goal": d["goal"],
        "pack_mass_M_g": mt["pack_h1_g"],
        "pack_mass_M_note": "ledger corrie_b2_h1 total at belt M - CORRIE B.2 bag side + CORRIE F bag side (meat trip, all "
                            "items); suspension as the ledger books it today (BL-005/006/017 diets not yet in the "
                            "ledger: BL-013)",
        "pack_mass_M_by_config_g": {c: d["configs"][c]["pack_h1_g"] for c in CFGS},
        "volume_L": round(float(np.mean(vol)), 2) if vol else None,
        "volume_note": "cloth-sim fill case (68 kg) closed volume, mean of 15/19/23 in; pouch, pockets and pod not counted",
        "fill_height_in": s["geometry"]["fill_height_in"],
        "pieces": d["metrics"]["pieces_base"], "curved_seams": d["metrics"]["curved_seams"],
        "zip_mm_total": d["metrics"]["zip_mm_with_pouch"], "beginner_hours": d["metrics"]["beginner_hours_with_addons"],
        "cg_fill_mm": {t: st[t]["fill"]["cg_y"] for t in st if "fill" in st[t]},
        "cg_meat_mm": {t: st[t]["meat"]["cg_y"] for t in st if "meat" in st[t]},
        "cg_fill_biased_mm": {t: st[t]["fill"]["cg_y_biased"] for t in st if "fill" in st[t]},
        "cg_meat_biased_mm": {t: st[t]["meat"]["cg_y_biased"] for t in st if "meat" in st[t]},
        "cg_method": "clothsim",
        "r28": {t: st[t]["r28"] for t in st},
        "access_misses": acc.get(door), "access_misses_by_door": {k: v for k, v in acc.items()},
        "doors": {dk: {"zip_mm": s["doors"][dk]["metrics"]["door_zip_mm"],
                       "clear_width_mm": s["doors"][dk]["metrics"]["clear_width_mm"],
                       "beginner_hours_base": s["doors"][dk]["metrics"]["beginner_hours_base"],
                       "pieces_base": s["doors"][dk]["metrics"]["pieces_base"],
                       "curved_seams": s["doors"][dk]["metrics"]["curved_seams"],
                       "bag_side_g": {c: s["doors"][dk]["configs"][c]["bag_side_g"] for c in CFGS},
                       "goal": s["doors"][dk]["goal"]} for dk in DOORS},
        "today_fabrics_bag_side_g": {dk: {c: s["doors"][dk]["today_fabrics"][c]["bag_side_g"] for c in CFGS} for dk in DOORS},
        "corrie_b2_metrics": s["corrie_b2_metrics"],
        "features": FEATURES, "risks": risks(s), "screenshots": screenshots or [],
    }
    if write:
        RESULT.write_text(json.dumps(out, indent=1, default=_j))
    return out


# ---------------------------------------------------------------------------------------------------------- plots
SYS_COL = {"bag_shell": "#8a5a2b", "bag_pockets": "#b07a3f", "pouch": "#c99a5b", "fly": "#dcbf8a",
           "straps_meat": "#7a2e2e", "straps_compression": "#a8473a", "attachment": "#4a5d7a"}


def plot_mass(path: Path, s: dict | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    s = s or summary("M")
    fig, ax = plt.subplots(figsize=(11, 6.6), dpi=100)
    x, labels = 0, []
    for cfg in CFGS:
        cols = [("CORRIE B.2", s["doors"]["D2"]["configs"][cfg]["corrie_b2_by_system"]),
                ("F · D1", s["doors"]["D1"]["configs"][cfg]["by_system"]),
                ("F · D2", s["doors"]["D2"]["configs"][cfg]["by_system"])]
        for lab, bs in cols:
            y = 0.0
            for k in BAG_SIDE:
                ax.bar(x, bs[k], bottom=y, color=SYS_COL[k], edgecolor="white", width=0.8,
                       label=k.replace("_", " ") if x == 0 else None)
                y += bs[k]
            ax.text(x, y + 15, f"{y:.0f} g\n{y / OZ:.1f} oz", ha="center", va="bottom", fontsize=9, weight="bold")
            labels.append((x, lab))
            x += 1
        ax.text(x - 2, -170, cfg.replace("_", " ").upper(), ha="center", fontsize=11, weight="bold")
        x += 0.8
    ax.set_xticks([l[0] for l in labels], [l[1] for l in labels], fontsize=9)
    b2 = s["doors"]["D2"]["goal"]["corrie_b2_g"]
    ax.axhline(b2 - 350, color="#c0392b", ls="--", lw=1.2)
    ax.text(-0.4, b2 - 350 + 12, f"goal: CORRIE B.2 - 350 g = {b2 - 350:.0f} g (meat-trip basis)", ha="left",
            color="#c0392b", fontsize=9)
    ax.set_ylabel("bag side, g (ledger systems, belt M)")
    ax.set_ylim(-200, max(b2, 1700) * 1.12)
    g1, g2 = s["doors"]["D1"]["goal"], s["doors"]["D2"]["goal"]
    ax.set_title(f"BL-011 CORRIE F bag side vs CORRIE B.2 (ledger). Like-for-like saving: D1 {g1['saving_g']:.0f} g, "
                 f"D2 {g2['saving_g']:.0f} g (target 350 g: NOT met)", fontsize=11)
    ax.legend(ncol=4, fontsize=8, loc="upper left", frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return path


def _outline(ax, piece, color, fill, lw=1.2, label=None, zorder=2):
    from matplotlib.patches import Polygon as MP
    pts = [tuple(q) for q in piece.outline]
    ax.add_patch(MP(pts, closed=True, facecolor=fill, edgecolor=color, lw=lw, label=label, zorder=zorder))


def plot_doors(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    c = make()
    fig, axs = plt.subplots(1, 3, figsize=(15, 7.2), dpi=95, gridspec_kw={"width_ratios": [1, 1, 0.8]})
    zk, S, A = _face_xy(c)
    camo, body = "#6b7d4f", "#c8c2b0"
    with frame_face(c):
        for ax, door in zip(axs[:2], DOORS):
            if door == "D2":
                P = d2_pieces(c)
                for pc, col, lab in ((P["blade"], camo, "camo blade U (630D printable)"), (P["door"], body, "door (ULTRAGrid)"),
                                     (P["band"], "#a39e8a", "hinge band (ULTRAGrid)")):
                    _outline(ax, pc, "k", col, label=lab)
                zp = np.asarray(P["door"].edge("zip").points)
            else:
                P = d1_pieces(c)
                for pc, col, lab in ((P["lid"], body, "lid (ULTRAGrid), floor hinge"), (P["band"], "#a39e8a",
                                                                                      "hinge band with corner tongues")):
                    _outline(ax, pc, "k", col, label=lab)
                zp = np.asarray(P["lid"].edge("zip").points)
                for z in D1["hoop_z"]:
                    ax.plot([-A(z) - 15, A(z) + 15], [S(z), S(z)], color="#333", lw=2.5, alpha=0.7)
                ax.plot([], [], color="#333", lw=2.5, label="lid straps H1-H3 (25 mm)")
                ax.plot([A(BC.Z0) - 17, A(D1["z_top"] - D1["r"]) - 17], [0, S(D1["z_top"] - D1["r"])], color=camo, lw=6,
                        alpha=0.8, label="camo storm flaps on the zip legs")
                ax.plot([-A(BC.Z0) + 17, -A(D1["z_top"] - D1["r"]) + 17], [0, S(D1["z_top"] - D1["r"])], color=camo, lw=6,
                        alpha=0.8)
            ax.plot(zp[:, 0], zp[:, 1], color="#d35400", lw=2.4, label=f"#10 door zip {P['zip_mm']:.0f} mm", zorder=4)
            for k, z in STATIONS.items():
                w = clear_width(c, door, z)
                ax.annotate("", (w / 2, S(z)), (-w / 2, S(z)), arrowprops=dict(arrowstyle="<->", color="#1f4e79", lw=1.3))
                ax.text(0, S(z) + 8, f"{k} clear {w:.0f} mm", ha="center", fontsize=9, color="#1f4e79", weight="bold")
            ax.set_aspect("equal")
            ax.set_xlim(-260, 260)
            ax.set_ylim(-40, S(c.z_c) + 60)
            m = build_metrics(door)
            ax.set_title(f"{door}: {'team C full-face tailgate' if door == 'D1' else 'team E camo-blade door on S15'}\n"
                         f"zip {m['door_zip_mm']:.0f} mm, {m['beginner_hours_base']:.1f} h base, {m['pieces_base']} pieces, "
                         f"{m['curved_seams']} curved seam", fontsize=10)
            ax.set_xlabel("aft face, flat (mm)")
            ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False)
            ax.grid(alpha=0.2)
        axs[0].set_ylabel("unrolled height above the floor seam (mm)")
        # side profile: frame face and aft face, S15 vs CORRIE F
        ax = axs[2]
        zz = np.linspace(BC.Z0, c.z_c, 200)
        c0 = make(0.0)
        ax.plot(_YF0(zz), zz, color="#555", lw=1.2, ls="--", label="S15 frame face (BL-009)")
        ax.plot(c.frame_y(zz), zz, color="#1f4e79", lw=2.2, label=f"CORRIE F frame face (+{c.setback:.0f} mm Z-fold)")
        ax.plot(c.y_front(zz), zz, color="#8a5a2b", lw=2.2, label="aft face (S15, unchanged)")
        ax.fill_betweenx(zz, c.frame_y(zz), c.y_front(zz), color="#c8c2b0", alpha=0.5)
        ax.axhline(BC.Z_SH, color="#999", lw=0.8)
        ax.axhline(c.z_c, color="#999", lw=0.8)
        ax.text(c.y_front([c.z_c])[0] + 5, c.z_c, "collar seam z 745", fontsize=8, va="bottom")
        ax.text(c.y_front([BC.Z_SH])[0] + 5, BC.Z_SH, "shoulder crease z 631", fontsize=8, va="top")
        ax.set_aspect("equal")
        ax.set_xlabel("y aft of the stay datum (mm)")
        ax.set_title(f"Side section: top setback for R-28\ndepth at collar seam {float(c0.depth([c.z_c])[0]):.0f} -> "
                     f"{float(c.depth([c.z_c])[0]):.0f} mm", fontsize=10)
        ax.legend(fontsize=7.5, loc="lower right")
        ax.grid(alpha=0.2)
    fig.suptitle("BL-011 CORRIE F: the two door options (flat aft-face pieces, clear width at IM1-IM3) and the top setback",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_cg(path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S = _sim()
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.6), dpi=100)
    ax = axs[0]
    for cn, col, lim in (("fill", "#4a6fa5", 205.0), ("meat", "#a8473a", 190.0)):
        ts, ys, yb = [], [], []
        for t in S.TORSOS:
            r = S.get("F", t)
            if r and cn in r["cases"]:
                ts.append(t)
                ys.append(r["cases"][cn]["cg_y"])
                yb.append(r["cases"][cn]["cg_y_biased"])
        ax.plot(ts, ys, "o-", color=col, label=f"{cn} CG as simulated")
        ax.plot(ts, yb, "s:", color=col, alpha=0.7, label=f"{cn} + rounding bias")
        for t, y in zip(ts, yb):
            ax.text(t + 0.15, y, f"{y:.1f}", color=col, fontsize=9, va="center")
        ax.axhline(lim, color=col, ls="--", lw=1)
        ax.text(15, lim + 1.5, f"rev C {cn} limit {lim:.0f} mm", color=col, fontsize=8)
    ax.set_xticks(list(S.TORSOS), [f"{t} in" for t in S.TORSOS])
    ax.set_ylabel("bag-load CG y, mm aft of the stay datum (with pouch + scope pod)")
    ax.set_title("CORRIE F cloth sim (coarse h 40), add-ons on")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    ax = axs[1]
    w = 0.2
    for i, (lab, var, key, col) in enumerate((("S15, method as coded", "F0", "as_coded_deg", "#bbb"),
                                              ("S15, method fixed", "F0", "worst_contact_deg", "#888"),
                                              ("CORRIE F, method fixed", "F", "worst_contact_deg", "#1f4e79"))):
        for j, t in enumerate(S.TORSOS):
            r = S.get(var, t)
            if not r or "r28" not in r:
                continue
            v = min(r["r28"][cn][key] for cn in ("fill", "meat"))
            ax.bar(j + (i - 1) * w, v, w, color=col, label=lab if j == 0 or (var == "F0" and t == 23) else None)
            ax.text(j + (i - 1) * w, v + 0.5, f"{v:.0f}", ha="center", fontsize=8)
    ax.axhline(30, color="#c0392b", ls="--")
    ax.text(-0.4, 30.6, "R-28: first head contact must be > 30 deg", color="#c0392b", fontsize=8)
    ax.set_xticks(range(len(S.TORSOS)), [f"{t} in" for t in S.TORSOS])
    ax.set_ylabel("first head contact, deg (worst of fill / meat)")
    ax.set_ylim(0, 42)
    ax.set_title("R-28 head clearance (S15 shown where simulated)")
    h, l = ax.get_legend_handles_labels()
    seen = {}
    for hh, ll in zip(h, l):
        seen.setdefault(ll, hh)
    ax.legend(seen.values(), seen.keys(), fontsize=8, loc="lower left")
    fig.suptitle("BL-011 CORRIE F: CG against HA-LS-1 rev C and R-28 at the three torso settings", fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def bl022_table() -> dict:
    """BL-022 numbers from the stored sim rows: R-28 coarse / fine for rev 0 and rev 1, the guys-off misuse case, and
    rev 1's coarse CG / volume / loads. Rows that are not run yet are None."""
    S = _sim()
    rows = S.load_results()["rows"]
    FACTOR = 3.0                      # attach_diet.FACTOR: HA-LS-1 C5 / C2 2.0 g x 1.5 on the 1 g simulated force

    def r28(k):
        r = rows.get(k)
        if not r or "r28" not in r:
            return None
        return {cn: {"deg": r["r28"][cn]["worst_contact_deg"], "gap30_mm": r["r28"][cn]["worst_gap_30_mm"],
                     "pass": r["r28"][cn]["pass"]} for cn in ("fill", "meat")}

    def worst(x):
        return None if x is None else min(x["fill"]["deg"], x["meat"]["deg"])
    r28t = {}
    for t in S.TORSOS:
        r28t[t] = {"rev0_coarse": r28(f"Fr0_PR{t}"), "rev0_fine": r28(f"Fr0_PR{t}_fineFM"),
                   "rev1_coarse": r28(f"F_PR{t}"), "rev1_fine": r28(f"F_PR{t}_fineFM")}
        r28t[t]["worst"] = {k: worst(v) for k, v in list(r28t[t].items())}
    fine = [r28t[t]["worst"]["rev1_fine"] for t in S.TORSOS]
    acc = {"target_deg": 31.0, "rev1_fine_deg": fine,
           "met": all(v is not None and v >= 31.0 for v in fine),
           "shortfall_deg": {t: round(31.0 - v, 1) for t, v in zip(S.TORSOS, fine) if v is not None and v < 31.0}}

    def case(k, cn):
        r = rows.get(k)
        if not r or cn not in r["cases"]:
            return None
        c = r["cases"][cn]
        im3 = max(c["loads_1g"].get("hook_im520_R", 0.0), c["loads_1g"].get("hook_im520_L", 0.0))
        guy = max(c["loads_1g"].get("TG_R", 0.0), c["loads_1g"].get("TG_L", 0.0))
        return {"converged": c["converged"], "rounding_mm": c["rounding_mm"], "cg_y": c["cg_y"], "cg_y_biased": c["cg_y_biased"],
                "cg_z": c["cg_z"], "closed_L": c["closed_L"], "im3_1g_n": im3, "im3_factored_n": round(FACTOR * im3, 0),
                "guy_1g_n": guy, "mesh_h": r["mesh_h"]}
    goff = case("F_PR15_goff", "meat")
    gon = case("F_PR15", "meat")
    misuse = None
    if goff:
        misuse = {"guys_off": goff, "guys_on": gon, "limit_meat_mm": 190.0,
                  "exceeds_rev_c": goff["cg_y_biased"] > 190.0,
                  "bl004_basis_factored_n": 1702.0,       # attachment_diet.md section 5 (CORRIE 15 in guys-off, 567 N x 3.0)
                  "above_bl004_basis": goff["im3_factored_n"] > 1702.0}
    rev1 = {t: {cn: case(f"F_PR{t}", cn) for cn in ("fill", "meat")} for t in S.TORSOS}
    rev0 = {t: {cn: case(f"Fr0_PR{t}", cn) for cn in ("fill", "meat")} for t in S.TORSOS}
    finec = {f"{v}_{t}": {cn: case(f"{v}_PR{t}_fineFM", cn) for cn in ("fill", "meat")}
             for v in ("Fr0", "F") for t in S.TORSOS if f"{v}_PR{t}_fineFM" in rows}
    guys = [c["guy_1g_n"] for d in list(rev1.values()) + list(finec.values()) for c in d.values() if c]
    return {"r28": r28t, "acceptance": acc, "guys_off": misuse, "rev1_coarse": rev1, "rev0_coarse": rev0, "fine": finec,
            "guy_max_1g_n": max(guys) if guys else None,
            "guy_max_factored_n": round(FACTOR * max(guys), 0) if guys else None}


def bl022_summary() -> dict:
    t = bl022_table()
    g = t["guy_max_factored_n"] or 244.0
    with revision(1):
        k2, k1 = tripod_keeper(door="D2"), tripod_keeper(door="D1")
        geo = geometry()
    return {"revision": REVISION, "revs": REVS, "sims": t, "guy_lifter": guy_lifter_check(), "guy_lines": guy_geometry(),
            "bridle": guy_bridle(), "tripod_keeper": {"D2": k2, "D1": k1}, "top_bar_guy_moment": top_bar_guy_moment(g),
            "geometry_rev1": {k: v for k, v in geo.items() if k != "profile"}}


def plot_bl022(path: Path) -> Path:
    """R-28 coarse vs fine, rev 0 (before) and rev 1 (after), plus the loaded frame-side face above the bar at 23 in."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S = _sim()
    t = bl022_table()
    rows = S.load_results()["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.6), dpi=100, gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axs[0]
    series = (("rev 0 coarse (h 40)", "rev0_coarse", "#b9c6d6"), ("rev 0 fine (h 25)", "rev0_fine", "#6d8fb3"),
              ("rev 1 coarse (h 40)", "rev1_coarse", "#d9b48a"), ("rev 1 fine (h 25)", "rev1_fine", "#8a5a2b"))
    w = 0.2
    for i, (lab, key, col) in enumerate(series):
        for j, tor in enumerate(S.TORSOS):
            v = t["r28"][tor]["worst"][key]
            x = j + (i - 1.5) * w
            if v is None:
                ax.text(x, 1.0, "not\nrun", ha="center", fontsize=6.5, color="#777")
                continue
            ax.bar(x, v, w, color=col, label=lab if j == 0 else None, edgecolor="white")
            ax.text(x, v + 0.5, f"{v:.0f}", ha="center", fontsize=8)
    ax.axhline(30, color="#c0392b", ls="--", lw=1)
    ax.axhline(31, color="#c0392b", ls=":", lw=1)
    ax.text(-0.45, 30.3, "> 30 deg required", color="#c0392b", fontsize=8, va="bottom")
    ax.text(1.55, 31.3, "BL-022 target 31 deg (1 deg margin)", color="#c0392b", fontsize=8, va="bottom")
    ax.set_xticks(range(len(S.TORSOS)), [f"{x} in" for x in S.TORSOS])
    ax.set_ylim(0, 42)
    ax.set_ylabel("first head contact, deg (worst of fill / meat)")
    ax.set_title(f"R-28 head clearance: rev 0 {REVS[0]['setback']:.0f} mm setback, guys x +/-{REVS[0]['guy_x']:.0f}; "
                 f"rev 1 {REVS[1]['setback']:.0f} mm, guys x +/-{REVS[1]['guy_x']:.0f}", fontsize=9.5)
    ax.legend(fontsize=8, loc="upper center", ncol=2)
    ax.set_ylim(0, 48)
    ax.grid(axis="y", alpha=0.25)
    ax = axs[1]
    bg = _bg()
    cs = min(bg.crown_settings(), key=lambda q: abs(q["torso_in"] - 23))
    zt = cs["crown_top_z"]
    for key, lab, col, ls in (("Fr0_PR23", "rev 0 coarse", "#b9c6d6", "-"), ("Fr0_PR23_fineFM", "rev 0 fine", "#6d8fb3", "-"),
                              ("F_PR23", "rev 1 coarse", "#d9b48a", "--"), ("F_PR23_fineFM", "rev 1 fine", "#8a5a2b", "--")):
        r = rows.get(key)
        if not r:
            continue
        for cn, mk in (("meat", "o"),):
            pr = [(w[0], w[1]) for w in r["cases"][cn]["profile"] if w[0] >= zt - 150]
            if pr:
                ax.plot([q[1] for q in pr], [q[0] for q in pr], ls, marker=mk, ms=3, color=col, label=f"{lab}, meat: loaded face")
    for var, lab, col in (("Fr0", "rev 0 drafted face (sim mesh)", "#999"), ("F", "rev 1 drafted face (sim mesh)", "#333")):
        if var == "F" and REVS[1]["setback"] == REVS[0]["setback"]:
            continue
        dr = sorted((z, y) for z, y in S.drafted_face(var, 23).items() if z >= zt - 150)
        ax.plot([q[1] for q in dr], [q[0] for q in dr], color=col, lw=1.2, label=lab)
    yb = float(bg.y_on_axis(zt) + bg.TOP_BAR_AFT)
    ax.add_patch(plt.Circle((yb, zt), 9.0, color="#222"))
    ax.text(yb + 12, zt - 8, "crown top bar (23 in)", fontsize=8)
    ax.set_xlabel("y, mm (head side <- -> aft)")
    ax.set_ylabel("z, mm")
    ax.set_title("23 in: frame-side face above the crown bar, as simulated", fontsize=9.5)
    ax.legend(fontsize=7, loc="upper left")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=0.25)
    acc = t["acceptance"]
    fig.suptitle("BL-022 CORRIE F rev 1: R-28 on the fine mesh "
                 + ("meets 31 deg at 15 / 19 / 23 in" if acc["met"] else
                    (f"short by {acc['shortfall_deg']} deg" if acc["shortfall_deg"] else "pending (runs missing)")),
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def all_plots() -> list:
    SCREENS.mkdir(parents=True, exist_ok=True)
    return [plot_mass(SCREENS / f"{PREFIX}1.png"), plot_doors(SCREENS / f"{PREFIX}2.png"), plot_cg(SCREENS / f"{PREFIX}3.png")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="M")
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bl022", action="store_true", help="BL-022 rev 1 summary + screenshot 20261111_BL022_1.png")
    a = ap.parse_args(argv)
    if a.bl022:
        SCREENS.mkdir(parents=True, exist_ok=True)
        print(json.dumps(bl022_summary(), indent=1, default=_j))
        print(plot_bl022(SCREENS / "20261111_BL022_1.png"))
        return
    s = summary(a.size)
    print(json.dumps(s, indent=1, default=_j))
    if a.rows:
        for r in parts(a.size):
            print(f"{r['system']:18s} {r['cfg']:9s} {r['g']:8.2f}  {r['name'][:100]}")
    if a.json:
        shots = all_plots()
        result(True, [str(Path(x).relative_to(ROOT)) for x in shots])


if __name__ == "__main__":
    main()
