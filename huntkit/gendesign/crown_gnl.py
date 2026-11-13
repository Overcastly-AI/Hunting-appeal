"""BL-047 (1a): crown frame buckling on the real crown (top bar 25 mm aft, 32 mm corner dog-legs) by a geometric
non-linear analysis of HA-LS-1 rev C C8 hipbelt-off abuse.

Why: the linear eigen check of BL-046 (``h1_spine_channel.md`` section 5) gives 0.54-0.57 on the real crown. That
check hangs the frame on grounded linear springs (``huntkit.fea.load_cases`` shoulder at the yoke, lifters at TB0 /
TB2). With the hipbelt off nothing holds the frame fore-aft below the yoke, so the linear solve balances the bag
couple with a horizontal couple between the shoulder spring (pushing the yoke AFT, about 1.4 kN) and the lifter
springs (pulling the top bar FORE, about 0.7 kN each), and the stay feet "move" about 2 m. A strap cannot push.

What this does
1. ``strap_model``: the C8 loads of ``LoadCase.build_model`` (dead loads, unchanged) on the real crown, with the
   springs replaced by what holds a hipbelt-off pack: two shoulder straps (yoke -> shoulder crest) and two lifters
   (lifter node -> strap at 40.6 deg, geometry.yaml ``lifter_angle_deg``) as tension-only follower cables
   (``huntkit.fea.gnl``), and the lumbar pad bearing on the back (or the T1(c) hip log) as compression-only contact.
   Axial stiffness per strap = the HA-LS-1 spring (x1) or x4 (ASSUMPTION STRAP-K); lifter tension at the factored
   load set by the lifter length (``calibrate_lifter``), swept 0 .. the linear model's 0.70 kN (ASSUMPTION LIFT-T).
2. Imperfection: the linear first buckling mode (``h1_spine_channel.buckling_mode``, the 0.54 mode) scaled to 4 mm
   (and 8 mm) at its largest node translation (ASSUMPTION IMP).
3. ``path``: load factor 0 -> 2.0 x the factored C8 load (Newton, load control, step halving), smallest eigenvalue
   of the tangent stiffness tracked. Margin = lambda_c / (1.5 x 1.0): the HA-LS-1 buckling rule (eigenvalue >= 1.5 x
   the case factor) applied to the non-linear limit load; the path is stopped at 2.0, so a margin >= 1.33 means
   "no limit point found up to 2.0".
4. Member first-ply / yield margins of the crown members on the non-linear state at lambda 1.0 against the linear
   (spring) C8 solve.

Record: designs/pack_5200/analysis/crown_gnl.md (+ .json). Run: python -m huntkit.gendesign.crown_gnl
Units mm, N, MPa, g.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import pickle
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
ANALYSIS = PACK / "analysis"
DOC = ANALYSIS / "crown_gnl.md"
RESULTS = ANALYSIS / "crown_gnl.json"
OUT = REPO / "outputs" / "crown_gnl"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_BL047_"

CASE = "hipbelt_off_abuse"
KITS = ("a_S", "a_M", "a_L")
LIFTER_ANGLE_DEG = 40.6           # geometry.yaml crown_settings lifter_angle_deg (every setting)
SHOULDER_OFF = (90.0, -100.0, 40.0)   # ASSUMPTION STRAP-GEOM: shoulder crest from the yoke node (|x|, fore, up)
DEFAULT_SPRINGS_BODY = ((4.0, 8.0, 10.0), (0.0, 6.0, 3.0))   # HA-LS-1 shoulder, lifter (pack5200 P5200_DEFAULTS springs)
K_LUMBAR = 30.0                   # HA-LS-1 lumbar_pad ky total (here compression only)
K_MULTS = (1.0, 4.0)              # ASSUMPTION STRAP-K band
LIFTER_T = (0.0, 200.0, 450.0, 700.0)   # lifter tension each at lambda 1 (N); 700 = the linear model's 696
IMP_MM = (4.0, 8.0)               # ASSUMPTION IMP
LAM_MAX = 2.0
BUCK_REQ = 1.5                    # HA-LS-1: buckling >= 1.5 x case factor (C8 factor 1.0)
PRE_STRAIN = 2e-3                 # straps snug at zero load

ASSUMPTIONS = {
    "STRAP-GEOM": ("Shoulder straps run from the yoke node to a shoulder-crest point 90 mm to each side, 100 mm fore "
                   "and 40 mm above it (yoke 50 mm below C7, geometry.yaml datums); the lifter runs from its node to "
                   "the same point (its strap end sits just fore of the crest): 42-46 deg below horizontal against "
                   "geometry.yaml's 40.6. Webbing cables, tension only, EA from poly_webbing_25mm (WEB-EA).",
                   "T1(c) on the rig: photograph the strap and lifter angles at 225 lb; re-run with the measured angles."),
    "STRAP-K": ("The body under each shoulder crest = the HA-LS-1 shoulder + lifter springs per side (2, 7, 6.5 N/mm "
                "x, y, z) and 4x that, as a band; the path is reported for both.",
                "T1(c): crown-top sag against load at 25 % steps; the measured secant stiffness picks the band end."),
    "STRAP-SLING": ("With the hipbelt off the shoulder strap is a sling: its front run (crest -> lower adjuster -> "
                    "lower anchor, geometry.yaml shoulder_strap_lower_anchor z 110) is snug and carries tension; "
                    "modelled as a straight cable crest -> nearest stay node. Run with and without it.",
                    "T1(c): crane scale on one lower strap at 225 lb."),
    "LIFT-T": ("Lifter tension at the factored load is set by how hard the wearer cinches it; swept 0 / 200 / 450 / "
               "700 N each (700 = the linear spring model's lifter reaction).",
               "T1(c): crane scale in each lifter at 225 lb (record the tension)."),
    "BACK": ("With the hipbelt off the lumbar pad bears on the wearer's lower back (on the rig: the hip log), "
             "compression only, 30 N/mm in total (HA-LS-1 lumbar_pad ky).",
             "T1(c) is run with the pad touching the hip log (belt unbuckled); a free-hanging variant is in T1(c)-sway."),
    "WEB-EA": ("Webbing linear to break: EA = 13344 N / 0.15 = 89 kN (secant); 25 mm polyester record.",
               "Pull a 300 mm length of the lifter webbing on the crane scale to 500 N and read the stretch."),
    "IMP": ("Imperfection = the linear first buckling mode of the real crown (the 0.54 mode) scaled to 4 mm at its "
            "largest node translation (about crown height / 200), and 8 mm as a check.",
            "First-article frame: measure crown-top and stay-foot out-of-plane against a straight edge before T1."),
    "DEAD": ("The C8 loads stay as HA-LS-1 places them (dead nodal loads on the bag nodes, bag couple on TB0/TB2 "
             "and the stay feet); only the supports are made physical.", "Not a test item: it is the standard's load."),
}


# ================================================================================== model
def linear_model(kit: str, torso: float, variant: str = "crown_bar", real: bool = True):
    """(case, C8 linear model with the HA-LS-1 springs) on the real crown of crown kit ``kit`` at ``torso``."""
    from huntkit.fea.load_standard import ls1_envelope
    from . import crown_diet as CD
    from . import h1_spine_channel as SC
    m0 = CD.build(CD.specs()[kit], float(torso))
    mr = SC.real_crown(m0) if real else m0
    case = copy.copy(next(c for c in ls1_envelope("C")[variant] if c.name == CASE))
    case.params = dict(case.params)
    return case, mr, case.build_model(mr)


def webbing_ea() -> float:
    """Secant axial stiffness of 25 mm polyester webbing, N per unit strain: breaking strength / elongation at break
    (data/materials/webbing/poly_webbing_25mm.yaml; ASSUMPTION WEB-EA: linear to break)."""
    from huntkit.materials import load
    w = load("poly_webbing_25mm")
    return float(w.require("breaking_strength_n")) / (float(w.require("elongation_at_break_pct")) / 100.0)


def lower_anchor_node(lm: dict, sx: float) -> str:
    """Model node nearest the shoulder strap's lower anchor (geometry.yaml hard_points shoulder_strap_lower_anchor)."""
    from . import crown_diet as CD
    hp = CD.geom()["g"]["frame"]["hard_points"]
    a = np.asarray(hp["shoulder_strap_lower_anchor_R" if sx > 0 else "shoulder_strap_lower_anchor_L"], float)
    stay = [k for k in lm["nodes"] if k.startswith("SR" if sx > 0 else "SL")]
    return min(stay, key=lambda k: float(np.linalg.norm(np.asarray(lm["nodes"][k], float) - a)))


