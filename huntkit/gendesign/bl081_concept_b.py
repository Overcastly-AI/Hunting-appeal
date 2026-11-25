"""BL-081: detailed structural checks of iteration-2 frame concept B (6061-T6 drawn-tube ladder, printed tees).

Source design: ``designs/pack_5200/iter2/frame_concepts.{md,json}`` (BL-080, concept B) and
``huntkit.gendesign.bl080_metal_frame`` (not edited; its ``build_model`` is called and the result re-wired here).
Standard: HA-LS-1 rev C (``load_standard.ls1_envelope``: 9 crown-bar cases + 5 IM3-couple cases), torsos 15/19/23 in.

What BL-081 changes against the BL-080 first-order model (the "B81" detail design, every node metal-to-metal):

* **Lumbar node (z 120)**: the cross tube is joined to each stay by a pair of 6061-T6 .090 in L-gussets (front and back
  of the tubes), 4 x M5 through-bolts per side (stay z 90 / 155, cross tube x +/-90 / +/-62), all along y. The printed
  "lumbar tee" is the filler between the plates: it takes only the bolt preload in compression across its layers.
  Each through-bolt is held at both ends (front and back plate), so tube torsion crosses the joint as a bearing couple
  across the tube diameter (link rotation stiffness 2 k R^2), not as bolt bending.
* **Hip bracket**: two 1-1/2 x 1-1/2 x 1/8 in 6061 angles, 80 mm long, as a U cradle round the cross tube: the front
  angle's leg is the Ti mount face (y -48.55, 6 of the 8 BL-055 positions used), the back angle's leg sits behind the
  tube; their webs overlap above the tube (2 x M5). Two M5 key bolts along y at x +/-32 through front leg, a 3/4 x .035
  spacer tube, both cross-tube walls and the back leg carry the hip load and the stand-off torque (V x 67 mm).
* **Hip pin at its real stand-off**: the hipbelt springs act at the pin, 21 mm in front of the mount face (BL-055
  ``HIP_STAND``), not on the face: the cross-tube torque is 1.46 x the BL-080 value.
* **Mid / upper tees (z 330 / 520)**: printed split clamps round the stay (40 mm long) squeezed by two 6061 1 x 1/8 in
  backers with 2 x M5 beside the stay (no hole in the stay: the crown leg slides inside); the bar end is through-bolted
  to the backers (metal path), the printed halves see only clamp pressure. Modelled as stiff links; slip is a check.
* **Foot**: printed cup with a 38 x 38 x 1/8 in 6061 foot plate under the tube end; hinge pin z 60 along x through the
  stay; US1 / hinge eye on the pin (metal).
* **Fairleads / IM anchors** on metal: z 60 hinge pin, IM1 on a gusset tab (z 190), IM2 / IM3 on the tee backers; webbing
  bears on 3/4 x .035 tube sleeves over M5 bolts, never on PAHT.

Checks (frame_concepts.md section 8, items 1-9) are in ``run``; local solid FE of the tube at the holes, bushings and
clamps uses ``huntkit.fea.tube_solid`` (verified against Heywood / beam theory / Roark in tests/test_tube_solid.py).

Units mm, N, MPa, g, USD. Run: ``python -m huntkit.gendesign.bl081_concept_b run`` (about 15 min, 4 cores).
"""
from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from huntkit.gendesign import bl080_metal_frame as B80

REPO = Path(__file__).resolve().parents[2]
OUTDIR = REPO / "designs" / "pack_5200" / "iter2" / "frame_b"
REC_JSON = OUTDIR / "bl081.json"
REC_MD = OUTDIR / "bl081.md"
CACHE = REPO / "outputs" / "bl081"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261125_bl081_"
DATE = "2026-11-25"

IN = 25.4
TORSOS = (15.0, 19.0, 23.0)
G_WALK = 1.6
G = 9.80665

# ----------------------------------------------------------------------------- stock (adds BL-081 sizes; cited)
STOCK = dict(B80.STOCK)
STOCK["t1000_065"] = {"desc": '1" OD x .065" 6061-T6 drawn tube', "od": 1.0 * IN, "t": 0.065 * IN,
                      "usd": 12.57, "len_in": 48,
                      "src": "Speedy Metals p-4588 (12 in 5.24, 24 in 7.85, 48 in 12.57, 72 in 15.71; read 2026-11-25)"}
STOCK["t1250_125"] = {"desc": '1-1/4" OD x .125" 6061-T6 tube (ID 1.000")', "od": 1.25 * IN, "t": 0.125 * IN,
                      "usd": 15.0, "len_in": 12, "src": "ASSUMPTION SHELL-PRICE: 12 in about USD 15 (Speedy-class list, "
                      "no cited listing read); bore = 1 in, so a sawn half is a conforming clamp shell"}
CRUSH_SLEEVE = {"od": 7.9, "id": 5.5, "src": "BL-082 ASSUMPTION CRUSH-SLEEVE (5.5 x 7.9 mm Al or steel tube cut to the "
                "tube ID span); booked as 5/16 in x .035 6061 tube offcut, ASSUMPTION SLEEVE-PRICE USD 3 per frame"}
