"""Team C (OPEN), bag competition 2026-11-10: TAILGATE, a full-access hauler on the CORRIE B.2 box body.

    python designs/pack_5200/bag_comp/C/tailgate.py            # numbers -> outputs/bag_comp_C/tailgate_numbers.json

What changes against CORRIE B.2 (concepts/corrie.py, read only; everything not named here is CORRIE B.2 as built):

* The whole aft face below the hinge band is ONE lid (B-02L) HINGED AT THE FLOOR SEAM (a sewn seam, not a zip). Two
  #10 coil zip legs run IN the aft corner seams (lid | gusset) from the floor corner up to z 590, turn R 60 onto the
  aft face and cross under the hinge band at z 650 (an inverted U, 2 sliders). Unzipped, the lid drops down like a
  tailgate: the opening is the full box width from the floor to z 650 (CORRIE's door: 45 mm inset, sill z 110).
  The zip is never at the floor (meat weight, ground water, abrasion stay on a sewn seam).
* Hoop load: three 25 mm LID STRAPS H1-H3 at the IM1-IM3 heights (z 190 / 330 / 520) span the lid from a webbing
  loop on the right gusset to one on the left gusset, 15 mm forward of the zip legs. The lid is cut 6 mm wider than
  the strap path (DECISION: ease 3 mm a side, eased into the hinge-band seam). The cloth sim shows the zip carries
  little hoop load either way (<= 0.45 N/mm, analysis/bag_comp_C.md section 3): the straps' job is the closing
  procedure and the dynamic case. Procedure: cinch H1-H3 FIRST, then zip (the straps close the gap; the slider never
  pulls a loaded chain together).
* Garages: the 2 sliders park closed at the top-right corner under a camo garage SH-07; the two zip feet end in
  500D boots under the kick plate; camo storm flaps SH-09 (630D, 35 mm, hot-cut) cover the two corner legs and frame
  the lid (the owner's camo as an accent edge); a 330D flap covers the top run.
* No wings. Side carry (tripod right, pad / decoy left) rides under 2 side straps per side, frame-corner seam to the
  same gusset loops; the IMP-1 scope sleeve is sewn to the left gusset (its own panel, unchanged). CORRIE's 4 wing
  straps -> 4 side straps; 2 x 200 x 450 wing panels and bars deleted.
* IMP-4 kill-kit pocket moves to the inside of the lid (same part). IMP-2, IMP-8, pouch, roll-top, fly: CORRIE B.2.
* IMP-C1 (new, harness): a stretch snack / GPS sleeve on the right J-strap, so today's snacks are reachable pack-on
  on every belt size (CORRIE's residual miss).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
sys.path.insert(0, str(CONCEPTS))
sys.path.insert(0, str(ROOT))

import bag_concepts as BC  # noqa: E402
import bag_concepts_wide as W  # noqa: E402
import corrie as CO  # noqa: E402
from bag_concepts import SA_BODY, SA_FLAT, _accent_rect, _seam  # noqa: E402
from huntkit import materials as MAT  # noqa: E402
from huntkit.patterns import Piece, rect_panel  # noqa: E402

NAME = "TAILGATE"
TEAM = "C"
OUT = ROOT / "outputs" / "bag_comp_C"

LID = {"z_top": 650.0, "r": 60.0, "ease_mm": 6.0}          # DECISION: hinge-band seam at z 650 as CORRIE (B-22 at 695)
HOOP_Z = (190.0, 330.0, 520.0)                              # DECISION: at IM1-IM3 (BC.STATIONS)
SIDE_Z = (330.0, 520.0)                                     # side straps share the H2 / H3 gusset loops
LOOP_IN_MM = 15.0                                           # gusset loops 15 mm forward of the zip leg
FLAP_W = 35.0                                               # storm flap width (finished), mm
SA_ZIP = 10.0
WEB25 = MAT.load("poly_webbing_25mm").require("mass_g_m")
WEB25_BREAK = MAT.load("poly_webbing_25mm").require("breaking_strength_n")
WEB25_EPS_BREAK = MAT.load("poly_webbing_25mm").require("elongation_at_break_pct") / 100.0
LADDER = MAT.load("ladder_lock_25mm").require("mass_g")
ZIP10 = MAT.load("coil_zipper_10")
ZIP10_CROSS_N = ZIP10.require("crosswise_strength_n")      # 900 N, ASTM D2061 crosswise (25.4 mm jaw), ESTIMATE
G_HOOK = CO.G_HOOK
CORD_PULL_G = CO.CORD_PULL_G
LADDER_SLIP_N = 300.0       # 25 mm ladder-lock slip (meat_haul_modes.md, as the W1-W3 wraps in the cloth sim)
POCKETS = ("IMP-1", "IMP-2", "IMP-4", "IMP-8")             # CORRIE B.2 bag pockets kept (IMP-6 is a harness part)
SNACK = {"w": 130.0, "h": 210.0, "stretch_depth": 45.0}     # IMP-C1 face, ASSUMPTION: power mesh stretches to 45 mm


def make():
    return CO.make()


# ----------------------------------------------------------------------------------------------- the aft face
def lid_face(c):
    """Lid B-02L (floor seam -> z 650, R 60 top corners, 3 mm ease a side) and hinge band B-02h (z 590 tongues at the
    corners -> collar seam). Face flat coords (x, s), s = unrolled aft-face length (bag_concepts.front_face_profile)."""
    zk, s, a = BC.front_face_profile(c)
    S = lambda z: float(np.interp(z, zk, s))           # noqa: E731
    A = lambda z: float(np.interp(z, zk, a))           # noqa: E731
    zt, r, e = LID["z_top"], LID["r"], LID["ease_mm"] / 2
    zr = zt - r
    legz = [z for z in zk if z < zr] + [zr]
    right = [(A(z) + e, S(z)) for z in legz]
    xr = A(zr) + e
    arc = [(xr - r + r * math.cos(t), S(zr) + r * math.sin(t)) for t in np.linspace(0, math.pi / 2, 13)]
    top_r = right + arc[1:]
    top_l = [(-x, y) for x, y in top_r][::-1]
    lid_edges = [("hinge", [(-A(zk[0]) - e, 0.0), (A(zk[0]) + e, 0.0)]),
                 ("zip", top_r + top_l)]
    # zip runs: right leg up, arc, top run, arc, left leg down (lid CCW from the hinge's right end)
    lid = Piece.from_edges("tailgate lid (full aft face, hinged at the floor seam)", lid_edges,
                           seam_allowance_mm={"default": SA_ZIP, "hinge": SA_BODY}, material_id="cordura_330d_nylon66",
                           piece_id="B-02L")
    # hinge band: tongues down the corners to z 590 (the zip arcs are its lower edge), straight top run at z 650
    hz = [zr] + [z for z in zk if z > zr]
    br = [(A(z), S(z)) for z in hz]
    bl = [(-x, y) for x, y in br]
    arc_b = [(A(zr) - r + r * math.cos(t), S(zr) + r * math.sin(t)) for t in np.linspace(0, math.pi / 2, 13)]
    zip_b = arc_b + [(-x, y) for x, y in arc_b][::-1]          # right tongue foot -> arc -> top run -> left foot
    band_edges = [("zip", zip_b), ("left", bl), ("top", [bl[-1], br[-1]]), ("right", br[::-1])]
    band = Piece.from_edges("hinge band with corner tongues", band_edges,
                            seam_allowance_mm={"default": SA_BODY, "zip": SA_ZIP}, material_id="cordura_330d_nylon66",
                            piece_id="B-02h")
    leg = lid.edge_length("zip")
    return lid, band, leg


def clear_width(c, z):
    """Clear opening width at height z: the full box width less the two zip chains (9 mm, record) and storm flaps."""
    a = float(c.a([min(z, LID["z_top"] - LID["r"])])[0])
    return 2 * a - 2 * ZIP10.require("chain_width_mm")


# ----------------------------------------------------------------------------------------------- the build
def build(c=None):
    """CORRIE B.2 build (corrie.build) with the aft face, door, wings and their hardware replaced by TAILGATE's."""
    c = c or make()
    b = CO.build(c, True, spec="B.2")
    drop_p = {"B-02u", "B-02door", "B-02h", "SH-07", "M-01", "SH-06"}
    b.pieces = [(p, g) for p, g in b.pieces if p.piece_id not in drop_p]
    b.appliques = [p for p in b.appliques if p.piece_id not in drop_p]
    b.seams = [(s, t) for s, t in b.seams if not any(k in s.name for k in (
        "aft face", "U-surround", "horseshoe", "hinge band", "wing"))]
    b.zips = [z for z in b.zips if "horseshoe" not in z["name"]]
    hw = b.extra.get("hardware", [])
    n_drop_tacks = sum(2 for n, _ in hw if n.startswith("wing strap"))
    b.extra["hardware"] = [(n, g) for n, g in hw if not (n.startswith("wing strap") or n.startswith("door: 2 cord"))]
    b.extra["bartacks"] = b.extra.get("bartacks", 0) - n_drop_tacks
    b.extra.pop("zip_door_mm", None)
    lid, band, Lzip = lid_face(c)
    G = next(p for p, _ in b.pieces if p.piece_id == "B-03")
    BOT = next(p for p, _ in b.pieces if p.piece_id == "B-05")
    b.pieces += [(lid, "shell"), (band, "shell")]
    b.seams += [
        _seam(lid.edge("hinge"), BOT.edge("top").reversed(), "lid hinge | floor (sewn, 2 rows: the tailgate hinge)",
              "seared"),
        _seam(lid.edge("zip"), lid.edge("zip"), "lid | gussets + hinge band (#10 zip, inverted U)", "zip"),
        _seam(band.edge("right"), band.edge("right"), "hinge band R | gusset R (above the zip)", "seared"),
        _seam(band.edge("left"), band.edge("left"), "hinge band L | gusset L (above the zip)", "seared"),
    ]
    b.zips.append({"name": "tailgate zip #10, inverted U, 2 sliders", "length_mm": Lzip, "corners": 2,
                   "z": (BC.Z0, LID["z_top"]), "where": "lid | gussets + hinge band"})
    b.extra["zip_lid_mm"] = Lzip
    W.add_hw(b, "lid zip: 2 cord pulls (3 mm Dyneema + rubber sleeve)", 2 * CORD_PULL_G, 0)
    # garages and flaps
    gar = rect_panel("slider garage, top-right corner (camo)", 50, 70, 0.0, seam_allowance_mm=SA_FLAT,
                     material_id="polyester_ht_630d_printable", piece_id="SH-07")
    boots = rect_panel("zip-foot boot (500D)", 40, 50, 0.0, seam_allowance_mm=SA_FLAT,
                       material_id="cordura_500d_nylon66", quantity=2, piece_id="SH-10")
    zk, s, a = BC.front_face_profile(c)
    leg_len = float(np.interp(LID["z_top"] - LID["r"], zk, s))
    flaps = _accent_rect("corner storm flap (camo, hot-cut edge)", FLAP_W, leg_len, "SH-09", qty=2)
    top_run = 2 * float(c.a([LID["z_top"]])[0]) - 2 * LID["r"]
    tflap = rect_panel("top-run storm flap (330D)", FLAP_W, top_run, 0.0, seam_allowance_mm=SA_FLAT,
                       material_id="cordura_330d_nylon66", piece_id="SH-11")
    b.pieces += [(gar, "accent"), (boots, "accent"), (flaps, "accent"), (tflap, "accent")]
    b.appliques += [gar]
    # lid straps H1-H3 + side straps + gusset loops
    for i, z in enumerate(HOOP_Z):
        L = 2 * float(c.a([z])[0]) + 2 * LOOP_IN_MM + 2 * 30.0 + 150.0      # span + round the corners + tail 150
        W.add_hw(b, f"lid strap H{i + 1}: 25 mm {L / 1000:.2f} m + G-hook (R loop) + ladder lock (L loop)",
                 L / 1000 * WEB25 + G_HOOK + LADDER, 1)
    for side in ("R", "L"):
        for z in SIDE_Z:
            L = float(c.depth([z])[0]) + 40.0 + 150.0
            W.add_hw(b, f"side strap {side} z {z:.0f}: 25 mm {L / 1000:.2f} m (frame-corner seam) + ladder lock",
                     L / 1000 * WEB25 + LADDER, 1)
    W.add_hw(b, "6 gusset loops 25 mm x 0.10 m (H1-H3 both sides), caught in the flap seam + bartack",
             6 * 0.10 * WEB25, 6)
    b.extra["spec"] = "TAILGATE on CORRIE B.2"
    return b


