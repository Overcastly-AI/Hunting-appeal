"""Kirchhoff plate bending with scikit-fem (Morley element), for rectangular plates such as a
hipbelt stiffener plate, a carbon/HDPE framesheet panel or a load-shelf plate.

Verified against the Navier series solution for a simply supported square plate and the
Timoshenko clamped-plate coefficient (tests/test_fea.py). Morley converges O(h^2) in deflection;
default mesh 64 x 64 (n=64) gives < 0.5 % (simply supported) / ~0.6 % (clamped) error.

Edge conditions per edge ("left" x=0, "right" x=a, "bottom" y=0, "top" y=b):
  "ss" simply supported (w = 0), "clamped" (w = 0 and dw/dn = 0), "free".
Loads: uniform pressure ``q`` (MPa = N/mm^2) and/or a patch load ``patch`` =
{"x0","x1","y0","y1","force_n"} spread uniformly over the patch.

Isotropic material from a DB id / inline dict (``youngs_modulus_mpa``, ``poisson``,
``yield_strength_mpa``) or explicit ``E``, ``nu``. For a symmetric laminate panel pass ``D``
(3x3 bending stiffness from ``composite.Laminate.D``) instead; stresses are then not computed
(use ``Laminate.first_ply_failure`` with the returned moments).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skfem import Basis, BilinearForm, ElementTriMorley, LinearForm, MeshTri, condense, solve
from skfem.helpers import dd

from .materials_bridge import get_material


@dataclass
class PlateResult:
    w_max: float               # max |deflection| (mm)
    M_max: np.ndarray          # max |Mx|, |My|, |Mxy| (N*mm/mm)
    sigma_vm_max: float | None
    sf: float | None
    D: np.ndarray
    mesh: object
    basis: object
    w: np.ndarray


def _edge_facets(m, a, b, edge):
    tol = 1e-9 * max(a, b)
    f = {"left": lambda x: np.abs(x[0]) < tol, "right": lambda x: np.abs(x[0] - a) < tol,
         "bottom": lambda x: np.abs(x[1]) < tol, "top": lambda x: np.abs(x[1] - b) < tol}[edge]
    return m.facets_satisfying(f)


def kirchhoff_plate(a: float, b: float, t: float, material=None, E: float | None = None,
                    nu: float | None = None, D: np.ndarray | None = None, q: float = 0.0,
                    patch: dict | None = None, edges: dict | str = "ss", n: int = 64) -> PlateResult:
    yield_mpa = None
    if D is None:
        if material is not None:
            mat = get_material(material)
            E = E or float(mat.require("youngs_modulus_mpa"))
            nu = nu if nu is not None else float(mat.get("poisson", 0.3))
            yield_mpa = mat.get("yield_strength_mpa")
        Dm = E * t ** 3 / (12 * (1 - nu ** 2))
        D = Dm * np.array([[1, nu, 0], [nu, 1, 0], [0, 0, (1 - nu) / 2]])
    D = np.asarray(D, float)
    if isinstance(edges, str):
        edges = {e: edges for e in ("left", "right", "bottom", "top")}

    nx = n
    ny = max(2, int(round(n * b / a)))
    m = MeshTri.init_tensor(np.linspace(0, a, nx + 1), np.linspace(0, b, ny + 1))
    ib = Basis(m, ElementTriMorley())

    @BilinearForm
    def bil(u, v, w):
        H, G = dd(u), dd(v)
        ku = (H[0, 0], H[1, 1], 2 * H[0, 1])
        kv = (G[0, 0], G[1, 1], 2 * G[0, 1])
        return sum(D[i, j] * ku[j] * kv[i] for i in range(3) for j in range(3))

    def load_density(x, y):
        f = q * np.ones_like(x)
        if patch:
            area = (patch["x1"] - patch["x0"]) * (patch["y1"] - patch["y0"])
            inside = ((x >= patch["x0"]) & (x <= patch["x1"]) & (y >= patch["y0"]) & (y <= patch["y1"]))
            f = f + inside * patch["force_n"] / area
        return f

    @LinearForm
    def lin(v, w):
        return load_density(w.x[0], w.x[1]) * v

    K = bil.assemble(ib)
    f = lin.assemble(ib)
    fix = []
    for edge, bc in edges.items():
        if bc == "free":
            continue
        dofs = ib.get_dofs(_edge_facets(m, a, b, edge))
        fix.append(dofs.nodal["u"])
        if bc == "clamped":
            fix.append(dofs.facet["u_n"])
    fix = np.unique(np.concatenate(fix)) if fix else np.array([], int)
    w = solve(*condense(K, f, D=fix))

    # curvature -> moments at quadrature points
    H = ib.interpolate(w).hess
    kap = np.stack([H[0, 0], H[1, 1], 2 * H[0, 1]])       # (3, nel, nqp)
    M = -np.einsum("ij,jkl->ikl", D, kap)
    Mmax = np.abs(M).reshape(3, -1).max(axis=1)
    svm = sf = None
    if yield_mpa is not None or E is not None:
        s = 6 * M / t ** 2
        vm = np.sqrt(s[0] ** 2 - s[0] * s[1] + s[1] ** 2 + 3 * s[2] ** 2)
        svm = float(vm.max())
        if yield_mpa:
            sf = float(yield_mpa) / svm
    wmax = float(np.abs(w[ib.nodal_dofs[0]]).max())
    return PlateResult(wmax, Mmax, svm, sf, D, m, ib, w)


def navier_ss_rect(a, b, D, q, terms=99) -> float:
    """Navier series: centre deflection of a simply supported a x b plate under uniform q."""
    s = 0.0
    for mm in range(1, terms + 1, 2):
        for nn in range(1, terms + 1, 2):
            s += (np.sin(mm * np.pi / 2) * np.sin(nn * np.pi / 2)
                  / (mm * nn * ((mm / a) ** 2 + (nn / b) ** 2) ** 2))
    return 16 * q / (np.pi ** 6 * D) * s
