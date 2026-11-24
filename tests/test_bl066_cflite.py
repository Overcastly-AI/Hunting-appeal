"""BL-066 CF-LITE rework (huntkit.gendesign.bl066_cflite): closed forms for the torque path and the tube scaling, the
bond rules on a synthetic record, then the part separation on the exported (re-rastered) geometry."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import bl066_cflite as B
from huntkit.gendesign import frame_iter1 as F

ROOT = Path(__file__).resolve().parents[1]
T = F.TUBE
R = T["od"] / 2
TW = (T["od"] - T["id"]) / 2


# ------------------------------------------------------------------------------------------------ torque path
def test_bond_shear_closed_forms():
    """Axial shear N / (pi d L), torque shear T / (2 pi r^2 L); orthogonal, combined as a vector."""
    s = B.bond_stresses(1000.0, 0.0, 40.0, 1.0, 1.0)
    assert s["tau_ax"] == pytest.approx(1000.0 / (math.pi * T["od"] * 40.0))
    s = B.bond_stresses(0.0, 20000.0, 40.0, 1.0, 1.0)
    assert s["tau_T"] == pytest.approx(20000.0 / (2 * math.pi * R ** 2 * 40.0))
    s = B.bond_stresses(1000.0, 20000.0, 40.0, 3.0, 5.0)
    assert s["avg"] == pytest.approx(math.hypot(s["tau_ax"], s["tau_T"]))
    assert s["peak"] == pytest.approx(math.hypot(3 * s["tau_ax"], 5 * s["tau_T"]))


def test_volkersen_axial_uses_Et_torque_uses_Gt():
    """omega^2 = G_a / t_a (1 / (X1 t1) + 1 / (X2 t2)) with X = E (axial) or G (torque); the torque lap is the
    sharper one here (the printed sleeve is soft in shear)."""
    from huntkit.fea.joints import volkersen_factor
    L, ta = 72.0, 0.8
    for kind, x1, x2 in (("axial", T["E"], F.E_PAHT), ("torque", T["G"], B.G_PAHT)):
        a1, a2 = x1 * TW, x2 * B.SLEEVE_T
        om = math.sqrt(B.MMA_G / ta * (1 / a1 + 1 / a2))
        assert B.volkersen_k(L, ta, kind) == pytest.approx(volkersen_factor(om * L, min(a1, a2) / max(a1, a2)))
    assert B.volkersen_k(L, ta, "torque") > 1.4 * B.volkersen_k(L, ta, "axial")
    assert B.G_PAHT == pytest.approx(F.E_PAHT / 2.7)
    # a thicker sleeve wall lowers both peaks
    assert B.volkersen_k(L, ta, "torque", 6.0) < B.volkersen_k(L, ta, "torque", 3.0)


def test_tube_fi_closed_forms():
    ts = B.tube_section_real()
    assert ts["A"] == pytest.approx(math.pi * (11 ** 2 - 9 ** 2))
    assert ts["J"] == pytest.approx(math.pi / 2 * (11 ** 4 - 9 ** 4))
    Xt = T["Xt"] * T["hot_wet"]
    Xc = T["Xc"] * T["hot_wet"] * T["impact_c"]
    S = T["S"] * T["hot_wet"]
    assert B.tube_fi(1000.0, 0, 0, 0) == pytest.approx(1000.0 / ts["A"] / Xt)
    assert B.tube_fi(-1000.0, 0, 0, 0) == pytest.approx(1000.0 / ts["A"] / Xc)
    assert B.tube_fi(0, 0, 50000.0, 0) == pytest.approx((50000.0 * 11 / ts["J"] / S) ** 2)
    assert B.tube_fi(0, 20000.0, 0, 0) == pytest.approx(20000.0 * 11 / ts["I"] / Xc)
    # two 4 mm holes: net section x (1 - 2 d t / A), open-hole strength
    f = 1 - 2 * 4.0 * TW / ts["A"]
    assert B.tube_fi(1000.0, 0, 0, 0, holes=2) == pytest.approx(1000.0 / (ts["A"] * f) / (Xt * B.OPEN_HOLE_KD))


# ------------------------------------------------------------------------------------------------ tube scaling
def test_resultants_read_the_rings_own_force():
    """A ring of voxels at uniform axial strain: the model's force is sum(w E_PAHT eps a); the old reading
    (eps x 75 GPa x a) is low by E_t / (w E_PAHT)."""
    ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    zc = 250.0
    cen = np.c_[T["x"] + 10 * np.cos(ang), T["y"] + 10 * np.sin(ang), np.full(24, zc + 1.0)]
    w = 20.7
    eps = 1e-3
    st = np.zeros((24, 6), np.float32)
    st[:, 2] = eps * F.E_PAHT                          # check() hands over phys / w = strain x E_PAHT
    f = {"cen": cen, "idx": np.arange(24), "stress": [st]}
    weight = np.full(24, w)
    rr = B.make_resultants(weight)(f, np.ones(24, bool), [{}])
    N = rr[f"R|{zc:g}"][0, 0]
    assert N == pytest.approx(w * F.E_PAHT * eps * 24 * F.H ** 2, rel=1e-5)
    old = F.tube_resultants(f, np.ones(24, bool), [{}])
    ratio = old[f"R|{zc:g}"][0, 0] / N
    assert ratio == pytest.approx(T["E"] / (w * F.E_PAHT), rel=1e-5)
    # and a pure torsion ring: T = sum(r x tau) a
    st = np.zeros((24, 6), np.float32)
    tau = 10.0 / w
    st[:, 4] = tau * np.cos(ang)                       # tau_yz = tau cos (tangential shear, counter-clockwise)
    st[:, 5] = -tau * np.sin(ang)                      # tau_xz = -tau sin
    rr = B.make_resultants(weight)({**f, "stress": [st]}, np.ones(24, bool), [{}])
    assert rr[f"R|{zc:g}"][0, 5] == pytest.approx(10.0 * 10.0 * 24 * F.H ** 2, rel=1e-4)


# ------------------------------------------------------------------------------------------------ bond rules
def _record(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(F, "OUT", tmp_path)
    meta = [json.dumps(m) for m, _ in rows]
    cuts = {}
    for sd in ("R", "L"):
        for zc in B.RES_CUTS:
            cuts[f"{sd}_{zc:g}"] = np.array([[0.0] * 6 for _ in rows])
        for i, (_, (N, Tq)) in enumerate(rows):
            cuts[f"{sd}_468"][i] = [N, 0, 0, 0, 0, Tq]     # only P3 transfers (free end above)
            cuts[f"{sd}_434"][i] = [N, 0, 0, 0, 0, Tq]     # P2 upper root: no transfer
    np.savez_compressed(tmp_path / "tube_t_fine.npz", meta=np.array(meta), **cuts)


def test_bond_rules_on_a_synthetic_record(tmp_path, monkeypatch):
    lim = {"set": "a", "case": "side_hill_torsion", "factor": 1.5, "scenario": "x"}
    c8 = {"set": "b", "case": "hipbelt_off_abuse", "factor": 1.0, "scenario": "x"}
    _record(tmp_path, monkeypatch, [(lim, (900.0, 30000.0)), (c8, (600.0, 10000.0))])
    v = B.variant_defaults()
    b = B.bonds("t", v, bases=("fine",))["P3 top node"]
    L = 543.5 - 472.0
    kA, kT = B.volkersen_k(L, 0.8, "axial"), B.volkersen_k(L, 0.8, "torque")
    allow = 3.7 * 0.8
    s = B.bond_stresses(900.0, 30000.0, L, kA, kT)
    s8 = B.bond_stresses(600.0, 10000.0, L, kA, kT)
    peak_lim = allow / (s["peak"] / 1.5)
    peak_c8 = allow / s8["peak"]                        # M1: judged at the factored (= limit) load
    assert b["peak"]["margin"] == pytest.approx(min(peak_lim, peak_c8), rel=2e-3)
    assert b["peak_c8"]["margin"] == pytest.approx(peak_c8, rel=2e-3)
    assert b["avg"]["margin"] == pytest.approx(allow / s["avg"], rel=2e-3)
    assert b["limit_transfer"]["dN_n"] == pytest.approx(900.0 / 1.5, abs=0.1)
    assert b["limit_transfer"]["dT_nmm"] == pytest.approx(30000.0 / 1.5, abs=0.1)
    # fail-safe at limit: each of two pins takes half the axial force plus the torque couple
    Fw = math.hypot(600.0 / 2, 20000.0 / T["od"])
    assert b["failsafe_print_bearing"]["margin"] == pytest.approx(
        B.BEARING_PRINT / (Fw / (4.0 * B.SLEEVE_T)), rel=2e-3)
    assert b["failsafe_tube_bearing"]["margin"] == pytest.approx(F.TUBE_BEARING_MPA / (Fw / (4.0 * TW)), rel=2e-3)
    # the torque sensitivity divides only the torque
    b2 = B.bonds("t", v, bases=("fine",), gw=2.3)["P3 top node"]
    assert b2["limit_transfer"]["dT_nmm"] == pytest.approx(30000.0 / 1.5 / 2.3, abs=0.1)


def test_bond_allowable_is_the_cited_floor():
    assert B.BOND_DRY_MPA * B.BOND_HOT_WET == pytest.approx(2.96)
    assert B.BEARING_PRINT == pytest.approx(37.6)


# ------------------------------------------------------------------------------------------------ part separation
def test_part_planes():
    cen = np.array([[0, 0, 191.0], [0, 0, 193.0], [0, 0, 195.0], [0, 0, 467.0], [0, 0, 469.0], [0, 0, 471.0]])
    assert list(B.part_of(cen)) == [1, 0, 2, 2, 0, 3]


def _body():
    p = B.OUT / "body_cflite_p.npz"
    if not p.exists():
        pytest.skip("CF-LITE parts not built (python -m huntkit.gendesign.bl066_cflite parts)")
    return B.build()


def test_printed_parts_are_separate_components():
    """B1: on the re-rastered STLs, P1 / P2 / P3 are three 26-connected bodies (no shared FE node): only the tubes
    join them."""
    con = _body()
    sep = B.separation(con["label"])
    assert sep["separate"]
    assert sep["n_components"] == 3
    assert set(sep["parts"]) == {"P1", "P2", "P3"}
    # and no printed voxel sits in a gap layer
    cen = F._base()["cen"]
    assert not (con["printed"] & (B.part_of(cen) == 0)).any()


def test_exported_stls_rerastered_are_separate():
    """The STL files on disk, re-rastered on the H1 grid, give the same three separate bodies."""
    import trimesh
    con = _body()
    meshes = {nm: trimesh.load(ROOT / s["file"]) for nm, s in con["info"]["stl"].items()}
    for nm, m in meshes.items():
        assert m.is_watertight, nm
    rr = B.rerastered(meshes, con["cf"])
    assert rr["raster_clash_voxels"] == 0
    assert B.separation(rr["label"])["separate"]
    assert (rr["printed"] == con["printed"]).mean() > 0.999
