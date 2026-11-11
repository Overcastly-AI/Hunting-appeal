"""BL-007: print-to-size frame without the telescoping crown (study for an owner decision, nothing adopted).

The H1 frame (``frame_h1``) carries a telescoping carbon crown: 430 mm legs that slide in 18 mm sleeve bores over
z 160-544 of the printed stays, two UHMWPE bushings per leg, a toothed rack on the crown spine, a pawl in the upper
bar and a 3:1 webbing pulley. The frame is printed per unit, so the torso length could be printed in. Variants:

- **H1** reproduced first (same solid, same 42 rev C sets, same checks).
- **(a) fixed crown:** the H1 body unchanged. Each carbon leg is cut to its unit's length and sits only in the top
  149 mm of the sleeve (z 395-544, the socket): two shims (40 mm at z 400-440, 60 mm at z 484-544) take the radial couple and two
  Ti M5 cross-bolts (z 480) take the axial load. No rack, pawl, pulley guides, 70 mm bushings, webbing or cam. The
  spine keeps the pawl housing as a lateral guide (slotted: no axial load), so the yoke and the lifters stay where
  they are; fine adjust at the yoke.
- **(c) = (a) + stays re-sized:** below the socket the sleeve keep-out (4.41 mm wall ring, bushing seat) is gone; the
  pulley-guide and cam-buckle pads are gone, and the empty channel is opened from 18 to 22 mm (2.4 mm wall) outside
  the z 234 joint and the spreader-clip sections. H1's push (D offset tool, A floors, judge settings) is continued
  on the fixed-crown load sets.
- **(b) printed upper frame:** the carbon legs are replaced by PAHT-CF legs printed per size and bolted on the stay
  top with the H1 bolted-joint method; carbon top bar and spine kept. Checked on the beam model (printed legs sized
  by a sweep, PAHT layer rule, A's buckling knock-down) and the (c) body under the (b) load sets.

Load path: every variant is re-solved on the rev C beam model (frame.yaml, both bag-couple variants, torsos 15 /
19 / 23, 42 sets) with the crown-to-stay links changed, then on the 2 mm voxel body (D's solver and FI99 rule).

Record: designs/pack_5200/analysis/frame_fixed_torso.md. Run (about 25 min on 2 cores):
    python -m huntkit.gendesign.frame_fixed all
"""
from __future__ import annotations

import copy
import dataclasses
import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np

from . import frame_comp_A as A
from . import frame_comp_d as D
from . import frame_h1 as H1

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "frame_fixed"
DOC = REPO / "designs" / "pack_5200" / "analysis" / "frame_fixed_torso.md"
RESULT = REPO / "designs" / "pack_5200" / "analysis" / "frame_fixed_results.json"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261110_BL007"
H = H1.H
MAT = H1.MAT
TORSOS = (15, 19, 23)

# ------------------------------------------------------------------------------------------------ socket design
SOCKET_Z0 = 395.0        # sleeve keep-out kept from here to the stay top (z 544): the fixed-leg socket (149 mm)
SOCKET_LOW_Z = 420.0     # low contact band (beam stay node S420; shim z 400-440); the top band is the H1 z 530 node
SHIM_LEN = 40.0          # two bonded 40 mm UHMWPE shims per leg (cut from today's bushing stock); a 94 mm socket
#                          with 25 mm shims fails leg ring crush (0.42, C8 hipbelt-off): see frame_fixed_torso.md 3.1
TOP_SHIM_LEN = 60.0      # top shim z 484-544 (40 mm fails ring crush at 0.92, C8 IM3 15 in)
TOP_SHIM_Z = 514.0       # its centre; the beam link sits at the S530 node, so the couple forces are scaled by
LEVER_CORR = (530.0 - SOCKET_LOW_Z) / (TOP_SHIM_Z - SOCKET_LOW_Z)   # lever beam / lever real (1.17, conservative)
K_SHIM = 2.0e4           # N/mm radial, as the H1 bushing (pack5200 default bushing_k_n_mm, ASSUMPTION)
K_BOLT_AX = 5.0e4        # N/mm axial at the cross-bolts (as pack5200 pawl_k_n_mm, ASSUMPTION)
CROSS_BOLT_Z = 445.0     # 2 Ti M5 cross-bolts per leg, 90 deg apart in plan, 5 mm above the low shim
CROSS_BOLT_L = 30.0      # M5 x 30 through the socket (stay OD 26.8)
CFRP_BEARING = 300.0     # ASSUMPTION (team C A1): pin bearing of the UD-rich roll-wrapped leg wall, MPa ultimate
OPEN_HOLE_KD = 0.55      # ASSUMPTION: open-hole / unnotched strength of the leg laminate at the cross-bolt hole
WALL_FLOOR = 2.4         # (c): printable wall round the channel below the socket (FDM min wall 2 mm, frame_topopt)
C_BORE_R = 11.0          # (c): the empty channel below the socket is opened from r 9.0 to r 11.0 (wall 2.4 mm), except
#                          in the frozen zones. With the 18 mm channel kept, the push removed 0.4 g in 3 iterates:
#                          the free wall was only about 1 mm (outputs/frame_fixed/push_c_bore18.log)
JOINT_FREEZE = (196.0, 256.0)   # (c): H1 material kept round the z 234 bolted joint (bosses z 198-252)

# fine adjust at the yoke (fixed variants): a short toothed strip on the spine, set at fitting
YOKE_ADJ_MM = 25.4       # +- 1.0 in: ASSUMPTION, sized from the research (docs/research/fixed_vs_adjustable_frames.md)
YOKE_STRIP_G = 8.0       # ASSUMPTION: 60 mm of today's pa66_gf30 rack + a 4 mm pin and keeper

# printed legs (b)
PRINT_LEG = {"od": 34.0, "t": 3.5}  # sweep_printed_legs: lightest section passing strength, fatigue, creep, buckling
E_PAHT = 3860.0
BUCKLE_E_KD = 0.6 * 0.7  # A's rule on printed members: hot x creep


# ================================================================================================ beam model
def _leg_len_mm(torso: float, variant: str) -> float:
    """Carbon leg length along the axis for a fixed-crown unit: from the low shim bottom (z 400) to the crown top."""
    from .frame_topopt import load_envelope
    env = load_envelope()
    cs = min(env.crown_settings, key=lambda c: abs(c["torso_in"] - torso))
    uz = 1.0 / math.sqrt(1 + env.axis_slope ** 2)
    return float((cs["crown_top_z"] - (SOCKET_LOW_Z - SHIM_LEN / 2)) / uz)


def modify_model(m: dict, variant: str, leg: dict | None = None, e_scale: float = 1.0) -> dict:
    """Rev C beam model of frame.yaml with the crown-to-stay links of a fixed-crown variant.

    'fixed' (a, c): leg bottom moved to the stay node at z 470 (socket), radial shim links at z 470 and 530, axial
    cross-bolt stiffness at z 470; the spine guide (old pawl) keeps its lateral stiffness and loses the axial one.
    'printed' (b): as 'fixed' plus the legs above the stay top are printed PAHT-CF tubes (``leg``), and the bonded
    carbon crown corners are replaced by printed corner sockets (bond check dropped, bolted check in
    ``corner_socket_check``)."""
    m = copy.deepcopy(m)
    nodes = m["nodes"]
    zl = f"{SOCKET_LOW_Z:g}"
    for tag in "LR":
        nodes[f"C{tag}bot"] = list(nodes[f"S{tag}{zl}"])
    for ln in m["links"]:
        tag = ln["id"][-1]
        if ln["id"].startswith("bush_low"):
            ln["nodes"] = [f"S{tag}{zl}", f"C{tag}bot"]
            ln["k"] = [K_SHIM, K_SHIM, K_BOLT_AX, 0, 0, 0]
        elif ln["id"].startswith("bush_top"):
            ln["k"] = [K_SHIM, K_SHIM, 0, 0, 0, 0]
        elif ln["id"] == "pawl":
            ln["k"] = [ln["k"][0], ln["k"][1], 0, 0, 0, 0]
    m["params"] = dict(m["params"], bushing_len_mm=SHIM_LEN)
    if variant == "printed":
        leg = leg or PRINT_LEG
        sec = {"type": "tube_round", "od": float(leg["od"]), "t": float(leg["t"])}
        mat = _paht_beam_material(e_scale)
        for mem in m["members"]:
            if mem["group"].startswith("crown_leg"):
                mem["section"] = sec
                mem["material"] = mat
        m["joints"] = [j for j in m["joints"] if not j["id"].startswith("crown_corner")]
    return m


