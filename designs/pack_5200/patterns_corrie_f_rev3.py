"""BL-032 part A: CORRIE F rev 3 production patterns (pattern-maker, 2026-11-13).

    python designs/pack_5200/patterns_corrie_f_rev3.py            # build + checks (no files)
    python designs/pack_5200/patterns_corrie_f_rev3_export.py     # build, check, export the release

Every sewn piece of the adopted bag (``huntkit.mass.ledger.ADOPTED_BAG``: CORRIE F rev 3, door D2), drawn from the
pack-designer's geometry and never re-shaped here:

* shell S15 with door D2, collar and roll top: ``concepts/corrie_f.build(make(), "D2", fabrics)`` (the pieces, their
  seam lines and allowances are taken as built; this module adds the notches, drill holes, cut-outs, placements and
  the real seam pairs);
* fairlead swells B-13x and their windows in B-01 (``bag_concepts.boxed_swell``, windows from ``patterns_v31.SWELLS``),
  B-12 strap-port patches, B-17 / B-18 / B-22 Hypalon (``huntkit.gendesign.attach_system.drawing_pieces``; B-17 at
  BL-004's 90 x 70), B-11 lash tabs (panels.yaml);
* B-27 port slits in B-01 and their facings (``corrie_f.guy_port``), the B-22 anchors inside the hinge band and the
  B-28 front tab on it;
* hip-reach pockets FP-L / FP-R (``bag_comp/A/evolve.FP``, moved to z 150-380 by ``corrie_f.hip_reach_pockets``),
  IMP-2 / IMP-4 / IMP-8 (``corrie.bag_pockets``), F-02 fly pocket (panels.yaml);
* B-29 crown lid (``corrie_f.LID``): crown drafted by radial development of the drawn dome with four corner darts,
  base, zipped wall ring, camo caps, strap channels;
* the BL-031 straps and keepers and the meat-trip extenders as hot-knife webbing pieces (``strap_tails``,
  ``corrie_f.crown_kit_straps``), B-25 / B-26 / guys / loops as webbing pieces;
* add-ons with a source pattern: scope pod (``lean.fell`` A1), meat liner (``D.cache`` SWAP slab).

Two fabric maps on one geometry (DECISIONS 2026-11-12, orchestrator): ``primary`` = today's fabrics
(``corrie_f.fab(role, "today")``), ``alternate`` = the team B set (``fab(role, "B")``), which is what the ledger
books. Units mm, g. Every number traces to a source module, a record, or an ``ASSUMPTION`` below.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "designs" / "pack_5200"
CONC = HERE / "concepts"
for _p in (str(ROOT), str(HERE), str(CONC), str(HERE / "bag_comp")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bag_concepts as BC  # noqa: E402
import corrie as CO  # noqa: E402
import corrie_f as F  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import Piece, Seam, check_seams, rect_panel  # noqa: E402
from huntkit.patterns import curves as CV  # noqa: E402
from huntkit.patterns.piece import EdgeRef  # noqa: E402

REV, DOOR = 3, "D2"
FABRIC_SETS = {"primary": "today", "alternate": "B"}     # DECISIONS 2026-11-12 (orchestrator, BL-032)
SA_BODY, SA_ZIP, SA_FLAT = BC.SA_BODY, BC.SA_ZIP, BC.SA_FLAT  # 12 bound body seams / 10 zip / 8 flat-work turn
SA_LASER = 0.0
NOTCH_PITCH = 50.0         # BUILD_PLAN.md: match notches every 50 mm
KNIFE = "CW from the grain-arrow head; cut windows and slits first"
CROWN_KITS = ("S", "M", "L")
KIT = F.CROWN_KIT_DEFAULT  # "M": the ledger's crown kit

# fairlead swells: (crest z, lower, upper) = patterns_v31.SWELLS (hinge pushed up 5 mm over the floor seam; IM3 tip
# 8 mm under the z 560 crease); window 50 wide (patterns_v31.SWELL_W) centred on the stay x (bag_concepts.STAY_X)
# BL-033 DECISION H-1 (corrie_f.SWELL_WINDOWS): no hinge window, it lay over the B-18 doubler (the hinge load path)
SWELLS = F.SWELL_WINDOWS
SWELL_W = F.SWELL_W
STAY_X = BC.STAY_X
B12 = (40.0, 60.0, 12.0, 45.0)   # panels.yaml B-12 40 x 60; slot 12 x 45 (ledger row "slot 45 x 12 mm")
B17 = (90.0, 70.0)               # BL-004 REC "B-17 trimmed 110 -> 70 mm tall" (corrie_f_body.md section 9.7: 90 x 70)
B17_Z = 420.0                    # ASSUMPTION B17-Z: the trimmed 70 mm tab sits z 385-455, its top 7 mm under the IM3
#                                  swell window (z 462): the 110 mm tab centred z 450 overlapped that window by 43 mm.
#                                  T3 box-X at the tab centre, z 420; settled by the PT-2 swatch pull
B22_XZ = F.B22_DRAWN              # corrie_body.md section 4 B-02h row / guy_geometry: B-22 at x +/-149, z 695
B22_WH = (F.B22_W, 60.0)          # attach_system.drawing_pieces B-22 50 x 60
B22_EDGE_CLEAR = F.B22_EDGE_CLEAR  # ASSUMPTION (corrie_f): tab edge >= 6 mm inside the hinge band | blade seam line
B28_TAB_Z = F.CROWN_FRONT_Z      # 700: front crown-strap tab on the hinge band at x +/-CROWN_X
PORT_LAP_IN = 30.0               # ASSUMPTION: the 50 mm facing sits 30 mm inboard / 20 mm outboard of the slit (the
#                                  20 mm lap of corrie_f.guy_port); settled by the port mock-up (hose test)
HARD_Z = F.HARD_Z                # scope-pod hard points z 420 / 640 (left corner seams)
POLE_TAB_Z = 640.0               # corrie_f.hip_reach_pockets E-5: grip tab in the right B-01 | gusset seam at z 640
FP_Z = (150.0, 380.0)            # corrie_f.hip_reach_pockets: z 150-380 on the gusset's lower front (aft) corner
IMP8_Z = (35.0, 150.0)           # corrie_f.fixed_pockets IMP-8: right gusset foot z 35-150
HOSE_Z_BL041 = CO.HYDRO["port_z"]  # 700: IMP-2 hose ports in the gussets, 20 mm aft of the frame seam (to BL-041)
HOSE_SLOT = (12.0, 40.0)          # corrie.bag_pockets hose port binding 'slot 12 x 40'
#                                  BL-043 DECISION HOSE-LOW: HOSE_Z (below w3_sweep) replaces z 700
IMP2_TAB = (0.0, 985.0)          # IMP-2 hang tab on B-06f at x 0, z 985 (lean.fell IMP-2L attach note)
IMP2_KEEP = (100.0, 560.0)       # IMP-2 bottom keeper tabs on B-01 at x +/-100, z 560
IMP4_Z = (350.0, 630.0)          # corrie.bag_pockets IMP-4 "B-02door inside face, z 350-630"
ELASTIC = "elastic_25mm"     # record (BL-034 part B, 15 g/m)
# ---- BL-034 placements (pack-designer)
B28_BOX = (21.0, 20.0)           # DECISION B28-FACE (BL-034): the B-28 front lock tab is box-X'd on the OUTSIDE of the
#                                  hinge band: the crown strap's taut path (corrie_f.crown_path, T9) comes over the lid and
#                                  down the band's aft (outer) face to the lock at z 700, so an inside tab would pull the
#                                  strap through the band. Box = the B-28t box (25 mm webbing less 2 mm a side, x the 20 mm
#                                  of the 2 x 30 fold), sewn through tab + band in one pass; a 25 x 25 box would run off a
#                                  25 mm tab. Centre 15 mm under the lock bar (mid of the 30 mm doubled tab).
B28_BAR_DROP = F.CROWN_TAB / 4.0  # 15 mm
LLT_BOX = (21.0, 25.0)           # BL-035: the guy ladder-lock tab box-X, sewn through LLT + B-22 + B-02h in one pass, so the
#                                  LLT piece and the B-02h mark are one box (25 mm webbing less 2 mm a side x 25 mm); the
#                                  B-02h mark was drawn 25 x 25 (would run off the 25 mm tab)
B11_W, B11_H = 30.0, 50.0        # panels.yaml B-11
B11_BOW_Z = (470.0, 560.0)       # ASSUMPTION B11-PLACE: bow riser tabs, stacked on the riser line 40 mm forward of the aft
B11_BOW_IN = 40.0                #   corner seam (the cam sits in IMP-8 at the right gusset's aft foot, z 35-150; a 30-33 in
#                                  ATA bow puts the grip ~400 mm above the cam), above FP (top z 380) and W2, below the B-26
#                                  cord (z 600). Same marks on the left gusset = antler / cape lash points (gusset is one
#                                  pattern). Settled by the archery loadout fit (bow in IMP-8, two BRL loops round the riser)
B11_MUZ_Z = 650.0                # ASSUMPTION B11-PLACE: muzzle keeper tabs side by side at z 650 (a keeper loop runs
B11_MUZ_X = (60.0, 130.0)        #   between them round the barrel), BL-040: 60 / 130 mm aft of the frame seam; BL-041
#                                  RT-FWD moves them aft of the roll-clip path (rt_layout mk_dx, 111 / 171): clear of the B-26 cord
#                                  (z 600), the IMP-2 hose slot (frame seam + 20-32 mm, z 680-720), W3 (z ~690-715) and the
#                                  hard-point loops in the seams (z 640). Settled by the rifle fit (butt boot on the belt wing,
#                                  both sides)
F02_OUT = "OUTSIDE"              # F02-PLACE (BL-034): F-02 centred on the outside of B-05 across its width; fore-aft on
#                                  the floor depth (ASSUMPTION F02-CENTRE, as the US channel stations), zip on the aft edge
KEEPER_CUT = F.TAIL_KEEPER_CUT_MM  # ASSUMPTION (corrie_f): 25 mm elastic keeper cut 90 mm, lapped 15 mm into a 75 mm loop
#                                  (fits 25 mm webbing + a 21 mm rolled tail); settled by weighing 10 cut keepers

# ---- BL-040 B-1 DECISION HE-ONE (pack-designer): ONE hinge-eye construction for the piece, the op, the load table
# and the PT-3 specimen. HE = 38 mm webbing folded in half at the eye fold; BOTH raw ends reach the B-01 cut edge so the
# floor seam (B-01 | B-05, 12 mm) catches both plies; box-X through HE (2 plies) + B-01 + B-18, its lower edge
# HE_BOX_GAP above the floor seam line. The free loop between the box top and the fold is the eye. Neck
# (bag_attachment.md HE row: 18 mm fairlead throat): each long edge folded 10 mm in over the loop zone, held by one BT-M
# bartack per leg, sewn on the FLAT strip before the fold. z below = height on B-01 above the floor seam line
# (BC.Z0 = 35 mm in frame z).
# ---- BL-041 X-2 DECISION HE-PIN (pack-designer, 2026-11-13): the eye goes back on the pin. BL-040 put a 34 x 34 box
# at +4..+38 and the eye at +38..+63, i.e. 13-38 mm ABOVE the z 60 pin (+25), relying on the eye folding down
# (ASSUMPTION HE-REACH, withdrawn): a 180 deg peel at the box top with the cheeks on the 38 mm box stack. Now the eye
# points UP with the box BELOW the fairlead cheeks: box top = cheek bottom (pin z - bag_attach.HALF_Z = +16) less
# HE_CHEEK_CLEAR, so only the 18 mm neck enters the 18 mm throat, and the eye length is solved (he_geometry) so the
# loaded pin sits at frame z 60 (bag_attachment.md:118 'eye top at z 60'; the bag floor stays at z 35 as every sim
# assumes). Box 34 x 10 (38 mm webbing less 2 mm a side x what fits under the cheeks). BL-044 replaced the section
# model (DECISION HE-ENV below): the 'in line, no peel' claim did not hold (review M-3).
HE_W = 38.0
HE_BOX_GAP = 4.0                  # ASSUMPTION HE-GAP: box 4 mm above the floor seam line (clear of the SSa row; the SSa2
#                                   allowances are turned DOWN onto B-05 at the hinge, op 4.15); settled by the PT-3 swatch
# ---- BL-044 DECISION HE-ENV (pack-designer, 2026-11-13; review 2026-11-13 Z-1 / M-3 / m-1): the hinge eye is solved
# against the BL-042 hinge fairlead, ``bag_attach.HINGE_EYE_ENVELOPE`` (pin 10.1 mm above the stay surface, 5.5 mm under
# the pin, 20 mm throat, cheek tips 17.7 mm proud, cheeks +/-9 mm about the pin), NOT the module constants HOLE_PROUD /
# THROAT (those stay the IM / US fairleads). The wrap is the real folded neck: the neck folds lie INSIDE the loop
# (op 4.05 step 3), so the main ply wraps the pin over HE_NF fold plies: 2 in the middle 2 mm where the two 10 mm folds
# overlap (the main ply rides that ridge), 1 elsewhere. Box top HE_CHEEK_CLEAR under the cheeks at the design pin, and
# never less than HE_CHEEK_MIN anywhere in the HE-FIT band (m-1).
HE_CHEEK_CLEAR = 5.0              # BL-044 DECISION HE-ENV: box top 5 mm under the cheeks' lower edge at the design pin
#                                   (+25): box top +11, box-X 34 x 7. Was 2 mm (box top +14), which left 0 mm at a pin of
#                                   23 mm and contradicted the HE-FIT band (review m-1)
HE_CHEEK_MIN = 2.0                # ASSUMPTION HE-CHEEK: the box top must stay >= 2 mm under the cheeks' lower edge (cheek
#                                   fillet, print tolerance) at every loaded pin height HE-FIT may pass; settled by HE-FIT
HE_PIN_HI = 4.0                   # ASSUMPTION HE-PIN-HI: a loaded pin up to 4 mm above the design (+25) is accepted: the
#                                   bag floor hangs at most 4 mm below the z 35 every sim assumes; settled by QC-20 / T9
HE_T = F.WEB38_T                  # BL-048 M-B: the 38 mm webbing record's purchase-spec ply thickness (1.5 nominal,
#                                   poly_webbing_38mm thickness_mm; was ASSUMPTION HE-T); ONE value for every 38 mm part
#                                   (HE, IME, T3, B-24, B-25: corrie_f.B25_T reads the same record). The caliper gate is
#                                   at the PURCHASE (sample before the roll), HE-FIT step 1 re-checks the roll in hand
HE_T_RANGE = (F.WEB38_T_RANGE[0], F.WEB38_T_RANGE[1])         # BL-044: the bracket the eye is solved over. The upper end is a GATE, not a bracket:
#                                   3 plies of 1.6 mm (4.8) leave 0.7 mm under the pin (gap 5.5, review Z-1 rule: wrap
#                                   <= gap - 0.5); a roll thicker than 1.6 mm is rejected at the caliper (HE-FIT step 1)
HE_NF_DESIGN = 2                  # fold plies under the main ply in the wrap (the 2 mm ridge, see above); 1 = the flanks
HE_NECK_EDGE = 10.0               # each long edge folded 10 mm in: 38 -> 18 mm neck (bag_attach.HE_FOLD_EDGE)
HE_TACK_ABOVE_BOX = 4.0           # neck bartack 4 mm above the box top, one per leg (on the straight leg, under the cheeks)
B18_W = 90.0
B18_BELOW = SA_BODY               # B-1 fix: B-18 runs 12 mm below the floor seam line into the allowance (caught by it)
B18_TOP = 50.0                    # BL-041: kept at +50 (90 x 62, the BL-040 piece): B-18 now also backs the cleat
#                                   cheeks (+16..+34 above the seam line, hinge_standoff) with its 9 mm row 7 mm above them
B18_H = B18_BELOW + B18_TOP       # 62 mm


def he_envelope() -> dict:
    """The BL-042 hinge fairlead the eye must meet (``bag_attach.HINGE_EYE_ENVELOPE``), in the HE section frame:
    y from the stay centre towards the bag, z above the floor seam line (frame z - BC.Z0)."""
    from huntkit.gendesign import bag_attach as BA
    E = dict(BA.HINGE_EYE_ENVELOPE)
    r = E["stay_r_mm_at_z60"]
    E.update(pin_z=E["station_z_mm"] - BC.Z0, pin_y=E["pin_centre_from_stay_centre_mm"],
             floor_y=round(r + E["throat_floor_above_stay_surface_mm"], 4),
             tip_y=round(r + E["cheek_tip_above_stay_surface_mm"], 4), panel_offset=BA.PANEL_OFFSET)
    return E


def _tangent(P, C, r, side):
    """Tangent point from P to the circle (C, r): side +1 = the one counter-clockwise of CP (y right, z up)."""
    dy, dz = P[0] - C[0], P[1] - C[1]
    d = math.hypot(dy, dz)
    if d <= r:
        raise ValueError("leg start inside the wrap")
    th = math.atan2(dz, dy) + side * math.acos(r / d)
    return th, (C[0] + r * math.cos(th), C[1] + r * math.sin(th))


def he_loop(face_y: float, box_top: float, pin_z: float, t: float = HE_T, nf: int = HE_NF_DESIGN) -> dict:
    """The loaded eye in section (BL-044). Main-ply centrelines: leg A (against B-01) leaves the box top at
    face_y - t/2 and passes the BAG side of the pin; leg B (outside it) leaves at face_y - 3t/2 and passes the STAY
    side, between the pin and the throat floor; they wrap the pin over ``nf`` fold plies (centreline radius
    PIN_D/2 + nf t + t/2). Returns the loop length L (box top -> round the pin -> box top; the flat eye is L/2), the
    tangent points, and each leg's angle from the panel line (deg, + = towards the bag)."""
    E = he_envelope()
    r = E["pin_d_mm"] / 2 + nf * t + t / 2
    A, B, C = (face_y - t / 2, box_top), (face_y - 1.5 * t, box_top), (E["pin_y"], pin_z)
    thA, tA = _tangent(A, C, r, +1)
    thB, tB = _tangent(B, C, r, -1)
    while thB < thA:
        thB += 2 * math.pi
    L = math.dist(A, tA) + r * (thB - thA) + math.dist(B, tB)
    aA = math.degrees(math.atan2(tA[0] - A[0], tA[1] - A[1]))
    aB = math.degrees(math.atan2(tB[0] - B[0], tB[1] - B[1]))
    return {"L": L, "A": A, "B": B, "C": C, "r_c": r, "tA": tA, "tB": tB, "thA": thA, "thB": thB,
            "leg_A_deg": aA, "leg_B_deg": aB, "resultant_deg": 0.5 * (aA + aB), "half_included_deg": 0.5 * (aA - aB)}


def he_inline_face(box_top: float, pin_z: float, t: float = HE_T, nf: int = HE_NF_DESIGN) -> float:
    """The B-01 face y (at the box) where the two legs' resultant lies along the panel: the box is IN LINE with the
    pull. A fabric panel goes there under load (it cannot hold a cross load), unless something stiff holds it off."""
    lo, hi = 12.0, 34.0
    for _ in range(70):
        m = 0.5 * (lo + hi)
        if he_loop(m, box_top, pin_z, t, nf)["resultant_deg"] > 0:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def he_geometry(face_y: float | None = None, t: float = HE_T, nf: int = HE_NF_DESIGN) -> dict:
    """BL-044 DECISION HE-ENV (replaces BL-041 HE-PIN's section model). The hinge-eye geometry from the BL-042
    fairlead envelope: pin, floor, throat, cheeks, cheek tips (``he_envelope``), the box below the cheeks, and the eye
    loop (``he_loop``) with the real folded-neck wrap. B-01 at the box (the stand-off): ``face_y`` None = the in-line
    face (design: the loaded box aligns with the legs' resultant); the bracket ``faces_y`` runs from bag_attach
    PANEL_OFFSET (20) to the cheek-tip plane (B-01 held off by the cheeks all the way down to the box)."""
    E = he_envelope()
    pin_z = E["pin_z"]                                       # +25 above the floor seam line (frame z 60)
    cheek_lo = pin_z - E["cheek_half_z_mm"]                  # +16
    box_top = cheek_lo - HE_CHEEK_CLEAR                      # +11
    box_h = box_top - HE_BOX_GAP                             # 7
    fi = he_inline_face(box_top, pin_z, t, nf)
    faces = (E["panel_offset"], E["tip_y"])
    fy = fi if face_y is None else face_y

    def loop_len(zc, y0=fy, t_=t, nf_=nf):
        return he_loop(y0, box_top, zc, t_, nf_)["L"]

    lp = he_loop(fy, box_top, pin_z, t, nf)
    return {"pin_z": pin_z, "cheek_lo": cheek_lo, "cheek_hi": pin_z + E["cheek_half_z_mm"], "box_top": box_top,
            "box_h": box_h, "box_gap": HE_BOX_GAP, "pin_y": E["pin_y"], "face_y": fy, "face_inline": fi,
            "faces_y": faces, "t": t, "nf": nf, "r_c": lp["r_c"], "eye_flat": lp["L"] / 2.0, "loop": lp,
            "throat": E["throat_mm"], "pin_d": E["pin_d_mm"], "floor_y": E["floor_y"], "tip_y": E["tip_y"],
            "stay_r": E["stay_r_mm_at_z60"], "gap_under_pin": E["gap_under_pin_mm"], "env": E, "loop_len": loop_len}