def pockets(c=None):
    """CORRIE B.2 bag pockets kept (IMP-1 now on the left gusset, IMP-4 on the lid inside: same parts) + IMP-C1."""
    c = c or make()
    bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    out = [{"id": k, "name": bp[k]["name"], "mass_g": round(bp[k]["mass_g"], 1),
            "where": {"IMP-1": "sewn to the LEFT GUSSET on 2 vertical lines (was: inside the left wing)",
                      "IMP-4": "sewn to the INSIDE OF THE LID at z 300-580 (was: inside the door)"}.get(k, "as CORRIE B.2"),
            "hours": bp[k].get("hours")} for k in POCKETS]
    mesh = MAT.load("power_mesh_nylon_spandex").require("areal_density_gsm")
    c330 = MAT.load("cordura_330d_nylon66").require("areal_density_gsm")
    a_face = (SNACK["w"] + 16) * (SNACK["h"] + 16) / 1e6
    g = a_face * (mesh + c330) + 0.30 * CO.SHOCK_GM + CO.CORDLOCK_G
    out.append({"id": "IMP-C1", "name": "snack / GPS stretch sleeve, right J-strap (power mesh over 330D)",
                "mass_g": round(g, 1), "where": "bartacked to the right J-strap above the belt (harness part)",
                "interior_mm": (SNACK["h"] - 10, SNACK["w"] - 15, SNACK["stretch_depth"]), "hours": 1.1,
                "volume_L": round((SNACK["h"] - 10) * (SNACK["w"] - 15) * SNACK["stretch_depth"] / 1e6, 2)})
    return out


