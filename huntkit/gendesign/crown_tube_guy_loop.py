"""Review Y-4 (2026-11-13): crown top bar wall (ring crush) under the webbing loops that bear on it, CORRIE F rev 3.

The question: TL-1 pulls a 25 mm loop round the bare OD 18 crown top bar to 432 N, but the repo's own wall check
(``frame_cg_recheck.bar_local``, "Roark point-load ring", used by ``loadpath_check`` A3) gives about 295 N for a
25 mm loop on the rev C bar, and that check was last run at the old 244 N guy load. This module

1. re-runs that check (basis A, identical formula, so the 295 N is reproduced) for every loop that bears on the bar at
   the current factored loads, per crown kit, including the guy + crown-strap loops sharing the B-25 sleeve;
2. adds two physically better ring models, both verified against closed forms (Roark case 1, Bruhn's fuselage-frame
   point load reacted by shear) and against an independent ring FE on ``huntkit.fea.frame``:
   basis B = the strap force as a concentrated load reacted by the bar's own beam shear flow (no spreading credit),
   basis C = the strap wrapped over 180 deg (uniform pressure) reacted by the beam shear flow;
3. sizes the lightest fix on basis A (the HA-LS-1 ring rule: point-load ring, a spread contact credited only with a
   passing coupon; load_standard.md section 4, "Crown bushings" row) and gives the TL-1 proof load and pass criteria.

Loop inventory on the crown top bar (rev 3):
- B-25 bridle sleeves at x +/-52 (25 mm webbing sewn round the bare bar, x 39.5-64.5): every rev 3 load on the bar
  goes through them. The port guy TG (B-25 tab -> B-27 port -> B-22) toggles into the sleeve's tab; the B-28 crown
  strap toggles into a second fold of the same tab. So the guy and the crown strap share one 25 mm bearing.
- GBL "guy bar loop" (25 mm x 170 mm round the bar, BL-004 REC): still in the rev 3 cut list and op 7.19, load table
  244 N, but rev 1+ routes the guy toggle into the B-25 tab. Checked here as if it carried the guy (same numbers as
  a 25 mm loop); flagged as a downstream question (see the doc).
- Load lifters: lugs on the crown-corner wraps at x +/-105 (build_geometry.LIFTER_X, node loads), not a webbing
  loop on the bare bar: outside this check.

Every crown kit (S 15-18, M 17.5-20.5, L 20-23 in) uses the same top bar: ``frame.yaml frame.top_bar_section``
(OD 18, [+-45 twill / UD 0 x5 / +-45 twill], wall 1.065 mm, 230 mm centreline, 214 mm cut); crown_diet kits cut
only legs, spine and rack per size (``crown_diet.Option``). This is asserted in :func:`kit_sections`.

Record: designs/pack_5200/analysis/crown_tube_guy_loop.md (+ crown_tube_guy_loop.json).

    python -m huntkit.gendesign.crown_tube_guy_loop        # JSON, Markdown, screenshot
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

from huntkit.fea.composite import DEFAULT_KNOCKDOWN
from huntkit.fea.sections import from_spec
from huntkit.materials import load as load_material

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / "designs" / "pack_5200"
CONCEPTS = PACK / "concepts"
ANALYSIS = PACK / "analysis"
FRAME_YAML = PACK / "frame.yaml"
DOC = ANALYSIS / "crown_tube_guy_loop.md"
RESULTS = ANALYSIS / "crown_tube_guy_loop.json"
SCREENS = REPO / "outputs" / "screens"
SHOT = "20261113_crowntube_1.png"

# ------------------------------------------------------------------------------------------- rules (sources)
CASE_FACTOR = 3.0        # HA-LS-1 rev C C5: 2.0 g x 1.5 on the 1 g sim force (load_standard.md section 4)
STATIC_FACTOR = 2.0      # HA-LS-1 rev C C1: static carry 1.0 g x 2.0 (used with the hand cinch combination)
CINCH_FACTOR = 1.5       # load_standard.md 4.3: hand cinch x 1.5
G_WALK = 1.6             # HA-LS-1 fatigue: 1e5 cycles 0 -> 1.6 g
FI_FAT = 0.5             # HA-LS-1 fatigue: CFRP FI <= 0.5 at the 1.6 g peak
PROOF = 1.5              # bag_attachment / loadpath_check: qualification proof = 1.5 x factored (sewn parts, hardware)
SF_REQ = 1.0             # factored load on knocked-down first-ply failure (HA-LS-1: "factor per case")
TORSO_SIMS = (15.0, 19.0, 23.0)
KITS = {"S": (15.0, 18.0), "M": (17.5, 20.5), "L": (20.0, 23.0)}   # crown_diet.SIZES

# geometry (corrie_f constants, read live where they exist)
LEG_X = 115.0            # crown legs at x +/-115 (corrie_f_body.md 12.3)
BAR_L = 230.0            # top bar centreline (frame.yaml stock: crown top bar centreline_mm)
SLEEVE_X = 52.0          # B-25 sleeves / guy / crown strap at x +/-52 (corrie_f.GUY_X, CROWN_X)
WRAP_SCARF_X = 69.0      # corner wrap scarf starts at x 69 (corrie_f.guy_tubes: wrap x 77-107, scarf 8 mm)
SPINE_CLAMP_HALF = 15.0  # corrie_f.SPINE_CLAMP_HALF (ASSUMPTION there)
MIN_CLEAR_MM = 10.0      # corrie_f.MIN_CLEAR_MM (ASSUMPTION there): gloved handling / webbing wander
BAR_CUT_MM = 214.0       # frame.yaml stock: crown top bar cut_length_mm

ASSUMPTIONS = {
    "RING_SLICE": ("The bar wall under a loop is a ring slice as wide as the bearing (the strap or saddle width); the "
                   "tube either side is not credited. Conservative: the adjacent shell resists ovalisation.",
                   "TL-1b: ovalisation of the bare bar under a 25 mm loop, measured, against the basis A/B/C predictions."),
    "BASIS_A": ("Design basis = the repo's existing rule (frame_cg_recheck.bar_local): Roark point-load ring, "
                "M = 0.318 F Rm / w, with the hoop membrane N = -F / 2w added at the same point. HA-LS-1 keeps the "
                "point-load ring for ring crush and credits a spread contact only with a passing coupon.",
                "TL-1b coupon unlocks basis B or C (as T7 does for the crown bushings)."),
    "WRAP_UNIFORM": ("Basis C: the strap presses uniformly over the 180 deg it wraps (equal legs, friction not "
                     "mobilised under a symmetric pull).", "TL-1b ovalisation reading."),
    "LOAD_INTERP": ("The port guy 1 g force varies linearly with torso between the rev 3 fine sims at 15 / 19 / 23 in "
                    "(corrie_f.bl029_table, rev 3 over_port); a kit is checked at its tallest setting. The crown "
                    "strap takes the larger of the two bracketing sims.",
                    "T9 / PORT-1 load reading on the prototype at each kit."),
    "COLLINEAR": ("Guy and crown strap forces on the shared B-25 sleeve are added as scalars (collinear). They are "
                  "about 90 deg apart in the sims (guy aft, crown strap up the frame face), so the vector sum is "
                  "lower; the scalar sum is the conservative envelope.", "-"),
    "CINCH": ("Crown strap hand cinch 80 N (corrie_f.CROWN_PRE_N, ASSUMPTION there) x 1.5, combined with the guy at "
              "the C1 static factor (1 g x 2.0): the cinch is applied with the pack at rest.",
              "B-28 cinch pull reading at fit (FS-O5 / T9)."),
    "BAR_BENDING": ("The bar's own bending at the sleeve (both guys pulling, fixed-fixed between the corners, spine "
                    "support ignored: M = P a^2 / L at the load, a = 63 mm) and its beam shear flow F / (2 pi R) are "
                    "added at every angle with the worse sign.", "-"),
    "WIDE_SLEEVE": ("A 38 mm B-25 sleeve spreads the 25 mm tab pull over its full 38 mm (webbing in-plane shear over "
                    "a 70 mm wrap). The sleeve is shifted inboard (x 26.5-64.5) to stay 4.5 mm clear of the corner "
                    "wrap scarf at x 69 and 11.5 mm clear of the spine clamp.",
                    "TL-1 is run on the 38 mm sleeve as built (this is what it proves)."),
    "COLLAR_SPREAD": ("A printed PA12-CF collar (2 mm wall, 40 mm long) spreads the strap over its length (stiff "
                      "in that short overhang); its ring-moment share is not credited.", "TL-1 with the collar fitted."),
    "LINER_SPREAD": ("A 1.6 mm HDPE liner spreads the strap only by 45 deg through its thickness (w + 2 t): soft "
                     "(1.1 GPa), so no ring-moment share or longer spread is credited.", "-"),
}


# ============================================================================================ ring theory
def ring_fourier(p: np.ndarray, q: np.ndarray, th: np.ndarray, R: float = 1.0, nmax: int = 600) -> dict:
    """Inextensional thin ring under self-equilibrated line loads (per unit arc length): radial ``p`` (outward +)
    and tangential ``q`` (+theta), sampled on the uniform grid ``th`` (0..2pi, endpoint excluded).

    Equilibrium of an element (F = N e_theta + V e_r on the +theta face): N' + V + qR = 0, V' - N + pR = 0,
    M' = R V. Eliminating: M''' + M' = -R^2 (p' + q). With p = sum p_n cos n th, q = sum q_n sin n th:
        M = sum_{n>=2} R^2 (n p_n - q_n) / (n (n^2 - 1)) cos n th      (closed ring, uniform EI: M_0 = M_1 = 0)
        N = R (p_0 + p_1 cos th) + R sum_{n>=2} (n q_n - p_n) / (n^2 - 1) cos n th
    n = 1 equilibrium needs p_1 = q_1 (net force zero). Radial only, this is ``huntkit.fea.rings``.
    Verified: Roark case 1 (0.3183 / 0.1817 F R), Bruhn's point load on shear (0.2387 F R), ring FE (tests)."""
    dth = th[1] - th[0]
    n = np.arange(nmax + 1)
    C = np.cos(np.outer(n, th))
    S = np.sin(np.outer(n, th))
    pn = C @ p * dth / np.pi
    pn[0] /= 2.0
    qn = S @ q * dth / np.pi
    k = n[2:].astype(float)
    m = R ** 2 * (k * pn[2:] - qn[2:]) / (k * (k * k - 1.0))
    nn = R * (k * qn[2:] - pn[2:]) / (k * k - 1.0)
    M = m @ C[2:]
    N = R * (pn[0] + pn[1] * np.cos(th)) + nn @ C[2:]
    return {"M": M, "N": N, "p1": float(pn[1]), "q1": float(qn[1])}


