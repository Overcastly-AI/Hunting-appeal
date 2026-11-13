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
from huntkit.patterns.piece import EdgeRef  # noqa: E402

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
# x +/-100; tripod held by W1/W2 only). rev 1 = BL-022 (doc section 12): setback checked on the FINE mesh (kept at 30 mm), guys moved
# inboard to a bridle clear of the lifter lugs, a shock-cord tripod keeper on the right gusset. ``revision(0)`` gives
# rev 0 back exactly (tests).
REVS = {0: {"setback": 30.0, "guy_x": 100.0, "guy_bridle": False, "tripod_keeper": False},
        1: {"setback": 30.0, "guy_x": 52.0, "guy_bridle": True, "tripod_keeper": True},
        2: {"setback": 30.0, "guy_x": 52.0, "guy_bridle": True, "tripod_keeper": True, "guy_port": True},
        3: {"setback": 30.0, "guy_x": 52.0, "guy_bridle": True, "tripod_keeper": True, "guy_port": True, "crown_lid": True,
            "crown_w": 25.0, "crown_kits": True}}
# BL-031 (owner 2026-11-12): rev 3's crown straps are 25 mm again and cut PER CROWN KIT (``crown_kit_straps``), with a
# ladder lock at each end and the tail rule (``TAIL_RULE_MM``). BL-030's 20 mm diet stays as history in
# ``crown_strap_diet`` (its ``chosen`` is the 20 mm option BL-030 adopted).
# rev 3 = BL-029 (doc section 14), ADOPTED by the owner 2026-11-12 and the MODULE DEFAULT since BL-030 (doc section 15):
# rev 2 + the B-29 crown lid on two B-28 crown straps (B-25 bridle -> over the roll and the lid -> the hinge band),
# replacing the 2.7 L top pouch. BL-030 put the crown straps on a diet (``crown_w`` 20 mm, cut from the rolled top:
# ``crown_strap_diet``); BL-029's 25 mm straps stay reproducible as ``crown_straps(25.0)``.
# rev 2 = BL-028 (doc section 13): the guy goes through a lapped port B-27 in the frame face and runs INSIDE the bag to
# B-22 (turned to the inside). ``with revision(2):`` gives its parts. Rev 1's straight guy was a model artefact (it ran
# through the bag); its real path wraps the bag's side. Revs 0-2 stay reproducible with ``with revision(n):``.
REVISION = 3
TOP_SETBACK_MM = REVS[REVISION]["setback"]   # DECISION (R-28, doc sections 5 / 12): sized by the corrie_f_sim R-28 runs
GUY_X = REVS[REVISION]["guy_x"]               # DECISION (BL-022 S6, doc section 12.3): guy bar-end centre, x +/- mm


def sim_rev(n: int | None = None) -> int:
    """The cloth-sim shell revision of rev ``n`` (default: the current one). Revs 1-3 share one simulated shell (30 mm
    setback, guys at x +/-52 on the B-25 bridle): rev 2's port and rev 3's crown straps are corrie_f_sim ROUTES on the
    rev 1 shell, so their runs live in the ``F_r1_*`` folders (BL-025 naming). Rev 0 has its own (guys at x +/-100)."""
    n = REVISION if n is None else n
    return 0 if n == 0 else 1


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


class PolyEdge(EdgeRef):
    """A seam side made of a raw polyline on a real piece (part of an edge): an EdgeRef whose points are given, so
    ``check_seams`` and ``bag_concepts.metrics`` treat it like any edge (BL-033; was patterns_corrie_f_rev3.VEdge)."""

    def __init__(self, piece, pts, name):
        object.__setattr__(self, "piece", piece)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "reverse", False)
        object.__setattr__(self, "_pts", [tuple(map(float, p)) for p in pts])

    @property
    def points(self):
        return self._pts

    @property
    def length(self):
        p = np.asarray(self._pts, float)
        return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0

    @property
    def label(self):
        return f"{self.piece.piece_id}.{self.name}"

    def reversed(self):
        return PolyEdge(self.piece, self._pts[::-1], self.name)


