"""BL-020 render-only cloth pass (huntkit/viz3d/cloth_pass.py).

The geometry tests run anywhere. The solver tests need Blender's Python (``bpy`` importable here, or the venv named
by HUNTKIT_BPY, see huntkit/viz3d/README.md) and skip without it. The S15 test also needs the huntkit full drape in
``outputs/`` (not tracked) and skips without it.
"""
from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from huntkit.viz3d import cloth_pass as CP

P = CP.ClothParams()


def _has_solver() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        py = os.environ.get("HUNTKIT_BPY")
        return bool(py and Path(py).exists())


needs_bpy = pytest.mark.skipif(not _has_solver(), reason="needs bpy (set HUNTKIT_BPY to the Blender venv's python)")


# ------------------------------------------------------------------------------------------------- roll geometry
def test_roll_takes_the_collar_length():
    for length in (175.0, 405.0, 425.0):
        Q, N, r_out = CP.roll_section(length, P, per_turn=200)
        arc = np.linalg.norm(np.diff(Q, axis=0), axis=1).sum()
        assert abs(arc - length) < 0.03 * length                 # the wound polyline is the collar that went in
        assert abs(r_out - (P.roll_core + P.roll_pitch * N)) < 1e-9
    # the 175 mm of collar above the fill line makes about three turns; more collar = more turns, a fatter roll
    assert 2.4 < CP.roll_turns(175.0, P) < 3.3
    assert CP.roll_turns(425.0, P) > CP.roll_turns(175.0, P) + 2.0


def test_roll_section_is_a_spiral_that_never_crosses_itself():
    Q, N, r_out = CP.roll_section(175.0, P, per_turn=120)
    # distance from the flat's axis shrinks monotonically turn over turn
    d = np.where(np.abs(Q[:, 0]) <= P.roll_fold / 2, np.abs(Q[:, 1]),
                 np.hypot(np.abs(Q[:, 0]) - P.roll_fold / 2, Q[:, 1]))
    assert np.all(np.diff(d) < 1e-6)
    assert abs(d[0] - r_out) < 1e-6 and d[-1] >= P.roll_core - 1e-6


def test_arch_keeps_the_lip_length_and_bends_the_ends_down():
    s = np.linspace(-277.0, 277.0, 2000)
    x, z, tx, tz = CP.arch(s, 1000.0, P)
    arc = np.hypot(np.diff(x), np.diff(z)).sum()
    assert abs(arc - 554.0) < 0.5                                  # inextensible: the lip is carried, not stretched
    mid = np.abs(s) < P.roll_flat
    assert np.allclose(z[mid], 1000.0)
    assert z[0] < 1000.0 - 60 and z[-1] < 1000.0 - 60 and abs(z[0] - z[-1]) < 1e-6
    assert np.allclose(np.hypot(tx, tz), 1.0)


def test_bend_for_drop():
    full = CP.end_drop(P.roll_bend_deg, 277.0, P)
    assert CP.bend_for_drop(full + 50, 277.0, P) == pytest.approx(P.roll_bend_deg)
    d = CP.bend_for_drop(30.0, 277.0, P)
    assert 0 < d < P.roll_bend_deg
    assert CP.end_drop(d, 277.0, P) == pytest.approx(30.0, abs=0.1)


def test_roll_mesh_sits_on_the_lip_line():
    lip = {"half": 277.0, "y": 170.0, "z": 1000.0}
    m, info, C, fr = CP.roll_mesh(lip, 175.0, P)
    V = np.asarray(m.vertices)
    k = len(V) // len(C)
    first = V.reshape(len(C), k, 3)[:, 0]                           # the outer end of the spiral = the lip line
    assert np.allclose(first, fr["L0"], atol=1e-6)
    assert info["width_mm"] == pytest.approx(P.roll_fold + 2 * fr["r_out"], abs=0.1)
    assert 25 < info["width_mm"] < 45 and 8 < info["thick_mm"] < 20
    assert V[:, 1].min() >= lip["y"] - fr["r_out"] - 1e-6            # the roll lies aft of the lip