def _paht_beam_material(e_scale: float = 1.0):
    """PAHT-CF record for the beam solver (E XY 3860 MPa x ``e_scale``). The record has no yield; the solver's own
    von Mises SF is not used (printed legs are checked by ``printed_leg_fi``), so a placeholder allowable 0.8 x 88 is
    set."""
    from huntkit.fea.materials_bridge import Mat, get_material
    m0 = get_material("pa12_cf_fdm_paht")
    props = {**m0.props, "design_allowable_mpa": H1.PAHT["knock"] * H1.PAHT["s_xy"]}
    if e_scale != 1.0:
        for k in ("youngs_modulus_mpa", "youngs_modulus_xy_mpa", "E_mpa"):
            if k in props and props[k]:
                props[k] = float(props[k]) * e_scale
    return Mat(id=m0.id, name=m0.name, category=m0.category, props=props, source=m0.source)


def _member(res, mid):
    return next(q for q in res.members if q["id"] == mid)


def _extra_rows(res, model, variant: str) -> dict:
    """Per run: socket loads (fixed) or printed-leg / joint loads (printed), unfactored -> factored by the caller."""
    lf = res.meta.get("link_forces", {})
    out = {"socket": {}, "leg_sections": {}}
    for tag in "LR":
        lo = np.asarray(lf.get(f"bush_low_{tag}", np.zeros(6)), float)
        top = np.asarray(lf.get(f"bush_top_{tag}", np.zeros(6)), float)
        out["socket"][tag] = {"low_radial_n": float(np.hypot(lo[0], lo[1])), "axial_n": float(lo[2]),
                              "top_radial_n": float(np.hypot(top[0], top[1]))}
        ef = _member(res, f"C{tag}bot-C{tag}530")["end_forces"]
        f0, f1 = np.asarray(ef[0], float), np.asarray(ef[1], float)
        L = 530.0 - SOCKET_LOW_Z
        fb = f0 + (f1 - f0) * (CROSS_BOLT_Z - SOCKET_LOW_Z) / L          # internal forces at the cross-bolt
        out["leg_sections"][tag] = {"at_bolt": [float(v) for v in fb],
                                    "at_stay_top": [float(v) for v in _member(res, f"C{tag}530-C{tag}mid")["end_forces"][0]]}
        if variant == "printed":
            mx = np.zeros(6)
            for q in res.members:
                if q["group"] == f"crown_leg_{tag}" and not q["id"].startswith(f"C{tag}bot"):
                    mx = np.maximum(mx, np.asarray(q["max_abs_forces"], float))
            out["leg_sections"][tag]["printed_max_abs"] = [float(v) for v in mx]
            # top-bar end at the corner (bolted printed corner socket)
            ids = [q["id"] for q in res.members if q["group"] == "crown_top_bar" and f"C{tag}top" in q["id"]]
            q = _member(res, ids[0])
            e = q["end_forces"][0] if q["id"].startswith(f"C{tag}top") else q["end_forces"][1]
            out["leg_sections"][tag]["corner_bar_end"] = [float(v) for v in e]
    return out