def load_pattern(kind: str, th: np.ndarray, F: float = 1.0, R: float = 1.0, wrap_deg: float = 180.0):
    """Line loads (p radial outward +, q tangential +theta) with resultant F in +x on the ring.

    kind 'pair': two opposed inward point loads F at theta 0 and pi (Roark case 1; self-equilibrated).
    kind 'point_shear': inward point load at theta = pi pushing +x, reacted by the beam shear flow
        q = F sin(theta) / (pi R) (Bruhn A8 fuselage frame, M_max = 3 F R / (4 pi) = 0.2387 F R at the load).
    kind 'wrap_shear': a strap pulled toward +x wraps the back side (|theta - pi| < wrap/2) with uniform pressure,
        reacted by the same beam shear flow."""
    dth = th[1] - th[0]
    p = np.zeros_like(th)
    i_pi = int(np.argmin(np.abs(th - np.pi)))
    if kind == "pair":
        p[i_pi] = -F / (R * dth)
        p[0] = -F / (R * dth)
        return p, np.zeros_like(th)
    if kind == "point_shear":
        p[i_pi] = -F / (R * dth)
    elif kind == "wrap_shear":
        half = math.radians(wrap_deg) / 2.0
        on = np.abs(th - np.pi) < half
        # resultant along +x of a uniform inward pressure p0 over +-half about pi: 2 p0 R sin(half) = F
        p[on] = -F / (2.0 * R * math.sin(half))
    else:
        raise ValueError(kind)
    q = F * np.sin(th) / (np.pi * R)
    return p, q