PRICE = dict(B80.PRICE_LENGTHS)
PRICE["t1000_065"] = {12: 5.24, 18: 6.73, 24: 7.85, 36: 10.47, 48: 12.57, 60: 14.28, 72: 15.71}
PRICE["t1000_049"] = {12: 14.40, 18: 18.51, 24: 21.60, 36: 28.80, 48: 34.56, 60: 39.27, 72: 43.20}
SHEET_090 = {"desc": '.090" 6061-T6 sheet 12 x 12 in', "t": 0.090 * IN, "usd": 22.05,
             "src": "Speedy Metals p-84 61SH090 12 x 12 in USD 22.05 (read 2026-11-25)"}
ANGLE_15 = {"desc": '1-1/2 x 1-1/2 x 1/8 in 6061-T6 angle, 18 in', "leg": 1.5 * IN, "t": 0.125 * IN, "usd": 4.92,
            "src": "Speedy Metals p-2183 18 in USD 4.92 (BL-080 booking, search snippet, secondary)"}
FLAT_1x18 = {"desc": '1 x 1/8 in 6061 flat, 18 in', "w": IN, "t": 0.125 * IN, "usd": 3.25,
             "src": "Speedy Metals p-2225 18 in USD 3.25 (BL-080 booking, search snippet, secondary)"}

RHO_AL = 2.70e-3            # g/mm3 (alu_6061_t6)
RHO_PAHT = 1.06e-3          # g/mm3 (pa12_cf_fdm_paht)
RHO_STEEL = 7.93e-3

# ----------------------------------------------------------------------------- materials (records; BL-082 when present)
FY_6061 = 241.0             # MMPDS S-basis yield (alu_6061_t6 yield_strength_sbasis_mpa)
FU_6061 = 290.0
E_AL = 68900.0
BRG_Y_ED2 = 386.0           # bearing yield at e/D 2 (alu_6061_t6_drawn_tube bearing_yield_ed2_mpa)
A2_PROOF = 450.0            # A2-70 0.2 % proof (ISO 3506-1)
M5_AS = 14.2                # M5 tensile stress area (ISO 898-1)
M5_MINOR_A = math.pi / 4 * 4.134 ** 2   # minor-diameter area (thread in the shear plane, conservative)
PETERSON_A_AL = 0.635       # Peterson notch constant for aluminium alloys, 0.025 in (Pilkey, Peterson's SCF, s 1.9)


def paht() -> dict:
    """PAHT-CF honest hot/wet basis (data/materials/polymers/pa12_cf_fdm_paht.yaml, BL-077 fields)."""
    from huntkit.materials import load
    m = load("pa12_cf_fdm_paht")
    g = lambda k: float(m.require(k))   # noqa: E731
    return {"z_hw": g("tensile_strength_z_hw_mpa"), "xy_hw": g("tensile_strength_xy_hw_mpa"),
            "ils_hw": g("interlayer_shear_hw_mpa"), "fat": g("fatigue_1e5_ratio"),
            "creep": g("creep_rupture_8h_40c_ratio"), "creep_mod": g("creep_modulus_8h_40c_ratio"),
            "E_hw": g("youngs_modulus_xy_mpa") * 0.587, "Ez_hw": g("youngs_modulus_z_mpa") * 0.587}


def bl082_records() -> dict:
    """BL-082 records if the materials agent has added them (notched / clamped 6061 S-N, friction, tube crush).
    Returns {} until they exist; every caller then uses its cited ASSUMPTION."""
    out = {}
    root = REPO / "data" / "materials"
    import yaml
    for p in root.rglob("*.yaml"):
        n = p.stem.lower()
        if any(k in n for k in ("notch", "s_n", "sn_", "friction", "clamp", "crush", "ovalis", "fretting")):
            try:
                out[p.stem] = yaml.safe_load(p.read_text())
            except Exception:   # pragma: no cover
                continue
    return out


def sn_6061() -> dict:
    """BL-082 6061-T6 fatigue basis (data/materials/metals/alu_6061_t6.yaml): Yahr (ORNL 1993) mean curve
    Sa = C / sqrt(N) + floor, fully reversed; modified Goodman on Su 290 (the conservative choice: Yahr notes Gerber fits
    aluminium better; Goodman is kept because the curve is a MEAN curve with no scatter factor); notch q 1 (Kf = Kt,
    Bennett & Weinberg 1954); no preload credit in bolted tube joints (BJ-NOCREDIT); anodise 0.7 (ANODISE-FAT)."""
    from huntkit.materials import load
    m = load("alu_6061_t6")
    g = lambda k: float(m.require(k))   # noqa: E731
    return {"C": g("sn_fit_coeff_mpa"), "floor": g("sn_fit_floor_mpa"), "Su": g("goodman_ultimate_mpa"),
            "q": g("notch_sensitivity_design_ratio"), "anodise": g("anodize_fatigue_knockdown_ratio"),
            "smax_r0_1e5": g("fatigue_smax_1e5_r0_goodman_mpa")}


ANODISED_HOLES = False      # recommendation: holes and clamp zones bare (or thin Type II); True applies ANODISE-FAT 0.7


def fat_allow_local(kt: float = 1.0, N: float = 1e5) -> float:
    """Allowable max stress at R 0 (0 -> peak) for N cycles: Goodman on the Yahr mean curve, S_max = 2 Sf Su / (Su + Sf),
    divided by Kf = Kt (q 1). With kt 1 this is the smooth limit the local (FE, Kt-including) peak is compared with:
    190.9 MPa at 1e5 (record fatigue_smax_1e5_r0_goodman_mpa)."""
    d = sn_6061()
    Sf = d["C"] / math.sqrt(N) + d["floor"]
    smax = 2 * Sf * d["Su"] / (d["Su"] + Sf)
    if ANODISED_HOLES:
        smax *= d["anodise"]
    return smax / kt


