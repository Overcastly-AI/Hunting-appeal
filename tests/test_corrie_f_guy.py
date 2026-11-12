"""BL-028 CORRIE F guy routing: the taut-strap path solver against closed-form cases, and the stored results
(real path on the fine drapes, lifter gap, the fix's CG and R-28).

    python -m pytest -q tests/test_corrie_f_guy.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = ROOT / "designs" / "pack_5200" / "concepts"
for p in (str(ROOT), str(CONCEPTS), str(CONCEPTS / "corrie_f_sim")):
    if p not in sys.path:
        sys.path.insert(0, p)

import corrie_f as F  # noqa: E402


def _cylinder(R=100.0, H=400.0, n=128, dz=20.0, flip=False):
    """Closed faceted cylinder, axis z, centred on x = y = 0, z 0..H, rings every dz (cloth-mesh-like facets)."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    zs = np.linspace(0.0, H, int(round(H / dz)) + 1)
    X = np.vstack([np.column_stack([R * np.cos(a), R * np.sin(a), np.full(n, z)]) for z in zs])
    m = len(zs)
    cb, ct = m * n, m * n + 1
    X = np.vstack([X, [[0, 0, 0], [0, 0, H]]])
    T = []
    for r in range(m - 1):
        for i in range(n):
            j = (i + 1) % n
            p, q = r * n, (r + 1) * n
            T += [[p + i, p + j, q + j], [p + i, q + j, q + i]]
    top = (m - 1) * n
    for i in range(n):
        j = (i + 1) % n
        T += [[cb, j, i], [ct, top + i, top + j]]
    T = np.asarray(T)
    return X, (T[:, ::-1] if flip else T)


@pytest.mark.parametrize("flip", [False, True])
def test_cloth_surface_normals_point_out_whatever_the_winding(flip):
    X, T = _cylinder(flip=flip)
    s = F.ClothSurface(X, T)
    assert s.signed(np.array([[150.0, 0.0, 200.0]]))[0] > 0      # outside
    assert s.signed(np.array([[50.0, 0.0, 200.0]]))[0] < 0       # inside


def test_taut_path_round_a_cylinder_matches_the_closed_form():
    """Strap from one side of a round body to the other, round its +x side: two tangents and an arc of radius R + clear.
    The solver's length and wrap angle agree with the closed form within 1 % / 3 deg."""
    R, d, c = 100.0, 200.0, F.PATH_CLEAR
    X, T = _cylinder(R)
    s = F.ClothSurface(X, T)
    A, B = np.array([0.0, -d, 200.0]), np.array([0.0, d, 200.0])
    P = F.taut_path(s, A, B, [400.0, 0.0, 200.0])
    Rc = R * math.cos(math.pi / 128) + c                   # facets sit inside the circle by R (1 - cos(pi / n))
    al = math.acos(Rc / d)
    L = 2 * math.sqrt(d * d - Rc * Rc) + Rc * (math.pi - 2 * al)
    Ls = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    assert Ls == pytest.approx(L, rel=0.01)
    assert P[:, 0].min() > -1.0                            # went round the +x side
    m = F.path_metrics(P, s, A, B, 19.0)
    assert m["wrap_deg"] == pytest.approx(math.degrees(math.pi - 2 * al), abs=3.0)
    assert m["friction_share"] == pytest.approx(1 - math.exp(-F.MU_WEB_FAB * math.radians(m["wrap_deg"])), abs=1e-3)
    # the pull on the body leaves along the first tangent: from the tangent point toward A, mostly -y
    assert m["u_bag"][1] < -0.8 and m["fwd_share_bag"] > 0.8


def test_free_strap_is_straight_with_no_wrap():
    X, T = _cylinder(R=50.0)
    s = F.ClothSurface(X, T)
    A, B = np.array([200.0, -100.0, 200.0]), np.array([200.0, 100.0, 300.0])
    P = F.taut_path(s, A, B, [300.0, 0.0, 250.0])
    m = F.path_metrics(P, s, A, B, 19.0)
    assert m["length_mm"] == pytest.approx(m["straight_mm"], abs=0.5)
    assert m["wrap_deg"] < 1.0 and m["friction_share"] < 0.01
    assert m["b22_along_straight"] > 0.999


def test_crown_tubes_match_the_sim_crown_and_lifter_sits_on_the_corner():
    tb = F.crown_tubes(601.0)
    bar = tb[0]
    assert bar[0][2] == bar[1][2] == 601.0 and bar[0][1] == pytest.approx(13.7, abs=0.1)   # attach_system: 13.7
    la, lb = F.lifter_line(15.0)
    assert la[0] == F.LIFTER_X and la[2] == 601.0 and lb[1] < la[1] and lb[2] < la[2]   # forward and down


# ------------------------------------------------------------------------------------------------ stored results
def _paths():
    if not F.GUY_PATHS.exists():
        pytest.skip("corrie_f_guy_paths.json not written (python designs/pack_5200/concepts/corrie_f.py --bl028)")
    return json.loads(F.GUY_PATHS.read_text())