def fly_g(b):
    """Rain fly F-01 scaled to the outer shell area, as corrie.b2_rows G-2 (ASSUMPTION there)."""
    P = CO._panels()
    fly = sum(r["mass_g_total"] for k, r in P.items() if k.startswith("F-01"))
    ids = ("B-03", "B-02L", "B-02h", "B-05") if any(p.piece_id == "B-02L" for p, _ in b.pieces) else CO.OUTER_IDS
    a = sum(p.area_mm2 * p.quantity for p, _ in b.pieces if p.piece_id in ids) / 1e6
    return fly * a / CO.SPINE_OUTER_M2, a


def bag_system(b, pk):
    """bag + pockets + lid/pouch + wings/compression + fly (belt independent), RULES.md result.json definition.
    Body group = bag_concepts.metrics total (shell, collar, swells, accents, wings/straps, pouch, zips, hardware)."""
    m = BC.metrics(b)
    fly, a = fly_g(b)
    body = m["mass_g"]["total"]
    pkts = sum(p["mass_g"] for p in pk)
    return {"body_group_g": round(body, 1), "pockets_g": round(pkts, 1), "fly_g": round(fly, 1),
            "outer_shell_m2": round(a, 3), "total_g": round(body + pkts + fly, 1), "metrics": m}


def corrie_bag_system():
    """The same definition applied to CORRIE B.2 (concepts/corrie.py, unchanged): the baseline for pack_mass_M_g."""
    c = make()
    b = CO.build(c, True, spec="B.2")
    bp = {d["id"]: d for d in CO.bag_pockets(c, spec="B.2")}
    pk = [{"id": k, "mass_g": bp[k]["mass_g"]} for k in POCKETS]
    return bag_system(b, pk)