# ------------------------------------------------------------------------------------------ proxies and straps
def _fake_seed():
    """A 400 x 200 x 700 box 'drape' with the piece names the pass looks for."""
    V, F, uv, g = CP.box_mesh(400.0, 200.0, 700.0, h=25.0)
    V = V + [0.0, 110.0, 385.0]
    c = V[F].mean(1)
    piece = np.where(c[:, 1] < 10.5, "B-01", np.where(c[:, 2] < 35.5, "B-05", "B-02u"))
    return {"X": V, "X0": V.copy(), "tris": F, "piece": piece, "uv": uv}


def test_block_proxy_holds_the_state_volume():
    sd = _fake_seed()
    for litres, spec in ((12.0, CP.PROXY["day"]), (45.0, CP.PROXY["sixday"])):
        V, F, info = CP.block_proxy(sd, litres, spec["w"], spec["z1"], spec["ex"], spec["ez"])
        assert CP.signed_volume_L(V, F) == pytest.approx(litres, abs=0.05)      # closed, wound outward
        assert V[:, 1].min() >= 10.0 + 3.9                                      # lies on the frame face, not in it
        assert V[:, 2].max() <= spec["z1"] + 1e-6
    d12 = CP.block_proxy(sd, 12.0, **CP.PROXY["day"])[2]["depth_mm"]
    d45 = CP.block_proxy(sd, 45.0, **CP.PROXY["sixday"])[2]["depth_mm"]
    assert d12 < d45


def test_outward_winding():
    V, F, _, _ = CP.box_mesh(100.0, 80.0, 60.0, h=20.0)
    assert CP.signed_volume_L(V, F) == pytest.approx(0.48, abs=1e-6)
    assert CP.signed_volume_L(V, CP.outward(V, F[:, ::-1])) > 0


def test_taut_path_goes_round_the_aft_face_and_climbs():
    sd = _fake_seed()
    w = {"id": "W1", "R": np.array([115.0, 10.5, 80.0]), "L": np.array([-115.0, 7.3, 250.0])}
    Vd, Fd, _ = CP.subdivide(sd, 2)["X"], None, None
    Pth = CP.taut_path(w, [Vd], bite=2.0)
    assert Pth[0, 0] > 150 and Pth[-1, 0] < -150                    # right corner to left corner
    assert Pth[:, 1].max() == pytest.approx(210.0 + 2.0, abs=2.5)   # over the aft face, 2 mm proud
    assert np.all(np.diff(Pth[:, 2]) > 0) and 80 < Pth[0, 2] < Pth[-1, 2] < 250
    length = np.linalg.norm(np.diff(Pth, axis=0), axis=1).sum()
    assert 780 < length < 860                                       # 200 + 400 + 200 plus the climb and the bite
    # a smaller obstacle = a shorter taut line (the strap closes on the contents)
    small = Vd.copy()
    small[:, 1] = 10.5 + (small[:, 1] - 10.5) * 0.4
    assert np.linalg.norm(np.diff(CP.taut_path(w, [small], bite=2.0), axis=0), axis=1).sum() < length - 200


def test_strap_slab_is_a_closed_solid_outside_the_line():
    t = np.linspace(0, np.pi, 40)
    Pth = np.column_stack([200 * np.cos(t), 200 * np.sin(t), np.linspace(100, 150, 40)])
    V, F = CP.strap_slab(Pth, 25.0, 45.0)
    e = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    assert np.all(cnt == 2)                                         # watertight
    assert CP.signed_volume_L(V, F) > 0
    assert np.hypot(V[:, 0], V[:, 1]).min() > 199.0                 # nothing of the slab is inside the strap line


def test_box_mesh_and_departure():
    V, F, uv, g = CP.box_mesh(280.0, 190.0, 60.0)
    assert CP.signed_volume_L(V, F) == pytest.approx(280 * 190 * 60 / 1e6, rel=1e-6)
    assert set(g) == {"top", "bottom", "aft", "fore", "right", "left"}
    assert np.allclose(V[g["top"]][..., 2], 30.0) and np.allclose(V[g["aft"]][..., 1], 95.0)
    meta = {"straps": [{"P1": [[0.0, 95.0, 0.0], [10.0, 95.0, 0.0]]}], "lip": {"half": 100.0, "y": 0.0, "z": 500.0},
            "params": CP.asdict(P)}
    W = V.copy()
    W[:, 0] += 4.0
    d = CP.departure(V, W, F, meta)
    assert d["all_mean_mm"] == pytest.approx(4.0) and d["body_max_mm"] == pytest.approx(4.0)
    assert 0 < d["body_share"] < 1 and d["over_15mm_share"] == 0