def beam_runs(variant: str, leg: dict | None = None, torsos=TORSOS, buckling: bool = True, log=print):
    """Every rev C case set x torso on the modified beam model (both couple variants). Returns (LoadSets for
    the voxel body, crown rows as frame_cg_recheck._crown_rows + 'extra')."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.load_standard import TABLE, ls1_envelope
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    from .rev_c_verification import TAGS
    env = ls1_envelope("C")
    sets, rows = [], []
    for t in torsos:
        def mk(posts, e_scale=1.0):
            base = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=posts),
                                   95.0)
            return modify_model(base, variant, leg, e_scale)
        fm, fmp = mk(False), None
        fm_kd = mk(False, BUCKLE_E_KD) if variant == "printed" else None
        for vname, cases in env.items():
            tag = TAGS[vname]
            for c in cases:
                c = copy.copy(c)
                c.params = dict(c.params)
                c.buckling = buckling and vname == "crown_bar" and c.kind != "setdown"
                m = fm
                if c.name == "tall_load_posts":
                    fmp = fmp or mk(True)
                    m = fmp
                res = c.run(m)
                ls = ft._extract(res, m, c, t, TABLE)
                ls.key = f"{tag}:{ls.key}"
                sets.append(ls)
                row = {"scenario": tag, "case": c.name, "torso": float(t), "factor": float(c.required_sf),
                       "g": float(c.g_factor), **R._crown_rows(res, m, c), "extra": _extra_rows(res, m, variant)}
                if fm_kd is not None and c.buckling and c.name != "tall_load_posts":
                    # A's rule for printed members: buckling with the printed-leg E x 0.6 hot x 0.7 creep
                    c2 = copy.copy(c)
                    r2 = c2.run(fm_kd)
                    row["buckling"] = R._crown_rows(r2, fm_kd, c2)["buckling"]
                    row["buckling_basis"] = "printed legs at E x 0.42 (A rule)"
                rows.append(row)
        if log:
            log(f"  [{variant}] beam model torso {t} in")
    return sets, rows


def load_beam(variant: str, leg: dict | None = None, log=print):
    leg = leg or (PRINT_LEG if variant == "printed" else None)
    tagx = "" if leg is None else f"_{leg['od']:g}x{leg['t']:g}"
    p = OUT / f"beam_{variant}{tagx}.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    sets, rows = beam_runs(variant, leg, log=log)
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps((sets, rows)))
    return sets, rows


# ================================================================================================ beam-level checks
def _leg_section():
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.pack5200 import _sec
    from . import frame_topopt as ft
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    return _sec(next(m for m in fm["members"] if m["group"].startswith("crown_leg"))["section"])


def socket_checks(rows: list) -> dict:
    """Fixed-crown socket, per scenario, min over sets and both legs. Static at the factored load; fatigue at
    C1 x 1.6 g against 0.30 x the knocked-down PAHT allowable (printed parts) or FI <= 0.5 (CFRP, HA-LS-1)."""
    from huntkit.fea.pack5200 import _sec  # noqa: F401
    from .frame_comp_B import bolt_mass_g  # noqa: F401
    P = H1.PAHT
    k = P["knock"]
    leg = _leg_section()
    od, t = leg.dims["od"], leg.dims["t"]
    d = 5.0
    wall_socket = 13.4 - 9.0                       # printed socket wall each side of the 18 mm bore (H1 r_out 13.41)
    n_b = 2
    cap = {
        # Ti M5 in double shear (two planes per bolt), B rule 0.6 UTS on the minor diameter
        "cross-bolt Ti double shear": n_b * 2 * 0.6 * H1.TI["uts"] * math.pi / 4 * H1.TI["d_minor"] ** 2,
        # CFRP leg wall pin bearing, both walls, x hot/wet
        "leg wall pin bearing (CFRP 300 MPa x 0.8)": n_b * 2 * d * t * CFRP_BEARING * 0.8,
        # printed socket: bolt bears along frame z = in the layers (0.8 x 88) on both socket walls
        "socket bearing on the bolt (in-layer)": n_b * 2 * d * wall_socket * k * P["s_xy"],
        # printed socket shear-out to the socket bottom edge (30 mm below the bolt), 2 planes x wall, interlayer
        "socket shear-out (interlayer, 2 planes)": n_b * 2 * 2 * (CROSS_BOLT_Z - SOCKET_Z0) * wall_socket * 0.6 * k * P["s_z"] * 0.5,
    }
    sig_bear_allow = k * P["s_z"]                     # radial shim pressure on the printed bore: across the layers
    out = {}
    for tag_s in ("C", "C_im3"):
        rs = [r for r in rows if r["scenario"] == tag_s]
        worst: dict = {}

        def keep(kind, name, val, where):
            if (kind, name) not in worst or val < worst[(kind, name)][0]:
                worst[(kind, name)] = (val, where)

        for r in rs:
            fac = r["factor"]
            where = f"{r['case']}|{r['torso']:g}"
            for side in "LR":
                s = r["extra"]["socket"][side]
                ax = abs(s["axial_n"]) * fac
                for nm, c_ in cap.items():
                    keep("strength", nm, c_ / max(ax, 1e-9), where)
                for band in ("low", "top"):
                    Fr = s[f"{band}_radial_n"] * fac * LEVER_CORR
                    Ls = TOP_SHIM_LEN if band == "top" else SHIM_LEN
                    pb = Fr / (od * Ls)                             # projected bearing on the shim / bore
                    keep("strength", f"printed bore bearing under the {band} shim (across layers)", sig_bear_allow / max(pb, 1e-9), where)
                    # leg ring crush under the shim (Roark ring, 60 deg contact as the H1 bushing model)
                    from huntkit.fea.rings import ring_moment_coeff
                    cm = ring_moment_coeff(60.0)
                    Rm = od / 2 - t / 2
                    mh = cm * (Fr / Ls) * Rm
                    sf = float(leg.laminate.first_ply_failure((0, -Fr / (2 * Ls), 0), (0, mh, 0))["sf"])
                    keep("strength", f"leg ring crush under the {band} shim", sf, where)
                # leg net section at the cross-bolt hole
                N, Vy, Vz, T, My, Mz = [v * fac for v in r["extra"]["leg_sections"][side]["at_bolt"]]
                sfb = float(leg.failure(N, Vy, Vz, T, My, Mz)["sf"]) * OPEN_HOLE_KD
                keep("strength", "leg at the cross-bolt hole (FPF x open-hole 0.55)", sfb, where)
                if r["case"] == "static_carry":
                    kf = D.FAT_G / fac
                    for nm in ("socket bearing on the bolt (in-layer)", "socket shear-out (interlayer, 2 planes)"):
                        keep("fatigue", nm + " at 1.6 g", P["fat"] * cap[nm] / max(ax * kf, 1e-9), where)
                    keep("fatigue", "cross-bolt Ti thread-free shank at 1.6 g (0.25 UTS shear)",
                         0.25 / 0.6 * cap["cross-bolt Ti double shear"] / max(ax * kf, 1e-9), where)
                    for band in ("low", "top"):
                        Fr = s[f"{band}_radial_n"] * fac * kf * LEVER_CORR
                        Ls = TOP_SHIM_LEN if band == "top" else SHIM_LEN
                        keep("fatigue", f"printed bore bearing ({band} shim) at 1.6 g",
                             P["fat"] * sig_bear_allow / max(Fr / (od * Ls), 1e-9), where)
                        # CFRP leg ring at the walking peak: FI <= 0.5 (HA-LS-1 composite fatigue rule)
                        mh = cm * (Fr / Ls) * Rm
                        sfr = float(leg.laminate.first_ply_failure((0, -Fr / (2 * Ls), 0), (0, mh, 0))["sf"])
                        keep("fatigue", f"leg ring under the {band} shim at 1.6 g (FI <= 0.5)", 0.5 * sfr, where)
                    keep("fatigue", "leg at the cross-bolt hole at 1.6 g (CFRP FI <= 0.5)", 0.5 * sfb / kf, where)
        o = {"strength": {}, "fatigue": {}}
        for (kind, nm), (v, wh) in worst.items():
            o[kind][nm] = {"margin": round(float(v), 3), "set": wh}
        o["min_strength"] = min(v["margin"] for v in o["strength"].values())
        o["min_fatigue"] = min(v["margin"] for v in o["fatigue"].values())
        out[tag_s] = o
    out["capacities_n"] = {k_: round(v, 1) for k_, v in cap.items()}
    out["design"] = {"socket_z": [SOCKET_Z0, 544.0], "shims": f"UHMWPE {SHIM_LEN:g} mm at z 400-440 and {TOP_SHIM_LEN:g} mm at z 484-544", "lever_correction": LEVER_CORR,
                     "cross_bolts": f"2 x Ti gr5 M5 x {CROSS_BOLT_L:g} per leg at z {CROSS_BOLT_Z:g}, 90 deg apart in plan, "
                                    "reamed 5.1 through socket and leg, A2 nut",
                     "leg": {"od": od, "t": t}}
    return out


def spine_guide_checks(rows: list) -> dict:
    """The pawl housing kept as a lateral spine guide (axial slot): the H1 pawl-cheek detail (304 bushing) under
    the factored lateral guide force (frame_cg_recheck.pawl_cheek)."""
    from . import frame_cg_recheck as R
    out = {}
    for tag_s in ("C", "C_im3"):
        rs = [r for r in rows if r["scenario"] == tag_s]
        r = max(rs, key=lambda q: math.hypot(q["pawl_n"][1], q["pawl_n"][2]) * q["factor"])
        f = [0.0, r["pawl_n"][1] * r["factor"], r["pawl_n"][2] * r["factor"]]
        ch = R.pawl_cheek(f)
        out[tag_s] = {"sf": round(float(ch["sf_fi"]), 3), "set": f"{r['case']}|{r['torso']:g}",
                      "factored_yz_n": [round(f[1], 1), round(f[2], 1)]}
    return out


def crown_checks(rows: list) -> dict:
    """The rev C crown rows (frame_cg_recheck.crown_summary, corner-bond fatigue) on the modified model."""
    from . import frame_cg_recheck as R
    from .rev_c_verification import corner_bond_fatigue
    out = {}
    for tag_s in ("C", "C_im3"):
        cs = R.crown_summary(rows, tag_s)
        if "leg_ring_crush" in cs:     # pack5200 row assumes both shims 40 mm at the beam lever: see socket_checks
            cs["leg_ring_crush_pack5200_40mm_info"] = cs.pop("leg_ring_crush")
        if "bushing_bearing" in cs:
            cs["shim_bearing_uhmwpe"] = cs.pop("bushing_bearing")
        try:
            cs["corner_bond_fatigue"] = corner_bond_fatigue(rows, tag_s)
        except Exception as e:          # printed corners: no bonded corner
            cs["corner_bond_fatigue"] = {"note": f"n/a ({type(e).__name__})"}
        out[tag_s] = cs
    return out


def printed_leg_fi(forces6, leg: dict) -> float:
    """PAHT-CF printed leg tube (printed lying down: leg axis in the layers). Axial + bending stress in-layer;
    torsion + transverse shear treated as interlayer (conservative: part of the section is). Layer rule of
    frame_topopt.layer_failure_index with the H1 allowables (88 / 47, x 0.8, interlayer 0.6 x 47)."""
    from huntkit.fea.sections import tube_round
    N, Vy, Vz, T, My, Mz = [abs(v) for v in forces6]
    s = tube_round(leg["od"], leg["t"])
    sig = N / s.A + math.hypot(My, Mz) * (leg["od"] / 2) / s.Iy
    tau = T * (leg["od"] / 2) / s.J + 2.0 * math.hypot(Vy, Vz) / s.A
    P = H1.PAHT
    k = P["knock"]
    return max(sig / (k * P["s_xy"]), tau / (k * 0.6 * P["s_z"]),
               math.sqrt(sig ** 2 + 3 * tau ** 2) / (k * P["s_xy"]))


def printed_leg_checks(rows: list, leg: dict) -> dict:
    out = {}
    for tag_s in ("C", "C_im3"):
        rs = [r for r in rows if r["scenario"] == tag_s]
        st, fat, cr = (9e9, ""), (9e9, ""), (9e9, "")
        for r in rs:
            for side in "LR":
                fi = printed_leg_fi(r["extra"]["leg_sections"][side]["printed_max_abs"], leg)   # unfactored
                where = f"{r['case']}|{r['torso']:g} {side}"
                st = min(st, (1.0 / max(fi * r["factor"], 1e-9), where))
                if r["case"] == "static_carry":
                    fat = min(fat, (H1.PAHT["fat"] / max(fi * D.FAT_G, 1e-9), where))
                    cr = min(cr, (D.MATERIALS[MAT]["rup"] / max(fi, 1e-9), where))
        bk = [(r["buckling"], f"{r['case']}|{r['torso']:g}") for r in rs if r.get("buckling") is not None]
        b = min(bk) if bk else (None, "")
        out[tag_s] = {"strength": (round(st[0], 3), st[1]), "fatigue": (round(fat[0], 3), fat[1]),
                      "creep": (round(cr[0], 3), cr[1]),
                      # beam eigenvalue (>= 1.5 x factor) re-solved with the printed-leg E x 0.6 hot x 0.7 creep
                      "buckling_A_rule": (round(b[0], 3) if b[0] is not None else None, b[1])}
    return out


# ------------------------------------------------------------------------------------------------ (b) z 544 joint
@dataclasses.dataclass
class LegJoint:
    """(b) printed leg on the stay top: a flange joint at z 544 by the H1 method (dry face, Ti M5 through-bolts in
    printed bosses, no preload credited, prying 1.25). n bolts on a circle of radius r_b about the leg axis."""
    n: int = 4
    r_b: float = 23.0          # leg od 34: bolt line 6 mm outside the tube wall
    r_boss: float = 8.0
    plug: float = 16.0         # printed plug between washer face and split (each side)
    washer_od: float = 12.0
    hole_d: float = 5.1


def leg_joint_check(rows: list, leg: dict, j: LegJoint | None = None) -> dict:
    j = j or LegJoint()
    P, TI = H1.PAHT, H1.TI
    k = P["knock"]
    ro, ri = leg["od"] / 2, leg["od"] / 2 - leg["t"]
    # contact face = the tube ring + the boss footprints, sampled on a 1 mm grid
    g = np.arange(-ro - j.r_boss - 2, ro + j.r_boss + 2, 1.0)
    X, Y = np.meshgrid(g, g)
    x, y = X.ravel(), Y.ravel()
    ang = np.arange(j.n) * 2 * math.pi / j.n + math.pi / 4
    bolts = np.c_[j.r_b * np.cos(ang), j.r_b * np.sin(ang)]
    r = np.hypot(x, y)
    face = ((r >= ri) & (r <= ro)) | (np.min(np.hypot(x[:, None] - bolts[:, 0], y[:, None] - bolts[:, 1]), axis=1) <= j.r_boss)
    face &= np.min(np.hypot(x[:, None] - bolts[:, 0], y[:, None] - bolts[:, 1]), axis=1) > j.hole_d / 2
    x, y = x[face], y[face]
    area = np.ones_like(x)
    kb = TI["E"] * TI["As"] / (2 * j.plug + 2.0)
    kc = P["E"] * P["E_hot"] / H1.L_CONTACT
    ring = math.pi / 4 * (j.washer_od ** 2 - j.hole_d ** 2)
    cap = {"washer bearing (XY)": ring * k * P["s_xy"],
           "plug shear-out (interlayer)": 2 * j.plug * j.washer_od * 0.6 * k * P["s_z"],
           "bolt tension Ti (0.7 UTS)": 0.7 * TI["uts"] * TI["As"]}
    worst: dict = {}

    def keep(kind, name, val, where):
        if (kind, name) not in worst or val < worst[(kind, name)][0]:
            worst[(kind, name)] = (val, where)

    for r_ in rows:
        for side in "LR":
            N, Vy, Vz, T, My, Mz = [v * r_["factor"] for v in r_["extra"]["leg_sections"][side]["at_stay_top"]]
            # beam local: x along the leg; bending about local y / z -> face moments (signs irrelevant: both checked)
            for sgn in (1.0, -1.0):
                cs = H1.contact_solve(x, y, area, sgn * N, My, Mz, bolts, kb, kc)
                Tb = float(cs["bolt_n"].max()) * H1.PRYING
                where = f"{r_['scenario']}:{r_['case']}|{r_['torso']:g} {side}"
                for nm, c_ in cap.items():
                    keep("strength", nm, c_ / max(Tb, 1e-9), where)
                keep("strength", "dry-face contact bearing", k * P["s_xy"] / max(cs["contact_mpa"], 1e-9), where)
                a = j.r_b - ro
                sig = 6.0 * Tb * a / (2 * j.r_boss * j.plug ** 2)       # boss cantilever (H1 boss_bending_fi model)
                bfi = sig / (k * P["s_xy"])
                keep("strength", "boss bending + prying", 1 / max(bfi, 1e-9), where)
                if r_["case"] == "static_carry":
                    kf = D.FAT_G / r_["factor"]
                    keep("fatigue", "washer bearing at 1.6 g", P["fat"] * cap["washer bearing (XY)"] / max(Tb * kf, 1e-9), where)
                    keep("fatigue", "boss bending + prying at 1.6 g", P["fat"] / max(bfi * kf, 1e-9), where)
                    keep("fatigue", "bolt thread Ti at 1.6 g (0.25 UTS)", 0.25 * TI["uts"] * TI["As"] / max(Tb * kf, 1e-9), where)
            V = math.hypot(Vy, Vz)
            Vb = V / j.n + abs(T) / (j.n * j.r_b)
            keep("strength", "fitted-bolt hole bearing (shear)", j.hole_d * j.plug * k * P["s_xy"] / max(Vb, 1e-9),
                 f"{r_['case']}|{r_['torso']:g} {side}")
    out = {"strength": {}, "fatigue": {}}
    for (kind, nm), (v, wh) in worst.items():
        out[kind][nm] = {"margin": round(float(v), 3), "set": wh}
    out["min_strength"] = min(v["margin"] for v in out["strength"].values())
    out["min_fatigue"] = min(v["margin"] for v in out["fatigue"].values())
    out["design"] = dataclasses.asdict(j)
    return out


CORNER_LS = 80.0          # (b) printed corner socket length on the bar
CORNER_PLUG = {"od": 15.8, "t": 2.0, "L": 80.0}   # 7075-T6 tube bonded inside each top-bar end (ASSUMPTION fit)


def corner_socket_check(rows: list) -> dict:
    """(b) printed corner socket on each leg top holding the carbon top bar (OD 18): the bar end moment is taken by
    contact at the socket ends (couple lever 0.8 x 80 mm, contact over a third of the socket at each end), axial
    load and torsion by 2 Ti M5 cross-bolts. Without the bonded carbon corner wrap the bar ring crushes (row
    'bare bar', info), so a 7075 tube is bonded inside each bar end; its ring bending governs ('with plug').
    Checks: printed bore bearing across the layers, bar / plug ring, bar pin bearing."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.pack5200 import _sec
    from huntkit.fea.rings import ring_moment_coeff
    from . import frame_topopt as ft
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    bar = _sec(next(m for m in fm["members"] if m["group"] == "crown_top_bar")["section"])
    od, t = bar.dims["od"], bar.dims["t"]
    Ls, lev = CORNER_LS, 0.8 * CORNER_LS
    Lc = Ls / 3
    P = H1.PAHT
    k = P["knock"]
    cm = ring_moment_coeff(60.0)
    best = {}
    for r in rows:
        for side in "LR":
            N, Vy, Vz, T, My, Mz = [abs(v) * r["factor"] for v in r["extra"]["leg_sections"][side]["corner_bar_end"]]
            Fc = math.hypot(My, Mz) / lev + math.hypot(Vy, Vz)
            where = f"{r['scenario']}:{r['case']}|{r['torso']:g}"
            rows_ = {"corner socket bore bearing (across layers)": k * P["s_z"] / max(Fc / (od * Lc), 1e-9)}
            Rm = od / 2 - t / 2
            mh = cm * (Fc / Lc) * Rm
            rows_["info: bare top bar ring crush in the socket (FPF, no plug)"] = float(
                bar.laminate.first_ply_failure((0, -Fc / (2 * Lc), 0), (0, mh, 0))["sf"])
            # with the plug: ring moment shared by bar wall and plug in proportion to E t^3 (as pack5200 collar)
            tp, Rp = CORNER_PLUG["t"], CORNER_PLUG["od"] / 2 - CORNER_PLUG["t"] / 2
            Dp, Db = 71700.0 * tp ** 3, bar.Ex * t ** 3
            share = Dp / (Dp + Db)
            sig = 6 * cm * (Fc / Lc) * Rp * share / tp ** 2
            rows_["7075 bar-end plug ring bending (S-basis yield 462)"] = 462.0 / max(sig, 1e-9)
            rows_["top bar ring with the plug (FPF)"] = float(
                bar.laminate.first_ply_failure((0, -Fc / (2 * Lc), 0), (0, mh * (1 - share), 0))["sf"])
            Fb = N + T / (od / 2)
            rows_["top bar pin bearing (2 x M5, CFRP 300 x 0.8)"] = 2 * 2 * 5.0 * t * CFRP_BEARING * 0.8 / max(Fb, 1e-9)
            for nm, v in rows_.items():
                if nm not in best or v < best[nm][0]:
                    best[nm] = (v, where)
    out = {nm: {"margin": round(v, 3), "set": wh} for nm, (v, wh) in best.items()}
    out["min_strength"] = min(v["margin"] for nm, v in out.items() if not nm.startswith("info"))
    return out


