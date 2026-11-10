"""Frame competition, team C: ROD. Printed PAHT-CF clamshell knuckles on bought carbon tubes, no adhesive.

Rules: ``designs/pack_5200/frame_comp/RULES.md``. Design doc: ``designs/pack_5200/analysis/frame_comp_C.md``.
Research: ``docs/research/frame_comp_C.md``. Result: ``designs/pack_5200/frame_comp/C/result.json``.

Concept
-------
"Rebar in a printed bone". Two straight stock carbon stays and two carbon cross bars (the long members) are held
in printed PAHT-CF clamshell knuckles (the nodes, interfaces and the generative look). Every printed part is a
one-piece BODY with open (180 deg) channels for the tubes plus a CAP closed by M3 titanium bolts with Belleville
washers. Load gets in and out of the smooth tubes by bearing and interlock only:

- bending and shear: contact pressure of the tube on the channel walls (socket / sleeve couple),
- axial force and torsion of the bars: one M4 titanium cross pin per bar end (drilled + reamed, double bearing on
  the tube walls) 12 mm from the bar tip, where the socket contact has taken out ~88 % of the mouth moment,
- stays: the crown legs telescope INSIDE the stays above ~z 170, so no pin may cross the stay bore at the knuckles.
  The mid knuckle is spliced to the foot-saddle (a printed rail z 0-355) and hands its axial load down the rail to
  the stay end; the upper knuckle holds the stay stub by two 3 mm single-wall radial pins at z 525 (flush with the
  bore, engaging the top crown bushing),
- stay foot: the stay end bears on a 1.5 mm aluminium disc in the boot floor (compression); the foot pin takes
  uplift and torque,
- lumbar pan: a flat bought QI CFRP plate bolted (M4, bearing) to the two printed foot-saddles; hip node bolted
  through the pan (the 4 x M5 inserts of the fixed interface stay in the printed hip node).

Clamp friction is NOT credited anywhere in the strength or fatigue checks: the cap bolts only keep the channels
closed. That makes PAHT-CF preload creep a serviceability item (rattle), handled with Belleville washers and checked
here as an information number (``preload_creep``).

The beam model is the v2 tube ladder of ``huntkit.fea.pack5200`` (as in frame_light2), with every bar end split into
a printed PAHT neck member (stay axis to the bar tip, ``NECK_MM``) so the printed node's compliance and root stress
come out of the solve. The carbon crown with the rev C fix, the torso adjust, the Ti pivot and the Sandwich v2
spreader are unchanged (fixed interfaces).

Run: ``python -m huntkit.gendesign.frame_comp_C``    (about 5 min on 2 cores)
"""
from __future__ import annotations

import copy
import json
import math
import time
from pathlib import Path

import numpy as np

from huntkit.fea.materials_bridge import REPO_ROOT, get_material
from . import frame_light2 as L2

TEAM_DIR = REPO_ROOT / "designs" / "pack_5200" / "frame_comp" / "C"
RESULT_JSON = TEAM_DIR / "result.json"
DETAIL_JSON = TEAM_DIR / "rod_results.json"
SCREENS = REPO_ROOT / "outputs" / "screens"
SHOT = "20261110_compC"
SCRATCH = REPO_ROOT / "outputs" / "frame_comp_C"          # scratch (not tracked)
TORSOS = (15.0, 19.0, 23.0)

UD, WV = "cfrp_t700_ud_epoxy_ply", "cfrp_t300_3k_woven_epoxy_ply"

# ----------------------------------------------------------------------------- stock tubes (cited in research doc)
# Rock West Composites P/N 46710, fabric roll-wrapped metric tube 18 x 20 x 2000 mm, published layup (Rev NC, inside
# to outside) 0 / 0 / 0 / 90 / 90 / 3K 2x2 twill; 0.401 lb per 2 m = 91 g/m; $111.99 per 2 m (1-9 pcs).
# https://www.rockwestcomposites.com/46710.html
# Modelled with the repo ply records: 3 x UD 0 + 2 x UD 90 + 1 twill = 0.845 mm (vendor wall 1.0 mm): strength and
# stiffness conservative, mass from the vendor figure.
RW46710 = {"type": "composite_tube", "od": 20.0,
           "layup": [{"angle": 0, "material": UD}] * 3 + [{"angle": 90, "material": UD}] * 2
           + [{"angle": 0, "material": WV}]}
STOCK = {
    "RW46710": {"spec": RW46710, "g_per_m": 90.9, "usd_per_m": 111.99 / 2, "od": 20.0, "wall": 1.0,
                "label": "Rock West 46710, 20 x 18 mm roll-wrapped (0/0/0/90/90/twill), stock"},
}


def custom_rw45(od, k):
    """Custom roll-wrapped +-45 torsion tube (frame_light2 RW45 family), special order like today's crown tubes."""
    spec = L2._spec(od, "RW45", k)
    from huntkit.fea.sections import from_spec
    s = from_spec(spec)
    return {"spec": spec, "g_per_m": s.A * L2.RHO_CF * 1000, "usd_per_m": L2.TUBE_USD_PER_M_16 * od / 16.0,
            "od": od, "wall": s.dims["t"], "label": f"custom roll-wrapped OD {od} RW45 k{k} (special order)"}


# ----------------------------------------------------------------------------- printed knuckle geometry
GEO = {
    "shell_t": 2.4,          # clamshell channel wall, mm (6 perimeters x 0.4; record min wall 2.0)
    "gap": 0.15,             # slip-fit clearance per side (no adhesive), mm
    "neck_mm": 25.0,         # stay axis to the bar tip (printed neck), mm
    "neck_t": 4.0,           # neck modelled as a PAHT annulus around the bar line, mm (generative boss: ASSUMPTION)
    "socket_mm": 55.0,       # bar engagement in the socket channel
    "bar_pin_from_tip": 12.0,  # e = 3 d for the M4 pin
    "stay_sleeve_mm": 70.0,  # stay channel length counted for the contact couple at a hub
    "stay_pin_dz": 5.0,      # upper knuckle radial pins 5 mm above the hub (z 525), in the stay stub
    "radial_pin_d": 3.0,     # 3 mm Ti dowel through ONE wall, flush with the bore (leg telescopes inside)
    "rail_top": 355.0,       # mid knuckle sleeve top; the rail (saddle + mid knuckle) spans z 0-355
    "upper_sleeve_bot": 410.0,  # upper knuckle sleeve from z 410 (carries the z 420 lash eye) to the stay top
    "pin_d": 4.0,            # M4 Ti-6Al-4V bolt, plain shank in bearing (DIN 912 partial thread), reamed hole
    "paht_bear_len": 6.0,    # PAHT bearing length per side of a pin (boss), mm
    "saddle_mm": 205.0,      # foot-saddle: boot floor to above the pan top (z 0..205)
    "saddle_fill": 0.5,      # generative windows in long sleeves away from the hubs (ASSUMPTION: 50 % cut away)
    "foot_pin_z": 20.0,
    "pan_bolts_per_side": 5,  # one M4 per lumbar grid row (z 50 / 90 / 120 / 155 / 190)
    "pan_tab_t": 9.0,        # printed saddle tab under a pan bolt
    "cap_bolts": 3,          # M3 Ti per knuckle cap (the bar pin closes the 4th corner)
    "flare": 0.25,           # generative fillets / root fingers, fraction of the shell volume (ASSUMPTION)
}

# Allowables (MPa). CFRP pin bearing: ASSUMPTION 300 MPa ultimate for a thin 0/90 roll-wrapped wall loaded by a
# pin without clamp-up (D5961 procedure dependence: clamp-up raises it; the QI plate record lists 500), x 0.8 hot/wet.
BEAR_CF = 300.0 * 0.8
BEAR_CF_PLATE = 500.0 * 0.8           # cfrp_plate_quasi_iso record bearing x 0.8 (pan)
SHEAR_CF_TUBE = 62.5 * 0.8           # Rock West 46710 published in-plane shear 9064 psi x 0.8 (shear-out)
NOTCH = 0.55                          # filled-hole / unnotched strength at a 4 mm hole (ASSUMPTION, coupon RC-3)
PAHT_XY, PAHT_Z = L2.PAHT_XY, L2.PAHT_Z
PAHT_BEAR = PAHT_XY                   # pin bearing in the layer plane (ASSUMPTION: >= tensile XY), x 0.8 incl.
TI = get_material("ti_6al_4v")
TI_YIELD = float(TI.require("yield_strength_mpa"))
AS_M3, AS_M4 = 5.03, 8.78             # tensile stress areas, ISO 898
WASHER_M3 = (10.0, 3.4)               # penny washer under each M3 head / nut
PRELOAD_M3 = 600.0                    # N, ~0.5 N m (ASSUMPTION: hand torque, keeps the cap closed only)
BELLEVILLE_K = 1200.0                 # N/mm, DIN 2093 A-series ~10 x 3.2 x 0.4 stacked in series x2 (ASSUMPTION)
CF_BEAR_FAT = 0.5                     # bearing fatigue 1e5 / static (ASSUMPTION, coupon RC-2f)
MU_INFO = 0.15                        # PA on CFRP, information only (never credited)

FASTENER_G = {"M4 Ti pin set (bolt 25 mm + nut + 2 washers)": 2.4, "M3 Ti cap set (bolt 16 + nut + 2 penny "
              "washers + Belleville pair)": 1.4, "Al end disc 20 x 1.5": 1.3,
              "Ti dowel 3 x 6 (radial stay pin)": 0.2, "M4 Ti pan set (bolt 16 mm + nut + 2 washers)": 1.7}