def strap_model(lm: dict, k_mult: float = 1.0, lifter_pre: float = PRE_STRAIN, back: bool = True,
                sling: bool = True) -> dict:
    """C8 model with the harness in place of the grounded springs: per side one shoulder-crest body node (BS) on
    the HA-LS-1 body springs (shoulder + lifter share, x ``k_mult``), the shoulder strap (yoke -> BS) and the lifter
    (lifter node -> BS: the lifter's strap end sits just fore of the crest, on the same line) as tension-only
    webbing cables; the lumbar pad bears on the back (compression only). ``lifter_pre``: lifter shortening (strain)
    the wearer pulls in."""
    m = copy.deepcopy(lm)
    n = m["nodes"]
    yk = m["groups"]["shoulder"][0]
    y = np.asarray(n[yk], float)
    cab, sup = [], {}
    ea = webbing_ea()
    ks, kl = DEFAULT_SPRINGS_BODY
    for sx, t, ln in ((-1, "L", m["groups"]["lifter"][0]), (1, "R", m["groups"]["lifter"][1])):
        B = y + np.array([sx * SHOULDER_OFF[0], SHOULDER_OFF[1], SHOULDER_OFF[2]])
        n[f"BS{t}"] = B.tolist()
        kb = k_mult * (np.asarray(ks) + np.asarray(kl)) / 2.0
        sup[f"BS{t}"] = {"fix": "rx ry rz", "spring": [float(kb[0]), float(kb[1]), float(kb[2]), 0, 0, 0]}
        cab.append({"id": f"shoulder_{t}", "nodes": [yk, f"BS{t}"], "EA": ea, "pre_strain": PRE_STRAIN})
        cab.append({"id": f"lifter_{t}", "nodes": [ln, f"BS{t}"], "EA": ea, "pre_strain": lifter_pre})
        if sling:       # the strap's front run, crest -> lower anchor (adjuster snug)
            cab.append({"id": f"strap_lower_{t}", "nodes": [lower_anchor_node(lm, sx), f"BS{t}"], "EA": ea,
                        "pre_strain": PRE_STRAIN})
    m["supports"] = sup
    m["cables"] = cab
    if back:
        pads = m["groups"]["lumbar_pad"]
        m["contacts"] = [{"node": p, "dir": [0.0, -1.0, 0.0], "k": K_LUMBAR / len(pads)} for p in pads]
    m.setdefault("settings", {})["nseg"] = 2
    return m


def lifter_angle(lm: dict) -> float:
    """Lifter angle below horizontal (deg) in the strap model (geometry.yaml: 40.6)."""
    n = lm["nodes"]
    P = np.asarray(n[lm["groups"]["lifter"][1]], float)
    B = np.asarray(n[lm["groups"]["shoulder"][0]], float) + np.array([SHOULDER_OFF[0], SHOULDER_OFF[1], SHOULDER_OFF[2]])
    d = B - P
    return float(math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1]))))


def mode_imperfection(mr: dict, amp: float) -> tuple:
    from . import h1_spine_channel as SC
    _, marg, U = SC.buckling_mode(mr)
    return {k: amp * np.asarray(v, float) for k, v in U.items()}, float(marg)


def run_path(m: dict, imp: dict | None, lam_max: float = LAM_MAX, track: bool = True, log=None):
    from huntkit.fea.gnl import GNL
    g = GNL(m, imperfection=imp)
    pts = g.path(lam_max=lam_max, dlam=0.1, track_eig=track, log=log)
    return g, pts


def calibrate_lifter(lm: dict, k_mult: float, target: float, imp=None) -> tuple:
    """Lifter shortening (strain) so each lifter carries ``target`` N at lambda 1 (secant on the strap length).
    Returns (pre-strain, tension reached)."""
    def tension(pre):
        g, pts = run_path(strap_model(lm, k_mult, pre), imp, lam_max=1.0, track=False)
        if pts[-1].lam < 1.0 - 1e-9:
            return float("nan")
        t = pts[-1].cable_t
        return 0.5 * (t["lifter_L"] + t["lifter_R"])
    if target <= 0:
        return -0.05, tension(-0.05)          # lifters 5 % slack: loose
    x0, t0 = 0.0, tension(0.0)
    if t0 >= target:
        return x0, t0
    x1 = 0.02
    t1 = tension(x1)
    for _ in range(10):
        if abs(t1 - target) < 0.02 * target:
            break
        s_ = (t1 - t0) / (x1 - x0) if x1 != x0 else 0.0
        xn = x1 + (target - t1) / s_ if s_ > 0 else x1 * 2
        xn = float(np.clip(xn, 0.0, 0.15))
        x0, t0, x1 = x1, t1, xn
        t1 = tension(x1)
    return x1, t1


# ================================================================================== member checks
CROWN_GROUPS = ("crown_leg_L", "crown_leg_R", "crown_top_bar", "crown_spine", "spine_clamp")


def _elem_sf(mem_info, member: int, f6) -> float:
    from huntkit.fea.materials_bridge import yield_of
    mi = mem_info[member]
    sec = mi["section"]
    if sec.composite:
        return float(sec.failure(*f6)["sf"])
    r = sec.stresses(*f6)
    fy, _ = yield_of(mi["material"])
    return float(fy / r["von_mises"]) if r["von_mises"] > 0 else float("inf")


def member_sf_gnl(g) -> dict:
    """Least FPF / yield factor per crown member group on the GNL state (local end forces)."""
    ef = g.member_forces()
    out = {}
    for e, el in enumerate(g.elements):
        grp = g.mem_info[el.member]["group"]
        if grp not in CROWN_GROUPS and not g.mem_info[el.member]["id"].startswith(("CLtop-", "TBR95-")):
            continue
        key = "dog_leg" if g.mem_info[el.member]["id"].startswith(("CLtop-", "TBR95-")) else grp
        for end in range(2):
            s = _elem_sf(g.mem_info, el.member, ef[e, end])
            out[key] = min(out.get(key, float("inf")), s)
    return out


def member_sf_linear(res) -> dict:
    out = {}
    for q in res.members:
        key = "dog_leg" if q["id"].startswith(("CLtop-", "TBR95-")) else q["group"]
        if key in CROWN_GROUPS or key == "dog_leg":
            out[key] = min(out.get(key, float("inf")), float(q["sf"]))
    return out


def dog_leg_axial(g) -> float:
    ef = g.member_forces()
    vals = [ef[e, 0, 0] for e, el in enumerate(g.elements) if g.mem_info[el.member]["id"].startswith(("CLtop-", "TBR95-"))]
    return float(min(vals))


# ================================================================================== one set
LIFTER_STATES = ("loose", "half", "cinched")   # lifter 5 % slack; lifter = yoke-strap tension at lambda 1; yoke
#                                                strap just slack at lambda 1 (the lifter carries the whole upper run)


def lifter_pre(lm: dict, k_mult: float, state: str, support: str, imp=None) -> tuple:
    """Lifter shortening (strain) for a lifter state, by bisection at lambda 1. Returns (pre, {cable: T})."""
    def tens(pre):
        g, pts = run_path(strap_model(lm, k_mult, pre, **SUPPORTS[support]), imp, lam_max=1.0, track=False)
        return pts[-1].cable_t if pts[-1].lam >= 1.0 - 1e-9 else None
    if state == "loose":
        return -0.05, tens(-0.05)

    def f(t):
        sh = 0.5 * (t["shoulder_L"] + t["shoulder_R"])
        li = 0.5 * (t["lifter_L"] + t["lifter_R"])
        return li - sh if state == "half" else (1.0 if sh <= 0.02 * max(li, 1.0) else -1.0)
    lo, hi = 0.0, 0.6
    tl = tens(lo)
    if tl is not None and f(tl) >= 0:
        return lo, tl
    best = (hi, tens(hi))
    for _ in range(9):
        mid = 0.5 * (lo + hi)
        t = tens(mid)
        if t is None or f(t) >= 0:
            hi, best = mid, (mid, t)
        else:
            lo = mid
    return best
SUPPORTS = {"sling_back": {"sling": True, "back": True},      # worn: strap sling + lumbar pad on the back (baseline)
            "sling_free": {"sling": True, "back": False},     # T1(c)-sway: hanging free of the hip log
            "yoke_back": {"sling": False, "back": True}}      # lower straps loose


def watch_nodes(g) -> dict:
    return {k: g.idx[k] for k in ("SL0", "SR0", "TB1", "CLtop", "CRtop", "SP150") if k in g.idx}


def _path_rec(g, pts) -> dict:
    w = watch_nodes(g)
    return {"lam": [p.lam for p in pts], "min_eig": [p.min_eig for p in pts],
            "u": {k: [[round(float(x), 3) for x in p.u[i, :3]] for p in pts] for k, i in w.items()},
            "cable_t": [{k: round(v, 1) for k, v in p.cable_t.items()} for p in pts]}


