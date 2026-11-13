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
    for kit in KITS:                         # worn baseline: every setting, both couples, stiffness band, lifter ends
        for t in sets_for(kit):
            for variant in ("crown_bar", "strap_upper"):
                for km in K_MULTS:
                    for lf in ("loose", "cinched"):
                        key = ("set", kit, t, variant, km, lf, "sling_back", IMP_MM[0])
                        rows.append(get(key, lambda: run_set(kit, t, variant, km, lf, "sling_back", IMP_MM[0], log=log)))
    for kit in KITS:                         # support variants on each kit's linear-worst setting
        w = min((r for r in rows if r["kit"] == kit), key=lambda r: r["linear_margin"])
        for sp_ in ("sling_free", "yoke_back"):
            for km in K_MULTS:
                for lf in LIFTER_STATES:
                    key = ("set", kit, w["torso_in"], w["variant"], km, lf, sp_, IMP_MM[0])
                    rows.append(get(key, lambda: run_set(kit, w["torso_in"], w["variant"], km, lf, sp_, IMP_MM[0],
                                                         log=log)))
    gov = min(rows, key=lambda r: (r["lam_reached"], r["min_eig_last"]))
    imp8 = get(("set", gov["kit"], gov["torso_in"], gov["variant"], gov["k_mult"], gov["lifter"], gov["support"],
                IMP_MM[1]), lambda: run_set(gov["kit"], gov["torso_in"], gov["variant"], gov["k_mult"], gov["lifter"],
                                            gov["support"], IMP_MM[1], log=log))
    ref = get(("ref", "a_L", 23.0), lambda: spring_reference("a_L", 23.0))
    return {"rows": rows, "governing": gov, "imp8": imp8, "spring_reference": ref}