def he_pin_z(eye_flat: float, face_y: float | None = None, t: float = HE_T, nf: int = HE_NF_DESIGN) -> float:
    """Loaded pin-centre height above the floor seam line for an eye of ``eye_flat`` mm (box top -> fold, flat):
    the inverse of he_geometry (bisection on the pin height)."""
    g = he_geometry(face_y, t, nf)
    lo, hi = g["box_top"] + g["r_c"] + 0.5, g["box_top"] + 2 * eye_flat
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if g["loop_len"](mid) / 2.0 < eye_flat:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def he_bracket(eye_flat: float) -> list:
    """Loaded pin height at every bracket corner: B-01 face (PANEL_OFFSET, in line, cheek-tip plane) x webbing
    thickness (HE_T_RANGE + HE_T) x fold plies under the main ply (1, 2)."""
    g = he_geometry()
    out = []
    for fy in (g["faces_y"][0], g["face_inline"], g["faces_y"][1]):
        for t in sorted({HE_T_RANGE[0], HE_T, HE_T_RANGE[1]}):
            for nf in (1, 2):
                out.append({"face_y": round(fy, 2), "t": t, "nf": nf, "pin_z": he_pin_z(eye_flat, fy, t, nf)})
    return out


def he_band() -> tuple:
    """HE-FIT pass band for the loaded pin centre above the floor seam line (review m-1): low end = the box top keeps
    HE_CHEEK_MIN under the cheeks; high end = HE_PIN_HI above the design."""
    g = he_geometry()
    return (g["box_top"] + g["env"]["cheek_half_z_mm"] + HE_CHEEK_MIN, g["pin_z"] + HE_PIN_HI)


def he_peel(eye_flat: float | None = None) -> dict:
    """BL-044 M-3: where each leg leaves the box top, design and worst. Leg A (against B-01) pulls INTO the panel;
    leg B (outside) pulls AWAY from the stack: its angle off the box line is a peel on the box top row. In line (the
    design face) the box sits on the resultant and leg B peels by half the included angle; held at the cheek-tip
    plane (a stiff B-18 / contents holding B-01 off) leg B peels by its full angle off the panel."""
    g = he_geometry()
    e = HE_EYE if eye_flat is None else eye_flat
    rows = {}
    for key, fy in (("inline", g["face_inline"]), ("tip_plane", g["faces_y"][1]), ("panel_offset", g["faces_y"][0])):
        for nf in (1, 2):
            pz = he_pin_z(e, fy, HE_T, nf)
            lp = he_loop(fy, g["box_top"], pz, HE_T, nf)
            box_dir = lp["resultant_deg"] if key == "inline" else 0.0
            rows[f"{key}_nf{nf}"] = {"face_y": round(fy, 2), "pin_z": round(pz, 2), "leg_A_deg": round(lp["leg_A_deg"], 1),
                                     "leg_B_deg": round(lp["leg_B_deg"], 1),
                                     "peel_deg": round(box_dir - lp["leg_B_deg"], 1)}
    worst = max(rows.values(), key=lambda r: r["peel_deg"])
    design = rows["inline_nf2"]
    return {"rows": rows, "design": design, "worst": worst,
            "peel_frac_design": round(math.sin(math.radians(design["peel_deg"])) / 2, 3),
            "peel_frac_worst": round(math.sin(math.radians(worst["peel_deg"])) / 2, 3)}


_HEG = he_geometry()
HE_BOX = (HE_W - 4.0, round(_HEG["box_h"], 1))          # 34 x 7
HE_EYE = round(_HEG["eye_flat"])                          # box top -> fold on the flat strip (mm, whole mm)
HE_FOLD = B18_BELOW + HE_BOX_GAP + HE_BOX[1] + HE_EYE     # fold from a raw end (raw end = B-01 cut edge)
HE_CUT = 2.0 * HE_FOLD                                    # BL-044: 2 x (12 + 4 + 7 + 25) = 96 (BL-041: 86)
HE_NECK_W = HE_W - 2 * HE_NECK_EDGE                       # 18
HE_NECK_TOL = 1.0                                         # ASSUMPTION HE-NECK-TOL (bag_attach.HINGE_NECK_TOL): 18 +/- 1
HE_CUT_BL041 = 86.0                                       # the BL-041 HE-PIN cut (box 34 x 10 at +4..+14, 17 mm eye): ledger
# ---- BL-040 B-2 DECISION RT-MATE: the roll-top clips' second buckle half sits on a webbing tab on each gusset, as the
# cloth-pass roll model put it (huntkit.viz3d.corrie_f CLIP_BELOW_SEAM_MM = 150 mm below the collar seam, tab hanging
# 38 mm). Female half on the gusset tab (fixed); the RT strap carries the adjustable male half.
# ---- BL-041 Y-2 DECISION RT-FWD (pack-designer): the clip path (RT strap + RTM tab + buckle body) ran down the gusset
# centre, between the two muzzle-keeper tabs and across their cord. BL-041 moved it forward to flat x 91 and its strap
# origin on the hem to the same ring position; BL-043 keeps the forward tab and corrects the rest (``rt_layout``):
# ---- BL-043 M-1 DECISION W3-OVER (pack-designer, 2026-11-13; supersedes BL-041 RT-OVER-W3 and its W3G guide). W3 is
# anchored on the crown top bar, so its crossing of the gusset moves with the torso setting: z 601 (kit S, 15 in) to
# 804 (kit L, 23 in) against a collar seam at z 745 (``w3_sweep``). No guide sewn on the gusset can span that (it ends
# 59 mm below the top of the sweep), and the roll model puts the roll and its bent-down ends at z 681-827 for the day
# and 6-day loads (``corrie_f_sim/corrie_f_roll_clips.json`` w3_roll), so at kit M and L settings W3 lies on the roll
# itself whatever the gusset carries. W3 is therefore the OUTER layer: it may cross the RT strap and the roll, and the
# user slackens W3 (G-hook off) before opening the roll top. Nothing hard sits in W3's sweep: the RTM buckle body and
# the hose slot are RT_CLEAR below the lowest W3 edge at every kit and torso end (6 corners, ``w3_corners``); W3 bears
# on webbing and cord only, never on a tack (W3G and its two unrated BT-S tacks are deleted).
#  * the RTM buckle bar sits BUCKLE_ENV + RT_CLEAR under the lowest W3 edge (kit S at 15 in), i.e. under the B-26 cord:
#    the cord crosses the strap above the buckle (soft on soft, accepted) and never the buckle body;
#  * DECISION HOSE-LOW (BL-043 m-9): the IMP-2 hose slot moves from z 700 (under W3 from 16.6 to 20.3 in: a cinched W3
#    pinched the hose) to HOSE_Z, its top RT_CLEAR under the lowest W3 edge: the hose leaves the bag below W3 at
#    every setting and goes forward to the shoulder strap without crossing it;
#  * the strap hangs from the slot's aft edge + RT_CLEAR + half the buckle (RT_X rule, now on the buckle width: the slot
#    and the buckle share a height band);
#  * BL-043 M-2 DECISION RT-ORIGIN: the strap is sewn at the ROLL END, the gusset centre of the hem (BL-040 RT-MATE,
#    restored). BL-041 put it at the clip path's ring position (27 % of the gusset from the frame corner): the hem then
#    folds flat only with a 76 mm tuck of each gusset's aft part (front layer 449 mm against a 601 mm back layer), and
#    the sewn 60 mm and box-X lay across the 40 mm HDPE-strip gap where the hem folds. Fall back to the old origin
#    (ticket rule); the strap runs from the roll end down to the forward tab (re-solved on the cloth-pass roll model).
RTM_CUT, RTM_FOLD = 70.0, 35.0    # as LLT: 70 mm, folded round the buckle bar
RTM_BOX = (21.0, 25.0)            # LLT_BOX rule (25 mm webbing less 2 mm a side x 25)
RT_SEWN = 60.0                    # strap_tails.ROLL_END_MM 90 = 60 sewn to the roll end + 30 round the buckle bar
RT_BOX = (25.0, 21.0)             # box-X on the hem: 25 along the strap x 21 across it (strap lies along the hem)
RT_HEM_Y = 16.5                   # ASSUMPTION RT-HEM: strap centred 16.5 mm above the hem seam line on B-07 (outer half of
#                                   the 70 mm hem, clear of the fold and of the B-07s strips); settled by the first collar
RT_CLEAR = 10.0                   # BL-041 ticket: >= 10 mm between the clip path and the muzzle tabs / cords / slot / W3
BUCKLE_ENV = (35.0, 35.0)         # ASSUMPTION BUCKLE-ENV: 25 mm side-release female half + mated male, 35 wide x 35 above
#                                   its bar (the record gives no body size); settled by a caliper on the bought buckle
STRAP_W = 25.0
CORD_R = 1.5                      # 3 mm shock cord (B-26, the muzzle keeper cord)
MK_PITCH = F.MUZZLE_TAB_GAP       # 60, ASSUMPTION MK-GAP: muzzle tabs 60 mm apart (30 mm clear between them for the barrel +
#                                   the keeper cord; was 70 / 40); settled by FIT-R3 (rifle in the keeper)
HEM_GAP = 40.0                    # bag_concepts.collar_set: two B-07s strips of (hem / 2 - 40): a 40 mm gap at each fold
ROLL_CLIPS_JSON = CONC / "corrie_f_sim" / "corrie_f_roll_clips.json"   # huntkit.viz3d.corrie_f --roll-clips (BL-043)


def w3_sweep() -> dict:
    """BL-043 M-1: W3's height at every crown setting of every crown kit. Both W3 anchors are on the crown top bar
    (geometry.yaml haul_wraps W3 'moves with torso'), so W3 runs level at the bar height (kw_heights: z linear between
    two equal anchor heights) while the bag stays on the hinge. Bar heights: geometry.yaml frame.crown_settings; kit
    ranges: crown_diet.SIZES. Returns {kit: {torso_in: z}} and the six kit-end corners."""
    from huntkit.gendesign import crown_diet as CDI
    cs = {round(float(q["torso_in"]), 1): float(q["crown_top_z"]) for q in BC.GEOM["frame"]["crown_settings"]}
    kits = {k: {t: z for t, z in cs.items() if lo - 1e-6 <= t <= hi + 1e-6} for k, (lo, hi) in CDI.SIZES.items()}
    corners = {f"{k} {t:g} in": cs[round(float(t), 1)] for k, (lo, hi) in CDI.SIZES.items() for t in (lo, hi)}
    zs = [z for d in kits.values() for z in d.values()]
    return {"kits": kits, "corners": corners, "z_min": min(zs), "z_max": max(zs), "half_w": STRAP_W / 2}


# DECISION HOSE-LOW (BL-043 m-9): slot top RT_CLEAR under the lowest W3 edge (z; the gusset is vertical there, so the
# sigma gap equals the z gap: checked in rt_clearances / w3_corners). ASSUMPTION HOSE-LOW: the bladder outlet sits at
# the IMP-2 sleeve foot (keeper tabs z 560), so the shorter inside run reaches the low port; settled by the hydration fit
# (hose from the port to the bite-valve clip on the shoulder strap at kit S 15 in and kit L 23 in, nothing crossing it).
HOSE_Z = float(math.floor(w3_sweep()["z_min"] - STRAP_W / 2 - RT_CLEAR - HOSE_SLOT[1] / 2))


def rt_layout(M: dict, c) -> dict:
    """BL-041 RT-FWD as corrected by BL-043 (W3-OVER, HOSE-LOW, RT-ORIGIN): the roll-clip path and the muzzle keepers on
    the flat gusset (x = flat x, the frame seam line is gy_frame(z); y = sigma). Every number from the pattern maps,
    the W3 sweep (all kits), the hose slot, the B-26 cord height."""
    gf, ga, sig = M["gy_frame"], M["gy_aft"], M["sig"]
    sw = w3_sweep()
    zz = np.linspace(BC.Z0, M["z_c"], 400)
    z_of = lambda y: float(np.interp(y, [sig(z) for z in zz], zz))       # noqa: E731
    y_w3_lo = sig(sw["z_min"]) - sw["half_w"]                     # lowest W3 edge (kit S, 15 in)
    y_bar = y_w3_lo - RT_CLEAR - BUCKLE_ENV[1]                    # buckle envelope RT_CLEAR under it
    z_bar = z_of(y_bar)
    hose_z = HOSE_Z                                               # DECISION HOSE-LOW
    hose_x1 = gf(hose_z) + 20.0 + HOSE_SLOT[0]
    x_rt = math.ceil(hose_x1 + RT_CLEAR + max(BUCKLE_ENV[0], STRAP_W) / 2)
    zt = M["z_c"]
    x_top = 0.5 * (gf(zt) + ga(zt))                               # RT-ORIGIN: the roll end = the gusset centre at the top
    y_env, y_top = y_bar + BUCKLE_ENV[1], sig(zt)

    def corridor_x(y):                                            # strap centre line in the flat: buckle -> roll end
        return x_rt + (x_top - x_rt) * float(np.clip((y - y_env) / (y_top - y_env), 0.0, 1.0))
    y_mk = (sig(B11_MUZ_Z) - B11_H / 2, sig(B11_MUZ_Z) + B11_H / 2)
    slope = (x_top - x_rt) / (y_top - y_env)                      # the band's horizontal half-width grows on a slant
    tab1_x0 = max(corridor_x(y) for y in y_mk) + (STRAP_W / 2 + RT_CLEAR) * math.hypot(1.0, slope)
    dx1 = math.ceil(tab1_x0 + B11_W / 2 - gf(B11_MUZ_Z))
    mk = (float(dx1), float(dx1 + MK_PITCH))
    return {"x": float(x_rt), "y_bar": y_bar, "z_bar": round(z_bar, 1), "below_seam": round(zt - z_bar, 1),
            "y_top": y_top, "x_top": x_top, "y_env": y_env, "frac_top": 0.5,
            "tab_frac": (x_rt - gf(z_bar)) / (ga(z_bar) - gf(z_bar)), "y_cord": sig(F.TRIPOD_KEEPER_Z), "mk_dx": mk,
            "z_w3_min": sw["z_min"], "z_w3_max": sw["z_max"], "y_w3_lo": y_w3_lo, "hose_z": hose_z,
            "hose_x1": hose_x1, "corridor": [(x_rt, y_env), (x_top, y_top)]}


def _rect_gap(r1, r2) -> float:
    """Clear distance between two axis-aligned rectangles (x0, y0, x1, y1); 0 when they touch or overlap."""
    dx = max(r2[0] - r1[2], r1[0] - r2[2], 0.0)
    dy = max(r2[1] - r1[3], r1[1] - r2[3], 0.0)
    return math.hypot(dx, dy)


def _bbox(ln):
    xs, ys = [q[0] for q in ln.points], [q[1] for q in ln.points]
    return (min(xs), min(ys), max(xs), max(ys))


def _gap(a, b) -> float:
    """Clear distance between two shapes, each an axis-aligned rect (x0, y0, x1, y1) or a shapely geometry."""
    from shapely.geometry import box
    ga_ = box(*a) if isinstance(a, tuple) else a
    gb_ = box(*b) if isinstance(b, tuple) else b
    return float(ga_.distance(gb_))


def rt_clearances(G: Piece, rl: dict, M: dict | None = None) -> dict:
    """BL-041 Y-2 / BL-043 M-1: clear distance (mm) from each part of the roll-clip path (RTM tab, buckle envelope, strap
    corridor from the buckle to the roll end) to every placement on the gusset it could foul: the muzzle-keeper tabs,
    the keeper cord between their slots, the hose slot, the bow tabs, the B-26 cord. Then W3 at the SIX kit-end corners
    (``w3_corners``): its band against the buckle body, the hose slot and the tabs."""
    from shapely.geometry import LineString
    x, yb = rl["x"], rl["y_bar"]
    corr = LineString(rl["corridor"]).buffer(STRAP_W / 2, cap_style=2)
    path = {"RTM tab": (x - STRAP_W / 2, yb - RTM_FOLD, x + STRAP_W / 2, yb),
            "buckle envelope": (x - BUCKLE_ENV[0] / 2, yb, x + BUCKLE_ENV[0] / 2, yb + BUCKLE_ENV[1]),
            "strap corridor": corr}
    obs = {}
    mk = []
    for ln in G.internal_lines:
        lab = ln.label or ""
        if lab.startswith("B-11 lash tab"):
            kind = "muzzle tab" if "muzzle" in lab else "bow tab"
            bb = _bbox(ln)
            obs[f"{kind} x {0.5 * (bb[0] + bb[2]):.0f}"] = bb
            if kind == "muzzle tab":
                mk.append(bb)
        elif lab.startswith("IMP-2 hose port slot"):
            obs["hose slot"] = _bbox(ln)
    if len(mk) == 2:                                   # keeper cord between the two slots (op 7.22)
        mk.sort()
        ys = mk[0][1] + 30.0
        obs["muzzle keeper cord"] = (0.5 * (mk[0][0] + mk[0][2]), ys - 3.0, 0.5 * (mk[1][0] + mk[1][2]), ys + 8.0)
    obs["B-26 cord (R)"] = (-1e3, rl["y_cord"] - CORD_R, 1e3, rl["y_cord"] + CORD_R)
    out = {f"{pk} | {ok}": round(_gap(pr, orr), 1) for pk, pr in path.items() for ok, orr in obs.items()}
    # the B-26 cord crosses the whole R gusset at z 600: it lies over the flat sewn RTM tab or under the strap (soft on
    # soft, as W3), never against the buckle body (W3-OVER puts the buckle RT_CLEAR under the lowest W3 edge, below it)
    accepted = {"RTM tab | B-26 cord (R)": "the cord lies over the flat, box-X'd tab below the buckle bar",
                "strap corridor | B-26 cord (R)": "the strap crosses the cord above the buckle (soft on soft; the clip "
                                                  "opens and the strap slides out from under or over it)"}
    accepted = {k: v for k, v in accepted.items() if k in out and out[k] < RT_CLEAR}
    chk = {k: v for k, v in out.items() if k not in accepted}
    corners = w3_corners(G, rl, path, obs, M)
    return {"gaps": out, "min_gap": min(chk.values()), "min_pair": min(chk, key=chk.get), "req": RT_CLEAR,
            "accepted": accepted, "w3_corners": corners,
            "w3_hard_min": min(r["hard_min"] for r in corners.values()),
            "w3_crossing": {"how": "W3 is the outer layer (DECISION W3-OVER): it may cross the RT strap, the RTM tab, "
                                   "the B-26 cord and the roll; slacken W3 to open the roll top"}}


# ---- BL-044 item 3: the RT strap's stand-off against the rifle barrel. ASSUMPTION RIFLE-LINE: the rifle lies on the
# gusset on a straight line from the butt boot (on the hip-belt wing: the frame seam line at the bag floor, +/-60 mm
# fore-aft for the boot's cant and the belt size) through the muzzle keeper (midway between the two muzzle-tab slots),
# and 300 mm on past it; barrel / brake OD corrie_f.MUZZLE_BARREL_D lying on the cloth. Settled by FIT-R3 row 5 (gloved
# clip open / close with the rifle in the keeper, both kit ends).
RIFLE_BOOT_DX = (-60.0, -30.0, 0.0, 30.0, 60.0)
RIFLE_PAST_KEEPER = 300.0


def rt_rifle_clearance(M: dict, rl: dict) -> dict:
    """Clear distance in the flat gusset between the rifle barrel (OD MUZZLE_BARREL_D, on ASSUMPTION RIFLE-LINE) and
    the roll-clip path (strap corridor, buckle envelope, RTM tab), for each boot position; and the strap's stand-off
    from the cloth at the muzzle-tab height (cloth-pass roll model) against the barrel OD."""
    from shapely.geometry import LineString, box
    gf, sig = M["gy_frame"], M["sig"]
    corr = LineString(rl["corridor"]).buffer(STRAP_W / 2, cap_style=2)
    env = box(rl["x"] - BUCKLE_ENV[0] / 2, rl["y_bar"] - RTM_FOLD, rl["x"] + BUCKLE_ENV[0] / 2, rl["y_bar"] + BUCKLE_ENV[1])
    K = (gf(B11_MUZ_Z) + 0.5 * sum(rl["mk_dx"]), sig(B11_MUZ_Z) + 7.5)          # slot centre: tab bottom + 30..35
    rows = {}
    for dx in RIFLE_BOOT_DX:
        B = (gf(BC.Z0) + dx, sig(BC.Z0))
        ux, uy = K[0] - B[0], K[1] - B[1]
        L = math.hypot(ux, uy)
        bar = LineString([B, (K[0] + ux / L * RIFLE_PAST_KEEPER, K[1] + uy / L * RIFLE_PAST_KEEPER)]).buffer(
            F.MUZZLE_BARREL_D / 2)
        rows[f"boot {dx:+.0f}"] = {"lean_deg": round(math.degrees(math.atan2(ux, uy)), 1),
                                   "to_strap_mm": round(float(bar.distance(corr)), 1),
                                   "to_buckle_mm": round(float(bar.distance(env)), 1)}
    so = {}
    try:
        d = json.loads(ROLL_CLIPS_JSON.read_text())
        for st, r in d["states"].items():
            for side, v in r["standoff"].items():
                so[f"{st} {side}"] = v["at_muzzle_tabs_mm"]
    except (OSError, KeyError, ValueError):
        pass
    mn = min(min(r["to_strap_mm"], r["to_buckle_mm"]) for r in rows.values())
    return {"rows": rows, "min_flat_mm": mn, "req": RT_CLEAR, "ok": mn >= RT_CLEAR, "keeper_xy": [round(v, 1) for v in K],
            "strap_standoff_at_muzzle_mm": so, "barrel_od": F.MUZZLE_BARREL_D,
            "standoff_min_mm": min(so.values()) if so else None,
            "note": "the strap passes forward of the barrel in the flat at every boot position; where it stands off "
                    "the cloth (27-40 mm at the muzzle tabs) it is also outboard of a barrel lying on the cloth"}