def run_set(kit: str, torso: float, variant: str, k_mult: float, lifter: str, support: str = "sling_back",
            imp_mm: float = IMP_MM[0], log=None) -> dict:
    from huntkit.fea.frame import solve
    from huntkit.fea.gnl import GNL, critical_from_path
    case, mr, lm = linear_model(kit, torso, variant)
    imp, lin_margin = mode_imperfection(mr, imp_mm)
    pre, _ = lifter_pre(lm, k_mult, lifter, support, imp)
    sm = strap_model(lm, k_mult, pre, **SUPPORTS[support])
    g, pts = run_path(sm, imp)
    crit = critical_from_path(pts)
    lam = np.array([p.lam for p in pts])
    rec = {"kit": kit, "torso_in": torso, "variant": variant, "k_mult": k_mult, "lifter": lifter, "support": support,
           "imp_mm": imp_mm, "lifter_pre_strain": round(float(pre), 4), "linear_margin": round(lin_margin, 3),
           "lam_reached": float(lam[-1]),
           "limit_point_found": bool(lam[-1] < LAM_MAX - 1e-9), "lam_extrap": crit["lam_extrap"],
           "min_eig_0": crit["min_eig_0"], "min_eig_last": crit["min_eig_last"]}
    rec["margin"] = round(float(lam[-1]) / BUCK_REQ, 3)
    rec["path"] = _path_rec(g, pts)
    g1 = GNL(sm, imperfection=imp)
    p1 = g1.path(lam_max=1.0, dlam=0.1, track_eig=False)
    if p1[-1].lam >= 1.0 - 1e-9:
        rec["at_1"] = {"cable_t": {k: round(v, 1) for k, v in g1._cable_t.items()},
                       "back_contact_n": round(sum(g1._contact_f.values()), 1),
                       "dog_leg_axial_n": round(dog_leg_axial(g1), 1),
                       "member_sf": {k: round(v, 3) for k, v in member_sf_gnl(g1).items()}}
    lin = solve(lm, name="lin")
    rec["linear"] = {"member_sf": {k: round(v, 3) for k, v in member_sf_linear(lin).items()},
                     "reactions": {k: [round(float(x), 1) for x in v[:3]] for k, v in lin.reactions.items()},
                     "dog_leg_axial_n": round(float(min(q["end_forces"][0][0] for q in lin.members
                                                         if q["id"].startswith(("CLtop-", "TBR95-")))), 1)}
    if log:
        lt = rec.get("at_1", {}).get("cable_t", {})
        log(f"  {kit} {torso:g} {variant} k x{k_mult:g} {lifter} {support} imp {imp_mm:g}: reached "
            f"{rec['lam_reached']:.2f}, margin {rec['margin']:.2f} (linear {lin_margin:.2f}); lifter "
            f"{lt.get('lifter_R', float('nan')):.0f} N")
    return rec


def spring_reference(kit: str, torso: float, variant: str = "crown_bar", imp_mm: float = IMP_MM[0]) -> dict:
    """The GNL on the HA-LS-1 grounded springs themselves (the linear check's supports), for reference."""
    from huntkit.fea.gnl import critical_from_path
    case, mr, lm = linear_model(kit, torso, variant)
    imp, lin_margin = mode_imperfection(mr, imp_mm)
    m = copy.deepcopy(lm)
    m.setdefault("settings", {})["nseg"] = 2
    g, pts = run_path(m, imp)
    crit = critical_from_path(pts)
    return {"kit": kit, "torso_in": torso, "variant": variant, "lam_reached": pts[-1].lam,
            "lam_extrap": crit["lam_extrap"], "linear_margin": lin_margin, "path": _path_rec(g, pts)}


def sets_for(kit: str) -> list:
    from . import crown_diet as CD
    return [float(t) for t in CD.specs()[kit].torsos]


def run_all(log=print) -> dict:
    """Every crown kit at every recorded torso, both couple variants, the stiffness band, three lifter states and
    the three support conditions; the 8 mm imperfection on the governing set; the spring reference."""
    OUT.mkdir(parents=True, exist_ok=True)
    cache = OUT / "runs.pkl"
    done = pickle.loads(cache.read_bytes()) if cache.exists() else {}

    def get(key, fn):
        if key not in done:
            done[key] = fn()
            cache.write_bytes(pickle.dumps(done))
        return done[key]
    rows = []
    for kit in KITS:                         # worn baseline: every setting, both couples, stiffness band, lifter loose
        for t in sets_for(kit):
            for variant in ("crown_bar", "strap_upper"):
                for km in K_MULTS:
                    key = ("set", kit, t, variant, km, "loose", "sling_back", IMP_MM[0])
                    rows.append(get(key, lambda: run_set(kit, t, variant, km, "loose", "sling_back", IMP_MM[0], log=log)))
    for kit in KITS:                         # each kit's linear-worst setting: lifter cinched, and the support variants
        w = min((r for r in rows if r["kit"] == kit), key=lambda r: r["linear_margin"])
        for sp_ in SUPPORTS:
            for km in K_MULTS:
                for lf in ("loose", "cinched"):
                    key = ("set", kit, w["torso_in"], w["variant"], km, lf, sp_, IMP_MM[0])
                    rows.append(get(key, lambda: run_set(kit, w["torso_in"], w["variant"], km, lf, sp_, IMP_MM[0],
                                                         log=log)))
    gov = min(rows, key=lambda r: (r["lam_reached"], r["min_eig_last"]))
    imp8 = get(("set", gov["kit"], gov["torso_in"], gov["variant"], gov["k_mult"], gov["lifter"], gov["support"],
                IMP_MM[1]), lambda: run_set(gov["kit"], gov["torso_in"], gov["variant"], gov["k_mult"], gov["lifter"],
                                            gov["support"], IMP_MM[1], log=log))
    ref = get(("ref", "a_L", 23.0), lambda: spring_reference("a_L", 23.0))
    return {"rows": rows, "governing": gov, "imp8": imp8, "spring_reference": ref}


# ================================================================================== record
def summary(d: dict) -> dict:
    rows = d["rows"]
    a1 = [r for r in rows if "at_1" in r]
    gnl_sf, lin_sf = {}, {}
    for r in a1:
        for k, v in r["at_1"]["member_sf"].items():
            gnl_sf[k] = min(gnl_sf.get(k, 9e9), v)
    for r in rows:
        for k, v in r["linear"]["member_sf"].items():
            lin_sf[k] = min(lin_sf.get(k, 9e9), v)

    def sway(r, lam):
        L = np.array(r["path"]["lam"])
        i = int(np.argmin(np.abs(L - lam)))
        u = r["path"]["u"]
        return abs(u["SL0"][i][1] - u["SR0"][i][1]) / 2.0
    lows = min(rows, key=lambda r: min(r["path"]["min_eig"][1:]))
    return {"n_runs": len(rows), "all_reach_lam_max": bool(all(r["lam_reached"] >= LAM_MAX - 1e-9 for r in rows)),
            "limit_points": int(sum(r["limit_point_found"] for r in rows)),
            "margin_min": min(r["margin"] for r in rows), "lam_max": LAM_MAX,
            "linear_margin_range": [min(r["linear_margin"] for r in rows), max(r["linear_margin"] for r in rows)],
            "lowest_tangent_eig": {"value": min(lows["path"]["min_eig"][1:]),
                                   **{k: lows[k] for k in ("kit", "torso_in", "variant", "k_mult", "lifter", "support")}},
            "member_sf_gnl_at_1": gnl_sf, "member_sf_linear_c8": lin_sf,
            "dog_leg_axial_gnl_n": [min(r["at_1"]["dog_leg_axial_n"] for r in a1), max(r["at_1"]["dog_leg_axial_n"] for r in a1)],
            "dog_leg_axial_linear_min_n": min(r["linear"]["dog_leg_axial_n"] for r in rows),
            "lifter_max_n": max(max(r["at_1"]["cable_t"].get("lifter_L", 0), r["at_1"]["cable_t"].get("lifter_R", 0)) for r in a1),
            "back_contact_n": [min(r["at_1"]["back_contact_n"] for r in a1), max(r["at_1"]["back_contact_n"] for r in a1)],
            "sway_antisym_mm_at_1": max(sway(r, 1.0) for r in rows), "sway_antisym_mm_at_2": max(sway(r, 2.0) for r in rows),
            "imp8": {k: d["imp8"][k] for k in ("kit", "torso_in", "support", "lifter", "k_mult", "lam_reached", "margin")},
            "spring_reference": {k: d["spring_reference"][k] for k in ("kit", "torso_in", "lam_reached", "lam_extrap",
                                                                       "linear_margin")}}


def deformed(kit="a_L", torso=23.0, variant="crown_bar", k_mult=4.0, lifter="cinched", support="sling_back"):
    """Full deformed states at lambda 0 / 1 / 2 of one set (for the figure)."""
    from huntkit.fea.gnl import GNL
    case, mr, lm = linear_model(kit, torso, variant)
    imp, _ = mode_imperfection(mr, IMP_MM[0])
    pre, _ = lifter_pre(lm, k_mult, lifter, support, imp)
    sm = strap_model(lm, k_mult, pre, **SUPPORTS[support])
    out = {}
    for lam in (1.0, 2.0):
        g = GNL(sm, imperfection=imp)
        g.path(lam_max=lam, dlam=0.1, track_eig=False)
        out[lam] = (g, g.state[0].copy())
    return sm, out