def rod_candidate(stay="RW46710", bar="RW46710", ubar=("rw45", 22, 5), pan_t=1.5) -> dict:
    def tube(t):
        return STOCK[t] if isinstance(t, str) else custom_rw45(t[1], t[2])
    return {"name": "ROD", "stay_t": tube(stay), "bar_t": tube(bar), "ubar_t": tube(ubar), "pan_t": float(pan_t),
            "keys": {"stay": stay, "bar": bar, "ubar": ubar}}


# ----------------------------------------------------------------------------- model
def neck_section(od_bar: float):
    from huntkit.fea.sections import tube_round
    return tube_round(od_bar + 2 * GEO["gap"] + 2 * GEO["neck_t"], GEO["neck_t"])


def build(cand: dict, torso: float, posts: bool = False) -> dict:
    from huntkit.fea.frames import build_frame_from_yaml
    from huntkit.fea.sections import from_spec
    from . import frame_cg_recheck as R
    from . import frame_topopt as ft
    over = {"stay_section": cand["stay_t"]["spec"], "bar_section": cand["bar_t"]["spec"],
            "upper_bar_section": cand["ubar_t"]["spec"], "lumbar_plate_t": cand["pan_t"],
            "crown_joint": L2._crown_joint()}
    m = R.split_top_bar(build_frame_from_yaml(ft.FRAME_YAML, torso_in=float(torso), extension_posts=posts, **over),
                        95.0)
    m["name"] = "comp_C_ROD"
    mat = L2.paht_neck_material()
    joints = []
    for j in m["joints"]:
        jid = j["id"]
        if jid.startswith("crown_corner"):
            joints.append(j)
        elif jid.startswith("post_socket"):          # P-1 of frame_light2: 0.8 mm bondline on the accessory socket
            joints.append({**j, "params": {**(j.get("params") or {}), **L2._crown_joint()}})
        elif jid.startswith(("mid_hub", "upper_hub")):
            tag = jid[-1]
            bar_id = j["members"][0]
            od = from_spec(next(q for q in m["members"] if q["id"] == bar_id)["section"]).dims["od"]
            nk = f"NK{'M' if jid.startswith('mid') else 'U'}{tag}"
            rest = L2._split(m, bar_id, j["node"], GEO["neck_mm"], nk, "lug_neck", neck_section(od), mat)
            m.setdefault("rod_knuckles", []).append({"id": jid, "stay_node": j["node"], "neck_node": nk,
                                                     "bar": rest, "through": j["through"][0], "od_bar": od})
    m["joints"] = joints          # only the crown bonds (fixed interface) remain bonded
    m["rod"] = cand
    return m


# ----------------------------------------------------------------------------- joint mechanics (no friction credit)
def _end(res, model, mid, node):
    mem = next(mm for mm in res.members if mm["id"] == mid)
    md = next(q for q in model["members"] if q["id"] == mid)
    return np.asarray(mem["end_forces"][0 if md["nodes"][0] == node else 1], float)


def socket_contact(V: float, M: float, L: float):
    """Rigid tube in a socket of length L, loaded at the mouth by shear V and moment M. Linear contact line load
    q(u) = a + b u (u from the mouth) with  int q = -V,  int q u = -M; internal moment
    M(u) = M - V u - int_0^u q(w)(u - w) dw  (M(L) = 0). Both relative senses of V and M are taken.
    Returns (peak line load N/mm, M_int(u) worst over the two senses)."""
    A = np.array([[L, L ** 2 / 2], [L ** 2 / 2, L ** 3 / 3]])
    sols = []
    for sv in (1.0, -1.0):
        Vs, Ms = sv * abs(V), abs(M)
        a, b = np.linalg.solve(A, [-Vs, -Ms])
        sols.append((Vs, Ms, a, b))
    qpk = max(max(abs(a), abs(a + b * L)) for _, _, a, b in sols)

    def M_int(u):
        return max(abs(Ms - Vs * u - (a * u ** 2 / 2 + b * u ** 3 / 6)) for Vs, Ms, a, b in sols)
    return qpk, M_int


def end_global(res, model, mid, node):
    """(F, M) global vectors of the member end at ``node`` (from one element force vector, signs consistent)."""
    mi = next(i for i, m in enumerate(res.members) if m["id"] == mid)
    ni = res.node_ids.index(node)
    for e in res.members[mi]["elements"]:
        el = res.elements[e]
        R = el.T[:3, :3]
        if el.n1 == ni:
            v = res.elem_forces[e, 0]
            return R.T @ v[:3], R.T @ v[3:6]
        if el.n2 == ni:
            v = -res.elem_forces[e, 1]
            return R.T @ v[:3], R.T @ v[3:6]
    raise KeyError((mid, node))


def tube_fpf_at_hole(sec, axis, F, M, pin_dir, notch=NOTCH, d_hole=None):
    """First-ply SF of the tube wall at the two edges of each cross-pin hole. ``axis`` tube axis, ``pin_dir`` pin
    axis (both unit, global); F, M internal force / moment vectors at the hole station (global). Running loads at
    the hole edges (angle +-asin(r_pin / R) from the pin axis), both signs, knocked-down laminate, x notch ratio."""
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    pd = np.asarray(pin_dir, float)
    pd = pd - (pd @ a) * a
    pd /= np.linalg.norm(pd)
    q = np.cross(a, pd)
    R = sec.dims["od"] / 2
    t = sec.dims["t"]
    N = float(F @ a)
    T = float(M @ a)
    Mp = M - (M @ a) * a
    Am = math.pi * (R - t / 2) ** 2
    Nxy = abs(T) / (2 * Am)
    dth = math.asin(min(0.99, (d_hole or GEO["pin_d"]) / 2 / R))
    worst = np.inf
    for base in (pd, -pd):
        for sgn in (1, -1):
            p = R * (math.cos(dth) * base + sgn * math.sin(dth) * q)
            sig = N / sec.A + float(a @ np.cross(Mp, p)) / sec.Iy
            for s in (1.0, -1.0):          # load reversal
                fpf = sec.laminate.first_ply_failure((s * sig * t, 0.0, Nxy), (0, 0, 0))
                worst = min(worst, float(fpf["sf"]))
    return worst * notch


def pin_checks(N, T, sec, e_end=None):
    """Cross pin through both tube walls: each wall takes N/2 plus the torque couple T/d_m. Returns SFs."""
    d = GEO["pin_d"]
    t = sec.dims["t"]
    dm = sec.dims["od"] - t
    Fw = math.hypot(abs(N) / 2, abs(T) / dm)
    out = {"Fw": Fw,
           "cf_bearing": BEAR_CF * d * t / Fw if Fw > 0 else np.inf,
           "paht_bearing": PAHT_BEAR * d * GEO["paht_bear_len"] / Fw if Fw > 0 else np.inf,
           "pin_shear": 0.6 * TI_YIELD * math.pi / 4 * d ** 2 / Fw if Fw > 0 else np.inf}
    if e_end is not None:
        out["shear_out"] = SHEAR_CF_TUBE * 2 * (e_end - d / 2) * t / Fw if Fw > 0 else np.inf
    return out


def cap_bolts(F_trans):
    """Worst case: the whole transverse node force pulls the cap off. Ti M3 tension, penny washer bearing in Z
    on top of the preload."""
    n = GEO["cap_bolts"]
    f = F_trans / n
    Aw = math.pi / 4 * (WASHER_M3[0] ** 2 - WASHER_M3[1] ** 2)
    return {"bolt": TI_YIELD * AS_M3 / (PRELOAD_M3 + f), "washer": PAHT_Z * Aw / (PRELOAD_M3 + f) if f >= 0 else np.inf,
            "f_per_bolt": f}


def preload_creep() -> dict:
    """Information: preload loss from compressive creep of the PAHT flange stack under a clamped M3.
    Strain increment from the record's creep modulus ratio (0.7 at 40 C / 8 h, ASSUMPTION there); x 3 for
    long-term (ASSUMPTION). With and without the Belleville pair."""
    Ez = float(get_material(L2.PAHT).require("youngs_modulus_z_mpa"))
    Aw = math.pi / 4 * (WASHER_M3[0] ** 2 - WASHER_M3[1] ** 2)
    sig = PRELOAD_M3 / Aw
    grip = 2 * GEO["shell_t"] + 4.0                       # cap flange + body flange (mm)
    d_creep = 3.0 * sig / Ez * (1 / 0.7 - 1) * grip
    k_bolt = 114000.0 * AS_M3 / (grip + 4.0)             # Ti E 114 GPa
    loss_plain = min(1.0, d_creep * k_bolt / PRELOAD_M3)
    k_ser = 1 / (1 / k_bolt + 1 / BELLEVILLE_K)
    loss_bell = min(1.0, d_creep * k_ser / PRELOAD_M3)
    return {"washer_stress_mpa": sig, "creep_mm": d_creep, "loss_plain_frac": loss_plain, "loss_belleville_frac":
            loss_bell, "friction_info_n": MU_INFO * 2 * GEO["cap_bolts"] * PRELOAD_M3 * (1 - loss_bell)}


PIN_DIR = {"bar": (0.0, 1.0, 0.0), "stay": (0.0, 1.0, 0.0)}   # bar pins fore-aft (y); stay-top radial pins at +-y


def _bar_net(res, model, k, bsec, M_mouth, M_pin):
    F, M = end_global(res, model, k["bar"], k["neck_node"])
    a = np.subtract(model["nodes"][k["bar"].split("-")[1]], model["nodes"][k["neck_node"]])
    a = a / np.linalg.norm(a)
    Mp = M - (M @ a) * a
    V = F - (F @ a) * a
    worst = np.inf
    for sg in (1, -1):               # moment at the mouth, both senses of the shear increment, scaled to the pin
        Mm = Mp + sg * np.cross(a, V) * GEO["socket_mm"]
        Mpin = Mm / max(np.linalg.norm(Mm), 1e-9) * M_pin
        worst = min(worst, tube_fpf_at_hole(bsec, a, F, Mpin + (M @ a) * a, PIN_DIR["bar"], d_hole=GEO["pin_d"]))
    return worst