def notch_q(r_mm: float) -> float:
    """BL-082: 6061-T6 is fully notch sensitive at these radii, design q = 1 (Kf = Kt)."""
    return sn_6061()["q"]


def tube_props() -> dict:
    """BL-082 tube record: ring crush / hoop limits and wet friction (alu_6061_t6_drawn_tube.yaml)."""
    from huntkit.materials import load
    m = load("alu_6061_t6_drawn_tube")
    g = lambda k: float(m.require(k))   # noqa: E731
    return {"w_yield": g("diametral_first_yield_1x049_n_mm"), "w_collapse": g("diametral_collapse_1x049_n_mm"),
            "p_hoop_yield": g("hoop_yield_pressure_1x049_mpa"), "p_buckle": g("ring_buckling_pressure_1x049_mpa"),
            "mu_al_wet": g("alu_6061_wet_cof"), "mu_paht_wet": g("paht_cf_wet_cof"),
            "ship_base": g("ship_ground_base_estimate_usd")}


# ----------------------------------------------------------------------------- design (B81)
HOLE_D = 5.3                # M5 through-bolt, drilled 5.2 then reamed / 5.3 jig bush (ISO 273 fine)
CFG0 = {
    "stay": "t1000_065", "ubar": "t1000_065", "bar": "t750_035", "ctube": "t1000_065",
    "gusset_t": SHEET_090["t"], "gusset_w": 38.1,
    "stay_bolt_z": (105.0, 135.0), "ct_bolt_x": (90.0, 62.0), "rung_z": (85.0, 155.0), "tie_x": 30.0,
    "post_len": 90.0, "clamp_len": 50.0, "clamp_preload_n": 2600.0, "clamp_preload_upper_n": 2000.0, "backer_t": 0.25 * IN, "backer_len": 55.0,
    "mu": 0.15, "preload_retention": 0.9, "shell": "t1250_125", "bush_len": 70.0, "bush_contact_deg": 30.0, "leg_clear_mm": 0.50,
}
Y_MOUNT = -48.55            # Ti mount face (hip_mount.FACE_Y)
HIP_STAND = 21.0            # pin load stand-off from the mount face (h1_closeout.HIP_STAND)
PIN_Y = Y_MOUNT - HIP_STAND
MOUNT_POS = [(18.44, 115.4), (18.44, 124.6), (14.12, 132.71), (-18.44, 115.4), (-18.44, 124.6), (-14.12, 132.71)]
#   ^ 6 of the 8 BL-055 positions (h1_closeout.json hip.chosen.pattern): the z 107.29 row would sit 2.7 mm off the
#     front angle's lower edge; the other six are through-bolted M5 x 16 A2 + nuts into 6061 (no inserts).


def stock_sec(key):
    from huntkit.fea.sections import tube_round
    s = STOCK[key]
    return tube_round(s["od"], s["t"])


def yc_ct():
    """Cross-tube centre y (the straight stay line at z 120)."""
    return -10.0 * 120.0 / 530.0


def area(key):
    s = STOCK[key]
    di = s["od"] - 2 * s["t"]
    return math.pi * (s["od"] ** 2 - di ** 2) / 4


# ----------------------------------------------------------------------------- joint stiffness
def huth_k(t1, E1, t2, E2, d=5.0, Eb=193000.0, n=1, a=2 / 3, b=3.0) -> float:
    """Huth (1986) fastener flexibility, metallic bolted joint, per shear plane: k = 1 / C (N/mm)."""
    C = ((t1 + t2) / (2 * d)) ** a * (b / n) * (1 / (t1 * E1) + 1 / (n * t2 * E2) + 1 / (2 * t1 * Eb)
                                               + 1 / (2 * n * t2 * Eb))
    return 1.0 / C


GAP_KNOCK = 0.5     # ASSUMPTION GAP-K: a 1 mm printed shim between plate and tube wall halves the Huth stiffness


def bolt_link_k(tube_t, plate_t, tube_r, axis: str, twist_axis: str | None, axial: bool = True) -> list:
    """6-vector (global) of a through-bolt held at both ends: shear in the plane normal to the bolt (two interfaces in
    parallel), axial through the shims, and the torsion couple about ``twist_axis`` (the tube axis) = 2 k R^2.
    ``axial=False``: the plates cannot push the tube along the bolt (thin plates out of plane; the lumbar node's
    fore-aft load goes through the saddle plug instead), so the axial term is a nominal 100 N/mm."""
    k = GAP_KNOCK * huth_k(plate_t, E_AL, tube_t, E_AL)
    kt = 2 * k
    ka = 3.0e4 if axial else 1.0e2  # ASSUMPTION: bolt axial through two printed shims (preloaded), N/mm
    v = [kt, kt, kt, 0.0, 0.0, 0.0]
    i = "xyz".index(axis)
    v[i] = ka
    if twist_axis:
        # the two bores sit at +/- R along the bolt: opposite wall forces make a couple about EITHER axis normal to
        # the bolt (tube torsion and the tube's bending in the plane of the bolt); only rotation about the bolt is free
        for ax in "xyz":
            if ax != axis:
                v[3 + "xyz".index(ax)] = 2 * k * tube_r ** 2
    return v