def test_real_path_runs_round_the_bag_and_loses_the_straight_line_pull():
    """On every rev 1 fine drape (15 / 19 / 23 in, fill and meat) the guy wraps the bag's side (longer than straight,
    > 120 deg of wrap), and its forward pull on the bag is well under the straight model's."""
    rows = [r for k, r in _paths()["rows"].items() if r["route"].startswith("straight") and r["case"] in ("fill", "meat")]
    assert {(r["torso"], r["case"]) for r in rows} >= {(t, c) for t in (15, 19, 23) for c in ("fill", "meat")}
    for r in rows:
        for s in ("R", "L"):
            m = r[s]
            assert m["length_mm"] > 1.3 * m["straight_mm"]
            assert m["wrap_deg"] > 120.0
            assert m["fwd_share_bag"] < 0.75 * m["fwd_share_straight"]


def test_guy_clears_the_lifter_by_10_mm_on_every_drape():
    for k, r in _paths()["rows"].items():
        for s in ("R", "L"):
            assert r[s]["lifter_gap_mm"] >= F.MIN_CLEAR_MM, (k, s, r[s]["lifter_gap_mm"])


def test_sim_routing_rebuilds_the_guy_through_eyelets_and_restores_huntkit():
    """corrie_f_sim's BL-028 swap: TG_R runs bag end -> eyelets -> bar anchor with a rest length from that drafted
    path; an internal tie is a bag-to-bag cable; 'off' deletes the guy; huntkit's PackModel is restored after."""
    import corrie_f_sim as S
    from huntkit.clothsim.pack import PackModel, load_scenario
    orig = PackModel._attachments
    S.ROUTE.clear()
    S.ROUTE.update({"name": "t", "R": {"vias": [683, 951], "b22": None, "internal": {"TI_R": [1204, 745]}},
                    "L": {"off": True}})
    S.install(None)
    S._install_route()
    try:
        pm = PackModel(load_scenario(str(S.scenario_path(15, F.REVS[1]["guy_x"]))), fine=True, verbose=False)
    finally:
        S.uninstall()
        S.ROUTE.clear()
    assert PackModel._attachments is orig
    cb = pm.cables["TG_R"]
    assert list(cb.nodes[1:-1]) == [683, 951] and cb.nodes[-1] == -1
    X0 = pm.mesh.X0
    P = np.vstack([X0[cb.nodes[0]], X0[683], X0[951], cb.fixed[-1]])
    assert cb.meta["L_init"] == pytest.approx(float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum()), abs=1e-6)
    assert cb.L0 < cb.meta["L_init"]                                   # 30 N pretension
    assert "TG_L" not in pm.cables and list(pm.cables["TI_R"].nodes) == [1204, 745]


def test_rev2_adds_only_the_port_and_revs_stay_reproducible():
    with F.revision(1):
        r1 = F.parts("M", "D2")
    with F.revision(2):
        assert F.REVISION == 2 and F.GUY_X == 52.0
        r2 = F.parts("M", "D2")
    assert F.REVISION == 3                                              # BL-030: rev 3 is the module default
    new = [r for r in r2 if r["name"].startswith("BL-028")]
    assert len(new) == 1 and new[0]["system"] == "attachment"
    p = F.guy_port()
    assert sum(r["g"] for r in r2) - sum(r["g"] for r in r1) == pytest.approx(p["mass_g"], abs=0.01)
    assert p["mass_g"] == pytest.approx(p["area_mm2"] * F._gsm(p["material"]) / 1e6, abs=0.01) and p["mass_g"] < 5.0
    assert p["z_mm"][0] < 601.0 and p["z_mm"][1] == 745.0          # covers the 15 in bar, ends at B-01's top edge


def _table():
    t = F.bl028_table()
    if t["cg15_meat"]["rev 1 real: round the bag (eyelets on its path)"] is None or t["fix"][15]["meat"] is None:
        pytest.skip("BL-028 sim rows not stored")
    return t


def test_rev1_real_routing_fails_rev_c_and_rev2_takes_most_of_it_back():
    t = _table()
    c = t["cg15_meat"]
    real = c["rev 1 real: round the bag (eyelets on its path)"]
    assert real["converged"] and real["cg_y"] > 190.0                  # rev 1 as it would really be built: over rev C
    assert c["internal depth tie + rev 1 wrap"]["cg_y"] > 190.0        # a depth tie alone does nothing
    fix = t["fix"][15]["meat"]
    assert fix["converged"] and fix["cg_y"] <= 190.0 and fix["cg_y"] < real["cg_y"] - 10.0
    a = t["acceptance"]
    assert a["cg15_ok"] == (fix["cg_y"] <= 180.0)                      # the flag tells the truth either way
    assert a["cg15_short_mm"] == pytest.approx(max(0.0, fix["cg_y"] - 180.0), abs=0.05)


def test_rev2_r28_and_lifter_gap():
    t = _table()
    for tor in (15, 19, 23):
        if t["fix"][tor]["r28_deg"] is None:
            pytest.skip(f"rev 2 fine run at {tor} in not stored")
        assert t["fix"][tor]["r28_deg"] >= 31.0
    for k, r in t["paths"].items():
        if r["route"] == "port":
            for s in ("R", "L"):
                assert r[s]["outside_mm"] < 100.0                    # outside the bag only from the bar to the port
                assert r[s]["lifter_gap_mm"] >= 25.0


def test_rev1_real_guy_is_longer_than_booked():
    g = F.guy_length_check()
    if not g:
        pytest.skip("corrie_f_guy_paths.json not written")
    assert all(v["extra_mm"] > 100.0 for v in g.values())
