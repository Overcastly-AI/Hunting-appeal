"""BL-081 local checks on concept B81 (frame_concepts.md section 8, items 2-9).

Every row takes its forces from the global model (``bl081_concept_b.evaluate_global``: factored = x case factor,
walk = static carry x 1.6 g) and returns {"row", "check", "value", "allow", "margin", "basis", "kind"} with
margin = allow / value (>= 1.0 passes, the case factor is already in the forces).

Hole checks use the solid submodel (``huntkit.fea.tube_solid``) by superposition of 10 unit cases on a 1 in tube with
an M5 through-hole (N, Vy, Vz, T, My, Mz at the hole and bolt bearing on each bore along and across the tube axis).
Fatigue: the superposed bore peak at the walking load (R 0), notch-sensitivity corrected
sigma_f = sigma_ref + q (sigma_peak - sigma_ref), q = Peterson 1 / (1 + a / r), against the smooth R 0 1e5 allowable
of the BL-080 basis (``fat_allow_local``). Static: bearing yield (e/D rule) and net-section von Mises.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache

import numpy as np

from huntkit.gendesign import bl081_concept_b as BQ

UNIT_NAMES = ("N", "Vy", "Vz", "T", "My", "Mz", "b0x", "b0s", "b1x", "b1s", "w0", "w1")
SUB_L = 80.0


# ============================================================================ hole submodel (unit cases, cached)
def _hole_units(tube_key: str) -> dict:
    """Bore stress tensors for the 10 unit cases on hole 0 (theta 0) and hole 1 (theta pi). Cached to disk."""
    from huntkit.fea.tube_solid import Hole, TubeFE, TubeModel
    BQ.CACHE.mkdir(parents=True, exist_ok=True)
    path = BQ.CACHE / f"hole_units_v2_{tube_key}.npz"
    st = BQ.STOCK[tube_key]
    if path.exists():
        d = np.load(path, allow_pickle=True)
        return {"S0": d["S0"], "S1": d["S1"], "meta": d["meta"].item()}
    m = TubeModel(L=SUB_L, od=st["od"], t=st["t"], holes=[Hole(SUB_L / 2, 0.0, BQ.HOLE_D)], h=2.0, h_hole=0.25)
    fe = TubeFE(m)
    lev = SUB_L - SUB_L / 2
    loads = {"N": fe.end_load(N=1.0), "Vy": fe.end_load(Vy=1.0, Mz=-lev), "Vz": fe.end_load(Vz=1.0, My=lev),
             "T": fe.end_load(T=1.0), "My": fe.end_load(My=1.0), "Mz": fe.end_load(Mz=1.0),
             "b0x": fe.hole_bearing(0, 1.0, (1, 0)), "b0s": fe.hole_bearing(0, 1.0, (0, 1)),
             "b1x": fe.hole_bearing(1, 1.0, (1, 0)), "b1s": fe.hole_bearing(1, 1.0, (0, 1)),
             # washer / spacer end pushing the wall inward round the bore (bolt axial load), 14 mm patch
             "w0": fe.patch_pressure(SUB_L / 2 - 7, SUB_L / 2 + 7, 0.0, math.radians(32), 1.0, "outer"),
             "w1": fe.patch_pressure(SUB_L / 2 - 7, SUB_L / 2 + 7, math.pi, math.radians(32), 1.0, "outer")}
    S0, S1 = [], []
    for k in UNIT_NAMES:
        u = fe.solve(loads[k])
        t0 = fe.bore_stress_tensors(u, 0)
        t1 = fe.bore_stress_tensors(u, 1)
        S0.append(np.array([t0[v] for v in sorted(t0)]))
        S1.append(np.array([t1[v] for v in sorted(t1)]))
    S0, S1 = np.array(S0), np.array(S1)
    meta = {"tube": tube_key, "L": SUB_L, "h": 2.0, "h_hole": 0.25, "nodes": int(fe.mesh.p.shape[1]),
            "dofs": int(fe.K.shape[0])}
    ro, ri = st["od"] / 2, st["od"] / 2 - st["t"]
    A = math.pi * (ro ** 2 - ri ** 2)
    I = math.pi * (ro ** 4 - ri ** 4) / 4

    def pk(S):
        return float(max(np.abs(np.linalg.eigvalsh(S)).max(axis=1)))
    meta["kt_gross"] = {"tension": pk(S0[0]) * A, "bending_hole_on_extreme_fibre": max(pk(S0[5]), pk(S1[5])) * I / ro,
                        "bending_hole_on_neutral_axis": pk(S0[4]) * I / ro, "torsion_on_tau": pk(S0[3]) * 2 * I / ro,
                        "bearing_axial_on_sigma_br": pk(S0[6]) * BQ.HOLE_D * st["t"],
                        "bearing_circ_on_sigma_br": pk(S0[7]) * BQ.HOLE_D * st["t"]}
    np.savez(path, S0=S0, S1=S1, meta=np.array(meta, dtype=object))
    return {"S0": S0, "S1": S1, "meta": meta}


@lru_cache(maxsize=None)
def hole_units(tube_key: str) -> dict:
    return _hole_units(tube_key)


def sub_forces(f_local, R, hole_axis: str):
    """Member section forces (local N..Mz, rotation R) -> submodel (X tube axis, Y hole axis, Z = X x Y)."""
    f = np.asarray(f_local, float)
    R = np.asarray(R, float)
    F = R.T @ f[:3]
    M = R.T @ f[3:]
    X = R[0]
    h = np.zeros(3)
    h["xyz".index(hole_axis)] = 1.0
    Y = h - (h @ X) * X
    Y /= np.linalg.norm(Y)
    Z = np.cross(X, Y)
    return np.array([F @ X, F @ Y, F @ Z, M @ X, M @ Y, M @ Z]), (X, Y, Z)


def hole_peak(tube_key, sec6, wall0, wall1, washer=(0.0, 0.0)):
    """Superposed bore principal peak (abs) and the gross nominal at the hole fibres. wall0 / wall1 = bearing force
    (axial X, circumferential e_theta) on the theta 0 / theta pi bore."""
    U = hole_units(tube_key)
    c = np.r_[sec6, wall0[0], wall0[1], wall1[0], wall1[1], washer[0], washer[1]]
    S0 = np.tensordot(c, U["S0"], axes=1)
    S1 = np.tensordot(c, U["S1"], axes=1)
    pk = max(np.abs(np.linalg.eigvalsh(S0)).max(), np.abs(np.linalg.eigvalsh(S1)).max())
    st = BQ.STOCK[tube_key]
    ro, ri = st["od"] / 2, st["od"] / 2 - st["t"]
    A = math.pi * (ro ** 2 - ri ** 2)
    I = math.pi * (ro ** 4 - ri ** 4) / 4
    N, Vy, Vz, T, My, Mz = sec6
    s_h = max(abs(N / A - Mz * ro / I), abs(N / A + Mz * ro / I))      # hole fibres (Y = +/- R)
    s_max = abs(N / A) + math.hypot(My, Mz) * ro / I                   # section extreme fibre
    tau = abs(T) * ro / (2 * I) + 2 * math.hypot(Vy, Vz) / A
    brg = max(np.hypot(*wall0), np.hypot(*wall1)) / (BQ.HOLE_D * st["t"])
    return {"peak": float(pk), "s_hole_nom": float(s_h), "s_max_nom": float(s_max), "tau": float(tau),
            "brg": float(brg), "A": A, "I": I}


def _walls(link6, frame, R_m, pin=None, pin_force=None):
    """Bearing on the two bores from a bolt link (force + torque on the tube, global) or from a pin load."""
    X, Y, Z = frame
    if link6 is not None:
        F = np.asarray(link6[:3], float)
        M = np.asarray(link6[3:], float)
        fx, fz = F @ X / 2, F @ Z / 2
        f_c = (M @ X) / (2 * R_m)          # couple: +Z at theta 0, -Z at theta pi (= +e_theta at both)
        return np.array([fx, fz + f_c]), np.array([fx, -(fz) + f_c])
    if pin_force is not None:
        F = np.asarray(pin_force, float)
        fx, fz = F @ X, F @ Z
        if pin == "hinge":                 # eye between the outer cheek and the stay: the near wall takes F / 2
            return np.array([fx / 2, fz / 2]), np.zeros(2)
        return np.array([fx / 2, fz / 2]), np.array([fx / 2, -fz / 2])
    return np.zeros(2), np.zeros(2)


def _pin_vec(name: str, kind: str, factored: bool) -> np.ndarray:
    """Pin loads that the beam model does not carry as links: hinge (bag-on hinge 1018.8 N factored, down onto the
    z 60 pin, attach_system_results.json factored_n.hinge) and the pawl housing (half the pawl link force per bolt,
    taken from the case record)."""
    if kind == "hinge":
        F = 1018.8 if factored else 1018.8 / 3.0 * BQ.G_WALK
        return np.array([0.0, 0.0, -F])
    return np.zeros(3)


def hole_rows(glob: dict, cfg: dict) -> list[dict]:
    """Item 2 (cross tube), item 3 / 7 (stay holes z 60 / 90 / 155), item 5 (pawl-housing holes): static + fatigue."""
    rows = []
    sts = {s["name"]: s for s in BQ.stations(cfg)}
    pawl_by_case = {}
    for rec in glob["walk"].get("_links", []):
        pawl_by_case[rec["case"]] = np.asarray(rec["links"]["pawl"], float)
    q = BQ.notch_q(BQ.HOLE_D / 2)
    f_allow = BQ.fat_allow_local(1.0)
    for name, s in sts.items():
        st = BQ.STOCK[s["tube"]]
        R_m = st["od"] / 2 - st["t"] / 2
        worst_s, worst_f = None, None
        for kind, recs in (("static", glob["stations"].get(name, [])), ("fatigue", glob["walk"].get(name, []))):
            for rec in recs:
                sec, frame = sub_forces(rec["f"], rec["R"], s["axis"])
                if s.get("link"):
                    w0, w1 = _walls(rec["link"], frame, R_m)
                elif s.get("pin") == "hinge":
                    w0, w1 = _walls(None, frame, R_m, "hinge", _pin_vec(name, "hinge", kind == "static"))
                elif s.get("pin") == "pawl":
                    # pawl link force on UB1 shared by the two housing bolts
                    if kind == "static":
                        lp = np.asarray(glob["links"]["pawl"]["vec"][:3], float) / 2
                    else:
                        lp = pawl_by_case.get(rec["case"], np.zeros(6))[:3] / 2
                    w0, w1 = _walls(None, frame, R_m, "pawl", lp)
                else:
                    w0, w1 = np.zeros(2), np.zeros(2)
                wsh = (0.0, 0.0)
                if s.get("washer") and rec["link"] is not None:
                    FY = float(np.asarray(rec["link"][:3]) @ frame[1])
                    wsh = (max(-FY, 0.0), max(FY, 0.0))
                h = hole_peak(s["tube"], sec, w0, w1, wsh)
                if kind == "static":
                    # e/D >= 2 everywhere: continuous tube, or the cross-tube end bolt 11.3 mm from the cut end
                    brg_allow = BQ.BRG_Y_ED2
                    sig_net = math.sqrt(h["s_max_nom"] ** 2 + 3 * h["tau"] ** 2) * h["A"] / (h["A"] - BQ.HOLE_D * st["t"] * 2)
                    m = min(brg_allow / max(h["brg"], 1e-9), BQ.FY_6061 / max(sig_net, 1e-9))
                    if worst_s is None or m < worst_s["margin"]:
                        worst_s = {"margin": m, "brg": h["brg"], "brg_allow": brg_allow, "sig_net": sig_net,
                                   "case": rec["case"], "peak": h["peak"]}
                else:
                    ref = max(h["s_hole_nom"], h["tau"] * math.sqrt(3), h["brg"] * 0.0)
                    sf = ref + q * max(h["peak"] - ref, 0.0)
                    m = f_allow / max(sf, 1e-9)
                    if worst_f is None or m < worst_f["margin"]:
                        worst_f = {"margin": m, "peak": h["peak"], "ref": ref, "sigma_f": sf, "case": rec["case"],
                                   "kt_eff": h["peak"] / max(ref, 1e-6)}
        item = "2" if "rung" in name else ("5" if "upper bar" in name else ("7" if "z60" in name else "3"))
        if worst_s:
            rows.append({"item": item, "row": f"{name}: static (bearing / net section)", "kind": "strength",
                         "value": worst_s["brg"], "allow": worst_s["brg_allow"], "margin": worst_s["margin"],
                         "basis": f"bearing {worst_s['brg']:.0f} MPa vs {worst_s['brg_allow']:.0f} (AA e/D 2), net-section "
                                  f"VM {worst_s['sig_net']:.0f} vs S-basis Fy 241; {worst_s['case']}"})
        if worst_f:
            rows.append({"item": item, "row": f"{name}: fatigue 1e5 x 0-1.6 g", "kind": "fatigue",
                         "value": worst_f["sigma_f"], "allow": f_allow, "margin": worst_f["margin"],
                         "basis": f"solid FE bore peak {worst_f['peak']:.0f} MPa (Kt_eff {worst_f['kt_eff']:.2f} on "
                                  f"{worst_f['ref']:.0f}), q {q:.2f} -> {worst_f['sigma_f']:.0f} vs smooth R0 {f_allow:.0f}; "
                                  f"{worst_f['case']}"})
    return rows


# ============================================================================ gussets (item 1 / 2)
def gusset_rows(glob: dict, cfg: dict) -> list[dict]:
    """6061 L-gusset pair, hand check on the arm root forces (per plate): axial, in-plane bending (Mz), out-of-plane
    couple (My / 2d), torsion as differential in-plane bending (T / 2d x arm length), net section at the first hole.
    Bolt bearing in the plate from the link forces. Fatigue: walk stresses x Kf (Heywood strip Kt, Peterson q)."""
    from huntkit.fea.tube_solid import heywood_kt
    t, w = cfg["gusset_t"], cfg["gusset_w"]
    st = BQ.STOCK[cfg["stay"]]
    d = st["od"] / 2 + 1.0 + t / 2
    rows = []
    net = (w - BQ.HOLE_D) / w
    kt = heywood_kt(BQ.HOLE_D / w)
    kf = 1 + BQ.notch_q(BQ.HOLE_D / 2) * (kt - 1)
    arm_L = {"lo": 120.0 - cfg["stay_bolt_z"][0], "hi": cfg["stay_bolt_z"][1] - 120.0,
             "a": 115.0 - cfg["ct_bolt_x"][1]}

    def plate_sigma(f, L):
        N, Vy, Vz, T, My, Mz = f
        s = abs(N) / (2 * w * t) + abs(Mz) / 2 / (t * w ** 2 / 6) + abs(My) / (2 * d) / (w * t) \
            + abs(T) / (2 * d) * L / (t * w ** 2 / 6)
        return s

    worst_s, worst_f = (np.inf, None), (np.inf, None)
    f_allow = BQ.fat_allow_local(1.0)
    for mid, recs in glob.get("members_f", {}).items():
        if not mid.startswith("G"):
            continue
        key = "a" if mid.endswith("-GLa") or mid.endswith("-GRa") else ("lo" if "lo" in mid else "hi")
        L = arm_L.get(key, 30.0)
        for rec in recs:
            for end in ("start", "end"):
                s = plate_sigma(rec[end], L) / net
                m = BQ.FY_6061 / s if s > 0 else np.inf
                if m < worst_s[0]:
                    worst_s = (m, {"member": mid, "case": rec["case"], "sigma": s})
        for rec in glob.get("members_w", {}).get(mid, []):
            for end in ("start", "end"):
                s = plate_sigma(rec[end], L) * kf
                m = f_allow / s if s > 0 else np.inf
                if m < worst_f[0]:
                    worst_f = (m, {"member": mid, "case": rec["case"], "sigma": s})
    rows.append({"item": "1", "row": f"lumbar L-gussets ({t / 25.4:.3f} in x {w:.1f} mm): plate strength", "kind": "strength",
                 "value": worst_s[1]["sigma"], "allow": BQ.FY_6061, "margin": worst_s[0],
                 "basis": f"per-plate axial + in-plane + couple + torsion-as-differential-bending on the net section "
                          f"(w - d)/w {net:.2f}; {worst_s[1]['member']} {worst_s[1]['case']}"})
    rows.append({"item": "1", "row": "lumbar L-gussets: fatigue at the bolt holes", "kind": "fatigue",
                 "value": worst_f[1]["sigma"], "allow": f_allow, "margin": worst_f[0],
                 "basis": f"walk plate stress x Kf {kf:.2f} (Heywood Kt {kt:.2f}, q {BQ.notch_q(BQ.HOLE_D / 2):.2f}); "
                          f"{worst_f[1]['member']} {worst_f[1]['case']}"})
    # bearing in the plates (2 plates share each bolt)
    worst = (0.0, None)
    for lid, v in glob["links"].items():
        if lid.startswith(("lb_", "lc_")) and "|" not in lid:
            F = v["F"]
            Mt = glob["links"][lid + "|M"]["M"]
            R_m = st["od"] / 2 - st["t"] / 2
            per_plate = F / 2 + Mt / (2 * R_m)
            b = per_plate / (BQ.HOLE_D * t)
            if b > worst[0]:
                worst = (b, lid, v["case"])
    allow = BQ.BRG_Y_ED2 * 0.95       # plate edge distance 10 mm = 1.9 d
    rows.append({"item": "1", "row": "lumbar gussets: bolt bearing in the .090 plate", "kind": "joint",
                 "value": worst[0], "allow": allow, "margin": allow / worst[0],
                 "basis": f"(F / 2 + T / 2R) / (d t), e/D 1.9 -> 386 x 0.95; {worst[1]} {worst[2]}"})
    return rows


# ============================================================================ bolts (shear) and joint stiffness rows
def bolt_rows(glob: dict, cfg: dict) -> list[dict]:
    rows = []
    tau_allow = 0.6 * BQ.A2_PROOF
    worst = (0.0, None)
    for lid, v in glob["links"].items():
        if "|" in lid or not lid.startswith(("lb_", "lc_", "tie_")):
            continue
        tube = BQ.STOCK[cfg["ctube"] if lid.startswith(("lc_", "tie_")) else cfg["stay"]]
        R_m = tube["od"] / 2 - tube["t"] / 2
        Mt = glob["links"][lid + "|M"]["M"]
        per_plane = v["F"] / 2 + Mt / (2 * R_m)
        tau = per_plane / BQ.M5_MINOR_A
        if tau > worst[0]:
            worst = (tau, lid, v["case"])
    rows.append({"item": "1", "row": "M5 A2-70 through-bolts: shear at each wall (gussets, hip ties)", "kind": "joint",
                 "value": worst[0], "allow": tau_allow, "margin": tau_allow / worst[0],
                 "basis": f"(F/2 + T/2R) on the minor-diameter area, 0.6 x 450 MPa proof; {worst[1]} {worst[2]}"})
    return rows


# ============================================================================ hip bracket (item 6)
def hip_rows(glob: dict, cfg: dict) -> list[dict]:
    """Two-angle U cradle: Ti-mount bolts (tipping), front leg plate bending, key bolt spacer column, web bolts,
    angle bearing; loads = hip pin reaction from the global model (x case factor) plus the lumbar push H on the pin
    (hipbelt_structure C2 1239 N / walk 661 N, the H_pin bound of BL-055)."""
    from huntkit.gendesign import h1_closeout as HC
    from huntkit.gendesign import hipbelt_structure as HS
    rows = []
    ls = HS.load_sets()
    H_c2, H_walk = ls["C2"].H, ls["walk"].H
    hp = glob["hip_pin"]
    Vf = max(abs(r["F"][2]) for r in hp)
    Vw = max(abs(r["walk"][2]) for r in hp if r["walk"] is not None)
    Vx = max(abs(r["F"][0]) for r in hp)
    pat = {"boss_d": 50.0, "positions_xz": [[x, z] for x, z in BQ.MOUNT_POS]}
    tip_s = HC.tip_tension(pat, Vf, H_c2)
    tip_w = HC.tip_tension(pat, Vw, H_walk)
    cap = BQ.A2_PROOF * BQ.M5_AS - 2600.0     # M5 A2 at 2.6 kN preload (BL-080 ASSUMPTION CLAMP-PRELOAD)
    rows.append({"item": "6", "row": "Ti mount on the front angle: 6 x M5 A2 tension (tipping)", "kind": "joint",
                 "value": tip_s["T_max_n"], "allow": cap, "margin": cap / max(tip_s["T_max_n"], 1e-9),
                 "basis": f"h1_closeout.tip_tension on the 6 used positions, V {Vf:.0f} N (global, factored) + H {H_c2:.0f} N; "
                          f"capacity proof x As - preload 2.6 kN"})
    t = 0.125 * BQ.IN
    b = 2 * 1.5 * BQ.IN - 2 * BQ.HOLE_D
    M_leg = tip_s["M_net_nmm"] / 2
    s_leg = 6 * M_leg / (b * t ** 2)
    rows.append({"item": "6", "row": "front angle leg: plate bending under the mount tipping couple", "kind": "strength",
                 "value": s_leg, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_leg,
                 "basis": f"M_net {tip_s['M_net_nmm'] / 1e3:.1f} N m shared by the web corner and the key-bolt row (1/2 each), "
                          f"strip {b:.0f} mm (2 holes out) x 3.175"})
    kt_leg = 2.0       # ASSUMPTION: bolt holes in a plate strip in bending (Peterson 4.x, d/W small), HA-LS-1 Kt 2 rule
    s_leg_w = 6 * tip_w["M_net_nmm"] / 2 / (b * t ** 2) * (1 + BQ.notch_q(BQ.HOLE_D / 2) * (kt_leg - 1))
    fa = BQ.fat_allow_local(1.0)
    rows.append({"item": "6", "row": "front angle leg: fatigue at the mount holes", "kind": "fatigue",
                 "value": s_leg_w, "allow": fa, "margin": fa / s_leg_w,
                 "basis": f"walk M_net {tip_w['M_net_nmm'] / 1e3:.1f} N m, Kf from Kt 2"})
    # front leg + 1 x 1/8 backer strip at the tie bolts: plate strip from the stem (outer edge) to the tie
    ties = [k for k in glob["links"] if k.startswith("tie_") and "|" not in k]
    yv = lambda k, rec=None: abs(np.asarray((rec or glob["links"][k])["vec"] if rec is None else rec, float)[1])  # noqa: E731
    Ft = max(abs(np.asarray(glob["links"][k]["vec"], float)[1]) for k in ties)
    Ft_case = max(ties, key=lambda k: abs(np.asarray(glob["links"][k]["vec"], float)[1]))
    Ftw = max(abs(np.asarray(r["links"][k], float)[1]) for r in glob["walk"]["_links"] for k in ties)
    lever = 1.5 * BQ.IN - t - cfg["tie_x"]
    wstrip = BQ.IN
    s_tie = 6 * Ft * lever / (wstrip * t ** 2) / 2.0
    rows.append({"item": "6", "row": "front leg + backer strip at the tie bolts (plate bending)", "kind": "strength",
                 "value": s_tie, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_tie,
                 "basis": f"tie axial {Ft:.0f} N ({glob['links'][Ft_case]['case']}) x {lever:.1f} mm from the stem, "
                          f"two 1/8 in layers 25.4 wide (no composite action)"})
    kf2 = 1 + BQ.notch_q(BQ.HOLE_D / 2) * (2.0 - 1)
    s_tie_w = 6 * Ftw * lever / (wstrip * t ** 2) / 2.0 * kf2
    rows.append({"item": "6", "row": "front leg + backer strip at the tie bolts: fatigue", "kind": "fatigue",
                 "value": s_tie_w, "allow": fa, "margin": fa / s_tie_w, "basis": f"walk tie {Ftw:.0f} N, Kf {kf2:.2f} (Kt 2)"})
    rows.append({"item": "6", "row": "tie bolts (M5 A2) tension", "kind": "joint", "value": Ft, "allow": cap,
                 "margin": cap / Ft, "basis": "proof x As - preload 2.6 kN"})
    # tie spacer columns (3/4 x .035) and the post (2 angles): fatigue from the walk member forces, Kt 2 at holes / ends
    sp = BQ.STOCK["t750_035"]
    A_sp = BQ.area("t750_035")
    S_sp = math.pi / 32 * (sp["od"] ** 4 - (sp["od"] - 2 * sp["t"]) ** 4) / sp["od"]
    ps = BQ.post_sec()
    worst_t, worst_p = (0.0, None), (0.0, None)
    for mid, recs in glob.get("members_w", {}).items():
        for rec in recs:
            for end in ("start", "end"):
                N, Vy, Vz, T, My, Mz = rec[end]
                if mid.startswith("tie_"):
                    sg = (abs(N) / A_sp + math.hypot(My, Mz) / S_sp) * 2.0
                    if sg > worst_t[0]:
                        worst_t = (sg, f"{mid} {rec['case']}")
                elif mid.startswith(("HM-PO", "PO")):
                    sg = (abs(N) / ps.A + abs(My) * ps.zmax / ps.Iy + abs(Mz) * ps.ymax / ps.Iz) * kf2
                    if sg > worst_p[0]:
                        worst_p = (sg, f"{mid} {rec['case']}")
    rows.append({"item": "6", "row": "tie spacer columns (3/4 x .035): fatigue, Kt 2 at the clamped ends", "kind": "fatigue",
                 "value": worst_t[0], "allow": fa, "margin": fa / worst_t[0], "basis": worst_t[1]})
    rows.append({"item": "6", "row": "hip post (2 angles): fatigue at the mount / tie holes", "kind": "fatigue",
                 "value": worst_p[0], "allow": fa, "margin": fa / worst_p[0], "basis": f"walk, Kf {kf2:.2f}; {worst_p[1]}"})
    # spacer end on the lower rung through the printed hip saddle (compression)
    P_ = BQ.paht()
    a_sh = math.pi / 4 * (sp["od"] ** 2 - 5.6 ** 2)
    rows.append({"item": "6", "row": "printed hip saddle under the tie spacer ends (compression)", "kind": "strength",
                 "value": Ft / a_sh, "allow": P_["z_hw"], "margin": P_["z_hw"] / (Ft / a_sh),
                 "basis": "tie axial on the spacer end annulus, layers in compression"})
    rows.append({"item": "6", "row": "printed hip saddle: compression fatigue", "kind": "fatigue",
                 "value": Ftw / a_sh, "allow": P_["fat"] * P_["z_hw"], "margin": P_["fat"] * P_["z_hw"] / (Ftw / a_sh),
                 "basis": "walk tie force, 0.30 x 19.66"})
    ct = BQ.STOCK[cfg["ctube"]]
    # saddle plugs (lumbar node fore-aft): PAHT in compression on the stay saddle, in-plane shear in the plug body
    P = BQ.paht()
    plugs = [k for k in glob["links"] if k.startswith("plug_") and "|" not in k]
    Fp = max(glob["links"][k]["F"] for k in plugs)
    a_sad = 2 * math.radians(70) * 12.7 * 20.0 * 0.6       # 140 deg saddle x 20 mm wide, 60 % effective (cos)
    rows.append({"item": "1", "row": "lumbar saddle plug (printed): bearing on the stay", "kind": "strength",
                 "value": Fp / a_sad, "allow": P["z_hw"], "margin": P["z_hw"] / (Fp / a_sad),
                 "basis": f"{Fp:.0f} N factored (plug link) on a 140 deg x 20 mm saddle, 60 % effective"})
    a_pl = math.pi / 4 * (ct["od"] - 2 * ct["t"]) ** 2
    rows.append({"item": "1", "row": "lumbar saddle plug: shear in the plug body (in the layer plane)", "kind": "strength",
                 "value": Fp / a_pl, "allow": P["ils_hw"], "margin": P["ils_hw"] / (Fp / a_pl),
                 "basis": "printed with the plug axis in the layer plane: in-plane shear, interlayer value 11.35 used (lower)"})
    Fpw = max(np.linalg.norm(np.asarray(r["links"][k][:3])) for r in glob["walk"]["_links"] for k in plugs)
    rows.append({"item": "1", "row": "lumbar saddle plug: bearing fatigue", "kind": "fatigue",
                 "value": Fpw / a_sad, "allow": P["fat"] * P["z_hw"], "margin": P["fat"] * P["z_hw"] / (Fpw / a_sad),
                 "basis": "walk plug force, 0.30 x 19.66"})
    return rows


# ============================================================================ bushings (item 3)
@lru_cache(maxsize=None)
def bushing_units(tube_key: str, bush_len: float, contact_deg: float) -> dict:
    """Per 1 kN of bushing load: peak |hoop| stress (ring part, free of the submodel's beam bending) and the bore
    ovalisation (n = 2 harmonic, diametral) at a mid-tube station (leg end) and at the free tube end (stay top)."""
    from huntkit.fea.tube_solid import TubeFE, TubeModel
    st = BQ.STOCK[tube_key]
    out = {}
    a = math.radians(contact_deg)
    L = 130.0
    for where, (x0, x1) in (("mid", (L / 2 - bush_len / 2, L / 2 + bush_len / 2)), ("end", (L - bush_len, L))):
        m = TubeModel(L=L, od=st["od"], t=st["t"], h=2.0, refine_x=((x0 - 4, min(x1 + 4, L), 1.6),))
        fe = TubeFE(m)
        u = fe.solve(fe.patch_pressure(x0, x1, 0.0, a, 1000.0, "inner"))
        hoop = fe.surface_hoop(u, x0 - 6, min(x1 + 6, L))
        xs = np.linspace(x0 + 2, x1 - 2, 5)
        ov = max((fe.ovalisation(u, x) for x in xs), key=lambda d: d["oval_diam_mm"])
        out[where] = {"hoop_peak": hoop, **ov}
    return out


def bushing_rows(glob: dict, cfg: dict) -> list[dict]:
    rows = []
    U = bushing_units(cfg["stay"], cfg["bush_len"], cfg["bush_contact_deg"])
    fa = BQ.fat_allow_local(1.0)
    walk = {}
    for rec in glob["walk"].get("_links", []):
        for k in ("bush_low_L", "bush_low_R", "bush_top_L", "bush_top_R"):
            walk[k] = max(walk.get(k, 0.0), float(np.linalg.norm(np.asarray(rec["links"][k])[:2])))
    s_beam = BQ.FY_6061 / glob["strength"]["stays"]["sf"] if glob["strength"].get("stays") else 0.0
    for where, keys in (("mid", ("bush_low_L", "bush_low_R")), ("end", ("bush_top_L", "bush_top_R"))):
        F = max(glob["links"][k]["F"] for k in keys)
        Fw = max(walk[k] for k in keys)
        sh = U[where]["hoop_peak"] * F / 1000.0
        sb = s_beam if where == "mid" else s_beam * 0.5     # stay top: beam moment falls to 0 at the free end
        vm = math.sqrt(sb ** 2 + sh ** 2 + sb * sh)          # opposite signs (worst) of axial beam and hoop
        label = "leg-end bushing (z 171-374)" if where == "mid" else "stay-top bushing (z 460-530, free tube end)"
        rows.append({"item": "3", "row": f"stay at the {label}: static (ring + beam)", "kind": "strength",
                     "value": vm, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / vm,
                     "basis": f"solid FE {cfg['bush_len']:g} mm bushing, {cfg['bush_contact_deg']:g} deg contact, F {F:.0f} N "
                              f"factored -> hoop {sh:.0f} MPa; with the worst stay beam stress {sb:.0f} MPa (VM, opposite signs)"})
        shw = U[where]["hoop_peak"] * Fw / 1000.0
        sbw = sb / 3.0 * BQ.G_WALK
        sf = math.sqrt((2 * sbw) ** 2 + shw ** 2 + 2 * sbw * shw)
        rows.append({"item": "3", "row": f"stay at the {label}: fatigue", "kind": "fatigue",
                     "value": sf, "allow": fa, "margin": fa / sf,
                     "basis": f"walk bushing {Fw:.0f} N -> hoop {shw:.0f} MPa, Kt 2 x beam {sbw:.0f} MPa (HA-LS-1 Kt 2 at the "
                              f"bushing end; UHMWPE on 6061 does not fret)"})
        ov = U[where]["oval_diam_mm"] * F / 1000.0
        rows.append({"item": "3", "row": f"{label}: bore ovalisation at limit vs leg clearance", "kind": "joint",
                     "value": ov, "allow": 2 * cfg["leg_clear_mm"], "margin": 2 * cfg["leg_clear_mm"] / max(ov, 1e-9),
                     "basis": "n = 2 diametral change under the bushing load vs 2 x radial leg clearance (ASSUMPTION FIT)"})
    return rows


# ============================================================================ clamp tees (items 5, 8, 9)
@lru_cache(maxsize=None)
def clamp_units(tube_key: str, clamp_len: float) -> dict:
    """Stay under (a) the two clamp halves at preload: uniform pressure over +/- 80 deg each (2 x 10 deg split gaps;
    the printed halves conform, ASSUMPTION CLAMP-UNIFORM), 1 kN resultant per half; (b) the IM3 webbing loop (1 kN
    aft, uniform on the front half of the outer surface, 25 mm wide, just under the clamp); (c) a clamp-edge couple
    (1 kN on 8 mm at each clamp end, opposite sides). Ring part only (hoop) and bore change (n 0 + n 2 harmonics)."""
    from huntkit.fea.tube_solid import TubeFE, TubeModel
    st = BQ.STOCK[tube_key]
    L = 130.0
    x0, x1 = L / 2 - clamp_len / 2, L / 2 + clamp_len / 2
    m = TubeModel(L=L, od=st["od"], t=st["t"], h=2.0, refine_x=((x0 - 30, x1 + 4, 1.6),))
    fe = TubeFE(m)
    jaw = math.radians(80.0)
    fa_ = fe.patch_pressure(x0, x1, 0.0, jaw, 1000.0, "outer", uniform=True) + \
        fe.patch_pressure(x0, x1, math.pi, jaw, 1000.0, "outer", uniform=True)
    ua = fe.solve(fa_)
    ub = fe.solve(fe.patch_pressure(x0 - 27, x0 - 2, math.pi, math.pi / 2, 1000.0, "outer", uniform=True))
    fc = fe.patch_pressure(x0, x0 + 8, 0.0, math.radians(60), 1000.0, "outer") + \
        fe.patch_pressure(x1 - 8, x1, math.pi, math.radians(60), 1000.0, "outer")
    uc = fe.solve(fc)
    out = {}
    for k, u, (xa, xb) in (("jaws", ua, (x0, x1)), ("loop", ub, (x0 - 27, x0 - 2)), ("edge", uc, (x0, x1))):
        xs = np.linspace(xa + 2, xb - 2, 5)
        ovs = [fe.ovalisation(u, x) for x in xs]
        out[k] = {"hoop_peak": fe.surface_hoop(u, xa - 4, xb + 4),
                  "gap_loss_mm": max(o["min_gap_change_mm"] for o in ovs),
                  "oval_diam_mm": max(o["oval_diam_mm"] for o in ovs)}
    return out


def clamp_rows(glob: dict, cfg: dict) -> list[dict]:
    P = BQ.paht()
    rows = []
    Fb = cfg["clamp_preload_n"]
    ret = cfg["preload_retention"]
    mu = cfg["mu"]
    st = BQ.STOCK[cfg["stay"]]
    R = st["od"] / 2
    N_tot = 16 * Fb * ret / math.pi            # cosine jaw pressure, 2 bolts, both halves
    F_cap, T_cap = mu * N_tot, mu * N_tot * R
    for z in (330.0, 520.0):
        worst = (0.0, None)
        for tag in ("L", "R"):
            for k in (f"tee_{tag}{z:g}", f"tee_{tag}{z:g}|M"):
                v = np.asarray(glob["links"][k]["vec"], float)
                u = abs(v[2]) / F_cap + abs(v[5]) / T_cap
                if u > worst[0]:
                    worst = (u, glob["links"][k]["case"], v)
        rows.append({"item": "5", "row": f"tee clamp z {z:g}: slip (axial + torque about the stay)", "kind": "joint",
                     "value": worst[0], "allow": 1.0, "margin": 1.0 / worst[0],
                     "basis": f"mu {mu} x 16 Fb ret / pi = {F_cap:.0f} N / {T_cap / 1e3:.1f} N m (Fb {Fb:.0f} N, retention "
                              f"{ret} after PAHT creep, ASSUMPTIONS MU / CLAMP-PRELOAD / CREEP-RET, CL-1); {worst[1]}"})
    # pawl explicit: 1334 N x 1.5 (geometry.yaml crown_retention compression, ultimate) and 1001 N (C8)
    for P_pawl, lab in ((1334.0 * 1.5, "1334 N x 1.5 tall-load compression"), (1001.0, "1001 N C8 hipbelt-off")):
        u = (P_pawl / 2) / F_cap
        rows.append({"item": "5", "row": f"upper tee slip under the pawl {lab}", "kind": "joint", "value": u,
                     "allow": 1.0, "margin": 1 / u, "basis": "pawl at the bar centre, half to each tee along the stay"})
        ub = BQ.STOCK[cfg["ubar"]]
        I = math.pi / 64 * (ub["od"] ** 4 - (ub["od"] - 2 * ub["t"]) ** 4)
        Lb = 2 * (115.0 - 12.7 - 2.0)
        s = P_pawl * Lb / 8 / (I / (ub["od"] / 2)) * (ub["od"] * ub["t"] * math.pi / (ub["od"] * ub["t"] * math.pi - 2 * BQ.HOLE_D * ub["t"]))
        rows.append({"item": "5", "row": f"upper bar bending at the pawl housing, {lab}", "kind": "strength",
                     "value": s, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s,
                     "basis": f"fixed-fixed bar (clamp k_r 2e8 >> EI/L), P L / 8 over {Lb:.0f} mm, net section at the 2 holes"})
    # ovalisation with the leg inside
    U = clamp_units(cfg["stay"], cfg["clamp_len"])
    jaw_F = 2 * Fb / 1000.0                  # kN resultant per jaw at full preload
    d_pre = U["jaws"]["gap_loss_mm"] * jaw_F
    im3 = 1415.1
    edge = max(glob["links"][f"tee_{t}520|M"]["M"] for t in "LR") / (0.67 * cfg["clamp_len"]) / 1000.0
    d_lim = d_pre + U["loop"]["gap_loss_mm"] * im3 / 1000.0 + U["edge"]["gap_loss_mm"] * edge
    c0 = cfg["leg_clear_mm"]
    for lab, dd in (("preload", d_pre), ("limit (preload + IM3 hook 1415 N + bar-end couple)", d_lim)):
        rem = c0 - dd
        rows.append({"item": "5", "row": f"upper tee: leg radial clearance at {lab}", "kind": "joint", "value": dd,
                     "allow": c0 - 0.3, "margin": (c0 - 0.3) / max(dd, 1e-9) if c0 > 0.3 else 0.0,
                     "basis": f"bore inward {dd:.3f} mm (solid FE) vs nominal clearance {c0} mm - 0.3 required "
                              f"(remaining {rem:.2f} mm); ASSUMPTION FIT: bushing bore = leg OD + 0.80 mm"})
    sh = U["jaws"]["hoop_peak"] * jaw_F + U["loop"]["hoop_peak"] * im3 / 1000 + U["edge"]["hoop_peak"] * edge
    sb = BQ.FY_6061 / glob["strength"]["stays"]["sf"]
    s_lim = math.sqrt(sh ** 2 + sb ** 2 + sh * sb)
    rows.append({"item": "5", "row": "stay wall under the upper tee at limit (clamp + IM3 loop + couple + beam)",
                 "kind": "strength", "value": s_lim, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_lim,
                 "basis": f"solid FE hoop peaks summed {sh:.0f} MPa with the worst stay beam stress {sb:.0f} MPa (VM)"})
    # printed halves: clamp pressure in compression across the layers (printed split face down, layer normal y)
    p = 2 * Fb / (st["od"] * cfg["clamp_len"])
    rows.append({"item": "5", "row": "printed tee halves: clamp pressure (compression, layer normal)", "kind": "strength",
                 "value": p, "allow": P["z_hw"], "margin": P["z_hw"] / p,
                 "basis": "2 Fb / (D L) at full preload vs PAHT Z hot/wet B 19.66 MPa (tension value used for compression)"})
    rows.append({"item": "5", "row": "printed tee halves: sustained clamp pressure (creep rupture)", "kind": "creep",
                 "value": p, "allow": P["creep"] * P["z_hw"], "margin": P["creep"] * P["z_hw"] / p,
                 "basis": "creep_rupture_8h_40c_ratio 0.4 x 19.66"})
    # item 9: static cinch 150 N x 1e5 at the anchors
    cyc = 150.0 * 0.3                          # ASSUMPTION CINCH-ANGLE: 30 % of the aft cinch acts along the stay
    rows.append({"item": "9", "row": "static-cinch cycles 150 N x 1e5: clamp micro-slip (fretting) criterion", "kind": "fatigue",
                 "value": cyc, "allow": 0.5 * F_cap, "margin": 0.5 * F_cap / cyc,
                 "basis": "cyclic tangential <= 0.5 x retained slip capacity (no gross or partial slip, ASSUMPTION FRET-50)"})
    pc = (2 * Fb + 150.0) / (st["od"] * cfg["clamp_len"])
    rows.append({"item": "9", "row": "static-cinch cycles: PAHT clamp halves, compression fatigue", "kind": "fatigue",
                 "value": 150.0 / (st["od"] * cfg["clamp_len"]), "allow": P["fat"] * P["z_hw"],
                 "margin": P["fat"] * P["z_hw"] / (150.0 / (st["od"] * cfg["clamp_len"])),
                 "basis": f"cyclic part 150 N on the jaw (mean {pc:.1f} MPa) vs 0.30 x 19.66"})
    return rows


# ============================================================================ foot (item 7)
def foot_rows(glob: dict, cfg: dict) -> list[dict]:
    P = BQ.paht()
    rows = []
    st = BQ.STOCK[cfg["stay"]]
    W4 = 68.0 * BQ.G * 2.0 * 1.5                              # C4 set-down, factored
    plate = 38.1 ** 2
    rows.append({"item": "7", "row": "foot cup floor under the 38 x 38 6061 foot plate, C4 set-down", "kind": "strength",
                 "value": W4 / plate, "allow": P["z_hw"], "margin": P["z_hw"] / (W4 / plate),
                 "basis": f"{W4:.0f} N (68 kg x 2.0 g x 1.5) on 1452 mm2, layers in compression"})
    rim = math.pi * (st["od"] - st["t"]) * st["t"]
    rows.append({"item": "7", "row": "tube rim on the foot plate (Al on Al), C4", "kind": "strength",
                 "value": W4 / rim, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / (W4 / rim), "basis": "rim area pi D t"})
    # hinge pin (BL-041 tethered 5 mm 7075 pull-pin): eye 18 mm wide between the outer PAHT cheek and the stay wall
    F = 1018.8
    span, w_eye = 22.0, 18.0
    M = F / 2 * (span / 2 - w_eye / 4)
    s_pin = 32 * M / (math.pi * 5.0 ** 3)
    fy7 = 462.0
    rows.append({"item": "7", "row": "hinge pin z 60 (5 mm 7075-T6), bending", "kind": "strength", "value": s_pin,
                 "allow": fy7, "margin": fy7 / s_pin,
                 "basis": f"bag-on hinge {F:.0f} N factored (attach_system factored_n.hinge), simply supported {span:g} mm, "
                          f"eye load spread over {w_eye:g} mm; 7075-T6 S-basis yield 462"})
    t_ch = 12.0
    b_s = F / 2 / (5.0 * t_ch)
    rows.append({"item": "7", "row": "foot cup outer cheek: pin bearing (PAHT, compression)", "kind": "strength",
                 "value": b_s, "allow": P["z_hw"], "margin": P["z_hw"] / b_s,
                 "basis": f"F/2 on 5 x {t_ch:g} mm vs 19.66 (bearing, printed cheek layers in compression)"})
    Fw = F / 3.0 * BQ.G_WALK
    b_w = Fw / 2 / (5.0 * t_ch)
    rows.append({"item": "7", "row": "foot cup outer cheek: pin bearing fatigue", "kind": "fatigue",
                 "value": b_w, "allow": P["fat"] * P["z_hw"], "margin": P["fat"] * P["z_hw"] / b_w,
                 "basis": "walk 543 N, 0.30 x 19.66"})
    rows.append({"item": "7", "row": "US1 float cradle on the hinge pin (489 N factored)", "kind": "joint",
                 "value": 489.0, "allow": F, "margin": F / 489.0,
                 "basis": "same pin and cheek as the 1019 N hinge case (load_standard 4.3 float cradle)"})
    # T4c drop: 122 cm, empty pack, one foot; effective rigid mass = frame + crown, TPU foot pad as the contact spring
    m_eff, h = 1.6, 1.22
    k_pad = 60.0 * 1452 / 6.0                 # ASSUMPTION PAD: 6 mm Shore 95A TPU, E 60 MPa, on the foot plate area
    k_ply = 2.0e4                             # ASSUMPTION: 19 mm plywood on concrete, local, N/mm
    k = 1 / (1 / k_pad + 1 / k_ply)
    v = math.sqrt(2 * 9.81 * h)
    Fd = v * math.sqrt(k * 1e3 * m_eff)
    s_tube = Fd / (math.pi / 4 * (st["od"] ** 2 - (st["od"] - 2 * st["t"]) ** 2))
    rows.append({"item": "7", "row": "T4c 122 cm drop on one foot: stay end axial (estimate)", "kind": "strength",
                 "value": s_tube, "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s_tube,
                 "basis": f"F = v sqrt(k m): m {m_eff} kg rigid (frame + crown), TPU pad 6 mm + plywood, k {k:.0f} N/mm -> "
                          f"{Fd / 1e3:.1f} kN; test T4c decides (ASSUMPTION PAD / DROP-MASS)"})
    rows.append({"item": "7", "row": "T4c drop: cup floor under the foot plate (estimate)", "kind": "strength",
                 "value": Fd / plate, "allow": P["z_hw"] * 2.4, "margin": P["z_hw"] * 2.4 / (Fd / plate),
                 "basis": "abuse, no-collapse: compressive crush ~ 2.4 x Z tension hot/wet (ASSUMPTION COMP-Z, PA12-CF "
                          "compressive / Z-tensile; settled by the CF-1 cup crush coupon)"})
    return rows


# ============================================================================ fairleads and IM anchors (item 8)
def fairlead_rows(glob: dict, cfg: dict) -> list[dict]:
    """The 8 fairleads = hinge z 60 (pin, item 7) + IM1 z 190, IM2 z 330, IM3 z 520 webbing loops round the stay,
    both sides. A loop bears on the round 6061 stay (ring) and is located vertically by a printed collar that rests
    on metal (gusset top / tee clamp): PAHT in compression only."""
    P = BQ.paht()
    rows = []
    st = BQ.STOCK[cfg["stay"]]
    U = clamp_units(cfg["stay"], cfg["clamp_len"])
    # IM1: meat case lumbar strap anchor load (factored), from the load case
    from huntkit.fea.load_standard import ls1_cases
    m = BQ.build(cfg, 19.0)
    case = [c for c in ls1_cases() if c.name == "meat_straps"][0]
    L = case._loads(m)
    im1 = max(float(np.linalg.norm(L[n][:3])) for n in m["groups"]["strap_lumbar"]) * case.required_sf
    for lab, F, z in (("IM1 z 190 (loop on the stay above the gusset)", im1, 190.0),
                      ("IM2 z 330 (loop under the mid tee)", 403.3, 330.0),
                      ("IM3 z 520 (loop under the upper tee, bag-on hook case)", 1415.1, 520.0)):
        s = U["loop"]["hoop_peak"] * F / 1000.0
        rows.append({"item": "8", "row": f"{lab}: stay ring + local stress", "kind": "strength", "value": s,
                     "allow": BQ.FY_6061, "margin": BQ.FY_6061 / s,
                     "basis": f"{F:.0f} N factored (attach_system_results factored_n; IM1 from the C5 load case) as a 25 mm "
                              f"loop on the outer half, solid FE hoop (ring) stress; the beam part is in the stay rows"})
        sw = U["loop"]["hoop_peak"] * F / 3.0 * BQ.G_WALK / 1000.0 * 2.0
        fa = BQ.fat_allow_local(1.0)
        rows.append({"item": "8", "row": f"{lab}: fatigue", "kind": "fatigue", "value": sw, "allow": fa,
                     "margin": fa / sw, "basis": "walk = factored / 3 x 1.6; Kt 2 on the FE peak (webbing edge)"})
        # vertical share into the printed collar (friction share of the meat weight, C5): bearing on the collar
        Fv = 0.5 * 68.0 * BQ.G * 3.0 / 6.0
        pc = Fv / (math.pi / 4 * ((st["od"] + 8) ** 2 - st["od"] ** 2))
        rows.append({"item": "8", "row": f"{lab}: printed collar in compression", "kind": "strength", "value": pc,
                     "allow": P["z_hw"], "margin": P["z_hw"] / pc,
                     "basis": "vertical friction share (1 - floor 0.5) x P x 3.0 / 6 anchors on a 4 mm collar ring"})
    rows.append({"item": "8", "row": "float design / misuse IM3 eye 559 / 1142 N", "kind": "joint", "value": 1142.0,
                 "allow": 1415.1, "margin": 1415.1 / 1142.0,
                 "basis": "inside the bag-on IM3 hook case checked above (load_standard 4.3)"})
    return rows


# ============================================================================ spreader (item 4)
def spreader_b(cfg: dict | None = None, h: float = 4.0, log=print) -> dict:
    """``spreader.evaluate`` on the production sheet (sw110c7d) with the B81 supports patched in: round 1 in stays
    at x +/-115 on the straight B stay line, the cross tube (z 120) and the mid bar (z 330, 3/4 in) as beams, the
    gusset plates as raised lands, clips at z 166 / 260 / 400. The branch-frame supports (frame_top / sleeve_y /
    stay_r / build_plate) are patched for the call and restored."""
    from huntkit.gendesign import spreader as S
    from huntkit.fea.plate_grid import Beam, Spring
    from huntkit.materials import load
    cfg = {**BQ.CFG0, **(cfg or {})}
    cfg_default = lambda: cfg   # noqa: E731
    saved = {k: getattr(S, k) for k in ("build_plate", "frame_top", "sleeve_y", "stay_r")}
    R_st = BQ.STOCK[cfg_default()["stay"]]["od"] / 2
    yline = lambda z: -10.0 * np.asarray(z, float) / 530.0   # noqa: E731
    t_g = cfg_default()["gusset_t"]

    def frame_top_b(hh, x_lo=-124.0, x_hi=124.0, z_lo=S.Z_LO):
        xs = np.arange(x_lo, x_hi + 1e-6, hh)
        zs = np.arange(z_lo, S.Z_HI + 1e-6, hh)
        X, Z = np.meshgrid(xs, zs, indexing="ij")
        top = np.full(X.shape, np.nan)
        dx = np.abs(np.abs(X) - 115.0)
        on = dx <= R_st
        top[on] = yline(Z[on]) + np.sqrt(R_st ** 2 - dx[on] ** 2)
        for zb, rb in ((120.0, 12.7), (330.0, 9.525)):
            dz = np.abs(Z - zb)
            ok = (dz <= rb) & (np.abs(X) <= 115.0)
            v = yline(zb) + np.sqrt(np.clip(rb ** 2 - dz ** 2, 0, None))
            top = np.where(ok, np.fmax(top, v), top)
        # gusset back plates (aft face) z 75-165 at the stays and along the cross tube x 50-115
        g1 = (np.abs(np.abs(X) - 115.0) <= 12.7) & (Z >= 75.0) & (Z <= 165.0)
        g2 = (np.abs(X) >= 50.0) & (np.abs(X) <= 115.0) & (np.abs(Z - 120.0) <= 12.7)
        gy = yline(120.0) + R_st + 1.0 + t_g
        top = np.where(g1 | g2, np.fmax(np.nan_to_num(top, nan=-99), gy), top)
        return xs, zs, top

    def build_plate_b(opt, h=4.0, shape=None, version="v2", holes_mask=None, lands=True, tubes=None):
        from shapely.geometry import Point
        from shapely.prepared import prep
        shape = shape or S.outline_v2()
        minx, miny, maxx, maxy = shape.bounds
        x0 = np.floor(minx / h) * h
        nx = int(np.ceil((maxx - x0) / h))
        z_lo = np.floor(miny / h) * h
        ny = int(np.ceil((S.Z_HI - z_lo) / h))
        ps = prep(shape)
        pl = S.GridPlate(x0, z_lo, nx, ny, h, opt.lam.D)
        exy = pl.elem_xy()
        pl.active = np.array([[ps.contains(Point(*exy[i, j])) for j in range(ny)] for i in range(nx)])
        D = np.broadcast_to(opt.lam.D, (nx, ny, 3, 3)).copy()
        dbl = np.zeros((nx, ny), bool)
        if opt.doubler:
            dbl = S.doubler_mask(exy)
            D[dbl] = S.doubler_lam(opt).D
        pl.D = D
        info = {"shape": shape, "bead": np.zeros((nx, ny), bool), "h": h, "version": version, "doubler": dbl}
        xs, zs, top = frame_top_b(h, x0, x0 + nx * h, z_lo)
        nxy = pl.node_xy()
        i = np.clip(np.round((nxy[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1)
        j = np.clip(np.round((nxy[:, 1] - zs[0]) / h).astype(int), 0, len(zs) - 1)
        topn = top[i, j]
        actn = pl.active_nodes()
        y_crown = yline(nxy[:, 1]) + R_st
        rel = topn - y_crown
        keep_out = np.zeros(pl.nn, bool)
        for zf in S.FAIRLEADS_Z:
            keep_out |= (np.abs(np.abs(nxy[:, 0]) - S.STAY_X) <= S.FAIRLEAD_HALF_X + S.NOTCH_CLEAR) & \
                        (np.abs(nxy[:, 1] - zf) <= S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR)
        crown = actn & ~keep_out & (np.abs(np.abs(nxy[:, 0]) - S.STAY_X) <= h / 2 + 1e-6) & (nxy[:, 1] > 170)
        lift = float(np.nanmedian(np.where(crown, rel, np.nan)))
        info["bump_mm"] = float(np.nanmax(np.where(actn & ~keep_out, rel - lift, np.nan)))
        plane = y_crown + lift
        gap = np.maximum(plane - topn, 0.0)
        info.update(plane=plane, gap=gap, lift=float(lift))
        E = float(load("alu_6061_t6").require("youngs_modulus_mpa"))
        beams = {}
        for zb, sec in ((120.0, BQ.STOCK[cfg_default()["ctube"]]), (330.0, BQ.STOCK[cfg_default()["bar"]])):
            xb = np.arange(-S.STAY_X, S.STAY_X + 1e-6, h)
            I = math.pi / 64 * (sec["od"] ** 4 - (sec["od"] - 2 * sec["t"]) ** 4)
            bm = pl.add_beam(S.Beam(np.c_[xb, np.full_like(xb, zb)], E * I, tag=f"bar{zb:.0f}"))
            beams[zb] = (bm, xb)
        kinds = np.full(pl.nn, "", dtype=object)
        for n in np.nonzero(actn & np.isfinite(topn) & (gap < 30.0) & ~keep_out)[0]:
            x, z = nxy[n]
            g = max(float(gap[n]), 0.0)
            hit = None
            for zb, rb in ((120.0, 12.7), (330.0, 9.525)):
                if abs(z - zb) <= rb and abs(x) <= 115.0 - R_st:
                    hit = zb
            if hit is not None:
                bm, xb = beams[hit]
                k = int(np.argmin(np.abs(xb - x)))
                pl.springs.append(S.Spring(n, 0.0, g, other=bm.dof0 + 2 * k, tag="bar"))
                kinds[n] = "bar"
            else:
                pl.springs.append(S.Spring(n, 0.0, g, tag="stay" if abs(x) >= 100.0 else "rigid"))
                kinds[n] = "stay" if abs(x) >= 100.0 else "rigid"
        for zc in S.CLIP_Z + S.PAD_Z:
            cw = S.CLIP_W_BY_Z.get(zc, S.CLIP_W)
            sel = actn & (np.abs(nxy[:, 1] - zc) <= cw / 2 + 1e-6) & (np.abs(nxy[:, 0]) >= S.STAY_X - 4.0)
            for n in np.nonzero(sel)[0]:
                if zc in S.CLIP_Z:
                    pl.springs.append(S.Spring(n, S.clip_k(cw) / max(int(sel.sum()), 1), 0.0, sense=-1.0, tag="clip"))
                if zc in S.PAD_Z:
                    pl.springs.append(S.Spring(n, 0.0, S.LAND_FIT, tag="stay"))
        tubes = S.EDGE_TUBES if tubes is None else tubes
        info["tubes"] = []
        for (zt, od, idd) in tubes:
            jrow = int(round((zt - pl.y0) / h))
            row = actn & (np.abs(nxy[:, 1] - (pl.y0 + jrow * h)) < 1e-6)
            nodes_t = np.nonzero(row)[0]
            nodes_t = nodes_t[np.argsort(nxy[nodes_t, 0])]
            if len(nodes_t) < 3:
                continue
            xt = nxy[nodes_t, 0]
            tb = pl.add_beam(S.Beam(np.c_[xt, np.full_like(xt, zt)], S.tube_EI(od, idd), clamp_start=False,
                                    clamp_end=False, tag=f"tube{zt:.0f}"))
            for k, n in enumerate(nodes_t):
                pl.springs.append(S.Spring(int(n), 0.0, 0.0, other=tb.dof0 + 2 * k, unilateral=False, tag="tube_bond"))
            info["tubes"].append({"beam": tb, "z": zt, "od": od, "id": idd, "len": float(xt[-1] - xt[0]),
                                  "mass_g": S.tube_mass_g(od, idd, float(xt[-1] - xt[0]) + h)})
        info["kinds"] = kinds
        info["beams"] = {}
        return pl, info

    try:
        S.build_plate = build_plate_b
        S.frame_top = frame_top_b
        S.sleeve_y = yline
        S.stay_r = lambda z: np.full_like(np.asarray(z, float), R_st)
        opt = {o.key: o for o in S.options()}[S.PRODUCTION_KEY]
        r = S.evaluate(opt, h=h, step=None)
    finally:
        for k, v in saved.items():
            setattr(S, k, v)
    keys = ("sf_fpf", "fpf_where", "sf_fatigue", "sandwich_sf_min", "clear_walk_min", "clear_fact_min",
            "clear_fact_lean_min", "skin_peak_kpa", "skin_where", "w_fact_max", "meat_force_fact_n", "meat_force_by_tag",
            "clip_lift_max_n", "plane_lift_mm", "checks", "passes", "passes_sheet")
    out = {k: r.get(k) for k in keys}
    out.update(sheet=opt.key, h=h)
    return out


def spreader_rows(sp: dict) -> list[dict]:
    rows = []
    for k, lab, kind in (("sf_fpf", "spreader sheet first-ply (factored)", "strength"),
                         ("sf_fatigue", "spreader sheet fatigue (FI <= 0.5 at 1.6 g)", "fatigue"),
                         ("sandwich_sf_min", "spreader sandwich local (bone patch)", "strength")):
        v = sp.get(k)
        if v is not None:
            rows.append({"item": "4", "row": lab, "kind": kind, "value": 1 / v, "allow": 1.0, "margin": float(v),
                         "basis": f"spreader.evaluate({sp['sheet']}, h {sp['h']:g}) on the B81 supports"})
    rows.append({"item": "4", "row": "spreader clearance to the skin at the factored case (>= 0 mm)", "kind": "info",
                 "value": sp.get("clear_fact_min"), "allow": 0.0,
                 "margin": None, "basis": f"walk clearance {sp.get('clear_walk_min'):.1f} mm (>= 3 mm mesh rule); "
                                          f"skin peak {sp.get('skin_peak_kpa'):.1f} kPa (<= 14)"})
    return rows


def cfg_default() -> dict:
    return dict(BQ.CFG0)