PLUG_K = 3.0e4          # ASSUMPTION PLUG-K: printed saddle plug (PAHT, 20 mm long, D 22) in compression, N/mm
CLAMP_KT = 2.0e4        # ASSUMPTION CLAMP-K: clamp tee translation stiffness (as the UHMWPE bushing links), N/mm
CLAMP_KR = 2.0e8        # ASSUMPTION CLAMP-K: E_hw 2266 x 25.4 x 40^3 / 12 / 1.5 mm shim, N mm / rad


# ----------------------------------------------------------------------------- model
def _bar_end_split(m, nid, member_id, new):
    """Re-point one end of ``member_id`` from ``nid`` to a new coincident node ``new``."""
    m["nodes"][new] = list(m["nodes"][nid])
    for mem in m["members"]:
        if mem["id"] == member_id:
            mem["nodes"] = [new if n == nid else n for n in mem["nodes"]]
            return
    raise KeyError(member_id)


def post_sec():
    """Two 1-1/2 x 1-1/2 x 1/8 in angles side by side, front legs coplanar (the Ti mount face), stems aft at the outer
    edges (a channel open to the rear). Local y = global x for a vertical member (ref x): Iy = bending that deflects the
    post fore-aft (both angles' own I about the axis parallel to the front leg, 32.4e3 mm4 each)."""
    from huntkit.fea.sections import generic
    leg, t = 1.5 * IN, 0.125 * IN
    A1 = (2 * leg - t) * t
    yb = (leg * t * t / 2 + (leg - t) * t * (t + (leg - t) / 2)) / A1
    I1 = leg * t ** 3 / 12 + leg * t * (yb - t / 2) ** 2 + t * (leg - t) ** 3 / 12 + (leg - t) * t * (t + (leg - t) / 2 - yb) ** 2
    Iz = 2 * (I1 + A1 * (leg - yb) ** 2)
    J = 2 * (2 * leg * t ** 3 / 3)
    s = generic(2 * A1, 2 * I1, Iz, J, ymax=leg, zmax=leg - yb, Wt=J / t)
    s.kind = "post_2angles"
    s.dims = {"leg": leg, "t": t, "I1": I1, "yb": yb}
    return s


def _gusset_sec(t, w, d, L=30.0):
    """Pair of plates w x t at +/- d (centre lines) either side of the tube axis. Local y = in-plane width direction
    (bending about local z is in-plane: 2 t w^3 / 12), local z = through the pair (couple: 2 (w t^3/12 + w t d^2)).
    Torsion of the pair is differential in-plane bending of the two plates (bolts tie them through the tubes only):
    a cantilever arm L twisted by T gives plate forces T / 2d, tip deflection F L^3 / 3 E I_p, so the equivalent
    GJ = 6 E I_p d^2 / L^2 (ASSUMPTION GUSSET-J, L = bolt pitch). Gusset stresses are hand-checked
    (``gusset_check``), not read from this equivalent section."""
    from huntkit.fea.sections import generic
    A = 2 * w * t
    Iy = 2 * (w * t ** 3 / 12 + w * t * d ** 2)   # bending that pulls one plate and pushes the other
    Iz = 2 * t * w ** 3 / 12
    J = 6 * E_AL * (t * w ** 3 / 12) * d ** 2 / (26000.0 * L ** 2) + 2 * w * t ** 3 / 3
    s = generic(A, Iy, Iz, J, ymax=w / 2, zmax=d + t / 2, Wt=J / t)
    s.kind = "gusset_pair"
    s.dims = {"w": w, "t": t, "d": d}
    return s


