"""BL-085: preload-tolerant upper and mid tees for the B81 aluminium tube-ladder frame (review 9, B1-B4, M1, M2, M5,
M8; frame "B85").

What changes against B81 (``bl081_concept_b`` / ``bl081_local``, not edited)
-----------------------------------------------------------------------------
* **Upper tee (bar at z 520): long two-pair clamp, fully on tube, below a real free end.** The stays are 15 mm longer
  (545 mm), so the stay top is at z 545 and the stay-top collar sits at z 530-548. The two 6061 half-shells
  (1-1/4 x .120 tube, Speedy p-4573, ID 1.010 in, sawn) are 100 mm long, z 430-530: 15 mm of continuous tube above them, then the free end
  (``tee_units`` models that free end; BL-081 modelled a continuous tube and the as-drawn shell overhung the end, B1).
  Two backer pairs (1 x 3/16 flat, front and back) at z 430-455 and 505-530, each with 2 x M5 A2 beside the stay:
  4 bolts per tee. The bar end is **through-bolted in double shear** between the upper backer pair: 2 x M5 A2 along y
  at 16 mm pitch through the backers, 3.2 mm 6061 spacer washers and the bar (crush sleeve inside the bar); a printed
  saddle plug in the bar end (coped to the shell OD) takes bar compression only. Every load path from the bar to the
  stay is metal (M8): bar -> 2 bolts in bearing / double shear -> backers -> clamp bolts -> shells -> stay.
  The IM3 webbing loop goes round the shells between the backer pairs (z 466-494).
* **Mid tee (bar at z 330): pinned saddle, no metal clamp on the stay.** The global model shows the worst stay beam
  stress of the frame at z 330 (meat / tall-load cases); any metal clamp edge there is a fretting site at full beam
  stress, which no clamp passes on the design S-N curve. B85 joins the mid bar to the stay with a printed PAHT-CF split
  saddle sleeve (bar socket + outer half, 40 mm long, 1.5 mm wall under a 9 mm hose band at positioning torque): it
  carries the bar's axial force in bearing, no moment, nothing along the stay (``bl085_global.SADDLE_K``). Releasing the
  joint changes the frame's member margins by < 2 % (global rows).

Fatigue basis (review 9 B4): the Yahr (ORNL 1993) **design** curve, Sa = min(fit / 2 on stress, fit at 20 N), which at
1e5 is 71.2 MPa (mean fit 142.3); Goodman on Su 290; Kt 2 on the stay beam stress at a metal clamp edge (HA-LS-1 rule);
fretting allowance on the allowable at a contact edge: metal on metal 0.6 (ASSUMPTION FRET-METAL, the middle of the
0.5-0.7 aluminium range quoted in review 9), polymer on metal 0.85 (ASSUMPTION FRET-POLY); finish: stays and every
clamp zone bare (no anodise, knock-down 1.0; with Type II anodise the record also reports the 0.7 case).

Preload (B3): M5 A2 set with a torque screwdriver; every clamp row is checked at the nominal and at both scatter limits
+/-30 % (ASSUMPTION SCATTER: torque-controlled +/-25 % plus K uncertainty). Slip and leg clearance at -30 %, wall
stress and bolt tension at +30 %.

Units mm, N, MPa, g, USD.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ

# ----------------------------------------------------------------------------- design (B85)
CFG85 = {
    "stay_len": 545.0, "stay_ext": 15.0,
    "shell_len": 100.0, "shell_top_z": 530.0, "free_above": 15.0,      # tube above the shell top to the stay top
    "bolt_pairs": 2, "Fb_nom": 1500.0, "scatter": 0.30, "retention": 0.9, "mu": 0.15,
    "torque_nm": 1.5, "K_nut": 0.2,
    "backer_len_upper": 80.0, "backer_len_lower": 55.0, "backer_t": 0.1875 * BQ.IN, "backer_w": BQ.IN,
    "bar_bolt_pitch": 16.0, "bar_bolt_edge": 10.0, "spacer_t": 3.2,
    "im3_width": 28.0,                  # IM3 loop on the shells between the backer pairs, centred on the shells (mm)
    "saddle_len": 40.0, "saddle_wall": 1.5, "band_torque_nm": 1.5,
    "finish": "bare",                   # stays and clamp zones bare 6061 (no anodise); "anodised" applies 0.7
    "fret_metal": 0.60, "fret_poly": 0.85, "kt_clamp_edge": 2.0, "kt_saddle": 1.15,
}
STAY = "t1000_065"
SHELL = {"od": 1.25 * BQ.IN, "t": 0.120 * BQ.IN, "id": 1.010 * BQ.IN,
         "src": "Speedy Metals p-4573 1-1/4 OD x 1.010 ID x .120 wall 6061-T6 (read 2026-11-25)"}


# ----------------------------------------------------------------------------- fatigue basis
def sn_basis(N: float = 1e5) -> dict:
    """Yahr 6061-T6 mean fit and design curve at N (record alu_6061_t6.yaml: design = fit / 2 on stress or fit at
    20 N on life, whichever is lower)."""
    d = BQ.sn_6061()
    fit = lambda n: d["C"] / math.sqrt(n) + d["floor"]   # noqa: E731
    mean = fit(N)
    design = min(mean / 2.0, fit(20.0 * N))
    return {"mean": mean, "design": design, "Su": d["Su"], "anodise": d["anodise"]}


def allowable_sa(contact: str | None, cfg: dict, curve: str = "design") -> float:
    """Fully reversed amplitude allowable at 1e5 with the knock-downs: curve (design / mean), fretting by contact type
    ('metal' / 'poly' / None), finish (anodise 0.7 when cfg finish is 'anodised')."""
    b = sn_basis()
    sa = b[curve]
    if contact == "metal":
        sa *= cfg["fret_metal"]
    elif contact == "poly":
        sa *= cfg["fret_poly"]
    if cfg.get("finish") == "anodised":
        sa *= b["anodise"]
    return sa


def goodman_margin(sa: float, sm: float, Sa_allow: float, Su: float = 290.0) -> float:
    return 1.0 / (sa / Sa_allow + max(sm, 0.0) / Su)


# ----------------------------------------------------------------------------- solid FE unit fields
_TEE_FE: dict = {}


@lru_cache(maxsize=None)
def tee_units(clamp_len: float, above: float | None, below: float = 75.0, tube: str = STAY) -> dict:
    """Stay under an upper-tee clamp (tube_solid P2 tets, fixed end ``below`` mm under the shells, so >= 3 R from the
    clamp edge, review 9 m1). ``above`` = tube beyond the shell top to the FREE END (None: 60 mm of tube, i.e.
    continuous). Unit fields (1 kN each): jaw0 / jaw1 = one half-shell pressed on (uniform over +/- 86.5 deg, 1.5 mm
    kerf), loop = IM3 webbing 1 kN aft over the aft half on the IM3 band, edge_j / edge_k = the bar-moment couple
    (1 kN cos over 180 deg on a quarter length at each end, opposite sides) centred on the jaws (j, as BL-081) and on
    the kerfs (k). Returns per-field hoop peaks; the fields stay in _TEE_FE for superposition."""
    from huntkit.fea.tube_solid import TubeFE, TubeModel
    st = BQ.STOCK[tube]
    ab = 60.0 if above is None else above
    L = below + clamp_len + ab
    x0, x1 = below, below + clamp_len
    m = TubeModel(L=L, od=st["od"], t=st["t"], h=2.2, refine_x=((x0 - 6, min(x1 + 6, L), 1.7),))
    fe = TubeFE(m)
    jaw = math.radians(86.5)
    u = {}
    u["jaw0"] = fe.solve(fe.patch_pressure(x0, x1, 0.0, jaw, 1000.0, "outer", uniform=True))
    u["jaw1"] = fe.solve(fe.patch_pressure(x0, x1, math.pi, jaw, 1000.0, "outer", uniform=True))
    # SHELL-FIT bound: a 1.010 in shell bore that has not fully conformed bears at its crown first (cos distribution)
    u["jawc0"] = fe.solve(fe.patch_pressure(x0, x1, 0.0, jaw, 1000.0, "outer", uniform=False))
    u["jawc1"] = fe.solve(fe.patch_pressure(x0, x1, math.pi, jaw, 1000.0, "outer", uniform=False))
    w_ = CFG85["im3_width"]
    if clamp_len >= 2 * 25.4 + w_:
        la, lb = x0 + clamp_len / 2 - w_ / 2, x0 + clamp_len / 2 + w_ / 2
    else:                                   # short (B81) clamp: the loop under the shells
        la, lb = x0 - 27.0, x0 - 2.0
    u["loop"] = fe.solve(fe.patch_pressure(la, lb, math.pi, math.pi / 2, 1000.0, "outer", uniform=True))
    q4 = clamp_len / 4
    for tag, th in (("edge_j", 0.0), ("edge_k", math.pi / 2)):
        f = fe.patch_pressure(x0, x0 + q4, th, math.radians(90), 1000.0, "outer") + \
            fe.patch_pressure(x1 - q4, x1, th + math.pi, math.radians(90), 1000.0, "outer")
        u[tag] = fe.solve(f)
    _TEE_FE[(clamp_len, above, below, tube)] = (fe, u, x0, x1, (la, lb))
    out = {"L": L, "x0": x0, "x1": x1, "dofs": int(fe.K.shape[0])}
    for k, v in u.items():
        out[k] = {"hoop": fe.surface_hoop(v, max(x0 - 30, 0.5), min(x1 + 4, L))}
    return out


def release() -> None:
    """Drop the solid-FE models (each holds a factorised stiffness of a few GB)."""
    import gc
    for v in _TEE_FE.values():
        sol = getattr(v[0], "_solver", None)
        if sol and sol[0] == "pardiso":
            try:
                sol[1].free_memory(everything=True)
            except Exception:   # pragma: no cover
                pass
    _TEE_FE.clear()
    tee_units.cache_clear()
    gc.collect()


def tee_hoop(clamp_len, above, mags: dict, below: float = 75.0, tube: str = STAY) -> float:
    """Peak |hoop| of the superposed field sum(mags[k] (kN) x unit k)."""
    tee_units(clamp_len, above, below, tube)
    fe, u, x0, x1, _ = _TEE_FE[(clamp_len, above, below, tube)]
    tot = sum(mags.get(k, 0.0) * u[k] for k in u)
    return fe.surface_hoop(tot, max(x0 - 30, 0.5), min(x1 + 4, fe.m.L))


def tee_gap_loss(clamp_len, above, mags: dict, below: float = 75.0, tube: str = STAY) -> float:
    """Bore gap loss (n 0 + n 2 harmonics, mm) under the shells, worst of 5 stations (leg-clearance check)."""
    tee_units(clamp_len, above, below, tube)
    fe, u, x0, x1, _ = _TEE_FE[(clamp_len, above, below, tube)]
    tot = sum(mags.get(k, 0.0) * u[k] for k in u)
    return max(fe.ovalisation(tot, x)["min_gap_change_mm"] for x in np.linspace(x0 + 2, x1 - 2, 5))


def shell_close_force(L: float) -> float:
    """ASSUMPTION SHELL-FIT: force per half-shell (N) spent closing the 1.010 in bore (p-4573) onto the 1.000 in stay
    before the contact is uniform: the half ring's curvature change d(kappa) = 1 / Rm_stay - 1 / Rm_shell needs a
    moment E I d(kappa) per mm; reacted at the crown over the lever Rm it is a force E I d(kappa) / Rm per mm, x 2
    (both legs) x L. That part of the force enters as a crown (cos) field, the rest uniformly."""
    sw = SHELL
    st = BQ.STOCK[STAY]
    rm_s, rm_t = (sw["id"] + sw["t"]) / 2, (st["od"] + sw["t"]) / 2
    dk = 1 / rm_t - 1 / rm_s
    I = sw["t"] ** 3 / 12
    return 2 * BQ.E_AL * I * dk / rm_t * L


# ----------------------------------------------------------------------------- loads from the global pass
def tee_loads(g: dict, z: float) -> dict:
    """Envelope of the tee link (factored, every case incl. C6p) and walk records at z, and the stay beam stress at
    the tee (stay member just above / below the tee node, factored and walk)."""
    from huntkit.gendesign.bl085_global import section_stress
    st = BQ.STOCK[STAY]
    out = {"fz": 0.0, "mz": 0.0, "fy": 0.0, "fx": 0.0, "mxy": 0.0, "slip_u_terms": [], "w_fy": 0.0, "w_mxy": 0.0,
           "w_fx": 0.0}
    for tag in "LR":
        for r in g["links"][f"tee_{tag}{z:g}"]:
            v = np.asarray(r["vec"], float)
            out["slip_u_terms"].append((abs(v[2]), abs(v[5]), r["case"]))
            out["fz"] = max(out["fz"], abs(v[2]))
            out["mz"] = max(out["mz"], abs(v[5]))
            out["fy"] = max(out["fy"], abs(v[1]))
            out["fx"] = max(out["fx"], abs(v[0]))
            out["mxy"] = max(out["mxy"], math.hypot(v[3], v[4]))
        for r in g["links"][f"tee_{tag}{z:g}|walk"]:
            v = np.asarray(r["vec"], float)
            out["w_fy"] = max(out["w_fy"], abs(v[1]))
            out["w_fx"] = max(out["w_fx"], abs(v[0]))
            out["w_mxy"] = max(out["w_mxy"], math.hypot(v[3], v[4]))
    fac, walk = (0.0, ""), (0.0, "")
    for tag in "LR":
        nm = f"stay at tee z{z:g} {tag}"
        for r in g["tee_stay"][nm]:
            s = section_stress(r["f"], st["od"], st["t"])["sigma"]
            if s > fac[0]:
                fac = (s, r["case"])
        for r in g["tee_stay_walk"][nm]:
            s = section_stress(r["f"], st["od"], st["t"])["sigma"]
            if s > walk[0]:
                walk = (s, r["case"])
    out["beam_fact"], out["beam_fact_case"] = fac
    out["beam_walk"], out["beam_walk_case"] = walk
    return out


IM3_F = 1415.1          # bag-on IM3 hook case, factored (attach_system_results factored_n, BL-081 fairlead rows)
PAWL_ROWS = ((1334.0 * 1.5 / 2, "pawl 1334 N x 1.5 tall-load compression, half per tee"),
             (1001.0 / 2, "pawl 1001 N C8 hipbelt-off, half per tee"))


# ----------------------------------------------------------------------------- upper tee rows
def upper_tee_rows(g: dict, cfg: dict | None = None) -> list[dict]:
    cfg = {**CFG85, **(cfg or {})}
    L, ab = cfg["shell_len"], cfg["free_above"]
    ld = tee_loads(g, 520.0)
    st = BQ.STOCK[STAY]
    R = st["od"] / 2
    nb = 2 * cfg["bolt_pairs"]
    P_nom = nb * cfg["Fb_nom"]                        # force on each half-shell (sum of the bolt tensions)
    lim = {"lo": 1 - cfg["scatter"], "nom": 1.0, "hi": 1 + cfg["scatter"]}
    rows = []
    # --- slip (friction carries the force along the stay and the torque about it), at -30 % and nominal
    for k in ("lo", "nom"):
        P = P_nom * lim[k]
        Fc = cfg["mu"] * math.pi * P * cfg["retention"]
        Tc = Fc * R
        u, case = max(((fz / Fc + mz / Tc), c) for fz, mz, c in ld["slip_u_terms"])
        for F, lab in PAWL_ROWS:
            if F / Fc > u:
                u, case = F / Fc, lab
        rows.append({"item": "5", "row": f"upper tee slip (axial + torque about the stay), preload {k} "
                     f"({P:.0f} N per half)", "kind": "joint", "value": u, "allow": 1.0, "margin": 1 / u,
                     "basis": f"mu {cfg['mu']} wet Al/Al x pi x P x ret {cfg['retention']} = {Fc:.0f} N / {Tc / 1e3:.1f} N m; "
                              f"worst of every case incl. C6p and the pawl rows: {case}"})
    # --- edge couple and side push from the bar (through the backers), factored and walk
    edge = ld["mxy"] / (0.67 * L) / 1000.0
    side = ld["fy"] / 1000.0
    edge_w, side_w = ld["w_mxy"] / (0.67 * L) / 1000.0, ld["w_fy"] / 1000.0
    im3_w = IM3_F / 3.0 * BQ.G_WALK / 1000.0
    sb_f, sb_w = ld["beam_fact"], ld["beam_walk"]

    DISTS = ("uniform", "fit")
    Fc = shell_close_force(L)

    def hoop(P, loop, e, s, ek, dist):
        """dist 'uniform' = conformed shells (CLAMP-UNIFORM); 'fit' = the first Fc of each half's force goes in at the
        crown (cos field) while the 1.010 in bore closes onto the stay, the rest uniform (SHELL-FIT)."""
        fc = min(P, Fc) if dist == "fit" else 0.0
        mags = {"jaw0": (P - fc) / 1000 + s, "jaw1": (P - fc) / 1000, "jawc0": fc / 1000, "jawc1": fc / 1000,
                "loop": loop, ("edge_k" if ek else "edge_j"): e}
        return tee_hoop(L, ab, mags)
    # --- static wall at +30 %
    worst = None
    for ek in (False, True):
        for dist in DISTS:
            sh = hoop(P_nom * lim["hi"], IM3_F / 1000, edge, side, ek, dist)
            if worst is None or sh > worst[0]:
                worst = (sh, ek, dist)
    sh = worst[0]
    s_lim = math.sqrt(sh ** 2 + sb_f ** 2 + sh * sb_f)
    rows.append({"item": "5", "row": "upper tee: stay wall at limit, preload +30 % (clamp + IM3 + bar couple + side + beam)",
                 "kind": "strength", "value": s_lim, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_lim,
                 "basis": f"solid FE hoop {sh:.0f} MPa ({L:g} mm shells, free end {ab:g} mm above, couple "
                          f"{'on the kerfs' if worst[1] else 'on the jaws'} {edge:.2f} kN, jaw pressure {worst[2]}, side {side:.2f} kN, IM3 1415 N) with "
                          f"the stay beam stress at the tee {sb_f:.0f} MPa ({ld['beam_fact_case']}), VM opposite signs"})
    # --- fatigue at the three preloads, design curve + fretting (metal edge)
    Sa_d = allowable_sa("metal", cfg, "design")
    Sa_m = allowable_sa(None, cfg, "mean")
    fat = {}
    for k in ("lo", "nom", "hi"):
        P = P_nom * lim[k]
        best = None
        for ek, dist in ((a_, b_) for a_ in (False, True) for b_ in DISTS):
            smax = hoop(P, im3_w, edge_w, side_w, ek, dist)
            smin = hoop(P, 0.0, 0.0, 0.0, ek, dist)
            ha, hm = abs(smax - smin) / 2, (smax + smin) / 2
            kb = cfg["kt_clamp_edge"] * sb_w / 2            # R 0 walk at the clamp edge, Kt 2
            sa, sm = ha + kb, hm + kb
            mg = goodman_margin(sa, sm, Sa_d)
            if best is None or mg < best["margin"]:
                best = {"margin": mg, "sa": sa, "sm": sm, "smin": smin, "smax": smax, "ek": ek, "dist": dist,
                        "mean_curve": goodman_margin(sa, sm, Sa_m)}
        fat[k] = best
        rows.append({"item": "5", "row": f"upper tee: stay wall fatigue, preload {k} ({P:.0f} N per half), design curve + fretting",
                     "kind": "fatigue", "value": 1 / best["margin"], "allow": 1.0, "margin": best["margin"],
                     "basis": f"Goodman sa {best['sa']:.1f} / Sa {Sa_d:.1f} (Yahr design {sn_basis()['design']:.1f} x fretting "
                              f"{cfg['fret_metal']}{' x anodise 0.7' if cfg['finish'] == 'anodised' else ''}) + sm {best['sm']:.0f} / 290; "
                              f"hoop {best['smin']:.0f} -> {best['smax']:.0f} MPa ({best['dist']} jaws, closing force {Fc:.0f} N), Kt {cfg['kt_clamp_edge']:g} x stay beam walk "
                              f"{sb_w:.1f} MPa ({ld['beam_walk_case']}); on the mean curve without fretting: {best['mean_curve']:.2f}"})
    # --- leg clearance at +30 % + limit loads
    Ph = P_nom * lim["hi"]
    gl = max(tee_gap_loss(L, ab, {"jaw0": (Ph - fc) / 1000 + side, "jaw1": (Ph - fc) / 1000, "jawc0": fc / 1000,
                                  "jawc1": fc / 1000, "loop": IM3_F / 1000, k_: edge})
             for k_ in ("edge_j", "edge_k") for fc in (0.0, min(Ph, Fc)))
    c0 = BQ.CFG0["leg_clear_mm"]
    rows.append({"item": "5", "row": "upper tee: crown-leg radial clearance at +30 % preload + limit loads", "kind": "joint",
                 "value": gl, "allow": c0 - 0.3, "margin": (c0 - 0.3) / max(gl, 1e-9),
                 "basis": f"bore gap loss {gl:.3f} mm (n 0 + n 2, solid FE) vs {c0} - 0.3 mm (ASSUMPTION FIT)"})
    # --- clamp bolts (tension at +30 %), shells, backers
    Fb_hi = cfg["Fb_nom"] * lim["hi"]
    cap = BQ.A2_PROOF * BQ.M5_AS
    ext = (ld["fy"] / 2) / 2                              # side push shared by the pair on that side (prying ignored)
    rows.append({"item": "5", "row": "upper tee clamp bolts (M5 A2-70): tension at +30 % preload + side push",
                 "kind": "joint", "value": Fb_hi + ext, "allow": cap, "margin": cap / (Fb_hi + ext),
                 "basis": f"proof 450 MPa x As 14.2 = {cap:.0f} N; preload {Fb_hi:.0f} + {ext:.0f} N"})
    sw = SHELL
    k_f = BQ.E_AL * st["t"] / (R - st["t"] / 2) ** 2
    beta = (k_f / (4 * BQ.E_AL * sw["t"] ** 3 / 12)) ** 0.25
    w_line = 2 * Fb_hi / cfg["backer_w"]                  # one bolt pair on one backer, 25.4 mm wide
    s_sh = 6 * (w_line / (4 * beta)) / sw["t"] ** 2
    # ASSUMPTION SHELL-FIT: the 1.010 in bore closes 0.127 mm radially onto the 1.000 in stay; the half-shell bends to
    # the stay's curvature: sigma = E (t / 2) d(kappa) on the mean radii
    rm_s, rm_t = (sw["id"] + sw["t"]) / 2, (st["od"] + sw["t"]) / 2
    s_fit = BQ.E_AL * sw["t"] / 2 * (1 / rm_t - 1 / rm_s)
    rows.append({"item": "5", "row": "clamp half-shell: backer line load (+30 %) + closing the 1.010 in bore onto the stay",
                 "kind": "strength", "value": s_sh + s_fit, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / (s_sh + s_fit),
                 "basis": f"beam on elastic foundation (Hetenyi, BL-081 method): w {w_line:.0f} N/mm, beta {beta:.3f} -> "
                          f"{s_sh:.0f} MPa; + fit bending {s_fit:.0f} MPa (ASSUMPTION SHELL-FIT)"})
    span = 2 * (sw["od"] / 2 + 3.0)
    tb = cfg["backer_t"]
    s_bk = 6 * (2 * Fb_hi * span / 8) / (cfg["backer_w"] * tb ** 2)
    rows.append({"item": "5", "row": "tee backer (1 x 3/16) bending between the clamp bolts (+30 %)", "kind": "strength",
                 "value": s_bk, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_bk,
                 "basis": f"2 Fb on the shell crown, bolts {span:.1f} mm apart, P L / 8"})
    # --- bar end: 2 x M5 in double shear through the upper backers and the bar (crush sleeve), metal path (M8)
    p = cfg["bar_bolt_pitch"]
    ub = BQ.STOCK[BQ.CFG0["ubar"]]
    F_bolt = ld["mxy"] / p + math.hypot(ld["fy"], ld["fz"]) / 2
    tau = F_bolt / 2 / BQ.M5_MINOR_A
    rows.append({"item": "5", "row": "upper bar end: 2 x M5 A2 in double shear (bar couple + shear)", "kind": "joint",
                 "value": tau, "allow": 0.6 * BQ.A2_PROOF, "margin": 0.6 * BQ.A2_PROOF / tau,
                 "basis": f"per bolt M / pitch {p:g} + V / 2 = {F_bolt:.0f} N, two shear planes on the minor area"})
    ed = cfg["bar_bolt_edge"] / BQ.HOLE_D
    brg_allow = BQ.BRG_Y_ED2 * min(1.0, ed / 2.0)
    brg = F_bolt / (2 * BQ.HOLE_D * ub["t"])
    rows.append({"item": "5", "row": "upper bar wall: bolt bearing at the bar end (e/D {:.1f})".format(ed), "kind": "strength",
                 "value": brg, "allow": brg_allow, "margin": brg_allow / brg,
                 "basis": f"{F_bolt:.0f} N on two walls 5.3 x {ub['t']:.2f}; allowable 386 x min(1, e/D / 2)"})
    brg_bk = F_bolt / 2 / (BQ.HOLE_D * tb)
    rows.append({"item": "5", "row": "upper backer: bar-bolt bearing (3/16 flat)", "kind": "strength", "value": brg_bk,
                 "allow": BQ.BRG_Y_ED2, "margin": BQ.BRG_Y_ED2 / brg_bk, "basis": "half the bolt force per backer"})
    # bar holes fatigue: walk couple, pin-loaded hole Kt from the BL-081 solid FE (bearing along the tube 1.28 on P/dt,
    # tension 3.35 gross): bore peak ~ Kt_brg x bearing + Kt_t x bar axial, design curve, no fretting (bolt bearing)
    Fw = ld["w_mxy"] / p + ld["w_fy"] / 2
    s_w = 1.28 * Fw / (2 * BQ.HOLE_D * ub["t"]) + 3.35 * ld["w_fx"] / BQ.area(BQ.CFG0["ubar"])
    Sm0 = 2 * allowable_sa(None, cfg) * 290 / (290 + allowable_sa(None, cfg))      # R 0 Smax, design curve
    rows.append({"item": "5", "row": "upper bar end bolt holes: fatigue (design curve)", "kind": "fatigue", "value": s_w,
                 "allow": Sm0, "margin": Sm0 / max(s_w, 1e-9),
                 "basis": f"walk bolt force {Fw:.0f} N; pin-loaded Kt 1.28 on P/dt + Kt 3.35 on the walk axial; R 0 design "
                          f"S_max {Sm0:.0f} MPa (Goodman)"})
    # printed parts: bar saddle plug (compression of the coped end), stay-top collar (rim, bushing flange)
    P_ = BQ.paht()
    a_pl = math.pi / 4 * (ub["od"] - 2 * ub["t"]) ** 2
    s_pl = ld["fx"] / a_pl
    rows.append({"item": "5", "row": "printed bar saddle plug: bar compression (PAHT, across the layers)", "kind": "strength",
                 "value": s_pl, "allow": P_["z_hw"], "margin": P_["z_hw"] / max(s_pl, 1e-9),
                 "basis": f"bar axial {ld['fx']:.0f} N on the {a_pl:.0f} mm2 plug face; the bolts carry the bar if the plug is absent"})
    # --- static-cinch fretting criterion (BL-081 FRET-50) at -30 %
    Fc_lo = cfg["mu"] * math.pi * P_nom * lim["lo"] * cfg["retention"]
    cyc = 150.0 * 0.3
    rows.append({"item": "9", "row": "static-cinch cycles 150 N x 1e5: clamp micro-slip criterion at -30 % preload",
                 "kind": "fatigue", "value": cyc, "allow": 0.5 * Fc_lo, "margin": 0.5 * Fc_lo / cyc,
                 "basis": "cyclic tangential <= 0.5 x retained slip capacity (ASSUMPTION FRET-50)"})
    rows.append({"item": "5", "row": "upper tee preload window (info)", "kind": "info", "value": None, "allow": None,
                 "margin": None, "basis": f"{nb} x M5 A2 at {cfg['Fb_nom']:.0f} N ({cfg['torque_nm']} N m at K {cfg['K_nut']}, "
                 f"torque screwdriver); rows above at {lim['lo']:.2f} / 1.00 / {lim['hi']:.2f} x nominal"})
    for r in rows:
        r.setdefault("tee", "upper")
    return rows


def preload_sweep(g: dict, cfg: dict | None = None, factors=(0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7)) -> list[dict]:
    """Upper-tee slip and wall-fatigue margins against the preload factor (x nominal): the window (B3)."""
    cfg = {**CFG85, **(cfg or {})}
    out = []
    for f in factors:
        c = {**cfg, "Fb_nom": cfg["Fb_nom"] * f, "scatter": 0.0}
        rs = upper_tee_rows(g, c)
        slip = next(r for r in rs if r["row"].startswith("upper tee slip") and "nom" in r["row"])["margin"]
        fat = next(r for r in rs if "fatigue, preload nom" in r["row"])["margin"]
        st = next(r for r in rs if r["row"].startswith("upper tee: stay wall at limit"))["margin"]
        out.append({"factor": f, "Fb": cfg["Fb_nom"] * f, "slip": slip, "fatigue": fat, "static": st})
    return out


# ----------------------------------------------------------------------------- mid tee rows (pinned saddle)
def mid_tee_rows(g: dict, cfg: dict | None = None) -> list[dict]:
    cfg = {**CFG85, **(cfg or {})}
    ld = tee_loads(g, 330.0)
    U = tee_units(cfg["shell_len"], cfg["free_above"])
    loop_hoop = U["loop"]["hoop"]                     # per kN, 25-28 mm aft patch (conservative for a 40 mm saddle)
    rows = []
    sb_f, sb_w = ld["beam_fact"], ld["beam_walk"]
    sh = loop_hoop * max(ld["fx"], ld["fy"]) / 1000.0
    s_lim = math.sqrt(sh ** 2 + sb_f ** 2 + sh * sb_f)
    rows.append({"item": "5", "row": "mid tee (pinned saddle): stay wall at limit (beam + saddle bearing)", "kind": "strength",
                 "value": s_lim, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_lim,
                 "basis": f"stay beam stress at z 330 {sb_f:.0f} MPa ({ld['beam_fact_case']}, C6p included) + saddle ring "
                          f"{sh:.1f} MPa from the bar force {max(ld['fx'], ld['fy']):.0f} N"})
    shw = loop_hoop * max(ld["w_fx"], ld["w_fy"]) / 1000.0
    smax = cfg["kt_saddle"] * sb_w + shw
    Sa = allowable_sa("poly", cfg)
    mg = goodman_margin(smax / 2, smax / 2, Sa)
    rows.append({"item": "5", "row": "mid tee (pinned saddle): stay wall fatigue, design curve + polymer-contact fretting",
                 "kind": "fatigue", "value": 1 / mg, "allow": 1.0, "margin": mg,
                 "basis": f"R 0 walk: Kt {cfg['kt_saddle']} (ASSUMPTION SADDLE-KT, PAHT pad edge, no metal clamp) x beam "
                          f"{sb_w:.1f} MPa ({ld['beam_walk_case']}) + ring {shw:.1f}; Sa {Sa:.1f} (design {sn_basis()['design']:.1f} x "
                          f"{cfg['fret_poly']}); preload-free: the band only positions the saddle"})
    P_ = BQ.paht()
    st = BQ.STOCK[STAY]
    a_c = st["od"] * cfg["saddle_len"] * 0.6
    s_c = max(ld["fx"], ld["fy"]) / a_c
    rows.append({"item": "5", "row": "mid tee saddle (PAHT): bearing on the stay", "kind": "strength", "value": s_c,
                 "allow": P_["z_hw"], "margin": P_["z_hw"] / max(s_c, 1e-9),
                 "basis": f"{max(ld['fx'], ld['fy']):.0f} N factored on D x {cfg['saddle_len']:g} mm x 0.6 (cos), compression"})
    mb = BQ.STOCK[BQ.CFG0["bar"]]
    brg = ld["fx"] / (2 * BQ.HOLE_D * 6.0)                # M5 through the socket + bar end, 6 mm PAHT each side
    rows.append({"item": "5", "row": "mid bar socket bolt: bearing in PAHT", "kind": "strength", "value": brg,
                 "allow": P_["z_hw"], "margin": P_["z_hw"] / max(brg, 1e-9),
                 "basis": f"bar axial {ld['fx']:.0f} N factored on 2 x 5.3 x 6 mm"})
    brg_c = ld["w_fx"] / BQ.G_WALK / (2 * BQ.HOLE_D * 6.0)
    allow_c = P_["z_hw"] * P_["creep"]
    rows.append({"item": "5", "row": "mid bar socket: sustained bearing (creep, 1 g carry)", "kind": "creep", "value": brg_c,
                 "allow": allow_c, "margin": allow_c / max(brg_c, 1e-9),
                 "basis": "1 g share of the walk bar force vs z_hw x creep_rupture_8h_40c_ratio (review 9 m8)"})
    wall = mb["t"]
    s_mb = ld["fx"] / (2 * BQ.HOLE_D * wall)
    rows.append({"item": "5", "row": "mid bar (3/4 x .035) wall: socket bolt bearing", "kind": "strength", "value": s_mb,
                 "allow": BQ.BRG_Y_ED2 * 0.6, "margin": BQ.BRG_Y_ED2 * 0.6 / max(s_mb, 1e-9),
                 "basis": "e/D 1.2 at the bar end -> 0.6 x 386"})
    rows.append({"item": "5", "row": "mid tee: force along the stay (band positioning only)", "kind": "info", "value": ld["fz"],
                 "allow": None, "margin": None,
                 "basis": f"{ld['fz']:.1f} N factored on the 200 N/mm positioning spring: the band carries no strength load"})
    for r in rows:
        r.setdefault("tee", "mid")
    return rows


def b81_asbuilt_check(g: dict) -> dict:
    """Review 9 B1 control on this code: the B81 shell (pressure on the 35 mm of tube that the 50 mm shell overlaps,
    free end at its top), 2 x 2000 N, the BL-081 load magnitudes (IM3 loop below), mean and design curve."""
    ld = tee_loads(g, 520.0)
    cfg = dict(CFG85)
    release()
    U = tee_units(35.0, 0.0)
    edge = max(ld["mxy"], 50073.0) / (0.67 * 50.0) / 1000.0
    sh = max(tee_hoop(35.0, 0.0, {"jaw0": 4.0, "jaw1": 4.0, "loop": IM3_F / 1000, k: edge}) for k in ("edge_j", "edge_k"))
    sb_rec = 91.0
    s_lim = math.sqrt(sh ** 2 + sb_rec ** 2 + sh * sb_rec)
    im3w, edw = IM3_F / 3.0 * BQ.G_WALK / 1000, edge / 3.0 * BQ.G_WALK
    smax = max(tee_hoop(35.0, 0.0, {"jaw0": 4.0, "jaw1": 4.0, "loop": im3w, k: edw}) for k in ("edge_j", "edge_k"))
    smin = tee_hoop(35.0, 0.0, {"jaw0": 4.0, "jaw1": 4.0})
    kb = sb_rec / 3.0 * BQ.G_WALK
    sa, sm = abs(smax - smin) / 2 + kb, (smax + smin) / 2 + kb
    return {"hoop_limit": sh, "static_margin": BQ.FY_6061 / s_lim, "hoop_walk": [smin, smax],
            "fatigue_mean": goodman_margin(sa, sm, allowable_sa(None, cfg, "mean")),
            "fatigue_design_fret": goodman_margin(sa, sm, allowable_sa("metal", cfg, "design")),
            "dofs": U["dofs"],
            "note": "B81 basis (record beam stress 91 MPa, Kt 2, IM3 loop under the shell); review 9 got 0.65 / 0.67"}