def ring_fe(kind: str, R: float, EI: float, EA: float, F: float = 1.0, nel: int = 360,
            wrap_deg: float = 180.0) -> dict:
    """Independent check: the same ring as ``nel`` straight 3D frame elements (huntkit.fea.frame.solve) in the XY
    plane, loads lumped to the nodes. Returns theta, |M|, N per element (mid) and the ovalisation (change of the
    diameter along the load and across it)."""
    from huntkit.fea.frame import solve
    th = np.linspace(0.0, 2 * np.pi, nel, endpoint=False)
    p, q = load_pattern(kind, th, F, R, wrap_deg)
    dth = th[1] - th[0]
    nodes = {f"n{i}": [R * math.cos(t), R * math.sin(t), 0.0] for i, t in enumerate(th)}
    E = 1000.0
    I = EI / E
    sec = {"type": "generic", "A": EA / E, "Iy": I, "Iz": I, "J": 2 * I}
    mat = {"id": "ring", "youngs_modulus_mpa": E, "shear_modulus_mpa": E / 2.6, "density_kg_m3": 1.0,
           "yield_strength_mpa": 1e9}
    members = [{"id": f"e{i}", "nodes": [f"n{i}", f"n{(i + 1) % nel}"], "section": sec, "material": mat,
                "ref": [0, 0, 1]} for i in range(nel)]
    loads = {}
    for i, t in enumerate(th):
        er = np.array([math.cos(t), math.sin(t)])
        et = np.array([-math.sin(t), math.cos(t)])
        f = (p[i] * er + q[i] * et) * R * dth
        if np.any(np.abs(f) > 0):
            loads[f"n{i}"] = [float(f[0]), float(f[1]), 0.0, 0.0, 0.0, 0.0]
    i90 = nel // 4
    sup = {f"n{i}": {"fix": "z rx ry"} for i in range(nel)}
    sup["n0"] = {"fix": "x y z rx ry"}
    sup[f"n{i90}"] = {"fix": "x z rx ry"}
    res = solve({"nodes": nodes, "members": members, "supports": sup, "loads": loads}, name=f"ring_{kind}")
    ef = res.elem_forces                                   # (ne, 2, 6): N, Vy, Vz, T, My, Mz
    Mb = 0.5 * (np.abs(ef[:, 0, 4]) + np.abs(ef[:, 1, 4])) if np.abs(ef[:, :, 4]).max() > np.abs(ef[:, :, 5]).max() \
        else 0.5 * (np.abs(ef[:, 0, 5]) + np.abs(ef[:, 1, 5]))
    Nax = 0.5 * (ef[:, 0, 0] + ef[:, 1, 0])
    D = res.displacements
    ux = lambda i: D[f"n{i}"][0]
    uy = lambda i: D[f"n{i}"][1]
    i180, i270 = nel // 2, 3 * nel // 4
    return {"theta_mid": th + dth / 2, "M_abs": Mb, "N": Nax,
            "dD_along": float(ux(0) - ux(i180)), "dD_across": float(uy(i90) - uy(i270)),
            "max_reaction": float(max(np.abs(np.asarray(v)[:3]).max() for v in res.reactions.values()))}


def peak_coeff(kind: str, wrap_deg: float = 180.0, n_grid: int = 7200, nmax: int = 1200) -> dict:
    """Peak |M| / (F R) and the hoop N range / F for a load pattern (Fourier)."""
    th = np.linspace(0, 2 * np.pi, n_grid, endpoint=False)
    p, q = load_pattern(kind, th, 1.0, 1.0, wrap_deg)
    r = ring_fourier(p, q, th, 1.0, nmax)
    i = int(np.argmax(np.abs(r["M"])))
    return {"m_coeff": float(np.abs(r["M"]).max()), "at_deg": float(np.degrees(th[i])),
            "n_min": float(r["N"].min()), "n_max": float(r["N"].max())}


# ============================================================================================ the bar
def frame_spec() -> dict:
    return yaml.safe_load(FRAME_YAML.read_text())


def bar_spec(name: str = "rev_c") -> dict:
    """Crown top bar section specs: the released rev C bar and the candidate wall changes (OD 18 kept: the corner
    wraps are coped to it; plies added inside, as rev C did)."""
    fy = frame_spec()
    base = copy.deepcopy(fy["frame"]["top_bar_section"])
    if name == "rev_c":
        return base
    if name == "rev_b":
        return copy.deepcopy(fy["frame"]["bar_section"])
    lay = base["layup"]
    ud = "cfrp_t700_ud_epoxy_ply"
    tw = "cfrp_t300_3k_woven_epoxy_ply"
    if name == "hoop2":          # + one UD 90 ply under each twill: [+-45 / 90 / 0 x5 / 90 / +-45]
        base["layup"] = [lay[0], {"angle": 90, "material": ud}] + lay[1:-1] + [{"angle": 90, "material": ud}, lay[-1]]
    elif name == "hoop1_in":     # + one UD 90 ply on the inside only (asymmetric)
        base["layup"] = lay[:-1] + [{"angle": 90, "material": ud}, lay[-1]]
    elif name == "tw0_in":       # + one 0/90 twill (angle 0) inside, under the inner +-45 twill
        base["layup"] = lay[:-1] + [{"angle": 0, "material": tw}, lay[-1]]
    else:
        raise ValueError(name)
    return base


def section(name: str = "rev_c"):
    return from_spec(bar_spec(name))


def kit_sections() -> dict:
    """The crown top bar member section at the kit torsos (frame.yaml through build_frame_from_yaml): one bar."""
    from huntkit.fea.frames import build_frame_from_yaml
    out = {}
    for kit, (lo, hi) in KITS.items():
        for t in (lo, hi):
            fm = build_frame_from_yaml(FRAME_YAML, torso_in=float(t))
            s = from_spec(next(m for m in fm["members"] if m["group"] == "crown_top_bar")["section"])
            out[f"{kit}@{t:g}"] = {"od": float(s.dims["od"]), "t": float(s.dims["t"]), "layup": s.layup_str}
    return out


def bar_mass_g(name: str) -> float:
    s = section(name)
    return float(s.A * BAR_CUT_MM * s.density_kg_m3 * 1e-6)