def build(cfg: dict | None = None, torso: float = 19.0, rigid: bool = False) -> dict:
    """B81 beam model. ``rigid=True`` gives the BL-080 joints (everything welded) on the same geometry for comparison."""
    from huntkit.fea.sections import generic, tube_round, tube_rect
    cfg = {**CFG0, **(cfg or {})}
    c = {**B80.CONCEPTS["B"], "stay": cfg["stay"], "ubar": cfg["ubar"], "bar": cfg["bar"],
         "lumbar": {"kind": "cross_tube", "tube": cfg["ctube"]}}
    for k_ in (cfg["stay"], cfg["ubar"], cfg["bar"], cfg["ctube"]):
        if k_ not in B80.STOCK:
            B80.STOCK[k_] = STOCK[k_]     # build_model reads its own STOCK (in memory only)
    m = B80.build_model(c, torso)
    m = copy.deepcopy(m)
    nodes = m["nodes"]
    st = STOCK[cfg["stay"]]
    R_st = st["od"] / 2
    ct = stock_sec(cfg["ctube"])
    yc = nodes["SL120"][1]
    soft = next(mm for mm in m["members"] if mm["group"] == "lumbar_plate")
    soft_sec, soft_mat = soft["section"], soft["material"]
    drop = {"plh20", "plh21", "plh22", "plh23", "pivot_boss", "pivot_doubler_0", "pivot_doubler_1"}
    m["members"] = [mm for mm in m["members"] if mm["id"] not in drop]
    yline = lambda z: float(np.interp(z, [0.0, 530.0], [nodes["SR0"][1], nodes["SR530"][1]]))   # noqa: E731

    def stay_node(tag, z):
        """Stay node at height z (splits the stay member that spans z)."""
        nid = f"S{tag}{z:g}"
        if nid in nodes:
            return nid
        for mm in m["members"]:
            if mm["group"].startswith("stay") and mm["group"].endswith(tag):
                a_, b_ = mm["nodes"]
                za, zb = nodes[a_][2], nodes[b_][2]
                if min(za, zb) < z < max(za, zb):
                    pa, pb = np.array(nodes[a_]), np.array(nodes[b_])
                    nodes[nid] = list(map(float, pa + (z - za) / (zb - za) * (pb - pa)))
                    m["members"].append({**mm, "id": f"{nid}-{b_}", "nodes": [nid, b_]})
                    mm["nodes"], mm["id"] = [a_, nid], f"{a_}-{nid}"
                    return nid
        raise KeyError(nid)

    # the z 120 grillage row is back-sheet again (BL-080 had the cross tube there)
    for i, (a_, b_) in enumerate((("SL120", "P21"), ("P21", "P22"), ("P22", "P23"), ("P23", "SR120"))):
        m["members"].append({"id": f"soft120_{i}", "nodes": [a_, b_], "section": soft_sec, "material": soft_mat,
                             "group": "lumbar_plate", "ref": [0.0, 0.0, 1.0], "no_kg": True})
    # ---- twin lumbar rungs (z rung_z), ends on saddle plugs + 2 gusset bolts each end, tie bolts at +/- tie_x
    zr = tuple(cfg["rung_z"])
    xb1, xb2 = cfg["ct_bolt_x"]
    xt = cfg["tie_x"]
    x_end = 115.0           # rung end node on the stay axis: the plug link is then between coincident nodes (an offset
    #                         translational link would resist the frame's rigid rotation on the body springs)
    rn = lambda z, x: f"R{z:g}{'m' if x < 0 else 'p'}{abs(x):g}" if abs(x) > 1e-9 else f"R{z:g}c"   # noqa: E731
    for z in zr:
        yz = yline(z)
        xs = sorted({-x_end, -xb1, -xb2, -xt, 0.0, xt, xb2, xb1, x_end})
        for x in xs:
            nodes[rn(z, x)] = [float(x), yz, float(z)]
        for x0_, x1_ in zip(xs[:-1], xs[1:]):
            m["members"].append({"id": f"{rn(z, x0_)}-{rn(z, x1_)}", "nodes": [rn(z, x0_), rn(z, x1_)], "section": ct,
                                 "material": "alu_6061_t6", "group": "lumbar_cross_tube", "ref": [0.0, 0.0, 1.0]})
    # ---- lumbar gussets: plate pair on the stay (z rung_z[0] .. rung_z[1]) with an arm along each rung
    t, w = cfg["gusset_t"], cfg["gusset_w"]
    d = R_st + t / 2              # plates on the tube crowns (no shim: BL-082, nothing printed under preload)
    gs = _gusset_sec(t, w, d)
    zs1, zs2 = cfg["stay_bolt_z"]
    bolts = []
    ctk = STOCK[cfg["ctube"]]
    Rm_ct = ctk["od"] / 2 - ctk["t"] / 2
    for tag, sx in (("L", -1.0), ("R", 1.0)):
        spine = sorted({zr[0], zs1, 120.0, zs2, zr[1]})
        gn = {z: f"G{tag}s{z:g}" for z in spine}
        for z in spine:
            nodes[gn[z]] = list(nodes[stay_node(tag, z)])
        for z0_, z1_ in zip(spine[:-1], spine[1:]):
            m["members"].append({"id": f"{gn[z0_]}-{gn[z1_]}", "nodes": [gn[z0_], gn[z1_]], "section": gs,
                                 "material": "alu_6061_t6", "group": "lumbar_gusset", "ref": [1.0, 0.0, 0.0]})
        for z in zr:
            ga, gb = f"G{tag}a{z:g}", f"G{tag}b{z:g}"
            nodes[ga] = [sx * xb1, yline(z), float(z)]
            nodes[gb] = [sx * xb2, yline(z), float(z)]
            for a_, b_ in ((gn[z], ga), (ga, gb)):
                m["members"].append({"id": f"{a_}-{b_}", "nodes": [a_, b_], "section": gs, "material": "alu_6061_t6",
                                     "group": "lumbar_gusset", "ref": [0.0, 0.0, 1.0]})
            kct = bolt_link_k(ctk["t"], t, Rm_ct, "y", "x", axial=False)
            for x, gnode in ((xb1, ga), (xb2, gb)):
                bolts.append({"id": f"lc_{tag}{z:g}_{x:g}", "nodes": [rn(z, sx * x), gnode], "k": kct,
                              "kind": "rung_end_bolt", "tube": cfg["ctube"]})
            bolts.append({"id": f"plug_{tag}{z:g}", "nodes": [rn(z, sx * x_end), stay_node(tag, z)],
                          "k": [PLUG_K, PLUG_K, 0.0, 0.0, 0.0, 0.0], "kind": "saddle_plug", "tube": cfg["ctube"]})
        # the plate between the two rung arms (inner verticals)
        for x in (xb1, xb2):
            a_, b_ = f"G{tag}{'a' if x == xb1 else 'b'}{zr[0]:g}", f"G{tag}{'a' if x == xb1 else 'b'}{zr[1]:g}"
            m["members"].append({"id": f"{a_}-{b_}", "nodes": [a_, b_], "section": gs, "material": "alu_6061_t6",
                                 "group": "lumbar_gusset", "ref": [1.0, 0.0, 0.0]})
        kst = bolt_link_k(st["t"], t, R_st - st["t"] / 2, "y", "z", axial=False)
        for z in (zs1, zs2):
            bolts.append({"id": f"lb_{tag}{z:g}", "nodes": [stay_node(tag, z), gn[z]], "k": kst, "kind": "stay_bolt",
                          "tube": cfg["stay"]})
    # ---- hip post: two 1-1/2 in angles (front legs = Ti mount face, stems aft), ties to the rungs at +/- tie_x
    y_post = Y_MOUNT + 1.6
    nodes["HM"] = [0.0, y_post, 120.0]
    nodes["HP"] = [0.0, PIN_Y, 120.0]
    m["members"].append({"id": "ti_mount", "nodes": ["HM", "HP"], "section": tube_round(14.0, 6.9),
                         "material": "ti_6al_4v", "group": "hip_pivot", "ref": [1.0, 0.0, 0.0]})
    ps = post_sec()
    y_tie_end = yline(120.0) - R_st - 1.0
    sp = stock_sec("t750_035")
    for z in zr:
        po = f"PO{z:g}"
        nodes[po] = [0.0, y_post, float(z)]
        m["members"].append({"id": f"HM-{po}", "nodes": ["HM", po], "section": ps, "material": "alu_6061_t6",
                             "group": "hip_bracket", "ref": [1.0, 0.0, 0.0]})
        for tag, sx in (("L", -1.0), ("R", 1.0)):
            tp, tr = f"TP{tag}{z:g}", f"TR{tag}{z:g}"
            nodes[tp] = [sx * xt, y_post, float(z)]
            nodes[tr] = [sx * xt, yline(z), float(z)]      # tie column modelled to the rung axis (coincident link)
            m["members"].append({"id": f"{po}-{tp}", "nodes": [po, tp], "section": ps, "material": "alu_6061_t6",
                                 "group": "hip_bracket", "ref": [0.0, 0.0, 1.0]})
            m["members"].append({"id": f"tie_{tag}{z:g}", "nodes": [tp, tr], "section": sp, "material": "alu_6061_t6",
                                 "group": "hip_ties", "ref": [0.0, 0.0, 1.0]})
            kt_ = 2 * GAP_KNOCK * huth_k(STOCK["t750_035"]["t"], E_AL, ctk["t"], E_AL)
            bolts.append({"id": f"tie_{tag}{z:g}", "nodes": [rn(z, sx * xt), tr], "k": [kt_, 3.0e4, kt_, 0, 0, 0],
                          "kind": "tie_bolt", "tube": cfg["ctube"]})
    # ---- upper bar: pawl-housing bolt stations x +/-15
    ub = [mm for mm in m["members"] if mm["group"] == "upper_bar" and mm["id"] in ("UB0-UB1", "UB1-UB2")]
    for mm in ub:
        a, b = mm["nodes"]
        x_new = -15.0 if a == "UB0" else 15.0
        nid = f"UBh{'m' if x_new < 0 else 'p'}15"
        pa = np.array(nodes[a]); pb = np.array(nodes[b])
        f = (x_new - pa[0]) / (pb[0] - pa[0])
        nodes[nid] = list(map(float, pa + f * (pb - pa)))
        mm["nodes"] = [a, nid]
        mm["id"] = f"{a}-{nid}"
        m["members"].append({**mm, "id": f"{nid}-{b}", "nodes": [nid, b]})
    # ---- clamp tees at z 330 / 520
    tees = []
    for g_, z in (("mid_bar", 330.0), ("upper_bar", 520.0)):
        for tag in ("L", "R"):
            sn = f"S{tag}{z:g}"
            mem = next(mm for mm in m["members"] if mm["group"] == g_ and sn in mm["nodes"])
            new = f"T{tag}{z:g}"
            _bar_end_split(m, sn, mem["id"], new)
            tees.append({"id": f"tee_{tag}{z:g}", "nodes": [sn, new], "k": [CLAMP_KT] * 3 + [CLAMP_KR] * 3,
                         "kind": "clamp_tee", "z": z})
    if rigid:
        for b in bolts + tees:
            b["k"] = [1e7] * 3 + [1e11] * 3
    for ln in bolts + tees:
        m["links"].append({k: v for k, v in ln.items()})
    m["b81"] = {"cfg": cfg, "bolts": [b["id"] for b in bolts], "tees": [t_["id"] for t_ in tees], "rigid": rigid}
    return m