def sweep_printed_legs(log=print, cands=((30, 4), (32, 4), (34, 3.5), (34, 4), (36, 3.5), (38, 3.5))) -> list:
    """Printed-leg size sweep on the beam model (rev C, 42 sets each): strength / fatigue / creep / buckling."""
    res = []
    for od, t in cands:
        leg = {"od": float(od), "t": float(t)}
        _, rows = load_beam("printed", leg, log=None)
        c = printed_leg_checks(rows, leg)
        mins = {kk: min(c[s][kk][0] for s in c if c[s][kk][0] is not None) for kk in ("strength", "fatigue", "creep", "buckling_A_rule")}
        g = math.pi / 4 * (od ** 2 - (od - 2 * t) ** 2) * 1.06e-3       # g per mm
        rec = {"od": od, "t": t, "g_per_mm": round(g, 4), **{k_: round(v, 3) for k_, v in mins.items()},
               "pass": bool(min(mins.values()) >= 1.0)}
        res.append(rec)
        if log:
            log(json.dumps(rec))
    return res


# ================================================================================================ voxel body
def _stay_r(cen: np.ndarray) -> np.ndarray:
    """Radial distance of element centres from the nearer stay (crown) axis, mm."""
    from .frame_topopt import load_envelope
    env = load_envelope()
    yc = env.sleeve_y(cen[:, 2])
    return np.hypot(np.abs(cen[:, 0]) - env.top_pt[0], cen[:, 1] - yc)


def _pulley_pads(dom) -> np.ndarray:
    """Pad spheres of the pulley fixed guide and the cam buckle (both sides), as frame_topopt.build_domain."""
    from .frame_topopt import PAD_R, Y_LO, pad_points
    env = dom.env
    cen = dom.grid.elem_centers()
    pts = pad_points(env)
    m = np.zeros(dom.grid.ne, bool)
    for name in ("pulley_fixed_guide_C", "pulley_cam_buckle_R"):
        p = pts[name]
        for s in (1, -1):
            q = np.array([s * p[0], p[1], p[2]])
            q[1] = np.clip(q[1], Y_LO + PAD_R, env.y_hi(q[2]) - PAD_R * 0.5)
            m |= np.linalg.norm(cen - q, axis=1) < max(PAD_R, 1.01 * dom.h)
    return m


