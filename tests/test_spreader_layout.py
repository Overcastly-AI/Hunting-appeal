"""Spreader layout study (BP-06 rev C): geometry rules, material data and the recorded result."""
import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign import spreader as S
from huntkit.gendesign import spreader_layout as L

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "designs" / "pack_5200" / "analysis" / "spreader_layout_results.json"


def test_hdpe_fatigue_from_basquin():
    # Djebli et al. 2014: Smax = 32.46 N^-0.067 -> 15.0 MPa at 1e5 cycles
    assert abs(L.HDPE_FAT_1E5 - 15.0) < 0.1
    sh = L.sheets()["hdpe15"]
    assert sh.fat_allow() < sh.yield_hot() < 26.0


def test_neuber_strain_monotonic():
    sh = L.sheets()["hdpe15"]
    a, b = L.ductile_strain(sh, 10.0), L.ductile_strain(sh, 40.0)
    assert a == pytest.approx(10.0 / sh.E)
    assert b > a and b == pytest.approx(40.0 ** 2 / (sh.E * sh.yield_hot()))


@pytest.mark.parametrize("key", [l.key for l in L.layouts()])
def test_ribs_flush_with_sheet_plane_and_clear_of_bores(key):
    lay = L.layout_by_key(key)
    for r in lay.ribs:
        if r.kind in ("land",):
            continue
        P = np.asarray(r.pts, float)
        mid = P[len(P) // 2] if len(P) > 2 else P.mean(0)
        x, z = mid
        yp = float(L.plane_y(z)) + r.lift
        below = np.array([[x, yp - L.LAND_FIT - 1.0 - (r.od / 2 if r.kind == "tube" else 0.0), z]])
        above = np.array([[x, yp + 0.5, z]])
        if r.kind == "rib":
            assert L.frame_sdf_layout(below, lay)[0] < 0.0          # the rib is there
        assert L.frame_sdf_layout(above, lay)[0] > 0.0              # nothing pokes through the sheet plane
    # the crown sleeve bores stay open
    for z in (200.0, 330.0, 420.0):
        bore = np.array([[s * 115.0, float(S.sleeve_y(z)), z] for s in (1, -1)])
        assert (L.frame_sdf_layout(bore, lay) > 0).all()


@pytest.mark.parametrize("key", [l.key for l in L.layouts()])
def test_members_clear_the_cleats(key):
    hz = S.FAIRLEAD_HALF_Z + S.NOTCH_CLEAR
    for r in L.layout_by_key(key).ribs:
        if r.kind == "land":
            continue
        P = np.asarray(r.pts, float)
        for zf in S.FAIRLEADS_Z:
            near = (np.abs(P[:, 1] - zf) < hz) & (np.abs(P[:, 0]) > S.STAY_X - S.FAIRLEAD_HALF_X - S.NOTCH_CLEAR)
            assert not near.any(), (key, r.tag, zf)


def test_tube_socket_is_a_cup():
    lay = L.layout_by_key("d_tubes")
    t = lay.tubes[0]
    x, z = t.pts[-1]
    yc = float(L.plane_y(z)) + t.lift - L.LAND_FIT - t.od / 2
    inside_bore = np.array([[x - 6.0, yc, z]])
    in_wall = np.array([[x - 6.0, yc - t.od / 2 - 1.2, z]])
    assert L._socket_sdf(inside_bore, t)[0] > 0
    assert L._socket_sdf(in_wall, t)[0] < 0


def test_recorded_result_meets_requirements():
    if not RESULTS.exists():
        pytest.skip("run python -m huntkit.gendesign.spreader_layout_report")
    r = json.loads(RESULTS.read_text())
    ch = next(x for x in r["rows"] if x["layout"] == r["chosen"])
    fr = next(f for f in r["frames"] if f["key"] == r["chosen"])
    assert fr["sf_min"] >= 1.0 and fr["sf_fatigue"] >= 1.0 and fr["sf_creep"] >= 1.0
    fin = next(x for x in r["final"] if x["sheet"] == "hdpe15")
    assert fin["passes_barrier"]
    assert fin["rib_sf_fact"] >= 1.0 and fin["rib_sf_fatigue"] >= 1.0
    assert fin["clear_walk_min"] >= S.MESH_T and fin["clear_fact_min"] >= 0 and fin["clear_fact_lean_min"] >= 0
    assert fin["skin_peak_kpa"] <= S.PEAK_KPA
    m = r["mass"]
    assert abs(m["total_g"] - (m["frame_delta_g"] + m["sheet_g"] + m["clips_g"] + m["tubes_g"])) < 0.5
    assert m["total_g"] < 230.0               # the thin-sheet option is heavier than the 154 g sandwich (record)
    assert r["sandwich_recheck"]["clear_fact_lean_min"] >= 0.0
    assert ch["passes"]
    for p in (r["files"]["dxf"], r["files"]["drawing"], r["doc"]):
        assert (ROOT / p).exists()
    # owner 2026-11-05: d6L is an alternative. Its socketed frame must never be recorded as the production print file.
    for p in (r["files"]["assembled"], r["files"]["barrier"]):
        assert not p.startswith("designs/pack_5200/print/frame/"), p
    for s in r["screens"]:
        f = ROOT / s
        assert f.exists() and f.stat().st_size <= 1_500_000


def test_alternative_never_writes_production_print_folder():
    from huntkit.gendesign import spreader_layout_report as R
    assert R.ALT_PRINT != R.PRINT and R.PRINT not in R.ALT_PRINT.parents