# ----------------------------------------------------------------------------- global evaluation
def _role(group: str):
    if group.startswith("stay"):
        return "stays"
    if group in ("mid_bar", "upper_bar"):
        return "bars"
    if group == "lumbar_cross_tube":
        return "lumbar rungs"
    if group == "hip_bracket":
        return "hip post (2 angles)"
    if group == "hip_ties":
        return "hip ties (spacer columns)"
    return None


def station_forces(res, member_id: str, node_id: str):
    """Section forces at a node end of a member (local N, Vy, Vz, T, My, Mz) and the element rotation (3x3)."""
    mi = next(i for i, mm in enumerate(res.members) if mm["id"] == member_id)
    ni = res.node_ids.index(node_id)
    for e in res.members[mi]["elements"]:
        el = res.elements[e]
        if el.n1 == ni:
            return res.elem_forces[e, 0].copy(), el.T[:3, :3].copy()
        if el.n2 == ni:
            return res.elem_forces[e, 1].copy(), el.T[:3, :3].copy()
    raise KeyError((member_id, node_id))


# hole / joint stations: (name, member group filter, node, hole axis (global), tube key cfg field, bolt link id or None)
def stations(cfg: dict) -> list[dict]:
    zs1, zs2 = cfg["stay_bolt_z"]
    xb1, xb2 = cfg["ct_bolt_x"]
    xt = cfg["tie_x"]
    out = []
    for tag, sx in (("L", -1), ("R", 1)):
        s = "m" if sx < 0 else "p"
        out += [
            {"name": f"stay z{zs1:g} gusset bolt {tag}", "node": f"S{tag}{zs1:g}", "group": "stay", "axis": "y",
             "tube": cfg["stay"], "link": f"lb_{tag}{zs1:g}"},
            {"name": f"stay z{zs2:g} gusset bolt {tag}", "node": f"S{tag}{zs2:g}", "group": "stay", "axis": "y",
             "tube": cfg["stay"], "link": f"lb_{tag}{zs2:g}"},
            {"name": f"stay z60 hinge pin {tag}", "node": f"S{tag}60", "group": "stay", "axis": "x",
             "tube": cfg["stay"], "link": None, "pin": "hinge"},
            {"name": f"upper bar x{sx * 15:+g} pawl-housing bolt", "node": f"UBh{s}15", "group": "upper_bar",
             "axis": "y", "tube": cfg["ubar"], "link": None, "pin": "pawl"},
        ]
        for z in cfg["rung_z"]:
            for x in (xb1, xb2):
                out.append({"name": f"rung z{z:g} x{sx * x:+g} gusset bolt", "node": f"R{z:g}{s}{x:g}",
                            "group": "lumbar_cross_tube", "axis": "y", "tube": cfg["ctube"],
                            "link": f"lc_{tag}{z:g}_{x:g}"})
            out.append({"name": f"rung z{z:g} x{sx * xt:+g} hip tie bolt", "node": f"R{z:g}{s}{xt:g}",
                        "group": "lumbar_cross_tube", "axis": "y", "tube": cfg["ctube"], "link": f"tie_{tag}{z:g}",
                        "washer": True})
    return out


