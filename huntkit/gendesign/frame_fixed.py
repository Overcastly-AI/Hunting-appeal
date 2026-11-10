"""BL-007: print-to-size frame without the telescoping crown (study for an owner decision, nothing adopted).

The H1 frame (``frame_h1``) carries a telescoping carbon crown: 430 mm legs that slide in 18 mm sleeve bores over
z 160-544 of the printed stays, two UHMWPE bushings per leg, a toothed rack on the crown spine, a pawl in the upper
bar and a 3:1 webbing pulley. The frame is printed per unit, so the torso length could be printed in. Variants:

- **H1** reproduced first (same solid, same 42 rev C sets, same checks).
- **(a) fixed crown:** the H1 body unchanged. Each carbon leg is cut to its unit's length and sits only in the top
  94 mm of the sleeve (z 450-544, the socket): two 25 mm shims (z 457-482 and 519-544) take the radial couple and two
  Ti M5 cross-bolts (z 480) take the axial load. No rack, pawl, pulley guides, 70 mm bushings, webbing or cam. The
  spine keeps the pawl housing as a lateral guide (slotted: no axial load), so the yoke and the lifters stay where
  they are; fine adjust at the yoke.
- **(c) = (a) + stays re-sized:** below the socket the sleeve keep-out (4.41 mm wall ring, bushing seat) is gone; the
  pulley-guide and cam-buckle pads are gone. H1's push (D offset tool, A floors, judge settings) is continued on the
  fixed-crown load sets with a 2.5 mm printable wall floor round the remaining 18 mm channel and the z 234 joint
  zone frozen.
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
SOCKET_Z0 = 450.0        # sleeve keep-out kept from here to the stay top (z 544): the fixed-leg socket
SOCKET_LOW_Z = 470.0     # low contact band (beam stay node S470; shim z 457-482); the top band is the H1 z 530 node
SHIM_LEN = 25.0          # ASSUMPTION: two bonded 25 mm UHMWPE shims per leg (cut from today's bushing stock)
K_SHIM = 2.0e4           # N/mm radial, as the H1 bushing (pack5200 default bushing_k_n_mm, ASSUMPTION)
K_BOLT_AX = 5.0e4        # N/mm axial at the cross-bolts (as pack5200 pawl_k_n_mm, ASSUMPTION)
CROSS_BOLT_Z = 480.0     # 2 Ti M5 cross-bolts per leg, 90 deg apart in plan, 10 mm above the low shim centre
CROSS_BOLT_L = 30.0      # M5 x 30 through the socket (stay OD 26.8)
CFRP_BEARING = 300.0     # ASSUMPTION (team C A1): pin bearing of the UD-rich roll-wrapped leg wall, MPa ultimate
OPEN_HOLE_KD = 0.55      # ASSUMPTION: open-hole / unnotched strength of the leg laminate at the cross-bolt hole
WALL_FLOOR = 2.5         # (c): printable wall round the 18 mm channel below the socket (frame_topopt.SLEEVE_WALL)
JOINT_FREEZE = (196.0, 256.0)   # (c): H1 material kept round the z 234 bolted joint (bosses z 198-252)

# fine adjust at the yoke (fixed variants): a short toothed strip on the spine, set at fitting
YOKE_ADJ_MM = 25.4       # +- 1.0 in: ASSUMPTION, sized from the research (docs/research/fixed_vs_adjustable_frames.md)
YOKE_STRIP_G = 8.0       # ASSUMPTION: 60 mm of today's pa66_gf30 rack + a 4 mm pin and keeper

# printed legs (b)
PRINT_LEG = {"od": 34.0, "t": 4.0}  # chosen by sweep_printed_legs (smallest passing mass); overwritten by run
E_PAHT = 3860.0
BUCKLE_E_KD = 0.6 * 0.7  # A's rule on printed members: hot x creep


# ================================================================================================ beam model
def _leg_len_mm(torso: float, variant: str) -> float:
    """Carbon leg length along the axis for a fixed-crown unit: from the low shim (z 457) to the crown top."""
    from .frame_topopt import load_envelope
    env = load_envelope()
    cs = min(env.crown_settings, key=lambda c: abs(c["torso_in"] - torso))
    uz = 1.0 / math.sqrt(1 + env.axis_slope ** 2)
    return float((cs["crown_top_z"] - (SOCKET_LOW_Z - SHIM_LEN / 2)) / uz)


def modify_model(m: dict, variant: str, leg: dict | None = None) -> dict:
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
        for mem in m["members"]:
            if mem["group"].startswith("crown_leg"):
                mem["section"] = sec
                mem["material"] = "pa12_cf_fdm_paht"
        m["joints"] = [j for j in m["joints"] if not j["id"].startswith("crown_corner")]
    return m


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
        def mk(posts):
            base = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(t), extension_posts=posts),
                                   95.0)
            return modify_model(base, variant, leg)
        fm, fmp = mk(False), None
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
                rows.append({"scenario": tag, "case": c.name, "torso": float(t), "factor": float(c.required_sf),
                             "g": float(c.g_factor), **R._crown_rows(res, m, c), "extra": _extra_rows(res, m, variant)})
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
                    Fr = s[f"{band}_radial_n"] * fac
                    pb = Fr / (od * SHIM_LEN)                       # projected bearing on the shim / bore
                    keep("strength", f"printed bore bearing under the {band} shim (across layers)", sig_bear_allow / max(pb, 1e-9), where)
                    # leg ring crush under the shim (Roark ring, 60 deg contact as the H1 bushing model)
                    from huntkit.fea.rings import ring_moment_coeff
                    cm = ring_moment_coeff(60.0)
                    Rm = od / 2 - t / 2
                    mh = cm * (Fr / SHIM_LEN) * Rm
                    sf = float(leg.laminate.first_ply_failure((0, -Fr / (2 * SHIM_LEN), 0), (0, mh, 0))["sf"])
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
                        Fr = s[f"{band}_radial_n"] * fac * kf
                        keep("fatigue", f"printed bore bearing ({band} shim) at 1.6 g",
                             P["fat"] * sig_bear_allow / max(Fr / (od * SHIM_LEN), 1e-9), where)
                    keep("fatigue", "leg at the cross-bolt hole at 1.6 g (CFRP FI <= 0.5)", 0.5 * sfb / kf, where)
        o = {"strength": {}, "fatigue": {}}
        for (kind, nm), (v, wh) in worst.items():
            o[kind][nm] = {"margin": round(float(v), 3), "set": wh}
        o["min_strength"] = min(v["margin"] for v in o["strength"].values())
        o["min_fatigue"] = min(v["margin"] for v in o["fatigue"].values())
        out[tag_s] = o
    out["capacities_n"] = {k_: round(v, 1) for k_, v in cap.items()}
    out["design"] = {"socket_z": [SOCKET_Z0, 544.0], "shims": f"2 x {SHIM_LEN:g} mm UHMWPE, z 457-482 and 519-544",
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
        ch = R.pawl_cheek(f[1:])
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
                      # beam eigenvalue with the full printed E; A's rule knocks E down by 0.6 x 0.7 (the leg mode
                      # dominates, so the factor scales the eigenvalue: conservative for the carbon members)
                      "buckling_A_rule": (round(b[0] * BUCKLE_E_KD, 3) if b[0] is not None else None, b[1])}
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


def corner_socket_check(rows: list) -> dict:
    """(b) printed corner socket on each leg top holding the carbon top bar (OD 18): the bar end moment is taken
    by contact over a 40 mm socket (couple lever 0.8 x 40 mm), axial and torsion by 2 Ti M5 cross-bolts.
    Checks: printed bore bearing across the layers, bar ring crush (CFRP FPF), bar pin bearing."""
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.pack5200 import _sec
    from huntkit.fea.rings import ring_moment_coeff
    from . import frame_topopt as ft
    fm = build_frame_from_yaml(ft.FRAME_YAML, torso_in=19.0)
    bar = _sec(next(m for m in fm["members"] if m["group"] == "crown_top_bar")["section"])
    od, t = bar.dims["od"], bar.dims["t"]
    Ls, lev = 40.0, 32.0
    P = H1.PAHT
    k = P["knock"]
    best = {}
    for r in rows:
        for side in "LR":
            N, Vy, Vz, T, My, Mz = [abs(v) * r["factor"] for v in r["extra"]["leg_sections"][side]["corner_bar_end"]]
            Fc = math.hypot(My, Mz) / lev + math.hypot(Vy, Vz)
            pb = Fc / (od * Ls / 3)                    # contact over a third of the socket at each end
            where = f"{r['scenario']}:{r['case']}|{r['torso']:g}"
            rows_ = {"corner socket bore bearing (across layers)": k * P["s_z"] / max(pb, 1e-9)}
            Rm = od / 2 - t / 2
            mh = ring_moment_coeff(60.0) * (Fc / (Ls / 3)) * Rm
            rows_["top bar ring crush in the socket (FPF)"] = float(
                bar.laminate.first_ply_failure((0, -Fc / (2 * Ls / 3), 0), (0, mh, 0))["sf"])
            Fb = N + T / (od / 2)
            rows_["top bar pin bearing (2 x M5, CFRP 300 x 0.8)"] = 2 * 2 * 5.0 * t * CFRP_BEARING * 0.8 / max(Fb, 1e-9)
            for nm, v in rows_.items():
                if nm not in best or v < best[nm][0]:
                    best[nm] = (v, where)
    out = {nm: {"margin": round(v, 3), "set": wh} for nm, (v, wh) in best.items()}
    out["min_strength"] = min(v["margin"] for v in out.values())
    return out


def sweep_printed_legs(log=print, cands=((26, 4), (30, 4), (34, 4), (38, 4), (34, 5), (38, 3.5), (42, 3.5))) -> list:
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