def _stay_top_net(res, model, k, above, ssec):
    """Stay wall at the radial pins, ``stay_pin_dz`` above the upper hub (stay stub to the top end)."""
    F, M = end_global(res, model, above, k["stay_node"])
    a = np.array([0.0, 0.0, 1.0])
    V = F - (F @ a) * a
    worst = np.inf
    for sg in (1, -1):
        Mh = M + sg * np.cross(a, V) * GEO["stay_pin_dz"]
        worst = min(worst, tube_fpf_at_hole(ssec, a, F, Mh, PIN_DIR["stay"], d_hole=GEO["radial_pin_d"]))
    return worst


def radial_pin_checks(N, T, sec):
    """Two single-wall radial pins at opposite sides (flush with the bore, retained by the knuckle cap): each takes
    N/2 plus the torque couple T/d_m, bearing on ONE wall."""
    d = GEO["radial_pin_d"]
    t = sec.dims["t"]
    dm = sec.dims["od"] - t
    Fw = math.hypot(abs(N) / 2, abs(T) / dm)
    return {"Fw": Fw, "cf_bearing": BEAR_CF * d * t / Fw if Fw > 0 else np.inf,
            "paht_bearing": PAHT_BEAR * d * GEO["paht_bear_len"] / Fw if Fw > 0 else np.inf,
            "pin_shear": 0.6 * TI_YIELD * math.pi / 4 * d ** 2 / Fw if Fw > 0 else np.inf}


def knuckle_rows(res, model) -> list[dict]:
    """Mid knuckle (part of the stay rail: axial goes down the rail to the foot) and upper knuckle (radial pins in
    the stay stub above the hub): bar pin, bar net section, socket contact, sleeve contact, cap bolts, rail splice."""
    from huntkit.fea.sections import from_spec
    out = []
    for k in model["rod_knuckles"]:
        upper = k["id"].startswith("upper")
        bsec = from_spec(next(q for q in model["members"] if q["id"] == k["bar"])["section"])
        f = _end(res, model, k["bar"], k["neck_node"])
        N, Vy, Vz, T, My, Mz = f
        V = math.hypot(Vy, Vz)
        Lsock = GEO["socket_mm"]
        Mm = max(math.hypot(My + s * Vz * Lsock, Mz - s * Vy * Lsock) for s in (1, -1))
        qpk, M_int = socket_contact(V, Mm, Lsock)
        u_pin = Lsock - GEO["bar_pin_from_tip"]
        bp = pin_checks(N, T, bsec, e_end=GEO["bar_pin_from_tip"])
        row = {"knuckle": k["id"], "bar_N": N, "bar_V": V, "bar_T": T, "bar_M_mouth": Mm,
               "bar_pin_cf": bp["cf_bearing"], "bar_pin_paht": bp["paht_bearing"], "bar_pin_shear": bp["pin_shear"],
               "bar_shear_out": bp["shear_out"],
               "bar_net_section": _bar_net(res, model, k, bsec, Mm, M_int(u_pin)),
               "socket_contact": PAHT_Z * (bsec.dims["od"]) / qpk if qpk > 0 else np.inf}
        below, above = k["through"]
        ssec = from_spec(next(q for q in model["members"] if q["id"] == above)["section"])
        jump = _end(res, model, above, k["stay_node"]) - _end(res, model, below, k["stay_node"])
        Ftr = math.hypot(jump[1], jump[2])
        Mj = math.hypot(jump[4], jump[5])
        Ls = GEO["stay_sleeve_mm"]
        q_s, _ = socket_contact(Ftr, Mj / 2, Ls / 2)      # half sleeve each side of the hub carries half the couple
        row.update({"stay_jump_N": jump[0], "stay_jump_T": jump[3],
                    "sleeve_contact": PAHT_Z * ssec.dims["od"] / q_s if q_s > 0 else np.inf})
        if upper:
            fa = _end(res, model, above, k["stay_node"])
            # pins above the hub carry what the knuckle hands to the stay stub + crown bushing: the jump
            rp = radial_pin_checks(jump[0], jump[3], ssec)
            row.update({"stay_pin_cf": rp["cf_bearing"], "stay_pin_paht": rp["paht_bearing"],
                        "stay_pin_shear": rp["pin_shear"],
                        "stay_net_section": _stay_top_net(res, model, k, above, ssec)})
        else:
            # rail splice (mid knuckle to foot-saddle): 2 x M4 Ti through printed laps, double shear, bearing
            Fs = math.hypot(jump[0], jump[3] / 30.0)       # torque as a couple over the 30 mm lap span
            row["rail_splice"] = 2 * PAHT_BEAR * GEO["pin_d"] * GEO["pan_tab_t"] / Fs if Fs > 0 else np.inf
        cb = cap_bolts(max(V, Ftr))
        row["cap_bolt"] = cb["bolt"]
        row["cap_washer"] = cb["washer"]
        Aw = math.pi / 4 * (WASHER_M3[0] ** 2 - WASHER_M3[1] ** 2)
        row["cap_washer_cyc"] = PAHT_Z * Aw / cb["f_per_bolt"] if cb["f_per_bolt"] > 0 else np.inf
        out.append(row)
    return out


def rail_strain(res, model) -> float:
    """Printed rail / sleeves clamped on the stays are strained with the stay (compatibility): sigma = E_paht x
    curvature x rail mid-wall radius x Kt 1.5 (window corners, ASSUMPTION), over z 0-355 and 410-530. Returns SF
    vs PAHT XY (layers along the stay)."""
    from huntkit.fea.sections import from_spec
    E = float(get_material(L2.PAHT).require("youngs_modulus_xy_mpa"))
    worst = 0.0
    for md, mm in zip(model["members"], res.members):
        if not md["group"].startswith("stay"):
            continue
        sec = from_spec(md["section"])
        z = [model["nodes"][n][2] for n in md["nodes"]]
        if not any((0 <= zz <= 355) or (410 <= zz <= 530) for zz in z):
            continue
        r = sec.dims["od"] / 2 + GEO["gap"] + GEO["shell_t"] / 2
        for ef in mm["end_forces"]:
            kap = math.hypot(ef[4], ef[5]) / (sec.Ex * sec.Iy)
            ax = abs(ef[0]) / (sec.Ex * sec.A)
            worst = max(worst, E * (kap * r + ax) * 1.5)
    return PAHT_XY / worst if worst > 0 else np.inf


def saddle_rows(res, model) -> dict:
    """Foot of the rail: the stay end on the Al disc (compression) and the foot pin at z 20 (uplift + torque) carry
    the stay force arriving from above the rail top (z 355) plus the setdown reaction; pan bolts (M4 bearing in
    the QI pan and the printed tab); hip node through-bolts."""
    from huntkit.fea.pack5200 import PLATE_Z, _member_node_force_global
    from huntkit.fea.sections import from_spec
    ssec = from_spec(next(q for q in model["members"] if q["group"].startswith("stay_lower"))["section"])
    out = {}
    worst_pin, worst_disc = np.inf, np.inf
    for s in ("L", "R"):
        top = f"S{s}330"
        abv = next(q["id"] for q in model["members"] if q["nodes"][0] == top and q["group"].startswith("stay"))
        f = _end(res, model, abv, top)
        p = pin_checks(abs(f[0]), f[3], ssec)        # either sense, conservative
        worst_pin = min(worst_pin, p["cf_bearing"], p["paht_bearing"], p["pin_shear"])
        Fz = abs(float(res.reactions[f"S{s}0"][2])) if f"S{s}0" in res.reactions else 0.0
        Nc = abs(f[0]) + Fz
        A_disc = math.pi / 4 * 20.0 ** 2
        worst_disc = min(worst_disc, PAHT_Z * A_disc / Nc if Nc > 0 else np.inf)
    out["foot_pin"] = worst_pin
    out["end_disc"] = worst_disc
    grid = model["plate_grid"]
    t = model["params"]["lumbar_plate_t"]
    Fmax = 0.0
    for i, _z in enumerate(PLATE_Z):
        for j in (0, 4):
            nid = grid[f"{i},{j}"]
            F = np.zeros(3)
            for m in model["members"]:
                if m["group"].startswith("lumbar_plate") and nid in m["nodes"]:
                    F += _member_node_force_global(res, m["id"], nid)
            Fmax = max(Fmax, float(np.linalg.norm(F)))
    d = 4.0
    out["pan_bolt_cf"] = BEAR_CF_PLATE * d * t / Fmax if Fmax > 0 else np.inf
    out["pan_bolt_paht"] = PAHT_BEAR * d * GEO["pan_tab_t"] / Fmax if Fmax > 0 else np.inf
    out["pan_bolt_F"] = Fmax
    R6 = np.asarray(res.reactions.get("HP", np.zeros(6)), float)
    Fx, Fy, Fz = R6[:3]
    px, pz = L2.INSERT_PITCH
    Mx, Mz = abs(Fz) * L2.PIVOT_STANDOFF, abs(Fx) * L2.PIVOT_STANDOFF
    ten = max(-Fy, 0.0) / 4 + Mx / (2 * pz) + Mz / (2 * px)
    sh = math.hypot(Fx, Fz) / 4
    out["hip_bolt_cf"] = BEAR_CF_PLATE * d * t / sh if sh > 0 else np.inf
    out["hip_bolt_paht"] = PAHT_BEAR * d * GEO["pan_tab_t"] / sh if sh > 0 else np.inf
    out["hip_bolt_ti"] = TI_YIELD * AS_M4 / (ten + 1500.0)       # + M4 preload 1500 N (ASSUMPTION)
    out["rail_strain"] = rail_strain(res, model)
    return out


