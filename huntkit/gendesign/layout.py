"""Frame layout optimization.

1. Ground structure (truss layout, plastic design LP; Dorn-Gomory-Greenberg 1964 / Gilbert & Tyas
   2003): nodes = the frame hard points + every load/body-interface point of the frame model; candidate
   bars = all node pairs inside the frame envelope (no bar through the wearer zone y < -50 mm).
       min  sum_i L_i a_i      s.t.  B q_c = f_c,  -a_i sigma_c <= q_ic <= a_i sigma_t   (every case c)
   The loads f_c are the frame model's own external loads + body-spring reactions (+ d'Alembert loads
   for the set-down case), i.e. self-equilibrated sets taken from huntkit.fea for every case of the
   current standard at torso 15 / 19 / 23 in. Answers "where does material want to go".
2. Discrete check on buyable round carbon tubes: candidate topologies (current, X-braced bays,
   diagonal stays) are built as huntkit.fea frame models (the current pack5200 model + added bonded
   brace tubes), every tube group is re-sized over the roll-wrapped stock list, and every case is
   re-run (member first-ply SF and frame buckling against the standard). Brace joints are charged as
   printed Ti lugs.
"""
from __future__ import annotations

import copy
import itertools

import numpy as np
from scipy.optimize import linprog

from huntkit.fea.sections import from_spec


def ground_nodes(model: dict) -> dict:
    """User nodes of the frame model that carry load/body interfaces or are structural hard points."""
    keep = set()
    for grp in ("hipbelt", "shoulder", "lifter", "shelf_pivot", "shelf_strap", "lash", "foot_left", "foot_right", "bag"):
        keep |= set(model["groups"].get(grp, []))
    for j in model["joints"]:
        keep.add(j["node"])
    for t in ("L", "R"):
        for z in (190.0, 250.0, 420.0):
            nid = f"S{t}{z:g}"
            if nid in model["nodes"]:
                keep.add(nid)
    return {n: np.asarray(model["nodes"][n], float) for n in sorted(keep)}


def case_loads(res, model, gnodes: dict) -> np.ndarray:
    """Self-equilibrated nodal forces at the ground nodes from a solved frame case. Loads at nodes
    that are not ground nodes are moved to the nearest ground node (force only; the small transfer
    moment is ignored and the set is re-balanced by least squares)."""
    from .loads import external_on_node
    ids = list(gnodes)
    P = np.array([gnodes[i] for i in ids])
    f = np.zeros((len(ids), 3))
    for nid in model["nodes"]:
        v = external_on_node(res, model, nid)
        if not np.any(v[:3]):
            continue
        p = np.asarray(model["nodes"][nid], float)
        k = int(np.argmin(np.linalg.norm(P - p, axis=1)))
        f[k] += v[:3]
    # re-balance (force + moment) by the minimum-norm correction
    A = np.zeros((6, 3 * len(ids)))
    c = P.mean(0)
    for i, p in enumerate(P):
        A[:3, 3 * i: 3 * i + 3] = np.eye(3)
        r = p - c
        A[3:, 3 * i: 3 * i + 3] = np.array([[0, -r[2], r[1]], [r[2], 0, -r[0]], [-r[1], r[0], 0]])
    resid = A @ f.ravel()
    corr = A.T @ np.linalg.lstsq(A @ A.T, resid, rcond=None)[0]
    return (f.ravel() - corr), float(np.linalg.norm(resid[:3]))


def candidate_bars(gnodes: dict, max_len=520.0, min_len=8.0):
    ids = list(gnodes)
    bars = []
    for a, b in itertools.combinations(range(len(ids)), 2):
        pa, pb = gnodes[ids[a]], gnodes[ids[b]]
        L = np.linalg.norm(pb - pa)
        if L < min_len or L > max_len:
            continue
        mid = (pa + pb) / 2
        if mid[1] < -50:      # keep off the wearer's back
            continue
        bars.append((a, b, L))
    # remove overlapping collinear bars (keep the shortest pieces)
    out = []
    P = np.array([gnodes[i] for i in ids])
    for a, b, L in bars:
        d = (P[b] - P[a]) / L
        hit = False
        for k in range(len(ids)):
            if k in (a, b):
                continue
            s = (P[k] - P[a]) @ d
            if 1.0 < s < L - 1.0 and np.linalg.norm(P[a] + s * d - P[k]) < 1.0:
                hit = True
                break
        if not hit:
            out.append((a, b, L))
    return ids, out


def _skew(r):
    return np.array([[0, -r[2], r[1]], [r[2], 0, -r[0]], [-r[1], r[0], 0]])