# ============================================================================================ capacity
def _fpf(lam, Ny, My, Nx=0.0, Nxy=0.0, knockdown=DEFAULT_KNOCKDOWN) -> float:
    """Worst FI over the four sign combinations of the bar's own (Nx, Nxy)."""
    fi = 0.0
    for sx in (1.0, -1.0):
        for sxy in (1.0, -1.0):
            r = lam.first_ply_failure((sx * Nx, Ny, sxy * Nxy), (0.0, My, 0.0), knockdown=knockdown)
            fi = max(fi, float(r["fi"]))
    return fi


def bar_globals(sec, F: float) -> tuple:
    """Bar bending running load Nx at the sleeve (both guys, fixed-fixed, a = 63 mm) and the beam shear flow."""
    a = LEG_X - SLEEVE_X
    Mg = F * a * a / BAR_L
    ro = sec.dims["od"] / 2.0
    eps = Mg * ro / (sec.Ex * sec.Iy)
    Nx = eps * sec.laminate.A[0, 0]
    Rm = ro - sec.dims["t"] / 2.0
    Nxy = F / (2.0 * math.pi * Rm)
    return Nx, Nxy


def capacity(sec, width: float, basis: str = "A", knockdown=DEFAULT_KNOCKDOWN, globals_: bool = True,
             F_ref: float = 100.0, n_grid: int = 1440, nmax: int = 600) -> dict:
    """Load F (N) on a bearing ``width`` mm wide at which the bar wall reaches first-ply failure (FI = 1, Tsai-Wu,
    knockdowns per HA-LS-1 unless ``knockdown=None``). Basis A reproduces frame_cg_recheck.bar_local exactly when
    ``globals_`` is False. FI is linear in load for these proportional loads, so capacity = F_ref / FI(F_ref)."""
    lam = sec.laminate
    Rm = sec.dims["od"] / 2.0 - sec.dims["t"] / 2.0
    Nx, Nxy = bar_globals(sec, F_ref) if globals_ else (0.0, 0.0)
    if basis == "A":
        Ny = -F_ref / (2.0 * width)
        My = 0.318 * (F_ref / width) * Rm
        fi = _fpf(lam, Ny, My, Nx, Nxy, knockdown)
        where = 0.0
    else:
        kind = {"B": "point_shear", "C": "wrap_shear", "pair": "pair"}[basis]
        th = np.linspace(0, 2 * np.pi, n_grid, endpoint=False)
        p, q = load_pattern(kind, th, F_ref / width, Rm)
        r = ring_fourier(p, q, th, Rm, nmax)
        # the peaks: scan the 24 largest |M| and the extreme N points (FI is not monotone in M alone)
        idx = set(np.argsort(-np.abs(r["M"]))[:24].tolist()) | {int(np.argmin(r["N"])), int(np.argmax(r["N"]))}
        fis = {i: _fpf(lam, float(r["N"][i]), float(r["M"][i]), Nx, Nxy, knockdown) for i in idx}
        i = max(fis, key=fis.get)
        fi, where = fis[i], float(np.degrees(th[i]))
    return {"capacity_n": F_ref / fi, "fi_per_n": fi / F_ref, "at_deg": where, "basis": basis, "width_mm": width}


def ovalisation(sec, F: float, width: float, basis: str = "A") -> float:
    """Elastic change of the diameter along the pull (mm) of the ring slice ``width`` wide: basis A = Roark case 1
    0.1488 F R^3 / EI; B / C from the ring FE. EI = D22 x width (plane-strain slice)."""
    Rm = sec.dims["od"] / 2.0 - sec.dims["t"] / 2.0
    EI = sec.laminate.D[1, 1] * width
    if basis == "A":
        return 0.1488 * F * Rm ** 3 / EI
    EA = sec.laminate.A[1, 1] * width
    r = ring_fe({"B": "point_shear", "C": "wrap_shear"}[basis], Rm, EI, EA, F, nel=240)
    return abs(r["dD_along"])


# ============================================================================================ loads
def _corrie():
    if str(CONCEPTS) not in sys.path:
        sys.path.insert(0, str(CONCEPTS))
    import corrie_f as C
    return C


def sim_loads() -> dict:
    """Rev 3 fine-sim 1 g forces at the bar: port guy and crown strap, per torso (fill / meat; the same sim, so the
    pair is concurrent). Source: corrie_f.bl029_table (rev 3 over_port runs)."""
    C = _corrie()
    t = C.bl029_table()["rev3"]
    out = {}
    for tor in TORSO_SIMS:
        r = t[int(tor)]
        rows = {cn: {"guy": float(r[cn]["port_guy_1g_n"]), "crown": float(r[cn]["crown_or_guy_1g_n"])}
                for cn in ("fill", "meat") if r.get(cn)}
        out[tor] = {"rows": rows, "guy": max(v["guy"] for v in rows.values()),
                    "crown": max(v["crown"] for v in rows.values()),
                    "pair": max(v["guy"] + v["crown"] for v in rows.values())}
    d = C.crown_strap_diet()["loads"]
    return {"by_torso": out, "guy_1g_envelope_n": float(C.GUY_1G_MAX_N), "crown_1g_max_n": float(d["crown_1g_max_n"]),
            "crown_cinch_n": float(C.CROWN_PRE_N), "lid_3g_n": float(d["lid_3g_n"]),
            "guy_envelope_factored_n": float(d["guy_envelope_factored_n"])}


def _interp(sl: dict, key: str, t: float) -> float:
    xs = list(TORSO_SIMS)
    return float(np.interp(t, xs, [sl["by_torso"][x][key] for x in xs]))


def kit_loads(sl: dict | None = None) -> dict:
    """Per crown kit (at its tallest setting) and the envelope: the loads on one B-25 sleeve (N)."""
    sl = sl or sim_loads()
    out = {}
    for kit, (lo, hi) in KITS.items():
        g = _interp(sl, "guy", hi)
        lo_s = max(x for x in TORSO_SIMS if x <= hi)
        hi_s = min(x for x in TORSO_SIMS if x >= hi)
        c = max(sl["by_torso"][lo_s]["crown"], sl["by_torso"][hi_s]["crown"])
        out[kit] = _combos(g, c, sl["crown_cinch_n"], f"{kit} at {hi:g} in")
    out["envelope"] = _combos(sl["guy_1g_envelope_n"], sl["crown_1g_max_n"], sl["crown_cinch_n"],
                              "envelope (guy 96 N at 23 in + crown strap 11.6 N at 15 in)")
    return out