# ----------------------------------------------------------------------------- one case
def run_case(cand, torso, variant, case, posts=False):
    from huntkit.fea.pack5200 import plate_checks
    from . import frame_cg_recheck as R
    c = copy.copy(case)
    c.params = dict(c.params)
    c.buckling = variant == "crown_bar" and c.kind != "setdown"
    m = build(cand, torso, posts)
    res = c.run(m)
    req = float(c.required_sf)
    row = {"case": c.name, "torso": torso, "variant": variant, "req": req, "members": {}, "joints": {}}
    for mm in res.members:
        g = L2._group_label(mm["group"])
        if g == "lumbar_plate_shear":
            continue
        sf = float(mm["sf"]) / req
        if sf < row["members"].get(g, (np.inf,))[0]:
            row["members"][g] = (sf, mm["id"], float(mm["sf"]))
    row["buckling"] = float(res.buckling_sf) / (1.5 * req) if c.buckling and res.buckling_sf else None
    cr = R._crown_rows(res, m, c)
    row["crown"] = {"members": cr["members"], "joints": cr["joints"], "bushings": cr["bushings"], "pawl_n": cr["pawl_n"]}
    row["plate"] = {}
    for p in plate_checks(res, m):
        k = p["check"].split("(")[0].strip()
        if "bond" in k:
            continue                      # no pan bond in ROD: replaced by the pan bolts below
        row["plate"][k] = float(p["sf"]) / ((1.5 * req) if p.get("buckling") else req)
    kr = knuckle_rows(res, m)
    J = row["joints"]

    def put(k, v, where):
        if v is not None and np.isfinite(v) and v / req < J.get(k, (np.inf,))[0]:
            J[k] = (v / req, where, v)
    for r in kr:
        for k in ("bar_pin_cf", "bar_pin_paht", "bar_pin_shear", "bar_shear_out", "bar_net_section",
                  "socket_contact", "stay_pin_cf", "stay_pin_paht", "stay_pin_shear", "stay_net_section",
                  "sleeve_contact", "cap_bolt", "cap_washer", "rail_splice"):
            if k in r:
                put(k, r[k], r["knuckle"])
    sr = saddle_rows(res, m)
    for k in ("foot_pin", "end_disc", "pan_bolt_cf", "pan_bolt_paht", "hip_bolt_cf", "hip_bolt_paht", "hip_bolt_ti",
              "rail_strain"):
        put(k, sr[k], "saddle/pan")
    fb = L2.foot_boot(res, m)
    put("foot boot (PAHT)", fb["sf"], fb["node"])
    stc = L2.stay_top_collar(res, m)
    put("stay-top collar ring (PAHT, Z)", stc["sf_collar"], "upper knuckle")
    put("stay ring under the collar", stc["sf_stay"], "stay top")
    hn = L2.hip_node(res, m)
    put("hip node 4 x M5 inserts", hn["sf_insert"], "HP")
    pawl = abs(cr["pawl_n"][2])
    put("torso adjust: rack (5328 N)", 5328.0 / pawl if pawl > 0 else np.inf, "rack")
    if c.name == "static_carry":
        fat = {}
        creep = {}
        for mm in res.members:
            g = L2._group_label(mm["group"])
            if g == "lumbar_plate_shear":
                continue
            raw = float(mm["sf"])
            f = (L2.PAHT_FAT * raw / L2.G_WALK) if g == "lug_neck" else (L2.CFRP_FAT_FI * raw / L2.G_WALK)
            if f < fat.get(g, (np.inf,))[0]:
                fat[g] = (f, mm["id"])
            if g == "lug_neck":
                creep["neck"] = min(creep.get("neck", np.inf), 0.4 * raw)
        paht = ("bar_pin_paht", "socket_contact", "stay_pin_paht", "sleeve_contact", "cap_washer_cyc", "rail_splice")
        cf = ("bar_pin_cf", "stay_pin_cf", "bar_shear_out")
        net = ("bar_net_section", "stay_net_section")
        for r in kr:
            for k in paht:
                if k not in r:
                    continue
                v = L2.PAHT_FAT * r[k] / L2.G_WALK
                if v < fat.get(k, (np.inf,))[0]:
                    fat[k] = (v, r["knuckle"])
                if k != "cap_washer_cyc":
                    creep[k] = min(creep.get(k, np.inf), 0.4 * r[k])
            for k in cf:
                if k not in r:
                    continue
                v = CF_BEAR_FAT * r[k] / L2.G_WALK
                if v < fat.get(k, (np.inf,))[0]:
                    fat[k] = (v, r["knuckle"])
            for k in net:
                if k not in r:
                    continue
                v = L2.CFRP_FAT_FI * r[k] / L2.G_WALK
                if v < fat.get(k, (np.inf,))[0]:
                    fat[k] = (v, r["knuckle"])
        Aw = math.pi / 4 * (WASHER_M3[0] ** 2 - WASHER_M3[1] ** 2)
        creep["cap washer under preload"] = 0.4 * PAHT_Z * Aw / PRELOAD_M3
        for k in ("pan_bolt_cf", "hip_bolt_cf"):
            fat[k] = (CF_BEAR_FAT * sr[k] / L2.G_WALK, "pan")
        for k in ("pan_bolt_paht", "hip_bolt_paht", "end_disc", "rail_strain"):
            fat[k] = (L2.PAHT_FAT * sr[k] / L2.G_WALK, "saddle")
            creep[k] = 0.4 * sr[k]
        fat["foot pin"] = (min(CF_BEAR_FAT, L2.PAHT_FAT) * sr["foot_pin"] / L2.G_WALK, "foot")
        fat["foot boot"] = (L2.PAHT_FAT * fb["sf"] / L2.G_WALK, fb["node"])
        fat["stay-top collar"] = (L2.PAHT_FAT * stc["sf_collar"] / L2.G_WALK, "bush_top")
        fat["hip inserts"] = (0.5 * hn["sf_insert"] / L2.G_WALK, "HP")
        creep["foot boot"] = 0.4 * fb["sf"]
        creep["stay-top collar"] = 0.4 * stc["sf_collar"]
        cj = cr["joints"].get("crown_corner")
        if cj:
            fat["crown corner bond"] = (cj[0] * req * L2.BOND_FAT / L2.G_WALK, "crown_corner")
        row["fatigue"] = fat
        row["creep"] = creep
    return row


def _task(args):
    cand, torso = args
    from huntkit.fea.load_standard import ls1_envelope
    rows = []
    for variant, cases in ls1_envelope("C").items():
        for c in cases:
            rows.append(run_case(cand, torso, variant, c, posts=(c.name == "tall_load_posts")))
    return rows


def evaluate(cand: dict, procs: int = 2, torsos=TORSOS) -> dict:
    t0 = time.time()
    args = [(cand, t) for t in torsos]
    if procs > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(procs, len(args))) as pool:
            parts = pool.map(_task, args)
    else:
        parts = [_task(a) for a in args]
    rows = [r for p in parts for r in p]
    return {"cand": cand, "rows": rows, "summary": summarize(rows), "seconds": time.time() - t0}


JOINT_LABELS = {
    "bar_pin_cf": "bar pin: CFRP wall bearing", "bar_pin_paht": "bar pin: PAHT boss bearing",
    "bar_pin_shear": "bar pin: Ti shear", "bar_shear_out": "bar pin: tube shear-out",
    "bar_net_section": "bar net section at the pin (notched FPF)", "socket_contact": "bar socket contact (PAHT Z)",
    "sleeve_contact": "stay sleeve contact (PAHT Z)", "cap_bolt": "cap M3 Ti bolt (preload + pull-off)",
    "cap_washer": "cap washer bearing (PAHT Z)", "cap_washer_cyc": "cap washer, cyclic part (PAHT Z)", "foot_pin": "foot pin (uplift + torque)",
    "end_disc": "stay end on Al disc / boot floor", "pan_bolt_cf": "pan M4 bolt: QI pan bearing",
    "pan_bolt_paht": "pan M4 bolt: saddle tab bearing", "hip_bolt_cf": "hip node M4 through pan: pan bearing",
    "hip_bolt_paht": "hip node M4: printed bearing", "hip_bolt_ti": "hip node M4 Ti tension",
    "rail_splice": "rail splice 2 x M4 (mid knuckle to saddle)", "rail_strain": "printed rail / sleeve compatibility strain",
    "stay_pin_cf": "stay-top radial pins: CFRP wall bearing", "stay_pin_paht": "stay-top radial pins: PAHT bearing",
    "stay_pin_shear": "stay-top radial pins: Ti shear", "stay_net_section": "stay stub net section at the radial pins",
}