def model_bars(model: dict, ids: list) -> list:
    """Current topology contracted onto the ground nodes: two ground nodes are joined when a chain of
    model members (through non-ground nodes) connects them. Plate shear diagonals are skipped."""
    import collections
    gset = set(ids)
    adj = collections.defaultdict(set)
    for mm in model["members"]:
        if mm["group"] in ("lumbar_plate_shear",):
            continue
        a, b = mm["nodes"]
        adj[a].add(b); adj[b].add(a)
    for ln in model.get("links", []):          # crown bushings + pawl
        a, b = ln["nodes"]
        adj[a].add(b); adj[b].add(a)
    pairs = set()
    for g0 in ids:
        seen, stack = {g0}, [g0]
        while stack:
            n = stack.pop()
            for k in adj[n]:
                if k in seen:
                    continue
                seen.add(k)
                if k in gset:
                    pairs.add(tuple(sorted((g0, k))))
                else:
                    stack.append(k)
    return sorted(pairs)


def frame_ground_structure(frame: dict, torsos=(15, 19, 23), r_tube=11.0, restrict=None, extra=(),
                           cases=None, max_len=520.0):
    """Plastic (lower-bound) layout LP for a FRAME ground structure (bending + axial + torsion).

    Each candidate member is a thin round tube of fixed mean radius ``r_tube`` and free wall area A:
        N_p = sigma_c A,  M_p = sigma_c A r / 2,  T_p = tau A r
    and every end must satisfy |N|/N_p + (|M_1| + |M_2|)/M_p <= 1, |T| <= T_p (linearised, conservative).
    Variables per member and case: the end force f and end moment m_a at node a (m_b follows from
    member equilibrium). Equilibrium at every ground node for every case. Objective: sum L_i A_i rho.

    restrict: None (full ground structure) or a list of (id_a, id_b) bars allowed; extra: bars to add.
    """
    import scipy.sparse as sp
    runs = frame["runs"]
    res0, m0, _ = next(iter(runs.values()))
    st = from_spec(next(mm for mm in m0["members"] if mm["group"].startswith("stay_upper"))["section"])
    lam, t = st.laminate, st.dims["t"]
    sig_t = 1.0 / lam.first_ply_failure((1.0, 0, 0), (0, 0, 0))["fi"] / t
    sig_c = 1.0 / lam.first_ply_failure((-1.0, 0, 0), (0, 0, 0))["fi"] / t
    tau = 1.0 / lam.first_ply_failure((0, 0, 1.0), (0, 0, 0))["fi"] / t
    rho = st.density_kg_m3 * 1e-6          # g/mm^3
    out = {}
    for t_in in torsos:
        names = [c for c in (cases or frame["cases"]) if (c, t_in) in runs]
        _, m_t, _ = runs[(names[0], t_in)]
        gn = ground_nodes(m_t)
        ids, cand = candidate_bars(gn, max_len=max_len)
        if restrict is not None:
            allowed = {tuple(sorted(p)) for p in list(restrict(m_t, ids) if callable(restrict) else restrict)}
            allowed |= {tuple(sorted(p)) for p in extra}
            idx = {n: i for i, n in enumerate(ids)}
            cand = []
            for a, b in allowed:
                if a in idx and b in idx:
                    L = np.linalg.norm(gn[a] - gn[b])
                    cand.append((idx[a], idx[b], L))
        P = np.array([gn[i] for i in ids])
        nb, nn, nc = len(cand), len(ids), len(names)
        Ls = np.array([L for *_, L in cand])
        # per member geometry
        D = np.array([(P[b] - P[a]) / L for a, b, L in cand])
        E1 = np.zeros_like(D); E2 = np.zeros_like(D)
        for k, d in enumerate(D):
            ref = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
            e1 = np.cross(d, ref); e1 /= np.linalg.norm(e1)
            E1[k], E2[k] = e1, np.cross(d, e1)
        # variable layout: A (nb) | per case: f (3nb), m (3nb), aux |N| (nb), |M1a|,|M2a|,|M1b|,|M2b| (4nb)
        per = 3 * nb + 3 * nb + nb + 4 * nb
        nv = nb + nc * per
        cost = np.zeros(nv); cost[:nb] = Ls * rho
        eq_r, eq_c, eq_v, beq = [], [], [], []
        ub_r, ub_c, ub_v = [], [], []
        row_eq = 0
        row_ub = 0
        Np = sig_c; Mp = sig_c * r_tube / 2; Tp = tau * r_tube
        for c, cname in enumerate(names):
            res, model, cs = runs[(cname, t_in)]
            f_ext, _ = case_loads(res, model, gn)
            # moments: external nodal moments at ground nodes (forces only from case_loads) -> none
            base = nb + c * per
            fo, mo, No, Mo = base, base + 3 * nb, base + 6 * nb, base + 7 * nb
            # nodal equilibrium: sum over members of (force/moment member exerts on node) = -external
            for k, (a, b, L) in enumerate(cand):
                rab = P[b] - P[a]
                S = _skew(rab)
                for d in range(3):
                    # forces: node a gets f, node b gets -f
                    eq_r += [3 * a + d, 3 * b + d]; eq_c += [fo + 3 * k + d] * 2; eq_v += [1.0, -1.0]
                    # moments: node a gets m_a; node b gets -m_a + rab x f
                    eq_r += [3 * nn + 3 * a + d, 3 * nn + 3 * b + d]
                    eq_c += [mo + 3 * k + d] * 2; eq_v += [1.0, -1.0]
                    for e in range(3):
                        if S[d, e]:
                            eq_r.append(3 * nn + 3 * b + d); eq_c.append(fo + 3 * k + e); eq_v.append(S[d, e])
            eq_r = [r + row_eq if i >= len(beq) * 0 else r for i, r in enumerate(eq_r)]  # placeholder
            beq_c = np.r_[-f_ext * cs.required_sf, np.zeros(3 * nn)]
            # shift rows of this case
            nrow = 6 * nn
            # (rows were added unshifted for this case: shift the slice appended in this loop)
            beq.append(beq_c)
            # capacity constraints
            for k, (a, b, L) in enumerate(cand):
                d, e1, e2 = D[k], E1[k], E2[k]
                rab = P[b] - P[a]
                fk = [fo + 3 * k + i for i in range(3)]
                mk = [mo + 3 * k + i for i in range(3)]
                # N = d.f ; |N| <= aux
                for sg in (1, -1):
                    ub_r += [row_ub] * 4; ub_c += fk + [No + k]; ub_v += [sg * d[0], sg * d[1], sg * d[2], -1.0]; row_ub += 1
                # end a moments: e1.m_a, e2.m_a ; end b: m_b = -m_a + rab x f  -> e.m_b = -e.m_a + (e . (rab x f)) = -e.m_a + (f . (e x rab))... use (e x ... )
                for j, e in enumerate((e1, e2)):
                    for sg in (1, -1):
                        ub_r += [row_ub] * 4; ub_c += mk + [Mo + j * nb + k]; ub_v += [sg * e[0], sg * e[1], sg * e[2], -1.0]; row_ub += 1
                    w = np.cross(rab, e)       # e.(rab x f) = f.(e x rab) = -f.(rab x e)
                    for sg in (1, -1):
                        ub_r += [row_ub] * 7
                        ub_c += mk + fk + [Mo + (2 + j) * nb + k]
                        ub_v += [-sg * e[0], -sg * e[1], -sg * e[2], -sg * w[0], -sg * w[1], -sg * w[2], -1.0]
                        row_ub += 1
                # combined at both ends: aux_N/Np + (aux_M1 + aux_M2)/Mp - A <= 0
                for end in (0, 1):
                    ub_r += [row_ub] * 4
                    ub_c += [No + k, Mo + (2 * end) * nb + k, Mo + (2 * end + 1) * nb + k, k]
                    ub_v += [1 / Np, 1 / Mp, 1 / Mp, -1.0]; row_ub += 1
                # torsion |d.m_a| <= Tp A
                for sg in (1, -1):
                    ub_r += [row_ub] * 4; ub_c += mk + [k]; ub_v += [sg * d[0], sg * d[1], sg * d[2], -Tp]; row_ub += 1
        # assemble equality with per-case row offsets: rebuild cleanly
        Aeq_blocks = []
        # Rebuild equality per case (simpler and correct): structure is identical for all cases
        rows0, cols0, vals0 = [], [], []
        for k, (a, b, L) in enumerate(cand):
            S = _skew(P[b] - P[a])
            for d in range(3):
                rows0 += [3 * a + d, 3 * b + d]; cols0 += [3 * k + d] * 2; vals0 += [1.0, -1.0]
                rows0 += [3 * nn + 3 * a + d, 3 * nn + 3 * b + d]; cols0 += [3 * nb + 3 * k + d] * 2; vals0 += [1.0, -1.0]
                for e in range(3):
                    if S[d, e]:
                        rows0.append(3 * nn + 3 * b + d); cols0.append(3 * k + e); vals0.append(S[d, e])
        rows0, cols0, vals0 = np.array(rows0), np.array(cols0), np.array(vals0)
        R, C, V = [], [], []
        for c in range(nc):
            R.append(rows0 + c * 6 * nn); C.append(cols0 + nb + c * per); V.append(vals0)
        Aeq = sp.csr_matrix((np.concatenate(V), (np.concatenate(R), np.concatenate(C))), shape=(6 * nn * nc, nv))
        beq = np.concatenate(beq)
        Aub = sp.csr_matrix((ub_v, (ub_r, ub_c)), shape=(row_ub, nv))
        bounds = [(0, None)] * nb + ([(None, None)] * (6 * nb) + [(0, None)] * (5 * nb)) * nc
        sol = linprog(cost, A_ub=Aub, b_ub=np.zeros(row_ub), A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
        A = sol.x[:nb] if sol.success else np.full(nb, np.nan)
        out[t_in] = {"ids": ids, "P": P, "bars": cand, "area": A, "status": sol.message, "success": bool(sol.success),
                     "mass_g": float(cost[:nb] @ A) if sol.success else np.inf, "cases": names,
                     "sigma_c": sig_c, "tau": tau, "r_tube": r_tube}
    return out


def classify_bar(P, a, b):
    """'stay' (vertical-ish on one side), 'cross' (horizontal across), 'diagonal' (crosses the centreline
    with a vertical component), 'local'."""
    pa, pb = P[a], P[b]
    d = pb - pa
    L = np.linalg.norm(d)
    if np.sign(pa[0]) == np.sign(pb[0]) and abs(pa[0]) > 40 and abs(pb[0]) > 40:
        return "stay/side"
    if abs(d[2]) < 0.25 * L:
        return "cross"
    return "diagonal"


# ----------------------------------------------------------------------------- discrete topology check
TOPOLOGIES = {
    "current": [],
    "X_upper_bay": [("SL330", "SR520"), ("SR330", "SL520")],              # X between mid bar and upper bar
    "X_lower_bay": [("SL190", "SR330"), ("SR190", "SL330")],              # X between plate top and mid bar
    "V_lower": [("SL330", "HPX"), ("SR330", "HPX")],                      # V from mid-bar nodes to the plate top centre
    "X_both_bays": [("SL330", "SR520"), ("SR330", "SL520"), ("SL190", "SR330"), ("SR190", "SL330")],
}


def add_braces(model: dict, pairs, section) -> dict:
    m = copy.deepcopy(model)
    added = []
    for a, b in pairs:
        if b == "HPX":     # plate top-centre node
            b = m["plate_grid"].get("4,2", b)
        if a not in m["nodes"] or b not in m["nodes"]:
            continue
        mid = f"brace_{a}_{b}"
        m["members"].append({"id": mid, "nodes": [a, b], "section": section, "material": None,
                             "group": "brace", "ref": [0.0, 0.0, 1.0] if False else [1.0, 0.0, 0.0], "nseg": 2})
        added.append(mid)
    m["_braces"] = added
    return m


GROUPS = ("stay", "mid_bar", "upper_bar", "brace", "lumbar_plate")   # members the bracing can relieve


def evaluate_topology(frame_params_over: dict, braces, stay_spec, bar_spec, brace_spec, cases, torsos=(15, 19, 23)):
    """Member first-ply margin (SF / required) and buckling margin (vs 1.5 x factor, HA-LS-1) at all
    torsos; mass of tubes (+ brace lugs)."""
    from huntkit.fea.frames import build_frame_from_yaml
    from .loads import FRAME_YAML
    from huntkit.fea.sizing import make_section
    worst_m, worst_b, gov = np.inf, np.inf, ""
    mass = None
    for t in torsos:
        p = {"torso_in": float(t), "stay_section": make_section(stay_spec)}
        if bar_spec is not None:
            p["bar_section"] = make_section(bar_spec)
        p.update(frame_params_over)
        base = build_frame_from_yaml(FRAME_YAML, **p)
        m = add_braces(base, braces, make_section(brace_spec)) if braces else base
        for c in cases:
            if c.name == "tall_load_posts":
                continue
            cc = copy.copy(c)
            cc.buckling = True
            r = cc.run(m)
            req = r.meta["required_sf"]
            grp = [x for x in r.members if x["group"].startswith(GROUPS)]
            crit = min(grp, key=lambda x: x["sf"])
            mm = crit["sf"] / req
            if mm < worst_m:
                worst_m, gov = mm, f"{c.name}@{t}: {crit['id']}"
            if r.buckling_factors:
                worst_b = min(worst_b, r.buckling_sf / (1.5 * req))
        if mass is None:
            mass = tube_mass_g(m)
    return {"member_margin": worst_m, "buckling_margin": worst_b, "governing": gov, **mass}


def tube_mass_g(model) -> dict:
    tot, br = 0.0, 0.0
    for mm in model["members"]:
        s = from_spec(mm["section"])
        if not getattr(s, "composite", False):
            continue
        L = np.linalg.norm(np.subtract(model["nodes"][mm["nodes"][1]], model["nodes"][mm["nodes"][0]]))
        g = s.density_kg_m3 * s.A * 1e-9 * L * 1e3
        if mm["group"].startswith("crown_leg"):
            continue
        tot += g
        if mm["group"] == "brace":
            br += g
    return {"tubes_g": tot, "brace_tubes_g": br, "n_braces": len(model.get("_braces", []))}