def _combos(g: float, c: float, cinch: float, label: str) -> dict:
    cases = {
        "guy alone (C5, x3.0)": CASE_FACTOR * g,
        "crown strap alone, 288 N envelope (guy off)": CASE_FACTOR * g,
        "guy + crown strap, stumble (x3.0 each)": CASE_FACTOR * (g + c),
        "guy (C1 x2.0) + crown strap hand cinch (x1.5)": STATIC_FACTOR * g + CINCH_FACTOR * cinch,
    }
    gov = max(cases, key=cases.get)
    return {"label": label, "guy_1g_n": round(g, 1), "crown_1g_n": round(c, 1), "cases": cases,
            "static_n": cases[gov], "static_case": gov,
            "vector_stumble_n": CASE_FACTOR * math.hypot(g, c),
            "fatigue_peak_n": G_WALK * (g + c), "proof_n": PROOF * cases[gov]}


# ============================================================================================ checks
def check_row(sec, width: float, loads: dict, basis: str = "A") -> dict:
    cap = capacity(sec, width, basis)
    cap0 = capacity(sec, width, basis, knockdown=None)
    return {"width_mm": width, "basis": basis, "capacity_n": cap["capacity_n"], "capacity_rt_n": cap0["capacity_n"],
            "sf_static": cap["capacity_n"] / loads["static_n"],
            "fi_fatigue": loads["fatigue_peak_n"] / cap["capacity_n"],
            "sf_fatigue": FI_FAT / (loads["fatigue_peak_n"] / cap["capacity_n"]),
            "proof_over_rt_capacity": loads["proof_n"] / cap0["capacity_n"]}


def _web_g_m(w: int) -> float:
    return float(load_material(f"poly_webbing_{w}mm").require("mass_g_m"))


def fix_options(env: dict) -> list:
    """Candidate fixes, each re-checked on basis A at the envelope loads, with the mass change per pack."""
    C = _corrie()
    rc = section("rev_c")
    rows = []
    b25 = C.guy_bridle()

    def add(key, label, sec, width, dmass, where, notes, credit, fits=True):
        r = check_row(sec, width, env, "A")
        r.update(key=key, label=label, d_mass_g=round(dmass, 2), where=where, notes=notes, credit=credit,
                 fits=bool(fits), strength_ok=bool(r["sf_static"] >= SF_REQ and r["sf_fatigue"] >= 1.0))
        r["passes"] = r["strength_ok"] and r["fits"]
        rows.append(r)

    add("bare25", "today: 25 mm B-25 sleeve on the bare bar", rc, 25.0, 0.0, "-", "rev 3 as released", "-")
    # wider sleeve: the whole B-25 in 38 mm webbing (one piece, as today). Run shortens by the inboard shift.
    for w in (38, 50):
        x_in = SLEEVE_X + 12.5 - w            # outboard edge kept at x 64.5 (4.5 mm to the wrap scarf at 69)
        clear_spine = x_in - SPINE_CLAMP_HALF
        run = 2.0 * (x_in - SPINE_CLAMP_HALF)
        L = 2 * C.BAR_WRAP_MM + run + C.SPINE_WRAP_MM + 2 * C.BRIDLE_TAB_MM
        m = L * _web_g_m(w) / 1000.0
        add(f"b25_{w}", f"B-25 bridle in {w} mm webbing (sleeve x {x_in:.1f}-64.5)", rc, float(w),
            m - b25["mass_g"], "bag side (B-25, frame-fitted)",
            f"one piece, {L:.0f} mm of poly_webbing_{w}mm; {clear_spine:.1f} mm to the spine clamp",
            "ASSUMPTION WIDE_SLEEVE", fits=clear_spine >= MIN_CLEAR_MM)
    # HDPE liner under today's sleeve (1.6 mm x 40 mm wrap)
    hd = load_material("hdpe_sheet")
    t_l, L_l = 1.6, 40.0
    m_l = 2 * L_l * math.pi * (18.0 + t_l) * t_l * float(hd.require("density_kg_m3")) * 1e-6
    add("hdpe_liner", "HDPE liner 1.6 x 40 mm under the 25 mm sleeve", rc, 25.0 + 2 * t_l, m_l, "frame (pair)",
        "hdpe_sheet record; spread w + 2t only", "ASSUMPTION LINER_SPREAD")
    # printed PA12-CF split collar, 2 mm x 40 mm
    pa = load_material("pa12_cf_fdm_paht")
    m_c = 2 * L_l * math.pi * (18.2 + 2.0) * 2.0 * float(pa.require("density_kg_m3")) * 1e-6
    add("pa12_collar", "printed PA12-CF collar 2 x 40 mm under the sleeve", rc, L_l, m_c, "frame (pair)",
        "pa12_cf_fdm_paht record; needs its own creep / fatigue check (PAHT ratios 0.4 / 0.3)", "ASSUMPTION COLLAR_SPREAD")
    m0 = bar_mass_g("rev_c")
    for key, lab in (("hoop2", "bar wall + 2 UD 90 plies [+-45/90/0x5/90/+-45], 1.315 mm"),
                     ("hoop1_in", "bar wall + 1 UD 90 ply inside, 1.19 mm"),
                     ("tw0_in", "bar wall + 1 twill 0/90 inside, 1.285 mm")):
        add(key, lab, section(key), 25.0, bar_mass_g(key) - m0, "frame (top bar, every kit)",
            "special-order wrap (same vendors as rev C); OD 18 kept, ID smaller; frame.yaml + bar checks re-run",
            "CLT, no new assumption")
    return rows