def summarize(rows: list) -> dict:
    checks = {}

    def put(key, val, where, fam):
        if val is None or not np.isfinite(val):
            return
        if key not in checks or val < checks[key][0]:
            checks[key] = (float(val), where, fam)
    by_case = {}
    for r in rows:
        where = f"{r['case']}|{r['torso']:g}|{'IM3' if r['variant'] == 'strap_upper' else 'bar'}"
        vals = []
        for g, (sf, mid, _) in r["members"].items():
            put(f"member: {g}", sf, f"{where} {mid}", "strength")
            vals.append(sf)
        if r["buckling"] is not None:
            put("frame buckling", r["buckling"], where, "strength")
            vals.append(r["buckling"])
        for k, (sf, mid) in r["crown"]["members"].items():
            put(f"crown: {k}", sf, f"{where} {mid}", "strength")
            vals.append(sf)
        for k, (a, pk, mid) in r["crown"]["joints"].items():
            put(f"crown: {k} bond avg", a, where, "joint")
            put(f"crown: {k} bond peak", pk, where, "joint")
            vals += [a, pk]
        for k, v in r["crown"]["bushings"].items():
            put(f"crown: {k}", v, where, "joint")
            vals.append(v)
        for k, v in r["plate"].items():
            put(f"lumbar pan: {k}", v, where, "strength")
            vals.append(v)
        for k, (v, w, _) in r["joints"].items():
            put(f"joint: {JOINT_LABELS.get(k, k)}", v, f"{where} {w}", "joint")
            vals.append(v)
        key = (r["case"], r["variant"])
        mn = min(v for v in vals if np.isfinite(v))
        if key not in by_case or mn < by_case[key][0]:
            by_case[key] = (mn, r["torso"])
        if "fatigue" in r:
            for k, (f, mid) in r["fatigue"].items():
                put(f"fatigue: {JOINT_LABELS.get(k, k)}", f, f"{r['torso']:g}|{'IM3' if r['variant'] == 'strap_upper' else 'bar'} {mid}", "fatigue")
            for k, v in r["creep"].items():
                put(f"creep-rupture 40 C: {JOINT_LABELS.get(k, k)}", v, f"{r['torso']:g}", "creep")
    fam = {f: {k: v for k, v in checks.items() if v[2] == f} for f in ("strength", "joint", "fatigue", "creep")}
    mins = {f: min(d.items(), key=lambda kv: kv[1][0]) for f, d in fam.items() if d}
    passes = all(v[1][0] >= 1.0 for v in mins.values())
    return {"checks": checks, "min": {f: (v[1][0], v[0], v[1][1]) for f, v in mins.items()},
            "by_case": {f"{k[0]}|{k[1]}": v for k, v in by_case.items()}, "pass": passes}


# ----------------------------------------------------------------------------- mass, cost, print
def _shell(d, L, t):
    return math.pi * (d + 2 * GEO["gap"] + t) * t * L


def parts(cand: dict) -> list[dict]:
    """Printed parts per side (volume mm3, feature g) and their fasteners. Shell = channel wall around the tube;
    'fill' = generative windowing of long sleeves (ASSUMPTION 0.65 solid)."""
    ds = cand["stay_t"]["od"]
    t = GEO["shell_t"]
    fl = 1 + GEO["flare"]
    fill = GEO["saddle_fill"]
    P4, P3 = "M4 Ti pin set (bolt 25 mm + nut + 2 washers)", "M3 Ti cap set (bolt 16 + nut + 2 penny washers + Belleville pair)"
    out = []

    def boss(n):                 # bolt flange boss 10 x 10 x 8 mm per bolt hole, minus the hole
        return n * (10 * 10 * 8 - math.pi * 4 * 8)

    def socket(b):
        db = b["od"]
        return (_shell(db, GEO["socket_mm"], t)
                + math.pi / 4 * ((db + 2 * GEO["neck_t"]) ** 2 - db ** 2) * (GEO["neck_mm"] - ds / 2 - t))
    # mid knuckle: sleeve z 205-355 (z 250 lash eye, IM2 seat), bar socket, splice lap to the saddle
    v_mid = (_shell(ds, 295.0 - GEO["saddle_mm"], t) * fill + _shell(ds, GEO["rail_top"] - 295.0, t)
             + socket(cand["bar_t"])
             + boss(GEO["cap_bolts"] + 1 + 2) + 30 * 14 * GEO["pan_tab_t"]) * fl
    out.append({"name": "mid knuckle z 205-355 (body + cap: bar socket, IM2 seat, z 250 wing lash, splice lap)",
                "qty": 2, "vol_mm3": v_mid, "feature_g": 4.0 + 2.0,
                "fasteners": {P4: 1 + 2, P3: GEO["cap_bolts"] + 1}, "pieces": 2})
    # upper knuckle: sleeve z 410-530 + stay-top bushing collar, bar socket, pawl side, IM3 + B-24 eye, z 420 lash
    v_up = (_shell(ds, 485.0 - GEO["upper_sleeve_bot"], t) * fill + _shell(ds, 530.0 - 485.0, t)
            + _shell(ds, 35.0, 3.0) * 0.5
            + socket(cand["ubar_t"]) + boss(GEO["cap_bolts"] + 1 + 2)) * fl
    out.append({"name": "upper knuckle z 410-530 (body + cap: stay-top collar, bar socket, IM3 + B-24 eye, z 420 lash)",
                "qty": 2, "vol_mm3": v_up, "feature_g": 5.0 + 2.0 + 2.0,
                "fasteners": {P4: 1, P3: GEO["cap_bolts"] + 2, "Ti dowel 3 x 6 (radial stay pin)": 2}, "pieces": 2})
    v_sad = (_shell(ds, GEO["saddle_mm"], t) * fill + math.pi / 4 * (ds + 2 * t) ** 2 * 4
             + GEO["pan_bolts_per_side"] * (14 * 12 * GEO["pan_tab_t"]) + boss(4)) * fl
    out.append({"name": "foot-saddle z 0-205 (boot, Al end disc, foot pin, hinge pins z 60, US pins, z 80/110/190 "
                        "hard points, pan tabs)",
                "qty": 2, "vol_mm3": v_sad, "feature_g": 6.0 + 3 * 2.5,
                "fasteners": {P4: 1, "M4 Ti pan set (bolt 16 mm + nut + 2 washers)": GEO["pan_bolts_per_side"],
                              P3: 4, "Al end disc 20 x 1.5": 1}, "pieces": 2})
    a, b = L2.HIP_FLANGE
    out.append({"name": "hip node (Ti-mount boss, 4 x M5 inserts, bolted through the pan)", "qty": 1,
                "vol_mm3": a * b * 3.0 + math.pi / 4 * (30.0 ** 2 - 10.0 ** 2) * L2.PIVOT_STANDOFF * 0.6,
                "feature_g": 0.0, "fasteners": {"M4 Ti pan set (bolt 16 mm + nut + 2 washers)": 4}, "pieces": 1})
    for p in out:
        p["printed_g"] = p["vol_mm3"] * L2.RHO_PAHT + p["feature_g"]
        p["fastener_g"] = sum(FASTENER_G[k] * n for k, n in p["fasteners"].items())
    return out


def tube_lengths(cand, model19) -> dict:
    Ls = L2._member_len(model19, ["stay"]) / 2
    sp = 230.0
    Lb = sp - 2 * GEO["neck_mm"]
    return {"stays (2)": (2 * Ls, cand["stay_t"]), "mid bar": (Lb, cand["bar_t"]), "upper bar": (Lb, cand["ubar_t"])}


def mass_rollup(cand: dict, model19: dict) -> dict:
    tubes = {k: L * t["g_per_m"] / 1000 for k, (L, t) in tube_lengths(cand, model19).items()}
    ps = parts(cand)
    printed = sum(p["qty"] * p["printed_g"] for p in ps)
    fast = sum(p["qty"] * p["fastener_g"] for p in ps)
    pan_g = 250.0 * 140.0 * cand["pan_t"] * L2.RHO_CF          # flat QI plate, no formed flanges
    groups = {"tubes": sum(tubes.values()), "printed knuckles + saddles + hip node": printed,
              "fasteners (Ti pins, M3 caps, Belleville, Al discs)": fast,
              "lumbar pan (flat QI sheet) + pad-up": pan_g + L2.PADUP_G,
              "crown + torso adjust (unchanged)": sum(L2.CROWN.values()),
              "Ti pivot mount + inserts": sum(L2.PIVOT.values())}
    total = sum(groups.values())
    return {"tubes": tubes, "parts": ps, "groups": groups, "frame_g": total,
            "frame_spreader_g": total + L2.TODAY["spreader_g"], "printed_g": printed,
            "printed_vol_cm3": sum(p["qty"] * p["vol_mm3"] for p in ps) / 1e3,
            "n_printed_pieces": sum(p["qty"] * p["pieces"] for p in ps)}


def print_hours(mr) -> float:
    from .frame_production import print_hours as ph
    return ph(mr["printed_vol_cm3"] * 1e3) + 0.15 * mr["n_printed_pieces"]


def cost(cand, mr, model19) -> dict:
    """USD at 1 / 10 / 100 frames. Tubes by vendor price (Rock West tiers 1-9 / 10-49 / 50+)."""
    out = {}
    for n, tier in ((1, 1.0), (10, 100.79 / 111.99), (100, 90.59 / 111.99)):
        c = {}
        L = {}
        for k, (Lk, t) in tube_lengths(cand, model19).items():
            L.setdefault(t["label"], [0.0, t])[0] += Lk
        for lab, (Lk, t) in L.items():
            if "Rock West" in lab:
                n_tubes = math.ceil(Lk * 1.05 / 2000.0 * n) / n          # whole 2 m sticks
                c[f"tube: {lab}"] = n_tubes * 111.99 * tier
            else:
                c[f"tube: {lab}"] = Lk / 1000 * t["usd_per_m"] * (1.0 if n == 1 else 0.85 if n == 10 else 0.7) + (
                    40.0 / n)                                            # special-order set-up (ASSUMPTION)
        c["crown tubes (unchanged)"] = (2 * 430 * 16 + 214 * 18 + 300 * 20) / 1000 / 16 * L2.TUBE_USD_PER_M_16
        c["PAHT-CF filament + 15 % failed prints"] = (mr["printed_g"] + 44.0) * 1.15 * 0.08
        c["QI CF sheet 1.5 mm, 250 x 140 (cfrp_plate_quasi_iso $350/m2) + waterjet (ASSUMPTION $15)"] = (
            0.27 * 0.16 * 350.0 + 15.0)
        nb = sum(p["qty"] * sum(p["fasteners"].values()) for p in mr["parts"])
        c[f"Ti M3/M4 bolts, nuts, washers, Belleville ({nb} sets, ASSUMPTION $1.6/set)"] = nb * 1.6 * (
            1.0 if n == 1 else 0.8)
        c["crown corner MMA + glass beads (fixed interface, 1 small cartridge)"] = 25.0
        c["SLM Ti hip mount (ASSUMPTION, mass_cut.md)"] = 35.0
        c["M5 heat-set inserts + UHMWPE bushings"] = 12.0
        c["drill jig (printed) + 4.0 mm carbide drill + 4.0 H8 reamer (ASSUMPTION)"] = 45.0 / n
        out[str(n)] = {"lines": c, "total": sum(c.values())}
    return out


