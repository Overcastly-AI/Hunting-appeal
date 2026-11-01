"""Tests for huntkit.camo: seamlessness, determinism, colour maths, coverage."""
import numpy as np
import pytest

from huntkit.camo import color, engine, noise, vision

PATTERNS = ["cirquefall", "cirquefall_shard", "cirquefall_firn", "cirquefall_firn_shard"]


@pytest.fixture(scope="module")
def specs():
    return {n: engine.load_pattern(n) for n in PATTERNS}


@pytest.fixture(scope="module")
def low_res(specs):
    """Label maps at 1 px/mm (fast) for every pattern."""
    out = {}
    for n, s in specs.items():
        m = engine.build_fields(s, s["seed"])
        out[n] = (m, engine.render_labels(m, 25.4))
    return out


# ----------------------------------------------------------------------------- seamless
def _edge_ratio(a: np.ndarray, axis: int) -> float:
    """Mean |difference| across the wrap seam divided by the mean |difference| between
    adjacent interior rows/cols. ~1 for a seamless tile, >>1 for a visible seam."""
    a = np.asarray(a, dtype=np.float64)
    d_int = np.abs(np.diff(a, axis=axis)).mean()
    first = np.take(a, 0, axis=axis)
    last = np.take(a, -1, axis=axis)
    return float(np.abs(first - last).mean() / d_int)


def test_fbm_is_periodic():
    g = noise.Grid.from_density(300, 200, 1.0)
    f = noise.fbm(g, noise.substream(1, "t"), 80, 4, 1.5)
    assert _edge_ratio(f, 0) < 1.5 and _edge_ratio(f, 1) < 1.5


@pytest.mark.parametrize("name", PATTERNS)
def test_tiles_are_seamless(low_res, name):
    model, lab = low_res[name]
    # continuous fields: seam difference like any interior neighbour difference
    for f in model.fields:
        assert _edge_ratio(f, 0) < 1.5
        assert _edge_ratio(f, 1) < 1.5
    # label map: fraction of pixels changing colour across the seam vs interior
    lab = lab.astype(np.int32)
    seam_x = np.mean(lab[:, 0] != lab[:, -1])
    int_x = np.mean(lab[:, 1:] != lab[:, :-1])
    seam_y = np.mean(lab[0, :] != lab[-1, :])
    int_y = np.mean(lab[1:, :] != lab[:-1, :])
    assert seam_x < 2.0 * int_x + 0.02
    assert seam_y < 2.0 * int_y + 0.02


def test_seamless_rgb_at_print_like_resolution(specs):
    s = specs["cirquefall_shard"]
    rgb = engine.generate(s, None, None, None, 60, s["seed"]).astype(np.float64)
    lum = rgb.mean(-1)
    assert _edge_ratio(lum, 0) < 2.0 and _edge_ratio(lum, 1) < 2.0


# ----------------------------------------------------------------------------- determinism
def test_deterministic_seed(specs):
    s = specs["cirquefall_shard"]
    a = engine.generate(s, None, None, None, 30, 123)
    b = engine.generate(s, None, None, None, 30, 123)
    c = engine.generate(s, None, None, None, 30, 124)
    assert a.shape == (449, 449, 3)
    assert np.array_equal(a, b)
    assert np.mean(np.any(a != c, axis=-1)) > 0.3


def test_generate_contract_shape_and_palette(specs):
    s = specs["cirquefall"]
    rgb = engine.generate(s, None, 380, 200, 25.4, 5)
    assert rgb.dtype == np.uint8 and rgb.shape == (200, 380, 3)
    cols = {tuple(c) for c in rgb.reshape(-1, 3)}
    pal = {color.hex_to_rgb8(c["hex"]) for c in s["palette"]}
    assert cols <= pal                       # flat colour separations: only palette inks
    alt = ["#000000", "#111111", "#222222", "#333333", "#444444", "#555555"]
    rgb2 = engine.generate(s, alt, 380, 200, 25.4, 5)
    assert {tuple(c) for c in rgb2.reshape(-1, 3)} <= {color.hex_to_rgb8(h) for h in alt}


