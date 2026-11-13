"""Geometric non-linear (large-displacement, small-strain) 3D frame solver: co-rotational beams, tension-only
cables, co-rotated spring links, dead and follower loads. BL-047 (crown buckling with the real top-bar offset).

Same model dict as :mod:`huntkit.fea.frame` (nodes, members, supports, links, loads; the members are built by
``frame.build`` so sections, materials, ``nseg`` and truss members mean the same), plus:

    "cables":   [{"id": "lift_L", "nodes": ["TB0", "LB_L"], "EA": 8.9e4, "L0": None}]   # tension-only, follower
    "follower": {"TB0": [Fx, Fy, Fz]}     # nodal forces that turn with the node (per unit load factor)
    "contacts": [{"node": "P22", "dir": [0, -1, 0], "k": 3.3, "gap": 0.0}]   # one-sided grounded springs

Element: the linear 12-dof beam of ``frame.k_local`` in a co-rotated frame (Crisfield's simplified co-rotational
beam): the chord gives local x, the mean of the two end triads' local-y gives local y; the end rotations relative to
that frame are taken by the matrix logarithm. Internal force = R^T k d_local; tangent = R^T (k + kg(N)) R (the
consistent geometric stiffness of ``frame.kg_local`` with the current axial force). Exact for rigid-body motion of
any size; small strain. Rotational DOFs are spatial spins (global axes), updated by R <- exp(dtheta) R.

Cables: tension T = EA (l - L0) / L0 when l > L0, else 0; tangent EA/L0 n n^T + T/l (I - n n^T) (the string
stiffness that a linear spring support leaves out). Links (``frame`` node-to-node springs, global axes at rest)
turn with the rotation of their first node, so a bushing's free sliding direction follows the tube.

Solution path: Newton-Raphson under load control with step halving (``path``). The smallest eigenvalue of the
tangent stiffness is tracked; it crossing zero (or Newton failing below the step floor) is the limit / bifurcation
point. Units mm, N, MPa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.spatial.transform import Rotation

from .frame import _support, build, kg_local


def _rotvec(Rm: np.ndarray) -> np.ndarray:
    return Rotation.from_matrix(Rm).as_rotvec()


def _expm(v: np.ndarray) -> np.ndarray:
    return Rotation.from_rotvec(v).as_matrix()


@dataclass
class PathPoint:
    lam: float
    u: np.ndarray            # (nn, 6): translations and rotation vectors
    min_eig: float
    iters: int
    cable_t: dict = field(default_factory=dict)


class GNL:
    """Co-rotational solver for one model. ``imperfection``: (nn_user, 3) translations added to the user nodes'
    coordinates before anything is built (an imperfect stress-free geometry)."""

    def __init__(self, model: dict, imperfection: dict | None = None, reg_k: float = 0.0):
        m = dict(model)
        if imperfection:
            m["nodes"] = {k: list(np.asarray(v, float) + np.asarray(imperfection.get(k, (0, 0, 0)), float))
                          for k, v in model["nodes"].items()}
        self.model = m
        node_ids, coords, n_user, elements, mem_info, idx = build(m)
        self.node_ids, self.X0, self.n_user, self.idx = node_ids, coords.copy(), n_user, idx
        self.elements, self.mem_info = elements, mem_info
        nn = len(node_ids)
        self.nn, self.ndof = nn, 6 * nn
        ne = len(elements)
        self.n1 = np.array([e.n1 for e in elements], int)
        self.n2 = np.array([e.n2 for e in elements], int)
        self.L0 = np.array([e.L for e in elements], float)
        self.R0 = np.array([e.T[:3, :3] for e in elements]).reshape(-1, 3, 3)            # rows = local axes (global comps)
        self.k = np.array([e.k for e in elements]).reshape(-1, 12, 12)
        G = np.zeros((ne, 12, 12))
        for i, e in enumerate(elements):
            if not e.props.get("no_kg"):
                G[i] = kg_local(e.L, 1.0, e.props["Ip_over_A"], e.truss)   # kg per unit axial force
        self.G = G
        # element dof map
        self.edofs = np.hstack([6 * self.n1[:, None] + np.arange(6), 6 * self.n2[:, None] + np.arange(6)]).astype(int)
        # supports
        fixed, springs = set(), {}
        for nid, spec in (m.get("supports") or {}).items():
            fx, kv = _support(spec)
            i = idx[nid]
            fixed |= {6 * i + d for d in fx}
            if np.any(kv):
                springs[i] = np.asarray(kv, float)
        self.springs = springs
        self.links = []
        for ln in m.get("links") or []:
            kv = np.zeros(6)
            kv[: len(ln["k"])] = ln["k"]
            self.links.append((idx[ln["nodes"][0]], idx[ln["nodes"][1]], kv, ln.get("id", "")))
        self.cables = []
        for c in m.get("cables") or []:
            a, b = idx[c["nodes"][0]], idx[c["nodes"][1]]
            L0 = c.get("L0")
            if L0 is None:
                L0 = float(np.linalg.norm(self.X0[b] - self.X0[a])) * (1.0 - float(c.get("pre_strain", 0.0)))
            self.cables.append((a, b, float(c["EA"]), float(L0), c.get("id", f"c{len(self.cables)}")))
        self.contacts = [(idx[c["node"]], np.asarray(c["dir"], float) / np.linalg.norm(c["dir"]), float(c["k"]),
                          float(c.get("gap", 0.0))) for c in (m.get("contacts") or [])]
        self.reg_k = float(reg_k)
        F = np.zeros(self.ndof)
        for nid, f in (m.get("loads") or {}).items():
            f = np.asarray(f, float)
            F[6 * idx[nid]: 6 * idx[nid] + len(f)] += f
        self.F_dead = F
        self.follower = {idx[k]: np.asarray(v, float)[:3] for k, v in (m.get("follower") or {}).items()}
        # DOFs with no stiffness at all (rotations of truss-only / cable-only nodes): fixed, as frame.solve does
        x, Rn = self.X0.copy(), np.repeat(np.eye(3)[None], nn, 0)
        K, _ = self._assemble(x, Rn)
        diag = np.abs(K.diagonal())
        fixed |= set(np.where(diag < 1e-12 * diag.max())[0].tolist())
        self.fixed = np.array(sorted(fixed), int)
        self.free = np.array(sorted(set(range(self.ndof)) - fixed), int)

    # -------------------------------------------------------------------------------------------- element state
    def _elem(self, x, Rn):
        n1, n2 = self.n1, self.n2
        d = x[n2] - x[n1]
        l = np.linalg.norm(d, axis=1)
        e1 = d / l[:, None]
        R0T = self.R0.transpose(0, 2, 1)                       # columns = initial local axes
        Q1 = Rn[n1] @ R0T
        Q2 = Rn[n2] @ R0T
        q = 0.5 * (Q1[:, :, 1] + Q2[:, :, 1])
        e3 = np.cross(e1, q)
        e3 /= np.linalg.norm(e3, axis=1)[:, None]
        e2 = np.cross(e3, e1)
        Er = np.stack([e1, e2, e3], axis=2)                    # columns = current local axes
        ErT = Er.transpose(0, 2, 1)
        th1 = _rotvec(ErT @ Q1)
        th2 = _rotvec(ErT @ Q2)
        dl = np.zeros((len(l), 12))
        dl[:, 3:6] = th1
        dl[:, 6] = l - self.L0
        dl[:, 9:12] = th2
        f_loc = np.einsum("eij,ej->ei", self.k, dl)
        return Er, ErT, f_loc, l

    def _assemble(self, x, Rn, lam: float = 0.0, want_force: bool = False):
        ne = len(self.L0)
        Er, ErT, f_loc, l = self._elem(x, Rn)
        N = f_loc[:, 6]                                         # axial (tension +)
        T = np.zeros((ne, 12, 12))
        for b in range(4):
            T[:, 3 * b: 3 * b + 3, 3 * b: 3 * b + 3] = ErT     # global -> local
        Kl = self.k + N[:, None, None] * self.G
        Ke = np.einsum("eji,ejk,ekl->eil", T, Kl, T)
        rows = np.repeat(self.edofs, 12, axis=1).ravel()
        cols = np.tile(self.edofs, (1, 12)).ravel()
        vals = Ke.ravel()
        fint = np.zeros(self.ndof)
        fg = np.einsum("eji,ej->ei", T, f_loc)
        np.add.at(fint, self.edofs.ravel(), fg.ravel())
        R_, C_, V_ = [rows], [cols], [vals]

        def add_block(dofs, Kb):
            rr, cc = np.meshgrid(dofs, dofs, indexing="ij")
            R_.append(rr.ravel()); C_.append(cc.ravel()); V_.append(Kb.ravel())
        # grounded springs (global axes)
        U = x - self.X0
        for i, kv in self.springs.items():
            dofs = np.arange(6 * i, 6 * i + 6)
            add_block(dofs, np.diag(kv))
            rot = _rotvec(Rn[i][None])[0]
            fint[dofs] += kv * np.r_[U[i], rot]
        if self.reg_k:
            for i in range(self.n_user):
                dofs = np.arange(6 * i, 6 * i + 3)
                add_block(dofs, np.eye(3) * self.reg_k)
                fint[dofs] += self.reg_k * U[i]
        # links, turning with node a
        self._link_f = {}
        for a, b, kv, lid in self.links:
            Ra = Rn[a]
            Kt = Ra @ np.diag(kv[:3]) @ Ra.T
            Kr = Ra @ np.diag(kv[3:]) @ Ra.T
            rel = (x[b] - x[a]) - Ra @ (self.X0[b] - self.X0[a])
            relr = _rotvec((Rn[b] @ Ra.T)[None])[0]
            fb = np.r_[Kt @ rel, Kr @ relr]
            fint[6 * a: 6 * a + 6] -= fb
            fint[6 * b: 6 * b + 6] += fb
            Kb = np.zeros((12, 12))
            K6 = np.zeros((6, 6)); K6[:3, :3] = Kt; K6[3:, 3:] = Kr
            Kb[:6, :6] = K6; Kb[6:, 6:] = K6; Kb[:6, 6:] = -K6; Kb[6:, :6] = -K6
            add_block(np.r_[6 * a: 6 * a + 6, 6 * b: 6 * b + 6], Kb)
            self._link_f[lid] = fb
        # one-sided contacts (compression only): resist motion along dir beyond gap
        self._contact_f = {}
        for i, n, kc, gap in self.contacts:
            dpen = float(U[i] @ n) - gap
            if dpen > 0:
                fint[6 * i: 6 * i + 3] += kc * dpen * n
                add_block(np.arange(6 * i, 6 * i + 3), kc * np.outer(n, n))
            self._contact_f[self.node_ids[i]] = max(dpen, 0.0) * kc
        # cables
        self._cable_t = {}
        for a, b, EA, L0, cid in self.cables:
            d = x[b] - x[a]
            lc = float(np.linalg.norm(d))
            n = d / lc
            Tn = EA * (lc - L0) / L0
            if Tn > 0:
                Kc = EA / L0 * np.outer(n, n) + Tn / lc * (np.eye(3) - np.outer(n, n))
                fint[6 * a: 6 * a + 3] -= Tn * n
                fint[6 * b: 6 * b + 3] += Tn * n
            else:
                Tn = 0.0
                Kc = np.zeros((3, 3))
            Kb = np.block([[Kc, -Kc], [-Kc, Kc]])
            add_block(np.r_[6 * a: 6 * a + 3, 6 * b: 6 * b + 3], Kb)
            self._cable_t[cid] = Tn
        K = sp.csr_matrix((np.concatenate(V_), (np.concatenate(R_), np.concatenate(C_))), shape=(self.ndof, self.ndof))
        self._N, self._f_loc, self._l = N, f_loc, l
        if want_force:
            return K, fint
        return K, fint

    def f_ext(self, lam: float, Rn) -> np.ndarray:
        F = lam * self.F_dead
        if self.follower:
            F = F.copy()
            for i, f in self.follower.items():
                F[6 * i: 6 * i + 3] += lam * (Rn[i] @ f)
        return F

    # -------------------------------------------------------------------------------------------- solution
    def _update(self, x, Rn, du):
        D = du.reshape(-1, 6)
        x = x + D[:, :3]
        Rn = _expm(D[:, 3:]) @ Rn
        return x, Rn

    max_dx = 25.0          # mm per Newton iteration
    max_dth = 0.15         # rad per Newton iteration
    runaway_mm = 600.0

    def newton(self, x, Rn, lam, tol=1e-7, maxit=60):
        fr = self.free
        Fn = max(np.linalg.norm(self.f_ext(lam, Rn)[fr]), 1.0)
        for it in range(1, maxit + 1):
            K, fint = self._assemble(x, Rn)
            r = self.f_ext(lam, Rn) - fint
            rn = np.linalg.norm(r[fr])
            if rn < tol * Fn + 1e-5 and it > 1:
                return x, Rn, it, True, K
            Kf = K[fr][:, fr].tocsc()
            try:
                duf = spla.spsolve(Kf, r[fr])
            except Exception:
                return x, Rn, it, False, K
            if not np.all(np.isfinite(duf)):
                return x, Rn, it, False, K
            du = np.zeros(self.ndof)
            du[fr] = duf
            D = du.reshape(-1, 6)
            big = max(np.abs(D[:, :3]).max() / self.max_dx, np.abs(D[:, 3:]).max() / self.max_dth, 1.0)
            if big > 1.0:                         # damped Newton: limit one iteration's move
                du = du / big
            x, Rn = self._update(x, Rn, du)
            if np.abs(x - self.X0).max() > self.runaway_mm:       # collapse / runaway guard
                return x, Rn, it, False, K
        return x, Rn, maxit, False, K

    def min_eig(self, K) -> float:
        fr = self.free
        Kf = K[fr][:, fr].tocsc()
        try:
            w = spla.eigsh(Kf, k=1, sigma=-1e-3, which="LM", return_eigenvectors=False, tol=1e-8)
            return float(w[0])
        except Exception:
            return float(np.linalg.eigvalsh(Kf.toarray())[0])

    def path(self, lam_max: float = 2.0, dlam: float = 0.05, dlam_min: float = 2e-3, log=None,
             track_eig: bool = True) -> list[PathPoint]:
        x, Rn = self.X0.copy(), np.repeat(np.eye(3)[None], self.nn, 0)
        K0, _ = self._assemble(x, Rn)
        pts = [PathPoint(0.0, np.zeros((self.nn, 6)), self.min_eig(K0) if track_eig else np.nan, 0, {})]
        lam, step = 0.0, dlam
        self.converged_to = 0.0
        while lam < lam_max - 1e-12:
            tgt = min(lam + step, lam_max)
            x1, R1, it, ok, K = self.newton(x, Rn, tgt)
            me = np.nan
            if ok and track_eig:
                me = self.min_eig(K)
                if me <= 0:                      # passed a bifurcation / limit point inside the step
                    ok = False
            if not ok:
                step /= 2
                if step < dlam_min:
                    break
                continue
            x, Rn, lam = x1, R1, tgt
            u = np.hstack([x - self.X0, _rotvec(Rn)])
            pts.append(PathPoint(lam, u, me if track_eig else np.nan, it, dict(self._cable_t)))
            if log:
                log(f"    lam {lam:.3f}  it {it}  min eig {pts[-1].min_eig:.4g}")
            if it <= 6:
                step = min(step * 1.5, dlam)
        self.converged_to = lam
        self.state = (x, Rn)
        return pts

    def member_forces(self) -> np.ndarray:
        """Local end forces (ne, 2, 6) at the last state: N, Vy, Vz, T, My, Mz (frame.solve sign convention)."""
        f = self._f_loc
        out = np.zeros((len(f), 2, 6))
        out[:, 0] = -f[:, :6]
        out[:, 1] = f[:, 6:]
        return out


def critical_from_path(pts: list[PathPoint]) -> dict:
    """Limit / bifurcation estimate from the tangent's smallest eigenvalue: the last converged load, and a
    linear extrapolation of min-eig to zero over the last two points (an upper-bound-free estimate when the path
    stops at lam_max with the stiffness still positive)."""
    lam = np.array([p.lam for p in pts])
    me = np.array([p.min_eig for p in pts])
    out = {"lam_last": float(lam[-1]), "min_eig_0": float(me[0]), "min_eig_last": float(me[-1])}
    if len(pts) >= 3 and me[-1] < me[-2]:
        s = (me[-1] - me[-2]) / (lam[-1] - lam[-2])
        out["lam_extrap"] = float(lam[-1] - me[-1] / s)
    else:
        out["lam_extrap"] = float("inf")
    return out