def w3_corners(G: Piece, rl: dict, path: dict, obs: dict, M: dict | None = None) -> dict:
    """BL-043 M-1: W3 at the six kit-end corners (S/M/L at both ends of their torso range). W3's band (25 mm, level at the
    crown-bar height) in the flat gusset, and its clear distance to the HARD parts on the gusset: the buckle envelope
    and the hose slot (>= RT_CLEAR required), and what it lies over (soft, recorded): RT strap corridor, RTM tab, muzzle
    tabs, B-26 cord. Above the collar seam (z_c) W3 is off the gusset (on the collar or the roll)."""
    from shapely.geometry import box
    sw = w3_sweep()
    M = M or _maps(F.make())
    sig, zc = M["sig"], M["z_c"]
    out = {}
    hard = {k: v for k, v in {"buckle envelope": path["buckle envelope"], "hose slot": obs.get("hose slot")}.items() if v}
    for name, z in sw["corners"].items():
        lo, hi = z - sw["half_w"], z + sw["half_w"]
        on = lo < zc
        yb = (sig(min(lo, zc)), sig(min(hi, zc)))
        band = box(-1e3, yb[0], 1e3, yb[1]) if on else None
        gaps = {k: (round(_gap(band, v), 1) if band is not None else None) for k, v in hard.items()}
        over = sorted(k for k, v in {**path, **obs}.items() if band is not None and k not in hard and _gap(band, v) == 0.0)
        hm = min((g for g in gaps.values() if g is not None), default=float("inf"))
        out[name] = {"z": z, "band_z": (round(lo, 1), round(hi, 1)), "on_gusset": on,
                     "above_collar_seam_mm": round(max(hi - zc, 0.0), 1), "hard_gaps": gaps, "hard_min": hm,
                     "lies_over": over, "ok": hm >= RT_CLEAR - 1e-6}
    return out


MATERIAL_FACE = {
    "challenge_ultra_200": ("film side DOWN (inside)", "non-directional, keep grain"),
    "cordura_330d_nylon66": ("PU coat DOWN (inside)", "solid colour: two-way lay allowed"),
    "cordura_500d_nylon66": ("PU coat DOWN (inside)", "solid colour: two-way lay allowed"),
    "robic_100d_ripstop": ("coated side DOWN (inside)", "two-way lay allowed"),
    "nylon_ripstop_70d": ("PU coat DOWN (inside)", "two-way lay allowed"),
    "ultragrid_210d_uhmwpe_ripstop": ("grid face UP", "two-way lay allowed"),
    "polyester_ht_630d_printable": ("print UP", "ONE-WAY camo print: all pieces the same way up"),
    "power_mesh_nylon_spandex": ("either", "ONE-WAY: stretch runs ACROSS the pocket (weft)"),
    "silicone_coated_poly_ripstop_40d": ("either", "two-way; weigh plies down, it slides"),
    "hypalon_coated_nylon": ("coated face UP", "laser-cut, any rotation"),
    "tpu_coated_nylon_840d": ("TPU DOWN (inside)", "laser-cut, any rotation"),
    "hdpe_sheet": ("-", "CNC router / knife, any rotation"),
    "poly_webbing_25mm": ("-", "hot-knife from the roll"), "poly_webbing_38mm": ("-", "hot-knife from the roll"),
    ELASTIC: ("-", "cold-cut, zigzag the lap"),
}
FREE_ROTATION = {"hypalon_coated_nylon", "tpu_coated_nylon_840d", "hdpe_sheet"}
ONE_WAY = {"polyester_ht_630d_printable", "power_mesh_nylon_spandex"}
WEBBING = {"poly_webbing_25mm", "poly_webbing_38mm", ELASTIC}
ROLL_FALLBACK = {"power_mesh_nylon_spandex": (1500.0, 1450.0)}   # ASSUMPTION: no roll width in the record (60 in mesh)


def fab(role: str, fabrics: str) -> str:
    return F.fab(role, fabrics)


# ============================================================================ helpers
def _len(pts) -> float:
    p = np.asarray(pts, float)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0


def _pt_at(pts, s):
    return CV.point_at_length(list(map(tuple, pts)), float(np.clip(s, 0.0, _len(pts))))[0]


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _box_x(p: Piece, cx, cy, w, h, label):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    p.add_internal_line(_rect(x0, y0, x1, y1), "stitch", f"{label} box-X {w:.0f}x{h:.0f}", closed=True)
    p.add_internal_line([(x0, y0), (x1, y1)], "stitch", "")
    p.add_internal_line([(x1, y0), (x0, y1)], "stitch", "")
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        p.add_drill_hole(x, y, 3.0, f"{label} box corner")


def _dedupe_notches(p: Piece, tol=3.0):
    keep = []
    for n in p.notches:
        if all(math.hypot(n.x - k.x, n.y - k.y) > tol for k in keep):
            keep.append(n)
        else:      # merge labels so nothing is lost
            for k in keep:
                if math.hypot(n.x - k.x, n.y - k.y) <= tol and n.label and n.label not in k.label:
                    k.label = (k.label + " / " + n.label).strip(" /")
    p.notches = keep


def _side_pts(side):
    """side = list of (piece, polyline) in sewing order -> cumulative junction lengths."""
    L = [_len(pts) for _, pts in side]
    return L, np.r_[0.0, np.cumsum(L)]


def _notch_on_side(side, s, label, kind="slit"):
    L, cum = _side_pts(side)
    k = int(np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(side) - 1))
    p, pts = side[k]
    x, y = _pt_at(pts, s - cum[k])
    p.add_notch(float(x), float(y), kind, label)


def notch_pair(sideA, sideB, label, pitch=NOTCH_PITCH, ends=False):
    """Match notches on two seam sides (each a list of (piece, polyline) in the SAME sewing direction): every ``pitch``
    mm of side A (scaled onto B when the seam has ease) plus every panel junction of either side on the other one.
    Returns the number of match points."""
    _, ca = _side_pts(sideA)
    _, cb = _side_pts(sideB)
    La, Lb = ca[-1], cb[-1]
    r = Lb / La if La else 1.0
    pos = list(np.arange(pitch, La - 0.4 * pitch, pitch))
    jA = [float(v) for v in ca[1:-1]]
    jB = [float(v) / r for v in cb[1:-1]]
    pos = sorted(set(round(v, 2) for v in pos + jA + jB + ([0.0, La] if ends else [])))
    for s in pos:
        kind = "v" if (min([abs(s - j) for j in jA + jB] or [99]) < 0.5) else "slit"
        _notch_on_side(sideA, s, label, kind)
        _notch_on_side(sideB, s * r, label, kind)
    return len(pos)