# ----------------------------------------------------------------------------------------------- hoop load
def hoop_check(res_on: dict | None = None, res_off: dict | None = None) -> dict:
    """Zip crosswise load. Sources: the TAILGATE cloth sims (lid straps on / straps off) when given; the zip record
    (900 N per 25.4 mm crosswise, ESTIMATE); the ease argument for the strap-first rule."""
    cap = ZIP10_CROSS_N / 25.4
    out = {"zip_crosswise_n_mm": round(cap, 1), "zip_record": "coil_zipper_10 crosswise 900 N (ASTM D2061 1 in jaw), ESTIMATE"}

    def zip_rows(res):
        rows = {}
        for case in ("fill", "meat"):
            if case not in res["cases"]:
                continue
            sm = res["cases"][case]["seams"]
            zs = {k: v for k, v in sm.items() if "B-02L" in k and "B-05" not in k}
            hinge = {k: v for k, v in sm.items() if "B-02L" in k and "B-05" in k}
            mx = max(zs.items(), key=lambda kv: kv[1]["max_n_mm"])
            rows[case] = {"zip_seams": {k: round(v["max_n_mm"], 3) for k, v in zs.items()},
                          "zip_max_n_mm": round(mx[1]["max_n_mm"], 3), "zip_max_seam": mx[0],
                          "zip_p95_n_mm": round(max(v["p95_n_mm"] for v in zs.values()), 3),
                          "hinge_n_mm": round(max((v["max_n_mm"] for v in hinge.values()), default=0.0), 3),
                          "sf_static_1g": round(cap / mx[1]["max_n_mm"], 1),
                          "sf_3g": round(cap / (3 * mx[1]["max_n_mm"]), 1),
                          "straps": {k: round(v["tension_n"], 1) for k, v in res["cases"][case]["attachments"].items()
                                     if k.startswith("H")}}
        return rows
    if res_on:
        out["straps_on"] = zip_rows(res_on)
    if res_off:
        out["straps_off"] = zip_rows(res_off)
    if res_on and res_off:
        out["reduction_pct"] = {k: round(100 * (1 - out["straps_on"][k]["zip_max_n_mm"] / out["straps_off"][k]["zip_max_n_mm"]), 1)
                                for k in out["straps_on"] if k in out["straps_off"]}
    # ease: the strap stretches T / EA x L; EA from the record (secant to break, x 0.5 for the low-load toe, ASSUMPTION)
    EA = 0.5 * WEB25_BREAK / WEB25_EPS_BREAK
    c = make()
    span = 2 * float(c.a([330.0])[0]) + 2 * LOOP_IN_MM
    T = max([v for r in (out.get("straps_on") or {}).values() for v in r["straps"].values()] or [150.0])
    out["ease"] = {"ease_mm": LID["ease_mm"], "strap_EA_n": round(EA, 0), "lid_span_mm": round(span, 0),
                   "strap_tension_max_n": T, "strap_stretch_mm": round(T / EA * span, 2),
                   "zip_unloaded": T / EA * span < LID["ease_mm"],
                   "ladder_slip_sf": round(LADDER_SLIP_N / max(T, 1e-6), 2)}
    return out


