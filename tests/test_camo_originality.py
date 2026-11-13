"""huntkit.camo.originality: the copy indicator separates a derivative from same-style art."""
import warnings

import numpy as np
import pytest

from huntkit.camo import originality as O, owner_base as ob

warnings.simplefilter("ignore", ob.ProxyWarning)


@pytest.fixture(scope="module")
def calib():
    return O.calibrate()


def test_copy_is_flagged(calib):
    assert calib["owner_vs_shift_scale_noise_copy"]["ncc_max"] >= O.NCC_COPY


def test_same_statistics_different_art_is_not_flagged(calib):
    r = calib["owner_vs_proxy_same_statistics"]
    assert r["ncc_max"] < O.NCC_CLEAR
    assert r["spectrum_corr"] > 0.95          # the spectrum alone cannot tell them apart: that is the point


def test_other_family_is_clear(calib):
    assert calib["owner_vs_cirquefall_shard"]["ncc_max"] < O.NCC_CLEAR


def test_flip_and_rotation_are_caught():
    rng = np.random.default_rng(0)
    a = (rng.random((60, 60)) > 0.5).astype(np.uint8)
    a = np.kron(a, np.ones((4, 4), np.uint8)) * 200
    rgb = np.stack([a] * 3, -1)
    b = np.rot90(rgb[:, ::-1], 1)
    r = O.image_similarity(rgb, np.ascontiguousarray(b), 1.0, 1.0, target_ppmm=1.0, scales=(1.0,))
    assert r["ncc_max"] > 0.95


def test_descriptor_and_reference_overlap():
    base = ob.load_owner_base()
    d = O.describe(base.rgb(380), 1.0, target_ppmm=1.0)
    assert d["n_inks"] == 4 and not d["continuous_tone"]
    assert d["digital_micro"] and d["vertical_streaks"]
    refs = {r["id"]: r for r in O.compare_to_references(d)}
    assert refs["sitka_optifade"]["same"] == ["digital_micro"]          # concept overlap is reported, not hidden
    assert refs["first_lite_fusion_cipher_specter"]["family_overlap"] is None   # nothing published to compare
    for r in O.load_refs():
        assert r["sources"], r["id"]                                  # every reference is cited