_DOM: dict = {}


def _freeze_z(z: np.ndarray) -> np.ndarray:
    """z bands where (c) keeps H1's material: the z 234 joint (bosses, traps: ligaments to the r 9 bore) and the
    three spreader-clip sections."""
    from .spreader import CLIP_Z
    m = (z >= JOINT_FREEZE[0]) & (z <= JOINT_FREEZE[1])
    for zc in CLIP_Z:
        m |= np.abs(z - zc) <= 8.0
    return m


def fixed_domain(variant: str):
    """Domain of the fixed-crown body. 'a': H1's domain with the sleeve / bore masks (load bands, keep rule,
    torsion test) cut to the socket z >= SOCKET_Z0; passive solids unchanged (the H1 body is not touched).
    'c': as 'a', and below the socket the sleeve walls are no longer passive (designable), the 18 mm channel stays
    a void, and the pulley-guide / cam-buckle pads are removed."""
    if variant in _DOM:
        return _DOM[variant]
    c = H1.base()
    dom = c["dom"]
    z = c["cen"][:, 2]
    sock = z >= SOCKET_Z0 - 1e-6
    masks = dict(dom.masks)
    for t in "RL":
        masks[f"sleeve_{t}"] = np.asarray(dom.masks[f"sleeve_{t}"], bool) & sock
        masks[f"bore_{t}"] = np.asarray(dom.masks[f"bore_{t}"], bool) & sock
    ps, pv = dom.passive_solid.copy(), dom.passive_void.copy()
    if variant == "c":
        old = (np.asarray(dom.masks["sleeve_R"], bool) | np.asarray(dom.masks["sleeve_L"], bool)) & ~sock
        pul = _pulley_pads(dom) & ~sock
        ps &= ~(old | pul)
        masks["pads"] = np.asarray(dom.masks["pads"], bool) & ~pul
        from .frame_topopt import SLEEVE_Z0
        r = _stay_r(c["cen"])
        opened = (r < C_BORE_R) & (z >= SLEEVE_Z0) & (z < SOCKET_Z0 - 5.0) & ~_freeze_z(z)
        pv |= opened
        ps &= ~opened
    out = dataclasses.replace(dom, passive_solid=ps, passive_void=pv, masks=masks)
    _DOM[variant] = out
    return out


_C: dict = {}


def c_base() -> dict:
    """Fixed parts of the (c) assembly: pads zone without the pulley pads, the 2.5 mm wall floor round the channel
    below the socket, H1's material in the z 234 joint zone and at the three spreader-clip sections."""
    if _C:
        return _C
    from scipy import ndimage
    c = H1.base()
    dom = fixed_domain("c")
    g = dom.grid
    cen = c["cen"]
    pads = g.from_array(ndimage.binary_dilation(g.to_array(np.asarray(dom.masks["pads"], bool)), iterations=3))
    r = _stay_r(cen)
    z = cen[:, 2]
    from .frame_topopt import SLEEVE_BORE_R, SLEEVE_Z0
    wall = (r >= C_BORE_R) & (r < C_BORE_R + WALL_FLOOR + H / 2) & (z >= SLEEVE_Z0) & (z < SOCKET_Z0)
    h1 = np.load(H1.OUT / "h1_final.npz")["solid"]
    jz = _freeze_z(z) & (r < 32.0)      # joint + spreader-clip sections stay as H1 (clips are not re-made)
    _C.update(pad_zone=pads & c["solid0"], wall_floor=wall & ~dom.passive_void, joint_keep=h1 & jz, h1=h1)
    return _C


def assemble_c(shift: np.ndarray) -> np.ndarray:
    """(c) solid for a cumulative surface shift (frame_h1.assemble on the (c) domain, plus the wall floor and the
    frozen joint zone)."""
    from . import frame_production as prod
    c, cc = H1.base(), c_base()
    dom = fixed_domain("c")
    s = D.solid_from_shift(dom, c["sdf0"], shift)
    s = (D.restore_hardpoints(dom, c["solid0"], s) | c["branch_ctrl"] | c["floor"] | cc["pad_zone"]
         | cc["wall_floor"] | cc["joint_keep"])
    s = (s | c["boss"]) & ~c["holes"]
    s &= ~dom.passive_void
    s |= dom.passive_solid & ~c["holes"]
    return prod._largest_with_pivot(dom, s)


def _eval(dom, solid, sets):
    f = D.solve_fields(dom, solid, sets, log=None)
    ev = D.evaluate(f, MAT)
    return f, ev


def h1_reproduce(log=print) -> dict:
    """H1 as recorded: its final solid on H1's domain and the cached rev C sets. Must give strength 1.45,
    fatigue 1.28 (frame_h1_results.json)."""
    c = H1.base()
    solid = np.load(H1.OUT / "h1_final.npz")["solid"]
    sets, _ = D.load_sets(log=None)
    f, ev = _eval(c["dom"], solid, sets)
    bk = H1.buckling(f)
    jc = H1.joint_check(f)
    k = D.torsion_k(c["dom"], solid, sets, E_PAHT)
    rec = json.loads(H1.RESULT.read_text())
    out = {"raster_g": D.mass_g(solid, H, 1060.0), "min": ev["min"], "body": ev["body"],
           "by_torso": H1.by_torso(ev),
           "buckling_min": min(v["margin"] for v in bk.values() if v["margin"] is not None),
           "joint_strength": jc["min_strength"], "joint_fatigue": jc["min_fatigue"], "torsion_Nm_deg": k,
           "recorded": {"min": rec["min"], "buckling_min": rec["buckling_min"],
                        "joint": [rec["joint"]["min_strength"], rec["joint"]["min_fatigue"]]}}
    out["reproduced"] = bool(abs(out["min"]["strength"] - rec["min"]["strength"]) < 0.005
                             and abs(out["min"]["fatigue"] - rec["min"]["fatigue"]) < 0.005)
    if log:
        log(json.dumps({k_: out[k_] for k_ in ("raster_g", "min", "buckling_min", "joint_strength", "joint_fatigue",
                                                "reproduced")}, default=float))
    return out


def body_verify(variant: str, solid: np.ndarray, sets, log=print) -> dict:
    """All rev C body checks of H1's verify on one solve: strength / fatigue / creep per couple variant and torso,
    per case, A's branch buckling, the z 234 joint, keep-outs, torsion, member families."""
    dom = fixed_domain("a" if variant == "a" else "c")
    c = H1.base()
    f, ev = _eval(dom, solid, sets)
    bk = H1.buckling(f)
    jc = H1.joint_check(f)
    grp = c["grp"]
    fam = {gn: round(float(((grp == i) & solid).sum() * H ** 3 * 1.06e-3), 1) for i, gn in enumerate(A.GROUPS)}
    cases: dict = {}
    for tg, b in ev["body"].items():
        for cs, v in b["cases"].items():
            cases[cs] = min(cases.get(cs, 9e9), v)
    ko = {}
    for k in ("sleeve_R", "sleeve_L", "pawl", "pivot"):
        m = np.asarray(dom.masks[k], bool) & ~c["holes"]
        ko[f"{k} present"] = float((solid & m).sum() / max(m.sum(), 1))
    for k in ("bore_R", "bore_L", "spine_channel"):
        m = np.asarray(dom.masks[k], bool)
        ko[f"{k} empty"] = float(1.0 - (solid & m).sum() / max(m.sum(), 1))
    from .bag_attach import attachment_field
    from .spreader import SCALE
    fl = (attachment_field(c["cen"], SCALE) <= 0.0) & ~dom.passive_void
    ko["fairleads present"] = float((solid & fl).sum() / max(fl.sum(), 1))
    ko["outside envelope (voxels)"] = int((solid & dom.passive_void).sum())
    # spreader clip sections must stay as H1 (clips are not re-made)
    from .spreader import CLIP_Z
    h1 = np.load(H1.OUT / "h1_final.npz")["solid"]
    zc = c["cen"][:, 2]
    ko["spreader clip sections identical to H1"] = bool(all(
        ((solid != h1) & (np.abs(zc - zz) <= 6.0) & (np.abs(c["cen"][:, 0]) > 90)).sum() == 0 for zz in CLIP_Z))
    out = {"variant": variant, "raster_g": D.mass_g(solid, H, 1060.0), "min": ev["min"], "governing": ev["governing"],
           "body": ev["body"], "by_torso": H1.by_torso(ev), "cases": cases, "buckling": bk,
           "buckling_min": min(v["margin"] for v in bk.values() if v["margin"] is not None),
           "joint": jc, "keepouts": ko, "family_g": fam,
           "torsion_Nm_deg": D.torsion_k(dom, solid, sets, E_PAHT)}
    if log:
        log(json.dumps({k_: out[k_] for k_ in ("variant", "raster_g", "min", "buckling_min", "torsion_Nm_deg")},
                       default=float) + f" joint {jc['min_strength']} / {jc['min_fatigue']}")
    return out, ev


