"""BL-018 modelling layer: hardware dimensions against the material records, watertight solids, webbing / seam / zip
geometry at the specified sizes, the fabric pass's displacement bound, and the studio scene build. The Cycles render
test skips when bpy is not importable."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from huntkit.viz3d import studio
from huntkit.viz3d.assets import arclen, mesh, record
from huntkit.viz3d.assets import fabric as FB
from huntkit.viz3d.assets import hardware as HW
from huntkit.viz3d.assets import seams as SM
from huntkit.viz3d.assets import webbing as WB
from huntkit.viz3d.assets import zips as ZP

REPO = Path(__file__).resolve().parents[1]
TOL = 0.5      # mm, BL-018 acceptance


@pytest.mark.parametrize("kind", sorted(HW.SPECS))
def test_hardware_watertight_and_envelope(kind):
    m = HW.build(kind)
    assert HW.is_watertight(m), f"{kind} has an open or inconsistent component"
    L, W, T = HW.envelope(kind)
    sp = HW.SPECS[kind]
    assert abs(L - sp["L"]) <= TOL
    if not kind.startswith("cam_buckle"):            # the cam pin stands 0.4 mm proud of each cheek
        assert abs(W - sp["W"]) <= TOL
    assert all(c.volume > 0 for c in HW.components(kind).values())


def test_hardware_matches_records():
    r = record("hardware", "ladder_lock_25mm_heavy")
    L, W, T = HW.envelope("ladder_lock_25_heavy")
    assert abs(L - r["outer_length_mm"]) <= TOL and abs(W - r["outer_width_mm"]) <= TOL
    assert abs(T - r["thickness_mm"]) <= TOL
    d = record("hardware", "d_ring_25mm_aluminium")
    L, W, T = HW.envelope("d_ring_25")
    assert abs(T - d["section_thickness_mm"]) <= TOL                 # round section
    assert W - 2 * d["section_thickness_mm"] >= d["width_mm"]        # 25 mm webbing passes inside
    for n, rid in ((5, "coil_zipper_5"), (8, "coil_zipper_8"), (10, "coil_zipper_10")):
        cw = record("hardware", rid)["chain_width_mm"]
        assert HW.SPECS[f"zip_slider_{n}"]["chain"] == cw and ZP.dims(n)["chain"] == cw
        assert HW.SPECS[f"zip_slider_{n}"]["throat"] > cw
    for w in (25, 38, 50):
        assert HW.SPECS[f"side_release_{w}"]["web"] == record("hardware", f"buckle_side_release_{w}mm")["width_mm"]


def _z_ray_hits(m, x, y):
    """Does the vertical line through (x, y) cut the mesh? (2D point-in-triangle on the xy projection.)"""
    V, F = np.asarray(m.vertices)[:, :2], np.asarray(m.faces)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    p = np.array([x, y])
    d1 = (p[0] - b[:, 0]) * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * (p[1] - b[:, 1])
    d2 = (p[0] - c[:, 0]) * (b[:, 1] - c[:, 1]) - (b[:, 0] - c[:, 0]) * (p[1] - c[:, 1])
    d3 = (p[0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (p[1] - a[:, 1])
    neg = (d1 < 0) | (d2 < 0) | (d3 < 0)
    pos = (d1 > 0) | (d2 > 0) | (d3 > 0)
    area = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    return bool(np.any(~(neg & pos) & (area > 1e-9)))


@pytest.mark.parametrize("kind", ["side_release_25", "ladder_lock_25", "tri_glide_25", "g_hook_25"])
def test_slots_are_real_openings(kind):
    """A line along z through a slot must pass through the piece without touching it, over the webbing width."""
    sp = HW.SPECS[kind]
    m = HW.build(kind)
    xs = np.linspace(-sp["L"] / 2 + 1, sp["L"] / 2 - 1, 160)
    clear = [x for x in xs if not _z_ray_hits(m, x + 0.0137, 0.4113)]
    assert len(clear) >= 3, "no through-opening on the centre line"
    wide = [x for x in clear if not _z_ray_hits(m, x + 0.0137, 0.47 * sp["web"]) and not _z_ray_hits(m, x + 0.0137, -0.47 * sp["web"])]
    assert wide, f"no slot as wide as the {sp['web']} mm webbing"


def test_webbing_dimensions_and_threading():
    P = np.column_stack([np.linspace(0, 200, 40), np.zeros(40), np.zeros(40)])
    s = WB.strap(P, [0, 0, 1.0], 25.0)
    ext = s.vertices.max(0) - s.vertices.min(0)
    assert abs(ext[0] - 200) < 0.5 and abs(ext[1] - 25.0) < 0.3 and abs(ext[2] - WB.thickness(25) * 1.08) < 0.2
    assert s.is_watertight
    uv = s.metadata["uv"] * 500.0
    assert abs(np.ptp(uv[:, 0]) - 25.0) < 1.0 and abs(np.ptp(uv[:, 1]) - 200.0) < 1.0      # true-scale weave UVs
    for kind in ("side_release_25", "ladder_lock_25", "g_hook_25"):
        kit = WB.threading(kind)
        assert kit["webbing"] and kit["thread"]
        top = max(q.vertices[:, 2].max() for q in kit["webbing"])
        assert top > 0, "the wrap must pass over a bar, above the piece's mid-plane"
    t = WB.tail([0, 0, 0], [1, 0, 0], [0, 1.0, 0], length=80.0)
    assert t.vertices[:, 2].min() < -20, "a free tail hangs"
    assert "thread" in t.metadata.get("extras", {}), "tail end is folded and bartacked"
    k = WB.keeper([0, 0, 0], [0, 0, 1.0], [1.0, 0, 0], 25.0)
    assert np.ptp(k.vertices[:, 1]) > 25.0 and abs(np.ptp(k.vertices[:, 0]) - 12.0) < 1.5


def test_stitch_pitch_and_seam():
    P = np.column_stack([np.linspace(0, 300, 100), np.zeros(100), np.zeros(100)])
    N = np.tile([0, 0, 1.0], (100, 1))
    row = SM.stitch_row(P, N, pitch=3.0)
    n_st = len(row.vertices) // 16
    assert n_st == 100, f"{n_st} stitches on 300 mm at 3.0 mm"
    s = SM.seam(P, N)
    z = s["ridge"].vertices[:, 2]
    assert 0.6 < z.max() < 1.6, "ridge is raised geometry, about 1 mm"
    assert np.ptp(s["ridge"].vertices[:, 1]) > SM.ALLOWANCE
    zz = s["ridge"].vertices[:, 2].reshape(-1, 9)[:, 4]                 # along the topstitch line
    assert zz.std() > 0.02, "pucker: the ridge height varies along the seam"
    bt = SM.bartack([0, 0, 0], [0, 0, 1.0], [1.0, 0, 0], width=20.0)
    assert abs(np.ptp(bt.vertices[:, 0]) - 20.0) < 1.0
    bx = SM.box_x([0, 0, 0], [0, 0, 1.0], [1.0, 0, 0], 25.0, 19.0)
    assert abs(np.ptp(bx.vertices[:, 0]) - 25.0) < 1.5 and abs(np.ptp(bx.vertices[:, 1]) - 19.0) < 1.5


def test_zip_geometry():
    P = np.column_stack([np.linspace(0, 200, 60), np.zeros(60), np.zeros(60)])
    z = ZP.coil_zip(P, [0, 0, 1.0], 10, sliders=(0.25,), closed=(0.25, 1.0))
    d = ZP.dims(10)
    coil_w = np.ptp(z["coil"].vertices[z["coil"].vertices[:, 0] > 80][:, 1])
    assert abs(coil_w - d["chain"]) < 1.5, f"meshed chain {coil_w:.1f} vs record {d['chain']}"
    assert abs(np.ptp(z["tape"].vertices[:, 1]) - 2 * d["tape"]) < 1.0
    for k in ("slider", "cord", "grip", "thread"):
        assert len(z[k].faces) > 0
    half = ZP.coil_zip(P, [0, 0, 1.0], 10, closed=(0.0, 0.0), half=1, sliders=())
    assert len(half["coil"].faces) > 0 and half["tape"].vertices[:, 1].min() > 0


def _sheet(n=50, comp=0.94):
    x, y = np.meshgrid(np.linspace(0, 400, n), np.linspace(0, 400, n))
    V = np.column_stack([x.ravel() * comp, y.ravel(), np.zeros(n * n)])
    F = []
    for i in range(n - 1):
        for j in range(n - 1):
            a = i * n + j
            F += [[a, a + 1, a + n + 1], [a, a + n + 1, a + n]]
    return mesh(V, np.array(F), np.column_stack([x.ravel(), y.ravel()]) / 500.0)


def test_fabric_pass_bound_and_taut_vs_slack():
    slack = FB.refine(_sheet(comp=0.94), 1)
    taut = FB.refine(_sheet(comp=1.03), 1)
    ec, d, st = FB.strain_field(slack.vertices, slack.faces, slack.metadata["uv"] * 500.0)
    assert abs(ec.mean() - 0.06) < 0.005 and abs(abs(d[:, 0]).mean() - 1.0) < 0.01     # 6 % compression along x
    o1, r1 = FB.displace(slack)
    o2, r2 = FB.displace(taut)
    assert r1["max_abs_mm"] <= 5.0 and r2["max_abs_mm"] <= 5.0
    assert FB.deviation(slack.vertices, o1.vertices)[0] <= 5.0 + 1e-6                 # BL-018: shape moves <= 5 mm
    assert r1["rms_mm"] > 3 * r2["rms_mm"], "a slack panel wrinkles, a taut one stays nearly flat"
    # seam crease + strap dent
    seam = np.column_stack([np.full(60, 188.0), np.linspace(0, 400, 60), np.zeros(60)])
    strap = np.column_stack([np.linspace(20, 360, 60), np.full(60, 100.0), np.zeros(60)])
    o3, _ = FB.displace(taut, seams=[seam], straps=[(strap, 25.0)])
    V = o3.vertices
    on_seam = (np.abs(taut.vertices[:, 0] - 188.0) < 1.5) & (taut.vertices[:, 1] > 200)
    assert V[on_seam, 2].mean() < -0.6, "the cloth dips at the seam line"
    under = (np.abs(taut.vertices[:, 1] - 100.0) < 8) & (taut.vertices[:, 0] > 220) & (taut.vertices[:, 0] < 340)
    beside = (np.abs(np.abs(taut.vertices[:, 1] - 100.0) - 21.5) < 3) & (taut.vertices[:, 0] > 220) & (taut.vertices[:, 0] < 340)
    assert V[under, 2].mean() < -0.5 and V[beside, 2].mean() > 1.0, "pressed in under the webbing, pillowed beside it"
    th = FB.solidify(taut, 0.6)
    assert len(th.vertices) == 2 * len(taut.vertices)


def test_scene_build_and_manifest(tmp_path):
    sc = studio.hardware_sheet_scene("t_sheet")
    js = sc.build(tmp_path, verbose=False)
    spec = json.loads(js.read_text())
    assert (tmp_path / spec["glb"]).stat().st_size > 100_000
    names = set(spec["parts"])
    assert {"swatch", "side_release_25", "side_release_25__webbing", "side_release_25__thread", "demo_zip__coil",
            "demo_seam__ridge", "demo_seam__thread"} <= names
    assert spec["report"]["fabric"]["swatch"]["dev_max_mm"] <= 5.0
    assert all(spec["parts"][n]["material"] in spec["materials"] for n in names)
    sh = studio.shots("hero", "side", detail={"view": {"at": [0, 0, 100], "span": 80}})
    assert sh["detail"]["view"]["fov"] == 14 and sh["hero"]["view"]["frame"] == "pack"


def _bpy_python():
    return studio.find_bpy_python() if not studio._has_bpy() else sys.executable


@pytest.mark.skipif(_bpy_python() is None, reason="bpy not available (set HUNTKIT_BPY)")
def test_render_with_wearer_hook(tmp_path):
    sc = studio.hardware_sheet_scene("t_sheet")
    env_pp = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = f"{REPO}{os.pathsep}{env_pp}"
    try:
        res = studio.render(sc, {"t": {"view": {"az": -20, "el": 20, "fov": 24}, "state": {}, "caption": "t"}},
                            tmp_path / "out", prefix="t", quality={"res": (160, 120), "samples": 2},
                            wearer="huntkit.viz3d.studio:marker_wearer", wearer_kwargs={"height_m": 0.4},
                            pack_on_torso=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0.05], [0, 0, 0, 1]],
                            work_dir=tmp_path)
    finally:
        os.environ["PYTHONPATH"] = env_pp
    from PIL import Image
    im = np.asarray(Image.open(res[0]["file"]).convert("RGB")).astype(float)
    assert im.shape[1] == 160 and im[:120].std() > 5, "a lit, non-uniform frame"
    _ = subprocess