def _members_at(res, node, group_prefix):
    return [mm["id"] for mm in res.members if node in mm["id"].split("-") and mm["group"].startswith(group_prefix)] \
        or [mm["id"] for mm in res.model["members"] if node in mm["nodes"] and mm["group"].startswith(group_prefix)]


def evaluate_global(cfg: dict | None = None, torsos=TORSOS, rigid: bool = False, log=print) -> dict:
    """Every HA-LS-1 rev C case set: member margins by role, buckling, link (bolt / tee / bushing / pawl) forces
    factored, station section forces (factored and walk) for the hole checks, T1 deflection."""
    from huntkit.fea.load_standard import ls1_envelope
    cfg = {**CFG0, **(cfg or {})}
    env = ls1_envelope()
    out = {"strength": {}, "buckling": None, "links": {}, "stations": {}, "walk": {}, "deflection": {},
           "members_util": {}, "case_list": []}
    sts = stations(cfg)
    for t in torsos:
        m = build(cfg, t, rigid)
        for var, cases in env.items():
            for case in cases:
                if case.name == "tall_load_posts":
                    continue
                r = case.run(m)
                req = float(r.meta["required_sf"])
                key = f"{case.name}|{var}|{t:g}"
                out["case_list"].append(key)
                for mm in r.members:
                    role = _role(mm["group"])
                    if role is None or B80._mid(mm["material"]) == B80.SOFT_MAT["id"]:
                        continue
                    marg = mm["sf"] / req
                    u = out["members_util"].get(mm["id"])
                    if u is None or 1 / marg > u:
                        out["members_util"][mm["id"]] = 1 / marg
                    cur = out["strength"].get(role)
                    if cur is None or marg < cur["margin"]:
                        out["strength"][role] = {"margin": float(marg), "case": key, "member": mm["id"],
                                                 "sf": float(mm["sf"]), "required": req}
                bf = r.buckling_sf
                if np.isfinite(bf):
                    mg = bf / (1.5 * req)
                    if out["buckling"] is None or mg < out["buckling"]["margin"]:
                        out["buckling"] = {"margin": float(mg), "eigen": float(bf), "case": key}
                lf = r.meta["link_forces"]
                for lid, f in lf.items():
                    fv = np.asarray(f, float) * req
                    cur = out["links"].get(lid)
                    mag = float(np.linalg.norm(fv[:3]))
                    if cur is None or mag > cur["F"]:
                        out["links"][lid] = {"F": mag, "vec": fv.tolist(), "case": key}
                    cur = out["links"].get(lid + "|M")
                    mm_ = float(np.linalg.norm(fv[3:]))
                    if cur is None or mm_ > cur["M"]:
                        out["links"][lid + "|M"] = {"M": mm_, "vec": fv.tolist(), "case": key}
                # station forces
                for s in sts:
                    for mid in _members_at(r, s["node"], s["group"]):
                        try:
                            f, R = station_forces(r, mid, s["node"])
                        except KeyError:
                            continue
                        rec = {"f": (f * req).tolist(), "R": R.tolist(), "case": key, "member": mid,
                               "link": (np.asarray(lf[s["link"]]) * req).tolist() if s.get("link") else None}
                        out["stations"].setdefault(s["name"], []).append(rec)
                        if case.name == "static_carry":
                            rw = {"f": (f * G_WALK).tolist(), "R": R.tolist(), "case": key, "member": mid,
                                  "link": (np.asarray(lf[s["link"]]) * G_WALK).tolist() if s.get("link") else None}
                            out["walk"].setdefault(s["name"], []).append(rw)
                # gusset / bracket end forces (hand checks), hip pin reaction
                for mm in r.members:
                    if mm["group"] in ("lumbar_gusset", "hip_bracket", "hip_ties"):
                        rec = {"case": key, "req": req, "start": (np.asarray(mm["end_forces"][0]) * req).tolist(),
                               "end": (np.asarray(mm["end_forces"][1]) * req).tolist()}
                        out.setdefault("members_f", {}).setdefault(mm["id"], []).append(rec)
                        if case.name == "static_carry":
                            rw = {"case": key, "start": (np.asarray(mm["end_forces"][0]) * G_WALK).tolist(),
                                  "end": (np.asarray(mm["end_forces"][1]) * G_WALK).tolist()}
                            out.setdefault("members_w", {}).setdefault(mm["id"], []).append(rw)
                hp = np.asarray(r.reactions.get("HP", np.zeros(6)), float)
                out.setdefault("hip_pin", []).append({"case": key, "req": req, "F": (hp[:3] * req).tolist(),
                                                      "walk": (hp[:3] * G_WALK).tolist() if case.name == "static_carry" else None})
                if case.name == "static_carry":
                    out["walk"].setdefault("_links", []).append(
                        {"case": key, "links": {k: (np.asarray(v) * G_WALK).tolist() for k, v in lf.items()}})
                    if var == "crown_bar":
                        out["deflection"][f"{t:g}"] = t1_deflection(r)
                if case.name in ("static_carry", "hipbelt_off_abuse", "drop_2p5g"):
                    out.setdefault("_disp", {})[key] = {n: list(map(float, v[:3])) for n, v in r.displacements.items()}
        log(f"  global torso {t:g} done")
    return out


