"""BL-012 / BL-026: CORRIE F rev 1 studio scene (huntkit/viz3d/corrie_f.py).

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


DAY_BLADE_U = {"z_low_max": 115.0, "width_min": 290.0}       # day-state bounds, see test_scene_builds_as_corrie_f


def test_outboard_hull_is_the_taut_line():
    # a to b round a half disc of radius 50 centred between them: two tangents (86.6 mm) and a 60 degree arc
    a = np.linspace(0, np.pi, 400)
    disc = np.column_stack([100.0 + 50.0 * np.cos(a), 50.0 * np.sin(a)])
    ch = CF._outboard_hull(disc, [0.0, 0.0], [200.0, 0.0], 0.0, [100.0, 500.0])
    L = float(np.linalg.norm(np.diff(ch, axis=0), axis=1).sum())
    assert abs(L - (2 * np.sqrt(100.0 ** 2 - 50.0 ** 2) + 50.0 * np.pi / 3)) < 0.5
    assert np.allclose(ch[0], [0, 0]) and np.allclose(ch[-1], [200, 0]) and ch[:, 1].min() >= 0.0
    # points on the other side of a-b are ignored; with nothing on the asked side the line is straight
    other = disc * [1.0, -1.0]
    assert len(CF._outboard_hull(other, [0.0, 0.0], [200.0, 0.0], 0.0, [100.0, 500.0])) == 2
    # lift stands the line off the cloud
    up = CF._outboard_hull(disc, [0.0, 0.0], [200.0, 0.0], 3.0, [100.0, 500.0])
    assert abs(up[:, 1].max() - 53.0) < 0.3


def test_restrap_and_panel_binding_on_a_plain_scene():
    import trimesh
    from huntkit.viz3d import studio
    from huntkit.viz3d.assets import webbing as WB
    sc = studio.ConceptScene("bl026_parts")
    P = np.column_stack([np.linspace(-100, 100, 60), np.zeros(60), np.full(60, 50.0)])
    N = np.tile([0.0, 1.0, 0.0], (60, 1))
    m = WB.strap(P, N, 38.0)
    m.metadata["straps"] = [m.metadata["strap"]]
    sc.add_part("under_straps", m, "webbing")
    assert abs(np.ptp(np.asarray(m.vertices)[:, 2]) - 38.0) < 1.0
    recs = CF.restrap(sc, "under_straps")
    V = np.asarray(sc.parts[0].mesh.vertices)
    assert len(recs) == 1 and recs[0]["width"] == CF.STRAP_W == 25.0
    assert abs(np.ptp(V[:, 2]) - 25.0) < 1.0 and abs(np.ptp(V[:, 0]) - 200.0) < 1.0
    assert CF.restrap(sc, "no_such_part") == []
    # back panel: a 370 x 13 x 440 slab; the binding wraps its whole edge, BIND_W on each face, 1 mm proud
    slab = trimesh.creation.box(extents=(370.0, 13.0, 440.0))
    slab.apply_translation([0.0, -25.0, 260.0])
    slab = slab.subdivide().subdivide().subdivide()
    sc.add_part("back_panel", slab, "spacer", group="backpanel")
    info = CF.panel_binding(sc)
    b = next(x for x in sc.parts if x.name == "back_panel_binding")
    Vb = np.asarray(b.mesh.vertices)
    assert b.material == "body" and b.group == "backpanel"
    assert abs(info["loop_mm"] - 2 * (370.0 + 440.0)) < 1.0
    assert np.allclose(Vb.max(0), [186.15, -17.5, 481.15], atol=0.6) and np.allclose(Vb.min(0), [-186.15, -32.5, 38.85], atol=0.6)
    inside = np.minimum(185.0 - np.abs(Vb[:, 0]), np.minimum(Vb[:, 2] - 40.0, 480.0 - Vb[:, 2]))
    assert inside.max() <= CF.BIND_W + 0.5                       # nothing reaches further in than the band
    fn = np.asarray(trimesh.Trimesh(Vb, np.asarray(b.mesh.faces), process=False).face_normals)
    aft = np.asarray(b.mesh.faces)[fn[:, 1] > 0.9]
    assert len(aft) and Vb[np.unique(aft)][:, 1].min() > -20.0    # the faces that look aft are the aft band


def test_final_h1_body_is_the_frame():
    if not CF.H1_FINAL_STL.exists():
        pytest.skip("print/frame_h1/h1_assembled.stl missing")
    d = CF.h1_dir()
    assert (d / "genframe_assembled.stl").stat().st_size == CF.H1_FINAL_STL.stat().st_size
    assert CF.viz_params()["generative_frame_dir"] == str(d)
    assert "BL-027" in CF.frame_note() and "28 mm" in CF.frame_note()


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
    assert not any(n.startswith("cf3_") for n in names)          # BL-030 rev 3: crown lid and its straps off too
    assert not any(n in ("cf_guy_R@t19", "cf_guy_L@t19") for n in names)    # rev 3: no outside guys
    for n in ("s15_W1", "s15_W2", "s15_W3", "s15_roll", "cf_guy_toggles@t19", "corrie_door", "corrie_kick",
              "cf_guy_stub_R@t19", "cf_guy_stub_L@t19", "cf_ports", "cf_guy_loops@t19", "cf_keeper_B26",
              "back_panel_binding"):
        assert n in names, n
    assert "corrie_top_guys@t19" not in names                    # the rev 0 guys are replaced, not doubled
    by = {p.name: p for p in sc.parts}
    assert by["cf_guy_toggles@t19"].material == "blaze" and by["corrie_kick"].material == "camo"
    # blade U: camo right up both corner seams to the collar seam, and across the floor edge. Bounds for the DAY
    # state (BL-026): at 12 L the solved floor lifts and the bag draws in, so the strip sits higher and narrower than
    # at 6-day (81 mm, 365 mm) or full (44 mm, 377 mm). Measured at level 1: lowest point 105 mm, width 304 mm.
    Vk = np.asarray(by["corrie_kick"].mesh.vertices)
    assert Vk[:, 2].max() > 700.0 and Vk[:, 2].min() < DAY_BLADE_U["z_low_max"]
    assert np.ptp(Vk[:, 0]) > DAY_BLADE_U["width_min"]
    assert abs(Vk[:, 0].min() + Vk[:, 0].max()) < 40.0           # still about the centre line (crumpled, not skewed)
    # rev 1 (BL-022): guys at x +/-52 on the bridle, clear of the lifters; keeper cord on the right gusset
    BC, CO, F, CS = CF._mods()
    gx = F.REVS[1]["guy_x"]
    Vl = np.asarray(by["cf_guy_loops@t19"].mesh.vertices)
    assert abs(np.abs(Vl[:, 0]).max() - (gx + F.GUY_W / 2)) < 2.0          # sleeves 25 mm wide centred on x 52
    Vt = np.asarray(by["cf_guy_toggles@t19"].mesh.vertices)
    for sx in (1, -1):
        side = Vt[Vt[:, 0] * sx > 0]
        assert abs(0.5 * (side[:, 0].min() + side[:, 0].max()) - sx * gx) < 1.0
        Vg = np.asarray(by[f"cf_guy_stub_{'R' if sx > 0 else 'L'}@t19"].mesh.vertices)
        # rev 3 (BL-030): outside, the port guy only runs from its sleeve to the B-27 port, inside the bar band
        assert np.abs(np.abs(Vg[:, 0]) - gx).max() < F.GUY_W / 2 + 1.0
    Vkc = np.asarray(by["cf_keeper_B26"].mesh.vertices)
    # right gusset, seam to seam. At the day load the gusset is cinched to about half its drafted 214 mm depth
    # (95 mm measured at level 1); at full load the cord spans 200 mm
    assert Vkc[:, 0].min() > 100.0 and np.ptp(Vkc[:, 1]) > 60.0
    assert sc.report["rev1"]["straps_25"]["under_straps"] == 2
    for n in ("under_straps", "under_straps_slack", "cradle_straps", "meat_straps", "corrie_im_straps"):
        assert {r["width"] for r in by[n].mesh.metadata["straps"]} == {CF.STRAP_W}, n
    Vb, Vp = (np.asarray(by[n].mesh.vertices) for n in ("back_panel_binding", "back_panel"))
    assert by["back_panel_binding"].material == "body"
    assert np.all(np.abs(Vb.max(0) - Vp.max(0)) < 2.5) and np.all(np.abs(Vb.min(0) - Vp.min(0)) < 2.5)
    assert "BL-027" in sc.report["source"]["frame"]
    # IM3 carabiners only (two), no IM2 hooks
    Vh = np.asarray(by["bag_hooks"].mesh.vertices)
    assert Vh[:, 2].min() > 400.0
    # roll-clip tab lower than BL-020's: the clip strap reaches 150 mm below the collar seam
    z_seam = sc.cloth_meta["z_seam"]
    assert abs(sc.cloth_meta["z_clip"] - (z_seam - CF.CLIP_BELOW_SEAM_MM)) < 1e-6
    assert CP.SHELL_PROVIDERS[CF.SHELL].viz_door is False        # the door swap is undone
    assert CO.DOOR["r"] == 60.0 and CO.DOOR["inset"] == 45.0


@pytest.mark.skipif(not _has_solver(), reason="needs bpy (set HUNTKIT_BPY to the Blender venv's python)")
def test_rev3_lid_and_crown_straps_are_native():
    """BL-030: the 6-day scene draws rev 3 itself: crown lid (variant lid), crown straps over it (25 mm since BL-031), no
    pouch."""
    BC, CO, F, CS = CF._mods()
    if not (CS.run_dir("F", CF.TORSO, "_fine") / "x_packed.npy").exists():
        pytest.skip("CORRIE F fine drape missing: run corrie_f_sim.py fine --torso 19")
    assert F.REVISION == 3
    sc = CF.scene("sixday", level=1)
    by = {p.name: p for p in sc.parts}
    assert not any("pouch" in n for n in by)
    for n in ("cf3_lid", "cf3_lid_caps", "cf3_lid_base", "cf3_crown_R", "cf3_crown_L", "cf3_crown_toggles", "cf_ports"):
        assert n in by, n
    assert by["cf3_lid"].variant == "lid" and by["cf3_crown_R"].variant == "lid"   # add-on: off when the lid is off
    assert by["cf3_lid_caps"].material == "camo"
    r = sc.report["rev3"]
    assert r["strap_w_mm"] == F.crown_strap_w() == 25.0             # BL-031: 25 mm, cut for crown kit M
    # BL-031: a lock at each end; both tails drawn at their real 6-day length, rolled in a keeper
    want = F.crown_kit_straps("M")["tails_mm"]["sixday"]["mid_torso"]
    for k in ("front_R", "front_L", "rear_R", "rear_L"):
        assert r["tails"][k]["tail_mm"] == pytest.approx(want, abs=0.1)
    for n in ("cf3_crown_lock_rear_R", "cf3_crown_tail_R__keeper", "cf_roll_clip_tail_R__keeper"):
        assert n in by, n
    assert by["cf3_crown_tail_R__keeper"].material == "elastic"
    for s in ("R", "L"):
        P = np.asarray(by[f"cf3_crown_{s}"].mesh.vertices)
        # stays in its x +/-52 line: the mesh edge is half the strap width off it (25 mm since BL-031) + 1 mm
        assert np.abs(np.abs(P[:, 0]) - F.CROWN_X).max() < r["strap_w_mm"] / 2 + 1.0
        assert P[:, 2].max() > r["lid_top_z"]                                     # over the lid, not through it
        assert 350.0 < r["straps"][s]["length_mm"] < 700.0
    Vl = np.asarray(by["cf3_lid"].mesh.vertices)
    assert np.ptp(Vl[:, 0]) <= F.LID["W"] + 2.0
