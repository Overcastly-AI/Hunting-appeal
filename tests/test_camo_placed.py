"""huntkit.camo.placed: DXF import, packing, phase engineering, placed-sheet render, and the CORRIE F
rev 3 camo release generator (fast mode)."""
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from shapely.geometry import Polygon, box

from huntkit.camo import placed as P

ROOT = Path(__file__).resolve().parents[1]
DXF = ROOT / "outputs" / "release" / "pack5200_corrie_f_rev3" / "patterns" / "dxf" / "primary" / \
    "polyester_ht_630d_printable.dxf"
need_dxf = pytest.mark.skipif(not DXF.exists(), reason="release DXF not present")


def _u_piece():
    """A U: 200 wide, 300 tall, 40 mm legs and a 40 mm base (piece frame, y up)."""
    outer = [(0, 0), (200, 0), (200, 300), (160, 300), (160, 40), (40, 40), (40, 300), (0, 300)]
    return P.PieceGeom("U", "u", Polygon(outer), None, 90.0, 1)


def test_grain_rotations():
    assert P.grain_rotations(90.0) == (0.0, 180.0)
    assert P.grain_rotations(0.0) == (90.0, 270.0)


def test_pack_into_respects_region_and_spacing():
    region = box(0, 0, 100, 100)
    items = [P.Item(f"r{i}", box(0, 0, 40, 40), (0.0,)) for i in range(4)]
    placed, left = P.pack_into(region, items, spacing_mm=6.0, step_mm=2.0)
    assert len(placed) == 4 and not left
    for a in placed:
        assert region.buffer(1e-6).contains(a.polygon)
        for b in placed:
            if a is not b:
                assert a.polygon.distance(b.polygon) >= 6.0 - 1e-6
    # a fifth does not fit
    placed, left = P.pack_into(region, items + [P.Item("r5", box(0, 0, 40, 40), (0.0,))], 6.0, 2.0)
    assert len(left) == 1


def test_set_tile_fills_the_u_hole():
    u = _u_piece()
    small = P.PieceGeom("S", "s", box(0, 0, 50, 80), None, 90.0, 2)
    t = P.set_tile([u, small], spacing_mm=6.0, step_mm=2.0)
    assert not t.unplaced
    assert t.width_mm == pytest.approx(200) and t.length_mm == pytest.approx(300)   # nothing grew the tile
    big = t.placed[0].polygon
    for p in t.placed[1:]:
        assert p.polygon.distance(big) >= 6.0 - 1e-6


def test_clean_hairlines_removes_only_1px_lines():
    L = np.zeros((40, 40), np.uint8)
    L[10:30, 10:30] = 3
    L[20, :] = 0                     # 1-px seam through the dark block
    L[5:7, 5:20] = 1                 # a 2-px real feature stays
    C = P.clean_hairlines(L)
    assert (C[20, 10:30] == 3).all()
    assert (C[5:7, 5:20] == 1).all()