def verification() -> dict:
    """Closed-form checks of the ring theory and of the FE cross-check (also asserted in the tests)."""
    pair = peak_coeff("pair")
    th = np.linspace(0, 2 * np.pi, 7200, endpoint=False)
    p, q = load_pattern("pair", th)
    r = ring_fourier(p, q, th, 1.0, 1200)
    j = int(np.argmin(np.abs(th - np.pi / 2)))
    ps = peak_coeff("point_shear")
    ws = peak_coeff("wrap_shear")
    sec = section("rev_c")
    Rm = sec.dims["od"] / 2.0 - sec.dims["t"] / 2.0
    EI, EA = sec.laminate.D[1, 1] * 25.0, sec.laminate.A[1, 1] * 25.0
    fe = {k: ring_fe(k, Rm, EI, EA, 100.0, nel=360) for k in ("pair", "point_shear", "wrap_shear")}
    return {
        "roark1_M_load": {"closed_form": 1 / math.pi, "fourier": pair["m_coeff"],
                          "fe": float(fe["pair"]["M_abs"].max() / (100.0 * Rm))},
        "roark1_M_90": {"closed_form": 0.5 - 1 / math.pi, "fourier": float(r["M"][j])},
        "roark1_N_90": {"closed_form": -0.5, "fourier": float(r["N"][j])},
        "roark1_dD": {"closed_form": 0.1488 * 100.0 * Rm ** 3 / EI, "fe": abs(fe["pair"]["dD_along"])},
        "bruhn_point_shear_M": {"closed_form": 3 / (4 * math.pi), "fourier": ps["m_coeff"],
                                "fe": float(fe["point_shear"]["M_abs"].max() / (100.0 * Rm))},
        "wrap180_M": {"fourier": ws["m_coeff"], "fe": float(fe["wrap_shear"]["M_abs"].max() / (100.0 * Rm)),
                      "at_deg": ws["at_deg"]},
        "fe_max_reaction_n": max(v["max_reaction"] for v in fe.values()),
    }


# ============================================================================================ BL-045 re-check
GUY_PATHS = CONCEPTS / "corrie_f_sim" / "corrie_f_guy_paths.json"
CROWN_PATHS = CONCEPTS / "corrie_f_sim" / "corrie_f_crown_paths.json"
TOGGLE_L_MM = 30.0       # pom_toggle record: POM 30 x 8 x 5 mm (attach_system.TOGGLE_G source)
ASSUMPTIONS["GUY-DIR"] = ("The port guy's direction at the bar is the rev 2 port runs' (corrie_f_guy_paths.json, "
                          "F_r1_PR*_fineFM_port); rev 3 keeps that routing (B-27 port to B-22) and its over_port runs "
                          "store only the crown strap's path. Crown strap direction: corrie_f_crown_paths.json over_port.",
                          "PORT-1 / T9 guy angle reading at each kit.")
ASSUMPTIONS["RUN-TENSION"] = ("B-25's run (mitre -> necked run -> spine wrap) carries the guy's outboard component, "
                              "with no sleeve friction credited, as a downward pull of the drop leg on the sleeve's aft "
                              "face; an inboard component slackens it (the sleeve is then held by friction, 14.5 mm "
                              "short of the clamp).", "TL-1 rig pulls at the worst measured guy angle (x share 0.14).")


def b25_topology_recheck(env: dict | None = None) -> dict:
    """BL-045 item 1: the ring check on the bar under B-25 as BL-043 built it (corrie_f.b25_topology, SK-12).
    1. Bearing: what of B-25 lies on the bar (the sleeve band) and what does not (drop, 45 deg mitre, necked run,
       spine wrap all sit below the bar's underside); bearing width = the sleeve band.
    2. Pull direction: the guy (aft, up or down with torso, sideways up to 51 %) and the crown strap at the bar, from
       the cloth-sim taut paths; the run's tension (outboard part of the guy) pulls the sleeve down through the drop
       leg. The radial (y-z) resultant on the sleeve against BL-041's scalar sum (guy + crown strap).
    3. Basis A SF at 38 mm with that demand; the toggle-width sensitivity; the spine wall under the spine wrap."""
    C = _corrie()
    tp = C.b25_topology()
    rb = C.BAR_OD / 2.0
    band = tuple(tp["band_x"])
    on_bar = {"sleeve": {"x": band, "width_mm": band[1] - band[0], "layers": "1 wrap + 15 mm lap (BAR_WRAP_MM)"}}
    below = {"drop": (rb, tp["mitre"]["s"][0]), "mitre": tuple(tp["mitre"]["s"]), "necked run + spine wrap":
             tuple(tp["run_s"])}
    off_bar = {k: {"s_mm": [round(v[0], 1), round(v[1], 1)], "below_bar_underside_mm": round(v[0] - rb, 1)}
               for k, v in below.items()}
    gp = json.loads(GUY_PATHS.read_text())["rows"]
    cp = json.loads(CROWN_PATHS.read_text())["rows"]
    sl = sim_loads()
    runs = []
    for t in TORSO_SIMS:
        for case in ("fill", "meat"):
            g = gp.get(f"F_r1_PR{int(t)}_fineFM_port:{case}")
            c = cp.get(f"F_r1_PR{int(t)}_fineFM_over_port:{case}")
            r = sl["by_torso"][t]["rows"].get(case)
            if not (g and c and r):
                continue
            for side in ("R", "L"):
                ug = -np.asarray(g[side]["u_bag"], float)          # pull on the bar (toward the bag)
                uc = -np.asarray(c[side]["u_bag"], float)
                xo = float(g[side]["outboard_share_at_bar"])
                Fg, Fc = r["guy"], r["crown"]
                T = Fg * max(xo, 0.0)
                v = Fg * np.array([ug[1], ug[2]]) + Fc * np.array([uc[1], uc[2]]) + T * np.array([0.0, -1.0])
                bound = Fg * (math.sqrt(max(1 - xo * xo, 0.0)) + max(xo, 0.0)) + Fc
                runs.append({"torso": t, "case": case, "side": side, "guy_1g_n": round(Fg, 1), "crown_1g_n": round(Fc, 1),
                             "guy_dir_on_bar": [round(float(q), 3) for q in ug], "outboard_share": xo,
                             "run_tension_1g_n": round(T, 1), "radial_1g_n": round(float(np.linalg.norm(v)), 1),
                             "scalar_1g_n": round(Fg + Fc, 1),
                             "k_vector": round(float(np.linalg.norm(v)) / (Fg + Fc), 3),
                             "k_bound": round(bound / (Fg + Fc), 3),
                             "guy_angle_below_horizontal_deg": round(math.degrees(math.atan2(-ug[2], abs(ug[1]))), 1)})
    kv = max(r_["k_vector"] for r_ in runs)
    kb = max(r_["k_bound"] for r_ in runs)
    env = env or kit_loads()["envelope"]
    rc = section("rev_c")
    w = on_bar["sleeve"]["width_mm"]
    out = {"topology": {"band_x": band, "on_bar": on_bar, "off_bar": off_bar,
                        "mitre_on_bar": bool(tp["mitre"]["s"][0] < rb),
                        "tab_width_mm": tp["width_mm"], "toggle_len_mm": TOGGLE_L_MM},
           "runs": runs, "k_vector_max": kv, "k_bound_max": kb,
           "k_vector_run": max(runs, key=lambda q: q["k_vector"]),
           "max_outboard_share": max(r_["outboard_share"] for r_ in runs),
           "max_inboard_share": -min(r_["outboard_share"] for r_ in runs)}
    rows = {}
    for key, k in (("bl041_scalar", 1.0), ("vector", kv), ("bound", kb)):
        e2 = dict(env, static_n=env["static_n"] * k, fatigue_peak_n=env["fatigue_peak_n"] * k,
                  proof_n=env["proof_n"] * k)
        rows[key] = {"k": k, "static_n": round(e2["static_n"], 1), "fatigue_peak_n": round(e2["fatigue_peak_n"], 1),
                     **{kk: round(float(vv), 3) for kk, vv in check_row(rc, w, e2, "A").items() if kk != "basis"}}
        if key != "bl041_scalar":
            rows[key + "_toggle_width"] = {"k": k, **{kk: round(float(vv), 3) for kk, vv in
                                                      check_row(rc, TOGGLE_L_MM, e2, "A").items() if kk != "basis"}}
    out["checks"] = rows
    # spine wall under the spine wrap (necked 25 mm), basis A, at the run tension (both runs pull outboard, the
    # wrap's net load on the spine is the difference; one side alone is the bound)
    from huntkit.fea.sections import from_spec as _fs
    sp = _fs(frame_spec()["frame"]["spine_section"])
    T_f = CASE_FACTOR * sl["guy_1g_envelope_n"] * max(out["max_outboard_share"], 0.0)
    cap = capacity(sp, tp["neck_w_mm"], "A", globals_=False)["capacity_n"]
    out["spine_wrap"] = {"run_tension_factored_n": round(T_f, 1), "capacity_n": round(cap, 1),
                         "sf": round(cap / max(T_f, 1e-9), 1), "width_mm": tp["neck_w_mm"]}
    out["proof_tl1_n"] = round(max(PROOF * env["static_n"] * kv, env["static_n"] * kv / 0.654), 0)
    return out