# ----------------------------------------------------------------------------------------------- numbers
def numbers():
    c = make()
    b = build(c)
    pk = pockets(c)
    bs = bag_system(b, pk)
    cb = corrie_bag_system()
    m = bs["metrics"]
    v = BC.volumes(c)
    lid, band, Lzip = lid_face(c)
    corrie_reach = CO.door_reach(c)
    reach = {k: {"z": z, "tailgate_clear_mm": round(clear_width(c, z), 0),
                 "corrie_door_clear_mm": corrie_reach[k]["clear_width_mm"]} for k, z in BC.STATIONS.items()}
    reach["floor"] = {"z": BC.Z0, "tailgate_clear_mm": round(clear_width(c, BC.Z0), 0),
                      "corrie_door_clear_mm": corrie_reach["floor"]["clear_width_mm"],
                      "note": "tailgate: no sill (lid hinged at the floor seam); CORRIE: sill at z 110"}
    open_area = lid.area_mm2 / 1e6
    door = BC.hatch_face(c, CO.DOOR)[1]
    out = {
        "name": NAME, "team": TEAM, "volume_L_rule": round(v["volume_L"], 1), "fill_height_in": round(v["fill_height_in"], 1),
        "geo_cg": [round(v["cg_y"], 1), round(v["cg_z"], 1)],
        "bag_system": {k: v_ for k, v_ in bs.items() if k != "metrics"},
        "corrie_b2_bag_system": {k: v_ for k, v_ in cb.items() if k != "metrics"},
        "pack_mass_M_g": round(3943.0 - cb["total_g"] + bs["total_g"], 1),
        "pieces": m["cut_pieces"], "curved_seams": m["curved_seams"], "zip_mm_total": round(m["zip_length_m"] * 1000, 0),
        "zip_lid_mm": round(Lzip, 0), "hours": m["hours"], "beginner_hours": m["hours_total"],
        "corrie_metrics": {k: cb["metrics"][k] for k in ("cut_pieces", "curved_seams", "zip_length_m", "hours_total")},
        "opening_m2": {"tailgate_lid": round(open_area, 3), "corrie_door": round(door.area_mm2 / 1e6, 3)},
        "reach": reach, "pockets": pk, "hardware": b.extra.get("hardware"),
        "pieces_list": [(p.piece_id, p.name, p.material_id, p.quantity, round(BC.piece_mass_g(p), 1)) for p, _ in b.pieces],
    }
    return out


if __name__ == "__main__":
    n = numbers()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tailgate_numbers.json").write_text(json.dumps(n, indent=1, default=float))
    print(json.dumps({k: v for k, v in n.items() if k not in ("pieces_list", "hardware")}, indent=1, default=float))