def test_render_is_upright_and_phase_exact():
    """A label tile whose top half is ink 3: the art must be upright in the PIECE frame at 0 and 180 deg."""
    n, rep = 100, 100.0
    lab = np.zeros((n, n), np.uint8)
    lab[: n // 2] = 3
    pg = P.PieceGeom("Q", "q", box(0, 0, 100, 100), None, 90.0, 1)
    for rot in (0.0, 180.0):
        it = P.Item("Q#1", P._flip_y(pg.cut), (rot,), pg)
        sheet = P.Sheet("t", 140, 140, 0, [])
        pl, _ = P.pack_into(box(20, 20, 140, 140), [it], 0.0, 1.0)
        sheet.placed = pl
        img = np.asarray(P.render_sheet(sheet, lab, rep, ["#AE9D6C", "#8B8148", "#C6B497", "#313120"], 25.4,
                                        {"Q#1": (0.0, 0.0)}, bleed_mm=0, cutline_mm=0.1))
        x0, y0 = int(pl[0].polygon.bounds[0]), int(pl[0].polygon.bounds[1])
        top = img[y0 + 10, x0 + 50]
        bot = img[y0 + 90, x0 + 50]
        dark, light = (0x31, 0x31, 0x20), (0xAE, 0x9D, 0x6C)
        # rot 0: piece top is the sheet top. rot 180: the piece lies inverted on the cloth, so its
        # top (dark half of the art) must be at the sheet bottom: upright once sewn on the bag.
        assert tuple(top) == (dark if rot == 0 else light), rot
        assert tuple(bot) == (light if rot == 0 else dark), rot


def test_choose_phase_prefers_dark_on_the_edges():
    n, rep = 200, 200.0
    lab = np.zeros((n, n), np.uint8)
    lab[:, :30] = 3                                          # one dark vertical stripe
    lab[:, 100:110] = 2
    pg = P.PieceGeom("B", "b", box(0, 0, 60, 150), None, 90.0, 1)
    (px, _), _ = P.choose_phase(lab, rep, pg, ppmm=1.0, n_candidates=200, seed=3, edge_mm=10)
    crop, mask = P.sample_piece(lab, rep, pg.visible, (px, 0.0), 1.0)
    assert (crop[mask] == 3).any()


@need_dxf
def test_release_dxf_pieces():
    pcs = {p.piece_id: p for p in P.read_dxf_pieces(DXF)}
    assert set(pcs) == {"B-02u", "SH-07", "SH-01b", "FP-b", "B-29f", "A1-d"}
    assert pcs["B-02u"].cut.area / 1e6 == pytest.approx(0.11019, abs=2e-4)     # cutlist.csv area_m2
    assert pcs["SH-01b"].quantity == 2 and pcs["B-29f"].quantity == 2
    assert pcs["B-29f"].grain_deg == pytest.approx(0, abs=1)
    net = sum(p.cut.area * p.quantity for p in pcs.values()) / 1e6
    assert net == pytest.approx(0.2010, abs=5e-4)                                 # cutlist net 0.2010 m2
    t = P.set_tile(list(pcs.values()))
    assert not t.unplaced
    assert t.utilisation > 0.6                                                    # vs 0.47 on the 10-bag marker


@need_dxf
def test_release_generator_fast(tmp_path):
    sys.path.insert(0, str(ROOT / "designs" / "pack_5200"))
    import camo_corrie_f_rev3 as G
    warnings.simplefilter("ignore")
    r = G.run(dpi=40.0, out=tmp_path, screens=False, verbose=False)
    assert {"corrie_f_rev3_camo_hyperd300_1yd_3sets", "corrie_f_rev3_camo_hyperd300_1yd_2sets_ab1",
            "corrie_f_rev3_camo_630d_engineered_repeat_3sets", "corrie_f_rev3_camo_1set_tile"} <= set(r["sheets"])
    for m in r["sheets"].values():
        assert not m["notes"]
        assert m["px"][0] == pytest.approx(m["width_mm"] / 25.4 * 40, abs=1)
    hd = r["sheets"]["corrie_f_rev3_camo_hyperd300_1yd_3sets"]
    assert hd["width_mm"] == pytest.approx(58 * 25.4) and hd["length_mm"] == pytest.approx(36 * 25.4)
    # printed ink shares on the pieces stay near the measured artwork
    cov = {c["key"]: c["coverage_on_pieces_pct"] for c in r["colours"]}
    assert 20 < cov["deadfall_shadow"] < 40
    assert all(c["L"] == pytest.approx(c2, abs=0.2) for c, c2 in zip(r["colours"], (65.1, 53.7, 74.1, 19.9)))
    costs = {(c["scenario"][0], c["bags"]): c for c in r["costs"]}
    assert costs[("A", 1)]["fabric_print_usd"] == pytest.approx(30.25)
    assert costs[("A", 10)]["fabric_print_usd"] == pytest.approx(4 * 30.25)
    assert (tmp_path / "colour_spec.csv").exists() and (tmp_path / "placement.csv").exists()
    im = Image.open(tmp_path / "print" / "owner_base_accent_380mm_40dpi.tif")
    assert im.size[0] == round(380 / 25.4 * 40)