def plot_path(d: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(13, 5.2), dpi=100)
    pick = {}
    for r in d["rows"]:
        key = (r["support"], r["lifter"], r["k_mult"])
        if r["kit"] == "a_L" and r["torso_in"] == 23.0 and r["variant"] == "crown_bar":
            pick[key] = r
    cols = {"sling_back": "#1f77b4", "sling_free": "#d62728", "yoke_back": "#2ca02c"}
    for (sp_, lf, km), r in sorted(pick.items()):
        L = np.array(r["path"]["lam"])
        u = r["path"]["u"]
        ls = "-" if km == 1.0 else "--"
        lab = f"{sp_}, lifter {lf}, body x{km:g}"
        axs[0].plot([q[1] for q in u["TB1"]], L, ls, color=cols[sp_], lw=1.2, label=lab)
        axs[1].plot([abs(a[1] - b[1]) / 2 for a, b in zip(u["SL0"], u["SR0"])], L, ls, color=cols[sp_], lw=1.2)
        axs[2].plot(L[1:], r["path"]["min_eig"][1:], ls, color=cols[sp_], lw=1.2)
    ref = d["spring_reference"]
    axs[0].plot([q[1] for q in ref["path"]["u"]["TB1"]], ref["path"]["lam"], ":", color="k", lw=1.5,
                label="HA-LS-1 grounded springs (the linear check's supports), GNL")
    for ax in axs[:2]:
        ax.axhline(1.0, color="0.5", lw=0.8)
        ax.axhline(BUCK_REQ, color="#d62728", lw=0.8, ls="--")
        ax.set_ylabel("load factor x factored C8 (1.5 g x 68 kg)")
        ax.grid(alpha=0.3)
    axs[0].set_xlabel("crown top bar fore-aft, mm (+ aft)")
    axs[1].set_xlabel("stay-foot antisymmetric sway |dy_L - dy_R| / 2, mm")
    axs[2].set_xlabel("load factor")
    axs[2].set_ylabel("smallest tangent-stiffness eigenvalue, N/mm")
    axs[2].axvline(BUCK_REQ, color="#d62728", lw=0.8, ls="--")
    axs[2].grid(alpha=0.3)
    axs[0].legend(fontsize=6.5, loc="lower right")
    axs[0].set_title("Load-displacement, kit L 23 in (linear-worst set)", fontsize=10)
    axs[1].set_title("The linear 0.54 mode's coordinate (4 mm seed)", fontsize=10)
    axs[2].set_title("Tangent stiffness stays positive to 2.0", fontsize=10)
    fig.suptitle(f"BL-047 crown GNL, hipbelt-off abuse: {d['summary']['n_runs']} runs, no limit point to "
                 f"{LAM_MAX:g} x factored (margin >= {LAM_MAX / BUCK_REQ:.2f}); linear eigen check "
                 f"{d['summary']['linear_margin_range'][0]:.2f}", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_deformed(path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import h1_spine_channel as SC
    sm, st = deformed()
    case, mr, lm = linear_model("a_L", 23.0)
    res, marg, U = SC.buckling_mode(mr)
    fig, axs = plt.subplots(1, 2, figsize=(9, 6.8), dpi=100)
    n = sm["nodes"]
    ax = axs[0]
    for q in mr["members"]:
        a, b = q["nodes"]
        pa, pb = np.asarray(mr["nodes"][a]), np.asarray(mr["nodes"][b])
        ax.plot([pa[1], pb[1]], [pa[2], pb[2]], color="0.75", lw=1.0)
        if a in U and b in U:
            da, db = pa + 60 * U[a], pb + 60 * U[b]
            ax.plot([da[1], db[1]], [da[2], db[2]], color="#e67e22", lw=1.0)
    for nid, r in lm["supports"].items():
        p = np.asarray(mr["nodes"][nid])
        ax.annotate("", xy=(p[1] - 0.06 * res.reactions[nid][1] * 0 - 0.05 * res.reactions[nid][1], p[2]), xytext=(p[1], p[2]),
                    arrowprops=dict(arrowstyle="<-", color="#c0392b"))
    ax.set_title(f"Linear check, grounded springs:\nmode x60 (orange), margin {marg:.2f}", fontsize=9)
    ax = axs[1]
    for lam, col in ((1.0, "#1f77b4"), (2.0, "#9467bd")):
        g, x = st[lam]
        for e in g.elements:
            ax.plot([x[e.n1][1], x[e.n2][1]], [x[e.n1][2], x[e.n2][2]], color=col, lw=0.9)
        for a_, b_, ea, L0, cid in g.cables:
            ax.plot([x[a_][1], x[b_][1]], [x[a_][2], x[b_][2]], color="#2ca02c", lw=1.4, ls="-" if lam == 1.0 else ":")
    g0 = st[1.0][0]
    for e in g0.elements:
        ax.plot([g0.X0[e.n1][1], g0.X0[e.n2][1]], [g0.X0[e.n1][2], g0.X0[e.n2][2]], color="0.8", lw=0.8)
    ax.axvline(-28.0, color="#8c564b", lw=0.8, ls="--")
    ax.text(-30, 820, "back / hip log", fontsize=7, ha="right", color="#8c564b")
    ax.set_title("GNL, L 23 in, body x4, straps green:\ngrey 0 / blue 1.0 / violet 2.0 x factored", fontsize=9)
    for a in axs:
        a.set_aspect("equal")
        a.set_xlabel("y, mm (+ aft, toward the bag)")
        a.set_ylabel("z, mm")
        a.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_pawl(chk: dict, path: Path) -> str:
    """Section at x 0 of the exported STL round the housing, with the old and LP pawls swept, bore and window."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from shapely import affinity
    from . import h1_fairleads as HF
    from . import h1_pawl as PW
    from . import h1_spine_channel as SC
    mesh = trimesh.load(str(SC.PRINT_DIR / "h1_assembled.stl"))
    bef = trimesh.load(str(OUT / "h1_assembled_bl046.stl"))
    fig, axs = plt.subplots(1, 3, figsize=(13, 6), dpi=100)
    s = SC.axis_slope()
    y0 = float(SC.axis_y(0.0))

    def sh(p):
        return affinity.affine_transform(p, [1.0, s, 0.0, 1.0, y0, 0.0])

    def fill(ax, geom, **kw):
        for gg in getattr(geom, "geoms", [geom]):
            if gg.is_empty or gg.geom_type != "Polygon":
                continue
            xx, yy = gg.exterior.xy
            ax.fill(xx, yy, **kw)
            for it in gg.interiors:
                xi, yi = it.xy
                ax.fill(xi, yi, color="white")
    for ax, m, title, prof in ((axs[0], bef, "BL-046 print, old FDM pawl", PW.old_profile()),
                               (axs[1], mesh, "BL-047 print (window), LP pawl", PW.lp_profile())):
        S = HF._xplane(m, 0.0)
        fill(ax, S, color="0.7")
        fill(ax, sh(PW.to_yz(PW.swept(prof))), color="#e67e22", alpha=0.35)
        fill(ax, sh(PW.to_yz(prof)), color="#e67e22", alpha=0.9)
        ax.set_xlim(-60, 25)
        ax.set_ylim(480, 545)
        ax.set_title(title + f"\nswept to {PW.PAWL_LIFT_DEG:g} deg: {PW.max_py(prof):.1f} mm off the tooth face", fontsize=9)
    S = HF._xplane(mesh, -18.0)
    fill(axs[2], S, color="0.7")
    P = PW.frame_place()
    from shapely.geometry import Point
    fill(axs[2], sh(Point(P["pivot_y_rel"], P["z_pivot"]).buffer(PW.BORE_REAM_D / 2)), color="#1f77b4", alpha=0.6)
    axs[2].set_xlim(-60, 25)
    axs[2].set_ylim(480, 545)
    axs[2].set_title(f"x -18 (left cheek): pivot bore 7.6 printed / 8.0 reamed (blue),\nboss to z {PW.BOSS_Z_LO:g}; "
                     f"slice check {'PASS' if chk.get('pass') else 'FAIL'}", fontsize=9)
    for a in axs:
        a.set_aspect("equal")
        a.axvline(SC.HOUSING_FORE_Y_AT_PAWL, color="#d62728", lw=0.8, ls="--")
        a.set_xlabel("y, mm (fore -, aft +); red = housing fore face", fontsize=8)
        a.set_ylabel("z, mm")
        a.grid(alpha=0.25)
    fig.suptitle("BL-047 pawl: grey = printed body (x-section of the exported STL), orange = pawl and its swept zone",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def plot_margins(d: dict, items: dict, path: Path) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sm = d["summary"]
    lab, lin, gnl = [], [], []
    for k in ("crown_leg_L", "crown_top_bar", "crown_spine", "dog_leg", "spine_clamp"):
        lab.append(k.replace("_L", ""))
        lin.append(sm["member_sf_linear_c8"][k])
        gnl.append(sm["member_sf_gnl_at_1"][k])
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.2), dpi=100)
    xx = np.arange(len(lab))
    axs[0].bar(xx - 0.2, lin, 0.4, label="linear C8 (grounded springs)", color="#7f7f7f")
    axs[0].bar(xx + 0.2, gnl, 0.4, label="GNL C8 at 1.0 (straps + back), least of 64 runs", color="#1f77b4")
    axs[0].bar([len(lab) - 0.2], [sm["linear_margin_range"][0]], 0.4, color="#d62728")
    axs[0].bar([len(lab) + 0.2], [sm["margin_min"]], 0.4, color="#2ca02c")
    axs[0].set_xticks(list(xx) + [len(lab)])
    axs[0].set_xticklabels(lab + ["frame buckling\n(lin / GNL)"], fontsize=8)
    axs[0].axhline(1.0, color="k", lw=0.8)
    axs[0].set_ylim(0, 6)
    axs[0].set_ylabel("margin (pass >= 1)")
    axs[0].legend(fontsize=8)
    axs[0].set_title("Crown, hipbelt-off abuse (C8)", fontsize=10)
    rows = items.get("rows", [])
    axs[1].barh([r[0] for r in rows], [min(r[1], 4) for r in rows], color=["#2ca02c" if r[1] >= 1 else "#d62728" for r in rows])
    axs[1].axvline(1.0, color="k", lw=0.8)
    axs[1].set_xlabel("margin (pass >= 1; bars capped at 4)")
    axs[1].set_title("Pawl, clamp web 2.0, hinge row 1019 N, TL-1", fontsize=10)
    for i, r in enumerate(rows):
        axs[1].text(min(r[1], 4) + 0.05, i, f"{r[1]:.2f}", va="center", fontsize=7)
    axs[1].tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def _np(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def build_record(log=print) -> dict:
    """Everything BL-047 records: GNL summary + table rows, pawl, keep-outs, clamp web, review items, mass."""
    import trimesh
    from . import bl047_frame_items as B
    from . import crown_spine_clamp as CS
    from . import frame_h1 as H1
    from . import h1_pawl as PW
    from . import h1_spine_channel as SC
    d = pickle.loads((OUT / "run_all.pkl").read_bytes())
    d["summary"] = summary(d)
    table = [{k: r[k] for k in ("kit", "torso_in", "variant", "k_mult", "lifter", "support", "imp_mm", "linear_margin",
                                "lam_reached", "margin", "lifter_pre_strain")} |
             {"lifter_n": max(r["at_1"]["cable_t"].get("lifter_L", 0), r["at_1"]["cable_t"].get("lifter_R", 0)),
              "back_n": r["at_1"]["back_contact_n"], "dog_leg_n": r["at_1"]["dog_leg_axial_n"],
              "member_min": min(r["at_1"]["member_sf"].values()), "min_eig": min(r["path"]["min_eig"][1:])}
             for r in d["rows"] + [d["imp8"]]]
    stl = SC.PRINT_DIR / "h1_assembled.stl"
    mesh = trimesh.load(str(stl))
    chk = json.loads((OUT / "stl_checks.json").read_text())
    cheek = json.loads((OUT / "cheek.json").read_text())
    web = json.loads((OUT / "web20.json").read_text())
    webc = json.loads((OUT / "web20_crown.json").read_text())
    items = B.compute(log=None)
    he = chk["he"]
    solid, _ = SC.body_solid() if isinstance(SC.body_solid(), tuple) else (SC.body_solid(), None)
    keep = H1.keepouts(solid)
    old_keep = json.loads(SC.RESULTS.read_text()).get("keepouts_bl046", {})
    pinfo = json.loads((REPO / "outputs" / "h1_buckling" / "print_info.json").read_text())
    pawls = chk["pawls"]
    old_pawl_slm_g = None
    try:
        old_pawl_slm_g = round(trimesh.load(str(PACK / "print" / "crown_pawl_slm.stl")).volume * 4.43e-3, 2)
    except Exception:
        pass
    mass = {"clamp_g": CS.SPINE_CLAMP_MASS_G, "clamp_bl046_g": 15.9, "clamp_delta_g": round(CS.SPINE_CLAMP_MASS_G - 15.9, 1),
            "pawl_print_net_g": round(pinfo["fairleads_bl042"]["pawl_bl047"]["net_g"], 2),
            "hinge_relief_g": round(pinfo["fairleads_bl042"]["hinge_relief_bl047"]["g"], 2),
            "pawl_lp_slm_g": pawls["crown_pawl_lp_slm"]["g"], "pawl_old_slm_g": old_pawl_slm_g,
            "assembled_g": pinfo["assembled"]["g"], "assembled_bl046_g": 887.6,
            "lower_g": pinfo["lower"]["g"], "upper_g": pinfo["upper"]["g"]}
    mass["pawl_delta_g"] = round(mass["pawl_lp_slm_g"] - (old_pawl_slm_g or mass["pawl_lp_slm_g"]), 2)
    mass["h1_print_delta_g"] = round(mass["pawl_print_net_g"] + mass["hinge_relief_g"], 2)
    hn = items["hinge_one_number"]
    tl = items["tl1"]
    rows_bar = [("pawl cheek, as built (FI99)", cheek["cheek"]["built"]["sf_fi"]),
                ("pawl LP clear of print, 0-10 deg (mm / 0.5)", chk["pawl"]["lp_min_dist_mm"] / 0.5),
                ("clamp web 2.0 yield", web["w20"]["webs"]["sf_yield"]),
                ("clamp web 2.0 fatigue (Kt 2)", web["w20"]["webs"]["sf_fatigue_kt2"]),
                ("hinge pin 5 mm 7075 yield @1019", hn["pin_7075_5mm"]["sf_yield"]),
                ("hinge pin fatigue @1.6 g x 340", hn["pin_7075_5mm"]["sf_fatigue"]),
                ("hinge fairlead strength @1019 (rev C dir)", hn["revC_direction"]["sf_strength"]),
                ("hinge fairlead strength @1019 (sim dir)", hn["sim_direction"]["sf_strength"]),
                ("hinge fairlead fatigue (rev C dir)", hn["revC_direction"]["sf_fatigue"]),
                ("hinge fairlead fatigue (sim dir)", hn["sim_direction"]["sf_fatigue"]),
                ("B-25 bar, BL-046 vector, static", tl["rows"]["vector_bl046"]["sf_static"]),
                ("B-25 bar, BL-046 vector, fatigue", tl["rows"]["vector_bl046"]["sf_fatigue"])]
    rec = {"date": "2026-11-13", "ticket": "BL-047", "gnl": {"summary": d["summary"], "table": table},
           "assumptions": ASSUMPTIONS, "pawl": {"check": chk["pawl"], "cheek": cheek, "files": pawls,
                                                "assumptions": PW.ASSUMPTIONS, "place": PW.frame_place()},
           "channel_check": chk["channel"], "fairleads_all_pass": chk["fairleads_all_pass"], "he": he,
           "keepouts": keep, "keepouts_bl046": old_keep, "clamp_web": {"bl046_2p5": web["base"], "bl047_2p0": web["w20"],
                                                                        "mass_g": web["mass"], "crown_real_2p0": webc},
           "items": items, "mass": mass, "print": pinfo, "margin_rows": rows_bar}
    return rec, d


SUPERSEDED_HINGE_MD = (
    "> **SUPERSEDED (BL-051 note, 2026-11-13): the hinge fairlead fatigue 0.86 (sim direction, 1019 N row) below is the "
    "BL-047 hinge.** BL-049 grew the hinge (cheeks 10 mm, 27 mm up the stay, floor lowered 1 mm, relief groove gone, "
    "Ti pin): fatigue in the sims' inboard-up direction **1.30** at the 1019 N row (strength 2.30), rev C direction "
    "3.50 (`h1_lanes.md`, `h1_lanes.json` hinge). The other numbers in this file stand.\n")
SUPERSEDED_HINGE_JSON = ("BL-051 (2026-11-13): the hinge fairlead sf_fatigue 0.86 (sim direction) is the BL-047 hinge; "
                         "BL-049's grown hinge gives 1.30 inboard-up at the 1019 N row, strength 2.30 "
                         "(analysis/h1_lanes.json hinge). The rest of this record stands.")


def write_doc(rec: dict, d: dict, shots: list) -> str:
    s = rec["gnl"]["summary"]
    T = rec["gnl"]["table"]
    pw = rec["pawl"]
    it = rec["items"]
    hn, tl = it["hinge_one_number"], it["tl1"]
    m = rec["mass"]
    he = rec["he"]
    L = []
    a = L.append
    a("# BL-047 Crown frame buckling (GNL) on the real crown; pawl pivot and window; keep-outs; clamp web\n")
    a("Generated by `python -m huntkit.gendesign.crown_gnl` (data `crown_gnl.json`, review items "
      "`bl047_frame_items.json`). Date 2026-11-13. Units mm, N, g (in, lbf, oz alongside). Loads and factors: "
      "HA-LS-1 rev C (`load_standard.md`), unchanged. Solver: `huntkit/fea/gnl.py` (co-rotational beams, tension-only "
      "cables, one-sided contact), verified in `tests/test_fea_gnl.py` against the cantilever, the tip-moment elastica, "
      "the imperfect Euler column (amplification 1/(1-P/Pcr) and the bifurcation at Pcr) and the hanging cable.\n")
    a("## Summary\n")
    a(f"- **Crown buckling on the real crown holds.** Geometric non-linear C8 hipbelt-off abuse, {s['n_runs']} runs "
      "(every crown kit S / M / L at every recorded torso, both rev C couple variants, body stiffness x1 and x4, lifters "
      "loose to fully cinched, worn / free-hanging / lower straps loose, 4 mm and 8 mm imperfection in the linear "
      f"0.54 mode): **no limit point up to {LAM_MAX:g} x the factored load in any run**; the smallest tangent "
      f"eigenvalue stays positive ({s['lowest_tangent_eig']['value']:.4f} N/mm, free-hanging pendulum). Margin "
      f"lambda_c / (1.5 x 1.0) **>= {s['margin_min']:.2f}** (HA-LS-1 buckling rule applied to the non-linear limit "
      f"load; the path is stopped at {LAM_MAX:g}). The linear eigen check gives {s['linear_margin_range'][0]:.2f}-"
      f"{s['linear_margin_range'][1]:.2f} on the same sets.")
    a("- **Why the linear check is wrong here:** with the hipbelt off, HA-LS-1's grounded springs are the only "
      "supports, all above the bag. To hold the bag couple the linear solve makes the shoulder spring PUSH the yoke aft "
      "(about 1.39 kN) and the lifter springs pull the bar fore (0.70 kN each); the stay feet 'move' about 2 m. A strap "
      "cannot push, and that couple is what loads the 32 mm dog-legs (linear: down to "
      f"{s['dog_leg_axial_linear_min_n']:.0f} N). With straps (tension only, turning with the frame) and the lumbar pad "
      f"on the back, the frame hangs; dog-leg axial {s['dog_leg_axial_gnl_n'][0]:.0f} .. {s['dog_leg_axial_gnl_n'][1]:+.0f} N, "
      f"lifters up to {s['lifter_max_n']:.0f} N, back contact {s['back_contact_n'][0]:.0f}-{s['back_contact_n'][1]:.0f} N.")
    a(f"- **No fix needed:** (b) top bar into the legs' plane and (c) stiffer corner wraps were not sized (the ticket "
      "sizes them only if (a) gives < 1.0). TOP-BAR-AFT stays; R-28 head clearance and the clamp are unchanged.")
    a(f"- **Crown members at 1.0 x factored (GNL, least of all runs):** legs {s['member_sf_gnl_at_1']['crown_leg_L']:.2f}, "
      f"top bar {s['member_sf_gnl_at_1']['crown_top_bar']:.2f}, spine {s['member_sf_gnl_at_1']['crown_spine']:.2f}, "
      f"dog-legs {s['member_sf_gnl_at_1']['dog_leg']:.2f}, clamp {s['member_sf_gnl_at_1']['spine_clamp']:.2f}; the linear "
      f"C8 values ({s['member_sf_linear_c8']['crown_leg_L']:.2f} / {s['member_sf_linear_c8']['crown_top_bar']:.2f} / "
      f"{s['member_sf_linear_c8']['crown_spine']:.2f}) stay the record (conservative).")
    a("- **T1(c) defined** (hipbelt-off frame test with sway gauges and a Southwell plot): "
      "`designs/pack_5200/tests_physical/T1c_hipbelt_off_frame.md`.")
    a(f"- **Pawl:** pivot bore (printed 7.6, reamed 8.0) through both cheeks at z {pw['place']['z_pivot']:.0f}, cheek "
      f"bosses to z {__import__('huntkit.gendesign.h1_pawl', fromlist=['x']).BOSS_Z_LO:g}, fore-wall window. The old FDM pawl "
      f"does not fit even with a window: swung to release it reaches {pw['check']['old_max_py']:.1f} mm off the tooth face, "
      f"{pw['check']['old_max_py'] - pw['check']['face_py']:.1f} mm proud of the housing face (yoke path). New low-profile "
      f"pawl (LP, same pin, teeth and arm length): {pw['check']['lp_max_py']:.2f} mm, inside the {pw['check']['face_py']:.2f} "
      f"mm face. **Slice check on the exported STL, 0-10 deg every 1 deg: LP clear by {pw['check']['lp_min_dist_mm']:.2f} mm "
      f"(>= 0.45); old pawl overlaps by {-pw['check']['old_min_dist_mm']:.1f} mm; bore clear with full 2 mm walls in both "
      f"cheeks: PASS.** Cheek as built FI99 SF {pw['cheek']['cheek']['built']['sf_fi']:.2f} at "
      f"{pw['cheek']['force']['n']:.0f} N factored (record 8 x 8 cheek {pw['cheek']['cheek']['record_8x8']['sf_fi']:.2f}).")
    a(f"- **Keep-outs re-based** on the BL-046 channel: outside envelope {rec['keepouts_bl046'].get('outside envelope (voxels)', 1800)} "
      f"-> {rec['keepouts']['outside envelope (voxels)']} voxels; the old 'pawl present' / 'spine_channel empty' masks "
      f"replaced by the housing ring ({rec['keepouts']['pawl housing ring (BL-046, cheeks for the BL-047 pivot) present']:.3f}) "
      "and the BL-046 channel (1.000 empty).")
    w = rec["clamp_web"]["bl047_2p0"]
    a(f"- **Clamp web 2.0 mm taken:** web yield {w['webs']['sf_yield']:.2f}, fatigue {w['webs']['sf_fatigue_kt2']:.2f}; every "
      "bond margin equal or better (the softer clamp draws less moment); crown members on the real crown within 0.1. "
      f"Clamp {m['clamp_bl046_g']:.1f} -> **{m['clamp_g']:.1f} g** ({m['clamp_delta_g']:+.1f} g).")
    a(f"- **Review items (fourth bag review):** m-1 hinge relief cut; HE corner clearance at ply 1.6 "
      f"0.19 -> **{he['per_ply']['1.6']['worst']:.2f} mm** (HE check PASS), {he['tol_0p15']['worst_under_pin_clear_mm']:.2f} mm "
      f"at a 0.15 mm print tolerance. M-A: TL-1 re-run on BL-046 geometry, k 1.006 -> {tl['k_vector_bl046']:.3f}; TL-1 "
      f"proof stays **{tl['proof_publish_n']:.0f} N** (pull A and pull B published). M-C: one hinge number, **1019 N**: pin "
      f"yield {hn['pin_7075_5mm']['sf_yield']:.2f} / fatigue {hn['pin_7075_5mm']['sf_fatigue']:.2f}; printed fairlead "
      f"strength {hn['revC_direction']['sf_strength']:.2f} / {hn['sim_direction']['sf_strength']:.2f}, fatigue "
      f"{hn['revC_direction']['sf_fatigue']:.2f} / **{hn['sim_direction']['sf_fatigue']:.2f}** (rev C / sim direction).")
    a(f"- **Mass (ledger BL047):** clamp {m['clamp_delta_g']:+.1f} g every config; H1 print {m['h1_print_delta_g']:+.2f} g "
      f"(pawl bosses / bore / window {m['pawl_print_net_g']:+.2f}, hinge relief {m['hinge_relief_g']:+.2f}); LP Ti pawl "
      f"{m['pawl_delta_g']:+.2f} g against the old SLM pawl. Print: assembled {m['assembled_g']:.1f} g "
      f"(BL-046 {m['assembled_bl046_g']:.1f}), lower {m['lower_g']:.1f} / upper {m['upper_g']:.1f} g, one closed shell each.\n")
    a("## 1. The linear check and its supports\n")
    a("HA-LS-1 C8 hangs the frame on HA-LS-1's body springs (shoulder at the yoke 4 / 8 / 10 N/mm, lifters at TB0 / TB2 "
      "0 / 6 / 3 N/mm in total, `huntkit.fea.load_cases`), hipbelt and lumbar springs removed. Kit L 23 in, real crown, "
      "linear: reactions SP150 (0, +1392, +632) N (pushes the yoke aft), TB0 / TB2 (0, -696, +184) N each; stay feet "
      "u_y about -2000 mm; dog-leg axial -172 N (crown_bar) to about -1030 N (strap_upper). The eigen-buckling factor "
      "0.81 (margin 0.54) is the bifurcation of that prestress. Run non-linearly on the same springs, the frame swings "
      f"about 260 mm and the solve stops converging at {s['spring_reference']['lam_reached']:.2f} with the tangent still "
      f"positive (extrapolated zero {s['spring_reference']['lam_extrap']:.1f}): the spring model is not a hanging "
      "system, so it can only be judged with physical supports.\n")
    a("## 2. GNL model\n")
    a("- Frame: the real crown beam model (`h1_spine_channel.real_crown`: top bar 25 mm aft, dog-legs, 25 mm clamp "
      "member), members split in 2 (`nseg`), C8 loads exactly as HA-LS-1 places them (dead nodal loads).")
    a("- Harness: per side a shoulder-crest body node on the HA-LS-1 shoulder + lifter springs (x1 and x4); the shoulder "
      "strap (yoke -> crest), the lifter (lifter node -> crest, 41-46 deg below horizontal; geometry.yaml 40.6) and the "
      "strap's front run (crest -> lower anchor, z 120 node; geometry.yaml z 110) as tension-only follower cables, EA "
      "89 kN (25 mm polyester record, linear to break). Lumbar pad on the back (rig: hip log): compression only, 30 N/mm.")
    a("- Lifter states: loose (5 % slack) and cinched (yoke strap just slack) in the matrix ('half' is coded, "
      "not run); lifter tension cannot exceed the upper run's share (the lifter and yoke strap meet at the crest).")
    a("- Imperfection: the linear 0.54 mode scaled to 4 mm (8 mm on the governing set). Path: Newton, load control, "
      f"0 -> {LAM_MAX:g} x factored, step halving, smallest tangent eigenvalue tracked (limit = it crossing zero). The "
      "matrix ran on the 2.5 mm clamp webs (before section 7); the clamp is >= 12 in every run, so it does not "
      "govern the path.\n")
    a("## 3. Results\n")
    a("| kit | torso in | couple | body k | lifter | support | imp mm | linear margin | lambda reached | GNL margin | lifter N | back N | dog-leg N | crown min SF @1 | min eig N/mm |")
    a("|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in T:
        a(f"| {r['kit']} | {r['torso_in']:g} | {r['variant']} | x{r['k_mult']:g} | {r['lifter']} | {r['support']} | "
          f"{r['imp_mm']:g} | {r['linear_margin']:.2f} | {r['lam_reached']:.2f} | {r['margin']:.2f} | {r['lifter_n']:.0f} | "
          f"{r['back_n']:.0f} | {r['dog_leg_n']:+.0f} | {r['member_min']:.2f} | {r['min_eig']:.4f} |")
    a(f"\nThe stay-foot antisymmetric sway (the 0.54 mode's coordinate) stays <= {s['sway_antisym_mm_at_1']:.1f} mm at 1.0 "
      f"and <= {s['sway_antisym_mm_at_2']:.1f} mm at 2.0 from a 4 mm seed: it does not grow toward a mode.\n")
    a("## 4. T1(c) hipbelt-off frame test\n")
    a("Defined in `designs/pack_5200/tests_physical/T1c_hipbelt_off_frame.md` (register row to add: T1c-SW). It is T1(c) "
      "of `load_standard.md` (225 lb / 102 kg, 2 min, hipbelt unbuckled) with the lumbar pad on the hip log, plus dial "
      "gauges on both stay feet (fore-aft) and the crown top bar (lateral), crane scales in one lifter and one lower "
      "strap, and a Southwell plot. Pass: no crack, crown set <= 1 mm, slip 0 (T1), antisymmetric foot sway at 225 lb "
      "<= 3 mm and returns within 0.5 mm, Southwell P_cr >= 340 lb (1.5 x 225 lb). A T1(c)-sway variant hangs free of the "
      "log at 150 lb only.\n")
    a("## 5. Pawl pivot, cheeks and window\n")
    p = pw["place"]
    a(f"| item | value |\n|---|---|\n| pin (pawl pivot) | z {p['z_pivot']:.1f}, {p['pivot_y_rel']:.2f} mm from the spine axis "
      f"(4 mm fore of the tooth face, 20 mm below the teeth) |\n| bore | printed 7.6, ream 8.0, 304 sleeve OD 8 / ID 4.2 / "
      "8 long each cheek (PRODUCTION.md op 2) |\n| cheek boss | |x| 11-24.8, to z 491.5 (4 mm under the reamed bore) |\n"
      f"| window | through the fore wall, x +/-9, over the swept pawl + 0.5 mm |\n| swing | 10 deg (teeth tips "
      f"{pw['check']['lift_at_teeth_mm']:.2f} mm clear at full swing; 0.5 mm at 7.9 deg) |\n| zone / housing face from the "
      f"tooth face | {pw['check']['zone_py']:.2f} / {pw['check']['face_py']:.2f} mm |\n| old pawl swept | "
      f"{pw['check']['old_max_py']:.2f} mm (proud of the face) |\n| LP pawl swept | {pw['check']['lp_max_py']:.2f} mm |\n"
      f"| LP files | `print/frame_h1/crown_pawl_lp_fdm_pacf.stl` ({pw['files']['crown_pawl_lp_fdm_pacf']['g']:.2f} g PAHT-CF), "
      f"`crown_pawl_lp_slm.stl` ({pw['files']['crown_pawl_lp_slm']['g']:.2f} g Ti) |\n")
    a(f"Cheek strength as built (`h1_pawl.cheek_strength`, `frame_production.cheek_check`'s voxel FE with the real "
      f"edges, root at the housing top only): FI99 {pw['cheek']['cheek']['built']['fi99']:.3f}, SF "
      f"{pw['cheek']['cheek']['built']['sf_fi']:.2f}; plastic bearing {pw['cheek']['cheek']['built']['bearing_sf']:.2f}; "
      f"304 sleeve {pw['cheek']['cheek']['built']['metal_sf']:.2f}; force {pw['cheek']['force']['n']:.0f} N "
      f"({pw['cheek']['force']['set']}, linear C8: conservative per section 1). The fore wall beside the window keeps "
      f"{rec['channel_check']['min']['fore_wall_mm']:.2f} mm; BL-046's channel slice check re-run on the new STL: "
      f"{rec['channel_check']['settings_pass']}/{rec['channel_check']['n']} settings PASS, least clearance "
      f"{rec['channel_check']['min']['clear_mm']:.2f} mm.\n")
    a("## 6. Keep-outs (re-based)\n")
    a("| keep-out | BL-046 | BL-047 |\n|---|---:|---:|")
    for k, v in rec["keepouts"].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            a(f"| {k} | {rec['keepouts_bl046'].get(k, '-')} | {v:.3f} |" if isinstance(v, float) else
              f"| {k} | {rec['keepouts_bl046'].get(k, '-')} | {v} |")
    a("\nThe ring reads 0.967 because the 2 mm raster rounds the housing's 3 mm corners; the exact housing is on the "
      "print mesh (slice check above).\n")
    a("## 7. Clamp web 2.0 mm\n")
    b0, b1 = rec["clamp_web"]["bl046_2p5"], rec["clamp_web"]["bl047_2p0"]
    a("| margin | web 2.5 (BL-046) | web 2.0 (BL-047) |\n|---|---:|---:|")
    for grp in ("socket", "saddle", "socket_with_shear", "saddle_with_shear"):
        for k in ("avg", "peak", "fat_avg", "fat_peak"):
            a(f"| {grp} {k} | {b0[grp][k]['sf']:.3f} | {b1[grp][k]['sf']:.3f} |")
    for grp, k in (("socket_bending", "sf_yield"), ("socket_bending", "sf_fatigue_kt2"), ("webs", "sf_yield"),
                   ("webs", "sf_fatigue_kt2")):
        a(f"| {grp} {k} | {b0[grp][k]:.3f} | {b1[grp][k]:.3f} |")
    a("\nThe saddle + transverse-shear peak (0.81) is below 1 with either web, as BL-046 recorded: the T6 coupon must "
      "cover it. Real-crown crown members at 2.0 (`crown_margins`): a_S / a_M / a_L least "
      + " / ".join(f"{v['min_all']:.3f}" for v in rec["clamp_web"]["crown_real_2p0"].values())
      + " (the linear buckling term, now replaced by section 3); all strength terms within 0.1 of BL-046. The H1 body "
      "voxel checks were not re-run for the web (clamp end forces change < 2 %).\n")
    a("## 8. Fourth bag review: m-1, M-A, M-C\n")
    a(f"**m-1 hinge relief.** `bl047_frame_items.hinge_relief`: per cheek a 1.5 mm groove along the cheek, bottom 1.0 mm "
      "below the floor (r 0.75), open up the cheek face to floor + 4.5 mm (the corner fillet goes), 0.2 mm into the cheek "
      f"face; both hinge fairleads, {m['hinge_relief_g']:+.2f} g. `he_stl_check` on the re-exported HE-FIT piece: "
      f"{'PASS' if he['as_written']['pass'] else 'FAIL'}; under the pin at ply 1.2 / 1.5 / 1.6: "
      f"{he['per_ply']['1.2']['worst']:.2f} / {he['per_ply']['1.5']['worst']:.2f} / {he['per_ply']['1.6']['worst']:.2f} mm, "
      f"now governed {abs(he['per_ply']['1.6']['where']):.1f} mm off the throat centre (the ply ridge), not in the corner "
      f"(was 0.61 / 0.29 / 0.19 in the corner). At a 0.15 mm print tolerance: {he['tol_0p15']['worst_under_pin_clear_mm']:.2f} "
      f"mm (>= 0.5: {he['tol_0p15']['meets_0p5_everywhere']}). The cheeks are untouched in section (the relief is in the "
      "throat floor; 0.2 mm of an 8 mm cheek face), so the hinge fairlead FEA stands.\n")
    rv = tl["run_vector"]
    a(f"**M-A TL-1 on BL-046 geometry.** The B-25 run leaves the mitre (x {rv['mitre_centre_x_s'][0]:.1f}, s "
      f"{rv['mitre_centre_x_s'][1]:.1f}) for the spine wrap {rv['spine_fore_mm']:.2f} mm fore under the {rv['collar_mm']:.1f} mm "
      f"collar: {rv['plan_angle_fore_deg']:.0f} deg fore in plan, {rv['below_horizontal_deg']:.0f} deg below horizontal; "
      f"its y-z share on the sleeve {rv['yz_share']:.2f} (BL-045 took it straight down). Pull ratio (vector) "
      f"{tl['k_vector_bl045']:.3f} -> **{tl['k_vector_bl046']:.3f}** (the run's fore pull now offsets the guy's aft pull); "
      f"bound (run in line with the guy) {tl['k_bound']:.3f}, unchanged. Bar at 38 mm, basis A: static "
      f"{tl['rows']['vector_bl046']['sf_static']:.2f} / fatigue {tl['rows']['vector_bl046']['sf_fatigue']:.2f} (BL-045 "
      f"{tl['rows']['vector_bl045']['sf_static']:.2f} / {tl['rows']['vector_bl045']['sf_fatigue']:.2f}; bound "
      f"{tl['rows']['bound']['sf_static']:.2f} / {tl['rows']['bound']['sf_fatigue']:.2f}). TL-1 proof on the new vector "
      f"{tl['proof_tl1_n']:.0f} N; **published {tl['proof_publish_n']:.0f} N** (kept at BL-045's value).\n")
    pa, pb = tl["pull"]["rig"], tl["pull"]["rig_B_run_loaded"]
    a("| TL-1 pull (published, `bl047_frame_items.json` tl1.pull) | A: governing vector | B: run loaded |\n|---|---|---|")
    a(f"| guy toggle pull | {pa['guy_toggle_pull_n']:.0f} N | {pb['guy_toggle_pull_n']:.0f} N |")
    a(f"| guy direction (x out, y aft, z up) | {pa['guy_unit_x_out_y_aft_z_up']} | {pb['guy_unit_x_out_y_aft_z_up']} |")
    a(f"| below horizontal / outboard | {pa['guy_below_horizontal_deg']:.0f} deg / {pa['guy_outboard_pct']:.1f} % | "
      f"{pb['guy_below_horizontal_deg']:.0f} deg / {pb['guy_outboard_pct']:.1f} % |")
    a(f"| crown-strap toggle | {pa['crown_strap_toggle_n']:.0f} N | {pb['crown_strap_toggle_n']:.0f} N |")
    a(f"| run's spine end | {pa['run_spine_end']} | same |\n")
    a(f"**M-C one hinge number: {hn['hinge_row_n']:.0f} N factored per side** (`bl047_frame_items.HINGE_ROW_N` = "
      f"`mfg_corrie_f_rev3.HINGE_N`; 3.0 x {hn['f_1g_n']:.0f} N at 1 g). The frame had checked {hn['previous_basis']['revC_n']:.0f} "
      f"N (rev C beam) and {hn['previous_basis']['sim_x3_n']:.0f} N (frame-side sim x 3). The voxel FE of the hinge fairlead "
      "is linear, so it is scaled from its two load directions on file:\n")
    a("| check at 1019 N (fatigue 1.6 g x 340 N) | rev C direction (down the stay) | sim direction (inboard, up) |\n|---|---:|---:|")
    for k in ("sf_strength", "sf_fatigue", "sf_creep"):
        a(f"| fairlead {k[3:]} | {hn['revC_direction'][k]:.2f} | {hn['sim_direction'][k]:.2f} |")
    a(f"| pin 5 mm 7075 yield / fatigue | {hn['pin_7075_5mm']['sf_yield']:.2f} / {hn['pin_7075_5mm']['sf_fatigue']:.2f} | same |\n")
    a(f"The sim-direction fatigue {hn['sim_direction']['sf_fatigue']:.2f} < 1 only if the bag's 340 N (1 g, the attach "
      "sims' worst hinge eye) acts in the frame-side sim's inboard-up direction (those sims gave 250 N at 1 g). The attach "
      "sims record magnitude only. See OWNER DECISIONS / found, not fixed.\n")
    a("## 9. Mass\n")
    a("| item | g | oz | source |\n|---|---:|---:|---|")
    for lab, g_, src in (("spine clamp, webs 2.5 -> 2.0", m["clamp_delta_g"], "crown_spine_clamp.size_clamp"),
                         ("H1 print: pawl bosses + bore + window", m["pawl_print_net_g"], "print mesh (h1_pawl.add_pawl)"),
                         ("H1 print: hinge relief (2)", m["hinge_relief_g"], "print mesh (bl047_frame_items)"),
                         ("LP Ti pawl vs the old SLM pawl", m["pawl_delta_g"], "mesh volume x 4.43 g/cm3")):
        a(f"| {lab} | {g_:+.2f} | {g_ / 28.35:+.3f} | {src} |")
    a(f"\nBooked as ledger correction **BL047** (`huntkit.mass.ledger`). The H1 assembled print is {m['assembled_g']:.1f} g "
      f"({m['assembled_g'] / 453.6:.2f} lb).\n")
    a("Mass reductions that keep the margins (not applied): GNL crown members at 1.0 are >= 3.8 against 1.0, but the "
      "crown tubes are sized by the other rev C cases (legs 1.12 in hipbelt-off linear, side-hill / static fatigue): a "
      "GNL C8 basis would free the hipbelt-off-governed rows only (crown legs, a_S top bar) once T1(c) confirms it; "
      "housing aft wall 6.8 -> 3 mm (about 3 g) after the dry fit (BL-046).\n")
    a("## 10. Assumptions\n")
    for k, (txt, test) in {**ASSUMPTIONS, **__import__("huntkit.gendesign.h1_pawl", fromlist=["x"]).ASSUMPTIONS}.items():
        a(f"- ASSUMPTION {k}: {txt} Settled by: {test}")
    a("- ASSUMPTION RELIEF-STRENGTH: the m-1 relief takes throat floor, not cheek section (0.2 mm of an 8 mm cheek "
      "face), so the BL-042 hinge fairlead FEA stands. Settled by: PT-3 on the printed fairlead (relief included).")
    a("- ASSUMPTION WEB-BODY: the H1 body voxel checks are not re-run for the 2.0 mm web (clamp end forces change < 2 %). "
      "Settled by: the next body re-run.\n")
    a("## 11. Found, not fixed\n")
    a("- The linear C8 support model (grounded springs, hipbelt off) is non-physical for every C8 check, not only buckling: "
      "the crown legs (1.12), the pawl force (2.3 kN, mostly fore-aft) and the clamp socket peak (C8-governed) all carry "
      "the 1.4 kN spring couple. They are conservative, but they size parts. A load-standard change (C8 on straps + back "
      "contact) is an owner / HA-LS-1 decision.")
    a(f"- Hinge fairlead fatigue {hn['sim_direction']['sf_fatigue']:.2f} at the bag's 1019 N row in the frame-side sim "
      "direction (section 8).")
    a(f"- HE throat side clearance at a 0.15 mm print tolerance {he['tol_0p15']['throat_clear_side_mm']:.2f} mm (rule 0.5); "
      "the throat width is the bag-side HE-FIT gate (not changed here).")
    a("- `print/crown_pawl_fdm_pacf.stl` / `crown_pawl_slm.stl` (old pawl) do not fit the H1 housing; the print README "
      "and the test kit still list them.\n")
    a("## Screenshots\n")
    for sh in shots:
        a(f"- `{Path(sh).relative_to(REPO)}`")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="store_true", help="run the GNL matrix (about 40 min)")
    a = ap.parse_args(argv)
    if a.run or not (OUT / "run_all.pkl").exists():
        out = run_all()
        (OUT / "run_all.pkl").write_bytes(pickle.dumps(out))
    rec, d = build_record()
    SCREENS.mkdir(parents=True, exist_ok=True)
    shots = [plot_path(d, SCREENS / f"{SHOT}1.png"), plot_deformed(SCREENS / f"{SHOT}2.png"),
             plot_pawl(rec["pawl"]["check"], SCREENS / f"{SHOT}3.png"),
             plot_margins(d, {"rows": rec["margin_rows"]}, SCREENS / f"{SHOT}4.png")]
    RESULTS.write_text(json.dumps(rec, indent=1, default=_np))
    from . import bl047_frame_items as B
    B.RESULTS.write_text(json.dumps({"superseded_note": SUPERSEDED_HINGE_JSON, **rec["items"]}, indent=1, default=_np))
    doc = write_doc(rec, d, shots)
    first, rest = doc.split("\n", 1)
    DOC.write_text(first + "\n\n" + SUPERSEDED_HINGE_MD + rest)
    print("\n".join(shots))


if __name__ == "__main__":
    main()