# ---------------------------------------------------------------------------------------------- Blender solver
def _sheet(n=31, size=300.0, z=120.0):
    u = np.linspace(-size / 2, size / 2, n)
    X, Y = np.meshgrid(u, u, indexing="ij")
    V = np.column_stack([X.ravel(), Y.ravel(), np.full(n * n, z)])
    idx = np.arange(n * n).reshape(n, n)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    return V, np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])


@needs_bpy
def test_cloth_job_drapes_a_sheet_over_a_ball(tmp_path):
    import trimesh
    V, F = _sheet()
    ball = trimesh.creation.icosphere(subdivisions=3, radius=80.0)
    out = CP.cloth_job("sheet", V, F, colliders=[("ball", np.asarray(ball.vertices), np.asarray(ball.faces))],
                       params=replace(P, bending=0.3), frames=(2, 48), work=tmp_path, vertex_mass=0.004)
    assert out.shape == V.shape and np.isfinite(out).all()
    r = np.linalg.norm(out, axis=1)
    assert r.min() > 79.0                                           # nothing went through the ball
    centre = np.argmin(np.hypot(V[:, 0], V[:, 1]))
    corner = np.argmax(V[:, 0] + V[:, 1])
    assert out[centre, 2] > 78.0                                    # held up by the ball
    assert out[corner, 2] < out[centre, 2] - 30.0                   # corners hang (still settling at 2 s)
    e0 = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1)
    e1 = np.linalg.norm(out[F[:, 0]] - out[F[:, 1]], axis=1)
    assert np.percentile(np.abs(e1 / e0 - 1), 95) < 0.08            # it folded, it did not stretch


@needs_bpy
def test_render_cloth_pass_hook_solves_registered_parts(tmp_path):
    import trimesh
    from huntkit.viz3d import studio
    from huntkit.viz3d.assets import mesh as amesh
    V, F = _sheet(n=21, size=200.0, z=70.0)
    sc = studio.ConceptScene("bl020_hook")
    sc.add_fabric("sheet", amesh(V, F, V[:, :2] / 500.0), "body")
    ball = trimesh.creation.icosphere(subdivisions=2, radius=50.0)
    pin = (np.hypot(V[:, 0], V[:, 1]) < 12.0).astype(float)         # sewn down at the middle
    CP.register(sc, "sheet", pin=pin, colliders=[("ball", np.asarray(ball.vertices), np.asarray(ball.faces))],
                frames=(2, 30), vertex_mass=0.004)
    rep = CP.apply(sc, {"bending": 0.3}, work=tmp_path)
    out = np.asarray(sc.parts[0].mesh.vertices)
    assert rep["sheet"]["moved_max_mm"] > 30.0
    assert np.allclose(out[pin > 0], V[pin > 0], atol=0.5)          # pinned vertices stay
    assert CP.apply(sc, True, work=tmp_path) == {}                  # a second call does not solve again
    assert "cloth_pass" in studio.render.__code__.co_varnames


@needs_bpy
def test_s15_full_stays_on_the_huntkit_drape():
    SS = CP._ss()
    if not (SS.RENDER_DIR / "S15_PR19_fine" / "skin_full.pkl").exists():
        pytest.skip("needs the huntkit full drape: python designs/pack_5200/concepts/shell_sweep.py render full")
    r = CP.run("full", CP.ClothParams(level=1))
    d = r["departure"]
    assert d["body_mean_mm"] < 6.0 and d["over_15mm_share"] < 0.03  # away from roll and straps: on the drape
    assert d["all_max_mm"] > 60.0                                   # the closure's ears really were bent down
    assert abs(r["volume_L"] - r["seed_volume_L"]) < 5.0
    lip = r["meta"]["lip"]
    V, X0 = r["skin"]["X"], r["skin"]["X0"]
    top = np.where(X0[:, 2] > X0[:, 2].max() - 1e-3)[0]
    x, z, _, _ = CP.arch(X0[top, 0], lip["z"], CP.ClothParams(**r["meta"]["params"]))
    assert np.abs(V[top, 0] - x).max() < 1.0 and np.abs(V[top, 2] - z).max() < 1.0    # lip carried to the roll line
