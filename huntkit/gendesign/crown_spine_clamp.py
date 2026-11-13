"""BL-045 item 2: the crown spine clamp (spine-to-top-bar joint) from the frame model, and B-25's clearances on it.

The frame files carry no spine-clamp drawing: ``frame.yaml`` books 6 g ('spine clamp', ``pack5200.HW`` ASSUMPTION) and
``huntkit.fea.pack5200`` joins the spine to the top bar at node TB1 rigidly, with no joint check (the crown corners and
the stay hubs are checked by ``huntkit.fea.joints``; TB1 never was). BL-043 drew B-25 round an assumed clamp
(half-width 15 mm along the bar, 12 mm collar down the spine) and an assumed pawl housing (20 mm above the pawl line,
+/-18 mm). This module replaces the three assumptions with the real geometry:

1. **Joint loads** at TB1 from the frame model: every HA-LS-1 rev C case set (both bag-couple variants) on the three
   crown kits at both ends of their torso range (``crown_diet.build``, the beam model the crown records use): the
   spine's end forces at TB1 and the jump in the bar's internal forces across TB1, both factored.
2. **Sizing** of the clamp as the frame's own joint type, a bonded tube socket (``huntkit.fea.joints.bond_check``,
   the crown-corner rule of HA-LS-1 rev C: average shear >= the case factor, Volkersen peak >= 1.0 at limit load,
   fatigue <= 0.3 x lap shear at 0 -> 1.6 g): a machined 7075-T6 T-fitting, a socket on the spine and a saddle round
   the bar, MMA with the crown corners' 0.8 mm bondline. Shortest socket and saddle that pass, rounded up to 1 mm.
3. **Real geometry** of what sits under the clamp, measured on the H1 print STL (``print/frame_h1/h1_assembled.stl``):
   the pawl housing (top, half-width, fore-aft extent) and the spine channel through it, the printed body's top in the
   B-25 sleeve band, and the spine axis (channel centre) against the bar axis (frame model nodes).
4. **B-25 clearances** (``corrie_f.b25_topology``'s checks, re-run here with the real clamp and housing; corrie_f is not
   edited: the pack-designer imports the constants below).

Publishes ``SPINE_CLAMP`` and ``PAWL_HOUSING`` (the pack-designer imports them in place of SPINE_CLAMP_HALF,
SPINE_CLAMP_COLLAR, PAWL_HOUSING_HALF_W, PAWL_HOUSING_UP, UPPER_BAR_OD in corrie_f).

    python -m huntkit.gendesign.crown_spine_clamp      # JSON summary
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
FRAME_YAML = PACK / "frame.yaml"
H1_STL = PACK / "print" / "frame_h1" / "h1_assembled.stl"
OUT = REPO / "outputs" / "crown_spine_clamp"

# ------------------------------------------------------------------------------------------ rules and sources
KITS = ("a_S", "a_M", "a_L")       # crown_diet.specs(): the three adopted crown kits (owner 2026-11-11), today's legs
ADHESIVE = "adhesive_methacrylate_ma"   # frame.yaml joints.adhesive
BONDLINE_MM = 0.8                  # frame.yaml joints.crown_corner_bondline_mm (rev C, glass-bead spacer)
FITTING_MAT = "alu_7075_t6"        # the hub socket default of huntkit.fea.joints (hard-anodised, glass-bead bondline)
FITTING_WALL_MM = 0.8              # ASSUMPTION CLAMP-WALL: 0.8 mm turned 7075 wall. A thicker (stiffer) saddle raises the
#                                    Volkersen peak on the bar: 1.5 mm never reaches 1.0 at limit (0.93 plateau), 0.8 mm
#                                    does from 20 mm (sweep in the record); socket bending SF checked below
BOND_FAT_RATIO = 0.3               # HA-LS-1 rev C fatigue: bond shear <= 0.3 x lap shear at 0 -> 1.6 g
G_WALK = 1.6
PEAK_REQ_AT_LIMIT = 1.0            # load_standard.md 4.2: Volkersen peak >= 1.0 at LIMIT load
SADDLE_MIN_OVER_SOCKET_MM = 0.0    # the saddle is at least as long (along the bar) as the spine socket is wide
SOCKET_MIN_MM = 15.0               # ASSUMPTION SOCKET-MIN: socket depth >= 0.75 x the spine OD for alignment at bonding
#                                    (the bond rule alone asks 12 mm)
MIN_CLEAR_MM = 10.0                # corrie_f.MIN_CLEAR_MM (ASSUMPTION there): B-25 band to the clamp, gloved handling
B25_RUN_GAP = 2.0                  # corrie_f.B25_RUN_GAP: run's top edge 2 mm under the clamp collar
B25_NECK_W = 25.0                  # corrie_f.B25_NECK_W (DECISION B25-TOPO)
B25_W = 38.0                       # corrie_f.BRIDLE_W_REV3
B25_BAND = (26.5, 64.5)            # corrie_f.BRIDLE_BAND_REV3
B25_T = 1.2                        # corrie_f.B25_T (ASSUMPTION there)
BAR_OD, SPINE_OD = 18.0, 20.0      # frame.yaml top_bar_section / spine_section od
REAL_CROWN = True                  # BL-046: clamp loads on the crown as built (h1_spine_channel.real_crown)
WEB_T_MM = 2.5                     # BL-046: the fitting's two webs (h1_spine_channel.CLAMP_WEB_T); sized in web_check
G_PER_KG = 9.81

ASSUMPTIONS = {
    "CLAMP-TYPE": ("The spine clamp is built as the frame's own bonded joint (a socket on each tube, as the stay hubs "
                   "and crown corners), machined 7075-T6, MMA with the crown corners' 0.8 mm bondline; no clamp "
                   "friction is credited. A split collar that only grips was not sized: it has no rated slip under a "
                   "55 N m joint moment.", "T6 joint coupon of the fitting (as the crown-corner coupons), before bonding."),
    "CLAMP-WALL": ("0.8 mm 7075 wall on the socket and the saddle (thinner = lower Volkersen peak on the bar); the two "
                   "webs joining saddle and socket are 1.5 mm and are not stress-checked here.",
                   "Socket bending SF in the record; the T6 coupon of the fitting loads the webs."),
    "SOCKET-MIN": ("Socket depth >= 0.75 x spine OD (15 mm) for alignment while the MMA cures; the bond rule alone "
                   "asks 12 mm.", "-"),
    "SPINE-AXIS": ("The spine axis runs through the centre of the printed spine channel (H1 STL, z 510-530), parallel to "
                   "the legs; the frame model's spine (in the bar plane) is a beam idealisation.",
                   "Crown dry fit on the printed H1 body (op 7.17 B25-FIT is at the same fit)."),
    "TRANSVERSE-SHEAR": ("As huntkit.fea.joints: transverse shear goes into bearing at the socket lip, not bond shear. "
                         "A sensitivity with it added to the bond shear is reported.", "T6 coupon."),
}


# ================================================================================== 1. joint loads (frame model)
def joint_loads(kits=KITS, log=None, real: bool = REAL_CROWN) -> list[dict]:
    """Every rev C set on every kit end: the spine's end forces at its top (N, Vy, Vz, T, My, Mz in the member's local
    axes) and the bar's force jump across TB1 (TB1-TB2 start minus TB0-TB1 end), at LIMIT load, with the case factor
    and g. Cached in outputs/crown_spine_clamp/joint_loads[_real].json (keyed on frame.yaml).

    BL-046 ``real`` (default): the crown as built (``h1_spine_channel.real_crown``: top bar 25 mm aft of the legs'
    plane, the spine in the legs' plane hanging from the clamp member TB1 -> SPC). The spine's end forces are then
    taken at SPC (socket) and the clamp member's at both ends ('clamp_spc', 'clamp_tb1': the webs). ``real=False`` is
    BL-045's model (spine rigid on TB1, in the bar's plane)."""
    from huntkit.fea.load_standard import ls1_envelope
    from . import crown_diet as CD
    from .h1_spine_channel import real_crown
    key = FRAME_YAML.read_text()
    cp = OUT / ("joint_loads_real.json" if real else "joint_loads.json")
    if cp.exists():
        d = json.loads(cp.read_text())
        if d.get("frame_yaml") == key and d.get("kits") == list(kits):
            return d["rows"]
    env = ls1_envelope("C")
    sp = CD.specs()
    rows = []
    for kit in kits:
        spec = sp[kit]
        for t in spec.torsos:
            fm, fmp = CD.build(spec, t), None
            if real:
                fm = real_crown(fm)
            for vname, cases in env.items():
                for c in cases:
                    c = copy.copy(c)
                    c.params = dict(c.params)
                    c.buckling = False
                    m = fm
                    if c.name == "tall_load_posts":
                        fmp = fmp or CD.build(spec, t, posts=True)
                        if real and "real_crown" not in fmp:
                            fmp = real_crown(fmp)
                        m = fmp
                    res = c.run(m)
                    ef = {q["id"]: np.asarray(q["end_forces"], float) for q in res.members
                          if q["id"] in ("TB0-TB1", "TB1-TB2", "TB1-SPC") or q["id"].startswith(("TB1-SP", "SPC-SP"))}
                    sid = next(k for k in ef if k.startswith("SPC-SP" if real else "TB1-SP"))
                    row = {"kit": kit, "torso": float(t), "variant": vname, "case": c.name,
                           "req": float(c.required_sf), "g": float(c.g_factor),
                           "spine": ef[sid][0].tolist(),
                           "jump": (ef["TB1-TB2"][0] - ef["TB0-TB1"][1]).tolist()}
                    if real:
                        row["clamp_spc"] = ef["TB1-SPC"][1].tolist()
                        row["clamp_tb1"] = ef["TB1-SPC"][0].tolist()
                    rows.append(row)
            if log:
                log(f"  {kit} {t:g} in")
    OUT.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps({"frame_yaml": key, "kits": list(kits), "rows": rows}))
    return rows


# ================================================================================== 2. sizing
def _sections():
    from huntkit.fea.sections import from_spec
    fy = yaml.safe_load(FRAME_YAML.read_text())["frame"]
    return from_spec(fy["top_bar_section"]), from_spec(fy["spine_section"])


def _params(L: float) -> dict:
    return {"adhesive": ADHESIVE, "adhesive_t_mm": BONDLINE_MM, "sleeve_material": FITTING_MAT,
            "sleeve_t_mm": FITTING_WALL_MM, "cfrp_adherend": True, "overlap_mm": float(L)}


def bond_margins(rows: list[dict], which: str, L: float, with_shear: bool = False) -> dict:
    """Worst margins of one bond (``which`` = 'spine' socket or 'jump' = bar saddle) of length L over every set:
    average (factored >= 1), peak (at limit >= 1), fatigue (avg and peak at 1.6 g bag carry <= 0.3 lap shear; the
    meat case is information). ``with_shear``: the transverse shear added to the bond shear as V / (pi r L)."""
    from huntkit.fea.joints import bond_check, tube_wall_stiffness
    bar, spine = _sections()
    sec = spine if which == "spine" else bar
    Et, Gt = tube_wall_stiffness(sec)
    r = sec.dims["od"] / 2.0
    out = {"avg": (np.inf, ""), "peak": (np.inf, ""), "fat_avg": (np.inf, ""), "fat_peak": (np.inf, "")}
    for rw in rows:
        N, Vy, Vz, T, My, Mz = rw[which]
        br = bond_check(N, T, (My, Mz), r, Et, Gt, _params(L))
        sfa, sfp = br.sf_avg, br.sf_peak                    # at LIMIT load
        if with_shear:
            nmax = abs(N) / (2 * math.pi * r) + math.hypot(My, Mz) / (math.pi * r * r)
            qt = abs(T) / (2 * math.pi * r * r) + math.hypot(Vy, Vz) / (math.pi * r)
            sfa = br.allow / math.hypot(nmax / L, qt / L)
            sfp = br.allow / math.hypot(br.k_axial * nmax / L, br.k_torsion * qt / L)
        tag = f"{rw['kit']} {rw['torso']:g} in {rw['case']} ({rw['variant']})"
        if sfa / rw["req"] < out["avg"][0]:
            out["avg"] = (sfa / rw["req"], tag)
        if sfp < out["peak"][0]:
            out["peak"] = (sfp, tag)
        if rw["case"] == "static_carry":                     # 1 g -> 1.6 g walking peak
            k = BOND_FAT_RATIO * rw["g"] / G_WALK
            if sfa * k < out["fat_avg"][0]:
                out["fat_avg"] = (sfa * k, tag)
            if sfp * k < out["fat_peak"][0]:
                out["fat_peak"] = (sfp * k, tag)
    return {k: {"sf": round(float(v[0]), 3), "set": v[1]} for k, v in out.items()}


def _passes(m: dict) -> bool:
    return m["avg"]["sf"] >= 1.0 and m["peak"]["sf"] >= PEAK_REQ_AT_LIMIT and m["fat_avg"]["sf"] >= 1.0


def min_length(rows: list[dict], which: str, lo: float = 5.0, hi: float = 80.0) -> float:
    """Shortest bond (1 mm steps) that passes average, peak and fatigue (average) for ``which``."""
    L = lo
    while L <= hi:
        if _passes(bond_margins(rows, which, L)):
            return L
        L += 1.0
    return math.nan


def socket_bending(rows: list[dict], wall: float = FITTING_WALL_MM) -> dict:
    """7075 socket on the spine: the spine's TB1 moment on the socket's own ring section at the lip (S-basis yield on
    the factored load; 1.6 g bag carry on the record's fatigue limit with Kt 2, HA-LS-1 metal rule)."""
    from huntkit.materials import load
    al = load(FITTING_MAT)
    sy = float(al.require("yield_strength_sbasis_mpa"))
    se = float(al.require("fatigue_limit_mpa"))
    ri = SPINE_OD / 2 + BONDLINE_MM
    ro = ri + wall
    Z = math.pi / 4 * (ro ** 4 - ri ** 4) / ro
    A = math.pi * (ro ** 2 - ri ** 2)
    smax = max((math.hypot(r["spine"][4], r["spine"][5]) / Z + abs(r["spine"][0]) / A) * r["req"] for r in rows)
    swalk = max((math.hypot(r["spine"][4], r["spine"][5]) / Z + abs(r["spine"][0]) / A) * G_WALK / r["g"]
                for r in rows if r["case"] == "static_carry")
    return {"sigma_factored_mpa": round(smax, 1), "sf_yield": round(sy / smax, 2),
            "sigma_walk_mpa": round(swalk, 1), "sf_fatigue_kt2": round(se / (2.0 * swalk), 2)}


def web_check(rows: list[dict], t: float | None = None) -> dict:
    """BL-046: the fitting's two webs between the bar saddle and the spine socket (never checked in BL-045), on the
    clamp member's end forces at both ends (``joint_loads(real=True)``: local x along the member, fore from the bar to
    the spine). Section: two 7075 plates t x CLAMP_WEB_H at the socket's sides. Normal stress = N / A + |M_strong| / Z_s
    + |M_weak| / Z_w, shear = |V| / A + |T| / (h t^2 / 3 per web); von Mises. Yield SF on the factored load (S-basis);
    fatigue at 1.6 g bag carry with Kt 2 on the record's fatigue limit (HA-LS-1 metal rule, as socket_bending)."""
    from huntkit.materials import load
    from .h1_spine_channel import CLAMP_WEB_GAP, CLAMP_WEB_H
    t = WEB_T_MM if t is None else t
    al = load(FITTING_MAT)
    sy = float(al.require("yield_strength_sbasis_mpa"))
    se = float(al.require("fatigue_limit_mpa"))
    h, d = CLAMP_WEB_H, CLAMP_WEB_GAP - t
    A = 2 * t * h
    Zs = 2 * t * h ** 2 / 6.0                                  # bending about the member's local z (in the y-z plane)
    Zw = 2 * (h * t ** 3 / 12.0 + h * t * (d / 2) ** 2) / (CLAMP_WEB_GAP / 2)
    Jt = 2 * h * t ** 2 / 3.0                                  # open plates: tau = T / (h t^2 / 3) per pair

    def vm(f):
        N, Vy, Vz, T, My, Mz = f
        sig = abs(N) / A + abs(Mz) / Zs + abs(My) / Zw
        tau = math.hypot(Vy, Vz) / A + abs(T) / Jt
        return math.sqrt(sig ** 2 + 3 * tau ** 2)
    smax, wmax, gov = 0.0, 0.0, ""
    for r in rows:
        if "clamp_spc" not in r:
            continue
        s_ = max(vm(r["clamp_spc"]), vm(r["clamp_tb1"]))
        if s_ * r["req"] > smax:
            smax, gov = s_ * r["req"], f"{r['kit']} {r['torso']:g} in {r['case']} ({r['variant']})"
        if r["case"] == "static_carry":
            wmax = max(wmax, s_ * G_WALK / r["g"])
    return {"web_t_mm": t, "web_h_mm": h, "sigma_vm_factored_mpa": round(smax, 1), "sf_yield": round(sy / smax, 2),
            "set": gov, "sigma_vm_walk_mpa": round(wmax, 1), "sf_fatigue_kt2": round(se / (2.0 * wmax), 2)}


def size_clamp(rows: list[dict] | None = None) -> dict:
    """The clamp's real dimensions (published as SPINE_CLAMP)."""
    rows = rows or joint_loads()
    Ls_bond = min_length(rows, "spine")
    Ls = max(Ls_bond, SOCKET_MIN_MM)
    Lb_bond = min_length(rows, "jump")
    socket_od = SPINE_OD + 2 * (BONDLINE_MM + FITTING_WALL_MM)
    Lb = max(Lb_bond, math.ceil(socket_od + SADDLE_MIN_OVER_SOCKET_MM))
    geo = spine_axis()
    dy = geo["spine_axis_minus_bar_axis_y_mm"]
    # the spine's aft face clears the bar circle below s_free (s from the bar centre down the spine): the socket is
    # bonded on the full circumference only below s_free, so it runs from s_free to s_free + Ls
    rb, rs = BAR_OD / 2, SPINE_OD / 2
    gap = abs(dy) - rs                                       # bar centre to the spine's aft face, fore-aft
    s_free = math.sqrt(max(rb ** 2 - gap ** 2, 0.0)) if gap < rb else 0.0
    collar = s_free + Ls - rb                                # below the bar's underside
    al = __import__("huntkit.materials", fromlist=["load"]).load(FITTING_MAT)
    rho = float(al.require("density_kg_m3")) * 1e-6
    ri_b, ri_s = BAR_OD / 2 + BONDLINE_MM, SPINE_OD / 2 + BONDLINE_MM
    t = FITTING_WALL_MM
    v_saddle = math.pi * ((ri_b + t) ** 2 - ri_b ** 2) * Lb
    v_socket = math.pi * ((ri_s + t) ** 2 - ri_s ** 2) * (s_free + Ls)
    web_t = WEB_T_MM if REAL_CROWN else 1.5
    v_web = 2 * web_t * (abs(dy)) * min(Lb, socket_od)       # ASSUMPTION CLAMP-TYPE: two webs bridge the bores (full dy)
    from huntkit.materials import load
    adh = float(load(ADHESIVE).require("density_kg_m3")) * 1e-6
    v_bond = math.pi * ((ri_b) ** 2 - (BAR_OD / 2) ** 2) * Lb + math.pi * (ri_s ** 2 - (SPINE_OD / 2) ** 2) * Ls
    mass = (v_saddle + v_socket + v_web) * rho + v_bond * adh
    return {"socket_len_mm": Ls, "socket_len_bond_min_mm": Ls_bond, "saddle_len_mm": float(Lb), "saddle_len_bond_min_mm": Lb_bond,
            "half_x_mm": Lb / 2.0, "socket_od_mm": socket_od, "saddle_od_mm": BAR_OD + 2 * (BONDLINE_MM + t),
            "s_full_circumference_mm": round(s_free, 2), "collar_below_bar_underside_mm": round(collar, 1),
            "spine_axis_offset_fore_mm": round(-dy, 2),
            "fore_face_from_bar_axis_mm": round(-dy + socket_od / 2, 1),
            "aft_face_from_bar_axis_mm": round(BAR_OD / 2 + BONDLINE_MM + t, 1),
            "wall_mm": t, "material": FITTING_MAT, "adhesive": ADHESIVE, "bondline_mm": BONDLINE_MM,
            "mass_g": round(mass, 1), "mass_booked_g": 6.0,
            "margins": {"socket": bond_margins(rows, "spine", Ls), "saddle": bond_margins(rows, "jump", Lb),
                        "socket_with_shear": bond_margins(rows, "spine", Ls, True),
                        "saddle_with_shear": bond_margins(rows, "jump", Lb, True),
                        "socket_bending": socket_bending(rows),
                        **({"webs": web_check(rows)} if any("clamp_spc" in r for r in rows) else {})},
            "loads_max_factored": _load_summary(rows),
            "source": "crown_spine_clamp.size_clamp: frame model TB1 forces (crown_diet kits, rev C), "
                      "huntkit.fea.joints.bond_check, H1 STL spine channel; ASSUMPTIONS CLAMP-TYPE, CLAMP-WALL, "
                      "SPINE-AXIS, TRANSVERSE-SHEAR"}


def _load_summary(rows):
    S = np.array([np.asarray(r["spine"]) * r["req"] for r in rows])
    J = np.array([np.asarray(r["jump"]) * r["req"] for r in rows])
    M = np.hypot(S[:, 4], S[:, 5])
    i = int(np.argmax(M))
    return {"spine_N_max_n": round(float(np.abs(S[:, 0]).max()), 0),
            "spine_V_max_n": round(float(np.hypot(S[:, 1], S[:, 2]).max()), 0),
            "spine_M_max_nm": round(float(M.max()) / 1000, 1),
            "spine_M_set": f"{rows[i]['kit']} {rows[i]['torso']:g} in {rows[i]['case']} ({rows[i]['variant']})",
            "bar_T_jump_max_nm": round(float(np.abs(J[:, 3]).max()) / 1000, 1),
            "bar_M_jump_max_nm": round(float(np.hypot(J[:, 4], J[:, 5]).max()) / 1000, 1)}


# ================================================================================== 3. real geometry (H1 STL)
_GEO: dict = {}


def _section_loops(mesh, z):
    s = mesh.section(plane_origin=[0, 0, float(z)], plane_normal=[0, 0, 1])
    return [] if s is None else list(s.discrete)


def h1_crown_interfaces(stl: Path = H1_STL) -> dict:
    """Measured on the H1 print STL: the pawl housing (top z, max |x|, y extent), the spine channel through it (x, y
    extent, depth), and the printed body's top inside the B-25 band (|x| 26.5-64.5) and over the run (|x| 11-26.5)."""
    if "h1" in _GEO:
        return _GEO["h1"]
    import trimesh
    m = trimesh.load(stl)
    v = m.vertices
    ch, top_h, xmax, y_lo, y_hi = [], None, 0.0, 0.0, -99.0
    for z in np.arange(510.0, 530.01, 0.5):          # the channel: an inner loop 15-45 mm each way in the housing
        for e in _section_loops(m, z):                # (BL-045 plate channel 40.2 x 18.3; BL-046 tube channel 22 x 36.3)
            w, d = e[:, 0].max() - e[:, 0].min(), e[:, 1].max() - e[:, 1].min()
            if 15.0 < w < 45.0 and 15.0 < d < 45.0 and np.abs(e[:, 0]).max() < 25.0:
                ch.append((z, e[:, 0].min(), e[:, 0].max(), e[:, 1].min(), e[:, 1].max()))
    for z in np.arange(520.5, 545.0, 0.25):          # the housing: above the upper bar (top z ~519 in the band)
        for e in _section_loops(m, z):
            if np.abs(e[:, 0]).max() < 45.0 and e[:, 0].max() - e[:, 0].min() > 40.0:
                xmax = max(xmax, float(np.abs(e[:, 0]).max()))
                y_lo, y_hi = min(y_lo, float(e[:, 1].min())), max(y_hi, float(e[:, 1].max()))
    ch = np.array(ch)
    band = (np.abs(v[:, 0]) >= B25_BAND[0]) & (np.abs(v[:, 0]) <= B25_BAND[1]) & (v[:, 2] > 440)
    run = (np.abs(v[:, 0]) >= SPINE_OD / 2 + B25_T) & (np.abs(v[:, 0]) < B25_BAND[0]) & (v[:, 2] > 440)
    out = {"pawl_housing_top_z": round(float(v[(np.abs(v[:, 0]) < 26) & (v[:, 2] > 500), 2].max()), 2),
           "pawl_housing_half_w_mm": round(xmax, 2), "pawl_housing_y_mm": [round(y_lo, 1), round(y_hi, 1)],
           "spine_channel_x_mm": [round(float(ch[:, 1].min()), 2), round(float(ch[:, 2].max()), 2)],
           "spine_channel_y_mm": [round(float(ch[:, 3].min()), 2), round(float(ch[:, 4].max()), 2)],
           "spine_channel_z_mm": [round(float(ch[:, 0].min()), 2), round(float(ch[:, 0].max()), 2)],
           "body_top_z_in_b25_band": round(float(v[band, 2].max()), 2),
           "body_top_z_under_run": round(float(v[run, 2].max()), 2),
           "pawl_z": 520.0, "source": f"{stl.relative_to(REPO)} sections (z 500-545, 0.25 mm) and vertices"}
    out["spine_channel_depth_y_mm"] = round(out["spine_channel_y_mm"][1] - out["spine_channel_y_mm"][0], 2)
    out["spine_channel_width_x_mm"] = round(out["spine_channel_x_mm"][1] - out["spine_channel_x_mm"][0], 2)
    out["spine_channel_centre"] = [round(0.5 * sum(out["spine_channel_x_mm"]), 2),
                                   round(0.5 * sum(out["spine_channel_y_mm"]), 2)]
    out["pawl_housing_up_mm"] = round(out["pawl_housing_top_z"] - out["pawl_z"], 2)
    # BL-046: a channel deeper than tube + rack has a round aft end on the tube axis (h1_spine_channel.channel_section):
    # the axis is the aft face minus the aft radius, slope-corrected to the pawl line; a shallower one (the old plate
    # channel) has the spine at its centre
    from . import h1_spine_channel as HSC
    if out["spine_channel_depth_y_mm"] >= SPINE_OD + HSC.RACK_T:
        sl = HSC.axis_slope()
        aft = float(np.mean([r[4] - sl * (r[0] - out["pawl_z"]) for r in ch]))
        out["spine_axis_y_at_pawl"] = round(aft - HSC.channel_dims()["aft_r"], 2)
        out["spine_axis_rule"] = "aft face - (tube r + running clearance) (BL-046 tube channel)"
    else:
        out["spine_axis_y_at_pawl"] = out["spine_channel_centre"][1]
        out["spine_axis_rule"] = "channel centre (plate channel)"
    _GEO["h1"] = out
    return out


def top_bar_aft_mm() -> float:
    """geometry.yaml frame.members_topology.crown.top_bar_aft_offset_mm: the crown top bar's axis aft of the legs'
    plane (v3.1 head clearance, offset corner wraps)."""
    g = yaml.safe_load((PACK / "geometry.yaml").read_text())
    return float(g["frame"]["members_topology"]["crown"].get("top_bar_aft_offset_mm", 0.0))


def spine_axis() -> dict:
    """Spine axis (printed channel, ``h1_crown_interfaces``) against the legs' plane (the frame model's spine line at
    the pawl line) and against the crown top bar's real axis (BL-046: the legs' plane + top_bar_aft_mm aft; BL-045
    took the bar in the legs' plane, as the beam model draws it). Both run parallel to the legs."""
    from huntkit.fea.frames import build_frame_from_yaml
    h = h1_crown_interfaces()
    fm = build_frame_from_yaml(FRAME_YAML, torso_in=15.0)
    n = fm["nodes"]
    pts = np.array([n[k] for k in n if k.startswith("SP") or k == "TB1"], float)
    y_model = float(np.interp(520.0, *zip(*sorted(zip(pts[:, 2], pts[:, 1])))))   # the model spine at the pawl line
    rack = rack_dims()
    ys = h["spine_axis_y_at_pawl"]
    aft = top_bar_aft_mm() if REAL_CROWN else 0.0
    return {"spine_axis_y_at_pawl_mm": ys, "model_spine_y_at_pawl_mm": round(y_model, 2),
            "spine_axis_minus_legs_plane_y_mm": round(ys - y_model, 2), "top_bar_aft_of_legs_plane_mm": aft,
            "spine_axis_minus_bar_axis_y_mm": round(ys - y_model - aft, 2),
            "channel_depth_y_mm": h["spine_channel_depth_y_mm"], "channel_width_x_mm": h["spine_channel_width_x_mm"],
            "spine_od_mm": SPINE_OD, "rack_mm": rack,
            "tube_fits_channel": bool(h["spine_channel_depth_y_mm"] >= SPINE_OD and
                                      h["spine_channel_width_x_mm"] >= SPINE_OD),
            "tube_plus_rack_fits": bool(min(h["spine_channel_depth_y_mm"], h["spine_channel_width_x_mm"]) >= SPINE_OD
                                        and max(h["spine_channel_depth_y_mm"], h["spine_channel_width_x_mm"])
                                        >= SPINE_OD + rack["thickness_mm"])}


def rack_dims() -> dict:
    """The printed crown rack (designs/pack_5200/print/crown_rack_fdm_pacf.stl) extents."""
    import trimesh
    e = sorted(trimesh.load(PACK / "print" / "crown_rack_fdm_pacf.stl").extents)
    return {"thickness_mm": round(float(e[0]), 2), "width_mm": round(float(e[1]), 2), "length_mm": round(float(e[2]), 2)}


# ================================================================================== 4. B-25 on the real clamp
def b25_clearances(clamp: dict | None = None, geo: dict | None = None) -> dict:
    """corrie_f.b25_topology's clearance checks with the real clamp and pawl housing, per crown kit at its SHORTEST
    torso (the spine above the pawl is shortest there). s = along the spine from the bar centre, x = along the bar."""
    from . import crown_diet as CDI
    clamp = clamp or size_clamp()
    geo = geo or h1_crown_interfaces()
    rb = BAR_OD / 2
    x0, x1 = B25_BAND
    s_top = rb + clamp["collar_below_bar_underside_mm"] + B25_RUN_GAP
    mitre = (s_top, s_top + B25_W)
    wrap = (s_top, s_top + B25_NECK_W)
    uz = CDI.geom()["uz"]
    kits = {}
    for k, (lo, hi) in CDI.SIZES.items():
        zb = CDI.crown_top_z(lo)
        s_h = (zb - geo["pawl_housing_top_z"]) / uz
        s_band = (zb - geo["body_top_z_in_b25_band"]) / uz
        s_run = (zb - geo["body_top_z_under_run"]) / uz
        mitre_side = x0 - geo["pawl_housing_half_w_mm"]
        kits[k] = {"torso_in": lo, "bar_z": zb, "housing_top_s_mm": round(s_h, 1),
                   "wrap_bottom_s_mm": round(wrap[1], 1), "wrap_to_housing_mm": round(s_h - wrap[1], 1),
                   "run_to_body_mm": round(s_run - wrap[1], 1),
                   "mitre_bottom_s_mm": round(mitre[1], 1), "mitre_to_body_in_band_mm": round(s_band - mitre[1], 1),
                   "mitre_to_housing_side_x_mm": round(mitre_side, 2),
                   # in the x-s plane, y ignored (the mitre lies on the bar's aft face, the housing top is 13+ mm fore)
                   "mitre_to_housing_xs_mm": round(mitre_side if mitre[1] > s_h else math.hypot(mitre_side, s_h - mitre[1]), 1)}
        kits[k]["ok"] = bool(kits[k]["wrap_to_housing_mm"] >= 0 and kits[k]["run_to_body_mm"] >= 0 and
                             kits[k]["mitre_to_body_in_band_mm"] >= 0 and mitre_side > 0)
    gov = min(kits, key=lambda q: kits[q]["wrap_to_housing_mm"])
    band_clear = x0 - clamp["half_x_mm"]
    # the run reaches the spine 15.9 mm fore of the bar plane: its path from the mitre centre to the spine wrap
    dy = clamp["spine_axis_offset_fore_mm"]
    y_run = rb + B25_T                                       # the drop / mitre lie on the bar's aft face
    xc = 0.5 * (x0 + x1)
    rw = SPINE_OD / 2 + B25_T / 2
    d = math.hypot(xc, y_run + dy)                           # mitre centre to the spine axis, in plan
    tangent = math.sqrt(max(d * d - rw * rw, 0.0))
    run_bl043 = xc - (SPINE_OD / 2 + B25_T)
    d_cut = 2 * (tangent - run_bl043)                        # the one full spine wrap is unchanged
    return {"clamp_half_x_mm": clamp["half_x_mm"], "band_to_clamp_x_mm": round(band_clear, 1),
            "band_to_clamp_ok": bool(band_clear >= MIN_CLEAR_MM),
            "run_top_s_mm": round(s_top, 1), "mitre_s_mm": [round(v, 1) for v in mitre],
            "wrap_s_mm": [round(v, 1) for v in wrap], "kits": kits, "governing_kit": gov,
            "all_ok": bool(all(v["ok"] for v in kits.values()) and band_clear >= MIN_CLEAR_MM),
            "run_plan_mm": {"spine_axis_fore_of_bar_mm": dy, "run_bl043_mm": round(run_bl043, 1),
                            "run_real_mm": round(tangent, 1), "cut_change_mm": round(d_cut, 1),
                            "note": "run = plan length from the mitre centre (aft face of the bar) to its tangent on the "
                                    "spine wrap; the spine wrap (one full turn) is unchanged"},
            "source": "crown_spine_clamp.b25_clearances (corrie_f.b25_topology checks; real clamp + H1 STL)"}


# ================================================================================== published constants
def published() -> dict:
    """What the pack-designer imports (BL-045): SPINE_CLAMP, PAWL_HOUSING, the B-25 clearances."""
    c = size_clamp()
    g = h1_crown_interfaces()
    return {"SPINE_CLAMP": {k: c[k] for k in ("half_x_mm", "collar_below_bar_underside_mm", "saddle_len_mm",
                                               "socket_len_mm", "socket_od_mm", "saddle_od_mm",
                                               "spine_axis_offset_fore_mm", "fore_face_from_bar_axis_mm",
                                               "aft_face_from_bar_axis_mm", "mass_g", "material")},
            "PAWL_HOUSING": {"up_from_pawl_line_mm": g["pawl_housing_up_mm"], "half_w_mm": g["pawl_housing_half_w_mm"],
                             "y_mm": g["pawl_housing_y_mm"], "body_top_z_in_b25_band": g["body_top_z_in_b25_band"]},
            "B25": b25_clearances(c, g)}


# Constants for corrie_f (BL-045 values; tests/test_bl045_crown_fairleads.py asserts each against the functions above).
SPINE_CLAMP_HALF_X = 12.0          # size_clamp half_x_mm: saddle 24 mm along the bar (>= the 23.2 mm socket OD; the
#                                    bar bond alone needs 19 mm). Replaces corrie_f.SPINE_CLAMP_HALF 15 (ASSUMPTION)
SPINE_CLAMP_COLLAR = 12.8          # size_clamp collar_below_bar_underside_mm: socket bonded from s 6.84 (spine clear of
#                                    the bar) for 15 mm. Replaces corrie_f.SPINE_CLAMP_COLLAR 12 (ASSUMPTION B25-CLAMP)
SPINE_AXIS_FORE_MM = 15.85         # spine_axis: spine axis fore (wearer side) of the bar axis
SPINE_CLAMP_MASS_G = 10.4          # size_clamp mass_g (frame.yaml books 6.0)
PAWL_HOUSING_UP = 15.62            # h1_crown_interfaces: housing top z 535.62 above the pawl line z 520 (was 20 ASSUMED)
PAWL_HOUSING_HALF_W = 24.82        # h1_crown_interfaces: housing max |x| above the upper bar (was 18 ASSUMED)
BODY_TOP_Z_IN_B25_BAND = 519.18    # h1_crown_interfaces: printed body top under the sleeve band (corrie_f modelled the
#                                    upper bar as OD 22 centred on z 520, top 531)
B25_RUN_EXTRA_PER_SIDE_MM = 17.0   # b25_clearances run_plan: the run reaches the spine 15.85 mm fore of the bar plane
B25_CUT_CHANGE_MM = 34.1           # b25_clearances run_plan cut_change_mm (both sides)


def main(argv=None):
    print(json.dumps(published(), indent=1, default=float))


if __name__ == "__main__":
    main()