def stiffness(cand, torso=19.0) -> dict:
    """frame_light2.stiffness on this model (hip pivot clamped)."""
    orig = L2.build
    try:
        L2.build = lambda c, t, posts=False: build(c, t, posts)
        return L2.stiffness(cand, torso)
    finally:
        L2.build = orig


# ----------------------------------------------------------------------------- sizing + run
def run(log=print, procs: int = 2) -> dict:
    t0 = time.time()
    trials = []
    options = [dict(), dict(ubar="RW46710"), dict(ubar=("rw45", 20, 5)), dict(ubar=("rw45", 22, 4))]
    best = None
    for o in options:
        cand = rod_candidate(**o)
        ev = evaluate(cand, procs)
        s = ev["summary"]
        log(f"[ROD {cand['keys']}] " + ", ".join(f"{f} {v[0]:.2f} ({v[1]})" for f, v in s["min"].items())
            + f" pass={s['pass']} ({ev['seconds']:.0f} s)")
        trials.append({"keys": cand["keys"], "min": s["min"], "pass": s["pass"]})
        st = stiffness(cand)
        mr = mass_rollup(cand, st["model"])
        trials[-1]["frame_g"] = mr["frame_g"]
        if s["pass"] and (best is None or mr["frame_g"] < best[2]["frame_g"]):
            best = (ev, st, mr)
    if best is None:
        ev = evaluate(rod_candidate(), procs)
        st = stiffness(ev["cand"])
        best = (ev, st, mass_rollup(ev["cand"], st["model"]))
    ev, st, mr = best
    return {"date": "2026-11-10", "standard": "HA-LS-1 rev C", "geo": GEO, "trials": trials, "best": ev,
            "stiffness": {"carry_dy_mm": st["carry_dy_mm"], "torsion_Nm_per_deg": st["torsion_Nm_per_deg"]},
            "mass": mr, "print_h": print_hours(mr), "cost": cost(ev["cand"], mr, st["model"]),
            "preload_creep": preload_creep(), "seconds": time.time() - t0, "_model": st["model"],
            "_u": st["u_carry"]}


def result_json(ctx) -> dict:
    s = ctx["best"]["summary"]
    mr = ctx["mass"]
    fsg = mr["frame_spreader_g"]
    gov = s["min"]["strength"] if s["min"]["strength"][0] <= s["min"]["joint"][0] else s["min"]["joint"]
    return {
        "team": "C",
        "concept_name": "ROD",
        "one_line": ("Stock 20 mm roll-wrapped carbon stays + bars held in bolted PAHT-CF clamshell rails and knuckles by "
                     "Ti cross-pins, end bearing and contact only (no glue, no friction credit); flat QI pan bolted on; "
                     "crown, pivot and spreader unchanged."),
        "frame_g": round(mr["frame_g"], 1),
        "frame_plus_spreader_g": round(fsg, 1),
        "pack_mass_corrie_b2_M_g": round(3964.5 - (1225.0 - fsg), 1),
        "passes_rev_c": bool(s["pass"]),
        "worst_strength_margin": round(s["min"]["strength"][0], 3),
        "worst_fatigue_margin": round(s["min"]["fatigue"][0], 3),
        "worst_joint_margin": round(s["min"]["joint"][0], 3),
        "governing_case": f"{gov[1]} @ {gov[2]}",
        "torsion_stiffness_vs_today": round(ctx["stiffness"]["torsion_Nm_per_deg"] / L2.TODAY["torsion_Nm_per_deg"], 2),
        "print_hours": round(ctx["print_h"], 1),
        "printer": "H2S home",
        "cost_usd": {k: round(v["total"]) for k, v in ctx["cost"].items()},
        "build_hours": 9.0,
        "skill_level": "intermediate",
        "looks_generative": False,      # reads as a ladder with windowed printed sleeves, not the branch look
        "patents_checked": [
            "US 10,952,523 (Mystery Ranch, load lifter / crown guardrail): crown unchanged",
            "US 10,668,965 (Divergent, node with adhesive injection): no adhesive, no injection ports, design-around",
            "KUIU one-piece frame family: multi-part tube ladder, not one-piece",
            "docs/DECISIONS.md patent guardrails: no change to crown, lifters, torso adjust",
        ],
        "governing_assumptions": [
            "ASSUMPTION A1: CFRP pin bearing 300 MPa ultimate x 0.8 hot/wet on the 1 mm 0/90 roll-wrapped wall, M4 pin, no clamp-up (coupon RC-2)",
            "ASSUMPTION A2: filled-hole / unnotched strength 0.55 at the 4 mm bar-pin holes and the 3 mm radial stay-pin holes (coupon RC-3)",
            "ASSUMPTION A3: PAHT-CF pin bearing >= XY tensile 88 x 0.8; channel contact checked at Z 47 x 0.8 (coupon RC-4)",
            "ASSUMPTION A4: bearing fatigue at 1e5 = 0.5 x static for CFRP, 0.3 x static for PAHT (record ratio) (coupon RC-2f)",
            "ASSUMPTION A5: zero friction credit; Belleville-held M3 preload only keeps caps closed (coupon RC-5 creep hold)",
            "ASSUMPTION A6: Rock West 46710 modelled at 0.845 mm with repo plies (vendor 1.0 mm); one 3-point bend coupon per batch (RC-1)",
            "ASSUMPTION A7: printed neck = PAHT annulus t 4 mm around the bar line from the stay axis to the bar tip",
            "ASSUMPTION A8: flat 1.5 mm QI pan with printed saddles replaces the formed pan + flanges at the same beam-model plate",
        ],
        "coupon_tests": [
            "RC-1 tube 3-point bend + weigh, 1 per 2 m stick (accept >= modelled EI and strength)",
            "RC-2 pin bearing: 20 mm tube, reamed 4.0 hole, M4 Ti pin in a printed boss, pull to failure, 5 pcs; pass mean >= 1.25 x 240 MPa design, min >= 240",
            "RC-2f bearing fatigue: 1e5 cycles 0 -> 0.5 x static bearing, no hole elongation > 0.1 mm",
            "RC-3 notched tube 4-point bend: 400 mm offcuts with (a) a 4 mm cross hole (bar) and (b) two 3 mm single-wall holes (stay stub) at mid-span, pinned, to failure, 3 pcs each; pass >= 0.55 x unnotched",
            "RC-4 printed knuckle proof: mid + upper knuckle on tube offcuts, bar pulled / twisted to 1.5 x the largest factored end load, 3 pcs each, then to failure",
            "RC-5 clamp creep hold: torqued M3 cap with Belleville pair, 40 C 8 h + 7 days RT, residual torque >= 50 %",
            "RC-6 foot-saddle: stay end on the Al disc, 2 kN compression + 1 kN uplift on the foot pin, 3 pcs",
            "then HA-LS-1 T9, T1-T5, T2u on frames P1/P2 as load_standard.md section 5",
        ],
    }


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items() if not str(k).startswith("_") and k not in ("rows", "model")}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def save(ctx) -> dict:
    TEAM_DIR.mkdir(parents=True, exist_ok=True)
    res = result_json(ctx)
    RESULT_JSON.write_text(json.dumps(_jsonable(res), indent=1))
    detail = {k: v for k, v in ctx.items() if not k.startswith("_")}
    DETAIL_JSON.write_text(json.dumps(_jsonable(detail), indent=1))
    return res


def main():
    ctx = run()
    res = save(ctx)
    print(json.dumps(_jsonable(res), indent=1))
    import pickle
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "ctx.pkl").write_bytes(pickle.dumps(ctx))


if __name__ == "__main__":
    main()


# ============================================================================= visuals
WORK = REPO_ROOT / "outputs" / "frame_comp_C" / "render"
BPY = Path("/tmp/claude-0/-home-user-Hunting-appeal/4e7b6300-4974-5e9f-8ec3-7f9ff06a9ed6/scratchpad/bpyenv/bin/python")
TODAY_DX = -420.0


def _R():
    from . import frame_light2_render as R
    return R


def _sdf_mesh(lo, hi, h, fn):
    import trimesh
    from skimage.measure import marching_cubes
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    xs = [np.arange(lo[i], hi[i] + h, h) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing="ij")
    P = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
    d = fn(P).reshape(X.shape)
    v, f, _, _ = marching_cubes(d, 0.0, spacing=(h, h, h))
    m = trimesh.Trimesh(v + lo, f, process=True)
    comps = m.split(only_watertight=False)
    big = max(len(c.faces) for c in comps)
    m = trimesh.util.concatenate([c for c in comps if len(c.faces) > 0.02 * big])
    trimesh.smoothing.filter_taubin(m, iterations=6)
    return m


def _shell_z(P, c, z0, z1, ri, ro, windows=0, wlen=26.0, wz=(0, 0)):
    """Capped hollow sleeve along z at xy centre c, with staggered elliptical windows between wz[0]..wz[1]."""
    r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
    d = np.maximum(np.maximum(r - ro, ri - r), np.maximum(z0 - P[:, 2], P[:, 2] - z1))
    if windows:
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        zs = np.arange(wz[0] + wlen / 2 + 4, wz[1] - wlen / 2 - 2, wlen + 7)
        for i, zc in enumerate(zs):
            for k in range(windows):
                ph = 2 * np.pi * k / windows + (np.pi / windows if i % 2 else 0.0)
                dth = np.angle(np.exp(1j * (th - ph)))
                e = np.hypot(dth * ro / (np.pi * ro / windows * 0.36), (P[:, 2] - zc) / (wlen / 2)) - 1.0
                d = np.maximum(d, -e * 4.0)
    return d