# ----------------------------------------------------------------------------- coverage
@pytest.mark.parametrize("name", PATTERNS)
def test_palette_coverage_matches_spec(specs, low_res, name):
    s = specs[name]
    _, lab = low_res[name]
    cov = engine.coverage(lab, len(s["palette"]))
    tgt = engine.target_coverage(s)
    assert abs(tgt.sum() - 1) < 1e-9
    assert np.max(np.abs(cov - tgt)) < 0.01


def test_coverage_stable_across_dpi(specs):
    s = specs["cirquefall_shard"]
    m = engine.build_fields(s, s["seed"])
    c1 = engine.coverage(engine.render_labels(m, 25.4), 6)
    c2 = engine.coverage(engine.render_labels(m, 90), 6)
    assert np.max(np.abs(c1 - c2)) < 0.01


# ----------------------------------------------------------------------------- colour maths
def test_srgb_lab_round_trip():
    rng = np.random.default_rng(0)
    rgb = rng.random((2000, 3))
    back = color.lab_to_srgb(color.srgb_to_lab(rgb))
    assert np.max(np.abs(back - rgb)) < 1e-9
    assert np.allclose(color.srgb_to_lab([1.0, 1.0, 1.0]), [100, 0, 0], atol=1e-3)
    assert np.allclose(color.srgb_to_lab([0.0, 0.0, 0.0]), [0, 0, 0], atol=1e-6)


def test_hex_round_trip():
    for h in ["#9F9888", "#2D2B27", "#D5D6D0"]:
        assert color.rgb8_to_hex(color.hex_to_rgb8(h)) == h


# Sharma, Wu & Dalal (2005), Table 1: CIEDE2000 test data (pairs 1-34)
SHARMA = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


def test_delta_e2000_sharma_pairs():
    l1 = np.array([p[0] for p in SHARMA])
    l2 = np.array([p[1] for p in SHARMA])
    expected = np.array([p[2] for p in SHARMA])
    got = color.delta_e2000(l1, l2)
    assert np.allclose(got, expected, atol=1e-4), np.c_[got, expected]
    # symmetric
    assert np.allclose(color.delta_e2000(l2, l1), expected, atol=1e-4)


# ----------------------------------------------------------------------------- vision
def test_dichromat_sim_properties():
    grey = np.array([[0.5, 0.5, 0.5], [1.0, 1.0, 1.0]])
    # neutrals stay (nearly) neutral
    assert np.allclose(color.simulate_dichromat(grey), grey, atol=0.02)
    # red/green confusion: red and a matched green collapse more than for trichromats
    red, green = color.hex_to_srgb("#B04030"), color.hex_to_srgb("#707020")
    de_h = color.delta_e2000(color.srgb_to_lab(red), color.srgb_to_lab(green))
    de_d = color.delta_e2000(color.srgb_to_lab(color.simulate_dichromat(red)),
                             color.srgb_to_lab(color.simulate_dichromat(green)))
    assert de_d < 0.5 * de_h
    # protan-type: blaze orange darkens for the ungulate model
    orange = color.hex_to_srgb("#FF6A00")
    assert color.relative_luminance(color.simulate_dichromat(orange)) < color.relative_luminance(orange)


def test_distance_sim_reduces_contrast(specs):
    s = specs["cirquefall_shard"]
    rgb = engine.generate(s, None, None, None, 25.4, s["seed"])
    rms = [vision.simulate_distance(rgb, 1.0, d)[1]["rms_contrast"] for d in (10, 50, 150, 300)]
    assert all(a > b for a, b in zip(rms, rms[1:]))
    assert vision.cycle_mm(100, 6.0) == pytest.approx(290.9, rel=1e-3)


def test_colorways_share_inks_with_camo():
    import yaml
    from pathlib import Path
    cw = yaml.safe_load((Path(__file__).resolve().parents[1] / "designs/apparel/colorways.yaml").read_text())
    solids = {s["key"]: s for s in cw["solids"]}
    assert 4 <= len(solids) <= 6
    for s in solids.values():
        assert np.allclose(color.hex_to_lab(s["hex"]), s["cielab_d65"], atol=0.06)
        assert s["qc_tolerance"]["dE00"] <= 1.0
    for p in cw["accent_pairings"]:
        spec = engine.load_pattern(p["accent_pattern"])
        camo_hex = {c["hex"] for c in spec["palette"]}
        shared = [k for k in (p["body"], p["trim"]) if solids[k]["hex"] in camo_hex]
        assert len(shared) >= 1, p["id"]
