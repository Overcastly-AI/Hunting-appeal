"""BL-012: CORRIE F studio scene (huntkit/viz3d/corrie_f.py).

The geometry tests run anywhere. The scene test needs Blender's Python (HUNTKIT_BPY, see huntkit/viz3d/README.md) and
CORRIE F's fine drape in ``outputs/`` (not tracked); it skips without either.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from huntkit.viz3d import cloth_pass as CP
from huntkit.viz3d import corrie_f as CF


def _has_solver() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except ImportError:
        py = os.environ.get("HUNTKIT_BPY")
        return bool(py and Path(py).exists())


def _flat_face(n=41):
    """A flat aft face in the drafted frame: x -200..200, z 35..745, one piece 'B-02u', ringed by a gusset strip."""
    BC, CO, F, CS = CF._mods()
    c = F.make()
    xs = np.linspace(-float(c.a([400.0])[0]), float(c.a([400.0])[0]), n)
    zs = np.linspace(BC.Z0, c.z_c, 2 * n)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    half = np.asarray(c.a(Z.ravel()), float)
    V = np.column_stack([X.ravel() * half / half.max(), np.full(X.size, 200.0), Z.ravel()])
    idx = np.arange(X.size).reshape(X.shape)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    T = np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    return c, {"X": V.copy(), "X0": V.copy(), "tris": T, "piece": np.array(["B-02u"] * len(T)),
               "uv": V[:, [0, 2]].copy()}


def test_provider_is_registered_and_default_shells_are_untouched():
    assert CP.SHELL_PROVIDERS[CF.SHELL] is CF.PV
    assert isinstance(CP.provider("S15"), CP._SweepShell)
    # BL-012's new parameters default to the BL-020 constants, so the S15 cache keys do not move
    p = CP.ClothParams()
    assert (p.clip_below_seam, p.clip_run) == (CP.CLIP_BELOW_SEAM, CP.CLIP_RUN) == (60.0, 45.0)
    assert CF.CLIP_BELOW_SEAM_MM > p.clip_below_seam            # CORRIE F: the tab sits lower


def test_lower_clip_tab_bends_the_roll_ends_further_down():
    half = 277.0
    lo = CP.ClothParams()
    out = {}
    for name, below in (("b2", lo.clip_below_seam), ("f", CF.CLIP_BELOW_SEAM_MM)):
        drop = 22.0 + below - lo.clip_run                        # day load: lip 22 mm above the collar seam
        deg = CP.bend_for_drop(drop, half, lo)
        q = CP.ClothParams(roll_bend_deg=deg)
        x, z, _, _ = CP.arch(np.array([half]), 0.0, q)
        out[name] = (deg, float(x[0]), float(-z[0]))
    assert out["f"][0] > out["b2"][0] + 20.0                     # degrees
    assert out["f"][1] < out["b2"][1] - 25.0                     # the end reaches less far out to the side (mm)
    assert out["f"][2] > out["b2"][2] + 50.0                     # and ends lower


def test_d2_recut_areas_match_the_drafted_door():
    BC, CO, F, CS = CF._mods()
    c, sk = _flat_face()
    r = CF.d2_recut(sk)
    assert len(r["X"]) == len(sk["X"]) and r["tris"].shape == sk["tris"].shape
    assert set(np.unique(r["piece"])) == {"B-02door", "B-02h", "B-02u"}
    T, V = r["tris"], r["X0"]
    A = 0.5 * np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1)
    area = {k: float(A[r["piece"] == k].sum()) for k in ("B-02door", "B-02h", "B-02u")}
    # door: between the blades from z 110 to 650, less the two R 55 corner cut-offs
    zz = np.linspace(F.D2["z_lo"], F.D2["z_hinge"], 2000)
    w = 2 * (np.asarray(c.a(zz), float) - np.asarray(F.blade_w(c, zz), float))
    want = float(np.sum(0.5 * (w[1:] + w[:-1]) * np.diff(zz))) - 2 * (1 - np.pi / 4) * F.D2["r"] ** 2
    assert abs(area["B-02door"] - want) < 0.015 * want
    # clear width at IM2 as corrie_f.clear_width has it (plus the two chains it takes off)
    m = (r["piece"] == "B-02door")
    vz = V[np.unique(T[m])]
    row = vz[np.abs(vz[:, 2] - 330.0) < 12.0]
    assert abs(np.ptp(row[:, 0]) - (F.clear_width(c, "D2", 330.0) + 2 * F.CHAIN10)) < 6.0
    # every vertex moved at most half an edge of the test grid, and only inside the face
    d = np.linalg.norm(r["X0"] - sk["X0"], axis=1)
    assert d.max() < 12.0
    assert area["B-02h"] > 0 and area["B-02u"] > 0
    assert abs(sum(area.values()) - float(A.sum())) < 1e-6


def test_d2_fields_signs():
    BC, CO, F, CS = CF._mods()
    c = F.make()
    g, d = CF.d2_fields(c, np.array([0.0, 0.0, 0.0, 190.0, 150.0]), np.array([330.0, 60.0, 700.0, 330.0, 112.0]))
    assert d[0] > 0 and d[1] < 0 and d[2] < 0 and d[3] < 0       # door, kick strip, hinge band, blade
    assert g[2] > 0 and g[3] < 0                                 # hinge band is between the blades; the blade is not
    assert d[4] < 0                                              # the rounded corner is cut off the door


def test_carabiner_envelope():
    m = CF.carabiner([0, 0, 0], [0, 0, 1.0], [0, -1.0, 0])
    ext = np.ptp(np.asarray(m.vertices), axis=0)
    assert abs(ext[2] - CF.BINER["L"]) < 6.0 and abs(ext[0] - CF.BINER["W"]) < 6.0 and ext[1] < 12.0


def test_shot_list_covers_the_ticket_and_labels_the_figure():
    for k in CF.ORDER:
        assert k in CF.SHOTS
    for k, s in CF.SHOTS.items():
        if s.get("pose"):
            assert CF.NOT_A_PHOTO in s["sub"], k                 # every shot with the hunter says it is a render
        else:
            assert CF.MODEL in s["sub"], k                       # display-form shots say so too
        assert len(s["sub"]) <= CF.SUB_MAX, (k, len(s["sub"]))   # the caption band does not cut the line off
    cams = [tuple(CF.SHOTS[k]["view"][a] for a in ("az", "el", "fov")) + tuple(CF.SHOTS[k]["view"]["box"])
            for k in ("hero", "day", "full")]
    assert cams[0] == cams[1] == cams[2]                         # the three load states share one camera
    assert {CF.SHOTS[k]["scene"] for k in ("hero", "day", "full")} == {"sixday", "day", "full"}


@pytest.mark.skipif(not _has_solver(), reason="needs bpy (set HUNTKIT_BPY to the Blender venv's python)")
def test_scene_builds_as_corrie_f():
    BC, CO, F, CS = CF._mods()
    if not (CS.run_dir("F", CF.TORSO, "_fine") / "x_packed.npy").exists():
        pytest.skip("CORRIE F fine drape missing: run corrie_f_sim.py fine --torso 19")
    sc = CF.scene("day", level=1)
    names = [p.name for p in sc.parts]
    assert not any(n.startswith(("corrie_wing_", "crown_hood", "hood_ladders", "hood_lining")) for n in names)
    assert not any("pouch" in n for n in names)                  # day mode: top pouch off
    for n in ("s15_W1", "s15_W2", "s15_W3", "s15_roll", "cf_guy_toggles@t19", "corrie_door", "corrie_kick"):
        assert n in names, n
    by = {p.name: p for p in sc.parts}
    assert by["cf_guy_toggles@t19"].material == "blaze" and by["corrie_kick"].material == "camo"
    # blade U: camo right up both corner seams to the collar seam, and across the floor edge
    Vk = np.asarray(by["corrie_kick"].mesh.vertices)
    assert Vk[:, 2].max() > 700.0 and Vk[:, 2].min() < 80.0
    assert np.ptp(Vk[:, 0]) > 330.0
    # IM3 carabiners only (two), no IM2 hooks
    Vh = np.asarray(by["bag_hooks"].mesh.vertices)
    assert Vh[:, 2].min() > 400.0
    # roll-clip tab lower than BL-020's: the clip strap reaches 150 mm below the collar seam
    z_seam = sc.cloth_meta["z_seam"]
    assert abs(sc.cloth_meta["z_clip"] - (z_seam - CF.CLIP_BELOW_SEAM_MM)) < 1e-6
    assert CP.SHELL_PROVIDERS[CF.SHELL].viz_door is False        # the door swap is undone
    assert CO.DOOR["r"] == 60.0 and CO.DOOR["inset"] == 45.0