def legacy_reproduction() -> dict:
    """frame_cg_recheck.bar_local (the repo's check) against basis A here without the bar globals."""
    from huntkit.gendesign import frame_cg_recheck as R
    out = {}
    for F in (244.5, 288.0):
        old = R.bar_local(F, 25.0, over={})["tie"]["sf"]
        new = capacity(section("rev_c"), 25.0, "A", globals_=False)["capacity_n"] / F
        out[f"{F:g}"] = {"bar_local_sf": float(old), "basis_A_sf": float(new)}
    old_b = R.bar_local(210.0, 25.0)["tie"]["sf"]
    out["rev_b_210"] = {"bar_local_sf": float(old_b), "capacity_n": float(210.0 * old_b)}
    return out


# ============================================================================================ driver
def run() -> dict:
    sl = sim_loads()
    kl = kit_loads(sl)
    env = kl["envelope"]
    rc = section("rev_c")
    per_kit = {}
    for kit, L in kl.items():
        per_kit[kit] = {b: check_row(rc, 25.0, L, b) for b in ("A", "B", "C")}
    widths = list(range(15, 61))
    sweep = {b: [capacity(rc, float(w), b)["capacity_n"] for w in widths] for b in ("A", "B", "C")}
    fixes = fix_options(env)
    passing = [f for f in fixes if f["passes"]]
    light = min(passing, key=lambda f: f["d_mass_g"]) if passing else None
    rec = next((f for f in fixes if f["key"] == "b25_38"), None)
    # TL-1 with the recommended fix: proof, RT capacity, predicted ovalisation
    w_rec = rec["width_mm"]
    tl1 = {"proof_n": env["proof_n"], "proof_kg": env["proof_n"] / 9.80665,
           "rt_capacity_A_n": capacity(rc, w_rec, "A", knockdown=None)["capacity_n"],
           "kd_capacity_A_n": capacity(rc, w_rec, "A")["capacity_n"],
           "dD_A_mm": ovalisation(rc, env["proof_n"], w_rec, "A"),
           "dD_B_mm": ovalisation(rc, env["proof_n"], w_rec, "B"),
           "dD_C_mm": ovalisation(rc, env["proof_n"], w_rec, "C"),
           "bare25_rt_capacity_A_n": capacity(rc, 25.0, "A", knockdown=None)["capacity_n"],
           "bare25_dD_A_at_288": ovalisation(rc, 288.0, 25.0, "A"),
           "bare25_dD_B_at_288": ovalisation(rc, 288.0, 25.0, "B"),
           "bare25_dD_C_at_288": ovalisation(rc, 288.0, 25.0, "C")}
    tl1["kd_eff"] = tl1["kd_capacity_A_n"] / tl1["rt_capacity_A_n"]
    tl1["bar_rule_proof_n"] = env["static_n"] / tl1["kd_eff"]
    return {"date": "2026-11-13", "section": {"od": rc.dims["od"], "t": rc.dims["t"], "layup": rc.layup_str,
                                              "D22": float(rc.laminate.D[1, 1]), "A22": float(rc.laminate.A[1, 1]),
                                              "mass_g": bar_mass_g("rev_c")},
            "kit_sections": kit_sections(), "sim_loads": sl, "kit_loads": kl, "per_kit": per_kit,
            "sweep": {"widths": widths, **sweep}, "fixes": fixes,
            "lightest_passing": light["key"] if light else None, "recommended": rec["key"],
            "tl1": tl1, "verification": verification(), "legacy": legacy_reproduction(),
            "assumptions": ASSUMPTIONS}


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def plot(ctx: dict, path: Path | None = None) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    path = path or SCREENS / SHOT
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 12})
    fig, ax = plt.subplots(2, 2, figsize=(13, 11), dpi=100)
    env = ctx["kit_loads"]["envelope"]
    # (a) ring moment around the bar for the three bases, F = 100 N on 25 mm
    a = ax[0, 0]
    sec = section("rev_c")
    Rm = sec.dims["od"] / 2 - sec.dims["t"] / 2
    th = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
    for kind, lab, c in (("pair", "pair of point loads (Roark 1)", "#c0392b"),
                         ("point_shear", "point load on beam shear (B)", "#e67e22"),
                         ("wrap_shear", "180 deg strap wrap on beam shear (C)", "#2471a3")):
        p, q = load_pattern(kind, th, 100.0 / 25.0, Rm)
        r = ring_fourier(p, q, th, Rm, 600)
        a.plot(np.degrees(th), r["M"], color=c, lw=2, label=lab)
    for sgn in (1, -1):
        a.axhline(sgn * 0.318 * 100 / 25 * Rm, color="#c0392b", ls=":", lw=1.5,
                  label="basis A = 0.318 F R / w" if sgn > 0 else None)
    a.set_xlabel("angle round the bar from the pull direction, deg (strap on the back, 180)")
    a.set_ylabel("ring moment, N mm / mm (100 N on 25 mm)")
    a.set_title("(a) Wall bending round the bar")
    a.legend(fontsize=9, loc="lower left")
    a.set_xlim(0, 360)
    a.grid(alpha=0.3)
    # (b) capacity vs bearing width
    b = ax[0, 1]
    w = ctx["sweep"]["widths"]
    for k, c in (("A", "#c0392b"), ("B", "#e67e22")):
        b.plot(w, ctx["sweep"][k], color=c, lw=2, label=f"capacity, basis {k}")
    i25 = ctx["sweep"]["widths"].index(25)
    b.plot([], [], color="#2471a3", lw=2, label=f"basis C off scale ({ctx['sweep']['C'][i25]:.0f} N at 25 mm)")
    b.axhline(env["static_n"], color="k", lw=1.5, label=f"factored, guy + crown strap {env['static_n']:.0f} N")
    b.axhline(env["fatigue_peak_n"] / FI_FAT, color="k", ls="--", lw=1.5,
              label=f"fatigue need (1.6 g / 0.5) {env['fatigue_peak_n'] / FI_FAT:.0f} N")
    b.axvline(25, color="grey", ls=":")
    b.axvline(38, color="#1e8449", ls="-", lw=2)
    b.text(38.5, env["static_n"] * 0.55, "fix: 38 mm\nB-25 sleeve", color="#1e8449", fontsize=11)
    b.text(25.5, env["static_n"] * 0.55, "today\n25 mm", color="grey", fontsize=11)
    b.set_ylim(0, 1200)
    b.set_xlabel("bearing width on the bar, mm")
    b.set_ylabel("first-ply failure load (knocked down), N")
    b.set_title("(b) Bar wall capacity vs loop width")
    b.legend(fontsize=9, loc="upper left")
    b.grid(alpha=0.3)
    # (c) per-kit utilisation, basis A, today
    c = ax[1, 0]
    kits = ["S", "M", "L", "envelope"]
    st = [1 / ctx["per_kit"][k]["A"]["sf_static"] for k in kits]
    ft = [1 / ctx["per_kit"][k]["A"]["sf_fatigue"] for k in kits]
    fx = next(f for f in ctx["fixes"] if f["key"] == ctx["recommended"])
    xs = np.arange(len(kits))
    c.bar(xs - 0.2, st, 0.4, color="#c0392b", label="static: factored / capacity")
    c.bar(xs + 0.2, ft, 0.4, color="#7d3c98", label="fatigue: FI(1.6 g) / 0.5")
    c.axhline(1.0, color="k", lw=1.5)
    for i, k in enumerate(kits):
        L = ctx["kit_loads"][k]
        c.text(i, max(st[i], ft[i]) + 0.04, f"{L['static_n']:.0f} N", ha="center", fontsize=10)
    c.axhline(1 / fx["sf_fatigue"], color="#1e8449", ls="--", lw=2,
              label=f"with the 38 mm sleeve (worst {max(1 / fx['sf_fatigue'], 1 / fx['sf_static']):.2f})")
    c.set_xticks(xs, ["kit S", "kit M", "kit L", "envelope"])
    c.set_ylabel("utilisation (>1 fails)")
    c.set_ylim(0, 1.4)
    c.set_title("(c) Today's 25 mm sleeve, basis A, per crown kit")
    c.legend(fontsize=9, loc="upper left")
    c.grid(alpha=0.3, axis="y")
    # (d) fix options: mass vs worst utilisation
    d = ax[1, 1]
    for f in ctx["fixes"]:
        u = max(1 / f["sf_static"], 1 / f["sf_fatigue"])
        col = "#1e8449" if f["passes"] else ("#e67e22" if f["strength_ok"] else "#c0392b")
        d.scatter(f["d_mass_g"], u, s=90, color=col, zorder=3)
        d.annotate(f["key"], (f["d_mass_g"], u), textcoords="offset points", xytext=(6, 4), fontsize=10)
    d.axhline(1.0, color="k", lw=1.5)
    d.set_xlabel("mass change per pack, g")
    d.set_ylabel("worst utilisation, basis A (static or fatigue)")
    d.set_title("(d) Fixes: green pass, red fail, orange does not fit")
    d.grid(alpha=0.3)
    fig.suptitle("Crown top bar (OD 18, wall 1.065) under the B-25 guy / crown-strap sleeve, CORRIE F rev 3",
                 fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return path


def main(argv=None) -> int:
    ctx = run()
    RESULTS.write_text(json.dumps(_jsonable(ctx), indent=1))
    p = plot(ctx)
    env = ctx["kit_loads"]["envelope"]
    a = ctx["per_kit"]["envelope"]["A"]
    print(f"envelope static {env['static_n']:.1f} N ({env['static_case']}), fatigue peak {env['fatigue_peak_n']:.1f} N")
    print(f"basis A 25 mm: capacity {a['capacity_n']:.1f} N, SF static {a['sf_static']:.2f}, fatigue {a['sf_fatigue']:.2f}")
    for f in ctx["fixes"]:
        print(f"  {f['key']:12s} w {f['width_mm']:5.1f}  cap {f['capacity_n']:6.1f}  SF {f['sf_static']:.2f}  "
              f"fat {f['sf_fatigue']:.2f}  dm {f['d_mass_g']:+.2f} g  {'PASS' if f['passes'] else 'fail'}")
    print("results", RESULTS, "\nscreen", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
