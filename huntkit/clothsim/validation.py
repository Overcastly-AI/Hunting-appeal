"""Analytic validation cases for the cloth solver (used by tests/test_clothsim.py and the CLI).

1. Inflated closed cylinder: hoop tension p r, axial p r / 2, longitudinal seam line force p r,
   end-cap seam line force p r / 2 (thin-wall membrane, any stiffness).
2. Hanging sheet (catenary): a strip pinned on two parallel lines sags as y = a cosh(x / a) with
   arc length L = 2 a sinh(S / 2a); horizontal tension H = w a, sag f = a (cosh(S / 2a) - 1).
3. Flat-pattern area: the triangulation conserves the pattern area, and a draped sheet keeps
   its area (3D / flat) within the fabric strain.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq

from .assemble import PieceSpec, assemble, densify
from .fabric import FabricModel
from .model import Anchor, Bending, Gravity, Membrane, Pins, Pressure, Sim
from .results import cauchy, seam_forces, tri_measures


def iso_fabric(k=200.0, shear=50.0, bending=0.05, gsm=200.0, c=0.01) -> FabricModel:
    return FabricModel("validation_iso", k, k, shear, bending, c, gsm * 1e-9, 50.0, 50.0)


def _rect_edges(W, H, map3d, step=2.0, names=("bottom", "right", "top", "left")):
    corners = np.array([[0, 0], [W, 0], [W, H], [0, H]], float)
    out = []
    for i in range(4):
        fl = densify(np.array([corners[i], corners[(i + 1) % 4]]), step)
        out.append((names[i], fl, map3d(fl)))
    return out


# ----------------------------------------------------------------------------- 1. cylinder
def cylinder(R=100.0, L=500.0, p=0.005, h=15.0, fabric=None, verbose=False) -> dict:
    fab = fabric or iso_fabric()
    W = 2 * math.pi * R

    def tube3(fl):
        th = fl[:, 0] / R
        return np.column_stack([R * np.cos(th), R * np.sin(th), fl[:, 1]])

    def cap(z):
        def m3(fl):
            return np.column_stack([fl[:, 0], fl[:, 1], np.full(len(fl), z)])
        th = np.linspace(0, 2 * math.pi, int(W / 2) + 1)
        rim = np.column_stack([R * np.cos(th), R * np.sin(th)])
        return [("rim", rim, m3(rim))], m3

    e0, m0 = cap(0.0)
    e1, m1 = cap(L)
    # caps: same cloth but compression-carrying (c = 1), so the flat discs dome without wrinkling;
    # the mid-length answer does not depend on the caps
    capf = FabricModel(**{**fab.__dict__, "compression": 1.0, "material_id": "validation_cap"})
    specs = [PieceSpec("tube", _rect_edges(W, L, tube3), tube3, fab, grain_deg=0.0),
             PieceSpec("cap0", e0, m0, capf), PieceSpec("cap1", e1, m1, capf)]
    mesh, diag = assemble(specs, h, tol=1.0, outward_ref=np.array([0, 0, L / 2]))
    memb = Membrane(mesh)
    pr = Pressure(mesh.tris, p0=p)
    sim = Sim(mesh, [memb, Bending(mesh), pr, Anchor(mesh.X0, 1e-6)])
    x, info = sim.solve(tol=1e-5, max_iter=80, verbose=verbose)
    # mid-length band of the tube
    tp = mesh.tri_piece == 0
    on_tube = np.unique(mesh.tris[tp])
    zc = x[on_tube, 2].mean()
    axis = x[on_tube, :2].mean(0)
    cen = x[mesh.tris].mean(1)
    band = tp & (np.abs(cen[:, 2] - zc) < L / 6)
    sig = cauchy(mesh, memb, x)[band]
    e_hoop = float(np.mean(tri_measures(mesh, memb, x)["e_warp"][band]))
    c = cen[band] - np.r_[axis, 0]
    eth = np.column_stack([-c[:, 1], c[:, 0], np.zeros(len(c))])
    eth /= np.linalg.norm(eth, axis=1, keepdims=True)
    ez = np.array([0, 0, 1.0])
    hoop = np.einsum("ti,tij,tj->t", eth, sig, eth)
    axial = np.einsum("j,tij,i->t", ez, sig, ez)
    mid = np.abs(x[:, 2] - zc) < L / 6
    sel = np.intersect1d(np.where(mid)[0], on_tube)
    r_def = float(np.mean(np.hypot(x[sel, 0] - axis[0], x[sel, 1] - axis[1])))
    sf = seam_forces(mesh, x, memb, diag["seams"])
    long_seam = next(v for k, v in sf.items() if v["pieces"] == ("tube", "tube"))
    lz = x[long_seam["nodes"], 2]
    lmid = np.abs(lz - zc) < L / 6
    cap_seams = [v for k, v in sf.items() if "cap" in v["pieces"][0] or "cap" in v["pieces"][1]]
    cap_line = np.concatenate([v["line_n_mm"] for v in cap_seams])
    return {"R": R, "L": L, "p": p, "r_def": r_def, "hoop": float(hoop.mean()), "hoop_std": float(hoop.std()),
            "axial": float(axial.mean()), "hoop_exact": p * R * (1 + e_hoop), "axial_exact": p * R * (1 + e_hoop) / 2,
            "r_eq": R * (1 + e_hoop),
            "seam_long": float(long_seam["line_n_mm"][lmid].mean()), "seam_cap": float(np.median(cap_line)),
            "r_exact_linear": R * (1 + p * R / fab.k_warp), "info": info, "mesh": mesh, "x": x,
            "nodes": mesh.n, "tris": len(mesh.tris), "free_segments": len(diag["free_segments"]),
            "volume": pr.volume(x), "volume_exact": math.pi * r_def ** 2 * L}


# ----------------------------------------------------------------------------- 2. catenary
def catenary_exact(S, Ls, w):
    a = brentq(lambda a: 2 * a * math.sinh(S / (2 * a)) - Ls, S / 50, 1e6)
    return {"a": a, "H": w * a, "sag": a * (math.cosh(S / (2 * a)) - 1), "V": w * Ls / 2}


def catenary(S=400.0, Ls=500.0, b=60.0, h=12.0, gsm=600.0, k=500.0, verbose=False) -> dict:
    fab = iso_fabric(k=k, shear=5.0, bending=1e-4, gsm=gsm)
    half = Ls / 2
    # start: a V of the right length (not the answer)
    zd = math.sqrt(max(half ** 2 - (S / 2) ** 2, 0))

    def m3(fl):
        s = fl[:, 0]
        xx = np.where(s < half, -S / 2 + s * (S / 2) / half, (s - half) * (S / 2) / half)
        zz = np.where(s < half, -zd * s / half, -zd * (Ls - s) / half)
        return np.column_stack([xx, fl[:, 1], zz])
    specs = [PieceSpec("strip", _rect_edges(Ls, b, m3), m3, fab, grain_deg=0.0)]
    mesh, diag = assemble(specs, h, tol=0.5)
    ends = np.where((np.abs(mesh.X0[:, 0] + S / 2) < 1e-6) | (np.abs(mesh.X0[:, 0] - S / 2) < 1e-6))[0]
    pins = Pins(ends, mesh.X0[ends], k=1e3)
    sim = Sim(mesh, [Membrane(mesh), Bending(mesh), Gravity(mesh.mass), pins])
    x, info = sim.solve(tol=1e-7, max_iter=200, verbose=verbose)
    w = gsm * 1e-9 * 9.81                       # N/mm^2 = N/mm per mm of width
    ex = catenary_exact(S, Ls, w)
    f = pins.forces(x)
    right = x[ends, 0] > 0
    H = abs(f[right, 0].sum()) / b
    V = f[right, 2].sum() / b
    sag = float(-x[:, 2].min())
    # shape: compare the mid-width line with the catenary through the supports
    xs = np.linspace(-S / 2 * 0.95, S / 2 * 0.95, 41)
    a = ex["a"]
    zc = a * np.cosh(xs / a) - a * math.cosh(S / (2 * a))
    mline = np.abs(x[:, 1] - b / 2) < h * 0.6
    order = np.argsort(x[mline, 0])
    zs = np.interp(xs, x[mline, 0][order], x[mline, 2][order])
    return {"S": S, "Ls": Ls, "w": w, "sag": sag, "sag_exact": ex["sag"], "H": H, "H_exact": ex["H"],
            "V": V, "V_exact": ex["V"], "shape_err_mm": float(np.max(np.abs(zs - zc))), "xs": xs, "z_sim": zs,
            "z_exact": zc, "info": info, "mesh": mesh, "x": x, "nodes": mesh.n}


# ----------------------------------------------------------------------------- 3. area
def drape_area(L=400.0, h=15.0, gsm=300.0, k=150.0, verbose=False) -> dict:
    """Square sheet pinned at its four corners, sagging under its own weight."""
    fab = iso_fabric(k=k, shear=1.0, bending=0.05, gsm=gsm)

    def m3(fl):
        return np.column_stack([fl[:, 0], fl[:, 1], np.zeros(len(fl))])
    specs = [PieceSpec("sheet", _rect_edges(L, L, m3), m3, fab)]
    mesh, diag = assemble(specs, h, tol=0.5)
    X = mesh.X0
    corners = [int(np.argmin(np.linalg.norm(X[:, :2] - np.array(c), axis=1))) for c in
               ((0, 0), (L, 0), (L, L), (0, L))]
    # corners pulled 10 % inward so the sheet can sag
    tgt = X[corners].copy()
    tgt[:, :2] = L / 2 + 0.9 * (tgt[:, :2] - L / 2)
    sim = Sim(mesh, [Membrane(mesh), Bending(mesh), Gravity(mesh.mass), Pins(corners, tgt, k=1e3)])
    # small out-of-plane seed so the sheet buckles downward, not into a saddle
    x0 = X.copy()
    r = np.hypot(X[:, 0] - L / 2, X[:, 1] - L / 2)
    x0[:, 2] = -0.2 * (L / 2 - np.minimum(r, L / 2))
    x, info = sim.solve(x0, tol=1e-6, max_iter=150, verbose=verbose)
    return {"flat_area": mesh.flat_area(), "area_3d": mesh.area(x), "polygon_area": L * L,
            "sag": float(-x[:, 2].min()), "info": info, "mesh": mesh, "x": x}