def t1_deflection(res) -> dict:
    """T1 measurement at 150 lb (1 g static carry): fore-aft movement of the crown top bar centre (a) relative to the
    hip pin (includes the frame's rotation on the body springs, which the rig's ratcheted shoulder straps also allow)
    and (b) ELASTIC: relative to the lumbar block (stay nodes z 90..150) extrapolated as a rigid body, i.e. the crown
    reading minus the lumbar dial-gauge reading and its rotation (load_standard 5.2 records both). (b) is the number
    to compare with the +/-30 % band."""
    U = res.displacements
    ids = res.node_ids
    X = res.coords
    zs, uy = [], []
    for tag in "LR":
        for z in (90.0, 105.0, 120.0, 135.0, 150.0):
            n = f"S{tag}{z:g}"
            if n in U:
                zs.append(X[ids.index(n)][2])
                uy.append(U[n][1])
    a, b = np.polyfit(zs, uy, 1)
    z_tb = X[ids.index("TB1")][2]
    d_el = float(U["TB1"][1] - (a * z_tb + b))
    d = float(U["TB1"][1] - U["HP"][1])
    return {"crown_rel_hip_y_mm": d, "crown_elastic_mm": d_el, "band_lo": 0.7 * d_el, "band_hi": 1.3 * d_el,
            "crown_abs_mm": float(np.linalg.norm(U["TB1"][:3]))}


def t1_all(cfg=None, torsos=TORSOS) -> dict:
    """T1 numbers for the B81 joints and for rigid joints (static carry, crown-bar couple)."""
    from huntkit.fea.load_standard import ls1_cases
    case = [c for c in ls1_cases() if c.name == "static_carry"][0]
    out = {}
    for rigid in (False, True):
        for t in torsos:
            out.setdefault("rigid" if rigid else "b81", {})[f"{t:g}"] = t1_deflection(case.run(build(cfg, t, rigid)))
    return out


def torsion_stiffness(cfg=None, torso=19.0, rigid=False) -> float:
    """N m / deg by the record's test (frame_comp_e.torsion_stiffness): hip pivot clamped, +/- F (y) at the stay tops."""
    from huntkit.fea.frame import solve
    from huntkit.gendesign import frame_topopt as ft
    m = dict(build(cfg, torso, rigid))
    m["loads"] = {"SR530": [0, ft.TORSION_F, 0, 0, 0, 0], "SL530": [0, -ft.TORSION_F, 0, 0, 0, 0]}
    m["supports"] = {"HP": "fixed"}
    m["inertia_relief"] = False
    r = solve(m, buckling=False)
    i = {n: r.node_ids.index(n) for n in ("SL530", "SR530")}
    dy = r.u[6 * i["SR530"] + 1] - r.u[6 * i["SL530"] + 1]
    w = abs(m["nodes"]["SR530"][0] - m["nodes"]["SL530"][0])
    return float(ft.TORSION_F * w / 1000.0 / np.degrees(dy / w))


def torsion_reference() -> dict:
    """The released carbon tube frame (frame.yaml beam model) by the same test, and H1 = 0.94 x tube frame (cold,
    production_frame.md: 'cold torsion 0.94 of the tube frame')."""
    from huntkit.gendesign import frame_comp_e as E
    k_tube = E.torsion_stiffness(None)
    return {"tube_Nm_deg": k_tube, "h1_Nm_deg": 0.94 * k_tube, "h1_basis": "production_frame.md: H1 cold torsion "
            "0.94 x the tube frame (printed_frame_study.md)"}