def _shell_seg(P, a, b, ri, ro):
    dist, t = _R()._seg_dist(P, a, b)
    L = np.linalg.norm(b - a)
    s = (P - a) @ ((b - a) / L)
    return np.maximum(np.maximum(dist - ro, ri - dist), np.maximum(-s, s - L))


def build_meshes(cand: dict, out: Path = WORK) -> dict:
    """STLs (mm, frame coordinates) of ROD at 19 in and today's frame 420 mm to the left."""
    import trimesh
    out.mkdir(parents=True, exist_ok=True)
    m = build(cand, 19.0)
    N = {k: np.array(v, float) for k, v in m["nodes"].items()}
    ds, dbar, dub = cand["stay_t"]["od"], cand["bar_t"]["od"], cand["ubar_t"]["od"]
    t = GEO["shell_t"]
    ri_s, ro_s = ds / 2 + GEO["gap"], ds / 2 + GEO["gap"] + t
    carbon, printed, ti, crown = [], [], [], []
    cyl = L2_render_cyl
    for tag in ("L", "R"):
        carbon.append(cyl(N[f"S{tag}0"] + [0, 0, 1.5], N[f"S{tag}530"], ds / 2))
        crown.append(cyl(N[f"C{tag}530"], N[f"C{tag}top"], 8.0))
    for z, d in ((330.0, dbar), (520.0, dub)):
        carbon.append(cyl(N[f"SL{z:g}"] + [GEO["neck_mm"], 0, 0], N[f"SR{z:g}"] - [GEO["neck_mm"], 0, 0], d / 2))
    crown.append(cyl(N["CLtop"], N["CRtop"], 9.0))
    lowest = min((n for n in N if n.startswith("SP")), key=lambda n: N[n][2])
    crown.append(cyl(N["TB1"], N[lowest], 10.0))
    yL = N["SL120"][1]
    pan = trimesh.creation.box(extents=(236.0, cand["pan_t"] * 1.2, 140.0))
    pan.apply_translation((0.0, yL - ds / 2 - t - 2.0, 120.0))
    carbon.append(pan)
    for tag, sx in (("L", -1.0), ("R", 1.0)):
        c = N[f"S{tag}0"][:2]
        inward = np.array([-sx, 0.0, 0.0])

        def saddle(P, c=c, sx=sx):
            d = _shell_z(P, c, -3.0, 205.0, ri_s, ro_s, windows=3, wz=(28, 200))
            boot = _shell_z(P, c, -3.0, 25.0, 0.0, ro_s + 1.5)
            d = _R()._smin(d, np.maximum(boot, -(_shell_z(P, c, 1.5, 40, 0, ri_s))), 4.0)
            for z in (50.0, 90.0, 120.0, 155.0, 190.0):         # pan tabs toward the wearer + inward
                a = np.array([c[0], c[1], z])
                b = a + np.array([-sx * 16.0, -ro_s - 2.0, 0.0])
                dd, _ = _R()._seg_dist(P, a, b)
                d = _R()._smin(d, dd - 5.0, 4.0)
            hz = np.array([c[0], c[1], 60.0])                    # hinge-pin boss aft
            dd, _ = _R()._seg_dist(P, hz, hz + [sx * 4, 18.0, 0])
            d = _R()._smin(d, dd - 5.5, 4.0)
            return np.maximum(d, -(np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) - ri_s))
        lo = np.array([c[0] - 40, c[1] - 40, -6]); hi = np.array([c[0] + 40, c[1] + 40, 212])
        printed.append(_sdf_mesh(lo, hi, 1.0, saddle))
        for z0, z1, zh, db, wz in ((205.0, 355.0, 330.0, dbar, (205, 300)), (410.0, 533.0, 520.0, dub, (410, 490))):
            ri_b, ro_b = db / 2 + GEO["gap"], db / 2 + GEO["gap"] + t

            def knuckle(P, c=c, z0=z0, z1=z1, zh=zh, ri_b=ri_b, ro_b=ro_b, wz=wz, inward=inward):
                d = _shell_z(P, c, z0, z1, ri_s, ro_s, windows=3, wz=wz)
                hub = np.array([c[0], c[1], zh])
                a = hub + inward * (ro_s - 1.0)
                b = hub + inward * (GEO["neck_mm"] + GEO["socket_mm"])
                sock = _shell_seg(P, hub + inward * GEO["neck_mm"], b, ri_b, ro_b)
                neck, _ = _R()._seg_dist(P, a, hub + inward * (GEO["neck_mm"] + 2))
                d = _R()._smin(d, sock, 4.0)
                d = _R()._smin(d, neck - (ro_b + 1.0), 6.0)
                for up in (1.0, -1.0):                     # root fingers from the socket onto the sleeve
                    f0 = hub + inward * (GEO["neck_mm"] + 20) + np.array([0, 0, up * (ro_b - 1)])
                    f1 = hub + np.array([0, 0, up * 38.0]) + inward * (ro_s - 1)
                    dd, tt = _R()._seg_dist(P, f0, f1)
                    d = _R()._smin(d, dd - (2.6 * (1 - tt) + 1.2), 3.0)
                d = np.maximum(d, -(np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) - ri_s))
                dist_b, _ = _R()._seg_dist(P, hub + inward * (GEO["neck_mm"] - 1), b + inward * 2)
                return np.maximum(d, -(dist_b - ri_b))
            lo = np.array([min(c[0], c[0] - sx * 90) - 25, c[1] - 30, z0 - 5])
            hi = np.array([max(c[0], c[0] - sx * 90) + 25, c[1] + 30, z1 + 5])
            printed.append(_sdf_mesh(lo, hi, 1.0, knuckle))
            # Ti hardware: bar pin (along y) and cap bolt heads
            pp = np.array([c[0], c[1], zh]) + inward * (GEO["neck_mm"] + GEO["socket_mm"] - GEO["bar_pin_from_tip"])
            ti.append(cyl(pp + [0, -ro_b - 2.5, 0], pp + [0, ro_b + 2.5, 0], 2.0))
            ti.append(cyl(pp + [0, ro_b + 1.0, 0], pp + [0, ro_b + 3.5, 0], 3.5))
            for zz in (zh - 30.0, zh + (8.0 if zh > 500 else 22.0)):
                q = np.array([c[0], c[1], zz]) + inward * (ro_s + 3.0)
                ti.append(cyl(q + [0, ro_s - 3, 0], q + [0, ro_s + 0.5, 0], 3.0))
        ti.append(cyl(np.array([c[0] - 13, c[1], 20.0]), np.array([c[0] + 13, c[1], 20.0]), 2.0))
    hp = N["HP"]
    face = np.array([0.0, yL - ds / 2 - t - 4.0, 120.0])

    def hipnode(P):
        d = np.maximum(np.abs(P[:, 0]) - 35, np.maximum(np.abs(P[:, 1] - face[1]) - 1.8, np.abs(P[:, 2] - 120) - 30))
        dd, _ = _R()._seg_dist(P, face, hp)
        d = _R()._smin(d, dd - 9.0, 6.0)
        for sx_, sz in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            dd, tt = _R()._seg_dist(P, face + [sx_ * 30, 0, sz * 26], hp + [sx_ * 6, 0, sz * 6])
            d = _R()._smin(d, dd - (3.0 - 1.2 * tt), 4.0)
        return d
    printed.append(_sdf_mesh(face + [-45, -40, -42], face + [45, 12, 42], 1.0, hipnode))
    ti.append(cyl(hp + np.array([0, 3.0, 0]), hp - np.array([0, 6.0, 0]), 9.0))
    files = {}
    for name, parts_, dx in (("rod_carbon", carbon + crown, 0.0), ("rod_printed", printed, 0.0),
                             ("rod_ti", ti, 0.0), ("today_carbon", crown, TODAY_DX)):
        mm = trimesh.util.concatenate([p for p in parts_ if p is not None])
        mm.apply_translation((dx, 0, 0))
        f = out / f"{name}.stl"
        mm.export(f)
        files[name] = str(f)
    body = trimesh.load(REPO_ROOT / "designs" / "pack_5200" / "print" / "frame" / "genframe_assembled.stl")
    body.apply_translation((TODAY_DX, 0, 0))
    f = out / "today_printed.stl"
    body.export(f)
    files["today_printed"] = str(f)
    (out / "manifest.json").write_text(json.dumps({"files": files}, indent=1))
    return files


def L2_render_cyl(p0, p1, r):
    from . import frame_light2_render as R
    return R._cyl(p0, p1, r)


