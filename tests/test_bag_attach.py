"""Bag-to-frame fairleads: loads, the bore stays open, and the FEA record clears."""
import json
from pathlib import Path

import numpy as np
import pytest

from huntkit.gendesign.bag_attach import (
    BARTACK_N,
    HOOK_N,
    SCALE,
    governing,
    pin_check,
)
from huntkit.gendesign.frame_branch import _sleeve_y, frame_sdf, stay_radius

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "designs" / "pack_5200" / "analysis" / "bag_attachment_results.json"


def test_hinge_is_the_heavy_factored_load():
    gov = governing()
    hinge = gov["hinge"]
    assert hinge["n"] > 700.0
    assert hinge["case"] in {"meat_straps", "tall_load", "tall_load_posts", "overload_haul"}
    assert abs(hinge["fz"]) > abs(hinge["fy"])
    # IM3 is mostly an aft pull, and it is the heavy clip
    assert gov["im3"]["n"] > gov["im1"]["n"]
    assert gov["im3"]["fy"] > 400.0
    pin = pin_check(hinge["n"], hinge["g_times_req"])
    assert pin["sf_yield"] > 2.0
    assert pin["sleeve_sf"] > 1.0
    assert HOOK_N / gov["im3"]["n"] > 1.0
    assert BARTACK_N / hinge["n"] > 1.0


def test_fairlead_does_not_fill_the_bore_or_the_branch_gap():
    def sdf(p):
        return float(frame_sdf(np.array([p], float), SCALE)[0])

    # sleeve bore, open
    yb = float(_sleeve_y(300.0))
    assert sdf([115.0, yb, 300.0]) > 2.0
    # stay wall, solid
    r = float(stay_radius(300.0, SCALE))
    assert sdf([115.0, yb + r - 2.0, 300.0]) < 0.0
    # branch gap above the mid bar (the bar itself crosses at z 330)
    z = 270.0
    yc = float(_sleeve_y(z))
    t = (z - 165.0) / 320.0
    bow = np.sin(np.pi * t)
    gap_x = 0.5 * ((115.0 - 46.0 * bow) + 6.5 * SCALE + 115.0 - float(stay_radius(z, SCALE)))
    assert sdf([gap_x, yc, z]) > 0.0
    # cheek of the IM2 fairlead is material
    z = 330.0
    yc = float(_sleeve_y(z))
    r = float(stay_radius(z, SCALE))
    # front wall of the cheek, ahead of the pin hole
    cheek_x = 115.0 + 9.0 + 4.0
    assert sdf([cheek_x, yc + r + 12.0, z]) < 0.0


def test_recorded_fairlead_clears_strength_and_fatigue():
    data = json.loads(RESULT.read_text())
    assert data["recommendation"] == "branch_fairlead"
    assert data["h_mm"] <= 1.0
    assert data["sf_min"] >= 1.0
    assert data["sf_fatigue_min"] >= 1.0
    assert data["sf_creep_min"] >= 1.0
    assert data["pin_sf"] > 2.0
    assert data["sleeve_sf"] > 1.0
    assert data["hook_sf"] > 1.0
    assert data["delta_g"] < 250.0
    for row in data["fea"]:
        if abs(row["h_mm"] - data["h_mm"]) < 1e-6:
            assert row["sf"] >= 1.0
            assert row["sf_fatigue"] >= 1.0
            assert abs(row["applied_n"] - row["requested_n"]) / row["requested_n"] < 0.05
    screens = data["screens"]
    assert len(screens) >= 4
    for s in screens:
        assert Path(s).exists()


def test_all_haul_modes_required():
    from huntkit.gendesign.meat_haul import analyse
    modes = analyse()
    assert "between" not in modes                     # the hinge swing is retired (owner 2026-11-06)
    for key in ("bag_on", "float", "bag_off"):
        assert modes[key]["required"] is True
        assert modes[key]["viable"] is True
        assert modes[key]["cleat_fatigue"] >= 1.0
        assert modes[key]["hook_sf"] >= 1.0
        # bearing face = Sandwich v2 on the real supports (spreader.md). HA-LS-1 puts the factor on the load,
        # so first-ply and fatigue SF >= 1.0. (The old 1.3 margin belonged to the retired QI comfort model.)
        assert modes[key]["sheet_sf"] >= 1.0
        assert modes[key]["sheet_fatigue_sf"] >= 1.0
    assert modes["bag_off"]["leg_walk_with_wraps_n"] == pytest.approx(141, abs=2)
    assert modes["bag_off"]["cradle_cam_sf"] >= 1.5
    assert modes["bag_on"]["nodes"]["us1"]["sf_fatigue"] >= 1.0
    assert modes["bag_off"]["nodes"]["us1"]["n"] > modes["bag_on"]["nodes"]["us1"]["n"]
    for name in ("20261101_attach_8_cradle_anchors.png", "20261101_attach_9_cradle_bag_on.png",
                 "20261101_attach_10_cradle_bag_off.png", "20261101_attach_11_cradle_fea.png"):
        assert (ROOT / "docs" / "screens" / name).exists()


def test_attachment_note_quotes_the_sandwich_v2_notch():
    """bag_attachment.md is generated; its spreader notch must be the Sandwich v2 notch (spreader.py), not 22 mm."""
    from huntkit.gendesign.spreader import FAIRLEAD_HALF_Z, NOTCH_CLEAR
    md = (ROOT / "designs" / "pack_5200" / "analysis" / "bag_attachment.md").read_text()
    h = 2 * (FAIRLEAD_HALF_Z + NOTCH_CLEAR)
    assert h == pytest.approx(30.0)
    assert f"notched {h:.0f} mm in height" in md
    assert "notched 22 mm" not in md