def d2_inner_split(c, U) -> dict:
    """The D2 blade U inner edge split at the hinge (z 650): hi R (band side) | door zip run | hi L."""
    _, S, A = _face_xy(c)
    zh = D2["z_hinge"]
    yh, xh = S(zh), A(zh) - float(blade_w(c, zh))
    inner = U.edge_points("inner")
    hits = [i for i, (x, y) in enumerate(inner) if abs(y - yh) < 1e-6 and abs(abs(x) - xh) < 1e-6]
    iR, iL = hits[0], hits[-1]
    return {"hiR": inner[:iR + 1], "mid": inner[iR:iL + 1], "hiL": inner[iL:]}


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
                _seam(HB.edge("bottom"), DR.edge("hinge"), "hinge band | door (door hinge, z 650)", "seared"),
            ]
            # BL-033: the real pairs (were three self-paired placeholders): the blade U inner edge split at the hinge
            # (z 650) into hi R | door zip run | hi L, each sewn in the door's / band's direction
            sp = d2_inner_split(c, U)
            b.extra["d2_inner_split"] = sp
            b.seams += [
                _seam(DR.edge("zip"), [PolyEdge(U, sp["mid"][::-1], "inner (door zip run)")],
                      "door | blade U (#10 zip, R 55 corners)", "zip"),
                _seam(HB.edge("right"), [PolyEdge(U, sp["hiR"][::-1], "inner hi R")],
                      "hinge band R | blade U", "seared"),
                _seam(HB.edge("left"), [PolyEdge(U, sp["hiL"][::-1], "inner hi L")],
                      "hinge band L | blade U", "seared"),
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


# ---- B-01 fairlead swell windows (BL-033). Windows 50 wide centred on the stay x (bag_concepts.STAY_X), (crest z,
# lower, upper) = patterns_v31.SWELLS. DECISION H-1 (BL-033 task 1): no hinge window. The hinge window (z 40-130)
# lay over the B-18 hinge-eye doubler (z 35-80), whose lower edge in the floor seam IS the hinge load path (A5:
# HE box-X through B-18 + B-01, B-18 seam 80 mm into the B-05 strip): a window there cuts B-01 from under the box-X.
# The hinge cleat bears on B-18 instead (``hinge_standoff``: 3.5 mm into the 20 mm B-01 offset, the same as the
# under-strap cleat US2, which the v3.1 patterns accepted with no swell).
SWELL_W = 50.0
SWELL_WINDOWS = {"im1": (BC.STATIONS["im1"], 45.0, 45.0), "im2": (BC.STATIONS["im2"], 45.0, 45.0),
                 "im3": (BC.STATIONS["im3"], 58.0, 32.0)}
SWELL_WINDOWS_DROPPED = {"hinge": (62.0, 22.0, 68.0)}     # patterns_v31.SWELLS hinge (BL-032 drew it; H-1 removes it)
B18_RECT = (90.0, 45.0)                                  # attach_system.drawing_pieces B-18 90 x 45, lower edge at BC.Z0


def b01_flat_s(c: ShellF | None = None):
    """B-01 flat length coordinate s(z) (the unrolled frame face, as ``bag_concepts.frame_panel`` drafts it)."""
    c = c or make()
    with frame_face(c):
        zk = BC._kinks(c)
        s01 = BC.unroll(zk, BC.y_frame(zk))
    return lambda z: float(np.interp(z, zk, s01))


def swell_windows(c: ShellF | None = None) -> list:
    """The B-01 swell windows as cut: [{station, side, x0, x1, y0, y1 (flat), area_mm2}]."""
    s01 = b01_flat_s(c)
    out = []
    for st, (zc, lo, hi) in SWELL_WINDOWS.items():
        for sx in (-1, 1):
            y0, y1 = s01(zc - lo), s01(zc + hi)
            out.append({"station": st, "side": "R" if sx > 0 else "L", "x0": sx * BC.STAY_X - SWELL_W / 2,
                        "x1": sx * BC.STAY_X + SWELL_W / 2, "y0": y0, "y1": y1, "z": (zc - lo, zc + hi),
                        "area_mm2": SWELL_W * (y1 - y0)})
    return out


def hinge_standoff() -> dict:
    """BL-033 task 1: what the hinge cleat does to B-01 with no swell, against US2 (no swell since v3.1). Fairlead proud
    of the stay = bag_attach HOLE_PROUD + HOLE_D / 2 + WALL_FRONT; stay radius frame_branch.stay_radius (attachment.yaml
    scale); B-01 at bag_attach.PANEL_OFFSET from the stay centre; B-18 thickness from the hypalon record."""
    import yaml
    from huntkit.gendesign import bag_attach as BA
    from huntkit.gendesign.frame_branch import stay_radius
    sc = float(yaml.safe_load((PACK / "attachment.yaml").read_text())["scale"])
    proud = BA.HOLE_PROUD + BA.HOLE_D / 2 + BA.WALL_FRONT
    out = {"proud_mm": round(proud, 2), "panel_offset_mm": BA.PANEL_OFFSET, "scale": sc,
           "b18_t_mm": _rec("hypalon_coated_nylon", "thickness_mm")}
    for k, z in (("hinge", 60.0), ("us2", 142.0)):
        r = float(stay_radius(z, sc))
        out[k] = {"z": z, "stay_r_mm": round(r, 2), "top_mm": round(r + proud, 2),
                  "push_mm": round(max(0.0, r + proud - BA.PANEL_OFFSET), 2)}
    out["hinge"]["push_with_b18_mm"] = round(out["hinge"]["push_mm"] + out["b18_t_mm"], 2)
    z0 = BC.Z0
    out["b18_z"] = (z0, z0 + B18_RECT[1])
    lo = SWELL_WINDOWS_DROPPED["hinge"]
    out["dropped_window_z"] = (lo[0] - lo[1], lo[0] + lo[2])
    out["overlap_z_mm"] = round(max(0.0, min(out["b18_z"][1], out["dropped_window_z"][1])
                                    - max(out["b18_z"][0], out["dropped_window_z"][0])), 1)
    win = swell_windows()
    out["b18_window_overlap_mm2"] = round(sum(max(0.0, min(w["x1"], sx * BC.STAY_X + B18_RECT[0] / 2)
                                                  - max(w["x0"], sx * BC.STAY_X - B18_RECT[0] / 2))
                                              * max(0.0, min(w["z"][1], z0 + B18_RECT[1]) - max(w["z"][0], z0))
                                              for w in win for sx in (-1, 1)), 1)
    out["nearest_window_above_b18_mm"] = round(min(w["z"][0] for w in win) - (z0 + B18_RECT[1]), 1)
    return out


def b01_net_g(c: ShellF | None = None, fabrics: str = "B", b01=None) -> dict:
    """B-01 booked net of its swell windows (BL-033: the windows are cut out; each swell B-13x is its own row)."""
    c = c or make()
    if b01 is None:
        with frame_face(c):
            b01 = BC.frame_panel(c)
    full = BC.piece_mass_g(b01)
    win = sum(w["area_mm2"] for w in swell_windows(c))
    return {"full_g": full, "windows": len(SWELL_WINDOWS) * 2, "window_mm2": win,
            "net_g": full - win * _gsm(b01.material_id) / 1e6}


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


FP_FACE_W = 165.0     # DECISION (BL-033 task 3): hip-reach pocket face 180 -> 165 mm. BL-032's pattern found the 180 mm
#                       face does not fit the gusset depth over z 150-380 with its inner edge 10 mm off the frame seam
#                       (clamped up to 15.5 mm); 165 fits at every height, so the pocket is a plain rectangle again.
FP_KEEP_MESH = True   # DECISION (BL-033): the mesh keeps team A's 260 mm width; the 15 mm the face loses goes into the two
#                       box pleats (2 x 40 -> 2 x 47.5). With the pleats unchanged (mesh 245) the arc model below gives
#                       1.78 L and the sheep8 2nd bottle misses FP-R (corrie_f_loadout, every belt size).


def _mesh_arc_area(w: float, L: float) -> float:
    """Cross-section of a stretch-mesh pocket: a mesh of width L sewn over a chord w, taken as a circular arc."""
    lo, hi = 1e-6, 2 * math.pi - 1e-6
    for _ in range(200):                      # bisection on L sin(th/2) / (th/2) = w
        th = 0.5 * (lo + hi)
        if L * math.sin(th / 2) / (th / 2) > w:
            lo = th
        else:
            hi = th
    R = L / th
    return R * R / 2 * (th - math.sin(th))


def fp_spec() -> dict:
    """Team A's evolve.FP on CORRIE F's 165 mm face. ASSUMPTION FP-ARC: the pocket's stretch capacity scales with its
    cross-section (mesh width over the sewn face as a circular arc, ``_mesh_arc_area``), never above team A's 2.0 L;
    the envelope's width dimension scales the same way. Settled by EV-3 on the prototype (1 L bottle + GPS + snacks,
    gloved, pack on)."""
    E = _A()
    fp = dict(E.FP)
    mesh = fp["w"] + fp["pleat"] if FP_KEEP_MESH else FP_FACE_W + fp["pleat"]
    k = min(1.0, _mesh_arc_area(FP_FACE_W, mesh) / _mesh_arc_area(fp["w"], fp["w"] + fp["pleat"]))
    env = fp["env_mm"]
    fp.update(w=FP_FACE_W, pleat=mesh - FP_FACE_W, cap_L=round(fp["cap_L"] * k, 2), cap_ratio=round(k, 3),
              env_mm=tuple(sorted((env[0], round(env[1] * k, 1), env[2]), reverse=True)), team_a_w=E.FP["w"])
    return fp


def hip_reach_pockets() -> list:
    """Team A's E-4 hip-reach pockets FP-L / FP-R, the same part (evolve.FP) moved from the wings' lower front corners
    to the gussets' lower front corners (the wings are deleted), z 150-380 (A's write-up height; IMP-8 stays below on
    the right, z 35-150). Plus E-5, the pole quiver (boot in FP-R's front pleat, grip loop at the gusset's top hard
    point). Mass by A's recipe from the records."""
    E = _A()
    FP, POLE, H = fp_spec(), E.POLE, BC.HOURS
    mesh = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (FP["h"] + 2 * SA_FLAT) * 1e-6 * _gsm(MESH)
    cord = 2 * (FP["w"] + FP["pleat"] + 60) / 1000 * SHOCK_GM
    band = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (25.0 + 2 * SA_FLAT) * 1e-6 * _gsm(CAMO)
    fp_h = 2 * H["cut_piece"] + 2 * (2 * FP["h"] + FP["w"]) / 1000 * H["straight_m"] + 2 * 0.25 * H["straight_m"] \
        + 4 * H["bartack"] + 0.3
    pole_g = POLE["cord_m"] * SHOCK_GM + CORDLOCK_G + POLE["tab_m"] * WEB25
    pole_h = 0.25 * H["straight_m"] + 2 * H["bartack"] + 0.1
    return [
        {"id": "FP-L/R", "name": f"hip-reach pockets FP-L / FP-R (team A E-4): power mesh {FP['w'] + FP['pleat']:.0f} x "
         f"{FP['h']:.0f} ({FP['w']:.0f} mm face), 2 box pleats, "
         "shock-cord top in a 25 mm camo mouth band, sewn to each gusset's lower front corner (z 150-380)",
         "mass_g": round(mesh + cord + band, 1), "hours": round(fp_h, 2), "pieces": 4, "seam_m": round(
             2 * (2 * FP["h"] + FP["w"] + 250) / 1000, 2), "z": (150.0, 380.0), "cap_L": FP["cap_L"], "env_mm": FP["env_mm"],
         "source": "evolve.FP at FP_FACE_W (fp_spec) + power_mesh_nylon_spandex, shock_cord_3mm, "
                   "polyester_ht_630d_printable records (A's recipe, cut + 8 mm SA)"},
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
    if REVS[REVISION].get("crown_lid"):          # BL-029 rev 3: crown lid + crown straps replace the top pouch
        out = rev3_addons(out)
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


# ---- F-01 rain fly for rev 3 (BL-033 task 5). A three-piece box cover: one spine strip (under the floor edge, up the
# aft face, up the rolled collar and the lid wall, over the lid to the frame side) and two side panels (gusset profile,
# then the roll and lid). Girths get FLY_EASE; lengths follow the bag's corner line, so the two seams match by
# construction. Free edges get a 20 mm elastic channel (v3.1 fly rule). Sized for the FULL rolled state (lid top
# z 1060, CROWN_ROLLED); smaller loads gather on the elastic.
FLY_MAT = "silicone_coated_poly_ripstop_40d"     # panels.yaml F-01
FLY_EASE = 1.10       # ASSUMPTION (patterns_v31.build_fly, 10 % ring ease over pockets and wraps); settled by the 1st fly
FLY_TUCK = 40.0       # ASSUMPTION: the hem tucks 40 mm under the floor edge (holds the fly down); same test
FLY_WRAP = 25.0       # ASSUMPTION: the side panels and the top wrap 25 mm round onto the frame side (v31: 0.08 of the
#                       frame half); same test
FLY_HEM = 20.0        # patterns_v31.build_fly: 20 mm channel hems, 6 mm elastic
FLY_SA = 10.0         # patterns_v31 SA_301
FLY_STATE = "full"    # CROWN_ROLLED state the fly is cut for (largest)
FLY_ELASTIC_RATIO = 0.75  # ASSUMPTION: elastic cut to 75 % of its channel (gathers the fly on the day load); same test
FLY_ELASTIC_GM = 3.0  # build_geometry.py fly row: "elastic 3 g/m ASSUMPTION (no record)"


def _matched_edge(xs_a, xs_b, L_seg):
    """Two seam sides with the same segment lengths: horizontal offsets xs_* (per point) and target 3D segment
    lengths L_seg; each side's vertical step is sqrt(L^2 - dx^2), so both sides measure sum(L_seg)."""
    ya, yb = [0.0], [0.0]
    for k, L in enumerate(L_seg):
        for xs, ys in ((xs_a, ya), (xs_b, yb)):
            dx = xs[k + 1] - xs[k]
            ys.append(ys[-1] + math.sqrt(max(L * L - dx * dx, 0.0)))
    return np.array(ya), np.array(yb)


def fly_geometry(c: ShellF | None = None) -> dict:
    """F-01 outline points (flat, mm). Spine: x across the bag (centred), y along the run from the under-floor hem.
    Side: x = depth from the frame face (the frame line at x 0), y = height along the aft corner line."""
    c = c or make()
    rp = json.loads(CROWN_ROLLED.read_text())["states"][FLY_STATE]
    z_wall = float(rp["lid_top_z"]) - LID["dome"]          # lid wall top (the dome is taken by the ease and the cord)
    zc = float(c.z_c)
    with frame_face(c):
        G = BC.gusset(c)
        _, S, A = _face_xy(c)
    aft, frm = np.asarray(G.edge_points("aft"), float), np.asarray(G.edge_points("frame"), float)[::-1]
    # aft corner line: N stations by fraction of its length (gusset aft edge = blade outer edge, 715.3 mm)
    N = 48
    la = np.r_[0.0, np.cumsum(np.hypot(*np.diff(aft, axis=0).T))]
    t = np.linspace(0.0, la[-1], N + 1)
    ax_, ay_ = np.interp(t, la, aft[:, 0]), np.interp(t, la, aft[:, 1])
    fx_ = np.interp(ay_, frm[:, 1], frm[:, 0])
    depth = ax_ - fx_                                    # gusset depth at each station
    zst = np.interp(t / la[-1], [0.0, 1.0], [BC.Z0, zc])  # station z (for the aft-face half width)
    # map each station to its z through the aft-face flat length (S is the aft-face analogue of the gusset sigma)
    zz = np.linspace(BC.Z0, zc, 400)
    Sz = np.array([S(z) for z in zz])
    zst = np.interp(t / la[-1] * Sz[-1], Sz, zz)
    half = np.array([A(z) for z in zst])
    seg = np.diff(t)
    # roll + lid wall rise: half width -> lid W/2, depth -> lid D, over the rise (straight, ASSUMPTION)
    M = 12
    rise = z_wall - zc
    hr = np.linspace(half[-1], LID["W"] / 2, M + 1)
    dr = np.linspace(depth[-1], LID["D"], M + 1)
    xs_sp = np.r_[half, hr[1:]] * FLY_EASE
    xs_sd = np.r_[depth, dr[1:]] * FLY_EASE
    L_seg = np.r_[seg, np.full(M, rise / M)]
    fx_all = np.r_[fx_, np.full(M, fx_[-1])]
    y_sp, y_sd = _matched_edge(xs_sp, fx_all + xs_sd, L_seg)
    y_sp, y_sd = y_sp + FLY_TUCK, y_sd + FLY_TUCK
    top = LID["D"] * FLY_EASE + FLY_WRAP                 # over the lid, aft edge to past the frame face
    y_end = y_sp[-1] + top
    W_top = LID["W"] / 2 * FLY_EASE
    spine_R = [(xs_sp[0], 0.0)] + list(zip(xs_sp, y_sp)) + [(W_top, y_end)]
    # side: frame line at x = -FLY_WRAP (follows the frame face fx_, offset), aft edge at fx_ + ease x depth
    side_aft = [(fx_all[0] + xs_sd[0], 0.0)] + [(fx_all[k] + xs_sd[k], y_sd[k]) for k in range(len(xs_sd))]
    side_top = [(fx_all[-1] + xs_sd[-1], y_sd[-1]), (fx_all[-1] + xs_sd[-1] - top, y_sd[-1])]
    side_frm = [(side_top[-1][0], y_sd[-1])] + [(fx_all[k] - FLY_WRAP, y_sd[k]) for k in range(len(xs_sd) - 1, -1, -1)] \
        + [(fx_all[0] - FLY_WRAP, 0.0)]
    return {"spine_R": spine_R, "side_aft": side_aft, "side_top": side_top, "side_frame": side_frm, "y_end": y_end,
            "z_wall": z_wall, "rise_mm": rise, "top_mm": top, "seam_mm": float(np.sum(L_seg)) + FLY_TUCK + top,
            "state": FLY_STATE, "lid_top_z": float(rp["lid_top_z"])}


def fly_pieces(c: ShellF | None = None) -> dict:
    """F-01a spine strip and F-01b side panel (pair) as pieces, with their two seams (spine R / L | side)."""
    g = fly_geometry(c)
    R = g["spine_R"]
    L = [(-x, y) for x, y in R]
    sp = Piece.from_edges("rain fly: spine (under-floor hem, aft face, roll, over the lid)",
                          [("bottom", [L[0], R[0]]), ("right", R), ("top", [R[-1], L[-1]]), ("left", L[::-1])],
                          seam_allowance_mm={"default": FLY_SA, "bottom": FLY_HEM, "top": FLY_HEM}, material_id=FLY_MAT,
                          piece_id="F-01a", grain=90.0)
    sa, st, sf = g["side_aft"], g["side_top"], g["side_frame"]
    sd = Piece.from_edges("rain fly: side panel (gusset, roll, lid)",
                          [("bottom", [sf[-1], sa[0]]), ("aft", sa), ("top", st), ("frame", sf)],
                          seam_allowance_mm={"default": FLY_SA, "bottom": FLY_HEM, "frame": FLY_HEM},
                          material_id=FLY_MAT, piece_id="F-01b", quantity=2, mirror=True, grain=90.0)
    from huntkit.patterns import Seam
    seams = [Seam(sp.edge("right"), [sd.edge("aft"), sd.edge("top")], name="F-01a spine R | F-01b side"),
             Seam(sp.edge("left").reversed(), [sd.edge("aft"), sd.edge("top")], name="F-01a spine L | F-01b side")]
    hem = (sp.edge_length("bottom") + sp.edge_length("top")
           + 2 * (sd.edge_length("bottom") + sd.edge_length("frame")))
    mass = BC.piece_mass_g(sp) + BC.piece_mass_g(sd)
    return {"pieces": [sp, sd], "seams": seams, "geo": g, "hem_mm": hem, "mass_g": mass,
            "area_m2": (sp.area_mm2 + 2 * sd.area_mm2) / 1e6,
            "elastic_m": FLY_ELASTIC_RATIO * hem / 1000.0}


# ---- US1/US2 bag-floor channels (BL-033 task 4). The under-straps run frame pin to frame pin UNDER the bag floor and
# take about 55 % of the floor's vertical in bag-on (meat_haul_modes.md); open channels on the floor hold them at fixed
# fore-aft stations (bag_attachment.md section 2: "B-16 floor channels"). v3.1 drew them (patterns_v31 B-16); CORRIE F
# had no geometry. Same design on CORRIE F's floor, sized for the 25 mm webbing the REC strap set uses.
US_CHANNEL_Y = (0.30, 0.65)   # patterns_v31.CHANNEL_Y: ASSUMPTION there (channel centres at 30 / 65 % of floor depth from
#                               the frame edge); settled by the US cradle fit on the prototype
US_CHANNEL_PLAY = 12.0        # patterns_v31.CHANNEL_W 50 = 38 mm webbing + 12 mm play; the same play on 25 mm webbing
US_CHANNEL_END = 15.0         # patterns_v31 B-16: ends turned 15 mm, open
F02_WH = (190.0, 140.0)       # panels.yaml F-02 (finished): the channels are topstitched across its outer face


def us_channels(c: ShellF | None = None, fabrics: str = "B") -> dict:
    """B-16 x2: open channels across the floor (on the F-02 fly pocket's outer face, which covers the floor's middle),
    channel length = F-02 width, in the floor fabric. Returns the piece, the stations and the mass."""
    c = c or make()
    d0 = float(c.depth([BC.Z0])[0])
    w = 25.0 + US_CHANNEL_PLAY
    p = rect_panel("under-strap floor channel (US1 / US2)", F02_WH[0], w, 0.0, piece_id="B-16",
                   material_id=fab("floor", fabrics), quantity=2, grain=0.0,
                   seam_allowance_mm={"default": SA_BODY, "left": US_CHANNEL_END, "right": US_CHANNEL_END})
    st = [round(f * d0, 1) for f in US_CHANNEL_Y]
    return {"piece": p, "width_mm": w, "stations_mm": st, "floor_depth_mm": d0, "mass_g": BC.piece_mass_g(p),
            "source": f"{p.material_id} record x cut area (patterns_v31 B-16 rule, 25 mm webbing)"}


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
    if REVS[REVISION].get("crown_lid"):          # BL-033: the drafted rev 3 fly (shell + roll + lid), not a scaled area
        fp = fly_pieces(b.concept)
        el0 = 3.0                                 # the hem row's elastic length (build_geometry: "fly elastic hem 3.0 m")
        return [("fly", f"F-01 rain fly, drafted for CORRIE F rev 3 (spine F-01a + sides F-01b x2, {fp['area_m2']:.3f} m2 cut)",
                 fp["mass_g"], "as_hunted", f"corrie_f.fly_pieces: cut area x {FLY_MAT} record gsm"),
                ("fly", "F-02 fly base pocket (stays on the bag)", f02, "base", "panels.yaml F-02"),
                ("fly", f"rain fly: fly elastic hem {fp['elastic_m']:.2f} m (drafted), #5 pocket zip + slider, tether",
                 hem["g"] + (fp["elastic_m"] - el0) * FLY_ELASTIC_GM, "as_hunted",
                 "ledger row with the elastic re-booked: FLY_ELASTIC_RATIO x the drafted hem channels x FLY_ELASTIC_GM")]
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
    # BL-033: the US floor channels drafted (B-16), not the B.2 estimate (floor geometry: the same in every revision)
    uc = us_channels()                       # (floor geometry: the same in every revision)
    rows = [(s_, f"US-chan: US bag-floor channels B-16 x2 ({uc['width_mm']:.0f} x {F02_WH[0]:.0f} mm on F-02, at "
                 f"{uc['stations_mm'][0]:.0f} / {uc['stations_mm'][1]:.0f} mm from the frame edge)", uc["mass_g"], cfg,
             uc["source"]) if n.startswith("US-chan:") else (s_, n, g, cfg, src) for s_, n, g, cfg, src in rows]
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
    # BL-033: the ledger's C2 correction (B-01 swell patches = the same 8 swells as cut piece B-13x) applied to the
    # adopted bag too; and DECISION H-1: the two hinge swells go (no hinge window, section above SWELL_WINDOWS)
    rows = [("attachment", r["name"], r["g"], "base", "ledger") for r in ledger_rows if r["system"] == "attachment"
            and r["name"] != "attachment: B-01 swell patches"]
    b13 = next(r for r in ledger_rows if r["name"].startswith("B-13x boxed fairlead swell"))
    rows.append(("attachment", "BL-033 H-1: hinge swells B-13xh x2 deleted (no hinge window; B-18 takes the cleat)",
                 -len(SWELL_WINDOWS_DROPPED) * 2 * b13["g"] / 8.0, "base", "ledger B-13x row / 8 x 2"))
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
        if p.piece_id == "B-01":                       # BL-033: net of its swell windows (cut out; B-13x is its own row)
            nb = b01_net_g(c, fabrics, p)
            add("bag_shell", f"B-01 {p.name} ({p.material_id}), net of {nb['windows']} swell windows", nb["net_g"], "base",
                f"corrie_f.build(): cut area less {nb['window_mm2']:.0f} mm2 of windows (corrie_f.swell_windows) x record gsm")
            continue
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
    # BL-031 strap tails (rev 3 with crown kits): W1-W3 cut for carry + haul extenders, IM and roll-clip tail keepers
    if REVS[REVISION].get("crown_kits"):
        import strap_tails as ST
        for s, n, g, cfg, src in ST.bag_rows(CROWN_KIT_DEFAULT):
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
           "zip_mm_base": round(zip_mm, 0), "zip_mm_with_pouch": round(zip_mm + ad.get("top_pouch", ad.get("crown_lid"))["zip_mm"], 0),
           "door_zip_mm": round(b.extra["zip_door_mm"], 0),
           "beginner_hours_base": round(base_h, 1), "beginner_hours_with_addons": round(base_h + addon_h, 1),
           # CORRIE B.2's 35.6 h basis (lean.fell.corrie_bag_system: body incl. pouch + IMP-1/2/4/8, no fly)
           "beginner_hours_b2_basis": round(base_h - 0.3 + ad.get("top_pouch", ad.get("crown_lid"))["hours"] + ad["scope_pod"]["hours"], 1),
           "pieces_b2_basis": pieces - 1 + ad.get("top_pouch", ad.get("crown_lid"))["pieces"] + ad["scope_pod"]["pieces"],
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
    if r.get("guy_port"):
        p = guy_port()
        rows.append(("attachment", f"BL-028 rev 2: {p['id']} guy ports (2), lapped slits in B-01 at x +/-{p['x_mm']:.0f}, "
                     f"z {p['z_mm'][0]:.0f}-{p['z_mm'][1]:.0f}", p["mass_g"], "base", p["source"]))
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


# ---------------------------------------------------------------------------------------------------------- BL-028
# The guy's REAL path. BL-022 (guy_geometry) and every cloth sim since 2026-11-05 drew the top guy as a straight line
# from the crown bar to B-22; with a packed bag that line runs through the bag. Here the guy is a taut strap that
# must stay outside the cloth (fine-mesh drape) and outside the crown tubes: a string pulled tight from the bridle
# sleeve on the bar to B-22 (or through a guide loop on the way). Units mm, N.
MU_WEB_FAB = 0.30         # ASSUMPTION: 25 mm poly webbing sliding on ULTRAGrid / 70D PU-coated face fabric (no record;
#                           webbing-on-carbon MU_WEB_BAR uses the same value). Settled by GT-1, a capstan test: hang
#                           5 kg on the guy over the packed bag's corner and read the pull to start it moving.
MU_SENS = (0.20, 0.40)    # sensitivity band reported next to MU_WEB_FAB
PATH_CLEAR = 2.0          # ASSUMPTION: strap centre 2 mm off the simulated cloth (0.6 mm half webbing + cloth and mesh
#                           facet scatter); settled with the guy clearance check on the prototype (MIN_CLEAR_MM gate)
CORNER_WRAP_OD = 19.5     # DECISIONS 2026-11-06: crown corner wraps x +/-77 to +/-107, OD about 19.5
SIM_CROWN_AX = (0.0, -0.0189, 0.9998)    # huntkit.clothsim.pack.crown_field: frame axis through the crown legs
SIM_LEG_BASE = (115.0, -10.0, 530.0)     # same source: leg axis from the stay top
PATH_N = 60               # string points per free run (about 6 mm spacing on a 380 mm guy)
PATH_ITERS = 8000         # relaxation sweeps (the length is stable to 0.1 mm from about 4000; test_guy_path_*)
LIFTER_LEN = 150.0        # lifter webbing modelled from the lug toward the shoulder strap (as guy_geometry)


def crown_tubes(top_z: float) -> list:
    """Crown tubes near the guy as (a, b, r): the top bar (with the corner wraps), both legs and the spine, placed as
    the cloth sim places them (pack.crown_field: bar 25 mm aft of the leg axis at top_z), real ODs from frame.yaml."""
    ax = np.asarray(SIM_CROWN_AX, float)
    ax = ax / np.linalg.norm(ax)
    yb = SIM_LEG_BASE[1] + (top_z - SIM_LEG_BASE[2]) * ax[1] / ax[2] + 25.0
    out = [(np.array([-115.0, yb, top_z]), np.array([115.0, yb, top_z]), BAR_OD / 2.0)]
    for sx in (1, -1):
        out.append((np.array([sx * 69.0, yb, top_z]), np.array([sx * 115.0, yb, top_z]), CORNER_WRAP_OD / 2.0))
        a = np.array([sx * SIM_LEG_BASE[0], SIM_LEG_BASE[1], SIM_LEG_BASE[2]])
        out.append((a, a + ax * (top_z - SIM_LEG_BASE[2]) / ax[2], LEG_OD / 2.0))
    out.append((np.array([0.0, yb - 25.0, top_z]), np.array([0.0, yb - 25.0, top_z - 300.0]), SPINE_OD / 2.0))
    return out


def lifter_line(torso: float, side: int = 1) -> tuple:
    """Lifter webbing centre line: from the lug on the crown corner (attach_system crown settings: x 105, 15 mm forward
    of the leg axis, at the crown top) toward the shoulder strap at the setting's lifter angle (forward and down)."""
    bg = _bg()
    cs = min(bg.crown_settings(), key=lambda q: abs(q["torso_in"] - torso))
    la = np.array(cs["lifter_anchor_R"], float) * np.array([side, 1.0, 1.0])
    ang = math.radians(cs["lifter_angle_deg"])
    return la, la + LIFTER_LEN * np.array([0.0, -math.cos(ang), -math.sin(ang)])


class ClothSurface:
    """Closed cloth mesh as dense surface samples with outward face normals (closest point by KD tree)."""

    def __init__(self, X, tris, k: int = 7):
        from scipy.spatial import cKDTree
        X = np.asarray(X, float)
        V = X[np.asarray(tris)]
        fn = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
        if np.einsum("ij,ij->i", V[:, 0], fn).sum() < 0:      # signed volume < 0: faces point in
            fn = -fn
        fn /= np.maximum(np.linalg.norm(fn, axis=1), 1e-12)[:, None]
        bc = np.array([(1 - i / k - j / k, i / k, j / k) for i in range(k + 1) for j in range(k + 1 - i)])
        self.S = np.einsum("bk,fkd->fbd", bc, V).reshape(-1, 3)
        self.N = np.repeat(fn, len(bc), axis=0)
        self.tree = cKDTree(self.S)

    def closest(self, P):
        _, j = self.tree.query(P)
        return self.S[j], self.N[j]

    def signed(self, P):
        c, n = self.closest(P)
        return np.einsum("ij,ij->i", np.asarray(P) - c, n)


def _push_tubes(P, tubes, extra=1.0):
    for a, b, r in tubes:
        t = b - a
        L = float(np.linalg.norm(t))
        t = t / L
        s = np.clip((P - a) @ t, 0.0, L)
        C = a + s[:, None] * t
        d = P - C
        n = np.linalg.norm(d, axis=1)
        m = n < r + extra
        if m.any():
            P[m] = C[m] + d[m] / np.maximum(n[m], 1e-9)[:, None] * (r + extra)
    return P


def taut_path(surf: ClothSurface | None, A, B, around, tubes=(), n: int = PATH_N, iters: int = PATH_ITERS,
              clear: float = PATH_CLEAR) -> np.ndarray:
    """Shortest strap from A to B that stays ``clear`` outside the cloth and outside the tubes, in the homotopy class
    of the polyline A -> ``around`` -> B (``around`` is a point well outboard on the side the strap passes). String
    relaxation: each sweep moves every inner point toward its neighbours' mid-point (shortens), then pushes it back
    out of the obstacles; resampled to equal spacing every 25 sweeps."""
    A, B, W = (np.asarray(v, float) for v in (A, B, around))
    P = np.vstack([np.linspace(A, W, n // 2, endpoint=False), np.linspace(W, B, n - n // 2)])
    for it in range(iters):
        P[1:-1] += 0.6 * (0.5 * (P[:-2] + P[2:]) - P[1:-1])
        if surf is not None and (it % 5 == 0 or it > iters - 50):
            c, nr = surf.closest(P[1:-1])
            sd = np.einsum("ij,ij->i", P[1:-1] - c, nr)
            m = sd < clear
            Q = P[1:-1]
            Q[m] = c[m] + nr[m] * clear
            P[1:-1] = Q
        if len(tubes):
            P[1:-1] = _push_tubes(P[1:-1], tubes)
        if it % 25 == 0:
            s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            si = np.linspace(0.0, s[-1], n)
            P = np.column_stack([np.interp(si, s, P[:, k]) for k in range(3)])
    return P


def _ribbon_gap(P, surf, la, lb, w=GUY_W) -> float:
    """Edge-to-edge gap between the guy ribbon (width across the cloth, square to the path) and the lifter ribbon
    (width along x at the lug, the lug's slot axis), both 25 mm, from 6 x 40 samples per ribbon."""
    from scipy.spatial import cKDTree
    u = np.diff(P, axis=0)
    u /= np.maximum(np.linalg.norm(u, axis=1), 1e-9)[:, None]
    mid = 0.5 * (P[:-1] + P[1:])
    # no cloth (a strap through the vertical port slit): webbing on edge, width vertical
    nr = surf.closest(mid)[1] if surf is not None else np.tile([1.0, 0.0, 0.0], (len(mid), 1))
    wd = np.cross(nr, u)
    wd /= np.maximum(np.linalg.norm(wd, axis=1), 1e-9)[:, None]
    G = np.vstack([mid + k * wd for k in np.linspace(-w / 2, w / 2, 6)])
    le = la + np.linspace(0, 1, 40)[:, None] * (lb - la)
    Lr = np.vstack([le + np.array([k, 0.0, 0.0]) for k in np.linspace(-LIFTER_W / 2, LIFTER_W / 2, 6)])
    return float(cKDTree(Lr).query(G)[0].min())


def path_metrics(P, surf: ClothSurface | None, A, B, torso: float, side: int = 1, T_n: float | None = None,
                 clear: float = PATH_CLEAR, loops=()) -> dict:
    """Length, wrap, friction share, the force the guy puts on B-22 and on the bag as a whole, and the gap to the lifter.

    * wrap angle theta = total turning of the (lightly smoothed) path where it bears on the cloth or a guide loop;
      friction share = 1 - exp(-mu theta) = the part of the cinch tension the wrap holds back (capstan);
    * u_bag = unit pull of the guy on the bag as a whole = from the bag toward the bar along the first free run (the
      wrapped part and B-22 move with the bag; GT-1 / sim): its -y part is the forward pull that holds the CG;
    * u_B22 = unit pull at B-22 itself (back along the last run); the straight-line model put it along B-22 -> bar.
    ``T_n`` (the simulated guy tension at the bar end) turns shares into newtons; the B-22 range is T e^(-mu theta)
    (guy being cinched) to T (load creeping out against friction is not credited)."""
    from scipy.ndimage import gaussian_filter1d
    A, B = np.asarray(A, float), np.asarray(B, float)
    seg = np.diff(P, axis=0)
    ln = np.linalg.norm(seg, axis=1)
    u = seg / np.maximum(ln, 1e-9)[:, None]
    if surf is not None:
        con = surf.signed(P) < clear + 1.5
    else:
        con = np.zeros(len(P), bool)
    for lp in loops:                                  # a guide loop is a bearing point too
        con |= np.linalg.norm(P - np.asarray(lp, float), axis=1) < 15.0
    Ps = P.copy()
    Ps[1:-1] = gaussian_filter1d(P, 1.5, axis=0, mode="nearest")[1:-1]
    us = np.diff(Ps, axis=0)
    us /= np.maximum(np.linalg.norm(us, axis=1), 1e-9)[:, None]
    turn = np.arccos(np.clip(np.einsum("ij,ij->i", us[:-1], us[1:]), -1.0, 1.0))
    theta = float(turn[con[1:-1]].sum())
    i0 = int(np.argmax(con[1:])) + 1 if con[1:].any() else len(P) - 1
    d0 = P[i0] - A
    uA = d0 / np.linalg.norm(d0) if np.linalg.norm(d0) > 5.0 else u[0]
    u_bag = -uA                                       # pull on the bag: toward the bar
    u_b22 = -u[-1]                                    # pull on B-22: back along the last run
    u_str = (A - B) / np.linalg.norm(A - B)
    la, lb = lifter_line(torso, side)
    out = {"length_mm": round(float(ln.sum()), 1), "straight_mm": round(float(np.linalg.norm(B - A)), 1),
           "wrap_deg": round(math.degrees(theta), 1),
           "friction_share": round(1.0 - math.exp(-MU_WEB_FAB * theta), 3),
           "friction_share_band": [round(1.0 - math.exp(-m * theta), 3) for m in MU_SENS],
           "u_bag": [round(float(v), 3) for v in u_bag], "u_b22": [round(float(v), 3) for v in u_b22],
           "fwd_share_bag": round(float(-u_bag[1]), 3), "fwd_share_b22": round(float(-u_b22[1]), 3),
           "fwd_share_straight": round(float(-u_str[1]), 3),
           "b22_along_straight": round(float(u_b22 @ u_str), 3),
           "outboard_share_at_bar": round(float(side * uA[0]), 3),
           "lifter_gap_mm": round(_ribbon_gap(P, surf, la, lb), 1),
           "lifter_centre_mm": round(float(np.min(np.linalg.norm(
               P[:, None, :] - (la + np.linspace(0, 1, 60)[:, None] * (lb - la))[None], axis=2))), 1),
           "x_max_mm": round(float(np.max(side * P[:, 0])), 1)}
    if T_n is not None:
        e = math.exp(-MU_WEB_FAB * theta)
        out["T_bar_n"] = round(float(T_n), 1)
        out["b22_n"] = [round(float(T_n) * e, 1), round(float(T_n), 1)]
        out["fwd_pull_bag_n"] = round(float(T_n) * out["fwd_share_bag"], 1)
        out["fwd_pull_straight_model_n"] = round(float(T_n) * out["fwd_share_straight"], 1)
    return out


# fine drapes and their mesh (node order is fixed by the pattern, the same at every torso)
FINE_DRAPE_DIR = ROOT / "outputs" / "clothsim" / "corrie_f"
_MESH = {}


def fine_mesh(torso: int) -> dict:
    """Fine (h 25) sim mesh of the current shell: triangles, drafted nodes, piece of each node, B-22 nodes and the
    guy bar anchors as the scenario places them. Built once per torso (PackModel, about 20 s)."""
    if torso in _MESH:
        return _MESH[torso]
    S = _sim()
    from huntkit.clothsim.pack import PackModel, load_scenario
    S.install(None)
    try:
        pm = PackModel(load_scenario(str(S.scenario_path(torso, REVS[1]["guy_x"]))), fine=True, verbose=False)
    finally:
        S.uninstall()
    X0 = pm.mesh.X0
    m = {"X0": X0, "tris": np.asarray(pm.mesh.tris), "piece": [sorted(pm.node_pieces[j])[0] for j in range(len(X0))],
         "b22": {s: int(pm.cables[f"TG_{s}"].nodes[0]) for s in ("R", "L")},
         "anchor": {s: np.asarray(pm.cables[f"TG_{s}"].fixed[-1], float) for s in ("R", "L")}}
    _MESH[torso] = m
    return m


def drape(run: str, case: str):
    """Loaded node positions of a stored fine run (outputs/, not tracked: None when the run is not on disk)."""
    p = FINE_DRAPE_DIR / run / f"x_{case}.npy"
    return np.load(p) if p.exists() else None


def real_guy_path(X, torso: int, side: str = "R", loops=(), anchor=None, b22=None, tubes=None):
    """The taut guy on a loaded drape ``X``: bridle anchor (x +/-GUY_X on the bar's bag face, as the sim) -> optional
    guide loops (3D points the strap passes through) -> B-22. Returns (path, surface, A, B)."""
    m = fine_mesh(torso)
    sx = 1 if side == "R" else -1
    A = np.asarray(anchor if anchor is not None else m["anchor"][side], float)
    B = np.asarray(b22 if b22 is not None else X[m["b22"][side]], float)
    surf = ClothSurface(X, m["tris"])
    tubes = crown_tubes(float(A[2])) if tubes is None else tubes
    pts = [A] + [np.asarray(q, float) for q in loops] + [B]
    parts = []
    for p0, p1 in zip(pts[:-1], pts[1:]):
        around = [sx * 330.0, 0.5 * (p0[1] + p1[1]), 0.5 * (p0[2] + p1[2])]
        direct = taut_path(None, p0, p1, 0.5 * (p0 + p1), (), n=12, iters=10)
        free = (surf.signed(direct[1:-1]) > PATH_CLEAR).all()
        parts.append(direct if free else taut_path(surf, p0, p1, around, tubes))
    P = np.vstack([parts[0]] + [q[1:] for q in parts[1:]])
    return P, surf, A, B


def path_vias(P, X, surf: ClothSurface, spacing: float = 40.0, end_keep: float = 25.0) -> list:
    """Mesh nodes for the cloth sim's frictionless eyelets (huntkit Cable via nodes) along a real guy path: the nodes
    nearest the points where the path bears on the cloth, every ``spacing`` mm of arc, ``end_keep`` mm clear of the
    ends. The sim's straight runs between them then follow the wrap (chords on a 40 mm spacing)."""
    from scipy.spatial import cKDTree
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    on = surf.signed(P) < PATH_CLEAR + 1.5
    tr = cKDTree(np.asarray(X, float))
    out, last = [], -1e9
    for i in range(len(P)):
        if not on[i] or s[i] < end_keep or s[i] > s[-1] - end_keep or s[i] - last < spacing:
            continue
        k = int(tr.query(P[i])[1])
        if k not in out:
            out.append(k)
            last = s[i]
    return out


ROUTE_SEED = ("F_r1_PR{t}_fineFM", "meat")     # the drape each route's eyelets are picked on (rev 1, fine, meat)


def _route_wrap(torso: int) -> dict:
    """'wrap' = rev 1 as it would really sit: the guy round the bag's side corner to B-22 (eyelets on its real path on
    the rev 1 fine meat drape)."""
    X = drape(ROUTE_SEED[0].format(t=torso), ROUTE_SEED[1])
    if X is None:
        raise FileNotFoundError(f"{ROUTE_SEED[0].format(t=torso)} not on disk: run corrie_f_sim.py finerun F --torso {torso}")
    out = {}
    for s in ("R", "L"):
        P, surf, A, B = real_guy_path(X, torso, s)
        out[s] = {"vias": path_vias(P, X, surf), "b22": None}
    return out


def _b01_node(torso: int, x: float, z: float) -> int:
    """B-01 (frame-face) node nearest drafted (x, z)."""
    m = fine_mesh(torso)
    X0 = m["X0"]
    idx = np.array([j for j, p in enumerate(m["piece"]) if p == "B-01"])
    return int(idx[np.argmin(np.hypot(X0[idx, 0] - x, X0[idx, 2] - z))])


def _route_tie(torso: int, keep_guys: bool = True) -> dict:
    """'tie' = an internal depth tie from B-22 straight across the inside of the bag to the frame face B-01 at the same
    x and z (no frame end), with the external guys kept on their real wrap ('tie_wrap') or deleted ('tie')."""
    m = fine_mesh(torso)
    base = _route_wrap(torso) if keep_guys else {"R": {"off": True}, "L": {"off": True}}
    for s, sx in (("R", 1), ("L", -1)):
        b = m["b22"][s]
        x, z = float(m["X0"][b, 0]), float(m["X0"][b, 2])
        base[s]["internal"] = {f"TI_{s}": [b, _b01_node(torso, x, z)]}
    return base


GUY_PATHS = HERE / "corrie_f_sim" / "corrie_f_guy_paths.json"
# stored fine runs whose drapes BL-028 measures: (row key, run folder, torso, routing; None = the straight tie)
BL028_RUNS = [(f"F_PR{t}_fineFM", f"F_r1_PR{t}_fineFM", t, None) for t in (15, 19, 23)] + \
             [(f"F_PR{t}_fineFM_wrap_6d", f"F_r1_PR{t}_fineFM_wrap_6d", t, "wrap") for t in (15, 19, 23)] + \
             [("F_PR15_fineFM_wrap", "F_r1_PR15_fineFM_wrap", 15, "wrap")] + \
             [(f"F_PR{t}_fineFM_port", f"F_r1_PR{t}_fineFM_port", t, "port") for t in (15, 19, 23)]


def bl028_paths(runs=None, write: bool = True) -> dict:
    """Real guy path (both sides) on every stored fine drape that is on disk: length, wrap, friction share, pull on
    B-22 and on the bag, lifter gap. Tension = the run's simulated guy load at 1 g. Written to GUY_PATHS."""
    S = _sim()
    rows = S.load_results()["rows"]
    old = json.loads(GUY_PATHS.read_text()) if GUY_PATHS.exists() else {"rows": {}}
    out = {"method": "taut string outside the fine cloth drape (PATH_CLEAR) and the crown tubes; corrie_f.taut_path",
           "mu": MU_WEB_FAB, "mu_band": list(MU_SENS), "min_clear_mm": MIN_CLEAR_MM, "rows": dict(old.get("rows", {}))}
    for key, folder, t, route in (runs or BL028_RUNS):
        for case in ("fill", "meat", "sixday"):
            X = drape(folder, case)
            if X is None:
                continue
            row = {"torso": t, "case": case, "route": route or "straight (as simulated)", "run": folder}
            rj = FINE_DRAPE_DIR / folder / "results.json"
            if rj.exists():                    # a drape that did not converge is kept, flagged (geometry only)
                cc = json.loads(rj.read_text())["cases"].get(case, {})
                row["converged"] = bool(cc.get("converged"))
                row["residual_n"] = (cc.get("solve") or [{}])[-1].get("residual_n")
            loads = rows.get(key, {}).get("cases", {}).get(case, {}).get("loads_1g", {})
            spec = ROUTES[route](t) if route == FIX_ROUTE else None
            for s, sx in (("R", 1), ("L", -1)):
                if spec is not None:              # rev 2: bar -> port (outside) -> B-22 (inside the bag, straight)
                    m = fine_mesh(t)
                    A, Q = m["anchor"][s], X[spec[s]["vias"][0]]
                    B = X[spec[s]["b22"] if spec[s].get("b22") is not None else m["b22"][s]]
                    P = np.vstack([np.linspace(A, Q, 8, endpoint=False), np.linspace(Q, B, 40)])
                    row[s] = path_metrics(P, None, A, B, t, sx, T_n=loads.get(f"TG_{s}"), loops=[Q])
                    row[s]["outside_mm"] = round(float(np.linalg.norm(Q - A)), 1)
                    continue
                loops = ROUTE_LOOPS.get(route, lambda *_: [])(X, t, s)
                P, surf, A, B = real_guy_path(X, t, s, loops=loops)
                row[s] = path_metrics(P, surf, A, B, t, sx, T_n=loads.get(f"TG_{s}"), loops=loops)
            out["rows"][f"{folder}:{case}"] = row
    if write:
        GUY_PATHS.write_text(json.dumps(out, indent=1, default=_j))
    return out


ROUTE_LOOPS = {}      # routing -> fn(X, torso, side) giving the guide-loop points the guy is held through


def _hook_node(torso: int, side: str) -> int:
    """Bag node of the IM3 bag hook (scenario hooks station 520) on ``side``."""
    S = _sim()
    from huntkit.clothsim.pack import PackModel, load_scenario
    S.install(None)
    try:
        pm = PackModel(load_scenario(str(S.scenario_path(torso, REVS[1]["guy_x"]))), fine=True, verbose=False)
    finally:
        S.uninstall()
    ks = sorted(int(c.nodes[0]) for c in pm.cables.values() if c.meta.get("group", c.name) == f"hook_im520_{side}")
    X0 = pm.mesh.X0
    return min(ks, key=lambda k: abs(X0[k, 0] - np.mean(X0[ks, 0])))     # the bridle's middle node (hook eye)


def _route_im3(torso: int) -> dict:
    """'im3' = no external guy; an internal guy from B-22 down to the IM3 bag-hook eye on the frame face (z 520), so
    the frame end is the IM3 hook (torso independent, no port), at the price of more load on the IM3 cheek."""
    m = fine_mesh(torso)
    return {s: {"off": True, "internal": {f"TI_{s}": [m["b22"][s], _hook_node(torso, s)]}} for s in ("R", "L")}


def _route_port(torso: int) -> dict:
    """'port' = the guy passes through a lapped port in the frame face B-01 at x +/-GUY_X, where B-01 meets the bar,
    and runs inside the bag to B-22 (its tab turned to the inside of the hinge band). The port is the B-01 node
    nearest the bar crossing (drafted x GUY_X, z = bar, capped at the collar seam z 745)."""
    m = fine_mesh(torso)
    out = {}
    for s, sx in (("R", 1), ("L", -1)):
        zb = min(float(m["anchor"][s][2]), 745.0)
        out[s] = {"vias": [_b01_node(torso, sx * REVS[1]["guy_x"], zb)], "b22": None}
    return out


def _piece_node(torso: int, piece: str, x: float, z: float) -> int:
    m = fine_mesh(torso)
    X0 = m["X0"]
    idx = np.array([j for j, p in enumerate(m["piece"]) if p == piece])
    return int(idx[np.argmin(np.hypot(X0[idx, 0] - x, X0[idx, 2] - z))])


def _route_port_at(torso: int, x22: float, z22: float) -> dict:
    """'port' with the inside guy tab moved to the hinge band at (x22, z22)."""
    out = _route_port(torso)
    for s, sx in (("R", 1), ("L", -1)):
        out[s]["b22"] = _piece_node(torso, "B-02h", sx * x22, z22)
    return out


ROUTES = {"wrap": _route_wrap, "im3": _route_im3, "port": _route_port,
          "port_hi": lambda t: _route_port_at(t, 149.0, 740.0), "port_hi_in": lambda t: _route_port_at(t, 100.0, 740.0), "tie_wrap": lambda t: _route_tie(t, True), "tie": lambda t: _route_tie(t, False)}


def route_spec(name: str, torso: int) -> dict:
    return ROUTES[name](torso)


# rev 2 (BL-028, PROPOSED): the guy goes inside. Path, CG and R-28 are in section 13 of corrie_f_body.md.
FIX_ROUTE = "port"            # the corrie_f_sim routing that models rev 2 (runs F_r1_PR{t}_fineFM_port: rev 1 bag + port)
PORT_Z = (595.0, 745.0)       # DECISION: port slit from 6 mm under the lowest bar (15 in, z 601) to the collar seam z 745
#                               (B-01's top edge). The L kit's bar (z 728-804) meets it at the top end (section 13.3)
PORT_FACING_W = 50.0          # ASSUMPTION: lap facing 50 mm wide (20 mm lap + 2 x 15 mm stitch lines); settled by the
#                               first port mock-up (water hose test from above, guy pulled at 45 deg through it)
PORT_TURN = 6.0               # slit edges turned 6 mm and edge-stitched (both edges)
PORT_END = 10.0               # facing runs 10 mm past each slit end (bartacked)


def guy_port(fabrics: str = "B") -> dict:
    """B-27 guy port (rev 2), one each side: a vertical lapped slit in the frame face B-01 at x +/-GUY_X from PORT_Z[0]
    to PORT_Z[1]. The outboard edge laps 20 mm over the inboard edge on a B-01-fabric facing sewn inside; both edges
    turned and edge-stitched; bartacks at the ends. The guy passes through it where the bar meets B-01, so it never
    leaves the bar band x 39.5-64.5 outside the bag (lifter band starts at x 92.5). Mass = (facing + turned edges)
    x the B-01 fabric record."""
    c = make()
    with frame_face(c):
        mid = BC.frame_panel(c).material_id
    s01 = b01_flat_s(c)
    h = s01(PORT_Z[1]) - s01(PORT_Z[0])       # BL-033: the slit on the fabric (B-01's Z-fold sits in z 631-745), not dz
    area = (PORT_FACING_W * (h + 2 * PORT_END) + 2 * PORT_TURN * h) * 2      # two ports
    return {"id": "B-27", "x_mm": REVS[1]["guy_x"], "z_mm": list(PORT_Z), "slit_mm": round(h, 1),
            "slit_dz_mm": PORT_Z[1] - PORT_Z[0], "material": mid,
            "area_mm2": round(area, 0), "mass_g": round(area * _gsm(mid) / 1e6, 2),
            "source": f"{mid} record (B-01 fabric) x facing and turned-edge area (PORT_FACING_W, PORT_TURN ASSUMPTIONS)"}


def guy_length_check() -> dict:
    """Guy webbing per side: what the straight model books (bar to B-22) against rev 1's real outside path and rev 2's
    inside path (fine meat drapes; GUY_PATHS). Rev 1 never booked the extra outside length."""
    gp = json.loads(GUY_PATHS.read_text()) if GUY_PATHS.exists() else {"rows": {}}
    out = {}
    for t in (15, 19, 23):
        r = gp["rows"].get(f"F_r1_PR{t}_fineFM:meat")
        if r:
            ext = max(r["R"]["length_mm"], r["L"]["length_mm"])
            st = max(r["R"]["straight_mm"], r["L"]["straight_mm"])
            out[t] = {"straight_mm": st, "rev1_real_mm": ext, "extra_mm": round(ext - st, 1),
                      "extra_g_pair": round(2 * (ext - st) * WEB25 / 1000.0, 2)}
    return out


BL028_CG_RUNS = {          # 15 in meat, fine mesh: what each guy model / routing gives (stored corrie_f_sim rows)
    "straight model (BL-022, through the bag)": "F_PR15_fineFM",
    "guys off (misuse)": "F_PR15_fineFM_goff_sm8",
    "rev 1 real: round the bag (eyelets on its path)": "F_PR15_fineFM_wrap",
    "internal depth tie + rev 1 wrap": "F_PR15_fineFM_tie_wrap",
    "internal guy to the IM3 hook eye": "F_PR15_fineFM_im3",
    "rev 2: B-01 port, inside to B-22 (z 695)": "F_PR15_fineFM_port",
    "port, tab at the collar seam x 149": "F_PR15_fineFM_port_hi",
    "port, tab at the collar seam x 100": "F_PR15_fineFM_port_hi_in",
}


def bl028_table() -> dict:
    """BL-028 numbers from stored results: the real path on every fine drape, the 15 in meat CG of each routing, and
    rev 2 (port) fill / meat CG and R-28 at 15 / 19 / 23 in. Acceptance: lifter gap >= MIN_CLEAR_MM on the real path,
    15 in meat CG <= 180 mm (fine), R-28 >= 31 deg."""
    S = _sim()
    rows = S.load_results()["rows"]
    gp = json.loads(GUY_PATHS.read_text()) if GUY_PATHS.exists() else {"rows": {}}

    def cg(key, case="meat"):
        c = rows.get(key, {}).get("cases", {}).get(case)
        if not c:
            return None
        g = c["loads_1g"]
        return {"converged": c["converged"], "rounding_mm": c["rounding_mm"], "cg_y": c["cg_y"], "cg_y_biased": c["cg_y_biased"],
                "closed_L": c["closed_L"], "guy_1g_n": max(g.get("TG_R", 0.0), g.get("TG_L", 0.0)),
                "tie_1g_n": max(g.get("TI_R", 0.0), g.get("TI_L", 0.0)),
                "im3_1g_n": max(g.get("hook_im520_R", 0.0), g.get("hook_im520_L", 0.0))}
    cg15 = {k: cg(v) for k, v in BL028_CG_RUNS.items()}
    paths = {k: r for k, r in gp["rows"].items()}
    gaps = [min(r["R"]["lifter_gap_mm"], r["L"]["lifter_gap_mm"]) for r in paths.values()
            if r["case"] in ("fill", "meat", "sixday")]
    fix = {}
    for t in (15, 19, 23):
        key = f"F_PR{t}_fineFM_{FIX_ROUTE}"
        r = rows.get(key, {})
        fix[t] = {cn: cg(key, cn) for cn in ("fill", "meat")}
        fix[t]["r28_deg"] = (min(r["r28"]["fill"]["worst_contact_deg"], r["r28"]["meat"]["worst_contact_deg"])
                             if "r28" in r else None)
        fix[t]["r28_gap30_mm"] = (min(r["r28"]["fill"]["worst_gap_30_mm"], r["r28"]["meat"]["worst_gap_30_mm"])
                                  if "r28" in r else None)
    m15 = (fix[15].get("meat") or {}).get("cg_y")
    r28s = [fix[t]["r28_deg"] for t in (15, 19, 23)]
    acc = {"lifter_gap_min_mm": min(gaps) if gaps else None,
           "lifter_ok": bool(gaps) and min(gaps) >= MIN_CLEAR_MM,
           "cg15_meat_fix_mm": m15, "cg15_ok": m15 is not None and m15 <= 180.0,
           "cg15_short_mm": None if m15 is None else round(max(0.0, m15 - 180.0), 1),
           "r28_fix_deg": r28s, "r28_ok": all(v is not None and v >= 31.0 for v in r28s)}
    return {"paths": paths, "cg15_meat": cg15, "fix_route": FIX_ROUTE, "fix": fix, "acceptance": acc,
            "port": guy_port(), "guy_length": guy_length_check()}


def BL028_NOTE_TEXT() -> str:
    t = bl028_table()
    a, c = t["acceptance"], t["cg15_meat"]

    def v(k):
        return "n/a" if not c.get(k) else f"{c[k]['cg_y']:.1f}"
    return ("Read this first\n"
            "- The straight guy in every sim since 2026-11-05 passes\n  through the full bag. It does not exist.\n"
            "- Real path: round the bag's side, 360-420 mm, 170-210 deg\n  of wrap. It stays aft of the bar, clear of the\n"
            f"  lifters (worst edge gap {a['lifter_gap_min_mm']:.0f} mm, need 10).\n"
            "- But it pulls the bag sideways. 15 in meat CG:\n"
            f"  straight model {v('straight model (BL-022, through the bag)')}, real {v('rev 1 real: round the bag (eyelets on its path)')} mm\n"
            f"  (guys off {v('guys off (misuse)')}; rev C limit 190).\n"
            f"- Rev 2: guy through a lapped port in B-01 at x 52,\n  inside to B-22: {a['cg15_meat_fix_mm']:.1f} mm "
            f"({'meets' if a['cg15_ok'] else 'misses'} 180 by {abs((a['cg15_meat_fix_mm'] or 0) - 180):.1f}).\n"
            f"- R-28 with rev 2: {', '.join('n/a' if x is None else f'{x:.0f}' for x in a['r28_fix_deg'])} deg at 15/19/23 in.")


# ---------------------------------------------------------------------------------------------------------- BL-029
# Top anchor and lid (doc section 14). BL-028 showed that only a line from the BAR toward the bag's aft top holds the
# 15 in meat CG, and that outside the bag the guy's line runs sideways. BL-029 takes the line OVER the roll: two crown
# straps B-28 from the B-25 bridle tabs (x +/-52, unchanged) up the frame face, over the closed roll and the lid, and
# down to tabs on the hinge band at the same x. The lid B-29 rides under them in two channels. The straps are the bag's
# (they close the roll); the lid comes off them. Units mm, N, g.
CROWN_X = 52.0             # DECISION: the crown straps run at the bridle x (B-25 sleeves, lifter band starts x 92.5)
CROWN_FRONT_Z = 700.0      # DECISION: front tab on the hinge band B-02h (z 650-745 drafted), above the D2 door top
#                            (z 650), so the crown straps never cross the door
CROWN_PRE_N = 80.0         # ASSUMPTION: hand-cinched 25 mm ladder lock, the W1-W3 value (pack5200_v31 wraps); settled
#                            by the T9 loaded-CG test at the S kit with a spring scale on the cinched strap
CROWN_CAP_N = 300.0        # 25 mm ladder-lock slip (meat_haul_modes.md, the W1-W3 value)
ROUTE_SEED_OVER = ("F_r1_PR{t}_fineFM", "meat")   # drape the crown-strap eyelets are picked on (rev 1, fine, meat)


def _vias_head_first(vias: list) -> list:
    """corrie_f_sim._install_route builds the cable as [bag end] + vias + [bar]: path_vias lists the nodes from the
    bar, so they are reversed here (BL-029 found that the BL-028 'wrap' route passed them bar-first; section 14.8)."""
    return list(reversed(vias))


def crown_path(X, torso: int, side: str = "R", front_node: int | None = None):
    """The taut crown strap on a drape ``X``: bridle anchor (x +/-CROWN_X on the bar) -> up the frame face, over the
    top -> the front tab node on the hinge band. Returns (path, surface, A, B, front node)."""
    m = fine_mesh(torso)
    sx = 1 if side == "R" else -1
    k = front_node if front_node is not None else _piece_node(torso, "B-02h", sx * CROWN_X, CROWN_FRONT_Z)
    A = np.asarray(m["anchor"][side], float).copy()
    A[0] = sx * CROWN_X
    B = np.asarray(X[k], float)
    surf = ClothSurface(X, m["tris"])
    P = taut_path(surf, A, B, [sx * CROWN_X, 0.5 * (A[1] + B[1]), 1150.0], crown_tubes(float(A[2])))
    return P, surf, A, B, k


def _route_over(torso: int, keep_port: bool = False) -> dict:
    """'over' = BL-029 crown straps: the guy cable re-threaded from the bar over the top to the hinge-band tab
    (eyelets on its taut path over the rev 1 fine meat drape), hand-cinched (ladder lock) on the loaded bag.
    ``keep_port``: rev 2's inside guy stays as well (an extra frame-anchored cable through the B-27 port)."""
    X = drape(ROUTE_SEED_OVER[0].format(t=torso), ROUTE_SEED_OVER[1])
    if X is None:
        raise FileNotFoundError(f"{ROUTE_SEED_OVER[0].format(t=torso)} not on disk: run corrie_f_sim.py finerun F --torso {torso}")
    out = {}
    port = _route_port(torso) if keep_port else {}
    m = fine_mesh(torso)
    for s in ("R", "L"):
        P, surf, A, B, k = crown_path(X, torso, s)
        out[s] = {"vias": _vias_head_first(path_vias(P, X, surf)), "b22": k, "anchor": [float(v) for v in A],
                  "mode": "cinched", "pretension_n": CROWN_PRE_N}
        if keep_port:
            out[s]["extra"] = {f"TP_{s}": {"nodes": [m["b22"][s]] + port[s]["vias"], "anchor": [float(v) for v in m["anchor"][s]],
                                           "mode": "elastic", "pretension_n": 30.0}}
    return out


def _route_wrap_fixed(torso: int) -> dict:
    """BL-028's 'wrap' with its eyelets in cable order (B-22 first). A check run for section 14.8, not a design."""
    r = _route_wrap(torso)
    for s in ("R", "L"):
        r[s]["vias"] = _vias_head_first(r[s]["vias"])
    return r


ROUTES.update({"over": _route_over, "over_port": lambda t: _route_over(t, True), "wrapfix": _route_wrap_fixed})

# ---- BL-033 task 2: B-22 as the rev 3 pattern places it (patterns_corrie_f_rev3 drew it 18.7 mm inboard of the drawn
# x +/-149, because a 50 mm tab at 149 lies over the hinge band | blade seam at z 695). One source for both.
B22_DRAWN = (149.0, 695.0)    # corrie_body.md section 4 B-02h row / guy_geometry: B-22 at x +/-149, z 695
B22_W = 50.0                  # attach_system.drawing_pieces B-22 50 x 60
B22_EDGE_CLEAR = 6.0          # ASSUMPTION: tab edge >= 6 mm inside the band | blade seam line (presser foot); settled by
#                               sewing the first hinge band
B22_FALLBACK = {"x": 149.0, "tab_w": 38.0}   # ticket BL-033 task 2: a 38 mm tab at x +/-149 if the moved tab fails


def b22_placement(c: ShellF | None = None, tab_w: float = B22_W, x_want: float = B22_DRAWN[0]) -> dict:
    """Where a ``tab_w`` wide B-22 can sit on the hinge band at z 695: the band's flat half width there (aft face
    a(z) less the D2 blade) less the edge clearance and half the tab. Same flat maps as the pattern (``_face_xy``)."""
    c = c or make()
    z = B22_DRAWN[1]
    with frame_face(c):
        _, S, A = _face_xy(c)
    band = A(z) - float(blade_w(c, z))
    x_max = band - B22_EDGE_CLEAR - tab_w / 2
    x = min(x_want, x_max)
    return {"z": z, "band_half_w_mm": round(band, 1), "x_max_mm": round(x_max, 1), "x_mm": round(x, 1),
            "moved_mm": round(x_want - x, 1), "tab_w_mm": tab_w, "fits_at_want": x_want <= x_max + 1e-9}


def _row_node(torso: int, side: str, x: float) -> int:
    """Hinge-band node on the scenario B-22 node's own mesh row (same drafted z) nearest x. ASSUMPTION B22-NODE: the fine
    mesh (h 25) has no node at (130.3, 695); the row of the scenario B-22 (z 682) isolates the x move, and its nearest
    node (x 125.3) is 5 mm MORE inboard than drafted (conservative for the guy's lifter gap and pull angle)."""
    m = fine_mesh(torso)
    X0 = m["X0"]
    z0 = X0[m["b22"][side], 2]
    idx = np.array([j for j, p in enumerate(m["piece"]) if p == "B-02h" and abs(X0[j, 2] - z0) < 1.0])
    return int(idx[np.argmin(np.abs(X0[idx, 0] - x))])


def _route_over_port_at(torso: int, x22: float, z22: float) -> dict:
    """'over_port' (rev 3) with the inside port guy's B-22 end moved to x22 on the scenario B-22 row (``_row_node``)."""
    out = _route_over(torso, True)
    for s, sx in (("R", 1), ("L", -1)):
        out[s]["extra"][f"TP_{s}"]["nodes"][0] = _row_node(torso, s, sx * x22)
    return out


def _route_over_port_b22in(torso: int) -> dict:
    p = b22_placement()
    return _route_over_port_at(torso, p["x_mm"], p["z"])


ROUTES.update({"over_port_b22in": _route_over_port_b22in,
               "over_port_b22fb": lambda t: _route_over_port_at(t, B22_FALLBACK["x"], B22_DRAWN[1])})

B22_CHECK = HERE / "corrie_f_sim" / "corrie_f_b22in.json"
B22_RUN = ("F_PR15_fineFM_over_port_b22in", "F_r1_PR15_fineFM_over_port_b22in")
B22_BASE = ("F_PR15_fineFM_over_port", "F_r1_PR15_fineFM_over_port")


def bl033_b22_check(write: bool = True) -> dict:
    """BL-033 task 2: rev 3 (crown straps + port guy) at 15 in, fine mesh, with B-22 on the hinge band where the pattern
    puts it (``b22_placement``; sim node ``_row_node``), against the stored rev 3 run with B-22 at x 149. Acceptance
    (ticket): meat CG <= CG_TARGET, lifter gap >= MIN_CLEAR_MM (crown strap and port guy outside run), R-28 >= 31 deg.
    Needs the run (``corrie_f_sim.py finerun F --torso 15 --route over_port_b22in``) and both drapes on disk; the
    result is written to B22_CHECK (tracked) so it can be read without them."""
    S = _sim()
    rows = S.load_results()["rows"]
    out = {"placement": b22_placement(), "runs": {}, "cg_target_mm": CG_TARGET, "min_clear_mm": MIN_CLEAR_MM,
           "r28_min_deg": 31.0, "fallback": B22_FALLBACK}
    m = fine_mesh(15)
    for tag, (key, folder) in (("moved", B22_RUN), ("drawn_149", B22_BASE)):
        r = rows.get(key)
        if r is None:
            raise FileNotFoundError(f"{key} not in corrie_f_sim_results.json")
        spec = r.get("route", {})
        node = {s: (spec.get(s, {}).get("extra", {}).get(f"TP_{s}", {}).get("nodes") or [m["b22"][s]])[0] for s in "RL"}
        p = bl029_paths(runs=[(key, folder, 15, "over_port")], write=False)["rows"]
        gaps = [v[s][k] for v in p.values() for s in "RL" for k in ("lifter_gap_mm", "port_lifter_gap_mm") if k in v[s]]
        c = r["cases"]
        out["runs"][tag] = {
            "run": key, "b22_node_x_mm": {s: round(float(m["X0"][node[s], 0]), 1) for s in "RL"},
            "b22_node_z_mm": {s: round(float(m["X0"][node[s], 2]), 1) for s in "RL"},
            "meat_cg_y_mm": c["meat"]["cg_y"], "fill_cg_y_mm": c["fill"]["cg_y"],
            "meat_converged": c["meat"]["converged"], "fill_converged": c["fill"]["converged"],
            "r28_deg": min(r["r28"]["fill"]["worst_contact_deg"], r["r28"]["meat"]["worst_contact_deg"]),
            "lifter_gap_min_mm": round(min(gaps), 1),
            "port_guy_1g_n": max(c[cn]["loads_1g"].get(f"TP_{s}", 0.0) for cn in ("fill", "meat") for s in "RL"),
            "im3_1g_n": max(c[cn]["loads_1g"].get(f"hook_im520_{s}", 0.0) for cn in ("fill", "meat") for s in "RL")}
    mv = out["runs"]["moved"]
    out["acceptance"] = {"cg_ok": mv["meat_cg_y_mm"] <= CG_TARGET and mv["meat_converged"],
                         "lifter_ok": mv["lifter_gap_min_mm"] >= MIN_CLEAR_MM, "r28_ok": mv["r28_deg"] >= 31.0}
    out["pass"] = all(out["acceptance"].values())
    out["use_fallback"] = not out["pass"]
    if write:
        B22_CHECK.write_text(json.dumps(out, indent=1, default=_j))
    return out


# ---- the crown lid B-29 (BL-029 look rules, docs/research/top_anchor_and_lids.md section 7)
# The lid is the bag's cap, not a box on the roll: plan = the closed top's footprint (a rounded square, superellipse
# n 4, the bag's corner language), a low boxing wall and a domed crown, base on the roll. Two channels on the crown at
# x +/-52 carry the B-28 crown straps, so the strap line runs unbroken from the bar over the lid to the hinge band.
# The boxing wall is solid body fabric except two camo corner caps at the aft corners, in line with the D2 camo
# blades below them (O-6 accents only). A #5 coil zip runs along the aft wall under the straps' front runs.
LID = {"W": 350.0,          # DECISION: plan width, 10 mm inside the 360 mm collar seam (flush with the closed roll)
       "D": 210.0,          # DECISION: collar depth 165 + 25 mm aft overhang (the lid's aft wall sits over the hinge
       #                      band seam, so lid edge and panel break line up) + 20 mm over the roll's frame side
       "wall": 30.0,        # DECISION: boxing wall height
       "dome": 55.0,        # DECISION: crown rise above the wall
       "n": 4.0,            # superellipse exponent of the plan (rounded square)
       "cap_mm": 90.0,      # camo corner cap: 90 mm of perimeter each side of each aft corner (blade cap)
       "zip_mm": 470.0,     # #5 coil zip along the aft wall and round both aft corners (W + 2 x 60)
       "channel_w": 30.0}   # strap channel width (25 mm webbing + 5 mm ease)
LID_SLIDER5_G = 3.0         # ASSUMPTION: #5 coil slider with a cord pull loop (bag_weight_plan.md gives 4.0 g for #8)
LID_THREAD = 0.03           # ASSUMPTION: thread and bartacks 3 % of the lid's fabric mass (no record; weigh the 1st lid)


def _lid_grid(n: int = 241):
    W, D, p = LID["W"], LID["D"], LID["n"]
    x = np.linspace(-W / 2, W / 2, n)
    y = np.linspace(-D / 2, D / 2, n)
    Xg, Yg = np.meshgrid(x, y)
    r = (np.abs(2 * Xg / W) ** p + np.abs(2 * Yg / D) ** p) ** (1.0 / p)
    inside = r <= 1.0
    h = np.where(inside, LID["wall"] + LID["dome"] * np.sqrt(np.clip(1.0 - r ** p, 0.0, 1.0)), 0.0)
    return x, y, h, inside


def lid_geometry() -> dict:
    """Plan area, perimeter, crown surface area and volume of B-29 (numerical, from LID). The volume is counted
    OUTSIDE the 85 L main bag (as every peer lid: docs/research/top_anchor_and_lids.md section 8)."""
    x, y, h, inside = _lid_grid()
    dx, dy = x[1] - x[0], y[1] - y[0]
    area = float(inside.sum() * dx * dy)
    vol = float(h[inside].sum() * dx * dy) / 1e6
    dom = np.where(inside, h - LID["wall"], 0.0)
    gy, gx = np.gradient(dom, dy, dx)
    crown = float((np.sqrt(1 + gx ** 2 + gy ** 2)[inside]).sum() * dx * dy)
    t = np.linspace(0, 2 * np.pi, 2000)
    W, D, p = LID["W"], LID["D"], LID["n"]
    px = W / 2 * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / p)
    py = D / 2 * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / p)
    per = float(np.hypot(np.diff(px), np.diff(py)).sum())
    # channel run over the crown at x = CROWN_X (front-back arc length of the dome along y)
    j = int(np.argmin(np.abs(x - CROWN_X)))
    col = dom[:, j]
    ch = float(np.hypot(np.diff(y), np.diff(col))[inside[1:, j]].sum())
    return {"plan_W_mm": W, "plan_D_mm": D, "height_mm": LID["wall"] + LID["dome"], "plan_area_mm2": round(area),
            "perimeter_mm": round(per, 1), "crown_area_mm2": round(crown), "volume_L": round(vol, 2),
            "volume_cu_in": round(vol * 61.0237, 0), "channel_run_mm": round(ch, 1)}


_LID_H = {}


def lid_hours_drafted() -> dict:
    """BL-033: the lid's build hours on the DRAFTED B-29 pattern (patterns_corrie_f_rev3.lid_hours_ops: BL-030's seam
    list on the drafted pieces, plus the four crown darts the dome needs). Lazy import: the pattern module reads this
    one. Cached per LID (the pattern is drawn from LID alone)."""
    key = tuple(sorted(LID.items()))
    if key not in _LID_H:
        import importlib
        PR = importlib.import_module("patterns_corrie_f_rev3")
        ops = PR.lid_hours_ops()
        _LID_H[key] = {"hours": ops["hours"], "pieces_cut": ops["pieces_cut"],
                       "source": "patterns_corrie_f_rev3.lid_hours_ops (drafted B-29, bag_concepts.HOURS rates)"}
    return _LID_H[key]


def crown_lid(fabrics: str = "B") -> dict:
    """B-29 crown lid: pieces x record gsm + zip record + ASSUMPTION slider / thread. Crown and wall in the body
    fabric, base in the collar fabric (70D: it lies on the roll), camo corner caps in the 630D printable."""
    g = lid_geometry()
    body, base_f = fab("body", fabrics), fab("collar", fabrics)
    SA = SA_BODY
    per = g["perimeter_mm"]
    crown = (g["crown_area_mm2"] + per * SA) * _gsm(body)
    base = (g["plan_area_mm2"] + per * SA) * _gsm(base_f)
    cap = 4 * LID["cap_mm"]
    wall_h = LID["wall"] + 2 * SA
    wall = ((per - cap) * _gsm(body) + cap * _gsm(CAMO)) * wall_h
    chan = 2 * (g["channel_run_mm"] + 2 * SA) * (LID["channel_w"] + 2 * SA) * _gsm(body)
    fabric_g = (crown + base + wall + chan) / 1e6
    zip_g = _rec("coil_zipper_5", "mass_g_m") * (LID["zip_mm"] + 60.0) / 1000.0 + LID_SLIDER5_G + CORD_PULL_G
    mass = fabric_g * (1 + LID_THREAD) + zip_g
    H = BC.HOURS
    pieces = 9                      # crown, base, 3 body wall runs, 2 camo corner caps, 2 strap channels
    hours = (pieces * H["cut_piece"] + 2 * per / 1000 * H["curved_m"] + H["zip_fixed"] + LID["zip_mm"] / 1000 * H["zip_m"]
             + 2 * H["zip_corner"] + 2 * 2 * g["channel_run_mm"] / 1000 * H["straight_m"] + 4 * H["bartack"]
             + 4 * 2 * 0.05 * H["applique_m"])
    dr = lid_hours_drafted()
    return {"id": "B-29", **g, "mass_g": round(mass, 1), "fabric_g": round(fabric_g, 1), "zip_g": round(zip_g, 1),
            "hours": dr["hours"], "hours_bl029": round(hours, 2), "hours_source": dr["source"], "pieces": pieces,
            "source": f"{body} / {base_f} / {CAMO} records x cut area (lid_geometry) + coil_zipper_5 record; "
                      "LID_SLIDER5_G, LID_THREAD ASSUMPTIONS"}


LID_WALL_CLOSE = 2          # DECISION (BL-030 seam list): the wall ring is closed with two short vertical seams, one at
#                             each end of the zipped aft run (front run | aft run)


def lid_seam_list() -> dict:
    """BL-030 task 5: a pattern-maker style check of the B-29 build hours, operation by operation from the lid's seam
    list, on the same bag_concepts.HOURS rates BL-029 used. Differences from ``crown_lid``'s one-line estimate:
    the zip splits the aft wall into an upper and a lower strip (one more piece); crown | wall and wall | base are each
    a CLOSED ring seam (HOURS 'ring' handling, which the BL-029 sum left out); the wall ring has two closing seams.
    Lengths from ``lid_geometry`` and ``LID``."""
    H = BC.HOURS
    g = lid_geometry()
    per, ch, L = g["perimeter_mm"] / 1000.0, g["channel_run_mm"] / 1000.0, LID
    wall_h = (L["wall"] + 2 * SA_BODY) / 1000.0
    ops = [
        ("cut, mark, notch: crown, base, front wall run, aft wall upper + lower (split by the zip), 2 camo caps, "
         "2 strap channels", 10, H["cut_piece"]),
        ("strap channels topstitched to the crown, both edges (2 x 2 runs)", 4 * ch, H["straight_m"]),
        ("bartacks at the 4 channel ends (strap entries)", 4, H["bartack"]),
        ("camo caps turned and topstitched on the wall, short edges (4 x 2)", 8 * 0.05, H["applique_m"]),
        ("#5 coil zip set between the aft wall strips: tape baste, stops, slider", 1, H["zip_fixed"]),
        ("#5 coil zip sewn, both tapes", L["zip_mm"] / 1000.0, H["zip_m"]),
        ("zip round the two aft corners", 2, H["zip_corner"]),
        ("wall ring closed: two short vertical seams", LID_WALL_CLOSE * wall_h, H["straight_m"]),
        ("crown | wall perimeter (curved, notch match, bind)", per, H["curved_m"]),
        ("crown | wall: closed ring handling", 1, H["ring"]),
        ("wall | base perimeter (curved, notch match, bind), turned through the zip", per, H["curved_m"]),
        ("wall | base: closed ring handling", 1, H["ring"]),
    ]
    rows = [{"op": n, "qty": round(q, 3), "rate_h": r, "hours": round(q * r, 2)} for n, q, r in ops]
    tot = round(sum(q * r for _, q, r in ops), 2)
    est = crown_lid()["hours_bl029"]
    with revision(1):
        pouch_h = addons()["top_pouch"]["hours"]
    return {"rows": rows, "hours": tot, "bl029_estimate_h": est, "delta_h": round(tot - est, 2),
            "pieces": 10, "pouch_h": pouch_h, "vs_pouch_h": round(tot - pouch_h, 2),
            "note": "pattern-maker style check by the pack-designer on the HOURS rates (no drafted lid pattern yet); "
                    "the pattern-maker confirms on the drafted B-29 pattern"}


CROWN_TAIL = 150.0         # tail past the ladder lock (the W1-W3 rule after A-2)
CROWN_LOOP = 60.0          # rear toggle loop (folded 2 x 30 mm, the B-25 tab rule)


def crown_strap_length(rows=None) -> dict:
    """B-28 webbing per strap = longest taut path over the simulated tops (stored 'over' drapes, both sides) + the
    lid's crown height (the lid lies between strap and roll; the sim models it as a load, not a solid) + tail + loop."""
    gp = json.loads(CROWN_PATHS.read_text()) if CROWN_PATHS.exists() else {"rows": {}}
    L = [max(r["R"]["length_mm"], r["L"]["length_mm"]) for r in gp["rows"].values()]
    Lmax = max(L) if L else None
    if Lmax is None:
        return {"path_mm": None}
    cut = Lmax + 2 * (LID["wall"] + LID["dome"]) + CROWN_TAIL + CROWN_LOOP
    return {"path_mm": round(Lmax, 1), "cut_mm": round(cut, 1), "mass_g_pair": round(2 * cut * WEB25 / 1000, 2)}


CROWN_PATHS = HERE / "corrie_f_sim" / "corrie_f_crown_paths.json"


def crown_straps_bl029() -> dict:
    """BL-029's B-28 as proposed (history): 25 mm, one cut from the sim paths (``crown_strap_length``) + rear POM
    toggle loop into the B-25 bridle tab (attach_diet.TOGGLE_G ASSUMPTION; a second 60 mm fold on each B-25 tab takes
    it, so the guy keeps its own tab) + heavy 25 mm ladder lock at the front (ladder_lock_25mm_heavy record, BL-010 A3
    rule) on a 60 mm webbing tab caught in the hinge band B-02h | B-06 seam at x +/-CROWN_X."""
    import attach_diet as AD
    L = crown_strap_length()
    if L.get("cut_mm") is None:
        raise FileNotFoundError(f"{CROWN_PATHS.name} missing: run corrie_f.py --bl029")
    tog, llh = AD.TOGGLE_G, _rec("ladder_lock_25mm_heavy", "mass_g")
    tab = 60.0 * WEB25 / 1000.0
    g = L["mass_g_pair"] + 2 * (tog + llh + 2 * tab)       # front tab on the hinge band + a 2nd fold on each B-25 tab
    return {"id": "B-28", **L, "width_mm": 25.0, "mass_g": round(g, 2), "toggle_g": tog, "ladder_lock_g": llh,
            "source": "poly_webbing_25mm, ladder_lock_25mm_heavy records x cut length (taut path over the stored "
                      "drapes + lid height + tail + loop); TOGGLE_G ASSUMPTION (attach_diet)"}


def crown_straps(width: float | None = None, kit: str | None = None) -> dict:
    """B-28 crown straps (pair) at the current revision. Rev 3 (BL-031, owner 2026-11-12): **25 mm, cut per crown kit**
    (``crown_kit_straps(kit)``, default kit ``CROWN_KIT_DEFAULT`` = M, the ledger's headline size), a heavy ladder
    lock at each end, tail keepers where the rule asks. ``width`` 20 gives BL-030's 20 mm diet (history,
    ``crown_strap_diet()["options"]["w20"]``); revs without ``crown_kits`` give BL-029's one cut (``crown_straps_bl029``)."""
    w = crown_strap_w() if width is None else float(width)
    if w == 20.0:
        d = crown_strap_diet()
        return {"id": "B-28", **d["options"]["w20"]}
    if w != 25.0:
        raise ValueError(f"no B-28 at {w} mm (25 mm per kit, or the 20 mm BL-030 history)")
    if not REVS[REVISION].get("crown_kits"):
        return crown_straps_bl029()
    k = crown_kit_straps(kit or CROWN_KIT_DEFAULT)
    return {"id": "B-28", **k}


# ---- BL-030 crown strap diet (doc section 15.2). BL-029 cut the strap from the longest SIM path (818 mm, 15 in full),
# but the sim never rolls the collar: with the lid on, the top is always rolled. The cut is sized here from the strap's
# path over the ROLLED top with the lid (cloth pass, 19 in, day / 6-day / full: ``CROWN_ROLLED``) plus the change of the
# path with the torso setting, taken from the sim paths (same bag, bar at z 601 / 703 / 804).
# ASSUMPTION ROLL-PATH: the cloth pass's rolled top stands in for the sewn bag's (the render drape is seeded by the
#   fine sim; LID-SEAT), and the torso change of the path on the rolled top equals the sim's on the unrolled top (the
#   change is in the frame-face run, below the roll). Settled by T9: measure the crown strap's free length cinched at
#   the S kit full and at the L kit 6-day on the first sewn bag.
WEB20_GM = 18.0 * 20.0 / 25.0      # ASSUMPTION: 20 mm heavyweight polyester webbing, poly_webbing_25mm scaled by width
#                                    (14.4 g/m; no 20 mm record). Settled by weighing 1 m of the bought 20 mm webbing
WEB20_BREAK_N = 13344.0 * 20.0 / 25.0   # ASSUMPTION: same width scaling of the 25 mm record's break (10.7 kN)
LL20 = {"tensile_n": 65.0 * 9.80665,    # ITW Classic Ladderloc 20 mm "20mm - 65Kg" (Ace Supplies UK listing, method not
        #                                 stated, https://www.acesupplies.co.uk/products/standard-ladderlock/, read
        #                                 2026-11-12); the Super Ladderloc is listed in 25 mm only
        "slip_ratio": 0.5,              # ASSUMPTION: slip = 0.5 x tensile, the ladder_lock_25mm / _heavy record basis
        "mass_g": 4.0 * 20.0 / 25.0}    # ASSUMPTION: ladder_lock_25mm record (4 g) scaled by width; weigh one
#  -> settled by the B-28 slip gate (5 locks on the bought 20 mm webbing, 50 mm/min, no slip > 5 mm below 288 N,
#     dry / wet, 20 C / -20 C) and by weighing; a materials-engineer record for both parts is the clean fix (section 15.6)
GUY_1G_MAX_N = 96.0        # BL-029 table (bl029_table rev3 port guy 1 g max, 23 in fill); x CASE_FACTOR = 288 N
CASE_FACTOR = 3.0          # HA-LS-1 rev C C5 limit factor (load_standard.md section 4)
LID_FILL_KG = 1.0          # the 1 kg in the lid (LID-SIM, section 14.5)
EXT_LAP = 40.0             # ASSUMPTION: extender webbing sewn round its ladder lock's bar (2 x 20 mm); settled by the pattern


def _crown_torso_delta() -> dict:
    """Change of the crown strap path with the torso setting, from the stored rev 3 sim paths (unrolled top):
    L(t) - L(19 in), per side and case; max at 15 in, min at 23 in."""
    gp = json.loads(CROWN_PATHS.read_text())["rows"]
    out = {}
    for t in (15, 23):
        d = []
        for cn in ("fill", "meat"):
            a = gp.get(f"F_r1_PR{t}_fineFM_{REV3_ROUTE}:{cn}")
            b = gp.get(f"F_r1_PR19_fineFM_{REV3_ROUTE}:{cn}")
            if a and b:
                d += [a[s]["length_mm"] - b[s]["length_mm"] for s in ("R", "L")]
        out[t] = d
    return {"d15_max_mm": round(max(out[15]), 1), "d23_min_mm": round(min(out[23]), 1), "all": out}


def crown_strap_diet() -> dict:
    """B-28 cut from the rolled-top path (ROLL-PATH): path range over day / 6-day / full at 19 in, shifted by the
    15 in (longest) and 23 in (shortest) torso change; cut = longest + tail + rear loop. Mass at 25 mm and 20 mm, the
    hardware ratings against the loads (crown strap 1 g max from the sims, the 80 N hand cinch, the port guy's 96 N
    x 3.0 = 288 N as an envelope in case the crown strap ever has to hold the top alone, the loaded lid at 3 g)."""
    import attach_diet as AD
    if not CROWN_ROLLED.exists():
        raise FileNotFoundError(f"{CROWN_ROLLED.name} missing: python -m huntkit.viz3d.corrie_f --crown-paths")
    rp = json.loads(CROWN_ROLLED.read_text())
    st = rp["states"]
    Ls = {k: max(v["straps"][s]["length_mm"] for s in v["straps"]) for k, v in st.items() if v.get("straps")}
    Lmin_s = {k: min(v["straps"][s]["length_mm"] for s in v["straps"]) for k, v in st.items() if v.get("straps")}
    td = _crown_torso_delta()
    L_max = max(Ls.values()) + td["d15_max_mm"]
    L_min = min(Lmin_s.values()) + td["d23_min_mm"]
    cut = L_max + CROWN_TAIL + CROWN_LOOP
    tail_short = cut - CROWN_LOOP - L_min
    tog = AD.TOGGLE_G
    gp = json.loads(CROWN_PATHS.read_text())["rows"]
    t1g = max(max(r[s].get("T_bar_n") or 0.0 for s in ("R", "L")) for r in gp.values()
              if r.get("route") == REV3_ROUTE)
    lid_kg = crown_lid()["mass_g"] / 1000.0 + LID_FILL_KG
    loads = {"crown_1g_max_n": round(t1g, 1), "crown_factored_n": round(CASE_FACTOR * t1g, 1),
             "hand_cinch_n": CROWN_PRE_N, "guy_envelope_factored_n": CASE_FACTOR * GUY_1G_MAX_N,
             "lid_3g_n": round(3 * 9.80665 * lid_kg, 1)}
    demand = max(loads["crown_factored_n"], loads["hand_cinch_n"], loads["guy_envelope_factored_n"])
    opts = {}
    for w, gm, brk, lock, lock_g, slip, ten, rec in (
            (25.0, WEB25, _rec("poly_webbing_25mm", "breaking_strength_n"), "ladder_lock_25mm_heavy",
             _rec("ladder_lock_25mm_heavy", "mass_g"), _rec("ladder_lock_25mm_heavy", "slip_load_n"),
             _rec("ladder_lock_25mm_heavy", "tensile_rating_n"), "poly_webbing_25mm, ladder_lock_25mm_heavy records"),
            (20.0, WEB20_GM, WEB20_BREAK_N, "ITW Classic Ladderloc 20 mm", LL20["mass_g"], LL20["slip_ratio"] * LL20["tensile_n"],
             LL20["tensile_n"], "WEB20_GM, LL20 (cited tensile; slip and masses ASSUMPTIONS)")):
        web = 2 * cut * gm / 1000.0
        hw = 2 * (tog + lock_g + 60.0 * gm / 1000.0 + 60.0 * WEB25 / 1000.0)   # toggle, lock, front tab, B-25 2nd fold
        opts[f"w{w:.0f}"] = {"width_mm": w, "cut_mm": round(cut, 1), "path_mm": round(L_max, 1),
                             "mass_g": round(web + hw, 2), "webbing_g": round(web, 2), "toggle_g": tog,
                             "ladder_lock": lock, "ladder_lock_g": round(lock_g, 2),
                             "slip_n": round(slip, 1), "tensile_n": round(ten, 1), "webbing_break_n": round(brk, 0),
                             "margin_slip": round(slip / demand, 2), "margin_tensile": round(ten / demand, 2),
                             "margin_webbing": round(brk / demand, 1),
                             "source": f"{rec} x cut (crown_strap_diet: rolled path + torso change + tail + loop); "
                                       "TOGGLE_G ASSUMPTION (attach_diet)"}
    # option: cut for the part-full states (day, 6-day) and a 20 mm extender (webbing + ladder lock, one a side) for the
    # full load with the collar standing. Owner choice (doc section 15.2): lighter and a shorter tail, one more part.
    part = [v for k, v in Ls.items() if k != "full"]
    if part and "full" in Ls:
        cut_e = max(part) + td["d15_max_mm"] + CROWN_TAIL + CROWN_LOOP
        ext = Ls["full"] - max(part) + CROWN_LOOP + EXT_LAP
        o = dict(opts["w20"])
        web = 2 * cut_e * WEB20_GM / 1000.0
        o.update(cut_mm=round(cut_e, 1), path_mm=round(max(part) + td["d15_max_mm"], 1),
                 webbing_g=round(web, 2), mass_g=round(web + o["mass_g"] - o["webbing_g"], 2),
                 extender_mm=round(ext, 1), extender_g_pair=round(2 * (ext * WEB20_GM / 1000.0 + LL20["mass_g"]), 2),
                 tail_at_shortest_mm=round(cut_e - CROWN_LOOP - L_min, 1),
                 source=o["source"] + "; extender = full - part-full path + loop + lap (EXT_LAP ASSUMPTION)")
        opts["w20_ext"] = o
    bl029 = crown_straps_bl029()
    for o in opts.values():
        o["delta_vs_bl029_g"] = round(o["mass_g"] - bl029["mass_g"], 2)
    chosen = opts["w20"]       # BL-030 adopted 20 mm (history since BL-031: rev 3 is 25 mm per kit, crown_kit_straps)
    return {"rolled_19in_mm": {k: round(v, 1) for k, v in Ls.items()}, "torso": td, "path_max_mm": round(L_max, 1),
            "path_min_mm": round(L_min, 1), "adjust_range_mm": round(L_max - L_min, 1), "cut_mm": round(cut, 1),
            "tail_at_shortest_mm": round(tail_short, 1), "loads": loads, "demand_n": demand, "options": opts,
            "bl029_g": bl029["mass_g"], "bl029_cut_mm": bl029["cut_mm"], "chosen": chosen,
            "pass": chosen["margin_slip"] >= 1.0 and chosen["margin_tensile"] >= 1.0}


MU_LID = MU_SENS[0]        # lid base (70D) on the roll and strap in channel: the low end of the MU_WEB_FAB band (0.20)


def lid_hold(T_relaxed_n: float | None = None) -> dict:
    """Paper check of the lid's hold (doc section 15.3), loaded lid (B-29 + 1 kg) at 1 g and 3 g. Two crown straps
    wrap the lid by theta (cloth-pass path, 6-day, CROWN_ROLLED); each presses it on the roll with 2 T sin(theta/2).
    (a) lid thrown outward (pack dropped on its top, or swung): the straps must hold m a: tension added per strap
        m a / (2 x 2 sin(theta/2)), on top of the cinch; against the ladder-lock slip.
    (b) lid sliding fore-aft or sideways on the roll (fall on the side, snag): friction mu (m g + clamp) with T at the
        hand cinch and at the relaxed 1 g value (sims: the cinch relaxes as the top settles). Sideways the channels
        tie the lid to the straps, so the straps would have to slide on the bag: the same friction bound.
    (c) drop on the base (pack set down hard, 3 g down): the lid bears on the roll; straps unloaded.
    (d) geometric capture: see ``captured_by_state``."""
    rp = json.loads(CROWN_ROLLED.read_text())
    th = min(v["straps"][s]["wrap_lid_deg"] for k, v in rp["states"].items() if k == "sixday" for s in v["straps"])
    gp = json.loads(CROWN_PATHS.read_text())["rows"]
    if T_relaxed_n is None:
        T_relaxed_n = min(min(r[s].get("T_bar_n") or 1e9 for s in ("R", "L")) for r in gp.values()
                          if r.get("route") == REV3_ROUTE)
    m = crown_lid()["mass_g"] / 1000.0 + LID_FILL_KG
    k = 2.0 * math.sin(math.radians(min(th, 180.0)) / 2.0)   # wrap over 180 deg adds no more clamp than 180
    slip = crown_straps()["slip_n"]            # the current B-28's ladder lock (BL-031: 25 mm heavy, 490 N)
    wraps = {k: round(min(v["straps"][s]["wrap_lid_deg"] for s in v["straps"]), 1) for k, v in rp["states"].items()
             if v.get("straps")}
    out = {"lid_kg": round(m, 3), "wrap_deg": round(th, 1), "clamp_factor": round(k, 3), "mu": MU_LID,
           "wrap_by_state_deg": wraps,
           # (d) with >= 180 deg of wrap both strap runs leave the lid downward: a fore-aft shift must stretch the
           #     strap (geometric capture, not friction). Under 180 deg (full, collar standing) only friction holds it
           "captured_by_state": {k: v >= 180.0 for k, v in wraps.items()},
           "T_cinch_n": CROWN_PRE_N, "T_relaxed_n": round(T_relaxed_n, 1), "slip_n": slip, "cases": {}}
    for a in (1.0, 3.0):
        Fa = m * a * 9.80665
        dT = Fa / (2 * k)
        hold = {lab: MU_LID * (m * 9.80665 + 2 * k * T) for lab, T in (("cinch", CROWN_PRE_N), ("relaxed", T_relaxed_n))}
        out["cases"][f"{a:.0f}g"] = {
            "inertia_n": round(Fa, 1),
            "outward_added_T_per_strap_n": round(dT, 1),
            "outward_lock_load_n": round(CROWN_PRE_N + dT, 1), "outward_margin_slip": round(slip / (CROWN_PRE_N + dT), 1),
            "slide_hold_cinch_n": round(hold["cinch"], 1), "slide_hold_relaxed_n": round(hold["relaxed"], 1),
            "slide_ok_cinch": hold["cinch"] >= Fa, "slide_ok_relaxed": hold["relaxed"] >= Fa}
    return out


def crown_strap_w() -> float:
    """B-28 crown strap webbing width at the current revision (rev 3: 25 mm, owner 2026-11-12 / BL-031; BL-030 had put
    it on a 20 mm diet, kept as history in ``crown_strap_diet``)."""
    return float(REVS[REVISION].get("crown_w", 25.0))


CROWN_ROLLED = HERE / "corrie_f_sim" / "corrie_f_crown_rolled.json"   # huntkit.viz3d.corrie_f --crown-paths (BL-030)


# ---- BL-031: B-28 cut per crown kit, 25 mm, a ladder lock at each end; the pack-wide tail rule (doc section 16).
# Owner 2026-11-12: "Different sizes. We don't want straps hanging everywhere." and 25 mm crown straps.
TAIL_RULE_MM = 100.0       # DECISION (BL-031): free tail <= 100 mm (4 in) at the most-used setting (6-day load, mid
#                            torso of the crown kit / mid waist of the belt size), measured from the adjuster
KEEPER_OVER_MM = 150.0     # DECISION (BL-031): a strap whose tail can pass 150 mm (6 in) at ANY setting gets a keeper
#                            (a 6 in tail of 25 mm webbing lies along its strap; a longer one swings and snags)
TAIL_GRIP_MM = 50.0        # ASSUMPTION: the shortest free tail a gloved hand pinches and pulls through a 25 mm ladder
#                            lock (two gloved finger widths ~ 40 mm + 10 mm); settled by the gloved cinch trial in T9
#                            (BL-031 addition: 5 users, winter gloves, each strap at its longest setting)
CROWN_ADJ = 2              # BL-031 task 1: the slack range is shared by two adjusters, a heavy ladder lock at each end
CROWN_TAB = 60.0           # front (hinge band) and rear (B-25 toggle) lock tabs, folded 2 x 30 mm (the B-25 tab rule)
CROWN_KIT_DEFAULT = "M"    # the ledger's headline crown kit (weight_rollup_v2.KIT)
CROWN_STATES = ("day", "sixday", "full")
MOST_USED_STATE = "sixday"  # the tail rule's most-used load: 6-day, 45 L (loadouts.yaml), lid on


TAIL_KEEPER_G = 0.6        # ASSUMPTION (attach_system.mass_delta "guy tail elastic keepers x2": 2 x 0.6 g): one 25 mm
#                            elastic keeper, a closed loop that slides on the strap and holds the rolled tail. No
#                            elastic-band record; settled by weighing 10 cut keepers (BL-031 addition to T9)


def tail_keeper_g() -> float:
    return TAIL_KEEPER_G


def crown_kits() -> dict:
    """BL-017 crown kits (owner 2026-11-11): torso range in inches, ``crown_diet.SIZES``."""
    from huntkit.gendesign import crown_diet as CDI
    return dict(CDI.SIZES)


def _crown_delta_at(t_in: float) -> list:
    """Change of the crown strap path with the torso setting at ``t_in`` (per side and case, mm), piecewise linear
    between the stored rev 3 sims at 15 / 19 / 23 in (``_crown_torso_delta``; 0 at 19 in by definition). ASSUMPTION
    TORSO-LIN: linear between the sim torsos; the bar height is linear in the torso setting (build_geometry
    crown_settings), and the 15-19 and 19-23 deltas are near-symmetric (+59..+98 / -89..-92 mm). Settled with ROLL-PATH
    by T9 (free length measured at both ends of each kit)."""
    td = _crown_torso_delta()["all"]
    return [float(np.interp(t_in, (15.0, 19.0, 23.0), (a, 0.0, b))) for a, b in zip(td[15], td[23])]


def crown_kit_straps(kit: str = CROWN_KIT_DEFAULT, adjusters: int = CROWN_ADJ) -> dict:
    """B-28 crown strap pair for one crown kit (BL-031), 25 mm, from the BL-030 rolled-top paths (``CROWN_ROLLED``,
    19 in, day / 6-day / full with the collar standing) moved to the kit's own torso range (``_crown_delta_at``).

    * longest path = full at the kit's shortest torso (largest delta); shortest = day at its longest torso;
      most-used = 6-day at the kit's mid torso (mean of the two sides and cases).
    * cut = longest + ``adjusters`` x TAIL_GRIP (each adjuster keeps a gloved grip at the longest path); the free tail
      at each adjuster at path L is TAIL_GRIP + (longest - L) / adjusters (the user takes up evenly at both ends).
    * hardware per strap: ``adjusters`` heavy ladder locks (ladder_lock_25mm_heavy, BL-010 A3), a 60 mm tab per lock
      (front: hinge band at z 700; rear: the POM toggle into the second fold of the B-25 tab, which stays), the
      toggle (attach_diet.TOGGLE_G), the B-25 second fold; a tail keeper per adjuster when a tail can pass
      KEEPER_OVER_MM. ``adjusters`` 1 gives the one-lock comparison (rear end a sewn toggle loop, as BL-029)."""
    import attach_diet as AD
    lo, hi = crown_kits()[kit]
    mid = 0.5 * (lo + hi)
    rp = json.loads(CROWN_ROLLED.read_text())["states"]
    Lmax_s = {k: max(v["straps"][s]["length_mm"] for s in v["straps"]) for k, v in rp.items() if v.get("straps")}
    Lmin_s = {k: min(v["straps"][s]["length_mm"] for s in v["straps"]) for k, v in rp.items() if v.get("straps")}
    Lmean_s = {k: float(np.mean([v["straps"][s]["length_mm"] for s in v["straps"]])) for k, v in rp.items()
               if v.get("straps")}
    d_lo, d_hi, d_mid = _crown_delta_at(lo), _crown_delta_at(hi), _crown_delta_at(mid)
    dmax, dmin = max(d_lo + d_hi), min(d_lo + d_hi)
    L_max = max(Lmax_s.values()) + dmax
    L_min = min(Lmin_s.values()) + dmin
    by = {}                                        # path at each state x (kit short end, mid, long end)
    for st in CROWN_STATES:
        by[st] = {"short_torso": round(Lmean_s[st] + float(np.mean(d_lo)), 1),
                  "mid_torso": round(Lmean_s[st] + float(np.mean(d_mid)), 1),
                  "long_torso": round(Lmean_s[st] + float(np.mean(d_hi)), 1)}
    L_used = by[MOST_USED_STATE]["mid_torso"]
    loop = 0.0 if adjusters == 2 else CROWN_LOOP
    cut = L_max + adjusters * TAIL_GRIP_MM + loop

    def tail(L):
        return TAIL_GRIP_MM + (L_max - L) / adjusters

    tails = {st: {k: round(tail(v), 1) for k, v in row.items()} for st, row in by.items()}
    worst = tail(L_min)
    keepers = adjusters if worst > KEEPER_OVER_MM else 0
    tog, llh = AD.TOGGLE_G, _rec("ladder_lock_25mm_heavy", "mass_g")
    tabs = (adjusters + 1) * CROWN_TAB             # a tab per lock (one-lock: the front tab) + the B-25 second fold
    kg = tail_keeper_g()
    g = 2 * (cut * WEB25 / 1000.0 + tabs * WEB25 / 1000.0 + tog + adjusters * llh + keepers * kg)
    return {"kit": kit, "torso_in": (lo, hi), "width_mm": 25.0, "adjusters": adjusters,
            "path_max_mm": round(L_max, 1), "path_min_mm": round(L_min, 1), "path_used_mm": round(L_used, 1),
            "adjust_range_mm": round(L_max - L_min, 1), "cut_mm": round(cut, 1), "paths_mm": by, "tails_mm": tails,
            "tail_used_mm": round(tail(L_used), 1), "tail_worst_mm": round(worst, 1),
            "tail_rule_ok": tail(L_used) <= TAIL_RULE_MM, "keepers_per_strap": keepers,
            "mass_g": round(g, 2), "toggle_g": tog, "ladder_lock": "ladder_lock_25mm_heavy", "ladder_lock_g": llh,
            "keeper_g": kg, "slip_n": _rec("ladder_lock_25mm_heavy", "slip_load_n"),
            "tensile_n": _rec("ladder_lock_25mm_heavy", "tensile_rating_n"),
            "source": f"crown_kit_straps('{kit}'): rolled-top paths (CROWN_ROLLED, ROLL-PATH) + torso change "
                      f"(TORSO-LIN) + {adjusters} x TAIL_GRIP (ASSUMPTION); poly_webbing_25mm, ladder_lock_25mm_heavy "
                      "records; TOGGLE_G and the elastic keeper ASSUMPTIONS (attach_diet, attach_system)"}


def crown_kit_table() -> dict:
    """BL-031 table: B-28 per kit (two adjusters, as built) and the one-adjuster comparison, and the margins of the
    25 mm heavy lock on BL-030's load envelope (``crown_strap_diet()['loads']``)."""
    d = crown_strap_diet()
    demand = d["demand_n"]
    out = {"kits": {}, "one_lock": {}, "demand_n": demand, "loads": d["loads"]}
    for k in crown_kits():
        a = crown_kit_straps(k)
        a["margin_slip"] = round(a["slip_n"] / demand, 2)
        a["margin_tensile"] = round(a["tensile_n"] / demand, 2)
        out["kits"][k] = a
        out["one_lock"][k] = crown_kit_straps(k, adjusters=1)
    out["bl030_single_cut"] = {"cut_mm": d["cut_mm"], "tail_at_shortest_mm": d["tail_at_shortest_mm"],
                               "mass_g_25": d["options"]["w25"]["mass_g"], "mass_g_20": d["options"]["w20"]["mass_g"]}
    return out


def rev3_addons(ad: dict) -> dict:
    """Rev 3 (BL-029): the 2.7 L top pouch and its 4 straps leave; the B-29 crown lid and the B-28 crown straps come in.
    Both as hunted (BL-008 rule): lid off, the straps come off with it and the roll's own side clips close the bag;
    the B-27 port guys (base) hold the top either way."""
    out = {k: v for k, v in ad.items() if k not in ("top_pouch", "top_pouch_straps")}
    lid = crown_lid()
    out["crown_lid"] = {"name": f"B-29 crown lid {lid['volume_L']:.1f} L ({lid['plan_W_mm']:.0f} x {lid['plan_D_mm']:.0f}"
                                f" x {lid['height_mm']:.0f} mm, domed, camo corner caps, #5 coil zip)",
                        "system": "pouch", "cfg": "as_hunted", "mass_g": lid["mass_g"], "hours": lid["hours"],
                        "pieces": lid["pieces"], "zip_mm": LID["zip_mm"], "source": lid["source"]}
    cs = crown_straps()
    lock = "heavy ladder lock" if cs["width_mm"] == 25.0 else f"{cs['width_mm']:.0f} mm ladder lock"
    if cs.get("adjusters") == 2:      # BL-031: per kit, a lock at each end, tail keepers
        nm = (f"B-28 crown straps (2), kit {cs['kit']}: {cs['width_mm']:.0f} mm {cs['cut_mm'] / 1000:.3f} m, heavy "
              f"ladder lock at each end (B-25 toggle tab, hinge-band tab), {cs['keepers_per_strap']} tail keepers each")
        bt = 2 * (2 + 1) * BC.HOURS["bartack"]     # tabs: front, rear (+ toggle), B-25 second fold
    else:
        nm = (f"B-28 crown straps (2): {cs['width_mm']:.0f} mm {cs['cut_mm'] / 1000:.2f} m, toggle at the B-25 bridle, "
              f"{lock} on a hinge-band tab")
        bt = 2 * 2 * BC.HOURS["bartack"]
    out["crown_straps"] = {"name": nm, "system": "straps_compression",
                           "cfg": "as_hunted", "mass_g": cs["mass_g"], "hours": round(bt, 2),
                           "pieces": 0, "source": cs["source"]}
    return out


# ---- BL-029 results: crown-strap paths, lifter gaps, CG table
BL029_RUNS = [("F_PR15_fineFM_over", "F_r1_PR15_fineFM_over", 15, "over")] + \
             [(f"F_PR{t}_fineFM_over_port", f"F_r1_PR{t}_fineFM_over_port", t, "over_port") for t in (15, 19, 23)]


def bl029_paths(runs=None, write: bool = True) -> dict:
    """The crown strap's taut path (bar -> over the top -> hinge-band tab) on every stored BL-029 drape: length, wrap,
    forward share of the pull at the bar, lifter gap (both sides). For 'over_port' also the port guy's outside run
    (bar -> B-27) and its lifter gap. Written to CROWN_PATHS."""
    S = _sim()
    rows = S.load_results()["rows"]
    out = {"method": "corrie_f.crown_path: taut string over the fine drape (PATH_CLEAR) and the crown tubes",
           "min_clear_mm": MIN_CLEAR_MM, "rows": {}}
    for key, folder, t, route in (runs or BL029_RUNS):
        rr = rows.get(key, {})
        spec = rr.get("route", {})
        for case in ("fill", "meat"):
            X = drape(folder, case)
            if X is None:
                continue
            loads = rr.get("cases", {}).get(case, {}).get("loads_1g", {})
            row = {"torso": t, "case": case, "route": route, "run": folder}
            for s, sx in (("R", 1), ("L", -1)):
                k = spec.get(s, {}).get("b22")
                P, surf, A, B, k = crown_path(X, t, s, front_node=k)
                row[s] = path_metrics(P, surf, A, B, t, sx, T_n=loads.get(f"TG_{s}"))
                if route == "over_port":
                    m = fine_mesh(t)
                    Q = X[_route_port(t)[s]["vias"][0]]
                    Pp = np.linspace(m["anchor"][s], Q, 12)
                    row[s]["port_outside_mm"] = round(float(np.linalg.norm(Q - m["anchor"][s])), 1)
                    row[s]["port_lifter_gap_mm"] = round(_ribbon_gap(Pp, None, *lifter_line(t, sx)), 1)
            out["rows"][f"{folder}:{case}"] = row
    if write:
        CROWN_PATHS.write_text(json.dumps(out, indent=1, default=_j))
    return out


BL029_CG_RUNS = {     # 15 in, fine mesh, stored corrie_f_sim rows
    "rev 1 straight guy (model artefact, BL-022)": "F_PR15_fineFM",
    "rev 1 real wrap (BL-028, eyelets bar-first)": "F_PR15_fineFM_wrap",
    "rev 1 real wrap, eyelets in cable order (BL-029 check)": "F_PR15_fineFM_wrapfix",
    "guys off (misuse)": "F_PR15_fineFM_goff_sm8",
    "T1/T2: crown straps over the roll, no guy": "F_PR15_fineFM_over",
    "rev 2: B-27 port guy (BL-028)": "F_PR15_fineFM_port",
    "T3 = rev 3: port guy + crown straps + crown lid": "F_PR15_fineFM_over_port",
}
REV3_ROUTE = "over_port"
CG_TARGET = 185.0           # BL-029 acceptance: 15 in meat CG on the fine mesh (rev C limit 190)


def bl029_table() -> dict:
    S = _sim()
    rows = S.load_results()["rows"]
    gp = json.loads(CROWN_PATHS.read_text()) if CROWN_PATHS.exists() else {"rows": {}}

    def cg(key, case):
        c = rows.get(key, {}).get("cases", {}).get(case)
        if not c:
            return None
        g = c["loads_1g"]
        return {"converged": c["converged"], "rounding_mm": c["rounding_mm"], "cg_y": c["cg_y"],
                "cg_y_biased": c["cg_y_biased"], "closed_L": c["closed_L"],
                "crown_or_guy_1g_n": max(g.get("TG_R", 0.0), g.get("TG_L", 0.0)),
                "port_guy_1g_n": max(g.get("TP_R", 0.0), g.get("TP_L", 0.0)),
                "im3_1g_n": max(g.get("hook_im520_R", 0.0), g.get("hook_im520_L", 0.0))}
    cg15 = {k: {cn: cg(v, cn) for cn in ("fill", "meat")} for k, v in BL029_CG_RUNS.items()}
    rev3 = {}
    for t in (15, 19, 23):
        key = f"F_PR{t}_fineFM_{REV3_ROUTE}"
        r = rows.get(key, {})
        rev3[t] = {cn: cg(key, cn) for cn in ("fill", "meat")}
        rev3[t]["r28_deg"] = (min(r["r28"]["fill"]["worst_contact_deg"], r["r28"]["meat"]["worst_contact_deg"])
                              if "r28" in r else None)
        p = [gp["rows"].get(f"F_r1_PR{t}_fineFM_{REV3_ROUTE}:{cn}") for cn in ("fill", "meat")]
        p = [q for q in p if q]
        rev3[t]["lifter_gap_crown_mm"] = min((min(q["R"]["lifter_gap_mm"], q["L"]["lifter_gap_mm"]) for q in p), default=None)
        rev3[t]["lifter_gap_port_mm"] = min((min(q["R"].get("port_lifter_gap_mm", 1e9), q["L"].get("port_lifter_gap_mm", 1e9))
                                             for q in p), default=None)
        rev3[t]["crown_fwd_share"] = [q[s]["fwd_share_bag"] for q in p for s in ("R", "L")]
    m15 = (rev3[15].get("meat") or {}).get("cg_y")
    r28s = [rev3[t]["r28_deg"] for t in (15, 19, 23)]
    gaps = [g for t in (15, 19, 23) for g in (rev3[t]["lifter_gap_crown_mm"], rev3[t]["lifter_gap_port_mm"]) if g is not None]
    acc = {"cg15_meat_mm": m15, "cg15_ok": m15 is not None and m15 <= CG_TARGET,
           "r28_deg": r28s, "r28_ok": all(v is not None and v >= 31.0 for v in r28s),
           "lifter_gap_min_mm": min(gaps) if gaps else None, "lifter_ok": bool(gaps) and min(gaps) >= MIN_CLEAR_MM,
           "rev_c_ok": all((rev3[t].get(cn) or {}).get("cg_y_biased", 1e9) <= S.LIMIT[cn]
                           for t in (15, 19, 23) for cn in ("fill", "meat"))}
    return {"cg15": cg15, "rev3": rev3, "acceptance": acc, "lid": lid_geometry(), "paths": gp["rows"]}


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
    # Guys-off misuse (S11), 15 in meat. Three runs: coarse at the standard 6 mm rounding stalled (not converged);
    # coarse from 8 mm rounding converged at 2 mm on a different equilibrium (hooks / hinges ~2-3x, closed volume
    # +3 L); fine h 25 from 8 mm converged at 0 mm and agrees with the stalled coarse run. The fine run governs the
    # CG (finest mesh, zero rounding, and the worse CG); the IM3 basis takes the WORST converged run (conservative).
    goff_runs = {"coarse_sm6": case("F_PR15_goff", "meat"), "coarse_sm8": case("F_PR15_goff_sm8", "meat"),
                 "fine_sm8": case("F_PR15_fineFM_goff_sm8", "meat")}
    conv = {k: v for k, v in goff_runs.items() if v and v["converged"]}
    gon = case("F_PR15_fineFM", "meat") if goff_runs["fine_sm8"] else case("F_PR15", "meat")
    misuse = None
    if conv:
        gov = conv.get("fine_sm8") or max(conv.values(), key=lambda v: v["cg_y_biased"])
        im3w = max(conv.values(), key=lambda v: v["im3_1g_n"])
        misuse = {"runs": goff_runs, "guys_off": gov, "guys_on": gon, "limit_meat_mm": 190.0,
                  "exceeds_rev_c": gov["cg_y_biased"] > 190.0,
                  "over_limit_mm": round(gov["cg_y_biased"] - 190.0, 1),
                  "im3_worst_1g_n": im3w["im3_1g_n"], "im3_worst_factored_n": im3w["im3_factored_n"],
                  "bl004_basis_factored_n": 1702.0,       # attachment_diet.md section 5 (CORRIE 15 in guys-off, 567 N x 3.0)
                  "above_bl004_basis": im3w["im3_factored_n"] > 1702.0,
                  "governing_above_bl004_basis": gov["im3_factored_n"] > 1702.0}
    rev1 = {t: {cn: case(f"F_PR{t}", cn) for cn in ("fill", "meat")} for t in S.TORSOS}
    for t in S.TORSOS:            # a stalled coarse case is retried from 8 mm rounding (tag _sm8); use it if it converged
        for cn in ("fill", "meat"):
            alt = case(f"F_PR{t}_sm8", cn)
            if rev1[t][cn] and not rev1[t][cn]["converged"] and alt and alt["converged"]:
                rev1[t][cn] = dict(alt, retried_from_8mm=True)
    rev0 = {t: {cn: case(f"Fr0_PR{t}", cn) for cn in ("fill", "meat")} for t in S.TORSOS}
    finec = {f"{v}_{t}": {cn: case(f"{v}_PR{t}_fineFM", cn) for cn in ("fill", "meat")}
             for v in ("Fr0", "F") for t in S.TORSOS if f"{v}_PR{t}_fineFM" in rows}
    guys = [c["guy_1g_n"] for d in list(rev1.values()) + list(finec.values()) for c in d.values() if c]
    sw = S.SWEEP
    sweep = json.loads(sw.read_text()) if sw.exists() else None
    return {"r28": r28t, "acceptance": acc, "r28_allow_sweep": sweep, "guys_off": misuse, "rev1_coarse": rev1, "rev0_coarse": rev0, "fine": finec,
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
    fig, axs = plt.subplots(1, 3, figsize=(17.5, 5.8), dpi=90, gridspec_kw={"width_ratios": [1.15, 1, 0.95]})
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
    ax.axhline(30, color="#c0392b", ls="--", lw=1, label="> 30 deg required")
    ax.axhline(31, color="#c0392b", ls=":", lw=1, label="BL-022 target 31 deg")
    ax.set_xticks(range(len(S.TORSOS)), [f"{x} in" for x in S.TORSOS])
    ax.set_ylim(0, 42)
    ax.set_ylabel("first head contact, deg (worst of fill / meat)")
    ax.set_title(f"R-28 head clearance: rev 0 {REVS[0]['setback']:.0f} mm setback, guys x +/-{REVS[0]['guy_x']:.0f}; "
                 f"rev 1 {REVS[1]['setback']:.0f} mm, guys x +/-{REVS[1]['guy_x']:.0f}", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="upper center", ncol=3)
    ax.set_ylim(0, 50)
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
    ax = axs[2]
    sw = t.get("r28_allow_sweep")
    if sw:
        sty = {"Fr0_PR23": ("rev 0 coarse 23 in", "#b9c6d6", "-"), "F_PR23": ("rev 1 coarse 23 in", "#d9b48a", "-"),
               "Fr0_PR23_fineFM": ("rev 0 fine 23 in", "#6d8fb3", "--"), "F_PR15_fineFM": ("rev 1 fine 15 in", "#c49a6c", "--"),
               "F_PR19_fineFM": ("rev 1 fine 19 in", "#a87443", "--"), "F_PR23_fineFM": ("rev 1 fine 23 in", "#8a5a2b", "--")}
        for k, row in sw["rows"].items():
            lab, col, ls = sty.get(k, (k, "#555", ":"))
            xs = [float(a) for a in row]
            ys = [min(v["fill"]["deg"], v["meat"]["deg"]) for v in row.values()]
            ax.plot(xs, ys, ls, marker="o", ms=4, color=col, label=lab, lw=1.8)
        ax.axhline(30, color="#c0392b", ls="--", lw=1)
        ax.axhline(31, color="#c0392b", ls=":", lw=1)
        ax.axvline(sw["as_coded_allow_mm"], color="#777", lw=0.8)
        ax.text(sw["as_coded_allow_mm"] + 0.3, 24.3, "as coded 3 mm", fontsize=7.5, color="#555")
        ax.set_xlabel("wall allowance R28_ALLOW, mm (fabric + mesh scatter)")
        ax.set_ylabel("first head contact, deg (worst of fill / meat)")
        ax.set_ylim(24, 36)
        ax.set_title("Sensitivity (review B3): 34 deg = frame-only limit (bar + back pad, no bag)", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
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


def plot_bl028(path: Path, torso: int = 15) -> Path:
    """BL-028 diagram: the guy on the 15 in meat drape (plan and rear) as BL-022 modelled it (straight, through the
    bag), as it really lies (round the bag's side), and the rev 2 port routing; the 15 in meat CG of every routing
    run on the fine mesh; and the lifter gap on every drape."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S = _sim()
    rows = S.load_results()["rows"]
    gp = json.loads(GUY_PATHS.read_text()) if GUY_PATHS.exists() else {"rows": {}}
    X = drape(f"F_r1_PR{torso}_fineFM", "meat")
    Xp = drape(f"F_r1_PR{torso}_fineFM_{FIX_ROUTE}", "meat")
    fig = plt.figure(figsize=(16.0, 10.0), dpi=80)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.05, 1.0])
    C_STR, C_REAL, C_FIX, C_LIFT = "#c0392b", "#d98a1c", "#2e8b57", "#2b6cb0"
    if X is not None:
        m = fine_mesh(torso)
        Pr, surf, A, B = real_guy_path(X, torso, "R")
        tubes = crown_tubes(float(A[2]))
        la, lb = lifter_line(torso)
        band = np.abs(X[:, 2] - 0.5 * (A[2] + B[2])) < 45.0
        for k, (i, j, title) in enumerate(((0, 1, f"Plan, {torso} in, meat load (fine drape): right guy"),
                                           (0, 2, "Seen from behind (bag side), right half"))):
            ax = fig.add_subplot(gs[0, k])
            sel = band if k == 0 else (X[:, 0] > -20)
            ax.scatter(X[sel, i], X[sel, j], s=3, c="#b8b8b8", lw=0, label="bag cloth (fine sim nodes)")
            for a, b, r in tubes:
                if k == 0 and abs(a[2] - b[2]) > 1:
                    ax.add_patch(plt.Circle((a[0], a[1] + (b[1] - a[1]) * 0.98), r, color="#333"))
                else:
                    ax.plot([a[i], b[i]], [a[j], b[j]], color="#333", lw=2 * r * 0.55, solid_capstyle="butt")
            ax.plot([la[i], lb[i]], [la[j], lb[j]], color=C_LIFT, lw=7, alpha=0.85, label="lifter webbing (lug x 105)")
            ax.plot([A[i], B[i]], [A[j], B[j]], "--", color=C_STR, lw=2.2, label="BL-022 model: straight (through the bag)")
            ax.plot(Pr[:, i], Pr[:, j], color=C_REAL, lw=3.2, label=f"rev 1 real path: {path_metrics(Pr, surf, A, B, torso)['length_mm']:.0f} mm")
            if Xp is not None:
                spec = ROUTES[FIX_ROUTE](torso)["R"]
                hd = Xp[spec["b22"]] if spec.get("b22") is not None else Xp[m["b22"]["R"]]
                pts = np.vstack([A] + [Xp[v] for v in spec["vias"]] + [hd])
                ax.plot(pts[:, i], pts[:, j], color=C_FIX, lw=3.2, marker="o", ms=5,
                        label="rev 2: B-01 port, then inside")
            ax.plot(*A[[i, j]], "ks", ms=7)
            ax.annotate("bridle sleeve\nx 52 on the bar", A[[i, j]], xytext=(8, -26 if k == 0 else 10), textcoords="offset points", fontsize=9)
            ax.plot(*B[[i, j]], "k*", ms=13)
            ax.annotate("B-22", B[[i, j]], xytext=(6, 6), textcoords="offset points", fontsize=10)
            ax.set_aspect("equal")
            ax.set_xlabel("x, mm (outboard ->)" if i == 0 else "")
            ax.set_ylabel("y, mm (aft ->)" if j == 1 else "z, mm")
            ax.set_title(title, fontsize=11)
            ax.grid(alpha=0.2)
            if k == 0:
                ax.set_xlim(-30, 240)
                ax.set_ylim(-160, 330)
                ax.legend(fontsize=7.6, loc="lower right", framealpha=0.95)
            else:
                ax.set_xlim(-20, 240)
                ax.set_ylim(440, 800)
    # CG bars
    ax = fig.add_subplot(gs[0, 2])
    runs = [("straight model\n(BL-022, not real)", f"F_PR{torso}_fineFM", "#e4b5ae"), ("guys off", f"F_PR{torso}_fineFM_goff_sm8", "#999"),
            ("real wrap\n(rev 1 as built)", f"F_PR{torso}_fineFM_wrap", C_REAL), ("internal depth\ntie + wrap", f"F_PR{torso}_fineFM_tie_wrap", "#c9a227"),
            ("internal guy\nto IM3 eye", f"F_PR{torso}_fineFM_im3", "#8e6c8a"), ("port, tab\nz 695", f"F_PR{torso}_fineFM_port", "#7fbf9b"),
            ("port, tab\nz 745 x 149", f"F_PR{torso}_fineFM_port_hi", "#4fa77a"), ("port, tab\nz 745 x 100", f"F_PR{torso}_fineFM_port_hi_in", C_FIX)]
    xs, labs = [], []
    for n, (lab, key, col) in enumerate(runs):
        c = rows.get(key, {}).get("cases", {}).get("meat")
        if not c:
            continue
        v = c["cg_y"]
        ax.barh(len(xs), v, color=col, edgecolor="white")
        ax.text(v + 1, len(xs), f"{v:.1f}" + ("" if c["rounding_mm"] in (0, 0.0) else f" (+{S.bias(c['rounding_mm']):.0f} bias)"),
                va="center", fontsize=9)
        xs.append(v)
        labs.append(lab)
    ax.axvline(180, color="#c0392b", ls=":", lw=1.4, label="BL-028 acceptance 180")
    ax.axvline(190, color="#c0392b", ls="--", lw=1.2, label="rev C meat limit 190")
    ax.set_yticks(range(len(labs)), labs, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(150, 215)
    ax.set_xlabel("15 in meat load CG, mm aft (fine mesh h 25, 1 g; (+n) = rounding bias)")
    ax.set_title("What each guy routing does to the 15 in meat CG", fontsize=11)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    # forward pull and lifter gap
    ax = fig.add_subplot(gs[1, 0:2])
    keys = [k for k, r in gp["rows"].items() if r["case"] in ("fill", "meat", "sixday")]
    tag = {"straight": (0, "rev 1 real"), "wrap": (1, "rev 1 real\n(wrap sim)"), "port": (2, "rev 2 port")}
    keys.sort(key=lambda k: (tag[gp["rows"][k]["route"].split(" ")[0]][0], gp["rows"][k]["torso"], gp["rows"][k]["case"]))
    labels = [f"{gp['rows'][k]['torso']} in {gp['rows'][k]['case'].replace('sixday', '6-day*')}\n"
              f"{tag[gp['rows'][k]['route'].split(' ')[0]][1]}" for k in keys]
    gap = [min(gp["rows"][k]["R"]["lifter_gap_mm"], gp["rows"][k]["L"]["lifter_gap_mm"]) for k in keys]
    fs = [min(gp["rows"][k]["R"]["fwd_share_bag"], gp["rows"][k]["L"]["fwd_share_bag"]) for k in keys]
    st = [min(gp["rows"][k]["R"]["fwd_share_straight"], gp["rows"][k]["L"]["fwd_share_straight"]) for k in keys]
    xx = np.arange(len(keys))
    ax.bar(xx - 0.2, gap, 0.4, color=C_LIFT, label="guy to lifter webbing, edge gap, mm (worse side)")
    ax.axhline(MIN_CLEAR_MM, color=C_LIFT, ls=":", lw=1.2)
    ax.text(len(keys) - 0.5, MIN_CLEAR_MM + 1.5, f"{MIN_CLEAR_MM:.0f} mm required", color=C_LIFT, fontsize=8.5, ha="right")
    for x_, g_ in zip(xx, gap):
        ax.text(x_ - 0.2, g_ + 1, f"{g_:.0f}", ha="center", fontsize=8)
    ax.set_ylabel("gap, mm")
    ax.set_ylim(0, 80)
    ax2 = ax.twinx()
    ax2.plot(xx + 0.2, st, "_", color=C_STR, ms=18, mew=2.5, label="forward pull share: straight model")
    ax2.plot(xx + 0.2, fs, "o", color=C_REAL, ms=7, label="forward pull share: real path (worse side)")
    ax2.set_ylim(-1.05, 1.05)
    ax2.set_ylabel("share of guy tension pulling the bag forward")
    ax.set_xticks(xx, labels, fontsize=8)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8.2, loc="upper left", ncol=3)
    ax.set_title("Guy on every fine drape: always clear of the lifters; rev 1's real path pulls the bag sideways, not forward "
                 "(* 6-day drape not converged, geometry only)", fontsize=10.5)
    ax = fig.add_subplot(gs[1, 2])
    ax.axis("off")
    txt = BL028_NOTE_TEXT()
    ax.text(0.0, 1.0, txt, va="top", fontsize=9.2, family="DejaVu Sans", wrap=True)
    fig.suptitle("BL-028 CORRIE F guy routing: the straight guy was a model artefact; rev 2 takes the guy inside through a "
                 "B-01 port", fontsize=13)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_bl028_port(path: Path) -> Path:
    """Rev 2 construction sketch: the frame face B-01 seen from the frame side with the two B-27 port slits, where the
    crown bar meets it for each crown kit, and a section through one lapped port with the guy passing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Rectangle
    from huntkit.gendesign import crown_diet as CD
    c = make()
    fig, axs = plt.subplots(1, 2, figsize=(14.5, 8.0), dpi=80, gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axs[0]
    zs = np.linspace(BC.Z0, 745.0, 60)
    a = c.a(zs)
    ax.fill(np.r_[a, -a[::-1]], np.r_[zs, zs[::-1]], color="#e9e4da", ec="#666", lw=1.2, label="B-01 frame face (to z 745)")
    ax.axhline(631.0, color="#999", ls="--", lw=1)
    ax.text(-190, 636, "setback fold z 631 (30 mm aft above)", fontsize=8.5, color="#555")
    bands = {"S": "#7fb3d5", "M": "#76b7a0", "L": "#e0a96d"}
    bg = _bg()
    zt = {round(q["torso_in"], 1): q["crown_top_z"] for q in bg.crown_settings()}
    for k, (lo, hi) in CD.SIZES.items():
        z0, z1 = zt[round(lo, 1)], zt[round(hi, 1)]
        ax.add_patch(Rectangle((-115, z0), 230, z1 - z0, color=bands[k], alpha=0.28, lw=0))
        ax.text(118, 0.5 * (z0 + z1), f"{k} kit bar\n{lo:g}-{hi:g} in\nz {z0:.0f}-{z1:.0f}", fontsize=8.5, va="center")
    for sx in (1, -1):
        x = sx * REVS[2]["guy_x"]
        ax.plot([x, x], PORT_Z, color="#2e8b57", lw=4, solid_capstyle="butt")
        ax.add_patch(Rectangle((x - PORT_FACING_W / 2, PORT_Z[0] - PORT_END), PORT_FACING_W,
                               PORT_Z[1] - PORT_Z[0] + 2 * PORT_END, fill=False, ec="#2e8b57", ls=":", lw=1.2))
        ax.plot([x - 6, x + 6], [PORT_Z[0], PORT_Z[0]], color="k", lw=2.5)
        ax.plot([x - 6, x + 6], [PORT_Z[1], PORT_Z[1]], color="k", lw=2.5)
    ax.text(REVS[2]["guy_x"] + 30, PORT_Z[0] - 35, f"B-27 port slit x +/-{REVS[2]['guy_x']:.0f}, z {PORT_Z[0]:.0f}-{PORT_Z[1]:.0f}\n"
            f"(facing {PORT_FACING_W:.0f} mm, dotted; bartacks black)", fontsize=8.5, color="#2e8b57")
    for sx in (1, -1):
        ax.plot([sx * (LIFTER_X - LIFTER_W / 2), sx * (LIFTER_X + LIFTER_W / 2)], [810, 810], color="#2b6cb0", lw=6)
    ax.text(0, 822, "lifter lugs x +/-105 on the crown corners (unchanged)", ha="center", fontsize=8.5, color="#2b6cb0")
    ax.set_xlim(-230, 230)
    ax.set_ylim(450, 860)
    ax.set_aspect("equal")
    ax.set_xlabel("x, mm (seen from the frame side)")
    ax.set_ylabel("z, mm")
    ax.set_title("Rev 2: where the guy enters the bag (top of the frame face)", fontsize=11)
    ax.grid(alpha=0.2)
    ax = axs[1]                                                     # horizontal section through one port, at the bar
    ax.add_patch(plt.Circle((0, -20), 9, color="#333"))
    ax.text(14, -24, "crown top bar (OD 18)", fontsize=9)
    ax.plot([-60, 10], [12, 12], color="#8a7f6a", lw=3)              # B-01 inboard part, its edge at x +10
    ax.plot([-10, 10], [12.0 - 2.5, 12.0 - 2.5], color="#2e8b57", lw=3)  # facing sewn to it, the under-lap
    ax.plot([-10, 75], [3, 3], color="#8a7f6a", lw=3)                 # B-01 outboard part, its edge at x -10
    ax.text(-60, 17, "B-01, inboard side of the slit", fontsize=9)
    ax.text(14, -6, "B-01, outboard side", fontsize=9)
    ax.annotate("facing: 20 mm lap", (0, 9.5), xytext=(-62, -14), fontsize=9, color="#2e8b57",
                arrowprops={"arrowstyle": "-", "color": "#2e8b57"})
    gx = [0, -14, -14, 14, 14, 4]
    gy = [-11, -4, 6.5, 6.5, 18, 120]
    ax.plot(gx[:-1], gy[:-1], color="#d98a1c", lw=3)
    ax.add_patch(FancyArrowPatch((gx[-2], gy[-2]), (gx[-1], gy[-1]), arrowstyle="-|>", mutation_scale=18, color="#d98a1c", lw=3))
    ax.text(16, 62, "guy (25 mm, on edge)\nfrom the bridle tab,\nbetween the laps,\ninside to B-22\non the hinge band", fontsize=9,
            color="#a35f00")
    ax.text(-62, 112, "INSIDE THE BAG", fontsize=10, color="#555")
    ax.text(-62, -60, "FRAME / WEARER SIDE", fontsize=10, color="#555")
    ax.set_xlim(-70, 100)
    ax.set_ylim(-70, 130)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Section through one port (from above), not to scale across the lap", fontsize=11)
    fig.suptitle(f"BL-028 rev 2 (proposed): B-27 guy port, two per bag, {guy_port()['mass_g']:.1f} g; outside the bag the guy "
                 "stays in x 39.5-64.5 (lifter band from x 92.5)",
                 fontsize=12.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


# ---- BL-029 concepts: mass on the ledger basis, gloved steps, patent check (doc section 14.3)
GUY_ROWS = ("attachment system: top side guys x2", "attachment system: guy ladder locks", "attachment system: guy tail",
            "BL-010 A3: guy ladder locks", "BL-004 REC: guy bar loops", "attachment system: guy corner tabs B-22")
# ASSUMPTION GLOVE-T: gloved hand actions counted from the parts (one action = one buckle, lock, hook, zip or flip);
# settled by the FT glove test (timed, winter gloves) on the prototype
GLOVE_STEPS = {
    "rev 1 pouch": {"pouch pocket": 1, "open main bag": 7, "note": "4 pouch G-hooks, 2 roll buckles, unroll"},
    "T1 anchor lid": {"pouch pocket": 1, "open main bag": 6, "note": "2 front ladder locks, flip lid, 2 roll buckles, "
                      "unroll; lid off = top anchor off"},
    "T2 crown straps": {"pouch pocket": 1, "open main bag": 6, "note": "as T1; the straps stay on the bag when the lid "
                        "comes off"},
    "T3 rev 3": {"pouch pocket": 1, "open main bag": 6, "note": "as T2; the port guys are inside and never touched"},
}


def bl029_concepts() -> dict:
    """The three integrated top systems on the ledger basis (belt M, D2, as hunted unless stated), against rev 1:
    T1 = the lid IS the anchor (its 4 straps: rear to the B-25 tabs, front to the hinge band; guys deleted);
    T2 = the B-28 crown straps belong to the bag (base, they are the anchor), the B-29 lid rides in their channels;
    T3 = rev 3: rev 2's port guys (base) + B-28 / B-29 as hunted. CG from the stored 15 in fine runs."""
    with revision(1):
        r1 = parts()
    with revision(3):
        r3 = parts()
    guys = sum(r["g"] for r in r1 if r["name"].startswith(GUY_ROWS))
    pouch = sum(r["g"] for r in r1 if "top_pouch" in r["name"])
    lid, cs = crown_lid()["mass_g"], crown_straps()["mass_g"]

    def tot(rows, cfgs):
        return sum(r["g"] for r in rows if r["cfg"] in cfgs)
    b1, h1 = tot(r1, ("base",)), tot(r1, ("base", "as_hunted"))
    b3, h3 = tot(r3, ("base",)), tot(r3, ("base", "as_hunted"))
    t = bl029_table()["cg15"]
    cg = lambda k: (t.get(k, {}).get("meat") or {}).get("cg_y")   # noqa: E731
    return {
        "guys_rev1_g": round(guys, 1), "pouch_rev1_g": round(pouch, 1), "lid_g": lid, "crown_straps_g": cs,
        "T1": {"base_delta_g": round(-guys, 1), "as_hunted_delta_g": round(-guys - pouch + lid + cs, 1),
               "cg15_meat_mm": cg("T1/T2: crown straps over the roll, no guy"), "glove": GLOVE_STEPS["T1 anchor lid"],
               "lid_off_cg15_meat_mm": cg("guys off (misuse)")},
        "T2": {"base_delta_g": round(-guys + cs, 1), "as_hunted_delta_g": round(-guys - pouch + lid + cs, 1),
               "cg15_meat_mm": cg("T1/T2: crown straps over the roll, no guy"), "glove": GLOVE_STEPS["T2 crown straps"]},
        "T3": {"base_delta_g": round(b3 - b1, 1), "as_hunted_delta_g": round(h3 - h1, 1),
               "cg15_meat_mm": cg("T3 = rev 3: port guy + crown straps + crown lid"), "glove": GLOVE_STEPS["T3 rev 3"]},
        "rev1": {"glove": GLOVE_STEPS["rev 1 pouch"]},
        "patent": "all three: no strap from the bag top to the lifters or shoulder straps; lifters stay on the crown top "
                  "bar (x +/-105); no pop-up pole (US 10,952,523 claim 1); strap over the closure = expired US 4,213,549; "
                  "no frame-top pocket (US 8,579,171). Attorney review before tooling (DECISIONS 2026-11-01)",
    }


def plot_bl029(path: Path) -> Path:
    """BL-029 results: the three concepts in section on the 15 in meat drapes (crown strap and port guy), the 15 in meat
    CG of every guy / strap model, and rev 3 at 15 / 19 / 23 in."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tb = bl029_table()
    fig = plt.figure(figsize=(16, 8.6), dpi=80)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1])
    secs = [("T1 / T2: crown straps over the roll\n(no guy; T1 = the lid's own straps)", "F_r1_PR15_fineFM_over", False),
            ("T3 = rev 3: crown straps + lid\n+ rev 2 port guys inside", "F_r1_PR15_fineFM_over_port", True)]
    for k, (title, run, port) in enumerate(secs):
        ax = fig.add_subplot(gs[0, k])
        X = drape(run, "meat")
        if X is None:
            ax.text(0.5, 0.5, f"{run} not on disk", ha="center", transform=ax.transAxes)
            continue
        m = fine_mesh(15)
        s = np.abs(X[:, 0] - CROWN_X) < 14
        ax.scatter(X[s, 1], X[s, 2], s=3, c="#9a9a8a")
        S = _sim()
        spec = S.load_results()["rows"][run.replace("F_r1_", "F_")].get("route", {}).get("R", {})
        P, surf, A, B, kk = crown_path(X, 15, "R", front_node=spec.get("b22"))
        ax.plot(P[:, 1], P[:, 2], color="#3a3a3a", lw=3, label="B-28 crown strap (taut path)")
        if port:
            Q = X[_route_port(15)["R"]["vias"][0]]
            Bq = X[m["b22"]["R"]]
            ax.plot([A[1], Q[1], Bq[1]], [A[2], Q[2], Bq[2]], color="#2e8b57", lw=3, label="B-27 port guy (inside)")
        ax.plot(A[1], A[2], "ko", ms=9)
        ax.text(A[1] - 8, A[2] - 28, "bar, S kit\nz 601", fontsize=8.5, ha="right")
        cg = (tb["cg15"]["T3 = rev 3: port guy + crown straps + crown lid" if port else
                          "T1/T2: crown straps over the roll, no guy"]["meat"] or {}).get("cg_y")
        ax.set_title(f"{title}\n15 in meat CG {cg:.1f} mm ({'pass' if cg <= CG_TARGET else 'FAIL'})", fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(-60, 460)
        ax.set_ylim(300, 960)
        ax.grid(alpha=0.25)
        ax.set_xlabel("y, mm (aft ->)")
        ax.legend(fontsize=8, loc="lower right")
    ax = fig.add_subplot(gs[0, 2])
    ks = list(tb["cg15"].keys())
    vals = [(tb["cg15"][k]["meat"] or {}).get("cg_y") for k in ks]
    cols = ["#2e8b57" if (v or 999) <= CG_TARGET else ("#d98a1c" if (v or 999) <= 190 else "#c0392b") for v in vals]
    ax.barh(range(len(ks)), [v or 0 for v in vals], color=cols)
    for i, v in enumerate(vals):
        ax.text((v or 0) + 1, i, f"{v:.1f}" if v else "n/a", va="center", fontsize=9)
    ax.axvline(CG_TARGET, color="#2e8b57", ls="--", lw=1.2)
    ax.axvline(190.0, color="#c0392b", ls="--", lw=1.2)
    ax.text(CG_TARGET - 1, len(ks) - 0.4, "target 185", ha="right", fontsize=8.5, color="#2e8b57")
    ax.text(191, len(ks) - 0.4, "rev C 190", fontsize=8.5, color="#c0392b")
    ax.set_yticks(range(len(ks)))
    ax.set_yticklabels([k.replace(" (", "\n(") for k in ks], fontsize=8)
    ax.set_xlim(160, 210)
    ax.set_title("15 in meat CG y, fine mesh (mm from the frame)", fontsize=10)
    ax = fig.add_subplot(gs[1, :])
    ax.axis("off")
    r3 = tb["rev3"]
    con = bl029_concepts()
    lines = ["Rev 3 (T3), fine mesh h 25, real strap paths (eyelets on the cloth):",
             "torso | fill CG (+bias) | meat CG (+bias) | R-28 | crown strap / port guy N at 1 g (max) | IM3 N | lifter gap crown / port",
             ]
    for t in (15, 19, 23):
        f, mm = r3[t]["fill"], r3[t]["meat"]
        lines.append(f"{t} in | {f['cg_y']:.1f} ({f['cg_y_biased']:.1f}) | {mm['cg_y']:.1f} ({mm['cg_y_biased']:.1f}) | "
                     f"{r3[t]['r28_deg']:.0f} deg | {max(f['crown_or_guy_1g_n'], mm['crown_or_guy_1g_n']):.0f} / "
                     f"{max(f['port_guy_1g_n'], mm['port_guy_1g_n']):.0f} | {max(f['im3_1g_n'], mm['im3_1g_n']):.0f} | "
                     f"{r3[t]['lifter_gap_crown_mm']:.0f} / {r3[t]['lifter_gap_port_mm']:.0f} mm")
    lines += ["",
              f"Mass vs rev 1 (belt M, D2):  T1 base {con['T1']['base_delta_g']:+.1f} g, as hunted {con['T1']['as_hunted_delta_g']:+.1f} g"
              f"  |  T2 base {con['T2']['base_delta_g']:+.1f}, as hunted {con['T2']['as_hunted_delta_g']:+.1f}"
              f"  |  T3 base {con['T3']['base_delta_g']:+.1f}, as hunted {con['T3']['as_hunted_delta_g']:+.1f} g",
              f"B-29 lid {tb['lid']['volume_L']:.1f} L ({tb['lid']['volume_cu_in']:.0f} cu in), {con['lid_g']:.1f} g; "
              f"B-28 crown straps {con['crown_straps_g']:.1f} g the pair; top pouch it replaces {con['pouch_rev1_g']:.1f} g",
              "Why T1 / T2 fail: an outside strap pulls the bag only along its first run from the bar. At the S kit the bar",
              "(z 601) is 130+ mm below the bag top, so that run climbs the frame face: mostly down, not forward."]
    ax.text(0.0, 1.0, "\n".join(lines), va="top", family="monospace", fontsize=9.6, transform=ax.transAxes)
    fig.suptitle("BL-029 top anchor and lid: only the inside (port) guy holds the 15 in meat load; the crown lid rides on top",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_bl029_concepts(path: Path) -> Path:
    """Concept sketches (side and rear schematics, to scale on the 6-day render geometry's lid): T1 anchor lid, T2 crown
    straps with a captured lid, T3 = rev 3 (T2's look + the port guys inside)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    c = make()
    fig, axs = plt.subplots(1, 3, figsize=(16, 7.4), dpi=80)
    zs = np.linspace(BC.Z0, c.z_c, 80)
    yf, ya = c.frame_y(zs), c.y_front(zs)
    L = LID
    con = bl029_concepts()
    for ax, key, title in zip(axs, ("T1", "T2", "T3"),
                              ("T1 anchor lid: the lid's own 4 straps\nare the top anchor (Exo-style float)",
                               "T2 crown straps on the bag,\nlid captured in two channels",
                               "T3 = rev 3: T2's look + rev 2's\nport guys inside (recommended)")):
        ax.fill(np.r_[yf, ya[::-1]], np.r_[zs, zs[::-1]], color="#b9c4a4", ec="#555", lw=1.2)
        ax.add_patch(FancyBboxPatch((c.frame_y([c.z_c])[0] + 2, c.z_c), 160, 45, boxstyle="round,pad=0,rounding_size=20",
                                    color="#a7b38f", ec="#555"))                          # the closed roll
        y0 = float(c.frame_y([c.z_c])[0]) - 15
        ax.add_patch(FancyBboxPatch((y0, c.z_c + 40), L["D"], L["wall"] + L["dome"], boxstyle="round,pad=0,rounding_size=35",
                                    color="#8f9d74", ec="#333", lw=1.4))                  # the lid
        ax.add_patch(FancyBboxPatch((y0 + L["D"] - 28, c.z_c + 40), 28, L["wall"], boxstyle="round,pad=0,rounding_size=8",
                                    color="#c8b48a", ec="#333", lw=0.8))                  # camo corner cap
        zb = 601.0
        ax.plot([-5, 25], [zb, zb], color="k", lw=7, solid_capstyle="round")
        ax.text(-12, zb - 30, "bar (S kit)", fontsize=8.5, ha="right")
        top = c.z_c + 40 + L["wall"] + L["dome"]
        ys = [20, 6, y0 + 20, y0 + L["D"] - 25, ya[-1] + 4, ya[-1] + 4]
        zz = [zb, c.z_c - 40, top + 3, top + 3, c.z_c + 30, 700]
        col = "#3a3a3a" if key != "T1" else "#6b4f2a"
        ax.plot(ys, zz, color=col, lw=3.2)
        ax.plot(ya[-1] + 4, 700, "s", color="#222", ms=8)
        if key == "T1":
            ax.text(250, 905, "straps sewn to the lid:\nlid off = anchor off", fontsize=9, color="#6b4f2a")
        else:
            ax.text(250, 905, "straps sewn to the bag:\nlid slides off them", fontsize=9, color="#333")
        if key == "T3":
            ax.plot([20, 32, ya[-1] - 40], [zb, zb + 2, 695], color="#2e8b57", lw=3)
            ax.text(70, 610, "B-27 port guy\n(inside)", color="#2e8b57", fontsize=9)
        d = con[key]
        cgv = d["cg15_meat_mm"]
        ax.set_title(f"{title}\n15 in meat CG {cgv:.1f} mm ({'pass' if cgv <= CG_TARGET else 'FAIL rev C'}); "
                     f"as hunted {d['as_hunted_delta_g']:+.0f} g vs rev 1", fontsize=10)
        ax.text(-40, 330, f"gloved steps to open the main bag: {d['glove']['open main bag']}\n({d['glove']['note']})",
                fontsize=8.3)
        ax.set_xlim(-80, 420)
        ax.set_ylim(300, 960)
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("BL-029 concepts (side schematics, to scale): one strap line from the bar, over the lid, to the bag",
                 fontsize=13)
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
    ap.add_argument("--bl022", action="store_true", help="BL-022 rev 1 summary + screenshot 20261112_BL022_1.png")
    ap.add_argument("--bl028", action="store_true", help="BL-028 real guy paths (writes corrie_f_guy_paths.json), "
                                                         "table + screenshot 20261112_BL028_1.png")
    ap.add_argument("--bl029", action="store_true", help="BL-029 crown-strap paths (writes corrie_f_crown_paths.json), "
                                                         "concepts, table + screenshots 20261112_BL029_5/6.png")
    a = ap.parse_args(argv)
    if a.bl029:
        SCREENS.mkdir(parents=True, exist_ok=True)
        bl029_paths()
        print(json.dumps({k: v for k, v in bl029_table().items() if k != "paths"}, indent=1, default=_j))
        print(json.dumps(bl029_concepts(), indent=1, default=_j))
        print(plot_bl029_concepts(SCREENS / "20261112_BL029_5.png"))
        print(plot_bl029(SCREENS / "20261112_BL029_6.png"))
        return
    if a.bl028:
        SCREENS.mkdir(parents=True, exist_ok=True)
        bl028_paths()
        print(json.dumps({k: v for k, v in bl028_table().items() if k != "paths"}, indent=1, default=_j))
        print(plot_bl028(SCREENS / "20261112_BL028_1.png"))
        print(plot_bl028_port(SCREENS / "20261112_BL028_2.png"))
        return
    if a.bl022:
        SCREENS.mkdir(parents=True, exist_ok=True)
        print(json.dumps(bl022_summary(), indent=1, default=_j))
        print(plot_bl022(SCREENS / "20261112_BL022_1.png"))
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