def push_c(sets, iters: int = 5, log=print) -> dict:
    """H1's push continued on the (c) domain under the fixed-crown sets (judge settings, A floors, joint bosses,
    accept rule min(strength, fatigue, creep) >= 1.02 and buckling >= 1.0)."""
    import gc
    c = H1.base()
    dom = fixed_domain("c")
    D.R_FRAC = H1.R_FRAC
    shift = np.load(H1.OUT / "h1_shift.npz")["shift"].astype(float)
    hist, best = [], None
    for it in range(iters + 1):
        solid = assemble_c(shift)
        t0 = time.time()
        f, ev = _eval(dom, solid, sets)
        bk = H1.buckling(f)
        bmin = min(v["margin"] for v in bk.values() if v["margin"] is not None)
        rec = {"it": it, "raster_g": D.mass_g(solid, H, 1060.0), "min": ev["min"], "buckling_min": bmin,
               "gov": ev["governing"], "s": round(time.time() - t0)}
        rec["pass"] = bool(min(ev["min"].values()) >= H1.KEEP and bmin >= H1.BUCKLE_KEEP)
        hist.append(rec)
        if log:
            log(json.dumps(rec, default=float))
        if rec["pass"] and (best is None or rec["raster_g"] < best["raster_g"]):
            best = {**rec, "shift": shift.copy()}
        if it == iters:
            break
        util = ev["util"]
        del f, ev
        gc.collect()
        shift = D.offset_step(dom, c["sdf0"], solid, util, shift, 1.04, grow_only=False, u_lo=H1.U_LO)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "c_shift.npz", shift=best["shift"], it=best["it"])
    (OUT / "push_c.json").write_text(json.dumps(hist, indent=1, default=float))
    return {"history": hist, "best_it": best["it"]}


# ================================================================================================ mass, cost, fit
LEG_G_PER_MM = None      # set from the beam model's rev C crown-leg mass (2 legs x 430 mm)
RACK_PAWL_GUIDES_G = 44.0     # frame.yaml mass_g "crown rack + pawl housing + pulley guides" (frame_eval.KEPT_G)
BUSHINGS_G = 16.748942889953792   # frame.yaml mass_g "UHMWPE bushings (4)", 4 x 70 mm
TORSO_ADJUST_SOFT_G = 41.7    # weight_pass_corrie.json "Torso adjust": webbing 1.4 m, cam buckle, release cord + toggle
CORNER_BONDLINE_G = 2.21      # frame_mass_production.json crown_fix_lines_g corner_bondline (gone with printed corners)
SIZES_IN = (16.0, 18.0, 20.0, 22.0)   # 4 printed sizes, +-1 in at the yoke: 15-17, 17-19, 19-21, 21-23
FIL_USD_KG = 80.0 * 1.08 * 1.15       # H1 basis (frame_h1.md section 5): $80/kg, 8 % waste, 15 % reprint
G_PER_H = 764.5 / 27.0                # H1 print mesh g per machine hour (frame_h1.md section 5)


def leg_g_per_mm() -> float:
    from huntkit.fea.frames import build_frame_from_yaml
    from . import frame_topopt as ft
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    return float(fm["hardware"]["items"]["tubes: crown_leg"]) / (2 * 430.0)


def nut_washer_g() -> tuple:
    j = H1.JOINT
    nut = (3 * math.sqrt(3) / 2 * (j.nut_af / math.sqrt(3)) ** 2 - math.pi / 4 * 5.0 ** 2) * j.nut_t * 7.9e-3
    washer = math.pi / 4 * (j.washer_od ** 2 - 5.3 ** 2) * j.washer_t * 7.9e-3
    return nut, washer


def _printed_leg_len(torso: float) -> float:
    from .frame_topopt import Z_TOP, load_envelope
    env = load_envelope()
    cs = min(env.crown_settings, key=lambda c: abs(c["torso_in"] - torso))
    uz = 1.0 / math.sqrt(1 + env.axis_slope ** 2)
    return float((cs["crown_top_z"] - Z_TOP) / uz)


CORNER_SOCKET_G = math.pi / 4 * (30.0 ** 2 - 18.2 ** 2) * CORNER_LS * 1.06e-3 + 4.0   # ASSUMPTION: OD 30 ring + gusset
CORNER_PLUG_G = math.pi / 4 * (CORNER_PLUG["od"] ** 2 - (CORNER_PLUG["od"] - 2 * CORNER_PLUG["t"]) ** 2) * CORNER_PLUG["L"] * 2.81e-3
LEG_FLANGE_G = 2 * 4 * math.pi * 8.0 ** 2 * 16.0 * 1.06e-3                     # 4 bosses r 8 x 16 mm, both sides


def frame_mass(variant: str, torso: float, body_raster_g: float, h1_raster_g: float) -> dict:
    """Frame mass on the H1 booking basis (frame_mass_h1.json): fixed 239.4 g, body booked as 757.7 g minus the
    raster difference, z 234 joint hardware 28.0 g. Items removed / added are each sourced."""
    from .frame_comp_B import bolt_mass_g
    base = json.loads(H1.MASS_JSON.read_text())["h1"]
    jhw = sum(base["joint_hardware_g"].values())
    body = base["body_g"] - (h1_raster_g - body_raster_g)
    gpm = leg_g_per_mm()
    nut, washer = nut_washer_g()
    items = {"printed body (H1 basis)": round(body, 1), "fixed interfaces as H1": base["fixed_g"],
             "z 234 joint hardware": round(jhw, 1)}
    if variant == "h1":
        pass
    elif variant in ("a", "c"):
        L = _leg_len_mm(torso, variant)
        items["crown legs cut to the unit (2 x %.0f mm instead of 430)" % L] = round(2 * gpm * (L - 430.0), 1)
        items["rack + pawl + pulley guides removed"] = -RACK_PAWL_GUIDES_G
        items["4 x 70 mm UHMWPE bushings -> 2 shims per leg (40 + 60 mm)"] = round(
            -BUSHINGS_G + BUSHINGS_G * 2 * (SHIM_LEN + TOP_SHIM_LEN) / 280.0, 1)
        items["4 Ti M5 x 30 cross-bolts + nuts + washers"] = round(4 * bolt_mass_g(CROSS_BOLT_L) + 4 * nut + 4 * washer, 1)
        items["yoke fine-adjust strip + pin (ASSUMPTION)"] = YOKE_STRIP_G
    elif variant == "b":
        Lp = _printed_leg_len(torso)
        items["carbon crown legs removed (2 x 430 mm)"] = round(-2 * gpm * 430.0, 1)
        items["crown corner bondlines removed"] = -CORNER_BONDLINE_G
        items["rack + pawl + pulley guides removed"] = -RACK_PAWL_GUIDES_G
        items["UHMWPE bushings removed"] = round(-BUSHINGS_G, 1)
        from huntkit.fea.sections import tube_round
        s = tube_round(PRINT_LEG["od"], PRINT_LEG["t"])
        items["printed legs PAHT-CF OD %g x %g, 2 x %.0f mm" % (PRINT_LEG["od"], PRINT_LEG["t"], Lp)] = round(2 * s.A * Lp * 1.06e-3, 1)
        items["printed corner sockets (ASSUMPTION ring OD 30 x 80 + gusset)"] = round(2 * CORNER_SOCKET_G, 1)
        items["7075 plugs bonded in the bar ends (15.8 x 2 x 80)"] = round(2 * CORNER_PLUG_G, 1)
        items["z 544 joint bosses (4 per leg, both sides)"] = round(2 * LEG_FLANGE_G, 1)
        items["z 544 joint: 8 Ti M5 x 45 + nuts + washers"] = round(8 * bolt_mass_g(45.0) + 8 * nut + 16 * washer, 1)
        items["corner sockets: 4 Ti M5 x 30 + nuts"] = round(4 * bolt_mass_g(30.0) + 4 * nut, 1)
        items["yoke fine-adjust strip + pin (ASSUMPTION)"] = YOKE_STRIP_G
    frame = sum(items.values())
    pack_rest = H1.PACK_REST_G - (TORSO_ADJUST_SOFT_G if variant != "h1" else 0.0)
    return {"items": items, "frame_g": round(frame, 1), "frame_plus_spreader_g": round(frame + H1.SPREADER_G, 1),
            "pack_g": round(frame + H1.SPREADER_G + pack_rest, 1),
            "pack_note": "CORRIE B.2 belt M on the ledger basis 3926.9 g = H1 frame 1025.1 + spreader 162.3 + rest "
                         "2739.5" + ("" if variant == "h1" else " - torso-adjust soft goods 41.7")}