def ring_notches(sideA, origins, sideB, label, pitch=NOTCH_PITCH):
    """BL-040 M-3: notch a ring seam segment by segment. Each segment of side A gets notches every ``pitch`` mm measured
    from its own 'start' or 'end' (origins[i]) plus a V at every junction; side B gets the same ring positions (scaled
    when the seam has ease). A pattern used twice in the ring (the gusset, cut as a pair) therefore carries one notch set
    when both passes measure from the same physical end. Returns {segment index: [distance from its origin, ...]}."""
    L, ca = _side_pts(sideA)
    _, cb = _side_pts(sideB)
    r = cb[-1] / ca[-1] if ca[-1] else 1.0
    pos, seg = [], {}
    for i, (Li, c0) in enumerate(zip(L, ca[:-1])):
        ks = [k * pitch for k in range(1, int(Li // pitch) + 1) if k * pitch < Li - 0.4 * pitch]
        seg[i] = [round(d, 2) for d in ks]
        pos += [(c0 + d if origins[i] == "start" else c0 + Li - d, "slit") for d in ks]
        if i:
            pos.append((c0, "v"))
    pos += [(float(v) / r, "v") for v in cb[1:-1]]
    for s, kind in sorted(pos):
        _notch_on_side(sideA, s, label, kind)
        _notch_on_side(sideB, s * r, label, kind)
    return seg


VEdge = F.PolyEdge   # BL-033: the class moved to corrie_f (its build uses it for the D2 seams)


def _v_side(name, side):
    """A seam side made of raw polylines (for the seam-length report)."""
    return [VEdge(p, pts, f"{name} {i}") for i, (p, pts) in enumerate(side)]


# ============================================================================ the set
@dataclass
class RevSet:
    fabrics: str
    pieces: dict = field(default_factory=dict)       # id -> Piece (base size)
    graded: dict = field(default_factory=dict)       # id -> {kit: Piece}
    meta: dict = field(default_factory=dict)         # id -> {group, kit, step, notes}
    seams: list = field(default_factory=list)
    webbing: list = field(default_factory=list)      # cut list rows (also drawn as pieces where useful)
    hardware: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    lid: dict = field(default_factory=dict)
    geo: dict = field(default_factory=dict)

    def add(self, p: Piece, group: str, step: str, kit: str = "base", notes: str = "") -> Piece:
        if p.piece_id in self.pieces:
            raise KeyError(f"duplicate piece id {p.piece_id}")
        p.knife_direction = p.knife_direction or KNIFE
        p.labels.setdefault("pack", "5200 CORRIE F rev 3")
        self.pieces[p.piece_id] = p
        self.meta[p.piece_id] = {"group": group, "step": step, "kit": kit, "notes": notes}
        return p

    def all_pieces(self, kits=None, sizes=None, webbing=None):
        out = []
        for pid, p in self.pieces.items():
            m = self.meta[pid]
            if kits and m["kit"] not in kits:
                continue
            is_web = p.material_id in WEBBING
            if webbing is not None and is_web != webbing:
                continue
            if pid in self.graded:
                for s, g in self.graded[pid].items():
                    if sizes is None or s in sizes:
                        out.append(g)
            else:
                out.append(p)
        return out


# ============================================================================ BL-034 placement helpers
def kw_heights(c) -> dict:
    """Height z at which each haul wrap W1-W3 crosses the two aft corner seams (where its K-W keeper loop is caught).
    Anchors from geometry.yaml haul_wraps (19 in) and frame.hard_points. ASSUMPTION KW-PATH: the wrap runs from its R
    anchor round the frame face, R gusset, aft face, L gusset to its L anchor with z linear in the path length (a
    straight line on the developed surface); a and depth taken at the wrap's mid height. Settled by the first fitting
    (T9 W free lengths): the keeper notch must sit within +/-15 mm of the wrap's edge."""
    hp = BC.GEOM["frame"]["hard_points"]
    out = {}
    with F.frame_face(c):
        for w in BC.GEOM["haul_wraps"]:
            zR, zL = float(w["z_R_at_19in"]), float(w["z_L_at_19in"])
            xa = abs(float(hp[w["anchor_R"]][0])) if w["anchor_R"] in hp else 0.0
            zm = 0.5 * (zR + zL)
            a, d = float(c.a([zm])[0]), float(c.depth([zm])[0])
            run = max(a - xa, 0.0) if xa else 0.0
            T = 2 * run + 2 * d + 2 * a
            fR, fL = (run + d) / T, (run + d + 2 * a) / T
            out[w["id"]] = {"R": round(zR + (zL - zR) * fR, 1), "L": round(zR + (zL - zR) * fL, 1)}
    return out


# ---- BL-044 DECISION KW-W3-OFF (BL-043 found-not-fixed; review M-1 'K-W keepers z 703'): W3's two anchors are on the
# crown top bar, so W3 runs level at the bar height, z 601-804 over the crown kits (w3_sweep), while the bag stays on
# the hinge. A K-W loop sewn in the aft corner seam fixes W3's height there (z 702.6, the 19 in crossing): at any other
# setting W3 climbs or drops along the gusset to the loop and turns level across the aft face, and the loop (a seam-
# caught 25 mm fold, no rating) takes the turn's cross load. Nothing on the bag can follow a 203 mm sweep (the
# collar seam is at 745 and the roll above it), so the W3 loops are deleted: W3 is located by its own two anchors at
# one height and runs straight (level) at every kit end. The W1 / W2 loops stay (anchors on the frame, which does not
# move with the torso setting). Unhooked, W3 hangs from its R anchor on the crown bar as before (the loops never held
# that end).
KW_WRAPS = ("W1", "W2")
KW_CUT = 80.0                     # ASSUMPTION (ledger 'keepers: 6 haul-wrap keeper loops'): 25 mm webbing, 80 mm cut
W3_HAUL_N = 225.0                 # loadpath_verification S9 (the W G-hook end load row, mfg load_points)


def kw_w3_kink(c) -> dict:
    """What a W3 K-W loop fixed at the 19 in crossing would do at the six kit-end corners: W3 runs on the gusset from the
    frame seam (crown-bar height) to the loop at the aft corner seam, then level across the aft face. Slope over the
    gusset depth at the loop height (c.depth), the turn angle at the loop and the loop's cross load at W3's haul
    tension (2 T sin(turn / 2))."""
    z_k = kw_heights(c)["W3"]["R"]
    sw = w3_sweep()
    with F.frame_face(c):
        d = float(c.depth([z_k])[0])
    rows = {}
    for name, z in sw["corners"].items():
        dz = z - z_k
        ang = math.degrees(math.atan2(abs(dz), d))
        rows[name] = {"w3_z": z, "dz_mm": round(dz, 1), "slope_deg": round(ang, 1),
                      "loop_cross_load_n": round(2 * W3_HAUL_N * math.sin(math.radians(ang) / 2), 1)}
    worst = max(rows.values(), key=lambda r: r["slope_deg"])
    return {"loop_z": z_k, "gusset_depth_mm": round(d, 1), "corners": rows, "worst": worst, "haul_n": W3_HAUL_N,
            "decision": "KW-W3-OFF: W3 loops deleted, W3 level at its anchor height at every corner"}


def _b11_marks(G, xc, yc, label):
    """B-11 lash tab on the gusset: 30 x 50 outline (slot end up), its sew-down box (the B-11 piece's 24 x 19 box at the
    lower end) and the box corners as drill marks."""
    x0, y0 = xc - B11_W / 2, yc - B11_H / 2
    G.add_internal_line(_rect(x0, y0, x0 + B11_W, y0 + B11_H), "placement", f"B-11 lash tab: {label} (both gussets)",
                        closed=True)
    G.add_internal_line(_rect(x0 + 3, y0 + 3, x0 + 27, y0 + 22), "stitch", "B-11 sew-down box", closed=True)
    G.add_internal_line(_rect(x0 + 1.5, y0 + 30, x0 + 28.5, y0 + 35), "placement", "B-11 slot 27 x 5 (on the tab)", closed=True)
    for x, y in ((x0 + 3, y0 + 3), (x0 + 27, y0 + 3), (x0 + 27, y0 + 22), (x0 + 3, y0 + 22)):
        G.add_drill_hole(x, y, 3.0, "B-11 box corner")


# ============================================================================ shell + door + collar
def _maps(c):
    """Flat coordinate maps of the S15 shell pieces (the same formulas corrie_f / bag_concepts draft them with)."""
    with F.frame_face(c):
        zk = BC._kinks(c)
        s01 = BC.unroll(zk, BC.y_frame(zk))
        sig = BC.unroll_xz(zk, c.a(zk))
        yr = float(BC.y_frame([BC.Z0])[0])
        fy = {float(z): float(BC.y_frame([z])[0]) - yr for z in np.linspace(BC.Z0, c.z_c, 300)}
        ay = {float(z): float(c.y_front([z])[0]) - yr for z in np.linspace(BC.Z0, c.z_c, 300)}
        zf, S, A = F._face_xy(c)
    zz = np.array(sorted(fy))
    return {
        "s01": lambda z: float(np.interp(z, zk, s01)),
        "a": lambda z: float(c.a([z])[0]),
        "sig": lambda z: float(np.interp(z, zk, sig)),
        "gy_frame": lambda z: float(np.interp(z, zz, [fy[k] for k in zz])),
        "gy_aft": lambda z: float(np.interp(z, zz, [ay[k] for k in zz])),
        "S": S, "A": A, "inner": lambda z: A(z) - float(F.blade_w(c, z)), "zk": zk, "z_c": float(c.z_c),
    }


def build_shell(rs: RevSet, c):
    b = F.build(c, DOOR, rs.fabrics)
    P = {p.piece_id: p for p, _ in b.pieces}
    M = _maps(c)
    rs.geo.update(z_c=M["z_c"], zip_door_mm=b.extra["zip_door_mm"], collar_per_mm=b.extra["collar_perimeter_mm"])
    step = {"B-01": "9 main bag", "B-03": "9 main bag", "B-05": "9 main bag", "B-02u": "8 door + blade",
            "B-02door": "8 door + blade", "B-02h": "8 door + blade", "SH-07": "8 door + blade",
            "SH-01b": "9 main bag", "B-06f": "10 collar + roll top", "B-06": "10 collar + roll top",
            "B-07": "10 collar + roll top", "B-07s": "10 collar + roll top"}
    for pid, p in P.items():
        if pid == "B-13x":
            continue
        rs.add(p, "shell", step[pid])
    B01, G, BOT, U, DR, HB = (P[k] for k in ("B-01", "B-03", "B-05", "B-02u", "B-02door", "B-02h"))
    G.labels["cut"] = "1 pair L+R (mirror); marks labelled 'L only' / 'R only' go on that gusset only"
    # ---- seams: corrie_f.build's pairs as built (BL-033: the door zip and band | blade seams are real pairs there now)
    for s, tags in b.seams:
        ea, eb = s.a[0], s.b[0]
        if len(s.a) == 1 and len(s.b) == 1 and ea.piece is eb.piece and ea.name == eb.name:
            raise ValueError(f"self-paired placeholder seam in corrie_f.build: {s.name}")
        rs.seams.append(Seam(s.a, s.b, name=s.name, stitch="301"))
    sp = b.extra["d2_inner_split"]
    hiR, mid, hiL = sp["hiR"], sp["mid"], sp["hiL"]
    zipe = DR.edge_points("zip")
    # ---- notches on every seam (50 mm + junctions)
    E = lambda p, e, rev=False: (p, p.edge_points(e)[::-1] if rev else p.edge_points(e))  # noqa: E731
    pairs = [
        ([E(B01, "right")], [E(G, "frame", True)], "B-01|B-03 R"),
        ([E(B01, "left", True)], [E(G, "frame", True)], "B-01|B-03 L"),
        ([E(B01, "bottom")], [E(BOT, "bottom")], "B-01|B-05"),
        ([E(G, "bottom")], [E(BOT, "right")], "B-03|B-05 R"),
        ([E(G, "bottom")], [E(BOT, "left", True)], "B-03|B-05 L"),
        ([E(U, "outer_right")], [E(G, "aft")], "blade|B-03 R"),
        ([E(U, "outer_left", True)], [E(G, "aft")], "blade|B-03 L"),
        ([E(U, "bottom")], [E(BOT, "top", True)], "blade|B-05"),
        ([E(DR, "zip")], [(U, mid[::-1])], "door zip"),
        ([E(HB, "bottom")], [E(DR, "hinge")], "hinge"),
        ([E(HB, "right")], [(U, hiR[::-1])], "band|blade R"),
        ([E(HB, "left")], [(U, hiL[::-1])], "band|blade L"),
    ]
    for a, bb, lab in pairs:
        notch_pair(a, bb, lab)
    col = {p.piece_id: p for p, g in b.pieces if g == "collar"}
    # BL-040 M-3: the ring runs ONE way round the bag. B-01 top runs R -> L (x +180 -> -180), so the L gusset follows,
    # traversed frame -> aft (its 'top' edge runs aft -> frame: reversed), then the L blade top, the band and the R blade
    # top (all reversed: they run L <- R as drawn), then the R gusset aft -> frame (as drawn). BL-032 passed every edge
    # unreversed, which mirrored the notches on the gusset and the band (review M-3: 10 mm off on the gusset).
    tops = [E(B01, "top"), E(G, "top", True), E(U, "top_left", True), E(HB, "top", True), E(U, "top_right", True),
            E(G, "top")]
    # both gusset passes measure their 50 mm notches from the FRAME end, so the one gusset pattern carries one set
    rs.geo["collar_ring"] = ring_notches(tops, ["start", "start", "start", "start", "start", "end"],
                                         [E(col["B-06f"], "bottom"), E(col["B-06"], "bottom")], "collar ring")
    notch_pair([E(col["B-06f"], "right")], [E(col["B-06"], "left", True)], "collar R", pitch=100.0)
    notch_pair([E(col["B-06f"], "left")], [E(col["B-06"], "right", True)], "collar L", pitch=100.0)
    notch_pair([E(col["B-07"], "bottom")], [E(col["B-06f"], "top"), E(col["B-06"], "top")], "hem ring")
    # BL-040 B-2: RT strap placements on the hem B-07, above each gusset's centre (the roll end). The collar is a straight
    # tube (B-06f / B-06 bottom = top), so a ring position carries straight up. Body ring: B-01 top, L gusset, ..., R
    # gusset; collar bottom ring: B-06f (0 -> 360) then B-06 (0 -> 690); hem ring: B-06f top (360 -> 0) then B-06 top
    # (690 -> 0) = B-07 bottom (0 -> 1050). The strap's sewn 60 mm lies on the FRAME-side half of the gusset (both sides
    # the same, mirror), its free end crossing the gusset-centre notch.
    _, ctop = _side_pts(tops)
    _, ccol = _side_pts([E(col["B-06f"], "bottom"), E(col["B-06"], "bottom")])
    L06f, L06 = col["B-06f"].edge_length("bottom"), col["B-06"].edge_length("bottom")
    L07 = col["B-07"].edge_length("bottom")
    Lg = float(ctop[2] - ctop[1])
    rt = {}
    # BL-043 M-2 DECISION RT-ORIGIN: the strap is sewn at the ROLL END again (the gusset centre of the hem, where the
    # 40 mm gap between the two B-07s strips lets the hem fold flat); its sewn 60 mm lies on the FRAME-side half, on the
    # strip, its free end leaving across the fold line (the gusset-centre notch) and out of the roll end.
    k_hem = L07 / float(ctop[-1])
    Lf = float(ctop[1])                                            # B-01 top (the frame side of the ring)
    hem = {"hem_mm": round(L07, 1), "frame_mm": round(Lf * k_hem, 1), "gusset_mm": round(Lg * k_hem, 1)}
    f41 = 0.269                                                    # BL-041 frac_top (clip path ring position)
    front = (Lf + 2 * f41 * Lg) * k_hem
    hem.update(fold="gusset centre (B-07s strip gap)", front_layer_mm=round(0.5 * L07, 1),
               bl041_front_layer_mm=round(front, 1), bl041_back_layer_mm=round(L07 - front, 1),
               bl041_tuck_each_mm=round(0.5 * ((L07 - front) - front), 1))
    for side, s_ring, sgn in (("L", float(ctop[1]) + 0.5 * Lg, -1), ("R", float(ctop[-1]) - 0.5 * Lg, 1)):
        x06 = s_ring * ccol[-1] / ctop[-1] - L06f                  # on B-06 (bottom = top x)
        s_hem = L06f + (L06 - x06)
        xc = s_hem * L07 / (L06f + L06)
        # R: hem runs frame -> aft at the R gusset, so the frame side is x < xc; L: aft -> frame, frame side x > xc
        x0, x1 = (xc - RT_SEWN, xc) if sgn > 0 else (xc, xc + RT_SEWN)
        B07 = col["B-07"]
        B07.add_internal_line(_rect(x0, RT_HEM_Y - 12.5, x1, RT_HEM_Y + 12.5), "placement",
                              f"RT roll-clip strap {side} (OUTSIDE; free end out across the roll-end notch)", closed=True)
        # box on the part that lies on the B-07s strip (sewn 60 less the half gap), clear of the fold zone
        bx = xc - sgn * (HEM_GAP / 2 + 0.5 * (RT_SEWN - HEM_GAP / 2))
        _box_x(B07, bx, RT_HEM_Y, RT_BOX[0], RT_BOX[1], f"RT strap {side}")
        B07.add_notch(xc, 0.0, "v", f"roll end {side} (RT strap; hem folds here)")
        # BL-044 (stale mark): the strip ends were edge slits, and _dedupe_notches merged the L frame-side one into the
        # 'hem ring' match slit 2.7 mm away (drawn at 950.0 for 947.3). They are now placement lines across the hem at
        # their exact x, which no edge-notch merge can move.
        hy0, hy1 = B07.bounds(cut=False)[1], B07.bounds(cut=False)[3]
        for xg in (xc - HEM_GAP / 2, xc + HEM_GAP / 2):
            B07.add_internal_line([(xg, hy0), (xg, hy1)], "placement", "B-07s strip end (HDPE strip stops here)")
        rt[side] = {"x_centre": round(xc, 1), "x0": round(x0, 1), "x1": round(x1, 1), "box_x": round(bx, 1),
                    "box_to_gap_mm": round(abs(bx - xc) - RT_BOX[0] / 2 - HEM_GAP / 2, 1)}
    rs.geo["rt_origin"] = hem
    rs.geo["rt_on_b07"] = rt
    # door zip corner tangents (corrie_f_body.md section 9.3)
    zl, r = F.D2["z_lo"], F.D2["r"]
    xc = M["inner"](zl + r)
    for sx in (-1, 1):
        for q in ((sx * xc, M["S"](zl + r)), (sx * (xc - r), M["S"](zl + r) - r)):
            for p in (DR, U):
                p.add_notch(q[0], q[1], "v", "zip corner tangent")
    # ---- B-01 marks
    s01, a = M["s01"], M["a"]
    for cz in getattr(B01, "creases", []):
        hw = float(np.interp(cz, [s01(z) for z in M["zk"]], [a(z) for z in M["zk"]]))
        B01.add_internal_line([(-hw, cz), (hw, cz)], "fold", "crease (bend, no stitch)")
    for st, (zc, lo, hi) in SWELLS.items():
        for sx in (-1, 1):
            x0, x1 = sx * STAY_X - SWELL_W / 2, sx * STAY_X + SWELL_W / 2
            y0, y1 = s01(zc - lo), s01(zc + hi)
            B01.add_internal_line(_rect(x0, y0, x1, y1), "cut_inside", f"swell window {st.upper()} (cut out)", closed=True)
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                B01.add_drill_hole(x, y, 3.0, "swell window corner")
    # B-27 guy port slits (corrie_f.guy_port): x +/-52, z 595 -> top edge (collar seam z 745)
    z0p, z1p = F.PORT_Z
    for sx in (-1, 1):
        x = sx * F.REVS[2]["guy_x"]
        pts = [(x, s01(z)) for z in sorted({z0p, *[z for z in M["zk"] if z0p < z < z1p], z1p})]
        B01.add_internal_line(pts, "cut_inside", "B-27 guy port slit (cut)")
        B01.add_drill_hole(x, s01(z0p), 3.0, "B-27 slit end: bartack")
        xi, xo = x - sx * PORT_LAP_IN, x + sx * (F.PORT_FACING_W - PORT_LAP_IN)
        fz0, fz1 = s01(z0p) - F.PORT_END, s01(z1p)
        B01.add_internal_line(_rect(min(xi, xo), fz0, max(xi, xo), fz1), "placement", "B-27f facing (inside)", closed=True)
    # B-17 (outside) / B-18 (inside) at the stays; IMP-2 keeper tabs; B-01 side notches
    for sx in (-1, 1):
        x = sx * STAY_X
        y0 = s01(B17_Z - B17[1] / 2)
        B01.add_internal_line(_rect(x - B17[0] / 2, y0, x + B17[0] / 2, y0 + B17[1]), "placement",
                              "B-17 IM3 bag-hook tab (OUTSIDE)", closed=True)
        # BL-040 B-1: B-18 reaches 12 mm below the floor seam line (to the B-01 cut edge) so the floor seam catches it;
        # the HE box-X (DECISION HE-ONE) drawn on B-01 too, so the box_mismatches check sees every layer of the stack
        y18 = s01(BC.Z0) - B18_BELOW
        B01.add_internal_line(_rect(x - B18_W / 2, y18, x + B18_W / 2, s01(BC.Z0 + B18_TOP)), "placement",
                              "B-18 hinge-eye doubler (INSIDE; lower edge ON the B-01 cut edge, caught in the floor seam)",
                              closed=True)
        _box_x(B01, x, s01(BC.Z0 + HE_BOX_GAP + HE_BOX[1] / 2), HE_BOX[0], HE_BOX[1], "HE hinge eye (OUTSIDE)")
        B01.add_drill_hole(sx * IMP2_KEEP[0], s01(IMP2_KEEP[1]), 3.0, "IMP-2 keeper tab")
    _edge_notch_at_z(B01, "left", lambda z: (-a(z), s01(z)), HARD_Z, "hard-point loop (L only)")
    _edge_notch_at_z(B01, "right", lambda z: (a(z), s01(z)), (POLE_TAB_Z,), "E-5 pole grip tab")
    _edge_notch_at_z(B01, "right", lambda z: (a(z), s01(z)), (F.TRIPOD_KEEPER_Z,), "B-26 tripod keeper")
    # ---- B-03 gusset marks (flat x = depth from the frame face, y = sigma)
    sig, gf, ga = M["sig"], M["gy_frame"], M["gy_aft"]
    for z in HARD_Z:
        G.add_notch(gf(z), sig(z), "v", "hard-point loop (L only)")
        G.add_notch(ga(z), sig(z), "v", "hard-point loop (L only)")
    G.add_notch(gf(POLE_TAB_Z), sig(POLE_TAB_Z), "v", "E-5 pole grip tab (R only)")
    for z in (F.TRIPOD_KEEPER_Z,):
        G.add_notch(gf(z), sig(z), "v", "B-26 keeper (R only)")
        G.add_notch(ga(z), sig(z), "v", "B-26 keeper (R only)")
    fpw = F.fp_spec()["w"]               # BL-033: 165 mm face (corrie_f.FP_FACE_W)
    zs = np.linspace(*FP_Z, 12)
    inn = [ga(z) - fpw for z in zs]      # BL-033: a plain 165 mm face, no clamp (BL-032 clamped the 180 mm face)
    rs.geo["fp_min_margin_mm"] = round(min(ga(z) - gf(z) - fpw for z in zs), 1)   # face inner edge to the frame seam
    # ASSUMPTION FP-CLEAR: >= 9 mm between the pocket's inner edge stitch and the B-01 | gusset seam line (presser foot
    # 6 mm + 3 mm); BL-032 held 10 mm. Settled by sewing FP-L on the first gusset.
    rs.geo["fp_clear_req_mm"] = 9.0
    rs.geo["fp_clamped_mm"] = 0.0         # kept for readers of BL-032's key (mfg_corrie_f_rev3): nothing is clamped now
    G.add_internal_line([(ga(z), sig(z)) for z in zs] + [(x, sig(z)) for x, z in zip(inn[::-1], zs[::-1])], "placement",
                        "FP hip-reach pocket (both gussets)", closed=True)
    G.add_drill_hole(ga(FP_Z[0]) - 3, sig(FP_Z[0]) + 3, 3.0, "FP corner")
    G.add_drill_hole(inn[0] + 3, sig(FP_Z[0]) + 3, 3.0, "FP corner")
    G.add_internal_line([(ga(IMP8_Z[1]) - 140.0, sig(IMP8_Z[1])), (ga(IMP8_Z[1]), sig(IMP8_Z[1]))], "placement",
                        "IMP-8 cup top (R only)")
    hx = gf(HOSE_Z) + 20.0 + HOSE_SLOT[0] / 2
    G.add_internal_line(_rect(hx - HOSE_SLOT[0] / 2, sig(HOSE_Z) - HOSE_SLOT[1] / 2, hx + HOSE_SLOT[0] / 2,
                              sig(HOSE_Z) + HOSE_SLOT[1] / 2), "cut_inside", "IMP-2 hose port slot (both)", closed=True)
    G.add_internal_line([(gf(BC.Z0), sig(BC.Z0) + 70.0), (ga(BC.Z0), sig(BC.Z0) + 70.0)], "placement",
                        "SH-01b kick band top")
    # BL-034: B-11 lash tabs, 4 per gusset (ASSUMPTION B11-PLACE): 2 bow riser / lash tabs, 2 muzzle keeper tabs
    b11 = []
    for z in B11_BOW_Z:
        _b11_marks(G, ga(z) - B11_BOW_IN, sig(z), f"bow riser (R) / light lash, no load rating (L), z {z:.0f}")
        b11.append(("bow riser / lash", z, round(ga(z) - B11_BOW_IN - gf(z), 1)))
    rl = rt_layout(M, c)                       # BL-041 Y-2 DECISION RT-FWD
    for dx in rl["mk_dx"]:
        _b11_marks(G, gf(B11_MUZ_Z) + dx, sig(B11_MUZ_Z), f"muzzle keeper, z {B11_MUZ_Z:.0f}")
        b11.append(("muzzle keeper", B11_MUZ_Z, dx))
    rs.geo["b11"] = {"per_gusset": len(b11), "tabs": b11}
    # BL-040 B-2 DECISION RT-MATE + BL-041 RT-FWD: the roll-clip buckle tab on each gusset (both: one pattern) on the
    # clip path RT_X, its bar RT_CLEAR above the B-26 cord; buckle bar on the top line, tab hanging down; LLT box rule
    xm, yb, zt = rl["x"], rl["y_bar"], rl["z_bar"]
    G.add_internal_line(_rect(xm - 12.5, yb - RTM_FOLD, xm + 12.5, yb), "placement",
                        "RTM roll-clip buckle tab (both gussets, OUTSIDE; buckle bar on the top line)", closed=True)
    _box_x(G, xm, yb - (RTM_CUT * 0.75 - RTM_FOLD), RTM_BOX[0], RTM_BOX[1], "RTM buckle tab")
    # BL-043: no W3G (DECISION W3-OVER); the strap's flat shadow from the buckle to the roll end, for the reader
    G.add_internal_line([(xm, yb + BUCKLE_ENV[1]), (rl["x_top"], rl["y_top"])], "placement",
                        "RT strap from the roll end (roll clip; nothing sewn on it; W3 may lie over it)")
    rs.geo["rtm"] = {"z": round(zt, 1), "below_seam_mm": rl["below_seam"],
                     "depth_from_frame_mm": round(xm - gf(zt), 1), "gusset_depth_mm": round(ga(zt) - gf(zt), 1),
                     "rect": (round(xm - 12.5, 1), round(yb - RTM_FOLD, 1), round(xm + 12.5, 1), round(yb, 1)),
                     "x": xm, "y_bar": round(yb, 1), "tab_frac": round(rl["tab_frac"], 3)}
    rs.geo["rt_layout"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rl.items()}
    rs.geo["rt_clear"] = rt_clearances(G, rl, M)
    rs.geo["rt_rifle"] = rt_rifle_clearance(M, rl)             # BL-044 item 3
    rs.geo["w3_sweep"] = {k: v for k, v in w3_sweep().items() if k != "kits"}
    # BL-034: K-W keeper loops at the W1-W3 crossings of the aft corner seams (ASSUMPTION KW-PATH). BL-044 DECISION
    # KW-W3-OFF: only W1 / W2 get keepers (frame-fixed anchors); W3 rides at the crown-bar height (kw_w3_kink)
    kw = {k: v for k, v in kw_heights(c).items() if k in KW_WRAPS}
    rs.geo["kw_z"] = kw
    rs.geo["kw_w3"] = kw_w3_kink(c)
    for wid, zz in kw.items():
        for side, sx in (("R", 1), ("L", -1)):
            z = zz[side]
            G.add_notch(ga(z), sig(z), "v", f"K-W keeper {wid} ({side} only)")
            U.add_notch(sx * M["A"](z), M["S"](z), "v", f"K-W keeper {wid}")
    # ---- D2 face marks
    S, A, inner_f = M["S"], M["A"], M["inner"]
    pl = F.b22_placement(c)              # BL-033: one source with the sim route (corrie_f.over_port_b22in)
    x22 = pl["x_mm"]
    rs.geo["b22"] = {"drawn_x": round(B22_XZ[0], 1), "band_half_w_at_z": pl["band_half_w_mm"], "placed_x": x22,
                     "moved_mm": pl["moved_mm"]}
    for sx in (-1, 1):
        HB.add_internal_line(_rect(sx * x22 - B22_WH[0] / 2, S(B22_XZ[1]) - B22_WH[1] / 2, sx * x22 + B22_WH[0] / 2,
                                   S(B22_XZ[1]) + B22_WH[1] / 2), "placement", "B-22 guy anchor (INSIDE)", closed=True)
        _box_x(HB, sx * x22, S(B22_XZ[1]), LLT_BOX[0], LLT_BOX[1], "B-22 / guy LLT")
        # BL-034 DECISION B28-FACE: OUTSIDE, 21 x 20 box (the B-28t box), lock bar at z 700
        yb = S(B28_TAB_Z)
        HB.add_internal_line(_rect(sx * F.CROWN_X - 12.5, yb - 2 * B28_BAR_DROP, sx * F.CROWN_X + 12.5, yb), "placement",
                             "B-28 front lock tab (OUTSIDE, lock bar at the top line)", closed=True)
        _box_x(HB, sx * F.CROWN_X, yb - B28_BAR_DROP, B28_BOX[0], B28_BOX[1], "B-28 front tab (OUTSIDE)")
    di = (S(IMP4_Z[0]), S(IMP4_Z[1]))
    w4 = 200.0      # IMP4-a 216 cut = 200 finished (8 mm SA)
    DR.add_internal_line(_rect(-w4 / 2, di[0], w4 / 2, di[1]), "placement", "IMP-4 pocket (INSIDE face)", closed=True)
    for x, y in ((-w4 / 2, di[0]), (w4 / 2, di[0]), (w4 / 2, di[1]), (-w4 / 2, di[1])):
        DR.add_drill_hole(x, y, 3.0, "IMP-4 corner")
    U.add_internal_line(_rect(A(c.z_c) - 40 - 1, S(c.z_c) - 60, A(c.z_c) - 1, S(c.z_c)), "placement",
                        "SH-07 slider garage", closed=True)
    _edge_notch_at_z(U, "outer_left", lambda z: (-A(z), S(z)), HARD_Z, "hard-point loop")
    _edge_notch_at_z(U, "outer_right", lambda z: (A(z), S(z)), (F.TRIPOD_KEEPER_Z,), "B-26 tripod keeper")
    # B-05: hinge eye centre lines
    a0 = a(BC.Z0)
    # BL-034 F02-PLACE: F-02 on the OUTSIDE of B-05, centred across, ASSUMPTION F02-CENTRE fore-aft; zip edge aft
    W2, H2 = F.F02_WH
    bx0, by0, bx1, by1 = BOT.bounds(cut=False)
    fx0, fy0 = 0.5 * (bx0 + bx1) - W2 / 2, 0.5 * (by0 + by1) - H2 / 2
    BOT.add_internal_line(_rect(fx0, fy0, fx0 + W2, fy0 + H2), "placement",
                          f"F-02 fly pocket ({F02_OUT}), #5 zip on the aft edge (top line)", closed=True)
    for x, y in ((fx0 + 3, fy0 + 3), (fx0 + W2 - 3, fy0 + 3), (fx0 + W2 - 3, fy0 + H2 - 3), (fx0 + 3, fy0 + H2 - 3)):
        BOT.add_drill_hole(x, y, 3.0, "F-02 corner")
    rs.geo["f02_on_b05"] = {"x0": round(fx0, 1), "y0": round(fy0, 1), "w": W2, "h": H2, "face": F02_OUT}
    for sx in (-1, 1):
        BOT.add_notch(a0 + sx * STAY_X, 0.0, "v", "hinge eye CL")
        B01.add_notch(sx * STAY_X, 0.0, "v", "hinge eye CL")
    # B-06f IMP-2 hang tab (z 985 is on the collar: measured up from the collar seam)
    cf = col["B-06f"]
    x0, y0, x1, y1 = cf.bounds(cut=False)
    cf.add_drill_hole(0.5 * (x0 + x1), y0 + (IMP2_TAB[1] - M["z_c"]), 3.0, "IMP-2 hang tab")
    for p in rs.pieces.values():
        _dedupe_notches(p)
    rs.geo["pieces_shell"] = sorted(P)
    return b, P, M, {"hiR": hiR, "mid": mid, "hiL": hiL, "zip": zipe}


def _edge_notch_at_z(p: Piece, edge, xy_of_z, zs, label):
    for z in zs:
        x, y = xy_of_z(z)
        p.add_notch(float(x), float(y), "v", label)


# ============================================================================ swells, ports, Hypalon
def build_hardpoints(rs: RevSet, fabrics: str):
    sw = BC.boxed_swell(qty=6)
    sw.piece_id, sw.name = "B-13x", "boxed fairlead swell, IM1-IM3 (with port)"
    W_, H_ = 90 + 32, 50 + 32
    _swell_marks(sw, W_, H_)
    # the slot runs along the strap's width (z): the swell's long side is z, so the slot is 45 along x of this piece
    # BL-040 m-7: the swell's slot is cut AFTER B-12 is sewn on (op 2.01), through the laser-cut B-12 slot, so it is a
    # placement mark here, not a cut-out (B-12 keeps its laser-cut slot)
    sw.add_internal_line(_rect(W_ / 2 - 22.5, H_ / 2 - 6, W_ / 2 + 22.5, H_ / 2 + 6), "placement",
                         "port slot 45 x 12: cut AFTER sewing B-12 on, through the B-12 slot", closed=True)
    sw.labels["note"] = "sew INSIDE B-01 over the IM1/IM2/IM3 windows; B-12 patch on the crest first"
    # BL-033 H-1: no hinge swell (B-13xh): the hinge cleat bears on the B-18 doubler
    rs.add(sw, "attachment", "6 swells + ports")
    w, h, sw_, sh_ = B12
    b12 = rect_panel("strap-port patch", w, h, 4.0, seam_allowance_mm=SA_LASER, material_id="tpu_coated_nylon_840d",
                     quantity=6, piece_id="B-12", labels={"note": "laser-cut; on the swell crest (outside), slot through "
                                                                "patch + swell; edge-stitch slot and perimeter; no load"})
    b12.add_internal_line(_rect((w - sw_) / 2, (h - sh_) / 2, (w + sw_) / 2, (h + sh_) / 2), "cut_inside",
                          "slot 12 x 45", closed=True)
    b12.add_internal_line(_rect(3, 3, w - 3, h - 3), "stitch", "perimeter 3 mm", closed=True)
    rs.add(b12, "attachment", "6 swells + ports")
    from huntkit.gendesign import attach_system as AS
    dp = {p.piece_id: p for p in AS.drawing_pieces()}
    b17 = rect_panel("IM3 bag-hook tab (trimmed)", B17[0], B17[1], 6.0, seam_allowance_mm=SA_LASER,
                     material_id="hypalon_coated_nylon", quantity=2, piece_id="B-17",
                     labels={"note": f"laser-cut; OUTSIDE B-01 at x +/-{STAY_X:.0f}, z {B17_Z - B17[1] / 2:.0f}-"
                                     f"{B17_Z + B17[1] / 2:.0f}; T3 tongue box-X at centre"})
    b17.add_internal_line(_rect(3, 3, B17[0] - 3, B17[1] - 3), "stitch", "perimeter row 1", closed=True)
    b17.add_internal_line(_rect(9, 9, B17[0] - 9, B17[1] - 9), "stitch", "perimeter row 2", closed=True)
    # BL-040 M-2: 34 x 34, the T3 piece / op 2.03 / load-table box (38 mm webbing less 2 mm a side); was 38 x 38
    _box_x(b17, B17[0] / 2, B17[1] / 2, 34, 34, "T3 tongue")
    rs.add(b17, "attachment", "7 Hypalon + webbing parts")
    # BL-040 B-1 DECISION HE-ONE: B-18 drawn here (attach_system's 90 x 45 piece stopped at the seam line, with a 38 x 38
    # box and rows on 4 sides): 90 x 62, its lower 12 mm in the floor seam allowance, rows on the top and both sides only
    b18 = rect_panel("hinge-eye doubler", B18_W, B18_H, 6.0, seam_allowance_mm=SA_LASER, material_id="hypalon_coated_nylon",
                     quantity=2, piece_id="B-18",
                     labels={"note": f"laser-cut; INSIDE B-01 at x +/-{STAY_X:.0f}, coated face to B-01; lower edge ON the "
                                     f"B-01 cut edge ({B18_BELOW:.0f} mm below the floor seam line, caught in the floor seam); "
                                     f"HE box-X {HE_BOX[0]:.0f}x{HE_BOX[1]:.0f}; rows top + sides only"})
    for d in (3.0, 9.0):
        b18.add_internal_line([(d, 0.0), (d, B18_H - d), (B18_W - d, B18_H - d), (B18_W - d, 0.0)], "stitch",
                              f"perimeter row {'1' if d == 3.0 else '2'} ({d:g} mm in; top + sides, bottom open)")
    b18.add_internal_line([(0.0, B18_BELOW), (B18_W, B18_BELOW)], "placement", "floor seam line (B-01 | B-05)")
    _box_x(b18, B18_W / 2, B18_BELOW + HE_BOX_GAP + HE_BOX[1] / 2, HE_BOX[0], HE_BOX[1], "HE eye")
    rs.add(b18, "attachment", "7 Hypalon + webbing parts")
    b22 = dp["B-22"]
    # BL-040 M-4: the attach_system note said OUTSIDE B-02d at the drawn x +/-149 z 752 (rev 1); state the rev 3 placement
    pl22 = rs.geo["b22"]
    b22.labels["note"] = (f"laser-cut, no seam allowance; INSIDE B-02h (the hinge band) at x +/-{pl22['placed_x']:.1f}, "
                          f"z {B22_XZ[1]:.0f}; coated face to the band")
    rs.add(b22, "attachment", "7 Hypalon + webbing parts")
    # BL-040 m-11: slot 27 x 5 (the POM toggle record's clearance for 25 mm webbing; 25 x 5 had none)
    b11 = rect_panel("lash tab", 30.0, 50.0, 4.0, seam_allowance_mm=SA_LASER, material_id="hypalon_coated_nylon",
                     quantity=8, piece_id="B-11", labels={"note": "laser-cut; slot 27 x 5; R gusset: bow riser; L gusset: "
                                                                "light lash only, NO load rating; muzzle keepers both "
                                                                "(panels.yaml B-11, released)"})
    b11.add_internal_line(_rect(1.5, 30.0, 28.5, 35.0), "cut_inside", "slot 27 x 5", closed=True)
    b11.add_internal_line([(3, 3), (27, 3), (27, 22), (3, 22)], "stitch", "sew-down box", closed=True)
    rs.add(b11, "attachment", "7 Hypalon + webbing parts")
    # B-27 facing: 50 x (slit + 2 x 10 mm), B-01 fabric
    h27 = F.guy_port()["slit_mm"] + 2 * F.PORT_END     # BL-033: the slit on the fabric (156.2), not the 150 mm dz
    b27 = rect_panel("guy port facing", F.PORT_FACING_W, h27, 0.0, seam_allowance_mm=SA_LASER,
                     material_id=_b01_mat(rs), quantity=2, piece_id="B-27f",
                     labels={"note": "B-01 fabric, hot-cut edges (laminate does not fray); INSIDE B-01 under the slit"})
    b27.add_internal_line([(PORT_LAP_IN, F.PORT_END), (PORT_LAP_IN, h27)], "placement", "slit line")
    b27.add_internal_line([(PORT_LAP_IN - 15.0, 0), (PORT_LAP_IN - 15.0, h27)], "stitch", "inboard stitch line")
    b27.add_drill_hole(PORT_LAP_IN, F.PORT_END, 3.0, "slit end bartack")
    rs.add(b27, "attachment", "5 guy ports")


def _b01_mat(rs):
    return rs.pieces["B-01"].material_id


def _swell_marks(p, W_, H_):
    for x, y in ((16, 16), (W_ - 16, 16), (W_ - 16, H_ - 16), (16, H_ - 16)):
        p.add_drill_hole(x, y, 3.0, "box corner (window corner)")
    for (x0, y0, x1, y1) in ((0, 16, 16, 16), (W_ - 16, 16, W_, 16), (0, H_ - 16, 16, H_ - 16), (W_ - 16, H_ - 16, W_, H_ - 16)):
        p.add_internal_line([(x0, y0), (x1, y1)], "fold", "box the corner")
    for e in ("bottom", "top"):
        p.add_notch_on_edge(e, 0.5, kind="v", label="CL")
    p.labels["cut"] = p.labels.get("cut", "")


# ============================================================================ pockets
def build_pockets(rs: RevSet, c, fabrics: str):
    with F.frame_face(c):
        bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    sleeve = "nylon_ripstop_70d" if fabrics == "B" else None     # lean.fell IMP-2L: the 70D tube (team B set)
    for pid_, step in (("IMP-2", "3 pockets"), ("IMP-4", "3 pockets"), ("IMP-8", "3 pockets")):
        for p in bp[pid_]["pieces"]:
            q = copy.deepcopy(p)
            if sleeve and q.piece_id == "B-09c":
                q.material_id = sleeve
            if q.piece_id == "B-09p" and not any(ln.kind == "cut_inside" for ln in q.internal_lines):
                # BL-040 m-4: the hose slot the binding frames (named 'slot 12 x 40', never drawn): laser-cut it
                x0, y0, x1, y1 = q.bounds(cut=False)
                cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
                q.add_internal_line(_rect(cx - HOSE_SLOT[0] / 2, cy - HOSE_SLOT[1] / 2, cx + HOSE_SLOT[0] / 2,
                                          cy + HOSE_SLOT[1] / 2), "cut_inside", "hose slot 12 x 40", closed=True)
            for e in q.edge_names:
                q.add_notch_on_edge(e, 0.5, kind="v", label="CL")
            rs.add(q, "pockets", step, notes=bp[pid_]["name"])
    FP = F.fp_spec()                      # BL-033: 165 mm face
    W_, H_ = FP["w"] + FP["pleat"], FP["h"]
    fpa = rect_panel("hip-reach pocket body (power mesh)", W_, H_, 0.0, seam_allowance_mm=SA_FLAT,
                     material_id="power_mesh_nylon_spandex", quantity=2, piece_id="FP-a", grain=90.0,
                     labels={"note": "stretch ACROSS; 2 box pleats; one each gusset (FP-L, FP-R)"})
    pl = FP["pleat"] / 4.0          # 2 box pleats, each 2 folds x pleat/4
    for k, xc in enumerate((W_ * 0.25, W_ * 0.75)):
        for d in (-pl, pl):
            fpa.add_internal_line([(xc + d, 0), (xc + d, 40.0)], "fold", f"box pleat {k + 1}")
        fpa.add_notch(xc - pl, 0, "slit", "pleat")
        fpa.add_notch(xc + pl, 0, "slit", "pleat")
        fpa.add_notch(xc, 0, "v", "pleat CL")
    rs.add(fpa, "pockets", "3 pockets", notes=f"corrie_f.hip_reach_pockets FP-L / FP-R ({FP['w']:.0f} mm face)")
    fpb = rect_panel("hip-reach pocket mouth band (camo)", W_, 25.0, 0.0, seam_allowance_mm=SA_FLAT,
                     material_id=F.CAMO, quantity=2, piece_id="FP-b",
                     labels={"note": "shock-cord channel; fold on the line, cord inside"})
    fpb.add_internal_line([(0, 12.5), (W_, 12.5)], "fold", "fold line")
    for e in ("bottom", "top"):
        fpb.add_notch_on_edge(e, 0.5, kind="v", label="CL")
    rs.add(fpb, "pockets", "3 pockets")
    rs.seams.append(Seam(fpa.edge("top"), fpb.edge("bottom"), name="FP body | mouth band"))
    f02 = rect_panel("fly base pocket", 190.0, 140.0, 0.0, seam_allowance_mm=10.0,
                     material_id="cordura_330d_nylon66", piece_id="F-02",
                     labels={"note": "under B-05, #5 coil zip on the floor's aft edge (panels.yaml F-02)"})
    rs.add(f02, "pockets", "3 pockets")
    # BL-033: US1/US2 floor channels B-16 on F-02's outer face (corrie_f.us_channels), across the pocket
    uc = F.us_channels(c, fabrics)
    b16 = uc["piece"]
    b16.labels["note"] = "ends turned 15 mm and left OPEN (the 25 mm under-strap passes through); topstitch both long edges"
    rs.add(b16, "pockets", "3 pockets", notes="corrie_f.us_channels")
    W2, H2 = F.F02_WH
    for k, st in enumerate(uc["stations_mm"]):
        # F-02: y 0 = its aft (zip) edge, y H2 = its frame-side edge; ASSUMPTION F02-CENTRE: the pocket is centred on the
        # floor depth, so its frame-side edge is (d0 - H2) / 2 from the floor's frame edge
        yc = H2 - (st - (uc["floor_depth_mm"] - H2) / 2)
        for d in (-uc["width_mm"] / 2, uc["width_mm"] / 2):
            f02.add_internal_line([(0.0, yc + d), (W2, yc + d)], "stitch", f"B-16 channel {'US1' if k == 0 else 'US2'} edge")
        f02.add_notch(0.0, yc, "v", f"B-16 {'US1' if k == 0 else 'US2'} CL")
        f02.add_notch(W2, yc, "v", f"B-16 {'US1' if k == 0 else 'US2'} CL")
    rs.geo["us_channels"] = {"stations_mm": uc["stations_mm"], "width_mm": uc["width_mm"]}


ADDON_TODAY = {F.UG: F.fab("body", "today"), F.R70: F.fab("collar", "today")}
# ASSUMPTION ADDON-MAP: the team B add-ons (scope pod, meat liner) are drafted in team B fabrics; the primary set maps
# them by the same role rule as the bag (ULTRAGrid -> 330D, 70D -> 100D Robic), so the primary build needs no fabric gate


def build_addons(rs: RevSet):
    ad = F._B().addons()
    import importlib
    D = importlib.import_module("D.cache")
    for grp, kit, pcs in (("add-on scope pod", "addon", ad["A1"]["pieces"]),
                          ("add-on meat liner", "meat_trip", D.modules()[0]["pieces"])):
        for p in pcs:
            q = copy.deepcopy(p)
            if rs.fabrics == "today":
                q.material_id = ADDON_TODAY.get(q.material_id, q.material_id)
            for e in q.edge_names:
                if q.seam_allowance_mm != 0.0 and q.edge_length(e) > 60.0:
                    q.add_notch_on_edge(e, 0.5, kind="v", label="CL")
            rs.add(q, grp, "12 add-ons", kit=kit)


# ============================================================================ B-29 crown lid
LID = F.LID
LID_ZIP_SPLIT = 0.5          # ASSUMPTION: the #5 zip line sits at mid-wall (15 / 15 mm finished strips); settled by
#                              the first lid (zip tape 25 mm in a 30 mm wall)
LID_DART_FRAC = 0.5          # ASSUMPTION LID-DART: dart length = half the corner meridian; settled by the first lid
#                              filled with 5.0 L of dry rice (height 85 mm, no corner pucker)
LID_CAP_LEN = 2 * LID["cap_mm"]   # 180 mm camo cap centred on each aft corner (corrie_f.LID cap_mm 90 each side)


def _se(t, W=None, D=None, n=None):
    W, D, n = W or LID["W"], D or LID["D"], n or LID["n"]
    t = np.asarray(t, float)
    return np.stack([W / 2 * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / n),
                     D / 2 * np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / n)], -1)


def _h(r):
    return LID["wall"] + LID["dome"] * np.sqrt(np.clip(1.0 - np.asarray(r) ** LID["n"], 0.0, 1.0))


_RS = 1.0 - (1.0 - np.linspace(0.0, 1.0, 400)) ** 3     # radial samples, dense at the rim (vertical tangent)


def _meridian(t):
    """3D meridian arc length from the crown top to radius r (along r * B(t)), sampled on _RS."""
    B = float(np.hypot(*_se(t)))
    rr = _RS * B
    hh = _h(_RS)
    return np.r_[0.0, np.cumsum(np.hypot(np.diff(rr), np.diff(hh)))]


def _t_of_xy(x, y):
    W, D, n = LID["W"], LID["D"], LID["n"]
    r = (abs(2 * x / W) ** n + abs(2 * y / D) ** n) ** (1 / n)
    if r < 1e-9:
        return 0.0, 0.0
    cx = (abs(x) / (r * W / 2)) ** (n / 2)
    sy = (abs(y) / (r * D / 2)) ** (n / 2)
    return math.atan2(math.copysign(sy, y), math.copysign(cx, x)), r


def _crown_flat(x, y):
    """Flat image of a crown point (plan x, y) by radial development: its distance from the crown top along the
    meridian, in the meridian's plan direction."""
    t, r = _t_of_xy(x, y)
    if r < 1e-9:
        return (0.0, 0.0)
    m = _meridian(t)
    s = float(np.interp(r, _RS, m))
    u = _se(t) / np.hypot(*_se(t))
    return (float(s * u[0]), float(s * u[1]))


def lid_draft() -> dict:
    """Draft B-29 (corrie_f.LID). Lid frame: x across the bag (+x = the wearer's right), y fore-aft (+y = aft, the
    hinge-band side), plan arc sigma measured CCW from the aft centre (t = pi/2)."""
    N = 1440
    t = np.pi / 2 + np.linspace(0.0, 2 * np.pi, N + 1)
    plan = _se(t)
    sig = np.r_[0.0, np.cumsum(np.hypot(*np.diff(plan, axis=0).T))]
    P = float(sig[-1])
    A = np.array([_meridian(tt)[-1] for tt in t])
    U = plan / np.hypot(plan[:, 0], plan[:, 1])[:, None]
    flat = A[:, None] * U
    fs = np.r_[0.0, np.cumsum(np.hypot(*np.diff(flat, axis=0).T))]
    tc = np.pi / 2 + np.pi / 4 + np.arange(4) * np.pi / 2          # corner params: aft-left, front-left, front-right, aft-right
    sc_plan = np.interp(tc, t, sig)
    centres = np.pi / 2 + np.arange(5) * np.pi / 2                  # side centres (aft, left, front, right, aft)
    s_cen_plan = np.interp(centres, t, sig)
    s_cen_flat = np.interp(centres, t, fs)
    legs = []
    for k in range(4):
        # leg before the corner: flat arc from the side centre k equals the plan arc from centre k to the corner
        want_a = sc_plan[k] - s_cen_plan[k]
        la = float(np.interp(s_cen_flat[k] + want_a, fs, t))
        want_b = s_cen_plan[k + 1] - sc_plan[k]
        lb = float(np.interp(s_cen_flat[k + 1] - want_b, fs, t))
        legs.append((la, lb))
    pf = lambda tt: (float(np.interp(tt, t, flat[:, 0])), float(np.interp(tt, t, flat[:, 1])))  # noqa: E731
    seg = lambda t0, t1: [pf(tt) for tt in np.r_[t0, t[(t > t0) & (t < t1)], t1]]           # noqa: E731
    # darts: equal legs, apex on the chord's inward normal
    darts = []
    for k, (la, lb) in enumerate(legs):
        pa, pb = np.array(pf(la)), np.array(pf(lb))
        mid = 0.5 * (pa + pb)
        mlen = float(np.interp(tc[k], t, A))
        Ld = LID_DART_FRAC * mlen
        ch_ = (pb - pa) / np.linalg.norm(pb - pa)
        nrm = np.array([-ch_[1], ch_[0]])
        if nrm @ mid > 0:                   # point the dart inward (towards the crown top)
            nrm = -nrm
        half = 0.5 * np.linalg.norm(pb - pa)
        depth = math.sqrt(max(Ld ** 2 - half ** 2, 1.0))
        apex = mid + nrm * depth
        darts.append({"a": tuple(pa), "b": tuple(pb), "apex": tuple(apex), "leg_mm": round(Ld, 1),
                      "open_mm": round(2 * half, 1)})
    edges = []
    # start at the aft centre, go CCW: aft-left half span, dart AL, left span, dart FL, front, dart FR, right, dart AR,
    # aft-right half span back to the aft centre
    edges.append(("aft_L", seg(t[0], legs[0][0])))
    for k in range(4):
        d = darts[k]
        edges.append((f"dart{k + 1}a", [d["a"], d["apex"]]))
        edges.append((f"dart{k + 1}b", [d["apex"], d["b"]]))
        nxt = legs[k + 1][0] if k < 3 else t[-1]
        edges.append(([n for n in ("left", "front", "right", "aft_R")][k], seg(legs[k][1], nxt)))
    crown = Piece.from_edges("crown lid: crown (4 corner darts)", edges,
                             seam_allowance_mm={"default": SA_BODY, **{f"dart{k}{s}": 10.0 for k in range(1, 5)
                                                                        for s in "ab"}},
                             piece_id="B-29a", grain=0.0)
    for k in range(4):
        crown.add_drill_hole(*darts[k]["apex"], 3.0, "dart apex")
    # strap channels at x = +/- CROWN_X, front to aft over the dome (radial development of the 3D line)
    ch = []
    for sx in (-1, 1):
        x = sx * F.CROWN_X
        yb = float(LID["D"] / 2 * (1 - (abs(2 * x / LID["W"])) ** LID["n"]) ** (1 / LID["n"]))
        ys = np.linspace(-yb, yb, 120)
        pts = [_crown_flat(x, y) for y in ys]
        crown.add_internal_line(pts, "placement", f"B-29g strap channel CL x {x:+.0f}")
        for d in (-LID["channel_w"] / 2, LID["channel_w"] / 2):
            crown.add_internal_line([(px + d, py) for px, py in pts], "stitch", "channel edge stitch")
        ch.append(_len(pts))
    zipL = LID["zip_mm"]
    s_zip = (zipL / 2, P - zipL / 2)            # zip ends, plan sigma (the aft run spans sigma P - 235 -> 235)
    return {"P": P, "plan": plan, "sig": sig, "t": t, "flat": flat, "fs": fs, "legs": legs, "darts": darts,
            "crown": crown, "corner_sig": [float(v) for v in sc_plan], "centre_sig": [float(v) for v in s_cen_plan],
            "channel_mm": ch, "zip_sig": s_zip, "flat_perimeter_mm": float(fs[-1])}


def build_lid(rs: RevSet, fabrics: str):
    L = lid_draft()
    P, zipL = L["P"], LID["zip_mm"]
    body, base_f = F.fab("body", fabrics), F.fab("collar", fabrics)
    crown = L["crown"]
    crown.material_id = body
    wall = LID["wall"]
    hz = wall * LID_ZIP_SPLIT
    front_len = P - zipL
    base = Piece.from_edges("crown lid: base (lies on the roll)",
                            [("perimeter", [tuple(p) for p in L["plan"]])], seam_allowance_mm=SA_BODY,
                            material_id=base_f, piece_id="B-29b", grain=0.0)
    wf = rect_panel("crown lid: front wall run", front_len, wall, 0.0, piece_id="B-29c", material_id=body,
                    seam_allowance_mm=SA_BODY, grain=0.0)
    wu = rect_panel("crown lid: aft wall, upper (zip)", zipL, wall - hz, 0.0, piece_id="B-29d", material_id=body,
                    seam_allowance_mm={"default": SA_BODY, "bottom": SA_ZIP}, grain=0.0)
    wl = rect_panel("crown lid: aft wall, lower (zip)", zipL, hz, 0.0, piece_id="B-29e", material_id=body,
                    seam_allowance_mm={"default": SA_BODY, "top": SA_ZIP}, grain=0.0)
    # caps: overlay on the lower aft strip, centred on each aft corner, clamped inside the strip (top in the zip seam,
    # bottom in the base seam, short ends turned 8 mm and topstitched)
    capL = LID_CAP_LEN
    cs = L["corner_sig"]
    aft_corners = [cs[0], cs[3] - P]             # sigma of the aft-left and aft-right corners, aft centre = 0
    cap_pos = []
    for sc in aft_corners:
        cap_pos.append(float(np.clip(sc - capL / 2, -zipL / 2, zipL / 2 - capL)))
    caps = rect_panel("crown lid: camo corner cap (overlay)", capL, hz, 0.0, piece_id="B-29f", material_id=F.CAMO,
                      quantity=2, seam_allowance_mm={"default": SA_FLAT, "top": SA_ZIP, "bottom": SA_BODY}, grain=0.0,
                      labels={"note": "print UP; laid on B-29e, caught in the zip and base seams, ends turned 8 mm"})
    chL = float(np.mean(L["channel_mm"]))
    chan = rect_panel("crown lid: strap channel", LID["channel_w"], chL, 0.0, piece_id="B-29g", material_id=body,
                      quantity=2, seam_allowance_mm={"default": SA_FLAT, "bottom": SA_BODY, "top": SA_BODY},
                      labels={"note": "long edges turned 8 mm and topstitched on the crown line; ends in the "
                                      "crown | wall seam"})
    for p in (crown, base, wf, wu, wl, caps, chan):
        rs.add(p, "lid", "11 crown lid", kit="as_hunted")
    # seams + notches. Wall ring order (sewing direction CCW, from the aft-left zip end sigma = zipL / 2):
    # front run top / bottom, then the aft strip run from sigma P - zipL/2 to P + zipL/2 (through the aft centre)
    wrap = lambda s: s % P  # noqa: E731
    sig, plan = L["sig"], L["plan"]

    def plan_run(s0, s1):
        ss = np.linspace(s0, s1, max(8, int((s1 - s0) / 3)))
        return [(float(np.interp(wrap(s), sig, plan[:, 0])), float(np.interp(wrap(s), sig, plan[:, 1]))) for s in ss]

    def crown_run(s0, s1):
        """Crown span polylines between plan sigma s0 -> s1 (darts skipped): spans equal plan arcs per half side."""
        out = []
        spans = [("aft_L", 0.0, cs[0]), ("left", cs[0], cs[1]), ("front", cs[1], cs[2]), ("right", cs[2], cs[3]),
                 ("aft_R", cs[3], P)]
        for nm, a0, a1 in spans:
            for off in (0.0, P):
                lo, hi = max(s0, a0 + off), min(s1, a1 + off)
                if hi - lo > 1e-6:
                    pts = crown.edge_points(nm)
                    Ls = _len(pts)
                    u0, u1 = (lo - a0 - off) / (a1 - a0) * Ls, (hi - a0 - off) / (a1 - a0) * Ls
                    k = np.linspace(u0, u1, max(6, int((u1 - u0) / 3)))
                    out.append((crown, [_pt_at(pts, v) for v in k]))
        return out

    z0, z1 = zipL / 2, P - zipL / 2
    wall_top = [(wf, wf.edge_points("top")[::-1]), (wu, wu.edge_points("top")[::-1])]
    wall_bot = [(wf, wf.edge_points("bottom")), (wl, wl.edge_points("bottom"))]
    crown_side = crown_run(z0, P) + crown_run(0.0, z0)
    base_side = [(base, plan_run(z0, z1)), (base, plan_run(z1, P + z0))]
    rs.seams += [
        Seam(_v_side("lid wall top", wall_top), _v_side("lid crown spans", crown_side), name="B-29 crown | wall (ring)"),
        Seam(_v_side("lid wall bottom", wall_bot), _v_side("lid base", base_side), name="B-29 wall | base (ring)"),
        Seam(wf.edge("right"), [wu.edge("left"), wl.edge("left")], name="B-29 wall closing L (front | aft)"),
        Seam(wf.edge("left"), [wu.edge("right"), wl.edge("right")], name="B-29 wall closing R (front | aft)"),
        Seam(wu.edge("bottom"), wl.edge("top"), name="B-29 aft wall #5 zip (upper | lower)"),
        Seam(chan.edge("left"), _v_side("crown channel line", [(crown, crown.internal_lines[-3].points)]),
             name="B-29g channel | crown line"),
    ]
    for k in range(1, 5):
        rs.seams.append(Seam(crown.edge(f"dart{k}a"), crown.edge(f"dart{k}b").reversed(), name=f"B-29a dart {k}"))
    notch_pair(wall_top, crown_side, "crown|wall")
    notch_pair(wall_bot, base_side, "wall|base")
    # extra marks: corners and side centres on the walls (match the darts / base corners)
    for s_ in L["corner_sig"] + L["centre_sig"][:4]:
        ss = (s_ - z0) % P
        _notch_on_side(wall_bot, ss, "corner / centre", "v")
        _notch_on_side(base_side, ss, "corner / centre", "v")
    for k, c0 in enumerate(cap_pos):
        x0 = c0 + zipL / 2
        wl.add_internal_line(_rect(x0, 0, x0 + capL, hz), "placement", "B-29f camo cap", closed=True)
        wl.add_notch(x0, 0, "slit", "cap end")
        wl.add_notch(x0 + capL, 0, "slit", "cap end")
    for p in (wu, wl):
        p.add_drill_hole(4.0, (wall - hz) / 2 if p is wu else hz / 2, 3.0, "zip stop")
        p.add_drill_hole(zipL - 4.0, (wall - hz) / 2 if p is wu else hz / 2, 3.0, "zip stop")
    for p in (crown, base, wf, wu, wl):
        _dedupe_notches(p)
    rs.lid = {"perimeter_mm": round(P, 1), "flat_crown_perimeter_mm": round(L["flat_perimeter_mm"], 1),
              "darts": L["darts"], "channel_mm": [round(v, 1) for v in L["channel_mm"]],
              "channel_3d_mm": F.lid_geometry()["channel_run_mm"], "front_run_mm": round(front_len, 1),
              "cap_start_sigma_mm": [round(v, 1) for v in cap_pos], "zip_line_mm": hz,
              "corner_sigma_mm": [round(v, 1) for v in L["corner_sig"]]}
    return L


def lid_hours_ops(rs: RevSet | None = None) -> dict:
    """BL-030's seam list (corrie_f.lid_seam_list) re-run on the DRAFTED B-29: lengths and counts from the pieces,
    the same bag_concepts.HOURS rates. Adds the four crown darts the drafted dome needs (HOURS 'dart'). With no RevSet
    the lid alone is drafted (corrie_f.lid_hours_drafted books this total)."""
    if rs is None:
        rs = RevSet(fabrics="B")
        build_lid(rs, "B")
    H = BC.HOURS
    p = {k: rs.pieces[k] for k in ("B-29a", "B-29b", "B-29c", "B-29d", "B-29e", "B-29f", "B-29g")}
    ncut = sum(q.quantity for q in p.values())
    per = rs.lid["perimeter_mm"] / 1000.0
    ch = float(np.mean(rs.lid["channel_mm"])) / 1000.0
    zip_m = p["B-29d"].edge_length("bottom") / 1000.0
    close_h = p["B-29c"].edge_length("right") / 1000.0
    cap_ends = 2 * 2 * p["B-29f"].edge_length("left") / 1000.0        # 2 caps x 2 short ends
    ops = [
        (f"cut, mark, notch {ncut} pieces (crown, base, front run, aft upper + lower, 2 caps, 2 channels)", ncut,
         H["cut_piece"]),
        ("4 crown darts sewn + pressed", 4, H["dart"]),
        ("strap channels topstitched to the crown, both edges (2 x 2 runs)", 4 * ch, H["straight_m"]),
        ("bartacks at the 4 channel ends", 4, H["bartack"]),
        ("camo caps: short ends turned and topstitched (2 x 2)", cap_ends, H["applique_m"]),
        ("#5 coil zip: tape baste, stops, slider", 1, H["zip_fixed"]),
        ("#5 coil zip sewn, both tapes", zip_m, H["zip_m"]),
        ("zip round the two aft corners", 2, H["zip_corner"]),
        ("wall ring closed: two short seams", 2 * close_h, H["straight_m"]),
        ("crown | wall perimeter (curved, notch match, bind)", per, H["curved_m"]),
        ("crown | wall: closed ring handling", 1, H["ring"]),
        ("wall | base perimeter (curved, notch match, bind), turned through the zip", per, H["curved_m"]),
        ("wall | base: closed ring handling", 1, H["ring"]),
    ]
    rows = [{"op": n, "qty": round(q, 3), "rate_h": r, "hours": round(q * r, 2)} for n, q, r in ops]
    return {"rows": rows, "hours": round(sum(q * r for _, q, r in ops), 2), "pieces_cut": ncut}


def lid_hours(rs: RevSet) -> dict:
    """``lid_hours_ops`` against BL-030's seam-list estimate and BL-029's one-line estimate."""
    o = lid_hours_ops(rs)
    sl = F.lid_seam_list()
    tot = o["hours"]
    return {**o, "bl030_h": sl["hours"], "bl029_booked_h": sl["bl029_estimate_h"],
            "delta_vs_bl030_h": round(tot - sl["hours"], 2), "delta_vs_booked_h": round(tot - sl["bl029_estimate_h"], 2),
            "booked_now_h": F.crown_lid()["hours"], "bl030_pieces": sl["pieces"]}


# ============================================================================ webbing (hot-knife pieces)
def _web(rs, pid, name, length, qty, mat="poly_webbing_25mm", folds=(), boxes=(), note="", group="webbing",
         step="13 straps + webbing", kit="base", source="", graded=None, box_w=None):
    w = 38.0 if mat == "poly_webbing_38mm" else 25.0
    p = rect_panel(name, w, float(length), 0.0, seam_allowance_mm=0.0, material_id=mat, quantity=qty, piece_id=pid,
                   labels={"note": ("hot-knife cut; " + note).rstrip("; ")})
    for y, lab in folds:
        p.add_internal_line([(0, y), (w, y)], "fold", lab)
    for y, hb, lab in boxes:
        _box_x(p, w / 2, y, box_w or (w - 4), hb, lab)      # BL-041: B-25 keeps its 21 x 15 box on 38 mm (structural)
    if graded is None:
        rs.add(p, group, step, kit=kit, notes=source)
    rs.webbing.append({"id": pid, "use": name, "material_id": mat, "length_mm": round(float(length), 1), "qty": qty,
                       "kit": kit, "source": source})
    return p


IM_LOOP = 60.0         # strap_tails / mfg IM-BOX: 60 mm end-loop fold
IMC_FOLD_BL041 = 45.0  # BL-041 IM-CAM-TAB: 45 mm folds, box 2 mm from the raw end (review 3 m-4)
IMC_LOOP = 18.0        # ASSUMPTION IMC-LOOP: 25 mm cam and G-hook bars pass an 18 mm clear loop; settled by threading the
#                        bought cam and hook on the first tab
IMC_TIP_GAP = 5.0      # BL-043 m-4: box edge 5 mm in from each raw end (as RTM / LLT), not 2
IMC_FOLD = IMC_LOOP + 25.0 + IMC_TIP_GAP   # 48: loop 18 + 21 x 25 box + 5 mm to the raw end; cut 4 x 48 = 192 mm
US_EYE = 50.0          # ASSUMPTION US-EYE: 50 mm eye fold round the left pin's UHMWPE sleeve (the HE eye fold); settled
#                        by the MT-1 specimens, sewn this way
B25_BOX = (21.0, 15.0)  # DECISION B25-BOX (BL-034): 21 x 15 at the tip end of the 2 x 30 tab leaves a 13 mm clear loop,
#                        the least that passes the 30 x 8 x 5 POM toggle (2 x (8 + 5) = 26 mm perimeter); a 21 x 20 box
#                        leaves 8 mm (no pass). attach_system.box_x 2504 N against the 288 N guy load (SF 8.7)
BOX_TIP_GAP = 2.0      # box edge 2 mm from the folded tip (heat-sealed end)


# BL-044 (BL-045 imus_eye_envelope): every eye on an IM / US pin is necked to 18 mm where it passes the 20 mm throat, as
# the HE (op 4.05): the 38 mm IME with each edge folded 10 mm in, the 25 mm US eye and US cam anchor with each edge
# folded 3.5 mm in. Neck spans on the flat strip (the free loop between its box and the fold, both legs):
IME_NECK_EDGE = 10.0
US_NECK_EDGE = 3.5
IME_NECK = (45.0, 155.0)           # IME: box 155-185 (and 15-45 on the other leg) -> free loop 45..155 round the fold at 100
US_NECK = (100.0 - (2 * US_EYE - BOX_TIP_GAP - 25.0), 2 * US_EYE - BOX_TIP_GAP - 25.0)   # US: tail and strap between box and fold
# USA pin loop: BL-044 imus_stl_check. With the IMC's 18 mm loop the 25 mm box sits 8.9 mm from the pin, 1.3 mm in
# front of the cheek tips, and the printed US cheeks cut it at any pull steeper than 15 deg off +y (sliced: US1 / US2 R,
# overlap 0.5-37 mm2 at -30..-90 deg). DECISION USA-LOOP: the pin loop is the US eye's (fold to box edge US_EYE -
# BOX_TIP_GAP - 25 = 23 mm): box 14.5 mm from the pin, the same clear pull range as the left eye (-60..+45 deg).
USA_PIN_LOOP = US_EYE - BOX_TIP_GAP - 25.0                                  # 23
USA_PIN_FOLD = USA_PIN_LOOP + 25.0 + IMC_TIP_GAP                            # 53 (cam end keeps IMC_FOLD 48)
USA_CUT = 2.0 * USA_PIN_FOLD + 2.0 * IMC_FOLD                               # 202 (BL-044 first draw: 192)
USA_NECK = (USA_PIN_FOLD - USA_PIN_LOOP, USA_PIN_FOLD + USA_PIN_LOOP)         # pin loop 30..76 round the fold at 53


def _neck(p, w, edge, span, tack=4.0):
    """Neck lines, fold-in lines and one BT-M tack per leg on a flat webbing piece (BL-044, as op 4.05's HE neck)."""
    y0, y1 = span
    for y in (y0, y1):
        p.add_internal_line([(0, y), (w, y)], "placement", "neck line")
    for x in (edge, w - edge):
        p.add_internal_line([(x, y0), (x, y1)], "fold", "neck: fold the edge in to this line")
    for y in (y0 + tack, y1 - tack):
        p.add_internal_line([(edge + 1, y), (w - edge - 1, y)], "stitch", "neck tack BT-M (one per leg)")


def _tip_box_y(fold, h):
    """Flat y of a box sewn in the doubled zone of an end folded at ``fold`` (tip lands at 2 x fold), its edge
    BOX_TIP_GAP from the tip: leaves the largest loop at the fold."""
    return 2 * fold - BOX_TIP_GAP - h / 2


def build_webbing(rs: RevSet, c):
    import strap_tails as ST
    import attach_diet as AD  # noqa: F401  (TOGGLE_G is booked as hardware)
    from huntkit.gendesign import attach_system as AS  # noqa: F811
    # B-28 crown straps per crown kit (BL-031): cut, a 60 mm tab per lock + the B-25 second fold
    g = {}
    for k in CROWN_KITS:
        cs = F.crown_kit_straps(k)
        p = rect_panel(f"B-28 crown strap kit {k}", 25.0, float(cs["cut_mm"]), 0.0, seam_allowance_mm=0.0,
                       material_id="poly_webbing_25mm", quantity=2, piece_id="B-28", size=k,
                       labels={"note": f"hot-knife; torso {cs['torso_in'][0]}-{cs['torso_in'][1]} in; heavy ladder "
                                       "lock each end on its tab; 2 elastic keepers"})
        p.add_internal_line([(0, F.TAIL_GRIP_MM), (25, F.TAIL_GRIP_MM)], "placement", "grip tail mark (each end)")
        p.add_internal_line([(0, cs["cut_mm"] - F.TAIL_GRIP_MM), (25, cs["cut_mm"] - F.TAIL_GRIP_MM)], "placement",
                            "grip tail mark")
        g[k] = p
        rs.webbing.append({"id": "B-28", "use": f"B-28 crown strap, kit {k}", "material_id": "poly_webbing_25mm",
                           "length_mm": round(cs["cut_mm"], 1), "qty": 2, "kit": f"crown kit {k} (as hunted)",
                           "source": "corrie_f.crown_kit_straps"})
    base = copy.deepcopy(g[KIT])
    base.size = KIT
    rs.add(base, "webbing", "13 straps + webbing", kit="as_hunted", notes="graded per crown kit S / M / L")
    rs.graded["B-28"] = g
    # BL-035: B-28t split. The two lock tabs per strap (front on the hinge band, rear carrying the POM toggle) keep the
    # 21 x 20 box (B28-FACE); the third tab, the B-25 second fold the rear toggle passes into, is its own piece B-28s
    # with the B25-BOX rule: 21 x 15 at the tip end leaves the 13 mm loop the 30 x 8 x 5 toggle needs (a 21 x 20 box
    # at 0.75 x tab left 5 mm: the toggle did not pass).
    _web(rs, "B-28t", "lock tab", F.CROWN_TAB, 4,
         folds=[(F.CROWN_TAB / 2, "fold round the lock bar")],
         boxes=[(F.CROWN_TAB * 0.75, B28_BOX[1], "box-X")], kit="as_hunted",
         note="B-28 front + rear lock tabs; front: OUTSIDE the hinge band; rear: POM toggle sewn across the tip",
         source="corrie_f.CROWN_TAB, 2 per strap (front + rear lock)")
    _web(rs, "B-28s", "toggle loop", F.CROWN_TAB, 2,
         folds=[(F.CROWN_TAB / 2, "fold: toggle loop")],
         boxes=[(_tip_box_y(F.CROWN_TAB / 2, B25_BOX[1]), B25_BOX[1], "box-X 21x15 tip")], kit="as_hunted",
         note="B-28 toggle loop = the B-25 second fold, sewn on the B-25 tab; 13 mm loop passes the POM toggle (B25-BOX)",
         source="corrie_f.CROWN_TAB, 1 per strap (the B-25 second fold)")
    _web(rs, "K-28", "B-28 tail keeper (25 mm elastic loop)", KEEPER_CUT, 4, mat=ELASTIC,
         folds=[(15.0, "lap 15 mm, zigzag")], kit="as_hunted", source="corrie_f.crown_kit_straps keepers_per_strap x 2")
    # W1-W3 cut for carry + meat-trip haul extenders (strap_tails.wrap_rows, kit M; W3 per kit)
    for r in ST.wrap_rows(KIT):
        if r["id"] == "W3":
            gw = {}
            for k in CROWN_KITS:
                rk = [x for x in ST.wrap_rows(k) if x["id"] == "W3"][0]
                q = rect_panel(f"haul wrap W3 kit {k}", 25.0, float(rk["after"]["cut_mm"]), 0.0, seam_allowance_mm=0.0,
                               material_id="poly_webbing_25mm", quantity=1, piece_id="W3", size=k,
                               labels={"note": "hot-knife; G-hook end folded 2 x 30 and box-X'd; ladder lock on the "
                                               "gusset side"})
                q.add_internal_line([(0, 30), (25, 30)], "fold", "G-hook fold")
                _box_x(q, 12.5, 45.0, 21.0, 25.0, "G-hook end")      # BL-034: W3-BOX drawn (as W1 / W2)
                gw[k] = q
                rs.webbing.append({"id": "W3", "use": f"haul wrap W3, kit {k}", "material_id": "poly_webbing_25mm",
                                   "length_mm": round(rk["after"]["cut_mm"], 1), "qty": 1, "kit": f"crown kit {k}",
                                   "source": "strap_tails.wrap_rows"})
            b3 = copy.deepcopy(gw[KIT])
            rs.add(b3, "webbing", "13 straps + webbing", notes="per crown kit")
            rs.graded["W3"] = gw
        else:
            _web(rs, r["id"], f"haul wrap {r['id']} (cut for carry)", r["after"]["cut_mm"], 1,
                 folds=[(30.0, "G-hook fold")], boxes=[(45.0, 25, "box-X")], source="strap_tails.wrap_rows")
        ext = r["haul"]["extender_mm"]
    _web(rs, "WX", "W haul extender (meat-trip kit)", ext, 3,
         folds=[(30.0, "G-hook fold"), (ext - 60.0, "sewn loop fold (takes the W's own G-hook)")],
         boxes=[(45.0, 25, "box-X hook end"), (ext - 30.0, 25, "box-X loop")], kit="meat_trip",
         note="rated 25 mm G-hook on the hook end", source="strap_tails.wrap_rows haul extender_mm")
    _web(rs, "K-W", f"W gore keeper loop ({2 * len(KW_WRAPS)}, in the aft corner seams: W1, W2)", KW_CUT,
         2 * len(KW_WRAPS), folds=[(KW_CUT / 2, "fold, raw ends in the seam")],
         source="ledger 'keepers: 6 haul-wrap keeper loops' (ASSUMPTION 80 mm cut) less the 2 W3 loops (BL-044 "
                "DECISION KW-W3-OFF row)")
    rr = ST.roll_row()
    # BL-040 B-2: the RT end (0-60 mm) is box-X'd on the hem B-07 at its drawn 'RT roll-clip strap' placement; the free
    # end threads the adjustable (male) half of the side-release buckle, whose female half is on the RTM gusset tab
    _web(rs, "RT", "roll-top side clip strap", rr["after"]["cut_mm"], 2,
         folds=[(RT_SEWN, "end of the sewn zone (60 mm on the hem)")],
         boxes=[(RT_SEWN / 2, RT_BOX[0], "box-X to the hem B-07")],
         note="free end through the ADJUSTABLE (male) buckle half; tail keeper K-RT below the buckle",
         source="strap_tails.roll_row")
    _web(rs, "RTM", "roll-clip buckle tab on the gusset (female half)", RTM_CUT, 2,
         folds=[(RTM_FOLD, "fold round the buckle's female-half bar")],
         boxes=[(RTM_CUT * 0.75, RTM_BOX[1], "box-X through RTM + B-03")],
         note="one per gusset, flat work before the gusset seams (BL-040 B-2); on the BL-041 clip path",
         source="BL-040 DECISION RT-MATE (LLT tab rule); BL-041 RT-FWD placement (rt_layout)")
    # BL-043 DECISION W3-OVER: the BL-041 W3G guides (2 x 60 mm, two unrated BT-S tacks each) are deleted
    _web(rs, "K-RT", "roll clip tail keeper (25 mm elastic)", KEEPER_CUT, 2, mat=ELASTIC,
         folds=[(15.0, "lap 15 mm, zigzag")], source="BL-031")
    for r in ST.im_rows():
        _web(rs, r["id"], f"internal meat strap {r['id']}", r["after"]["cut_mm"], 1,
             folds=[(IM_LOOP, "left end loop (girth-hitched on the eye)")],
             boxes=[(_tip_box_y(IM_LOOP, 25.0), 25.0, "end loop (MT-1)")], source="strap_tails.im_rows (unchanged)")
    # BL-041 m-19 / n-15 DECISION IM-CAM-TAB: each IM strap's cam gets a SEWN anchor on the rated path. IMC = a 25 mm
    # dog-bone: one end folded round the cam's anchor bar, the other round the G-hook bar (IM1 / IM2) or into a
    # carabiner loop (IM3), each closed by a 21 x 25 box at the tip end (the IM end-loop box, MT-1). Path: left eye <-
    # girth-hitched IM loop - IM strap - through the cam - cam bar = IMC = hook / carabiner -> right eye (SK-11).
    _web(rs, "IMC", "IM cam anchor tab (cam bar <-> hook / carabiner)", 4.0 * IMC_FOLD, 3,
         folds=[(IMC_FOLD, "fold round the CAM anchor bar"), (3.0 * IMC_FOLD, "fold round the G-hook bar / carabiner")],
         boxes=[(IMC_FOLD + IMC_LOOP + 12.5, 25.0, "cam end box-X (MT-1)"),
                (3.0 * IMC_FOLD - IMC_LOOP - 12.5, 25.0, "hook end box-X (MT-1)")],
         note=f"one per IM strap; both raw ends meet in the middle; clear loop {IMC_LOOP:.0f} mm each end; each box "
              f"{IMC_TIP_GAP:.0f} mm in from its raw end (BL-043 m-4)",
         source="BL-041 DECISION IM-CAM-TAB (review m-19 / n-15: the cam had no sewn anchor)")
    _web(rs, "K-IM", "IM tail keeper (25 mm elastic)", KEEPER_CUT, 3, mat=ELASTIC, folds=[(15.0, "lap 15 mm")],
         source="BL-031")
    ime = _web(rs, "IME", "IM fairlead eye (38 mm)", 200.0, 6, mat="poly_webbing_38mm", folds=[(100.0, "fold (eye)")],
               boxes=[(170.0, 30, "box-X")], source="ledger IM-eyes 6 x 0.20 m",
               note=f"neck: long edges folded {IME_NECK_EDGE:.0f} mm in between the neck lines, one BT-M per leg, sewn "
                    "flat BEFORE the fold (BL-044, bag_attach.imus_eye_envelope)")
    _neck(ime, 38.0, IME_NECK_EDGE, IME_NECK)
    us = _web(rs, "US", "under-strap US1 / US2", 550.0, 2, folds=[(US_EYE, "eye fold (round the left pin)")],
              boxes=[(_tip_box_y(US_EYE, 25.0), 25.0, "sewn eye (MT-1)")], source="ledger US-web 1.10 m",
              note=f"eye neck: long edges folded {US_NECK_EDGE:.1f} mm in between the neck lines (BL-044)")
    _neck(us, 25.0, US_NECK_EDGE, US_NECK)
    # BL-044 (BL-045 found-not-fixed): the US cam on the RIGHT pin had no drawn anchor (BOM 'US-anchor' only). USA = a
    # 25 mm dog-bone as IMC: one loop round the right pin (necked to 18 mm where it passes the throat), the
    # other round the US cam's anchor bar, each closed by a 21 x 25 box. Path: left eye (US) - US strap - cam - cam bar
    # = USA = right pin.
    usa = _web(rs, "USA", "US cam anchor (right pin <-> cam bar)", USA_CUT, 2,
               folds=[(USA_PIN_FOLD, "fold round the RIGHT PIN"), (USA_CUT - IMC_FOLD, "fold round the CAM anchor bar")],
               boxes=[(USA_PIN_FOLD + USA_PIN_LOOP + 12.5, 25.0, "pin end box-X (MT-1)"),
                      (USA_CUT - IMC_FOLD - IMC_LOOP - 12.5, 25.0, "cam end box-X (MT-1)")],
               note=f"one per under-strap; both raw ends meet in the middle; pin loop {USA_PIN_LOOP:.0f} mm clear, necked "
                    f"to 18 mm (edges folded {US_NECK_EDGE:.1f} mm in; DECISION USA-LOOP); cam loop {IMC_LOOP:.0f} mm",
               source="BL-044 (BL-045: the US cam had no sewn anchor); IMC construction")
    _neck(usa, 25.0, US_NECK_EDGE, USA_NECK)
    # BL-034: B-24 drawn by attach_system.link_piece (folds at the real loop stations, hook box + 3 loop boxes 34 x 20)
    lk = AS.link_piece()
    # BL-040 m-15: the attach_system note still names a 'rated 38 mm hook'; BL-010 made the hook end a wiregate carabiner
    lk.labels["note"] = ("hot-knife cut; " + lk.labels.get("note", "")).replace(
        "rated 38 mm hook (same part as the bag hooks)", "wiregate carabiner (carabiner_wiregate_22kn, as the IM3 bag hook)")
    rs.add(lk, "webbing", "13 straps + webbing", kit="meat_trip", notes="attach_system.link_piece (meat_haul.LINK)")
    rs.webbing.append({"id": "B-24", "use": "float stand-off link (38 mm, meat-trip)", "material_id": "poly_webbing_38mm",
                       "length_mm": round(lk.edge_length("left"), 1), "qty": lk.quantity, "kit": "meat_trip",
                       "source": "attach_system.link_piece; ledger B-24-web 2 x 435 mm"})
    # BL-040 B-1 DECISION HE-ONE: folded in half; both legs carry the box (they lie on top of each other once folded)
    yb = B18_BELOW + HE_BOX_GAP + HE_BOX[1] / 2               # box centre from a raw end (raw end = B-01 cut edge)
    neck0, neck1 = B18_BELOW + HE_BOX_GAP + HE_BOX[1], HE_CUT - (B18_BELOW + HE_BOX_GAP + HE_BOX[1])
    he = _web(rs, "HE", "hinge eye (38 mm)", HE_CUT, 2, mat="poly_webbing_38mm",
              folds=[(HE_FOLD, "EYE FOLD: fold in half here")],
              boxes=[(yb, HE_BOX[1], "box-X through HE (2 plies) + B-01 + B-18 (leg A)"),
                     (HE_CUT - yb, HE_BOX[1], "box-X (leg B, same box once folded)")],
              note=f"fold in half at {HE_FOLD:.0f} mm, both raw ends to the B-01 cut edge; neck: long edges folded "
                   f"{HE_NECK_EDGE:.0f} mm in between the neck lines, one BT-M per leg, sewn flat BEFORE the fold; "
                   f"eye {HE_EYE:.0f} mm points UP onto the z 60 pin (HE-PIN / HE-ENV)",
              source=f"BL-040 DECISION HE-ONE + BL-041 HE-PIN + BL-044 DECISION HE-ENV (cut 38 x {HE_CUT:.0f}; eye solved by "
                     "he_geometry on bag_attach.HINGE_EYE_ENVELOPE)")
    for y in (B18_BELOW, HE_CUT - B18_BELOW):
        he.add_internal_line([(0, y), (HE_W, y)], "placement", "floor seam line (raw end below it goes in the seam)")
    for y in (neck0, neck1):
        he.add_internal_line([(0, y), (HE_W, y)], "placement", "neck line")
    for x in (HE_NECK_EDGE, HE_W - HE_NECK_EDGE):
        he.add_internal_line([(x, neck0), (x, neck1)], "fold", "neck: fold the edge in to this line")
    for y in (neck0 + HE_TACK_ABOVE_BOX, neck1 - HE_TACK_ABOVE_BOX):
        he.add_internal_line([(HE_NECK_EDGE + 1, y), (HE_W - HE_NECK_EDGE - 1, y)], "stitch", "neck tack BT-M (one per leg)")
    g = he_geometry()
    br = he_bracket(HE_EYE)
    pins = [r["pin_z"] for r in br]
    band = he_band()
    pl = he_peel()
    E = g["env"]
    rs.geo["he"] = {"cut": HE_CUT, "fold": HE_FOLD, "box": HE_BOX, "box_z_above_seam": (HE_BOX_GAP, HE_BOX_GAP + HE_BOX[1]),
                    "eye_mm": HE_FOLD - B18_BELOW - HE_BOX_GAP - HE_BOX[1], "neck_w": HE_NECK_W,
                    "neck_w_max": HE_NECK_W + HE_NECK_TOL,
                    "b18": (B18_W, B18_H), "b18_below_seam": B18_BELOW,
                    # BL-044 HE-ENV: where the eye sits on the BL-042 hinge fairlead (heights above the floor seam line)
                    "pin_target_z": g["pin_z"], "pin_z_design": round(he_pin_z(HE_EYE), 2),
                    "pin_z_range": (round(min(pins), 2), round(max(pins), 2)), "pin_band": band,
                    "bracket": br, "t_range": HE_T_RANGE,
                    "cheek_z": (g["cheek_lo"], g["cheek_hi"]), "cheek_clear": round(g["cheek_lo"] - HE_BOX_GAP - HE_BOX[1], 2),
                    "cheek_clear_min": round(min(pins) - E["cheek_half_z_mm"] - (HE_BOX_GAP + HE_BOX[1]), 2),
                    "fold_z_flat": HE_BOX_GAP + HE_BOX[1] + HE_EYE, "throat": g["throat"],
                    "throat_clear_side_min": round((g["throat"] - HE_NECK_W - HE_NECK_TOL) / 2, 2),
                    "gap_under_pin": g["gap_under_pin"],
                    "wrap_t": {"design": HE_T * (1 + HE_NF_DESIGN), "max": HE_T_RANGE[1] * (1 + HE_NF_DESIGN)},
                    "wrap_clear_min": round(g["gap_under_pin"] - HE_T_RANGE[1] * (1 + HE_NF_DESIGN), 2),
                    "face_inline": round(g["face_inline"], 2), "faces_y": g["faces_y"], "pin_y": g["pin_y"],
                    "peel": pl,
                    # the open eye's footprint on B-01 / B-18 (x about the eye CL, z above the seam line): no stitch
                    # row sewn after the HE is placed may cross it (X-1)
                    "eye_footprint": (-HE_W / 2, HE_BOX_GAP + HE_BOX[1], HE_W / 2, HE_BOX_GAP + HE_BOX[1] + HE_EYE)}
    _web(rs, "T3", "IM3 bag-hook tongue (38 mm)", 160.0, 2, mat="poly_webbing_38mm",
         folds=[(45.0, "fold round the hook bed")], boxes=[(22.0, 30, "loop box-X"), (130.0, 34, "box-X to B-17")],
         source="attach_system.drawing_pieces T2/T3 (IM2 hooks removed by BL-004: 2 left)")
    gb = F.guy_bridle(wide=True)    # BL-041 (crown_tube_guy_loop.md 8.1): 38 mm, sleeves x 26.5-64.5
    tp = F.b25_topology()           # BL-043 M-4 DECISION B25-TOPO: sleeve | mitre | necked run | spine wrap
    rs.geo["b25"] = {k: gb[k] for k in ("width_mm", "band", "sleeve_x", "clear_to_clamp_mm")}
    rs.geo["b25"].update(length_mm=tp["cut_mm"], length_bl041_mm=gb["length_mm"], clamp_half=F.SPINE_CLAMP_HALF,
                         min_clear=F.MIN_CLEAR_MM, mass_g=round(tp["cut_mm"] * gb["mass_g"] / gb["length_mm"], 2),
                         topology=tp)
    # B25-LAYOUT (BL-034) + B25-TOPO (BL-043), from the R end: tab | sleeve | drop | MITRE | run (neck from the band
    # edge) | half spine wrap | (centre) | mirror. Each end tab folds 2 x 30 into the toggle loop (B25-BOX).
    Lb, tb, bw = tp["cut_mm"], F.BRIDLE_TAB_MM, tp["lengths_mm"]["sleeve"]
    lm = tp["lengths_mm"]
    y_m = tb + bw + lm["drop"]                                   # mitre centre (strip centre line)
    y_n = y_m + (0.5 * sum(tp["band_x"]) - tp["band_x"][0])      # the band's inboard edge: the neck starts here
    w38 = tp["width_mm"]
    q = _web(rs, "B-25", "guy bridle on the crown top bar (38 mm, BL-041 / BL-043 topology)", Lb, 1, mat=gb["material_id"],
             folds=[(tb / 2, "tab fold R (toggle loop)"), (tb, "bar sleeve R start"),
                    (tb + bw, "bar sleeve R lap (bartack); leaves the bar DOWN, aft side"),
                    (Lb / 2, "spine wrap centre (round the spine)"),
                    (Lb - tb - bw, "bar sleeve L lap (bartack)"), (Lb - tb, "bar sleeve L start"),
                    (Lb - tb / 2, "tab fold L (toggle loop)")],
             boxes=[(_tip_box_y(tb / 2, B25_BOX[1]), B25_BOX[1], "toggle tab R"),
                    (Lb - _tip_box_y(tb / 2, B25_BOX[1]), B25_BOX[1], "toggle tab L")], box_w=B25_BOX[0],
             note=f"fitted on the bar before the crown corners are bonded; sleeves x {gb['band'][0]}-{gb['band'][1]} each "
                  f"side ({gb['clear_to_clamp_mm']} mm clear of the spine clamp); toggle tab at the sleeve centre x "
                  f"{gb['sleeve_x']} (DECISION B25-TAB-CENTRE); 45 deg MITRE under each sleeve, run + spine wrap NECKED to "
                  f"{tp['neck_w_mm']:.0f} mm (DECISION B25-TOPO, SK-12); box {B25_BOX[0]:.0f} x {B25_BOX[1]:.0f} on 38 mm is "
                  "the B25-BOX exception (8.5 mm unsewn each edge: the box must leave the 13 mm toggle loop; SK-1)",
             source="corrie_f.b25_topology (BL-043 B25-TOPO) on corrie_f.guy_bridle(wide=True) (crown_tube_guy_loop.md 5, 8.1)")
    for ym, side in ((y_m, "R"), (Lb - y_m, "L")):
        sg = 1.0 if side == "R" else -1.0
        q.add_internal_line([(0.0, ym - sg * w38 / 2), (w38, ym + sg * w38 / 2)], "fold",
                            f"MITRE {side}: 45 deg fold, turns the strip 90 deg inboard (under the sleeve)")
    neck = w38 - tp["neck_w_mm"]
    q.add_internal_line([(neck, y_n), (neck, Lb - y_n)], "fold",
                        f"NECK: fold the lower {neck:.0f} mm (x 0 edge = lower edge) up between the two band-edge marks")
    for yy in (y_n, Lb - y_n):
        q.add_internal_line([(0.0, yy), (w38, yy)], "placement", "sleeve band inboard edge (neck starts)")
    rs.geo["b25"]["flat"] = {"mitre_y": round(y_m, 1), "neck_y": round(y_n, 1), "centre_y": round(Lb / 2, 1)}
    _web(rs, "TG", "port guy (B-25 toggle -> B-27 port -> B-22 inside)", AS.GUY["cut_mm"], 2,
         boxes=[(20.0, 25, "toggle loop box-X")], note="free end through the heavy ladder lock; heat-seal",
         source="attach_system.GUY cut_mm")
    _web(rs, "LLT", "guy ladder-lock tab on B-22", 70.0, 2, folds=[(35.0, "fold round the lock bar")],
         boxes=[(52.0, LLT_BOX[1], "box-X through B-22 + B-02h")], source="attach_system.drawing_pieces LLT")
    _web(rs, "K-G", "guy tail keeper (25 mm elastic)", KEEPER_CUT, 2, mat=ELASTIC, folds=[(15.0, "lap 15 mm")],
         source="ledger 'guy tail elastic keepers x2'")
    # BL-041: GBL deleted. Rev 1+ toggles the guy into the B-25 tab; the 25 mm guy bar loop carried nothing in rev 3
    # (crown_tube_guy_loop.md 8.2). Its POM toggle is the guy's own toggle and stays (ledger row unchanged).
    _web(rs, "HPL", "scope-pod hard-point loop", F.LOOP_M * 1000.0, 4, folds=[(40.0, "fold, raw ends in the seam")],
         source="corrie_f.LOOP_M")
    _web(rs, "E5", "pole grip tab (cord lock)", F._A().POLE["tab_m"] * 1000.0, 1, folds=[(30.0, "fold")],
         source="evolve.POLE tab_m")
    _web(rs, "I2T", "IMP-2 hang tab (B-06f)", 100.0, 1, folds=[(50.0, "fold")], source="lean.fell IMP-2L 0.10 m")
    _web(rs, "I2K", "IMP-2 bottom keeper tab (B-01)", 60.0, 2, folds=[(30.0, "fold")], source="lean.fell IMP-2L 0.06 m")
    _web(rs, "BRL", "bow riser loop (through B-11)", 100.0, 2, folds=[(50.0, "fold")],
         source="ledger bow riser carry (ASSUMPTION 100 mm loops)")
    _web(rs, "BRS", "bow riser strap + G-hook", 300.0, 1, folds=[(30.0, "G-hook fold")],
         source="ledger bow riser carry (ASSUMPTION 300 mm strap)")
    tk = F.tripod_keeper(c)
    rs.webbing.append({"id": "B-26", "use": "B-26 tripod keeper, 3 mm shock cord (ends 15 mm in the R corner seams)",
                       "material_id": "shock_cord_3mm", "length_mm": tk["cut_mm"], "qty": 1, "kit": "base",
                       "source": "corrie_f.tripod_keeper"})
    rs.webbing.append({"id": "FP-cord", "use": "FP mouth shock cord", "material_id": "shock_cord_3mm",
                       "length_mm": F.fp_spec()["w"] + F.fp_spec()["pleat"] + 60.0, "qty": 2, "kit": "base",
                       "source": "corrie_f.hip_reach_pockets (w + pleat + 60)"})
    rs.webbing.append({"id": "E5-cord", "use": "pole quiver grip cord", "material_id": "shock_cord_3mm",
                       "length_mm": F._A().POLE["cord_m"] * 1000.0, "qty": 1, "kit": "base", "source": "evolve.POLE"})
    mk = F.muzzle_keeper()               # BL-035: rifle muzzle keepers through the B-11 muzzle tabs (both gussets)
    rs.webbing.append({"id": "MK-cord", "use": "rifle muzzle keeper, 3 mm shock cord loop through the 2 B-11 muzzle tabs "
                                          "+ spring cord lock (one per gusset)", "material_id": "shock_cord_3mm",
                       "length_mm": mk["cut_mm"], "qty": mk["qty"], "kit": "base",
                       "source": "corrie_f.muzzle_keeper (ASSUMPTION MUZZLE-CORD)"})
    # hardware (from the ledger rows; counts only)
    rs.hardware += [
        {"item": "#10 coil zip, door, 2 sliders + 2 cord pulls", "material_id": "coil_zipper_10",
         "length_mm": round(rs.geo["zip_door_mm"] + 60.0), "qty": 1},
        {"item": "#5 coil zip, B-29 lid aft wall + slider + pull", "material_id": "coil_zipper_5",
         "length_mm": LID["zip_mm"] + 60.0, "qty": 1},
        {"item": "#5 coil zip, IMP-4 + slider + pull", "material_id": "coil_zipper_5", "length_mm": 210.0, "qty": 1},
        {"item": "#5 coil zip, F-02 fly pocket", "material_id": "coil_zipper_5", "length_mm": 230.0, "qty": 1},
        {"item": "heavy 25 mm ladder locks: B-28 (4) + guys (2) + W1-W3 (3)", "material_id": "ladder_lock_25mm_heavy",
         "length_mm": None, "qty": 9},
        {"item": "POM toggles: B-28 rear (2) + guy loops (2)", "material_id": "pom_toggle",
         "length_mm": None, "qty": 4},
        {"item": "rated 25 mm G-hooks: W1-W3 (3) + extenders (3)", "material_id": "g_hook_25mm_aluminium",
         "length_mm": None, "qty": 6},
        {"item": "25 mm side-release buckles (roll top): male on RT, female on RTM", "material_id": "buckle_side_release_25mm",
         "length_mm": None, "qty": 2},
        # BL-040 m-14: the rest of the bag hardware, so the cut list's hardware table matches the BOM
        {"item": "rated 25 mm G-hooks: IM1, IM2 (2) + bow riser (1)", "material_id": "g_hook_25mm_aluminium",
         "length_mm": None, "qty": 3},
        {"item": "wiregate carabiners 22 kN: IM3 bag hooks (2) + IM3 free end (1) + B-24 links (2, meat trip)",
         "material_id": "carabiner_wiregate_22kn", "length_mm": None, "qty": 5},
        {"item": "25 mm aluminium cam buckles: IM1-IM3 (3) + US1/US2 (2)", "material_id": "cam_25mm_al",
         "length_mm": None, "qty": 5},
        {"item": "25 mm tri-glides: US backstop, STAINLESS (2) + guy tail keepers, nylon (2)", "material_id": "triglide_25mm",
         "length_mm": None, "qty": 4},
        {"item": "cord lock (E-5)", "material_id": "cord_lock_spring", "length_mm": None, "qty": 1},
        {"item": "cord locks: rifle muzzle keepers (2, BL-035)", "material_id": "cord_lock_spring", "length_mm": None,
         "qty": F.muzzle_keeper()["qty"]},
    ]


# ============================================================================ F-01 rain fly (BL-033)
def build_fly(rs: RevSet, c):
    """F-01a spine + F-01b sides (corrie_f.fly_pieces), seam notches every 50 mm and at the top aft corner, hem fold
    lines, tether grommet; the elastic as a cut line (F-EL)."""
    fp = F.fly_pieces(c)
    sp, sd = fp["pieces"]
    sp.labels["note"] = "silpoly: seams 301 then flat-felled + seam-sealed; 20 mm elastic channel hems top + bottom"
    sd.labels["note"] = "cut 1 pair (mirror); 20 mm elastic channel hems on the bottom and frame edges"
    for p in (sp, sd):
        rs.add(p, "fly", "14 rain fly", kit="as_hunted", notes="corrie_f.fly_pieces")
    rs.seams += fp["seams"]
    g = fp["geo"]
    R = g["spine_R"]
    notch_pair([(sp, sp.edge_points("right"))], [(sd, sd.edge_points("aft")), (sd, sd.edge_points("top"))], "fly seam R",
               pitch=100.0)
    for n in list(sp.notches):          # the L seam: the spine is symmetric, F-01b is cut as a mirrored pair
        sp.add_notch(-n.x, n.y, n.kind, n.label.replace(" R", " L"))
    # tuck line, collar line and lid-wall line across the spine (fold / placement marks)
    for y, lab in ((F.FLY_TUCK, "floor edge (tuck below)"), (g["y_end"] - g["top_mm"], "lid aft edge")):
        xr = float(np.interp(y, [q[1] for q in R], [q[0] for q in R]))
        sp.add_internal_line([(-xr, y), (xr, y)], "fold", lab)
    sp.add_drill_hole(0.0, F.FLY_TUCK / 2, 5.0, "tether grommet (cord to F-02)")
    for p, e in ((sp, "bottom"), (sp, "top"), (sd, "bottom"), (sd, "frame")):
        pts = p.edge_points(e)
        p.add_internal_line(pts, "fold", "hem: turn 20 mm, 6 mm elastic in the channel")
    _dedupe_notches(sp)
    _dedupe_notches(sd)
    rs.webbing.append({"id": "F-EL", "use": "fly hem elastic, 6 mm (spine top + bottom, sides bottom + frame)",
                       "material_id": "elastic_6mm", "length_mm": round(fp["elastic_m"] * 1000.0),
                       "qty": 1, "kit": "as_hunted", "source": "corrie_f.fly_pieces (FLY_ELASTIC_RATIO x hem channels)"})
    rs.geo["fly"] = {"area_m2": round(fp["area_m2"], 3), "mass_B_g": round(fp["mass_g"], 1), "hem_mm": round(fp["hem_mm"]),
                     "elastic_mm": round(fp["elastic_m"] * 1000.0), "lid_top_z": round(g["lid_top_z"], 1),
                     "seam_mm": round(g["seam_mm"], 1), "state": g["state"]}


# ============================================================================ build + checks
def build(fabrics: str = "today", addons: bool = True) -> RevSet:
    rs = RevSet(fabrics=fabrics)
    with F.revision(REV):
        c = F.make()
        build_shell(rs, c)
        build_hardpoints(rs, fabrics)
        build_pockets(rs, c, fabrics)
        build_lid(rs, fabrics)
        build_webbing(rs, c)
        build_fly(rs, c)
        if addons:
            build_addons(rs)
    for p in rs.pieces.values():
        sewn = p.material_id not in WEBBING and p.material_id not in FREE_ROTATION and p.seam_allowance_mm != 0.0
        if sewn and not p.notches:          # appliques and plain panels: a centre-line notch on every edge > 30 mm
            for e in p.edge_names:
                if p.edge_length(e) > 30.0:
                    p.add_notch_on_edge(e, 0.5, kind="v", label="CL")
        p.face = "up"
        p.labels.setdefault("face", MATERIAL_FACE.get(p.material_id, ("-", "-"))[0])
    rs.notes += [
        f"B-22: the drawn x +/-{B22_XZ[0]:.0f} puts the 50 mm tab over the hinge band | blade seam (band half width "
        f"{rs.geo['b22']['band_half_w_at_z']} mm at z {B22_XZ[1]:.0f}); placed at x +/-{rs.geo['b22']['placed_x']} "
        f"({rs.geo['b22']['moved_mm']} mm inboard, ASSUMPTION B22-IN). BL-033 confirmed it on the 15 in fine run "
        "(section 7.2).",
    ]
    return rs


def seam_report(rs: RevSet, tol: float = 1.0):
    return check_seams(rs.seams, tol_mm=tol)


def pattern_mass_g(p: Piece) -> float:
    """Cut area less the cut-outs (windows, slots) x record gsm (bag_concepts.piece_mass_g rule)."""
    from shapely.geometry import Polygon
    holes = sum(Polygon(ln.points).area for ln in p.internal_lines if ln.kind == "cut_inside" and ln.closed
                and len(ln.points) >= 3)
    if p.material_id in WEBBING:
        m = MAT.load(p.material_id)          # BL-034: elastic_25mm has a record now
        return p.edge_length("left") / 1000.0 * float(m.require("mass_g_m")) * p.quantity
    g_full = BC.piece_mass_g(p)
    return g_full * (1.0 - holes / max(p.area_mm2, 1.0)) if holes else g_full


# ledger row (name prefix) -> (status, piece ids, webbing ids, note). status: pattern | webbing | hardware | removed |
# not_drafted | double_booked. Every ledger bag row must match exactly one entry; every piece id at least one row.
RECON = [
    ("B-11 lash tabs", "pattern", ["B-11"], [], ""),
    ("main bag: bow riser carry", "webbing", [], ["BRL", "BRS"], "G-hook in the row"),
    ("B-01 ", "pattern", ["B-01"], [], ""), ("B-03 ", "pattern", ["B-03"], [], ""),
    ("B-05 ", "pattern", ["B-05"], [], ""), ("B-02u ", "pattern", ["B-02u"], [], ""),
    ("B-02door ", "pattern", ["B-02door"], [], ""), ("B-02h ", "pattern", ["B-02h"], [], ""),
    ("SH-07 ", "pattern", ["SH-07"], [], ""), ("SH-01b ", "pattern", ["SH-01b"], [], ""),
    ("B-06f ", "pattern", ["B-06f"], [], ""), ("B-06 ", "pattern", ["B-06"], [], ""),
    ("B-07 ", "pattern", ["B-07"], [], ""), ("B-07s ", "pattern", ["B-07s"], [], ""),
    ("D2 door zip", "hardware", [], [], "#10 coil zip"), ("door: 2 cord pulls", "hardware", [], [], ""),
    ("4 hard-point loops", "webbing", [], ["HPL"], ""),
    ("IMP-2 ", "pattern", ["B-09c", "B-09p"], ["I2T", "I2K"], "+ hardware in the row"),
    ("IMP-4 ", "pattern", ["IMP4-a", "IMP4-b"], [], "+ #5 zip"),
    ("IMP-8 ", "pattern", ["IMP8-a", "IMP8-b"], [], ""),
    ("FP-L/R ", "pattern", ["FP-a", "FP-b"], ["FP-cord"], ""),
    ("E-5 pole quiver", "webbing", [], ["E5", "E5-cord"], "+ cord lock"),
    ("add-on scope_pod", "pattern", ["A1-a", "A1-b", "A1-d"], [], "add-on (as hunted)"),
    ("add-on meat_liner", "pattern", ["MS-a", "MS-b", "MS-c", "MS-s"], [], "add-on (meat trip)"),
    ("add-on crown_lid", "pattern", ["B-29a", "B-29b", "B-29c", "B-29d", "B-29e", "B-29f", "B-29g"], [], "+ #5 zip"),
    ("add-on crown_straps", "webbing", [], ["B-28", "B-28t", "B-28s", "K-28"], "+ locks, toggles"),
    ("F-01 rain fly", "pattern", ["F-01a", "F-01b"], [], "drafted by BL-033"),
    ("F-02 fly base pocket", "pattern", ["F-02"], [], ""),
    ("rain fly: fly elastic hem", "webbing", [], ["F-EL"], "+ #5 zip, slider, tether"),
    ("IM-web:", "webbing", [], ["IM1", "IM2", "IM3"], ""), ("IM-eyes:", "webbing", [], ["IME"], ""),
    ("IM-hooks:", "hardware", [], [], ""), ("IM-cams:", "hardware", [], [], ""),
    ("B-12:", "pattern", ["B-12"], [], ""), ("US-anchor:", "hardware", [], [], "frame side"),
    ("US-cams:", "hardware", [], [], ""), ("US-tg:", "hardware", [], [], ""), ("US-web:", "webbing", [], ["US"], ""),
    ("US-chan:", "pattern", ["B-16"], [], "drafted by BL-033 (corrie_f.us_channels)"),
    ("B-24-web:", "webbing", [], ["B-24"], ""), ("B-24-hooks:", "hardware", [], [], ""),
    ("B-24-thr:", "hardware", [], [], "thread"),
    ("W-web:", "webbing", [], ["W1", "W2", "W3"], "with A-2 and BL-031 rows"),
    ("W-hw:", "hardware", [], [], ""), ("A-2:", "webbing", [], ["W1", "W2", "W3"], "tail trim, in the cut"),
    ("keepers:", "webbing", [], ["K-W"], ""), ("roll:", "webbing", [], ["RT"], "+ 2 buckles (the RTM tabs: BL-041 row)"),
    ("BL-010 S2", "hardware", [], [], ""), ("BL-010 S9", "hardware", [], [], ""), ("BL-010 S12", "hardware", [], [], ""),
    ("bag-side load spreaders", "pattern", ["B-17", "B-18"], [], "B-17 trimmed by the BL-004 REC row"),
    ("attachment: printed fairleads", "hardware", [], [], "frame side"),
    ("attachment: 7075 pins", "hardware", [], [], ""), ("attachment: UHMWPE sleeves", "hardware", [], [], ""),
    ("attachment: bag hooks, 38 mm", "hardware", [], [], ""), ("attachment: TPU hook sleeves", "hardware", [], [], ""),
    ("attachment: webbing eyes", "webbing", [], ["HE"], ""), ("attachment: bag-side straps", "webbing", [], ["T3"], ""),
    ("attachment: elastic keepers", "hardware", [], [], "IM2 hook keepers (removed below) + misc"),
    ("attachment: lifter tri-glide keepers", "hardware", [], [], "harness side"),
    ("attachment system: crown hood B-19", "removed", [], [], "BL-004 REC removes it"),
    ("attachment system: hood lip stiffener", "removed", [], [], "BL-004 REC"),
    ("attachment system: hood lining", "removed", [], [], "BL-004 REC"),
    ("attachment system: hood ladder strips", "removed", [], [], "BL-004 REC"),
    ("attachment system: hood tongues", "removed", [], [], "BL-004 REC"),
    ("attachment system: hood grab tab", "removed", [], [], "BL-004 REC"),
    ("attachment system: top side guys", "webbing", [], ["TG"], ""),
    ("attachment system: guy ladder locks", "webbing", [], ["LLT"], "+ locks"),
    ("attachment system: guy corner tabs B-22", "pattern", ["B-22"], [], ""),
    ("attachment system: guy tail elastic keepers", "webbing", [], ["K-G"], ""),
    ("attachment system: IM2 tongue backings B-23", "removed", [], [], "BL-004 REC"),
    ("attachment system: bag hooks 1500", "hardware", [], [], ""),
    ("attachment system: thread", "hardware", [], [], ""),
    ("B-13x boxed fairlead swell", "pattern", ["B-13x"], [], "6 with port (the 2 hinge swells: next row)"),
    ("BL-033 H-1: hinge swells", "removed", [], [], "no hinge window (B-18 is the hinge load path)"),
    ("BL-004 REC: IM2 bag hooks", "removed", [], [], ""), ("BL-004 REC: IM2 TPU hook sleeves", "removed", [], [], ""),
    ("BL-004 REC: T2 tongues", "removed", [], [], ""), ("BL-004 REC: B-23", "removed", [], [], ""),
    ("BL-004 REC: elastic keepers for the IM2", "removed", [], [], ""),
    ("BL-004 REC: hood B-19", "removed", [], [], ""),
    ("BL-004 REC: guy toggles", "hardware", [], [], "the POM toggles (on the guy's B-25 end); webbing: BL-041 row"),
    ("BL-041: GBL guy bar loop webbing deleted", "removed", [], [], "carried nothing in rev 3"),
    ("BL-041: B-25 bridle 25 -> 38 mm", "webbing", [], ["B-25"], "crown_tube_guy_loop.md"),
    ("BL-004 REC: B-17 trimmed", "pattern", ["B-17"], [], "B-17 drawn 90 x 70"),
    ("BL-010 A1", "hardware", [], [], ""), ("BL-010 A3", "hardware", [], [], ""),
    ("BL-022 rev 1: B-25", "webbing", [], ["B-25"], ""), ("BL-022 rev 1: B-26", "webbing", [], ["B-26"], "shock cord"),
    ("BL-028 rev 2: B-27", "pattern", ["B-27f"], [], "slits drawn on B-01"),
    ("BL-031: W1-W3 cut for carry", "webbing", [], ["W1", "W2", "W3"], ""),
    ("BL-031: W1-W3 haul extenders", "webbing", [], ["WX"], "+ rated G-hooks"),
    ("BL-031: IM1-IM3 tail keepers", "webbing", [], ["K-IM"], ""),
    ("BL-031: roll-top clip straps", "webbing", [], ["RT"], ""),
    ("BL-031: roll-top clip tail keepers", "webbing", [], ["K-RT"], ""),
    ("BL-034 records:", "hardware", [], [], "hardware / elastic re-booked on the BL-034 records"),
    ("BL-034 thread:", "hardware", [], [], "thread from the op lengths (build_effort_rev3)"),
    ("BL-035: rifle muzzle keepers", "webbing", [], ["MK-cord"], "+ 2 cord locks"),
    ("BL-041: B-18 hinge doublers", "pattern", [], [], "B-18 growth; weighed with the bag-side load spreaders row"),
    ("BL-041: HE hinge eyes", "webbing", [], ["HE"], "HE-PIN length change"),
    ("BL-041: RTM roll-clip buckle tabs", "webbing", [], ["RTM"], ""),
    ("BL-041: IMC IM cam anchor tabs", "webbing", [], ["IMC"], ""),
    ("BL-043: B-25 bridle drawn topology", "webbing", [], ["B-25"], "B25-TOPO"),
    ("BL-043: IMC tabs", "webbing", [], ["IMC"], "m-4"),
    ("BL-044: HE hinge eyes", "webbing", [], ["HE"], "HE-ENV length change"),
    ("BL-044: hinge pins", "hardware", [], [], "frame-side pins, 20 mm throat"),
    ("BL-044: W3 K-W keeper loops deleted", "removed", [], [], "DECISION KW-W3-OFF"),
    ("BL-044: B-25 on the sized spine clamp", "webbing", [], ["B-25"], "crown_spine_clamp run_plan"),
    ("BL-044: US cam anchors USA", "webbing", [], ["USA"], "BL-045 found-not-fixed; USA-LOOP"),
]


def ledger_rows(size: str = "M") -> list:
    from huntkit.mass import ledger as L
    return L.adopted_bag_rows(size)


def reconcile(rs: RevSet, rows=None) -> dict:
    """1:1 piece list <-> ledger bag rows (ADOPTED_BAG), and the fabric mass check (B fabrics = the ledger's)."""
    rows = rows if rows is not None else ledger_rows()
    out, unmatched, multi = [], [], []
    used = {e[0]: 0 for e in RECON}
    for r in rows:
        hits = [e for e in RECON if r["name"].startswith(e[0])]
        hits = [max(hits, key=lambda e: len(e[0]))] if len(hits) > 1 and len({len(h[0]) for h in hits}) == len(hits) \
            else hits
        if not hits:
            unmatched.append(r["name"])
            continue
        if len(hits) > 1:
            multi.append(r["name"])
        e = hits[0]
        used[e[0]] += 1
        out.append({"row": r["name"], "system": r["system"], "cfg": r["cfg"], "ledger_g": r["g"], "status": e[1],
                    "pieces": e[2], "webbing": e[3], "note": e[4]})
    ids = set(rs.pieces) | {w["id"] for w in rs.webbing}
    ref = {i for o in out for i in o["pieces"] + o["webbing"]}
    return {"rows": out, "unmatched_rows": unmatched, "multi_matched_rows": multi,
            "unused_entries": [k for k, v in used.items() if v == 0],
            "pieces_without_row": sorted(ids - ref), "row_ids_not_drafted": sorted(ref - ids)}


def fabric_component_g(name: str, g: float, fabrics: str = "B") -> float | None:
    """The cut-fabric part of a ledger row (what the pattern area replaces), from the row's own source."""
    if name.startswith("IMP-2 "):
        return [d for d in F._B().fixed_pockets(F.make()) if d["id"] == "IMP-2L"][0]["fabric_g"]
    if name.startswith(("IMP-4 ", "IMP-8 ")):
        c = F.make()
        with F.frame_face(c):
            bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
        return bp[name.split()[0]]["fabric_g"]
    if name.startswith("FP-L/R"):
        FP = F.fp_spec()
        mesh = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (FP["h"] + 2 * SA_FLAT) * 1e-6 * F._gsm(F.MESH)
        band = 2 * (FP["w"] + FP["pleat"] + 2 * SA_FLAT) * (25.0 + 2 * SA_FLAT) * 1e-6 * F._gsm(F.CAMO)
        return mesh + band
    if name.startswith("add-on scope_pod"):
        return F._B().addons()["A1"]["fabric_g"]
    if name.startswith("add-on meat_liner"):
        import importlib
        sw = importlib.import_module("D.cache").modules()[0]
        return sum(BC.piece_mass_g(p) for p in sw["pieces"])
    if name.startswith("add-on crown_lid"):
        return F.crown_lid(fabrics)["fabric_g"]
    if name.startswith("bag-side load spreaders"):
        return 2 * (90 * 110 + 90 * 45) * 1e-6 * 1000.0          # attach_system B-17 90x110 + B-18 90x45, 1000 gsm
    if name.startswith("BL-004 REC: B-17 trimmed"):
        return g
    if name.startswith("BL-028 rev 2: B-27"):
        return g
    return g


def mass_check(rs_B: RevSet, rows=None, tol_pct: float = 3.0) -> dict:
    """Pattern-area mass of every 'pattern' ledger row (B fabrics, the ledger's basis) against the row's fabric part.
    Webbing rows: cut lengths x record g/m against the same rows is reported, not gated (rows mix hardware)."""
    rec = reconcile(rs_B, rows)
    res, tp, tl = [], 0.0, 0.0
    for o in rec["rows"]:
        if o["status"] != "pattern":
            continue
        if o["row"].startswith(("BL-004 REC: B-17 trimmed", "BL-041: B-18 hinge doublers")):
            continue                                    # B-17 / B-18 are weighed once, against all their rows (below)
        if o["row"].startswith("B-13x boxed fairlead swell"):
            lf_h1 = next(r["ledger_g"] for r in rec["rows"] if r["row"].startswith("BL-033 H-1: hinge swells"))
        else:
            lf_h1 = 0.0
        pm = sum(pattern_mass_g(rs_B.pieces[i]) for i in o["pieces"])
        lf = fabric_component_g(o["row"], o["ledger_g"])
        if o["row"].startswith("bag-side load spreaders"):
            trim = next(r for r in rec["rows"] if r["row"].startswith("BL-004 REC: B-17 trimmed"))
            lf += trim["ledger_g"]
            lf += sum(r["ledger_g"] for r in rec["rows"] if r["row"].startswith("BL-041: B-18 hinge doublers"))
        lf += lf_h1                                     # B-13x: x8 row + the H-1 removal row (6 drawn)
        if o["row"].startswith("BL-028 rev 2: B-27"):
            pm += 2 * 2 * F.PORT_TURN * F.guy_port()["slit_mm"] * 1e-6 * F._gsm(rs_B.pieces["B-01"].material_id)
        res.append({"row": o["row"][:70], "pieces": o["pieces"], "pattern_g": round(pm, 2), "ledger_fabric_g": round(lf, 2),
                    "delta_g": round(pm - lf, 2), "delta_pct": round(100 * (pm - lf) / lf, 1) if lf else None})
        tp += pm
        tl += lf
    return {"rows": res, "pattern_g": round(tp, 1), "ledger_g": round(tl, 1), "delta_g": round(tp - tl, 1),
            "delta_pct": round(100 * (tp - tl) / tl, 2), "tol_pct": tol_pct, "ok": abs(tp - tl) / tl * 100 <= tol_pct}


def summary(rs: RevSet) -> dict:
    rep = seam_report(rs)
    return {"fabrics": rs.fabrics, "piece_types": len(rs.pieces),
            "fabric_types": sum(1 for p in rs.pieces.values() if p.material_id not in WEBBING),
            "webbing_types": sum(1 for p in rs.pieces.values() if p.material_id in WEBBING),
            "pieces_cut_base": sum(p.quantity for p in rs.all_pieces(kits={"base"}, sizes={KIT}, webbing=False)),
            "pieces_cut_all_fabric": sum(p.quantity for p in rs.all_pieces(sizes={KIT}, webbing=False)),
            "webbing_lines": len(rs.webbing), "seams": len(rep.results), "mismatches": len(rep.mismatches),
            "worst_seam_mm": round(max(abs(r.error_mm) for r in rep.results), 2), "lid": rs.lid, "geo": rs.geo,
            "notes": rs.notes}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fabrics", default="today", choices=("today", "B"))
    a = ap.parse_args(argv)
    rs = build(a.fabrics)
    rep = seam_report(rs)
    print(rep.markdown())
    print(json.dumps(summary(rs), indent=1, default=str))
    rsB = rs if a.fabrics == "B" else build("B")
    rec = reconcile(rsB)
    print({k: v for k, v in rec.items() if k != "rows"})
    print(json.dumps(mass_check(rsB), indent=1))
    print(json.dumps(lid_hours(rs), indent=1))


if __name__ == "__main__":
    main()
