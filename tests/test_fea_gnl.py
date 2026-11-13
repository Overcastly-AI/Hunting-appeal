"""Verification of the co-rotational GNL frame solver (huntkit.fea.gnl) against closed-form solutions (BL-047)."""
import math

import numpy as np
import pytest

from huntkit.fea.gnl import GNL, critical_from_path
from huntkit.fea.sections import tube_round

E_AL = None


def _mat():
    from huntkit.materials import load
    m = load("alu_7075_t6")
    return float(m.require("youngs_modulus_mpa"))


def cantilever(n=20, L=500.0, od=20.0, t=2.0, loads=None, axis="x"):
    nodes = {f"N{i}": [L * i / n, 0.0, 0.0] for i in range(n + 1)}
    mem = [{"id": f"m{i}", "nodes": [f"N{i}", f"N{i + 1}"], "section": tube_round(od, t), "material": "alu_7075_t6"}
           for i in range(n)]
    return {"nodes": nodes, "members": mem, "supports": {"N0": "fixed"}, "loads": loads or {}}


def test_small_load_matches_linear_cantilever():
    E = _mat()
    s = tube_round(20.0, 2.0)
    I = math.pi / 64 * (20 ** 4 - 16 ** 4)
    P = 1.0
    m = cantilever(loads={"N20": [0, 0, -P, 0, 0, 0]})
    g = GNL(m)
    pts = g.path(lam_max=1.0, dlam=1.0, track_eig=False)
    w = pts[-1].u[g.idx["N20"], 2]
    assert w == pytest.approx(-P * 500 ** 3 / (3 * E * I), rel=1e-3)
    assert s.A > 0


def test_tip_moment_bends_to_quarter_circle():
    """Elastica: a tip moment M = EI theta / L bends the cantilever into a circular arc (exact)."""
    E = _mat()
    I = math.pi / 64 * (20 ** 4 - 16 ** 4)
    L = 500.0
    th = math.pi / 2
    M = E * I * th / L
    m = cantilever(loads={"N20": [0, 0, 0, 0, -M, 0]})      # -My bends the tip toward +z
    g = GNL(m)
    g.path(lam_max=1.0, dlam=0.1, track_eig=False)
    x, Rn = g.state
    r = L / th
    tip = x[g.idx["N20"]]
    assert tip[0] == pytest.approx(r * math.sin(th), abs=0.01 * L)
    assert tip[2] == pytest.approx(r * (1 - math.cos(th)), abs=0.01 * L)
    rot = np.linalg.norm(Rotation_vec(Rn[g.idx["N20"]]))
    assert rot == pytest.approx(th, rel=0.01)


def Rotation_vec(R):
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(R).as_rotvec()


def euler_column(delta0=0.5, n=16, L=800.0):
    """Pinned-pinned column along z, half-sine imperfection delta0 at mid-span."""
    nodes = {f"N{i}": [delta0 * math.sin(math.pi * i / n), 0.0, L * i / n] for i in range(n + 1)}
    mem = [{"id": f"m{i}", "nodes": [f"N{i}", f"N{i + 1}"], "section": tube_round(12.0, 1.0),
            "material": "alu_7075_t6", "ref": [1, 0, 0]} for i in range(n)]
    sup = {"N0": {"fix": "x y z rz"}, f"N{n}": {"fix": "x y rz"}}
    return {"nodes": nodes, "members": mem, "supports": sup}


def test_euler_column_amplification_and_limit():
    E = _mat()
    I = math.pi / 64 * (12 ** 4 - 10 ** 4)
    L = 800.0
    Pcr = math.pi ** 2 * E * I / L ** 2
    m = euler_column()
    m["loads"] = {"N16": [0, 0, -Pcr, 0, 0, 0]}
    g = GNL(m)
    pts = g.path(lam_max=0.5, dlam=0.1, track_eig=True)
    d = 0.5 + pts[-1].u[g.idx["N8"], 0]
    assert d / 0.5 == pytest.approx(1 / (1 - 0.5), rel=0.03)          # 1 / (1 - P/Pcr): delta0 0.5 grows to 1.0
    # perfect column: tangent stiffness reaches zero at Pcr
    mp = euler_column(delta0=0.0)
    mp["loads"] = {"N16": [0, 0, -Pcr, 0, 0, 0]}
    gp = GNL(mp)
    pp = gp.path(lam_max=1.3, dlam=0.1, track_eig=True)
    lam_c = pp[-1].lam
    assert 0.97 < lam_c <= 1.01
    assert critical_from_path(pp)["lam_extrap"] == pytest.approx(1.0, abs=0.02)


def test_cable_pendulum_angle_and_string_stiffness():
    """A load hanging on a cable takes the angle tan(phi) = H / W, and the linearised lateral stiffness is T / L."""
    L = 300.0
    m = {"nodes": {"A": [0, 0, L], "B": [0, 0, 0]}, "members": [], "supports": {"A": "fixed"},
         "cables": [{"id": "c", "nodes": ["A", "B"], "EA": 1e6, "pre_strain": 1e-4}],
         "loads": {"B": [100.0, 0, -500.0, 0, 0, 0]}}
    g = GNL(m, reg_k=1e-6)
    g.path(lam_max=1.0, dlam=0.05, track_eig=False)
    x, _ = g.state
    b = x[g.idx["B"]]
    assert math.atan2(b[0], -(b[2] - L)) == pytest.approx(math.atan2(100, 500), rel=1e-3)
    K, _ = g._assemble(*g.state)
    T = g._cable_t["c"]
    l = np.linalg.norm(b - np.array([0, 0, L]))
    assert T == pytest.approx(math.hypot(100, 500), rel=1e-4)
    i = 6 * g.idx["B"] + 1          # y: perpendicular to the cable
    assert K[i, i] == pytest.approx(T / l + 1e-6, rel=1e-4)


def test_rigid_rotation_is_stress_free():
    m = cantilever(n=4)
    m["supports"] = {}
    g = GNL(m)
    from scipy.spatial.transform import Rotation
    Rr = Rotation.from_rotvec([0.3, -0.7, 1.1]).as_matrix()
    x = (g.X0 - g.X0[0]) @ Rr.T + np.array([10, 20, 30])
    Rn = np.repeat(Rr[None], g.nn, 0)
    _, fint = g._assemble(x, Rn)
    assert np.abs(fint).max() < 1e-6