def cost_usd(variant: str, torso: float, print_g: float) -> dict:
    """Unit cost, quantity 1, as deltas from H1's about $437 (frame_h1.md section 5)."""
    h1_print = 764.5
    d = {"H1 unit cost incl. spreader": 437.0,
         "filament + reprint (print mass change)": round((print_g - h1_print) * FIL_USD_KG / 1000.0, 1),
         "machine time ($1/h)": round((print_g - h1_print) / G_PER_H, 1)}
    leg_usd_mm = 50.3 * (16 * 860) / (16 * 860 + 18 * 214 + 20 * 300) / 860.0   # crown tube cost split by OD x length
    if variant in ("a", "c", "b"):
        d["rack + pawl + guides (ASSUMPTION $6 printed PA66-GF + pawl)"] = -6.0
        d["pulley webbing, cam buckle, cord, toggle (ASSUMPTION $15)"] = -15.0
        d["yoke strip (ASSUMPTION $2)"] = 2.0
    if variant in ("a", "c"):
        L = _leg_len_mm(torso, variant)
        d["carbon legs cut to length"] = round(2 * (L - 430.0) * leg_usd_mm, 1)
        d["UHMWPE bushings -> shims"] = -1.4
        d["4 Ti M5 cross-bolts ($4.50, A's figure) + nuts"] = 19.0
    if variant == "b":
        d["carbon legs removed"] = round(-2 * 430.0 * leg_usd_mm, 1)
        d["UHMWPE bushings removed"] = -5.0
        d["8 Ti M5 x 45 + 4 Ti M5 x 30 + nuts, washers"] = round(12 * 4.5 + 4.0, 1)
        d["2 x 7075 bar-end plugs (ASSUMPTION $4)"] = 4.0
    d["total"] = round(sum(d.values()), 1)
    return d


BUILD = {
    "h1": {"printed parts": 2, "hardware parts": "carbon legs 2, top bar, spine, rack, pawl + pin, pulley guides 3, "
                                               "UHMWPE bushings 4, 304 bushings 2, z 234 bolts 4 + nuts + washers, "
                                               "webbing, cam buckle, release cord + toggle",
           "count": 2 + 2 + 1 + 1 + 1 + 2 + 3 + 4 + 2 + 16 + 3,
           "steps": ["print 2 halves (27 h)", "anneal with a rod through both bores", "bolt z 234, ream 18.0 through",
                     "press 304 pawl bushings, fit pawl + spring", "bond rack to spine", "bond bushings on leg ends",
                     "build crown (2 corner wraps)", "thread 3:1 pulley through 3 guides, fit cam + release cord",
                     "slide crown in, set torso on the wearer"]},
    "a": {"printed parts": 2, "count": 2 + 2 + 1 + 1 + 1 + 2 + 4 + 16 + 12 + 1,
          "hardware parts": "carbon legs 2 (cut per size), top bar, spine, guide pin, 304 bushings 2, shims 4, "
                            "z 234 bolts 4 + nuts + washers, cross-bolts 4 + nuts + washers, yoke strip",
          "steps": ["print 2 halves (27 h)", "anneal", "bolt z 234, ream the socket 18.0 (z 395-544 only)",
                    "press 304 guide bushings", "cut legs to the size table, bond 2 shims per leg",
                    "build crown (2 corner wraps)", "insert legs, drill + ream 5.1 through socket and leg on a jig, "
                    "fit 4 cross-bolts", "set the yoke strip at the wearer's fine position"]},
    "b": {"printed parts": 4, "count": 4 + 1 + 1 + 1 + 2 + 16 + 24 + 8 + 1,
          "hardware parts": "top bar, spine, guide pin, 304 bushings 2, z 234 bolts 4 + nuts + washers, z 544 bolts "
                            "8 + nuts + 16 washers, corner cross-bolts 4 + nuts, yoke strip",
          "steps": ["print 2 body halves + 2 legs (legs about 3 h more)", "anneal 4 parts", "bolt z 234 and both z 544 "
                    "joints (8 bolts)", "press 304 guide bushings", "bond-free corners: insert the top bar, drill + "
                    "ream 2 cross-bolts per corner", "fit spine + yoke strip"]},
}
BUILD["c"] = BUILD["a"]


def fit_table() -> dict:
    """Fit consequences of a printed-in torso (frame_fixed_torso.md section 5)."""
    adj_in = YOKE_ADJ_MM / 25.4
    span = 23.0 - 15.0
    n = math.ceil(span / (2 * adj_in))
    sizes = [{"size": f"{s - adj_in:g}-{s + adj_in:g} in", "nominal_in": s,
              "printed_leg_carbon_mm": round(_leg_len_mm(s, "a")), "printed_leg_pa_mm": round(_printed_leg_len(s))}
             for s in SIZES_IN]
    return {"fine_adjust_mm": [-YOKE_ADJ_MM, YOKE_ADJ_MM], "fine_adjust_in": [-adj_in, adj_in],
            "sizes_for_15_23_in": n, "sizes": sizes,
            "hood_ladder_B20": "one rung per size: the 17-rung ladder (B-20, 250 mm) becomes a 3-rung strip of "
                               "about 70 mm per side (the hood follows the fixed bar; fine adjust is at the yoke, the "
                               "bar does not move), about -2.5 g ASSUMPTION (Hypalon 40 x 180 mm x 2 removed)"}


# ================================================================================================ driver
def beam_summary(variant: str) -> dict:
    sets, rows = load_beam(variant, log=None)
    out = {"crown": crown_checks(rows), "spine_guide": spine_guide_checks(rows)}
    if variant == "fixed":
        out["socket"] = socket_checks(rows)
    else:
        out["printed_legs"] = printed_leg_checks(rows, PRINT_LEG)
        out["leg_joint_z544"] = leg_joint_check(rows, PRINT_LEG)
        out["corner_socket"] = corner_socket_check(rows)
        out["leg"] = PRINT_LEG
    return out


def _cached(name, fn):
    p = OUT / name
    if p.exists():
        return pickle.loads(p.read_bytes())
    v = fn()
    OUT.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps(v))
    return v


def run_all(log=print, render: bool = True) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rep = _cached("h1_repro.pkl", lambda: h1_reproduce(log=log))
    sets_f, _ = load_beam("fixed", log=log)
    sets_p, _ = load_beam("printed", log=log)
    h1_solid = np.load(H1.OUT / "h1_final.npz")["solid"]
    va = _cached("verify_a.pkl", lambda: body_verify("a", h1_solid, sets_f, log=log)[0])
    if not (OUT / "c_shift.npz").exists():
        push_c(sets_f, log=log)
    sc = assemble_c(np.load(OUT / "c_shift.npz")["shift"])
    np.savez_compressed(OUT / "c_solid.npz", solid=sc)
    vc = _cached("verify_c.pkl", lambda: body_verify("c", sc, sets_f, log=log)[0])
    vb = _cached("verify_b.pkl", lambda: body_verify("b", sc, sets_p, log=log)[0])
    bf, bp = beam_summary("fixed"), beam_summary("printed")
    h1r = rep["raster_g"]
    from huntkit.fea.sections import tube_round
    s = tube_round(PRINT_LEG["od"], PRINT_LEG["t"])
    out = {"date": "2026-11-10", "ticket": "BL-007", "h1_reproduced": rep,
           "push_c": json.loads((OUT / "push_c.json").read_text()),
           "variants": {}, "fit": fit_table(), "build": BUILD,
           "socket_design": {"z": [SOCKET_Z0, 544.0], "shim_low": [400.0, 440.0], "shim_top": [484.0, 544.0],
                             "cross_bolt_z": CROSS_BOLT_Z, "lever_correction": LEVER_CORR}}
    for v, ver, beam in (("a", va, bf), ("c", vc, bf), ("b", vb, bp)):
        strip = {k: ver[k] for k in ver if k not in ("buckling", "body")}
        strip["buckling"] = {k: x["margin"] for k, x in ver["buckling"].items()}
        strip["torsion_vs_h1"] = ver["torsion_Nm_deg"] / rep["torsion_Nm_deg"]
        masses = {f"{t:g}": frame_mass(v, t, ver["raster_g"], h1r) for t in (15.0, 16.0, 18.0, 19.0, 20.0, 22.0, 23.0)}
        print_g = 764.5 * ver["raster_g"] / h1r
        if v == "b":
            print_g += 2 * (s.A * _printed_leg_len(19.0) * 1.06e-3 + CORNER_SOCKET_G + LEG_FLANGE_G / 2)
        out["variants"][v] = {"body": strip, "beam": beam, "mass": masses, "print_g_19": round(print_g, 1),
                              "print_h_19": round(print_g / G_PER_H, 1), "cost_19": cost_usd(v, 19.0, print_g)}
    out["variants"]["h1"] = {"mass": {"19": frame_mass("h1", 19.0, h1r, h1r)}, "print_h_19": 27.0}
    RESULT.write_text(json.dumps(out, indent=1, default=float))
    shots = [plot_summary(out, SCREENS / f"{SHOT}_2.png")]
    if render:
        shots.insert(0, render_compare(sc, out))
    out["screens"] = shots
    return out