def _bpy_main(work: Path, prefix: str, samples: int):
    """Runs in the bpy venv. Two Cycles shots at 1200 x 900 (RULES: max 2 renders)."""
    import bpy
    from huntkit.viz3d import cycles_render as CR
    man = json.loads((work / "manifest.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = CR.setup_scene(samples, (1200, 900), 4)
    mats = {}
    for key, base, rough, coat, bump in (("carbon", "#101112", 0.28, 0.9, 0.0), ("printed", "#4b4945", 0.72, 0.0, 0.35),
                                         ("ti", "#8d8a84", 0.35, 0.0, 0.0)):
        mt = bpy.data.materials.new(key)
        mt.use_nodes = True
        CR.solid(mt, CR.hexlin(base), rough, metallic=1.0 if key == "ti" else 0.0, coat=coat, noise_bump=bump)
        mats[key] = mt
    objs = []
    for name, path in man["files"].items():
        bpy.ops.wm.stl_import(filepath=path)
        ob = bpy.context.selected_objects[0]
        ob.name = name
        ob.scale = (0.001, 0.001, 0.001)
        mat = "carbon" if "carbon" in name else ("ti" if name.endswith("_ti") else "printed")
        ob.data.materials.clear()
        ob.data.materials.append(mats[mat])
        for p in ob.data.polygons:
            p.use_smooth = True
        objs.append(ob)
    bpy.context.view_layer.update()
    bpy.ops.mesh.primitive_plane_add(size=12)
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    CR.solid(fm, CR.hexlin("#d9d6cd"), 0.9, spec=0.2)
    floor.data.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    key = CR._area("key", 120.0, 1.6, (1.0, 0.95, 0.88), 1.2)
    fill = CR._area("fill", 22.0, 2.4, (0.88, 0.93, 1.0), 1.6)
    rim = CR._area("rim", 60.0, 1.0, (1.0, 1.0, 1.0), 2.0)
    shots = [("pair", -30.0, 14.0, None, 1.0, "Today's printed frame (left) vs ROD (right)",
              "ROD: stock carbon tubes pinned in bolted PAHT-CF clamshells, no glue; same carbon crown"),
             ("knuckle", 150.0, 18.0, ((0.02, -0.05, 0.19), (0.16, 0.06, 0.37)), 1.0,
              "ROD: mid knuckle + rail, bag side",
              "carbon visible through the printed windows; Ti pins and cap bolts; bar socket 55 mm")]
    outs = []
    for nm, az, el, box, zoom, cap, sub in shots:
        for o in objs:
            o.hide_render = nm != "pair" and o.name.startswith("today")
        lo, hi = CR.visible_bounds([o for o in objs if not o.hide_render])
        floor.location = (0.5 * (lo[0] + hi[0]), 0.5 * (lo[1] + hi[1]), lo[2] - 0.001)
        bmin, bmax = (lo, hi) if box is None else box
        cd.angle_y = math.radians(28.0)
        pos, tgt = CR.fit_camera(bmin, bmax, az, el, 28.0, 1200 / 900, zoom)
        cam.location = pos
        CR._aim(cam, tgt)
        dist = math.dist(pos, tgt)
        cd.dof.use_dof = True
        cd.dof.focus_distance = dist
        cd.dof.aperture_fstop = 8.0
        CR.place_rig((key, fill, rim), az, tgt, max(1.6, 0.75 * dist))
        raw = work / f"_raw_{nm}.png"
        sc.render.filepath = str(raw)
        bpy.ops.render.render(write_still=True)
        out = Path(f"{prefix}_{nm}.png")
        CR.composite(raw, out, cap, sub)
        CR.shrink_png(out)
        outs.append(str(out))
        print("RENDERED", out, flush=True)
    return outs


BPY_BOOT = ("import sys, types; sys.path.insert(0, {repo!r})\n"
            "for n, p in (('huntkit.gendesign', 'huntkit/gendesign'), ('huntkit.fea', 'huntkit/fea')):\n"
            "    m = types.ModuleType(n); m.__path__ = [{repo!r} + '/' + p]; sys.modules[n] = m\n"
            "from pathlib import Path\n"
            "import huntkit.gendesign.frame_comp_C as C\n"
            "C._bpy_main(Path({work!r}), {prefix!r}, {samples})\n")


def render(cand, samples: int = 32) -> list[str]:
    import subprocess
    build_meshes(cand)
    prefix = str(WORK / "shot")
    code = BPY_BOOT.format(repo=str(REPO_ROOT), work=str(WORK), prefix=prefix, samples=samples)
    r = subprocess.run([str(BPY), "-c", code], capture_output=True, text=True, timeout=3600, cwd=str(REPO_ROOT))
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    out = []
    for i, nm in enumerate(("pair", "knuckle"), start=1):
        dst = SCREENS / f"{SHOT}_{i}.png"
        dst.write_bytes(Path(f"{prefix}_{nm}.png").read_bytes())
        out.append(str(dst))
    return out


# ----------------------------------------------------------------------------- 2D plots (matplotlib)
def plot_margins(ctx, path) -> str:
    """Worst margin of the 24 lowest checks (all rev C cases, torsos, couple variants), one hue, 1.0 line."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ch = ctx["best"]["summary"]["checks"]
    rows = sorted(((v[0], k, v[1], v[2]) for k, v in ch.items()), key=lambda r: r[0])[:24][::-1]
    fig, ax = plt.subplots(figsize=(10, 9), dpi=110)
    fam_ink = {"strength": "#2a5d8f", "joint": "#5b8fc4", "fatigue": "#8db6de", "creep": "#b9d3ec"}
    y = np.arange(len(rows))
    ax.barh(y, [min(r[0], 4) for r in rows], color=[fam_ink[r[3]] for r in rows], height=0.7, edgecolor="white")
    ax.axvline(1.0, color="#222", lw=1.2)
    ax.text(1.02, len(rows) - 0.4, "pass line 1.0", fontsize=9, color="#222")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r[1][:58]}" for r in rows], fontsize=8.5)
    for yi, r in zip(y, rows):
        ax.text(min(r[0], 4) + 0.03, yi, f"{r[0]:.2f}  {r[2][:34]}", va="center", fontsize=7.5, color="#333")
    ax.set_xlim(0, 4.6)
    ax.set_xlabel("margin = SF / requirement (HA-LS-1 rev C)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, label=f) for f, c in fam_ink.items()], loc="lower right", fontsize=9,
              title="check family")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#ddd", lw=0.6)
    ax.set_axisbelow(True)
    s = ctx["best"]["summary"]["min"]
    ax.set_title("ROD (team C): 24 lowest margins, every rev C case, torso 15/19/23, both couple variants\n"
                 f"strength {s['strength'][0]:.2f} | joint {s['joint'][0]:.2f} | fatigue {s['fatigue'][0]:.2f} | "
                 f"creep {s['creep'][0]:.2f}  -> all >= 1.0", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_frame(cand, path) -> str:
    """Front view coloured by member utilisation (1 / margin, worst over the governing cases at 15 / 23 in) and a
    side view of the static-carry deflection (x 10) next to the undeformed frame."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors
    from huntkit.fea.load_standard import ls1_envelope
    util = {}
    for torso in (15.0, 23.0):
        for variant, cases in ls1_envelope("C").items():
            for case in cases:
                c = copy.copy(case)
                c.params = dict(c.params)
                c.buckling = False
                m = build(cand, torso, posts=(c.name == "tall_load_posts"))
                res = c.run(m)
                for mm in res.members:
                    if mm["group"] == "lumbar_plate_shear":
                        continue
                    u = float(c.required_sf) / max(float(mm["sf"]), 1e-9)
                    util[mm["id"]] = max(util.get(mm["id"], 0.0), u)
    m = build(cand, 19.0)
    st = stiffness(cand)
    N = m["nodes"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 8.5), dpi=110, gridspec_kw={"width_ratios": [2.2, 1]})
    norm = colors.Normalize(0, 1.0)
    cmap = matplotlib.colormaps["Blues"]
    for md in m["members"]:
        if md["group"] == "lumbar_plate_shear":
            continue
        a, b = (np.array(N[n]) for n in md["nodes"])
        u = util.get(md["id"], 0.0)
        lw = 1.2 if md["group"].startswith("lumbar") else (5 if md["group"] == "lug_neck" else 3.2)
        ax[0].plot([a[0], b[0]], [a[2], b[2]], color=cmap(0.15 + 0.85 * norm(min(u, 1.0))), lw=lw,
                   solid_capstyle="round")
    for k in ("SL", "SR"):
        for z, lab in ((0, "foot-saddle\n(pin z 20,\nAl disc)"), (330, "mid knuckle\n(rail, splice)"),
                       (520, "upper knuckle\n(radial pins z 525)")):
            p = N[f"{k}{z:g}"]
            ax[0].plot(p[0], p[2], "o", ms=9, mfc="none", mec="#555")
            if k == "SR":
                ax[0].text(p[0] + 14, p[2], lab, fontsize=8, va="center", color="#333")
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = fig.colorbar(sm, ax=ax[0], fraction=0.04, pad=0.02)
    cb.set_label("utilisation = required / SF (worst case, 1.0 = limit)")
    ax[0].set_aspect("equal")
    ax[0].set_xlim(-170, 230)
    ax[0].set_title("Front view (from the wearer), beam model, 19 in geometry", fontsize=10)
    ax[0].set_xlabel("x mm")
    ax[0].set_ylabel("z mm")
    ids = st["node_ids"]
    U = st["u_carry"]
    for md in m["members"]:
        if md["group"] == "lumbar_plate_shear" or md["group"].startswith("lumbar"):
            continue
        a, b = md["nodes"]
        pa, pb = np.array(N[a]), np.array(N[b])
        ax[1].plot([pa[1], pb[1]], [pa[2], pb[2]], color="#bbb", lw=2)
        da, db = U[ids.index(a)] * 10, U[ids.index(b)] * 10
        ax[1].plot([pa[1] + da[1], pb[1] + db[1]], [pa[2] + da[2], pb[2] + db[2]], color="#2a5d8f", lw=2)
    ax[1].set_aspect("equal")
    ax[1].set_title(f"Side: static carry, deflection x 10\nstay top {abs(st['carry_dy_mm']):.1f} mm (today 29.7)\n"
                    f"torsion {st['torsion_Nm_per_deg']:.2f} N m/deg (today 0.44)", fontsize=9)
    ax[1].set_xlabel("y mm (aft +)")
    for a_ in ax:
        for s in ("top", "right"):
            a_.spines[s].set_visible(False)
    fig.suptitle("ROD: member utilisation and deformed shape (HA-LS-1 rev C)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)
