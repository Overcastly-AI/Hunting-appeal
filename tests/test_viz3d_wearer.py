"""huntkit.viz3d.wearer (BL-019): the ANSUR-derived figure spec and the asset manifest always; the built figure's
dimensions against the ANSUR targets and the pack fit only when bpy and the downloaded assets are present."""
import importlib.util
import json
import re

import pytest

from huntkit.viz3d import wearer as W


def test_default_hunter_is_six_feet_and_sets_the_torso_from_ansur():
    s = W.figure_spec()
    assert s["sex"] == "male" and s["stature"] == pytest.approx(1829.0)
    a, b, _ = W.ANSUR["male"]["reg"]["torso"]
    assert s["torso_mm"] == pytest.approx(a + b * 1829.0)
    assert s["torso_mm"] == pytest.approx(471.6, abs=0.3)                 # 18.6 in
    assert s["torso_setting_in"] == 18.5                                    # nearest 0.5 in crown setting, not 19
    assert 84.0 < s["stature_pct"] < 87.0                                   # 1829 mm is about the 86th percentile man
    d = s["dims"]
    assert d["cervicaleheight"] - d["iliocristaleheight"] == pytest.approx(d["torso"], abs=0.2)


def test_regression_table_is_self_consistent():
    for sex in ("male", "female"):
        reg = W.ANSUR[sex]["reg"]
        for k in ("a", "b"):
            i = 0 if k == "a" else 1
            assert reg["cervicaleheight"][i] - reg["iliocristaleheight"][i] == pytest.approx(reg["torso"][i], abs=0.02)
        mean = W.ansur_predict(sex, W.ANSUR[sex]["stature_mean"])
        assert 0.84 < mean["cervicaleheight"] / W.ANSUR[sex]["stature_mean"] < 0.88
        q = W.ANSUR_Q[sex]
        assert all(x <= y for x, y in zip(q["torso"], q["torso"][1:])) and len(q["torso"]) == 21


def test_variants_and_setting_steps():
    lo, hi = W.figure_spec(15), W.figure_spec(23)
    assert lo["sex"] == "female" and lo["torso_mm"] == pytest.approx(381.0) and lo["torso_setting_in"] == 15.0
    assert hi["sex"] == "male" and hi["torso_mm"] == pytest.approx(584.2) and hi["torso_setting_in"] == 23.0
    assert lo["stature"] < 1829 < hi["stature"]
    assert hi["torso_pct"] == 100.0                                         # 23 in is beyond ANSUR II: extrapolated
    assert W.torso_setting_in(471.6) == 18.5 and W.torso_setting_in(300) == 15.0 and W.torso_setting_in(700) == 23.0


def test_manifest_every_asset_has_a_commercial_licence_and_checksum():
    m = W.load_manifest()
    ids = [a["id"] for a in m["assets"]]
    assert {"mpfb", "mh_system_assets", "ph_hdri", "ph_grass_diff"} <= set(ids) and len(ids) == len(set(ids))
    for a in m["assets"]:
        assert a["url"].startswith("https://") and re.fullmatch(r"[0-9a-f]{64}", a["sha256"])
        assert a["commercial_use"] is True and "CC0" in a["licence"]
        assert a["bytes"] > 0 and a["dir"] and a["file"]


def test_outfits_use_palette_colours_only():
    pal = W.palette()
    for o in W.OUTFITS.values():
        for k in ("top", "pants", "cap"):
            assert o[k] in pal, o[k]
    assert set(W.SHOTS[s]["pose"] for s in W.DEFAULT_SHOTS) == set(W.POSES)


HAS_BPY = importlib.util.find_spec("bpy") is not None
needs_assets = pytest.mark.skipif(not (HAS_BPY and W.assets_ready()),
                                  reason="needs bpy (huntkit/viz3d/README.md) and the human assets (wearer fetch)")


@needs_assets
def test_built_figure_matches_ansur_targets():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = W.figure_spec()
    t = W.tune_figure(s)
    m, tgt = t["measured"], t["target"]
    assert m["stature"] == pytest.approx(1829.0, abs=1.0)
    for k in ("cervicaleheight", "iliocristaleheight", "crotchheight"):
        assert m[k] == pytest.approx(tgt[k], abs=5.0), k
    assert m["torso"] == pytest.approx(s["torso_mm"], abs=5.0)
    # girth: the waist morph is capped to keep the lumbar hollow; the figure must stay within 1 SEE of the regression
    see = W.ANSUR["male"]["reg"]["waistcircumference"][2]
    assert abs(m["waistcircumference"] - tgt["waistcircumference"]) < see
    assert abs(t["details"]["torso/measure-waist-circ"]) <= W.WAIST_MORPH_MAX + 1e-9


@needs_assets
@pytest.mark.skipif(not W.PACK_GLB.exists(), reason="pack GLB not built (wearer model)")
def test_pack_sits_on_the_body():
    W.clear_scene()
    w = W.build_wearer(pose="stand")
    f = w.fit
    assert f["torso_setting_in"] == 18.5
    assert f["belt_mid_z_back_mm"] == pytest.approx(W.ILIAC_CREST_Z, abs=5.0)       # belt centred on the crest
    assert f["belt_mid_z_side_mm"] == pytest.approx(W.ILIAC_CREST_Z, abs=8.0)
    for part in ("harness", "belt"):                      # pads touch the cloth over (nearly) their whole footprint
        assert f[part]["pad_contact_fraction"] > 0.97 and f[part]["pad_gap_mm_max"] < 25.0, f[part]
        assert 3.0 < f[part]["press_mm_mean"] < 12.0
    assert 25.0 < min(f["lifter_angle_deg"]) and max(f["lifter_angle_deg"]) < 50.0
    assert f["head_gap_mm"] > 40.0
    assert len(w.pack) > 50 and len(w.figure) >= 7 and w.rig is None
    json.dumps(f)                                                           # plain numbers only