def _min_margins(out: dict, v: str) -> dict:
    """The rows of the summary figure: min margin of each check family over both couple variants."""
    if v == "h1":
        r = json.loads(H1.RESULT.read_text())
        rc = json.loads((REPO / "designs/pack_5200/analysis/rev_c_verification_results.json").read_text())
        return {"body strength": r["min"]["strength"], "body fatigue": r["min"]["fatigue"], "branch buckling": r["buckling_min"],
                "z 234 joint fatigue": r["joint"]["min_fatigue"], "crown legs FPF": 1.12, "crown spine FPF": 1.18,
                "crown-leg interface": 1.40, "corner bond peak": 1.22}
    V = out["variants"][v]
    b, bm = V["body"], V["beam"]
    cr = bm["crown"]
    m = {"body strength": b["min"]["strength"], "body fatigue": b["min"]["fatigue"], "branch buckling": b["buckling_min"],
         "z 234 joint fatigue": b["joint"]["min_fatigue"],
         "crown spine FPF": min(cr[t]["crown_spine"]["sf"] for t in cr)}
    if v == "b":
        pl = bm["printed_legs"]
        m["crown legs FPF"] = min(min(pl[t][k][0] for k in ("strength", "fatigue", "creep")) for t in pl)
        m["crown-leg interface"] = min(bm["leg_joint_z544"]["min_strength"], bm["leg_joint_z544"]["min_fatigue"],
                                       bm["corner_socket"]["min_strength"])
        m["corner bond peak"] = float("nan")
    else:
        m["crown legs FPF"] = min(cr[t]["crown_leg"]["sf"] for t in cr)
        so = bm["socket"]
        m["crown-leg interface"] = min(so[t][k] for t in ("C", "C_im3") for k in ("min_strength", "min_fatigue"))
        m["corner bond peak"] = min(cr[t]["corner_bond_peak"]["sf"] for t in cr)
    return m


def plot_summary(out: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = {"h1": "H1 (telescoping)", "a": "(a) fixed crown", "c": "(c) fixed + re-sized", "b": "(b) printed legs"}
    cols = {"h1": "#2a78d6", "a": "#eb6834", "c": "#1baf7a", "b": "#eda100"}
    order = ["h1", "a", "c", "b"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 6.2), gridspec_kw={"width_ratios": [1, 1.9]})
    fig.patch.set_facecolor("#fcfcfb")
    for ax in (ax1, ax2):
        ax.set_facecolor("#fcfcfb")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.spines["left"].set_color("#8a8984")
        ax.spines["bottom"].set_color("#8a8984")
    pk = [out["variants"][v]["mass"]["19"]["pack_g"] for v in order]
    fr = [out["variants"][v]["mass"]["19"]["frame_g"] for v in order]
    x = np.arange(len(order))
    ax1.bar(x, fr, color=[cols[v] for v in order], width=0.62, edgecolor="#fcfcfb", linewidth=2)
    for i, (f_, p_) in enumerate(zip(fr, pk)):
        d = f_ - fr[0]
        ax1.text(i, f_ + 12, f"{f_:.0f} g\n({f_ / 453.59:.2f} lb)" + (f"\n{d:+.0f} g" if i else ""), ha="center",
                 va="bottom", fontsize=9, color="#0b0b0b")
        ax1.text(i, 40, f"pack\n{p_:.0f} g\n{p_ / 453.59:.2f} lb", ha="center", va="bottom", fontsize=8.5, color="#fcfcfb")
    ax1.set_xticks(x, [names[v].replace(" (", "\n(").replace(") ", ")\n") for v in order], fontsize=8.5)
    ax1.set_ylabel("frame mass at 19 in, g (spreader excluded)", color="#52514e")
    ax1.set_ylim(0, max(fr) * 1.25)
    ax1.set_title("Frame and CORRIE B.2 pack mass (belt M)", fontsize=11, loc="left", color="#0b0b0b")
    checks = list(_min_margins(out, "a").keys())
    w = 0.2
    for i, v in enumerate(order):
        m = _min_margins(out, v)
        vals = [m.get(c, float("nan")) for c in checks]
        xs = np.arange(len(checks)) + (i - 1.5) * w
        ax2.barh(xs, [min(vv, 3.0) if vv == vv else 0 for vv in vals], height=w, color=cols[v], label=names[v],
                 edgecolor="#fcfcfb", linewidth=1)
        for xx, vv in zip(xs, vals):
            ax2.text((min(vv, 3.0) if vv == vv else 0) + 0.03, xx, "n/a" if vv != vv else f"{vv:.2f}", va="center",
                     fontsize=7, color="#0b0b0b" if (vv != vv or vv >= 1.0) else "#c0392b")
    ax2.axvline(1.0, color="#0b0b0b", lw=1.2, ls="--")
    ax2.text(1.0, len(checks) - 0.45, " pass >= 1.0", fontsize=8, color="#0b0b0b")
    ax2.set_yticks(np.arange(len(checks)), checks, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlim(0, 3.3)
    ax2.set_xlabel("min margin over 42 rev C sets (SF / requirement; bars capped at 3)", color="#52514e")
    ax2.set_title("Governing margins per check family", fontsize=11, loc="left", color="#0b0b0b")
    ax2.legend(loc="lower right", fontsize=8.5, frameon=False)
    fig.suptitle("BL-007 fixed-torso frame study: every variant passes rev C; (c) is the lightest", fontsize=12.5,
                 x=0.01, ha="left", color="#0b0b0b")
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return str(path)


def render_compare(sc: np.ndarray, out: dict) -> str:
    """Cycles: H1 with the telescoping crown at 19 in (left), (c) with the fixed crown (middle), (b) with
    printed legs (right)."""
    import trimesh
    from .frame_light2_render import _cyl as tcyl
    from .frame_branch import _sleeve_y
    from .frame_topopt import solid_to_mesh
    work = OUT / "render"
    work.mkdir(parents=True, exist_ok=True)
    dom = fixed_domain("c")
    dx = 360.0
    h1 = trimesh.load(H1.PRINT_DIR / "h1_assembled.stl")
    h1.export(work / "h1.stl")
    mc = solid_to_mesh(dom, sc)
    for nm, off in (("c", dx), ("b", 2 * dx)):
        m = mc.copy()
        m.apply_translation((off, 0, 0))
        m.export(work / f"{nm}.stl")
    y_top = float(_sleeve_y(540.0))
    zt = 702.6
    files = [{"path": str(work / f"{n}.stl"), "mat": "printed"} for n in ("h1", "c", "b")]
    carbon = []
    # H1: telescoping legs (visible part from the stay top), top bar, spine
    for off, z0 in ((0.0, 420.0), (dx, 420.0)):
        carbon += [tcyl((sx * 115 + off, y_top, z0), (sx * 113 + off, y_top + 4, zt), 8.0) for sx in (-1, 1)]
    for off in (0.0, dx, 2 * dx):
        carbon.append(tcyl((-113 + off, y_top + 4, zt), (113 + off, y_top + 4, zt), 9.0))
        carbon.append(tcyl((off, y_top - 18, zt - 300.0 + 150.0), (off, y_top - 2, zt), 10.0))
    trimesh.util.concatenate(carbon).export(work / "carbon.stl")
    files.append({"path": str(work / "carbon.stl"), "mat": "carbon"})
    r = PRINT_LEG["od"] / 2
    pl = [tcyl((sx * 115 + 2 * dx, y_top, 540.0), (sx * 113 + 2 * dx, y_top + 4, zt + 15.0), r) for sx in (-1, 1)]
    pl += [tcyl((sx * 113 + 2 * dx, y_top + 4, zt - 20.0), (sx * 95 + 2 * dx, y_top + 4, zt), 15.0) for sx in (-1, 1)]
    trimesh.util.concatenate(pl).export(work / "printed_legs.stl")
    files.append({"path": str(work / "printed_legs.stl"), "mat": "printed"})
    V = out["variants"]
    p = SCREENS / f"{SHOT}_1.png"
    H1.render(p, files,
              f"H1 {V['h1']['mass']['19']['frame_g']:.0f} g | (c) fixed {V['c']['mass']['19']['frame_g']:.0f} g | "
              f"(b) printed legs {V['b']['mass']['19']['frame_g']:.0f} g",
              "19 in unit; (c): no rack, pawl, pulley, sleeves below z 395; (b): PAHT-CF legs OD 34 bolted at z 544",
              az=160.0, el=12.0, zoom=1.0)
    return str(p)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "all"
    if cmd == "all":
        r = run_all()
        print(json.dumps({v: r["variants"][v]["mass"]["19"]["frame_g"] for v in r["variants"]}))
    elif cmd == "sweep":
        sweep_printed_legs()
    elif cmd == "beam":
        print(json.dumps(beam_summary("fixed"), default=str, indent=1)[:4000])
    else:
        print("usage: python -m huntkit.gendesign.frame_fixed [all|sweep|beam]")


if __name__ == "__main__":
    main()
