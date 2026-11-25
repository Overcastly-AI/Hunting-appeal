"""Solid (3D P2-tet) submodel of a thin round tube segment with transverse through-holes, contact patches or
external clamp pressure (BL-081). Used for real hole Kt, loaded-hole (bolt bearing) peaks, ring bending under a
bushing and clamp ovalisation, where the beam model only gives section forces.

Geometry: tube axis = local X (0 .. L), mid-surface radius Rm, wall t; the wall is meshed by an unrolled
(arc length s, X) Delaunay triangulation with graded rings around each hole, extruded through the wall in
``n_layers`` prisms split into conforming tets, then mapped to the cylinder:
``Y = r cos(theta), Z = r sin(theta), theta = s / Rm``. A hole at theta 0 has its axis along local +Y; a through-bolt
makes a pair at theta 0 and pi. Holes are radial (ASSUMPTION RADIAL-HOLE: a drilled transverse hole differs by < 5 %
in edge angle at d/D 0.21, Peterson 4.x treats both).

Supports and loads: end X = 0 clamped; at X = L any of N, Vy, Vz, T, My, Mz as beam-theory tractions (thin-wall
shear flow for V and T, Navier for N and M), hole bearing as a cosine pressure on the hole bore, contact patches as a
cosine radial pressure over a half-angle and a length on the inner or outer surface.

Verification (tests/test_tube_solid.py): open-hole Kt in a wide strip vs Heywood; tube bending and torsion vs beam
theory; a long ring under a diametral line load vs Roark. Units mm, N, MPa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import Delaunay

E_AL, NU_AL = 68900.0, 0.33


@dataclass
class Hole:
    x: float            # axial position
    theta: float        # angular position of the hole axis (rad); its partner at theta + pi if ``through``
    d: float
    through: bool = True


@dataclass
class TubeModel:
    L: float
    od: float
    t: float
    holes: list = field(default_factory=list)
    h: float = 1.6                 # background in-plane element size (mm)
    h_hole: float = 0.18           # element size at a hole edge
    n_layers: int = 2
    E: float = E_AL
    nu: float = NU_AL
    seam: float = np.pi / 2        # unrolled strip runs theta in [seam - 2 pi, seam)
    refine_x: tuple = ()           # extra axial bands (x0, x1, h) to refine (contact patches, clamp edges)

    @property
    def Rm(self):
        return self.od / 2 - self.t / 2


def _hole_list(m: TubeModel):
    out = []
    for hl in m.holes:
        out.append((hl.x, hl.theta, hl.d))
        if hl.through:
            out.append((hl.x, hl.theta + np.pi, hl.d))
    return out


def _wrap(th, seam):
    lo = seam - 2 * np.pi
    return (th - lo) % (2 * np.pi) + lo


def mesh(m: TubeModel):
    """-> (skfem MeshTet, info). Unrolled points: s in [s0, s0 + 2 pi Rm), periodic seam merged."""
    from skfem import MeshTet
    Rm = m.Rm
    C = 2 * np.pi * Rm
    s0 = (m.seam - 2 * np.pi) * Rm
    holes = [(x, _wrap(th, m.seam) * Rm, d) for x, th, d in _hole_list(m)]
    # background structured points (nx x ns), ns divides the circumference exactly (seam columns match)
    ns = max(24, int(np.ceil(C / m.h)))
    xs = np.linspace(0.0, m.L, max(8, int(np.ceil(m.L / m.h))) + 1)
    for x0, x1, hb in m.refine_x:
        xs = np.union1d(xs[(xs < x0) | (xs > x1)], np.linspace(x0, x1, max(2, int(np.ceil((x1 - x0) / hb))) + 1))
        ns = max(ns, int(np.ceil(C / hb)))
    ss = s0 + C * np.arange(ns + 1) / ns            # includes both seam columns
    S, X = np.meshgrid(ss, xs, indexing="ij")
    pts = np.c_[S.ravel(), X.ravel()]
    # hole zones: drop background points, add graded rings
    for (hx, hs, d) in holes:
        a = d / 2
        rr = np.hypot(pts[:, 0] - hs, pts[:, 1] - hx)
        r_out = a + 4.0 * a
        pts = pts[rr > r_out + 0.5 * m.h]
        r = a
        rings = []
        while r < r_out:
            hloc = m.h_hole + (m.h - m.h_hole) * (r - a) / (r_out - a)
            n = max(16, int(np.ceil(2 * np.pi * r / hloc)))
            rings.append((r, n))
            r += hloc * 0.87
        rings.append((r_out, max(16, int(np.ceil(2 * np.pi * r_out / m.h)))))
        for k, (r, n) in enumerate(rings):
            ph = 2 * np.pi * (np.arange(n) + 0.5 * (k % 2)) / n
            pts = np.r_[pts, np.c_[hs + r * np.cos(ph), hx + r * np.sin(ph)]]
    # keep inside the strip
    keep = (pts[:, 1] >= -1e-9) & (pts[:, 1] <= m.L + 1e-9) & (pts[:, 0] >= s0 - 1e-9) & (pts[:, 0] <= s0 + C + 1e-9)
    pts = pts[keep]
    pts = np.unique(np.round(pts, 9), axis=0)
    tri = Delaunay(pts).simplices
    cen = pts[tri].mean(axis=1)
    ok = np.ones(len(tri), bool)
    for (hx, hs, d) in holes:
        ok &= np.hypot(cen[:, 0] - hs, cen[:, 1] - hx) > d / 2
    tri = tri[ok]
    # drop zero-area slivers on the strip edge
    e1, e2 = pts[tri[:, 1]] - pts[tri[:, 0]], pts[tri[:, 2]] - pts[tri[:, 0]]
    a2 = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    tri = tri[a2 > 1e-10]
    # merge the seam: points at s0 + C -> the matching point at s0
    on_hi = np.abs(pts[:, 0] - (s0 + C)) < 1e-7
    on_lo = np.abs(pts[:, 0] - s0) < 1e-7
    lo_idx = {round(float(x), 7): i for i, x in zip(np.nonzero(on_lo)[0], pts[on_lo, 1])}
    remap = np.arange(len(pts))
    for i in np.nonzero(on_hi)[0]:
        remap[i] = lo_idx[round(float(pts[i, 1]), 7)]
    tri = remap[tri]
    used = np.unique(tri)
    newid = -np.ones(len(pts), int)
    newid[used] = np.arange(len(used))
    tri = newid[tri]
    p2 = pts[used]
    # extrude through the wall
    nl = m.n_layers
    rs = np.linspace(m.od / 2 - m.t, m.od / 2, nl + 1)
    npt = len(p2)
    P = []
    for r in rs:
        th = p2[:, 0] / Rm
        P.append(np.c_[p2[:, 1], r * np.cos(th), r * np.sin(th)])
    P = np.vstack(P)
    tets = []
    for k in range(nl):
        for tr in tri:
            a, b, c = sorted(tr)
            A0, B0, C0 = a + k * npt, b + k * npt, c + k * npt
            A1, B1, C1 = A0 + npt, B0 + npt, C0 + npt
            tets += [(A0, B0, C0, C1), (A0, B0, B1, C1), (A0, A1, B1, C1)]
    T = np.array(tets).T
    # orient positively
    pp = P[T]
    vol = np.einsum("ij,ij->j", np.cross(pp[1] - pp[0], pp[2] - pp[0]).T, (pp[3] - pp[0]).T)
    T[[1, 2]] = np.where(vol < 0, T[[2, 1]], T[[1, 2]])
    msh = MeshTet(P.T.copy(), T.copy())
    return msh, {"s0": s0, "C": C, "rs": rs, "npt": npt, "holes": holes, "p2": p2}


class TubeFE:
    """Assembled model with a factorised stiffness; unit cases solve by back substitution."""

    def __init__(self, m: TubeModel):
        from skfem import Basis, ElementTetP2, ElementVector, asm
        from skfem.models.elasticity import lame_parameters, linear_elasticity
        self.m = m
        self.mesh, self.info = mesh(m)
        self.e = ElementVector(ElementTetP2())
        self.basis = Basis(self.mesh, self.e)
        lam, mu = lame_parameters(m.E, m.nu)
        self.lam, self.mu = lam, mu
        self.K = asm(linear_elasticity(lam, mu), self.basis)
        x = self.basis.doflocs
        self.fixed = np.nonzero(np.abs(x[0]) < 1e-7)[0]
        self.free = np.setdiff1d(np.arange(self.K.shape[0]), self.fixed)
        self._solver = None
        # global component (0 x, 1 y, 2 z) of every DOF (ElementVector interleaves the components)
        comp = np.zeros(self.K.shape[0], int)
        for k in range(3):
            comp[self.basis.split_indices()[k]] = k
        self._comp = comp

    # ------------------------------------------------------------------ solve
    def solve(self, f):
        import scipy.sparse.linalg as spla
        Kf = self.K[self.free][:, self.free].tocsr()
        if self._solver is None:
            try:
                import pypardiso
                self._solver = ("pardiso", pypardiso.PyPardisoSolver())
                self._Kf = Kf
            except Exception:  # pragma: no cover
                self._solver = ("splu", spla.splu(Kf.tocsc()))
        u = np.zeros(self.K.shape[0])
        if self._solver[0] == "pardiso":
            import pypardiso
            u[self.free] = pypardiso.spsolve(self._Kf, f[self.free], solver=self._solver[1])
        else:
            u[self.free] = self._solver[1].solve(f[self.free])
        return u

    # ------------------------------------------------------------------ loads
    def _facets(self, pred):
        mp = self.mesh.p[:, self.mesh.facets]
        sel = pred(mp)
        return np.nonzero(sel.all(axis=0) if sel.ndim == 2 else sel)[0]

    def _traction(self, facets, fun):
        """fun(x (3, nf, nq), n (3, nf, nq)) -> traction (3, nf, nq)."""
        from skfem import FacetBasis, LinearForm
        fb = FacetBasis(self.mesh, self.e, facets=facets)

        @LinearForm
        def lf(v, w):
            tr = fun(w.x, w.n)
            return tr[0] * v.value[0] + tr[1] * v.value[1] + tr[2] * v.value[2]
        return lf.assemble(fb)

    def end_load(self, N=0.0, Vy=0.0, Vz=0.0, T=0.0, My=0.0, Mz=0.0):
        """Beam tractions on the X = L face giving section forces (N, Vy, Vz, T, My, Mz) at X = L. Local axes:
        My about Y (stress + My Z / I), Mz about Z (stress - Mz Y / I), right-handed."""
        m = self.m
        ro, ri = m.od / 2, m.od / 2 - m.t
        A = np.pi * (ro ** 2 - ri ** 2)
        I = np.pi * (ro ** 4 - ri ** 4) / 4
        J = 2 * I
        fac = self._facets(lambda p: np.abs(p[0] - m.L) < 1e-7)

        def fun(x, n):
            Y, Z = x[1], x[2]
            r = np.hypot(Y, Z)
            sxx = N / A + My * Z / I - Mz * Y / I
            # torsion: tau = T r / J along e_theta = (-Z, Y) / r
            tt = T / J
            ty, tz = -tt * Z, tt * Y
            # thin-wall transverse shear: tau_xs = V Q / (I t); for a circle q(phi) = V sin(phi) / (pi R) per length
            th = np.arctan2(Z, Y)
            Rm = m.Rm
            # Vy: shear flow tangential, magnitude Vy sin(th)/(pi Rm t) along e_theta (zero at th 0 / pi)
            qy = -Vy * np.sin(th) / (np.pi * Rm * m.t)
            qz = Vz * np.cos(th) / (np.pi * Rm * m.t)
            q = qy + qz
            ty = ty + q * (-np.sin(th))
            tz = tz + q * np.cos(th)
            return np.array([sxx, ty, tz])
        f = self._traction(fac, fun)
        return f

    def hole_bearing(self, hole_index: int, F: float, direction):
        """Bolt bearing on one hole bore: total force F (N) on the wall, in the tangent-plane direction
        ``direction`` = (dx, ds) (axial, circumferential), cosine pressure over the loaded half."""
        hx, hs, d = self.info["holes"][hole_index]
        a = d / 2
        Rm = self.m.Rm
        dvec = np.asarray(direction, float)
        dvec = dvec / np.linalg.norm(dvec)

        def on_hole(p):
            th = np.arctan2(p[2], p[1])
            s = _wrap(th, self.m.seam) * Rm
            return np.abs(np.hypot(s - hs, p[0] - hx) - a) < 0.02 * a

        fac = self._facets(on_hole)

        def fun(x, n, p0=1.0):
            th = np.arctan2(x[2], x[1])
            s = _wrap(th, self.m.seam) * Rm
            ux, us = x[0] - hx, s - hs
            rr = np.hypot(ux, us) + 1e-12
            c = (ux * dvec[0] + us * dvec[1]) / rr
            p = p0 * np.clip(c, 0.0, None)
            # pressure pushes the material away from the hole centre: traction = p * (-n_out_of_material)
            # n is the outward normal of the material (it points into the hole), so traction = -p n
            return -p * n
        f = self._traction(fac, fun)
        # scale to the requested resultant along the load direction (global)
        thc = hs / Rm
        e_s = np.array([0.0, -np.sin(thc), np.cos(thc)])
        e_x = np.array([1.0, 0.0, 0.0])
        g = dvec[0] * e_x + dvec[1] * e_s
        mag = float(self._resultant(f) @ g)
        return f * (F / mag)

    def _resultant(self, f):
        """Sum of nodal forces per global component."""
        return np.array([f[self._comp == k].sum() for k in range(3)])

    def patch_pressure(self, x0, x1, theta0, half_angle, F, surface="inner", uniform=False):
        """Radial contact load F (N) over x0..x1 and theta0 +/- half_angle, cosine distribution, on the inner
        (load pushes outward, e.g. a bushing) or outer surface (load pushes inward, e.g. a clamp jaw)."""
        m = self.m
        r_s = m.od / 2 - m.t if surface == "inner" else m.od / 2
        sgn = 1.0 if surface == "inner" else -1.0

        def sel(p):
            r = np.hypot(p[1], p[2])
            th = np.arctan2(p[2], p[1])
            dth = np.angle(np.exp(1j * (th - theta0)))
            return (np.abs(r - r_s) < 1e-6) & (p[0] >= x0 - 1e-6) & (p[0] <= x1 + 1e-6) & (np.abs(dth) <= half_angle + 1e-6)
        fac = self._facets(sel)

        def fun(x, n):
            th = np.arctan2(x[2], x[1])
            dth = np.angle(np.exp(1j * (th - theta0)))
            p = (np.abs(dth) <= half_angle + 1e-9).astype(float) if uniform else \
                np.clip(np.cos(np.pi / 2 * dth / half_angle), 0.0, None)
            er = np.array([np.zeros_like(th), np.cos(th), np.sin(th)])
            return sgn * p * er
        f = self._traction(fac, fun)
        er0 = np.array([0.0, np.cos(theta0), np.sin(theta0)])
        mag = float(self._resultant(f) @ er0) * sgn
        return f * (F / mag)

    def uniform_pressure(self, x0, x1, p, surface="outer"):
        """Uniform radial pressure p (MPa) over x0..x1, inward on the outer surface (clamp) or outward inside."""
        m = self.m
        r_s = m.od / 2 if surface == "outer" else m.od / 2 - m.t
        sgn = -1.0 if surface == "outer" else 1.0

        def sel(pt):
            r = np.hypot(pt[1], pt[2])
            return (np.abs(r - r_s) < 1e-6) & (pt[0] >= x0 - 1e-6) & (pt[0] <= x1 + 1e-6)
        fac = self._facets(sel)

        def fun(x, n):
            th = np.arctan2(x[2], x[1])
            return sgn * p * np.array([np.zeros_like(th), np.cos(th), np.sin(th)])
        return self._traction(fac, fun)

    # ------------------------------------------------------------------ results
    def stress_at(self, u, elements=None):
        """Cauchy stress (3, 3, nel, 4) at the 4 vertices of each element (P2: linear strain)."""
        from skfem import Basis
        X = np.array([[0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])
        W = np.full(4, 1 / 24)
        b = Basis(self.mesh, self.e, quadrature=(X, W), elements=elements)
        g = b.interpolate(u).grad
        eps = 0.5 * (g + np.transpose(g, (1, 0, 2, 3)))
        tr = np.einsum("ii...->...", eps)
        I3 = np.eye(3)[:, :, None, None]
        return 2 * self.mu * eps + self.lam * tr[None, None] * I3

    def hole_edge(self, hole_index: int, band: float = 0.02):
        """Element ids touching the bore of a hole, and their vertex ids."""
        hx, hs, d = self.info["holes"][hole_index]
        p = self.mesh.p
        th = np.arctan2(p[2], p[1])
        s = _wrap(th, self.m.seam) * self.m.Rm
        on = np.abs(np.hypot(s - hs, p[0] - hx) - d / 2) < band * d / 2 + 1e-9
        el = np.nonzero(on[self.mesh.t].any(axis=0))[0]
        return el, on

    def peak_principal(self, u, hole_index: int):
        """Max principal stress at the bore vertices (nodal average over the touching elements)."""
        el, on = self.hole_edge(hole_index)
        S = self.stress_at(u, el)
        verts = self.mesh.t[:, el]
        acc, cnt = {}, {}
        for k in range(4):
            for j, v in enumerate(verts[k]):
                if on[v]:
                    acc[v] = acc.get(v, 0) + S[:, :, j, k]
                    cnt[v] = cnt.get(v, 0) + 1
        best = -np.inf
        for v, s in acc.items():
            w = np.linalg.eigvalsh(s / cnt[v])
            best = max(best, w[-1])
        return float(best)

    def bore_stress_tensors(self, u, hole_index: int):
        """{vertex: averaged stress tensor} on a hole bore (for superposition of unit cases)."""
        el, on = self.hole_edge(hole_index)
        S = self.stress_at(u, el)
        verts = self.mesh.t[:, el]
        acc, cnt = {}, {}
        for k in range(4):
            for j, v in enumerate(verts[k]):
                if on[v]:
                    acc[v] = acc.get(v, 0) + S[:, :, j, k]
                    cnt[v] = cnt.get(v, 0) + 1
        return {v: s / cnt[v] for v, s in acc.items()}

    def surface_peak(self, u, x0, x1, which="both"):
        """Max principal and von Mises over the inner/outer surface vertices with x0 <= X <= x1."""
        p = self.mesh.p
        r = np.hypot(p[1], p[2])
        ro, ri = self.m.od / 2, self.m.od / 2 - self.m.t
        surf = (np.abs(r - ro) < 1e-6) | (np.abs(r - ri) < 1e-6)
        on = surf & (p[0] >= x0) & (p[0] <= x1)
        el = np.nonzero(on[self.mesh.t].any(axis=0))[0]
        S = self.stress_at(u, el)
        verts = self.mesh.t[:, el]
        smax, vm = -np.inf, 0.0
        for k in range(4):
            for j, v in enumerate(verts[k]):
                if on[v]:
                    s = S[:, :, j, k]
                    w = np.linalg.eigvalsh(s)
                    smax = max(smax, w[-1])
                    vm = max(vm, np.sqrt(0.5 * ((w[0] - w[1]) ** 2 + (w[1] - w[2]) ** 2 + (w[2] - w[0]) ** 2)))
        return {"max_principal": float(smax), "von_mises": float(vm)}

    def surface_hoop(self, u, x0, x1):
        """Max |hoop stress| (sigma_theta_theta) on the inner and outer surface vertices with x0 <= X <= x1: the ring
        (local) part of a contact / clamp load, free of the beam bending (axial) stress of the submodel's supports."""
        p = self.mesh.p
        r = np.hypot(p[1], p[2])
        ro, ri = self.m.od / 2, self.m.od / 2 - self.m.t
        surf = (np.abs(r - ro) < 1e-6) | (np.abs(r - ri) < 1e-6)
        on = surf & (p[0] >= x0) & (p[0] <= x1)
        el = np.nonzero(on[self.mesh.t].any(axis=0))[0]
        S = self.stress_at(u, el)
        verts = self.mesh.t[:, el]
        best = 0.0
        for k in range(4):
            v = verts[k]
            sel = on[v]
            th = np.arctan2(p[2, v[sel]], p[1, v[sel]])
            et = np.array([np.zeros_like(th), -np.sin(th), np.cos(th)])
            s_tt = np.einsum("in,ijn,jn->n", et, S[:, :, sel, k], et)
            if s_tt.size:
                best = max(best, float(np.abs(s_tt).max()))
        return best

    def ovalisation(self, u, x, surface="inner"):
        """Diametral change of the bore from the n = 2 Fourier harmonic of u_r(theta) at station x (the n = 1 term is
        rigid translation / beam deflection and is excluded). Also the inward n = 0 term (uniform squeeze)."""
        th, ur = self.radial_disp(u, x, surface)
        A = np.c_[np.ones_like(th), np.cos(th), np.sin(th), np.cos(2 * th), np.sin(2 * th)]
        c, *_ = np.linalg.lstsq(A, ur, rcond=None)
        return {"oval_diam_mm": float(2 * np.hypot(c[3], c[4])), "uniform_inward_mm": float(-c[0]),
                "min_gap_change_mm": float(-c[0] + np.hypot(c[3], c[4]))}

    def radial_disp(self, u, x, surface="inner"):
        """Radial displacement around the circumference at axial station x on a surface: (theta, u_r)."""
        p = self.mesh.p
        r = np.hypot(p[1], p[2])
        rs = self.m.od / 2 - self.m.t if surface == "inner" else self.m.od / 2
        sel = np.nonzero((np.abs(r - rs) < 1e-6) & (np.abs(p[0] - x) < 0.6 * self.m.h + 1e-6))[0]
        th = np.arctan2(p[2, sel], p[1, sel])
        U = u[self.basis.nodal_dofs][:, sel]
        ur = U[1] * np.cos(th) + U[2] * np.sin(th)
        o = np.argsort(th)
        return th[o], ur[o]


# ---------------------------------------------------------------------------- closed forms used by the tests
def heywood_kt(d_over_w: float) -> float:
    """Gross-section Kt of a central hole in a finite-width strip in tension (Heywood; Pilkey, Peterson's SCF 3rd ed.
    eq. 4.4 on the net section): Kt_net = 2 + (1 - d/W)^3; Kt_gross = Kt_net / (1 - d/W)."""
    r = d_over_w
    return (2 + (1 - r) ** 3) / (1 - r)
