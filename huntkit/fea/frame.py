"""3D frame (6 DOF/node) linear static and linear buckling solver.

Model format (plain dict, YAML-friendly; units mm, N, MPa, kg)::

    {
      "nodes":   {"A": [x, y, z], ...},
      "members": [{"id": "m1", "nodes": ["A", "B"],
                   "section": Section | {"type": "tube_round", "od": 12.7, "t": 0.9},
                   "material": "alu_7075_t6" | {inline props} | None (composite sections),
                   "ref": [0, 0, 1],        # optional orientation vector -> local +y
                   "type": "frame" | "truss",
                   "group": "stay_left",    # optional, for reporting
                   "nseg": 4}],             # optional internal subdivision
      "supports": {"A": "fixed" | "pinned" | {"fix": "xyz rx", "spring": [kx,ky,kz,krx,kry,krz]}},
      "loads":    {"B": [Fx, Fy, Fz, Mx, My, Mz]},
      "masses":   {"B": kg},                # lumped, only used for inertia relief
      "inertia_relief": False,              # True -> free-free solve, loads balanced by d'Alembert
      "settings": {"nseg": 1, "timoshenko": False},
    }

Element: Euler-Bernoulli (default) or Timoshenko (``settings.timoshenko``) 12x12 beam with the
consistent geometric stiffness for linear buckling ``(K + lambda*Kg) phi = 0``.

Orientation: local x runs from node 1 to node 2; the reference vector ``ref`` (default global Z,
or global X for members within ~8 deg of Z) is projected normal to x to give local +y;
local z = x cross y.

Spring stiffnesses are in global axes (N/mm, N*mm/rad). Reactions include spring forces.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .materials_bridge import E_of, G_of, get_material, rho_of
from .sections import Section, from_spec

DOF_NAMES = ["x", "y", "z", "rx", "ry", "rz"]
G_ACC = 9.80665  # m/s^2


def _parse_dofs(spec) -> list[int]:
    if isinstance(spec, (list, tuple)):
        return [DOF_NAMES.index(s) if isinstance(s, str) else int(s) for s in spec]
    toks = str(spec).replace(",", " ").split()
    out = []
    for tok in toks:
        if tok in DOF_NAMES:
            out.append(DOF_NAMES.index(tok))
        else:  # e.g. "xyz"
            out += [DOF_NAMES.index(c) for c in tok]
    return out


def _support(spec):
    """-> (fixed dof list, spring 6-vector)"""
    k = np.zeros(6)
    if spec in ("fixed", "clamped"):
        return list(range(6)), k
    if spec == "pinned":
        return [0, 1, 2], k
    if isinstance(spec, dict):
        fixed = _parse_dofs(spec.get("fix", []))
        if "spring" in spec:
            s = spec["spring"]
            if isinstance(s, dict):
                for kk, v in s.items():
                    k[DOF_NAMES.index(kk)] = v
            else:
                k[: len(s)] = s
        return fixed, k
    return _parse_dofs(spec), k


# ----------------------------------------------------------------------------- element matrices
def k_local(L, EA, EIy, EIz, GJ, phiy=0.0, phiz=0.0, truss=False) -> np.ndarray:
    k = np.zeros((12, 12))
    k[0, 0] = k[6, 6] = EA / L
    k[0, 6] = k[6, 0] = -EA / L
    if truss:
        return k
    k[3, 3] = k[9, 9] = GJ / L
    k[3, 9] = k[9, 3] = -GJ / L
    # bending in x-y plane (v, theta_z), uses Iz
    a = EIz / (L ** 3 * (1 + phiy))
    b = 12 * a; c = 6 * a * L; d = (4 + phiy) * a * L * L; e = (2 - phiy) * a * L * L
    for (i, j, v) in [(1, 1, b), (1, 5, c), (1, 7, -b), (1, 11, c), (5, 5, d), (5, 7, -c),
                      (5, 11, e), (7, 7, b), (7, 11, -c), (11, 11, d)]:
        k[i, j] = k[j, i] = v
    # bending in x-z plane (w, theta_y), uses Iy
    a = EIy / (L ** 3 * (1 + phiz))
    b = 12 * a; c = 6 * a * L; d = (4 + phiz) * a * L * L; e = (2 - phiz) * a * L * L
    for (i, j, v) in [(2, 2, b), (2, 4, -c), (2, 8, -b), (2, 10, -c), (4, 4, d), (4, 8, c),
                      (4, 10, e), (8, 8, b), (8, 10, c), (10, 10, d)]:
        k[i, j] = k[j, i] = v
    return k


def kg_local(L, P, Ip_over_A, truss=False) -> np.ndarray:
    """Consistent geometric stiffness for axial force P (tension positive)."""
    g = np.zeros((12, 12))
    if truss:
        for i in (1, 2):
            g[i, i] = g[i + 6, i + 6] = 1.0
            g[i, i + 6] = g[i + 6, i] = -1.0
        return g * P / L
    for (i, j, v) in [(1, 1, 6 / 5), (1, 5, L / 10), (1, 7, -6 / 5), (1, 11, L / 10),
                      (5, 5, 2 * L * L / 15), (5, 7, -L / 10), (5, 11, -L * L / 30),
                      (7, 7, 6 / 5), (7, 11, -L / 10), (11, 11, 2 * L * L / 15),
                      (2, 2, 6 / 5), (2, 4, -L / 10), (2, 8, -6 / 5), (2, 10, -L / 10),
                      (4, 4, 2 * L * L / 15), (4, 8, L / 10), (4, 10, -L * L / 30),
                      (8, 8, 6 / 5), (8, 10, L / 10), (10, 10, 2 * L * L / 15),
                      (3, 3, Ip_over_A), (3, 9, -Ip_over_A), (9, 9, Ip_over_A)]:
        g[i, j] = g[j, i] = v
    return g * P / L


def rotation(p1, p2, ref=None) -> np.ndarray:
    x = np.asarray(p2, float) - np.asarray(p1, float)
    L = np.linalg.norm(x)
    if L == 0:
        raise ValueError("zero-length element")
    x /= L
    if ref is None:
        ref = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
    ref = np.asarray(ref, float)
    y = ref - ref.dot(x) * x
    if np.linalg.norm(y) < 1e-9:
        raise ValueError("reference vector parallel to member axis")
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return np.vstack([x, y, z])


def _T12(R):
    T = np.zeros((12, 12))
    for i in range(4):
        T[3 * i: 3 * i + 3, 3 * i: 3 * i + 3] = R
    return T


# ----------------------------------------------------------------------------- data structures
@dataclass
class Element:
    member: int
    n1: int
    n2: int
    L: float
    T: np.ndarray
    k: np.ndarray            # local stiffness
    props: dict
    truss: bool


@dataclass
class Result:
    name: str
    model: dict
    node_ids: list
    coords: np.ndarray                 # (n, 3) incl. internal sub-nodes
    n_user_nodes: int
    u: np.ndarray                      # (ndof,)
    elements: list
    elem_forces: np.ndarray            # (ne, 2, 6) internal forces N,Vy,Vz,T,My,Mz at both ends
    elem_check: list                   # per element dict (von_mises / fi, sf ...)
    members: list                      # per member summary dict
    reactions: dict
    buckling_factors: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def displacements(self) -> dict:
        U = self.u.reshape(-1, 6)
        return {nid: U[i] for i, nid in enumerate(self.node_ids[: self.n_user_nodes])}

    @property
    def member_forces(self) -> dict:
        return {m["id"]: {"start": m["end_forces"][0], "end": m["end_forces"][1],
                          "max_abs": m["max_abs_forces"]} for m in self.members}

    @property
    def min_sf(self) -> float:
        return float(min(m["sf"] for m in self.members)) if self.members else np.inf

    @property
    def max_sf(self) -> float:
        """Contract name (docs/CONTRACTS.md §2). This is the *governing* strength safety factor
        of the structure, i.e. the minimum member SF (the largest SF one can claim)."""
        return self.min_sf

    @property
    def critical_member(self) -> dict:
        return min(self.members, key=lambda m: m["sf"])

    @property
    def buckling_sf(self) -> float:
        pos = [b for b in self.buckling_factors if b > 0]
        return float(min(pos)) if pos else np.inf

    @property
    def mass_kg(self) -> float:
        return float(sum(m["mass_kg"] for m in self.members))

    def max_displacement(self) -> float:
        U = self.u.reshape(-1, 6)[:, :3]
        return float(np.linalg.norm(U, axis=1).max())


# ----------------------------------------------------------------------------- build & solve
def _member_props(mem: dict, sec: Section):
    if sec.composite:
        st = sec.stiffness()
        rho = sec.density_kg_m3
        mat = None
    else:
        mat = get_material(mem["material"])
        st = sec.stiffness(E_of(mat), G_of(mat))
        rho = rho_of(mat)
    st["Ip_over_A"] = sec.Ip / sec.A
    st["rho_lin"] = rho * sec.A * 1e-9   # kg/mm
    return st, mat


def build(model: dict):
    settings = {"nseg": 1, "timoshenko": False, **model.get("settings", {})}
    node_ids = list(model["nodes"].keys())
    idx = {n: i for i, n in enumerate(node_ids)}
    coords = [np.asarray(model["nodes"][n], float) for n in node_ids]
    n_user = len(node_ids)
    elements: list[Element] = []
    mem_info = []
    for mi, mem in enumerate(model["members"]):
        sec = from_spec(mem["section"])
        props, mat = _member_props(mem, sec)
        a, b = mem["nodes"]
        p1, p2 = coords[idx[a]], coords[idx[b]]
        nseg = int(mem.get("nseg", settings["nseg"]))
        truss = mem.get("type", "frame") == "truss"
        if truss:
            nseg = 1
        R = rotation(p1, p2, mem.get("ref"))
        chain = [idx[a]]
        for s in range(1, nseg):
            nid = f"{mem.get('id', mi)}#{s}"
            node_ids.append(nid)
            coords.append(p1 + (p2 - p1) * s / nseg)
            chain.append(len(coords) - 1)
        chain.append(idx[b])
        Lm = float(np.linalg.norm(p2 - p1))
        L = Lm / nseg
        phiy = phiz = 0.0
        if settings["timoshenko"] and not truss:
            phiy = 12 * props["EIz"] / (props["GAy"] * L * L)
            phiz = 12 * props["EIy"] / (props["GAz"] * L * L)
        kl = k_local(L, props["EA"], props["EIy"], props["EIz"], props["GJ"], phiy, phiz, truss)
        T = _T12(R)
        for s in range(nseg):
            elements.append(Element(mi, chain[s], chain[s + 1], L, T, kl, props, truss))
        mem_info.append({"id": str(mem.get("id", mi)), "group": mem.get("group", str(mem.get("id", mi))),
                         "section": sec, "material": mat, "L": Lm, "props": props,
                         "mass_kg": props["rho_lin"] * Lm})
    return node_ids, np.array(coords), n_user, elements, mem_info, idx


def _assemble(n_dof, elements, which="k", P=None):
    rows, cols, vals = [], [], []
    for e, el in enumerate(elements):
        if which == "k":
            kl = el.k
        else:
            kl = kg_local(el.L, P[e], el.props["Ip_over_A"], el.truss)
        kg = el.T.T @ kl @ el.T
        dofs = np.r_[6 * el.n1: 6 * el.n1 + 6, 6 * el.n2: 6 * el.n2 + 6]
        rr, cc = np.meshgrid(dofs, dofs, indexing="ij")
        rows.append(rr.ravel()); cols.append(cc.ravel()); vals.append(kg.ravel())
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                         shape=(n_dof, n_dof))


def rigid_body_modes(coords: np.ndarray, center=None) -> np.ndarray:
    n = len(coords)
    c = coords.mean(axis=0) if center is None else np.asarray(center)
    Phi = np.zeros((6 * n, 6))
    for i, p in enumerate(coords):
        r = p - c
        for k in range(3):
            Phi[6 * i + k, k] = 1.0
            ek = np.zeros(3); ek[k] = 1.0
            Phi[6 * i: 6 * i + 3, 3 + k] = np.cross(ek, r)
            Phi[6 * i + 3 + k, 3 + k] = 1.0
    return Phi


def solve(model: dict, buckling: bool = False, n_modes: int = 3, name: str = "") -> Result:
    """Linear static solve (optionally followed by linear buckling)."""
    node_ids, coords, n_user, elements, mem_info, idx = build(model)
    nn = len(node_ids)
    n_dof = 6 * nn
    K = _assemble(n_dof, elements, "k").tolil()
    F = np.zeros(n_dof)
    for nid, f in (model.get("loads") or {}).items():
        f = np.asarray(f, float)
        F[6 * idx[nid]: 6 * idx[nid] + len(f)] += f

    fixed = set()
    springs = {}
    for nid, spec in (model.get("supports") or {}).items():
        fx, kv = _support(spec)
        i = idx[nid]
        fixed |= {6 * i + d for d in fx}
        if np.any(kv):
            springs[nid] = kv
            for d in range(6):
                K[6 * i + d, 6 * i + d] += kv[d]
    K = K.tocsr()

    # DOFs with no stiffness at all (e.g. rotations at pure-truss nodes): constrain them.
    diag = K.diagonal()
    scale = np.abs(diag).max() if diag.size else 1.0
    fixed |= set(np.where(np.abs(diag) < 1e-12 * scale)[0].tolist())

    inertia = bool(model.get("inertia_relief", False))
    meta = {"inertia_relief": inertia}
    if inertia:
        if model.get("supports"):
            raise ValueError("inertia_relief models must not have supports")
        mvec = np.zeros(n_dof)
        for nid, m in (model.get("masses") or {}).items():
            mvec[6 * idx[nid]: 6 * idx[nid] + 3] += m * 1e-3   # kg -> tonne (N, mm, s consistent)
        Phi = rigid_body_modes(coords)
        Mrr = Phi.T @ (mvec[:, None] * Phi)
        acc = np.linalg.solve(Mrr, Phi.T @ F)          # rigid-body accelerations (mm/s^2, rad/s^2)
        F_in = -mvec * (Phi @ acc)
        meta["rigid_acc"] = acc
        meta["inertia_forces"] = F_in
        F = F + F_in
        free = np.array(sorted(set(range(n_dof)) - fixed))
        Kf = K[free][:, free]
        Pf = sp.csr_matrix(Phi[free])
        Z = sp.csr_matrix((6, 6))
        A_aug = sp.bmat([[Kf, Pf], [Pf.T, Z]]).tocsc()
        sol = spla.spsolve(A_aug, np.r_[F[free], np.zeros(6)])
        u = np.zeros(n_dof)
        u[free] = sol[: len(free)]
    else:
        free = np.array(sorted(set(range(n_dof)) - fixed))
        Kf = K[free][:, free].tocsc()
        u = np.zeros(n_dof)
        u[free] = spla.spsolve(Kf, F[free])

    # reactions
    Rfull = K @ u - F
    reactions = {}
    fixed_arr = np.array(sorted(fixed), dtype=int)
    for nid in (model.get("supports") or {}):
        i = idx[nid]
        kv = springs.get(nid, np.zeros(6))
        r = np.array([Rfull[6 * i + d] if (6 * i + d) in fixed else -kv[d] * u[6 * i + d]
                      for d in range(6)])
        reactions[nid] = r
    meta["fixed_dofs"] = fixed_arr

    # element forces & checks
    ne = len(elements)
    ef = np.zeros((ne, 2, 6))
    checks = []
    for e, el in enumerate(elements):
        ue = np.r_[u[6 * el.n1: 6 * el.n1 + 6], u[6 * el.n2: 6 * el.n2 + 6]]
        fl = el.k @ (el.T @ ue)
        ef[e, 0] = -fl[:6]
        ef[e, 1] = fl[6:]
        mi = mem_info[el.member]
        sec = mi["section"]
        worst = None
        for end in range(2):
            N, Vy, Vz, Tq, My, Mz = ef[e, end]
            if sec.composite:
                r = sec.failure(N, Vy, Vz, Tq, My, Mz)
                r["sigma_axial"] = N / sec.A
            else:
                r = sec.stresses(N, Vy, Vz, Tq, My, Mz)
                fy = mi["material"].require("yield_strength_mpa")
                r["sf"] = fy / r["von_mises"] if r["von_mises"] > 0 else np.inf
            if worst is None or r["sf"] < worst["sf"]:
                worst = dict(r, end=end)
        checks.append(worst)

    members = []
    for mi_i, mi in enumerate(mem_info):
        els = [e for e, el in enumerate(elements) if el.member == mi_i]
        sfs = [checks[e]["sf"] for e in els]
        k = els[int(np.argmin(sfs))]
        summ = {"id": mi["id"], "group": mi["group"], "section": mi["section"].label(),
                "material": (mi["material"].id if mi["material"] is not None
                             else getattr(mi["section"], "laminate").plies[0].name),
                "L": mi["L"], "mass_kg": mi["mass_kg"], "sf": float(min(sfs)),
                "check": checks[k], "elements": els,
                "end_forces": (ef[els[0], 0], ef[els[-1], 1]),
                "max_abs_forces": np.abs(ef[els]).reshape(-1, 6).max(axis=0)}
        if mi["section"].composite:
            summ["fi"] = 1 / summ["sf"] if summ["sf"] > 0 else np.inf
        else:
            summ["von_mises"] = checks[k]["von_mises"]
        members.append(summ)

    res = Result(name=name or model.get("name", ""), model=model, node_ids=node_ids, coords=coords,
                 n_user_nodes=n_user, u=u, elements=elements, elem_forces=ef, elem_check=checks,
                 members=members, reactions=reactions, meta=meta)

    if buckling and not inertia:
        P = ef[:, 1, 0]     # axial force (tension +)
        Kg = _assemble(n_dof, elements, "g", P)
        res.buckling_factors = buckling_factors(K, Kg, free, n_modes)
    return res


def buckling_factors(K, Kg, free, n_modes=3) -> list:
    """Smallest positive lambda with (K + lambda Kg) phi = 0 on the free DOFs."""
    Kf = K[free][:, free]
    Gf = Kg[free][:, free]
    if abs(Gf).max() == 0:
        return []
    if len(free) <= 3000:
        mu = sla.eigh(-Gf.toarray(), Kf.toarray(), eigvals_only=True)
    else:
        mu = spla.eigsh(-Gf.tocsc(), k=min(20, len(free) - 2), M=Kf.tocsc(), which="LA",
                        return_eigenvectors=False)
    mu = np.sort(mu[mu > 1e-12])[::-1]
    return [float(1 / m) for m in mu[:n_modes]]
